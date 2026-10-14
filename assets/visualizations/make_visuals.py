"""Oblique, eye-dome-lit renders of the Jaarbeurs crop for the deck: hero (slides 1, 5) and before/after (slide 18).

    uv run python assets/visualizations/make_visuals.py              # all
    uv run python assets/visualizations/make_visuals.py --only hero  # subset: hero split

Reads only what pipeline/render.py reads (results/labels_crop.npz, data/<crop>.laz, deck/content.yaml palette) and
reuses its Data, colours and cluster colouring, so every colour means the same thing as in renders/. Nothing is
recomputed: no RANSAC, no DBSCAN, no labelling. Only the camera and the shading differ from renders/:
- an oblique perspective camera (one pose for every image, never reset),
- eye-dome lighting (VTK's depth-only shading) so roofs, facades and trees read as 3D.
EDL darkens point colours at depth edges, so these PNGs are NOT pixel-exact class colours: they are for the
audience, not for the grayscale/anchor QA of pipeline/render.py, which keeps its own flat renders.

Writes assets/visualizations/*.png and spec.json (camera, sizes, inputs' sha256).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pyvista as pv
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "pipeline"))

import render as R  # noqa: E402  (pipeline/render.py: Data, palette, colouring)

OUT = Path(__file__).resolve().parent

# Crop-local metres (origin = LAS header.mins); the crop is 200 m x 200 m, the hall centre at about (112, 108).
# One pose for every image: from the south-south-west (azimuth 200 deg), 28 deg above the horizon, so facades, the
# parking deck's floors, the crane and tree crowns all show. Chosen from four candidates (200/35, 200/28, 235/32,
# 160/32); a steeper view flattens the scene back into a map, a lower one hides the ground behind the hall.
FOCAL = np.array([102.0, 100.0, 10.0])
AZIMUTH_DEG, ELEVATION_DEG, DISTANCE_M, VIEW_ANGLE = 200.0, 28.0, 350.0, 30.0
FIT = 0.83  # the crop spans about 78 % of the 16:9 hero's width; narrower images should fill about 94 %


def camera_for(size) -> dict:
    """Same direction and focal point for every image; only the distance grows for images narrower than 16:9
    (VTK's view angle is vertical, so a narrower image would cut the crop's sides off)."""
    aspect = size[0] / size[1]
    dist = DISTANCE_M * max(1.0, (16 / 9) / aspect * FIT)
    a, e = np.radians(AZIMUTH_DEG), np.radians(ELEVATION_DEG)
    pos = FOCAL + dist * np.array([np.sin(a) * np.cos(e), np.cos(a) * np.cos(e), np.sin(e)])
    return dict(position=pos.round(3).tolist(), focal_point=FOCAL.tolist(), view_up=[0.0, 0.0, 1.0],
                view_angle=VIEW_ANGLE, azimuth_deg=AZIMUTH_DEG, elevation_deg=ELEVATION_DEG,
                distance_m=round(float(dist), 2))


HERO_PX = (3840, 2160)   # rendered 16:9, saved cropped to the crop's content (hero_trim.png)
SPLIT_PX = (1920, 1560)  # each half of the before/after
# Point sizes in px for a 1920 px wide image, scaled with the image width so every image has the same look.
PS_FULL = 4              # raw and painted-back points (722 961)
PS_FURNITURE = 14        # street furniture: 3 objects, a few dozen points; same deliberate choice as renders/


def render(layers, size, edl=True, hall=None):
    """layers: [(points, rgb uint8 (N, 3), point size px at 1920 px width), ...]. With hall=Data, also returns
    pipeline/render.py's Jaarbeurs hall anchor (BAG footprint centre at roof height) projected with this camera."""
    k = size[0] / 1920
    pl = pv.Plotter(off_screen=True, window_size=list(size))
    pl.set_background(R.BACKGROUND)
    for pts, rgb, ps in layers:
        if len(pts):
            pl.add_points(np.ascontiguousarray(pts, np.float64), scalars=rgb, rgb=True, point_size=max(1.0, ps * k),
                          render_points_as_spheres=False, lighting=False)
    if edl:
        pl.enable_eye_dome_lighting()
    cam = camera_for(size)
    pl.camera_position = [tuple(cam["position"]), tuple(cam["focal_point"]), tuple(cam["view_up"])]
    pl.camera.view_angle = cam["view_angle"]
    img = pl.screenshot(None, return_img=True)[..., :3].copy()
    c = pl.camera
    assert np.allclose(c.position, cam["position"]) and np.allclose(c.focal_point, cam["focal_point"])
    anchor = R.jaarbeurs_hall(hall, pl, img) if hall is not None else None
    pl.close()
    return (img, anchor) if hall is not None else img


def content_box(imgs, margin=0.03):
    """One crop box (x0, y0, x1, y1) around every non-background pixel of all images, plus a margin: the same
    box for every image of a set, so their framing stays identical."""
    bg = R.hex_rgb(R.BACKGROUND)
    m = np.zeros(imgs[0].shape[:2], bool)
    for im in imgs:
        m |= np.any(im != bg, axis=-1)
    ys, xs = np.nonzero(m)
    h, w = m.shape
    pad = int(margin * max(h, w))
    return (max(0, xs.min() - pad), max(0, ys.min() - pad), min(w, xs.max() + 1 + pad), min(h, ys.max() + 1 + pad))


def crop(img, box):
    x0, y0, x1, y1 = box
    return img[y0:y1, x0:x1]


def save(img, name):
    p = OUT / name
    Image.fromarray(img).save(p, optimize=True)
    print(f"{name}: {img.shape[1]}x{img.shape[0]}")
    return p


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", nargs="*", default=None)
    a = ap.parse_args()
    want = (lambda k: not a.only or k in a.only)
    pal, col, d = R.PAL, R.Colours(R.PAL), R.Data()
    zr = d.ground_z_ref
    ramp_full = R.ramp_colours(d.xyz[:, 2], zr, pal["height_ramp"])
    sf_p = d.p_class == R.S.STREET_FURNITURE
    rgb_p = col.classes(d.p_class)
    files, crops, anchors = {}, {}, {}

    if want("hero"):
        img, hall = render([(d.xyz, ramp_full, PS_FULL)], HERO_PX, hall=d)
        box = content_box([img])
        crops["hero_trim"] = [int(v) for v in box]
        files["hero_trim"] = save(crop(img, box), "hero_trim.png")
        anchors["hero_trim"] = dict(jaarbeurs_hall=[hall["px"][0] - int(box[0]), hall["px"][1] - int(box[1])],
                                    jaarbeurs_hall_note=hall)
        assert hall["pixel_shows_crop"], "hall anchor lands on the background"

    if want("split"):
        raw = render([(d.xyz, ramp_full, PS_FULL)], SPLIT_PX)
        lab = render([(d.xyz[~sf_p], rgb_p[~sf_p], PS_FULL), (d.xyz[sf_p], rgb_p[sf_p], PS_FURNITURE)],
                     SPLIT_PX)
        box = content_box([raw, lab])
        crops["split"] = [int(v) for v in box]
        files["split_raw"] = save(crop(raw, box), "split_raw.png")
        files["split_labels"] = save(crop(lab, box), "split_labels.png")

    spec_p = OUT / "spec.json"
    spec = json.loads(spec_p.read_text()) if spec_p.exists() and a.only else {}
    spec.update(camera={n: camera_for(sz) for n, sz in (("hero", HERO_PX), ("split", SPLIT_PX))},
                edl=True, point_size_px_at_1920=dict(full=PS_FULL, street_furniture=PS_FURNITURE),
                inputs=dict(labels_crop_npz_sha256=d.npz_sha256, crop=d.crop_file, palette=R.PALETTE_SOURCE),
                note="Same arrays and colours as pipeline/render.py; only camera, eye-dome shading and the crop "
                     "box differ. EDL darkens colours at depth edges: not for pixel-exact class QA.")
    spec.setdefault("crop_boxes_px", {}).update(crops)
    spec.setdefault("outputs_sha256", {}).update({k_: hashlib.sha256(p.read_bytes()).hexdigest()
                                                   for k_, p in files.items()})
    spec_p.write_text(json.dumps(spec, indent=1, default=str))
    if anchors:
        an_p = OUT / "anchors.json"   # same shape as renders/labels.json: {frame stem: {key: [x_px, y_px]}}
        old = json.loads(an_p.read_text()) if an_p.exists() else {}
        old.update(anchors)
        an_p.write_text(json.dumps(old, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
