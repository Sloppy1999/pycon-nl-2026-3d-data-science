"""PyVista 0.49.0 / VTK 9.7.1 off-screen rendering check: PolyData from numpy, dark background, fixed camera,
1920x1080 screenshot, and the large-coordinate (RD/UTM) precision question.

Run normally and with DISPLAY/WAYLAND_DISPLAY unset to emulate a headless box:
    env -u DISPLAY -u WAYLAND_DISPLAY python 04_pyvista_render.py headless
"""
import sys
import time
from pathlib import Path

import numpy as np
import laspy
import pyvista as pv

tag = sys.argv[1] if len(sys.argv) > 1 else "desktop"
OUT = Path(__file__).with_name("out")
las = laspy.read(OUT / "street.laz")
xyz = np.ascontiguousarray(las.xyz)
cls = np.asarray(las.classification)
rng = np.random.default_rng(0)
sel = rng.choice(len(xyz), 300_000, replace=False)
xyz, cls = xyz[sel], cls[sel]
origin = np.floor(xyz.min(axis=0))
local = xyz - origin

# --- PolyData from numpy -----------------------------------------------------------
cloud = pv.PolyData(local)                 # deep=False default
print("PolyData points dtype", cloud.points.dtype, "| n_points", cloud.n_points, "| n_cells (verts)", cloud.n_cells)
print("PolyData shares memory with input (deep=False, float64):", np.shares_memory(cloud.points, local))
c32 = local.astype(np.float32)
print("PolyData(float32) shares memory:", np.shares_memory(pv.PolyData(c32).points, c32))
print("PolyData(deep=True) shares memory:", np.shares_memory(pv.PolyData(local, deep=True).points, local))
cloud["class"] = cls
print("point_data keys", list(cloud.point_data.keys()))

# --- camera: (position, focal_point, view_up), identical across all pipeline steps ---
CAMERA = [(-25.0, -45.0, 40.0), (50.0, 15.0, 2.0), (0.0, 0.0, 1.0)]
COLORS = {1: "#f2c14e", 2: "#5b6770", 5: "#4caf50", 6: "#d9d9d9"}


def render(points, scalars_rgb, path, camera, size=(1920, 1080), point_size=3.0, spheres=True):
    pl = pv.Plotter(off_screen=True, window_size=list(size))
    pl.set_background("#0b0d10")
    pl.add_points(points, scalars=scalars_rgb, rgb=True, point_size=point_size,
                  render_points_as_spheres=spheres)
    pl.camera_position = camera
    pl.enable_parallel_projection() if False else None
    t0 = time.perf_counter()
    img = pl.screenshot(str(path), return_img=True)
    dt = time.perf_counter() - t0
    cam_after = pl.camera_position
    rw = pl.render_window.GetClassName()
    pl.close()
    return img, dt, cam_after, rw


rgb = np.array([[int(COLORS[c][i:i + 2], 16) for i in (1, 3, 5)] for c in cls], dtype=np.uint8)
img, dt, cam_after, rw = render(local, rgb, OUT / f"render_{tag}.png", CAMERA)
print(f"[{tag}] render window class: {rw} | screenshot shape {img.shape} dtype {img.dtype} | {dt*1000:.0f} ms")
print(f"[{tag}] camera after render equals requested:",
      np.allclose(np.array([*cam_after]).ravel(), np.array(CAMERA).ravel()))

# Same camera, different data (pipeline step 2: ground removed) -> consistent framing for Morph
img2, *_ = render(local[cls != 2], rgb[cls != 2], OUT / f"render_{tag}_noground.png", CAMERA)

# --- precision: raw RD coordinates vs local, zoomed onto one pole ------------------------
pole_pts = local[cls == 1]
first = pole_pts[pole_pts[:, 0] < pole_pts[:, 0].min() + 1.0]       # the left-most pole only
pole_c = np.array([first[:, 0].mean(), first[:, 1].mean(), first[:, 2].min() + 0.5])  # ~0.5 m above its foot
near = np.linalg.norm(local[:, :2] - pole_c[:2], axis=1) < 1.0
print(f"[{tag}] zoom subset: {near.sum()} points, pole centre (local) {np.round(pole_c, 3)}")
zoom_cam_local = [tuple(pole_c + np.array([0.0, -1.2, 0.3])), tuple(pole_c), (0, 0, 1)]
zoom_cam_raw = [tuple(np.array(zoom_cam_local[0]) + origin), tuple(np.array(zoom_cam_local[1]) + origin), (0, 0, 1)]
im_local, *_ = render(local[near], rgb[near], OUT / f"zoom_local_{tag}.png", zoom_cam_local, size=(960, 540),
                      point_size=4.0, spheres=False)
im_raw, *_ = render(xyz[near], rgb[near], OUT / f"zoom_rawRD_{tag}.png", zoom_cam_raw, size=(960, 540),
                    point_size=4.0, spheres=False)
im_raw32, *_ = render(xyz[near].astype(np.float32), rgb[near], OUT / f"zoom_rawRD_f32input_{tag}.png", zoom_cam_raw,
                      size=(960, 540), point_size=4.0, spheres=False)
diff = np.abs(im_local.astype(int) - im_raw.astype(int)).sum(axis=2)
diff32 = np.abs(im_local.astype(int) - im_raw32.astype(int)).sum(axis=2)
print(f"[{tag}] zoom raw-RD(float64 input) vs local: pixels differing {np.count_nonzero(diff)} of {diff.size}")
print(f"[{tag}] zoom raw-RD(float32 input) vs local: pixels differing {np.count_nonzero(diff32)} of {diff32.size}")
