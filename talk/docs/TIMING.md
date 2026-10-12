# Timing

The talk is planned for **1800 s (30:00)**: the 29 `seconds` values in `deck/content.yaml`, the same in
`deck/notes.yaml`, whose `ends_at` gives the running clock. The brief's slot is 10:45 to 11:25 (40 minutes including
Q&A and changeover; whether Q&A is included is not confirmed yet, OPEN_ITEMS d1), with about 7 minutes of Q&A after
the talk. The backup slides B1 to B7 are hidden slides 30 to 36 and carry no time.

**2026-10-04, Python-and-memes extension:** five slides added (3 xkcd 353, 8 hand-offs copy or view, 17 expectation
vs reality, 22 profile, 23 free-threaded; 200 s together). The time came from slide 6 (old 5, -40 s), 7 (old 6,
-30 s), 9 (old 7, -10 s), 25 and 26 (old 20 and 21, -20 s each), 18 (old 15, -30 s) and modest trims of 4 and 5 (old
3 and 4, -10 s each), 20 and 21 (old 17 and 18, -10 s each) and 27 (old 22, -10 s). Slide numbers below are the new
ones.

## Per slide

"Words" is the spoken talk track in the built notes (counted on 2026-10-04); "wpm" is words per minute at the planned
seconds. Slide 27's count is its placeholder text only.

| Slide | Title | Section | Seconds | Starts | Ends | Skip-first | Checkpoint | Words | wpm |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 3D Data Science with Python | Hook | 20 | 0:00 | 0:20 |  |  | 42 | 126 |
| 2 | 3D used to mean C++. Not anymore | Hook | 25 | 0:20 | 0:45 |  |  | 54 | 130 |
| 3 | The Python 3D ecosystem at a glance | Hook | 30 | 0:45 | 1:15 |  |  | 67 | 134 |
| 4 | The Jaarbeurs hall, scanned from a plane | Hook | 80 | 1:15 | 2:35 |  |  | 100 | 75 |
| 5 | A point cloud is just an N×3 array | Hook | 80 | 2:35 | 3:55 |  |  | 76 | 57 |
| 6 | No single library does the whole job | Landscape | 65 | 3:55 | 5:00 |  |  | 82 | 76 |
| 7 | laspy loads, Open3D computes, PyVista draws | Landscape | 90 | 5:00 | 6:30 |  |  | 99 | 66 |
| 8 | Python passes the array, not the points | Landscape | 60 | 6:30 | 7:30 | 7 |  | 79 | 79 |
| 9 | Six steps turn a point cloud into labels | Pipeline | 30 | 7:30 | 8:00 |  |  | 43 | 86 |
| 10 | 1 Load: laspy hands you NumPy | Pipeline | 65 | 8:00 | 9:05 |  |  | 79 | 73 |
| 11 | 2 Voxel downsampling: one average per voxel | Pipeline | 55 | 9:05 | 10:00 |  |  | 85 | 93 |
| 12 | 3 Ground removal: one plane per tile | Pipeline | 75 | 10:00 | 11:15 |  |  | 98 | 78 |
| 13 | 4 Clustering: DBSCAN groups what touches | Pipeline | 55 | 11:15 | 12:10 |  |  | 69 | 75 |
| 14 | 5 Labelling: rules name the clusters | Pipeline | 70 | 12:10 | 13:20 |  |  | 146 | 125 |
| 15 | 6 Visualisation: PyVista paints every point | Pipeline | 40 | 13:20 | 14:00 | 6 |  | 56 | 84 |
| 16 | Seven calls run the whole pipeline | Pipeline | 80 | 14:00 | 15:20 |  | leave by 15:20 | 65 | 49 |
| 17 | Expectation vs reality: street furniture | Pipeline | 20 | 15:20 | 15:40 |  |  | 28 | 84 |
| 18 | How far is each point from the ground? | Performance | 25 | 15:40 | 16:05 | 2 |  | 35 | 84 |
| 19 | Same answer, very different bill | Performance | 80 | 16:05 | 17:25 |  |  | 94 | 70 |
| 20 | How much slower is the loop over rows? | Performance | 105 | 17:25 | 19:10 |  |  | 82 | 47 |
| 21 | Every trip into compiled code pays a toll | Performance | 105 | 19:10 | 20:55 |  |  | 129 | 74 |
| 22 | Profile before you vectorise | Performance | 55 | 20:55 | 21:50 | 4 |  | 72 | 79 |
| 23 | Will free-threaded Python save my loop? | Performance | 50 | 21:50 | 22:40 | 1 |  | 57 | 68 |
| 24 | Loop over tiles, never over points | Performance | 55 | 22:40 | 23:35 | 5 |  | 84 | 92 |
| 25 | Loading this street's AHN file outgrows 32 GB | RAM | 60 | 23:35 | 24:35 | 3 | arrive by 23:35 | 69 | 69 |
| 26 | Stream chunks, keep the first point per voxel | RAM | 80 | 24:35 | 25:55 |  |  | 119 | 89 |
| 27 | These [N] gotchas cost me weeks | Close | 120 | 25:55 | 27:55 |  |  | 54 | 27 |
| 28 | Three habits save you those weeks | Close | 75 | 27:55 | 29:10 |  |  | 75 | 60 |
| 29 | Copy the pipeline | Close | 50 | 29:10 | 30:00 |  |  | 64 | 77 |
| | **Total** | | **1800** | | **30:00** | | | **2162** | **72** |

## Sections against the brief

| Section (brief) | Slides | Brief | Deck | Difference | Deck ends | Brief ends |
|---|---|---|---|---|---|---|
| 1 Hook and running example | 1 to 5 | 240 s (4 min) | 235 s | 5 s under | 3:55 | 4:00 |
| 2 Landscape | 6 to 8 | 300 s (5 min) | 215 s | **85 s under** | 7:30 | 9:00 |
| 3 Pipeline on the running example | 9 to 17 | 480 s (8 min) | 490 s | 10 s over | 15:40 | 17:00 |
| 4 Performance cliff | 18 to 24 | 420 s (7 min) | 475 s | **55 s over** | 23:35 | 24:00 |
| 5 Fitting millions of points in RAM | 25, 26 | 180 s (3 min) | 140 s | **40 s under** | 25:55 | 27:00 |
| 6 Gotchas, takeaways, close | 27 to 29 | 180 s (3 min) | 245 s | **65 s over** | 30:00 | 30:00 |
| Total | 29 | 1800 s | 1800 s | 0 | | |

**Flagged deviations:**

- Section 2 runs 70 s under the brief (was 60 s): slides 6 and 7 were cut by 70 s for the new Python slides, and the
  new slide 8 (60 s) gives most of it back.
- Section 4 runs 55 s over (was on budget): the profile slide (22, 55 s) and the free-threaded slide (23, 50 s) are
  new; slide 18 was cut to 25 s and slides 20 and 21 by 10 s each. Slide 23 is skip-first number 1, slide 22 number 4.
- Section 5 runs 40 s under (was on budget): slides 25 and 26 gave 20 s each, as planned for the extension.
- Section 6 runs 65 s over (was 75 s) on purpose: the gotchas are half the abstract's promise. Slide 27's 120 s cannot
  be checked until its stories exist: rehearse it (OPEN_ITEMS g).

**Pace:** the brief asks for 1 to 1.5 minutes per content slide, shorter for hook slides. Over 90 s on purpose:
20 and 21 (105 s), 27 (120 s). The joke slides 3 (15 s) and 17 (20 s) and the shortened slide 18 (25 s) are short
by design. Overall the talk tracks run at 72 words per minute. The densest are slide 2 (130 wpm), slide 1 (126 wpm,
plus a show of hands), slide 14 (125 wpm) and slide 3 (120 wpm, 15 s); no slide reaches 150.

## Skip-first list

If time runs short, cut in this order (each slide's notes carry "Skip-first number N" and the line to say instead):

| Order | Slide | Saves | Cumulative | Decide | Say instead (from the notes) |
|---|---|---|---|---|---|
| 1 | 23 free-threaded | 50 s | 50 s | at the slide 16 checkpoint (leaving after 16:35) | nothing; if asked: free threads help some, NumPy still wins |
| 2 | 18 plane question | 25 s | 75 s | at the slide 16 checkpoint (after 16:35) | on slide 19: "the distance of every point to the ground plane, the test inside RANSAC" |
| 3 | 25 RAM chart | 60 s | 135 s | at the slide 16 checkpoint (after 18:05), or on arriving at 25 after 23:35 | on slide 26: "a full-size AHN file has 926 203 338 points" (token) |
| 4 | 22 profile | 55 s | 190 s | at the slide 16 checkpoint (after 18:05) | on the next slide shown: "a profiler finds such loops: Scalene puts one line at 88 percent" |
| 5 | 24 rule of thumb | 55 s | 245 s | when still late after slide 21 | nothing: the rule comes back as habit 2 on slide 28 |
| 6 | 15 visualisation | 40 s | 285 s | at the end of slide 14 (planned 13:20), only if already late | on slide 16: "every render here is PyVista, off-screen, one fixed camera" |
| 7 | 8 hand-offs | 60 s | 345 s | at the end of slide 7 (planned 6:30), only if already late | on slide 9: "Python passes whole arrays; Vector3dVector copies, np.asarray gives you a view" |

Caveats:

- Slides 15 and 8 come **before** the slide 16 checkpoint, so no checkpoint covers them. Whether Morph plays cleanly
  from 14 to 16 over a skipped slide 15 is UNVERIFIED.
- To skip, say the one sentence, then jump by slide number (type the number, then Enter). Jumping may not play Morph
  (UNVERIFIED); every skip-first slide except 15 sits outside the Morph run (10 to 16).

After 18:05 the notes also say to tell only one story on slide 27; how much that saves depends on the stories.

## Checkpoints (presenter view only, never spoken)

Wall-clock times assume the talk starts at 10:45:00 sharp; they shift with the real start.

| Where | Talk clock | Wall clock | Action |
|---|---|---|---|
| Leaving slide 16 | by 15:20 | 11:00:20 | on time: carry on |
| Leaving slide 16 | after 16:35 | after 11:01:35 | skip 23 and 18 (saves 75 s) |
| Leaving slide 16 | after 18:05 | after 11:03:05 | also skip 25 and 22 (190 s in all), and tell only one story on 27 |
| Arriving at slide 25 | by 23:35 | 11:08:35 | later than that: skip slide 25 |
| End of slide 29 | 30:00 | 11:15:00 | Q&A; slide 29 stays up with the QR code; B1 to B7 are slides 30 to 36 |

Source: `deck/notes.yaml` (slide 16 and 25 `checkpoint`, `skip` on 8, 15, 18, 22, 23, 24, 25) and `storyboard.md`.
