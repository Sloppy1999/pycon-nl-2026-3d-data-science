"""Native, editable PowerPoint charts for the deck (slides 17 and 20).

Every function has the shape ``f(slide, box, spec, style, values=None)``:

* ``slide``  python-pptx slide (or any object with ``.shapes``)
* ``box``    (left, top, width, height) in EMU
* ``spec``   the slide's ``chart`` dict from content.yaml (``bars``, ``axis_title``, ...) plus an
             optional resolved ``alt`` string (tokens already filled in by the builder)
* ``style``  ``lib.style.STYLE`` (a dict); ``None`` uses it too
* ``values`` the resolved numbers, one per ``spec["bars"]`` entry, in the bar's unit (ms or GB).
             ``None`` entries (or ``values=None``) fall back to a numeric ``bar["value"]`` in the
             spec. If any value is still missing, a visible ``[placeholder]`` text box is drawn
             instead of a chart, naming the missing token, so nothing is invented.

Both return the list of shapes they added. Data are embedded (the chart stays editable in
PowerPoint). All chart text is Fira Sans 20 pt (the PyCon NL site font). Colours (docs/DESIGN.md section 6):
highlighted bar blue, other bars grey, reference bars navy, data and category labels ink, axis labels and axis
title slate, axis lines grey; every value comes from lib.style (content.yaml meta.palette).

Log axis: python-pptx has no API for it, so ``<c:logBase val="10"/>`` is inserted as the first
child of ``c:valAx/c:scaling``. Rendered and checked in LibreOffice only; PowerPoint is UNVERIFIED.
"""

from __future__ import annotations

import math
from lxml import etree
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.dml import MSO_LINE_DASH_STYLE
from pptx.enum.chart import XL_AXIS_CROSSES, XL_CHART_TYPE, XL_LABEL_POSITION, XL_TICK_MARK
from pptx.enum.text import MSO_ANCHOR, MSO_AUTO_SIZE, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Pt

try:  # package import (build_deck.py imports the package as "lib")
    from .measure import width_in as _width_in
    from .style import STYLE as _DEFAULT_STYLE
except ImportError:  # pragma: no cover - run as a loose module
    from measure import width_in as _width_in  # type: ignore
    from style import STYLE as _DEFAULT_STYLE  # type: ignore

EMU_IN = 914400
CHART_PT = 20      # all chart text (data labels, category labels, axis title): the brief's 20 pt body minimum

# Number formats (Excel syntax; "0," divides by 1000, so ms values show as seconds).
FMT_MS_LABEL = '[<10]0.0" ms";[<1000]0" ms";0.0," s"'      # 5.7 ms / 450 ms / 14.9 s
FMT_MS_AXIS = '[<1000]0" ms";0," s"'                        # 1 ms, 10 ms, ..., 1 s, 10 s
FMT_MS_AXIS_SUB = '[<1]0.###" ms";[<1000]0" ms";0," s"'     # axis starting below 1 ms
FMT_GB = '0.0" GB"'
FMT_GB_INT = '0" GB"'


# ------------------------------------------------------------------------------------------
# Style and small XML helpers (shared with diagrams.py)
# ------------------------------------------------------------------------------------------

class Style:
    """Resolved style: colours as RGBColor (palette names and roles of lib.style), font names, language tag."""

    def __init__(self, style=None):
        src = style if style is not None else _DEFAULT_STYLE
        if not isinstance(src, dict):  # a module such as lib.style
            src = getattr(src, "STYLE", None) or _DEFAULT_STYLE
        cols = dict(src["colours"])
        self.hex = {k: v.lstrip("#").upper() for k, v in cols.items()}
        self.rgb = {k: RGBColor.from_string(v) for k, v in self.hex.items()}
        fonts = src["fonts"]
        self.major, self.minor, self.mono = fonts["major"], fonts["minor"], fonts["mono"]
        self.title_font = fonts.get("title", self.minor)
        self.medium_font = fonts.get("medium", self.minor)
        self.mono_pitch = str(src.get("mono_pitch_family", "49"))
        self.lang = src.get("lang", "en-GB")

    def __getattr__(self, name):  # st.navy, st.highlight, ...
        rgb = self.__dict__.get("rgb", {})
        if name in rgb:
            return rgb[name]
        raise AttributeError(name)


def emu_box(box):
    """(l, t, w, h) EMU -> floats in inches."""
    return tuple(int(v) / EMU_IN for v in box)


def inch(v: float) -> Emu:
    return Emu(int(round(v * EMU_IN)))


def set_alt(shape, alt: str | None, name: str | None = None):
    """Alt text (cNvPr descr) and optional shape name on any shape, group or graphic frame."""
    el = shape._element
    cnv = el.find(".//" + qn("p:cNvPr"))
    if cnv is None:
        return
    if alt:
        cnv.set("descr", alt)
    if name:
        cnv.set("name", name)


def set_run_font(run, st: Style, *, font=None, size=None, color=None, bold=None,
                 italic=None, mono=False):
    """Font on a run, with language tag; mono fonts get a fixed-pitch family so that a
    substitute (a machine without Fira Mono) stays monospaced."""
    f = run.font
    font = font or (st.mono if mono else st.minor)
    f.name = font
    if size is not None:
        f.size = Pt(size)
    if color is not None:
        f.color.rgb = color
    if bold is not None:
        f.bold = bold
    if italic is not None:
        f.italic = italic
    rpr = run._r.get_or_add_rPr()
    rpr.set("lang", st.lang)
    latin = rpr.find(qn("a:latin"))
    if latin is not None and (mono or font == st.mono):
        latin.set("pitchFamily", st.mono_pitch)
        latin.set("charset", "0")


def _txpr(st: Style, size: float, color_hex: str, bold=False, rot=None) -> etree._Element:
    """A c:txPr element: one font for a chart text element."""
    rot_attr = f' rot="{rot}" vert="horz"' if rot is not None else ""
    xml = (
        f'<c:txPr xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart" '
        f'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
        f'<a:bodyPr{rot_attr}/><a:lstStyle/><a:p><a:pPr>'
        f'<a:defRPr sz="{int(size * 100)}" b="{1 if bold else 0}">'
        f'<a:solidFill><a:srgbClr val="{color_hex}"/></a:solidFill>'
        f'<a:latin typeface="{st.minor}"/><a:cs typeface="{st.minor}"/>'
        f'</a:defRPr></a:pPr><a:endParaRPr lang="{st.lang}"/></a:p></c:txPr>'
    )
    return etree.fromstring(xml)


def _replace_child(parent, new_el, successors=()):
    """Replace parent's child with the same tag as new_el, keeping schema order."""
    old = parent.find(new_el.tag)
    if old is not None:
        old.addprevious(new_el)
        parent.remove(old)
        return new_el
    for tag in successors:
        succ = parent.find(qn(tag))
        if succ is not None:
            succ.addprevious(new_el)
            return new_el
    parent.append(new_el)
    return new_el


def _horizontal_labels(axis):
    """Keep tick labels horizontal (they wrap instead of rotating to 90 degrees)."""
    txpr = axis._element.find(qn("c:txPr"))
    if txpr is not None:
        body = txpr.find(qn("a:bodyPr"))
        body.set("rot", "0")
        body.set("vert", "horz")


def _line(fmt_line, color: RGBColor | None, width_pt: float = 0.75):
    if color is None:
        fmt_line.fill.background()
    else:
        fmt_line.color.rgb = color
        fmt_line.width = Pt(width_pt)


def _no_fill_chart_space(chart, st: Style):
    """Transparent chart and plot area, no border, en-GB, no rounded corners."""
    cs = chart._chartSpace
    # c:lang must be among the first children of chartSpace (after c:date1904)
    lang = cs.find(qn("c:lang"))
    if lang is None:
        lang = etree.SubElement(cs, qn("c:lang"))
        d1904 = cs.find(qn("c:date1904"))
        if d1904 is not None:
            d1904.addnext(lang)
        else:
            cs.insert(0, lang)
    lang.set("val", st.lang)
    rc = cs.find(qn("c:roundedCorners"))
    if rc is None:
        rc = etree.Element(qn("c:roundedCorners"))
        lang.addnext(rc)
    rc.set("val", "0")
    sppr_xml = ('<c:spPr xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart" '
                'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
                '<a:noFill/><a:ln><a:noFill/></a:ln></c:spPr>')
    _replace_child(cs, etree.fromstring(sppr_xml), successors=("c:txPr", "c:externalData",
                                                                "c:printSettings", "c:userShapes",
                                                                "c:extLst"))
    plot_area = cs.find(qn("c:chart")).find(qn("c:plotArea"))
    _replace_child(plot_area, etree.fromstring(sppr_xml), successors=("c:extLst",))
    _lang_everywhere(cs, st)


def _lang_everywhere(cs, st: Style):
    """en-GB on every run property of the chart part (python-pptx writes lang="en-US" into the chart-level txPr's
    endParaRPr). Called again at the end of each chart function, after all text elements exist."""
    for tag in ("a:endParaRPr", "a:rPr", "a:defRPr"):
        for el in cs.iter(qn(tag)):
            if tag != "a:defRPr" or el.get("lang"):
                el.set("lang", st.lang)


def _resolve_values(spec, values):
    """One float per bar, or (None, [missing names])."""
    bars = spec.get("bars", [])
    out, missing = [], []
    for i, bar in enumerate(bars):
        v = values[i] if values is not None and i < len(values) else None
        if v is None:
            raw = bar.get("value")
            v = raw if isinstance(raw, (int, float)) and not isinstance(raw, bool) else None
        if v is None:
            missing.append(str(bar.get("value", bar.get("label", f"bar {i + 1}"))))
        out.append(None if v is None else float(v))
    return (None, missing) if missing else (out, [])


def _placeholder(slide, box, st: Style, text: str, alt: str | None, name: str):
    """Visible placeholder in place of a chart whose numbers are not available yet."""
    l, t, w, h = box
    tb = slide.shapes.add_textbox(Emu(l), Emu(t), Emu(w), Emu(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.auto_size = MSO_AUTO_SIZE.NONE
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = text
    set_run_font(r, st, size=CHART_PT, color=st.text_small)
    tb.line.color.rgb = st.muted
    tb.line.width = Pt(1)
    tb.line.dash_style = MSO_LINE_DASH_STYLE.DASH
    set_alt(tb, alt or text, name)
    return [tb]


# ------------------------------------------------------------------------------------------
# Slide 17: column chart on a log10 time axis
# ------------------------------------------------------------------------------------------

def _decades(lo: float, hi: float, plot_h_in: float, label_in: float = 0.45):
    """Axis limits on whole decades, with room above the tallest column for its label and
    a visible stub for the shortest one."""
    dmin = math.floor(math.log10(lo))
    if math.log10(lo) - dmin < 0.3:
        dmin -= 1
    dmax = math.ceil(math.log10(hi))
    if dmax == math.log10(hi):
        dmax += 1
    while True:
        per_decade = plot_h_in / max(1, dmax - dmin)
        if dmax - math.log10(hi) >= label_in / per_decade:
            break
        dmax += 1
    return dmin, dmax


def add_column_log(slide, box, spec, style=None, values=None):
    """Native clustered column chart, one series, log10 value axis in ms.

    spec keys: ``bars`` [{label, value, highlight?, group?}], ``axis_title``, optional
    ``alt``, ``name`` (shape name, default "chart_time"), ``gap_width`` (default 60),
    ``axis_min_ms`` / ``axis_max_ms`` (override the decade limits).
    Bars with ``highlight: true`` are blue (highlight), the rest grey (muted). Optional ``group`` keys turn the
    categories into two levels (group label under the bar labels).
    """
    st = Style(style)
    alt = spec.get("alt")
    name = spec.get("name", "chart_time")
    vals, missing = _resolve_values(spec, values)
    if vals is None or any(v <= 0 for v in vals):
        what = ", ".join(missing) if missing else "a value <= 0 (log axis)"
        return _placeholder(slide, box, st, f"[chart: {what}]", alt, name)

    bars = spec["bars"]
    l, t, w, h = box
    cd = CategoryChartData(number_format="0.000")
    if any(b.get("group") for b in bars):
        groups = {}
        for b in bars:
            groups.setdefault(b.get("group", ""), []).append(b)
        ordered = [b for g in groups.values() for b in g]
        vals = [vals[bars.index(b)] for b in ordered]
        bars = ordered
        for g, items in groups.items():
            gc = cd.add_category(g)
            for b in items:
                gc.add_sub_category(b["label"])
    else:
        cd.categories = [b["label"] for b in bars]
    cd.add_series(spec.get("series_name", "Median time (ms)"), vals)

    gf = slide.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Emu(l), Emu(t), Emu(w), Emu(h), cd)
    ch = gf.chart
    ch.has_legend = False
    ch.has_title = False
    ch.font.name = st.minor
    ch.font.size = Pt(CHART_PT)
    ch.font.color.rgb = st.text
    _no_fill_chart_space(ch, st)

    plot = ch.plots[0]
    plot.gap_width = int(spec.get("gap_width", 60))
    plot.overlap = 0
    plot.vary_by_categories = False
    ser = plot.series[0]
    ser.invert_if_negative = False
    for i, b in enumerate(bars):
        fill = ser.points[i].format.fill
        fill.solid()
        fill.fore_color.rgb = st.highlight if b.get("highlight") else st.muted
        ser.points[i].format.line.fill.background()

    dl = ser.data_labels  # series-level c:dLbls (per-point labels live inside it)
    dl.number_format = FMT_MS_LABEL
    dl.number_format_is_linked = False
    dl.position = XL_LABEL_POSITION.OUTSIDE_END
    dl.show_value = True
    dl.font.size = Pt(CHART_PT)
    dl.font.name = st.minor
    dl.font.color.rgb = st.text

    # value axis: log10, whole decades
    plot_h_in = h / EMU_IN - 1.0  # minus category labels
    dmin, dmax = _decades(min(vals), max(vals), plot_h_in)
    vmin = float(spec.get("axis_min_ms", 10.0 ** dmin))
    vmax = float(spec.get("axis_max_ms", 10.0 ** dmax))
    va = ch.value_axis
    va.has_major_gridlines = False
    va.has_minor_gridlines = False
    va.minimum_scale = vmin
    va.maximum_scale = vmax
    va.major_tick_mark = XL_TICK_MARK.OUTSIDE
    va.minor_tick_mark = XL_TICK_MARK.NONE
    va.tick_labels.number_format = FMT_MS_AXIS if vmin >= 1 else FMT_MS_AXIS_SUB
    va.tick_labels.number_format_is_linked = False
    va.tick_labels.font.size = Pt(CHART_PT)
    va.tick_labels.font.name = st.minor
    va.tick_labels.font.color.rgb = st.text_small
    _line(va.format.line, st.muted)
    # Where the category axis crosses: "autoZero" when the axis starts at >= 1 (a log axis
    # has no zero, so both apps clamp the crossing to the lowest decade). With an explicit
    # c:crosses="min", LibreOffice draws outside-end labels of short columns at the axis
    # instead of above the column (tested); autoZero avoids that. Below 1 ms "min" is kept
    # so that columns still rise from the bottom (labels may then be misplaced in LibreOffice).
    va.crosses = XL_AXIS_CROSSES.AUTOMATIC if vmin >= 1 else XL_AXIS_CROSSES.MINIMUM
    scaling = va._element.find(qn("c:scaling"))
    log_base = scaling.find(qn("c:logBase"))
    if log_base is None:
        log_base = etree.Element(qn("c:logBase"))
    scaling.insert(0, log_base)  # must be the first child of c:scaling
    log_base.set("val", "10")

    if spec.get("axis_title"):
        va.has_title = True
        tf = va.axis_title.text_frame
        tf.text = spec["axis_title"]
        for r in tf.paragraphs[0].runs:
            set_run_font(r, st, size=CHART_PT, color=st.text_small, bold=False)

    ca = ch.category_axis
    ca.has_major_gridlines = False
    ca.major_tick_mark = XL_TICK_MARK.NONE
    ca.minor_tick_mark = XL_TICK_MARK.NONE
    ca.tick_labels.font.size = Pt(CHART_PT)
    ca.tick_labels.font.name = st.minor
    ca.tick_labels.font.color.rgb = st.text
    _horizontal_labels(ca)
    _line(ca.format.line, st.muted)
    _lang_everywhere(ch._chartSpace, st)

    set_alt(gf, alt, name)
    return [gf]


# ------------------------------------------------------------------------------------------
# Slide 20: horizontal bar chart in GB
# ------------------------------------------------------------------------------------------

def _nice(target: float) -> float:
    """Smallest 'nice' number >= target (1, 1.2, 1.5, 2, 2.5, 3, 4, 5, 6, 8 times 10^k)."""
    mag = 10 ** math.floor(math.log10(target))
    for step in (1, 1.2, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10):
        if step * mag >= target * (1 - 1e-9):
            return step * mag
    return 10 * mag


def _bar_axis_max(labels, vals, int_idx, box_w_in: float, no_label=None) -> float:
    """Axis maximum that leaves room beyond every bar for its outside-end label, from Fira Sans widths
    measured with the deck's font files (lib/measure.py)."""
    # a category label may hold "\n" line breaks: its width is its longest line
    cat_w = max(_width_in(line, CHART_PT) for s in labels for line in str(s).split("\n")) + 0.25
    plot_w = max(1.0, box_w_in - cat_w)
    need = 0.0
    for i, v in enumerate(vals):
        if no_label is not None and i in no_label:
            continue
        txt = f"{v:.0f} GB" if i in int_idx else f"{v:.1f} GB"
        share = min(0.6, (_width_in(txt, CHART_PT) + 0.15) / plot_w)
        need = max(need, v / (1.0 - share))
    return _nice(need)


def _point_dlbl_delete(ser_el, idx: int):
    """Remove the data label of one point (CT_DLbl with c:delete), e.g. a reference bar whose category already
    names its value."""
    dlbls = ser_el.find(qn("c:dLbls"))
    d = etree.fromstring(f'<c:dLbl xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart">'
                         f'<c:idx val="{idx}"/><c:delete val="1"/></c:dLbl>')
    existing = dlbls.findall(qn("c:dLbl"))
    if existing:
        existing[-1].addnext(d)
    else:
        dlbls.insert(0, d)
    return d


def _point_dlbl(ser_el, idx: int, numfmt: str, st: Style, size: float, color_hex: str):
    """Per-point data label with its own number format (schema order of CT_DLbl)."""
    dlbls = ser_el.find(qn("c:dLbls"))
    xml = (
        f'<c:dLbl xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart">'
        f'<c:idx val="{idx}"/><c:numFmt formatCode="{_xml_attr(numfmt)}" sourceLinked="0"/>'
        f'<c:spPr><a:noFill xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"/></c:spPr>'
        f'</c:dLbl>'
    )
    d = etree.fromstring(xml)
    d.append(_txpr(st, size, color_hex))
    for tag, val in (("c:dLblPos", "outEnd"), ("c:showLegendKey", "0"), ("c:showVal", "1"),
                     ("c:showCatName", "0"), ("c:showSerName", "0"), ("c:showPercent", "0"),
                     ("c:showBubbleSize", "0")):
        e = etree.SubElement(d, qn(tag))
        e.set("val", val)
    # dLbl elements come first inside c:dLbls, ordered by idx
    existing = dlbls.findall(qn("c:dLbl"))
    if existing:
        existing[-1].addnext(d)
    else:
        dlbls.insert(0, d)
    return d


def _xml_attr(s: str) -> str:
    return s.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")


def add_bar_gb(slide, box, spec, style=None, values=None):
    """Native horizontal bar chart in GB, categories top to bottom in content order.

    spec keys: ``bars`` [{label, value, kind?: "reference", highlight?}], optional ``alt``,
    ``name`` (default "chart_memory"), ``gap_width`` (default 45), ``axis_max_gb``.
    Reference bars (RAM) are navy with whole-GB labels, computed bars grey, the highlighted
    bar blue; labels "0.0 GB". No value axis is drawn: the data labels carry the numbers.
    """
    st = Style(style)
    alt = spec.get("alt")
    name = spec.get("name", "chart_memory")
    vals, missing = _resolve_values(spec, values)
    if vals is None or any(v < 0 for v in vals):
        what = ", ".join(missing) if missing else "a negative value"
        return _placeholder(slide, box, st, f"[chart: {what}]", alt, name)

    bars = spec["bars"]
    l, t, w, h = box
    cd = CategoryChartData(number_format="0.0")
    cd.categories = [b["label"] for b in bars]
    cd.add_series(spec.get("series_name", "GB (2^30 bytes)"), vals)   # workbook header: binary GB
    gf = slide.shapes.add_chart(XL_CHART_TYPE.BAR_CLUSTERED, Emu(l), Emu(t), Emu(w), Emu(h), cd)
    ch = gf.chart
    ch.has_legend = False
    ch.has_title = False
    ch.font.name = st.minor
    ch.font.size = Pt(CHART_PT)
    ch.font.color.rgb = st.text
    _no_fill_chart_space(ch, st)

    plot = ch.plots[0]
    plot.gap_width = int(spec.get("gap_width", 45))
    plot.overlap = 0
    plot.vary_by_categories = False
    ser = plot.series[0]
    ser.invert_if_negative = False
    for i, b in enumerate(bars):
        fill = ser.points[i].format.fill
        fill.solid()
        if b.get("highlight"):
            fill.fore_color.rgb = st.highlight
        elif b.get("kind") == "reference":
            fill.fore_color.rgb = st.navy
        else:
            fill.fore_color.rgb = st.muted
        ser.points[i].format.line.fill.background()

    dl = ser.data_labels  # series-level c:dLbls (per-point labels live inside it)
    dl.number_format = FMT_GB
    dl.number_format_is_linked = False
    dl.position = XL_LABEL_POSITION.OUTSIDE_END
    dl.show_value = True
    dl.font.size = Pt(CHART_PT)
    dl.font.name = st.minor
    dl.font.color.rgb = st.text
    # reference bars (RAM) whose category label already names the value ("RAM, 16 GB machine") get no data
    # label; other reference bars get a whole-GB label
    unlabelled = {i for i, b in enumerate(bars)
                  if b.get("kind") == "reference" and f"{vals[i]:g} GB" in str(b.get("label", ""))}
    for i, b in enumerate(bars):
        if i in unlabelled:
            _point_dlbl_delete(ser._element, i)
        elif b.get("kind") == "reference" and float(vals[i]).is_integer():
            _point_dlbl(ser._element, i, FMT_GB_INT, st, CHART_PT, st.hex["text"])

    va = ch.value_axis
    va.has_major_gridlines = False
    va.has_minor_gridlines = False
    va.minimum_scale = 0
    int_idx = {i for i, b in enumerate(bars)
               if b.get("kind") == "reference" and float(vals[i]).is_integer()}
    va.maximum_scale = float(spec.get("axis_max_gb") or
                             _bar_axis_max([b["label"] for b in bars], vals, int_idx, w / EMU_IN,
                                           no_label=unlabelled))
    va.visible = False

    if spec.get("threshold_gb") is not None:
        # fixed inner plot box (c:manualLayout), so the caller can draw a threshold line at an exact GB value:
        # category labels in the left cat_w, the bars in the rest; geometry handed back in spec["_plot_in"]
        w_in, h_in = w / EMU_IN, h / EMU_IN
        cat_w = max(_width_in(line, CHART_PT) for b in bars for line in str(b["label"]).split("\n")) + 0.25
        fx, fy, fw, fh = cat_w / w_in, 0.02, (w_in - cat_w - 0.02) / w_in, 0.96
        pa = ch._chartSpace.find(".//" + qn("c:plotArea"))
        old_layout = pa.find(qn("c:layout"))
        if old_layout is not None:
            pa.remove(old_layout)
        pa.insert(0, etree.fromstring(
            '<c:layout xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart"><c:manualLayout>'
            '<c:layoutTarget val="inner"/><c:xMode val="edge"/><c:yMode val="edge"/>'
            f'<c:x val="{fx:.4f}"/><c:y val="{fy:.4f}"/><c:w val="{fw:.4f}"/><c:h val="{fh:.4f}"/>'
            '</c:manualLayout></c:layout>'))
        spec["_plot_in"] = (l / EMU_IN + fx * w_in, t / EMU_IN + fy * h_in, fw * w_in, fh * h_in)
        spec["_axis_max"] = float(va.maximum_scale)
        spec["_gap_width"] = plot.gap_width

    ca = ch.category_axis
    ca.reverse_order = True  # first bar of the spec on top
    ca.has_major_gridlines = False
    ca.major_tick_mark = XL_TICK_MARK.NONE
    ca.minor_tick_mark = XL_TICK_MARK.NONE
    ca.tick_labels.font.size = Pt(CHART_PT)
    ca.tick_labels.font.name = st.minor
    ca.tick_labels.font.color.rgb = st.text
    _horizontal_labels(ca)
    _line(ca.format.line, st.muted)
    _lang_everywhere(ch._chartSpace, st)

    set_alt(gf, alt, name)
    return [gf]


# ------------------------------------------------------------------------------------------
# Slide 25: memory over time, two lines (results/memory_trace.json)
# ------------------------------------------------------------------------------------------

def add_memory_trace(slide, box, spec, style=None, values=None):
    """Native XY chart with straight lines, no markers: memory (GB) over time (s), one series per case.

    spec keys: ``series`` [{label, t_s: [...], mem_gb: [...], highlight?}], ``axis_title`` (value axis),
    ``time_title`` (time axis), optional ``alt``, ``name``. The highlighted series is blue and 3 pt, the other grey
    and 2.25 pt; each series is labelled directly at its peak with its label and peak (no legend).
    """
    from pptx.chart.data import XyChartData

    st = Style(style)
    alt = spec.get("alt")
    name = spec.get("name", "chart_memory_trace")
    series = spec.get("series") or []
    if not series or any(not s.get("t_s") for s in series):
        return _placeholder(slide, box, st, "[chart: results/memory_trace.json]", alt, name)
    l, t, w, h = box
    cd = XyChartData()
    for s in series:
        ser = cd.add_series(s["label"], number_format="0.0")
        for x, y in zip(s["t_s"], s["mem_gb"]):
            ser.add_data_point(float(x), float(y))
    gf = slide.shapes.add_chart(XL_CHART_TYPE.XY_SCATTER_LINES_NO_MARKERS, Emu(l), Emu(t), Emu(w), Emu(h), cd)
    ch = gf.chart
    ch.has_legend = False
    ch.has_title = False
    ch.font.name = st.minor
    ch.font.size = Pt(CHART_PT)
    ch.font.color.rgb = st.text
    _no_fill_chart_space(ch, st)
    plot = ch.plots[0]
    for s, ser in zip(series, plot.series):
        hl = bool(s.get("highlight"))
        ser.smooth = False
        ser.format.line.color.rgb = st.highlight if hl else st.muted
        ser.format.line.width = Pt(3.0 if hl else 2.25)
        ser.marker.style = None
        from pptx.enum.chart import XL_MARKER_STYLE
        ser.marker.style = XL_MARKER_STYLE.NONE
        # no data labels: the caller draws the direct labels as native text over the fixed plot box (spec
        # "_plot_in", below), because chart data labels wrap to a narrow width in some renderers
    ymax = max(max(float(v) for v in s["mem_gb"]) for s in series)
    xmax = max(max(float(v) for v in s["t_s"]) for s in series)
    va, ca = ch.value_axis, ch.category_axis
    va.minimum_scale, va.maximum_scale = 0.0, float(spec.get("y_max", math.ceil(ymax * 1.25)))
    va.major_unit = float(spec.get("y_major", 1.0))
    ca.minimum_scale, ca.maximum_scale = 0.0, float(spec.get("x_max", math.ceil(xmax)))
    ca.major_unit = float(spec.get("x_major", 2.0))
    for ax, title, fmt in ((va, spec.get("axis_title"), '0" GB"'), (ca, spec.get("time_title"), spec.get("time_fmt", '0" s"'))):
        ax.has_major_gridlines = False
        ax.has_minor_gridlines = False
        ax.major_tick_mark = XL_TICK_MARK.OUTSIDE
        ax.minor_tick_mark = XL_TICK_MARK.NONE
        ax.tick_labels.number_format = fmt
        ax.tick_labels.number_format_is_linked = False
        ax.tick_labels.font.size = Pt(CHART_PT)
        ax.tick_labels.font.name = st.minor
        ax.tick_labels.font.color.rgb = st.text_small
        _line(ax.format.line, st.muted)
        if title and spec.get("show_axis_titles"):
            ax.has_title = True
            tf = ax.axis_title.text_frame
            tf.text = title
            for r in tf.paragraphs[0].runs:
                set_run_font(r, st, size=CHART_PT, color=st.text_small, bold=False)
    # fixed inner plot box (c:manualLayout): value tick labels in the left 0.75 in, time tick labels in the bottom
    # 0.45 in; geometry handed back in spec["_plot_in"], axis maxima in spec["_axis"]
    w_in, h_in = w / EMU_IN, h / EMU_IN
    fx, fy = 0.80 / w_in, 0.05 / h_in
    fw, fh = (w_in - 0.80 - 0.15) / w_in, (h_in - 0.05 - 0.50) / h_in
    pa = ch._chartSpace.find(".//" + qn("c:plotArea"))
    old_layout = pa.find(qn("c:layout"))
    if old_layout is not None:
        pa.remove(old_layout)
    pa.insert(0, etree.fromstring(
        '<c:layout xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart"><c:manualLayout>'
        '<c:layoutTarget val="inner"/><c:xMode val="edge"/><c:yMode val="edge"/>'
        f'<c:x val="{fx:.4f}"/><c:y val="{fy:.4f}"/><c:w val="{fw:.4f}"/><c:h val="{fh:.4f}"/>'
        '</c:manualLayout></c:layout>'))
    spec["_plot_in"] = (l / EMU_IN + fx * w_in, t / EMU_IN + fy * h_in, fw * w_in, fh * h_in)
    spec["_axis"] = (float(ca.maximum_scale), float(va.maximum_scale))
    _lang_everywhere(ch._chartSpace, st)
    set_alt(gf, alt, name)
    return [gf]


__all__ = ["add_column_log", "add_bar_gb", "add_memory_trace", "Style", "set_alt", "set_run_font", "emu_box",
           "inch", "FMT_MS_LABEL", "FMT_MS_AXIS", "FMT_GB"]
