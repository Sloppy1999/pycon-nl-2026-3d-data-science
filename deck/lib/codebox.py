"""Code boxes: snippet regions -> Pygments tokens -> coloured Fira Mono runs, plus the key-line bar.

Snippet contract (CONTRACTS.md): only lines between `# --- slide ---` and `# --- end ---` are shown
(`// --- slide ---` in .cpp files). A line ending in `  # <<` (or `  // <<`) is the key line; the
marker is stripped. For the REPL slide (lang pycon) the transcript `<stem>.txt` is shown.
"""

from __future__ import annotations

import textwrap
from dataclasses import dataclass, field
from pathlib import Path
import re

from pygments.lexers import BashLexer, BashSessionLexer, CppLexer, PythonConsoleLexer, PythonLexer, TextLexer
from pygments.token import Comment, Generic, Keyword, Operator, String

from .pptx_helpers import (add_run, add_textbox, end_para_size, mark_decorative, para_format,
                           rect, set_name)
from .style import COLOURS, MONO_ADVANCE_EM

START_RE = re.compile(r"^\s*(#|//)\s*-{3}\s*slide\s*-{3}\s*$")
END_RE = re.compile(r"^\s*(#|//)\s*-{3}\s*end\s*-{3}\s*$")
KEY_RE = re.compile(r"\s+(#|//)\s*<<\s*$")

CODE_PT = 18.0
LINE_PT = 21.0              # exact line pitch, 1.167 em (Fira Mono at 100 % is 1.2 em = 21.6 pt; 21 pt keeps ten
                            # lines plus support, small print and source inside the L7 text column, deck/build_deck.py)
CHAR_EM = MONO_ADVANCE_EM   # Fira Mono advance width, 0.600 em
INSET_L, INSET_T, INSET_R, INSET_B = 0.16, 0.05, 0.06, 0.05
HL_EDGE = 0.07             # blue left edge of the key-line bar (the bar itself is LIGHT; key lines are also bold)


@dataclass
class Snippet:
    name: str
    path: Path | None
    lines: list[str] = field(default_factory=list)
    key: int | None = None
    keys: list[int] = field(default_factory=list)
    ok: bool = False
    note: str = ""
    lang: str = "python"

    @property
    def max_len(self) -> int:
        return max((len(x) for x in self.lines), default=0)


def read_snippet(snippets_dir: Path, name: str, lang: str | None = None) -> Snippet:
    lang = lang or ("cpp" if name.endswith((".cpp", ".cc", ".hpp", ".h")) else "python")
    p = Path(snippets_dir) / name
    candidates = [p]
    if lang == "pycon":
        candidates = [p.with_suffix(".txt"), p]
    src = next((c for c in candidates if c.exists()), None)
    sn = Snippet(name=name, path=src, lang=lang)
    if src is None:
        sn.note = "missing: " + " or ".join(str(c.name) for c in candidates)
        return sn
    raw = src.read_text(encoding="utf-8").splitlines()
    region: list[str] = []
    inside, found = False, False
    for line in raw:
        if START_RE.match(line):
            inside, found = True, True
            continue
        if END_RE.match(line):
            inside = False
            continue
        if inside:
            region.append(line)
    if not found:
        region = list(raw)
        if src.suffix != ".txt":
            sn.note = "no '--- slide ---' markers: whole file shown"
    # strip key markers, dedent, trim blank edges
    keys = []
    clean = []
    for i, line in enumerate(region):
        if KEY_RE.search(line):
            keys.append(i)
            line = KEY_RE.sub("", line)
        clean.append(line.rstrip())
    text = textwrap.dedent("\n".join(clean))
    lines = text.split("\n")
    lead = 0
    while lead < len(lines) and not lines[lead].strip():
        lead += 1
    lines = lines[lead:]
    keys = [k - lead for k in keys if k - lead >= 0]
    while lines and not lines[-1].strip():
        lines.pop()
    sn.lines = lines
    sn.keys = [k for k in keys if k < len(lines)]
    sn.key = sn.keys[0] if sn.keys else None
    sn.ok = bool(lines)
    if not lines:
        sn.note = "empty slide region"
    return sn


def _lexer(lang: str):
    if lang == "cpp":
        return CppLexer(stripnl=False, ensurenl=False)
    if lang == "pycon":
        return PythonConsoleLexer(stripnl=False, ensurenl=False)
    if lang == "bash":                  # a shell command line (the slide 2 install line)
        return BashLexer(stripnl=False, ensurenl=False)
    if lang == "console":               # "$ command" plus its output (the profile slide)
        return BashSessionLexer(stripnl=False, ensurenl=False)
    if lang == "text":
        return TextLexer(stripnl=False, ensurenl=False)
    return PythonLexer(stripnl=False, ensurenl=False)


def _style_for(tok, muted: bool, dark: bool = False) -> tuple[str, bool, bool]:
    """(colour, bold, italic). Fira Mono has no italic, so nothing is set italic.
    On white: default ink, keywords navy bold, strings blue, comments and prompts slate (docs/DESIGN.md section 6).
    Muted code (the greyed C++ on slide 2): everything slate (7.2:1; grey is too light for text), no bold.
    On navy (the title slide joke): default white, keywords white bold, strings and comments sage."""
    kw = tok in Keyword or tok in Operator.Word
    if muted:
        return COLOURS["text_small"], False, False
    if dark:
        if tok in Comment or tok in Generic.Prompt or tok in String:
            return COLOURS["text_small_dark"], False, False
        return COLOURS["text_dark"], kw, False
    if tok in Comment or tok in Generic.Prompt:
        return COLOURS["text_small"], False, False
    if tok in String:
        return COLOURS["highlight"], False, False
    if kw:
        return COLOURS["title"], True, False
    return COLOURS["text"], False, False


def tokenize(lines: list[str], lang: str, muted: bool = False,
             dark: bool = False) -> list[list[tuple[str, str, bool, bool]]]:
    """Per line: [(text, colour, bold, italic), ...] with adjacent equal styles merged."""
    code = "\n".join(lines) + ("\n" if lang == "console" else "")   # the session lexer drops an unterminated last line
    out: list[list[tuple[str, str, bool, bool]]] = [[]]
    for tok, val in _lexer(lang).get_tokens(code):
        colour, bold, italic = _style_for(tok, muted, dark)
        parts = val.split("\n")
        for j, part in enumerate(parts):
            if j > 0:
                out.append([])
            if not part:
                continue
            cur = out[-1]
            if cur and cur[-1][1:] == (colour, bold, italic):
                cur[-1] = (cur[-1][0] + part, colour, bold, italic)
            else:
                cur.append((part, colour, bold, italic))
    while len(out) < len(lines):
        out.append([])
    return out[: len(lines)]


def code_width_in(max_chars: int, size: float = CODE_PT) -> float:
    return max_chars * CHAR_EM * size / 72 + INSET_L + INSET_R


def code_height_in(n_lines: int, line_pt: float = LINE_PT) -> float:
    return n_lines * line_pt / 72 + INSET_T + INSET_B


def add_code(slide, sn: Snippet, x: float, y: float, w: float, h: float, *, name: str,
             hl_name: str | None = None, muted: bool = False, size: float = CODE_PT,
             line_pt: float = LINE_PT, highlight: bool = True, dark: bool = False):
    """Key-line bar first (behind), then the code text box; key lines are set bold (Fira Mono Bold has the
    same advance width, so the width budget holds). Returns (code_box, hl_group|None)."""
    hl = None
    keys = sn.keys if highlight else []
    keys = keys[:1] if hl_name else keys          # Morph slides: one key line, named hl_name
    for n, k in enumerate(keys):
        top = y + INSET_T + k * line_pt / 72
        grp = slide.shapes.add_group_shape()
        bar = rect(grp, x, top, w, line_pt / 72, fill="tile")
        edge = rect(grp, x, top, HL_EDGE, line_pt / 72, fill="highlight")
        set_name(bar, "Key line bar")
        set_name(edge, "Key line edge")
        set_name(grp, hl_name if (hl_name and n == 0) else f"Key line {k + 1}")
        mark_decorative(grp)
        hl = grp if hl is None else hl
    tb = add_textbox(slide, x, y, w, h, name=name, wrap=False, anchor="t",
                     insets=(INSET_L, INSET_T, INSET_R, INSET_B), autofit="none")
    tf = tb.text_frame
    key_set = set(keys)
    for i, toks in enumerate(tokenize(sn.lines, sn.lang, muted=muted, dark=dark)):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        para_format(p, align="left", line_pt=line_pt)
        for text, colour, bold, italic in toks:
            add_run(p, text, font="mono", size=size, colour=colour, bold=bold or i in key_set,
                    italic=italic or None, no_proof=True)
        end_para_size(p, size)
    return tb, hl
