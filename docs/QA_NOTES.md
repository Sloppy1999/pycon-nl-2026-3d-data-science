# QA notes

Deck: `deck/out/20261015_PyCon-NL_3D-Data-Science.pptx` ("3D Data Science with Python", PyCon NL 2026, 15 October),
built 2026-10-04 20:21 from the current `deck/content.yaml`, `deck/notes.yaml` and `deck/appendix.yaml` on the
PyCon NL 2026 style master (`deck/template/pycon_nl_2026_master.pptx`, docs/DESIGN.md); QA renders (`deck/out/png/`,
LibreOffice, with the Fira fonts from `deck/qa/fonts/`) from the same build. This file is the brief's "QA notes". What the speaker or the client still has to
supply or decide is in [OPEN_ITEMS.md](OPEN_ITEMS.md); the clock is in [TIMING.md](TIMING.md).

Numbers below are quoted as the deck prints them, with the result key they come from. Nothing here is a new
measurement: every figure is read from `results/*.json`, `renders/render_spec.json` or a cited research file.

## 2026-10-04 extension: more Python, memes and jokes (read this first)

Slides renumbered: old 1 and 2 stay; old 3 to 6 are 4 to 7; old 7 to 14 are 9 to 16 (Morph chain now 10 to 16);
old 15 to 18 are 18 to 21; old 19 to 24 are 24 to 29; new: 3 (xkcd 353), 8 (hand-offs copy or view), 17
(expectation vs reality), 22 (profile), 23 (free-threaded). Sections 1 to 8 below were written before and use the
OLD numbers unless they say otherwise.

| Check (re-run 2026-10-04 after the extension) | Result |
|---|---|
| `deck/qa/checks.py` | 40 pass, 1 warn (`body_words`: 4, 6, 7, 21 as before, plus 25 with the machine line), 2 pending (`pending_placeholders`, `speaker_placeholders`), 0 fail |
| `validate.py` | "All validations PASSED!" |
| `deck/out/build_report.json` | 0 warnings, 0 missing tokens |
| `snippets/run_all.py` | 15 of 15 Python snippets ok and within budget (new: `s06b_handoffs.py`, `s10b_zen.py`; `s03_antigravity.py` was removed 2026-10-11 with the xkcd comic); `s02_pcl.cpp` NOT RUN |
| Timing | 29 main slides, 1800 s in `content.yaml` and `notes.yaml`; `ends_at` recomputed |
| Visual check | every new or changed slide (2, 3, 8, 12, 17, 19, 22, 23, 24, 25, 29) looked at in `deck/out/png/` at full size; fixed: lamp posts overflowing their panel (17), the slide 23 chart's category labels and data labels colliding with four bars (now three bars; the GIL build's numbers are in the support line and conditions), the Drake support line moved under the rows (19) |

New measurements (all new result files, each with `conditions` from `bench/conditions.py`; load average below 1.0
before timing; nothing in `bench_cliff.json`, `memory.json` or `pipeline.json` was re-run or edited):

- `results/python_facts.json` (`bench/python_facts.py --final`): las.xyz is a new F-ordered array per access;
  Vector3dVector copies (float64 F-ordered 13.1 ms, C-ordered 2.9 ms, float32 567 ms: 43× and 196× slower);
  np.asarray(pcd.points) is a writeable view; pv.PolyData shares memory with a C-ordered float64 array and with the
  Open3D view, not with laspy's F-ordered array. 1 warm-up + 7 runs, median.
- `results/profile_scalene.json` (`bench/profile_loop_scalene.py --final`): Scalene's CPU profile of the loop, slide 22
- `results/profile_loop.json` and `.txt` (`bench/profile_loop.py --final`): `python -m cProfile -s tottime loop.py`, the cross-check
  on the slide 19 code: the loop ranks first (0.373 s tottime, 0.413 s cumtime, 66 % of the 0.629 s run), builtins.abs
  is called 722 961 times, the vectorised function 0.004 s. One profiled run.
- `results/bench_freethreaded.json` (`bench/bench_freethreaded.py --final`): CPython 3.14.7 free-threaded
  (sys._is_gil_enabled() False) vs default 3.14.7, numpy 2.5.3, laspy 2.7.0: loop 580 ms; 8 threads 108 ms (5.4×,
  fastest; 16 threads 126 ms); with the GIL 8 threads 599 ms (no gain); one NumPy call 5.0 ms, still 21× faster than
  the best threaded loop. All variants np.array_equal to the vectorised result. Added as slide 23 because the result
  is clear: threads help without the GIL, NumPy still wins by a wide margin.

Verified text: "Flat is better than nested." is line 7 of `python -c "import this"` (`snippets/s10b_zen.py`); NumPy
2.5.3's `np.vectorize` docstring, Notes: "The `vectorize` function is provided primarily for convenience, not for
performance. The implementation is essentially a for loop." (notes slide 24); `import antigravity` calls
`webbrowser.open("https://xkcd.com/353/")` (CPython Lib/antigravity.py; slide removed 2026-10-11). The install
line `uv add open3d "laspy[lazrs]" pyvista` was on slide 2 and resolved in a fresh uv project (uv 0.12.6, `--no-sync`); the line was removed from slide 2 on 2026-10-12.

**xkcd licence (HISTORY: the comic left slide 3 on 2026-10-11, file and snippet deleted):** `deck/assets/xkcd_353_python.png` (518 × 588 px, grayscale) downloaded 2026-10-04 from
https://imgs.xkcd.com/comics/python.png. xkcd.com/license.html: Creative Commons Attribution-NonCommercial 2.5;
"free to copy and reuse any of my drawings (noncommercially) as long as you tell people where they're from", with a
link back, and presentations are named. Use here: personal, non-commercial talk; credit "xkcd.com/353 by Randall
Munroe, CC BY-NC 2.5" in 12 pt under the comic, linked to xkcd.com/353 and the licence; the picture itself links to
xkcd.com/353; alt text on the picture. **Non-commercial use only** (OPEN_ITEMS k1). The comic's pixels are the only
non-palette colours added (grayscale), as allowed.

## 2026-10-12: hidden section "Mental models", C1 to C9

Nine hidden slides after B7 (section "Mental models"): C1 to C6 one idea each with a figure from
`deck/concepts/make_figures.py` (C1, C3, C4 synthetic and labelled so; C2, C5 from the crop; C6 from results), C7
foundational ideas against library spellings, C8 the ranked selection and narrative, C9 the glossary. Not timed: the
main deck still sums to 1800 s; the notes of slides 5, 6, 7, 11, 14, 18 and 24 point to the matching C slide
(`mental_model`). Citations with dates: docs/research/reports/mental_models.md, printed in each C slide's notes.
`literal_numbers` warns on C slides for ids and spec values (EPSG:7415, N×3, versions, 1 GB = 2^30 B, 80 %): reviewed,
not measurements.

**Update, same day:** C1 and C5 were promoted to main slides 6 and 20 (`concept: C1` and `concept: C5` in
`content.yaml`, content still in `appendix.yaml`): 31 main slides, 7 hidden mental-model slides (C2 to C4, C6 to C9),
still 1800 s (80 s taken from slides 5, 18, 21, 22 and 29, docs/TIMING.md). On the main deck the concept bullets are
20 pt (the 16 pt of the hidden C slides failed `min_sizes`). The c5 histogram title now reads "middle 80 % of cells".
The checkpoints and the skip-first list in `notes.yaml` use the new numbers.

**Later the same day:** the former slide 5 (N×3 array and REPL close-up) was removed, C1 became slide 5 and a
benefits-and-limits slide of the three representations (`build: tradeoffs`) became slide 6, 65 s, so slides 7 on keep their
numbers. The C1 figure now uses 1 500 points (700 left gaps in the voxel grid). `renders/closeup.png` is still used by
the laspy frame on slide 9; `snippets/s04_repl.py` no longer appears on a slide.

## State at a glance (re-checked 2026-10-04, after the re-theme)

| Check | Result |
|---|---|
| `deck/qa/checks.py` (re-run) | 40 pass, 1 warn (`body_words`), 2 pending (`pending_placeholders`, `speaker_placeholders`), 0 fail |
| `validate.py --original pycon_nl_2026_master.pptx` (inside the build and checks.py) | "All validations PASSED!" |
| `no_teqyard` package scan | pass: no former company string, font, colour, image, layout name or field in any part, including `docProps` and the parts inside the embedded chart workbooks (`ppt/embeddings/*.xlsx`: Fira Sans only); the one allowed mention is the plain-text affiliation "ML Engineer, Teqyard" in the slide 1 presenter line |
| `deck/out/build_report.json` | 0 warnings, 0 missing tokens, all result files labelled FINAL (research_facts.json: PILOT, by design) |
| `snippets/run_all.py` (2026-10-03, not re-run in the re-theme round) | 12 of 12 Python snippets ok and within budget; `s02_pcl.cpp` NOT RUN |
| Typefaces of all 517 slide text runs | Fira Mono 187, theme body font (Fira Sans) 185, inherited from the master (titles in Fira Sans SemiBold, placeholders) 63, Fira Sans 57, Fira Sans SemiBold 22, Fira Sans Medium 3; `glyph_coverage` pass (every character has a glyph in its Fira file); nothing on a main slide below 20 pt body, 18 pt code or 12 pt small print (`min_sizes`) |
| Speaker timing | 24 slides, 1800 s in `content.yaml` and `notes.yaml`; `ends_at` matches the running total |

The deck is **not ready to present** until the speaker items in OPEN_ITEMS.md section b are filled (21 visible
placeholders: repo URL, QR code, contact, PyCon NL logo, the slide 22 gotchas, the optional book credit).

## 1. Brief self-QA checklist

`[x]` done, `[ ]` not done or only partly done (the reason follows).

- [ ] **1. One idea per slide, the text hierarchy only, about 20 words of body text.** The hierarchy holds on all
  24 main slides and every support line has at most 15 words (`support_words`). `body_words` warns: slide 5 has 46
  words, 6 has 29, 18 has 25, 3 has 21 (diagram labels count). 5, 6 and 18 follow from the brief's per-library lines,
  a conflict inside the brief (OPEN_ITEMS h2).
- [x] **2. Titles are statements or questions, at most 8 words, sentence case.** `title_words` pass on all 28
  titles; the step slides 8 to 13 all follow "N Step: claim" (slide 9 fixed in the final round).
- [x] **3. One term per concept, en-GB.** point cloud, voxel downsampling, ground removal, clustering, labelling,
  visualisation, street furniture (`content.yaml` `meta.terms`). "tile" means only the processing squares; a download
  is an "AHN file" (re-read on all slide text and notes in this round). No US spellings found.
- [x] **4. Layouts, colours and fonts from the chosen template.** Every slide is a duplicated example slide of
  `deck/template/pycon_nl_2026_master.pptx` (11 layouts, 9 used; `master`). Slide text uses Fira Sans and Fira Mono
  only (`fonts`, `glyph_coverage`, `pdf_fonts`). Colours: `content.yaml` `meta.palette` plus the render label
  colours on the chip swatches (`colours`). Logos: item 20.
- [x] **5. No invented numbers.** No missing tokens, `unresolved_tokens` and `literal_numbers` pass; the trace audit
  recomputed every on-screen number, chart cache and embedded workbook from the result files. The slide 20 title and
  reference bars are tokens (`memory.ram_reference_gb`). B2 and B3 research numbers come from
  `results/research_facts.json` (PILOT) and are marked pilot or synthetic on the slide.
- [x] **6. Benchmark conditions in small print; "two orders of magnitude" only if measured.** Conditions lines on 17,
  18, 20, 21, B1, B2 and B4: CPU, cores and threads, RAM, OS and kernel, Python and library versions, N, runs and
  warm-up, statistic, threads of the plane runs (1, CPU/wall 1.0), governor, boost, date and data; B3 says single
  runs. The phrase is on no slide: slide 17 asks "How much slower is the loop over rows?" and the on-click hero answers with the measured 126× (`bench.plane.factor.median`); the
  notes allow saying it aloud for this loop only (`iqr_low` 124 ≥ 100). Two small gaps remain: the per-call timeit
  runs (slide 18, B4) record no thread count, and the `distance_upper_bound` value is not printed (it exists only
  inside a description string in `bench_cliff.json`).
- [x] **7. Code: monospace ≥ 18 pt, ≤ 12 lines, highlighted, key line marked, run or NOT RUN.** Section 3. Smallest
  code size 18 pt; `code_boxes` pass (wrap off, no autofit); every Python box has exactly one key line.
- [x] **8. Library descriptions accurate and neutral.** No "best" or "fastest"; every "not for this pipeline" item is
  backed in the notes; the B4 octree row now says "in memory" (out-of-core octrees are what COPC stores).
- [x] **9. Native, editable charts with embedded data, direct labels, one highlighted series, log scale labelled.**
  Slide 17: column chart, log10 axis, "Median time per run, log scale". Slide 20: horizontal bars, reference bars
  navy, computed bars grey, ours blue, and a dashed navy line that continues the 32 GB bar across the computed bars. No legend, gridlines or 3D; workbooks equal the JSON. PowerPoint rendering of
  the log axis is UNVERIFIED (section 4).
- [x] **10. Same street, camera and colour mapping on every running-example render.** One camera for all 9 renders,
  `camera_unchanged` true for each, fixed height limits (`renders/render_spec.json`). The camera is not the reviewed
  storyboard pose; the reason is recorded in `render_spec.json` `camera.change_from_reviewed` (OPEN_ITEMS d8).
- [x] **11. Morph on 8 to 14, fade elsewhere, no autoplay, on-click builds only where specified.** `transitions`, `animations`,
  `hero_build`, `tile_build`, `morph_geometry`, `morph_unique_names` pass; only the slide 21 hero (slide 23 before 2026-10-14) and
  the four rule tiles of slide 29, one per click, build. Playback is UNVERIFIED.
- [ ] **12. Notes on every main slide: talk track, time with question and answer, traceability.** Present on all 24
  slides, seconds sum to 1800. Not done: slide 22's talk track and answer are `[SPEAKER: ...]` placeholders.
- [x] **13. Skip-first list of 3 to 4 slides.** 15, 20, 19, 13 (saves 230 s), in the slide 14 checkpoint, in each
  skip slide's "IF SKIPPED" note and in TIMING.md.
- [x] **14. Alt text on every graphic and chart.** `alt_text` pass; only key-line bars and arrows are decorative.
- [ ] **15. Minimum sizes: 20 pt body, 18 pt code, 12 pt source lines.** Main slides pass on effective (inherited)
  sizes; the slide 23 references are 20 pt now. Not met: the hidden appendix uses 15 pt (B1) and 14 pt (B2 to B4)
  body text and 16 pt table captions (follows the brief's "plain and dense", OPEN_ITEMS h1). Two 12 pt hints on slides 22 and 24 are placeholders.
- [x] **16. Gotchas supplied, or marked placeholders listed under Open items.** Marked placeholders on slide 22; the
  16 candidates from testing are in the slide 22 notes and OPEN_ITEMS c, each labelled CANDIDATE.
- [x] **17. Dataset named in a source line; no identifiable people or readable licence plates.** Section 6.
- [ ] **18. Main part presentable in about 30 minutes; sections that run over flagged.** 1800 s planned; section 6
  runs 75 s over the brief on purpose, sections 1 and 2 are 15 s and 60 s under (TIMING.md). Not yet rehearsable:
  slide 22's 130 s have no talk track.
- [x] **19. No information by colour alone; classes readable in greyscale.** Direct label chips on 3 and 10 to 14
  (the Ground chip was added on 10 and 11 in the final round). Class colours differ by at least 43 grey levels against
  a threshold of 40 (`render_spec.json` `checks.grayscale_f6_final`, `grayscale_f5_labels`).
- [ ] **20. Logos on the title and closing slides only.** Logo zones exist on 1 and 24 only, and no other logo is in
  the deck; the PyCon NL logo itself is a labelled placeholder (file and the organisers' permission missing,
  OPEN_ITEMS d4).
- [x] **21. Footer "3D Data Science with Python | PyCon NL 2026" and slide number on every content slide.** From the
  master's footer and slide number placeholders on every content layout (`footer`); none on 1 and 24.
- [x] **22. Pre-rendered visuals only, no live demo, no autoplay.** The package holds 10 PNG (renders, icons) and no
  audio or video.
- [x] **23. A missing render becomes a labelled placeholder.** Nothing missing: every render picture is in place
  (`morph_renders_present`, build_report `renders`).
- [x] **24. Result files that disagree with the brief are used, and the differences listed.** Section 5.
- [x] **25. Uncertain API or version behaviour flagged instead of guessed.** Section 4, the B-slide status keys
  (verified, token, pilot, synthetic, judgement, not_tested, not_run) and the UNVERIFIED marks in the notes.

## 2. PyCon NL 2026 style checklist (docs/DESIGN.md section 6)

- [x] Outline presented and approved before building: `storyboard.md`, approved 2026-10-02, with a dated note on
  the re-theme (2026-10-03).
- [x] Personal talk: no company master, sidebar, wordmark, logo, claim, confidentiality field, company colour or
  company font anywhere in the package (`no_teqyard`, also inside the chart workbooks and `docProps`). The
  affiliation "ML Engineer, Teqyard" is plain text on slide 1 only.
- [x] Palette only: navy, blue, sage, white, grey, slate, ink, light from `content.yaml` `meta.palette`; the render
  palette only inside renders and on the chip swatches (`colours`); no colour literal in the builder code
  (`code_colour_literals`).
- [x] One highlight per slide: blue on white, sage on navy, never blue on navy. Slide 18: arrows slate, only the toll
  ticks and the hero blue; slide 23: no accent rule per tile (the slide's accent bar is the only decoration); slide 6:
  chain arrows navy, blue only on the "Worth it" check and bullets. Licence links on navy use the text colour, and the
  dark layouts map hyperlinks to sage for PowerPoint versions that ignore the run-level colour.
- [x] Fonts: Fira Sans (titles SemiBold, inherited from the master) and Fira Mono for code; every character has a
  glyph in its Fira file (`glyph_coverage`; thousands separator U+00A0, since Fira Sans has no U+202F).
- [x] Sizes: titles 32 pt (48 to 60 pt on the dark layouts), body 20 to 24 pt, code 18 pt or more, small print and
  source lines 12 pt or more (`min_sizes`, `label_sizes`); heroes 60 to 96 pt (slide 21 back at 60 pt).
- [x] No master placeholder text left: `no_master_strings`, `no_empty_placeholders` pass. (The speaker placeholders
  in OPEN_ITEMS b are talk content, not master text.)
- [x] Geometry from the master: 0.600 in margin, titles on the same position per layout (slide 4 now uses layout 7,
  so the title stays on the left margin from 3 to 5), content above 6.800 in, footer and slide number on every
  content slide (`footer`). Conditions and small print boxes are bottom-anchored with one spare line upwards, so a
  different line break in PowerPoint grows into free space, not onto the footer.
- [x] No two dark slides adjacent: dark slides are 1, 19 and 24 (`dark_not_adjacent`).
- [x] Label chips (3, 10 to 15): no chip or leader collisions (`label_chips`; slide 3 uses a 0.06 in frame margin to
  fit four chips in its 3.7 in frame).
- [x] No text overflows its box or the slide: all 28 renders inspected at full resolution after the final build.
  With PowerPoint and the Fira fonts on the presenting laptop: UNVERIFIED (OPEN_ITEMS e).
- [x] No dashes: `no_dashes` and `notes_no_dashes` pass. en-GB on every run (`lang_en_gb`, chart text included).
- [x] Icons: the deck uses none (the Lucide `check` and `x` icons left with the slides that drew them).
- [x] `validate.py ... --original pycon_nl_2026_master.pptx` without new errors: passed.
- [x] File name `20261015_PyCon-NL_3D-Data-Science.pptx`, delivered as .pptx plus PDF. The PDF in `deck/out/` is a
  LibreOffice export; the final PDF should be exported from PowerPoint (OPEN_ITEMS e).

## 3. Snippets

Re-run with `uv run python snippets/run_all.py` on 2026-10-03, CPython 3.13.15. Each snippet runs in a fresh temporary
directory and checks its slide lines against `pipeline/steps.py` and the result files.

| Snippet | Slide | Status | Lines / widest (budget 12 / 35, s21: 70) | What the run checks |
|---|---|---|---|---|
| `s02_python.py` | 2, right | RAN OK | 2 / 35 | reads 722 961 points from a .pcd; 232 180 voxels, as `pipeline.points_after_voxel` |
| `s02_pcl.cpp` | 2, left (greyed) | **NOT RUN** | 11 / 35 | no PCL toolchain (pkg-config finds no `pcl_common`); never compiled; the grid-anchoring remark in its header is UNVERIFIED |
| `s04_repl.py` (slide shows `s04_repl.txt`) | 4 | RAN OK | 6 / 35 | the real REPL transcript; shape (722961, 3), `las.classification[:5]` |
| `s08_load.py` | 8 | RAN OK | 6 / 35 | same points as `steps.load` + `to_open3d`; float64; local origin |
| `s09_voxel.py` | 9 | RAN OK | 3 / 33 | same voxels as `steps.downsample` |
| `s10_ground.py` | 10 | RAN OK | 10 / 34 | same parameters as `pipeline.json`, same mask as `labels_crop.npz` |
| `s11_cluster.py` | 11 | RAN OK | 8 / 32 | same cluster ids as `steps.cluster` and `labels_crop.npz`; 1 922 clusters |
| `s12_label.py` | 12 | RAN OK | 10 / 35 | rules identical to `steps.name`; 1 street furniture object |
| `s13_render.py` | 13 | RAN OK | 8 / 34 | same classes as `steps.paint_back`; camera from `render_spec.json`; its PNG goes to a temporary directory |
| `s14_pipeline.py` | 14 | RAN OK | 9 / 35 | the same class for all 722 961 points as `labels_crop.npz` |
| `s16_loop.py` | 16, left | RAN OK | 5 / 35 | `np.array_equal` with the expression; `bench_cliff.py` times these lines verbatim |
| `s16_vec.py` | 16, right | RAN OK | 3 / 33 | as above |
| `s21_chunked.py` | 21 | RAN OK | 12 / 70 | on the crop the result equals a load-everything first-point reference; `bench_memory.py` measured these lines on the 1 km file (`chunked_equals_reference` true) |

Code-like text on slides that is not a snippet and was not run as shown: the slide 1 joke (the abstract's line), the
slide 18 diagram chips `for p in pts: f(p)` and `f(pts)`, the struck-through `for p in points:` on slide 19, the slide
22 table tokens (placeholders), and the API calls quoted on B2 to B4 (sources in the B-slide notes; the COPC call on B2
ran once in research, `docs/research/dataset/copc_remote.py`).

## 4. UNVERIFIED

**Only checkable in PowerPoint or on the presenting machine** (everything here was rendered with LibreOffice):

- **Morph:** playback on 8 to 14; whether the first filmstrip thumbnail on slide 7 morphs into slide 8's frame;
  whether the Ground chip stays still from 10 to 14; Morph when slide 13 is skipped or when jumping by slide number.
  The XML is `p159:morph` (byObject) with a fade fallback.
- **Log axis (slide 17):** logBase 10, automatic axis crossing, data-label positions, the conditional ms formats.
- **Fonts:** the QA renders use the real Fira Sans and Fira Mono files (`deck/qa/fonts/`), but PowerPoint's line
  breaking and line pitch can differ from LibreOffice's. Fira Sans and Fira Mono must be installed on the presenting
  laptop or embedded in the file (OPEN_ITEMS d6); without them PowerPoint substitutes a font.
- **The cup glyph** is no longer on slide 1 (Fira Mono has no glyph for it); nothing to check unless it is put back.
- **Licence links:** in the text colour via `hlinkClr val="tx"` (Office 2019 and later); older versions fall back to
  the layout's hyperlink mapping (sage on the navy layouts, blue on white).
- **Screen readers** on the alt text of grouped diagrams (for example slides 5, 18 and 23).
- **Final PDF:** the PDF in `deck/out/` comes from LibreOffice with substitute fonts.

**Code and APIs:**

- `s02_pcl.cpp` (never compiled; the PCL `VoxelGrid` anchoring remark in its header).
- PyTorch3D CUDA build; the Open3D wheel without a GPU or driver; Open3D's PyTorch ops; a GPU run of this pipeline
  (B3: CUDA build UNVERIFIED, the rest NOT TESTED). The B3 Open3D CUDA and CPU timings are single synthetic runs.
- Numba, Cython, a hand-written C++ extension: NOT TESTED (B1). Octree timings: not benchmarked (B4).
- The B2 COPC remote read: one pilot run, on the AHN4 edition of the 1 km file, not on the AHN5 crop.
- Boost off was not tested (the conditions say boost on). Headless PyVista through EGL: research only (notes 13).
- KDTreeFlann's cheaper per-call cost (B4 notes): synthetic pilot only.

**Data and claims:**

- **Leaf-off:** the AHN5 acquisition spec was not checked; the AHN4 spec asks for a leaf-off flight, and the crop was
  flown in the night of 5 to 6 April 2023, about 01:35 CEST (GPS time). Slide 12 and its notes say exactly that.
- **The street furniture object:** what the 9-point object is on the ground (no imagery checked). Notes 12: do not
  call it a lamp post. What the 26 small groups dropped by DBSCAN are (`pipeline.street_furniture_missed_candidates`).
- **Venue:** which Jaarbeurs hall the talk room is in (OPEN_ITEMS d7). The location claim itself is checked (section 6).
- The largest mislabelled cluster as a sunken lane or ramp, and the facade stripes as balconies or floor edges, are
  readings from a top view only (section 7).
- The overlap cost of spatial tiling (B2) was not measured.

## 5. Brief and storyboard against the result files

The deck uses the result files. These are the places where they differ from the brief or the approved storyboard.

| Brief or storyboard | Result files and the deck | Keys or evidence |
|---|---|---|
| Abstract and slide 1: `# 12 million times. see you tomorrow ☕` | the joke stays, without the cup (no glyph in Fira Mono) and with `...` before the comment so the loop is valid Python; the crop has 722 961 points and the 1 km AHN file 21 013 926; no 12 million point loop was timed, and the slide 1 answer says so | `pipeline.points_in`, `memory.tile_1km.points` |
| "a single Python-level loop over your points can cost two orders of magnitude" | supported for the slide 16 loop over NumPy rows on laspy's column-ordered array: 126× (IQR bounds 124× to 128×). On a row-ordered copy it is 81× (78× to 81×): the expression slows from 4.3 ms to 6.8 ms while the loop barely changes. A loop over plain Python floats is 32× (plus 188 ms for `P.tolist()`); the kNN loop is 6.6× against one call on one thread and 62× against all 16 threads. So the title gives the measured 126×, the bar reads "Loop over NumPy rows", the support line no longer says "only the number of calls changes", and the phrase is spoken only | `bench.plane.factor`, `plane.sensitivity.factor_c_contiguous`, `plane.sensitivity.vectorised_c_contiguous`, `plane.factor_python_floats`, `plane.sensitivity.tolist`, `knn.factor_loop_vs_1t`, `knn.factor_loop_vs_all` |
| Labelled objects include "street furniture" | 1 object of 9 points (8 voxels), 3.25 to 4.53 m above the ground; 26 small groups (48 voxels) fall below `min_points` and become noise; drawn enlarged at 24 px, and slides 12 to 14 say "1 object, 9 points, drawn enlarged" | `pipeline.n_objects.street_furniture`, `label_points.street_furniture`, `street_furniture_missed_candidates`, `render_spec.json point_size_px` |
| Slide 4: attributes "intensity, colour, classification" | AHN5 point format 6 has no RGB; the slide says "intensity, returns, class" and the notes say there is no colour column | `pipeline.crop.point_format`; research: review/honesty/inspect_crop.out |
| "a raw LiDAR scan of a street" | AHN arrives classified. The pipeline hides AHN's classes and uses them only to score ground (class 2: 99 % precision, 94 % recall) and buildings (class 6: 81 %, 97 %); vegetation and street furniture have no answer key (class 1 mixes them) | `pipeline.ground`, `pipeline.buildings`, `pipeline.label_vs_ahn` |
| Storyboard v1 slide 3: "This is the street outside this building" | replaced by "This street is right next to Jaarbeurs": the BAG outline of the Jaarbeurs main halls lies 27 m south of the crop, the Jaarbeursplein 6 address point 254 m away | research: review/honesty/location_check.out; `render_spec.json labels.detail.f1_load.jaarbeurs_edge_note` |
| Storyboard slide 3: arrow "Jaarbeurs halls [27 m]", one wide split render | no distance on screen (it is not in `results/*.json`); the arrow reads "To the Jaarbeurs halls"; two portrait frames side by side instead of `hook_split.png` (kept, unused) | `content.yaml` slide 3 |
| Slide 9: [232 180] at [0.5 m] | 232 180 at 0.5 m, 32.1 % kept | `pipeline.points_after_voxel`, `kept_share`, `params.voxel` |
| Slide 10: [50 m] tiles, [P] % / [R] % | 25 m tiles (64 of them); 99 % precision, 94 % recall | `pipeline.params.tile`, `n_tiles`, `ground` |
| Slide 11: `eps=[1.0], min_points=[10]`, [N] clusters | eps 0.75 m, min_points 6, 1 922 clusters, 13 % noise | `pipeline.params.eps`, `min_points`, `n_clusters`, `noise_share` |
| Slide 17: [X ms], [Y ms], hero [X]× | 543 ms, 4.3 ms, 126× | `bench.plane.loop_numpy_rows.median_ms`, `vectorised.median_ms`, `factor.median` |
| Slide 18: hero [450 ns] per crossing; "one KD-tree query per point costs [3 µs]" | 438 ns per loop step, labelled "several NumPy calls" (one NumPy call per step, on Python floats, costs 111 ns); 10.1 µs for an empty k = 16 query, the call the loop makes; the cheapest empty call, a radius query, costs 3.3 µs | `bench.plane.per_step_ns_loop`, `per_step_ns_python_floats`, `knn.per_query_us_far_knn`, `knn.per_query_us_far` |
| Slide 20: [80] bytes per point; title "A full-size AHN file outgrows 32 GB" | 86 B per point, kept after `gc.collect()` and `malloc_trim(0)` (148 B untrimmed, 154 B at peak); title narrowed to "Loading this street's AHN file outgrows 32 GB" (one urban file with 926 203 338 points; its LAS records alone, 25.9 GB, stay under 32 GB, every loaded state goes over); totals computed, not run | `memory.tile_1km.bytes_per_point.pipeline_retained`, `bytes_per_point_untrimmed`, `bytes_per_point_peak`, `big_file` |
| Slide 21: peak [3.3 GB] → [1.0 GB]; support "Memory now follows the output, not the input" | 3.0 GB → 0.8 GB, increases over the process after imports (259 MiB), 1 GB = 2^30 bytes; the support line is spoken instead, to give the hero room | `memory.tile_1km.naive_peak_mb`, `chunked_peak_mb`, `baseline_mb_after_imports` |
| Render spec: 6 px after voxel downsampling, camera (-60, -110, 141) | 3 px on every frame, so the voxel gaps show; street furniture its own 24 px actor; camera (123, -106, 398), looking north from above the halls | `render_spec.json point_size_px`, `camera`, `camera.change_from_reviewed` |
| Storyboard slide 9 title "2 Voxel downsampling averages every voxel" | "2 Voxel downsampling: one average per voxel" (step-title pattern) | `content.yaml` |
| Brief: "Machine Learning Engineer at Teqyard" | slide 1 writes "ML Engineer, Teqyard" as plain text (personal talk, no company branding) | `content.yaml` slide 1 |
| Brief: logos on title and closing slides only | logo zones on 1 and 24 only; the PyCon NL logo is not supplied (OPEN_ITEMS d4) | |
| Brief: slot 10:45 to 11:25, "[Confirm with organizers whether the 40 min includes Q&A.]" | not confirmed; the deck is planned for 30 minutes | OPEN_ITEMS d1 |

The research pilots measured smaller plane factors (row-ordered arrays, a loaded machine); the deck uses only the
FINAL runs of 2026-10-02 (`docs/research/reports/` keeps the history).

## 6. Dataset licence and privacy

**Dataset:** AHN5, Actueel Hoogtebestand Nederland, licensor Het Waterschapshuis, CC BY 4.0. AHN file
`AHN5_C_135000_455000.COPC.LAZ` (130 213 150 B, SHA-256 `b326b5a6…c327`), cropped to RD New x 135715 to 135915,
y 455475 to 455675: `data/utrecht_jaarbeurs_200m.laz`, 722 961 points, SHA-256 `b8dfa077…`
(`data/README.md`, `results/pipeline.json` `crop.sha256`).

**Licence evidence** (`data/DATA_LICENSE.md`, checked 2026-10-01 and 2026-10-02): the AHN download page ("AHN5/6,
Creative Commons Naamsvermelding 4.0"), the Nationaal Georegister record `4995e338-fec7-425e-bb86-eea3875cf114`
("Naamsvermelding verplicht, organisatienaam") and ahn.nl (source must be named on derived products).

**How the deck complies:**

- Attribution: the source line "Point cloud: AHN5, Actueel Hoogtebestand Nederland (ahn.nl), Het Waterschapshuis,
  CC BY 4.0. AHN file 135000_455000, cropped and processed." on every slide that shows a render (3, 4, 7, 8 to 15) and
  on slide 24; the conditions lines on 17, 18, 20, 21, B1, B2, B4 and the slide 16 small print name the data and the
  licence.
- Licence link (CC BY 4.0 section 3(a)(1)(C)): every "CC BY 4.0" in slide text links to
  https://creativecommons.org/licenses/by/4.0/, and slide 24 prints "Licence: creativecommons.org/licenses/by/4.0".
  `licence_links` and `source_lines` pass; the PDF carries the links.
- Changes: "cropped and processed" on the slides; the three changes are listed in `data/DATA_LICENSE.md`, which also
  says the talk is not endorsed by Het Waterschapshuis or AHN.

**Privacy check:** nothing identifiable, nothing to flag.

- No colour: LAS 1.4 point format 6, 18 dimensions, no RGB (research: review/honesty/inspect_crop.out).
- Density: about 18 points per m² on the crop, all returns (722 961 points on 40 000 m², inspect_crop.out); 18.2
  first-return points per m² on the 1 km file (research: reports/dataset.md). From the air a person is a handful of
  points and licence plates cannot be resolved (dataset.md).
- Night flight: the GPS times decode to 5 April 2023, 23:35 to 23:52 GPS time, about 01:35 local time on 6 April
  (dataset.md), so few people or moving cars.
- People and cars sit in AHN class 1 by spec; the pipeline leaves cars unlabelled.
- The close-up render (slide 4) shows the roof junction of a building (renders build report); at this density
  nothing in it can identify a person.

**Other third-party material:** Fira Sans and Fira Mono (SIL OFL 1.1) are the deck fonts; the QA copies live in `deck/qa/fonts/`, git-ignored. The BAG and PDOK
lookups for the venue check appear only in a research file, not on a slide. The talk title is shared with Florent
Poux's O'Reilly book (2025); the optional credit on slide 24 is the speaker's decision (OPEN_ITEMS d5).

## 7. Known render and label errors

From `results/pipeline.json` (`known_errors`, `label_vs_ahn`, `buildings.note`), `renders/render_spec.json`
(`observations`, `checks`) and the renders build report:

- **A 117 m strip called vegetation:** cluster 156, 14 971 points, at most 3.76 m high, beside the curved building.
  Its multiple-return share (0.42) is just over rule 1's 0.4. In a top view it looks like a sunken lane or ramp
  (UNVERIFIED). It shows as a sage arc around the plaza. Six more clusters of 500 or more points are called vegetation
  although at least 25 % of their points are AHN ground or building.
- **Facade stripes called vegetation:** 347 flat clusters (10 655 points) within 2 m of buildings, more than 5 m up;
  horizontal stripes, most visible on the 38 m tower at the crop's south edge (balconies or floor edges, UNVERIFIED).
- **Building precision is a lower bound:** AHN puts many facade points in class 1, so facades we call buildings count
  as errors (81 % precision against class 6).
- **Points per predicted class against AHN:** vegetation holds 10 118 AHN ground and 3 953 AHN building points;
  unlabelled holds 34 541 AHN ground points; ground holds 9 693 class 1 points.
- **Street furniture:** one object of 9 points, drawn enlarged at 24 px (at 3 px it is a speck); the small print says
  so. 26 candidate groups were dropped as noise. Cars stay unlabelled (they fail "twice as tall as wide").
- **Objects are clusters:** one tree can be several vegetation clusters; the 26 buildings are roof clusters, with
  facade fragments counted separately (`n_objects_note`).
- **Greyscale:** the smallest gap between class colours is ground against the navy background (43 levels, threshold
  40); unlabelled sits 17 levels from ground on purpose, so it recedes. On slide 10 the ground grey is close to parts
  of the height ramp in greyscale; the Ground chip on 10 and 11 carries that information.
- **Chips on slide 12** use the f6 anchors on the f5 frame so they stay still through the Morph; every anchor lands
  on a pixel of its class on f5 too (`anchors_on_class_f5_labels`).
- **Framing:** the top of each portrait frame is empty navy, and a sliver of the building at the crop's south-east
  corner is clipped at the bottom right (renders build report). The voxel frames (f2 to f5) show grid gaps, most in
  the rows nearest the camera; that is intended (`render_spec.json` `point_size_px.voxels_reason`).
- **Plane sheet (slide 15):** the ticks for the street furniture object and a car are recorded but not drawn (too
  short to read); the sheets are the 64 tile planes, while the benchmark uses one plane for the whole crop (notes 15).

## 8. Findings of this round for the deck owner (not fixed here)

1. **Slide 20 "all arrays kept" leaves one array out.** The measured case (`bench/bench_memory.py`, case `pipeline`)
   builds `PointCloud(Vector3dVector(xyz))`, so the temporary vector is freed. The slide 8 code names it
   (`v = o3d.utility.Vector3dVector(xyz)`), which keeps it alive: Open3D then holds 48 instead of 24 B per point
   (`memory.tile_1km.open3d_points_v_alive_retained` against `bytes_per_point.open3d_points`). The 86 B holds for the
   slide 14 helpers (`pipeline/steps.py` `to_open3d`), not for the slide 8 lines typed as shown. The title only gets
   safer, but the small print overstates what was kept. Options: say "as in the slide 14 helpers" in the small print,
   or change the slide 8 lines so the vector is not kept (within the 35-character width budget) and re-run the
   snippets.
2. **`data/README.md` states "Flown at night, leaf-off"** as a fact; the deck now says the AHN4 spec asks for leaf-off
   and the AHN5 spec was not checked. Align the README.
3. **Candidate gotcha 4's suggested consequence** "Copy hundreds of times slower" reads stronger than its evidence
   ("roughly two orders of magnitude", single runs). Word it from the evidence if the speaker picks it (OPEN_ITEMS c).
4. **No builder key for a real logo file:** removing `logo_placeholder` removes the box, but nothing inserts a logo
   (HOW_TO_UPDATE.md). The PyCon NL logo also needs the organisers' permission and a version that shows on navy.
5. **Skip-first number 4 (slide 13) comes before the slide 14 checkpoint,** so no checkpoint covers it (TIMING.md).
6. Already known and recorded: the per-call timeit thread count is not in `bench_cliff.json`; the
   `distance_upper_bound` value is not printed; slides 6, 7 and 23 centre their blocks vertically.

## How this was checked

```bash
uv run python deck/build_deck.py       # deck/out/*.pptx, build_report.json (validate.py runs inside)
uv run python deck/qa/render.py        # deck/out/png/slide-NN.png, the QA PDF
uv run python deck/qa/checks.py        # deck/out/qa_checks.json
```

Re-theme round (2026-10-04): the 37 inspection findings on the first PyCon NL build were applied (OPEN_ITEMS j),
then all 28 renders were inspected at full resolution. Benchmarks, the pipeline and the snippets were not re-run.

Plus, in the session scratchpad only: the checklist audit's effective-font script re-run on the final deck, a dump of
all slide text and rendered notes, measurements of title and content positions, the timing table, and a look at the
contact sheet and slide 22 of the final QA render. The audits of the previous phase (trace and checklist) and the
final fix report are summarised above where their results still hold.
