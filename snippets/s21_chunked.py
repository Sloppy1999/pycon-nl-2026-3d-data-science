"""Slide 21 (full width): stream a LAZ file in chunks and keep the first point per 0.5 m voxel.

Standalone:   uv run python snippets/s21_chunked.py            # the AHN5 crop (default)
              uv run python snippets/s21_chunked.py tile       # the 1 km AHN5 tile
              uv run python snippets/s21_chunked.py FILE.laz
After the slide lines the script checks the result against a load-everything reference that keeps the
first point per voxel in file order (independent grouping: stable lexsort on the integer voxel index).
bench/bench_memory.py measures the peak memory of exactly the slide lines.
"""

import sys
import time
from pathlib import Path

import laspy
import numpy as np

DATA = Path(__file__).resolve().parents[1] / "data"
arg = sys.argv[1] if len(sys.argv) > 1 else "crop"
path = {"crop": DATA / "utrecht_jaarbeurs_200m.laz",
        "tile": DATA / "AHN5_C_135000_455000.COPC.LAZ"}.get(arg, Path(arg))


def reference(path, v):
    """Load everything, then keep the first point (in file order) of every voxel, sorted by (i, j, k)."""
    las = laspy.read(path)
    xyz = las.xyz - las.header.mins
    ijk = (xyz // v).astype(np.int64)
    order = np.lexsort(ijk.T[::-1])  # stable: i, then j, then k; ties keep file order
    s = ijk[order]
    new = np.ones(len(s), bool)
    new[1:] = (s[1:] != s[:-1]).any(axis=1)
    return xyz[order[new]]


t0 = time.perf_counter()
# --- slide ---
v, keys, pts = 0.5, [], []                      # voxel size: 0.5 m
with laspy.open(path) as f:
    lo, hi = f.header.mins, f.header.maxs       # local origin, extent
    dims = ((hi - lo) // v).astype(np.int64) + 1  # voxels per axis
    for c in f.chunk_iterator(1_000_000):       # a million points  # <<
        xyz = np.c_[c.x, c.y, c.z] - lo
        ijk = (xyz // v).astype(np.int64).T     # voxel index per axis
        key = np.ravel_multi_index(ijk, dims)   # one int64 per voxel
        k, first = np.unique(key, return_index=True)
        keys.append(k); pts.append(xyz[first])  # first per voxel
k, first = np.unique(np.concatenate(keys), return_index=True)
points = np.concatenate(pts)[first]             # earliest chunk wins
# --- end ---
seconds = time.perf_counter() - t0

ref = reference(path, v)
same = np.array_equal(points, ref)
with laspy.open(path) as f:
    n = f.header.point_count
print(f"{Path(path).name}: {n} points in, {len(points)} kept at {v} m "
      f"({len(keys)} chunks, {seconds:.1f} s); equals the load-everything reference: {same}")
assert same, "chunked result differs from the load-everything reference"
