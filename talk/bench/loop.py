"""The slide-16 loop and expression as two functions, for profiling (Profile slide).

    cd talk/bench && uv run python -m cProfile -s tottime loop.py

bench/profile_loop.py runs exactly that command and stores the output (results/profile_loop.txt and .json).
The function bodies are the slide regions of snippets/s16_loop.py and snippets/s16_vec.py, read and compiled
verbatim (so the profile is of the exact code on the slide, under the file name of its snippet); the data and
the points are set up as in those snippets (AHN5 crop, local origin). The plane is the one those snippets fit
(seeded segment_plane, probability 1.0), read from results/bench_cliff.json plane.coefficients, so the profile
shows the loop and not RANSAC.
"""

import json
import textwrap
from pathlib import Path

import laspy
import numpy as np

TALK = Path(__file__).resolve().parents[1]
SNIPPETS = TALK / "snippets"


def region(name):
    lines = (SNIPPETS / name).read_text().splitlines()
    i, j = lines.index("# --- slide ---"), lines.index("# --- end ---")
    return "\n".join(ln.removesuffix("  # <<") for ln in lines[i + 1:j]) + "\n"


def compile_fn(name, snippet, result="h"):
    code = f"def {name}(P, plane):\n{textwrap.indent(region(snippet), '    ')}    return {result}\n"
    ns = {"np": np}
    exec(compile(code, f"snippets/{snippet}", "exec"), ns)
    return ns[name]


loop = compile_fn("loop", "s16_loop.py")
vectorised = compile_fn("vectorised", "s16_vec.py")

las = laspy.read(TALK / "data" / "utrecht_jaarbeurs_200m.laz")
P = las.xyz - las.header.mins  # local origin, as on slide 8
bench = json.loads((TALK / "results" / "bench_cliff.json").read_text())
plane = tuple(float(v) for v in bench["plane"]["coefficients"])

h_loop = loop(P, plane)
h_vec = vectorised(P, plane)
assert np.array_equal(h_loop, h_vec), "loop and expression differ"
print(f"{len(P)} points; np.array_equal(loop, vectorised): True")
