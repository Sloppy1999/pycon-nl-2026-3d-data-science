"""Every render in the deck, from the pipeline's own output, with ONE fixed camera.

    cd talk && uv run python pipeline/render.py            # all frames, labels.json, render_spec.json
    uv run python pipeline/render.py --only f1 f5          # a subset (no labels.json / render_spec.json)

Reads:  results/labels_crop.npz, results/pipeline.json (pipeline/run.py), data/<crop>.laz (full-density points),
        deck/content.yaml (meta.render_palette: every colour the renders show)
Writes: renders/f1_load.png ... f6_final.png, hook_split.png, closeup.png, plane_sheet.png (CONTRACTS.md),
        renders/*_gray.png (grayscale QA), renders/labels.json (anchor pixel per class), renders/render_spec.json

Conventions:
- Crop-local metres, origin = LAS header.mins of the crop (as in the slide 8 code). One camera for every frame;
  the camera is set once per plotter and never reset (no reset_camera, no view_isometric). Every render reads
  the pose back and checks it is unchanged.
- Frames are 1588 x 1792 px; hook_split is 4190 x 1792 px with the same camera and the same vertical view angle,
  so its centre 1588 columns are the frame (checked pixel by pixel, written to render_spec.json).
- Points are unlit squares (no spheres, no eye-dome lighting), anti-aliasing off: every pixel of a point has
  exactly its class colour, which the grayscale check and the label anchors rely on.
- Labels are never burnt into the PNGs: labels.json gives one anchor pixel per class and the deck draws the chips.
- Colours: PyCon NL 2026 palette, read only from deck/content.yaml meta.render_palette (PALETTE_KEYS, no built-in
  fallback: a missing key stops the run). The overlays that are not a class (plane sheet tint, distance ticks and
  their keyline, the hook's divider) take palette entries too (overlay_colours). The only colour literals in this
  file are the mask colours of the ID and compositing passes, which never reach a PNG.
- Point sizes: 3 px on every frame, raw and voxel alike. From this camera a 0.5 m voxel is only a few pixels
  apart on screen (measured per frame band and written to render_spec.json), so bigger voxel squares overlap and
  the voxel frames would look smoother than the raw frame instead of sparser. With the raw frame's own 3 px the
  only change from f1 to f2 is the number of points, and the gaps of the voxel grid show (coverage of the crop's
  footprint is measured and written too). f6 paints the labels back onto every point and is dense again.
- The one street furniture object (9 points, 8 voxels) is its own actor at PS_FURNITURE px on f5, f6 and the
  hook: a deliberate visibility choice, recorded in render_spec.json; at 3 px it is a speck on the slides.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
import time
from importlib.metadata import version
from pathlib import Path

import numpy as np
import pyvista as pv
import yaml
from PIL import Image
from scipy import ndimage
from scipy.spatial import KDTree
from vtkmodules.vtkCommonCore import vtkVersion
from vtkmodules.vtkRenderingCore import vtkCoordinate

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline import steps as S  # noqa: E402

NPZ = ROOT / "results" / "labels_crop.npz"
PIPELINE_JSON = ROOT / "results" / "pipeline.json"
CONTENT = ROOT / "deck" / "content.yaml"
OUT = ROOT / "renders"

# ----------------------------------------------------------------------------------------------- spec
H, W_FRAME, W_WIDE = 1792, 1588, 4190  # (W_WIDE - W_FRAME) is even, so the frame is the exact centre crop
assert (W_WIDE - W_FRAME) % 2 == 0

# Camera (2026-10-11, new crop: the Jaarbeurs hall and its surroundings): 15 deg west of south looking north-north-east
# at 75 deg elevation, 470 m from the focal point (the crop's centre), so the whole 200 m crop sits in the portrait frame (about
# 27 deg wide) and in the centre of the wide render. A flatter view hid two of the three street furniture objects
# behind the 40 m hall (tested at 60 to 80 deg elevation and several bearings: at 60 deg from the south only one of the
# three was visible; a steeper one made the distance ticks of slide 18 too short to draw, a more westerly bearing turned the crop
# and cut its corners off); this pose shows all three and about 98 % of the voxels inside the frame. View up and the 30 deg view
# angle are kept (VTK's default angle, so the slide 13 code that sets only camera_position renders the same view).
# The coverage numbers (share of every class inside the frame, empty columns of the wide render) are computed below
# and written to render_spec.json (camera.coverage).
# The first example street (until 2026-10-11) used position [123, -106, 398], focal point [99, 120, 4].
CAMERA = dict(position=[73.5, -17.5, 462.0], focal_point=[105.0, 100.0, 8.0], view_up=[0.0, 0.0, 1.0],
              view_angle=30.0)
REVIEWED_CAMERA = CAMERA  # one pose only since 2026-10-11 (kept so render_spec.json keeps its shape)
CLOSEUP_VIEW_ANGLE = 7.5
# The close-up (slide 5) keeps the camera position and aims the narrow view at the trees and street furniture north-west
# of the hall (a flat roof would show only a uniform field of points); focal point in crop-local metres.
CLOSEUP_CAMERA = dict(CAMERA, focal_point=[70.0, 155.0, 5.0])

HEIGHT_CLIM = (-1.0, 30.0)  # metres above the median z of the pipeline's own ground voxels (never AHN's classes)
PS_RAW, PS_VOXEL = 3, 3  # same squares on raw and voxel frames: f2 differs from f1 by point count only
PS_FURNITURE = 24  # street furniture actor only (f5, f6, hook): deliberate visibility choice, see render_spec
SPACING_BANDS_PX = 300  # row bands for the measured on-screen voxel spacing and footprint coverage
# Jaarbeurs: the hall building (BAG pand 0344100000077882, Jaarbeursplein 6, built 1970) lies inside the crop; its
# footprint centre (PDOK BAG WFS, checked 2026-10-11, footprint bbox RD 135747.7, 455512.5 to 135905.8, 455654.0)
# is where the deck's "Jaarbeurs hall" arrow points, at the height of the pipeline's own building voxels there.
HALL_CENTRE_RD = (135826.7, 455583.3)
HALL_BBOX_RD = (135747.7, 455512.5, 135905.8, 455654.0)
CLUSTER_SEED = 20261015
SHEET_OPACITY, SHEET_EDGE_OPACITY = 0.30, 0.60
TICK_PX, TICK_FOOT_PX, TICK_TOP_PX, TICK_MIN_PX = 12, 24, 20, 24  # thick enough to read from the back of the room (slide 15)
TICK_KEYLINE_PX = 4  # background-coloured rim around every tick, so a light tick still reads on light points
DIVIDER_PX = 4

CLASSES = ("ground", "buildings", "vegetation", "street_furniture")  # the four labelled classes
EXCLUDED_ANCHOR = (255, 0, 255)  # ID colour for vegetation clusters that must not carry the vegetation label
# Mask colours of the plane sheet's compositing passes: they only select pixels and never reach a PNG.
MASK_BG, MASK_SHEET, MASK_EDGE, MASK_TICK = "#000000", "#FFFFFF", "#FF0000", "#0000FF"
GRAY_THRESHOLD = 40  # smallest gray-level step accepted between two of the four classes and the background

PALETTE_SOURCE = "deck/content.yaml meta.render_palette"
PALETTE_KEYS = dict(background=str, ground=str, buildings=str, vegetation=str, street_furniture=str, unlabelled=str,
                    height_ramp=list, clusters=list, noise=str)

pv.OFF_SCREEN = True


def hex_rgb(h: str) -> np.ndarray:
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], dtype=np.uint8)


def load_palette() -> dict:
    """Every colour of the renders, from deck/content.yaml meta.render_palette. No fallback: a missing or
    malformed entry stops the run, so a render can never silently fall back to another palette."""
    meta = yaml.safe_load(CONTENT.read_text(encoding="utf-8"))["meta"]["render_palette"]
    pal = {}
    for key, kind in PALETTE_KEYS.items():
        v = meta.get(key)
        vals = v if kind is list else [v]
        is_hex = (lambda c: isinstance(c, str) and len(c) == 7 and c[0] == "#"
                  and all(ch in "0123456789abcdefABCDEF" for ch in c[1:]))
        if not isinstance(v, kind) or not vals or not all(is_hex(c) for c in vals):
            raise SystemExit(f"{PALETTE_SOURCE}.{key}: expected {'a list of ' if kind is list else ''}#RRGGBB, "
                             f"got {v!r}")
        pal[key] = [c.upper() for c in v] if kind is list else v.upper()
    if len(pal["height_ramp"]) < 2:
        raise SystemExit(f"{PALETTE_SOURCE}.height_ramp: needs at least two stops")
    return pal


def overlay_colours(pal: dict) -> dict:
    """The colours that are not a class, chosen from the palette entries (no colour literal of their own):
    plane sheet tint and distance ticks = the top stop of the height ramp (white), the ticks' keyline = the
    background (navy), the hook's divider = the top stop of the height ramp."""
    top = pal["height_ramp"][-1]
    return dict(sheet=top, tick=top, tick_keyline=pal["background"], divider=top,
                rule="sheet, tick, divider = render_palette.height_ramp[-1]; tick_keyline = render_palette.background")


PAL = load_palette()
OVERLAY = overlay_colours(PAL)
BACKGROUND = PAL["background"]


# ----------------------------------------------------------------------------------------------- data
class Data:
    def __init__(self):
        z = np.load(NPZ)
        self.npz_sha256 = hashlib.sha256(NPZ.read_bytes()).hexdigest()
        self.class_names = [str(s) for s in z["class_names"]]
        assert tuple(self.class_names) == S.CLASS_NAMES, self.class_names
        crop = ROOT / str(z["crop_file"])
        _, self.xyz, origin = S.load(crop)  # full density, local metres
        self.crop_file = str(z["crop_file"])
        assert np.allclose(origin, z["origin"]), "origin in labels_crop.npz differs from the crop's header.mins"
        self.origin = origin
        self.V = z["voxel_xyz"]
        self.v_class = z["voxel_class"]
        self.v_cluster = z["voxel_cluster"]
        self.v_ground = z["voxel_ground"]
        self.v_hag = z["voxel_hag"]
        self.p_class = z["point_class"]
        self.p_voxel = z["point_voxel"]
        assert len(self.p_class) == len(self.xyz), "point_class does not match the crop"
        self.cluster_class = z["cluster_class"]
        self.sf_clusters = z["street_furniture_clusters"]
        self.tile_ij, self.tile_bounds, self.tile_plane = z["tile_ij"], z["tile_bounds"], z["tile_plane"]
        self.tile_rejected = z["tile_rejected"]
        self.tile_size = float(z["tile_size"])
        self.ground_z_ref = float(np.median(self.V[self.v_ground, 2]))  # pipeline ground, local metres
        self.pipeline = json.loads(PIPELINE_JSON.read_text()) if PIPELINE_JSON.exists() else {}
        n_cl = len(self.cluster_class)
        on = self.v_cluster >= 0
        k = self.v_cluster[on]
        top = np.full(n_cl, -np.inf)
        np.maximum.at(top, k, self.v_hag[on])
        bottom = np.full(n_cl, np.inf)
        np.minimum.at(bottom, k, self.v_hag[on])
        self.cluster_vext = top - bottom  # vertical extent of each cluster (m)
        self.cluster_top_hag = top


def ramp_colours(z_local: np.ndarray, z_ref: float, stops: list[str], clim=HEIGHT_CLIM) -> np.ndarray:
    """Linear RGB ramp over the stops, fixed limits in metres above z_ref (identical on every frame)."""
    t = np.clip((z_local - z_ref - clim[0]) / (clim[1] - clim[0]), 0.0, 1.0)
    cols = np.stack([hex_rgb(c) for c in stops]).astype(float)
    pos = np.linspace(0.0, 1.0, len(stops))
    return np.stack([np.interp(t, pos, cols[:, i]) for i in range(3)], axis=1).round().astype(np.uint8)


# ----------------------------------------------------------------------------------------------- rendering
def new_plotter(width: int, background: str) -> pv.Plotter:
    pl = pv.Plotter(off_screen=True, window_size=[width, H])
    pl.disable_anti_aliasing()
    pl.set_background(background)
    return pl


def set_camera(pl: pv.Plotter, view_angle: float, cam: dict | None = None) -> None:
    cam = cam or CAMERA
    pl.camera_position = [tuple(cam["position"]), tuple(cam["focal_point"]), tuple(cam["view_up"])]
    pl.camera.view_angle = view_angle


def camera_unchanged(pl: pv.Plotter, view_angle: float, cam: dict | None = None) -> bool:
    c, cam = pl.camera, cam or CAMERA
    return bool(np.allclose(c.position, cam["position"]) and np.allclose(c.focal_point, cam["focal_point"])
                and np.allclose(c.up, cam["view_up"]) and np.isclose(c.view_angle, view_angle))


def render(layers, width=W_FRAME, view_angle=CAMERA["view_angle"], background=BACKGROUND, extra=None,
           keep=False, cam=None):
    """layers: [(points, rgb uint8 (N, 3), point_size_px), ...] drawn in order. Returns (image, plotter or None,
    camera_ok)."""
    pl = new_plotter(width, background)
    for pts, rgb, ps in layers:
        if len(pts) == 0:
            continue
        pl.add_points(np.ascontiguousarray(pts, dtype=np.float64), scalars=rgb, rgb=True, point_size=ps,
                      render_points_as_spheres=False, lighting=False)
    if extra is not None:
        extra(pl)
    set_camera(pl, view_angle, cam)
    img = pl.screenshot(None, return_img=True)
    ok = camera_unchanged(pl, view_angle, cam)
    if not keep:
        pl.close()
        pl = None
    return img[..., :3].copy(), pl, ok


def probe(width: int, cam: dict, view_angle: float = 30.0) -> pv.Plotter:
    """A plotter with the given camera and nothing drawn, used only to project points."""
    pl = new_plotter(width, BACKGROUND)
    pl.add_points(np.zeros((1, 3)), color="white")
    set_camera(pl, view_angle, cam)
    pl.render()
    return pl


def world_to_pixel(pl: pv.Plotter, P: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Project world points with the renderer's own camera matrices. Returns (xy, depth): xy in image pixels
    (x right, y down, continuous; pixel index = floor), depth = distance along the view direction."""
    ren = pl.renderer
    w, h = pl.window_size
    cam = ren.GetActiveCamera()
    m = cam.GetCompositeProjectionTransformMatrix(ren.GetTiledAspectRatio(), -1, 1)
    M = np.array([[m.GetElement(i, j) for j in range(4)] for i in range(4)])
    Ph = np.c_[P, np.ones(len(P))] @ M.T
    ndc = Ph[:, :3] / Ph[:, 3:4]
    xy = np.c_[(ndc[:, 0] + 1) / 2 * w, h - (ndc[:, 1] + 1) / 2 * h]
    view = np.asarray(cam.GetDirectionOfProjection())
    depth = (P - np.asarray(cam.GetPosition())) @ view
    return xy, depth


def vtk_display(pl: pv.Plotter, p) -> list[float]:
    """Cross-check of world_to_pixel with vtkCoordinate (display coordinates have y up)."""
    c = vtkCoordinate()
    c.SetCoordinateSystemToWorld()
    c.SetValue(*map(float, p))
    x, y = c.GetComputedDoubleDisplayValue(pl.renderer)
    return [x, pl.window_size[1] - y]


def save_png(img: np.ndarray, name: str) -> Path:
    p = OUT / name
    Image.fromarray(img).save(p, optimize=True)
    return p


# ----------------------------------------------------------------------------------------------- camera evidence
def pose_numbers(cam: dict) -> dict:
    dv = np.asarray(cam["position"], float) - np.asarray(cam["focal_point"], float)
    dist = float(np.linalg.norm(dv))
    return dict(distance_m=round(dist, 1),
                bearing_of_view_deg=round(float(np.degrees(np.arctan2(-dv[0], -dv[1]))), 1),
                elevation_deg=round(float(np.degrees(np.arcsin(dv[2] / dist))), 1))


def coverage(d: Data, cam: dict) -> dict:
    """Share of each class's voxels that project inside the portrait frame (20 px margin), where the street
    furniture lands, and how the crop sits in the wide render (empty columns left and right of the crop)."""
    pl = probe(W_FRAME, cam)
    xy, _ = world_to_pixel(pl, d.V)
    pl.close()
    m = 20
    inside = (xy[:, 0] > m) & (xy[:, 0] < W_FRAME - m) & (xy[:, 1] > m) & (xy[:, 1] < H - m)
    out = {n: round(float(inside[d.v_class == i].mean()), 3) for i, n in enumerate(S.CLASS_NAMES)
           if np.any(d.v_class == i)}
    hx0, hy0, hx1, hy1 = HALL_BBOX_RD
    hall = ((d.v_class == S.BUILDINGS) & (d.V[:, 0] + d.origin[0] >= hx0) & (d.V[:, 0] + d.origin[0] <= hx1)
            & (d.V[:, 1] + d.origin[1] >= hy0) & (d.V[:, 1] + d.origin[1] <= hy1))
    out["jaarbeurs_hall"] = round(float(inside[hall].mean()), 3)
    sf = d.V[d.v_class == S.STREET_FURNITURE]
    sf_xy = xy[d.v_class == S.STREET_FURNITURE].mean(axis=0) if len(sf) else None
    plw = probe(W_WIDE, cam)
    wxy, _ = world_to_pixel(plw, d.V)
    plw.close()
    lo, hi = np.percentile(wxy[:, 0], [0.1, 99.9])
    return dict(share_of_voxels_inside_frame=out,
                street_furniture_px_frame=[round(float(v)) for v in sf_xy] if sf_xy is not None else None,
                street_furniture_px_wide=(round(float(sf_xy[0] + (W_WIDE - W_FRAME) / 2)) if sf_xy is not None
                                          else None),
                wide_empty_columns_left_right=[round(float(lo)), round(float(W_WIDE - hi))],
                rule="voxels projected with the renderer's camera matrices; inside = more than 20 px from every "
                     "frame edge; wide empty columns = columns left of the 0.1st and right of the 99.9th "
                     "percentile of the projected voxel x")


def voxel_spacing(d: Data) -> dict:
    """On-screen distance from each ground voxel to its nearest ground voxel neighbour (portrait frame), median
    per band of rows: how far apart the voxel grid is drawn, which bounds the voxel point size that still leaves
    gaps."""
    pl = probe(W_FRAME, CAMERA)
    xy, _ = world_to_pixel(pl, d.V[d.v_ground])
    pl.close()
    inside = (xy[:, 0] >= 0) & (xy[:, 0] < W_FRAME) & (xy[:, 1] >= 0) & (xy[:, 1] < H)
    xy = xy[inside]
    nn = KDTree(xy).query(xy, k=2)[0][:, 1]
    bands = {}
    for lo in range(0, H, SPACING_BANDS_PX):
        m = (xy[:, 1] >= lo) & (xy[:, 1] < lo + SPACING_BANDS_PX)
        if m.sum() >= 1000:
            bands[f"rows_{lo}_{min(lo + SPACING_BANDS_PX, H)}"] = round(float(np.median(nn[m])), 2)
    return dict(median_nn_px_by_rows=bands, median_nn_px_all=round(float(np.median(nn)), 2),
                rule="ground voxels projected into the portrait frame; distance to the nearest other ground voxel "
                     "on screen; median per band of rows (bands with at least 1000 voxels)")


def footprint(img_raw: np.ndarray, bg: np.ndarray) -> np.ndarray:
    """The crop's silhouette in the raw frame (non-background, small holes closed): the area the coverage of
    the other frames is measured in."""
    m = ndimage.binary_closing(~np.all(img_raw == bg, axis=-1), iterations=3)
    return ndimage.binary_fill_holes(m)


def footprint_coverage(img: np.ndarray, foot: np.ndarray, bg: np.ndarray) -> dict:
    nb = ~np.all(img == bg, axis=-1)
    bands = {}
    for lo in range(0, H, SPACING_BANDS_PX):
        f = foot[lo:lo + SPACING_BANDS_PX]
        if f.sum() >= 10000:
            bands[f"rows_{lo}_{min(lo + SPACING_BANDS_PX, H)}"] = round(float(nb[lo:lo + SPACING_BANDS_PX][f].mean()),
                                                                         3)
    return dict(share_of_footprint_drawn=round(float(nb[foot].mean()), 3), by_rows=bands)


def jaarbeurs_hall(d: Data, pl: pv.Plotter, img: np.ndarray, x_offset: float = 0.0) -> dict:
    """Where the deck's arrow points: the centre of the Jaarbeurs hall's footprint (BAG), at the median height of the
    pipeline's building voxels within 15 m of it (the roof), projected with the renderer's camera. Returns the pixel
    (floor) plus the evidence: the roof height used, the number of voxels it comes from, and that the pixel shows
    a point (not the background)."""
    cx, cy = HALL_CENTRE_RD[0] - d.origin[0], HALL_CENTRE_RD[1] - d.origin[1]
    b = d.V[d.v_class == S.BUILDINGS]
    near = np.hypot(b[:, 0] - cx, b[:, 1] - cy) <= 15.0
    assert near.sum() >= 50, f"only {near.sum()} building voxels near the hall centre"
    ez = float(np.median(b[near, 2]))
    P = np.array([[cx, cy, ez]])
    xy, _ = world_to_pixel(pl, P)
    vtk_xy = vtk_display(pl, P[0])
    px = [int(np.floor(xy[0, 0] + x_offset)), int(np.floor(xy[0, 1]))]
    h, w = img.shape[:2]
    shows_crop = bool(0 <= px[0] < w and 0 <= px[1] < h and not np.all(img[px[1], px[0]] == hex_rgb(BACKGROUND)))
    return dict(px=px, point_local=[round(cx, 3), round(cy, 3), round(ez, 3)],
                roof_voxels_within_15_m=int(near.sum()),
                matrix_px=[round(float(xy[0, 0] + x_offset), 2), round(float(xy[0, 1]), 2)],
                vtkCoordinate_px=[round(vtk_xy[0] + x_offset, 2), round(vtk_xy[1], 2)],
                pixel_shows_crop=shows_crop,
                rule="centre of the hall's BAG footprint, at the median z of the pipeline's building voxels within "
                     "15 m of it; projected with the renderer's camera matrices (cross-checked with vtkCoordinate); "
                     "pixel = floor")


def anchors_on_class(img: np.ndarray, anchors: dict, col: Colours) -> dict:
    """Re-check on the image itself (not the ID pass): the anchor pixel has its class colour, and the share of
    that class in the 9 x 9 pixels around it."""
    out = {}
    for n in CLASSES:
        a = anchors.get(n)
        if not a:
            out[n] = None
            continue
        x, y = a["px"]
        c = col.cls[S.CLASS_NAMES.index(n)]
        win = img[max(y - 4, 0):y + 5, max(x - 4, 0):x + 5]
        out[n] = dict(pixel_is_class=bool(np.all(img[y, x] == c)),
                      share_of_class_9x9=round(float(np.all(win == c, axis=-1).mean()), 2),
                      snapped_to_point=a.get("point_local") is not None)
    out["all_on_class"] = all(v["pixel_is_class"] and v["snapped_to_point"] for v in out.values() if v)
    return out


# ----------------------------------------------------------------------------------------------- colours
class Colours:
    def __init__(self, pal: dict):
        self.pal = pal
        self.cls = np.stack([hex_rgb(pal[n]) for n in S.CLASS_NAMES])  # index = class code
        self.bg = hex_rgb(pal["background"])

    def classes(self, codes):
        return self.cls[np.asarray(codes)]


def cluster_colours(d: Data, pal: dict) -> tuple[np.ndarray, dict]:
    """Frame 4: clusters cycle the palette's cluster colours (fixed seed), noise dimmed, ground in the ground
    colour."""
    n_cl = len(d.cluster_class)
    rng = np.random.default_rng(CLUSTER_SEED)
    cyc = np.stack([hex_rgb(c) for c in pal["clusters"]])
    per_cluster = cyc[rng.permutation(n_cl) % len(cyc)]
    rgb = np.empty((len(d.V), 3), np.uint8)
    on = d.v_cluster >= 0
    rgb[on] = per_cluster[d.v_cluster[on]]
    rgb[d.v_cluster == S.NOISE] = hex_rgb(pal["noise"])
    near = (d.v_cluster == S.NOT_CLUSTERED) & ~d.v_ground  # not given to DBSCAN (at most 0.3 m above ground)
    rgb[near] = hex_rgb(pal["noise"])
    rgb[d.v_ground] = hex_rgb(pal["ground"])
    info = dict(clusters=int(n_cl), noise_voxels=int(np.count_nonzero(d.v_cluster == S.NOISE)),
                near_ground_not_clustered_voxels=int(np.count_nonzero(near)),
                rule=f"colour = cycle[permutation(n_clusters, seed) % {len(cyc)}]; DBSCAN noise and the "
                     "near-ground voxels that never went to DBSCAN in the noise colour; ground in the ground colour")
    return rgb, info


# ----------------------------------------------------------------------------------------------- anchors
def anchor_excluded_vegetation(d: Data) -> tuple[np.ndarray, dict]:
    """Vegetation clusters that must not carry the 'Vegetation' chip: the pipeline's known errors and clusters
    that are not tree-shaped (vertical extent below 3 m, e.g. the horizontal stripes on tall facades)."""
    known = [r["cluster"] for r in d.pipeline.get("known_errors", {})
             .get("vegetation_clusters_mostly_ahn_ground_or_building", [])]
    veg = d.cluster_class == S.VEGETATION
    flat = veg & (d.cluster_vext < 3.0)
    bad = np.zeros(len(d.cluster_class), bool)
    bad[known] = True
    bad |= flat
    return bad, dict(known_error_clusters=known, flat_clusters=int(np.count_nonzero(flat)))


def id_colours(codes: np.ndarray, cluster_of: np.ndarray, bad_cluster: np.ndarray, col: Colours) -> np.ndarray:
    rgb = col.classes(codes).copy()
    ex = (codes == S.VEGETATION) & (cluster_of >= 0) & bad_cluster[np.maximum(cluster_of, 0)]
    rgb[ex] = EXCLUDED_ANCHOR
    return rgb


def class_masks(img: np.ndarray, col: Colours) -> dict[str, np.ndarray]:
    return {n: np.all(img == col.cls[i], axis=-1) for i, n in enumerate(S.CLASS_NAMES)}


def pick_anchors(id_img: np.ndarray, pl: pv.Plotter, pts: np.ndarray, codes: np.ndarray, usable: np.ndarray,
                 col: Colours, x_range: tuple[int, int], visible_x: tuple[int, int], margin_y: int = 200,
                 win: int = 61, spacing: int = 300, prefer: dict | None = None, prefer_radius: int = 40) -> dict:
    """One anchor per class: a pixel deep inside a visible patch of that class (densest window, few pixels of
    other classes), inside x_range and away from the top and bottom edges, at least ``spacing`` px from the
    anchors already placed. Street furniture (a few pixels; with several objects the topmost visible patch) only needs to be inside ``visible_x`` (the part of
    the image that shows labels); if it is not visible there, it gets no anchor. Each anchor is the projected
    pixel of a real 3D point of that class that the renderer shows there (the front-most point projecting within
    3 px of the best pixel). With ``prefer`` ({class: [x, y]}, e.g. the f6 anchors for f5, so the chips stay put
    across the Morph from slide 12 to 13) a class's best pixel is searched within ``prefer_radius`` px of that
    pixel first, by the same score; only if nothing of the class is visible there does the normal search run."""
    h, w = id_img.shape[:2]
    masks = class_masks(id_img, col)
    bg = np.all(id_img == col.bg, axis=-1)
    region = np.zeros((h, w), bool)
    region[margin_y:h - margin_y, x_range[0]:x_range[1]] = True
    vis = np.zeros((h, w), bool)
    vis[:, visible_x[0]:visible_x[1]] = True
    xy, depth = world_to_pixel(pl, pts)
    out, placed = {}, []
    yy, xx = np.mgrid[0:h, 0:w]
    cx, cy = (x_range[0] + x_range[1]) / 2, h / 2
    for name in ("street_furniture", "buildings", "vegetation", "ground"):
        code = S.CLASS_NAMES.index(name)
        m = masks[name] & vis
        if not m.any():
            out[name] = None
            continue
        if name == "street_furniture":
            # few pixels, several objects: the topmost visible patch (its chip then sits in the empty space above
            # the scene, not on the other objects); in it the pixel nearest to the patch centroid
            patches, n_patches = ndimage.label(m)
            tops = [(np.nonzero(patches == j)[0].mean(), j) for j in range(1, n_patches + 1)]
            j = min(tops)[1]
            ys, xs = np.nonzero(patches == j)
            k = np.argmin((xs - xs.mean()) ** 2 + (ys - ys.mean()) ** 2)
            best = (int(xs[k]), int(ys[k]))
            score_best = float(ndimage.uniform_filter(m.astype(float), 15)[best[1], best[0]])
        else:
            dens = ndimage.uniform_filter(m.astype(float), win)
            other = ndimage.uniform_filter((~masks[name] & ~bg).astype(float), win)
            near_pref = None
            if prefer and prefer.get(name):
                qx, qy = prefer[name]
                near_pref = m & ((xx - qx) ** 2 + (yy - qy) ** 2 <= prefer_radius ** 2)
            if near_pref is not None and near_pref.any():
                score = dens - 0.5 * other - 0.002 * np.hypot(xx - qx, yy - qy)
                score[~near_pref] = -np.inf
            else:
                allowed = m & region
                for px, py in placed:
                    allowed &= (xx - px) ** 2 + (yy - py) ** 2 >= spacing ** 2
                score = dens - 0.5 * other - 0.10 * (np.abs(xx - cx) / w + np.abs(yy - cy) / h)
                score[~allowed] = -np.inf
            if not np.isfinite(score).any():
                out[name] = None
                continue
            iy, ix = np.unravel_index(np.argmax(score), score.shape)
            best, score_best = (int(ix), int(iy)), float(dens[iy, ix])
        # snap to a real point of this class that projects onto a pixel showing this class
        sel = np.flatnonzero((codes == code) & usable)
        dxy = xy[sel] - (np.array(best) + 0.5)
        near = sel[(np.abs(dxy) <= 3).all(axis=1)]
        chosen = None
        for i in near[np.argsort(depth[near])]:
            ix, iy = int(np.floor(xy[i, 0])), int(np.floor(xy[i, 1]))
            if 0 <= ix < w and 0 <= iy < h and m[iy, ix]:
                chosen = i
                break
        if chosen is None:
            out[name] = dict(px=[best[0], best[1]], point_local=None, density=round(score_best, 3),
                             note="no single point snapped; pixel of the class patch")
        else:
            ix, iy = int(np.floor(xy[chosen, 0])), int(np.floor(xy[chosen, 1]))
            vtk_xy = vtk_display(pl, pts[chosen])
            out[name] = dict(px=[ix, iy], point_local=[round(float(v), 3) for v in pts[chosen]],
                             density=round(score_best, 3),
                             vtkCoordinate_px=[round(v, 2) for v in vtk_xy],
                             matrix_px=[round(float(v), 2) for v in xy[chosen]])
        placed.append(tuple(out[name]["px"]))
    out["visible_pixels"] = {n: int((masks[n] & vis).sum()) for n in CLASSES}
    return out


# ----------------------------------------------------------------------------------------------- QA
def grayscale_qa(img: np.ndarray, name: str, col: Colours, x_from: int = 0, skip_cols=()) -> dict:
    """Write <name>_gray.png (PIL 'L', ITU-R 601-2 luma) and measure the gray level of every class colour as it
    appears in the image (pixels of exactly that colour, from column x_from on, minus skip_cols, e.g. the hook's
    white divider, which has the street furniture colour)."""
    g = np.asarray(Image.fromarray(img).convert("L"))
    save_png(g, name.replace(".png", "_gray.png"))
    use = np.zeros(img.shape[:2], bool)
    use[:, x_from:] = True
    for c in skip_cols:
        use[:, c] = False
    levels = {}
    for i, n in enumerate(S.CLASS_NAMES):
        m = np.all(img == col.cls[i], axis=-1) & use
        levels[n] = dict(pixels=int(m.sum()), gray=(int(np.median(g[m])) if m.any() else None))
    mb = np.all(img == col.bg, axis=-1) & use
    levels["background"] = dict(pixels=int(mb.sum()), gray=int(np.median(g[mb])) if mb.any() else None)
    keys = list(CLASSES) + ["background"]
    vals = {k: levels[k]["gray"] for k in keys if levels[k]["gray"] is not None}
    pairs = {f"{a}-{b}": abs(vals[a] - vals[b]) for i, a in enumerate(keys) for b in keys[i + 1:]
             if a in vals and b in vals}
    worst = min(pairs, key=pairs.get) if pairs else None
    ug = levels["unlabelled"]["gray"]
    return dict(levels=levels, pair_differences=pairs, smallest_pair=worst,
                smallest_difference=pairs.get(worst), threshold=GRAY_THRESHOLD,
                passes=bool(pairs) and min(pairs.values()) >= GRAY_THRESHOLD
                and all(levels[k]["pixels"] > 0 for k in CLASSES),
                columns_skipped=list(map(int, skip_cols)),
                unlabelled_vs_ground=(abs(ug - levels["ground"]["gray"]) if ug is not None
                                      and levels["ground"]["gray"] is not None else None),
                note="unlabelled (not one of the four classes) is meant to sit close to ground and recede")


def crop_identity(wide: np.ndarray, frame: np.ndarray) -> dict:
    x0 = (wide.shape[1] - frame.shape[1]) // 2
    centre = wide[:, x0:x0 + frame.shape[1]]
    diff = np.abs(centre.astype(int) - frame.astype(int)).max(axis=-1)
    ys, xs = np.nonzero(diff)
    edge = int(np.count_nonzero((xs < 6) | (xs >= frame.shape[1] - 6) | (ys < 6) | (ys >= frame.shape[0] - 6)))
    return dict(x0=int(x0), pixels=int(diff.size), differing=int(len(ys)),
                differing_share=float(len(ys) / diff.size), differing_within_6px_of_edge=edge,
                identical=bool(not diff.any()),
                reading="the few differing pixels are single 3 px point squares that land one pixel apart because "
                        "the two viewports round sub-pixel positions differently; same camera, same view")


def sf_visibility(img: np.ndarray, col: Colours, x_from: int = 0, skip_cols=()) -> dict:
    m = np.all(img == col.cls[S.STREET_FURNITURE], axis=-1)
    m[:, :x_from] = False
    for c in skip_cols:
        m[:, c] = False
    if not m.any():
        return dict(pixels=0)
    ys, xs = np.nonzero(m)
    # one box per connected patch (one per visible object), topmost first: the chip leader and the rings of slide 17
    patches, n = ndimage.label(m)
    boxes = []
    for j in range(1, n + 1):
        py, px = np.nonzero(patches == j)
        boxes.append(dict(bbox_px=[int(px.min()), int(py.min()), int(px.max()), int(py.max())], pixels=int(len(py))))
    boxes.sort(key=lambda b: (b["bbox_px"][1], b["bbox_px"][0]))
    return dict(pixels=int(m.sum()), bbox_px=[int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())],
                patches=boxes)


# ----------------------------------------------------------------------------------------------- plane sheet
def tile_index(d: Data, xy: np.ndarray) -> np.ndarray:
    ij = np.floor(xy / d.tile_size).astype(int)
    lut = {tuple(t): i for i, t in enumerate(d.tile_ij)}
    return np.array([lut.get(tuple(t), -1) for t in ij])


def plane_z(plane, x, y):
    a, b, c, dd = plane
    return -(a * x + b * y + dd) / c


def choose_ticks(d: Data, pl_probe: pv.Plotter) -> list[dict]:
    """A few objects for the distance ticks, chosen by rules (not by hand): the street furniture object, the
    three tallest free-standing tree-shaped vegetation clusters in the central part of the frame (at least
    150 px apart), the tallest building's roof corner nearest the camera, and one car-sized unlabelled
    cluster nearest the frame centre. Each tick runs from the object's highest voxel straight down to the
    plane of the tile it stands in. Ticks that project shorter than TICK_MIN_PX are listed but not drawn (from
    this steep camera a vertical metre is only a few pixels, so a short tick would read as a dot)."""
    V, cl, cc = d.V, d.v_cluster, d.cluster_class
    n_cl = len(cc)
    on = cl >= 0
    top_idx = np.full(n_cl, -1)
    order = np.argsort(V[:, 2])
    top_idx[cl[order][on[order]]] = order[on[order]]  # last write = highest voxel of each cluster
    xy, _ = world_to_pixel(pl_probe, V[np.maximum(top_idx, 0)])
    w = pl_probe.window_size[0]
    central = (xy[:, 0] > 0.18 * w) & (xy[:, 0] < 0.82 * w) & (xy[:, 1] > 0.15 * H) & (xy[:, 1] < 0.85 * H)
    bld = V[d.v_class == S.BUILDINGS, :2]
    d_bld, _ = KDTree(bld).query(V[np.maximum(top_idx, 0), :2])
    picks = []
    for k in d.sf_clusters:
        picks.append(("street furniture", int(k)))
    trees = np.flatnonzero((cc == S.VEGETATION) & (d.cluster_vext >= 4) & central & (d_bld > 6) & (top_idx >= 0))
    trees = trees[np.argsort(-d.cluster_top_hag[trees])]
    chosen_xy = []
    for k in trees:
        if all(np.hypot(*(xy[k] - q)) >= 150 for q in chosen_xy):
            picks.append(("tree", int(k)))
            chosen_xy.append(xy[k])
        if len(chosen_xy) == 3:
            break
    bk = np.flatnonzero((cc == S.BUILDINGS) & central & (top_idx >= 0))
    if len(bk):
        k = int(bk[np.argmax(d.cluster_top_hag[bk])])
        sel = np.flatnonzero((cl == k) & (V[:, 2] >= V[cl == k, 2].max() - 1.0))
        cam = np.asarray(CAMERA["position"][:2])
        i = sel[np.argmin(np.hypot(*(V[sel, :2] - cam).T))]
        picks.append(("building", (k, int(i))))
    lo = np.full((n_cl, 2), np.inf)
    hi = np.full((n_cl, 2), -np.inf)
    np.minimum.at(lo, cl[on], V[on, :2])
    np.maximum.at(hi, cl[on], V[on, :2])
    width = (hi - lo).max(axis=1)
    cars = np.flatnonzero((cc == S.UNLABELLED) & (d.cluster_top_hag > 1.2) & (d.cluster_top_hag < 2.2)
                          & (width > 3.5) & (width < 6.0) & central & (top_idx >= 0))
    if len(cars):
        k = int(cars[np.argmin(np.hypot(xy[cars, 0] - w / 2, xy[cars, 1] - H / 2))])
        picks.append(("car-sized unlabelled cluster", k))
    ticks = []
    for kind, ref in picks:
        if isinstance(ref, tuple):
            k, i = ref
        else:
            k, i = ref, int(top_idx[ref])
        p = V[i]
        t = int(tile_index(d, p[None, :2])[0])
        if t < 0 or d.tile_rejected[t]:
            continue
        pz = plane_z(d.tile_plane[t], p[0], p[1])
        a, b, c, dd = d.tile_plane[t]
        ends, _ = world_to_pixel(pl_probe, np.array([p, [p[0], p[1], pz]]))
        length_px = float(np.hypot(*(ends[0] - ends[1])))
        ticks.append(dict(kind=kind, cluster=int(k), top_local=[round(float(v), 3) for v in p],
                          tile_ij=[int(v) for v in d.tile_ij[t]], plane_z=round(float(pz), 3),
                          vertical_m=round(float(p[2] - pz), 2),
                          perpendicular_m=round(float(abs(a * p[0] + b * p[1] + c * p[2] + dd)), 2),
                          projected_px=round(length_px, 1), drawn=bool(length_px >= TICK_MIN_PX)))
    return ticks


def sheet_geometry(d: Data):
    pts, faces, lines = [], [], []
    for (x0, y0, x1, y1), plane, rej in zip(d.tile_bounds, d.tile_plane, d.tile_rejected):
        if rej:
            continue
        corners = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        base = len(pts)
        pts += [(x, y, plane_z(plane, x, y)) for x, y in corners]
        faces += [4, base, base + 1, base + 2, base + 3]
        lines += [5, base, base + 1, base + 2, base + 3, base]
    P = np.array(pts, float)
    return pv.PolyData(P, faces=np.array(faces)), pv.PolyData(P, lines=np.array(lines))


def plane_sheet(d: Data, ramp_full: np.ndarray, ticks: list[dict]) -> tuple[np.ndarray, bool, dict]:
    """Translucent tile planes by compositing, so the sheet does not band.

    A sheet drawn with ordinary depth testing cuts through the ground points it was fitted to (half of them lie
    a few centimetres above it, half below), which prints the terrain's tiny deviations as stripes. Instead:
    pass 1 renders all points on the ramp; passes 2 and 3 render, on black, the sheet faces (white) and the
    tile edges (red), each depth-tested against the points that are NOT plane inliers (the pipeline's non-ground
    voxels, painted back). Wherever a pass shows its colour, the sheet colour is blended over pass 1 (opacity
    SHEET_OPACITY, edges SHEET_EDGE_OPACITY). So objects standing on the ground hide the sheet behind them, and
    every plane inlier is seen through the sheet. Passes 4 and 5 draw the ticks (blue on black) with nothing in
    front of them, once widened by TICK_KEYLINE_PX on every side and once at their own size: they are
    annotations, drawn on top in the tick colour inside a keyline in the background colour (overlay_colours),
    because the points they measure from would hide them and a light tick needs a dark rim on light points.
    The pass colours (MASK_*) only select pixels; they never reach the PNG."""
    img, _, ok = render([(d.xyz, ramp_full, PS_RAW)])
    p_ground = d.v_ground[d.p_voxel]
    occ = d.xyz[~p_ground]
    black = np.zeros((len(occ), 3), np.uint8)
    faces, edges = sheet_geometry(d)

    def pass_img(add):
        im, _, ok_ = render([(occ, black, PS_RAW)], background=MASK_BG, extra=add)
        return im, ok_

    s_img, ok2 = pass_img(lambda pl: pl.add_mesh(faces, color=MASK_SHEET, lighting=False, show_edges=False))
    e_img, ok3 = pass_img(lambda pl: pl.add_mesh(edges, color=MASK_EDGE, line_width=2, lighting=False))

    def add_ticks(pad):
        def add(pl):
            tp, tl = [], []
            for t in (t for t in ticks if t["drawn"]):
                x, y, z = t["top_local"]
                base = len(tp)
                tp += [(x, y, z), (x, y, t["plane_z"])]
                tl += [2, base, base + 1]
            if tp:
                P = np.array(tp, float)
                pl.add_mesh(pv.PolyData(P, lines=np.array(tl)), color=MASK_TICK, line_width=TICK_PX + 2 * pad,
                            lighting=False)
                pl.add_points(P[1::2], color=MASK_TICK, point_size=TICK_FOOT_PX + 2 * pad, lighting=False,
                              render_points_as_spheres=False)
                pl.add_points(P[0::2], color=MASK_TICK, point_size=TICK_TOP_PX + 2 * pad, lighting=False,
                              render_points_as_spheres=False)
        return add

    k_img, _, ok4 = render([], background=MASK_BG, extra=add_ticks(TICK_KEYLINE_PX))
    t_img, _, ok5 = render([], background=MASK_BG, extra=add_ticks(0))
    sm = np.all(s_img == hex_rgb(MASK_SHEET), axis=-1)
    em = np.all(e_img == hex_rgb(MASK_EDGE), axis=-1)
    km = np.all(k_img == hex_rgb(MASK_TICK), axis=-1)
    tm = np.all(t_img == hex_rgb(MASK_TICK), axis=-1)
    out = img.astype(float)
    sc = hex_rgb(OVERLAY["sheet"]).astype(float)
    out[sm] = (1 - SHEET_OPACITY) * out[sm] + SHEET_OPACITY * sc
    out[em] = (1 - SHEET_EDGE_OPACITY) * out[em] + SHEET_EDGE_OPACITY * sc
    out[km] = hex_rgb(OVERLAY["tick_keyline"])
    out[tm] = hex_rgb(OVERLAY["tick"])
    info = dict(method="composite of five renders with the same camera (see pipeline/render.py plane_sheet)",
                occluders="points whose voxel is not a plane inlier (labels_crop.npz voxel_ground == False)",
                sheet_pixels=int(sm.sum()), edge_pixels=int(em.sum()), tick_pixels=int(tm.sum()),
                tick_keyline_pixels=int((km & ~tm).sum()))
    return out.round().astype(np.uint8), ok and ok2 and ok3 and ok4 and ok5, info


# ----------------------------------------------------------------------------------------------- weaknesses
def observations(d: Data) -> dict:
    """Facts about the labels that the speaker should know, measured on the arrays the renders show."""
    veg = d.cluster_class == S.VEGETATION
    on = d.v_cluster >= 0
    bvox = d.V[d.v_class == S.BUILDINGS, :2]
    dist, _ = KDTree(bvox).query(d.V[on, :2], workers=-1)
    n_cl = len(d.cluster_class)
    dmin = np.full(n_cl, np.inf)
    np.minimum.at(dmin, d.v_cluster[on], dist)
    flat_near = veg & (d.cluster_vext < 3.0) & (dmin < 2.0) & (d.cluster_top_hag > 5.0)
    vox = np.isin(d.v_cluster, np.flatnonzero(flat_near))
    pts = vox[d.p_voxel]
    sf_v = d.v_class == S.STREET_FURNITURE
    return dict(
        vegetation_flat_clusters_at_buildings=dict(
            clusters=int(np.count_nonzero(flat_near)), voxels=int(np.count_nonzero(vox)),
            points=int(np.count_nonzero(pts)),
            rule="vegetation clusters less than 3 m tall (vertical extent), more than 5 m above the ground and "
                 "within 2 m (plan view) of a building voxel",
            reading="horizontal stripes on facades (balconies or floor edges, UNVERIFIED) that rule 1 calls "
                    "vegetation because their share of multiple returns is above 0.4"),
        street_furniture=dict(objects=int(len(d.sf_clusters)), voxels=int(np.count_nonzero(sf_v)),
                              points=int(np.count_nonzero(d.p_class == S.STREET_FURNITURE)),
                              voxel_height_above_ground_m=([round(float(d.v_hag[sf_v].min()), 2),
                                                            round(float(d.v_hag[sf_v].max()), 2)]
                                                           if sf_v.any() else None),
                              what_it_is="UNVERIFIED (no imagery checked)"),
        known_errors_from_pipeline=[r["cluster"] for r in d.pipeline.get("known_errors", {})
                                    .get("vegetation_clusters_mostly_ahn_ground_or_building", [])],
    )


# ----------------------------------------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", nargs="*", help="subset: f1 f2 f3 f4 f5 f6 hook closeup plane")
    args = ap.parse_args()
    only = set(args.only or [])
    full = not only
    want = (lambda k: full or k in only)
    OUT.mkdir(parents=True, exist_ok=True)
    t_start = time.perf_counter()
    pal, pal_src = PAL, PALETTE_SOURCE
    col = Colours(pal)
    bg = pal["background"]
    d = Data()
    zr = d.ground_z_ref
    ramp_full = ramp_colours(d.xyz[:, 2], zr, pal["height_ramp"])
    ramp_vox = ramp_colours(d.V[:, 2], zr, pal["height_ramp"])
    sf_v = d.v_class == S.STREET_FURNITURE
    sf_p = d.p_class == S.STREET_FURNITURE
    ps_sf_v = ps_sf_p = PS_FURNITURE
    frames, checks, labels = {}, dict(camera_unchanged={}), {}
    imgs = {}
    half = W_WIDE // 2
    divider_cols = list(range(half - DIVIDER_PX // 2, half + DIVIDER_PX // 2))

    def done(key, file, img, ok, **info):
        save_png(img, file)
        imgs[key] = img
        checks["camera_unchanged"][file] = ok
        frames[file] = dict(px=[img.shape[1], img.shape[0]], **info)
        print(f"{file}: {img.shape[1]}x{img.shape[0]}, camera unchanged {ok}")

    if want("f1"):
        img, pl, ok = render([(d.xyz, ramp_full, PS_RAW)], keep=True)
        edge = jaarbeurs_hall(d, pl, img)
        pl.close()
        # Arrow for the deck (slide 4, left frame): the tip on the Jaarbeurs hall's roof.
        labels["f1_load"] = dict(jaarbeurs_hall=edge["px"], jaarbeurs_hall_note=edge)
        imgs["f1"] = img
        foot = footprint(img, col.bg)
        done("f1", "f1_load.png", img, ok, points=len(d.xyz), point_size_px=PS_RAW,
             footprint_coverage=footprint_coverage(img, foot, col.bg), shows="all points of the crop, height ramp")
    elif (OUT / "f1_load.png").exists():
        foot = footprint(np.asarray(Image.open(OUT / "f1_load.png").convert("RGB")), col.bg)
    else:
        foot = None

    def fcov(img):
        return footprint_coverage(img, foot, col.bg) if foot is not None else None

    if want("f2"):
        img, _, ok = render([(d.V, ramp_vox, PS_VOXEL)])
        done("f2", "f2_voxel.png", img, ok, points=len(d.V), point_size_px=PS_VOXEL, footprint_coverage=fcov(img),
             shows="voxel downsampling: one average point per 0.5 m voxel, height ramp")
    if want("f3"):
        rgb = ramp_vox.copy()
        rgb[d.v_ground] = hex_rgb(pal["ground"])
        img, _, ok = render([(d.V, rgb, PS_VOXEL)])
        done("f3", "f3_ground.png", img, ok, points=len(d.V), point_size_px=PS_VOXEL, footprint_coverage=fcov(img),
             ground_voxels=int(d.v_ground.sum()),
             shows="ground removal: ground voxels in the ground colour, the rest on the ramp")
    if want("f4"):
        rgb, info = cluster_colours(d, pal)
        img, _, ok = render([(d.V, rgb, PS_VOXEL)])
        done("f4", "f4_clusters.png", img, ok, points=len(d.V), point_size_px=PS_VOXEL, footprint_coverage=fcov(img),
             shows="clustering: DBSCAN clusters in the palette's cycling cluster colours, noise dimmed, ground in the "
                   "ground colour", **info)
    bad_cl, excl_info = anchor_excluded_vegetation(d)
    if want("f5"):
        rgb = col.classes(d.v_class)
        layers = [(d.V[~sf_v], rgb[~sf_v], PS_VOXEL), (d.V[sf_v], rgb[sf_v], ps_sf_v)]
        img, _, ok = render(layers)
        done("f5", "f5_labels.png", img, ok, points=len(d.V), point_size_px=PS_VOXEL, footprint_coverage=fcov(img),
             street_furniture_point_size_px=ps_sf_v, street_furniture_visible=sf_visibility(img, col),
             shows="labelling: the four classes on the voxels")
        idrgb = id_colours(d.v_class, d.v_cluster, bad_cl, col)
        id_img, pl, _ = render([(d.V[~sf_v], idrgb[~sf_v], PS_VOXEL), (d.V[sf_v], idrgb[sf_v], ps_sf_v)], keep=True)
        assert np.array_equal(np.all(id_img == col.bg, -1), np.all(img == col.bg, -1)), "ID pass differs"
        usable = ~((d.v_class == S.VEGETATION) & (d.v_cluster >= 0) & bad_cl[np.maximum(d.v_cluster, 0)])
        f5_anchor_job = (img, id_img, pl, usable)  # picked after f6, near the f6 anchors (Morph 12 -> 13)
        checks["grayscale_f5_labels"] = grayscale_qa(img, "f5_labels.png", col)
    else:
        f5_anchor_job = None
    p_cluster = d.v_cluster[d.p_voxel]
    usable_p = ~((d.p_class == S.VEGETATION) & (p_cluster >= 0) & bad_cl[np.maximum(p_cluster, 0)])
    rgb_p = col.classes(d.p_class)
    lab_layers = [(d.xyz[~sf_p], rgb_p[~sf_p], PS_RAW), (d.xyz[sf_p], rgb_p[sf_p], ps_sf_p)]
    idrgb_p = id_colours(d.p_class, p_cluster, bad_cl, col)
    id_layers = [(d.xyz[~sf_p], idrgb_p[~sf_p], PS_RAW), (d.xyz[sf_p], idrgb_p[sf_p], ps_sf_p)]
    if want("f6"):
        img, _, ok = render(lab_layers)
        done("f6", "f6_final.png", img, ok, points=len(d.xyz), point_size_px=PS_RAW, footprint_coverage=fcov(img),
             street_furniture_point_size_px=ps_sf_p, street_furniture_visible=sf_visibility(img, col),
             shows="visualisation: the voxel labels painted back onto every original point (one KDTree query)")
        id_img, pl, _ = render(id_layers, keep=True)
        labels["f6_final"] = pick_anchors(id_img, pl, d.xyz, d.p_class, usable_p, col, (200, W_FRAME - 200),
                                          (0, W_FRAME))
        pl.close()
        checks["anchors_on_class_f6_final"] = anchors_on_class(img, labels["f6_final"], col)
        checks["grayscale_f6_final"] = grayscale_qa(img, "f6_final.png", col)
    if f5_anchor_job is not None:
        img5, id_img, pl, usable = f5_anchor_job
        pref = {n: labels["f6_final"][n]["px"] for n in CLASSES if labels.get("f6_final", {}).get(n)}
        labels["f5_labels"] = pick_anchors(id_img, pl, d.V, d.v_class, usable, col, (200, W_FRAME - 200),
                                           (0, W_FRAME), prefer=pref or None)
        pl.close()
        checks["anchors_on_class_f5_labels"] = anchors_on_class(img5, labels["f5_labels"], col)
        if pref:
            checks["anchors_f5_vs_f6_px"] = {n: round(float(np.hypot(*np.subtract(labels["f5_labels"][n]["px"],
                                                                                   pref[n]))), 1)
                                             for n in pref if labels["f5_labels"].get(n)}
    if want("hook"):
        raw_w, _, ok1 = render([(d.xyz, ramp_full, PS_RAW)], width=W_WIDE)
        lab_w, _, ok2 = render(lab_layers, width=W_WIDE)
        split = raw_w.copy()
        split[:, half:] = lab_w[:, half:]
        split[:, divider_cols] = hex_rgb(OVERLAY["divider"])
        done("hook", "hook_split.png", split, ok1 and ok2, points=len(d.xyz), point_size_px=PS_RAW,
             street_furniture_point_size_px=ps_sf_p,
             street_furniture_visible_right_half=sf_visibility(split, col, x_from=half, skip_cols=divider_cols),
             divider=dict(colour=OVERLAY["divider"], px=DIVIDER_PX, columns=[divider_cols[0], divider_cols[-1]]),
             shows="left half: all points on the height ramp; right half: the painted-back labels (as f6)")
        ident = {}
        for key, wide, file in (("f1", raw_w, "f1_load.png"), ("f6", lab_w, "f6_final.png")):
            frame = imgs.get(key)
            if frame is None and (OUT / file).exists():
                frame = np.asarray(Image.open(OUT / file).convert("RGB"))
            if frame is not None:
                ident[f"wide_{'raw' if key == 'f1' else 'labels'}_centre_vs_{file}"] = crop_identity(wide, frame)
        checks["crop_identity"] = ident
        id_w, pl, _ = render(id_layers, width=W_WIDE, keep=True)
        id_w[:, divider_cols] = col.bg  # the divider is not street furniture
        anchors = pick_anchors(id_w, pl, d.xyz, d.p_class, usable_p, col, (half + 200, W_WIDE - 200),
                               (divider_cols[-1] + 1, W_WIDE))
        # Arrow for the wide alternative (slide 4 uses f1_load.jaarbeurs_hall): the tip on the hall's roof, in the
        # wide render's own pixels (the camera is the same, so the x of the raw half is the frame's x plus the margin).
        hall_info = jaarbeurs_hall(d, pl, split)
        anchors["jaarbeurs_hall"] = hall_info["px"]
        anchors["jaarbeurs_hall_note"] = hall_info
        labels["hook_split"] = anchors
        pl.close()
        checks["anchors_on_class_hook_split"] = anchors_on_class(split, anchors, col)
        checks["grayscale_hook_split_right_half"] = grayscale_qa(split, "hook_split.png", col, x_from=half,
                                                                 skip_cols=divider_cols)
    if want("closeup"):
        img, _, ok = render([(d.xyz, ramp_full, PS_RAW)], view_angle=CLOSEUP_VIEW_ANGLE, cam=CLOSEUP_CAMERA)
        pc = probe(W_FRAME, CLOSEUP_CAMERA, CLOSEUP_VIEW_ANGLE)
        cxy, _ = world_to_pixel(pc, d.xyz)
        pc.close()
        inside = (cxy[:, 0] >= 0) & (cxy[:, 0] < W_FRAME) & (cxy[:, 1] >= 0) & (cxy[:, 1] < H)
        cls_in = {n: int(np.count_nonzero(inside & (d.p_class == i))) for i, n in enumerate(S.CLASS_NAMES)}
        done("closeup", "closeup.png", img, ok, points=len(d.xyz), point_size_px=PS_RAW,
             view_angle_deg=CLOSEUP_VIEW_ANGLE, points_projecting_inside=int(inside.sum()),
             points_inside_by_our_label=cls_in,
             shows="same camera position, narrow view angle aimed at the trees north-west of the hall: single points visible (height ramp)")
    if want("plane"):
        pp = probe(W_FRAME, CAMERA)
        ticks = choose_ticks(d, pp)
        pp.close()
        img, ok, info = plane_sheet(d, ramp_full, ticks)
        done("plane", "plane_sheet.png", img, ok, points=len(d.xyz), point_size_px=PS_RAW,
             tiles=int(np.count_nonzero(~d.tile_rejected)), tiles_rejected=int(np.count_nonzero(d.tile_rejected)),
             sheet=dict(colour=OVERLAY["sheet"], opacity=SHEET_OPACITY, edge_opacity=SHEET_EDGE_OPACITY, **info),
             ticks=ticks, tick_colour=OVERLAY["tick"], tick_keyline_colour=OVERLAY["tick_keyline"],
             tick_px=dict(line=TICK_PX, foot=TICK_FOOT_PX, top=TICK_TOP_PX, keyline=TICK_KEYLINE_PX,
                          min_projected_length=TICK_MIN_PX),
             ticks_drawn_unoccluded=True,
             shows="the fitted per-tile ground planes as translucent sheets over all points, and ticks in the "
                   "tick colour (keyline in the background colour) from a few objects straight down to their "
                   "tile's plane")
    if not full:
        print(f"subset rendered in {time.perf_counter() - t_start:.1f} s (labels.json and render_spec.json untouched)")
        return 0

    # labels.json: {frame: {class: [x, y]}} (+ jaarbeurs_hall on f1_load and hook_split); details go to render_spec.json
    lab_out, lab_detail = {}, {}
    for frame, a in labels.items():
        lab_out[frame] = {n: a[n]["px"] for n in CLASSES if a.get(n)}
        if "jaarbeurs_hall" in a:
            lab_out[frame]["jaarbeurs_hall"] = a["jaarbeurs_hall"]
        lab_detail[frame] = a
    (OUT / "labels.json").write_text(json.dumps(lab_out, indent=1) + "\n")

    sf_alone = {f"{ps}_px": sf_visibility(render([(d.xyz[sf_p], rgb_p[sf_p], ps)])[0], col)
                for ps in sorted({PS_RAW, PS_FURNITURE})}
    vtk_v = vtkVersion.GetVTKVersion()
    spec = dict(
        label="FINAL",
        generated_by="pipeline/render.py",
        inputs=dict(labels_npz=str(NPZ.relative_to(ROOT)), labels_npz_sha256=d.npz_sha256, crop=d.crop_file,
                    pipeline_json_label=d.pipeline.get("label"), palette_source=pal_src),
        versions=dict(python=platform.python_version(), numpy=np.__version__, pyvista=pv.__version__, vtk=vtk_v,
                      scipy=version("scipy"), pillow=version("pillow")),
        coordinates=dict(frame="crop-local metres: xyz - LAS header.mins (as in the slide 8 code)",
                         origin_rd_nap=[float(v) for v in d.origin]),
        camera=dict(position=CAMERA["position"], focal_point=CAMERA["focal_point"], view_up=CAMERA["view_up"],
                    view_angle=CAMERA["view_angle"], view_angle_is="vertical (VTK default, UseHorizontalViewAngle off)",
                    **pose_numbers(CAMERA),
                    never_called=["reset_camera", "view_isometric"],
                    pose_history=("2026-10-11: new crop around the Jaarbeurs hall; one pose, 15 deg west of south at 75 deg "
                                  "elevation, centred on the crop (a flatter view hid two of the three street "
                                  "furniture objects behind the hall). The first example street used position "
                                  "[123, -106, 398], focal point [99, 120, 4]."),
                    coverage=dict(final=coverage(d, CAMERA)),
                    closeup_view_angle=CLOSEUP_VIEW_ANGLE),
        canvas=dict(height_px=H, frame_px=[W_FRAME, H], wide_px=[W_WIDE, H],
                    rule="same camera and vertical view angle at the same height: the frame is the centre crop of "
                         "the wide render; (4190 - 1588) is even"),
        background=bg, eye_dome_lighting=False,
        points=dict(style="unlit squares (render_points_as_spheres=False, lighting=False)", anti_aliasing="off"),
        height_ramp=dict(stops=pal["height_ramp"], interpolation="linear RGB",
                         clim_m_above_ground_median=list(HEIGHT_CLIM),
                         ground_median_local_z=round(zr, 4), ground_median_source="median z of the pipeline's ground "
                         "voxels (labels_crop.npz voxel_ground), not AHN's classes",
                         clim_local_z=[round(zr + HEIGHT_CLIM[0], 4), round(zr + HEIGHT_CLIM[1], 4)],
                         fixed_for_all_frames=True),
        palette={n: pal[n] for n in S.CLASS_NAMES},
        clusters=dict(cycle=pal["clusters"], seed=CLUSTER_SEED, noise=pal["noise"]),
        unlabelled=pal["unlabelled"],
        overlays=OVERLAY,
        point_size_px=dict(
            raw_and_painted_back=PS_RAW, voxels=PS_VOXEL, street_furniture=PS_FURNITURE,
            street_furniture_actor="own actor drawn after the rest, on f5, f6 and the hook's labelled half",
            street_furniture_reason=(
                "deliberate visibility choice: the class has one object (observations.street_furniture); at the "
                "3 px of the other points it is a speck (street_furniture_drawn_alone) that disappears when the "
                "frame is scaled down on a slide. Drawn larger so it can be seen and labelled; it stays where its "
                "own points project. Nothing hides it from this camera (compare street_furniture_drawn_alone with "
                "frames.f6_final.png.street_furniture_visible). The deck's small print states 1 object, 9 points."),
            street_furniture_drawn_alone=sf_alone,
            voxels_reason=(
                "voxel frames use the raw frame's 3 px, so f2 differs from f1 only in the number of points. From "
                "this camera neighbouring ground voxels are drawn only a few px apart (voxel_spacing_px), so "
                "larger squares overlap and the voxel frames looked smoother than f1 instead of sparser. At 3 px "
                "the gaps of the voxel grid "
                "show, most in the foreground rows nearest the camera (frames.*.footprint_coverage); f6 is dense "
                "again (all points painted back)."),
            voxel_spacing_px=voxel_spacing(d)),
        frames=frames,
        labels=dict(file="renders/labels.json", detail=lab_detail,
                    method="per class: densest visible patch (61 px window, minus other classes) inside the "
                           "margins (200 px left/right of the usable area, 200 px top/bottom), anchors at least 300 "
                           "px apart; street furniture: in the topmost visible patch the pixel nearest its centre; "
                           "snapped to the front-most 3D point of that class projecting within 3 px (renderer "
                           "camera matrices, cross-checked with vtkCoordinate); hook_split: right half only "
                           "(divider excluded); f5_labels: searched first within 40 px of the f6_final anchor of "
                           "the same class (chips stay put across the Morph from slide 12 to 13); f1_load: only "
                           "the Jaarbeurs hall arrow (see detail.f1_load.jaarbeurs_hall_note)",
                    vegetation_excluded=excl_info),
        checks=checks,
        observations=observations(d),
        seconds=round(time.perf_counter() - t_start, 1),
    )
    (OUT / "render_spec.json").write_text(json.dumps(spec, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps(dict(labels=lab_out, crop_identity=checks.get("crop_identity"),
                          gray={k: (v["smallest_pair"], v["smallest_difference"], v["passes"])
                                for k, v in checks.items() if k.startswith("grayscale")},
                          camera_unchanged=all(checks["camera_unchanged"].values()),
                          coverage_final=spec["camera"]["coverage"]["final"],
                          seconds=spec["seconds"]), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
