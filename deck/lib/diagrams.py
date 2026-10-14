"""Native diagrams for the deck (by content.yaml `build`: ecosystem, chain_images, filmstrip, handoffs, toll,
gotchas, logo_wall).

Every function has the shape ``f(slide, box, spec, style[, extra])``:

* ``box``   (left, top, width, height) in EMU; the diagram is laid out inside it
* ``spec``  the slide's ``visual`` / ``left`` / ``table`` dict from content.yaml, with
            an optional resolved ``alt`` string and optional ``name``
* ``style`` ``lib.style.STYLE`` (``None`` uses it)

All shapes are native (editable) PowerPoint shapes, except the logo and render pictures. Text: Fira Sans for labels,
Fira Sans SemiBold for headings, Fira Mono for code (the PyCon NL site
font family, docs/DESIGN.md). Body text >= 20 pt, code >= 18 pt, small print 12 pt. Colours are palette roles
from lib.style: highlight blue (arrows, ticks, rules), muted grey (outlines, work blocks, greyed bullets),
slate for secondary text on white. No dashes in any text produced here.
Every visible word comes from ``spec`` (content.yaml). There are no built-in default words: a
missing word is drawn as a visible ``[visual.<key>]`` placeholder (see ``_word``).

Grouping: the ecosystem map and toll diagram are returned as one group with
the alt text on the group. The filmstrip is NOT grouped, because its first picture is the Morph
target (``!!render``) and Morph matching inside groups is UNVERIFIED.
"""

from __future__ import annotations

from pathlib import Path

from lxml import etree
from pptx.enum.dml import MSO_LINE_DASH_STYLE
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, MSO_AUTO_SIZE, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Pt

try:
    from .charts import Style, emu_box, inch, set_alt, set_run_font
    from .pptx_helpers import mark_decorative as _mark_decorative
except ImportError:  # pragma: no cover - run as a loose module
    from charts import Style, emu_box, inch, set_alt, set_run_font  # type: ignore
    from pptx_helpers import mark_decorative as _mark_decorative  # type: ignore

# No default words: every visible word comes from content.yaml. Kept empty for importers.
DEFAULT_WORDS: dict = {}


def _word(spec, key):
    """The spec's word for ``key``, or a visible placeholder naming the content.yaml key."""
    v = spec.get(key)
    return v if isinstance(v, str) and v.strip() else f"[visual.{key}]"


# Geometry, inches
RADIUS = 0.08      # corner radius, same in the whole deck
GAP = 0.500        # gutter between tiles: the master's column gap (L5 columns, docs/DESIGN.md section 5)

# ------------------------------------------------------------------------------------------
# Text and shape helpers
# ------------------------------------------------------------------------------------------

def _add_runs(p, text, st: Style, *, font=None, size=20, color=None, bold=False, italic=False,
              mono=False):
    """Add text as one run in ``font`` (default Fira Sans, or Fira Mono with ``mono``)."""
    font = font or (st.mono if mono else st.minor)
    r = p.add_run()
    r.text = text
    set_run_font(r, st, font=font, size=size, color=color, bold=bold, italic=italic, mono=mono)
    return p


def _frame(tf, *, anchor=MSO_ANCHOR.TOP, margins=(0.0, 0.0, 0.0, 0.0), wrap=True):
    tf.word_wrap = wrap
    tf.auto_size = MSO_AUTO_SIZE.NONE
    tf.vertical_anchor = anchor
    tf.margin_left, tf.margin_top, tf.margin_right, tf.margin_bottom = (inch(m) for m in margins)
    return tf


def _paras(tf, st: Style, paras, align=PP_ALIGN.LEFT):
    """paras: list of dicts {text, size, color, bold, italic, mono, font, space_before, align}."""
    for i, pd in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = pd.get("align", align)
        if pd.get("space_before"):
            p.space_before = Pt(pd["space_before"])
        if pd.get("line_spacing"):
            p.line_spacing = pd["line_spacing"]
        _add_runs(p, pd["text"], st, font=pd.get("font"), size=pd.get("size", 20),
                  color=pd.get("color", st.text), bold=pd.get("bold", False),
                  italic=pd.get("italic", False), mono=pd.get("mono", False))
    return tf


def _textbox(shapes, st, x, y, w, h, paras, *, anchor=MSO_ANCHOR.TOP, align=PP_ALIGN.LEFT,
             margins=(0.0, 0.0, 0.0, 0.0), wrap=True, name=None):
    tb = shapes.add_textbox(inch(x), inch(y), inch(w), inch(h))
    _frame(tb.text_frame, anchor=anchor, margins=margins, wrap=wrap)
    _paras(tb.text_frame, st, paras, align=align)
    if name:
        tb.name = name
    return tb


def _box(shapes, x, y, w, h, *, fill=None, line=None, line_w=1.0, dash=None, rounded=True,
         name=None):
    shape = MSO_SHAPE.ROUNDED_RECTANGLE if rounded else MSO_SHAPE.RECTANGLE
    sh = shapes.add_shape(shape, inch(x), inch(y), inch(w), inch(h))
    if rounded:
        sh.adjustments[0] = min(0.5, RADIUS / min(w, h))
    sh.shadow.inherit = False
    if fill is None:
        sh.fill.background()
    else:
        sh.fill.solid()
        sh.fill.fore_color.rgb = fill
    if line is None:
        sh.line.fill.background()
    else:
        sh.line.color.rgb = line
        sh.line.width = Pt(line_w)
        if dash is not None:
            sh.line.dash_style = dash
    if name:
        sh.name = name
    return sh


def _connector(shapes, x1, y1, x2, y2, color, width_pt=2.0, *, arrow=False, dash=None,
               name=None):
    c = shapes.add_connector(MSO_CONNECTOR.STRAIGHT, inch(x1), inch(y1), inch(x2), inch(y2))
    c.line.color.rgb = color
    c.line.width = Pt(width_pt)
    if dash is not None:
        c.line.dash_style = dash
    ln = c.line._get_or_add_ln()
    if arrow:
        tail = etree.SubElement(ln, qn("a:tailEnd"))
        tail.set("type", "triangle")
        tail.set("w", "med")
        tail.set("len", "med")
    if name:
        c.name = name
    return c


def _arrow(shapes, cx, cy, w, h, color, name):
    """Block arrow pointing right in ``color``, centred on (cx, cy), no outline, marked decorative (the
    step connector of the slide 6 chain and the slide 7 filmstrip; same shape as the slide 3 arrow)."""
    a = shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, inch(cx - w / 2), inch(cy - h / 2), inch(w), inch(h))
    a.shadow.inherit = False
    a.fill.solid()
    a.fill.fore_color.rgb = color
    a.line.fill.background()
    a.name = name
    _mark_decorative(a)
    return a


def _group(slide, name, alt):
    grp = slide.shapes.add_group_shape()
    set_alt(grp, alt, name)
    return grp


def _finish_group(grp, alt, name):
    # python-pptx recalculates the group extents as shapes are added; set alt text last
    set_alt(grp, alt, name)
    return [grp]


# ------------------------------------------------------------------------------------------
# Slide 5: ecosystem map
# ------------------------------------------------------------------------------------------

def _wrap(text, size, width, bold=False):
    """Fira Sans word wrap estimate (deck/lib/measure.py, measured with the deck's font files)."""
    try:
        from .measure import wrap_lines
    except ImportError:  # pragma: no cover - run as a loose module
        from measure import wrap_lines  # type: ignore
    return wrap_lines(text, size, width, font="minor", bold=bold) if text else []


def _width(text, size, bold=False):
    """Fira Sans advance width in inches (deck/lib/measure.py)."""
    try:
        from .measure import width_in
    except ImportError:  # pragma: no cover - run as a loose module
        from measure import width_in  # type: ignore
    return width_in(text, size, font="minor", bold=bold)


def break_name(text, width, size=20, bold=True):
    """A step name wider than ``width`` (Fira Sans, measured) broken at its last space ("Ground removal" ->
    "Ground\nremoval"), so the wrap is explicit and does not depend on small metric differences between
    renderers; a name that fits, or has no space, is returned unchanged."""
    if "\n" in text or " " not in text or _width(text, size, bold=bold) <= width:
        return text
    head, tail = text.rsplit(" ", 1)
    return head + "\n" + tail


def _name_paras(text, st, *, size=20, color=None, bold=True):
    """One paragraph per line of ``text`` (explicit breaks from break_name)."""
    return [{"text": line, "size": size, "bold": bold, "color": color if color is not None else st.text}
            for line in text.split("\n")]


def _pack_rows(libs):
    """Greedy interval packing in content order: each library goes into the first row where
    its step span is free. Returns [(lib, row, first_step_idx, last_step_idx)]."""
    rows, out = [], []
    for lib in libs:
        a, b = min(lib["steps"]) - 1, max(lib["steps"]) - 1
        for r, occ in enumerate(rows):
            if all(b < oa or a > ob for oa, ob in occ):
                occ.append((a, b))
                out.append((lib, r, a, b))
                break
        else:
            rows.append([(a, b)])
            out.append((lib, len(rows) - 1, a, b))
    return out, len(rows)


def add_ecosystem_map(slide, box, spec, style=None):
    """Six step headers in a row (bold ink names on a navy rule, as a table header), library tiles under the steps
    they serve, unused libraries (``steps: []``) in dashed grey outlines with slate text and their ``note``.

    spec: ``steps`` [str], ``libraries`` [{name, job, steps: [1-based], note?}], ``alt``?,
    ``name``? Layout constants can be overridden with ``chip_h_in`` and ``apart_span``. Each row of tiles is as
    tall as its tallest tile's wrapped text; the gaps shrink (to at most half) when the rows need the room.
    """
    st = Style(style)
    x0, y0, W, H = emu_box(box)
    steps, libs = spec["steps"], spec["libraries"]
    n = len(steps)
    gap = 0.08          # narrow gaps: "downsampling" (1.86 in bold at 20 pt) fits one step column
    cw = (W - (n - 1) * gap) / n
    xs = [x0 + i * (cw + gap) for i in range(n)]
    chip_h = float(spec.get("chip_h_in", 0.76))
    used = [lib for lib in libs if lib.get("steps")]
    apart = [lib for lib in libs if not lib.get("steps")]
    placed, nrows = _pack_rows(used)
    chip_y = y0 + 0.05
    span = int(spec.get("apart_span", 2 if len(apart) * 2 < n else 3))
    notes = list(dict.fromkeys(lib["note"] for lib in apart if lib.get("note")))
    # one note and room left of the dashed boxes: the note sits in that room, on the boxes' row
    inline_note = len(notes) == 1 and len(apart) * span < n

    # row heights from the wrapped text (name over job, 20 pt): a row is as tall as its tallest tile
    line_h = 20 * 1.2 / 72
    pad_t, pad_b, pad_x = 0.07, 0.07, 0.24

    def tile_need(lib, w):
        lines = len(_wrap(lib["name"], 20, w - pad_x, bold=True)) + len(_wrap(lib.get("job", ""), 20, w - pad_x))
        return pad_t + lines * line_h + 2 / 72 + pad_b

    row_need = [0.0] * nrows
    for lib, r, a, b in placed:
        row_need[r] = max(row_need[r], tile_need(lib, xs[b] + cw - xs[a]))
    # the boxes of libraries outside the pipeline share the width right of the note (one note on their row), or
    # sit ``span`` steps wide, right-aligned, under the note's own line
    note_w = (_width(notes[0], 20) + 0.25) if inline_note else 0.0
    if inline_note:
        apart_w = (W - note_w - (len(apart) - 1) * gap) / max(1, len(apart))
    else:
        apart_w = span * cw + (span - 1) * gap
    apart_h = max([tile_need(lib, apart_w) for lib in apart] + [0.0])
    note_h = 0.0 if inline_note else 0.42 * len(notes)
    # gaps: the defaults, shrunk evenly (to at most half) when the rows need the room
    gaps = {"chip": 0.32, "row": 0.20, "apart": 0.30}
    fixed = (chip_y - y0) + chip_h + sum(row_need) + (note_h + apart_h if apart else 0)
    flex = gaps["chip"] + gaps["row"] * (nrows - 1) + (gaps["apart"] if apart else 0)
    k = max(0.5, min(1.0, (H - fixed) / flex)) if flex else 1.0
    chip_gap, row_gap, apart_gap = gaps["chip"] * k, gaps["row"] * k, gaps["apart"] * k

    name = spec.get("name", "ecosystem_map")
    alt = spec.get("alt") or ("Diagram: steps " + ", ".join(steps) + ". Libraries: " +
                              "; ".join(f"{lib['name']}, {lib.get('job', '')}" for lib in libs))
    grp = _group(slide, name, alt)
    S = grp.shapes
    # step headers as a table header: unboxed, Fira Sans bold ink 20 pt as the slide 7 step names (a name wider
    # than its column breaks at its last space), bottom-aligned on a 2.25 pt navy rule 0.06 in below, one rule
    # per column
    for i, s in enumerate(steps):
        head = _textbox(S, st, xs[i], chip_y, cw, chip_h,
                        _name_paras(break_name(s, cw - 0.05), st), anchor=MSO_ANCHOR.BOTTOM, align=PP_ALIGN.CENTER,
                        name=f"eco_step_{i + 1}")
        head.text_frame.word_wrap = False
        _connector(S, xs[i], chip_y + chip_h + 0.06, xs[i] + cw, chip_y + chip_h + 0.06, st.navy, 2.25,
                   name=f"eco_rule_{i + 1}")

    row_y = [chip_y + chip_h + chip_gap]
    for r in range(1, nrows):
        row_y.append(row_y[-1] + row_need[r - 1] + row_gap)
    for lib, r, a, b in placed:
        tx, tw = xs[a], xs[b] + cw - xs[a]
        tile = _box(S, tx, row_y[r], tw, row_need[r], fill=st.light, name=f"eco_lib_{lib['name']}")
        _frame(tile.text_frame, anchor=MSO_ANCHOR.TOP, margins=(0.12, pad_t, 0.12, pad_b))
        _paras(tile.text_frame, st, [
            {"text": lib["name"], "size": 20, "bold": True, "color": st.text},
            {"text": lib.get("job", ""), "size": 20, "color": st.text_small, "space_before": 2},
        ])

    # libraries outside the pipeline: dashed grey boxes, side by side, each ``span`` steps wide and
    # right-aligned, with the slate note ("not in this pipeline") in the room on their left, or on its own
    # line above them when there is no room
    ay = (row_y[-1] + row_need[-1] if nrows else chip_y + chip_h) + apart_gap
    first = n - len(apart) * span
    for j, note in enumerate(notes):
        if inline_note:
            _textbox(S, st, xs[0], ay, note_w, apart_h, [{"text": note, "size": 20, "color": st.text_small}],
                     anchor=MSO_ANCHOR.MIDDLE, margins=(0.0, 0.0, 0.0, 0.0), name=f"eco_note_{j + 1}")
        else:
            _textbox(S, st, xs[0], ay + j * 0.42, W, 0.40, [{"text": note, "size": 20, "color": st.text_small}],
                     anchor=MSO_ANCHOR.BOTTOM, margins=(0.0, 0.0, 0.0, 0.02), name=f"eco_note_{j + 1}")
    ay += note_h
    for kk, lib in enumerate(apart):
        if inline_note:
            tx, tw = x0 + note_w + kk * (apart_w + gap), apart_w
        else:
            a = max(0, first) + kk * span
            b = min(n, a + span) - 1
            tx, tw = xs[a], xs[b] + cw - xs[a]
        tile = _box(S, tx, ay, tw, apart_h, line=st.muted, line_w=1.25,
                    dash=MSO_LINE_DASH_STYLE.DASH, name=f"eco_apart_{lib['name']}")
        _frame(tile.text_frame, anchor=MSO_ANCHOR.MIDDLE, margins=(0.12, pad_t, 0.12, pad_b))
        _paras(tile.text_frame, st, [
            {"text": lib["name"], "size": 20, "bold": True, "color": st.text_small},
            {"text": lib.get("job", ""), "size": 20, "color": st.text_small, "space_before": 2},
        ])
    return _finish_group(grp, alt, name)


# ------------------------------------------------------------------------------------------
# Slide 7: filmstrip of the six render frames
# ------------------------------------------------------------------------------------------

FRAME_ASPECT = 1588 / 1792  # width / height of the L7 render frames


def add_filmstrip(slide, box, spec, style=None, renders_dir=None):
    """Six thumbnails in a row with blue block arrows between them, step names (20 pt bold) and library
    tags (20 pt slate) below. Missing render files become navy placeholders that name the file.
    The first picture is named ``spec['morph_first_as']`` (e.g. "!!render") for Morph.

    spec: ``frames`` [file names], ``names`` [str], ``tags`` [str], ``morph_first_as``?, ``alt``?
    renders_dir: directory with the frame PNGs (str or Path); None = placeholders only.
    """
    st = Style(style)
    x0, y0, W, H = emu_box(box)
    frames, names = spec["frames"], spec["names"]
    tags = spec.get("tags", [""] * len(frames))
    n = len(frames)
    sep = 0.30
    tw = (W - (n - 1) * sep) / n
    th = tw / FRAME_ASPECT
    name_h, tag_h = 0.72, 0.40
    total = th + 0.12 + name_h + 0.04 + tag_h
    ty = y0 + max(0.0, (H - total) / 2)
    rdir = Path(renders_dir) if renders_dir else None
    out = []
    for i, f in enumerate(frames):
        x = x0 + i * (tw + sep)
        pic_name = spec.get("morph_first_as") if i == 0 and spec.get("morph_first_as") else f"film_{i + 1}"
        descr = spec.get("alt") if i == 0 and spec.get("alt") else f"Thumbnail {i + 1}: {names[i]}"
        path = rdir / f if rdir else None
        if path is not None and path.is_file():
            pic = slide.shapes.add_picture(str(path), inch(x), inch(ty), inch(tw), inch(th))
            set_alt(pic, descr, pic_name)
            out.append(pic)
        else:
            ph = _box(slide.shapes, x, ty, tw, th, fill=st.navy, rounded=False, name=pic_name)
            _frame(ph.text_frame, anchor=MSO_ANCHOR.MIDDLE, margins=(0.05, 0.05, 0.05, 0.05))
            _paras(ph.text_frame, st, [{"text": f"[{f}]", "size": 12, "color": st.white}],
                   align=PP_ALIGN.CENTER)
            set_alt(ph, descr, pic_name)
            out.append(ph)
        if i < n - 1:
            # block arrow, 0.22 in square, centred in the gap at the thumbnails' mid-height
            out.append(_arrow(slide.shapes, x + tw + sep / 2, ty + th / 2, 0.22, 0.22, st.highlight,
                              f"film_sep_{i + 1}"))
        lx, lw = x - sep / 2 + 0.02, tw + sep - 0.04
        # a name wider than the thumbnail breaks at its last space ("Ground\nremoval", as "Voxel\ndownsampling"):
        # two lines fit the 0.72 in name box, and the wrap no longer depends on the renderer's metrics
        nb = _textbox(slide.shapes, st, lx, ty + th + 0.12, lw, name_h,
                      _name_paras(break_name(names[i], tw), st), align=PP_ALIGN.CENTER, name=f"film_name_{i + 1}")
        nb.text_frame.word_wrap = False
        out.append(nb)
        if tags[i]:
            out.append(_textbox(slide.shapes, st, lx, ty + th + 0.12 + name_h + 0.04, lw, tag_h,
                                [{"text": tags[i], "size": 20, "color": st.text_small}],
                                align=PP_ALIGN.CENTER, name=f"film_tag_{i + 1}"))
    return out


# ------------------------------------------------------------------------------------------
# Slide 18: the toll diagram
# ------------------------------------------------------------------------------------------

def add_toll_diagram(slide, box, spec, style=None, n_pairs=6):
    """Python lane above a dashed navy boundary, compiled code below. Left: a code chip and
    ``n_pairs`` slate down/up arrow pairs, each paying a blue toll tick on the boundary and doing a
    small grey piece of work, then "× N" (navy). Right: one call, one toll, one long work bar. The ticks are the
    diagram's only blue.

    spec: ``loop_code``, ``call_code``, ``lane_top``, ``lane_bottom``, ``times`` (all from
    content.yaml; a missing one shows as ``[visual.<key>]``), optional ``toll_label`` (a blue word that
    names the ticks on the boundary, drawn right of the last loop tick), ``alt``, ``name``.
    Returns [group].
    """
    st = Style(style)
    x0, y0, W, H = emu_box(box)
    lane_top = _word(spec, "lane_top")
    lane_bot = _word(spec, "lane_bottom")
    times = _word(spec, "times")
    name = spec.get("name", "toll_diagram")
    alt = spec.get("alt") or (f"Diagram: {lane_top} above a dashed boundary, {lane_bot} below. "
                              f"{spec['loop_code']} crosses it once per point; "
                              f"{spec['call_code']} crosses it once.")
    grp = _group(slide, name, alt)
    S = grp.shapes

    chip_h, work_h, lane_w, cap_h = 0.52, 0.32, 1.75, 0.36
    label_w = 2.0     # lane labels: "compiled code" fits on one line at 20 pt; ends left of the loop code box
    chip_y = y0 + 0.05
    free = max(0.8, H - 0.05 - chip_h - work_h - cap_h - 0.10)  # vertical room for the arrows
    y_line = chip_y + chip_h + 0.55 * free   # the boundary
    work_y = y_line + 0.45 * free            # top of the work blocks

    # lane labels and boundary
    # lane labels: zero left inset, so they start on the title's text edge like the support line
    _textbox(S, st, x0, y_line - 0.55, label_w, 0.45,
             [{"text": lane_top, "size": 20, "bold": True, "color": st.navy}],
             anchor=MSO_ANCHOR.BOTTOM, margins=(0.0, 0.0, 0.0, 0.0), name="toll_lane_top")
    _textbox(S, st, x0, y_line + 0.10, label_w, 0.45,
             [{"text": lane_bot, "size": 20, "bold": True, "color": st.navy}],
             anchor=MSO_ANCHOR.TOP, margins=(0.0, 0.0, 0.0, 0.0), name="toll_lane_bottom")
    _connector(S, x0, y_line, x0 + W, y_line, st.highlight, 2.25, dash=MSO_LINE_DASH_STYLE.DASH,
               name="toll_boundary")

    def call(xd, xu, w_left, w_right, idx, tag, aw=1.25):
        """One call: arrow down at xd, work block, arrow up at xu, toll tick at xd."""
        top = chip_y + chip_h + 0.06
        # arrows slate, so the blue toll ticks on them stay the slide's one highlight (with the hero)
        _connector(S, xd, top, xd, work_y - 0.03, st.text_small, aw, arrow=True, name=f"{tag}_down_{idx}")
        _box(S, w_left, work_y, w_right - w_left, work_h, fill=st.muted, rounded=True,
             name=f"{tag}_work_{idx}")
        _connector(S, xu, work_y - 0.03, xu, top, st.text_small, aw, arrow=True, name=f"{tag}_up_{idx}")
        _box(S, xd - 0.16, y_line - 0.07, 0.32, 0.14, fill=st.highlight, rounded=False,
             name=f"{tag}_toll_{idx}")

    # left: the loop, n_pairs calls
    n_pairs = 9
    pitch, pair = 0.38, 0.16
    lx = x0 + lane_w + 0.35
    span = (n_pairs - 1) * pitch + pair
    char_w = 0.6 * 18 / 72              # Fira Mono at 18 pt: 0.6 em per character
    loop_w = max(span + 0.40, char_w * len(spec["loop_code"]) + 0.36)
    chip = _box(S, lx, chip_y, loop_w, chip_h, fill=st.light, name="toll_loop_code")
    _frame(chip.text_frame, anchor=MSO_ANCHOR.MIDDLE, margins=(0.15, 0.04, 0.10, 0.04), wrap=False)
    _paras(chip.text_frame, st, [{"text": spec["loop_code"], "size": 18, "mono": True,
                                  "color": st.text}])
    px0 = lx + 0.20
    for i in range(n_pairs):
        xd = px0 + i * pitch
        call(xd, xd + pair, xd - 0.04, xd + pair + 0.04, i + 1, "loop")
    _textbox(S, st, px0 + span + 0.18, work_y - 0.05, 1.2, work_h + 0.10,
             [{"text": times, "size": 24, "bold": True, "color": st.navy}],
             anchor=MSO_ANCHOR.MIDDLE, name="toll_times")
    if spec.get("toll_label"):
        # the word that names the toll ticks, just above the boundary, right of the last loop pair
        _textbox(S, st, px0 + span + 0.18, y_line - 0.44, 1.0, 0.38,
                 [{"text": spec["toll_label"], "size": 20, "bold": True, "color": st.highlight}],
                 anchor=MSO_ANCHOR.BOTTOM, name="toll_label")

    # right: one call, all the work below the line
    rx = x0 + W * 0.60
    call_w = char_w * len(spec["call_code"]) + 0.36
    chip = _box(S, rx, chip_y, call_w, chip_h, fill=st.light, name="toll_call_code")
    _frame(chip.text_frame, anchor=MSO_ANCHOR.MIDDLE, margins=(0.15, 0.04, 0.10, 0.04), wrap=False)
    _paras(chip.text_frame, st, [{"text": spec["call_code"], "size": 18, "mono": True,
                                  "color": st.text}])
    xd = rx + 0.20
    call(xd, xd + 0.5, xd - 0.06, x0 + W - 0.05, 1, "call", aw=5.0)
    # captions under the work blocks (words from content.yaml)
    cy = work_y + work_h + 0.06
    _textbox(S, st, lx, cy, rx - lx - 0.3, cap_h,
             [{"text": _word(spec, "caption_loop"), "size": 18, "color": st.text}], name="toll_caption_loop")
    _textbox(S, st, rx, cy, x0 + W - rx, cap_h,
             [{"text": _word(spec, "caption_call"), "size": 18, "color": st.text}], name="toll_caption_call")

    # legend, stacked top right above the boundary (words from content.yaml): what the tick, bar and arrow mean
    row_h = 0.30
    items = [("toll", _word(spec, "legend_toll")), ("work", _word(spec, "legend_work")),
             ("arrow", _word(spec, "legend_arrow"))]
    lgx = x0 + W - max(_width(w, 18) for _, w in items) - 0.45
    for i, (kind, word) in enumerate(items):
        cy_mid = chip_y + i * row_h + row_h / 2
        if kind == "toll":
            _box(S, lgx, cy_mid - 0.07, 0.32, 0.14, fill=st.highlight, rounded=False, name="legend_toll_swatch")
        elif kind == "work":
            _box(S, lgx, cy_mid - 0.09, 0.32, 0.18, fill=st.muted, rounded=True, name="legend_work_swatch")
        else:
            _connector(S, lgx, cy_mid, lgx + 0.32, cy_mid, st.text_small, 1.25, arrow=True, name="legend_arrow_swatch")
        _textbox(S, st, lgx + 0.42, chip_y + i * row_h, _width(word, 18) + 0.1, row_h,
                 [{"text": word, "size": 18, "color": st.text}], anchor=MSO_ANCHOR.MIDDLE, wrap=False,
                 name=f"legend_{kind}")
    return _finish_group(grp, alt, name)


# ------------------------------------------------------------------------------------------
# Slide 22: gotcha table
# ------------------------------------------------------------------------------------------

NO_STYLE_NO_GRID = "{2D5ABB26-0587-4C30-8999-92F81FD0307C}"  # PowerPoint's built-in "No Style, No Grid"


def _cell_border(tcPr, side, color_hex=None, w=12700):
    """Set one border (lnL/lnR/lnT/lnB) of a cell: navy hairline or none."""
    tag = qn(f"a:{side}")
    old = tcPr.find(tag)
    if old is not None:
        tcPr.remove(old)
    ln = etree.Element(tag, w=str(w), cap="flat", cmpd="sng", algn="ctr")
    if color_hex:
        sf = etree.SubElement(ln, qn("a:solidFill"))
        etree.SubElement(sf, qn("a:srgbClr"), val=color_hex)
    else:
        etree.SubElement(ln, qn("a:noFill"))
    etree.SubElement(ln, qn("a:prstDash"), val="solid")
    etree.SubElement(ln, qn("a:round"))
    etree.SubElement(ln, qn("a:headEnd"), type="none", w="med", len="med")
    etree.SubElement(ln, qn("a:tailEnd"), type="none", w="med", len="med")
    order = ["a:lnL", "a:lnR", "a:lnT", "a:lnB"]
    later = order[order.index(f"a:{side}") + 1:] + ["a:lnTlToBr", "a:lnBlToTr", "a:cell3D",
                                                     "a:noFill", "a:solidFill", "a:extLst"]
    for t in later:
        succ = tcPr.find(qn(t))
        if succ is not None:
            succ.addprevious(ln)
            return
    tcPr.append(ln)


def add_gotcha_table(slide, box, spec, style=None):
    """Native table, one row per gotcha: Fira Mono 20 pt token left, Fira Sans 20 pt consequence
    right, navy 1 pt hairlines between rows, no fill.
    Row heights fill the box. spec: ``rows`` [[token, consequence]], ``split``? (share of the
    width for the token column, default 0.55), ``alt``?, ``name``?
    """
    st = Style(style)
    l, t, w, h = (int(v) for v in box)
    rows = spec["rows"]
    n = len(rows)
    gf = slide.shapes.add_table(n, 2, l, t, w, h)
    tbl = gf.table
    tbl_el = tbl._tbl
    tblPr = tbl_el.find(qn("a:tblPr"))
    for attr in ("firstRow", "bandRow", "lastRow", "firstCol", "lastCol", "bandCol"):
        if attr in tblPr.attrib:
            del tblPr.attrib[attr]
    sid = tblPr.find(qn("a:tableStyleId"))
    if sid is None:
        sid = etree.SubElement(tblPr, qn("a:tableStyleId"))
    sid.text = NO_STYLE_NO_GRID
    split = float(spec.get("split", 0.55))
    c0 = int(round(w * split))
    tbl.columns[0].width = c0
    tbl.columns[1].width = w - c0
    rh = h // n
    for r, (token, consequence) in enumerate(rows):
        tbl.rows[r].height = rh
        for c, text in enumerate((token, consequence)):
            cell = tbl.cell(r, c)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.margin_left = inch(0.0 if c == 0 else 0.15)
            cell.margin_right = inch(0.10)
            tf = cell.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            p.alignment = PP_ALIGN.LEFT
            _add_runs(p, str(text), st, size=20, color=st.text, mono=(c == 0))
            tcPr = cell._tc.get_or_add_tcPr()
            for fill_tag in ("a:noFill", "a:solidFill"):
                e = tcPr.find(qn(fill_tag))
                if e is not None:
                    tcPr.remove(e)
            _cell_border(tcPr, "lnL")
            _cell_border(tcPr, "lnR")
            _cell_border(tcPr, "lnT", st.hex["navy"] if r > 0 else None)
            _cell_border(tcPr, "lnB", st.hex["navy"] if r < n - 1 else None)
            etree.SubElement(tcPr, qn("a:noFill"))
    set_alt(gf, spec.get("alt"), spec.get("name", "gotcha_table"))
    return [gf]


# ------------------------------------------------------------------------------------------
# Slide 6: the chain of libraries that works (laspy -> NumPy -> Open3D -> PyVista)
# ------------------------------------------------------------------------------------------

def add_chain(slide, box, spec, style=None):
    """Boxes in one row with navy block arrows between them (the box outline colour; blue stays for the slide's
    one highlight), one box per entry of
    ``spec['items']``: navy 1.5 pt outline, no fill, Fira Sans bold navy text. Box width ``box_w_in``
    (default: the row split evenly with gaps of ``gap_in``, default 0.500 in, the L5 column gap, so
    that with four boxes the outer pairs line up with the two columns below).

    spec: ``items`` [str], ``text_pt`` (default 24), ``alt``?, ``name``?   Returns [group].
    """
    st = Style(style)
    x0, y0, W, H = emu_box(box)
    items = spec["items"]
    n = len(items)
    gap = float(spec.get("gap_in", GAP))
    bw = float(spec.get("box_w_in", (W - (n - 1) * gap) / n))
    text_pt = float(spec.get("text_pt", 24))
    name = spec.get("name", "chain")
    alt = spec.get("alt") or "Chain: " + ", then ".join(items)
    grp = _group(slide, name, alt)
    S = grp.shapes
    for i, it in enumerate(items):
        x = x0 + i * (bw + gap)
        b = _box(S, x, y0, bw, H, line=st.navy, line_w=1.5, name=f"chain_{i + 1}")
        _frame(b.text_frame, anchor=MSO_ANCHOR.MIDDLE, margins=(0.08, 0.04, 0.08, 0.04))
        _paras(b.text_frame, st, [{"text": it, "size": text_pt, "bold": True, "color": st.navy}],
               align=PP_ALIGN.CENTER)
        if i < n - 1:
            # block arrow, 0.30 x 0.26 in, centred in the gap between two boxes
            _arrow(S, x + bw + gap / 2, y0 + H / 2, 0.30, 0.26, st.navy, f"chain_sep_{i + 1}")
    return _finish_group(grp, alt, name)


# ------------------------------------------------------------------------------------------
# Python facts slide: the hand-offs between the libraries, each marked copy or view
# ------------------------------------------------------------------------------------------

def add_handoff_rows(slide, box, spec, style=None):
    """One row per hand-off: the code token (Fira Mono, ``code_pt``, default 22, ink on a light tile), a pill
    (``kind`` copy: white with a navy outline and navy text; view: blue with white text; words from
    ``spec['pills']``) and a short consequence (Fira Sans ``text_pt``, default 22, ink). Rows share one column
    grid and are centred vertically in ``box``.

    spec: ``rows`` [{code, kind, text}], ``pills`` {copy, view}, ``alt``?, ``name``?   Returns [group].
    """
    st = Style(style)
    x0, y0, W, H = emu_box(box)
    rows = spec["rows"]
    code_pt = float(spec.get("code_pt", 22))
    text_pt = float(spec.get("text_pt", 22))
    pills = spec.get("pills") or {}
    name = spec.get("name", "handoffs")
    alt = spec.get("alt") or "; ".join(f"{r['code']}: {r['kind']}, {r['text']}" for r in rows)
    try:
        from .measure import width_in
    except ImportError:  # pragma: no cover
        from measure import width_in  # type: ignore
    code_w = max(width_in(r["code"], code_pt, font="mono") for r in rows) + 0.40
    pill_w = max(width_in(_word(pills, r["kind"]), text_pt, font="title") for r in rows) + 0.60
    row_h = float(spec["row_h_in"]) if "row_h_in" in spec else max(0.62, code_pt * 1.2 / 72 + 0.22)
    gap = float(spec.get("row_gap_in", 0.30))
    total = len(rows) * row_h + (len(rows) - 1) * gap
    y = y0 + max(0.0, (H - total) / 2)
    grp = _group(slide, name, alt)
    S = grp.shapes
    for i, r in enumerate(rows):
        tile = _box(S, x0, y, code_w, row_h, fill=st.tile, name=f"{name}_code_{i + 1}")
        _frame(tile.text_frame, anchor=MSO_ANCHOR.MIDDLE, margins=(0.20, 0.0, 0.10, 0.0), wrap=False)
        _paras(tile.text_frame, st, [{"text": r["code"], "size": code_pt, "mono": True, "color": st.text}])
        px = x0 + code_w + 0.45
        view = r["kind"] == "view"
        pill = _box(S, px, y + 0.03, pill_w, row_h - 0.06, fill=st.highlight if view else st.white,
                    line=None if view else st.navy, line_w=1.5, name=f"{name}_pill_{i + 1}")
        pill.adjustments[0] = 0.5
        _frame(pill.text_frame, anchor=MSO_ANCHOR.MIDDLE, margins=(0.05, 0.0, 0.05, 0.0), wrap=False)
        _paras(pill.text_frame, st, [{"text": _word(pills, r["kind"]), "size": text_pt, "font": st.title_font,
                                      "color": st.white if view else st.navy}], align=PP_ALIGN.CENTER)
        tx = px + pill_w + 0.45
        _textbox(S, st, tx, y, x0 + W - tx, row_h, [{"text": r["text"], "size": text_pt, "color": st.text}],
                 anchor=MSO_ANCHOR.MIDDLE, wrap=False, name=f"{name}_text_{i + 1}")
        y += row_h + gap
    return _finish_group(grp, alt, name)


__all__ = ["add_ecosystem_map", "add_filmstrip", "add_toll_diagram", "add_gotcha_table", "add_chain",
           "add_handoff_rows", "DEFAULT_WORDS", "FRAME_ASPECT"]


# ------------------------------------------------------------------------------------------
# Slide 3: the ecosystem wall (logos in rows)
# ------------------------------------------------------------------------------------------

def add_logo_wall(slide, box, spec, style=None, logos_dir=None):
    """Rows of logo tiles, a row label (20 pt bold) at the left of each row. A tile is a white rounded box with a
    light outline and the project's or company's logo inside, scaled to fit (never stretched, recoloured or
    cropped). An item without a logo file is a text tile with its name, so the wall never shows a hole. A symbol
    that has no name in it carries its name as small print (``caption: true``) under the symbol.

    spec: ``rows`` [{label, items: [{name, file?, caption?, used?}], kind?: "company"}], ``alt``?, ``name``?; layout keys
    (builder, not words): ``label_w_in`` (default 2.45), ``gap_in`` (0.12), ``row_gap_in`` (0.14), ``pad_in`` (0.10).
    All rows share one tile width (the widest row fills the box), so the tiles line up in columns. A row of
    ``kind: company`` has its label slate and its tiles on the light grey, as the other group of the wall.
    """
    from PIL import Image

    st = Style(style)
    x0, y0, W, H = emu_box(box)
    rows = spec["rows"]
    label_w = float(spec.get("label_w_in", 2.45))
    gap = float(spec.get("gap_in", 0.12))
    row_gap = float(spec.get("row_gap_in", 0.14))
    pad = float(spec.get("pad_in", 0.10))
    ncol = max(len(r["items"]) for r in rows)
    tw = (W - label_w - 0.10 - (ncol - 1) * gap) / ncol
    th = (H - (len(rows) - 1) * row_gap) / len(rows)
    ldir = Path(logos_dir) if logos_dir else None
    name = spec.get("name", "ecosystem_wall")
    alt = spec.get("alt") or "Ecosystem wall. " + " ".join(
        f"{r['label']}: " + ", ".join(i["name"] for i in r["items"]) + "." for r in rows)
    grp = _group(slide, name, alt)
    S = grp.shapes
    missing = []
    for ri, row in enumerate(rows):
        y = y0 + ri * (th + row_gap)
        company = row.get("kind") == "company"
        lab = _textbox(S, st, x0, y, label_w, th,
                       [{"text": row["label"], "size": 20, "font": st.title_font,
                         "color": st.text_small if company else st.title}],
                       anchor=MSO_ANCHOR.MIDDLE, name=f"wall_label_{ri + 1}")
        lab.text_frame.word_wrap = True
        x_start = x0 + label_w + 0.10
        for ci, item in enumerate(row["items"]):
            x = x_start + ci * (tw + gap)
            used = bool(item.get("used"))      # used in the talk's pipeline: blue 2.25 pt outline
            _box(S, x, y, tw, th, fill=st.light if company else st.white,
                   line=st.highlight if used else st.light, line_w=2.25 if used else 1.0,
                   name=f"wall_tile_{ri + 1}_{ci + 1}")
            path = ldir / item["file"] if ldir and item.get("file") else None
            if path is not None and path.is_file():
                with Image.open(path) as im:
                    iw, ih = im.size
                cap_h = (12 * 1.25 / 72 + 0.02) if item.get("caption") else 0.0
                bw, bh = tw - 2 * pad, th - 2 * pad - cap_h
                sc = min(bw / iw, bh / ih)
                pw, ph = iw * sc, ih * sc
                px, py = x + (tw - pw) / 2, y + pad + (bh - ph) / 2
                pic = S.add_picture(str(path), inch(px), inch(py), inch(pw), inch(ph))
                set_alt(pic, f"{item['name']} logo", f"wall_logo_{ri + 1}_{ci + 1}")
                if cap_h:
                    _textbox(S, st, x, y + th - pad - cap_h + 0.02, tw, cap_h,
                             [{"text": item["name"], "size": 12, "color": st.text_small}],
                             align=PP_ALIGN.CENTER, name=f"tile_ref_{ri + 1}_{ci + 1}")
            else:
                missing.append(item["name"])
                _textbox(S, st, x + 0.05, y, tw - 0.10, th,
                         [{"text": item["name"], "size": 14, "font": st.medium_font, "color": st.text}],
                         anchor=MSO_ANCHOR.MIDDLE, align=PP_ALIGN.CENTER, name=f"tile_ref_text_{ri + 1}_{ci + 1}")
    out = _finish_group(grp, alt, name)
    slide._wall_missing_logos = missing        # for the build report
    return out
