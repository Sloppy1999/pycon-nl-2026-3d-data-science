"""Slide 8: the four hand-offs between laspy, NumPy, Open3D and PyVista, each checked as copy or view.

The slide shows the call of each hand-off (deck/content.yaml slide 8 rows); this file runs them on the AHN5 crop
and asserts the verdicts. bench/python_facts.py records the same checks plus timings in results/python_facts.json.
"""

from _setup import check

import laspy
import numpy as np
import open3d as o3d
import pyvista as pv

las = laspy.read("crop.laz")
pcd = o3d.geometry.PointCloud()

# --- slide ---
xyz = las.xyz - las.header.mins
v = o3d.utility.Vector3dVector(xyz)
pcd.points = v
pts = np.asarray(pcd.points)
poly = pv.PolyData(pts)
# --- end ---

check(not np.shares_memory(las.xyz, las.xyz), "las.xyz: a new array on every access (copy)")
xyz[0, 0] += 1000.0
check(np.asarray(pcd.points)[0, 0] != xyz[0, 0], "Vector3dVector: the point cloud keeps its own copy")
xyz[0, 0] -= 1000.0
pts[0, 0] = 12345.0
check(np.asarray(pcd.points)[0, 0] == 12345.0, "np.asarray(pcd.points): a writeable view (writes reach the cloud)")
check(np.shares_memory(poly.points, pts), "pv.PolyData(pts): shares memory with pts (view)")
