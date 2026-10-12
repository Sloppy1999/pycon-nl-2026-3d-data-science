The checker ran on all 24 main slides and found 18 violations. Timing, section totals, dark-slide spacing, Morph placement, the skip-first list, dashes and the code line caps all pass. Most of the violations are titles that are labels rather than statements.

Script: `scratchpad/review/rules/check.py`. Run it with `venv/bin/python check.py [--proposed proposed_titles.json]`. Results are written to `results.json` next to it. The replacement titles are in `proposed_titles.json` and were re-run through the same rules; all 11 pass.

How the checks work:
- **Statement test:** a list of known verbs, not a language model. A title counts as a label when it has no main verb.
- **Line estimates:** greedy word wrap using the given characters per line. A second estimate checks whether the lines fit the title box height (1.062 in at 30 pt; line height = 1.2 × size × 90 %). Corbel's real line height is not verified.
- **L11 capacity:** not given, so I scaled L1's 27 characters per line from 50 pt to 70 pt, which gives about 19.

## Results (main slides)

| # | Sec | Lay | Title words | Case | Title type | Supp w | Hero w | Body w | Title lines (fit in box) | Trans | s |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | S1 | L1 | 5 | FAIL | verbless | 5 | 0 | 5 | 1 (1) | none | 30 |
| 2 | S1 | L5 | 7 | ok | statement | 0 | 0 | 0 | 1 (2) | fade | 50 |
| 3 | S1 | L4 | 7 | ok | statement | 10 | 0 | 10 | 1 (2) | fade | 80 |
| 4 | S1 | L8 | 8 | ok | statement | 8 | 0 | 8 | 2 (2) | fade | 80 |
| 5 | S2 | L4 | 5 | ok | verbless | 0 | 0 | 0 | 1 (2) | fade | 150 |
| 6 | S2 | L5 | 6 | ok | statement | 7 | 0 | 7 | 1 (2) | fade | 150 |
| 7 | S3 | L4 | 7 | ok | verbless | 0 | 0 | 0 | 1 (2) | fade | 45 |
| 8 | S3 | L7 | 6 | ok | statement | 7 | 0 | 7 | 2 (2) | morph | 60 |
| 9 | S3 | L7 | 7 | ok | verbless | 0 | 3 | 3 | 2 (2) | morph | 55 |
| 10 | S3 | L7 | 7 | ok | statement | 10 | 0 | 10 | 2 (2) | morph | 70 |
| 11 | S3 | L7 | 6 | ok | statement | 0 | 2 | 2 | 2 (2) | morph | 55 |
| 12 | S3 | L7 | 7 | ok | verbless | 10 | 0 | 10 | **3** (2) | morph | 70 |
| 13 | S3 | L7 | 7 | ok | statement | 7 | 0 | 7 | 2 (2) | morph | 50 |
| 14 | S3 | L7 | 7 | ok | statement | 9 | 0 | 9 | 2 (2) | morph | 75 |
| 15 | S4 | L8 | 8 | ok | verbless | 9 | 0 | 9 | **3** (2) | fade | 60 |
| 16 | S4 | L5 | 6 | ok | verbless | 5 | 0 | 5 | 1 (2) | fade | 80 |
| 17 | S4 | L7 | 6 | ok | statement | 4 | 1 | 5 | 2 (2) | fade | 100 |
| 18 | S4 | L4 | 7 | ok | statement | 12 | 3 | 15 | 1 (2) | fade | 100 |
| 19 | S4 | L6 | 6 | ok | imperative | 0 | 0 | 0 | 2 (3) | fade | 80 |
| 20 | S5 | L8 | 8 | ok | statement | 9 | 4 | 13 | 2 (2) | fade | 80 |
| 21 | S5 | L5 | 7 | ok | imperative | 0 | 3 | 3 | 1 (2) | fade | 100 |
| 22 | S6 | L4 | 6 | ok | noun phrase + relative clause | 0 | 0 | 0 | 1 (2) | fade | 110 |
| 23 | S6 | L4 | 6 | ok | verbless | 0 | 0 | 0 | 1 (2) | fade | 45 |
| 24 | S6 | L11 | 4 | ok | imperative | 1 | 0 | 1 | **2** (1) | fade | 25 |

## Checks that pass
- **Seconds:** total is 1800. Section sums match the brief exactly: S1 240, S2 300, S3 480, S4 420, S5 180, S6 180. All cumulative times in the table are correct. The slide-to-section mapping matches the brief.
- **Title length:** every title is 8 words or fewer. Slides 4, 15 and 20 are at exactly 8.
- **Support line and body text:** every support line is 15 words or fewer (maximum 12, on slide 18). Every body total is 20 words or fewer (maximum 15, on slide 18). Slide 22 is the exception, see below.
- **Dark layouts:** slides 1, 19 and 24, none adjacent. No L3 or L6 sits next to L1 or L11, and that still holds after the skip-first slides are removed.
- **Transitions:** Morph on exactly slides 8 to 14.
- **Skip-first list:** slides 6, 13, 15 and 20. That is 4 slides, and the claimed 340 s saving matches the table.
- **Dashes:** no en or em dashes in on-screen text. The "–" empty-cell markers are ignored.
- **Code length:** every stated snippet is 12 lines or fewer.
- **Terminology:** no "segmentation". "Downsampling" always appears with "voxel".
- **Title lines:** no title runs past 3 lines.

## Violations and exact replacements

1. **Slide 1:** "3D Data Science with Python" fails sentence case ("Data", "Science") and is not a statement.
   - **Decision for the orchestrator:** treat it as exempt. It is the official talk title, it has to match the sidebar text word for word, and it is the name in the PyCon programme. No text change.
   - The transition is "none" where the rule says fade. Set it to fade.
2. **Slide 5:** "Six libraries, six different jobs" has no verb. Replace with **"Six libraries do six different jobs"** (6 words, 1 line on L4).
3. **Slide 7:** "Six steps from raw scan to labels" has no verb and uses "scan" instead of the deck's term "point cloud". Replace with **"Six steps turn a point cloud into labels"** (8 words, 1 line).
4. **Slide 9:** "2 Voxel downsampling: one centroid per cube" has no verb. Replace with **"2 Voxel downsampling averages each cube"** (6 words, 2 lines on L7: "2 Voxel downsampling" / "averages each cube"). Open3D returning the centroid is verified in critic.md.
5. **Slide 12:** "5 Labelling: four simple rules per cluster" has no verb and wraps to 3 lines on L7, where the box holds about 2. Replace with **"5 Labelling: four rules name clusters"** (6 words, 2 lines).
6. **Slide 13:** "Visualization" breaks the deck's British spelling (labelling, labelled, colours, neighbours). Replace with **"6 Visualisation: every render here is PyVista"** (2 lines). The first line is exactly 22 characters, which is at the limit, so this one is tight.
7. **Slide 15:** "The test: every point's distance to the ground" has no verb and wraps to 3 lines on L8 (about 2 fit). Replace with **"How far is each point from the ground?"** (8 words, 2 lines: "How far is each point" / "from the ground?").
8. **Slide 16:** "Same answer: one loop, one expression" has no verb. Replace with **"A loop and one expression agree exactly"** (7 words, 1 line on L5).
   - **Support line check:** "Identical results, checked with `np.array_equal`" only holds for the element-wise form. I tested 200k synthetic points in the venv:
     - the element-wise expression `a*x+b*y+c*z+d` gives `array_equal` True;
     - `pts @ n + d` gives False, with a maximum difference of 7.1e-15.
   - **If the right-hand code uses `@`:** use "Same results, checked with `np.allclose`" and title "A loop and one expression agree".
9. **Slide 22:** "[N] gotchas that cost me weeks" is a noun phrase, not a statement. Replace with **"These [N] gotchas cost me weeks"** (6 words).
   - The body word count is unknown because the gotchas are not supplied. Five one-line gotchas of 5 words or more each would reach 25 words or more, over the 20-word limit. Cap them at 5 items of 4 words or fewer.
10. **Slide 23:** "Three habits for fast 3D Python" has no verb. Replace with **"Three habits keep your 3D Python fast"** (7 words, 1 line).
11. **Slide 24:** "Take the pipeline home" is about 22 characters, against about 19 per line at 70 pt. That makes 2 lines in a 1.065 in box that holds about 1 (estimate). Replace with **"Copy the pipeline"** (3 words, 1 line). It also echoes the brief's "pipeline to copy".

## Softer findings (not hard violations)
- **Content-slide pace (60 to 90 s):** slides 5 and 6 (150 s each), 17, 18 and 21 (100 s each) and 22 (110 s) are over; slides 7 (45), 9 (55), 11 (55), 13 (50) and 23 (45) are under.
  - S2 has 300 s for only 2 slides, so the brief's section budget and its pace rule cannot both hold. Either add one S2 slide or accept 150 s per slide.
  - Slides 9, 11 and 13 are Morph steps, so being short is fine there.
- **Hero numbers on pipeline slides 9 and 11:** the brief reserves hero numbers for performance slides, and these slides already carry code and a render. Move them into the support line:
  - slide 9: "[1 239 310] points in, [X] out at [v] m voxels." (9 words)
  - slide 11: "[N] clusters, not labels yet." (5 words)
- **Slide 17 support line "Conditions in small print."** reads like a stage direction, not on-screen text. Replace it with "Same data, same answer; only the number of calls changes." (10 words) and put the conditions in the 12 pt source line.
- **Slide 21 has two visuals** (an 11-line snippet plus a trade-off table) and a hero number. Keep the code and the hero, and move the table to the notes or to B2. Support line: "Peak memory stays bounded only with voxels of 0.5 m or more." (12 words; critic.md C4).
- **Text inside diagrams is not counted** in body totals. Slide 5 is estimated at about 36 words (6 names, 6 lane labels, 6 one-line jobs; ESTIMATE). Limit each job to 3 words or fewer and drop the lane labels.
- **Title full stops:** only slides 2 and 19 end with a period. Use "Loop over tiles, never over points" (2 lines on L6, about 3 fit) and "3D used to mean C++. Not anymore".
- **Term spelling:** slide 6's visual says "SciPy KDTree" but B4 says "KD-tree". Change B4 to "What can replace a KDTree?". B4 "Alternatives to a KD-tree" is also a label.
- **Appendix transitions:** B1 to B4 are "none". They are hidden, but set them to fade for consistency.
- **Skip-first slide 13 is inside the Morph chain.** Whether PowerPoint morphs cleanly from 12 to 14 when 13 is hidden is UNVERIFIED.
- **Slide 3 claims are outside this check but UNVERIFIED** per critic.md:
  - "the street outside this building" (the crop's location has not been confirmed with pyproj);
  - "Raw point cloud in" (AHN is delivered already classified).