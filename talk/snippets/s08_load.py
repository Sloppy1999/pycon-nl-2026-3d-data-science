"""Slide 8: 1 Load. laspy reads the LAZ, NumPy subtracts a local origin, Open3D gets a float64 array.

Checks: the same coordinates as pipeline.steps.load (which also makes the array C-contiguous).
"""

from _setup import check

import numpy as np

from pipeline import steps

# --- slide ---
import laspy
import open3d as o3d
las = laspy.read("crop.laz")
xyz = las.xyz - las.header.mins  # <<
v = o3d.utility.Vector3dVector(xyz)
pcd = o3d.geometry.PointCloud(v)
# --- end ---

_, ref_xyz, origin = steps.load("crop.laz")
check(np.array_equal(np.asarray(pcd.points), ref_xyz), "same points as steps.load + steps.to_open3d")
check(xyz.dtype == np.float64, f"dtype {xyz.dtype}, local origin {origin.tolist()}")
print("max local coordinate (m):", xyz.max(axis=0).round(3).tolist(), "| las.xyz F-ordered:", las.xyz.flags.f_contiguous)
