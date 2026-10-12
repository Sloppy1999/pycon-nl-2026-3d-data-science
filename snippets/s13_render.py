"""Slide 13: 6 Visualisation. Paint the labels back onto every point (one KDTree query), render off-screen.

Setup: pipeline steps 1 to 5; class colours from deck/content.yaml (render_palette); the fixed camera from
renders/render_spec.json when pipeline/render.py has written it, else the camera of the approved render spec
(position (-60, -110, 141), focal point (110, 100, 6), view up z; VTK's default 30 degree view angle); frame size
1588 x 1792 and navy background via the PyVista theme. Writes f6_final.png into a temporary directory only.
Checks: the painted classes equal pipeline.steps.paint_back and results/labels_crop.npz; the PNG has the frame size.
"""

import json

from _setup import ROOT, check, labels_npz

import numpy as np
import pyvista as pv
import yaml
from scipy.spatial import KDTree

from pipeline import steps

las, xyz, origin = steps.load("crop.laz")
down = steps.downsample(steps.to_open3d(xyz, np.asarray(las.number_of_returns) > 1), 0.5)
ground, _ = steps.remove_ground(down, 25)
cls, _ = steps.label(down, ground, steps.cluster(down, ground, 0.75, 6))

palette = yaml.safe_load((ROOT / "deck" / "content.yaml").read_text())["meta"]["render_palette"]
RGB = np.array([[int(palette[n][i:i + 2], 16) for i in (1, 3, 5)] for n in steps.CLASS_NAMES], dtype=np.uint8)
spec_path = ROOT / "renders" / "render_spec.json"
cam = json.loads(spec_path.read_text()).get("camera", {}) if spec_path.exists() else {}
CAM = [tuple(cam.get("position", (-60.0, -110.0, 141.0))), tuple(cam.get("focal_point", (110.0, 100.0, 6.0))),
       tuple(cam.get("view_up", (0.0, 0.0, 1.0)))]
pv.OFF_SCREEN = True
pv.global_theme.window_size = [1588, 1792]
pv.global_theme.background = palette["background"]

# --- slide ---
P = np.asarray(down.points)
_, j = KDTree(P).query(
    xyz, workers=-1)
pl = pv.Plotter(off_screen=True)  # <<
pl.add_points(xyz, point_size=3,
    scalars=RGB[cls[j]], rgb=True)
pl.camera_position = CAM
pl.screenshot("f6_final.png")
# --- end ---

img = pl.screenshot(return_img=True)
pl.close()
check(img.shape[:2] == (1792, 1588), f"screenshot {img.shape[1]} x {img.shape[0]} px")
check(np.array_equal(cls[j], steps.paint_back(xyz, down, cls)), "same classes as steps.paint_back")
z = labels_npz()
if z is not None:
    check(np.array_equal(cls[j], z["point_class"]), f"same classes as results/labels_crop.npz ({len(j)} points)")
print("camera from", spec_path.name if cam else "the approved render spec (renders/render_spec.json not written yet)")
