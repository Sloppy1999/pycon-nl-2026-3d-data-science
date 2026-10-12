"""Slide 16, left column: a Python loop over NumPy rows (distance of every point to one plane).

Standalone on the AHN5 crop:   uv run python snippets/s16_loop.py [file.laz]
The deck shows only the lines between the slide markers. bench/bench_cliff.py times exactly those lines
(compiled as a function body) against snippets/s16_vec.py and asserts np.array_equal.
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
h = np.empty(len(P))  # distances
for i, p in enumerate(P):  # <<
    x, y, z = p[0], p[1], p[2]
    h[i] = abs(a*x + b*y + c*z + d)
# --- end ---

x, y, z = P.T
same = np.array_equal(h, np.abs(a*x + b*y + c*z + d))
assert same, "the loop and the NumPy expression differ"
print(f"{len(h)} distances; np.array_equal with the one-expression version: {same}")
