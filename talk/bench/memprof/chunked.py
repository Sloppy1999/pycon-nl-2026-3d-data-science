"""Scalene target: the chunked loop of slide 25 (snippets/s21_chunked.py), line for line.

    uv run scalene run -o OUT.json bench/memprof/chunked.py --- [crop|tile|FILE]

Scalene's memory mode hangs inside laspy's parallel LAZ decoder (LazrsParallel, rayon threads), so laspy is told to
use the single-threaded Lazrs backend here. The slide lines are unchanged; the check below fails if they drift.
"""
import functools
import sys
from pathlib import Path

import laspy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common import DATA_CROP, DATA_TILE, SNIPPETS, slide_lines  # noqa: E402

laspy.open = functools.partial(laspy.open, laz_backend=laspy.LazBackend.Lazrs)
arg = sys.argv[1] if len(sys.argv) > 1 else "tile"
path = {"crop": DATA_CROP, "tile": DATA_TILE}.get(arg, Path(arg))

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

src = Path(__file__).read_text().splitlines()
a, b = src.index("# --- slide ---"), src.index("# --- end ---")
body = [s[:-6] if s.endswith("  # <<") else s for s in src[a + 1:b]]
assert body == slide_lines(SNIPPETS / "s21_chunked.py"), "slide lines drifted from snippets/s21_chunked.py"
print(f"{len(points)} points kept")
