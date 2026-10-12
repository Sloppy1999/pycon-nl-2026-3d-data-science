# Interfaces between the parts of this project

Everything the deck shows is produced by a script and read from a file. Nothing is typed into the deck by hand.
Run everything with `uv run` from `talk/` (Python 3.13, `.venv`).

| Producer | Writes | Read by |
|---|---|---|
| `pipeline/run.py` | `results/pipeline.json`, `results/labels_crop.npz` | renders, deck, notes |
| `pipeline/render.py` | `renders/*.png`, `renders/render_spec.json`, `renders/labels.json` | deck |
| `snippets/run_all.py` | `results/snippets.json` | deck QA, docs |
| `bench/bench_cliff.py` | `results/bench_cliff.json` | deck (slides 18 to 21, B4) |
| `bench/bench_memory.py` | `results/memory.json` | deck (slides 25, 26, B2) |
| `bench/python_facts.py` | `results/python_facts.json` (copy or view per hand-off, Vector3dVector timings) | deck (slide 8), notes 8, 27 |
| `bench/profile_loop.py` (runs `python -m cProfile -s tottime loop.py` on `bench/loop.py`) | `results/profile_loop.json`, `results/profile_loop.txt` | deck (slide 22) |
| `bench/bench_freethreaded.py` (workers in two throw-away CPython 3.14t / 3.14 venvs) | `results/bench_freethreaded.json` | deck (slide 23), notes 23, 28 |
| `docs/research/collect.py` | `docs/research/**` (cited research files, same sub-paths), `docs/research/MANIFEST.json` | notes and appendix traces ("research:"), `deck/qa/checks.py` |
| `docs/research/research_facts.py` | `results/research_facts.json` (label PILOT: research numbers copied verbatim, nothing measured) | deck (B2, B3, slide 20 alt, notes 8, 20, 22) |
| `deck/build_deck.py` (with `deck/template/pycon_nl_2026_master.pptx`) | `deck/out/20261015_PyCon-NL_3D-Data-Science.pptx`, `deck/out/build_report.json` | `deck/qa/*` |
| `deck/qa/render.py` (private fontconfig `deck/qa/fonts.conf`, Fira only) | `deck/out/20261015_PyCon-NL_3D-Data-Science.pdf`, `deck/out/png/slide-NN.png` | visual QA |
| `deck/qa/checks.py` | `deck/out/qa_checks.json` | QA |

## Data

- `data/utrecht_jaarbeurs_200m.laz`: AHN5 crop, RD New (EPSG:28992) bbox x 135715 to 135915, y 455475 to 455675,
  722 961 points, point format 6, no RGB. Cut from the AHN file `AHN5_C_135000_455000.COPC.LAZ`.
- Source line (slides with AHN data): "Point cloud: AHN5, Actueel Hoogtebestand Nederland (ahn.nl), Het Waterschapshuis,
  CC BY 4.0. AHN file 135000_455000, cropped and processed."
  - On every slide that shows a render from `renders/` (4, 5, 9, 10 to 18) as `Source` / `!!src`, and on slide 29
    with "Licence: creativecommons.org/licenses/by/4.0" after it. The conditions lines (8, 20 to 23, 25, 26, B1, B2,
    B4) and the slide 19 small print name the data and "CC BY 4.0".
  - CC BY 4.0 section 3(a)(1)(C): every "CC BY 4.0" in slide text (and slide 29's URI) is a hyperlink to
    https://creativecommons.org/licenses/by/4.0/ (`deck/build_deck.py` link_licence, content.yaml `meta.licence_url`).
  - `deck/qa/checks.py`: `licence_links` (every "CC BY 4.0" linked) and `source_lines` (every slide with a render
    picture has the source line).

## results/pipeline.json (keys the deck uses)

```
label: "FINAL"
versions: {python, numpy, scipy, laspy, open3d, pyvista}
crop: {file, bbox_rd, points, ahn_classes: {"1": n, "2": n, "6": n, ...}}
params: {voxel, tile, ransac_threshold, ransac_n, ransac_iterations, ransac_probability, seed,
         eps, min_points, cluster_min_height_m, rules: {..., features: {multi, ...}}}
params_why: {tile, eps, min_points, ...}, param_choice   # notes traces only
checks: {ransac_default_probability, ...}                # notes traces only
points_in, points_after_voxel, kept_share, n_tiles
ground: {precision, recall}          # vs AHN class 2, point level, after paint-back
buildings: {precision, recall}       # vs AHN class 6, point level, after paint-back
n_clusters, noise_share, noise_share_note
label_points: {ground, buildings, vegetation, street_furniture, unlabelled}
n_objects: {buildings, vegetation, street_furniture}
runtime_s, runtime_note               # single run, indicative only; load to paint-back, renders not included
```

## results/bench_cliff.json

```
label: "FINAL"
conditions: {cpu, cores, threads, ram_gib, os, kernel, governor, boost, python, numpy, scipy, open3d,
             load_avg_before, load_avg_after, date_utc, data, n, runs, warmup, statistic}
plane: {n, loop_numpy_rows: T, loop_python_floats: T, vectorised: T, equal: bool,
        factor: {median, iqr_low, iqr_high}, factor_python_floats: {median},
        per_step_ns_loop, per_point_ns_vectorised,
        matmul_reference: {expr, equal, max_abs_diff}, plane_fit,
        sensitivity: {vectorised_c_contiguous: T, factor_c_contiguous: {median, iqr_low, iqr_high}}}
knn:   {n, k, loop: T, one_call_1t: T, one_call_all: T (threads),
        factor_loop_vs_1t: {median, iqr_low, iqr_high}, factor_loop_vs_all: {median, ...},
        per_query_us_far, per_query_us_far_knn, per_query_us_typical, per_point_us_one_call_1t}
# T = {median_ms, q1_ms, q3_ms, runs, threads}
# iqr_low = q1(slow)/q3(fast), iqr_high = q3(slow)/q1(fast)
```

## results/memory.json

```
label: "FINAL"
conditions: {...same fields as above...}
tile_1km: {file, points, point_format, record_bytes,
           bytes_per_point: {laspy_read_peak, laspy_read_retained, xyz_float64, open3d_points, pipeline_retained},
           naive_peak_mb, chunked_peak_mb, voxel, chunk_size, chunked_equals_reference: bool,
           cases: {pipeline, ...}, naive_kept_open3d_centroids, chunked_kept_first_points}
big_file: {name: "2023_C_31HZ2.LAZ", points: 926203338, source: "LAS header, 64 KB range request",
           computed_gb: {las_records, laspy_read_peak, plus_xyz, our_pipeline}, formulas}   # computed, not run
ram_reference_gb: [16, 32]
```

## renders/

All frames use ONE camera (stored in `render_spec.json`), local origin = LAS `header.mins` of the crop.

| File | Pixels | Used on |
|---|---|---|
| `f1_load.png` | 1588×1792 | 4 (left frame), 9 (thumb), 10 |
| `f2_voxel.png` | 1588×1792 | 9, 11 |
| `f3_ground.png` | 1588×1792 | 9, 12 |
| `f4_clusters.png` | 1588×1792 | 9, 13 |
| `f5_labels.png` | 1588×1792 | 9, 14 |
| `f6_final.png` | 1588×1792 | 4 (right frame), 9, 15, 16 (chip anchors also on 12 to 14); 17 (zoom, cropped in PowerPoint around the street furniture box) |
| `hook_split.png` | 4190×1792 | not used (former slide 3 frame: left half raw, right half f6 labels) |
| `closeup.png` | 1588×1792 | 5 (same pose, narrow view angle) |
| `plane_sheet.png` | 1588×1792 | 18 (fitted tile planes as translucent sheets, a few distance ticks) |
| `*_gray.png` | same | QA only (grayscale check) |

`labels.json`: `{frame_name: {class_name: [x_px, y_px], ...}, ...}` anchor pixel per class label in that image
(class names: ground, buildings, vegetation, street_furniture). The deck draws the label chips natively.

## snippets/

Each slide snippet is a runnable file. The deck shows only the lines between `# --- slide ---` and
`# --- end ---`. A line ending in `  # <<` is the highlighted key line (marker stripped). Width budget:
35 characters per line on L5/L7/L8 columns, 70 on L4 full width; at most 12 lines.
`snippets/run_all.py` runs every snippet and writes `results/snippets.json` `{name: {ok, seconds, error}}`.
`s02_pcl.cpp` is shown but NOT RUN (no PCL toolchain here). Snippet names keep the slide numbers of 2026-10-03 (for
example `s16_loop.py` is on slide 19 now; `bench_cliff.json` cites them by name); the snippets added on 2026-10-04 are
`s06b_handoffs.py` (slide 8) and `s10b_zen.py` (slide 12 callout).

## New result files (2026-10-04)

```
results/python_facts.json   label, script, conditions,
  las_xyz {fresh_copy_each_access, f_contiguous, ...}, vector3dvector {copies}, asarray_points {view, writeable, ...},
  polydata {shares_memory_c_float64, shares_memory_f_float64, shares_memory_open3d_view},
  timings {v3d_float64_f, v3d_float64_c, v3d_float32, las_xyz_access, asarray_points, polydata_c: T},
  factor_v3d_float32_vs_float64_c, factor_v3d_float32_vs_float64_f {median, iqr_low, iqr_high}, n
results/profile_loop.json   label, command, total_calls, total_s, loop {rank, ncalls, tottime_s, cumtime_s},
  abs {ncalls, ...}, vectorised {...}, share_loop_cumtime, display [lines shown on slide 22], rows_top10, conditions
results/bench_freethreaded.json   label, conditions (driver), threads,
  builds {free_threaded, gil: {python, gil_enabled_at_end, numpy, laspy, equal_to_vectorised,
          timings {loop, vectorised, threads_1 .. threads_16: T}}},
  summary {best_threads_ft, ft_speedup_best_vs_loop, ft_vectorised_vs_best_threads, gil_speedup_vs_loop, ...}
```
Token files: `facts`, `profile`, `ft` (`deck/lib/tokens.py`).

## Deck design (PyCon NL 2026 style, personal talk)

- Master: `deck/template/pycon_nl_2026_master.pptx` (generated by `deck/template/make_master.py`; geometry in
  `deck/template/pycon_nl_2026_master.geometry.json`; sources, palette, contrast, fonts and rules in `docs/DESIGN.md`).
  `deck/build_deck.py` duplicates the master's example slide for each `content.yaml` layout number (1 to 11) and
  draws each slide with the method named by its `build` key (not by slide number).
- Colours: only `deck/content.yaml` `meta.palette` (navy, blue, sage, white, grey, slate, ink, light), read by
  `deck/lib/style.py`; `meta.render_palette` only inside the renders and on the label chip swatches. The builder code
  holds no colour value of its own (`deck/qa/checks.py` `code_colour_literals`).
- Fonts: Fira Sans (titles Fira Sans SemiBold, inherited from the master) and Fira Mono for code, both OFL, in
  `deck/qa/fonts/`. Width estimates use these files (`deck/lib/measure.py`); every character on the slides, in the
  notes and in the charts must have a glyph in its Fira file (`glyph_coverage`; thousands separator U+00A0). The
  presenting laptop needs Fira Sans and Fira Mono installed, or the fonts embedded with PowerPoint's "Embed fonts in
  the file".
- Geometry: every position comes from the master's layout placeholders (`deck/lib/geometry.py`): 0.600 in margin,
  content 1.700 (2.150 under a two-line L7/L8 title) to 6.800 in, footer and slide number on every content slide.
- Footer: "3D Data Science with Python | PyCon NL 2026" (`meta.footer`) and the slide number on every slide except
  the title (1) and closing (29) slides; logo zones on 1 and 29 only (labelled placeholder until the PyCon NL logo
  file and the organisers' permission exist).
- No company master, branding, colour, font, field or metadata anywhere in the package, including the embedded chart
  workbooks (`ppt/embeddings/*.xlsx`, rewritten to Fira Sans by `deck/lib/xmlpost.py`) and `docProps`; the speaker's
  affiliation "ML Engineer, Teqyard" is plain text in the slide 1 presenter line only (`deck/qa/checks.py`
  `no_teqyard`).

## Exceptions to the brief

Approved: the render palette colours inside the renders and on the label chip swatches; no agenda and no chapter
dividers; no date in the footer; PDF export. (Morph on slides 10 to 16 and fade elsewhere follow the brief.)

Further deviations (see `docs/OPEN_ITEMS.md` section h):

1. Dense appendix B1 to B7 at 14 pt or more (the brief's body minimum is 20 pt), 95 % line spacing.
2. Body text over about 20 words on slides 4, 6, 7, 21 and 25 (25: the "works on my machine" joke line) (label chips and diagram labels count): a conflict inside
   the brief, whose "about 20 words" cap meets its request for a one-line "use it for" per library on slide 5.
