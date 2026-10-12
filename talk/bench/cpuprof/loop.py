"""Scalene target (CPU): the slide-19 loop and the one-expression version, line for line, repeated.

    uv run --group profile scalene run --cpu-only -o OUT.json bench/cpuprof/loop.py --- [REPEATS]

The bodies of `loop` and `vectorised` are the slide lines of snippets/s16_loop.py and snippets/s16_vec.py (indented
into a function, as bench/loop.py does; the check at the end fails if they drift). The data and the plane are set up
as in bench/loop.py. Both functions run REPEATS times (default 10) so that Scalene, which samples every 10 ms,
gets enough samples on the 0.4 s loop. The directory must not have "scalene" in its path (Scalene skips such files).
"""
import json
import sys
import textwrap
from pathlib import Path

import laspy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common import DATA_CROP, RESULTS, SNIPPETS, slide_lines  # noqa: E402


def loop(P, plane):
    a, b, c, d = plane
    h = np.empty(len(P))  # distances
    for i, p in enumerate(P):  # <<
        x, y, z = p[0], p[1], p[2]
        h[i] = abs(a*x + b*y + c*z + d)
    return h


def vectorised(P, plane):
    a, b, c, d = plane
    x, y, z = P.T  # columns, no copy
    h = np.abs(a*x + b*y + c*z + d)  # <<
    return h


def _body(fn_name):
    src = Path(__file__).read_text().splitlines()
    i = src.index(f"def {fn_name}(P, plane):")
    j = next(k for k in range(i + 1, len(src)) if src[k].strip() == "return h")
    return [s.removesuffix("  # <<") for s in textwrap.dedent("\n".join(src[i + 1:j])).splitlines()]


assert _body("loop") == slide_lines(SNIPPETS / "s16_loop.py"), "loop drifted from snippets/s16_loop.py"
assert _body("vectorised") == slide_lines(SNIPPETS / "s16_vec.py"), "vectorised drifted from snippets/s16_vec.py"

repeats = int(sys.argv[1]) if len(sys.argv) > 1 else 10
las = laspy.read(DATA_CROP, laz_backend=laspy.LazBackend.Lazrs)
P = las.xyz - las.header.mins
plane = tuple(float(v) for v in json.loads((RESULTS / "bench_cliff.json").read_text())["plane"]["coefficients"])
for _ in range(repeats):
    h_loop = loop(P, plane)
    h_vec = vectorised(P, plane)
assert np.array_equal(h_loop, h_vec), "loop and expression differ"
print(f"{len(P)} points; {repeats} repeats; np.array_equal(loop, vectorised): True")
