#!/usr/bin/env python3
"""Build the PyCon NL 2026 deck "3D Data Science with Python" from the PyCon NL 2026 master.

Personal talk: the conference palette and font (deck/template/pycon_nl_2026_master.pptx, docs/DESIGN.md); no
company master, branding or metadata. The speaker's affiliation appears only as plain text on slide 1.

Reads only: deck/content.yaml, deck/notes.yaml, deck/appendix.yaml, results/*.json, renders/*,
snippets/*, the master. Writes deck/out/20261015_PyCon-NL_3D-Data-Science.pptx and deck/out/build_report.json.

Steps: 1 structure (unpack the master, duplicate its example slide per content.yaml layout number with the pptx
skill's add_slide.py, order <p:sldIdLst>, sections, clean, pack) -> 2 fill with python-pptx (per-slide content,
footer and slide number, notes, alt text) -> 3 raw XML (transitions, on-click build, hidden appendix, en-GB,
document properties) -> 4 validate.py --original against the master.
Every position comes from the master's layout placeholders (lib/geometry.py), every colour from content.yaml
meta.palette (lib/style.py).

Run:  uv run python deck/build_deck.py
"""

from __future__ import annotations

import argparse
import copy
import datetime as dt
import importlib
import json
import os
import re
import shutil
import subprocess
import sys
import traceback
from pathlib import Path

import yaml
from lxml import etree

DECK = Path(__file__).resolve().parent
TALK = DECK.parent
sys.path.insert(0, str(DECK))

from PIL import Image  # noqa: E402
from pptx import Presentation  # noqa: E402
from pptx.enum.shapes import MSO_SHAPE  # noqa: E402
from pptx.enum.dml import MSO_LINE_DASH_STYLE  # noqa: E402
from pptx.oxml.ns import qn  # noqa: E402
from pptx.util import Pt  # noqa: E402

from lib import chips, xmlpost  # noqa: E402
from lib.codebox import (INSET_B, INSET_L, INSET_T, LINE_PT, Snippet, add_code, code_height_in,  # noqa: E402
                         code_width_in, read_snippet, tokenize)
from lib.geometry import GEO  # noqa: E402
from lib.measure import text_h, width_in, wrap_lines  # noqa: E402
from lib.pptx_helpers import (E, add_picture_fill, add_run, add_text_runs, add_textbox, box_emu,  # noqa: E402
                              clear_text_frame, drop_placeholder, end_para_size, insert_picture,
                              mark_decorative,
                              line, para_format, pending_box, placeholder, rect, set_alt, set_body_pr,
                              set_name, shape_text, text_block, title_placeholder)
from lib.structure import build_structure, PPTX_SKILL  # noqa: E402
from lib.style import COLOURS, LAYOUT_TITLE_PT, RENDER, SIZES, STYLE, hex_of, rgb  # noqa: E402
from lib.tokens import Resolver, fmt_int  # noqa: E402

TEMPLATE = DECK / "template" / "pycon_nl_2026_master.pptx"
OUT_DIR = DECK / "out"
WORK = OUT_DIR / "_work"
RESULTS = TALK / "results"
RENDERS = TALK / "renders"
SNIPPETS = TALK / "snippets"
CONTENT = DECK / "content.yaml"
NOTES = DECK / "notes.yaml"
APPENDIX = DECK / "appendix.yaml"

# ------------------------------------------------------------------------------- geometry (in)
# All read from the master's layout placeholders (lib/geometry.py, docs/DESIGN.md section 5).
X0, FULL_W, BOTTOM = GEO.margin, GEO.content_w, GEO.bottom      # 0.600, 12.133, 6.800
COL_W, XR = GEO.col_w, GEO.col_r                                # L5 columns: 5.817 wide, right one at 6.917
L7_TEXT, L8_TEXT = GEO.ph(7, 14), GEO.ph(8, 14)                 # text columns beside the media frame
MEDIA_R = GEO.ph(7, 18).t()                                     # L7 media idx 18, exact 1588:1792
MEDIA_L = GEO.ph(8, 18).t()                                     # L8 media idx 18
SMALL_PT, SUPPORT_PT = SIZES["small"], SIZES["support"]
LINE_EM = STYLE["line_height_em"]
EXPECTED_PX = {"hook_split.png": (4190, 1792)}
DEFAULT_PX = (1588, 1792)
CLASSES = ["ground", "buildings", "vegetation", "street_furniture"]
FOOTER_IDX, SLDNUM_IDX = 11, 12


def lines_h(n: int, size: float) -> float:
    """Height of n lines at 100 % line spacing (1.2 em)."""
    return n * size * LINE_EM / 72


def content_top(layout: int, n_lines: int) -> float:
    """First content y on `layout` under a title of n_lines lines (lib/geometry.py)."""
    return GEO.content_top(layout, n_lines, LAYOUT_TITLE_PT.get(layout, SIZES["title"]))


def _load_yaml(p: Path):
    if not p.exists():
        return None
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def _index_by_n(data, list_keys=("slides", "notes", "appendix")) -> dict[str, object]:
    """Accept {slides: [{n: ..}]}, [{n: ..}], or {n: {...}} and return {str(n): entry}."""
    if data is None:
        return {}
    if isinstance(data, dict):
        for k in list_keys:
            if isinstance(data.get(k), list):
                return _index_by_n(data[k])
        out = {}
        for k, v in data.items():
            if k in ("meta", "_meta", "version", "format"):
                continue
            out[str(k)] = v
        return out
    if isinstance(data, list):
        out = {}
        for e in data:
            if isinstance(e, dict):
                key = e.get("n", e.get("slide", e.get("id")))
                if key is not None:
                    out[str(key)] = e
        return out
    return {}


class Builder:
    def __init__(self, args):
        self.args = args
        self.content = yaml.safe_load(CONTENT.read_text(encoding="utf-8"))
        self.meta = self.content["meta"]
        self.res = Resolver(RESULTS)
        self.notes_raw = _load_yaml(NOTES)
        self.notes = _index_by_n(self.notes_raw)
        self.appendix_raw = _load_yaml(APPENDIX)
        self.appendix = _index_by_n(self.appendix_raw)
        lab = RENDERS / "labels.json"
        self.labels = json.loads(lab.read_text(encoding="utf-8")) if lab.exists() else None
        snj = RESULTS / "snippets.json"
        self.snippet_runs = json.loads(snj.read_text(encoding="utf-8")) if snj.exists() else None
        self.report: dict = {
            "output": None, "inputs": {}, "placeholders": [], "missing_tokens": [], "helpers": {},
            "helper_calls": [], "snippets": {}, "renders": {}, "notes": {"source": str(NOTES.relative_to(TALK)),
                                                                       "present": NOTES.exists(), "pending": []},
            "appendix": {"source": str(APPENDIX.relative_to(TALK)), "present": APPENDIX.exists()},
            "titles": {}, "warnings": [], "result_labels": self.res.labels, "result_load_errors": self.res.load_errors,
        }
        self.charts, err = self._import("charts")
        self.report["helpers"]["charts"] = "ok" if self.charts else err
        self.diagrams, err = self._import("diagrams")
        self.report["helpers"]["diagrams"] = "ok" if self.diagrams else err
        self.sketches, err = self._import("sketches")
        self.report["helpers"]["sketches"] = "ok" if self.sketches else err
        self._chip_cache: dict = {}
        self._cover_cache: dict = {}
        # Morph chain: chips on every Morph slide first try the chip rectangles of the last Morph
        # slide with labels (f6_final), so they stay put from slide 13 to 15.
        morph_labels = [sp.get("labels_from") for sp in self.content["slides"]
                        if sp.get("transition") == "morph" and sp.get("labels_from")]
        self.morph_chip_ref = morph_labels[-1] if morph_labels else None
        # slides with `labels_only` (10, 11: the Ground chip alone) reuse the chip layout of the first Morph slide
        # that draws every chip of that frame (12), computed against that slide's render, so the chips they
        # share stay in the same rectangle through the whole Morph chain
        self.chip_layout_file = {}
        for sp in self.content["slides"]:
            fk = sp.get("labels_from")
            if fk and not sp.get("labels_only") and fk not in self.chip_layout_file and sp.get("visual", {}).get("file"):
                self.chip_layout_file[fk] = sp["visual"]["file"]
        self.morph = self._morph_stack()

    def _morph_stack(self) -> dict:
        """Fixed boxes of the L7 text column on the Morph slides (8 to 14), identical on every one of them, so Morph
        only changes their content. Stacked from the content bottom (6.800 in): source line, small print, support
        line, each as tall as the longest of its kind on the Morph slides (measured with Fira Sans); the code box
        takes the rest of the column from content_top(7, 2) down."""
        col = L7_TEXT
        w = col.w - 0.02                           # wrap safety: renderers break slightly earlier than the estimate
        specs = [sp for sp in self.content["slides"] if sp.get("transition") == "morph"]

        def max_lines(key, size):
            n = 0
            for sp in specs:
                if sp.get(key):
                    txt = self.source_text(sp[key]) if key == "source" else self.res.resolve(sp[key])
                    n = max(n, len(wrap_lines(txt, size, w, font="minor")))
            return n

        n_src, n_small, n_sup = max_lines("source", SMALL_PT), max_lines("small_print", SMALL_PT), \
            max_lines("support", SUPPORT_PT)
        src_h = lines_h(n_src, SMALL_PT)
        src_y = BOTTOM - src_h
        small_h = lines_h(n_small, SMALL_PT)
        # the support box keeps the room of the old stack (small print 0.06 in above the source line), so the
        # code box keeps its height; the small print itself sits 0.14 in above the source line, so it does not
        # read as one paragraph with the attribution. The slides with small print (12 to 14) have a one-line
        # support line, so their small print stays well clear of it (checked in run(): support_vs_small).
        small_y = src_y - 0.14 - small_h
        sup_h = lines_h(n_sup, SUPPORT_PT)
        sup_y = ((src_y - 0.06 - small_h) if n_small else src_y) - 0.12 - sup_h
        code_y = content_top(7, 2)
        code_h = sup_y - 0.12 - code_y
        return {"code": (col.x, code_y, col.w, code_h), "support": (col.x, sup_y, col.w, sup_h),
                "small": (col.x, small_y, col.w, small_h), "src": (col.x, src_y, col.w, src_h),
                "lines": {"source": n_src, "small_print": n_small, "support": n_sup}}

    # ----------------------------------------------------------------------------- utilities
    @staticmethod
    def _import(name):
        try:
            return importlib.import_module(f"lib.{name}"), None
        except Exception as exc:  # helper not written yet, or broken
            return None, f"{type(exc).__name__}: {exc}"

    def R(self, text, n=None):
        return self.res.resolve(text, where=f"slide {n}" if n is not None else None)

    def placeholder_note(self, n, kind, what, caption):
        self.report["placeholders"].append({"slide": n, "kind": kind, "what": what, "caption": caption})

    def warn(self, n, msg):
        self.report["warnings"].append({"slide": n, "msg": msg})

    def source_text(self, key):
        if key == "ahn":
            return self.meta["source_ahn"]
        if key == "ahn_licence":                 # slide 25: the source line, then the readable licence URI
            return self.meta["source_ahn"] + "\n" + self.meta["licence_line"]
        return self.R(key)

    # ----------------------------------------------------------------------------- licence links
    HLINK_CLR_URI = "{A12FA001-AC4F-418D-AE19-62706E023703}"      # Office 2019+: the link keeps the run's colour
    AHYP_NS = "http://schemas.microsoft.com/office/drawing/2018/hyperlinkcolor"

    def link_licence(self, slide) -> int:
        """CC BY 4.0 section 3(a)(1)(C): every "CC BY 4.0" run (and slide 25's readable licence line) gets a
        hyperlink to meta.licence_url. A run holding the phrase is split so that only the phrase is linked."""
        url = self.meta.get("licence_url")
        if not url:
            return 0
        # the phrase "CC BY 4.0", and the URI part of slide 25's readable line ("Licence: <uri>")
        targets = ["CC BY 4.0"] + ([self.meta["licence_line"].split(": ", 1)[-1]] if self.meta.get("licence_line") else [])
        rid = None
        n = 0
        queue = list(slide._element.iter(qn("a:r")))
        while queue:
            r = queue.pop(0)
            rpr, t = r.find(qn("a:rPr")), r.find(qn("a:t"))
            if t is None or not t.text or (rpr is not None and rpr.find(qn("a:hlinkClick")) is not None):
                continue
            hits = [(t.text.find(x), x) for x in targets if x in t.text]
            if not hits:
                continue
            i, x = min(hits)
            before, after = t.text[:i], t.text[i + len(x):]
            if before:
                r0 = copy.deepcopy(r)
                r0.find(qn("a:t")).text = before
                r.addprevious(r0)
            if after:
                r2 = copy.deepcopy(r)
                r2.find(qn("a:t")).text = after
                r.addnext(r2)
                queue.insert(0, r2)
            t.text = x
            if rpr is None:
                rpr = etree.SubElement(r, qn("a:rPr"))
                r.insert(0, rpr)
            if rid is None:
                from pptx.opc.constants import RELATIONSHIP_TYPE as RT
                rid = slide.part.relate_to(url, RT.HYPERLINK, is_external=True)
            h = etree.Element(qn("a:hlinkClick"))
            h.set(qn("r:id"), rid)
            ext = etree.SubElement(etree.SubElement(h, qn("a:extLst")), qn("a:ext"))
            ext.set("uri", self.HLINK_CLR_URI)
            etree.SubElement(ext, f"{{{self.AHYP_NS}}}hlinkClr", nsmap={"ahyp": self.AHYP_NS}).set("val", "tx")
            later = next((c for c in rpr if c.tag in (qn("a:hlinkMouseOver"), qn("a:rtl"), qn("a:extLst"))), None)
            if later is not None:
                later.addprevious(h)
            else:
                rpr.append(h)
            n += 1
        return n

    # ----------------------------------------------------------------------------- text pieces
    def set_title(self, slide, n, text, layout, *, name=None):
        """Title text only: no typeface, size or colour on the runs, so they inherit the master's title style
        (Fira Sans SemiBold; 32 pt navy, or the dark layouts' size in white). Line breaks: a "\n" in content.yaml,
        or, on L7 (the Morph chain and slide 18), after the colon of a "N Step: claim" title, so every Morph title
        has the same two-line shape as the master's example; on L6/L8 after the separator when both halves fit on
        one line but the whole does not."""
        ph = title_placeholder(slide) or placeholder(slide, 0)
        text = self.R(text, n)
        if ph is None:
            self.warn(n, "no title placeholder")
            return 1
        size = LAYOUT_TITLE_PT.get(layout, SIZES["title"])
        width = GEO.title(layout).w - 0.02
        final = text
        if layout == 7 and ":" in text and "\n" not in text:
            head, rest = text.split(":", 1)
            final = head + ":\n" + rest.strip()
        sep = {8: ":", 6: ","}.get(layout)
        if sep and sep in text and "\n" not in text:
            head, rest = text.split(sep, 1)
            head, rest = head + sep, rest.strip()
            if len(wrap_lines(head, size, width)) == 1 and len(wrap_lines(rest, size, width)) == 1 \
                    and len(wrap_lines(text, size, width)) >= 2:
                final = head + "\n" + rest
        lines = wrap_lines(final, size, width)
        tf = ph.text_frame
        p = clear_text_frame(tf)
        for i, seg in enumerate(final.split("\n")):
            if i:
                p.add_line_break()
            add_text_runs(p, seg, font=None)
        if name:
            set_name(ph, name)
        self.report["titles"][str(n)] = {"text": final, "lines_est": len(lines), "layout": layout, "pt": size}
        max_lines = {7: 2, 8: 2, 10: 4, 6: 2, 1: 1, 11: 1}.get(layout, 1)
        if len(lines) > max_lines:
            self.warn(n, f"title estimated at {len(lines)} lines on L{layout} (max {max_lines})")
        return len(lines)

    def support(self, slide, n, text, box, name="Support"):
        if not text:
            return None
        return text_block(slide, *box, self.R(text, n), size=SUPPORT_PT, colour="text", name=name)

    # bottom-aligned small print (conditions, slide 17): the box is one 12 pt line taller than its text and
    # bottom-anchored, so a line that wraps differently in PowerPoint grows upwards into free space, not onto the
    # footer
    SMALL_PAD = 0.20

    def small(self, slide, n, text, box, name="Small print", colour=None, bottom=False):
        if not text:
            return None
        if isinstance(text, list):
            text = [self.source_text(t) for t in text]
        else:
            text = self.R(text, n)
        if bottom:
            x, y, w, h = box
            box = (x, y - self.SMALL_PAD, w, h + self.SMALL_PAD)
        return text_block(slide, *box, text, size=SMALL_PT, colour=colour or "text_small", name=name,
                          anchor="b" if bottom else "t")

    def source(self, slide, n, key, box, name="Source", colour=None):
        if not key:
            return None
        return text_block(slide, *box, self.source_text(key), size=SMALL_PT, colour=colour or "text_small", name=name)

    def hero(self, slide, n, x, y, w, value, label, *, size=96, name="Hero", min_size=28):
        """Hero number (Fira Sans SemiBold, blue) with its label (20 pt ink) on the same baseline, in one text box
        (so an on-click build reveals both together); the label moves under the value when the line is too wide."""
        value = self.R(value, n)
        label = self.R(label, n) if label else None
        while width_in(value, size, font="title") > w - 0.15 and size > min_size:
            size -= 4
        gap = "\u00a0"                      # no-break space between value and label (U+2002 is not in Fira Sans)
        inline = bool(label) and width_in(value, size, font="title") + width_in(gap + label, 20) <= w - 0.10
        h = lines_h(1, size) + (lines_h(1, 20) + 0.08 if label and not inline else 0)
        tb = add_textbox(slide, x, y, w, h, name=name, wrap=not inline)
        tf = tb.text_frame
        p = tf.paragraphs[0]
        para_format(p, align="left")
        add_text_runs(p, value, font="title", size=size, colour="highlight")
        if inline:
            add_text_runs(p, gap + label, font="minor", size=20, colour="text")
        end_para_size(p, size)
        if label and not inline:
            p2 = tf.add_paragraph()
            para_format(p2, align="left", space_before=6)
            add_text_runs(p2, label, font="minor", size=20, colour="text")
            end_para_size(p2, 20)
        return tb, h

    def hero_row(self, slide, n, x, y, w, value, label, *, size=44, min_size=24, name="Hero"):
        """Hero value and its label side by side (for slides where the hero sits under code or a diagram)."""
        value = self.R(value, n)
        label = self.R(label, n) if label else None
        max_vw = w * 0.62
        while width_in(value, size, font="title") > max_vw - 0.1 and size > min_size:
            size -= 2
        vh = lines_h(1, size)
        if width_in(value, size, font="title") > max_vw - 0.1:          # still too wide: two lines
            lines = len(wrap_lines(value, size, w, font="title"))
            tb = add_textbox(slide, x, y, w, vh * lines, name=name, wrap=True)
            p = tb.text_frame.paragraphs[0]
            para_format(p, align="left")
            add_text_runs(p, value, font="title", size=size, colour="highlight")
            end_para_size(p, size)
            y2 = y + lines * vh
            if label:
                text_block(slide, x, y2, w, lines_h(1, 20), label, size=20, colour="text", name="Hero label")
                y2 += lines_h(1, 20)
            return y2
        vw = width_in(value, size, font="title") + 0.15
        tb = add_textbox(slide, x, y, vw, vh, name=name, wrap=False, anchor="b")
        p = tb.text_frame.paragraphs[0]
        para_format(p, align="left")
        add_text_runs(p, value, font="title", size=size, colour="highlight")
        end_para_size(p, size)
        if label:
            # label baseline on the value baseline: both boxes bottom-anchored, the descents (0.265 em) differ
            lh = lines_h(1, 20)
            drop = 0.265 * (size - 20) / 72
            text_block(slide, x + vw + 0.20, y + vh - lh - drop, w - vw - 0.20, lh,
                       label, size=20, colour="text", name="Hero label", anchor="b", wrap=False)
        return y + vh

    def conditions_text(self, kind: str, note: str | None = None, n=None, plane_threads: bool = False,
                        short: bool = False) -> str:
        """The benchmark/memory conditions line; `note` (content.yaml / appendix.yaml `conditions_note`, tokens
        allowed) is appended, for measurements whose method differs from the runs the line describes.
        plane_threads: add the plane runs' thread count and CPU/wall ratio (only where the plane timings are
        charted, slide 21: content.yaml `conditions_threads`). short: the one-line version (content.yaml
        `conditions_short`, 2026-10-12): machine, versions, N, runs and the result file; the full line and the
        note go to the speaker notes (notes_text, CONDITIONS)."""
        if kind in ("scalene", "scalene_cpu"):
            return self._conditions_scalene(kind)
        if short:
            return self._conditions_short(kind)
        text = self._conditions_text(kind, plane_threads=plane_threads)
        if note:
            text += " " + self.R(note, n)
        return text

    RESULT_FILES = {"bench": "results/bench_cliff.json", "memory": "results/memory.json",
                    "facts": "results/python_facts.json", "profile": "results/profile_loop.json",
                    "ft": "results/bench_freethreaded.json", "eigen": "results/eigen_features.json"}

    @staticmethod
    def _cpu(c: dict) -> str:
        """'AMD Ryzen 7 5700X 8-Core Processor' -> 'Ryzen 7 5700X': the same CPU name on every conditions line."""
        return re.sub(r"^AMD |^Intel\(R\) Core\(TM\) | \d+-Core Processor$", "", str(c.get("cpu", "")))

    def _label_suffix(self, key: str) -> str:
        label = self.res.labels.get(key)
        return f" Result label: {label} (not final)." if label and label != "FINAL" else ""

    def _conditions_scalene(self, kind: str = "scalene") -> str:
        """Slides 23 and 27 (Scalene): the machine line as on the others, then what the figures are."""
        key = "prof" if kind == "scalene_cpu" else "scalene"
        c = self.res.lookup(f"{key}.conditions")
        if not isinstance(c, dict):
            self.res._miss(f"{key}.conditions", None, f"conditions ({kind})")
            return f"Conditions: [{key}.conditions] pending."
        cpu = self._cpu(c)
        ver = f"Python {c.get('python')}, Scalene {self.res.lookup(f'{key}.scalene')}"
        n = fmt_int(float(c["n"]))
        if kind == "scalene_cpu":
            ex = c.get("extra") or {}
            text = (f"Conditions: {cpu}, {ver} (--cpu-only, a sample every "
                    f"{float(ex.get('cpu_sampling_rate_s', 0.001)) * 1000:g}\u00a0ms); {n} points, both versions "
                    f"{ex.get('repeats_per_run')} times per run, median of {c.get('runs')} runs; AHN5 crop (CC BY 4.0). "
                    f"Shares are of the whole run, imports and reading the file included. Full: results/profile_scalene.json.")
        else:
            text = (f"Conditions: {cpu}, {ver}; {n} points, median of {c.get('runs')} runs; AHN5 1\u00a0km file "
                    f"(CC BY 4.0). Scalene counts allocations, not resident memory (slide 26). "
                    f"Full: results/memory_scalene.json.")
        return text + self._label_suffix(key)

    def _conditions_short(self, kind: str) -> str:
        """'Conditions: Ryzen 7 5700X, Python 3.13.15, NumPy 2.5.3; 722 961 points, median of 7 runs; AHN5 crop
        (CC BY 4.0). Full: results/bench_cliff.json.' One line on the slide, the rest in the notes."""
        c = self.res.lookup(f"{kind}.conditions")
        if not isinstance(c, dict):
            return self._conditions_text(kind)
        cpu = self._cpu(c)
        if kind == "ft":
            b = self.res.lookup("ft.builds") or {}
            f_, d_ = b.get("free_threaded", {}), b.get("gil", {})
            vers = f"CPython {f_.get('python', '?')} free-threaded and {d_.get('python', '?')}, NumPy {f_.get('numpy', '?')}"
        else:
            vers = f"Python {c.get('python')}, NumPy {c.get('numpy')}"
        n_pts = fmt_int(float(c["n"])) if c.get("n") is not None else "?"
        runs = c.get("runs")
        if kind == "profile":
            run_part = "one profiled run"
        elif kind == "memory":
            run_part = f"median of {runs} runs, each in a fresh process"
        else:
            run_part = f"median of {runs} runs"
        data = {"data/utrecht_jaarbeurs_200m.laz": "AHN5 crop",
                "data/AHN5_C_135000_455000.COPC.LAZ": "AHN5 1\u00a0km file"}.get(c.get("data") or "", "AHN5")
        text = (f"Conditions: {cpu}, {vers}; {n_pts} points, {run_part}; {data} (CC BY 4.0). "
                f"Full: {self.RESULT_FILES[kind]}.")
        if kind == "memory":
            text = text.replace(" Full:", " 1\u00a0GB\u00a0=\u00a02³⁰\u00a0B. Full:")
        return text + self._label_suffix(kind)

    def _conditions_text(self, kind: str, plane_threads: bool = False) -> str:
        fname = self.RESULT_FILES[kind]
        c = self.res.lookup(f"{kind}.conditions")
        if not isinstance(c, dict):
            self.res._miss(f"{kind}.conditions", None, f"conditions ({kind})")
            return f"Conditions: [{kind}.conditions] pending ({fname})."

        def g(key, fmt=None, required=False):
            v = c.get(key)
            if v is None or v == "":
                if required:
                    self.res._miss(f"{kind}.conditions.{key}", fmt, f"conditions ({kind})")
                    return f"[{kind}.conditions.{key}]"
                return None
            if fmt == "int":
                try:
                    return fmt_int(float(v))
                except (TypeError, ValueError):
                    return str(v)
            if isinstance(v, float):
                return f"{v:g}"
            return str(v)

        hw = self._cpu(c) if g("cpu") else g("cpu", required=True)
        if g("cores"):
            # the hardware's cores and threads; each variant's own thread count is on its bar or in the notes
            hw += f", {g('cores')} cores" + (f" / {g('threads')} threads" if g("threads") else "")
        if g("ram_gib"):
            # the same machine, the same unit on every slide (GiB: the value is in 2^30 bytes)
            hw += f", {g('ram_gib')} GiB RAM"
        osv = g("os", required=True)
        # the result files record the distribution and the kernel; the kernel is Linux
        osv = f"Linux ({osv}" + (f", kernel {g('kernel')})" if g("kernel") else ")")
        libs = [("Python", "python"), ("NumPy", "numpy"), ("SciPy", "scipy"), ("Open3D", "open3d"),
                ("laspy", "laspy")]
        if kind == "facts":
            libs.append(("PyVista", "pyvista"))
            c = {**(c.get("extra") or {}), **c}              # PyVista's version is under extra
        if kind == "eigen":
            libs.append(("scikit-learn", "scikit_learn"))
            c = {**(c.get("extra") or {}), **c}              # scikit-learn's version is under extra
        vers = ", ".join(f"{label} {g(k)}" for label, k in libs if g(k)) or f"[{kind}.conditions.python]"
        if kind == "ft":
            # the timed interpreters (two throw-away venvs), not the driver's project venv
            b = self.res.lookup("ft.builds")
            if isinstance(b, dict) and "free_threaded" in b and "gil" in b:
                f_, d_ = b["free_threaded"], b["gil"]
                vers = (f"CPython {f_['python']} free-threaded build (sys._is_gil_enabled() returns "
                        f"{f_['gil_enabled_at_end']}) and the default build {d_['python']}, NumPy {f_['numpy']}, "
                        f"laspy {f_['laspy']}")
            else:
                self.res._miss("ft.builds", None, "conditions (ft)")
                vers = "[ft.builds]"
        n_pts = g("n", "int", required=True)
        runs = g("runs", required=True)
        stat = g("statistic", required=True)
        # internal JSON paths stay in the result file, not on the slide
        stat = re.sub(r"\s*\(min and max under [^)]*\)", "", stat)
        stat = re.sub(r"\s*\(numpy\.percentile[^)]*\)", "", stat)      # how the quartiles are computed: in the file
        warm = g("warmup")
        if warm in ("0", "0.0"):
            warm = None
        if kind == "profile":
            run_part = f"N = {n_pts} points, {stat}"
        elif kind == "eigen":
            # the features are computed on the voxels of the clusters, not on the original points
            run_part = f"N = {n_pts} voxels in clusters, {runs} runs" + (f" after {warm} warm-up" if warm else "") + f", {stat}"
        elif kind == "memory" and "fresh subprocess" in stat:
            run_part = f"N = {n_pts} points, median of {runs} runs, each in a fresh subprocess"
        else:
            run_part = f"N = {n_pts} points, {runs} runs" + (f" after {warm} warm-up" if warm else "") + f", {stat}"
        parts = [f"Conditions: {hw}; {osv}; {vers}", run_part]
        if kind == "bench" and plane_threads:
            # thread count of the plane runs (slide 18 only; the kNN variants carry their own on B1 and B4)
            th = [self.res.lookup(f"bench.plane.{v}.threads") for v in ("loop_numpy_rows", "vectorised")]
            cw = [self.res.lookup(f"bench.plane.{v}.cpu_over_wall_median") for v in ("loop_numpy_rows", "vectorised")]
            if all(isinstance(v, (int, float)) for v in th):
                txt = (f"plane loop and expression on {fmt_int(th[0])} thread each" if th[0] == th[1] else
                       f"plane loop on {fmt_int(th[0])}, expression on {fmt_int(th[1])} threads")
                if all(isinstance(v, (int, float)) for v in cw):
                    a_, b_ = f"{cw[0]:.1f}", f"{cw[1]:.1f}"
                    txt += f" (CPU/wall {a_})" if a_ == b_ else f" (CPU/wall {a_} and {b_})"
                parts.append(txt)
        if g("governor"):
            parts.append(f"governor {g('governor')}")
        if g("boost"):
            parts.append(f"boost {g('boost')}")
        if g("date_utc"):
            d = g("date_utc")
            m = re.match(r"(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2})", d)
            parts.append(f"measured {m.group(1)} {m.group(2)} UTC" if m else
                         f"measured {d}" + ("" if d.endswith(("Z", "UTC", "+00:00")) else " UTC"))
        # the data the numbers were measured on (data/DATA_LICENSE.md: the source wherever derived data is shown)
        data = {"data/utrecht_jaarbeurs_200m.laz": "data: the AHN5 crop of slide 5 (ahn.nl, ",
                "data/AHN5_C_135000_455000.COPC.LAZ": "data: AHN file 135000_455000 (AHN5, ahn.nl, "}.get(g("data") or "")
        if data:
            parts.append(data + "Het Waterschapshuis, CC BY 4.0)")
        text = "; ".join(parts) + "."
        if kind == "memory":
            # memory figures are increases over the process after its imports (memory.json tile_1km.units)
            text += " Memory: increase over the process after imports; 1\u00a0GB\u00a0=\u00a02³⁰\u00a0bytes."
        return text + self._label_suffix(kind)

    def conditions_block(self, s, n, kind, x, w, bottom=BOTTOM, note=None, plane_threads=False, short=False):
        """Conditions small print, bottom-aligned at `bottom`, height from its wrapped lines (the box itself is
        SMALL_PAD taller and bottom-anchored). Returns the top y of the text (so callers can stack above it)."""
        text = self.conditions_text(kind, note=note, n=n, plane_threads=plane_threads, short=short)
        h = text_h(text, SMALL_PT, w - 0.02)
        self.small(s, n, text, (x, bottom - h, w, h), name="Conditions", bottom=True)
        self.report.setdefault("conditions_lines", {})[str(n)] = round(h / lines_h(1, SMALL_PT))
        return bottom - h

    # ----------------------------------------------------------------------------- renders
    def render_info(self, file):
        p = RENDERS / file
        exp = EXPECTED_PX.get(file, DEFAULT_PX)
        info = {"exists": p.exists(), "expected_px": list(exp)}
        if p.exists():
            with Image.open(p) as im:
                info["px"] = list(im.size)
            if tuple(info["px"]) != exp:
                info["note"] = "size differs from the render spec: centre-cropped to the frame"
        self.report["renders"][file] = info
        return p, info

    def place_render(self, slide, n, file, frame, *, name, alt, idx=18):
        p, info = self.render_info(file)
        if p.exists():
            if idx is not None and placeholder(slide, idx) is not None:
                return insert_picture(slide, idx, p, name=name, descr=alt, geometry=frame), info
            return add_picture_fill(slide, p, *frame, name=name, descr=alt), info
        if idx is not None:
            drop_placeholder(slide, idx)
        exp = info["expected_px"]
        caption = f"RENDER PENDING: renders/{file}"
        detail = f"{exp[0]}×{exp[1]} px, fixed camera from renders/render_spec.json. Shows: {alt}"
        sh = pending_box(slide, *frame, caption, detail, dark=True, name=name)
        self.placeholder_note(n, "render", f"renders/{file}", caption + ". " + detail)
        return sh, info

    # ----------------------------------------------------------------------------- label chips
    CHIP_H, CHIP_PAD, CHIP_SW, CHIP_GAP = 0.44, 0.10, 0.18, 0.10   # padding 0.10: four Fira Sans chips fit the slide 4 frame
    RING_R = 0.08

    SF_LEADER_GAP = 0.08
    POINT_CLASSES = ("street_furniture",)

    def _point_bbox(self, frame_key, cls, union=False):
        """Pixel box [x0, y0, x1, y1] of a class drawn as enlarged objects (renders/render_spec.json
        frames[<frame_key>.png].street_furniture_visible), or None. Default: the topmost visible object (the one the
        chip anchor sits on, pipeline/render.py pick_anchors); union=True: the box around all of them."""
        if cls not in self.POINT_CLASSES:
            return None
        p = RENDERS / "render_spec.json"
        if not p.exists():
            return None
        if not hasattr(self, "_rspec"):
            self._rspec = json.loads(p.read_text(encoding="utf-8"))
        vis = (((self._rspec or {}).get("frames") or {}).get(f"{frame_key}.png") or {}).get(f"{cls}_visible") or {}
        patches = vis.get("patches") or []
        bb = patches[0]["bbox_px"] if patches and not union else vis.get("bbox_px")
        return bb if isinstance(bb, list) and len(bb) == 4 else None

    def _point_patches(self, frame_key, cls):
        """Boxes of every visible object of a point class, topmost first (see _point_bbox)."""
        self._point_bbox(frame_key, cls)          # loads render_spec.json
        vis = (((self._rspec or {}).get("frames") or {}).get(f"{frame_key}.png") or {}).get(f"{cls}_visible") or {}
        return [pt["bbox_px"] for pt in vis.get("patches") or []]

    def chip_width(self, label: str) -> float:
        return self.CHIP_PAD + self.CHIP_SW + self.CHIP_GAP + width_in(label, SIZES["chip"], bold=True) \
            + self.CHIP_PAD + 0.06

    def _cover_fn(self, file, frame):
        """Share of a chip rectangle (slide inches) that hides render content: background 0,
        ground / unlabelled 0.35, every other pixel 1. Uses a 1/4 scale copy of the render."""
        p = RENDERS / file
        if not p.exists():
            return None
        key = (file, tuple(round(v, 4) for v in frame))
        if key in self._cover_cache:
            return self._cover_cache[key]
        import numpy as np
        with Image.open(p) as im:
            im = im.convert("RGB")
            iw, ih = im.size
            small = np.asarray(im.resize((max(1, iw // 4), max(1, ih // 4)), Image.BILINEAR), dtype=np.int16)
        def dist(hexv):
            h = hexv.lstrip("#")
            c = np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], dtype=np.int16)
            return np.abs(small - c).sum(axis=2)

        weight = np.ones(small.shape[:2], dtype=np.float64)
        weight[dist(RENDER["background"]) < 40] = 0.0
        for k in ("ground", "unlabelled"):
            weight[dist(RENDER[k]) < 30] = 0.35
        integ = np.zeros((weight.shape[0] + 1, weight.shape[1] + 1))
        integ[1:, 1:] = weight.cumsum(0).cumsum(1)
        fx, fy, fw, fh = frame
        sh, sw_ = weight.shape

        def cover(r):
            x0 = int(round((r.x - fx) / fw * sw_)); x1 = int(round((r.x2 - fx) / fw * sw_))
            y0 = int(round((r.y - fy) / fh * sh)); y1 = int(round((r.y2 - fy) / fh * sh))
            x0, x1 = max(0, min(sw_, x0)), max(0, min(sw_, x1))
            y0, y1 = max(0, min(sh, y0)), max(0, min(sh, y1))
            area = max(1, (x1 - x0) * (y1 - y0))
            return float(integ[y1, x1] - integ[y0, x1] - integ[y1, x0] + integ[y0, x0]) / area

        self._cover_cache[key] = cover
        return cover

    def chip_layout(self, frame_key, frame, img_px, file, *, obstacles=(), reference=None, rules=None):
        """Placements for the chips of one labels.json frame drawn into `frame` (cached)."""
        key = (frame_key, tuple(round(v, 4) for v in frame), reference is not None, rules is not None)
        if key in self._chip_cache:
            return self._chip_cache[key]
        anchors = (self.labels or {}).get(frame_key)
        if not isinstance(anchors, dict):
            return None
        fx, fy, fw, fh = frame
        iw, ih = img_px
        names = self.meta.get("class_names", {})
        specs, labels = [], {}
        for cls in CLASSES:
            a = anchors.get(cls)
            if not (isinstance(a, (list, tuple)) and len(a) >= 2):
                continue
            label = names.get(cls, cls.replace("_", " ").capitalize())
            labels[cls] = label
            anchor = (fx + float(a[0]) * fw / iw, fy + float(a[1]) * fh / ih)
            bb = self._point_bbox(frame_key, cls)
            if bb is not None:
                # a one-object class drawn enlarged (street furniture: 9 points, about 0.1 in on the slide): a ring
                # around it would hide it, so the leader ends SF_LEADER_GAP above the object's box instead
                anchor = (fx + (bb[0] + bb[2]) / 2 * fw / iw, fy + bb[1] * fh / ih - self.SF_LEADER_GAP)
            specs.append(chips.ChipSpec(cls, anchor, self.chip_width(label), self.CHIP_H))
        frame_r = chips.Rect(*frame)
        placements, info = chips.place(specs, frame_r, obstacles=obstacles, cover=self._cover_fn(file, frame),
                                       reference=reference, rules=rules)
        info["violations"] = chips.violations(placements, frame_r, obstacles=obstacles, rules=rules)
        out = (placements, labels, info)
        self._chip_cache[key] = out
        return out

    def label_chips(self, slide, n, frame_key, frame, img_px, file, *, prefix="!!lab_", obstacles=(),
                    reference_key=None, only=None, rules=None):
        if not self.labels:
            self.placeholder_note(n, "labels", "renders/labels.json",
                                  "Label chips pending: renders/labels.json (anchor pixel per class)")
            return []
        if not isinstance(self.labels.get(frame_key), dict):
            self.placeholder_note(n, "labels", f"renders/labels.json[{frame_key}]",
                                  f"Label chips pending: no '{frame_key}' entry in renders/labels.json")
            return []
        reference = None
        if reference_key and reference_key != frame_key and isinstance(self.labels.get(reference_key), dict):
            ref = self.chip_layout(reference_key, frame, img_px, f"{reference_key}.png", obstacles=obstacles)
            if ref:
                reference = {p.cls: p.rect for p in ref[0]}
        if only:
            file = self.chip_layout_file.get(frame_key, file)
        placements, labels, info = self.chip_layout(frame_key, frame, img_px, file, obstacles=obstacles,
                                                    reference=reference, rules=rules)
        if only:
            placements = [p for p in placements if p.cls in set(only)]
        if not info.get("ok"):
            self.warn(n, f"label chips: {info.get('reason')}; fallback placement used")
        for v in info.get("violations") or []:
            self.warn(n, f"label chips: {v}")
        self.report.setdefault("label_chips", {})[str(n)] = {
            "frame": frame_key, "frame_in": [round(v, 3) for v in frame], "ok": info.get("ok"),
            "reused_reference": info.get("reused_reference"), "reference": reference_key if reference else None,
            "violations": info.get("violations"),
            "chips": {p.cls: {"side": p.side, "rect_in": [round(p.rect.x, 3), round(p.rect.y, 3), round(p.rect.w, 3),
                                                           round(p.rect.h, 3)],
                              "anchor_in": [round(p.anchor[0], 3), round(p.anchor[1], 3)]} for p in placements}}
        made = []
        fx, fy, fw, fh = frame
        iw, ih = img_px
        for p in placements:
            bb = self._point_bbox(frame_key, p.cls)
            if bb is not None:
                # a class drawn as enlarged objects: the leader stops SF_LEADER_GAP short of the object's edge that
                # faces the chip (the chip is below the anchor: bottom edge, and so on), so it never crosses the object
                x0_, y0_ = fx + bb[0] * fw / iw, fy + bb[1] * fh / ih
                x1_, y1_ = fx + (bb[2] + 1) * fw / iw, fy + (bb[3] + 1) * fh / ih
                g, (cx_, cy_) = self.SF_LEADER_GAP, ((x0_ + x1_) / 2, (y0_ + y1_) / 2)
                p.anchor = {"below": (cx_, y1_ + g), "above": (cx_, y0_ - g),
                            "right": (x1_ + g, cy_), "left": (x0_ - g, cy_)}.get(p.side, p.anchor)
            made.append(self._draw_chip(slide, p, labels[p.cls], f"{prefix}{p.cls}", ring=bb is None))
        return made

    def _draw_chip(self, slide, p, label, name, ring=True):
        """Label chip on a navy render: navy chip with a sage outline, white 20 pt bold label, the class swatch
        (render palette) on its left; white leader and anchor ring, each over a navy halo so they stay visible on
        white points. ring=False (street furniture): no ring, the leader ends just above the object."""
        ax, ay = p.anchor
        ex, ey = p.end
        L = max(1e-6, ((ex - ax) ** 2 + (ey - ay) ** 2) ** 0.5)
        r = self.RING_R if ring else 0.0
        sx, sy = ax + (ex - ax) / L * r, ay + (ey - ay) / L * r
        grp = slide.shapes.add_group_shape()
        line(grp, sx, sy, ex, ey, colour="background_dark", width_pt=3.5, name="Leader halo")
        line(grp, sx, sy, ex, ey, colour="text_dark", width_pt=1.25, name="Leader")
        for colour, w_pt, nm in ((("background_dark", 3.5, "Anchor halo"), ("text_dark", 1.5, "Anchor"))
                                 if ring else ()):
            ring = grp.shapes.add_shape(MSO_SHAPE.OVAL, E(ax - r), E(ay - r), E(2 * r), E(2 * r))
            ring.fill.background()
            ring.line.color.rgb = rgb(colour)
            ring.line.width = Pt(w_pt)
            ring.shadow.inherit = False
            set_name(ring, nm)
        cx, cy, cw, ch = p.rect.x, p.rect.y, p.rect.w, p.rect.h
        chip = rect(grp, cx, cy, cw, ch, fill="background_dark", line="highlight_dark", line_pt=1.0,
                    rounded=True, name="Chip")
        shape_text(chip, label, size=SIZES["chip"], colour="text_dark", bold=True, align="left", anchor="ctr",
                   insets=(self.CHIP_PAD + self.CHIP_SW + self.CHIP_GAP, 0.0, self.CHIP_PAD, 0.0), wrap=False)
        rect(grp, cx + self.CHIP_PAD, cy + (ch - self.CHIP_SW) / 2, self.CHIP_SW, self.CHIP_SW, fill=RENDER[p.cls],
             line="text_dark", line_pt=0.75, name="Swatch")
        set_name(grp, name)
        set_alt(grp, f"Label: {label}, pointing at the {label.lower()} in the render")
        return grp

    # ----------------------------------------------------------------------------- code
    def snippet(self, n, name, lang=None):
        sn = read_snippet(SNIPPETS, name, lang)
        run = None
        if self.snippet_runs:
            stem = Path(name).stem
            run = self.snippet_runs.get(name) or self.snippet_runs.get(stem) or \
                self.snippet_runs.get(stem.replace("_repl", ""))
        self.report["snippets"][f"slide {n}: {name}"] = {
            "file": str(sn.path.relative_to(TALK)) if sn.path and sn.path.is_relative_to(TALK) else (str(sn.path) if sn.path else None), "lines": len(sn.lines),
            "max_chars": sn.max_len, "key_lines": [k + 1 for k in sn.keys], "note": sn.note,
            "run": run if run is not None else ("NOT RUN (C++, no PCL toolchain)" if name.endswith(".cpp")
                                                else "no entry in results/snippets.json"),
        }
        return sn

    def code_or_pending(self, slide, n, sn, x, y, w, h, *, name, hl_name=None, muted=False,
                        max_chars=None, max_lines=None, line_pt=LINE_PT):
        if not sn.ok:
            caption = f"CODE PENDING: snippets/{sn.name}"
            detail = "Region between '# --- slide ---' and '# --- end ---'; key line marked '  # <<'."
            pending_box(slide, x, y, w, h, caption, detail, name=name)
            self.placeholder_note(n, "snippet", f"snippets/{sn.name}", caption)
            return None, None
        if max_lines and len(sn.lines) > max_lines:
            self.warn(n, f"{sn.name}: {len(sn.lines)} lines, box holds {max_lines} at 18 pt")
        # the code text starts on x (the column's text edge, in line with titles and captions); the box and its
        # key-line bar hang INSET_L into the margin, so the bar's blue edge sits left of the text
        need_w = code_width_in(sn.max_len) - INSET_L
        if need_w > w + 1e-6:
            self.warn(n, f"{sn.name}: longest line {sn.max_len} chars needs {need_w:.2f} in, column is {w:.2f} in")
        return add_code(slide, sn, x - INSET_L, y, w + INSET_L, h, name=name, hl_name=hl_name, muted=muted,
                        line_pt=line_pt)

    # ----------------------------------------------------------------------------- helpers
    def call_helper(self, slide, n, module, fn_name, box_in_, spec, *extra, caption, detail="", dark=False):
        mod = getattr(self, module)
        fn = getattr(mod, fn_name, None) if mod else None
        x, y, w, h = box_in_
        tree = slide.shapes._spTree
        before = len(tree)
        status = {"slide": n, "fn": f"{module}.{fn_name}"}
        if fn is None:
            status["status"] = "missing"
            pending_box(slide, x, y, w, h, caption, detail or f"Drawn by lib/{module}.py:{fn_name} (not available)",
                        dark=dark, name=f"PENDING {fn_name}")
            self.placeholder_note(n, "helper", f"lib/{module}.py:{fn_name}", caption)
            self.report["helper_calls"].append(status)
            return []
        try:
            out = fn(slide, box_emu(x, y, w, h), spec, STYLE, *extra)
            status["status"] = "ok"
        except Exception as exc:
            for el in list(tree)[before:]:
                tree.remove(el)
            status["status"] = "error"
            status["error"] = f"{type(exc).__name__}: {exc}"
            status["traceback"] = traceback.format_exc(limit=4)
            pending_box(slide, x, y, w, h, caption, f"lib/{module}.py:{fn_name} failed: {type(exc).__name__}",
                        dark=dark, name=f"PENDING {fn_name}")
            self.placeholder_note(n, "helper", f"lib/{module}.py:{fn_name}", caption + " (helper error)")
            out = []
        self.report["helper_calls"].append(status)
        self._mark_helper_placeholders(tree, before, n)
        # alt text on every new picture / chart / group / table
        alt = spec.get("alt") if isinstance(spec, dict) else None
        for el in list(tree)[before:]:
            tag = el.tag.split("}")[1]
            if tag in ("pic", "graphicFrame", "grpSp"):
                c = el.find(".//" + qn("p:cNvPr"))
                if c is not None and not c.get("descr") and alt:
                    c.set("descr", alt)
        return out

    def _mark_helper_placeholders(self, tree, before, n):
        """Helpers draw their own placeholders for missing renders / values; tag them for qa/checks.py."""
        for el in list(tree)[before:]:
            for sp in [el] + list(el.iter(qn("p:sp"))):
                if sp.tag != qn("p:sp"):
                    continue
                txt = "".join(t.text or "" for t in sp.iter(qn("a:t")))
                if re.search(r"\.png\b", txt) or txt.strip().startswith("[chart:") or "PENDING" in txt:
                    c = sp.find(".//" + qn("p:cNvPr"))
                    if c is not None:
                        c.set("title", "PENDING")

    def resolved_spec(self, spec, n):
        s = self.res.resolve_tree(copy.deepcopy(spec), where=f"slide {n}")
        return s

    # ============================================================================ slides
    def build_slide(self, slide, spec, n):
        layout = int(spec["layout"])
        # content.yaml `build` names the method (slide_<build>), so slides can be inserted and renumbered freely
        if str(n)[0] in "BC" and spec.get("build") != "concept":
            fn = self.slide_dense
        else:
            fn = getattr(self, f"slide_{spec.get('build')}", None) or self.slide_generic
        fn(slide, spec, n, layout)

    # title -- title slide (L1, navy): title, the code joke in the subtitle, presenter line, logo zone
    def slide_title(self, s, spec, n, L):
        self.set_title(s, n, spec["title"], L)
        sub = placeholder(s, 1)
        if sub is not None and not spec.get("subtitle_code"):
            drop_placeholder(s, 1)   # no code joke: no empty prompt box
        elif sub is not None:
            # the layout's subtitle slot (Fira Mono 24 pt, two lines fit); geometry inherited from the layout
            tf = sub.text_frame
            p = clear_text_frame(tf)
            set_body_pr(tf, wrap=False, autofit="none")
            lines = [self.R(x, n) for x in spec.get("subtitle_code", [])]
            box = GEO.ph(L, 1)
            for line_ in lines:
                if width_in(line_, 24, font="mono") > box.w:
                    self.warn(n, f"code joke line wider than the subtitle slot ({box.w:.2f} in): {line_!r}")
            for i, toks in enumerate(tokenize(lines, "python", dark=True)):
                if i:
                    p = tf.add_paragraph()
                para_format(p, align="left", line_pt=28)
                for text, colour, bold, italic in toks:
                    add_run(p, text, font="mono", size=24, colour=colour, bold=bold, no_proof=True)
                end_para_size(p, 24)
            set_name(sub, "Code joke")
        pres = placeholder(s, 13)
        if pres is not None:
            # bottom-anchored in the layout; a presenter line wider than the slot breaks before the repo URL
            box = GEO.ph(L, 13)
            text = self.R(spec.get("presenter", ""), n)
            parts = [text]
            if width_in(text, 24) > box.w - 0.05 and " · " in text:
                parts = list(text.rsplit(" · ", 1))
            tf = pres.text_frame
            p = clear_text_frame(tf)
            for i, part in enumerate(parts):
                if i:
                    p = tf.add_paragraph()
                para_format(p, align="left")
                add_text_runs(p, part, font="minor", size=24, colour="text_dark")
                end_para_size(p, 24)
                if width_in(part, 24) > box.w - 0.05:
                    self.warn(n, f"presenter line wider than {box.w:.2f} in: {part!r}")
            set_name(pres, "Presenter")
        self._logo_zone(s, n, L, spec)

    def _logo_zone(self, s, n, L, spec):
        """The layout's logo zone (pic idx 16) holds a labelled placeholder until the PyCon NL logo file and
        permission exist; the empty picture placeholder is removed so no master prompt shows."""
        drop_placeholder(s, 16)
        if spec.get("logo"):
            # square logo on a white rounded tile at the right end of the zone (its outline is navy, so it needs a
            # light ground on the navy title/closing slides)
            x, y, w, h = GEO.ph(L, 16).t()
            tile = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, E(x + w - h), E(y), E(h), E(h))
            tile.fill.solid()
            tile.fill.fore_color.rgb = rgb(COLOURS["white"])
            tile.line.fill.background()
            set_name(tile, "Logo tile")
            set_alt(tile, "")
            pad = 0.06
            add_picture_fill(s, DECK / spec["logo"]["file"], x + w - h + pad, y + pad, h - 2 * pad, h - 2 * pad,
                             name="Logo", descr=spec["logo"]["alt"])
        elif spec.get("logo_placeholder"):
            pending_box(s, *GEO.ph(L, 16).t(), self.R(spec["logo_placeholder"], n), None, dark=True,
                        name="PENDING logo")
            self.placeholder_note(n, "logo", "PyCon NL logo", spec["logo_placeholder"])

    # two_code -- two code columns (L5), optional one-line install box under the right column
    def _two_code(self, s, spec, n, L, support_y=None, support_gap=0.30):
        lines = self.set_title(s, n, spec["title"], L)
        top = content_top(L, lines)
        drop_placeholder(s, 1)
        drop_placeholder(s, 2)
        cap_h = lines_h(1, 20) + 0.08
        sides = [("left", X0), ("right", XR)]
        sns = {}
        for side, x in sides:
            col = spec[side]
            sns[side] = self.snippet(n, col["snippet"], col.get("lang"))
        n_lines = max(len(sns["left"].lines), len(sns["right"].lines), 1)
        sp = self.R(spec["small_print"], n) if spec.get("small_print") else ""
        sph = text_h(sp, SMALL_PT, FULL_W - 0.02) if sp else 0.0
        floor = support_y if support_y is not None else BOTTOM - (sph + 0.15 if sp else 0.0)
        avail = floor - (top + cap_h) - 0.1
        h = min(code_height_in(n_lines), avail)
        side_h = {}
        for side, x in sides:
            col = spec[side]
            muted = bool(col.get("muted"))
            if col.get("caption"):
                text_block(s, x, top, COL_W, cap_h, self.R(col["caption"], n), size=20, font="title",
                           colour="text_small" if muted else "title", name=f"Caption {side}")
            # each code box as tall as its own lines, so a box under the shorter column does not overlap it
            side_h[side] = min(code_height_in(max(len(sns[side].lines), 1)), avail)
            # key-line bars named per column ("Key line left" / "Key line right"): unique names on the slide
            self.code_or_pending(s, n, sns[side], x, top + cap_h, COL_W, side_h[side],
                                 name=f"Code {side}", hl_name=f"Key line {side}", muted=muted,
                                 max_lines=int((avail - 0.1) * 72 / LINE_PT))
            if col.get("output"):
                # what the program printed when it ran (content.yaml `output`, from results/snippets.json), as a
                # two-line terminal box under the code: "# output" and the printed line (2026-10-12: both sides run)
                out = self.R(col["output"], n)
                osn = Snippet(name=f"output {side}", path=None, lines=["# output", out], keys=[], key=None, ok=True,
                              lang="bash")
                oy = top + cap_h + side_h[side] + 0.30
                add_code(s, osn, x - INSET_L, oy, COL_W + INSET_L, code_height_in(2), name=f"Code output {side}",
                         muted=muted)
                side_h[side] += 0.30 + code_height_in(2)
        inst = spec.get("install")
        if inst:
            # the one-line install, a separate code box 0.45 in under the Python code (Fira Mono 18 pt)
            texts = [self.R(t, n) for t in (inst["text"] if isinstance(inst["text"], list) else [inst["text"]])]
            sn = Snippet(name="install", path=None, lines=texts, keys=[], key=None, ok=True,
                         lang=inst.get("lang", "bash"))
            need = code_width_in(sn.max_len) - INSET_L
            if need > COL_W + 1e-6:
                self.warn(n, f"install line needs {need:.2f} in, the column is {COL_W:.2f} in")
            y = top + cap_h + side_h["right"] + 0.45
            box, _ = add_code(s, sn, XR - INSET_L, y, COL_W + INSET_L, code_height_in(len(texts)),
                              name="Code install")
            if inst.get("alt"):
                set_alt(box, self.R(inst["alt"], n))
        if support_y is not None and spec.get("support"):
            sup = self.R(spec["support"], n)
            sh = text_h(sup, SUPPORT_PT, FULL_W - 0.02)
            y_sup = min(top + cap_h + max(h, 1.0) + support_gap, support_y)
            self.support(s, n, sup, (X0, y_sup, FULL_W, sh))
        if sp:
            # 12 pt small print on the bottom edge
            self.small(s, n, sp, (X0, BOTTOM - sph, FULL_W, sph), bottom=True)

    def slide_two_code(self, s, spec, n, L):
        self._two_code(s, spec, n, L)

    # handoffs -- rows "code | copy/view | consequence" (L4), conditions on the bottom edge
    def slide_handoffs(self, s, spec, n, L):
        lines = self.set_title(s, n, spec["title"], L)
        top = content_top(L, lines)
        drop_placeholder(s, 1)
        for r in spec.get("rows") or []:
            key = r.get("verify")
            v = self.res.lookup(key) if key else None
            if v is not True:
                self.warn(n, f"hand-off {r.get('code')!r} shown as {r.get('kind')!r}, but {key} is {v!r}")
        cond_y = self.conditions_block(s, n, spec["conditions"], X0, FULL_W, note=spec.get("conditions_note"),
                                       short=bool(spec.get("conditions_short"))) if spec.get("conditions") else BOTTOM
        sub = self.helper_spec(spec, n, None)
        rows_top, rows_bottom = top, cond_y - 0.25
        if spec.get("legend"):
            # what copy and view mean, drawn above the rows (2026-10-12): two names on two blocks, two on one
            lg = dict(sub["legend"])
            lg.update({"name": "Copy or view", "alt": "Legend. Copy: two names, each on its own block of memory; "
                       + lg["copy"]["text"] + ". View: two names on one block of memory; " + lg["view"]["text"] + "."})
            lh = self.sketches.copy_view_legend_height() if self.sketches else 1.2
            self.call_helper(s, n, "sketches", "add_copy_view_legend", (X0, top, FULL_W, lh), lg,
                             caption="DIAGRAM PENDING: copy or view legend")
            rule = line(s, X0, top + lh + 0.08, X0 + FULL_W, top + lh + 0.08, colour="tile", width_pt=1.0,
                        name="Legend rule")
            mark_decorative(rule)
            rows_top = top + lh + 0.16
        if spec.get("support"):
            sup = self.R(spec["support"], n)
            sh = text_h(sup, SUPPORT_PT, FULL_W - 0.02)
            sy = cond_y - 0.20 - sh
            self.support(s, n, sup, (X0, sy, FULL_W, sh))
            rows_bottom = sy - 0.30
        sub = {"rows": sub["rows"], "pills": sub.get("pills"), "alt": sub.get("alt"), "name": "Handoffs",
               **({"row_gap_in": 0.10} if spec.get("legend") else {})}
        self.call_helper(s, n, "diagrams", "add_handoff_rows", (X0, rows_top, FULL_W, rows_bottom - rows_top), sub,
                         caption="DIAGRAM PENDING: hand-off rows")

    # profile -- the Scalene command and one bar per line of the slide-19 loop (L4)
    def slide_profile(self, s, spec, n, L):
        lines = self.set_title(s, n, spec["title"], L)
        top = content_top(L, lines)
        drop_placeholder(s, 1)
        self._line_profile(s, spec, n, top)

    def _line_profile(self, s, spec, n, top):
        """Slide 23 (2026-10-12, speaker: use Scalene): the command in a code box, then the slide-19 lines with a
        Scalene-style bar each (Python / native / system share of the run), from results/profile_scalene.json."""
        lp = spec["line_profile"]
        cmd = lp["command"]
        sn = Snippet(name="profile command", path=None, lines=[cmd], keys=[], key=None, ok=True, lang="console")
        ch = code_height_in(1)
        add_code(s, sn, X0 - INSET_L, top, FULL_W + INSET_L, ch, name="Code profile command", hl_name="Key line profile")
        cond_y = self.conditions_block(s, n, spec["conditions"], X0, FULL_W, note=spec.get("conditions_note"),
                                       short=bool(spec.get("conditions_short"))) if spec.get("conditions") else BOTTOM
        sup = self.R(spec["support"], n) if spec.get("support") else ""
        sup_h = text_h(sup, SUPPORT_PT, FULL_W - 0.02) if sup else 0.0
        sup_y = cond_y - 0.20 - sup_h
        rows = []
        for r in lp["rows"]:
            d = self.res.lookup(f"prof.lines.{r['line']}")
            if not isinstance(d, dict):
                self.res._miss(f"prof.lines.{r['line']}", None, f"slide {n} line profile")
                continue
            tot = d["total"]
            txt = "0\u00a0%" if tot == 0 else (f"{tot:.0f}\u00a0%" if tot >= 10 else f"{tot:.1f}\u00a0%")
            rows.append({"tag": r.get("tag"), "code": d["code"], "python": d["python"], "native": d["native"],
                         "system": d["system"], "total_text": txt, "key": r.get("key"), "gap": r.get("gap")})
        y = top + ch + 0.30
        h_lp = sup_y - 0.25 - y
        self.call_helper(s, n, "sketches", "add_line_profile", (X0, y, FULL_W, h_lp),
                         {"rows": rows, "legend": lp["legend"], "alt": self.R(lp.get("alt"), n),
                          "name": "Line profile"}, caption="CHART PENDING: line profile")
        if sup:
            self.support(s, n, sup, (X0, sup_y, FULL_W, sup_h))

    # split_renders -- two portrait frames side by side (L4): raw | labelled, same camera, same scale
    def _anchor(self, ref):
        """'frame.key' -> [x_px, y_px] from renders/labels.json, or None."""
        if not ref or not self.labels or "." not in str(ref):
            return None
        frame_key, key = str(ref).split(".", 1)
        a = (self.labels.get(frame_key) or {}).get(key)
        return a if isinstance(a, (list, tuple)) and len(a) >= 2 else None

    @staticmethod
    def _split_alt(alt, n_frames):
        """Alt text per frame from the slide alt 'Intro. Left half: ... Right half: ...'."""
        if not alt or n_frames != 2 or " Right half: " not in alt:
            return [alt] * n_frames
        head, right = alt.split(" Right half: ", 1)
        intro = head.split(" Left half: ", 1)[0]
        return [head, f"{intro} Right half: {right}"]

    def slide_split_renders(self, s, spec, n, L):
        lines = self.set_title(s, n, spec["title"], L)
        top = content_top(L, lines)
        drop_placeholder(s, 1)
        vis = spec["visual"]
        files = list(vis.get("files") or ([vis["file"]] if vis.get("file") else []))
        if vis.get("kind") != "side_by_side" or len(files) != 2:
            self.warn(n, f"slide 4 expects visual.kind side_by_side with two files, got {vis.get('kind')} {files}")
        infos = [self.render_info(f)[1] for f in files]
        pxs = [tuple(i.get("px") or DEFAULT_PX) for i in infos]
        # vertical budget: captions, frames, support line, source line; all inside top .. BOTTOM
        has_caps = bool(spec.get("split_captions"))
        cap_h, gap_x = (lines_h(1, 20) + 0.06 if has_caps else 0.0), 0.95
        src_txt = self.source_text(spec["source"]) if spec.get("source") else ""
        src_h = text_h(src_txt, SMALL_PT, FULL_W - 0.02) if src_txt else 0
        sup_txt = self.R(spec.get("support"), n) if spec.get("support") else ""
        sup_h = text_h(sup_txt, SUPPORT_PT, FULL_W - 0.02) if sup_txt else 0
        src_y = BOTTOM - src_h
        # 0.17 in between support and source line (0.20 in between frames and support): the two text lines read as
        # separate blocks, and the frames shrink to about 4.2 in (centred, same scale)
        sup_y = src_y - 0.17 - sup_h
        frame_y = top + (cap_h + 0.06 if has_caps else 0.0)
        frame_h = sup_y - 0.20 - frame_y
        # the data set table (content.yaml `specs`, 2026-10-12) takes the right of the body; the frames the rest
        specs = spec.get("specs")
        table_w = 3.95 if specs else 0.0
        row_avail = FULL_W - (table_w + 0.55 if specs else 0.0)
        # one scale for both frames: as tall as the body allows, as wide as the row allows
        scale = frame_h / max(ph for _, ph in pxs)
        scale = min(scale, (row_avail - gap_x * (len(pxs) - 1)) / sum(pw for pw, _ in pxs))
        # centre the row of frames in the content width (support and source lines stay on the margin); with the
        # table, the frames start on the margin
        row_w = sum(pw for pw, _ in pxs) * scale + gap_x * (len(pxs) - 1)
        frames, x = [], X0 + (0.0 if specs else max(0.0, (FULL_W - row_w) / 2))
        for pw, ph in pxs:
            frames.append((x, frame_y, pw * scale, ph * scale))
            x += pw * scale + gap_x
        self.report.setdefault("slide3_layout", {}).update(
            {"frames_in": [[round(v, 3) for v in f] for f in frames], "scale_in_per_px": round(scale, 6)})
        alts = [self.R(a, n) for a in (vis.get("alts") or [])]
        if len(alts) != len(files):
            alts = self._split_alt(self.R(spec.get("alt"), n), len(files))
        caps = [self.R(c, n) for c in (spec.get("split_captions") or [])]
        for i, (file, fr) in enumerate(zip(files, frames)):
            if i < len(caps):
                cw = fr[2] + (gap_x - 0.1 if i == 0 else 0.0)
                if width_in(caps[i], 20, bold=True) > cw:
                    self.warn(n, f"caption {i + 1} wider than its frame")
                text_block(s, fr[0], top, cw, cap_h, caps[i], size=20, bold=True, colour="title",
                           anchor="b", name=f"Caption {i + 1}", wrap=False)
            self.place_render(s, n, file, fr, name=f"Render {'raw' if i == 0 else 'labels'}", alt=alts[i], idx=None)
        if len(frames) == 2:                     # highlight arrow between the frames (on white: blue)
            l, r = frames
            aw, ah = 0.56, 0.44
            ax = l[0] + l[2] + (gap_x - aw) / 2
            ay = l[1] + l[3] / 2 - ah / 2
            arrow = s.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, E(ax), E(ay), E(aw), E(ah))
            arrow.fill.solid()
            arrow.fill.fore_color.rgb = rgb("highlight")
            arrow.line.fill.background()
            arrow.shadow.inherit = False
            set_name(arrow, "Arrow raw to labels")
            mark_decorative(arrow)
        ea = spec.get("edge_arrow")
        if ea and frames:
            txt = self.R(ea.get("text") if isinstance(ea, dict) else ea, n)
            ref = ea.get("anchor") if isinstance(ea, dict) else None
            anchor = self._anchor(ref)
            target = 0
            if ref:
                fk = str(ref).split(".", 1)[0]
                target = next((i for i, f in enumerate(files) if Path(f).stem == fk), 0)
            fx, fy, fw, fh = frames[target]
            pw, ph = pxs[target]
            if anchor is None:
                self.warn(n, f"edge arrow anchor {ref!r} not in renders/labels.json: arrow placed at the bottom "
                             "centre of the frame, check against the render")
                ex, ey = fx + fw / 2, fy + fh - 0.06
            else:
                ex, ey = fx + float(anchor[0]) * fw / pw, fy + float(anchor[1]) * fh / ph
            descr = self.R(ea.get("descr"), n) if isinstance(ea, dict) and ea.get("descr") else None
            # a long arrow lifts the chip clear of the tower at the crop's south edge; the tip stays on the anchor
            self._edge_arrow(s, txt, ex, ey, frames[target], descr=descr, ah=0.78)
        if spec.get("labels_from"):
            fk = spec["labels_from"]
            i = next((i for i, f in enumerate(files) if Path(f).stem == fk), len(files) - 1)
            # the slide 4 frame is about 3.7 in wide: four 20 pt chips fit only with a 0.06 in frame margin (the
            # default 0.10 leaves no valid place for Buildings between the other anchors)
            self.label_chips(s, n, fk, frames[i], pxs[i], files[i], prefix="Label ", rules=chips.Rules(margin=0.06))
        if specs:
            sub = self.resolved_spec(specs, n)
            sub["name"] = "Data set"
            tx = X0 + FULL_W - table_w
            th = min(frame_h, 24 * LINE_EM / 72 + 0.16 + 0.46 * len(sub["rows"]))
            self.call_helper(s, n, "sketches", "add_spec_table", (tx, frame_y, table_w, th), sub,
                             caption="TABLE PENDING: data set")
            from lib.measure import width_in as _w
            for a_, b_ in sub["rows"]:
                if _w(a_, 20, font="title") + 0.30 + _w(b_, 20) > table_w:
                    self.warn(n, f"data set row {a_!r}: {b_!r} wider than the table ({table_w:.2f} in)")
        if sup_txt:
            self.support(s, n, sup_txt, (X0, sup_y, FULL_W, sup_h))
        if src_txt:
            self.source(s, n, spec.get("source"), (X0, src_y, FULL_W, src_h))

    def _edge_arrow(self, s, txt, ex, ey, frame, descr=None, ah=0.40):
        """Down arrow (sage, the highlight on navy, navy outline) whose tip sits on (ex, ey), label chip (navy, sage
        outline, white text) above it, both inside `frame`."""
        fx, fy, fw, fh = frame
        aw, ch, gap, m = 0.30, 0.46, 0.06, 0.10
        tw = width_in(txt, 20, bold=True) + 0.30
        ey = min(ey, fy + fh - 0.02)
        cx = min(max(ex - tw / 2, fx + m), fx + fw - m - tw)
        cy = ey - ah - gap - ch
        grp = s.shapes.add_group_shape()
        arrow = grp.shapes.add_shape(MSO_SHAPE.DOWN_ARROW, E(ex - aw / 2), E(ey - ah), E(aw), E(ah))
        arrow.fill.solid()
        arrow.fill.fore_color.rgb = rgb("highlight_dark")
        arrow.line.color.rgb = rgb("background_dark")
        arrow.line.width = Pt(1.0)
        arrow.shadow.inherit = False
        set_name(arrow, "Edge arrow")
        chip = rect(grp, cx, cy, tw, ch, fill="background_dark", line="highlight_dark", line_pt=1.25, rounded=True,
                    name="Edge label")
        shape_text(chip, txt, size=20, colour="text_dark", bold=True, align="centre", anchor="ctr",
                   insets=(0.10, 0.0, 0.10, 0.0), wrap=False)
        set_name(grp, "Edge arrow Jaarbeurs")
        set_alt(grp, descr or f"Arrow: {txt}, beyond this edge of the crop")
        self.report.setdefault("slide3_layout", {})["edge_arrow_tip_in"] = [round(ex, 3), round(ey, 3)]
        return grp

    # render_column -- render and text column (L7: text left, render right, as on the Morph slides, so the title stays on the 0.600
    # margin from slide 4 to 6; L8 mirrors it)
    def slide_render_column(self, s, spec, n, L):
        lines = self.set_title(s, n, spec["title"], L)
        top = content_top(L, lines)
        drop_placeholder(s, 14)
        frame, col = (MEDIA_R, L7_TEXT) if L == 7 else (MEDIA_L, L8_TEXT)
        self.place_render(s, n, spec["visual"]["file"], frame, name="Render closeup", alt=self.R(spec.get("alt"), n))
        t = spec.get("text") or {}
        sup_y = top
        if t.get("snippet"):
            sn = self.snippet(n, t["snippet"], t.get("lang"))
            h = max(code_height_in(max(len(sn.lines), 1)), 1.2)
            self.code_or_pending(s, n, sn, col.x, top, col.w, h, name="Code REPL", max_lines=10)
            sup_y = top + h + 0.35                 # the attribute columns belong right under the array
        sup = self.R(spec.get("support"), n) if spec.get("support") else ""
        if sup:
            self.support(s, n, sup, (col.x, sup_y, col.w, text_h(sup, SUPPORT_PT, col.w - 0.02)))
        self._column_source(s, n, spec, col)

    def _column_source(self, s, n, spec, col):
        """Source line on the bottom edge of a text column (L7/L8), as tall as its wrapped lines."""
        if not spec.get("source"):
            return None
        txt = self.source_text(spec["source"])
        h = text_h(txt, SMALL_PT, col.w - 0.02)
        return self.source(s, n, spec["source"], (col.x, BOTTOM - h, col.w, h))

    # -- projection of local points into a render (renders/render_spec.json camera), for the poles on expectation_map
    def _render_spec(self):
        if not hasattr(self, "_rspec"):
            p = RENDERS / "render_spec.json"
            self._rspec = json.loads(p.read_text(encoding="utf-8")) if p.exists() else None
        return self._rspec

    def project(self, pts, px):
        """Local points (m, origin = LAS header.mins) -> image pixels with the one stored camera (VTK perspective,
        vertical view angle, window = the image), as pipeline/render.py world_to_pixel does."""
        import numpy as np
        cam = self._render_spec()["camera"]
        P, F, U = (np.asarray(cam[k], float) for k in ("position", "focal_point", "view_up"))
        d = (F - P) / np.linalg.norm(F - P)
        r = np.cross(d, U)
        r /= np.linalg.norm(r)
        u = np.cross(r, d)
        w, h = px
        f = 1.0 / np.tan(np.radians(float(cam["view_angle"])) / 2)
        X = np.atleast_2d(np.asarray(pts, float)) - P
        xc, yc, zc = X @ r, X @ u, X @ d
        nx, ny = f / (w / h) * xc / zc, f * yc / zc
        return np.c_[(nx + 1) / 2 * w, h - (ny + 1) / 2 * h]

    # ecosystem / filmstrip -- native diagrams (L4)
    def _l4_diagram(self, s, spec, n, L, fn, caption, *extra, key=None):
        lines = self.set_title(s, n, spec["title"], L)
        top = content_top(L, lines)
        drop_placeholder(s, 1)
        return self.call_helper(s, n, "diagrams", fn, (X0, top, FULL_W, BOTTOM - top), self.helper_spec(spec, n, key),
                                *extra, caption=caption)

    def helper_spec(self, spec, n, key):
        """diagrams.py takes the slide's sub-dict (visual / table / ...) plus the resolved alt text."""
        rs = self.resolved_spec(spec, n)
        sub = dict(rs[key]) if key else dict(rs)
        if rs.get("alt") and "alt" not in sub:
            sub["alt"] = rs["alt"]
        return sub

    def slide_ecosystem(self, s, spec, n, L):
        self._l4_diagram(s, spec, n, L, "add_ecosystem_map", "DIAGRAM PENDING: ecosystem map (6 steps, 6 libraries)",
                         key="visual")

    def slide_filmstrip(self, s, spec, n, L):
        # the thumbnails are AHN renders: source line on the bottom edge, the filmstrip centred above it
        lines = self.set_title(s, n, spec["title"], L)
        top = content_top(L, lines)
        drop_placeholder(s, 1)
        src_txt = self.source_text(spec["source"]) if spec.get("source") else ""
        src_h = text_h(src_txt, SMALL_PT, FULL_W - 0.02) if src_txt else 0
        self.call_helper(s, n, "diagrams", "add_filmstrip", (X0, top, FULL_W, BOTTOM - src_h - 0.10 - top),
                         self.helper_spec(spec, n, "visual"), RENDERS,
                         caption="DIAGRAM PENDING: filmstrip of the six frames")
        if src_txt:
            self.source(s, n, spec["source"], (X0, BOTTOM - src_h, FULL_W, src_h))
        if not any(sh.name == "!!render" for sh in s.shapes):
            pics = [sh for sh in s.shapes if sh.shape_type == 13]
            if pics:
                set_name(pics[0], "!!render")
            else:
                self.warn(n, "no picture to name !!render on the filmstrip slide (renders pending?)")

    # logo_wall -- rows of logo tiles (L4): the ecosystem of libraries and the companies behind them (slide 4).
    # Every id of a row resolves in deck/ecosystem/ecosystem.yaml (entries and orgs); the logo files are in
    # deck/assets/logos/. An id without a logo file becomes a text tile and is listed in the build report.
    def ecosystem(self) -> dict:
        if not hasattr(self, "_eco"):
            path = DECK / "ecosystem" / "ecosystem.yaml"
            data = _load_yaml(path) if path.exists() else {}
            self._eco = {e["id"]: e for e in list(data.get("entries") or []) + list(data.get("orgs") or [])}
        return self._eco

    def slide_logo_wall(self, s, spec, n, L):
        lines = self.set_title(s, n, spec["title"], L)
        top = content_top(L, lines)
        drop_placeholder(s, 1)
        eco = self.ecosystem()
        sp = self.R(spec["small_print"], n) if spec.get("small_print") else ""
        sph = text_h(sp, SMALL_PT, FULL_W - 0.02) if sp else 0.0
        wall = {"rows": [], "alt": self.R(spec.get("alt"), n), "name": "ecosystem_wall"}
        for r in spec["wall"]["rows"]:
            items = []
            for it in r["ids"]:
                key, cap = (it["id"], bool(it.get("caption"))) if isinstance(it, dict) else (it, False)
                used = bool(it.get("used")) if isinstance(it, dict) else False
                short = it.get("name") if isinstance(it, dict) else None     # a shorter name for the caption
                e = eco.get(key)
                if e is None:
                    self.warn(n, f"ecosystem id {key!r} is not in deck/ecosystem/ecosystem.yaml")
                    items.append({"name": key, "used": used})
                    continue
                logo = e.get("logo") or {}
                items.append({"name": short or e["name"], "file": logo.get("file"), "caption": cap, "used": used})
            wall["rows"].append({"label": r["label"], "items": items, "kind": r.get("kind")})
        for k in ("label_w_in", "gap_in", "row_gap_in", "pad_in"):
            if k in spec["wall"]:
                wall[k] = spec["wall"][k]
        bottom = BOTTOM - (sph + 0.15 if sp else 0.0)
        self.call_helper(s, n, "diagrams", "add_logo_wall", (X0, top + 0.05, FULL_W, bottom - top - 0.05), wall,
                         DECK / "assets" / "logos", caption="DIAGRAM PENDING: ecosystem logo wall")
        miss = [i["name"] for r in wall["rows"] for i in r["items"] if not i.get("file")]
        if miss:
            self.report.setdefault("logo_wall_text_tiles", {})[str(n)] = miss
        if sp:
            self.small(s, n, sp, (X0, BOTTOM - sph, FULL_W, sph), bottom=True)

    # morph -- Morph chain (L7): identical names and boxes on every slide (self.morph)
    def slide_morph(self, s, spec, n, L):
        self.set_title(s, n, spec["title"], L, name="!!title")
        drop_placeholder(s, 14)
        vis = spec["visual"]
        pic, info = self.place_render(s, n, vis["file"], MEDIA_R, name="!!render", alt=self.R(spec.get("alt"), n))
        sn = self.snippet(n, spec["code"]["snippet"])
        code = self.morph["code"]
        self.code_or_pending(s, n, sn, *code, name="!!code", hl_name="!!hl",
                             max_lines=int((code[3] - INSET_T - INSET_B) * 72 / LINE_PT + 1e-6))
        self.support(s, n, spec.get("support"), self.morph["support"], name="!!support")
        if spec.get("small_print"):
            # same box and name on every Morph slide that has one (12 to 14), so it stays still
            self.small(s, n, spec["small_print"], self.morph["small"], name="!!small")
            sup = self.R(spec.get("support"), n) or ""
            n_sup = len(wrap_lines(sup, SUPPORT_PT, L7_TEXT.w - 0.02, font="minor"))
            sup_bottom = self.morph["support"][1] + lines_h(n_sup, SUPPORT_PT)
            if self.morph["small"][1] - sup_bottom < 0.20:
                self.warn(n, f"support line ends {sup_bottom:.2f} in, small print starts {self.morph['small'][1]:.2f} in")
        self.source(s, n, spec.get("source"), self.morph["src"], name="!!src")
        if spec.get("callout"):
            self._callout(s, n, spec["callout"], MEDIA_R)
        if spec.get("sketch"):
            # what the step does, as a small schematic in the render's top-right corner (2026-10-12; lib/sketches.py).
            # Named per kind, not "!!", so Morph fades one sketch into the next instead of morphing shapes.
            sk = self.resolved_spec(spec["sketch"], n)
            sk["name"] = f"Sketch {sk['kind']}"
            self.call_helper(s, n, "sketches", "add_step_sketch", self.SKETCH_RECT, sk,
                             caption=f"SKETCH PENDING: {sk['kind']}", dark=True)
        if spec.get("labels_from"):
            px = tuple(info.get("px") or DEFAULT_PX)
            self.label_chips(s, n, spec["labels_from"], MEDIA_R, px, vis["file"], reference_key=self.morph_chip_ref,
                             only=spec.get("labels_only"), obstacles=self.chip_obstacles)


    # the step sketch on the Morph slides: top-right corner of the render frame (the other corners hold the Zen
    # callout, the street furniture and the ground chip); every chip on 11 to 17 keeps clear of it, so the chips
    # stay in the same place through the Morph chain and on the summary slide
    SKETCH_W, SKETCH_H, SKETCH_M = 2.55, 1.70, 0.12
    SKETCH_RECT = (MEDIA_R[0] + MEDIA_R[2] - SKETCH_W - SKETCH_M, MEDIA_R[1] + SKETCH_M, SKETCH_W, SKETCH_H)

    @property
    def chip_obstacles(self):
        return (chips.Rect(*self.SKETCH_RECT),)

    CALLOUT_PT, CALLOUT_LINE_PT = 18, 22

    def _callout(self, s, n, spec, frame):
        """A small REPL callout in the render's top-left corner (the navy sky above the street): navy box, sage
        outline, Fira Mono 18 pt; '>>> ' prompts in sage, the rest white (content.yaml `callout`, joke slide 13)."""
        fx, fy, fw, fh = frame
        lines = [self.R(x, n) for x in spec["lines"]]
        pad_x, pad_y = 0.14, 0.08
        w = max(len(x) for x in lines) * 0.6 * self.CALLOUT_PT / 72 + 2 * pad_x + 0.04
        h = len(lines) * self.CALLOUT_LINE_PT / 72 + 2 * pad_y
        if w > fw - 0.30:
            self.warn(n, f"callout {w:.2f} in wide, render frame {fw:.2f} in")
        box = rect(s, fx + 0.15, fy + 0.15, w, h, fill="background_dark", line="highlight_dark", line_pt=1.0,
                   rounded=True, name="Zen callout")
        tf = box.text_frame
        set_body_pr(tf, wrap=False, anchor="ctr", autofit="none", insets=(pad_x, pad_y, pad_x, pad_y))
        for i, ln in enumerate(lines):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            para_format(p, align="left", line_pt=self.CALLOUT_LINE_PT)
            if ln.startswith(">>> "):
                add_run(p, ">>> ", font="mono", size=self.CALLOUT_PT, colour="text_small_dark", no_proof=True)
                ln = ln[4:]
            add_run(p, ln, font="mono", size=self.CALLOUT_PT, colour="text_dark", no_proof=True)
            end_para_size(p, self.CALLOUT_PT)
        set_alt(box, self.R(spec.get("alt"), n) if spec.get("alt") else " ".join(lines))
        if spec.get("snippet"):
            self.snippet(n, spec["snippet"])            # recorded in the build report with its run status
        return box

    # chart_hero -- chart + hero (L7)
    def slide_chart_hero(self, s, spec, n, L):
        # always the content.yaml title: the measured factor holds for one loop on one memory layout, so the
        # general "two orders of magnitude" phrase stays out of the title (it is spoken, notes slide 18)
        lines = self.set_title(s, n, spec["title"], L)
        top = content_top(L, lines)
        drop_placeholder(s, 14)
        drop_placeholder(s, 18)
        ch = self._chart_spec(spec, n)
        values = [b["value"] if isinstance(b["value"], (int, float)) else self.res.number(b["value"], f"slide {n} chart")
                  for b in ch["bars"]]
        ch["alt"] = self.R(spec.get("alt"), n)
        self.chart(s, n, "add_column_log", MEDIA_R, ch, values, "CHART PENDING: column chart, log time axis")
        hero = spec.get("hero") or {}
        hb, hh = self.hero(s, n, L7_TEXT.x, top, L7_TEXT.w, hero.get("value", ""), hero.get("label"), size=96)
        if hero.get("build_on_click"):
            self.click_build = hb
        # conditions on the bottom edge, the support line just above them (never into the hero)
        cond_y = self.conditions_block(s, n, spec["conditions"], L7_TEXT.x, L7_TEXT.w, note=spec.get("conditions_note"),
                                       plane_threads=bool(spec.get("conditions_threads")),
                                       short=bool(spec.get("conditions_short"))) \
            if spec.get("conditions") else BOTTOM
        sup = self.R(spec.get("support"), n) if spec.get("support") else ""
        if sup:
            sh = text_h(sup, SUPPORT_PT, L7_TEXT.w - 0.02)
            y = cond_y - 0.20 - sh
            if y < top + hh + 0.15:
                self.warn(n, f"support line at {y:.2f} in reaches into the hero (ends {top + hh:.2f} in)")
            self.support(s, n, sup, (L7_TEXT.x, max(y, top + hh + 0.15), L7_TEXT.w, sh))

    def _chart_spec(self, spec, n):
        """The chart sub-dict with tokens resolved in its words (bar labels, axis title); a bar `value` stays a
        dotted results key (no braces), read as a number by the caller."""
        ch = self.res.resolve_tree(copy.deepcopy(spec["chart"]), where=f"slide {n} chart")
        for b, raw in zip(ch.get("bars", []), spec["chart"].get("bars", [])):
            b["value"] = raw["value"]
        return ch

    def chart(self, s, n, fn, frame, ch, values, caption):
        mod = self.charts
        f = getattr(mod, fn, None) if mod else None
        tree = s.shapes._spTree
        before = len(tree)
        status = {"slide": n, "fn": f"charts.{fn}", "values": values}
        if f is None:
            pending_box(s, *frame, caption, "Drawn natively by lib/charts.py (not available)", name="PENDING chart")
            self.placeholder_note(n, "chart", f"lib/charts.py:{fn}", caption)
            status["status"] = "missing"
        else:
            try:
                f(s, box_emu(*frame), ch, STYLE, values=values)
                status["status"] = "ok"
            except Exception as exc:
                for el in list(tree)[before:]:
                    tree.remove(el)
                status.update(status="error", error=f"{type(exc).__name__}: {exc}",
                              traceback=traceback.format_exc(limit=4))
                pending_box(s, *frame, caption, f"lib/charts.py:{fn} failed: {type(exc).__name__}",
                            name="PENDING chart")
                self.placeholder_note(n, "chart", f"lib/charts.py:{fn}", caption + " (helper error)")
        self._mark_helper_placeholders(tree, before, n)
        if any(v is None for v in values):
            self.placeholder_note(n, "result", "chart values", "Chart shows a [placeholder] until the result "
                                  "values exist: " + ", ".join(str(b["value"]) for b, v in zip(ch["bars"], values)
                                                               if v is None))
        self.report["helper_calls"].append(status)
        for el in list(tree)[before:]:
            c = el.find(".//" + qn("p:cNvPr"))
            if c is not None and not c.get("descr") and ch.get("alt"):
                c.set("descr", ch["alt"])

    # toll -- toll diagram + hero (L4)
    def slide_toll(self, s, spec, n, L):
        lines = self.set_title(s, n, spec["title"], L)
        top = content_top(L, lines)
        drop_placeholder(s, 1)
        vis = spec.get("visual") or {}
        for k in ("lane_top", "lane_bottom", "times", "loop_code", "call_code"):
            if not vis.get(k):
                self.warn(n, f"content.yaml slide 19 visual.{k} missing: shown as [visual.{k}]")
        # stack from the bottom: conditions (12 pt), support line, hero row; the diagram gets the rest
        cond = self.conditions_text(spec["conditions"], note=spec.get("conditions_note"), n=n,
                                    short=bool(spec.get("conditions_short"))) if spec.get("conditions") else ""
        cond_h = text_h(cond, SMALL_PT, FULL_W - 0.02) if cond else 0
        cond_y = BOTTOM - cond_h
        sup = self.R(spec.get("support"), n) if spec.get("support") else ""
        sup_h = text_h(sup, SUPPORT_PT, FULL_W - 0.02) if sup else 0
        sup_y = cond_y - 0.15 - sup_h
        hero = spec.get("hero") or {}
        hero_pt = 60
        hero_h = lines_h(1, hero_pt)
        hero_y = sup_y - 0.10 - hero_h
        self.call_helper(s, n, "diagrams", "add_toll_diagram", (X0, top, FULL_W, hero_y - 0.20 - top),
                         self.helper_spec(spec, n, "visual"),
                         caption="DIAGRAM PENDING: Python lane, compiled lane, toll per crossing")
        if hero.get("value"):
            self.hero_row(s, n, X0, hero_y, FULL_W, hero["value"], hero.get("label"), size=hero_pt, min_size=40)
        if sup:
            self.support(s, n, sup, (X0, sup_y, FULL_W, sup_h))
        if cond:
            self.small(s, n, cond, (X0, cond_y, FULL_W, cond_h), name="Conditions", bottom=True)
            self.report.setdefault("conditions_lines", {})[str(n)] = round(cond_h / lines_h(1, SMALL_PT))

    # bar_gb -- GB bar chart + hero (L8)
    def slide_bar_gb(self, s, spec, n, L):
        lines = self.set_title(s, n, spec["title"], L)
        top = content_top(L, lines)
        drop_placeholder(s, 14)
        drop_placeholder(s, 18)
        ch = self._chart_spec(spec, n)
        values = [b["value"] if isinstance(b["value"], (int, float)) else self.res.number(b["value"], f"slide {n} chart")
                  for b in ch["bars"]]
        ch["alt"] = self.R(spec.get("alt"), n)
        # the memory conditions run full width on the bottom edge (the right column has no room for them under
        # the hero, support line and small print); the chart ends above them
        cond_y = self.conditions_block(s, n, spec["conditions"], X0, FULL_W, note=spec.get("conditions_note"),
                                       short=bool(spec.get("conditions_short"))) if spec.get("conditions") else BOTTOM
        chart_box = (MEDIA_L[0], MEDIA_L[1], MEDIA_L[2], min(MEDIA_L[3], cond_y - 0.15 - MEDIA_L[1]))
        thr_key = spec["chart"].get("threshold")
        if thr_key:
            ch["threshold_gb"] = self.res.number(thr_key, f"slide {n} chart threshold")
        self.chart(s, n, "add_bar_gb", chart_box, ch, values, "CHART PENDING: horizontal bars in GB")
        if ch.get("_plot_in") and ch.get("threshold_gb") is not None:
            # dashed navy line at the RAM threshold, from the end of that RAM bar down across the bars below it,
            # so "outgrows 32 GB" reads at a glance (decorative: the alt text and the labels carry the numbers)
            px, py, pw, ph = ch["_plot_in"]
            k = len(ch["bars"])
            band = ph / k
            bar_h = band / (1 + ch["_gap_width"] / 100)
            ref_i = next((i for i, b in enumerate(spec["chart"]["bars"]) if b.get("value") == thr_key), None)
            lx = px + pw * ch["threshold_gb"] / ch["_axis_max"]
            y = py + (band * (ref_i + 0.5) + bar_h / 2 if ref_i is not None else 0.0)
            # a bar shorter than the threshold has its value label right where the line runs: skip its row
            segs = []
            for i in range((ref_i or -1) + 1, k):
                if values[i] is not None and values[i] < ch["threshold_gb"]:
                    top_i = py + band * (i + 0.5) - bar_h / 2
                    segs.append((y, top_i - 0.06))
                    y = top_i + bar_h + 0.06
            segs.append((y, py + ph))
            for j, (y1, y2) in enumerate(segs, 1):
                if y2 - y1 < 0.05:
                    continue
                thr = line(s, lx, y1, lx, y2, colour="navy", width_pt=1.5, name=f"Threshold line {j}")
                thr.line.dash_style = MSO_LINE_DASH_STYLE.DASH
                mark_decorative(thr)
        hero = spec.get("hero") or {}
        col = L8_TEXT
        hb, hh = self.hero(s, n, col.x, top, col.w, hero.get("value", ""), hero.get("label"), size=88)
        y = top + hh + 0.25
        sup = self.R(spec.get("support"), n)
        if sup:
            sh = text_h(sup, SUPPORT_PT, col.w - 0.02)
            self.support(s, n, sup, (col.x, y, col.w, sh))
            y += sh + 0.15
        if spec.get("small_print"):
            sp = self.R(spec["small_print"], n)
            sph = text_h(sp, SMALL_PT, col.w - 0.02)
            if y + sph > cond_y - 0.10:
                self.warn(n, f"small print ends at {y + sph:.2f} in, conditions start at {cond_y:.2f} in")
            self.small(s, n, sp, (col.x, y, col.w, sph))
            y += sph
        if spec.get("machine_line"):
            # the joke line (content.yaml machine_line), 20 pt slate, with room above it
            ml = self.R(spec["machine_line"], n)
            mh = text_h(ml, 20, col.w - 0.02)
            y += 0.30
            if y + mh > cond_y - 0.10:
                self.warn(n, f"machine line ends at {y + mh:.2f} in, conditions start at {cond_y:.2f} in")
            text_block(s, col.x, y, col.w, mh, ml, size=20, colour="text_small", name="Machine line")

    # code_hero -- full-width code + hero (L4)
    def slide_code_hero(self, s, spec, n, L):
        lines = self.set_title(s, n, spec["title"], L)
        top = content_top(L, lines)
        drop_placeholder(s, 1)
        sn = self.snippet(n, spec["code"]["snippet"])
        line_pt = float(spec["code"].get("line_pt", LINE_PT))      # 20 pt on slide 22: room for the 60 pt hero
        cw = max(code_width_in(max(sn.max_len, 40)) - INSET_L, 5.0)
        ch_ = code_height_in(max(len(sn.lines), 4), line_pt)
        hero = spec.get("hero") or {}
        # stack: code (full height, never clipped), hero row, optional support line, conditions (bottom-aligned).
        # The hero row takes the largest size up to 60 pt (as on slide 19) that fits the room under the code.
        cond_y = self.conditions_block(s, n, spec["conditions"], X0, FULL_W, short=bool(spec.get("conditions_short"))) \
            if spec.get("conditions") else BOTTOM
        has_sup = bool(spec.get("support"))
        sup_h = lines_h(1, SUPPORT_PT) if has_sup else 0.0
        sup_y = cond_y - 0.12 - sup_h
        code_bottom = top + ch_
        # tight box gaps (0.02 in above, 0.04 in below the hero box): the code box's bottom inset and the hero's own
        # ascender and descender space keep the visible gaps at about 0.25 in, and the hero gets 60 pt
        gap_above, gap_below = 0.02, 0.04
        room = (sup_y if has_sup else cond_y) - gap_below - (code_bottom + gap_above)
        hero_pt = next((pt for pt in (60, 56, 52, 48, 44, 40, 36) if lines_h(1, pt) <= room + 1e-6), None)
        if hero_pt is None:
            hero_pt = 36
            self.warn(n, f"hero row needs {lines_h(1, 36):.2f} in under the code, {room:.2f} in left")
        hero_h = lines_h(1, hero_pt)
        code_box, _ = self.code_or_pending(s, n, sn, X0, top, min(cw, FULL_W), ch_, name="Code",
                                           max_lines=int((ch_ - INSET_T - INSET_B) * 72 / line_pt + 1e-6),
                                           line_pt=line_pt)
        if code_box is not None and spec.get("alt"):
            set_alt(code_box, self.R(spec["alt"], n))
        self.report.setdefault("slide21_layout", {}).update({"line_pt": line_pt, "hero_pt": hero_pt})
        # the hero row sits in the middle of the room left between the code and what follows it
        hero_y = code_bottom + gap_above + max(0.0, room - hero_h) / 2
        self.hero_row(s, n, X0, hero_y, FULL_W, hero.get("value", ""), hero.get("label"), size=hero_pt,
                      min_size=32)
        if has_sup:
            self.support(s, n, spec.get("support"), (X0, sup_y, FULL_W, sup_h))

    # gotchas -- gotcha table (L10): title left, table in the layout's content column
    def slide_gotchas(self, s, spec, n, L):
        lines = self.set_title(s, n, spec["title"], L)
        drop_placeholder(s, 1)
        self.call_helper(s, n, "diagrams", "add_gotcha_table", GEO.ph(L, 1).t(),
                         self.helper_spec(spec, n, "table"),
                         caption="TABLE PENDING: five gotchas (speaker supplies)")
        if spec.get("placeholder_note"):
            t = GEO.title(L)
            note = self.R(spec["placeholder_note"], n)
            y = t.y + lines_h(lines, LAYOUT_TITLE_PT.get(L, SIZES["title"])) + 0.35
            self.small(s, n, note, (t.x, y, t.w, text_h(note, SMALL_PT, t.w - 0.02)), name="Placeholder note")
            self.placeholder_note(n, "speaker", "gotchas", spec["placeholder_note"])

    # closing -- closing (L11, navy): title, contact block, QR in the white tile, logo zone, small print
    def slide_closing(self, s, spec, n, L):
        self.set_title(s, n, spec["title"], L)
        contact = placeholder(s, 15)
        if contact is not None:
            # first line: the readable repo link (support line), then the contact lines; bottom-anchored in the
            # layout, so the block ends level with the QR tile
            lines = ([("support", self.R(spec["support"], n))] if spec.get("support") else []) + \
                [("contact", self.R(ln, n)) for ln in spec.get("contact", [])]
            tf = contact.text_frame
            p = clear_text_frame(tf)
            first_contact = True
            for i, (kind, ln) in enumerate(lines):
                if i:
                    p = tf.add_paragraph()
                # the readable repo link is the call to action: sage 28 pt, the one highlight on navy
                size = 28 if kind == "support" else 24
                para_format(p, align="left", space_after=14 if kind == "support" else 4)
                add_text_runs(p, ln, font="minor", size=size,
                              colour="highlight_dark" if kind == "support" else "text_dark",
                              bold=(kind == "contact" and first_contact))
                first_contact = first_contact and kind != "contact"
                end_para_size(p, size)
            set_name(contact, "Contact")
        qr = spec.get("qr") or {}
        url = self.R(qr.get("url"), n) if qr.get("url") else None
        qr_box = GEO.ph(L, 17)
        if url:
            try:
                import segno
                qr_path = WORK / "qr_repo.png"
                segno.make(url, error="m").save(str(qr_path), scale=20, border=2, dark=hex_of("navy"),
                                                light=hex_of("white"))
                insert_picture(s, 17, qr_path, name="QR code", descr=f"QR code linking to {url}")
            except Exception as exc:
                self.warn(n, f"QR generation failed: {exc}")
                url = None
        if not url:
            drop_placeholder(s, 17)
            t = pending_box(s, *qr_box.t(), self.R(qr.get("placeholder", "QR: [repo URL]"), n),
                            "Set qr.url in content.yaml", fill="white", name="PENDING QR")
            set_alt(t, "Placeholder for the QR code to the repository")
            self.placeholder_note(n, "qr", "repo URL", qr.get("placeholder", "QR: [repo URL]"))
        self._logo_zone(s, n, L, spec)
        if spec.get("callback"):
            # the coffee callback under the title, 24 pt sage (the small type on navy)
            t = GEO.title(L)
            cb = self.R(spec["callback"], n)
            text_block(s, t.x, t.y + lines_h(1, LAYOUT_TITLE_PT.get(L, SIZES["title"])) + 0.20, t.w,
                       text_h(cb, 24, t.w - 0.02), cb, size=24, colour="text_small_dark", name="Callback")
        sp = placeholder(s, 19)
        if spec.get("small_print") and sp is not None:
            # the layout's small print slot: 12 pt sage on navy (7.3:1), bottom-anchored, full content width
            texts = [part for t in spec["small_print"] for part in self.source_text(t).split("\n")]
            box = GEO.ph(L, 19)
            need = sum(text_h(t, SMALL_PT, box.w - 0.02) for t in texts)
            if need > box.h + 1e-6:
                self.warn(n, f"small print needs {need:.2f} in, the slot holds {box.h:.2f} in")
            tf = sp.text_frame
            p = clear_text_frame(tf)
            for i, t in enumerate(texts):
                if i:
                    p = tf.add_paragraph()
                para_format(p, align="left")
                add_text_runs(p, t, font="minor", size=SMALL_PT, colour="text_small_dark")
                end_para_size(p, SMALL_PT)
            set_name(sp, "Small print")
        elif sp is not None:
            drop_placeholder(s, 19)

    # ============================================================================ slides added 2026-10-12
    # rules -- four rules of thumb in a 2 x 2 grid (L4): the opening tips (slide 7) and, with their evidence, the
    # closing ones (slide 28)
    def slide_rules(self, s, spec, n, L):
        lines = self.set_title(s, n, spec["title"], L)
        top = content_top(L, lines)
        drop_placeholder(s, 1)
        sub = self.helper_spec(spec, n, None)
        sub = {"rules": sub["rules"], "alt": sub.get("alt"), "name": "Rules of thumb"}
        self.call_helper(s, n, "sketches", "add_rule_tiles", (X0, top + 0.05, FULL_W, BOTTOM - top - 0.20), sub,
                         caption="TILES PENDING: four rules of thumb")

    # workflow -- the stages of a 3D data science project (L4): a ring with loops back, the tools under each stage and
    # a render beside three of them (slide 7); the AHN source line on the bottom edge
    def slide_workflow(self, s, spec, n, L):
        lines = self.set_title(s, n, spec["title"], L)
        top = content_top(L, lines)
        drop_placeholder(s, 1)
        sub = self.helper_spec(spec, n, None)
        sub = {k: sub[k] for k in ("stages", "loops", "centre", "alt") if k in sub} | {"name": "Workflow"}
        src_txt = self.source_text(spec["source"]) if spec.get("source") else ""
        src_h = text_h(src_txt, SMALL_PT, FULL_W - 0.02) if src_txt else 0.0
        box = (X0, top + 0.05, FULL_W, BOTTOM - top - 0.20 - src_h - 0.05)
        self.call_helper(s, n, "sketches", "add_workflow", box, sub,
                         caption="WORKFLOW PENDING: six stages of a 3D data science project")
        tw = self.sketches.WF_THUMB_W if self.sketches else 1.0
        th = tw * DEFAULT_PX[1] / DEFAULT_PX[0]
        for i, st_ in enumerate(spec["stages"]):
            im = st_.get("image")
            if not im or not self.sketches:
                continue
            tx, ty = self.sketches.workflow_thumb(box, len(spec["stages"]), i, tw)
            self.place_render(s, n, im["file"], (tx, ty - th / 2, tw, th), name=f"Workflow image {i + 1}",
                              alt=im.get("alt"), idx=None)
        if src_txt:
            self.source(s, n, spec["source"], (X0, BOTTOM - src_h, FULL_W, src_h))

    # summary -- the end of the pipeline section (L7, fade): one row per step in the text column, the final render
    # with its chips on the right, as on the Morph slides
    def slide_summary(self, s, spec, n, L):
        self.set_title(s, n, spec["title"], L)
        drop_placeholder(s, 14)
        vis = spec["visual"]
        pic, info = self.place_render(s, n, vis["file"], MEDIA_R, name="Render final", alt=self.R(spec.get("alt"), n))
        tb = self.resolved_spec(spec["table"], n)
        tb["name"] = "Pipeline summary"
        cx, cy, cw, chh = self.morph["code"]
        self.call_helper(s, n, "sketches", "add_step_table", (cx, cy + 0.05, cw, chh - 0.05), tb,
                         caption="TABLE PENDING: pipeline summary")
        if getattr(s, "_step_table_overflow", 0) > 0.01:
            self.warn(n, f"summary table {s._step_table_overflow:.2f} in wider than the column")
        self.support(s, n, spec.get("support"), self.morph["support"], name="Support")
        if spec.get("small_print"):
            self.small(s, n, spec["small_print"], self.morph["small"], name="Small print")
        self.source(s, n, spec.get("source"), self.morph["src"], name="Source")
        if spec.get("labels_from"):
            px = tuple(info.get("px") or DEFAULT_PX)
            self.label_chips(s, n, spec["labels_from"], MEDIA_R, px, vis["file"], reference_key=self.morph_chip_ref,
                             obstacles=self.chip_obstacles, prefix="Label ")

    # expectation_map -- expectation vs reality on one map (L8): the final render left with rings at the BGT
    # register's poles (small, sage) and at the pipeline's street furniture (large, white); right, the two counts
    def _ring(self, s, cx, cy, r, colour, width_pt, name):
        halo = s.shapes.add_shape(MSO_SHAPE.OVAL, E(cx - r), E(cy - r), E(2 * r), E(2 * r))
        halo.fill.background()
        halo.line.color.rgb = rgb("navy")
        halo.line.width = Pt(width_pt + 2.0)
        halo.shadow.inherit = False
        set_name(halo, name + " halo")
        mark_decorative(halo)
        ring = s.shapes.add_shape(MSO_SHAPE.OVAL, E(cx - r), E(cy - r), E(2 * r), E(2 * r))
        ring.fill.background()
        ring.line.color.rgb = rgb(colour)
        ring.line.width = Pt(width_pt)
        ring.shadow.inherit = False
        set_name(ring, name)
        mark_decorative(ring)
        return ring

    POLE_R, OBJ_R = 0.075, 0.24

    def slide_expectation_map(self, s, spec, n, L):
        import numpy as np
        lines = self.set_title(s, n, spec["title"], L)
        top = content_top(L, lines)
        drop_placeholder(s, 14)
        vis = spec["visual"]
        pic, info = self.place_render(s, n, vis["file"], MEDIA_L, name="Render map", alt=self.R(spec.get("alt"), n))
        px = tuple(info.get("px") or DEFAULT_PX)
        fx, fy, fw, fh = MEDIA_L
        sx, sy = fw / px[0], fh / px[1]
        # expectation: BGT poles, projected with the stored camera (local = RD - origin, z = ground height)
        poles = self.res.lookup(spec["expectation"]["rings"])
        origin = self.res.lookup("pipeline.crop.origin_local")
        drawn = 0
        if isinstance(poles, list) and isinstance(origin, list) and self._render_spec():
            pts = np.array([[p["x_rd"] - origin[0], p["y_rd"] - origin[1],
                             (p.get("ground_z") if p.get("ground_z") is not None else 1.0) - origin[2]] for p in poles])
            for k, (u, v) in enumerate(self.project(pts, px)):
                if 0 <= u < px[0] and 0 <= v < px[1]:
                    self._ring(s, fx + u * sx, fy + v * sy, self.POLE_R, "highlight_dark", 1.75, f"BGT pole {k + 1}")
                    drawn += 1
        else:
            self.warn(n, "no BGT poles or no camera: expectation rings missing")
        self.report.setdefault("expectation_map", {})[str(n)] = {"poles": len(poles or []), "drawn": drawn}
        # reality: the pipeline's objects, at their drawn pixel boxes
        patches = self._point_patches(Path(vis["file"]).stem, "street_furniture") or []
        for k, pb in enumerate(patches):
            self._ring(s, fx + (pb[0] + pb[2]) / 2 * sx, fy + (pb[1] + pb[3]) / 2 * sy, self.OBJ_R, "text_dark", 2.5,
                       f"Our object {k + 1}")
        if not patches:
            self.warn(n, "no street furniture patches in render_spec.json: reality rings missing")
        # right column: two blocks, each a legend mark (the ring on a navy square), heading, count and one line
        col = L8_TEXT
        y = top
        for key, r, colour, wpt in (("expectation", self.POLE_R, "highlight_dark", 1.75),
                                    ("reality", self.OBJ_R * 0.55, "text_dark", 2.5)):
            b = spec[key]
            sq = float(spec.get("legend_sq", 0.44))
            mark = rect(s, col.x, y + 0.02, sq, sq, fill="navy", rounded=True, name=f"Legend {key}")
            mark_decorative(mark)
            self._ring(s, col.x + sq / 2, y + 0.02 + sq / 2, r, colour, wpt, f"Legend ring {key}")
            hp = int(spec.get("head_pt", 24))
            text_block(s, col.x + sq + 0.18, y, col.w - sq - 0.18, lines_h(1, hp) + 0.04, self.R(b["heading"], n),
                       size=hp, font="title", colour="title", name=f"Heading {key}")
            y += lines_h(1, hp) + float(spec.get("head_gap", 0.12))
            hb, hh = self.hero(s, n, col.x, y, col.w, b["value"], b.get("text"),
                               size=int(spec.get("hero_pt", 48)), name=f"Hero {key}")
            y += hh + float(spec.get("block_gap", 0.35))
        src_txt = self.source_text(spec["source"]) if spec.get("source") else ""
        src_h = text_h(src_txt, SMALL_PT, col.w - 0.02) if src_txt else 0.0
        sp = self.R(spec.get("small_print"), n) if spec.get("small_print") else ""
        sp_h = text_h(sp, SMALL_PT, col.w - 0.02) if sp else 0.0
        if sp:
            self.small(s, n, sp, (col.x, BOTTOM - src_h - 0.10 - sp_h, col.w, sp_h))
        if spec.get("support"):
            sup = self.R(spec["support"], n)
            sh = text_h(sup, SUPPORT_PT, col.w - 0.02)
            sy_ = BOTTOM - src_h - 0.10 - sp_h - 0.20 - sh
            if sy_ < y - 0.25:
                self.warn(n, f"support line at {sy_:.2f} in overlaps the blocks (end {y:.2f} in)")
            self.support(s, n, sup, (col.x, sy_, col.w, sh))
            if spec.get("photos"):
                self._photo_strip(s, n, spec["photos"], col, y + 0.04, sy_ - 0.16)
        self._column_source(s, n, spec, col)

    def _photo_strip(self, s, n, ph, col, y0, y1):
        """Real photos side by side in the free band y0..y1 of the right column, each cropped (cover) to its box
        around `focus` (fractions of the photo); a small navy caption chip bottom-left. Credits: small print."""
        from PIL import Image
        items, gap = ph["items"], 0.14
        w = (col.w - gap * (len(items) - 1)) / len(items)
        h = y1 - y0
        if h < 0.9:
            self.warn(n, f"photo band only {h:.2f} in tall")
        for k, it in enumerate(items):
            f = Path(__file__).parent / "assets" / "photos" / it["file"]
            if not f.exists():
                self.warn(n, f"photo {it['file']} missing: run deck/assets/photos/fetch_photos.py")
                continue
            iw, ih = Image.open(f).size
            x = col.x + k * (w + gap)
            zoom = float(it.get("zoom", 1.0))            # 1 = the widest crop that fills the box; 0.6 = closer in
            zw = min(1.0, (w / h) * ih / iw) * zoom      # visible width fraction at full height
            zh = (1.0 if zw < 1.0 else min(1.0, (h / w) * iw / ih)) * zoom if zoom < 1.0 else (1.0 if zw < 1.0 else min(1.0, (h / w) * iw / ih))
            if zoom < 1.0:
                zh = zw * (h / w) * iw / ih              # same aspect as the box
            fx, fy = it.get("focus", [0.5, 0.5])
            x0 = min(max(fx - zw / 2, 0), 1 - zw)
            yf = min(max(fy - zh / 2, 0), 1 - zh)
            pic = s.shapes.add_picture(str(f), E(x), E(y0), E(w), E(h))
            pic.crop_left, pic.crop_right = x0, 1 - x0 - zw
            pic.crop_top, pic.crop_bottom = yf, 1 - yf - zh
            set_name(pic, f"Photo {k + 1}")
            set_alt(pic, self.R(it.get("alt"), n))
            if it.get("caption"):
                cap = self.R(it["caption"], n)
                cw = min(width_in(cap, 12) + 0.2, w)
                chip = rect(s, x, y0 + h - 0.30, cw, 0.30, fill="navy", name=f"Small print photo credit {k + 1}")
                shape_text(chip, cap, size=12, colour="text_dark", align="centre", anchor="ctr")

    # quiz -- two options A and B with their code (L5), the answers as pills under them (slide 20; the answer is
    # the hero of the next slide)
    def slide_quiz(self, s, spec, n, L):
        lines = self.set_title(s, n, spec["title"], L)
        top = content_top(L, lines)
        drop_placeholder(s, 1)
        drop_placeholder(s, 2)
        y = top
        if spec.get("task"):
            task = self.R(spec["task"], n)
            th_ = text_h(task, SUPPORT_PT, FULL_W - 0.02)
            self.support(s, n, task, (X0, y, FULL_W, th_), name="Task")
            y += th_ + 0.25
        code_pt = float(spec.get("code_pt", 20))
        line_pt = round(code_pt * LINE_PT / 18.0, 2)
        sns = [self.snippet(n, r["snippet"]) for r in spec["rows"]]
        side = code_height_in(max(len(x.lines) for x in sns), line_pt)      # the letter panels' width
        gap_row, gap_x = 0.22, 0.45
        code_x = X0 + side + gap_x
        for i, (r, sn) in enumerate(zip(spec["rows"], sns)):
            panel = max(code_height_in(max(len(sn.lines), 1), line_pt), 1.0)
            letter = self.R(r.get("letter", "AB"[i]), n)
            box = rect(s, X0, y, side, panel, fill="highlight" if i == 0 else "navy", rounded=True,
                       name=f"Option {letter}")
            shape_text(box, letter, size=54, colour="text_dark", bold=True, align="centre", anchor="ctr",
                       font="title")
            set_alt(box, self.R(r.get("alt"), n))
            ch = code_height_in(max(len(sn.lines), 1), line_pt)
            need = code_width_in(sn.max_len, code_pt)
            if sn.ok:
                add_code(s, sn, code_x - INSET_L, y + (panel - ch) / 2, need, ch, name=f"Code {letter}",
                         hl_name=f"Key line {letter}", size=code_pt, line_pt=line_pt)
            else:
                self.code_or_pending(s, n, sn, code_x, y + (panel - ch) / 2, need, ch, name=f"Code {letter}")
            y += panel + gap_row
        answers = [self.R(a, n) for a in spec.get("answers") or []]
        sp = self.R(spec["small_print"], n) if spec.get("small_print") else ""
        sph = text_h(sp, SMALL_PT, FULL_W - 0.02) if sp else 0.0
        if answers:
            ay = y + 0.05
            lab = self.R(spec.get("answers_label", ""), n)
            lw = width_in(lab, 24, font="title") + 0.45 if lab else 0.0
            if lab:
                text_block(s, X0, ay, lw, 0.52, lab, size=24, font="title", colour="title", anchor="ctr",
                           name="Answers label", wrap=False)
            pw_, pg = 1.45, 0.25
            for k, a in enumerate(answers):
                pill = rect(s, X0 + lw + k * (pw_ + pg), ay, pw_, 0.52, fill="white", line="navy", line_pt=1.5,
                            rounded=True, name=f"Answer {k + 1}")
                pill.adjustments[0] = 0.5
                shape_text(pill, a, size=24, colour="title", bold=True, align="centre", anchor="ctr", font="title")
            y = ay + 0.52
        if y > BOTTOM - sph - 0.15:
            self.warn(n, f"quiz ends at {y:.2f} in, small print starts at {BOTTOM - sph:.2f} in")
        if sp:
            self.small(s, n, sp, (X0, BOTTOM - sph, FULL_W, sph), bottom=True)

    # trace -- memory over time, full width (L4, slide 27): one line per version, labelled at measured phases
    def slide_trace(self, s, spec, n, L):
        lines = self.set_title(s, n, spec["title"], L)
        top = content_top(L, lines)
        drop_placeholder(s, 1)
        cond_y = self.conditions_block(s, n, spec["conditions"], X0, FULL_W, note=spec.get("conditions_note"),
                                       short=bool(spec.get("conditions_short"))) if spec.get("conditions") else BOTTOM
        sup = self.R(spec.get("support"), n) if spec.get("support") else ""
        sup_h = text_h(sup, SUPPORT_PT, FULL_W - 0.02) if sup else 0.0
        sup_y = cond_y - 0.20 - sup_h
        ch = self.res.resolve_tree(copy.deepcopy(spec["chart"]), where=f"slide {n} chart")
        series = []
        for raw, sd in zip(spec["chart"]["series"], ch["series"]):
            case = self.res.lookup(raw["key"])
            if not isinstance(case, dict):
                self.res._miss(raw["key"], None, f"slide {n} chart")
                continue
            t_s, gb = case["t_s"], [v / 1024 for v in case["mem_mib"]]
            labels = []
            for lb in sd.get("labels") or []:
                if lb["at"] == "peak":
                    k = max(range(len(gb)), key=gb.__getitem__)
                else:
                    m = next((m for m in case.get("markers") or [] if m["label"] == lb["at"]), None)
                    if m is None:
                        self.warn(n, f"no marker {lb['at']!r} in {raw['key']}")
                        continue
                    k = min(range(len(t_s)), key=lambda i: abs(t_s[i] - m["t_s"]))
                labels.append({"index": k, "text": f"{lb['text']}: {gb[k]:.1f}\u00a0GB", "side": lb.get("side")})
            series.append({"label": sd["label"], "t_s": t_s, "mem_gb": gb, "highlight": sd.get("highlight"),
                           "labels": labels})
        self.report.setdefault("trace_labels", {})[str(n)] = [[l_["text"] for l_ in s_["labels"]] for s_ in series]
        chart_spec = {"series": series, "axis_title": ch.get("axis_title"), "time_title": ch.get("time_title"),
                      "alt": ch.get("alt"), "name": "Memory over time", "y_max": 4.0, "y_major": 1.0,
                      "x_max": float(ch.get("x_max", 10.0)), "x_major": float(ch.get("x_major", 1.0)),
                      "time_fmt": ch.get("time_fmt", '0" s"')}
        self.chart(s, n, "add_memory_trace", (X0 - 0.05, top, FULL_W + 0.05, sup_y - 0.20 - top), chart_spec, [],
                   "CHART PENDING: memory over time")
        if chart_spec.get("_plot_in"):
            # direct labels as native 20 pt text over the fixed plot box: above the point, a short leader down to
            # it; the first label of a series names the series (highlighted series in blue SemiBold)
            px_, py_, pw_, ph_ = chart_spec["_plot_in"]
            xm, ym = chart_spec["_axis"]
            for s_ in series:
                for j, lb in enumerate(s_["labels"]):
                    k = lb["index"]
                    ax_ = px_ + pw_ * float(s_["t_s"][k]) / xm
                    ay_ = py_ + ph_ * (1 - float(s_["mem_gb"][k]) / ym)
                    txt = (s_["label"] + ": " if j == 0 else "") + lb["text"]
                    tw = width_in(txt, 20, font="title" if s_.get("highlight") else "minor") + 0.12
                    up = 0.55 if not s_.get("highlight") else 0.45
                    if lb.get("side") == "left":
                        # content.yaml `side: left`: the label ends just left of the point, a little above it, no
                        # leader (for a peak near the right edge, where a label above would meet the other line)
                        lx = max(ax_ - 0.10 - tw, px_)
                        ly = ay_ - 0.20 - lines_h(1, 20)
                    else:
                        lx = min(max(ax_ - tw / 2, px_), px_ + pw_ - tw)
                        ly = ay_ - up - lines_h(1, 20)
                        ld = line(s, ax_, ay_ - 0.06, ax_, ly + lines_h(1, 20),
                                  colour="highlight" if s_.get("highlight") else "slate", width_pt=1.0,
                                  name="Trace leader")
                        mark_decorative(ld)
                    text_block(s, lx, ly, tw, lines_h(1, 20), txt, size=20, wrap=False,
                               font="title" if s_.get("highlight") else "minor",
                               colour="highlight" if s_.get("highlight") else "text", name="Trace label")
        if sup:
            self.support(s, n, sup, (X0, sup_y, FULL_W, sup_h))

    # generic fallback (should not be needed)
    def slide_generic(self, s, spec, n, L):
        self.set_title(s, n, spec.get("title", ""), L)
        self.warn(n, "built with the generic fallback")

    # C1 to C6 -- mental-model slides (L4, hidden): a figure from deck/concepts/make_figures.py on the left at its
    # drawn size (shrunk only to fit), its caption under it; the takeaway and bullets from appendix.yaml on the right
    def slide_concept(self, s, spec, n, L):
        # content.yaml `concept: C1` plays an appendix.yaml entry as a main slide; without it the slide is the entry itself
        entry = self.res.resolve_tree(copy.deepcopy(self.appendix.get(str(spec.get("concept", n))) or {}),
                                      where=f"slide {n}")
        top = content_top(L, self.set_title(s, n, spec["title"], L))
        drop_placeholder(s, 1)
        fig = entry.get("figure") or {}
        path = DECK / "assets" / "concepts" / str(fig.get("file", ""))
        cap = fig.get("caption", "")
        cap_h = text_h(cap, SMALL_PT, 7.2 - 0.02) if cap else 0
        if path.is_file():
            with Image.open(path) as im:
                iw, ih = im.size
            h = min(BOTTOM - top - cap_h - 0.10, 7.2 * ih / iw)
            w = h * iw / ih
            pic = s.shapes.add_picture(str(path), E(X0), E(top), E(w), E(h))
            set_name(pic, "Concept figure")
            set_alt(pic, fig.get("alt") or cap)
        else:
            w, h = 7.2, BOTTOM - top - cap_h - 0.10
            pending_box(s, X0, top, w, h, "FIGURE PENDING: deck/concepts/make_figures.py", str(path.name),
                        name="PENDING concept figure")
            self.placeholder_note(n, "figure", "deck/concepts/make_figures.py", f"{n} figure pending")
        if cap:
            self.small(s, n, cap, (X0, top + h + 0.10, w, cap_h), name="Small print caption")
        x = X0 + w + 0.35
        cw = X0 + FULL_W - x
        y = top
        if entry.get("takeaway"):
            th = text_h(entry["takeaway"], SUPPORT_PT, cw - 0.02)
            self.support(s, n, entry["takeaway"], (x, y, cw, th))
            y += th + 0.25
        items = [it.get("text", "") if isinstance(it, dict) else str(it) for it in entry.get("bullets") or []]
        if items:
            # main slides keep the 20 pt body minimum; the hidden ones use the appendix 16 pt
            self._bullets(s, x, y, cw, BOTTOM - y, items, 20 if spec.get("concept") else 16, "Concept bullets")

    # meme -- the picture left, a takeaway and bullets right (L4); small print on the bottom edge
    def slide_meme(self, s, spec, n, L):
        top = content_top(L, self.set_title(s, n, spec["title"], L))
        drop_placeholder(s, 1)
        sp = self.R(spec["small_print"], n) if spec.get("small_print") else ""
        sph = text_h(sp, SMALL_PT, FULL_W - 0.02) if sp else 0.0
        path = DECK / spec["image"]["file"]
        with Image.open(path) as im:
            iw, ih = im.size
        h = BOTTOM - top - (sph + 0.15 if sp else 0.0)
        w = h * iw / ih
        pic = s.shapes.add_picture(str(path), E(X0), E(top), E(w), E(h))
        set_name(pic, "Meme")
        set_alt(pic, self.R(spec["image"]["alt"], n))
        x = X0 + w + 0.5
        cw = X0 + FULL_W - x
        y = top
        if spec.get("takeaway"):
            tk = self.R(spec["takeaway"], n)
            th = text_h(tk, SUPPORT_PT, cw - 0.02)
            self.support(s, n, tk, (x, y, cw, th))
            y += th + 0.30
        items = [self.R(t_, n) for t_ in spec.get("bullets") or []]
        if items:
            self._bullets(s, x, y, cw, BOTTOM - y - (sph + 0.15 if sp else 0.0), items, 20, "Meme bullets")
        if sp:
            self.small(s, n, sp, (X0, BOTTOM - sph, FULL_W, sph), bottom=True)

    # B1 to B6 -- dense appendix (L4, hidden): bullets and/or a native table, 14 to 16 pt
    def slide_dense(self, s, spec, n, L):
        raw = self.appendix.get(str(n))
        if not isinstance(raw, dict):
            raw = {}
        entry = self.res.resolve_tree(copy.deepcopy(raw), where=f"slide {n}")
        if entry.get("title") and entry["title"] != spec["title"]:
            self.warn(n, f"appendix.yaml title differs from content.yaml: {entry['title']!r}; content.yaml used")
        lines = self.set_title(s, n, spec["title"], L)
        top = content_top(L, lines)
        drop_placeholder(s, 1)
        blocks = [k for k in entry if k in ("bullets", "body", "table")]
        if not blocks:
            pending_box(s, X0, top, FULL_W, BOTTOM - top, "APPENDIX CONTENT PENDING: deck/appendix.yaml",
                        f"{n}: {spec['title']}", name="PENDING appendix")
            self.placeholder_note(n, "appendix", "deck/appendix.yaml", f"{n} content pending")
            return
        # bottom block: small print + conditions (12 pt)
        foot = []
        if entry.get("small_print"):
            foot.append(entry["small_print"] if entry["small_print"] != "ahn" else self.meta["source_ahn"])
        if entry.get("conditions"):
            foot.append(self.conditions_text(entry["conditions"], note=entry.get("conditions_note"), n=n))
        foot_h = sum(text_h(t, SMALL_PT, FULL_W - 0.02) for t in foot) + 4 / 72 * max(0, len(foot) - 1)
        avail = BOTTOM - foot_h - top - 0.05
        options = []
        # stacked first, then side by side with the table taking 56 % of the width, then wider tables
        modes = ["stacked"] + (["side", "side:0.59", "side:0.62", "side:0.65", "side:0.68"] if len(blocks) == 2 else [])
        for mode in modes:
            for size in (16, 15, 14):
                options.append((mode, size) + self._dense_layout(entry, blocks, size, mode))
        fits = [o for o in options if o[3] <= avail]
        if fits:
            best = max(o[1] for o in fits)               # largest text size that fits, first mode in order
            mode, size, plan, total = next(o for o in fits if o[1] == best)
        else:
            mode, size, plan, total = min(options, key=lambda o: o[3])
            self.warn(n, f"appendix content needs {total:.2f} in ({mode}, {size} pt), {avail:.2f} in available")
        for kind, data, (bx, bw), by, bh in plan:
            if kind == "bullets":
                self._bullets(s, bx, top + by, bw, bh, data, size, "Appendix bullets")
            else:
                self._table(s, n, bx, top + by, bw, bh, data, size)
        if foot:
            # bottom-anchored, SMALL_PAD taller than its text (see small())
            text_block(s, X0, BOTTOM - foot_h - self.SMALL_PAD, FULL_W, foot_h + self.SMALL_PAD, foot, size=SMALL_PT,
                       colour="text_small", name="Small print", space_between=4, anchor="b")
        self.report.setdefault("appendix_layout", {})[str(n)] = {"mode": mode, "size": size,
                                                                  "need_in": round(total, 2), "avail_in": round(avail, 2)}

    # dense appendix text: 95 % line spacing (1.14 em per line), 0.03 in cell padding top and bottom
    DENSE_LINE_PCT, DENSE_CELL_TB, DENSE_BULLET_GAP = 95, 0.03, 4

    def _dense_block(self, entry, k, size, width):
        lh = size * LINE_EM * self.DENSE_LINE_PCT / 100 / 72
        if k in ("bullets", "body"):
            items = entry[k] if isinstance(entry[k], list) else [entry[k]]
            texts = [it.get("text", "") if isinstance(it, dict) else str(it) for it in items]
            h = sum(len(wrap_lines(t, size, width - 0.25 - 0.05, font="minor")) * lh
                    + self.DENSE_BULLET_GAP / 72 for t in texts) + 0.06
            return ("bullets", texts, h)
        t = entry["table"]
        cols = t.get("columns") or t.get("header") or []
        rows = [r.get("cells", []) if isinstance(r, dict) else list(r) for r in t.get("rows", [])]
        widths = self._col_widths(cols, rows, width, t.get("col_widths"))

        def row_h(cells, head=False):
            return max(len(wrap_lines(str(c), size, w - 0.18, font="title" if head else "minor"))
                       for c, w in zip(cells, widths)) * lh + 2 * self.DENSE_CELL_TB + 0.03

        heights = ([row_h(cols, head=True)] if cols else []) + [row_h(r) for r in rows]
        cap_h = (len(wrap_lines(t["caption"], size + 2, width - 0.02, font="title")) * (size + 2) * 1.25 / 72
                 + 0.06) if t.get("caption") else 0
        return ("table", {"caption": t.get("caption"), "columns": cols, "rows": rows, "widths": widths,
                          "cap_h": cap_h, "heights": heights}, sum(heights) + cap_h)

    def _dense_layout(self, entry, blocks, size, mode):
        """Returns (plan, total height); plan = [(kind, data, (x, w), y_offset, h)]."""
        plan = []
        if mode == "stacked":
            y = 0.0
            for k in blocks:
                kind, data, h = self._dense_block(entry, k, size, FULL_W)
                plan.append((kind, data, (X0, FULL_W), y, h))
                y += h + 0.12
            return plan, y - 0.12
        gap = 0.3
        t_share = float(mode.split(":")[1]) if ":" in mode else 0.56
        share = {"bullets": 1 - t_share, "body": 1 - t_share, "table": t_share}
        ws = [share[k] * (FULL_W - gap) for k in blocks]
        x, total = X0, 0.0
        for k, w in zip(blocks, ws):
            kind, data, h = self._dense_block(entry, k, size, w)
            plan.append((kind, data, (x, w), 0.0, h))
            x += w + gap
            total = max(total, h)
        return plan, total

    @staticmethod
    def _col_widths(cols, rows, total_w, fixed=None):
        """Column widths: appendix.yaml `col_widths` (relative weights, scaled to the table width) when given,
        else from the average text length per column (at least 1.6 in each)."""
        ncols = max([len(cols)] + [len(r) for r in rows] + [1])
        if fixed and len(fixed) == ncols:
            k = total_w / sum(float(v) for v in fixed)
            return [float(v) * k for v in fixed]
        weight = []
        for c in range(ncols):
            texts = ([str(cols[c])] if c < len(cols) else []) + [str(r[c]) for r in rows if c < len(r)]
            weight.append(max(8.0, sum(len(t) for t in texts) / max(len(texts), 1)))
        tot = sum(weight)
        ws = [max(1.6, total_w * w / tot) for w in weight]
        k = total_w / sum(ws)
        return [w * k for w in ws]

    def _bullets(self, s, x, y, w, h, items, size, name):
        """Bullets as in the master's body style: blue round bullet (Fira Sans), 0.25 in hanging indent."""
        tb = add_textbox(s, x, y, w, h, name=name)
        tf = tb.text_frame
        for i, it in enumerate(items):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            pPr = para_format(p, align="left", space_before=self.DENSE_BULLET_GAP if i else 0, no_bullet=False,
                              line_pct=self.DENSE_LINE_PCT)
            pPr.set("marL", str(int(E(0.25))))
            pPr.set("indent", str(int(-E(0.25))))
            clr = etree.Element(qn("a:buClr"))
            etree.SubElement(clr, qn("a:srgbClr")).set("val", COLOURS["highlight"])
            bu_font = etree.Element(qn("a:buFont"))
            bu_font.set("typeface", STYLE["fonts"]["minor"])
            bu = etree.Element(qn("a:buChar"))
            bu.set("char", "\u2022")
            sa = pPr.find(qn("a:spcAft"))
            sa.addnext(clr)
            clr.addnext(bu_font)
            bu_font.addnext(bu)
            add_text_runs(p, str(it), font="minor", size=size, colour="text")
            end_para_size(p, size)
        return tb

    def _table(self, s, n, x, y, w, h, t, size):
        cols, rows, widths = t["columns"], t["rows"], t["widths"]
        if t.get("caption"):
            text_block(s, x, y, w, t["cap_h"], t["caption"], size=size + 2, font="title", colour="title",
                       name="Table caption")
            y += t["cap_h"]
            h -= t["cap_h"]
        ncols = len(widths)
        data = ([cols] if cols else []) + rows
        gf = s.shapes.add_table(len(data), ncols, E(x), E(y), E(w), E(h))
        set_name(gf, "Appendix table")
        set_alt(gf, (t.get("caption") or "Table") + ". Columns: " + ", ".join(map(str, cols)) +
                f". {len(rows)} rows.")
        tbl = gf.table
        tblPr = tbl._tbl.find(qn("a:tblPr"))
        for attr in ("bandRow", "firstRow"):
            tblPr.set(attr, "0")
        style_id = tbl._tbl.find(qn("a:tblPr") + "/" + qn("a:tableStyleId"))
        if style_id is None:
            style_id = etree.SubElement(tblPr, qn("a:tableStyleId"))
        style_id.text = self.diagrams.NO_STYLE_NO_GRID if self.diagrams else "{2D5ABB26-0587-4C30-8999-92F81FD0307C}"
        for c, cw in enumerate(widths):
            tbl.columns[c].width = E(cw)
        for r, rh in enumerate(t.get("heights") or []):
            tbl.rows[r].height = E(rh)
        for r, row in enumerate(data):
            head = bool(cols) and r == 0
            for c in range(ncols):
                cell = tbl.cell(r, c)
                cell.margin_left = cell.margin_right = E(0.08)
                cell.margin_top = cell.margin_bottom = E(self.DENSE_CELL_TB)
                p = clear_text_frame(cell.text_frame)
                para_format(p, align="left", line_pct=self.DENSE_LINE_PCT)
                add_text_runs(p, str(row[c]) if c < len(row) else "", font="title" if head else "minor", size=size,
                              colour="text_dark" if head else "text")
                end_para_size(p, size)
                cell.fill.solid()
                cell.fill.fore_color.rgb = rgb("navy" if head else ("tile" if r % 2 == 1 else "white"))
                # white 1 pt cell edges (no default black grid): the banded fills separate the rows
                tcPr = cell._tc.get_or_add_tcPr()
                for side in ("lnL", "lnR", "lnT", "lnB"):
                    self._cell_edge(tcPr, side)
        return gf

    @staticmethod
    def _cell_edge(tcPr, side):
        """A white 1 pt cell edge (lnL/lnR/lnT/lnB) in schema order, before any fill already set."""
        old = tcPr.find(qn(f"a:{side}"))
        if old is not None:
            tcPr.remove(old)
        ln = etree.Element(qn(f"a:{side}"), w="12700", cap="flat", cmpd="sng", algn="ctr")
        etree.SubElement(etree.SubElement(ln, qn("a:solidFill")), qn("a:srgbClr")).set("val", COLOURS["white"])
        etree.SubElement(ln, qn("a:prstDash")).set("val", "solid")
        order = ["a:lnL", "a:lnR", "a:lnT", "a:lnB"]
        for t in order[order.index(f"a:{side}") + 1:] + ["a:lnTlToBr", "a:lnBlToTr", "a:cell3D", "a:noFill",
                                                          "a:solidFill", "a:gradFill", "a:blipFill", "a:pattFill",
                                                          "a:grpFill", "a:headers", "a:extLst"]:
            succ = tcPr.find(qn(t))
            if succ is not None:
                succ.addprevious(ln)
                return
        tcPr.append(ln)

    # ============================================================================ notes
    # Presenter view, one labelled block per paragraph, blank line between blocks, always in this order:
    # TALK TRACK, TIME, LIKELY QUESTION, ANSWER, CHECKPOINT, IF SKIPPED, CHECK BEFORE THE TALK, TRACE,
    # then slide-specific extras (CANDIDATE GOTCHAS on 22, any other notes.yaml key).
    NOTE_ORDER = ["TALK TRACK", "TIME", "LIKELY QUESTION", "ANSWER", "CHECKPOINT", "IF SKIPPED",
                  "CHECK BEFORE THE TALK", "TRACE"]

    @staticmethod
    def _items(v) -> list[str]:
        if v in (None, "", []):
            return []
        if isinstance(v, list):
            return [str(x).strip() for x in v if str(x).strip()]
        return [str(v).strip()]

    def _block(self, label, v, *, bullets=False) -> str | None:
        items = self._items(v)
        if not items:
            return None
        if bullets or len(items) > 1:
            return f"{label}:\n" + "\n".join(f"\u2022 {it}" for it in items)
        return f"{label}: {items[0]}"

    _COND_RE = re.compile(r"^\s*([a-z_]+(?:\.[A-Za-z0-9_\-]+)+)\s*(>=|<=|==|!=|>|<)\s*(\S+)\s*$")

    def _checks(self, items, n):
        """notes.yaml `checks`: plain strings pass through; {if, then, else} items are evaluated against
        results/*.json, so a condition the final results already settle prints as resolved."""
        if not items:
            return items
        out = []
        for it in items if isinstance(items, list) else [items]:
            if not isinstance(it, dict):
                out.append(it)
                continue
            m = self._COND_RE.match(str(it.get("if", "")))
            ok = None
            if m:
                v = self.res.lookup(m.group(1))
                want = yaml.safe_load(m.group(3))
                if self.res.has(m.group(1)) and not isinstance(v, (dict, list)):
                    try:
                        ok = {">=": v >= want, "<=": v <= want, ">": v > want, "<": v < want,
                              "==": v == want, "!=": v != want}[m.group(2)]
                    except TypeError:
                        ok = None
            else:
                self.warn(n, f"notes check condition not understood: {it.get('if')!r}")
            out.append(it.get("then") if ok else it.get("else") or it.get("if"))
        return out

    def appendix_notes(self, n, talk=True) -> str | None:
        raw = self.appendix.get(str(n))
        if not isinstance(raw, dict):
            return None
        e = self.res.resolve_tree(copy.deepcopy(raw), where=f"notes {n}")
        blocks = []
        if e.get("notes") and talk:
            blocks.append(self._block("TALK TRACK" if str(n).startswith("C") else "ANSWER IN Q&A", e["notes"]))
        # mental-model slides C1 to C9: the explanation, why it matters, an example, caveats, citations
        for key, label in (("why", "WHY IT MATTERS"), ("example", "EXAMPLE"), ("flags", "LIMITS AND DISAGREEMENTS"),
                           ("sources", "CITATIONS")):
            blocks.append(self._block(label, e.get(key), bullets=key in ("flags", "sources")))
        src = []
        k_b = k_r = 0
        for key in e:                       # same order as on the slide
            if key == "bullets":
                for it in e.get("bullets") or []:
                    if not isinstance(it, dict):
                        continue
                    k_b += 1
                    src.append(f"Bullet {k_b} \"{self._short(it.get('text', ''))}\": status {it.get('status', '?')}; "
                               f"source: {it.get('source', '[source missing]')}")
            elif key == "table":
                t = e.get("table") or {}
                for r in t.get("rows") or []:
                    if not isinstance(r, dict):
                        continue
                    k_r += 1
                    cells = r.get("cells") or []
                    src.append(f"Table row {k_r} \"{cells[0] if cells else 'row'}\": status {r.get('status', '?')}; "
                               f"source: {r.get('source', '[source missing]')}")
        if src:
            blocks.append(self._block("SOURCES AND STATUS", src, bullets=True))
            used = sorted({re.search(r"status ([^;]+);", x).group(1) for x in src if re.search(r"status ([^;]+);", x)})
            legend = {"token": "filled from results/*.json", "verified": "checked in a research report",
                      "arithmetic": "follows from a spec or data types", "pilot": "one research run on AHN data",
                      "synthetic": "measured in a research run on generated data (a synthetic street or point "
                                   "cloud), not AHN",
                      "judgement": "reasoning, not a measurement",
                      "not_tested": "not tested", "not_run": "not run", "UNVERIFIED": "unverified"}
            blocks.append("STATUS KEY: " + "; ".join(f"{u} = {legend.get(u, u)}" for u in used) + ".")
        return "\n\n".join(b for b in blocks if b) or None

    @staticmethod
    def _short(text, n_chars=60):
        text = re.sub(r"\s+", " ", str(text)).strip()
        if len(text) <= n_chars:
            return text
        cut = text[:n_chars].rsplit(" ", 1)[0].rstrip(",;:.")
        return cut + "..."

    def notes_text(self, n, spec) -> str | None:
        if str(n)[0] in "BC":
            return self.appendix_notes(n)
        entry = self.notes.get(str(n))
        if entry is None:
            self.report["notes"]["pending"].append(n)
            return "[notes pending]"
        if isinstance(entry, str):
            return self.R(entry, n)
        if isinstance(entry, dict) and entry.get("text"):
            return self.R(entry["text"], n)

        def g(*ks):
            return next((entry.get(k) for k in ks if entry.get(k) not in (None, "", [])), None)

        talk = g("talk_track", "talk", "script")
        secs = g("seconds", "time") or spec.get("seconds")
        if spec.get("seconds") and secs != spec.get("seconds"):
            self.warn(n, f"notes seconds {secs} differ from content.yaml {spec.get('seconds')}")
        ends = g("ends_at")
        time = f"{secs} s" + (f", ends at {ends}" if ends else "")
        blocks = [
            self._block("TALK TRACK", talk or "[pending]"),
            self._block("TIME", time),
            self._block("LIKELY QUESTION", g("question", "likely_question") or "[pending]"),
            self._block("ANSWER", g("answer") or "[pending]"),
            self._block("CHECKPOINT", g("checkpoint")),
            self._block("IF SKIPPED", g("skip")),
            self._block("CHECK BEFORE THE TALK", self._checks(g("checks"), n), bullets=True),
            self._block("TRACE", g("trace", "traceability") or "[pending]", bullets=True),
        ]
        if spec.get("conditions") and spec.get("conditions_short"):
            # the slide shows the one-line conditions (content.yaml conditions_short); the full line is here
            blocks.append(self._block("CONDITIONS IN FULL (the slide shows the short line)",
                                      self.conditions_text(spec["conditions"], note=spec.get("conditions_note"), n=n,
                                                           plane_threads=bool(spec.get("conditions_threads")))))
        cg = g("candidate_gotchas")
        if cg:
            items = []
            for i, c in enumerate(cg, 1):
                if isinstance(c, dict):
                    items.append(f"{i}) {c.get('code_token', '')}: {c.get('gotcha', '')} "
                                 f"[{c.get('status', 'CANDIDATE')}; evidence: {c.get('evidence', '?')}]")
                else:
                    items.append(f"{i}) {c}")
            blocks.append("CANDIDATE GOTCHAS (not on the slide, speaker to confirm):\n" + "\n".join(items))
        known = {"n", "slide", "id", "talk_track", "talk", "script", "seconds", "time", "ends_at", "question",
                 "likely_question", "answer", "trace", "traceability", "checkpoint", "skip", "checks",
                 "candidate_gotchas", "joke", "text", "title"}
        for k, v in entry.items():
            if k not in known and v not in (None, "", []):
                blocks.append(self._block(str(k).replace("_", " ").upper(), v))
        if spec.get("concept"):         # a promoted mental-model slide: its why, example, limits and citations
            blocks.append(self.appendix_notes(spec["concept"], talk=False))
        return self.R("\n\n".join(b for b in blocks if b), n)

    # ============================================================================ main
    def run(self):
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        WORK.mkdir(parents=True, exist_ok=True)
        slides = list(self.content["slides"])
        appendix = list(self.content.get("appendix") or [])
        plan = []
        for sp in slides:
            plan.append({"key": str(sp["n"]), "layout": int(sp["layout"]), "section": sp.get("section", "Main")})
        for sp in appendix:
            plan.append({"key": str(sp["n"]), "layout": int(sp["layout"]),
                         "section": "Mental models" if str(sp["n"]).startswith("C") else "Appendix"})
        # sections: merge RAM into Performance? keep as in content.yaml
        structure, log = build_structure(TEMPLATE, WORK, plan)
        self.report["structure_log"] = log

        prs = Presentation(str(structure))

        all_specs = [(sp, False) for sp in slides] + [(sp, True) for sp in appendix]
        n_notes = 0
        for (spec, hidden), slide, item in zip(all_specs, prs.slides, plan):
            n = spec["n"]
            self.click_build = None
            try:
                self.build_slide(slide, spec, n)
            except Exception as exc:
                self.report["warnings"].append({"slide": n, "msg": f"builder error {type(exc).__name__}: {exc}",
                                                "traceback": traceback.format_exc(limit=6)})
                pending_box(slide, X0, 2.0, FULL_W, 4.0, f"BUILD ERROR on slide {n}", f"{type(exc).__name__}: {exc}",
                            name="PENDING build error")
            self.report.setdefault("licence_links", {})[str(n)] = self.link_licence(slide)
            self._colour_map_from_layout(slide)
            # remove any still-empty content placeholders (they would show master prompt text)
            for ph in list(slide.placeholders):
                idx = ph.placeholder_format.idx
                if idx in (FOOTER_IDX, SLDNUM_IDX):
                    continue
                if ph.has_text_frame and not ph.text_frame.text.strip() and ph.shape_type != 13 \
                        and ph._element.tag.endswith("}sp"):
                    ph._element.getparent().remove(ph._element)
            self.report.setdefault("reading_order", {})[str(n)] = xmlpost.reading_order(slide)
            notes = self.notes_text(n, spec)
            if notes:
                slide.notes_slide.notes_text_frame.text = notes
                n_notes += 1
            xmlpost.set_transition(slide, "morph" if spec.get("transition") == "morph" else "fade")
            if self.click_build is not None:
                xmlpost.add_click_appear(slide, self.click_build)
            if hidden:
                xmlpost.hide(slide)
            xmlpost.unique_creation_id(slide, str(n))

        self._footer(prs, plan)
        # language everywhere: slides, notes, layouts, master, notes master, presentation defaults
        roots = [s._element for s in prs.slides]
        roots += [s.notes_slide._element for s in prs.slides if s.has_notes_slide]
        roots += [l._element for l in prs.slide_layouts] + [prs.slide_master._element, prs.notes_master._element,
                                                             prs._element]
        self.report["lang_tags_set"] = sum(xmlpost.normalise_lang(r) for r in roots)

        out = OUT_DIR / self.meta["file_name"]
        tmp = WORK / "filled.pptx"
        prs.save(str(tmp))
        # document timestamp: SOURCE_DATE_EPOCH if set, else the newest input file (same inputs, same bytes)
        inputs = [CONTENT, NOTES, APPENDIX] + sorted(RESULTS.glob("*.json")) + sorted(RENDERS.glob("*.png")) \
            + sorted(RENDERS.glob("*.json")) + sorted(p for p in SNIPPETS.glob("s*") if p.is_file())
        mt = float(os.environ["SOURCE_DATE_EPOCH"]) if os.environ.get("SOURCE_DATE_EPOCH") else \
            max((p.stat().st_mtime for p in inputs if p.exists()), default=CONTENT.stat().st_mtime)
        modified = dt.datetime.fromtimestamp(int(mt), dt.timezone.utc)
        xmlpost.finalise_package(tmp, author=self.meta.get("author", "Sergio Peral"), title=self.meta["title"],
                                 n_slides=len(plan), n_hidden=len(appendix), n_notes=n_notes, modified=modified,
                                 workbook_font=STYLE["fonts"]["minor"])
        out.write_bytes(tmp.read_bytes())
        self.report["output"] = str(out)
        self.report["inputs"] = {str(p.relative_to(TALK)): p.exists() for p in [CONTENT, NOTES, APPENDIX]}
        self.report["inputs"]["dirs"] = {"results": str(RESULTS), "renders": str(RENDERS), "snippets": str(SNIPPETS)}
        self.report["inputs"]["results"] = sorted(p.name for p in RESULTS.glob("*.json"))
        self.report["inputs"]["renders"] = sorted(p.name for p in RENDERS.glob("*.png"))
        self.report["inputs"]["snippets"] = sorted(p.name for p in SNIPPETS.glob("*") if p.is_file())

        # unresolved tokens anywhere in the output (should only be the visible [file.key] placeholders)
        seen = set()
        for m in self.res.missing:
            key = (m["token"], m["where"])
            if key not in seen:
                seen.add(key)
                self.report["missing_tokens"].append(m)
        self.report["validate"] = self.validate(out)
        rep = OUT_DIR / "build_report.json"
        rep.write_text(json.dumps(self.report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
        if not os.environ.get("DECK_KEEP_WORK"):
            shutil.rmtree(WORK, ignore_errors=True)
        return out, rep

    @staticmethod
    def _colour_map_from_layout(slide):
        """A layout with its own colour mapping (the navy layouts map hyperlinks to sage, docs/DESIGN.md): the
        slide gets the same override explicitly, so every reader applies it to the slide's links."""
        lay = slide.slide_layout._element.find(qn("p:clrMapOvr"))
        if lay is None or lay.find(qn("a:overrideClrMapping")) is None:
            return
        old = slide._element.find(qn("p:clrMapOvr"))
        new = copy.deepcopy(lay)
        if old is not None:
            old.addprevious(new)
            old.getparent().remove(old)
        else:
            slide._element.find(qn("p:cSld")).addnext(new)

    def _footer(self, prs, plan):
        """Footer and slide number on every slide whose layout has them (all but L1 title and L11 closing): the
        example slides carry both placeholders (geometry inherited from the layout); the footer text is set to
        content.yaml meta.footer exactly, and the slide-number field's cached text to the slide's position."""
        text = self.meta["footer"]
        done, bad = [], []
        for pos, (slide, item) in enumerate(zip(prs.slides, plan), 1):
            L = item["layout"]
            ftr, num = placeholder(slide, FOOTER_IDX), placeholder(slide, SLDNUM_IDX)
            if not GEO.has(L, FOOTER_IDX):
                for ph in (ftr, num):
                    if ph is not None:
                        ph._element.getparent().remove(ph._element)
                continue
            if ftr is None or num is None:
                bad.append(item["key"])
                continue
            p = clear_text_frame(ftr.text_frame)
            add_text_runs(p, text, font=None)
            set_name(ftr, "Footer")
            fld = num._element.find(".//" + qn("a:fld"))
            if fld is None or fld.get("type") != "slidenum":
                bad.append(item["key"])
            else:
                fld.find(qn("a:t")).text = str(pos)
            set_name(num, "Slide number")
            done.append(item["key"])
        if bad:
            self.warn(None, f"footer or slide number placeholder missing on slides {bad}")
        self.report["footer"] = {"text": text, "slides": done, "missing": bad}

    def validate(self, out: Path) -> dict:
        script = PPTX_SKILL / "scripts" / "office" / "validate.py"
        if not script.exists():
            return {"status": "NOT RUN", "reason": f"{script} not found"}
        env = dict(os.environ)
        env["PYTHONPATH"] = str(script.parent) + os.pathsep + str(PPTX_SKILL / "scripts") + os.pathsep \
            + env.get("PYTHONPATH", "")
        res = subprocess.run([sys.executable, str(script), str(out), "--original", str(TEMPLATE)],
                             cwd=str(script.parent), env=env, capture_output=True, text=True)
        txt = (res.stdout + "\n" + res.stderr).strip()
        return {"returncode": res.returncode, "output": txt[-6000:]}


def main():
    global RENDERS, RESULTS, SNIPPETS, OUT_DIR, WORK
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--renders", type=Path, help="test only: other renders directory")
    ap.add_argument("--results", type=Path, help="test only: other results directory")
    ap.add_argument("--out-dir", type=Path, help="test only: other output directory")
    args = ap.parse_args()
    if args.renders:
        RENDERS = args.renders.resolve()
    if args.results:
        RESULTS = args.results.resolve()
    if args.out_dir:
        OUT_DIR = args.out_dir.resolve()
        WORK = OUT_DIR / "_work"
    b = Builder(args)
    out, rep = b.run()
    r = b.report
    print(f"wrote {out}")
    print(f"report {rep}")
    print(f"placeholders: {len(r['placeholders'])}, missing tokens: {len(r['missing_tokens'])}, "
          f"warnings: {len(r['warnings'])}, notes pending: {len(r['notes']['pending'])}")
    print(f"helpers: {r['helpers']}")
    v = r["validate"]
    print(f"validate.py: rc={v.get('returncode', v.get('status'))}")
    print((v.get("output") or "")[-1500:])


if __name__ == "__main__":
    main()
