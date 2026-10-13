"""Figure for slide 13 (2 Voxel downsampling): the same 3 x 1.5 m patch of the crop before and after
voxel_down_sample(0.5), seen from above, with the 0.5 m cells drawn on both.

Writes deck/assets/concepts/s13_voxel.png. Real points from data/utrecht_jaarbeurs_200m.laz (the densest patch).

    uv run --group figures python deck/concepts/make_voxel_figure.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import make_figures as mf  # noqa: E402  (palette, fonts, save)

sys.path.insert(0, str(mf.TALK))
from pipeline import steps  # noqa: E402

VOXEL, W, H = 0.5, 3.0, 1.5


def main():
    mf.setup()
    C = mf.C
    _, xyz, _ = steps.load(mf.CROP)
    down = np.asarray(steps.downsample(steps.to_open3d(xyz), VOXEL).points)
    # densest W x H patch on a coarse grid of window origins, aligned to the voxel grid
    origin = xyz.min(axis=0) - VOXEL / 2
    # one layer of voxels (the fullest 0.5 m slab in z), so each cell holds one average, seen from above
    iz = np.floor((xyz[:, 2] - origin[2]) / VOXEL).astype(int)
    slab = np.bincount(iz).argmax()
    zlo = origin[2] + slab * VOXEL
    xyz = xyz[iz == slab]
    down = down[(down[:, 2] >= zlo) & (down[:, 2] < zlo + VOXEL)]
    ix = np.floor((xyz[:, :2] - origin[:2]) / [W, H]).astype(int)
    keys, counts = np.unique(ix, axis=0, return_counts=True)
    x0, y0 = origin[:2] + keys[counts.argmax()] * [W, H]

    def inside(p):
        return p[(p[:, 0] >= x0) & (p[:, 0] < x0 + W) & (p[:, 1] >= y0) & (p[:, 1] < y0 + H)]

    before, after = inside(xyz), inside(down)
    fig = plt.figure(figsize=(7.9, 2.9))
    # icon | before | after, equal aspect so a 0.5 m cell is square
    ax_b = fig.add_axes([0.02, 0.18, 0.43, 0.56])
    ax_a = fig.add_axes([0.56, 0.18, 0.43, 0.56])
    for ax in (ax_b, ax_a):
        ax.set_aspect("equal")
        ax.axis("off")
    def grid(ax):
        for g in np.arange(0, W + 1e-9, VOXEL):
            ax.plot([x0 + g] * 2, [y0, y0 + H], color=C["grey"], lw=1.0, zorder=0)
        for g in np.arange(0, H + 1e-9, VOXEL):
            ax.plot([x0, x0 + W], [y0 + g] * 2, color=C["grey"], lw=1.0, zorder=0)

    for ax, title, n in ((ax_b, "Before: every point", len(before)), (ax_a, "After: one average per cell", len(after))):
        ax.set_xlim(x0, x0 + W), ax.set_ylim(y0, y0 + H)
        grid(ax)
        ax.text(x0 + W / 2, y0 + H + 0.12, title, ha="center", va="bottom", fontsize=mf.FS + 1, color=C["navy"],
                fontweight="semibold")
        ax.text(x0 + W / 2, y0 - 0.12, f"{n} points", ha="center", va="top", fontsize=mf.FS + 2, color=C["blue"],
                fontweight="bold")
    ax_b.scatter(before[:, 0], before[:, 1], s=26, color=C["blue"], linewidths=0, zorder=2)
    ax_a.scatter(before[:, 0], before[:, 1], s=26, color=C["blue"], alpha=0.18, linewidths=0, zorder=1)
    ax_a.scatter(after[:, 0], after[:, 1], s=130, color=C["navy"], linewidths=0, zorder=3)
    fig.text(0.505, 0.43, "→", ha="center", va="center", fontsize=36, color=C["navy"])
    mf.save(fig, "s13_voxel.png")
    print(len(before), "->", len(after), "points in the patch")


if __name__ == "__main__":
    main()
