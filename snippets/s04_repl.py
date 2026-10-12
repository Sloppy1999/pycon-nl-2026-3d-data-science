"""Slide 4: a point cloud is just an N x 3 array. Writes the REPL transcript snippets/s04_repl.txt.

The slide region holds the statements. This script runs them one by one the way the interactive
interpreter does (compile in "single" mode, so expression values are echoed with repr) and writes
">>> statement" lines followed by the real output. The deck shows s04_repl.txt (lexer: pycon).
The output of `las.xyz.shape`, the line that carries the slide's idea, ends in the key-line marker "  # <<"
(the deck strips it and highlights the line); the width check runs on the lines without the marker.
"""

import contextlib
import io
from pathlib import Path

from _setup import KEY, SNIPPETS, check, pipeline_json, slide_region

# --- slide ---
import laspy
las = laspy.read("crop.laz")
las.xyz.shape
las.classification[:5]
# --- end ---

ns: dict = {}
transcript = []
for stmt in slide_region(__file__):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        exec(compile(stmt, "<stdin>", "single"), ns)
    transcript.append(">>> " + stmt)
    transcript += buf.getvalue().splitlines()
key_at = transcript.index(">>> las.xyz.shape") + 1   # its output line, (N, 3)
transcript[key_at] += KEY
shown = [ln[: -len(KEY)] if ln.endswith(KEY) else ln for ln in transcript]
out = SNIPPETS / "s04_repl.txt"
out.write_text("\n".join(transcript) + "\n")
print("\n".join(transcript))
check(len(shown) <= 6, f"{len(shown)} transcript lines")
check(max(map(len, shown)) <= 35, f"widest line {max(map(len, shown))} characters (key-line marker stripped)")
check(shown[key_at] == repr(ns["las"].xyz.shape), f"key line {key_at + 1} is the shape output")
pj = pipeline_json()
if pj is not None:
    check(ns["las"].xyz.shape == (pj["points_in"], 3), f"shape ({pj['points_in']}, 3) = pipeline.json points_in")
check(Path(out).read_text().splitlines() == transcript, f"wrote {out.name}")
