"""Fetch the deck's OFL fonts into deck/qa/fonts/ for faithful QA renders (never touches the user's font config).

The deck uses the PyCon NL 2026 site font, Fira Sans (Google Fonts, SIL OFL 1.1), and Fira Mono from the same
family for code (docs/DESIGN.md). The QA render uses the same font files the presenting laptop must have, so
no substitution or alias is involved (deck/qa/fonts.conf).

Weights that PowerPoint addresses by family name (legacy name ID 1 of the static TTFs):
  "Fira Sans"            Regular, Italic, Bold (b="1")
  "Fira Sans Medium"     Medium (500)
  "Fira Sans SemiBold"   SemiBold (600): slide titles
  "Fira Mono"            Regular, Bold (b="1")
  "Fira Mono Medium"     Medium (500)

Run:  cd talk && uv run python deck/qa/setup_fonts.py
"""

from __future__ import annotations

import shutil
import sys
import urllib.request
from pathlib import Path

FONT_DIR = Path(__file__).resolve().parent / "fonts"
GF = "https://raw.githubusercontent.com/google/fonts/bd8f81ddb5c74d5c8897b36ad88b440266245103/ofl"
DOWNLOADS = {
    "FiraSans-Regular.ttf": f"{GF}/firasans/FiraSans-Regular.ttf",
    "FiraSans-Italic.ttf": f"{GF}/firasans/FiraSans-Italic.ttf",
    "FiraSans-Medium.ttf": f"{GF}/firasans/FiraSans-Medium.ttf",
    "FiraSans-SemiBold.ttf": f"{GF}/firasans/FiraSans-SemiBold.ttf",
    "FiraSans-Bold.ttf": f"{GF}/firasans/FiraSans-Bold.ttf",
    "OFL-FiraSans.txt": f"{GF}/firasans/OFL.txt",
    "FiraMono-Regular.ttf": f"{GF}/firamono/FiraMono-Regular.ttf",
    "FiraMono-Medium.ttf": f"{GF}/firamono/FiraMono-Medium.ttf",
    "FiraMono-Bold.ttf": f"{GF}/firamono/FiraMono-Bold.ttf",
    "OFL-FiraMono.txt": f"{GF}/firamono/OFL.txt",
}


def ensure_fonts(verbose: bool = True) -> list[str]:
    """Download any missing font file; returns notes (empty when everything is present)."""
    FONT_DIR.mkdir(parents=True, exist_ok=True)
    notes = []
    for name, url in DOWNLOADS.items():
        p = FONT_DIR / name
        if p.exists() and p.stat().st_size > 0:
            continue
        if verbose:
            print("download", name)
        try:
            with urllib.request.urlopen(url, timeout=60) as r, open(p, "wb") as fh:
                shutil.copyfileobj(r, fh)
        except Exception as exc:  # noqa: BLE001 - offline: the render falls back to system fonts; QA must flag it
            notes.append(f"{name} missing and download failed: {exc}")
            if p.exists() and p.stat().st_size == 0:
                p.unlink()
    return notes


if __name__ == "__main__":
    for n in ensure_fonts():
        print("NOTE:", n, file=sys.stderr)
    print("fonts in", FONT_DIR)
