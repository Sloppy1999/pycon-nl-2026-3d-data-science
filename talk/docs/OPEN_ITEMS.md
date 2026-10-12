# Open items

Deck: `deck/out/20261015_PyCon-NL_3D-Data-Science.pptx` (PyCon NL 2026, 15 October). This file lists what the speaker
or the client still has to supply, decide or check before the talk. Nothing here may be filled in by guessing.
QA results, snippets, UNVERIFIED items and the differences from the brief are in [QA_NOTES.md](QA_NOTES.md); the clock
is in [TIMING.md](TIMING.md); how to apply a change is in [HOW_TO_UPDATE.md](HOW_TO_UPDATE.md).

`deck/qa/checks.py` lists every visible speaker placeholder as `speaker_placeholders` (pending, 21 items on
2026-10-03); it passes once section b is done.

## a. Skip-first list and checkpoints

- Skip-first order (2026-10-04, 29 main slides): **23, 18, 25, 22, 24, 15, 8**, saving 345 s
  (50 + 25 + 60 + 55 + 55 + 40 + 60 s). The free-threaded slide goes first. The slide 16 CHECKPOINT note opens with
  it; each skip slide's notes say what to say instead.
- Checkpoints (presenter view only): leave slide 16 by 15:20. After 16:35 skip 23 and 18 (75 s); after 18:05 also
  skip 25 and 22 (190 s in all) and tell only one story on 27. Reach slide 25 by 23:35, otherwise skip it.
- Slides 15 and 8 come before the slide 16 checkpoint: skip them only if already late at the end of slide 14 (15)
  or slide 7 (8, planned 6:30).
- Full table, wall-clock times and caveats: TIMING.md.

## b. Speaker placeholders (fill in before delivery)

| Slide | Key | Placeholder | What to put there |
|---|---|---|---|
| 1 | `content.yaml` slide 1 `presenter` | `[repo URL]` | the repository's short URL (a long URL moves to its own line) |
| 27 | slide 27 `title` | `[N]` | the number of gotchas, 4 to 6 |
| 27 | slide 27 `table.rows` | five rows `[GOTCHA n: code token]` / `[consequence, ≤ 4 words]` | the speaker's gotchas (section c) |
| 27 | slide 27 `placeholder_note` | grey "Speaker supplies 4 to 6 gotchas ..." | delete the key once the rows are real |
| 27 | `notes.yaml` slide 27 `talk_track` | `[N]`, `[SPEAKER: the one full story ...]`, `[SPEAKER: one sentence for each remaining gotcha ...]` | the stories, in the speaker's words |
| 27 | `notes.yaml` slide 27 `answer` | `[SPEAKER: say yes only if the repo really has the list ...]` | yes only if the repo has a written list (d11) |
| 29 | slide 29 `support` | `[repo URL]` | the readable link next to the QR code |
| 29 | slide 29 `contact` | `[email]`, `[GitHub / LinkedIn handle]` | contact details the speaker wants public |
| 29 | slide 29 `qr.url` | `null` (the tile says "Set qr.url in content.yaml") | the repo URL; the builder makes the QR code |
| 29 | slide 29 `small_print[1]` | `[Optional: Title shared with F. Poux, ...]` | keep it without the brackets, or delete it (d5) |

Set the repo URL and QR code only after the clean-up in section f.

## c. Gotchas for slide 27

The brief asks for 4 to 6 gotchas "supplied by the speaker". None is invented in the deck. Testing turned up these
candidates; they live in `notes.yaml` slide 27 `candidate_gotchas` with their evidence, each marked "CANDIDATE, speaker
to confirm". Pick, reword or replace them; then fill section b.

| # | Code token | Suggested consequence | What it is (evidence kind) |
|---|---|---|---|
| 1 | `probability=1.0` | Seeded runs still differ | a seeded `segment_plane` repeats only with `probability=1.0` (measured: `pipeline.checks.ransac_default_probability`) |
| 2 | `o3d.io.read_point_cloud("x.laz")` | Empty cloud, no error | Open3D returns 0 points and a warning for LAS/LAZ (verified; already the slide 7 joke) |
| 3 | `xyz - header.mins` | Silent centimetre steps | float32 at RD coordinates steps 1.6 cm in x, 3.1 cm in y (arithmetic, `research_facts.json float32_step_m`) |
| 4 | `Vector3dVector(float32)` | Copy hundreds of times slower | float32 input takes a slow path, roughly two orders of magnitude slower (single runs). The suggested wording reads stronger than this evidence |
| 5 | `classification == 1` | Class 1 is not trees | AHN class 1 also holds facades, cars, poles (AHN4 spec, crop analysis) |
| 6 | `cluster_dbscan(eps=...)` | Everything becomes noise | eps must clearly exceed the voxel size (prototype runs) |
| 7 | `voxel_down_sample` | Returns and classes lost | averaged new points, LAS attributes dropped (verified) |
| 8 | `np.unique(axis=0)` | Vectorised, still slow | no faster than a dict loop on voxel rows (1 M points and synthetic) |
| 9 | `np.isin + np.union1d` | Merge step crawls | merging chunk keys this way was several times slower than one `np.unique` (synthetic) |
| 10 | `segment_plane per tile` | Roofs become ground | without a low-height pre-filter some tiles fit a roof (prototype; `pipeline.param_choice`) |
| 11 | `pts @ n + d` | Layout changes the bits | bit-identical on laspy's column-ordered array, tiny differences on a row-ordered copy (final run and pilot) |
| 12 | `LasData(copc_header)` | Crop write fails | "Writing COPC is not supported" (verified while cutting the crop) |
| 13 | `las.xyz` | Hidden copies everywhere | a fresh F-ordered float64 copy on every access; chunks have no `.xyz` (verified) |
| 14 | `PointCloud.from_legacy` | float32 sneaks in | converts to float32 by default (verified; also in notes 8) |
| 15 | `pip install laspy` | LAZ will not open | without lazrs or laszip laspy cannot read LAZ (verified) |
| 16 | `fixed_radius_search` | Wrong array unpacked | returns (indices, distances, splits), its docstring lists another order (verified) |

Rehearse slide 27 once the stories exist: it has 120 s, the longest slot in the deck.

## d. Decisions for the speaker

1. **Slot:** confirm with the organisers whether the 10:45 to 11:25 slot (40 minutes) includes Q&A and changeover
   (the brief's open question). The deck is planned for 30 minutes of talk and about 7 of Q&A.
2. **Repo URL and QR code:** which repository, and its URL (b). Only after f.
3. **Contact details** for slide 29 (b).
4. **PyCon NL logo:** done (2026-10-04). The speaker supplied `deck/assets/pycon_nl_2026_logo.png`; it sits on a white
   tile on slides 1 and 29 (`content.yaml` `logo`). Only confirm with the organisers that speakers may use it.
5. **Book-title credit:** the title is shared with Florent Poux's O'Reilly book (2025). Keep the optional small print
   on slide 29 (drop the brackets) or delete it and say the credit aloud (notes 29).
6. **Fonts on the presenting laptop:** the deck uses Fira Sans (Regular, Medium, SemiBold, Bold) and Fira Mono (Regular,
   Medium, Bold) only. Either install them on the presenting laptop (Google Fonts, SIL OFL 1.1), or embed them before
   the deck travels: PowerPoint, File > Options > Save > "Embed fonts in the file" (all characters). Without them
   PowerPoint substitutes another font and line breaks, title line counts and code widths change.
7. **Venue phrase:** confirm the talk room is in the Jaarbeurs main halls; otherwise drop "the venue we're sitting in
   right now" from the slide 4 talk track (notes 3, CHECK BEFORE THE TALK).
8. **Render camera:** the renders use a camera above the halls looking north, not the reviewed storyboard pose
   (`renders/render_spec.json` `camera.change_from_reviewed`: the street, the vegetation and the street furniture
   object fit the frame; the street looks smaller and more map-like). Confirm, if not already done.
9. **"Two orders of magnitude":** the notes allow saying it aloud, for the loop over NumPy rows on laspy's array only
   (126×, lower IQR bound 124×); on a row-ordered copy it is 81×. It is not on any slide.
10. **Benchmarks on the presenting laptop (optional):** the numbers come from the speaker's desktop (Ryzen 7 5700X,
    2026-10-02). Re-running on the laptop changes every benchmark number, the charts and the conditions line (all
    filled from the result files on the next build); the notes' "two orders of magnitude" check is evaluated again
    (it needs the lower IQR bound to stay at 100× or more). Procedure: HOW_TO_UPDATE.md.
11. **Slide 27 answer:** is there a written list of gotchas in the repo (for example a GOTCHAS.md)?
12. **Licence for the code** in the public repo: none is chosen yet (the data licence is CC BY 4.0, see
    `data/DATA_LICENSE.md`).

## e. Checks in PowerPoint and on the presenting laptop

Everything so far was rendered with LibreOffice and substitute fonts (QA_NOTES section 4).

1. Open the deck in PowerPoint on a machine with Fira Sans and Fira Mono installed (d6). Check title line counts,
   that no text overflows, that the label chips on 3 and 10 to 14 sit where the QA render shows them, and that the
   Conditions boxes on 17, 18, 20, 21, B1, B2 and B4 stay clear of the footer.
2. Play Morph on 8 to 14: the first filmstrip thumbnail on 7 into slide 10, the Ground chip still from 10 to 14, and a
   jump over slide 15 (skip-first number 4).
3. Slide 20: the log axis, the data labels, and the on-click build of the hero number.
4. The cup (☕) of the abstract is not on slide 1: Fira Mono has no glyph for it, and a fallback emoji font drew it
   differently on every machine. If you put it back in `content.yaml` slide 1 `subtitle_code`, check on the
   presenting laptop that it renders; it is then the one glyph outside the Fira fonts, and `glyph_coverage` fails.
5. The "CC BY 4.0" links: clickable, and on navy (slide 29) not drawn in blue.
6. Export the final PDF from PowerPoint and replace `deck/out/20261015_PyCon-NL_3D-Data-Science.pdf` (today's PDF is a
   LibreOffice export).
7. Presenter view shows the notes; the hidden backup slides B1 to B7 are slides 30 to 36 (reach them by number).

## f. Repo clean-up before the QR code goes live

Do this before the repo URL or QR code is published:

- `deck/template/` (the PyCon NL 2026 style master and its generator) is versioned, so a clone can rebuild the deck.
  If the PyCon NL logo is added later, publish it only within the organisers' permission (d4).
- Code licence: MIT (`LICENSE`); change it there if you prefer another (d12).
- Done 2026-10-12: EPUB folder git-ignored, root stub project removed, client brief and template research removed, absolute paths scrubbed, QA outputs untracked.
- Already excluded: `data/AHN5_C_*.COPC.LAZ` (fetch with `data/fetch_ahn5.py`), `deck/qa/fonts/`, `deck/out/png/`.
- Then set `qr.url` and the repo URL (b) and rebuild.

## g. Rehearsal and optional work

- A full run-through with a timer once slide 27 has its stories; then one run with the skip-first slides left out.
- The fastest talk tracks are slide 2 (56 words in 25 s), slide 1 (42 words in 20 s, plus a show of hands) and
  slide 14 (146 words in 70 s); TIMING.md has every slide.
- **C++ snippet (optional):** `snippets/s02_pcl.cpp` is shown NOT RUN. On a machine with PCL, build it with the
  command in its header and run it on the `crop.pcd` that `s02_python.py` writes. If it runs, record that in QA_NOTES
  and in the notes of slides 2 and B1; if not, keep NOT RUN.

## h. Exceptions and conflicts

The approved exceptions are listed in `CONTRACTS.md`. Two further points follow from the brief itself and stay as
they are (no action needed, listed for transparency):

1. **Dense appendix:** B1 to B7 use 14 to 16 pt text. The brief allows backup slides to be "plain and dense"; the 20 pt
   minimum is kept on all 29 main slides.
2. **Body text over about 20 words on slides 6, 7 and 21: a conflict inside the brief.** The brief caps body text at
   about 20 words, and it also asks for a one-line "use it for" per library on slide 6 (and the lists on slide 7);
   slide 21 counts the diagram's lane labels. The deck follows the per-library lines (`body_words` warns: 5 has 46
   words, 6 has 29, 18 has 25; slide 4 is at 21). If you prefer the 20-word cap on slide 6, delete the job lines of
   the five pipeline libraries in `content.yaml` slide 6 and keep them on trimesh and PyTorch3D (about 30 words), or
   drop every job line (about 20); the talk track says each job anyway.

## k. Python-and-memes extension (2026-10-04)

Five new slides (3 xkcd 353, 8 hand-offs copy/view, 17 expectation vs reality, 22 profile, 23 free-threaded) and
changes on 2, 12, 19, 24, 25 and 29; every slide after 2 renumbered (old 3 to 24 are now 4 to 29; sections a to h
above use the new numbers, sections i and j are history and keep the old ones). Open points:

1. **Slide 3 (2026-10-11): ecosystem wall with third-party logos.** The xkcd comic (CC BY-NC 2.5) is gone; slide 3 is
   now 23 logos in five rows (cut from 42 to what the talk uses or mentions, and the companies row removed, 2026-10-11) (deck/ecosystem/ecosystem.yaml, merged from three researchers' parts; logos in
   deck/assets/logos/, terms per file in deck/assets/logos/SOURCES.md). Decide before the slides are published or
   recorded, because brand policies differ and some pages were NOT readable (403) when checked:
   - The companies row (Kitware, Intel, Meta, Hobu, NumFOCUS, NVIDIA) was removed at the speaker's request, so the
     strictest brand policies (NVIDIA, Meta, Intel) no longer apply to the slide. Their files stay in deck/assets/logos/.
   - NumPy: do not alter or recreate (done: scaled only). Not on the wall: pandas, Blender, Arrow and ASF, Google,
     Linux Foundation (their notes are in SOURCES.md).
   - To drop a logo, delete its id from its row in `deck/content.yaml` (slide 3); the row closes up on the next build.
   - Most project logos state no licence (`none stated`): they are the projects' own marks, shown to identify them.
   - Logos are in their own colours, an exception to the palette (docs/DESIGN.md), on white tiles (light grey in the
     companies row).
   - Not on the wall because the file is too small or unusable: Mayavi, OpenMVS, Esri (an older mark, 135 px), Panda3D
     (white text only), Rerun (152 px wide). Entwine was dropped from the wall (wordmark too small).
2. Rehearse the new timing: 1800 s still, but Landscape (230 s) and RAM (140 s) run under the brief and Performance
   (475 s) and Close (245 s) over it (TIMING.md). Slide 18 is down to 25 s and slide 17 is 20 s: say them fast.
3. Slide 23 (free-threaded): measured on CPython 3.14.7t and 3.14.7 in throw-away venvs with numpy 2.5.3 and laspy
   only (no Open3D wheel for 3.14t); results/bench_freethreaded.json. Re-run with bench/bench_freethreaded.py if a
   newer free-threaded release or NumPy is out before the talk.
4. Slide 8's float32 factor and slide 22's profile output are single-machine measurements (results/python_facts.json,
   results/profile_loop.json); the profile is one profiled run and changes slightly per run.
5. Slide 19 now shows the code at 20 pt in the Drake layout (captions dropped); check it reads from the back row.
6. Body-text word count: slide 25 now has 22 words with the machine line (warn, like slides 4, 6, 7 and 21).

## i. On-screen changes in the final QA round (for the client's review)

- Slide 3: the captions "Point cloud" / "Our labels" are gone (body text); the frames are a little larger.
- Slide 5: SciPy KDTree now spans clustering to visualisation (`height_above`, slide 11 code), NumPy all six steps;
  slide 7: tag 4 reads "Open3D, SciPy".
- Slide 7: AHN source line added. Slides 10 and 11: the Ground label chip, in the same place as on 12 to 14.
- Slide 9 title: "2 Voxel downsampling: one average per voxel" (step-title pattern).
- Slide 16: small print says what P and plane are.
- Slide 17: title "How much slower is the loop over rows?" (a question, so the on-click hero 126× gives the answer; no general "two orders of magnitude" title); bar label "Loop over
  NumPy rows"; support "Same data, same answer, far fewer calls into compiled code."; the conditions name the array and
  the row-ordered factor.
- Slide 18: hero label "per loop step (several NumPy calls)"; support "C++ libraries too: even an empty k = 16 KDTree
  query costs 10.1 µs."
- Slide 20 title: "Loading this street's AHN file outgrows 32 GB" (the LAS records alone, 25.9 GB, stay under 32 GB;
  every loaded state goes over); the conditions run full width under the chart.
- Slide 21 hero label: "extra peak memory, 1 km AHN file".
- Slide 23: the evidence references are 20 pt.
- Slide 24: "Licence: creativecommons.org/licenses/by/4.0" after the source line.
- Conditions lines (17, 18, 20, 21, B1, B2, B4): thread count of the plane runs, boost, the data and its licence,
  "Linux (Omarchy, ...)", and on the memory line "Memory: increase over the process after imports".
- QA_NOTES section 8 lists findings of the documentation round that are not fixed yet (for example the slide 20 small
  print "all arrays kept").

## j. Changes in the re-theme round (2026-10-03 and 2026-10-04)

The deck now uses the PyCon NL 2026 style master (`deck/template/pycon_nl_2026_master.pptx`, docs/DESIGN.md): navy,
blue and sage with neutrals, Fira Sans and Fira Mono, the footer and slide number from the master. Nothing of a
company master is left in the package (`no_teqyard`, which also scans the chart workbooks and the document
properties); the affiliation "ML Engineer, Teqyard" on slide 1 is plain text. On-screen changes besides the new look:

- Thousands separators are no-break spaces (Fira Sans has no narrow no-break space); `glyph_coverage` checks every
  character against the Fira font files.
- Slide 1: the cup is dropped and line 2 reads `    ...  # 12 million times. see you tomorrow` (valid Python; the
  slide 1 notes say how to restore the abstract's exact wording).
- Slide 3: smaller frames with more room for the support and source lines; the four label chips use a 0.06 in frame
  margin so they fit without collisions. Slide 4: text left, close-up right (title on the left margin, as 3 and 5).
- Slides 5 and 7: step names as bold headers with a navy rule (5), "Ground removal" on two lines (7). Slide 6: list
  headings 24 pt, chain arrows navy.
- Slides 12 to 14: no ring on the street furniture object (the leader ends just above it); slide 12 support on one line.
- Slide 15: the distance formula `h = abs(a*x + b*y + c*z + d)` and an "h" chip on the building's tick.
- Slide 16: the small print says what P and plane are in one line.
- Slide 18: slate arrows, blue toll ticks, navy "× N". Slide 19: the statement box no longer overlaps the code.
- Slide 20: RAM bar labels on one line, support "926 203 338 points × 86 B each.", and a dashed navy line that
  continues the 32 GB bar across the computed bars.
- Slide 21: 20 pt code line pitch, so the hero is 60 pt again. Slide 23: habit tiles at 28 pt without accent rules.
- Conditions boxes grow upwards (bottom-anchored), and the shortened CPU string and the thread note only on 16 and 17
  keep them off the footer. B2 to B4: wording fixes (CopcReader line, "slides 8 and 9", "numbers at right", "A CPU
  build ..."), "KDTree" everywhere.

## l. New running example: the Jaarbeurs hall (2026-10-11)

The crop moved from Graadt van Roggenweg to a 200 m box around the Jaarbeurs hall (data/fetch_ahn5.py CROP_BBOX_RD);
pipeline, renders, benchmarks, backup slides and notes were regenerated. Decide or check:

1. **Slide 12 changed its message.** One RANSAC plane for the whole crop ties with the 25 m tiles here (ground recall
   `pipeline.single_plane` against `pipeline.ground`); on the first street it did not (`pipeline.previous_street`). The
   title "Utrecht isn't flat" is gone; the talk track says "flat here, not on the street where I built this" and the
   code now also gives no ground to roof tiles (20 of 64 tiles). Rehearse the new 75 s.
2. **Slide 4 names the building**: "the Jaarbeurs hall at ... the big flat roof". The BAG pand is 0344100000077882
   (Jaarbeursplein 6). Which building the talk room is in is UNVERIFIED: confirm and, if it is this one, say "the
   building we're sitting in" (notes 4, checks).
3. **B5 flipped**: the Random Forest now scores higher than the rules against AHN's building class, mostly because AHN
   files facades (and the hall's floor edges) under class 1 and the rules call them buildings. The notes say so; the
   slide's table is data-driven.
4. **Street furniture**: 3 objects, 53 points, one of them only just above the ground; what they are is UNVERIFIED (no
   imagery checked). The camera pose was chosen so that none is hidden behind the hall (render.py, camera comment).
5. **Research numbers that were measured on the old crop** are replaced: the 0.1 m voxel share is in pipeline.json,
   the COPC read is bench/copc_remote.py (AHN5, the new box). Still from the old street: the lamp-post pilot
   (docs/research/dataset/pole_analysis.json, notes 14 say so) and the research critic's single-plane pilot (no longer
   cited).
6. The 1 km memory benchmark and the big-file numbers do not depend on the crop; the free-threaded run used numpy 2.5.4
   in throw-away venvs (recorded in its conditions), the project venv has 2.5.3.
