"""Open3D 0.20.0 tensor API (o3d.t.geometry.PointCloud): memory sharing, dtype, CUDA availability in the PyPI wheel."""
import time
from pathlib import Path

import numpy as np
import laspy
import open3d as o3d
import open3d.core as o3c

OUT = Path(__file__).with_name("out")
las = laspy.read(OUT / "street.laz")
xyz = np.ascontiguousarray(las.xyz)
local = xyz - xyz.min(axis=0)

print("open3d", o3d.__version__, "| cuda.is_available:", o3c.cuda.is_available(), "| device_count:", o3c.cuda.device_count())

# --- numpy <-> o3c.Tensor ---------------------------------------------------------
tens = o3c.Tensor.from_numpy(local)
back = tens.numpy()
print("Tensor.from_numpy dtype", tens.dtype, "| shares memory numpy->Tensor->numpy:", np.shares_memory(back, local))
tens_ctor = o3c.Tensor(local)
print("o3c.Tensor(ndarray) shares memory:", np.shares_memory(tens_ctor.numpy(), local))
try:
    o3c.Tensor.from_numpy(las.xyz)  # F-order
    print("from_numpy(F-order) accepted")
except Exception as e:
    print("from_numpy(F-order) ERROR:", type(e).__name__, str(e)[:160])

# --- t.geometry.PointCloud ----------------------------------------------------------
tp = o3d.t.geometry.PointCloud(tens)
pos = tp.point.positions
print("t.PointCloud(Tensor) positions dtype", pos.dtype, "| shares memory with numpy input:",
      np.shares_memory(pos.numpy(), local))
tp.point.classification = o3c.Tensor.from_numpy(np.asarray(las.classification).astype(np.int32).reshape(-1, 1))
print("custom attribute ok:", "classification" in tp.point)

legacy = o3d.geometry.PointCloud(o3d.utility.Vector3dVector(xyz))
tl = o3d.t.geometry.PointCloud.from_legacy(legacy)
print("from_legacy default dtype:", tl.point.positions.dtype,
      "| max abs err on RD coords (m):", np.abs(tl.point.positions.numpy().astype(np.float64) - xyz).max())
tl64 = o3d.t.geometry.PointCloud.from_legacy(legacy, o3c.float64)
print("from_legacy(float64) max abs err:", np.abs(tl64.point.positions.numpy() - xyz).max())

# --- ops on CPU ---------------------------------------------------------------------
def t(label, fn, *a, **k):
    t0 = time.perf_counter(); r = fn(*a, **k); dt = time.perf_counter() - t0
    print(f"  {label}: {dt*1000:.1f} ms"); return r

tp32 = o3d.t.geometry.PointCloud(o3c.Tensor.from_numpy(local.astype(np.float32)))
d = t("t.voxel_down_sample(0.10) CPU f32", tp32.voxel_down_sample, 0.10)
print("  n", d.point.positions.shape[0])
o3d.utility.random.seed(42)
plane, inl = t("t.segment_plane(0.05,3,1000) CPU", tp32.segment_plane, 0.05, 3, 1000)
print("  returns", type(plane).__name__, plane.shape, plane.dtype, "|", type(inl).__name__, inl.shape, inl.dtype)
lab = t("t.cluster_dbscan(0.5,10) on downsample", d.cluster_dbscan, 0.5, 10)
print("  labels", lab.dtype, lab.shape, "clusters", int(lab.max().item()) + 1)

# --- CUDA -----------------------------------------------------------------------------
if o3c.cuda.is_available():
    dev = o3c.Device("CUDA:0")
    tpg = tp32.to(dev)
    o3c.cuda.synchronize()
    dg = t("t.voxel_down_sample(0.10) CUDA (incl. first-call warm-up)", tpg.voxel_down_sample, 0.10); o3c.cuda.synchronize()
    dg = t("t.voxel_down_sample(0.10) CUDA (2nd call)", tpg.voxel_down_sample, 0.10); o3c.cuda.synchronize()
    print("  CUDA voxel count", dg.point.positions.shape[0], "| CPU count", d.point.positions.shape[0])
    plane_g, inl_g = t("t.segment_plane on CUDA tensor", tpg.segment_plane, 0.05, 3, 1000)
    print("  segment_plane result device:", plane_g.device, inl_g.device)
    labg = t("t.cluster_dbscan on CUDA tensor", dg.cluster_dbscan, 0.5, 10)
    print("  dbscan result device:", labg.device)
    try:
        print("  .numpy() on CUDA tensor:", tpg.point.positions.numpy().shape)
    except Exception as e:
        print("  .numpy() on CUDA tensor ERROR:", type(e).__name__, str(e)[:160])
    print("  .cpu().numpy() ok:", tpg.point.positions.cpu().numpy().shape)
