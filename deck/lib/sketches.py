"""Small explanatory drawings for the deck (added 2026-10-12): the step sketches on the Morph slides (11 to 16), the
copy-or-view legend (9), the rule-of-thumb tiles (6 and 27), the line profile (22) and the data set table (4).

Same shape and rules as lib/diagrams.py: ``f(slide, box, spec, style)``, ``box`` in EMU, every visible word from
``spec`` (content.yaml), native editable shapes only, colours from the palette roles in lib.style (the class colours
of the renders only on shapes named "Swatch", as the QA colour check allows), one group per drawing with the alt
text on the group.

The step sketches are schematic, not data: they show what a step does to a handful of points, drawn on a navy panel
like the renders and the slide 13 callout, with an 18 pt sage caption (a diagram label: QA allows 18 to 20 pt).
Point positions are fixed numbers, so every build draws the same sketch.
"""

from __future__ import annotations

import math

from pptx.enum.dml import MSO_LINE_DASH_STYLE
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Pt

from .charts import Style, emu_box, inch
from .diagrams import _box, _connector, _finish_group, _frame, _group, _paras, _textbox, _width
from .style import RENDER

CAPTION_PT = 18
PAD = 0.14


# ------------------------------------------------------------------------------------------
# primitives
# ------------------------------------------------------------------------------------------

def _dot(S, cx, cy, d, fill, *, line=None, line_w=0.75, name="dot"):
    sh = S.add_shape(MSO_SHAPE.OVAL, inch(cx - d / 2), inch(cy - d / 2), inch(d), inch(d))
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
    sh.name = name
    return sh


def _swatch(S, x, y, w, h, cls, st):
    """A class colour from the render palette (named "Swatch": the one place the QA colour check allows it)."""
    from pptx.dml.color import RGBColor
    sh = _box(S, x, y, w, h, fill=RGBColor.from_string(RENDER[cls]), line=st.white, line_w=0.75, rounded=False,
              name="Swatch")
    return sh


def _panel(S, st, x, y, w, h, name):
    """Navy panel with a sage outline, as the callout on slide 13 and the label chips."""
    return _box(S, x, y, w, h, fill=st.navy, line=st.sage, line_w=1.0, name=name)


def _caption(S, st, x, y, w, text, name):
    h = CAPTION_PT * 1.2 / 72 + 0.02
    _textbox(S, st, x, y, w, h, [{"text": text, "size": CAPTION_PT, "color": st.sage}], align=PP_ALIGN.CENTER,
             wrap=False, name=name)
    return h


# ------------------------------------------------------------------------------------------
# step sketches (Morph slides): one function per `kind`
# ------------------------------------------------------------------------------------------

def add_step_sketch(slide, box, spec, style=None):
    """Navy panel with a sketch of one pipeline step. spec: ``kind`` (origin | voxel | ground | dbscan | rules |
    paint), ``caption`` (not for origin), the kind's words, ``alt``, ``name``?   Returns [group]."""
    st = Style(style)
    x0, y0, W, H = emu_box(box)
    kind = spec["kind"]
    name = spec.get("name", f"Sketch {kind}")
    alt = spec.get("alt") or f"Sketch of the {kind} step"
    grp = _group(slide, name, alt)
    S = grp.shapes
    _panel(S, st, x0, y0, W, H, f"{name} panel")
    cap_h = CAPTION_PT * 1.2 / 72 + 0.02
    if kind != "origin":
        _caption(S, st, x0, y0 + H - PAD - cap_h + 0.04, W, spec.get("caption", ""), f"{name} caption")
    # drawing area above the caption
    ax, ay, aw, ah = x0 + PAD, y0 + PAD, W - 2 * PAD, H - 2 * PAD - (0 if kind == "origin" else cap_h)
    {"origin": _origin, "voxel": _voxel, "ground": _ground, "dbscan": _dbscan, "rules": _rules,
     "paint": _paint}[kind](S, st, ax, ay, aw, ah, spec)
    return _finish_group(grp, alt, name)


def _origin(S, st, x, y, w, h, spec):
    """Two values of x on a navy panel: RD (big) and local (small), the subtraction between them, and float32's
    step at each size on the right."""
    rows = [(spec["rd"] + " m", spec["rd_step"]), (spec["local"] + " m", spec["local_step"])]
    lh = 18 * 1.2 / 72
    head_h = lh + 0.02
    _textbox(S, st, x, y, w, head_h, [{"text": spec.get("step_label", ""), "size": CAPTION_PT,
                                       "color": st.sage}], align=PP_ALIGN.RIGHT, wrap=False, name="origin head")
    gap = (h - head_h - 2 * lh - lh) / 2
    ys = [y + head_h + max(gap, 0.02), None]
    ys[1] = ys[0] + lh + lh + max(gap, 0.02) * 0.6
    for i, ((val, step), yy) in enumerate(zip(rows, ys)):
        _textbox(S, st, x, yy, w * 0.66, lh, [{"text": val, "size": 18, "mono": True, "color": st.white}],
                 align=PP_ALIGN.RIGHT, wrap=False, name=f"origin value {i + 1}")
        _textbox(S, st, x + w * 0.70, yy, w * 0.30, lh, [{"text": step, "size": 18, "color": st.sage,
                                                          "bold": i == 1}],
                 align=PP_ALIGN.RIGHT, wrap=False, name=f"origin step {i + 1}")
    # the operation between the rows, with a down arrow
    my = ys[0] + lh + (ys[1] - ys[0] - lh) / 2
    ar = S.add_shape(MSO_SHAPE.DOWN_ARROW, inch(x + 0.05), inch(my - 0.13), inch(0.18), inch(0.26))
    ar.shadow.inherit = False
    ar.fill.solid()
    ar.fill.fore_color.rgb = st.sage
    ar.line.fill.background()
    ar.name = "origin arrow"
    _textbox(S, st, x + 0.30, my - lh / 2, w * 0.66 - 0.30, lh, [{"text": spec["op"], "size": 18, "mono": True,
                                                                  "color": st.sage}],
             wrap=False, name="origin op")


# fixed point sets in unit coordinates (0..1), so the sketches are identical on every build
_VOX_PTS = [(0.08, 0.22), (0.15, 0.12), (0.19, 0.30), (0.36, 0.10), (0.42, 0.24), (0.30, 0.28), (0.62, 0.18),
            (0.70, 0.08), (0.11, 0.62), (0.21, 0.55), (0.18, 0.80), (0.40, 0.58), (0.47, 0.70), (0.33, 0.85),
            (0.58, 0.62), (0.67, 0.76), (0.73, 0.55), (0.88, 0.62), (0.92, 0.80), (0.83, 0.88), (0.55, 0.45),
            (0.86, 0.20), (0.94, 0.30)]


def _voxel(S, st, x, y, w, h, spec):
    """A 4 x 2 grid of cells with small points; each occupied cell gets one larger sage point at their mean."""
    cols, rows = 4, 2
    side = min(w / cols, h / rows)
    gx, gy = x + (w - cols * side) / 2, y + (h - rows * side) / 2
    for c in range(cols + 1):
        _connector(S, gx + c * side, gy, gx + c * side, gy + rows * side, st.grey, 0.75, name="grid v")
    for r in range(rows + 1):
        _connector(S, gx, gy + r * side, gx + cols * side, gy + r * side, st.grey, 0.75, name="grid h")
    cells: dict = {}
    for u, v in _VOX_PTS:
        px, py = gx + u * cols * side, gy + v * rows * side
        cells.setdefault((min(int(u * cols), cols - 1), min(int(v * rows), rows - 1)), []).append((px, py))
        _dot(S, px, py, 0.05, st.white, name="point")
    for pts in cells.values():
        mx, my = sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)
        _dot(S, mx, my, 0.15, st.sage, line=st.navy, name="voxel mean")


def _ground(S, st, x, y, w, h, spec):
    """Side view: ground points on a gentle slope with a kink at the tile edge, a building and a tree above them,
    one white plane line per tile through its ground points; ground points sage, the rest white."""
    def gz(u):            # ground height (0 = bottom of the area), two slopes, a kink at the tile edge u = 0.5
        return 0.18 + (0.10 * u if u < 0.5 else 0.05 + 0.02 * (u - 0.5))
    base = y + h
    edge = x + w / 2
    tile_dash = _connector(S, edge, y, edge, base, st.grey, 0.75, dash=MSO_LINE_DASH_STYLE.DASH, name="tile edge")
    n = 22
    for i in range(n):
        u = (i + 0.5) / n
        _dot(S, x + u * w, base - gz(u) * h + (0.012 if i % 3 == 0 else -0.01) * h, 0.06, st.sage, name="ground pt")
    # building (left tile) and tree (right tile): white points above the ground
    for i in range(5):
        for j in range(3):
            _dot(S, x + (0.13 + 0.045 * i) * w, base - (0.42 + 0.17 * j) * h, 0.05, st.white, name="building pt")
    for a in range(9):
        t = a / 9 * 2 * math.pi
        _dot(S, x + (0.76 + 0.07 * math.cos(t)) * w, base - (0.62 + 0.14 * math.sin(t)) * h, 0.05, st.white,
             name="tree pt")
    _connector(S, x + 0.76 * w, base - gz(0.76) * h, x + 0.76 * w, base - 0.48 * h, st.white, 1.0, name="trunk")
    for u0, u1 in ((0.0, 0.5), (0.5, 1.0)):     # one plane per tile, through that tile's ground
        _connector(S, x + u0 * w, base - gz(u0 + 1e-6) * h, x + u1 * w, base - gz(u1 - 1e-6) * h, st.white, 2.0,
                   name="tile plane")
    return tile_dash


_CLUSTER_A = [(0.10, 0.45), (0.17, 0.30), (0.20, 0.55), (0.27, 0.40), (0.30, 0.62), (0.35, 0.28), (0.40, 0.48)]
_CLUSTER_B = [(0.60, 0.30), (0.66, 0.45), (0.72, 0.25), (0.76, 0.52), (0.82, 0.38)]
_NOISE = (0.93, 0.80)


def _dbscan(S, st, x, y, w, h, spec):
    """Two clusters (sage, white) of points that each have neighbours within eps (a dashed circle around one of
    them), and one lone grey point: noise."""
    def P(u, v):
        return x + u * w, y + v * h
    r = 0.11 * w
    cx, cy = P(*_CLUSTER_A[3])
    ring = _dot(S, cx, cy, 2 * r, None, line=st.white, line_w=1.0, name="eps ring")
    ring.line.dash_style = MSO_LINE_DASH_STYLE.DASH
    for u, v in _CLUSTER_A:
        _dot(S, *P(u, v), 0.10, st.sage, name="cluster A")
    for u, v in _CLUSTER_B:
        _dot(S, *P(u, v), 0.10, st.white, name="cluster B")
    _dot(S, *P(*_NOISE), 0.10, st.slate, line=st.grey, name="noise")


def _rules(S, st, x, y, w, h, spec):
    """Three cluster shapes (tree crown, flat building, pole), each with a short arrow to its class swatch."""
    sw = 0.22
    shape_h = h - sw - 0.16
    cols = [x + w * (i + 0.5) / 3 for i in range(3)]
    # tree: a crown of points over a trunk
    tx = cols[0]
    for a in range(10):
        t = a / 10 * 2 * math.pi
        _dot(S, tx + 0.28 * math.cos(t), y + shape_h * 0.38 + 0.22 * math.sin(t), 0.06, st.white, name="crown pt")
    _dot(S, tx, y + shape_h * 0.38, 0.06, st.white, name="crown pt")
    _connector(S, tx, y + shape_h * 0.62, tx, y + shape_h, st.white, 1.5, name="trunk")
    # building: a wide low block
    bx = cols[1]
    _box(S, bx - 0.30, y + shape_h * 0.45, 0.60, shape_h * 0.55, line=st.white, line_w=1.5, rounded=False,
         name="building")
    # pole: thin and tall
    px = cols[2]
    _box(S, px - 0.03, y + shape_h * 0.05, 0.06, shape_h * 0.95, fill=st.white, rounded=False, name="pole")
    for cx, cls in zip(cols, ("vegetation", "buildings", "street_furniture")):
        _connector(S, cx, y + shape_h + 0.02, cx, y + shape_h + 0.13, st.sage, 1.25, arrow=True, name="to class")
        _swatch(S, cx - sw / 2, y + h - sw, sw, sw, cls, st)


_VOXELS = [((0.22, 0.45), "buildings"), ((0.55, 0.30), "vegetation"), ((0.82, 0.62), "ground")]
_ORIG = [(0.10, 0.30), (0.14, 0.62), (0.30, 0.65), (0.32, 0.25), (0.45, 0.20), (0.48, 0.48), (0.63, 0.15),
         (0.66, 0.42), (0.72, 0.75), (0.90, 0.48), (0.93, 0.80), (0.75, 0.55)]


def _paint(S, st, x, y, w, h, spec):
    """Three large voxel points with class colours (swatches) and many small original points; a thin line from
    each small point to its nearest voxel, and the small point in that voxel's colour."""
    from pptx.dml.color import RGBColor

    def P(u, v):
        return x + u * w, y + v * h
    vp = [(P(*uv), cls) for uv, cls in _VOXELS]
    for (u, v) in _ORIG:
        px, py = P(u, v)
        (vx, vy), cls = min(vp, key=lambda t: (t[0][0] - px) ** 2 + (t[0][1] - py) ** 2)
        _connector(S, px, py, vx, vy, st.grey, 0.75, name="nearest")
        _dot(S, px, py, 0.08, RGBColor.from_string(RENDER[cls]), name="Swatch")
    for (vx, vy), cls in vp:
        _dot(S, vx, vy, 0.20, RGBColor.from_string(RENDER[cls]), line=st.white, line_w=1.25, name="Swatch")


# ------------------------------------------------------------------------------------------
# copy or view legend (slide 9)
# ------------------------------------------------------------------------------------------

def add_copy_view_legend(slide, box, spec, style=None):
    """Two panels side by side. Copy: two names, each with its own block of memory cells. View: two names, both
    arrows on one block. Under each, the pill word (as in the rows below) and its meaning.

    spec: ``copy`` {head, text}, ``view`` {head, text}, ``names`` [a, b] (default ["a", "b"]), ``alt``?, ``name``?
    """
    st = Style(style)
    x0, y0, W, H = emu_box(box)
    name = spec.get("name", "copy_view_legend")
    alt = spec.get("alt") or "Copy or view legend"
    grp = _group(slide, name, alt)
    S = grp.shapes
    gap = 0.50
    pw = (W - gap) / 2
    names = spec.get("names") or ["a", "b"]
    cell, ncell = 0.26, 5
    row_h = 0.36
    for k, kind in enumerate(("copy", "view")):
        px = x0 + k * (pw + gap)
        d = spec[kind]
        # left part: the drawing
        nx = px
        bx = px + 0.70
        rows_y = [y0 + 0.05, y0 + 0.05 + row_h + 0.18]
        for i, (nm, ry) in enumerate(zip(names, rows_y)):
            _textbox(S, st, nx, ry, 0.45, row_h, [{"text": nm, "size": 20, "mono": True, "color": st.text}],
                     anchor=MSO_ANCHOR.MIDDLE, wrap=False, name=f"{kind} name {i + 1}")
        blocks = rows_y if kind == "copy" else [(rows_y[0] + rows_y[1]) / 2]
        for j, by in enumerate(blocks):
            for c in range(ncell):
                _box(S, bx + c * cell, by + (row_h - cell) / 2, cell, cell,
                     fill=st.highlight if kind == "view" else st.white, line=st.navy, line_w=1.0, rounded=False,
                     name=f"{kind} cell")
        for i, ry in enumerate(rows_y):
            ty = (blocks[i] if kind == "copy" else blocks[0]) + row_h / 2
            _connector(S, nx + 0.32, ry + row_h / 2, bx - 0.05, ty, st.navy, 1.5, arrow=True, name=f"{kind} ref")
        # right part: pill word and meaning
        tx = bx + ncell * cell + 0.35
        view = kind == "view"
        pill_w = _width(d["head"], 20, bold=True) + 0.50
        pill = _box(S, tx, y0 + 0.06, pill_w, 0.42, fill=st.highlight if view else st.white,
                    line=None if view else st.navy, line_w=1.5, name=f"{kind} pill")
        pill.adjustments[0] = 0.5
        _frame(pill.text_frame, anchor=MSO_ANCHOR.MIDDLE, margins=(0.05, 0.0, 0.05, 0.0), wrap=False)
        _paras(pill.text_frame, st, [{"text": d["head"], "size": 20, "font": st.title_font,
                                      "color": st.white if view else st.navy}], align=PP_ALIGN.CENTER)
        _textbox(S, st, tx, y0 + 0.50, px + pw - tx, H - 0.50, [{"text": d["text"], "size": 20, "color": st.text}],
                 name=f"{kind} meaning")
    return _finish_group(grp, alt, name)


def copy_view_legend_height() -> float:
    """Height add_copy_view_legend needs: two name rows, and room for a two-line meaning beside them."""
    return 1.05


# ------------------------------------------------------------------------------------------
# rule-of-thumb tiles (slides 6 and 27)
# ------------------------------------------------------------------------------------------

def add_rule_tiles(slide, box, spec, style=None):
    """2 x 2 light tiles, one rule each: a blue number disc, the rule (24 pt SemiBold navy) and under it either the
    one-line explanation (20 pt ink) or, for the closing slide, the evidence (24 pt SemiBold blue) and the slides
    it comes from (20 pt slate).

    spec: ``rules`` [{head, text? | evidence?, ref?}], ``alt``?, ``name``?   Returns [group].
    """
    st = Style(style)
    x0, y0, W, H = emu_box(box)
    rules = spec["rules"]
    name = spec.get("name", "rule_tiles")
    alt = spec.get("alt") or "; ".join(r["head"] for r in rules)
    grp = _group(slide, name, alt)
    S = grp.shapes
    gx, gy = 0.50, 0.30
    tw, th = (W - gx) / 2, (H - gy) / 2
    disc = 0.56
    for i, r in enumerate(rules):
        x = x0 + (i % 2) * (tw + gx)
        y = y0 + (i // 2) * (th + gy)
        _box(S, x, y, tw, th, fill=st.light, name=f"rule tile {i + 1}")
        d = _dot(S, x + 0.25 + disc / 2, y + 0.25 + disc / 2, disc, st.highlight, name=f"rule number {i + 1}")
        _frame(d.text_frame, anchor=MSO_ANCHOR.MIDDLE, wrap=False)
        _paras(d.text_frame, st, [{"text": str(i + 1), "size": 24, "font": st.title_font, "color": st.white}],
               align=PP_ALIGN.CENTER)
        tx = x + 0.25 + disc + 0.25
        txw = x + tw - 0.25 - tx
        head_pt = 28
        head_lines = _wrap_title(r["head"], head_pt, txw - 0.05)
        head_h = len(head_lines) * head_pt * 1.2 / 72
        hy = y + 0.25 + max(0.0, (disc - head_h) / 2) if len(head_lines) == 1 else y + 0.22
        _textbox(S, st, tx, hy, txw, head_h,
                 [{"text": ln, "size": head_pt, "font": st.title_font, "color": st.title} for ln in head_lines],
                 anchor=MSO_ANCHOR.TOP, wrap=False, name=f"rule head {i + 1}")
        paras = []
        if r.get("text"):
            paras.append({"text": r["text"], "size": 24, "color": st.text})
        if r.get("evidence"):
            paras.append({"text": r["evidence"], "size": 24, "font": st.title_font, "color": st.highlight})
        if r.get("ref"):
            paras.append({"text": r["ref"], "size": 20, "color": st.text_small, "space_before": 6})
        by = max(y + 0.25 + disc, hy + head_h) + 0.15
        _textbox(S, st, tx, by, txw, y + th - 0.20 - by, paras, name=f"rule text {i + 1}")
    return _finish_group(grp, alt, name)


WF_DISC, WF_RX, WF_LABEL_W, WF_THUMB_W, WF_SHIFT = 0.95, 2.2, 2.3, 1.15, -0.5


def workflow_nodes(box, n):
    """Centres (inches) of the ``n`` discs of the workflow ring in ``box`` (x, y, w, h in inches): first stage top
    left, clockwise. The ring sits 0.5 in left of the centre so the thumbnails on the right have room."""
    x0, y0, W, H = box
    cx, cy = x0 + W / 2 + WF_SHIFT, y0 + H / 2
    ry = (H - WF_DISC) / 2 - 0.05
    return [(cx + WF_RX * math.cos(math.radians(-120 + i * 360 / n)),
             cy + ry * math.sin(math.radians(-120 + i * 360 / n))) for i in range(n)], cx, cy


def workflow_thumb(box, n, i, w=WF_THUMB_W):
    """Left x and centre y of the thumbnail of stage ``i`` (0-based): outside its label, on the side of the ring."""
    pos, cx, _ = workflow_nodes(box, n)
    x, y = pos[i]
    edge = WF_DISC / 2 + 0.20 + WF_LABEL_W + 0.12
    return (x - edge - w if x < cx else x + edge), y


def add_workflow(slide, box, spec, style=None):
    """The 3D data science workflow (slide 7) as a ring: numbered discs on an ellipse, joined by solid navy arrows
    clockwise, a label beside each disc (28 pt SemiBold stage, 20 pt ink line, 20 pt SemiBold blue tools), and
    dashed blue arrows through the middle for the loops back (``loops``), with the note ``centre`` between them.
    Disc colour marks the phase: ``tone`` per stage, "navy" (data), "blue" (understanding) or "sage" (delivery).
    The slide's builder places the thumbnails beside the labels (``workflow_thumb``).

    spec: ``stages`` [{head, text, tools?, tone?}], ``loops`` [[from, to]] (1-based), ``centre``?, ``alt``?, ``name``?
    Returns [group].
    """
    st = Style(style)
    x0, y0, W, H = emu_box(box)
    stages = spec["stages"]
    n = len(stages)
    name = spec.get("name", "workflow")
    alt = spec.get("alt") or "; ".join(s["head"] for s in stages)
    grp = _group(slide, name, alt)
    S = grp.shapes
    fills = {"navy": (st.navy, st.white), "blue": (st.highlight, st.white), "sage": (st.sage, st.navy)}
    d = WF_DISC
    pos, cx, cy = workflow_nodes((x0, y0, W, H), n)
    # arrows first so the discs sit on top of their ends
    for k, (f, t_, col, wd, dash) in enumerate(
            [(i + 1, (i + 1) % n + 1, st.navy, 3.5, None) for i in range(n)]
            + [(a, b, st.highlight, 3.0, MSO_LINE_DASH_STYLE.DASH) for a, b in spec.get("loops", [])]):
        (ax, ay), (bx, by) = pos[f - 1], pos[t_ - 1]
        L = math.hypot(bx - ax, by - ay)
        ux, uy = (bx - ax) / L, (by - ay) / L
        m = d / 2 + 0.10
        _connector(S, ax + ux * m, ay + uy * m, bx - ux * m, by - uy * m, col, wd, arrow=True, dash=dash,
                   name=f"{'arrow' if dash is None else 'loop'} {k + 1}")
    for i, s in enumerate(stages):
        x, y = pos[i]
        fill, ink = fills[s.get("tone", "navy")]
        dot = _dot(S, x, y, d, fill, name=f"stage disc {i + 1}")
        _frame(dot.text_frame, anchor=MSO_ANCHOR.MIDDLE, wrap=False)
        _paras(dot.text_frame, st, [{"text": str(i + 1), "size": 32, "font": st.title_font, "color": ink}],
               align=PP_ALIGN.CENTER)
        left = x < cx
        lx = x - d / 2 - 0.20 - WF_LABEL_W if left else x + d / 2 + 0.20
        paras = [{"text": s["head"], "size": 28, "font": st.title_font, "color": st.title},
                 {"text": s["text"], "size": 20, "color": st.text}]
        if s.get("tools"):
            paras.append({"text": s["tools"], "size": 20, "font": st.title_font, "color": st.highlight})
        _textbox(S, st, lx, y - 0.65, WF_LABEL_W, 1.3, paras, anchor=MSO_ANCHOR.MIDDLE,
                 align=PP_ALIGN.RIGHT if left else PP_ALIGN.LEFT, name=f"stage label {i + 1}")
    if spec.get("centre"):
        w = 2 * (WF_RX / 2) - 0.5
        _textbox(S, st, cx - w / 2, cy - 0.6, w, 1.2, [{"text": spec["centre"], "size": 20, "color": st.highlight}],
                 anchor=MSO_ANCHOR.MIDDLE, align=PP_ALIGN.CENTER, name="loop note")
    return _finish_group(grp, alt, name)


def add_tradeoff_cards(slide, box, spec, style=None):
    """One light card per column (slide 6): the name (28 pt SemiBold navy), then "Good for" and "Limits", each a
    20 pt SemiBold blue label over 20 pt ink text.

    spec: ``columns`` [{head, good, limits}], ``alt``?, ``name``?   Returns [group].
    """
    st = Style(style)
    x0, y0, W, H = emu_box(box)
    cols = spec["columns"]
    name = spec.get("name", "tradeoff_cards")
    alt = spec.get("alt") or "; ".join(c["head"] for c in cols)
    grp = _group(slide, name, alt)
    S = grp.shapes
    gx, pad = 0.30, 0.25
    tw = (W - gx * (len(cols) - 1)) / len(cols)
    head_pt = 28
    head_h = head_pt * 1.2 / 72
    for i, c in enumerate(cols):
        x = x0 + i * (tw + gx)
        _box(S, x, y0, tw, H, fill=st.light, name=f"card {i + 1}")
        _textbox(S, st, x + pad, y0 + pad, tw - 2 * pad, head_h,
                 [{"text": c["head"], "size": head_pt, "font": st.title_font, "color": st.title}],
                 anchor=MSO_ANCHOR.TOP, wrap=False, name=f"card head {i + 1}")
        paras = []
        for k, (label, key) in enumerate((("Good for", "good"), ("Limits", "limits"))):
            paras.append({"text": label, "size": 20, "font": st.title_font, "color": st.highlight,
                          "space_before": 0 if k == 0 else 14})
            paras.append({"text": c[key], "size": 20, "color": st.text})
        by = y0 + pad + head_h + 0.20
        _textbox(S, st, x + pad, by, tw - 2 * pad, y0 + H - pad - by, paras, name=f"card text {i + 1}")
    return _finish_group(grp, alt, name)


def _wrap_title(text, size, width):
    """Lines of ``text`` in Fira Sans SemiBold at ``size`` that fit ``width`` (deck/lib/measure.py)."""
    from .measure import wrap_lines
    return wrap_lines(text, size, width, font="title")


# ------------------------------------------------------------------------------------------
# step table (slide 17): header row and one row per step
# ------------------------------------------------------------------------------------------

def add_step_table(slide, box, spec, style=None):
    """Header row in Fira Sans SemiBold navy over a navy rule, then one row per step in Fira Sans ink with light
    rules between them; columns as wide as their widest text (measured) plus a gutter, the spare width to the
    widest column. The last column is right-aligned (times). Rows share the box height up to ``row_h_in``.

    spec: ``columns`` [str], ``rows`` [[str]], ``row_h_in``? (default 0.46), ``alt``?, ``name``?   Returns [group].
    """
    from .measure import width_in
    st = Style(style)
    x0, y0, W, H = emu_box(box)
    cols, rows = spec["columns"], spec["rows"]
    name = spec.get("name", "step_table")
    alt = spec.get("alt") or "Table"
    grp = _group(slide, name, alt)
    S = grp.shapes
    gut = 0.22
    widths = [max([width_in(c, 20, font="title")] + [width_in(r[i], 20) for r in rows]) + gut
              for i, c in enumerate(cols)]
    spare = W - sum(widths)
    widths[2 if len(widths) > 2 else -1] += max(0.0, spare)
    slide._step_table_overflow = max(0.0, -spare)          # for the build report
    rh = min(float(spec.get("row_h_in", 0.46)), H / (len(rows) + 1))
    for ri, row in enumerate([cols] + rows):
        y = y0 + ri * rh
        x = x0
        head = ri == 0
        for ci, (txt, cw) in enumerate(zip(row, widths)):
            last = ci == len(widths) - 1
            _textbox(S, st, x, y, cw - (0 if last else gut), rh,
                     [{"text": txt, "size": 20, "font": st.title_font if head else None,
                       "color": st.title if head else st.text}],
                     anchor=MSO_ANCHOR.MIDDLE, align=PP_ALIGN.RIGHT if last else PP_ALIGN.LEFT, wrap=False,
                     name=f"table {ri}.{ci + 1}")
            x += cw
        if ri:
            _connector(S, x0, y, x0 + W, y, st.navy if ri == 1 else st.light, 1.5 if ri == 1 else 1.0,
                       name="table rule")
    return _finish_group(grp, alt, name)


# ------------------------------------------------------------------------------------------
# per-line CPU profile, as Scalene shows it (slide 22)
# ------------------------------------------------------------------------------------------

def add_line_profile(slide, box, spec, style=None):
    """Source lines with a stacked bar each: Python (navy), native (blue) and system (grey) share of the whole run,
    and the total as a number; a thin rule between groups of lines.

    spec: ``rows`` [{tag?, code, python, native, system, total_text, key?}] (shares in percent of the run; a row
    with ``gap: true`` before it gets a rule), ``legend`` {python, native, system} (words), ``code_pt`` (default 20),
    ``alt``?, ``name``?   The bars share one scale: 100 % = the full bar width.   Returns [group].
    """
    st = Style(style)
    x0, y0, W, H = emu_box(box)
    rows = spec["rows"]
    name = spec.get("name", "line_profile")
    alt = spec.get("alt") or "Per-line CPU profile"
    pt = spec.get("code_pt", 20)
    grp = _group(slide, name, alt)
    S = grp.shapes
    tag_w = max((_width(r.get("tag") or "", 20) for r in rows), default=0) + 0.25
    code_w = max(len(r["code"]) for r in rows) * 0.6 * pt / 72 + 0.25            # Fira Mono advance 0.6 em
    pct_w = max(_width(r["total_text"], 20, bold=True) for r in rows) + 0.15
    bar_x = x0 + tag_w + code_w
    bar_w = W - tag_w - code_w - pct_w - 0.15
    # legend row on top: swatch + word, right-aligned over the bar area
    colours = {"python": st.navy, "native": st.highlight, "system": st.slate}
    lh = 0.34
    leg_w = sum(0.28 + _width(spec["legend"][k], 20) + 0.1 + 0.30 for k in ("python", "native", "system")) - 0.30
    lx = x0 + W - leg_w                      # right-aligned: the legend must not run off the slide
    for k in ("python", "native", "system"):
        word = spec["legend"][k]
        _box(S, lx, y0 + 0.07, 0.20, 0.20, fill=colours[k], rounded=False, name=f"legend {k} swatch")
        ww = _width(word, 20) + 0.1
        _textbox(S, st, lx + 0.28, y0, ww, lh, [{"text": word, "size": 20, "color": st.text}],
                 anchor=MSO_ANCHOR.MIDDLE, wrap=False, name=f"legend {k}")
        lx += 0.28 + ww + 0.30
    gap_h = 0.14
    n_gaps = sum(1 for r in rows if r.get("gap"))
    top = y0 + lh + 0.12
    rh = min(0.62, (H - (top - y0) - n_gaps * gap_h) / len(rows))
    y = top
    for r in rows:
        if r.get("gap"):
            _connector(S, x0, y + gap_h / 2, x0 + W, y + gap_h / 2, color=st.muted, width_pt=0.75, name="rule")
            y += gap_h
        if r.get("tag"):
            _textbox(S, st, x0, y, tag_w, rh, [{"text": r["tag"], "size": 20, "color": st.text_small}],
                     anchor=MSO_ANCHOR.MIDDLE, wrap=False, name="tag")
        _textbox(S, st, x0 + tag_w, y, code_w, rh, [{"text": r["code"], "size": pt, "color": st.text, "mono": True}],
                 anchor=MSO_ANCHOR.MIDDLE, wrap=False, name="code")
        bx = bar_x
        for k in ("python", "native", "system"):
            w_k = bar_w * float(r[k]) / 100.0
            if w_k >= 0.01:
                _box(S, bx, y + 0.09, w_k, rh - 0.18, fill=colours[k], rounded=False, name=f"bar {k}")
            bx += w_k
        tot = float(r["python"]) + float(r["native"]) + float(r["system"])
        _textbox(S, st, bar_x + bar_w * min(tot, 100.0) / 100.0 + 0.12, y, pct_w, rh,
                 [{"text": r["total_text"], "size": 20, "color": st.highlight if r.get("key") else st.text,
                   "bold": bool(r.get("key"))}], anchor=MSO_ANCHOR.MIDDLE, wrap=False, name="share")
        y += rh
    return _finish_group(grp, alt, name)


# ------------------------------------------------------------------------------------------
# data set table (slide 4)
# ------------------------------------------------------------------------------------------

def add_spec_table(slide, box, spec, style=None):
    """A light spec sheet: optional heading (24 pt SemiBold navy), then one row per item, label in Fira Sans
    SemiBold navy, value in Fira Sans ink, a navy rule on top and light rules between rows. Rows share the box
    height.

    spec: ``heading``?, ``rows`` [[label, value]], ``label_w_in``? (default: widest label + 0.25), ``alt``?, ``name``?
    """
    st = Style(style)
    x0, y0, W, H = emu_box(box)
    name = spec.get("name", "spec_table")
    rows = spec["rows"]
    alt = spec.get("alt") or "; ".join(f"{a}: {b}" for a, b in rows)
    grp = _group(slide, name, alt)
    S = grp.shapes
    y = y0
    if spec.get("heading"):
        hh = 24 * 1.2 / 72 + 0.10
        _textbox(S, st, x0, y, W, hh, [{"text": spec["heading"], "size": 24, "font": st.title_font,
                                         "color": st.title}], wrap=False, name="spec heading")
        y += hh + 0.06
    lw = float(spec.get("label_w_in", max(_width(a, 20, bold=True) for a, _ in rows) + 0.30))
    rh = (y0 + H - y) / len(rows)
    for i, (a, b) in enumerate(rows):
        ry = y + i * rh
        _connector(S, x0, ry, x0 + W, ry, st.light if i else st.navy, 1.0 if i else 1.5, name="spec rule")
        _textbox(S, st, x0, ry, lw, rh, [{"text": a, "size": 20, "font": st.title_font, "color": st.title}],
                 anchor=MSO_ANCHOR.MIDDLE, wrap=False, name=f"spec label {i + 1}")
        _textbox(S, st, x0 + lw, ry, W - lw, rh, [{"text": b, "size": 20, "color": st.text}],
                 anchor=MSO_ANCHOR.MIDDLE, wrap=False, name=f"spec value {i + 1}")
    return _finish_group(grp, alt, name)


__all__ = ["add_step_sketch", "add_copy_view_legend", "copy_view_legend_height", "add_rule_tiles", "add_line_profile",
           "add_spec_table", "add_step_table"]
