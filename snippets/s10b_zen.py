"""Slide 12 callout: `>>> import this` and the Zen of Python line "Flat is better than nested."

Checks that the callout's second line (deck/content.yaml slide 12 callout.lines) is, verbatim, one line of the
Zen of Python as `import this` prints it.
"""

import contextlib
import io
from pathlib import Path

import yaml

buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    # --- slide ---
    import this
    # --- end ---

zen = buf.getvalue().splitlines()
content = yaml.safe_load((Path(__file__).resolve().parents[1] / "deck" / "content.yaml").read_text())
callout = next(s["callout"] for s in content["slides"] if s.get("callout"))
line = callout["lines"][1]
assert line in zen, f"{line!r} is not a line of the Zen of Python"
assert this.s  # the module's rot13 source text
print(f"ok: {line!r} is line {zen.index(line) + 1} of `import this`")
