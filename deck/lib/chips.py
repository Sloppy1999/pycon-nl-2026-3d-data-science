"""Label chip placement on render frames (slides 3, 12, 13, 14). Pure geometry, inches.

A chip is a rounded rectangle (swatch + class name, 20 pt bold) joined to its anchor pixel by a
straight leader line that ends on the nearest point of the chip edge. ``place`` tries a fixed set
of offsets per chip (above / below / right / left of the anchor, several distances and shifts)
and returns the cheapest combination that satisfies every rule:

* every chip lies inside the frame, ``margin`` away from the frame edge
* no chip overlaps another chip (``gap`` between them) or an obstacle rectangle
* no chip covers any anchor (``anchor_clear`` around it)
* no leader runs through another chip, crosses or touches another leader, or passes close to
  another chip's anchor (it would look like it points there)

Cost per chip = leader length + small penalties for the side and the shift + ``cover_weight``
times the share of the chip that hides render content (``cover(rect)`` callback, 0 to 1).
The search is a depth-first branch and bound over the chips, cheapest candidates first.

``reference`` (class -> Rect) is tried first: if the same chip rectangles are still valid for
the new anchors, they are kept and only the leaders change. Slides 12 to 14 use this so the chips
stay put across the Morph transitions.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable


@dataclass(frozen=True)
class Rect:
    x: float
    y: float
    w: float
    h: float

    @property
    def x2(self) -> float:
        return self.x + self.w

    @property
    def y2(self) -> float:
        return self.y + self.h

    def inflate(self, d: float) -> "Rect":
        return Rect(self.x - d, self.y - d, self.w + 2 * d, self.h + 2 * d)

    def overlaps(self, o: "Rect") -> bool:
        return not (self.x2 <= o.x or o.x2 <= self.x or self.y2 <= o.y or o.y2 <= self.y)

    def contains(self, px: float, py: float) -> bool:
        return self.x <= px <= self.x2 and self.y <= py <= self.y2

    def within(self, outer: "Rect") -> bool:
        return outer.x <= self.x and self.x2 <= outer.x2 and outer.y <= self.y and self.y2 <= outer.y2


Point = tuple[float, float]
Segment = tuple[Point, Point]


@dataclass
class Placement:
    cls: str
    rect: Rect
    end: Point                  # where the leader meets the chip edge
    anchor: Point
    side: str
    cost: float = 0.0
    reused: bool = False


@dataclass
class ChipSpec:
    cls: str
    anchor: Point
    w: float
    h: float


@dataclass
class Rules:
    margin: float = 0.10        # chip to frame edge
    gap: float = 0.10           # chip to chip
    anchor_clear: float = 0.16  # no chip within this distance of any anchor
    leader_clear: float = 0.06  # leader to another chip / another leader
    leader_to_anchor: float = 0.14  # leader to another chip's anchor
    corner_inset: float = 0.12  # leader end stays this far from the chip corners
    min_leader: float = 0.38
    cover_weight: float = 2.0
    side_penalty: dict = field(default_factory=lambda: {"above": 0.0, "below": 0.12, "right": 0.06,
                                                        "left": 0.06})
    dists: tuple = (0.30, 0.45, 0.65, 0.90, 1.20, 1.55)
    hshifts: tuple = (0.5, 0.3, 0.7, 0.12, 0.88)   # share of the chip width left of the anchor
    vshifts: tuple = (0.0, -0.32, 0.32)             # chip centre above/below the anchor (left/right)
    diag_dx: tuple = (0.06, 0.18, 0.35)             # diagonal: chip corner offset from the anchor
    diag_dy: tuple = (0.18, 0.32, 0.55, 0.85)


# ------------------------------------------------------------------------------- geometry
def _orient(a: Point, b: Point, c: Point) -> float:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def segments_intersect(p1: Point, p2: Point, q1: Point, q2: Point) -> bool:
    """True if the two segments cross or touch."""
    return seg_seg_distance(p1, p2, q1, q2) < 1e-9


def point_seg_distance(p: Point, a: Point, b: Point) -> float:
    vx, vy = b[0] - a[0], b[1] - a[1]
    L2 = vx * vx + vy * vy
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((p[0] - a[0]) * vx + (p[1] - a[1]) * vy) / L2))
    return math.hypot(p[0] - (a[0] + t * vx), p[1] - (a[1] + t * vy))


def seg_seg_distance(p1: Point, p2: Point, q1: Point, q2: Point) -> float:
    d1, d2 = _orient(q1, q2, p1), _orient(q1, q2, p2)
    d3, d4 = _orient(p1, p2, q1), _orient(p1, p2, q2)
    if ((d1 > 0 and d2 < 0) or (d1 < 0 and d2 > 0)) and ((d3 > 0 and d4 < 0) or (d3 < 0 and d4 > 0)):
        return 0.0
    return min(point_seg_distance(p1, q1, q2), point_seg_distance(p2, q1, q2),
               point_seg_distance(q1, p1, p2), point_seg_distance(q2, p1, p2))


def segment_hits_rect(a: Point, b: Point, r: Rect) -> bool:
    """Liang-Barsky: does the segment a-b touch the rectangle?"""
    if r.contains(*a) or r.contains(*b):
        return True
    dx, dy = b[0] - a[0], b[1] - a[1]
    t0, t1 = 0.0, 1.0
    for p, q in ((-dx, a[0] - r.x), (dx, r.x2 - a[0]), (-dy, a[1] - r.y), (dy, r.y2 - a[1])):
        if p == 0:
            if q < 0:
                return False
            continue
        t = q / p
        if p < 0:
            t0 = max(t0, t)
        else:
            t1 = min(t1, t)
        if t0 > t1:
            return False
    return True


def nearest_on_rect(p: Point, r: Rect, inset: float = 0.0) -> Point:
    """Nearest point of the rectangle's outline to p (p outside), kept ``inset`` from corners."""
    ix = min(inset, r.w / 2)
    iy = min(inset, r.h / 2)
    x = min(max(p[0], r.x + ix), r.x2 - ix)
    y = min(max(p[1], r.y + iy), r.y2 - iy)
    if r.contains(*p):
        return (x, y)
    # p is outside: snap to the edge facing p
    if p[1] <= r.y:
        return (x, r.y)
    if p[1] >= r.y2:
        return (x, r.y2)
    if p[0] <= r.x:
        return (r.x, y)
    return (r.x2, y)


# ------------------------------------------------------------------------------- candidates
def candidates(c: ChipSpec, rules: Rules):
    ax, ay = c.anchor
    w, h = c.w, c.h
    out = []
    for d in rules.dists:
        for f in rules.hshifts:
            out.append(("above", abs(f - 0.5), Rect(ax - f * w, ay - d - h, w, h)))
            out.append(("below", abs(f - 0.5), Rect(ax - f * w, ay + d, w, h)))
        for v in rules.vshifts:
            out.append(("right", abs(v), Rect(ax + d, ay - h / 2 + v, w, h)))
            out.append(("left", abs(v), Rect(ax - d - w, ay - h / 2 + v, w, h)))
    for dx in rules.diag_dx:
        for dy in rules.diag_dy:
            pen = 0.15 + 0.1 * dx
            out.append(("below", pen, Rect(ax + dx, ay + dy, w, h)))
            out.append(("below", pen, Rect(ax - dx - w, ay + dy, w, h)))
            out.append(("above", pen, Rect(ax + dx, ay - dy - h, w, h)))
            out.append(("above", pen, Rect(ax - dx - w, ay - dy - h, w, h)))
    return out


def _side_of(rect: Rect, p: Point) -> str:
    if p[1] >= rect.y2:
        return "above"
    if p[1] <= rect.y:
        return "below"
    return "right" if p[0] <= rect.x else "left"


class _Cand:
    __slots__ = ("cls", "rect", "end", "anchor", "side", "cost", "seg")

    def __init__(self, cls, rect, end, anchor, side, cost):
        self.cls, self.rect, self.end, self.anchor, self.side, self.cost = cls, rect, end, anchor, side, cost
        self.seg = (anchor, end)


def _unary_ok(cand: _Cand, frame: Rect, anchors: dict, obstacles, rules: Rules) -> bool:
    r = cand.rect
    if not r.within(frame.inflate(-rules.margin)):
        return False
    if any(r.overlaps(o) for o in obstacles):
        return False
    for cls, a in anchors.items():
        if r.inflate(rules.anchor_clear).contains(*a):
            return False
        if cls != cand.cls and point_seg_distance(a, *cand.seg) < rules.leader_to_anchor:
            return False
    if math.dist(cand.anchor, cand.end) < rules.min_leader:
        return False
    if any(segment_hits_rect(cand.anchor, cand.end, o) for o in obstacles):
        return False
    return True


def _pair_ok(a: _Cand, b: _Cand, rules: Rules) -> bool:
    if a.rect.inflate(rules.gap / 2).overlaps(b.rect.inflate(rules.gap / 2)):
        return False
    if segment_hits_rect(*a.seg, b.rect.inflate(rules.leader_clear)):
        return False
    if segment_hits_rect(*b.seg, a.rect.inflate(rules.leader_clear)):
        return False
    if seg_seg_distance(*a.seg, *b.seg) < rules.leader_clear:
        return False
    return True


def _make(c: ChipSpec, rect: Rect, side: str, shift: float, rules: Rules, cover) -> _Cand:
    end = nearest_on_rect(c.anchor, rect, rules.corner_inset)
    length = math.dist(c.anchor, end)
    cost = length + rules.side_penalty.get(side, 0.1) + 0.25 * shift
    if cover is not None:
        cost += rules.cover_weight * float(cover(rect))
    return _Cand(c.cls, rect, end, c.anchor, side, cost)


def place(chips: list[ChipSpec], frame: Rect, *, obstacles=(), rules: Rules | None = None,
          cover: Callable[[Rect], float] | None = None,
          reference: dict[str, Rect] | None = None) -> tuple[list[Placement], dict]:
    """Returns (placements in the input order, info). Raises nothing: if no valid combination
    exists, info['ok'] is False and the cheapest per-chip candidates are returned."""
    rules = rules or Rules()
    obstacles = list(obstacles)
    anchors = {c.cls: c.anchor for c in chips}
    info = {"ok": True, "reused_reference": False, "searched": 0}

    # 1. the reference rectangles (Morph continuity), if they still satisfy every rule
    if reference and all(c.cls in reference for c in chips):
        cands = []
        for c in chips:
            r = reference[c.cls]
            if abs(r.w - c.w) > 1e-6 or abs(r.h - c.h) > 1e-6:
                break
            cands.append(_make(c, r, _side_of(r, c.anchor), 0.0, rules, cover))
        else:
            ok = all(_unary_ok(k, frame, anchors, obstacles, rules) for k in cands) and all(
                _pair_ok(cands[i], cands[j], rules) for i in range(len(cands)) for j in range(i + 1, len(cands)))
            if ok:
                info["reused_reference"] = True
                return [Placement(k.cls, k.rect, k.end, k.anchor, k.side, k.cost, True) for k in cands], info

    # 2. search
    per = []
    for c in chips:
        cs = [_make(c, r, side, shift, rules, cover) for side, shift, r in candidates(c, rules)]
        cs = [k for k in cs if _unary_ok(k, frame, anchors, obstacles, rules)]
        cs.sort(key=lambda k: k.cost)
        per.append(cs)
    order = sorted(range(len(chips)), key=lambda i: len(per[i]))
    info["candidates"] = {chips[i].cls: len(per[i]) for i in range(len(chips))}
    if any(not per[i] for i in order):
        info["ok"] = False
        info["reason"] = "no valid candidate for " + ", ".join(chips[i].cls for i in order if not per[i])
        return _fallback(chips, frame, rules, cover), info
    mins = [per[i][0].cost for i in order]
    rest_min = [sum(mins[k:]) for k in range(len(order) + 1)]
    best: list = [math.inf, None]
    chosen: list[_Cand] = []

    def dfs(k: int, total: float):
        if total + rest_min[k] >= best[0]:
            return
        if k == len(order):
            best[0], best[1] = total, list(chosen)
            return
        for cand in per[order[k]]:
            info["searched"] += 1
            if total + cand.cost + rest_min[k + 1] >= best[0]:
                break                       # sorted by cost: nothing cheaper follows
            if all(_pair_ok(cand, o, rules) for o in chosen):
                chosen.append(cand)
                dfs(k + 1, total + cand.cost)
                chosen.pop()

    dfs(0, 0.0)
    if best[1] is None:
        info["ok"] = False
        info["reason"] = "no collision-free combination"
        return _fallback(chips, frame, rules, cover), info
    by_cls = {k.cls: k for k in best[1]}
    info["cost"] = round(best[0], 3)
    return [Placement(c.cls, by_cls[c.cls].rect, by_cls[c.cls].end, c.anchor, by_cls[c.cls].side,
                      by_cls[c.cls].cost) for c in chips], info


def _fallback(chips, frame, rules, cover):
    out = []
    inner = frame.inflate(-rules.margin)
    for c in chips:
        ax, ay = c.anchor
        x = min(max(ax - c.w / 2, inner.x), inner.x2 - c.w)
        y = min(max(ay - 0.6 - c.h, inner.y), inner.y2 - c.h)
        r = Rect(x, y, c.w, c.h)
        out.append(Placement(c.cls, r, nearest_on_rect(c.anchor, r, rules.corner_inset), c.anchor,
                             _side_of(r, c.anchor)))
    return out


def violations(placements: list[Placement], frame: Rect, *, obstacles=(), rules: Rules | None = None) -> list[str]:
    """Human-readable list of broken rules (used by the builder report and qa/checks.py)."""
    rules = rules or Rules()
    anchors = {p.cls: p.anchor for p in placements}
    out = []
    cands = [_Cand(p.cls, p.rect, p.end, p.anchor, p.side, 0.0) for p in placements]
    for k in cands:
        if not k.rect.within(frame.inflate(-rules.margin + 1e-6)):
            out.append(f"{k.cls}: chip touches or leaves the frame")
        for o in obstacles:
            if k.rect.overlaps(o):
                out.append(f"{k.cls}: chip overlaps an obstacle")
        for cls, a in anchors.items():
            if k.rect.contains(*a):
                out.append(f"{k.cls}: chip covers the {cls} anchor")
    for i in range(len(cands)):
        for j in range(i + 1, len(cands)):
            a, b = cands[i], cands[j]
            if a.rect.overlaps(b.rect):
                out.append(f"{a.cls}/{b.cls}: chips overlap")
            if segment_hits_rect(*a.seg, b.rect):
                out.append(f"{a.cls} leader runs through the {b.cls} chip")
            if segment_hits_rect(*b.seg, a.rect):
                out.append(f"{b.cls} leader runs through the {a.cls} chip")
            if segments_intersect(*a.seg, *b.seg):
                out.append(f"{a.cls}/{b.cls}: leaders cross")
    return out
