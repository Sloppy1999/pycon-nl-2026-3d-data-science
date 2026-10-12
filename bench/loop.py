"""The slide-16 loop and expression as two functions, for profiling (Profile slide).

    cd bench && uv run python -m cProfile -s tottime loop.py

bench/profile_loop.py runs exactly that command and stores the output (results/profile_loop.txt and .json).
The function bodies are the slide regions of snippets/s16_loop.py and snippets/s16_vec.py, read and compiled
verbatim (so the profile is of the exact code on the slide, under the file name of its snippet); the data and
the points are set up as in those snippets (AHN5 crop, local origin). The plane is the one those snippets fit
(seeded segment_plane, probability 1.0), read from results/bench_cliff.json plane.coefficients, so the profile
shows the loop and not RANSAC.
"""

import json

import laspy
import numpy as np

from _common import DATA_CROP, RESULTS, SNIPPETS, region_function


loop, _ = region_function(SNIPPETS / "s16_loop.py", ("P", "plane"), "h", name="loop")
vectorised, _ = region_function(SNIPPETS / "s16_vec.py", ("P", "plane"), "h", name="vectorised")

las = laspy.read(DATA_CROP)
P = las.xyz - las.header.mins  # local origin, as on slide 8
bench = json.loads((RESULTS / "bench_cliff.json").read_text())
plane = tuple(float(v) for v in bench["plane"]["coefficients"])

h_loop = loop(P, plane)
h_vec = vectorised(P, plane)
assert np.array_equal(h_loop, h_vec), "loop and expression differ"
print(f"{len(P)} points; np.array_equal(loop, vectorised): True")
