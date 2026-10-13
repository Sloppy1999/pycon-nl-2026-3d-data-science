"""Figures for slides 14 to 17 (3 Ground removal, 4 Clustering, 5 Labelling, 6 Visualisation): one schematic strip
each, white background, 18 pt labels, drawn 1:1 on the slide. Fixed point positions, so every build is identical.

    uv run --group figures python deck/concepts/make_step_figures.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle, Rectangle

sys.path.insert(0, str(Path(__file__).parent))
import make_figures as mf  # noqa: E402

C, RP = mf.C, mf.META["render_palette"]
W, H, FS = 5.4, 1.75, 18


def canvas(xlim=(0, 10), ylim=(0, 3.5)):
    fig = plt.figure(figsize=(W, H))
    ax = fig.add_axes([0.01, 0.02, 0.98, 0.96])
    ax.set(xlim=xlim, ylim=ylim)
    ax.set_axis_off()
    return fig, ax


def txt(ax, x, y, s, **kw):
    kw = {"ha": "center", "va": "center", "fontsize": FS, "color": C["navy"], **kw}
    ax.text(x, y, s, **kw)


def ground():
    fig, ax = canvas()
    xs = np.linspace(0.3, 9.7, 24)
    zs = 1.0 + 0.06 * xs + 0.05 * np.sin(xs * 5)
    ax.axvline(5, ymin=0.05, ymax=0.78, color=C["grey"], lw=1.5, ls=(0, (4, 3)))
    for lo, hi in ((0.2, 4.8), (5.2, 9.8)):
        m = (xs > lo) & (xs < hi)
        p = np.polyfit(xs[m], zs[m], 1)
        ax.plot([lo, hi], np.polyval(p, [lo, hi]), color=C["navy"], lw=3)
    ax.scatter(xs, zs, s=22, color=C["blue"], zorder=3)
    ax.scatter(*np.meshgrid(np.linspace(1.4, 3.6, 5), np.linspace(1.9, 2.5, 3)), s=22, color=C["blue"], zorder=3)
    tx, ty = np.array([6.8, 7.3, 7.6, 7.0, 7.9, 7.4, 6.6, 7.8]), np.array([2.0, 2.3, 1.9, 2.5, 2.3, 2.7, 2.3, 2.1])
    ax.scatter(tx, ty, s=22, color=C["blue"], zorder=3)
    txt(ax, 2.5, 3.2, "tile 1")
    txt(ax, 7.5, 3.2, "tile 2")
    txt(ax, 5.0, 0.3, "one plane per tile", color=C["slate"])
    mf.save(fig, "f3_ground_strip.png")


def cluster():
    fig, ax = canvas()
    rng = np.random.default_rng(3)
    a = rng.normal((2.4, 2.1), 0.34, (14, 2))
    b = rng.normal((6.0, 2.1), 0.34, (14, 2))
    ax.scatter(*a.T, s=70, color=C["blue"], zorder=3)
    ax.scatter(*b.T, s=70, color=C["sage"], edgecolor=C["navy"], linewidth=1.0, zorder=3)
    ax.scatter([9.0], [2.6], s=70, color=C["grey"], zorder=3)
    c0 = a[np.argmin(np.hypot(*(a - a.mean(0)).T))]
    ax.add_patch(Circle(c0, 0.62, fill=False, ec=C["navy"], lw=2.2, ls=(0, (4, 3)), zorder=4))
    txt(ax, c0[0] + 1.25, c0[1] - 0.55, "eps", ha="left")
    txt(ax, 2.4, 0.4, "cluster")
    txt(ax, 6.0, 0.4, "cluster")
    txt(ax, 9.0, 1.7, "noise", color=C["slate"])
    mf.save(fig, "f4_cluster_strip.png")


def rules():
    fig, ax = canvas()
    cols = (RP["vegetation"], RP["buildings"], RP["street_furniture"])
    rng = np.random.default_rng(5)
    t = rng.uniform(0, 2 * np.pi, 16)
    ax.scatter(1.7 + 0.8 * np.cos(t) * rng.uniform(0.5, 1, 16), 2.3 + 0.7 * np.sin(t) * rng.uniform(0.5, 1, 16),
               s=40, color=C["blue"])
    ax.add_patch(Rectangle((4.2, 1.9), 1.9, 0.9, fill=False, ec=C["blue"], lw=3))
    ax.add_patch(Rectangle((8.45, 1.9), 0.1, 1.3, color=C["blue"]))
    for x, name, c in zip((1.7, 5.15, 8.5), ("vegetation", "buildings", "street furniture"), cols):
        ax.add_patch(Rectangle((x - 0.2, 0.95), 0.4, 0.4, fc=c, ec=C["navy"], lw=1.5))
        ax.annotate("", (x, 1.4), (x, 1.7), arrowprops=dict(arrowstyle="-|>", color=C["navy"], lw=1.5))
        txt(ax, x, 0.35, name)
    mf.save(fig, "f5_rules_strip.png")


def paint():
    fig, ax = canvas()
    rng = np.random.default_rng(7)
    for x, c in zip((1.9, 5.0, 8.1), (RP["buildings"], RP["vegetation"], RP["ground"])):
        p = rng.normal((x, 2.1), 0.5, (8, 2))
        ax.scatter(*p.T, s=60, color=c, edgecolor=C["navy"], linewidth=0.8, zorder=2)
        ax.scatter([x], [2.1], s=800, color=c, edgecolor=C["navy"], linewidth=2.2, zorder=3)
    txt(ax, 5.0, 0.4, "each point takes its nearest voxel's colour")
    mf.save(fig, "f6_paint_strip.png")


if __name__ == "__main__":
    mf.setup()
    for f in (ground, cluster, rules, paint):
        f()
    print("wrote f3_ground_strip, f4_cluster_strip, f5_rules_strip, f6_paint_strip")
