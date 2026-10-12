**Storyboard v1 review: speaker-coach lens (opening, titles, humour, one idea per slide, pacing, skip list, close)**

Priority order: P1 means fix before approval, P2 means fix in the build, P3 is polish. Unless marked UNVERIFIED, every number comes from the reports (most are PILOT runs), and some are my own arithmetic on them. No files were written.

### P1: must fix

**1. Slides 1–3: the street arrives at 1:20, after the minute in which people decide whether to stay.** In v1, 30 s plus 50 s pass before slide 3 appears. Keep the brief's order but compress it so the street is on screen by 0:45.
- **Slide 1 (L1, 20 s spoken):** Open with a show of hands ("who has written this loop?"), then the joke payoff, then the promise: "In 30 minutes: a pipeline you can copy, and the gotchas that cost me weeks." Today the promise is first said on slide 24.
  - **Layout:** The joke needs two code lines, but the L1 subtitle placeholder is 7.43 × 0.45 in, which holds one 24 pt line. Make it about 0.9 in tall; there is free space down to the presenter slot at y 6.39 in.
  - **☕ glyph:** Consolas probably has no emoji, and the fallback on the presenting machine is UNVERIFIED. Test it there or drop the cup.
  - **Repo link:** Put the short repo URL in the presenter slot, so people who photograph the slide during room-filling already have it.
  - **"12 million":** This matches no dataset figure (the crop is 1,239,310 points, the tile 21,013,926). Never suggest that the street has 12 M points.
- **Slide 2 (L5, 25 s):** Keep the title.
  - Grey out the C++ column so it shows the shape of the code only, and highlight the key Python line. Both sides must do the same task, including loading.
  - The C++ is NOT RUN. Run it before the talk or remove it; a C++ developer will challenge it in Q&A.
  - Talk track: "The C++ is still there underneath, you just stopped writing it. Hold that thought until minute 17." This sets up section 4.
- **Slide 3 (L4, 90 s, starts at 0:45):**
  - **Support line:** "Raw points in, labelled street out. The code is yours." (10 words)
  - **Say aloud:** "I threw away AHN's labels and graded myself against them." This is the honest framing of "raw" (critic §3).
  - **Location claim:** "Outside this building" is consistent with the data but UNVERIFIED. Running the dataset agent's own landmark conversion puts its guessed Jaarbeursplein point about 60 m east of the crop's edge, but that venue coordinate is itself a guess. Check the crop bounding box against a map first. If it is not adjacent, use the title "This is Utrecht, as a point cloud".
  - **Camera:** The render must use the same camera as slides 8–14, so the audience recognises the street at slide 8.

**2. Slides 8–13: the numbered "N Step:" titles mix a topic label with a statement and do not fit.**
- **Fit:** They run 29–45 characters. L7 fits about 22 characters per line at 30 pt, and the 1.06 in title box holds 2 lines. Slide 13 risks 3 lines and overflow with substitute fonts.
- **Spelling:** "Labelling" and "Visualization" mix British and American spelling. Use British spelling everywhere: labelling, visualisation.
- **Fix:** Add a `!!tracker` object, a strip of six chips (load · voxel downsampling · ground removal · clustering · labelling · visualisation). It sits in a fixed spot, highlights the current step in coral, keeps the others grey, and morphs with the render. Titles then become plain statements:
  - 8: "laspy hands you plain NumPy arrays"
  - 9: "Each voxel keeps one averaged point" (this matches Open3D's verified centroid behaviour and drops the word "cube")
  - 10: "Even Dutch streets are not flat"
  - 11: "DBSCAN groups whatever touches"
  - 12: "Four simple rules turn clusters into labels"
  - 13: "Every image in this talk is PyVista"

**3. Slide 22: the gotchas are half the promise but get 110 s, about 22 s each, and none have been supplied yet.**
- **Fix:** Plant one gotcha where it hurts, as the support line on 8, 9, 10, 12, 16 and 21. Give it a fixed coral "Gotcha" marker. Slide 22 then becomes a recap checklist people can photograph, plus one full war story, at 130 s.
- **Candidates the research verified:** Each is only a candidate. The speaker must confirm it actually cost him time, otherwise it goes.
  - 8: "Subtract a local origin, or float32 rounds to 3 cm." (Spacing at RD coordinates is 1.6 cm in x and 3.1 cm in y.)
  - 8, alternative: `Vector3dVector` with float32 takes 452 ms against 4.8 ms for float64, at 1M points.
  - 10: One plane recovers only 75 % of the ground (recall 0.753).
  - 12: "AHN class 1 is not vegetation: cars and facades too."
  - 16: NumPy scalars inside a loop are 5–7× slower than plain Python floats.
  - 21: Merging chunk keys with `np.isin` + `np.union1d` took 33 s, against about 6 s for one `np.unique`.
  - Seeded RANSAC is only reproducible with `probability=1.0`.

**4. Slide 14 is missing the "if I'm running late" note the brief requires.** Put it in the speaker notes (presenter view only, see the checkpoints below). Support line: "Full script: [short repo URL]". This is the "copy this" moment, and people will photograph it.

**5. Slide 17 carries two ideas.** It shows two task groups but has one hero, and one "[X]×" cannot stand for both 79× (plane distance) and 4.8× (kNN).
- **Fix:** Show plane distance only, with two bars that match slide 16's two snippets: the loop (450 ms, coral) and one vectorised call (5.7 ms, grey).
- **Hero:** [79]×.
- **Title:** "A loop over points: [79]× slower"
- **kNN:** 4.8×, or 40× with `workers=-1`, goes into the notes as the likely question, and into B4.

### P2: one idea per slide, and slides that will run long

**6. Slide 21 has two visuals (code and table) plus a hero.**
- Keep the code and the hero "peak [X GB] → [Y MB]". Run it at 0.5 m voxels or more: at 0.1 m, AHN keeps 93 % and the peak is 1586 MiB (critic C3, C4).
- Replace the table with the support line "Fine per point; neighbour steps need overlapping tiles."
- Move the table to B2.

**7. Slide 5 will run long.** A static 150 s diagram of six libraries realistically takes 3–4 minutes live.
- **Title:** "No single library does the whole job". It creates the need for slide 6.
- **Notes:** Exactly one sentence per tile.
- **Time:** 120 s.

**8. Slide 6: the "skip it" column is not covered by the title.**
- Grey it out, with at most three factual one-liners:
  - "PyTorch3D on 3.13: no supported install"
  - "Open3D legacy + tensor: different defaults"
  - "Open3D reading LAZ: empty cloud"
- Time: 120 s.

**9. Slide 19: 80 s on a six-word dark slide is too long, and it does not answer "how to spot the cliff".**
- **Title:** "Loop over tiles, never over points" (no full stop). It calls back to slide 10's per-tile loop.
- **Under the title:** one monospace line, `for p in points:`, struck through.
- **Time:** 55 s.

**10. Slide 20: "laptop" is unsupported, and "AHN tile" is jargon.** The benchmark machine is a Ryzen 7 5700X desktop with 31.3 GB RAM.
- **Title:** "One map tile of Utrecht outgrows 32 GB"
- **Caveat:** "Outgrows" is arithmetic only: 27.8 GB of records plus a float64 xyz copy. Measure it or mark it as such.

**11. Slide 12: "pass through leaves" is wrong for this data.** AHN flies in the leafless season, and this tile was a night flight in April.
- **Support line:** "Strongest rule: pulses slip past branches, so trees echo several times."
- **Risk:** The crop has only about 7 pole-like objects. If street furniture cannot be found, slide 3 must not promise four classes.

**12. Slide 9 and slide 21 use different meanings of "one point per voxel".** Slide 9 is Open3D's centroid; the chunked snippet keeps the first point. Keep 21's title, "Stream chunks, keep one point per voxel", and explain the first-point choice in the notes.

### P2: humour, one joke per section

| Section | Slide | Joke | Basis |
|---|---|---|---|
| S1 | 1 | The `for point in point_cloud` joke, plus the spoken payoff | Abstract |
| S2 | 6 | "Ask Open3D to read a .laz and it politely hands you an empty point cloud. That's why laspy loads." | Verified on 0.20.0; it is about file formats, so the library description stays neutral |
| S3 | 10 | Title: "Even Dutch streets are not flat" | Ground spread about 1.6 m; one plane: recall 0.753 |
| S4 | 17 | Right after the hero: "The abstract promised 'see you tomorrow'. Measured at 12 M points: [T]. I exaggerated; the [79]× is real." | Needs a real 12 M run. Pilot rates suggest seconds to minutes (UNVERIFIED extrapolation) |
| S5 | none | Optional, only if it happened to the speaker: "I saved RAM by writing to /tmp. /tmp was RAM." | The research machine's `/tmp` is tmpfs |
| S6 | 24 | Callback in the last line: "If you still write that loop, at least you know which coffee it costs." | Callback to slide 1 |

### P2: rebalanced timing (sums to 1800 s)

| Section | Seconds per slide | Section total | Ends at |
|---|---|---|---|
| S1 | 1: 20 · 2: 25 · 3: 90 · 4: 90 | 225 (−15) | 3:45 |
| S2 | 5: 120 · 6: 120 | 240 (−60) | 7:45 |
| S3 | 7: 40 · 8: 65 · 9: 55 · 10: 75 · 11: 55 · 12: 70 · 13: 40 · 14: 80 | 480 | 15:45 |
| S4 | 15: 55 · 16: 80 · 17: 115 · 18: 115 · 19: 55 | 420 | 22:45 |
| S5 | 20: 80 · 21: 100 | 180 | 25:45 |
| S6 | 22: 130 · 23: 75 · 24: 50 (includes about 20 s of slack) | 255 (+75) | 30:00 |

- **Client sign-off needed:** This moves 75 s from S1 and S2 into the gotchas.
- **Still over 90 s, on purpose:** 5, 6, 17, 18, 21 and 22. These are the centrepiece and the promise.
- **If the budgets must stay as in the brief:** Keep S1 and S2 at v1, cut 19 to 50 s, and give the 30 s to 17 and 18.

### P2: skip list and checkpoints

**Skip first, in this order:** 15 (−55 s), 20 (−80), 19 (−55), 13 (−40). Together that saves 230 s.
- **15:** Say the task in one sentence on slide 16.
- **20:** The 926 M-point fact is spoken on 21.
- **19:** Its rule comes back as takeaway 2.
- **13:** Say "every image here is PyVista" on slide 14.
- **Remove 6 from v1's skip list.** It carries an abstract promise and the S2 joke, and it explains the pipeline's library choices.
- **How to skip:** One sentence, then click. Jumping by slide number may not play Morph (UNVERIFIED).

**Checkpoints (notes only):**
- **Slide 14** (target to leave: 15:45):
  - Leaving after 17:00: skip 15 and 20.
  - Leaving after 18:30: also skip 19, and tell only the one story on 22.
- **Slide 20** (target to arrive: 22:45): arriving after 24:00, skip 20 and give 21 80 s.

### P3: takeaways, close and titles

**13. Slide 23 has no content yet.**
- **Title:** "Three habits that save you those weeks"
- **Tiles:**
  - "Pass NumPy arrays between libraries"
  - "Loop over tiles, never over points"
  - "Stream chunks, then downsample"
- None of these is new information. Time: 75 s.

**14. Slide 24.**
- **Title:** "Take the pipeline and the gotchas home"
- **QR:** It points to the repo, which needs the runnable pipeline script and a `GOTCHAS.md`.
- **Small print:**
  - AHN5 CC BY 4.0 line
  - "Title shared with F. Poux's O'Reilly book (2025); independent talk"

**Blocking dependencies for the promise:**
- The full six-step runnable script does not exist yet.
- The repo must be cleaned before the QR goes live: `.gitignore` does not exclude the O'Reilly EPUBs, and `pyproject.toml` contains a personal gmail address.

**15. Other titles.**
- 15: "How far is each point from the ground?"
- 16: "Same answer, very different bill" (sets up 18's toll)
- 18: keep, and keep its support line; its 2.3× evidence goes in the notes
- Keep 4, 7 and 14
- Drop the full stop on 19 and keep 2's two-beat title as the one exception
- Use British spelling throughout