"""Run the running-example pipeline on the AHN5 crop and write the results the deck reads.

    uv run python pipeline/run.py            # full run: pipeline, parameter sweep, determinism check
    uv run python pipeline/run.py --quick               # pipeline only (no sweep, no determinism check)

Writes (CONTRACTS.md):
    results/pipeline.json    every pipeline number on the slides (label "FINAL")
    results/labels_crop.npz  everything pipeline/render.py needs (voxels, classes, clusters, ground, tile planes,
                             the painted-back class of every point, origin)

AHN's own classes are read only to score the result (``steps.score``) and to describe the crop; no step uses them.
Deterministic: two runs give identical results except the timings (``runtime_s``, ``timings_s``) and the
deliberately non-reproducible check ``checks.ransac_default_probability``. ``--verify`` (default on) re-runs the
pipeline in a fresh process and records the comparison in ``checks.determinism``.
"""

from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import platform
import subprocess
import sys
import tempfile
import time
from importlib.metadata import version
from pathlib import Path

import numpy as np
import open3d as o3d

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline import steps as S  # noqa: E402



def _fetch_module():
    """data/fetch_ahn5.py defines the crop box (single source); load it without making data/ a package."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("fetch_ahn5", ROOT / "data" / "fetch_ahn5.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_FETCH = _fetch_module()
CROP = ROOT / "data" / _FETCH.CROP_NAME
CROP_BBOX_RD = list(_FETCH.CROP_BBOX_RD)  # x0, y0, x1, y1 (RD New, metres)

# Final parameters (why: see params_why below and the sweep in param_choice)
VOXEL = 0.5
GROUND = S.GroundParams(tile=25.0, threshold=0.4, ransac_n=3, iterations=300, probability=1.0, seed=0,
                        low_percentile=2.0, low_window=1.5, max_tilt_deg=15.0, max_above_median=2.5)
EPS, MIN_POINTS, MIN_HEIGHT = 0.75, 6, 0.3

NONDETERMINISTIC_KEYS = ("runtime_s", "timings_s", "checks")  # excluded from the determinism comparison


def r4(x):
    return None if x is None else round(float(x), 4)


def run_pipeline(path: Path, voxel: float, gp: S.GroundParams, eps: float, min_points: int, min_height: float) -> dict:
    """The seven calls of slide 14, timed. Returns every intermediate the outputs need."""
    t = {}
    t0 = time.perf_counter()
    las, xyz, origin = S.load(path)
    multi = np.asarray(las.number_of_returns) > 1
    t["load"] = time.perf_counter() - t0
    t1 = time.perf_counter()
    pcd = S.to_open3d(xyz, multi)
    t["to_open3d"] = time.perf_counter() - t1
    t1 = time.perf_counter()
    down = S.downsample(pcd, voxel)
    t["downsample"] = time.perf_counter() - t1
    t1 = time.perf_counter()
    ground, planes = S.remove_ground(down, params=gp)
    t["remove_ground"] = time.perf_counter() - t1
    t1 = time.perf_counter()
    ids = S.cluster(down, ground, eps, min_points, min_height=min_height)
    t["cluster"] = time.perf_counter() - t1
    t1 = time.perf_counter()
    classes, info = S.label(down, ground, ids)
    t["label"] = time.perf_counter() - t1
    t1 = time.perf_counter()
    point_classes, point_voxel = S.paint_back(xyz, down, classes, return_index=True)
    t["paint_back"] = time.perf_counter() - t1
    t["total"] = time.perf_counter() - t0
    return dict(las=las, xyz=xyz, origin=origin, multi=multi, pcd=pcd, down=down, ground=ground, planes=planes, ids=ids,
                classes=classes, info=info, point_classes=point_classes, point_voxel=point_voxel, timings=t)


def quick_metrics(r: dict, ahn: np.ndarray) -> dict:
    sc = S.score(r["point_classes"], ahn)
    ids, cc, first = r["ids"], r["info"]["cluster_classes"], r["info"]["first_pass"]
    considered = np.count_nonzero(ids != S.NOT_CLUSTERED)
    return dict(points_after_voxel=int(len(r["down"].points)), n_tiles=len(r["planes"]),
                tiles_flagged=int(sum(p.rejected for p in r["planes"])),
                ground=dict(precision=r4(sc["ground"]["precision"]), recall=r4(sc["ground"]["recall"])),
                buildings=dict(precision=r4(sc["buildings"]["precision"]), recall=r4(sc["buildings"]["recall"])),
                n_clusters=int(ids.max() + 1), noise_share=r4(np.count_nonzero(ids == S.NOISE) / max(considered, 1)),
                largest_cluster=int(r["info"]["features"]["n"].max()) if len(cc) else 0,
                # buildings = rule-2 roofs, as n_objects in build_json; facade fragments are not objects
                n_objects=dict(buildings=int(np.count_nonzero(first == S.BUILDINGS)),
                               **{S.CLASS_NAMES[c]: int(np.count_nonzero(cc == c))
                                  for c in (S.VEGETATION, S.STREET_FURNITURE, S.UNLABELLED)}))


def sweep(ahn: np.ndarray) -> list[dict]:
    """One-at-a-time variations around the final parameters, scored the same way (evidence for params_why)."""
    from dataclasses import replace

    variants = [
        ("final", {}),
        ("tile 50 m", dict(ground=replace(GROUND, tile=50.0))),
        ("one plane (tile 250 m)", dict(ground=replace(GROUND, tile=250.0))),  # the whole 200 m crop in one tile
        ("no low-point pre-filter", dict(ground=replace(GROUND, low_window=1e9))),
        ("RANSAC threshold 0.2 m", dict(ground=replace(GROUND, threshold=0.2))),
        ("pre-filter window 3 m", dict(ground=replace(GROUND, low_window=3.0))),
        ("eps 0.5 (= voxel size)", dict(eps=0.5)),
        ("eps 1.0", dict(eps=1.0)),
        ("min_points 5", dict(min_points=5)),
        ("min_points 10", dict(min_points=10)),
        ("no near-ground skip (min_height -inf)", dict(min_height=-np.inf)),
    ]
    out = []
    for name, v in variants:
        r = run_pipeline(CROP, VOXEL, v.get("ground", GROUND), v.get("eps", EPS), v.get("min_points", MIN_POINTS),
                         v.get("min_height", MIN_HEIGHT))
        m = quick_metrics(r, ahn)
        m["vegetation_points_ahn2"] = int(np.count_nonzero((r["point_classes"] == S.VEGETATION) & (ahn == 2)))
        out.append(dict(variant=name, **m))
    return out


PREVIOUS_STREET = ROOT / "data" / "previous" / "street_graadt_van_roggenweg_200m.laz"


def previous_street_check() -> dict | None:
    """Is the ground flat enough for one plane? The same pipeline with 25 m tiles and with one plane on the first
    example street (Graadt van Roggenweg, until 2026-10-11) against the Jaarbeurs crop's own result in single_plane."""
    from dataclasses import replace

    import laspy

    if not PREVIOUS_STREET.exists():
        return None
    ahn = np.asarray(laspy.read(PREVIOUS_STREET).classification)
    out = dict(file=str(PREVIOUS_STREET.relative_to(ROOT)), bbox_rd=list(_FETCH.PREVIOUS_STREET_BBOX_RD),
               note="the first example street, same parameters; kept in data/previous/, not used by the deck")
    for key, tile in (("tiles_25m", GROUND.tile), ("one_plane", 250.0)):
        r = run_pipeline(PREVIOUS_STREET, VOXEL, replace(GROUND, tile=tile), EPS, MIN_POINTS, MIN_HEIGHT)
        m = quick_metrics(r, ahn)
        z = [pl.z_centre for pl in r["planes"] if not pl.rejected]
        out[key] = dict(ground=m["ground"], n_tiles=m["n_tiles"], tiles_flagged=m["tiles_flagged"],
                        plane_height_range_m=[r4(min(z)), r4(max(z))])
    return out


def ransac_default_probability_check(down) -> dict:
    """Gotcha evidence: same seed, default probability, five runs. Deliberately not reproducible."""
    from dataclasses import replace

    res = {}
    for prob, key in ((1.0, "probability_1.0"), (0.99999999, "probability_default_0.99999999")):
        masks = [S.remove_ground(down, params=replace(GROUND, probability=prob))[0] for _ in range(5)]
        res[key] = dict(runs=5, voxels_differing_from_run_1=[int(np.count_nonzero(masks[0] != m)) for m in masks[1:]])
    res["note"] = ("o3d.utility.random.seed(0) before every run. With probability < 1 RANSAC may stop early and "
                   "the early stop races between threads, so seeded runs differ; with probability=1.0 they agree.")
    return res


def sf_table(r: dict, ahn: np.ndarray) -> list[dict]:
    info, origin = r["info"], r["origin"]
    pid = r["ids"][r["point_voxel"]]
    rows = []
    for k in np.flatnonzero(info["cluster_classes"] == S.STREET_FURNITURE):
        c = info["clusters"][k]
        pts = pid == k
        rows.append(dict(cluster=int(k), x_rd=round(c.cx + origin[0], 2), y_rd=round(c.cy + origin[1], 2),
                         voxels=c.n, points=int(np.count_nonzero(pts)), top_m=round(c.top, 2),
                         bottom_m=round(c.bottom, 2), width_m=round(c.width, 2), footprint_m2=c.foot,
                         multi_return_share=round(c.multi, 3), to_building_m=round(c.to_building, 2),
                         to_vegetation_m=round(c.to_vegetation, 2),
                         ahn_classes={str(a): int(n) for a, n in zip(*np.unique(ahn[pts], return_counts=True))}))
    return rows


def known_errors(r: dict, ahn: np.ndarray) -> list[dict]:
    """Clusters we call vegetation although a quarter or more of their points are AHN ground or building."""
    pid = r["ids"][r["point_voxel"]]
    info, origin = r["info"], r["origin"]
    rows = []
    for k in np.flatnonzero(info["cluster_classes"] == S.VEGETATION):
        pts = pid == k
        n = int(np.count_nonzero(pts))
        bad = int(np.count_nonzero(pts & ((ahn == 2) | (ahn == 6))))
        if n >= 500 and bad >= 0.25 * n:
            c = info["clusters"][k]
            rows.append(dict(cluster=int(k), called="vegetation", points=n,
                             ahn_classes={str(a): int(np.count_nonzero(pts & (ahn == a))) for a in np.unique(ahn)},
                             multi_return_share=round(c.multi, 3), top_m=round(c.top, 2), width_m=round(c.width, 1),
                             x_rd=round(c.cx + origin[0], 1), y_rd=round(c.cy + origin[1], 1)))
    return sorted(rows, key=lambda d: -d["points"])


def missed_small_objects(r: dict) -> dict:
    """Heuristic: free-standing, single-echo DBSCAN noise between 1.5 and 15 m, grouped within 1.5 m (plan view).
    These blobs are too small for min_points and might be poles or signs; UNVERIFIED what they are."""
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    from scipy.spatial import KDTree

    P, info, cls = np.asarray(r["down"].points), r["info"], r["classes"]
    multi = S.multi_share(r["down"])
    hag = info["hag"]
    cand = np.flatnonzero((r["ids"] == S.NOISE) & (hag > 1.5) & (hag <= 15) & (multi < 0.4))
    for target, dmin in ((S.BUILDINGS, 2.0), (S.VEGETATION, 1.0)):
        if len(cand) and np.any(cls == target):
            d, _ = KDTree(P[cls == target, :2]).query(P[cand, :2], workers=-1)
            cand = cand[d > dmin]
    groups = 0
    if len(cand):
        pairs = KDTree(P[cand, :2]).query_pairs(1.5, output_type="ndarray")
        a = coo_matrix((np.ones(len(pairs)), (pairs[:, 0], pairs[:, 1])), shape=(len(cand), len(cand)))
        groups = int(connected_components(a, directed=False)[0])
    return dict(voxels=int(len(cand)), groups=groups,
                rule="DBSCAN noise voxels 1.5 to 15 m above ground, multi-return share < 0.4, more than 2 m from "
                     "buildings and 1 m from vegetation, grouped within 1.5 m in plan view",
                note="too small for min_points; what they are is UNVERIFIED")


def cpu_name() -> str:
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.startswith("model name"):
                return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor() or platform.machine()


def versions() -> dict:
    return dict(python=platform.python_version(), numpy=np.__version__, scipy=version("scipy"),
                laspy=version("laspy"), lazrs=version("lazrs"), open3d=o3d.__version__, pyvista=version("pyvista"))


def build_json(r: dict, ahn: np.ndarray, sweep_rows, prob_check) -> dict:
    las, xyz, info = r["las"], r["xyz"], r["info"]
    n_in, n_vox = len(xyz), len(r["down"].points)
    pc, ids, cc = r["point_classes"], r["ids"], info["cluster_classes"]
    sc = S.score(pc, ahn)
    considered = np.count_nonzero(ids != S.NOT_CLUSTERED)
    f = info["features"]
    hdr = las.header
    assert all(CROP_BBOX_RD[i] <= hdr.mins[i] and hdr.maxs[i] < CROP_BBOX_RD[i + 2] for i in (0, 1))
    comp = {}
    for c in range(5):
        m = pc == c
        comp[S.CLASS_NAMES[c]] = {str(a): int(np.count_nonzero(m & (ahn == a))) for a in np.unique(ahn)}
    sf = sf_table(r, ahn)
    planes = r["planes"]
    rows = {x["variant"]: x for x in (sweep_rows or [])}
    w3, w15 = rows.get("pre-filter window 3 m"), rows.get("final")
    w50, one = rows.get("tile 50 m"), rows.get("one plane (tile 250 m)")
    tile_why = "25 m"
    if w50 and one:
        tile_why += (f": ground recall {r4(w15['ground']['recall'])} against {r4(w50['ground']['recall'])} for 50 m tiles "
                     f"('tile 50 m'); one plane for the whole crop scores {r4(one['ground']['recall'])} here "
                     "('one plane (tile 250 m)'): this ground is flat, the first example street's was not "
                     "(previous_street), so the tiles stay")
    window_why = ("1.5 m, kept from the first example street (not re-tuned: the sweep is scored against the same AHN "
                  "classes it would tune on)")
    if w3 and w15:
        # state what the sweep shows on this crop, whichever way it points
        window_why += (f"; 'pre-filter window 3 m' here: ground recall {r4(w3['ground']['recall'])} against "
                       f"{r4(w15['ground']['recall'])}, building precision {r4(w3['buildings']['precision'])} against "
                       f"{r4(w15['buildings']['precision'])}")
    out = dict(
        label="FINAL",
        versions=versions(),
        machine=dict(cpu=cpu_name(), os=f"{platform.system()} {platform.release()}"),
        crop=dict(file=str(CROP.relative_to(ROOT)), sha256=hashlib.sha256(CROP.read_bytes()).hexdigest(),
                  bbox_rd=CROP_BBOX_RD, points=int(n_in), point_format=int(hdr.point_format.id),
                  origin_local=[float(v) for v in r["origin"]], crs="EPSG:28992 + NAP (WKT record in the file)",
                  ahn_classes={str(a): int(n) for a, n in zip(*np.unique(ahn, return_counts=True))},
                  multi_return_share={"all": r4(r["multi"].mean()),
                                      **{f"ahn_class_{a}": r4(r["multi"][ahn == a].mean()) for a in np.unique(ahn)}}),
        params=dict(
            voxel=VOXEL, tile=GROUND.tile, ransac_threshold=GROUND.threshold, ransac_n=GROUND.ransac_n,
            ransac_iterations=GROUND.iterations, ransac_probability=GROUND.probability, seed=GROUND.seed,
            low_prefilter=dict(percentile=GROUND.low_percentile, window_m=GROUND.low_window),
            plausibility=dict(max_tilt_deg=GROUND.max_tilt_deg, max_above_median_m=GROUND.max_above_median),
            eps=EPS, min_points=MIN_POINTS, cluster_min_height_m=MIN_HEIGHT,
            rules=dict(
                order="first rule that fires wins; rules 3 and 4 use distances to the results of rules 1 and 2",
                source=inspect.getsource(S.name).splitlines(),
                slender=inspect.getsource(S.Cluster.slender.fget).strip().splitlines(),
                free=inspect.getsource(S.Cluster.free.fget).strip().splitlines(),
                features=dict(top="highest point above local ground (m)", foot="occupied 1 m x 1 m cells (m2)",
                              multi="share of points with number_of_returns > 1 (carried through voxel "
                                    "downsampling in a colour channel)",
                              width="largest horizontal extent (m)",
                              to_building="plan-view distance to the nearest point of a rule-2 building (m)",
                              to_vegetation="plan-view distance to the nearest point of rule-1 vegetation (m)",
                              height_above_ground="z minus z of the nearest ground voxel in plan view"))),
        params_why=dict(
            note="each reason points at a row of param_choice (one parameter changed, everything else final)",
            voxel="0.5 m, as approved in the storyboard",
            tile=tile_why,
            ransac_threshold="0.4 m: 0.2 m misses more of the uneven ground ('RANSAC threshold 0.2 m')",
            low_prefilter="without it RANSAC fits roofs and facades in several tiles, which the plausibility "
                          "check then has to catch ('no low-point pre-filter', tiles_flagged)",
            low_window=window_why,
            eps="0.75 m (1.5 voxels): 0.5 m, the voxel size, leaves most voxels as noise and finds no building; "
                "1.0 m glues buildings to trees and building recall collapses ('eps 0.5', 'eps 1.0')",
            min_points="6: 5 lets a tree fuse with a building (lower building recall); 10 turns more than half "
                       "of the voxels into noise ('min_points 5', 'min_points 10')",
            cluster_min_height="0.3 m: without it, ground that RANSAC missed links objects together, building "
                               "precision drops and more AHN ground becomes vegetation ('no near-ground skip')"),
        points_in=int(n_in),
        points_after_voxel=int(n_vox),
        kept_share=r4(n_vox / n_in),
        previous_street=previous_street_check(),
        single_plane=dict(
            ground=rows.get("one plane (tile 250 m)", {}).get("ground"),
            tiles_flagged=rows.get("one plane (tile 250 m)", {}).get("tiles_flagged"),
            note="the same pipeline with one 250 m tile, i.e. one RANSAC plane for the whole 200 m crop (sweep row "
                 "'one plane (tile 250 m)'); scored like the final run"),
        voxel_0_1=dict(voxel_m=0.1, kept_share=r4(len(S.downsample(r["pcd"], 0.1).points) / n_in),
                       note="share of the crop's points kept by voxel_down_sample(0.1), same code as step 2"),
        n_tiles=len(planes),
        tiles_flagged=int(sum(p.rejected for p in planes)),
        ground=dict(precision=r4(sc["ground"]["precision"]), recall=r4(sc["ground"]["recall"]),
                    counts={k: sc["ground"][k] for k in ("true_positives", "predicted", "truth")},
                    against="AHN class 2, point level, after paint-back"),
        buildings=dict(precision=r4(sc["buildings"]["precision"]), recall=r4(sc["buildings"]["recall"]),
                       counts={k: sc["buildings"][k] for k in ("true_positives", "predicted", "truth")},
                       against="AHN class 6, point level, after paint-back",
                       note="AHN class 1 ('overig') includes facade points and other objects. Predicted buildings "
                            "outside class 6 count as false positives here; this measures class-6 agreement, "
                            "not independently validated building precision or a proven lower bound"),
        n_clusters=int(ids.max() + 1),
        noise_share=r4(np.count_nonzero(ids == S.NOISE) / max(considered, 1)),
        noise_share_note="DBSCAN noise voxels / voxels given to DBSCAN (not ground, more than "
                         f"{MIN_HEIGHT} m above the ground)",
        voxels_not_clustered_near_ground=int(np.count_nonzero((ids == S.NOT_CLUSTERED) & ~r["ground"])),
        label_points={S.CLASS_NAMES[c]: int(np.count_nonzero(pc == c)) for c in range(5)},
        label_voxels={S.CLASS_NAMES[c]: int(np.count_nonzero(r["classes"] == c)) for c in range(5)},
        n_objects=dict(buildings=int(np.count_nonzero(info["first_pass"] == S.BUILDINGS)),
                       vegetation=int(np.count_nonzero(cc == S.VEGETATION)),
                       street_furniture=int(np.count_nonzero(cc == S.STREET_FURNITURE))),
        n_objects_note=("objects = DBSCAN clusters, not real-world objects: buildings = clusters named by rule 2 "
                        "(roofs); facade fragments (rule 3) are counted separately; one tree can be several "
                        "vegetation clusters"),
        n_clusters_by_rule=dict(
            vegetation_rule1=int(np.count_nonzero(cc == S.VEGETATION)),
            buildings_rule2=int(np.count_nonzero(info["first_pass"] == S.BUILDINGS)),
            facades_rule3=int(np.count_nonzero((cc == S.BUILDINGS) & (info["first_pass"] != S.BUILDINGS))),
            street_furniture_rule4=int(np.count_nonzero(cc == S.STREET_FURNITURE)),
            unlabelled=int(np.count_nonzero(cc == S.UNLABELLED))),
        largest_cluster_voxels=int(f["n"].max()),
        known_errors=dict(vegetation_clusters_mostly_ahn_ground_or_building=known_errors(r, ahn),
                          note="clusters of 500+ points called vegetation although at least 25 % of their points "
                               "are AHN class 2 or 6: low structures with many echoes and ground that RANSAC missed "
                               "(an empty list means no such cluster); what each one is on the ground is UNVERIFIED"),
        label_vs_ahn=dict(note="points per predicted class, split by AHN class (AHN has no vegetation or street "
                               "furniture class: both live in class 1)", **comp),
        street_furniture_objects=sf,
        street_furniture_missed_candidates=missed_small_objects(r),
        street_furniture_note=("free-standing, slender clusters with few multiple returns (rule 4). From the air a "
                               "lamp post is a few dozen points at most, and DBSCAN with min_points "
                               f"{MIN_POINTS} drops objects of fewer voxels as noise; what each object is on the "
                               "ground is UNVERIFIED"),
        tiles=[p.as_dict() for p in planes],
        runtime_s=round(r["timings"]["total"], 3),
        runtime_note="single run, load to paint-back, indicative only",
        timings_s={k: round(v, 3) for k, v in r["timings"].items()},
        param_choice=sweep_rows,
        checks=dict(ransac_default_probability=prob_check),
    )
    return out


def save_npz(path: Path, r: dict) -> None:
    info, planes = r["info"], r["planes"]
    f = info["features"]
    sf_ids = np.flatnonzero(info["cluster_classes"] == S.STREET_FURNITURE)
    np.savez_compressed(
        path,
        class_names=np.array(S.CLASS_NAMES),
        crop_file=np.array(str(CROP.relative_to(ROOT))),
        origin=r["origin"],
        voxel=np.float64(VOXEL),
        voxel_xyz=np.asarray(r["down"].points),
        voxel_multi=S.multi_share(r["down"]).astype(np.float32),
        voxel_class=r["classes"].astype(np.uint8),
        voxel_cluster=r["ids"].astype(np.int32),
        voxel_ground=r["ground"],
        voxel_hag=info["hag"].astype(np.float32),
        point_class=r["point_classes"].astype(np.uint8),
        point_voxel=r["point_voxel"].astype(np.int32),
        cluster_class=info["cluster_classes"].astype(np.uint8),
        cluster_centroid=np.c_[f["cx"], f["cy"]],
        cluster_top=f["top"].astype(np.float32),
        street_furniture_clusters=sf_ids.astype(np.int32),
        tile_ij=np.array([p.ij for p in planes], dtype=np.int32),
        tile_bounds=np.array([p.bounds for p in planes], dtype=np.float64),
        tile_plane=np.array([p.plane for p in planes], dtype=np.float64),
        tile_rejected=np.array([p.rejected for p in planes]),
        tile_size=np.float64(GROUND.tile),
    )


def compare(a_json: Path, b_json: Path, a_npz: Path, b_npz: Path) -> dict:
    A, B = json.loads(a_json.read_text()), json.loads(b_json.read_text())
    for k in NONDETERMINISTIC_KEYS:
        A.pop(k, None)
        B.pop(k, None)
    za, zb = np.load(a_npz), np.load(b_npz)
    arrays_equal = sorted(za.files) == sorted(zb.files) and all(np.array_equal(za[k], zb[k]) for k in za.files)
    return dict(json_identical=A == B, npz_arrays_identical=bool(arrays_equal),
                method="pipeline/run.py run again in a fresh process; pipeline.json compared without "
                       f"{list(NONDETERMINISTIC_KEYS)}, every labels_crop.npz array with np.array_equal")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out-dir", type=Path, default=ROOT / "results")
    ap.add_argument("--quick", action="store_true", help="pipeline only: no sweep, no checks")
    ap.add_argument("--no-verify", action="store_true", help="skip the determinism re-run")
    args = ap.parse_args()
    o3d.utility.set_verbosity_level(o3d.utility.VerbosityLevel.Error)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    r = run_pipeline(CROP, VOXEL, GROUND, EPS, MIN_POINTS, MIN_HEIGHT)
    ahn = np.asarray(r["las"].classification)
    sweep_rows = None if args.quick else sweep(ahn)
    prob = None if args.quick else ransac_default_probability_check(r["down"])
    out = build_json(r, ahn, sweep_rows, prob)
    jpath, npath = args.out_dir / "pipeline.json", args.out_dir / "labels_crop.npz"
    save_npz(npath, r)
    jpath.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    if not (args.quick or args.no_verify):
        with tempfile.TemporaryDirectory(dir=args.out_dir, prefix=".verify_") as tmp:
            subprocess.run([sys.executable, __file__, "--out-dir", tmp, "--no-verify"], check=True)
            out["checks"]["determinism"] = compare(jpath, Path(tmp) / "pipeline.json", npath, Path(tmp) / "labels_crop.npz")
        jpath.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps({k: out[k] for k in ("points_in", "points_after_voxel", "kept_share", "n_tiles", "tiles_flagged",
                                          "ground", "buildings", "n_clusters", "noise_share", "label_points",
                                          "n_objects", "runtime_s")}, indent=1))
    if "determinism" in out.get("checks", {}):
        print("determinism:", out["checks"]["determinism"])
    print("wrote", jpath, "and", npath)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
