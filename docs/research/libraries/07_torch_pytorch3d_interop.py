"""numpy -> torch -> PyTorch3D, and Open3D tensor <-> torch via DLPack.
Runs in libraries/pt3d-venv (torch 2.14.1+cpu, pytorch3d 0.7.9 built from source with a -std=c++20 patch)."""
import sys
import time
from pathlib import Path

import numpy as np
import torch
import laspy
import open3d as o3d
import open3d.core as o3c
import pytorch3d
from pytorch3d.structures import Pointclouds
from pytorch3d.ops import knn_points, sample_farthest_points
from scipy.spatial import KDTree

print("python", sys.version.split()[0], "| torch", torch.__version__, "| pytorch3d", pytorch3d.__version__,
      "| open3d", o3d.__version__, "| torch.cuda.is_available()", torch.cuda.is_available())
OUT = Path(__file__).with_name("out")
las = laspy.read(OUT / "street.laz")
local = np.ascontiguousarray(las.xyz - las.xyz.min(axis=0))

print("== numpy -> torch")
t64 = torch.from_numpy(local)
print("  torch.from_numpy shares memory:", t64.data_ptr() == local.ctypes.data, "| dtype", t64.dtype)
t32 = t64.float()
print("  .float() (f64->f32) is a copy:", t32.data_ptr() != t64.data_ptr())
try:
    torch.from_numpy(las.xyz)          # F-order
    print("  from_numpy(F-order) accepted; is_contiguous:", torch.from_numpy(las.xyz).is_contiguous())
except Exception as e:
    print("  from_numpy(F-order) ERROR", type(e).__name__, str(e)[:120])
print("  torch.as_tensor(np, dtype=float32) is a copy:", torch.as_tensor(local, dtype=torch.float32).data_ptr() != local.ctypes.data)

print("== PyTorch3D Pointclouds")
pc = Pointclouds(points=[t32])
print("  points_list()[0] shares memory with input tensor:", pc.points_list()[0].data_ptr() == t32.data_ptr())
print("  points_padded() shape", tuple(pc.points_padded().shape), "dtype", pc.points_padded().dtype)
pc64 = Pointclouds(points=[t64[:1000]])
print("  float64 input accepted, dtype kept:", pc64.points_padded().dtype)

print("== knn_points (CPU) vs SciPy KDTree on 100k pts, k=8")
sub = t32[::10].unsqueeze(0).contiguous()
t0 = time.perf_counter(); r = knn_points(sub, sub, K=8); t_p3d = time.perf_counter() - t0
t0 = time.perf_counter(); d_sp, i_sp = KDTree(local[::10]).query(local[::10], k=8, workers=-1); t_sp = time.perf_counter() - t0
print(f"  pytorch3d.knn_points CPU: {t_p3d*1000:.0f} ms | scipy KDTree build+query workers=-1: {t_sp*1000:.0f} ms")
print("  knn_points returns", type(r).__name__, "fields", r._fields, "| dists are SQUARED:",
      np.allclose(r.dists[0].sqrt().numpy(), d_sp, atol=1e-3))
fps, idx = sample_farthest_points(sub[:, :20000], K=1024)
print("  sample_farthest_points ->", tuple(fps.shape), tuple(idx.shape))

print("== Open3D tensor <-> torch via DLPack")
ot = o3c.Tensor.from_numpy(local)
tt = torch.utils.dlpack.from_dlpack(ot.to_dlpack())
print("  o3c -> torch via to_dlpack() shares memory:", tt.data_ptr() == local.ctypes.data)
try:
    tt2 = torch.from_dlpack(ot)
    print("  torch.from_dlpack(o3c.Tensor) (protocol) works, shares:", tt2.data_ptr() == local.ctypes.data)
except Exception as e:
    print("  torch.from_dlpack(o3c.Tensor) ERROR", type(e).__name__, str(e)[:150])
back = o3c.Tensor.from_dlpack(torch.utils.dlpack.to_dlpack(t32))
print("  torch -> o3c via from_dlpack shares memory:", np.shares_memory(back.numpy(), t32.numpy()))
