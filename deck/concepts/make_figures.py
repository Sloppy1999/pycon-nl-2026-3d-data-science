"""Figures for the mental-model backup slides C1 to C6 (deck/content.yaml appendix, deck/appendix.yaml).

Writes deck/assets/concepts/c1_representations.png ... c6_scale.png and results/concepts.json (every number
drawn into a figure; the slides and notes read them as {concept.*} tokens). Reads the crop
(data/utrecht_jaarbeurs_200m.laz) for C2 and C5, results/pipeline.json and results/memory.json for C6; C1, C3 and C4
are drawn from small synthetic shapes (stated in each caption). Colours: deck/content.yaml meta.palette.

    uv sync --group figures && uv run python deck/qa/setup_fonts.py   # once: matplotlib, Fira fonts
    uv run --group figures python deck/concepts/make_figures.py
"""
from __future__ import annotations

import json
from pathlib import Path

import laspy
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import yaml  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402
from mpl_toolkits.mplot3d.art3d import Poly3DCollection  # noqa: E402

TALK = Path(__file__).resolve().parents[2]
OUT = TALK / "deck" / "assets" / "concepts"
FONTS = TALK / "deck" / "qa" / "fonts"
CROP = TALK / "data" / "utrecht_jaarbeurs_200m.laz"
META = yaml.safe_load((TALK / "deck" / "content.yaml").read_text(encoding="utf-8"))["meta"]
C = META["palette"]
SIZE = (7.2, 4.5)          # inches, drawn 1:1 on the slide (deck/build_deck.py slide_concept), so pt sizes are real
FS = 14                    # smallest text in a figure (appendix minimum: 14 pt)
FACTS: dict = {}


def setup():
    for f in sorted(FONTS.glob("Fira*.ttf")):
        font_manager.fontManager.addfont(str(f))
    if not any(f.name == "Fira Sans" for f in font_manager.fontManager.ttflist):
        raise SystemExit("Fira Sans missing: run deck/qa/setup_fonts.py first")
    plt.rcParams.update({"font.family": "Fira Sans", "font.size": FS, "text.color": C["ink"],
                         "axes.labelcolor": C["ink"], "xtick.color": C["slate"], "ytick.color": C["slate"],
                         "axes.edgecolor": C["grey"], "svg.fonttype": "none", "savefig.dpi": 200})
    OUT.mkdir(parents=True, exist_ok=True)


def save(fig, name):
    fig.savefig(OUT / name, facecolor="white", metadata={"Software": None})
    plt.close(fig)


# ------------------------------------------------------------------ C1: one house, three representations
def house():
    """A box 4 x 3 x 2 m with a gable roof to 3 m: vertices and triangles."""
    v = np.array([[0, 0, 0], [4, 0, 0], [4, 3, 0], [0, 3, 0], [0, 0, 2], [4, 0, 2], [4, 3, 2], [0, 3, 2],
                  [0, 1.5, 3], [4, 1.5, 3]], float)
    f = np.array([[0, 1, 5], [0, 5, 4], [1, 2, 6], [1, 6, 5], [2, 3, 7], [2, 7, 6], [3, 0, 4], [3, 4, 7],
                  [4, 5, 9], [4, 9, 8], [7, 6, 9], [7, 9, 8], [0, 4, 8], [1, 9, 5], [2, 6, 9], [3, 8, 7]])
    return v, f


def sample_surface(v, f, n, rng):
    tri = v[f]
    area = 0.5 * np.linalg.norm(np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]), axis=1)
    idx = rng.choice(len(f), n, p=area / area.sum())
    a, b = rng.random((2, n))
    flip = a + b > 1
    a[flip], b[flip] = 1 - a[flip], 1 - b[flip]
    t = tri[idx]
    return t[:, 0] + a[:, None] * (t[:, 1] - t[:, 0]) + b[:, None] * (t[:, 2] - t[:, 0])


def c1():
    rng = np.random.default_rng(1)
    v, f = house()
    pts = sample_surface(v, f, 1500, rng)
    pitch = 0.5
    ijk = np.unique(np.floor(pts / pitch).astype(int), axis=0)
    fig = plt.figure(figsize=SIZE)
    heads = [("Point cloud", f"{len(pts)} × 3 floats\nno connectivity"),
             ("Mesh", f"{len(v)} vertices, {len(f)} triangles\na surface with neighbours"),
             ("Voxel grid", f"{len(ijk)} occupied {pitch} m cells\nvolume at one resolution")]
    for i, (head, sub) in enumerate(heads):
        ax = fig.add_axes([i / 3 - 0.02, 0.18, 1 / 3 + 0.04, 0.86], projection="3d")
        if i == 0:
            ax.scatter(*pts.T, s=3, c=C["blue"], depthshade=False)
        elif i == 1:
            ax.add_collection3d(Poly3DCollection(v[f], facecolor=C["sage"], edgecolor=C["navy"], linewidth=0.8))
        else:
            grid = np.zeros(ijk.max(0) + 1, bool)
            grid[tuple(ijk.T)] = True
            x, y, z = np.indices(np.array(grid.shape) + 1) * pitch
            ax.voxels(x, y, z, grid, facecolors=C["blue"], edgecolor=C["white"], linewidth=0.3, alpha=0.9)
        ax.set(xlim=(0, 4), ylim=(0, 4), zlim=(0, 3.5))
        ax.set_box_aspect((4, 4, 3.5))
        ax.view_init(elev=22, azim=-58)
        ax.set_axis_off()
        fig.text((i + 0.5) / 3, 0.17, head, ha="center", fontsize=18, weight="semibold", color=C["navy"])
        fig.text((i + 0.5) / 3, 0.02, sub, ha="center", fontsize=FS, color=C["slate"], linespacing=1.15)
    save(fig, "c1_representations.png")
    FACTS["c1"] = {"points": len(pts), "vertices": len(v), "triangles": len(f), "voxels": int(len(ijk)),
                   "pitch_m": pitch, "note": "synthetic house, 4 x 3 x 2 m box with a gable roof to 3 m"}


# ------------------------------------------------------------------ C2: one point, three frames
def c2():
    las = laspy.read(CROP)
    p_rd = np.array([las.x[0], las.y[0], las.z[0]])
    mins = np.array(las.header.mins)
    p_loc = p_rd - mins
    step_rd = float(np.spacing(np.float32(p_rd[0])))
    step_loc = float(np.spacing(np.float32(p_loc[0])))
    fig = plt.figure(figsize=SIZE)
    # panel 1: the Netherlands-wide RD frame, the crop as a dot far from its origin
    ax = fig.add_axes([0.13, 0.30, 0.22, 0.55])
    ax.set(xlim=(0, 300_000), ylim=(300_000, 625_000))
    ax.add_patch(plt.Rectangle((mins[0], mins[1]), 4000, 4000, color=C["blue"]))
    ax.annotate("crop", (mins[0] + 2000, mins[1] + 2000), (40_000, 520_000), fontsize=FS, color=C["navy"],
                arrowprops=dict(arrowstyle="->", color=C["navy"]))
    ax.set_xticks([0, 150_000, 300_000], ["0", "150 km", "300 km"], fontsize=FS - 2)
    ax.set_yticks([300_000, 625_000], ["300 km", "625 km"], fontsize=FS - 2)
    ax.set_title("RD New + NAP\nEPSG:7415", fontsize=FS + 2, color=C["navy"], weight="semibold")
    # panel 2: the local frame of the crop
    ax2 = fig.add_axes([0.44, 0.30, 0.22, 0.55])
    ax2.set(xlim=(0, 200), ylim=(0, 200), aspect="equal")
    ax2.plot(*p_loc[:2], "o", ms=9, color=C["blue"])
    ax2.annotate(f"({p_loc[0]:.1f}, {p_loc[1]:.1f})", p_loc[:2], (30, 150), fontsize=FS, color=C["navy"],
                 arrowprops=dict(arrowstyle="->", color=C["navy"]))
    ax2.set_xticks([0, 200], ["0", "200 m"], fontsize=FS - 2)
    ax2.set_yticks([0, 200], ["0", "200 m"], fontsize=FS - 2)
    ax2.set_title("Local frame\nxyz − header.mins", fontsize=FS + 2, color=C["navy"], weight="semibold")
    # arrow between them, with the coordinate before and after
    fig.text(0.07, 0.13, f"RD:     ({p_rd[0]:.1f}, {p_rd[1]:.1f})", fontsize=FS, family="Fira Mono", color=C["ink"])
    fig.text(0.07, 0.04, f"float32 step: {step_rd * 100:.1f} cm  vs  {step_loc * 1e6:.0f} µm local",
             fontsize=FS, color=C["slate"])
    # panel 3: two axis conventions
    # right-handed Z up: y goes into the page; Unity is left-handed Y up: z goes into the page (forward)
    for k, (title, up, depth) in enumerate([("Z up\nLAS, RD + NAP", "z", "y"), ("Y up\nUnity", "y", "z")]):
        ox, oy = 0.76, 0.66 - k * 0.46
        fig.text(ox + 0.11, oy + 0.27, title.replace("\n", ": "), fontsize=FS, ha="center", color=C["navy"], weight="semibold",
                 va="top", linespacing=1.1)
        for (dx, dy, lab) in [(0.10, 0.0, "x"), (0.0, 0.13, up), (0.06, 0.08, depth)]:
            fig.add_artist(matplotlib.patches.FancyArrowPatch((ox + 0.08, oy - 0.03), (ox + 0.08 + dx, oy - 0.03 + dy),
                           transform=fig.transFigure, arrowstyle="-|>", mutation_scale=14, color=C["blue"], lw=2))
            fig.text(ox + 0.08 + dx * 1.25, oy - 0.03 + dy * 1.2, lab, fontsize=FS, ha="center", va="center",
                     family="Fira Mono", color=C["ink"])
    for a in (ax, ax2):
        a.spines[["top", "right"]].set_visible(False)
    save(fig, "c2_frames.png")
    FACTS["c2"] = {"first_point_rd": [round(float(x), 3) for x in p_rd], "header_mins": [float(x) for x in mins],
                   "first_point_local": [round(float(x), 3) for x in p_loc], "float32_step_rd_m": step_rd,
                   "float32_step_local_m": step_loc}


# ------------------------------------------------------------------ C3: order matters
def c3():
    shape = np.array([[0, 0], [2, 0], [2, 1], [1, 1], [1, 2], [0, 2], [0, 0]], float)   # an L-shaped footprint
    th = np.radians(90)
    R = np.array([[np.cos(th), -np.sin(th)], [np.sin(th), np.cos(th)]])
    t = np.array([5.0, 0.0])
    a = shape @ R.T + t           # rotate, then translate
    b = (shape + t) @ R.T         # translate, then rotate
    fig, axs = plt.subplots(1, 2, figsize=SIZE, sharex=True, sharey=True)
    for ax, res, head, code in [(axs[0], a, "Rotate, then translate", "T @ R"),
                                (axs[1], b, "Translate, then rotate", "R @ T")]:
        ax.fill(*shape.T, color=C["light"], ec=C["grey"], lw=1.5)
        ax.fill(*res.T, color=C["blue"], alpha=0.85)
        ax.plot(0, 0, "+", ms=14, mew=2, color=C["ink"])
        ax.text(-0.3, -0.8, "origin", ha="center", fontsize=FS, color=C["slate"])
        ax.text(1.0, 2.3, "before", ha="center", fontsize=FS, color=C["slate"])
        c = res[:-1].mean(0)
        ax.text(c[0], res[:, 1].max() + 0.3, "after", ha="center", fontsize=FS, color=C["navy"], weight="semibold")
        ax.set_title(f"{head}\n{code}", fontsize=FS + 2, color=C["navy"], weight="semibold", linespacing=1.3)
        ax.set(aspect="equal", xlim=(-3, 7.5), ylim=(-1.6, 8.2))
        ax.set_xticks([]), ax.set_yticks([])
        for s in ax.spines.values():
            s.set_color(C["light"])
    fig.text(0.5, 0.03, "Same 90° rotation, same 5 m shift: different place.", ha="center", fontsize=FS,
             color=C["ink"])
    fig.subplots_adjust(left=0.02, right=0.98, top=0.84, bottom=0.10, wspace=0.08)
    save(fig, "c3_order.png")
    FACTS["c3"] = {"rotation_deg": 90, "shift_m": [5.0, 0.0], "note": "synthetic L-shaped footprint, top view"}


# ------------------------------------------------------------------ C4: neighbourhood size changes the answer
def pca_normal_error(pts, true_n, queries, r, tree):
    errs = []
    for q, n_true in zip(queries, true_n):
        idx = tree.query_ball_point(q, r)
        if len(idx) < 3:
            continue
        P = pts[idx] - pts[idx].mean(0)
        n = np.linalg.eigh(P.T @ P)[1][:, 0]
        errs.append(np.degrees(np.arccos(min(1.0, abs(n @ n_true)))))
    return float(np.median(errs)) if errs else np.nan


def c4():
    from scipy.spatial import KDTree
    rng = np.random.default_rng(4)
    density, sigma, slope = 18.0, 0.03, np.radians(30)   # about AHN density here (slide 4); 3 cm noise; 30° roof
    L = 16.0
    n = int(density * L * L)
    xy = rng.uniform(-L / 2, L / 2, (n, 2))
    z = -np.abs(xy[:, 0]) * np.tan(slope) + rng.normal(0, sigma, n)     # a gable roof, ridge along y at x = 0
    pts = np.c_[xy, z]
    tree = KDTree(pts)

    def normal(x):
        s = np.sign(x)
        nv = np.array([s * np.sin(slope), 0 * x, np.cos(slope) + 0 * x]).T
        return nv / np.linalg.norm(nv, axis=1, keepdims=True)

    radii = np.linspace(0.25, 3.0, 23)
    out = {}
    for key, dist in (("flat", 3.5), ("ridge", 0.4)):
        q = np.c_[np.full(200, dist) * rng.choice([-1, 1], 200), rng.uniform(-4, 4, 200)]
        q = np.c_[q, -np.abs(q[:, 0]) * np.tan(slope)]
        out[key] = [pca_normal_error(pts, normal(q[:, 0]), q, r, tree) for r in radii]
    fig, ax = plt.subplots(figsize=SIZE)
    ax.plot(radii, out["flat"], lw=3, color=C["blue"], label="point 3.5 m from the ridge")
    ax.plot(radii, out["ridge"], lw=3, color=C["slate"], ls="--", label="point 0.4 m from the ridge")
    ax.set_xlabel("Neighbourhood radius, m")
    ax.set_ylabel("Normal error, degrees (median)")
    ax.set_ylim(0, max(np.nanmax(out["ridge"]), np.nanmax(out["flat"])) * 1.1)
    ax.legend(frameon=False, loc="center right", bbox_to_anchor=(1.0, 0.17), fontsize=FS)
    i_small = 0
    ax.annotate("too small:\nnoise wins", (radii[i_small], out["flat"][i_small]), (0.55, out["flat"][i_small] * 0.75 + 4),
                fontsize=FS, color=C["navy"], arrowprops=dict(arrowstyle="->", color=C["navy"]))
    ax.annotate("too large:\nthe edge blurs in", (2.4, out["ridge"][19]), (1.7, out["ridge"][19] * 0.45),
                fontsize=FS, color=C["navy"], arrowprops=dict(arrowstyle="->", color=C["navy"]))
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    save(fig, "c4_scale.png")
    FACTS["c4"] = {"density_per_m2": density, "noise_sigma_m": sigma, "roof_slope_deg": 30,
                   "radii_m": radii.round(3).tolist(), "median_error_deg": {k: np.round(v, 2).tolist() for k, v in out.items()},
                   "ridge_best_radius_m": float(radii[int(np.nanargmin(out["ridge"]))]),
                   "ridge_best_error_deg": float(np.nanmin(out["ridge"])),
                   "error_smallest_radius_deg": float(out["flat"][0]), "ridge_error_largest_radius_deg": float(out["ridge"][-1]),
                   "note": "synthetic gable roof; PCA normal of the points within the radius (SciPy KDTree)"}


# ------------------------------------------------------------------ C5: density varies across one crop
def c5():
    las = laspy.read(CROP)
    x, y = np.asarray(las.x - las.header.mins[0]), np.asarray(las.y - las.header.mins[1])
    cell = 2.0
    H, _, _ = np.histogram2d(x, y, bins=int(200 / cell), range=[[0, 200], [0, 200]])
    dens = H.T / cell ** 2
    cmap = LinearSegmentedColormap.from_list("ramp", [C["navy"]] + META["render_palette"]["height_ramp"])
    fig = plt.figure(figsize=SIZE)
    ax = fig.add_axes([0.02, 0.06, 0.50, 0.86])
    vmax = float(np.percentile(dens, 99))
    im = ax.imshow(dens, origin="lower", extent=[0, 200, 0, 200], cmap=cmap, vmin=0, vmax=vmax)
    ax.set_xticks([]), ax.set_yticks([])
    cb = fig.colorbar(im, ax=ax, fraction=0.05, pad=0.02)
    cb.set_label("points per m², 2 m cells", fontsize=FS)
    cb.ax.tick_params(labelsize=FS - 2)
    ax2 = fig.add_axes([0.70, 0.17, 0.28, 0.60])
    ax2.hist(dens.ravel(), bins=40, range=(0, vmax), color=C["blue"])
    med = float(np.median(dens))
    p10, p90 = (float(np.percentile(dens, q)) for q in (10, 90))
    ax2.axvline(med, color=C["ink"], lw=2, ls="--")
    ax2.text(med, ax2.get_ylim()[1] * 0.97, f" median {med:.0f}", fontsize=FS, va="top", color=C["ink"])
    ax2.set_xlabel("points per m²", fontsize=FS)
    ax2.set_yticks([])
    ax2.spines[["top", "right", "left"]].set_visible(False)
    ax2.set_title(f"middle 80 % of cells:\n{p10:.0f} to {p90:.0f} per m²", fontsize=FS, color=C["slate"], loc="left")
    save(fig, "c5_density.png")
    FACTS["c5"] = {"cell_m": cell, "median_per_m2": med, "p10_per_m2": p10, "p90_per_m2": p90,
                   "empty_cells_share": float((dens == 0).mean()), "source": str(CROP.relative_to(TALK))}


# ------------------------------------------------------------------ C6: linear fits, quadratic never does
def c6():
    pipe = json.loads((TALK / "results" / "pipeline.json").read_text(encoding="utf-8"))
    mem = json.loads((TALK / "results" / "memory.json").read_text(encoding="utf-8"))
    marks = [("this crop", pipe["crop"]["points"]), ("1 km AHN file", mem["tile_1km"]["points"]),
             ("big AHN file", mem["big_file"]["points"])]
    ram = float(mem["ram_reference_gb"][1])
    N = np.logspace(3, 10, 200)
    gib = 2.0 ** 30
    fig, ax = plt.subplots(figsize=SIZE)
    ax.loglog(N, N * 24 / gib, lw=3, color=C["blue"], label="xyz, float64: N × 24 B")
    ax.loglog(N, N ** 2 * 8 / gib, lw=3, color=C["slate"], ls="--", label="all pairwise distances: N² × 8 B")
    ax.axhline(ram, color=C["navy"], lw=1.5)
    ax.text(1.3e3, ram * 1.6, f"{ram:.0f} GB RAM", fontsize=FS, color=C["navy"])
    for lab, n in marks:
        ax.axvline(n, color=C["grey"], lw=1, ls=":")
        ax.text(n * 1.15, 1e-5, lab, rotation=90, fontsize=FS - 1, color=C["slate"], va="bottom")
    ax.set_xlabel("Points N")
    ax.set_ylabel("Memory, GB (log scale)")
    ax.set_ylim(1e-6, 1e9)
    ax.legend(frameon=False, loc="lower left", bbox_to_anchor=(0.0, 1.0), fontsize=FS)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    save(fig, "c6_scale.png")
    FACTS["c6"] = {"ram_gb": ram, "marks": {k: int(n) for k, (_, n) in zip(("crop", "tile_1km", "big_file"), marks)},
                   "pairwise_gb_crop": marks[0][1] ** 2 * 8 / gib, "xyz_gb_big_file": marks[2][1] * 24 / gib}


def main():
    setup()
    for fn in (c1, c2, c3, c4, c5, c6):
        fn()
    (TALK / "results" / "concepts.json").write_text(json.dumps(FACTS, indent=2) + "\n", encoding="utf-8")
    print("wrote", ", ".join(sorted(p.name for p in OUT.glob("*.png"))))


if __name__ == "__main__":
    main()
