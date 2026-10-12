"""Text width estimates, measured with the deck's own font files (deck/qa/fonts/, the OFL Fira Sans and Fira Mono
that the QA render and the presenting laptop use; docs/DESIGN.md section 4).

font names: "minor" / "major" (Fira Sans Regular, Bold with bold=True), "title" (Fira Sans SemiBold),
"medium" (Fira Sans Medium), "mono" (Fira Mono, 0.6 em per character).
Without the font files the estimate falls back to an average advance per em (UNVERIFIED, wider than measured).
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

FONT_DIR = Path(__file__).resolve().parents[1] / "qa" / "fonts"
FILES = {
    ("minor", False): "FiraSans-Regular.ttf",
    ("minor", True): "FiraSans-Bold.ttf",
    ("title", False): "FiraSans-SemiBold.ttf",
    ("title", True): "FiraSans-SemiBold.ttf",
    ("medium", False): "FiraSans-Medium.ttf",
    ("medium", True): "FiraSans-Bold.ttf",
}
FALLBACK_EM = {"minor": 0.55, "title": 0.58, "medium": 0.56}
MONO_EM = 0.600


@lru_cache(maxsize=None)
def _font(font: str, bold: bool):
    try:
        from PIL import ImageFont
        return ImageFont.truetype(str(FONT_DIR / FILES[(font, bold)]), 1000)
    except Exception:  # noqa: BLE001 - missing file or Pillow without FreeType: estimate instead
        return None


def width_in(text: str, size_pt: float, *, font: str = "minor", bold: bool = False) -> float:
    """Advance width of `text` (one line) in inches."""
    if font == "mono":
        return len(text) * MONO_EM * size_pt / 72
    font = "minor" if font == "major" else font
    f = _font(font, bold)
    if f is None:
        return len(text) * FALLBACK_EM.get(font, 0.55) * size_pt / 72
    return f.getlength(text) / 1000 * size_pt / 72


def wrap_lines(text: str, size_pt: float, box_w_in: float, *, font: str = "title", bold: bool = False) -> list[str]:
    """Greedy word wrap with measured widths. Explicit '\n' forces a break. Default: slide title font."""
    out = []
    for para in str(text).split("\n"):
        words = para.split(" ")
        cur = ""
        for w in words:
            trial = (cur + " " + w).strip()
            if cur and width_in(trial, size_pt, font=font, bold=bold) > box_w_in:
                out.append(cur)
                cur = w
            else:
                cur = trial
        out.append(cur)
    return out


def text_h(text: str, size_pt: float, box_w_in: float, *, font: str = "minor", bold: bool = False,
           line: float = 1.2) -> float:
    """Height in inches of `text` wrapped into `box_w_in` at 100 % line spacing (1.2 em per line)."""
    return len(wrap_lines(text, size_pt, box_w_in, font=font, bold=bold)) * size_pt * line / 72
