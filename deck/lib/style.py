"""Shared style constants for the deck builder and its helpers (charts.py, diagrams.py, codebox.py, chips.py).

PyCon NL 2026 palette (pycon-nl.org CSS and inline SVG fills, fetched 2026-10-03) and the site font family:
Fira Sans for all text, Fira Mono for code (both SIL OFL 1.1). Master: deck/template/pycon_nl_2026_master.pptx
(built by deck/template/make_master.py). Values, sources, contrast ratios and rules: docs/DESIGN.md.

Single source of every colour: deck/content.yaml `meta.palette` (slide colours) and `meta.render_palette` (inside
the renders and on the render label chip swatches). This module holds no colour value of its own: a missing or
malformed key stops the build instead of falling back to another palette.

Rules in short:
  text on white: ink (body), navy (titles), slate (small print, footer, code comments; 7.2:1)
  text on navy:  white (titles, body), sage (small print, footer, highlight; 7.3:1)
  highlight:     blue on white, sage on navy (there is no warm accent)
  muted:         grey for non-text marks only (greyed bars, outlines, rules): 2.5:1 on white, never text

Usage by helpers:

    from .style import STYLE, EMU_PER_IN, rgb      # (build_deck.py imports the package as "lib")
    def add_column_log(slide, box, spec, style): ...   # style is STYLE

`box` is (left, top, width, height) in EMU.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml
from pptx.dml.color import RGBColor

EMU_PER_IN = 914400
EMU_PER_PT = 12700
CONTENT_YAML = Path(__file__).resolve().parents[1] / "content.yaml"

PALETTE_KEYS = ("navy", "blue", "sage", "white", "grey", "slate", "ink", "light")
RENDER_KEYS = ("background", "ground", "buildings", "vegetation", "street_furniture", "unlabelled")
RENDER_EXTRA_KEYS = ("height_ramp", "clusters", "noise")
_HEX = re.compile(r"^#?[0-9A-Fa-f]{6}$")


def _hex(v, where: str):
    if isinstance(v, list):
        return [_hex(x, where) for x in v]
    if not isinstance(v, str) or not _HEX.match(v):
        raise ValueError(f"content.yaml {where}: {v!r} is not a #RRGGBB colour")
    return v.lstrip("#").upper()


def _load() -> tuple[dict, dict, dict, dict]:
    meta = yaml.safe_load(CONTENT_YAML.read_text(encoding="utf-8"))["meta"]
    pal, rp = meta.get("palette") or {}, meta.get("render_palette") or {}
    missing = [f"palette.{k}" for k in PALETTE_KEYS if k not in pal] + \
        [f"render_palette.{k}" for k in RENDER_KEYS + RENDER_EXTRA_KEYS if k not in rp]
    if missing:
        raise KeyError(f"content.yaml meta is missing {', '.join(missing)}")
    palette = {k: _hex(pal[k], f"meta.palette.{k}") for k in PALETTE_KEYS}
    render = {k: _hex(rp[k], f"meta.render_palette.{k}") for k in RENDER_KEYS}
    extra = {k: _hex(rp[k], f"meta.render_palette.{k}") for k in RENDER_EXTRA_KEYS}
    fonts = meta.get("fonts") or {}
    return palette, render, extra, fonts


PALETTE, RENDER, RENDER_EXTRA, _META_FONTS = _load()

# Names as in content.yaml meta.palette (hex without '#')
NAVY = PALETTE["navy"]      # pycon-nl.org "north": dark backgrounds, titles on white, theme dk2
BLUE = PALETTE["blue"]      # "north2": highlight on white (6.0:1), links, key-line edge, theme accent1
SAGE = PALETTE["sage"]      # "north3": highlight and small print on navy (7.3:1), theme accent2
WHITE = PALETTE["white"]    # slide background, text on navy, theme lt1
GREY = PALETTE["grey"]      # site UI grey: muted marks only (greyed series, outlines, rules), NOT text on white
SLATE = PALETTE["slate"]    # small print, footer, slide number, code comments on white (7.2:1)
INK = PALETTE["ink"]        # body text on white (13.2:1), theme dk1
LIGHT = PALETTE["light"]    # tiles, code key-line bar, thin rules on white, theme lt2

# Roles: use these names, so the choice of colour follows the background.
ROLES = {
    "text": INK,              # body text on white
    "title": NAVY,            # titles on white (master title style)
    "text_small": SLATE,      # 12 pt source lines, conditions, small print, footer on white
    "text_dark": WHITE,       # titles and body text on navy
    "text_small_dark": SAGE,  # small print and footer on navy
    "highlight": BLUE,        # highlighted series / word / key line on white
    "highlight_dark": SAGE,   # highlight on navy
    "muted": GREY,            # greyed series, outlines, bullets of a muted list (not text)
    "background_dark": NAVY,
    "tile": LIGHT,
}

COLOURS = {**PALETTE, **ROLES}

# --- Fonts ----------------------------------------------------------------------------------------------------
# Theme font scheme: major = minor = Fira Sans. Weights other than Regular/Bold are separate family names in the
# static TTFs, so they are addressed by name. Slide titles inherit "Fira Sans SemiBold" from the master title
# style: do not put a typeface (or "+mj-lt", which is Fira Sans Regular) on title runs.
_SANS = _META_FONTS.get("sans", "Fira Sans")
_MONO = _META_FONTS.get("mono", "Fira Mono")
FONTS = {
    "major": _SANS,
    "minor": _SANS,
    "title": f"{_SANS} SemiBold",     # titles, hero numbers, headings
    "medium": f"{_SANS} Medium",      # emphasis between Regular and SemiBold (tile text)
    "mono": _MONO,                    # code, >= 18 pt
    "mono_medium": f"{_MONO} Medium",
}
ALLOWED_FONTS = sorted(set(FONTS.values()))
MONO_PITCH_FAMILY = "49"   # fixed pitch + modern family, so a substitute stays monospace
MONO_ADVANCE_EM = 0.600    # Fira Mono advance width: 35 characters at 18 pt = 5.25 in, 70 characters = 10.5 in
LINE_HEIGHT_EM = 1.2       # Fira Sans and Fira Mono at 100 % line spacing (ascender 935 + descender 265, upm 1000)

# --- Minimum sizes (pt) ---------------------------------------------------------------------------------------
MIN_PT = {
    "body": 20,        # body text, support line, labels
    "code": 18,        # code
    "chart": 20,       # chart text (charts.py CHART_PT)
    "small": 12,       # source lines, conditions, small print, footer
    "appendix": 14,    # dense appendix slides only
}

# Standard sizes used by the builder
SIZES = {
    "title": 32,       # master title size (Fira Sans SemiBold, navy) on every content layout
    "support": 20,
    "body": 20,
    "code": 18,
    "small": 12,
    "chip": 20,
    "hero": 96,
    "hero_label": 20,
    "chart": 20,
}
# Title sizes set by the master's dark layouts (layout number -> pt); every other layout uses SIZES["title"].
LAYOUT_TITLE_PT = {1: 54, 3: 44, 6: 48, 11: 60}

STYLE = {
    "fonts": FONTS,
    "colours": COLOURS,
    "palette": PALETTE,
    "roles": ROLES,
    "render": RENDER,
    "render_extra": RENDER_EXTRA,
    "min_pt": MIN_PT,
    "sizes": SIZES,
    "layout_title_pt": LAYOUT_TITLE_PT,
    "mono_pitch_family": MONO_PITCH_FAMILY,
    "mono_advance_em": MONO_ADVANCE_EM,
    "line_height_em": LINE_HEIGHT_EM,
    "lang": "en-GB",
}


def rgb(hex_or_name: str) -> RGBColor:
    """RGBColor from a palette name ('blue'), a role ('highlight') or a palette hex value."""
    h = COLOURS.get(hex_or_name, hex_or_name).lstrip("#").upper()
    if h not in PALETTE.values() and h not in RENDER.values():
        raise ValueError(f"colour {hex_or_name!r} is not in content.yaml meta.palette or meta.render_palette")
    return RGBColor.from_string(h)


def hex_of(name: str) -> str:
    """'#RRGGBB' of a palette name or role (for libraries that take CSS colours, such as segno)."""
    return "#" + COLOURS[name]


def inches(emu: int) -> float:
    return emu / EMU_PER_IN
