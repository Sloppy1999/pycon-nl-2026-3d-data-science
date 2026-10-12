"""laspy 2.7.0 API check on synthetic data: create/write LAS+LAZ, read, chunked read, xyz vs X/x.

Synthetic street-like scene with RD-New/UTM-like coordinates (x~155000, y~463000).
"""
import os
import time
import warnings
from pathlib import Path

import numpy as np
import laspy

warnings.simplefilter("always")
OUT = Path(__file__).with_name("out")
OUT.mkdir(exist_ok=True)
rng = np.random.default_rng(42)


def synthetic_street(n=1_000_000):
    """Ground plane + two building facades + a few 'trees' (blobs) + poles."""
    n_ground = int(n * 0.55)
    n_fac = int(n * 0.25)
    n_tree = int(n * 0.15)
    n_pole = n - n_ground - n_fac - n_tree
    g = np.c_[rng.uniform(0, 100, n_ground), rng.uniform(0, 30, n_ground), rng.normal(0, 0.02, n_ground)]
    f1 = np.c_[rng.uniform(0, 100, n_fac // 2), np.full(n_fac // 2, 0.0) + rng.normal(0, 0.02, n_fac // 2), rng.uniform(0, 12, n_fac // 2)]
    f2 = np.c_[rng.uniform(0, 100, n_fac - n_fac // 2), np.full(n_fac - n_fac // 2, 30.0) + rng.normal(0, 0.02, n_fac - n_fac // 2), rng.uniform(0, 12, n_fac - n_fac // 2)]
    centers = np.c_[np.linspace(10, 90, 5), np.full(5, 6.0), np.full(5, 5.0)]
    t = centers[rng.integers(0, 5, n_tree)] + rng.normal(0, 1.5, (n_tree, 3))
    pc = np.c_[np.linspace(15, 85, 4), np.full(4, 24.0)]
    p = np.c_[pc[rng.integers(0, 4, n_pole)] + rng.normal(0, 0.05, (n_pole, 2)), rng.uniform(0, 6, n_pole)]
    xyz = np.vstack([g, f1, f2, t, p])
    cls = np.concatenate([np.full(n_ground, 2), np.full(n_fac, 6), np.full(n_tree, 5), np.full(n_pole, 1)]).astype(np.uint8)
    xyz += np.array([155000.0, 463000.0, 0.0])  # RD-New-like offset
    return xyz, cls


xyz, cls = synthetic_street()
print("synthetic xyz dtype", xyz.dtype, xyz.shape, "min", xyz.min(0), "max", xyz.max(0))

# --- create + write ---------------------------------------------------------------
header = laspy.LasHeader(point_format=3, version="1.2")
header.offsets = np.floor(xyz.min(axis=0))
header.scales = np.array([0.001, 0.001, 0.001])
las = laspy.LasData(header)
las.x, las.y, las.z = xyz[:, 0], xyz[:, 1], xyz[:, 2]
las.classification = cls
las.intensity = rng.integers(0, 65535, len(xyz), dtype=np.uint16)

las_path, laz_path = OUT / "street.las", OUT / "street.laz"
t0 = time.perf_counter(); las.write(las_path); t_las = time.perf_counter() - t0
t0 = time.perf_counter(); las.write(laz_path, laz_backend=laspy.LazBackend.Lazrs); t_laz = time.perf_counter() - t0
print(f"write LAS {t_las:.2f}s {os.path.getsize(las_path)/1e6:.1f} MB | LAZ(lazrs) {t_laz:.2f}s {os.path.getsize(laz_path)/1e6:.1f} MB")
# note: do_compress is inferred from the .laz suffix when do_compress=None

# --- read ------------------------------------------------------------------------
t0 = time.perf_counter(); r = laspy.read(laz_path); t_read = time.perf_counter() - t0
print(f"laspy.read(LAZ) {t_read:.2f}s, type {type(r).__name__}, n={len(r.points)}, point_format={r.header.point_format.id}")
print("dimension names:", list(r.point_format.dimension_names)[:20])
print("type(r.X)", type(r.X).__name__, r.X.dtype, "| type(r.x)", type(r.x).__name__, getattr(r.x, "dtype", None))
xyz_r = r.xyz
print("type(r.xyz)", type(xyz_r).__name__, xyz_r.dtype, xyz_r.shape, "C-contig", xyz_r.flags["C_CONTIGUOUS"])
print("r.xyz is fresh copy each access:", r.xyz is not r.xyz, "shares memory w/ points:",
      np.shares_memory(xyz_r, r.points.array))
print("max |roundtrip error| (m):", np.abs(xyz_r - xyz).max(), "(scale 0.001 => <= 0.0005 expected)")
print("raw X int, scale, offset:", r.X[:2], r.header.scales, r.header.offsets)
print("classification dtype/type", type(r.classification).__name__, np.asarray(r.classification).dtype,
      np.unique(np.asarray(r.classification)))

# float32 precision with big coordinates
x32 = xyz[:, 0].astype(np.float32)
print("float32 spacing at 155000:", np.spacing(np.float32(155000.0)), " at 463000:", np.spacing(np.float32(463000.0)))
print("max |x - float32(x)| (m):", np.abs(x32.astype(np.float64) - xyz[:, 0]).max(),
      "| y:", np.abs(xyz[:, 1].astype(np.float32).astype(np.float64) - xyz[:, 1]).max())
local = xyz - xyz.min(axis=0)
print("after subtracting min, max |err| float32 (m):", np.abs(local.astype(np.float32).astype(np.float64) - local).max())

# --- chunked read ------------------------------------------------------------------
t0 = time.perf_counter()
n_total, bb_min = 0, np.full(3, np.inf)
with laspy.open(laz_path) as f:
    print("header-only: point_count", f.header.point_count, "mins", f.header.mins, "maxs", f.header.maxs)
    for chunk in f.chunk_iterator(250_000):
        n_total += len(chunk)
        bb_min = np.minimum(bb_min, chunk.xyz.min(axis=0)) if hasattr(chunk, "xyz") else bb_min
        ctype = type(chunk).__name__
print(f"chunk_iterator(250_000): chunk type {ctype}, total {n_total}, {time.perf_counter()-t0:.2f}s, has .xyz: {hasattr(chunk,'xyz')}")

# --- writing chunked (streaming) ---------------------------------------------------
with laspy.open(laz_path) as src, laspy.open(OUT / "ground_only.laz", mode="w", header=src.header) as dst:
    for chunk in src.chunk_iterator(250_000):
        dst.write_points(chunk[np.asarray(chunk.classification) == 2])
g = laspy.read(OUT / "ground_only.laz")
print("streamed ground-only LAZ points:", len(g.points))

# --- memory of xyz vs record ------------------------------------------------------
print("point record bytes/pt:", r.points.array.itemsize, "| xyz float64 bytes/pt: 24")
