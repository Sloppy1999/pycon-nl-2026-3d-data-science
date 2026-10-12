"""segment_plane reproducibility vs `probability` (early-termination) and thread count, Open3D 0.20.0 legacy API."""
import os
from pathlib import Path
import numpy as np, laspy, open3d as o3d
OUT = Path(__file__).with_name("out")
las = laspy.read(OUT / "street.laz")
pcd = o3d.geometry.PointCloud(o3d.utility.Vector3dVector(np.ascontiguousarray(las.xyz - las.xyz.min(axis=0))))
for prob in (0.99999999, 1.0):
    res = set()
    for _ in range(10):
        o3d.utility.random.seed(42)
        m, inl = pcd.segment_plane(0.05, 3, 1000, probability=prob)
        res.add(len(inl))
    print(f"OMP_NUM_THREADS={os.environ.get('OMP_NUM_THREADS','unset')} probability={prob}: distinct inlier counts over 10 seeded runs: {len(res)} {sorted(res)}")
import time
for prob in (0.99999999, 1.0):
    ts = []
    for _ in range(5):
        o3d.utility.random.seed(42); t0 = time.perf_counter(); pcd.segment_plane(0.05, 3, 1000, probability=prob); ts.append(time.perf_counter() - t0)
    print(f"probability={prob}: median time {np.median(ts)*1000:.0f} ms (5 runs)")
res = {len(pcd.segment_plane(0.05, 3, 1000, probability=1.0)[1]) for _ in range(5)}
print("probability=1.0 WITHOUT reseeding, 5 runs distinct:", len(res))
