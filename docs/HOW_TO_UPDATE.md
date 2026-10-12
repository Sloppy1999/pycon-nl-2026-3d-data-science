# How to update the deck

Rule one: **the deck is generated.** Every visible word comes from `deck/content.yaml` (main slides),
`deck/notes.yaml` (speaker notes) and `deck/appendix.yaml` (B1 to B7); every number, chart value and render comes from
a script's output in `results/` or `renders/`. Never edit the PPTX by hand (the next build overwrites it), and never
type a number into the YAML files or hand-edit a result file: re-run the script that produces it.

All commands run from `talk/` with uv (Python 3.13, `.venv`); `uv sync` installs the dependencies, including the
default `deck` group.

## Prerequisites

| For | Needs |
|---|---|
| everything | uv, Python 3.13 (`.python-version`) |
| `data/fetch_ahn5.py` | network access to basisdata.nl (no registration); about 130 MB |
| `deck/build_deck.py` | the PyCon NL 2026 style master `deck/template/pycon_nl_2026_master.pptx` and its geometry `pycon_nl_2026_master.geometry.json` (both in the repo; `uv run python deck/template/make_master.py` regenerates them, docs/DESIGN.md), and the pptx skill's scripts (`add_slide.py`, `clean.py`, `office/validate.py`) under `~/.claude/skills/pptx` or `$PPTX_SKILL_DIR` |
| presenting the deck | Fira Sans and Fira Mono installed on the presenting laptop (Google Fonts, SIL OFL 1.1), or embedded in the file with PowerPoint's "Embed fonts in the file" (File > Options > Save, all characters) |
| `deck/qa/render.py` | LibreOffice (through the pptx skill's `office/soffice.py` wrapper), `pdftoppm`, and the QA fonts from `deck/qa/setup_fonts.py` (git-ignored; that script uses `uvx` for fontTools) |
| the benchmarks | an idle machine: `--final` refuses to start above a 1-minute load average of 1.0 (cliff) or with less than 8 GiB RAM free (memory) unless `--force` is given |

## What feeds what

| Producer | Writes | Feeds |
|---|---|---|
| `data/fetch_ahn5.py` | `data/AHN5_C_135000_455000.COPC.LAZ` (git-ignored), `data/utrecht_jaarbeurs_200m.laz` (the crop, in the repo) | everything |
| `pipeline/run.py` | `results/pipeline.json`, `results/labels_crop.npz` | renders, slides 4 to 18, B1, B2, notes |
| `pipeline/render.py` | `renders/*.png`, `renders/labels.json`, `renders/render_spec.json` | slides 4, 5, 9 to 18; `s13_render.py` reads the camera |
| `snippets/run_all.py` | `results/snippets.json` (ok, lines, width per snippet) | code boxes' QA, notes traces |
| `bench/copc_remote.py --final` | `results/copc_remote.json` (the crop box read from the AHN5 file over HTTP) | B2 |
| `bench/bench_cliff.py --final` | `results/bench_cliff.json` | slides 18 to 21, B1, B4 |
| `bench/bench_memory.py --final` | `results/memory.json` | slides 25, 26, B2 |
| `bench/bench_memory_scalene.py --final` (needs `uv sync --group profile`) | `results/memory_scalene.json`: [Scalene](https://github.com/plasma-umass/scalene)'s memory timeline and per-line memory of `bench/memprof/*.py` on the 1 km tile | slide 26 |
| `bench/bench_memory_trace.py --final` | `results/memory_trace.json`: RSS over time, the cross-check of Scalene's curve (notes only) | notes 26 |
| `bench/python_facts.py --final` | `results/python_facts.json` (copy or view per hand-off, Vector3dVector timings) | slide 8, notes 8 and 27 |
| `bench/profile_loop_scalene.py --final` (needs `uv sync --group profile`) | `results/profile_scalene.json`: [Scalene](https://github.com/plasma-umass/scalene)'s CPU profile of `bench/cpuprof/loop.py` | slide 22 |
| `bench/profile_loop.py --final` | `results/profile_loop.json`, `results/profile_loop.txt` (cProfile of `bench/loop.py`, the cross-check) | notes 22 |
| `deck/ecosystem/merge.py` (reads `part1.yaml` to `part3.yaml` and `overrides.yaml`) | `deck/ecosystem/ecosystem.yaml`, `results/ecosystem.json`, `docs/ECOSYSTEM.md`, `deck/assets/logos/SOURCES.md` | slide 3, B7 |
| `bench/eigen_features.py --final` (needs `--group ml`) | `results/eigen_features.json` (eigenvalue features per cluster, Random Forest vs rules against AHN) | B5, notes 14 and 29 |
| `bench/bench_freethreaded.py --final` | `results/bench_freethreaded.json` (3.14t vs 3.14, threads vs NumPy) | slide 23, notes 23 and 28 |
| `deck/concepts/make_figures.py` (needs `uv sync --group figures` and the QA fonts from `deck/qa/setup_fonts.py`) | `deck/assets/concepts/c1_representations.png` to `c6_scale.png`, `results/concepts.json` | C1 to C6 (figures, captions, `{concept.*}` tokens) |
| `docs/research/research_facts.py` | `results/research_facts.json` (PILOT: research numbers copied verbatim) | B2, B3, slide 25 alt text, a few notes |
| `deck/build_deck.py` | `deck/out/20261015_PyCon-NL_3D-Data-Science.pptx`, `deck/out/build_report.json` | QA |
| `deck/qa/render.py` | `deck/out/*.pdf`, `deck/out/png/slide-NN.png`, `deck/out/qa_render.json` | visual QA |
| `deck/qa/checks.py` | `deck/out/qa_checks.json` | QA |

`docs/research/collect.py` copied the cited research files out of a session scratchpad once; it cannot be re-run
later. Re-run `research_facts.py` only if a file under `docs/research/` changes.

### Per slide

Code boxes show the lines between `# --- slide ---` and `# --- end ---` of the snippet; the line ending in `  # <<` is
the highlighted key line. Numbers are tokens `{file.key|format}` (formats are listed at the top of `content.yaml`).

| Slide | Code (`snippets/`) | Picture | Numbers on screen (result keys) |
|---|---|---|---|
| 1 | none (the joke is text in `content.yaml`) | none | none |
| 2 | `s02_pcl.cpp` (NOT RUN), `s02_python.py` | none | none |
| 3 | none (logo wall: ids in `content.yaml`, logos in `deck/assets/logos/`) | `deck/ecosystem/ecosystem.yaml` entries and orgs | `eco.n_entries` (small print) |
| 4 | none | `f1_load.png`, `f6_final.png`; chips from `labels.json` `f6_final`, edge arrow from `f1_load.jaarbeurs_edge` | none |
| 5 | `s04_repl.py`, shown as its transcript `s04_repl.txt` | `closeup.png` | `pipeline.points_in` (alt text) |
| 6, 7 | none (native diagrams from `content.yaml`) | none | none |
| 8 | rows in `content.yaml` (checked by `s06b_handoffs.py`) | native rows | `facts.factor_v3d_float32_vs_float64_f.median`, `facts.timings.*`; each row's `verify` boolean; conditions |
| 9 | none | `f1_load.png` to `f6_final.png` | none |
| 10 | `s08_load.py` | `f1_load.png` | none |
| 11 | `s09_voxel.py` | `f2_voxel.png` | `pipeline.points_in`, `points_after_voxel`, `params.voxel` |
| 12 | `s10_ground.py`; callout checked by `s10b_zen.py` | `f3_ground.png`; Ground chip from `labels.json` `f6_final` | `pipeline.ground.precision`, `ground.recall` |
| 13 | `s11_cluster.py` | `f4_clusters.png`; Ground chip | `pipeline.n_clusters` |
| 14 | `s12_label.py` | `f5_labels.png`; chips from `f6_final` | `pipeline.n_objects.street_furniture`, `label_points.street_furniture` |
| 15 | `s13_render.py` | `f6_final.png` | as 14 |
| 16 | `s14_pipeline.py` | `f6_final.png` | as 14 |
| 17 | none | lamp posts drawn natively; `f6_final.png` cropped in PowerPoint around `render_spec.json` street furniture box | as 14 |
| 18 | none | `plane_sheet.png` | `bench.plane.n`; `pipeline.n_tiles` (alt) |
| 19 | `s16_loop.py`, `s16_vec.py` (timed verbatim by `bench_cliff.py`), Drake rows | none | `bench.plane.n` |
| 20 | none | native column chart | bars `bench.plane.loop_numpy_rows.median_ms`, `vectorised.median_ms`; hero `plane.factor.median`; `plane.array.*`, `plane.sensitivity.factor_c_contiguous.median`; conditions |
| 21 | none (native diagram) | none | `bench.plane.per_step_ns_loop`, `knn.k`, `knn.per_query_us_far_knn`, `knn.per_query_desc.far_knn.*`; conditions |
| 22 | `bench/cpuprof/loop.py` lines (the slide 19 code), profiled by Scalene | none | `prof.lines.*` (per-line Python, native, system shares); conditions |
| 23 | none | native column chart | `ft.builds.*.timings.*`, `ft.summary.*`; conditions (timed interpreters from `ft.builds`) |
| 24 | none | none | none |
| 25 | none | native bar chart | `memory.ram_reference_gb`, `big_file.computed_gb.*`, `big_file.points`, `tile_1km.bytes_per_point.pipeline_retained`, `tile_1km.bytes_per_point_peak.pipeline`, `tile_1km.points`, `conditions.ram_gib` (machine line); `research.ahn5_c_31hz2` (alt); conditions |
| 26 | `s21_chunked.py` lines, profiled by Scalene (`bench/memprof/chunked.py`) | none | `scalene.cases.*` (peaks and the curve); conditions |
| 27 | none | none | speaker-supplied |
| 28 | none | none | none |
| 29 | none | QR code made from `qr.url` (`deck/assets/qr_repo.png`) | none |
| B1 | `appendix.yaml` | none | `bench.plane.*`, `bench.knn.*`, `pipeline.runtime_s` |
| B2 | `appendix.yaml` | none | `memory.tile_1km.*`, `memory.big_file.*`, `pipeline.kept_share`, `pipeline.params.*`, `research.*` |
| B3 | `appendix.yaml` | none | `research.open3d_tensor`, `research.pytorch3d_knn`, `research.b3_versions` |
| B4 | `appendix.yaml` | none | `bench.knn.*`, `bench.conditions` |
| B5 | `appendix.yaml` | none | `eigen.*`, `eigen.conditions` |
| B6 | `appendix.yaml` (sources: docs/research/reports/videos.md) | none | none |
| B7 | `appendix.yaml` | none | `eco.by_id.*`, `eco.by_status.*`, `eco.n_entries` |
| C1 to C6 | `appendix.yaml` (build: concept; citations: docs/research/reports/mental_models.md) | `deck/assets/concepts/*.png` | `concept.*` |
| C7 to C9 | `appendix.yaml` (dense tables) | none | none |

The conditions lines (8, 20, 21, 22, 23, 25, 26, B1, B2, B4) are composed by `_conditions_text` in
`deck/build_deck.py` from the `conditions` of `bench_cliff.json`, `memory.json`, `python_facts.json`, `profile_loop.json`
or `bench_freethreaded.json`; a slide adds its own `conditions_note` in the YAML. The chart
workbooks are written from the same values, so the team can edit them in PowerPoint, but a rebuild resets them.

## Full rebuild, in order

```bash
uv sync                                           # dependencies (default group "deck" included)

# 1 data (only if data/ is missing something)
uv run python data/fetch_ahn5.py --head           # check the official URL only
uv run python data/fetch_ahn5.py                  # download the 1 km AHN file, write the crop if missing
uv run python data/fetch_ahn5.py --crop-to /tmp/crop.laz --verify-against data/utrecht_jaarbeurs_200m.laz

# 2 pipeline: results/pipeline.json, results/labels_crop.npz (full run with parameter sweep and determinism check)
uv run python pipeline/run.py                     # --quick: pipeline only

# 3 renders: renders/*.png, labels.json, render_spec.json (always all frames for a real change)
uv run python pipeline/render.py

# 4 snippets: results/snippets.json
uv run python snippets/run_all.py
# s02_pcl.cpp needs PCL (no root needed; without it the .cpp is recorded as NOT RUN). Once per machine, outside the repo:
#   mkdir -p ~/pcl && curl -sL https://micro.mamba.pm/api/micromamba/linux-64/latest | tar -xj -C ~/pcl bin/micromamba
#   MAMBA_ROOT_PREFIX=~/pcl/root ~/pcl/bin/micromamba create -y -p ~/pcl/env -c conda-forge pcl cxx-compiler pkg-config
# (PCL 1.15.1, g++ 15.3.0 on 2026-10-12), then build, run and record s02_pcl.cpp ("722961 -> 230519") with
PCL_PREFIX=~/pcl/env uv run python snippets/run_all.py

# 5 benchmarks, on an idle machine, nothing else running (189 s and 79 s on 2026-10-02)
uv run python bench/bench_cliff.py --final
uv run python bench/bench_memory.py --final
uv run python bench/python_facts.py --final        # results/python_facts.json (slide 8; about 15 s)
uv run python bench/profile_loop.py --final        # results/profile_loop.json and .txt (slide 22; one profiled run)
# slide 23: two throw-away venvs (see the docstring of bench/bench_freethreaded.py), then
uv run python bench/bench_freethreaded.py --final --ft FT_VENV/bin/python --gil GIL_VENV/bin/python
# B5: scikit-learn lives in the optional "ml" group; re-run after pipeline/run.py (reads results/labels_crop.npz)
uv run --group ml python bench/eigen_features.py --final

# 6 research numbers (only if docs/research/ changed)
uv run python docs/research/research_facts.py

# 6b the crop's remote COPC read (network; B2)
uv run python bench/copc_remote.py --final

# 7 deck, QA render, checks
uv run python deck/build_deck.py
uv run python deck/qa/setup_fonts.py              # once per machine
uv run python deck/qa/render.py
uv run python deck/qa/checks.py
```

Then look at `deck/out/png/contact.png` and every slide you touched in `deck/out/png/slide-NN.png`, and read
`deck/out/qa_checks.json` (no `fail`; the `warn` and `pending` items are explained in QA_NOTES.md). Two builds from
the same inputs give the same bytes; the document date is `SOURCE_DATE_EPOCH` if set, else the newest input file.

For a wording change only step 7 is needed. After a pipeline change run 3, 4 and 7 as well (the snippets compare
their output with `pipeline.json` and `labels_crop.npz`). The benchmarks read only the crop and the 1 km file, so
they need re-running only when the data, the s16 or s21 snippet lines, the machine or the library versions change.
Bench smoke tests never write into `results/`: `--smoke --out DIR/file.json`.

## Fill in the speaker placeholders

All in `deck/content.yaml` unless noted; the list with the current placeholder text is OPEN_ITEMS.md section b.

```yaml
  - n: 1
    presenter: "Sergio Peral · ML Engineer, Teqyard · <short repo URL>"   # the affiliation stays plain text
    # logo_placeholder: delete the key once the real logo is handled (see below)
  - n: 22
    title: "These <N> gotchas cost me weeks"
    table:
      rows:
        - ["<code token>", "<consequence, at most 4 words>"]   # 4 to 6 rows
    # placeholder_note: delete the key
  - n: 24
    support: "<repo URL>"
    contact: ["Sergio Peral", "<email>", "<GitHub or LinkedIn handle>"]
    qr: {url: "<https://... repo URL>", placeholder: "QR: [repo URL]"}   # the builder writes deck/assets/qr_repo.png
    small_print:
      - ahn_licence
      - "Title shared with F. Poux, ..."   # without brackets, or delete this line (then say it aloud, notes 24)
```

- `deck/notes.yaml` slide 27: replace the `[SPEAKER: ...]` parts of `talk_track` and `answer`; keep the 130 s or
  change `seconds` in both YAML files (below).
- Gotcha tokens are set in Fira Mono 20 pt in a 4.25 in column: about 24 characters fit on one line. Check the render.
- **Logo:** the builder has no key for a logo file yet. Deleting `logo_placeholder` removes the dashed box on slides 1
  and 24. To show the PyCon NL logo (file and the organisers' permission first, OPEN_ITEMS d4), add a picture in
  `deck/build_deck.py` in the same boxes (slide 1: left 9.83, top 5.60, 2.90 × 1.30 in; slide 29: 9.83, 0.60,
  2.90 × 1.30 in) with alt text, or place it by hand in PowerPoint after the last build (a rebuild removes it). On the
  navy slides it needs a light version or a white tile (docs/DESIGN.md section 1).
- **Cup glyph:** slide 1 shows no cup (Fira Mono has no glyph for it). If you add " ☕" back to `subtitle_code`,
  check it on the presenting laptop; `glyph_coverage` in `checks.py` then fails on slide 1 (it has no exemption).
- Afterwards `speaker_placeholders` and `pending_placeholders` in `checks.py` should pass.

## Change a number

1. Never in the deck and never in a YAML file as a literal. Find the token in `content.yaml`, `notes.yaml` or
   `appendix.yaml`, e.g. `{bench.plane.factor.median|x}`, and the key it reads.
2. Re-run the producer of that result file (table above). Result files are labelled FINAL; do not edit them.
3. Rebuild, render, check. `unresolved_tokens` and `literal_numbers` catch missing keys and typed numbers;
   `title_words` catches a title that grew past 8 words.
4. Read the notes' conditional claims (`checks` in `notes.yaml`): `build_deck.py` evaluates them against the new
   results, for example whether "two orders of magnitude" may still be said (`bench.plane.factor.iqr_low` at least 100)
   and whether the chunked points still equal the reference (`memory.tile_1km.chunked_equals_reference`).
5. If the new number changes a sentence's meaning (a title, a support line, "exactly", "even"), reword it in the YAML
   and note the change in QA_NOTES.md section 5.

Re-running the benchmarks on another machine (for example the presenting laptop): run step 5 there with the same
`uv.lock`, then step 7. The conditions lines then name that machine.

## Slides are drawn by `build`, not by number

Each slide in `content.yaml` has `build: <name>`; `deck/build_deck.py` draws it with `slide_<name>` (title, two_code,
split_renders, render_column, ecosystem, chain_lists, handoffs, filmstrip, morph, expectation, plane, drake,
chart_hero, toll, profile, statement, bar_gb, code_hero, gotchas, tiles, closing). To insert a slide, add it with the
next free `n`, renumber the slides after it in `content.yaml` and `notes.yaml` (and the "slide N" references in the
text), and keep `seconds` summing to 1800. `deck/qa/checks.py` finds the Morph chain, the on-click build, the
filmstrip and the closing slide from `content.yaml`, not from fixed numbers.

## Change words, timing or layout

- On-screen words: `content.yaml`; spoken words: `notes.yaml`; backup slides: `appendix.yaml`.
- Rules the checks enforce: titles at most 8 words, sentence case; support lines at most 15 words; about 20 words of
  body text; no en or em dashes anywhere; en-GB; the terms in `meta.terms`; numbers only as tokens.
- Slides 10 to 16 Morph: keep their titles on two lines and do not rename objects (`!!title`, `!!code`, `!!render`,
  `!!support`, `!!src`, `!!lab_*`, `!!small`); `morph_geometry` checks that they stay identical.
- Seconds: change `seconds` in `content.yaml` and `notes.yaml` together, keep the sum at 1800, and update `ends_at` in
  `notes.yaml` and the tables in TIMING.md.

## Change the camera

All renders share one camera, so a change touches slides 4, 5, 9 to 18 at once.

1. Edit `CAMERA` in `pipeline/render.py` (and `CLOSEUP_VIEW_ANGLE` for slide 5). Keep the frame sizes (1588 × 1792 px,
   the hook frame 4190 × 1792) and never call `reset_camera` or `view_isometric`. Update the reason string that
   `render.py` writes as `camera.change_from_reviewed`.
2. `uv run python pipeline/render.py` for all frames (`--only` writes neither `labels.json` nor `render_spec.json`).
3. Read `renders/render_spec.json` `checks`: `camera_unchanged` true for every frame, the greyscale checks pass, every
   `anchors_on_class_*` is `all_on_class: true`. The label chips and the slide 4 edge arrow move with the new anchors in
   `labels.json`.
4. `uv run python snippets/run_all.py`: `s13_render.py` reads the camera from `render_spec.json`.
5. Build, render, check (`label_chips`, `render_no_crop`, `morph_geometry`, `source_lines`), look at slides 4, 5 and 9
   to 15, and re-read the alt texts in `content.yaml` that describe the view.
