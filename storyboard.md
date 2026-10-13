# Storyboard: "3D Data Science with Python", PyCon NL 2026 (for approval)

> **2026-10-14 (Phase 3 restructure, approved by the speaker): 31 main slides, 25:45, three acts.** Thesis: in Python
> you write the plan and compiled code does the work, so four rules take a city scan from LAZ to a label per point,
> fast, within memory and honestly. Act 1, Why: Intro (1 title, 2 C++ vs Python, 3 goal, 4 the four rules, 5 roadmap:
> one city block, six steps, three questions) · Data (6 case, 7 plane, 8 representations) · Toolbox (9 wall, 10 meme).
> Act 2, Build: Pipeline (11 overview, 12 to 18 the six steps, 19 summary) · Speed, "is it fast?" (20 to 24) · Memory,
> "does it fit?" (25, 26). Act 3: Reality, "is it right?" (27 poles, the twist; 28 density) · Wrap-up (29 rules, 30
> limits and next steps, 31 thank you with one closing line).
>
> Rules renumbered in the order the talk first proves them, same order on slide 4, every badge and slide 29:
> 1 Think in arrays, not points (8, 12, 13) · 2 Make it small first (14, 15, 17, 25, 26) · 3 Let compiled code loop
> (16, 18, 19, 20 to 24) · 4 Look before you compute (27, 28). Each chapter's last slide says its rule ("Rule k: …").
> The footer breadcrumb is Intro · Data · Toolbox · Pipeline · Speed · Memory · Reality · Wrap-up, highlighted on every
> footer slide. Footnotes (approved): 2 why the PCL and Open3D counts differ; 25 and 26 the 1 km tile against the
> full AHN5 sheet 2023_C_31HZ2 (computed, not run); 23 and 24 the different setup from the slide 21 baseline.
> Evaluation stated on 6: AHN for ground and buildings, BGT for poles; 30 says vegetation is not scored.
>
> Change log, old → new: 1 to 4 → 1 to 4 (2 and 4 retitled or reordered); new 5 (roadmap); 5, 6, 7 → 6, 7, 8 (6:
> evaluation line); 8 (lifecycle ring) → hidden backup B8; 9 → 9; 10 → 10 ("Python plans; compiled code does the
> work", callout rewritten); 11 → 11 ("Six steps: from LAZ file to labels", step 6 named Paint-back); 12, 13 → 12, 13
> (13: "pass views, not copies", the float32 factor moved to the notes); 14 to 19 → 14 to 19 (16, 17, 18 retitled and
> badged; 17's takeaway: 1 024 clusters, not 232 180 points); 22 to 26 → 20 to 24; 27, 28 → 25, 26 (25: "A full AHN
> sheet would need 74.2 GB", the "Why not 24 B?" box moved to the notes); 20, 21 → 27, 28 (28: "From the air, the city
> is sampled unevenly"); 29 → 29 (new order); new 30 (limits and next steps); 30 → 31 (closing line "Write the plan in
> Python; let compiled code loop."). Timing table: docs/TIMING.md.

> **2026-10-13 (restructure review): same 30 slides, same order, 25:45; the four rules made visible.** The rule chip is
> now the badge of slides 4 and 29 in small (blue number disc + the rule), on every evidence slide, now also 7 and 12
> (Rule 1). Slides 12 to 18 carry a six-step tracker top right (Load · Voxels · Ground · Clusters · Labels · Paint).
> Each chapter's last slide states its rule as a verdict line: 19 and 26 "Rule 4: …", 21 "Rule 2: …", 28 "Rule 3: …".
> Slide 3 has three columns ("Not today" is in the notes only). Slide 12 is titled "1 Load: subtract a local origin
> first", slide 13 "1 Load: use views, not copies". The side notes of 17 and 18 give the result ("Height, footprint and
> echoes decide the class"; "Each point takes its nearest voxel point's label"); leaf-off and the fixed camera are in
> the notes. Slide 29 shows one rule per click, and Rule 1's evidence is the cost of a copy (24 B per point per xyz
> copy, slides 7, 12, 13), no longer "722 961 × 3, as views". No new numbers.

> **2026-10-13 (restructure): 30 main slides, 25:45, the four rules as the spine.** Arc: Hook (1 to 4: C++ vs Python,
> the goal, the rules as the promise) · Data (5 case, 6 plane, 7 representations, 8 where the pipeline
> sits) · Toolbox (9 wall, 10 Python is the interface) · Pipeline (11 overview, 12 Load, 13 views not copies, 14 to 18
> steps 2 to 6, 19 summary) · Reality (20 poles, 21 density) · Speed (22 to 26) · Memory (27 the 86 B problem, 28 stream
> chunks, restored) · Rules (29) · Close (30). Removed: Agenda, Scope, "No single library does the whole job". Every
> evidence slide carries a rule badge; the footer breadcrumb lists the chapters. Old-to-new: 1, 2 same; 7 to 3; 12 to
> 4; 9 to 5; 8 to 6; 10 to 7; 11 to 8; 4 to 9; 3 to 10; 15, 16 to 11, 12; 14 to 13; 17 to 30 to 14 to 27; 31, 32 to
> 29, 30. Timing table: docs/TIMING.md.

> **2026-10-12: revised to 29 main slides (speaker's review).** New: 6 "Four rules of thumb for 3D data" and 28 "Take
> the four rules home" (the same rules with the talk's evidence), 26 "Why it works: memory over time" (Scalene memory timeline,
> bench/bench_memory_scalene.py; slides 24 and 25 keep the RSS peaks of bench_memory.py, notes 26 explain why the two differ). Removed: old 18 (plane render), old 24 (statement), old 28 (three habits). Changed: 2 (PCL
> compiled and run, both outputs shown), 3 (wall pruned to the libraries the talk uses or names), 4 (proposed as the
> case, with a data set table), 8 (images under the chain), 9 (copy or view legend), 11 to 16 (a step sketch in each
> render, line-by-line notes), 17 (summary table), 18 (expectation from the BGT register, bench/bgt_street_furniture.py),
> 19 (quiz), 20 to 26 (one-line conditions; the full line is in the notes), 22 (icicle), 27 (six gotchas). The current
> wording is in deck/content.yaml and deck/notes.yaml; old-to-new numbers: 6 to 17 became 7 to 18, 25 to 27 became 24, 25
> and 27, 29 became 29.
>
> **2026-10-11 (later): the running example is the Jaarbeurs hall and its surroundings (RD 135715, 455475 to 135915, 455675), not Graadt van Roggenweg: slide 4 is "The Jaarbeurs hall, scanned from a plane" with an arrow on the roof, slide 12 "one plane per tile" (one plane ties with the tiles here, not on the first street), all results, renders and benchmarks regenerated. The first street is in data/previous/. Tables below keep the old wording.**
>
> **2026-10-11: slide 3 is now "The Python 3D ecosystem at a glance" (a wall of 23 logos in five rows: load and store,
> arrays and geo, process and reconstruct, visualise, learn; 30 s, 15 s taken from slide 6;
> data in deck/ecosystem/); the xkcd 353 joke below was dropped. New hidden backup slides B5 to B7.**
>
> **2026-10-04: extended to 29 main slides (more Python content and natively drawn jokes, approved by the speaker).**
> New: 3 "import open3d feels like import antigravity" (xkcd 353, CC BY-NC 2.5, 15 s), 8 "Python passes the array,
> not the points" (copy or view at each hand-off, results/python_facts.json, 60 s), 17 "Expectation vs reality:
> street furniture" (20 s), 22 "Profile before you vectorise" (Scalene per-line CPU profile, results/profile_scalene.json, 55 s; cProfile kept as a cross-check),
> 23 "Will free-threaded Python save my loop?" (3.14t vs 3.14, results/bench_freethreaded.json, 50 s). Changed: 2
> 12 (`>>> import this` callout), 19 (Drake format redrawn, replaces the captions), 24
> (second line "np.vectorize is a for loop in disguise"), 25 ("It works on my machine" line), 29 (coffee callback).
> Old slides 3 to 24 are now 4 to 7, 9 to 16, 18 to 21 and 24 to 29; the table below keeps the OLD numbers. Timing,
> skip-first list and checkpoints: docs/TIMING.md. Since 2026-10-13 the deck has 28 main slides, all fades (no
> Morph); docs/TIMING.md has the current list, the tables here are history.
>
> **2026-10-03: re-themed to the PyCon NL 2026 palette; layout numbers refer to
> deck/template/pycon_nl_2026_master.pptx** (personal talk: Fira Sans and Fira Mono, docs/DESIGN.md). The storyboard
> below is otherwise the approved version of 2026-10-02; the built deck's current wording is in `deck/content.yaml`.

Status: storyboard only, nothing built. Square brackets = placeholder until a result file exists.
Template: PyCon NL 2026 style master, PPTX. Layouts: L1 title (dark), L4 title and text, L5 two columns,
L6 statement (dark), L7 text left / media right, L8 media left / text right, L10 title left / content right,
L11 closing (dark). Dark slides 1, 19, 24, never adjacent.

Running example: AHN5 tile 135000_455000, 200 m crop around the Jaarbeurs hall (RD 135715 to 135915 /
455475 to 455675), 722 961 points. Licence CC BY 4.0 (Het Waterschapshuis).

Terminology (en-GB, everywhere): point cloud · voxel downsampling · ground removal · clustering · labelling ·
visualisation · "tile" = the 50 m processing squares only · "AHN file" = a download.
Fourth class: [street furniture | cars and small objects], see question 1.

## Main deck

| # | Sec | Layout | Visual | Transition | On-screen title | Support line | Hero number / code | Sec (cum.) |
|---|---|---|---|---|---|---|---|---|
| 1 | Hook | L1 | Title slide; the joke as 2-line code in an enlarged subtitle slot | fade | 3D Data Science with Python | Sergio Peral · ML Engineer, Teqyard · [repo URL] | Code: `for point in point_cloud:` / `    # 12 million times. see you tomorrow ☕` | 20 (0:20) |
| 2 | Hook | L5 | Left, greyed: C++ (PCL) load + voxel grid. Right: the same in 2 lines of Open3D, key line highlighted | fade | 3D used to mean C++. Not anymore | – | Code both sides (C++ NOT RUN) | 25 (0:45) |
| 3 | Hook | L4 | Wide split render of the street: left raw (height ramp), right our labels; edge arrow "Jaarbeurs halls [27 m]" | fade | This street is right next to Jaarbeurs | AHN's labels hidden, rebuilt in Python, scored against AHN. | Source line: AHN5, CC BY 4.0 | 90 (2:15) |
| 4 | Hook | L8 | Close-up of the same street (same camera, narrow view angle), single points visible; REPL on the right | fade | A point cloud is just an N×3 array | Plus one column per attribute: intensity, returns, class. | Code: `las.xyz.shape` → `(722961, 3)`; `las.classification[:5]` | 90 (3:45) |
| 5 | Landscape | L4 | Native map: six step chips in a row, each library tile under the steps it serves; only the five pipeline libraries (no dashed tiles) | fade | No single library does the whole job | – | – | 120 (5:45) |
| 6 | Landscape | L5 | Left "Worth it": laspy → NumPy → Open3D → PyVista, plus SciPy KDTree, trimesh. Right "Not for this pipeline": 3 grey ✗ items | fade | laspy loads, Open3D computes, PyVista draws | – | – | 120 (7:45) |
| 7 | Pipeline | L4 | Filmstrip of six thumbnails (the frames of 8 to 13) with step names; thumbnail 1 zooms into slide 8 | fade | Six steps turn a point cloud into labels | – | – | 40 (8:25) |
| 8 | Pipeline | L7 | Code left; frame 1 right: point cloud, height ramp | Morph | 1 Load: laspy hands you NumPy | Subtract a local origin before anything else. | Code, 6 lines: `laspy.read`, `xyz - mins`, `Vector3dVector` | 65 (9:30) |
| 9 | Pipeline | L7 | Frame 2: after voxel downsampling (larger, sparser points) | Morph | 2 Voxel downsampling averages every voxel | 722 961 points in, [232 180] out at [0.5 m]. | Code, 3 lines: `pcd.voxel_down_sample([0.5])` | 55 (10:25) |
| 10 | Pipeline | L7 | Frame 3: ground dark grey, the rest on the height ramp | Morph | 3 Ground removal: Utrecht isn't flat | Scored against AHN's ground: [P] % precision, [R] % recall. | Code, ≤ 10 lines: loop over [50 m] tiles, `segment_plane(..., probability=1.0)` | 75 (11:40) |
| 11 | Pipeline | L7 | Frame 4: clusters in neutral cycling colours, noise dimmed | Morph | 4 Clustering: DBSCAN groups what touches | [N] clusters. Clusters are not labels yet. | Code, ≤ 7 lines: `cluster_dbscan(eps=[1.0], min_points=[10])` | 55 (12:35) |
| 12 | Pipeline | L7 | Frame 5: four classes, direct labels as native text chips | Morph | 5 Labelling: rules name the clusters | Leaf-off scan: pulses slip between branches, so trees echo repeatedly. | Code: per-cluster height, footprint, share of multiple returns | 70 (13:45) |
| 13 | Pipeline | L7 | Frame 6: labels painted back onto all 722 961 points (one KDTree query) | Morph | 6 Visualisation: PyVista paints every point | Fixed camera, off-screen, one PNG per step. | Code, ≤ 8 lines: `KDTree(...).query`, `Plotter(off_screen=True)`, `screenshot` | 40 (14:25) |
| 14 | Pipeline | L7 | Frame 6 stays; code column shows the pipeline as 7 calls | Morph | Seven calls run the whole pipeline | Helpers live in the repo; link at the end. | Code: 7 lines, one per step. Notes: running-late checkpoint | 80 (15:45) |
| 15 | Perf | L8 | Same street with the fitted ground plane as a translucent sheet and a few distance ticks | fade | How far is each point from the ground? | RANSAC's inner test, on 722 961 points. | – | 55 (16:40) |
| 16 | Perf | L5 | Left: loop over NumPy rows (5 lines). Right: one element-wise expression (3 lines). Key lines highlighted | fade | Same answer, very different bill | Identical results, checked with `np.array_equal`. | Code both sides | 80 (18:00) |
| 17 | Perf | L7 | Native column chart, log time axis: loop [X ms] blue, one expression [Y ms] grey; data labels; conditions in 12 pt | fade | A loop over NumPy rows costs [X]× | Same data, same answer; only the number of calls changes. | Hero: [X]× (on-click build) | 115 (19:55) |
| 18 | Perf | L4 | Native diagram: Python lane above a dashed boundary, compiled code below; the loop crosses N times with toll ticks, one call crosses once | fade | Every trip into compiled code pays a toll | Same for C++ libraries: one KD-tree query per point costs [3 µs]. | Hero: [450 ns] per crossing | 115 (21:50) |
| 19 | Perf | L6 | Statement plus one struck-through code line, `for p in points:` | fade | Loop over tiles, never over points | – | – | 55 (22:45) |
| 20 | RAM | L8 | Native horizontal bar chart in GB: RAM 16 / 32 (navy), LAS records, + float64 xyz, our pipeline (blue); computed bars marked "computed" | fade | A full-size AHN file outgrows 32 GB | 926 203 338 points × [80] bytes each in our pipeline. | Hero: [80] bytes per point | 80 (24:05) |
| 21 | RAM | L4 | Full-width code: chunked read, first point per voxel (12 lines, ran on the crop and the 1 km tile); hero on the right | fade | Stream chunks, keep the first point per voxel | Memory now follows the output, not the input. | Hero: peak [3.3 GB] → [1.0 GB] | 100 (25:45) |
| 22 | Close | L10 | Table on the right: 5 rows, code token + consequence in ≤ 4 words | fade | These [N] gotchas cost me weeks | – | [GOTCHA 1 to 5: speaker supplies] | 130 (27:55) |
| 23 | Close | L4 | Three tiles, one habit each, each pointing back to its evidence slide | fade | Three habits save you those weeks | – | – | 75 (29:10) |
| 24 | Close | L11 | QR code on a white tile (right), contact block (left), credits in 12 pt | fade | Thank you (community and attendees) | [repo URL] | – | 50 (30:00) |

Sections: S1 225 s (brief 240), S2 240 s (300), S3 480 s (480), S4 420 s (420), S5 180 s (180),
S6 255 s (180, runs 75 s over on purpose: the gotchas are half the promise). Total 1800 s.
Over the 90 s pace on purpose: 5, 6, 17, 18, 21, 22.
Skip first: 15, 20, 19, 13 (saves 230 s).
Checkpoints (notes only): leave slide 14 by 15:45. After 17:00 skip 15 and 20; after 18:30 also skip 19 and
tell only one story on 22. Reach slide 20 by 22:45, otherwise skip it.

## Appendix (hidden, fade, L4, dense)

| # | Title | Content |
|---|---|---|
| B1 | Why not just use C++? | When C++ pays off (real-time, embedded, custom kernels) vs Python glue over the same kernels |
| B2 | How does this scale to billions of points? | AHN file sizes, COPC bbox queries (`laspy.CopcReader`), tiles with overlap, the RAM trade-off table |
| B3 | Which GPU options actually help? | Open3D CUDA wheel: what got faster, what did not (single runs, indicative); PyTorch3D install status |
| B4 | What can replace a KDTree? | Open3D KDTreeFlann, voxel grid hashing, octree; the kNN loop numbers (per point vs one call vs all cores) |
| B5 | Could a classifier replace the labelling rules? | Added 2026-10-11 from F. Poux's PCA + Random Forest video: batched eigenvalue features per cluster, forest vs rules against AHN class 6 (results/eigen_features.json) |
| B6 | Where can I get my own point cloud? | Added 2026-10-11 from F. Poux's beginner video: open sources (AHN, 3DBAG, OpenTopography, national portals, Open Heritage 3D, Sketchfab), photogrammetry vs LiDAR |

## Render spec (one spec for the whole deck)

- One fixed camera, pose stored in `render_spec.json`, never `reset_camera`. Local origin = `header.mins`, as in the slide 8 code.
- Frames: L7 1588×1792 px. Slide 3 4190×1792 px with the same camera and vertical field of view, so the L7 frame is its exact centre.
- Slide 4: same pose, narrow view angle. Slide 7: the same files, scaled down.
- Colours re-themed 2026-10-03 (`deck/content.yaml` `meta.render_palette`): background PyCon NL navy #1C325B.
  Eye-dome lighting off.
- Height ramp #2B6797 → #B1CAC5 → #FFFFFF with fixed limits on every frame.
- Classes, each a different grey level, labelled directly with native text:
  - ground #4A5F69
  - buildings light blue #6FA0CC
  - vegetation sage #B1CAC5
  - 4th class white
- Point size: 3 px for raw and painted-back frames, 6 px after voxel downsampling.
- No green or yellow anywhere else in the deck.
