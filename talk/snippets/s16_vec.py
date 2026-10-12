"""Slide 16, right column: the same distances as one element-wise NumPy expression.

Standalone on the AHN5 crop:   uv run python snippets/s16_vec.py [file.laz]
Deliberately element-wise and in the same operation order as snippets/s16_loop.py, so the results are
bit-identical. `P @ (a, b, c) + d` is NOT used: its summation order differs and the last bit can change.
"""

import sys
from pathlib import Path

import laspy
import numpy as np
import open3d as o3d

o3d.utility.set_verbosity_level(o3d.utility.VerbosityLevel.Error)
DATA = Path(__file__).resolve().parents[1] / "data" / "utrecht_jaarbeurs_200m.laz"
las = laspy.read(sys.argv[1] if len(sys.argv) > 1 else DATA)
P = las.xyz - las.header.mins  # local origin, as on slide 8
pcd = o3d.geometry.PointCloud(o3d.utility.Vector3dVector(P))
o3d.utility.random.seed(0)  # seeded RANSAC, probability=1.0: same plane every run
coeffs, _ = pcd.segment_plane(0.3, 3, 1000, 1.0)
plane = tuple(float(v) for v in coeffs)

# --- slide ---
a, b, c, d = plane
x, y, z = P.T  # columns, no copy
h = np.abs(a*x + b*y + c*z + d)  # <<
# --- end ---

assert np.shares_memory(x, P), "P.T unpacking copied the data"
loop = np.array([abs(a*p[0] + b*p[1] + c*p[2] + d) for p in P])
same = np.array_equal(h, loop)
assert same, "the NumPy expression and the loop differ"
print(f"{len(h)} distances; np.array_equal with the loop over rows: {same}")
