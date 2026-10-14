# Presentation correction and validation record — 2026-10-14

The 28-slide structure, navy/white palette, Fira typography and existing camera are retained.
The generated PPTX and PDF are in `deck/out/`. Unrelated `.DS_Store` files were left untouched.

## Technical corrections

- **Ground removal:** `las.xyz - las.header.mins` translates X, Y **and Z**; local Z is above the crop
  minimum, not height above terrain. The old slide's `z0 < 5` was an intentional crop-specific roof
  shortcut, but its mask differed from the actual evaluated helper in rejected tiles. It would also
  reject elevated terrain on another crop. Slide 14 now calls the full evaluated `remove_ground`
  helper, including tilt/relative-height checks and neighbour-plane repair. Candidate indices are
  ascending indices in the downsampled cloud; `low[inl]` correctly maps subcloud inliers back.
- **Genuine helper defects:** vertical planes no longer divide by zero; rejected tiles without any
  plausible neighbour are cleared rather than left classified as ground; empty clouds have no tiles.
  Regression tests cover those cases and invariance under a vertical translation.
- **Evaluation:** AHN class 2/6 is withheld from classification, then compared with the painted-back
  original-point predictions. This is reference-label agreement on a single crop. The low percentile,
  1.5 m window, 0.4 m tolerance and median-height plausibility check remain dataset heuristics;
  majority-roof tiles and rapidly changing terrain require retuning/another ground method. The full
  sweep and fresh-process determinism check were rerun. Local determinism does not guarantee identical
  planes or voxel ordering across Open3D platforms.
- **Result:** slide 18 uses the original scan and regenerated labels at the same camera/scale, a
  five-category legend, indicative runtime and ground agreement. The per-stage times remain in
  speaker notes. Street-furniture candidates are intentionally enlarged in the existing renderer;
  they are real classified points, not illustrative replacements.
- **Poles:** the recorded BGT snapshot still contains 61 poles; 42 have no above-ground LiDAR return
  under the stated proximity rule. Rechecking current pipeline candidates against that snapshot
  gives distances 0.49, 0.51 and 4.97 m. Three candidates and two near lamp posts remain the honest
  result, not a claim of 3/61 validated pole recall. Flight/register dates differ. Updated verification
  is in `results/review/street_furniture.json`; the historical BGT result file was preserved.
- **Profiler:** 10.5 s and 79 ms are sample-share × 11.9 s for the whole instrumented run, with
  **30 calls of each version** plus imports and LAZ reading. They are not single-call timings.
  Slide 24 explains scope, repetitions and instrumentation. No experiment isolated profiler overhead.
- **Performance narrative:** keep the quiz, direct benchmark, batching explanation, bottleneck
  profile and workload-specific thread comparison. Remove repeated scalar-call-count arithmetic
  from the charts. The 439 ns is a full loop-step average including indexing and arithmetic, not
  isolated boundary overhead. The NumPy expression has several array operations, not literally one
  native crossing. The slide 20 transition connects these decisions to the pipeline and four rules.
- **Free threading:** the original record has matching CPython 3.14.7 and NumPy 2.5.4, GIL-disabled
  vs default/GIL-enabled builds, 1/2/4/8/16 threads, disjoint output slices, randomized variant order,
  one warm-up and seven repetitions. All outputs match. New guards reject mismatched versions,
  build/GIL states and calculations. Charts now follow the measured winning thread count on rebuild.
  The conclusion is explicitly for this loop, not for free-threaded Python generally.
- **Memory:** binary values are now labelled **GiB**, with MiB for the corresponding token formatter.
  926,203,338 × 30 / 2³⁰ = 25.8778 GiB records; × (30 + 24) / 2³⁰ = 46.5801 GiB including xyz.
  86.0717 retained B/input point × the large-file count / 2³⁰ = 74.2449 GiB, extrapolated from the
  smaller tile. Rounded 86 B is labelled approximate. That case is **load + voxel downsampling**,
  not the full classifier or peak. Temporaries increase the corresponding peak extrapolation to
  133.1468 GiB. The separate 0.8 GiB chunked peak is measured on 21,013,926 points in the 1 km tile,
  not on the large file. The script measures coexisting allocations inside each case; incremental
  peaks from independent cases must not be added. Chunked survivors accumulate, and first-per-voxel
  selection is not the same output as centroid downsampling.
- **Closing:** remove the unfinished optional book note; retain contact and AHN/CC BY attribution.
  The repository destination returned HTTP 200 and was decoded from the exported QR. Remote HEAD
  `13f572801c6e9526784623f44365b9f0277da6d6` contains the pipeline, benchmarks, results and deck source.
- **Build portability:** use native XML slide duplication/package checks when external pptx helper
  scripts are absent; support direct LibreOffice export and PyMuPDF when Poppler is absent. QA no
  longer crashes when all transitions are fade or mistakes profile indexing `[i]` for a placeholder.

## Measurements

These compare the stored Linux experiment with the new macOS verification, **not** a controlled
before/after performance regression. Original standalone/profile/thread/memory records remain intact.

| Claim | Stored Linux result | New macOS verification |
|---|---:|---:|
| Ground precision / recall | 98.16% / 94.27% | 98.41% / 94.37% |
| Building reference precision / recall | 83.42% / 98.86% | 82.20% / 98.86% |
| Pipeline runtime, one indicative run | 0.624 s | 0.999 s |
| DBSCAN clusters | 1,024 | 1,026 |
| Roof / vegetation / furniture clusters | 58 / 683 / 3 | 58 / 681 / 3 |
| Standalone loop / NumPy | 317.034 / 2.440 ms (129.91×) | 392.574 / 1.684 ms (233.07×) |
| Free-threaded loop / best threaded loop | 335.801 / 61.142 ms (5.49×, 8 threads) | 419.380 / 125.162 ms (3.35×, 4 threads) |
| Free-threaded NumPy expression | 2.271 ms | 1.871 ms |

The original CPython 3.14.7 download was unavailable; matched 3.14.2 builds with NumPy 2.5.4 were used
for the supplemental worker checks. Both starting and ending GIL states and equivalent outputs were
confirmed. Those workers ran during other validation work. The additional cliff run also had high
load (1-minute average 4.61 at start). They are supplemental checks, not final slide replacements.
See `results/review/` for raw rounds, audit formulas, pipeline comparison and PDF/QR checks.

## Validation and remaining limits

- Ten pipeline tests pass. All 14 Python snippets run successfully and fit their source budgets.
  PCL is unavailable: the C++ snippet was not rerun; its previously recorded output is preserved and
  explicitly labelled as historical on slide 2.
- The pipeline sweep and two fresh-process executions agree exactly on masks, labels and scored
  results on this machine. Real renders and the README pipeline banner were regenerated.
- Main PDF: 28 pages; full presentation reviewed as a contact sheet, with modified layouts inspected
  at full size. No extracted text lies outside a page; expected Fira fonts are embedded. QR decoding
  matches `https://github.com/Sloppy1999/pycon-nl-2026-3d-data-science`.
- Deck build: no missing tokens, placeholders or layout warnings. Structural package checks pass.
  External Office schema validation is unavailable. LibreOffice successfully renders the package.
- Automated slide QA: 40 passes, three advisory warnings (word counts, 18–20 pt labels/notes and
  literal-number review), no failures or pending checks. The deck intentionally retains technical
  code/conditions and backup tables; those advisories are not a claim that every word is large body text.
- The original Scalene profile and Linux RSS memory benchmark were **not rerun**. The memory script
  requires Linux `/proc` and the missing downloaded 1 km tile. Their stored conditions and raw results
  are retained; extrapolations remain estimates. The recorded header dump in `docs/research/dataset/top_tile_headers.txt` confirms point format 6 and
  926,203,338 points; the remote header was not fetched again. Historical eigen-feature/alternative-clustering backup experiments remain historical.
- Vegetation/furniture names are heuristic and lack independent field truth. AHN class 1 includes
  multiple object types; building reference precision does not establish a rigorous true-precision
  lower bound. No universal accuracy, thread-speedup or constant-memory claim is made.

## Reproduction

The current root-level commands are in README.md. For the supplemental runs:

```bash
uv run python bench/bench_cliff.py --smoke --n 722961 --runs 7 --out /tmp/cliff-review.json
# Matched temporary environments: use uv venv, then install numpy==2.5.4 and laspy[lazrs]==2.7.0.
# Workers perform one warm-up and seven timed randomized rounds and check exact equivalence.
FT_VENV/bin/python bench/bench_freethreaded.py --worker > /tmp/free-threaded.json
GIL_VENV/bin/python bench/bench_freethreaded.py --worker > /tmp/gil.json
```

Use an idle machine for final benchmarks. On macOS, Open3D requires libusb and VTK needs an accessible
OpenGL context even for off-screen rendering. Headless rendering/LibreOffice may require permission
outside an execution sandbox. PDF QA dependencies are installed by `uv sync --group qa`.

## Modified files

- `.gitignore`
- `README.md`
- `bench/bench_cliff.py`
- `bench/bench_freethreaded.py`
- `deck/build_deck.py`
- `deck/content.yaml`
- `deck/lib/charts.py`
- `deck/lib/diagrams.py`
- `deck/lib/structure.py`
- `deck/lib/tokens.py`
- `deck/notes.yaml`
- `deck/out/20261015_PyCon-NL_3D-Data-Science.pdf`
- `deck/out/20261015_PyCon-NL_3D-Data-Science.pptx`
- `deck/qa/checks.py`
- `deck/qa/render.py`
- `docs/HOW_TO_UPDATE.md`
- `docs/IMPROVEMENTS.md`
- `docs/img/pipeline.png`
- `pipeline/run.py`
- `pipeline/steps.py`
- `pyproject.toml`
- `renders/closeup.png`
- `renders/f1_load.png`
- `renders/f2_voxel.png`
- `renders/f3_ground.png`
- `renders/f4_clusters.png`
- `renders/f5_labels.png`
- `renders/f5_labels_gray.png`
- `renders/f6_final.png`
- `renders/f6_final_gray.png`
- `renders/hook_split.png`
- `renders/hook_split_gray.png`
- `renders/plane_sheet.png`
- `renders/render_spec.json`
- `results/labels_crop.npz`
- `results/pipeline.json`
- `results/review/audit.json`
- `results/review/bench_cliff.json`
- `results/review/freethreaded-worker.json`
- `results/review/gil-worker.json`
- `results/review/pdf_checks.json`
- `results/review/street_furniture.json`
- `results/snippets.json`
- `snippets/run_all.py`
- `snippets/s10_ground.py`
- `tests/test_steps.py`
- `uv.lock`

## Second review pass — 2026-10-14 (audit of the pass above)

Every number in the pass above was re-derived from `results/*.json`. Arithmetic, units and labels hold.
These presentation defects remained and were fixed:

- **Slide 14 showed configuration, not an algorithm.** `remove_ground` is now the tile loop plus a new
  `steps.check_planes` (the plausibility check and plane borrowing, behaviour unchanged). The slide shows
  the real loop and the `check_planes` call. `snippets/s10_ground.py` asserts that the slide mask equals
  `results/labels_crop.npz`, so 98.4 % / 94.4 % belongs to the code on screen. Pipeline metrics are unchanged
  (bit-identical mask, so `pipeline/run.py` was not rerun). 20 of 64 tiles are flagged; their lowest points
  sit 6.8–43.5 m above the crop minimum.
- **Slide 18 renders were about 3.3 in tall.** The legend and result line moved to a side column
  (`legend_side`), so the renders are about 4.1 in tall at the same camera. The precision format now matches slide 14.
- **Slide 24 discrepancy explained by the data.** 88.04 % × 11.9 s ÷ 30 calls = 349 ms per call. 0.66 % gives
  2.6 ms per call. Slide 22's standalone values are 317 ms and 2.4 ms. Derived in memory by
  `deck/lib/tokens.py Resolver._derive`, without editing results. The remaining ~10 % is not attributed.
- **Slide 25 claimed "GIL threads are slower" without showing it.** Added the GIL ×8 bar (346.5 ms, against
  the 327.1 ms GIL-build loop, 0.94×).
- **Slide 26 compared a measured 1 km value with extrapolated big-file bars.** Added the measured
  load-everything peak on the same 1 km tile (3 093 MiB = 3.0 GiB) next to the chunked peak (839 MiB). That is
  also the source of the slide 27 claim.
- **Slide 27 references** were stale: changed "slides 6, 11" to "10, 12", and "19, 26" to "19, 20".
- **Notes:** slides 14, 23, 24 and 26 are rewritten as speech. The repeated mechanism explanation was removed
  from slide 22, and slide 23 links back to rule 4 and the tile/cluster loops in the pipeline.

QA: 40 pass, 0 fail, 4 advisory warnings. The QR in the final PDF decodes to the repository URL (HTTP 200).
The **remote still lacks today's changes** (remote HEAD = local HEAD `13f5728`).
