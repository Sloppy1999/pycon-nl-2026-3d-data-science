"""Slide 12 joke: the Zen of Python line "Flat is better than nested.", spoken (the on-slide callout was dropped).

Checks that the line the notes quote is, verbatim, one line of the Zen of Python as `import this` prints it.
"""

import contextlib
import io

buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    # --- slide ---
    import this
    # --- end ---

zen = buf.getvalue().splitlines()
line = "Flat is better than nested."  # quoted in deck/notes.yaml slide 13
assert line in zen, f"{line!r} is not a line of the Zen of Python"
assert this.s  # the module's rot13 source text
print(f"ok: {line!r} is line {zen.index(line) + 1} of `import this`")
