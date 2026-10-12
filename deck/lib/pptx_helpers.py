"""Small python-pptx primitives used by build_deck.py (text runs, boxes, placeholders, alt text)."""

from __future__ import annotations

from pathlib import Path

from lxml import etree
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.oxml.ns import qn
from pptx.shapes.placeholder import PicturePlaceholder
from pptx.util import Emu, Pt

from .style import FONTS, MONO_PITCH_FAMILY, rgb

EMU_IN = 914400
LANG = "en-GB"
# Left/right text inset of the builder's own text boxes: zero, like every text placeholder of the PyCon NL master,
# so text starts exactly on the 0.600 in margin, on the same line as the title text (docs/DESIGN.md section 5).
TEXT_INSET = 0.0
DECORATIVE_URI = "{C183D7F6-B498-43B3-948B-1728B52AA6E4}"
ADEC_NS = "http://schemas.microsoft.com/office/drawing/2017/decorative"

# Font keys -> typeface. "major"/"minor" are theme references (both Fira Sans); weights other than Regular and Bold
# are their own family names. Title runs get no typeface at all (font=None): they inherit Fira Sans SemiBold.
THEME_FONT = {"major": "+mj-lt", "minor": "+mn-lt", "title": FONTS["title"], "medium": FONTS["medium"],
              "mono": FONTS["mono"], "mono_medium": FONTS["mono_medium"]}


def E(inches: float) -> Emu:
    return Emu(int(round(inches * EMU_IN)))


def box_in(box_emu) -> tuple[float, float, float, float]:
    return tuple(int(v) / EMU_IN for v in box_emu)


def box_emu(x: float, y: float, w: float, h: float) -> tuple[int, int, int, int]:
    return (int(E(x)), int(E(y)), int(E(w)), int(E(h)))


# --------------------------------------------------------------------------------- names / alt
def cnvpr(shape):
    el = shape._element
    for path in ("p:nvSpPr/p:cNvPr", "p:nvPicPr/p:cNvPr", "p:nvGrpSpPr/p:cNvPr",
                 "p:nvGraphicFramePr/p:cNvPr", "p:nvCxnSpPr/p:cNvPr"):
        found = el.find(path.replace("p:", "{http://schemas.openxmlformats.org/presentationml/2006/main}"))
        if found is not None:
            return found
    return None


def set_name(shape, name: str):
    c = cnvpr(shape)
    if c is not None:
        c.set("name", name)
    return shape


def set_alt(shape, descr: str | None):
    c = cnvpr(shape)
    if c is not None and descr:
        c.set("descr", descr)
    return shape


def mark_decorative(shape):
    """PowerPoint's 'Mark as decorative' flag (screen readers skip the shape)."""
    c = cnvpr(shape)
    if c is None:
        return shape
    ext_lst = c.find(qn("a:extLst"))
    if ext_lst is None:
        ext_lst = etree.SubElement(c, qn("a:extLst"))
    ext = etree.SubElement(ext_lst, qn("a:ext"))
    ext.set("uri", DECORATIVE_URI)
    dec = etree.SubElement(ext, f"{{{ADEC_NS}}}decorative", nsmap={"adec": ADEC_NS})
    dec.set("val", "1")
    return shape


# --------------------------------------------------------------------------------- runs
def style_run(run, *, font: str | None = "minor", size: float | None = None, colour: str | None = None,
              bold: bool | None = None, italic: bool | None = None, strike: bool = False,
              no_proof: bool = False):
    f = run.font
    if size is not None:
        f.size = Pt(size)
    if bold is not None:
        f.bold = bold
    if italic is not None:
        f.italic = italic
    if colour is not None:
        f.color.rgb = rgb(colour)
    if font:
        f.name = THEME_FONT.get(font, font)
        latin = run._r.get_or_add_rPr().find(qn("a:latin"))
        if font in ("mono", "mono_medium") and latin is not None:
            latin.set("pitchFamily", MONO_PITCH_FAMILY)
    rpr = run._r.get_or_add_rPr()
    rpr.set("lang", LANG)
    if strike:
        rpr.set("strike", "sngStrike")
    if no_proof:
        rpr.set("noProof", "1")
    return run


def add_run(paragraph, text: str, **kw):
    r = paragraph.add_run()
    r.text = text
    return style_run(r, **kw)


def add_text_runs(paragraph, text: str, *, font: str | None = "minor", **kw):
    """Add `text` as one run (font=None: no typeface, the run inherits it, as titles must)."""
    if not text:
        return
    add_run(paragraph, text, font=font, **kw)


def clear_text_frame(tf):
    """Remove all paragraphs but the first, and empty the first one (keeps its pPr)."""
    ps = tf._txBody.findall(qn("a:p"))
    for p in ps[1:]:
        tf._txBody.remove(p)
    p0 = ps[0]
    for child in list(p0):
        if child.tag != qn("a:pPr"):
            p0.remove(child)
    return tf.paragraphs[0]


def set_body_pr(tf, *, wrap: bool | None = None, anchor: str | None = None, autofit: str | None = None,
                insets: tuple[float, float, float, float] | None = None):
    """autofit: 'none' | 'norm' | 'shape'. insets in inches (l, t, r, b)."""
    bp = tf._txBody.find(qn("a:bodyPr"))
    if wrap is not None:
        bp.set("wrap", "square" if wrap else "none")
    if anchor is not None:
        bp.set("anchor", anchor)
    if insets is not None:
        for k, v in zip(("lIns", "tIns", "rIns", "bIns"), insets):
            bp.set(k, str(int(E(v))))
    if autofit is not None:
        for tag in ("a:noAutofit", "a:normAutofit", "a:spAutoFit"):
            for el in bp.findall(qn(tag)):
                bp.remove(el)
        tag = {"none": "a:noAutofit", "norm": "a:normAutofit", "shape": "a:spAutoFit"}[autofit]
        el = etree.SubElement(bp, qn(tag))
        # keep schema order: autofit precedes scene3d/sp3d/flatTx/extLst
        for later in ("a:scene3d", "a:sp3d", "a:flatTx", "a:extLst"):
            other = bp.find(qn(later))
            if other is not None:
                other.addprevious(el)
                break
    return bp


def para_format(p, *, align: str | None = None, space_before: float = 0, space_after: float = 0,
                line_pt: float | None = None, line_pct: float | None = None, no_bullet: bool = True):
    pPr = p._p.get_or_add_pPr()
    if no_bullet:
        pPr.set("marL", "0")
        pPr.set("indent", "0")
    if align:
        pPr.set("algn", {"left": "l", "centre": "ctr", "center": "ctr", "right": "r"}.get(align, align))
    for tag in ("a:lnSpc", "a:spcBef", "a:spcAft", "a:buNone"):
        for el in pPr.findall(qn(tag)):
            pPr.remove(el)
    # schema order inside pPr: lnSpc, spcBef, spcAft, buClr..., buNone/buChar, tabLst, defRPr
    first = pPr[0] if len(pPr) else None
    new = []
    if line_pt is not None or line_pct is not None:
        ln = etree.Element(qn("a:lnSpc"))
        if line_pt is not None:
            etree.SubElement(ln, qn("a:spcPts")).set("val", str(int(round(line_pt * 100))))
        else:
            etree.SubElement(ln, qn("a:spcPct")).set("val", str(int(round(line_pct * 1000))))
        new.append(ln)
    sb = etree.Element(qn("a:spcBef"))
    etree.SubElement(sb, qn("a:spcPts")).set("val", str(int(round(space_before * 100))))
    new.append(sb)
    sa = etree.Element(qn("a:spcAft"))
    etree.SubElement(sa, qn("a:spcPts")).set("val", str(int(round(space_after * 100))))
    new.append(sa)
    if no_bullet:
        new.append(etree.Element(qn("a:buNone")))
    for el in new:
        if first is not None:
            first.addprevious(el)
        else:
            pPr.append(el)
    return pPr


def end_para_size(p, size: float):
    """endParaRPr with a size, so empty lines keep the line height."""
    epr = p._p.find(qn("a:endParaRPr"))
    if epr is None:
        epr = etree.SubElement(p._p, qn("a:endParaRPr"))
    epr.set("lang", LANG)
    epr.set("sz", str(int(round(size * 100))))
    return epr


def add_textbox(slide, x: float, y: float, w: float, h: float, *, name: str | None = None,
                wrap: bool = True, anchor: str = "t", insets=(0.0, 0.0, 0.0, 0.0), autofit: str = "none"):
    tb = slide.shapes.add_textbox(E(x), E(y), E(w), E(h))
    set_body_pr(tb.text_frame, wrap=wrap, anchor=anchor, autofit=autofit, insets=insets)
    if name:
        set_name(tb, name)
    return tb


def text_block(slide, x, y, w, h, lines, *, size: float, colour: str = "text", font: str = "minor",
               bold: bool = False, align: str = "left", anchor: str = "t", name: str | None = None,
               line_pct: float | None = None, space_between: float = 0, wrap: bool = True,
               insets=(TEXT_INSET, 0.0, TEXT_INSET, 0.0), strike: bool = False):
    """Text box with one paragraph per entry in `lines` (str or list of str). A "\n" inside a line
    starts a new paragraph too."""
    if isinstance(lines, str):
        lines = [lines]
    lines = [part for ln in lines for part in str(ln).split("\n")]
    tb = add_textbox(slide, x, y, w, h, name=name, wrap=wrap, anchor=anchor, insets=insets)
    tf = tb.text_frame
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        para_format(p, align=align, space_before=space_between if i else 0, line_pct=line_pct)
        add_text_runs(p, line, font=font, size=size, colour=colour, bold=bold, strike=strike)
        end_para_size(p, size)
    return tb


# --------------------------------------------------------------------------------- placeholders
def placeholder(slide, idx: int):
    for sh in slide.placeholders:
        if sh.placeholder_format.idx == idx:
            return sh
    return None


def title_placeholder(slide):
    for sh in slide.placeholders:
        t = sh._element.find(".//" + qn("p:ph"))
        if t is not None and t.get("type") in ("title", "ctrTitle"):
            return sh
    return None


def drop_placeholder(slide, idx: int):
    sh = placeholder(slide, idx)
    if sh is not None:
        sh._element.getparent().remove(sh._element)


def set_geometry(shape, x: float, y: float, w: float, h: float):
    shape.left, shape.top, shape.width, shape.height = E(x), E(y), E(w), E(h)
    return shape


def insert_picture(slide, idx: int, path: Path, *, name: str, descr: str, geometry=None):
    """Picture into the layout's media placeholder (crops to fill, never distorts)."""
    ph = placeholder(slide, idx)
    if ph is None:
        raise ValueError(f"placeholder idx {idx} not found")
    pic = PicturePlaceholder(ph._element, slide.shapes).insert_picture(str(path))
    set_name(pic, name)
    set_alt(pic, descr)
    crops = [pic.crop_left, pic.crop_right, pic.crop_top, pic.crop_bottom]
    if all(abs(c) < 1e-3 for c in crops):
        pic.crop_left = pic.crop_right = pic.crop_top = pic.crop_bottom = 0.0
    if geometry is not None:
        set_geometry(pic, *geometry)
    return pic


def add_picture_fill(slide, path: Path, x, y, w, h, *, name: str, descr: str):
    """Free picture that fills the box by centre-cropping (no distortion)."""
    from PIL import Image

    with Image.open(path) as im:
        iw, ih = im.size
    pic = slide.shapes.add_picture(str(path), E(x), E(y), E(w), E(h))
    box_ar, img_ar = w / h, iw / ih
    if abs(img_ar - box_ar) / box_ar > 1e-3:
        if img_ar > box_ar:          # too wide: crop left/right
            c = (1 - box_ar / img_ar) / 2
            pic.crop_left = pic.crop_right = c
        else:
            c = (1 - img_ar / box_ar) / 2
            pic.crop_top = pic.crop_bottom = c
    set_name(pic, name)
    set_alt(pic, descr)
    return pic


# --------------------------------------------------------------------------------- shapes
def rect(slide_or_group, x, y, w, h, *, fill: str | None = None, line: str | None = None,
         line_pt: float = 1.0, dash: bool = False, name: str | None = None, rounded: bool = False):
    shapes = slide_or_group.shapes
    sh = shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE if rounded else MSO_SHAPE.RECTANGLE,
                          E(x), E(y), E(w), E(h))
    if rounded:
        sh.adjustments[0] = min(0.5, 0.08 / max(min(w, h), 0.01))
    sh.shadow.inherit = False
    if fill is None:
        sh.fill.background()
    else:
        sh.fill.solid()
        sh.fill.fore_color.rgb = rgb(fill)
    if line is None:
        sh.line.fill.background()
    else:
        sh.line.color.rgb = rgb(line)
        sh.line.width = Pt(line_pt)
        if dash:
            from pptx.enum.dml import MSO_LINE_DASH_STYLE
            sh.line.dash_style = MSO_LINE_DASH_STYLE.DASH
    if name:
        set_name(sh, name)
    # shapes carry no text by default; keep the text body language consistent anyway
    return sh


def line(slide_or_group, x1, y1, x2, y2, *, colour: str = "white", width_pt: float = 1.0, name=None):
    cx = slide_or_group.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, E(x1), E(y1), E(x2), E(y2))
    cx.line.color.rgb = rgb(colour)
    cx.line.width = Pt(width_pt)
    if name:
        set_name(cx, name)
    return cx


def shape_text(sh, lines, *, size: float, colour: str, font: str = "minor", bold: bool = False,
               align: str = "left", anchor: str = "ctr", insets=(0.1, 0.05, 0.1, 0.05), wrap=True,
               space_between: float = 0):
    tf = sh.text_frame
    set_body_pr(tf, wrap=wrap, anchor=anchor, autofit="none", insets=insets)
    if isinstance(lines, str):
        lines = [lines]
    for i, ln in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        para_format(p, align=align, space_before=space_between if i else 0)
        if isinstance(ln, tuple):       # (text, overrides)
            txt, ov = ln
            add_text_runs(p, txt, font=ov.get("font", font), size=ov.get("size", size),
                          colour=ov.get("colour", colour), bold=ov.get("bold", bold))
            end_para_size(p, ov.get("size", size))
        else:
            add_text_runs(p, ln, font=font, size=size, colour=colour, bold=bold)
            end_para_size(p, size)
    return sh


def pending_box(slide, x, y, w, h, caption: str, detail: str | None = None, *, dark: bool = False,
                name: str = "PENDING", fill: str | None = None):
    """Clearly labelled placeholder for a missing render / result / snippet / helper / logo.
    On white: light tile, dashed grey outline, slate text. On navy: navy tile, dashed sage outline, white text."""
    fill = fill or ("navy" if dark else "light")
    fg = "text_dark" if dark else "text_small"
    sh = rect(slide, x, y, w, h, fill=fill, line="sage" if dark else "muted", line_pt=1.25, dash=True, name=name)
    lines = [(caption, {"size": 20, "bold": True, "colour": fg})]
    if detail:
        lines.append((detail, {"size": 12, "colour": "text_small_dark" if dark else "text_small"}))
    shape_text(sh, lines, size=20, colour=fg, align="centre", anchor="ctr",
               insets=(0.2, 0.15, 0.2, 0.15), space_between=6)
    set_alt(sh, f"Placeholder: {caption}" + (f". {detail}" if detail else ""))
    c = cnvpr(sh)
    if c is not None:
        c.set("title", "PENDING")          # marks the box for qa/checks.py, whatever its (Morph) name
    return sh
