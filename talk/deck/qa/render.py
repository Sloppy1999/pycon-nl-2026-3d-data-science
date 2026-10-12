"""Render the deck for visual QA: PPTX -> PDF (LibreOffice through the pptx skill's soffice.py wrapper)
-> PNG per slide (pdftoppm, 1920 px wide) -> contact sheet.

Fonts: a private fontconfig (deck/qa/fonts.conf, FONTCONFIG_FILE) with the deck's own OFL fonts in deck/qa/fonts/:
Fira Sans (Regular, Italic, Medium, SemiBold, Bold) and Fira Mono (Regular, Medium, Bold), the fonts the presenting
laptop must have (docs/DESIGN.md section 4). No substitution or alias is configured. The config is rewritten with
absolute paths into deck/out/.fonts.generated.conf, its cache lives in deck/out/.fccache. The user's own font
configuration is not read or changed.

Outputs (deck/out/):
  20261015_PyCon-NL_3D-Data-Science.pdf   main slides only (hidden appendix excluded)
  qa_all.pdf                              all slides incl. the hidden appendix (source of the PNGs)
  png/slide-NN.png, png/contact.png       1920 px wide
  qa_render.json                          fonts embedded in the PDF, timings

Run:  cd talk && uv run python deck/qa/render.py
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

QA = Path(__file__).resolve().parent
DECK = QA.parent
OUT = Path(__import__("os").environ.get("DECK_OUT_DIR", DECK / "out")).resolve()
PNG = OUT / "png"
PPTX_NAME = "20261015_PyCon-NL_3D-Data-Science.pptx"
SKILL_OFFICE = Path(os.environ.get("PPTX_SKILL_DIR", Path.home() / ".claude/skills/pptx")) / "scripts" / "office"
W_PX = 1920

sys.path.insert(0, str(QA))
sys.path.insert(0, str(DECK))
from setup_fonts import ensure_fonts  # noqa: E402
from lib.style import hex_of  # noqa: E402


def _soffice(args: list[str]) -> subprocess.CompletedProcess:
    sys.path.insert(0, str(SKILL_OFFICE))
    from soffice import run_soffice  # the skill's wrapper (headless, sandbox shim, private profile)
    return run_soffice(args, capture_output=True, text=True, timeout=600)


def to_pdf(pptx: Path, out_pdf: Path, *, hidden: bool) -> float:
    tmpdir = OUT / "_pdf"
    if tmpdir.exists():
        shutil.rmtree(tmpdir)
    tmpdir.mkdir(parents=True)
    filt = 'pdf:impress_pdf_Export:{"ExportHiddenSlides":{"type":"boolean","value":"%s"},' \
           '"ExportNotesPages":{"type":"boolean","value":"false"}}' % ("true" if hidden else "false")
    t0 = time.time()
    res = _soffice(["--headless", "--convert-to", filt, "--outdir", str(tmpdir), str(pptx)])
    produced = list(tmpdir.glob("*.pdf"))
    if res.returncode != 0 or not produced:
        raise RuntimeError(f"soffice failed ({res.returncode}): {res.stderr[-2000:]} {res.stdout[-500:]}")
    produced[0].replace(out_pdf)
    shutil.rmtree(tmpdir, ignore_errors=True)
    return time.time() - t0


def to_png(pdf: Path) -> list[Path]:
    if PNG.exists():
        shutil.rmtree(PNG)
    PNG.mkdir(parents=True)
    subprocess.run(["pdftoppm", "-png", "-scale-to-x", str(W_PX), "-scale-to-y", "-1", str(pdf),
                    str(PNG / "slide")], check=True)
    files = sorted(PNG.glob("slide-*.png"))
    out = []
    for f in files:                       # normalise to slide-NN.png
        num = int(f.stem.split("-")[-1])
        dst = PNG / f"slide-{num:02d}.png"
        if f != dst:
            f.replace(dst)
        out.append(dst)
    return sorted(out)


def contact_sheet(pngs: list[Path], labels: list[str], cols: int = 4, thumb_w: int = 480) -> Path:
    from PIL import Image, ImageDraw, ImageFont
    ims = [Image.open(p).convert("RGB") for p in pngs]
    th = int(thumb_w * ims[0].height / ims[0].width)
    pad, lab_h = 12, 26
    rows = (len(ims) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * (thumb_w + pad) + pad, rows * (th + lab_h + pad) + pad), hex_of("white"))
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype(str(QA / "fonts" / "FiraSans-SemiBold.ttf"), 18)
    except Exception:
        font = None
    for i, (im, lab) in enumerate(zip(ims, labels)):
        r, c = divmod(i, cols)
        x = pad + c * (thumb_w + pad)
        y = pad + r * (th + lab_h + pad)
        sheet.paste(im.resize((thumb_w, th)), (x, y + lab_h))
        draw.rectangle([x, y + lab_h, x + thumb_w - 1, y + lab_h + th - 1], outline=hex_of("grey"))
        draw.text((x, y + 2), lab, fill=hex_of("ink"), font=font)
    out = PNG / "contact.png"
    sheet.save(out)
    return out


def fonts_in_pdf(pdf: Path) -> list[str]:
    try:
        res = subprocess.run(["pdffonts", str(pdf)], capture_output=True, text=True, check=True)
    except Exception:
        return ["pdffonts not available"]
    names = set()
    for line in res.stdout.splitlines()[2:]:
        if line.strip():
            names.add(line.split()[0].split("+")[-1])
    return sorted(names)


def main():
    pptx = OUT / PPTX_NAME
    if not pptx.exists():
        sys.exit(f"{pptx} missing: run deck/build_deck.py first")
    notes = ensure_fonts(verbose=False)
    # fontconfig resolves the relative cachedir against the working directory, not the config file, so write a copy
    # with absolute paths; the cache then always lands in deck/out/.fccache, whatever directory this runs from.
    conf = (QA / "fonts.conf").read_text()
    conf = conf.replace('<dir prefix="relative">fonts</dir>', f"<dir>{QA / 'fonts'}</dir>")
    conf = conf.replace('<cachedir prefix="relative">../out/.fccache</cachedir>', f"<cachedir>{OUT / '.fccache'}</cachedir>")
    (OUT / ".fccache").mkdir(parents=True, exist_ok=True)
    (OUT / ".fonts.generated.conf").write_text(conf)
    os.environ["FONTCONFIG_FILE"] = str(OUT / ".fonts.generated.conf")
    subprocess.run(["fc-cache", "-f"], env=dict(os.environ), capture_output=True)
    report = {"fontconfig": str(QA / "fonts.conf"), "fontconfig_generated": os.environ["FONTCONFIG_FILE"],
              "font_notes": notes}
    report["seconds_pdf_all"] = round(to_pdf(pptx, OUT / "qa_all.pdf", hidden=True), 1)
    report["seconds_pdf_main"] = round(to_pdf(pptx, OUT / PPTX_NAME.replace(".pptx", ".pdf"), hidden=False), 1)
    report["pdf_fonts"] = fonts_in_pdf(OUT / "qa_all.pdf")
    pngs = to_png(OUT / "qa_all.pdf")
    try:
        from pptx import Presentation
        prs = Presentation(str(pptx))
        hidden = [s._element.get("show") == "0" for s in prs.slides]
    except Exception:
        hidden = [False] * len(pngs)
    main_n = sum(1 for h in hidden if not h)
    labels = [f"{i + 1}" if i < main_n else f"B{i + 1 - main_n} (hidden)" for i in range(len(pngs))]
    report["png"] = [str(p) for p in pngs]
    report["contact_sheet"] = str(contact_sheet(pngs, labels))
    (OUT / "qa_render.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "png"}, indent=2))


if __name__ == "__main__":
    main()
