"""Extra checks: legacy vs tensor voxel grid alignment, Vector3dVector dtype slow path (repeated), o3d.io on LAZ."""
import time, warnings
from pathlib import Path
import numpy as np, laspy, open3d as o3d
warnings.simplefilter("always")
OUT = Path(__file__).with_name("out")
las = laspy.read(OUT / "street.laz")
local = np.ascontiguousarray(las.xyz - las.xyz.min(axis=0))
v = 0.10
leg = o3d.geometry.PointCloud(o3d.utility.Vector3dVector(local)).voxel_down_sample(v)
ten = o3d.t.geometry.PointCloud(o3d.core.Tensor.from_numpy(local)).voxel_down_sample(v)
mn = local.min(axis=0)
n_grid_min_half = len(np.unique(np.floor((local - (mn - v / 2)) / v).astype(np.int64), axis=0))
n_grid_origin = len(np.unique(np.floor(local / v).astype(np.int64), axis=0))
print(f"voxel {v}: legacy {len(leg.points)} | tensor {ten.point.positions.shape[0]} | numpy grid anchored at min-v/2 {n_grid_min_half} | numpy grid anchored at 0 {n_grid_origin}")
shift = local + np.array([0.05, 0.05, 0.05])
ten_s = o3d.t.geometry.PointCloud(o3d.core.Tensor.from_numpy(shift)).voxel_down_sample(v)
leg_s = o3d.geometry.PointCloud(o3d.utility.Vector3dVector(shift)).voxel_down_sample(v)
print(f"after shifting cloud by +5 cm: legacy {len(leg_s.points)} (translation-invariant) | tensor {ten_s.point.positions.shape[0]}")

for dt in (np.float64, np.float32):
    a = local.astype(dt)
    ts = []
    for _ in range(3):
        t0 = time.perf_counter(); o3d.utility.Vector3dVector(a); ts.append(time.perf_counter() - t0)
    print(f"Vector3dVector({np.dtype(dt).name}, 1M) best of 3: {min(ts)*1000:.1f} ms")
t0 = time.perf_counter(); o3d.utility.Vector3dVector(local.astype(np.float32).astype(np.float64)); print(f"  float32 -> .astype(float64) first: {(time.perf_counter()-t0)*1000:.1f} ms")

for ext in ("laz", "las"):
    p = o3d.io.read_point_cloud(str(OUT / f"street.{ext}"))
    print(f"o3d.io.read_point_cloud(street.{ext}) -> {len(p.points)} points")
t = o3d.t.io.read_point_cloud(str(OUT / "street.laz"))
print("o3d.t.io.read_point_cloud(street.laz) ->", t.point.positions.shape if "positions" in t.point else "no positions")
