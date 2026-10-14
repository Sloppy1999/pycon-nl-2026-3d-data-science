"""Pipeline helpers for the running example: an AHN5 point cloud of one street, turned into labels.

The deck's code slides (snippets/s08 to s14) are excerpts of these functions, with the same parameters.
Every number the deck shows is written by ``pipeline/run.py`` into ``results/pipeline.json``.

Steps and the helpers that do them:

1. Load                ``load`` (laspy), ``to_open3d`` (NumPy array to an Open3D point cloud)
2. Voxel downsampling  ``downsample`` (Open3D, one average point per voxel)
3. Ground removal      ``remove_ground`` (tiled RANSAC, Open3D ``segment_plane``)
4. Clustering          ``cluster`` (Open3D DBSCAN)
5. Labelling           ``label`` (rules per cluster: height, footprint, share of multiple returns, ...)
6. Visualisation       ``paint_back`` (one SciPy KDTree query), the PyVista renders live in ``render.py``

``score`` compares the painted-back labels with AHN's own classes (2 = ground, 6 = building).
AHN's labels are never used by steps 1 to 6: they are only read for scoring.

Conventions:
- Coordinates are local metres: ``xyz = las.xyz - las.header.mins`` (float64, C-contiguous).
  RD New coordinates are about 1.4e5 / 4.6e5; subtracting a local origin first keeps every later float32
  conversion (VTK, GPUs) precise.
- Class codes: 0 ground, 1 buildings, 2 vegetation, 3 street furniture, 4 unlabelled.
- Nothing here loops over points in Python: loops go over tiles (64 on the crop) and clusters (about 2 000).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace

import laspy
import numpy as np
import open3d as o3d
from scipy.spatial import KDTree

GROUND, BUILDINGS, VEGETATION, STREET_FURNITURE, UNLABELLED = 0, 1, 2, 3, 4
CLASS_NAMES = ("ground", "buildings", "vegetation", "street_furniture", "unlabelled")
NOISE, NOT_CLUSTERED = -1, -2  # cluster ids used by ``cluster``


# ---------------------------------------------------------------------------------------------------------
# 1 Load
# ---------------------------------------------------------------------------------------------------------
def load(path) -> tuple[laspy.LasData, np.ndarray, np.ndarray]:
    """Read a LAS/LAZ file. Returns ``(las, xyz, origin)``.

    ``origin`` is ``las.header.mins`` (float64, shape (3,)). ``xyz`` is ``las.xyz - origin`` as a float64,
    C-contiguous (N, 3) array. ``las.xyz`` itself is F-ordered and rebuilt on every access, so we take it
    once. Open3D does not read LAS/LAZ (``o3d.io.read_point_cloud("x.laz")`` returns 0 points and only
    a warning), which is why laspy loads and Open3D computes.
    """
    las = laspy.read(path)
    origin = np.asarray(las.header.mins, dtype=np.float64)
    xyz = np.ascontiguousarray(las.xyz - origin, dtype=np.float64)
    return las, xyz, origin


def to_open3d(xyz: np.ndarray, extra=None) -> o3d.geometry.PointCloud:
    """Wrap an (N, 3) float64 array as an Open3D point cloud.

    ``extra``: optional per-point values in [0, 1], shape (N,) or (N, k) with k <= 3, stored in the colour
    channels (zero-padded). Open3D's voxel downsampling averages colours per voxel, so a 0/1 flag such as
    "this pulse had multiple returns" (``las.number_of_returns > 1``) comes out of ``downsample`` as each
    voxel's share of multi-return points. Any other LAS attribute is lost by voxel downsampling.

    float32 input is accepted by ``Vector3dVector`` but is about 100 times slower, so we convert first.
    """
    pts = np.ascontiguousarray(xyz, dtype=np.float64)
    pcd = o3d.geometry.PointCloud(o3d.utility.Vector3dVector(pts))
    if extra is not None:
        e = np.asarray(extra, dtype=np.float64)
        e = e[:, None] if e.ndim == 1 else e
        if e.shape[0] != len(pts) or e.shape[1] > 3:
            raise ValueError(f"extra must have shape (N,) or (N, k<=3); got {e.shape}")
        rgb = np.zeros((len(pts), 3))
        rgb[:, : e.shape[1]] = e
        pcd.colors = o3d.utility.Vector3dVector(rgb)
    return pcd


def multi_share(pcd: o3d.geometry.PointCloud) -> np.ndarray:
    """Per-point share of multiple returns carried in colour channel 0 by ``to_open3d``."""
    if not pcd.has_colors():
        raise ValueError("point cloud has no colours: build it with to_open3d(xyz, multi_return_flag)")
    return np.asarray(pcd.colors)[:, 0].copy()


# ---------------------------------------------------------------------------------------------------------
# 2 Voxel downsampling
# ---------------------------------------------------------------------------------------------------------
def downsample(pcd: o3d.geometry.PointCloud, voxel: float) -> o3d.geometry.PointCloud:
    """One point per occupied voxel: the average (centroid) of the points in it, not an input point.

    Open3D anchors the voxel grid at ``min_bound - voxel / 2``. Colours (our multi-return flag) are
    averaged the same way. The output order is deterministic for a given input and Open3D build.
    """
    return pcd.voxel_down_sample(voxel)


# ---------------------------------------------------------------------------------------------------------
# 3 Ground removal: tiled RANSAC
# ---------------------------------------------------------------------------------------------------------
@dataclass
class TilePlane:
    """Ground plane of one tile, in local metres. ``plane`` = (a, b, c, d) with a*x + b*y + c*z + d = 0,
    unit normal, c > 0 (normal points up)."""

    ij: tuple[int, int]
    bounds: tuple[float, float, float, float]  # x0, y0, x1, y1 (local metres)
    plane: tuple[float, float, float, float]
    n_points: int  # voxels in the tile
    n_candidates: int  # voxels kept by the low-point pre-filter
    n_ground: int  # voxels labelled ground in this tile
    z_low: float  # low percentile of z in the tile (pre-filter anchor)
    z_centre: float  # height of the plane at the tile centre
    tilt_deg: float
    rejected: bool = False  # implausible plane (tilted or roof-high): plane borrowed from a neighbour
    borrowed_from: tuple[int, int] | None = None

    def as_dict(self) -> dict:
        d = asdict(self)
        d["ij"] = list(self.ij)
        d["bounds"] = [round(v, 6) for v in self.bounds]
        d["plane"] = [float(v) for v in self.plane]
        d["borrowed_from"] = list(self.borrowed_from) if self.borrowed_from else None
        d["z_low"] = round(self.z_low, 4)
        d["z_centre"] = round(self.z_centre, 4)
        d["tilt_deg"] = round(self.tilt_deg, 3)
        return d


@dataclass
class GroundParams:
    tile: float = 25.0  # tile size in metres
    threshold: float = 0.4  # RANSAC distance threshold (m); the inliers are the ground
    ransac_n: int = 3
    iterations: int = 300
    probability: float = 1.0  # 1.0: never stop early, so the result is reproducible
    seed: int = 0  # o3d.utility.random.seed, set once before the first tile
    low_percentile: float = 2.0  # pre-filter anchor: this percentile of z in the tile
    low_window: float = 1.5  # pre-filter: only points below anchor + window go into RANSAC
    max_tilt_deg: float = 15.0  # plausibility check: steeper planes are flagged
    max_above_median: float = 2.5  # plausibility check: planes this far above the median tile plane are flagged

    def as_dict(self) -> dict:
        return asdict(self)


def tiles(P: np.ndarray, size: float) -> list[np.ndarray]:
    """Split points into square tiles of ``size`` metres (plan view, local coordinates). Returns one
    index array per non-empty tile, ordered by tile (x index, then y index); indices ascend inside a
    tile."""
    if not len(P):
        return []
    ij = np.floor(P[:, :2] / size).astype(np.int64)
    key = ij[:, 0] * 100_000 + ij[:, 1]
    order = np.argsort(key, kind="stable")
    cuts = np.flatnonzero(np.diff(key[order])) + 1
    return np.split(order, cuts)


def remove_ground(pcd: o3d.geometry.PointCloud, tile: float | None = None, params: GroundParams | None = None,
                  **overrides) -> tuple[np.ndarray, list[TilePlane]]:
    """Tiled RANSAC ground removal. Returns ``(ground, planes)``: a boolean mask over the points of
    ``pcd`` and one ``TilePlane`` per tile. Parameters: ``params`` (default ``GroundParams()``), then
    ``tile`` and any ``GroundParams`` field given as a keyword override it; ``params`` is not modified.

    This crop is nearly flat; tiling also accommodates locally varying terrain.
    These parameters and the median-height roof check are crop-specific heuristics. Per tile:

    1. low-point pre-filter: only points less than ``low_window`` above the ``low_percentile``-th
       percentile of z in the tile go into RANSAC. Without it RANSAC happily fits a large flat roof (the
       roof has more points than the street below it).
    2. ``segment_plane(threshold, ransac_n, iterations, probability)`` on those points. Open3D has no seed
       argument: we call ``o3d.utility.random.seed(seed)`` once before the first tile, and pass
       ``probability=1.0`` so RANSAC never stops early. With the default probability two seeded runs can
       differ (the early stop races between threads).
    3. the plane's inliers are the ground.

    ``check_planes`` then flags planes tilted more than ``max_tilt_deg`` or more than
    ``max_above_median`` above the median tile plane (a roof that slipped through). A flagged tile
    borrows the plane of the nearest accepted tile, and its ground becomes the pre-filtered points within
    ``threshold`` of that plane. Slide 14 shows this loop and the ``check_planes`` call, so the displayed
    algorithm and the evaluated mask agree. Local Z is above the crop minimum, not height above terrain;
    every height test here is relative (to the tile's low percentile or to the median tile plane).
    """
    if tile is not None:
        overrides["tile"] = tile
    p = replace(params or GroundParams(), **overrides)  # raises TypeError for unknown names
    P = np.asarray(pcd.points)
    o3d.utility.random.seed(p.seed)
    fits = []
    for i in tiles(P, float(p.tile)):  # loop over tiles, never over points
        z0 = float(np.percentile(P[i, 2], p.low_percentile))
        low = i[P[i, 2] < z0 + p.low_window]
        if len(low) < p.ransac_n:  # too few voxels for a plane: leave the tile without ground
            continue
        plane, inl = pcd.select_by_index(low).segment_plane(p.threshold, p.ransac_n, p.iterations, p.probability)
        fits.append((i, low, inl, plane))
    return check_planes(P, fits, p)


def check_planes(P: np.ndarray, fits: list, params: GroundParams | None = None
                 ) -> tuple[np.ndarray, list[TilePlane]]:
    """Ground mask from per-tile RANSAC fits, with the plausibility check. ``fits`` holds one
    ``(i, low, inl, plane)`` per tile: the tile's indices into ``P``, its pre-filtered candidates (indices
    into ``P``), the inliers (positions in ``low``, as ``segment_plane`` returns them) and the plane.
    Returns ``(ground, planes)`` as ``remove_ground`` does. ``params`` defaults to ``GroundParams()``.
    """
    p = params or GroundParams()
    T = float(p.tile)
    ground = np.zeros(len(P), bool)
    planes: list[TilePlane] = []
    members: list[tuple[np.ndarray, np.ndarray]] = []
    for i, low, inl, plane in fits:
        inl = np.asarray(inl, dtype=np.int64)
        ground[low[inl]] = True  # inl indexes the sub-cloud; low maps it back to P
        plane = np.asarray(plane, dtype=float)
        a, b, c, d = (float(v) for v in (plane if plane[2] >= 0 else -plane))
        ij = tuple(int(v) for v in np.floor(P[i[0], :2] / T))
        x0, y0 = ij[0] * T, ij[1] * T
        # A vertical plane has no Z at the tile centre; reject it by tilt.
        zc = (-(a * (x0 + T / 2) + b * (y0 + T / 2) + d) / c
              if c > 1e-12 else float("nan"))
        planes.append(TilePlane(ij=ij, bounds=(x0, y0, x0 + T, y0 + T), plane=(a, b, c, d),
                                n_points=int(len(i)), n_candidates=int(len(low)), n_ground=int(len(inl)),
                                z_low=float(np.percentile(P[i, 2], p.low_percentile)), z_centre=float(zc),
                                tilt_deg=float(np.degrees(np.arccos(min(c, 1.0))))))
        members.append((i, low))
    # plausibility check: tilted or roof-high planes borrow the nearest accepted plane
    heights = [pl.z_centre for pl in planes if np.isfinite(pl.z_centre)]
    z_med = float(np.median(heights)) if heights else float("nan")
    for pl in planes:
        pl.rejected = pl.tilt_deg > p.max_tilt_deg or pl.z_centre > z_med + p.max_above_median
    good = [pl for pl in planes if not pl.rejected]
    for pl, (i, low) in zip(planes, members):
        if not pl.rejected:
            continue
        ground[i] = False
        pl.n_ground = 0
        if not good:  # no plausible neighbour: leave this tile unclassified
            continue
        src = min(good, key=lambda g: ((g.ij[0] - pl.ij[0]) ** 2 + (g.ij[1] - pl.ij[1]) ** 2, g.ij))
        n = np.asarray(src.plane)
        ground[low[np.abs(P[low] @ n[:3] + n[3]) <= p.threshold]] = True
        pl.plane, pl.borrowed_from = src.plane, src.ij
        pl.n_ground = int(np.count_nonzero(ground[i]))
    return ground, planes


def height_above(P: np.ndarray, ground: np.ndarray, k: int = 1) -> np.ndarray:
    """Height above local ground: z minus the z of the nearest ground point in plan view (median of the
    k nearest). One batched KDTree query on all cores."""
    G = P[ground]
    if len(G) == 0:  # no ground found: heights are measured from z = 0
        return P[:, 2].copy()
    _, j = KDTree(G[:, :2]).query(P[:, :2], k=k, workers=-1)
    zg = G[j, 2] if k == 1 else np.median(G[j, 2], axis=1)
    return P[:, 2] - zg


# ---------------------------------------------------------------------------------------------------------
# 4 Clustering
# ---------------------------------------------------------------------------------------------------------
def cluster(pcd: o3d.geometry.PointCloud, ground: np.ndarray | None, eps: float, min_points: int,
            min_height: float = 0.3) -> np.ndarray:
    """Open3D DBSCAN on what stands above the ground. Returns one cluster id per point of ``pcd``:
    0..n-1, ``NOISE`` (-1) for DBSCAN noise and ``NOT_CLUSTERED`` (-2) for ground points and for points
    at most ``min_height`` above the ground (``height_above``).

    Why skip the near-ground points: ground that RANSAC missed (a raised plaza, a sunken lane next to a
    building) otherwise links every tree on it into one huge cluster.

    ``eps`` has to scale with the voxel size: after 0.5 m voxel downsampling neighbouring points are
    about 0.5 m apart, so an eps at or below the voxel size turns most points into noise, and a much
    larger eps glues trees to the buildings next to them.
    """
    ids = np.full(len(pcd.points), NOT_CLUSTERED, dtype=np.int64)
    if ground is None:
        up = np.ones(len(ids), bool)
    else:
        up = ~ground & (height_above(np.asarray(pcd.points), ground) > min_height)
    sel = np.flatnonzero(up)
    rest = pcd.select_by_index(sel)  # keeps the original order
    ids[sel] = np.asarray(rest.cluster_dbscan(eps=eps, min_points=min_points), dtype=np.int64)
    return ids


# ---------------------------------------------------------------------------------------------------------
# 5 Labelling: cluster-level rules
# ---------------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Cluster:
    """Features of one cluster. Heights are above local ground (``height_above``), in metres."""

    n: int  # points in the cluster
    top: float  # highest point above ground
    bottom: float  # lowest point above ground
    width: float  # largest horizontal extent (x or y)
    foot: float  # footprint: occupied 1 m x 1 m cells, in m^2
    multi: float  # share of multiple returns (the colour channel carried through voxel downsampling)
    to_building: float = np.inf  # plan-view distance to the nearest building point (from rule 2)
    to_vegetation: float = np.inf  # plan-view distance to the nearest vegetation point (from rule 1)
    cx: float = 0.0  # centroid, local metres
    cy: float = 0.0

    @property
    def slender(self) -> bool:
        # pole-like: at most 1.5 m wide, taller than 1.5 m, at least twice as tall as it is wide, and
        # below 15 m. A car (about 1.5 m tall, 1.8 m wide) fails "twice as tall as wide".
        return self.width <= 1.5 and 1.5 < self.top <= 15 and self.top >= 2 * self.width

    @property
    def free(self) -> bool:
        # free-standing: more than 2 m from any building and more than 1 m from any tree (plan view)
        return self.to_building > 2 and self.to_vegetation > 1


# The labelling rules, applied to every cluster in this order (slide 12 shows this function verbatim).
# Rule 1: AHN flies leaf-off, so pulses slip between bare branches and trees echo several times, while
# roofs, roads and poles mostly return one echo. Rule 3 catches facade fragments: from the air facades
# are sparse and DBSCAN often splits them off their roof. Cars stay unlabelled: they are not slender.
def name(c):
    if c.multi > 0.4 and c.top > 1:
        return VEGETATION
    if c.foot > 25 and c.top > 2.5:
        return BUILDINGS
    if c.to_building < 2:  # facade
        return BUILDINGS
    if c.slender and c.free:
        return STREET_FURNITURE
    return UNLABELLED


def cluster_features(P: np.ndarray, hag: np.ndarray, multi: np.ndarray, ids: np.ndarray,
                     cell: float = 1.0) -> dict[str, np.ndarray]:
    """Per-cluster features as arrays indexed by cluster id, vectorised over clusters (see ``Cluster``)."""
    n_cl = int(ids.max()) + 1 if (ids >= 0).any() else 0
    c = np.flatnonzero(ids >= 0)
    k = ids[c]
    n = np.bincount(k, minlength=n_cl)
    top = np.full(n_cl, -np.inf)
    np.maximum.at(top, k, hag[c])
    bottom = np.full(n_cl, np.inf)
    np.minimum.at(bottom, k, hag[c])
    lo = np.full((n_cl, 2), np.inf)
    np.minimum.at(lo, k, P[c, :2])
    hi = np.full((n_cl, 2), -np.inf)
    np.maximum.at(hi, k, P[c, :2])
    cells = np.floor(P[c, :2] / cell).astype(np.int64)
    key = (k << 32) | ((cells[:, 0] + 2**15) << 16) | (cells[:, 1] + 2**15)
    foot = np.bincount(np.unique(key) >> 32, minlength=n_cl) * cell * cell
    safe = np.maximum(n, 1)
    return dict(n=n, top=top, bottom=bottom, width=(hi - lo).max(axis=1), foot=foot.astype(float),
                multi=np.bincount(k, weights=multi[c], minlength=n_cl) / safe,
                cx=np.bincount(k, weights=P[c, 0], minlength=n_cl) / safe,
                cy=np.bincount(k, weights=P[c, 1], minlength=n_cl) / safe)


def _min_dist_xy(P: np.ndarray, ids: np.ndarray, n_cl: int, target: np.ndarray) -> np.ndarray:
    """Per cluster: smallest plan-view distance from any of its points to any ``target`` point."""
    out = np.full(n_cl, np.inf)
    if not target.any() or n_cl == 0:
        return out
    c = np.flatnonzero(ids >= 0)
    d, _ = KDTree(P[target, :2]).query(P[c, :2], k=1, workers=-1)
    np.minimum.at(out, ids[c], d)
    return out


def label(pcd: o3d.geometry.PointCloud, ground: np.ndarray, ids: np.ndarray) -> tuple[np.ndarray, dict]:
    """Name the clusters with ``name``. Returns ``(classes, info)``: one class code per point of ``pcd``
    (ground from ``remove_ground``, DBSCAN noise and near-ground points unlabelled) and a dict with the
    per-cluster ``Cluster`` objects, their classes, the feature arrays and the height above ground.

    The loop runs over clusters (about 2 000), never over points. Rules 3 and 4 need distances to the
    buildings and trees found by rules 1 and 2, so ``name`` runs twice: first without distances (only
    rules 1 and 2 can fire), then with them.
    """
    P = np.asarray(pcd.points)
    multi = multi_share(pcd)
    hag = height_above(P, ground)
    f = cluster_features(P, hag, multi, ids)
    n_cl = len(f["n"])
    if n_cl == 0:  # DBSCAN found nothing: only ground and unlabelled points
        classes = np.full(len(P), UNLABELLED, dtype=np.uint8)
        classes[ground] = GROUND
        empty = np.empty(0)
        return classes, dict(clusters=[], cluster_classes=np.empty(0, np.uint8), first_pass=np.empty(0, np.uint8),
                             features=f, hag=hag, to_building=empty, to_vegetation=empty)
    base = [Cluster(n=int(f["n"][k]), top=float(f["top"][k]), bottom=float(f["bottom"][k]),
                    width=float(f["width"][k]), foot=float(f["foot"][k]), multi=float(f["multi"][k]),
                    to_building=np.inf, to_vegetation=0.0, cx=float(f["cx"][k]), cy=float(f["cy"][k]))
            for k in range(n_cl)]
    first = np.array([name(c) for c in base], dtype=np.uint8)  # rules 1 and 2 only
    on = ids >= 0
    d_bld = _min_dist_xy(P, ids, n_cl, on & (first[np.maximum(ids, 0)] == BUILDINGS))
    d_veg = _min_dist_xy(P, ids, n_cl, on & (first[np.maximum(ids, 0)] == VEGETATION))
    clusters = [replace(c, to_building=float(d_bld[k]), to_vegetation=float(d_veg[k])) for k, c in enumerate(base)]
    cls_cl = np.array([name(c) for c in clusters], dtype=np.uint8)
    classes = np.full(len(P), UNLABELLED, dtype=np.uint8)
    classes[ground] = GROUND
    classes[on] = cls_cl[ids[on]]
    info = dict(clusters=clusters, cluster_classes=cls_cl, first_pass=first, features=f, hag=hag,
                to_building=d_bld, to_vegetation=d_veg)
    return classes, info


# ---------------------------------------------------------------------------------------------------------
# 6 Visualisation: paint the labels back onto every original point
# ---------------------------------------------------------------------------------------------------------
def paint_back(full_xyz: np.ndarray, voxel_xyz, classes: np.ndarray, return_index: bool = False):
    """Give every original point the class of its nearest downsampled point: ONE batched KDTree query
    over all points, on all cores (``workers=-1``). ``voxel_xyz`` may be an array or an Open3D cloud."""
    V = np.asarray(voxel_xyz.points) if hasattr(voxel_xyz, "points") else np.asarray(voxel_xyz)
    _, j = KDTree(V).query(full_xyz, workers=-1)
    out = np.asarray(classes)[j]
    return (out, j) if return_index else out


# ---------------------------------------------------------------------------------------------------------
# Score against AHN (never used by the steps above)
# ---------------------------------------------------------------------------------------------------------
def precision_recall(pred: np.ndarray, truth: np.ndarray) -> dict:
    tp = int(np.count_nonzero(pred & truth))
    n_pred, n_truth = int(np.count_nonzero(pred)), int(np.count_nonzero(truth))
    return dict(precision=tp / n_pred if n_pred else None, recall=tp / n_truth if n_truth else None,
                true_positives=tp, predicted=n_pred, truth=n_truth)


def score(point_classes: np.ndarray, ahn_classes: np.ndarray) -> dict:
    """Point-level precision and recall after paint-back: ground vs AHN class 2, buildings vs AHN class 6.

    AHN puts many facade points in class 1 ("overig"), so points we call buildings on facades count as
    false positives: building precision is a lower bound.
    """
    pc, ac = np.asarray(point_classes), np.asarray(ahn_classes)
    return dict(ground=precision_recall(pc == GROUND, ac == 2), buildings=precision_recall(pc == BUILDINGS, ac == 6))
