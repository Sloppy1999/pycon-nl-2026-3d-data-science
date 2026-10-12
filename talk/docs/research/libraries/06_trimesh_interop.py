"""trimesh 5.1.0 + interop (laspy -> numpy -> Open3D -> PyVista, trimesh <-> Open3D, trimesh -> PyVista).
Checks which conversions share memory (zero-copy) and which copy."""
import gc
import time
import warnings
from pathlib import Path

import numpy as np
import laspy
import open3d as o3d
import pyvista as pv
import trimesh

warnings.simplefilter("always")
OUT = Path(__file__).with_name("out")
las = laspy.read(OUT / "street.laz")
cls = np.asarray(las.classification)


def timed(label, fn, *a, **k):
    t0 = time.perf_counter(); r = fn(*a, **k); dt = time.perf_counter() - t0
    print(f"  {label}: {dt*1000:.1f} ms"); return r


print("== laspy -> numpy")
x1, x2 = np.asarray(las.x), np.asarray(las.x)
print("  np.asarray(las.x) new array each time:", not np.shares_memory(x1, x2), "| dtype", x1.dtype)
X = las.X
print("  las.X (raw int32) is a view on the point record:", np.shares_memory(X, las.points.array))
xyz = timed("las.xyz (builds new float64 (N,3), F-order)", lambda: las.xyz)
local = np.ascontiguousarray(xyz - xyz.min(axis=0))

print("== numpy -> Open3D legacy (always copies into std::vector<Eigen::Vector3d>)")
pcd = o3d.geometry.PointCloud(timed("Vector3dVector(float64)", o3d.utility.Vector3dVector, local))
view = np.asarray(pcd.points)
print("  np.asarray(pcd.points) shares with numpy input:", np.shares_memory(view, local),
      "| repeat np.asarray -> same buffer:", np.shares_memory(view, np.asarray(pcd.points)))

print("== Open3D legacy -> PyVista")
poly = pv.PolyData(view)                         # deep=False
print("  PolyData(np.asarray(pcd.points)) shares Open3D buffer:", np.shares_memory(poly.points, view))
# lifetime: drop every Open3D reference, keep only the PyVista object
ref0 = poly.points[0].copy()
del pcd, view; gc.collect()
_junk = [np.random.rand(1000, 3) for _ in range(200)]
print("  after deleting the Open3D PointCloud, PolyData point[0] unchanged:", np.allclose(poly.points[0], ref0))

print("== trimesh.PointCloud on one cluster (a pole)")
pp = local[cls == 1]
pole = np.ascontiguousarray(pp[pp[:, 0] < pp[:, 0].min() + 1.0])   # left-most pole only
tpc = trimesh.PointCloud(pole)
print("  vertices type", type(tpc.vertices).__name__, tpc.vertices.dtype, "| shares memory with input:",
      np.shares_memory(tpc.vertices, pole))
hull = timed("convex_hull (SciPy/Qhull)", lambda: tpc.convex_hull)
obb = timed("bounding_box_oriented", lambda: tpc.bounding_box_oriented)
print("  OBB type", type(obb).__name__, "extents", np.round(obb.primitive.extents, 3))
print("  hull type", type(hull).__name__, "faces", len(hull.faces), "watertight", hull.is_watertight,
      "volume m^3", round(hull.volume, 4))
print("  extents (AABB):", np.round(tpc.extents, 3))

print("== trimesh <-> Open3D TriangleMesh")
box = trimesh.creation.box(extents=(2, 1, 1))
big = trimesh.creation.icosphere(subdivisions=7)          # ~ 330k faces
print("  icosphere faces dtype", big.faces.dtype, big.faces.shape, "| vertices dtype", big.vertices.dtype)
fi64 = np.asarray(big.faces)
tri_slow = timed("Vector3iVector(int64 faces)", o3d.utility.Vector3iVector, fi64)
tri_fast = timed("Vector3iVector(int32 faces)", o3d.utility.Vector3iVector, fi64.astype(np.int32))
om = o3d.geometry.TriangleMesh(o3d.utility.Vector3dVector(np.asarray(big.vertices)), tri_fast)
print("  Open3D mesh: vertices", len(om.vertices), "triangles", len(om.triangles),
      "| np.asarray(triangles).dtype", np.asarray(om.triangles).dtype)
back = trimesh.Trimesh(np.asarray(om.vertices), np.asarray(om.triangles), process=False)
print("  back to trimesh (process=False): faces", len(back.faces), "dtype", back.faces.dtype)
merged = trimesh.Trimesh(np.asarray(om.vertices), np.asarray(om.triangles))  # process=True default merges vertices
print("  trimesh default process=True: vertices", len(merged.vertices), "vs", len(om.vertices))

print("== trimesh / Open3D mesh -> PyVista")
w = pv.wrap(box)
print("  pv.wrap(trimesh.Trimesh) ->", type(w).__name__, "n_cells", w.n_cells)
pm = pv.PolyData.from_regular_faces(np.asarray(om.vertices), np.asarray(om.triangles))
print("  PolyData.from_regular_faces(o3d verts, tris) ->", pm.n_points, pm.n_cells)
