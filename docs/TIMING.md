# Timing

The talk is planned for **1575 s (26:15)**: the 33 `seconds` values in `deck/content.yaml`, the same in
`deck/notes.yaml`, whose `ends_at` gives the running clock. The brief's slot is 10:45 to 11:25 (40 minutes including
Q&A and changeover; whether Q&A is included is not confirmed yet, OPEN_ITEMS d1); the 3:45 under 30:00 is buffer. The backup slides B1 to B14 are hidden and carry no time.

## 2026-10-14 (restructure 2): 33 slides, 1575 s, Memory before Speed

Thesis: in Python you write the plan and compiled code does the work, so four rules take a city scan from unnamed x, y, z
to a checked class per point. Acts: Hook and context (Intro, Data, Toolbox) · Build (Pipeline, then does it fit, is it
fast) · Reality check and take-home (is it right, rules, limits, close). Per chapter: Intro 180 s · Data 180 s · Toolbox
100 s · Pipeline 460 s · Memory 115 s · Speed 300 s · Reality 75 s · Wrap-up 165 s. New: problem (3), agenda table (5,
replaces the roadmap), scope and assumptions (9); the plane (6) now comes before the data set (7) and has a swath inset;
the rules (10) open Toolbox; Memory moved before Speed so the rule badges run 1, 2, 3, 4; rule badges dropped on
clustering, paint-back and the summary. Trims: rules 40 to 30, views 60 to 45 (two rows on screen), logo wall 45 to 35,
toll 85 to 70, sampling 40 to 30, data set 50 to 45. Old to new: 1, 2 same; 3 to 4; 4 to 10; 5 to 5; 6 to 7; 7 to 6;
8 same; 9 to 19 to 11 to 21; 20 to 24 to 24 to 28; 25, 26 to 22, 23; 27 to 31 to 29 to 33. Skip-first order: 28, 27,
22, 20, 15.

| Slide | Title | Chapter | Seconds | Starts | Ends |
|---|---|---|---|---|---|
| 1 | 3D Data Science with Python | Intro | 20 | 0:00 | 0:20 |
| 2 | 3D meant C++; now Python drives it | Intro | 35 | 0:20 | 0:55 |
| 3 | A city scan: millions of points, no names | Intro | 45 | 0:55 | 1:40 |
| 4 | The goal: name every point, then check it | Intro | 40 | 1:40 | 2:20 |
| 5 | Eight chapters, three questions | Intro | 40 | 2:20 | 3:00 |
| 6 | A plane sweeps a strip with a laser | Data | 55 | 3:00 | 3:55 |
| 7 | Today's case: the block around the Jaarbeurs | Data | 45 | 3:55 | 4:40 |
| 8 | One object, three representations | Data | 40 | 4:40 | 5:20 |
| 9 | What this talk does, and doesn't | Data | 40 | 5:20 | 6:00 |
| 10 | Four rules this talk will prove | Toolbox | 30 | 6:00 | 6:30 |
| 11 | Python already has a library for every layer | Toolbox | 35 | 6:30 | 7:05 |
| 12 | Python plans; compiled code does the work | Toolbox | 35 | 7:05 | 7:40 |
| 13 | Six steps: from LAZ file to labels | Pipeline | 40 | 7:40 | 8:20 |
| 14 | 1 Load: subtract a local origin first | Pipeline | 55 | 8:20 | 9:15 |
| 15 | 1 Load: pass views, not copies | Pipeline | 45 | 9:15 | 10:00 |
| 16 | 2 Voxel downsampling: one average per voxel | Pipeline | 50 | 10:00 | 10:50 |
| 17 | 3 Ground removal: one plane per tile | Pipeline | 70 | 10:50 | 12:00 |
| 18 | 4 Clustering: DBSCAN groups points that touch | Pipeline | 50 | 12:00 | 12:50 |
| 19 | 5 Labelling: the first rule that fires wins | Pipeline | 65 | 12:50 | 13:55 |
| 20 | 6 Paint-back: every point takes its voxel's label | Pipeline | 35 | 13:55 | 14:30 |
| 21 | Six steps label every point in {pipeline.runtime_s|f1} s | Pipeline | 50 | 14:30 | 15:20 |
| 22 | A full AHN sheet would need {memory.big_file.computed_gb.our_pipeline|gb} | Memory | 55 | 15:20 | 16:15 |
| 23 | Stream chunks, keep the first point per voxel | Memory | 60 | 16:15 | 17:15 |
| 24 | Quiz: which is faster, and by how much? | Speed | 60 | 17:15 | 18:15 |
| 25 | How much slower is the loop over rows? | Speed | 70 | 18:15 | 19:25 |
| 26 | Every trip into compiled code pays a toll | Speed | 70 | 19:25 | 20:35 |
| 27 | Profile before you vectorise | Speed | 50 | 20:35 | 21:25 |
| 28 | Will free-threaded Python save my loop? | Speed | 50 | 21:25 | 22:15 |
| 29 | The register has {bgt.collections.paal.n|int} poles; we found {pipeline.n_objects.street_furniture|int} | Reality | 45 | 22:15 | 23:00 |
| 30 | From the air, the city is sampled unevenly | Reality | 30 | 23:00 | 23:30 |
| 31 | Four rules, each backed by this talk's numbers | Wrap-up | 75 | 23:30 | 24:45 |
| 32 | What this doesn't do yet, and what's next | Wrap-up | 45 | 24:45 | 25:30 |
| 33 | Thank you | Wrap-up | 45 | 25:30 | 26:15 |
| | **Total** | | **1575** | | **26:15** |

## 2026-10-14 (Phase 3 restructure): 31 slides, 1545 s, three acts

Thesis: in Python you write the plan and compiled code does the work, so four rules take a city scan from LAZ to a
label per point, fast, within memory and honestly. Acts: Why (Intro, Data, Toolbox) · Build (Pipeline, then two
questions: is it fast, does it fit) · Reality check and take-home (is it right, rules, limits, close). Per chapter:
Intro 170 s · Data 140 s · Toolbox 80 s · Pipeline 475 s · Speed 315 s · Memory 115 s · Reality 85 s · Wrap-up 165 s. Changes: roadmap slide 5 (new, 25 s), the lifecycle ring cut to hidden backup B8 (60 s), slide 4 from 50 to 40 s,
Reality moved after Memory (the twist), limits and next steps slide 30 (new, 45 s). The rules are renumbered in the
order the talk first proves them (1 arrays, 2 small first, 3 compiled loop, 4 look before you compute). Old to new:
1 to 4 same; 5, 6, 7 to 6, 7, 8; 8 to B8; 9 to 19 same; 22 to 26 to 20 to 24; 27, 28 to 25, 26; 20, 21 to 27, 28;
29 same; 30 to 31. Skip-first order: 24, 23, 25, 18, 13 (the slide 19 checkpoint covers 24, 23 and 25).

| Slide | Title | Chapter | Seconds | Starts | Ends | wpm |
|---|---|---|---|---|---|---|
| 1 | 3D Data Science with Python | Intro | 20 | 0:00 | 0:20 | 126 |
| 2 | 3D meant C++; now Python drives it | Intro | 35 | 0:20 | 0:55 | 153 |
| 3 | The goal: give every point a name | Intro | 50 | 0:55 | 1:45 | 143 |
| 4 | Four rules this talk will prove | Intro | 40 | 1:45 | 2:25 | 206 |
| 5 | One city block, six steps, three questions | Intro | 25 | 2:25 | 2:50 | 113 |
| 6 | Today's case: the Jaarbeurs hall, from a plane | Data | 50 | 2:50 | 3:40 | 116 |
| 7 | A plane scans the city with a laser | Data | 50 | 3:40 | 4:30 | 140 |
| 8 | One object, three representations | Data | 40 | 4:30 | 5:10 | 136 |
| 9 | Python already has a library for every layer | Toolbox | 45 | 5:10 | 5:55 | 115 |
| 10 | Python plans; compiled code does the work | Toolbox | 35 | 5:55 | 6:30 | 130 |
| 11 | Six steps: from LAZ file to labels | Pipeline | 40 | 6:30 | 7:10 | 86 |
| 12 | 1 Load: subtract a local origin first | Pipeline | 55 | 7:10 | 8:05 | 91 |
| 13 | 1 Load: pass views, not copies | Pipeline | 60 | 8:05 | 9:05 | 151 |
| 14 | 2 Voxel downsampling: one average per voxel | Pipeline | 50 | 9:05 | 9:55 | 110 |
| 15 | 3 Ground removal: one plane per tile | Pipeline | 70 | 9:55 | 11:05 | 93 |
| 16 | 4 Clustering: DBSCAN groups points that touch | Pipeline | 50 | 11:05 | 11:55 | 95 |
| 17 | 5 Labelling: the first rule that fires wins | Pipeline | 65 | 11:55 | 13:00 | 154 |
| 18 | 6 Paint-back: every point takes its voxel's label | Pipeline | 35 | 13:00 | 13:35 | 108 |
| 19 | Six steps label every point in 0.6 s | Pipeline | 50 | 13:35 | 14:25 | 120 |
| 20 | Quiz: which is faster, and by how much? | Speed | 60 | 14:25 | 15:25 | 69 |
| 21 | How much slower is the loop over rows? | Speed | 70 | 15:25 | 16:35 | 76 |
| 22 | Every trip into compiled code pays a toll | Speed | 85 | 16:35 | 18:00 | 91 |
| 23 | Profile before you vectorise | Speed | 50 | 18:00 | 18:50 | 122 |
| 24 | Will free-threaded Python save my loop? | Speed | 50 | 18:50 | 19:40 | 108 |
| 25 | A full AHN sheet would need 74.2 GB | Memory | 55 | 19:40 | 20:35 | 77 |
| 26 | Stream chunks, keep the first point per voxel | Memory | 60 | 20:35 | 21:35 | 128 |
| 27 | The register has 61 poles; we found 3 | Reality | 45 | 21:35 | 22:20 | 153 |
| 28 | From the air, the city is sampled unevenly | Reality | 40 | 22:20 | 23:00 | 134 |
| 29 | Four rules, each backed by this talk's numbers | Wrap-up | 75 | 23:00 | 24:15 | 78 |
| 30 | What this doesn't do yet, and what's next | Wrap-up | 45 | 24:15 | 25:00 | 112 |
| 31 | Thank you | Wrap-up | 45 | 25:00 | 25:45 | 101 |
| | **Total** | | **1545** | | **25:45** | |


## 2026-10-13 (restructure): 30 slides, 1545 s, the four rules as the spine

Restructure review, same day: no slide added, removed or moved, so every time below holds. Slide 29's four click
builds take no extra time (the talk track already walks the rules one by one). Titles 12 and 13 changed (below).

Narrative arc: Hook (1 to 4, the rules as the talk's promise) · Data (5 to 8) · Toolbox (9, 10) · Pipeline (11 to
19) · Reality (20, 21) · Speed (22 to 26) · Memory (27, 28) · Rules (29) · Close (30). Removed: Agenda (its parts are
now `meta.chapters`, the footer breadcrumb) and Scope ("Not today" is in the slide 3 notes); "No single library does the
whole job" (the filmstrip on slide 11 carries the library per step). Moved: the rules to slide 4, the case before the
plane, the ecosystem wall and the C++ meme into Toolbox, "Use views, not copies" right after Load. Restored from
5ccb438: "Stream chunks, keep the first point per voxel" (28). Slide 8 cut from 145 to 60 s. Slides that are evidence
for a rule carry a rule badge top right (number disc + rule); slides 12 to 18 a step tracker. Skip-first order: 26, 25, 27, 18, 13 (the slide 19 checkpoint covers 26,
25 and 27).

| Slide | Title | Section | Seconds | Starts | Ends | wpm |
|---|---|---|---|---|---|---|
| 1 | 3D Data Science with Python | Hook | 20 | 0:00 | 0:20 | 126 |
| 2 | 3D used to mean C++. Not anymore | Hook | 35 | 0:20 | 0:55 | 153 |
| 3 | The goal: give every point a name | Hook | 50 | 0:55 | 1:45 | 143 |
| 4 | Four rules this talk will prove | Hook | 50 | 1:45 | 2:35 | 154 |
| 5 | Today's case: the Jaarbeurs hall, from a plane | Data | 50 | 2:35 | 3:25 | 116 |
| 6 | A plane scans the city with a laser | Data | 50 | 3:25 | 4:15 | 140 |
| 7 | One object, three representations | Data | 40 | 4:15 | 4:55 | 141 |
| 8 | Where today's pipeline sits in a 3D project | Data | 60 | 4:55 | 5:55 | 89 |
| 9 | Python already has a library for every layer | Toolbox | 45 | 5:55 | 6:40 | 115 |
| 10 | Python is the interface. C++ does the work | Toolbox | 35 | 6:40 | 7:15 | 130 |
| 11 | Six steps turn a point cloud into labels | Pipeline | 40 | 7:15 | 7:55 | 86 |
| 12 | 1 Load: subtract a local origin first | Pipeline | 55 | 7:55 | 8:50 | 91 |
| 13 | 1 Load: use views, not copies | Pipeline | 60 | 8:50 | 9:50 | 141 |
| 14 | 2 Voxel downsampling: one average per voxel | Pipeline | 50 | 9:50 | 10:40 | 102 |
| 15 | 3 Ground removal: one plane per tile | Pipeline | 70 | 10:40 | 11:50 | 93 |
| 16 | 4 Clustering: DBSCAN groups what touches | Pipeline | 50 | 11:50 | 12:40 | 83 |
| 17 | 5 Labelling: rules name the clusters | Pipeline | 65 | 12:40 | 13:45 | 136 |
| 18 | 6 Visualisation: PyVista paints every point | Pipeline | 35 | 13:45 | 14:20 | 96 |
| 19 | Six steps label every point in {pipeline.runtime_s|f1} s | Pipeline | 50 | 14:20 | 15:10 | 97 |
| 20 | The map has {bgt.collections.paal.n|int} poles; we found {pipeline.n_objects.street_furniture|int} | Reality | 45 | 15:10 | 15:55 | 144 |
| 21 | A point cloud samples the surface unevenly | Reality | 40 | 15:55 | 16:35 | 134 |
| 22 | Quiz: which is faster, and by how much? | Speed | 60 | 16:35 | 17:35 | 69 |
| 23 | How much slower is the loop over rows? | Speed | 70 | 17:35 | 18:45 | 74 |
| 24 | Every trip into compiled code pays a toll | Speed | 85 | 18:45 | 20:10 | 91 |
| 25 | Profile before you vectorise | Speed | 50 | 20:10 | 21:00 | 122 |
| 26 | Will free-threaded Python save my loop? | Speed | 50 | 21:00 | 21:50 | 78 |
| 27 | Loading this area's AHN file outgrows {memory.ram_reference_gb.1|int} GB | Memory | 55 | 21:50 | 22:45 | 75 |
| 28 | Stream chunks, keep the first point per voxel | Memory | 60 | 22:45 | 23:45 | 113 |
| 29 | Four rules, each backed by this talk's numbers | Rules | 75 | 23:45 | 25:00 | 62 |
| 30 | Thank you | Close | 45 | 25:00 | 25:45 | 81 |
| | **Total** | | **1545** | | **25:45** | |

## 2026-10-13: agenda, scope, goal and data capture: agenda, scope, goal and data capture (32 slides, 1750 s)

Four slides after the ecosystem wall: 5 Agenda (35 s), 6 Scope (45 s), 7 Goal (45 s), 8 how a plane captures the
points (55 s); slide 9, the Jaarbeurs case, gave 15 s (65 to 50 s) because the plane is now on slide 8. Every later
slide moved by four. Skip-first order: 29, 28, 30, 21, 14 (the slide 22 checkpoint covers 29, 28 and 30).

| Slide | Title | Section | Seconds | Starts | Ends | wpm |
|---|---|---|---|---|---|---|
| 1 | 3D Data Science with Python | Hook | 20 | 0:00 | 0:20 | 126 |
| 2 | 3D used to mean C++. Not anymore | Hook | 35 | 0:20 | 0:55 | 153 |
| 3 | Python is the interface. C++ does the work | Hook | 30 | 0:55 | 1:25 | 126 |
| 4 | Python already has a library for every layer | Hook | 30 | 1:25 | 1:55 | 160 |
| 5 | Agenda | Intro | 35 | 1:55 | 2:30 | 132 |
| 6 | Scope: what to expect, and what not | Intro | 45 | 2:30 | 3:15 | 136 |
| 7 | The goal: give every point a name | Intro | 45 | 3:15 | 4:00 | 128 |
| 8 | A plane scans the city with a laser | Intro | 55 | 4:00 | 4:55 | 120 |
| 9 | Today's case: the Jaarbeurs hall, from a plane | Hook | 50 | 4:55 | 5:45 | 115 |
| 10 | One object, three representations | Hook | 40 | 5:45 | 6:25 | 124 |
| 11 | A 3D project moves through six stages | Hook | 145 | 6:25 | 8:50 | 84 |
| 12 | Four rules of thumb for 3D data | Hook | 45 | 8:50 | 9:35 | 137 |
| 13 | No single library does the whole job | Landscape | 55 | 9:35 | 10:30 | 80 |
| 14 | Use views, not copies | Landscape | 70 | 10:30 | 11:40 | 116 |
| 15 | Six steps turn a point cloud into labels | Pipeline | 25 | 11:40 | 12:05 | 103 |
| 16 | 1 Load: laspy hands you NumPy | Pipeline | 65 | 12:05 | 13:10 | 73 |
| 17 | 2 Voxel downsampling: one average per voxel | Pipeline | 55 | 13:10 | 14:05 | 93 |
| 18 | 3 Ground removal: one plane per tile | Pipeline | 75 | 14:05 | 15:20 | 87 |
| 19 | 4 Clustering: DBSCAN groups what touches | Pipeline | 55 | 15:20 | 16:15 | 75 |
| 20 | 5 Labelling: rules name the clusters | Pipeline | 70 | 16:15 | 17:25 | 126 |
| 21 | 6 Visualisation: PyVista paints every point | Pipeline | 40 | 17:25 | 18:05 | 84 |
| 22 | Six steps label every point in {pipeline.runtime_s|f1} s | Pipeline | 65 | 18:05 | 19:10 | 70 |
| 23 | The map has {bgt.collections.paal.n|int} poles; we found {pipeline.n_objects.street_furniture|int} | Pipeline | 40 | 19:10 | 19:50 | 162 |
| 24 | A point cloud samples the surface unevenly | Pipeline | 40 | 19:50 | 20:30 | 120 |
| 25 | Quiz: which is faster, and by how much? | Performance | 75 | 20:30 | 21:45 | 55 |
| 26 | How much slower is the loop over rows? | Performance | 80 | 21:45 | 23:05 | 64 |
| 27 | Every trip into compiled code pays a toll | Performance | 95 | 23:05 | 24:40 | 81 |
| 28 | Profile before you vectorise | Performance | 55 | 24:40 | 25:35 | 111 |
| 29 | Will free-threaded Python save my loop? | Performance | 50 | 25:35 | 26:25 | 78 |
| 30 | Loading this area's AHN file outgrows {memory.ram_reference_gb.1|int} GB | RAM | 55 | 26:25 | 27:20 | 75 |
| 31 | Four rules, each backed by this talk's numbers | Close | 60 | 27:20 | 28:20 | 77 |
| 32 | Thank you | Close | 50 | 28:20 | 29:10 | 73 |
| | **Total** | | **1750** | | **29:10** | **98** |

## 2026-10-13 (later): 28 slides, 1585 s, Morph dropped

The stream-chunks, memory-over-time and gotchas slides are gone and every slide is a fade (no Morph chain), so the
Morph caveats in the older sections below no longer apply. The talk is 26:25 on purpose, not 30:00. Skip-first order:
25, 24, 26, 17, 10 (the slide 18 checkpoint covers 25, 24 and 26). The table is generated from `deck/notes.yaml`
(wpm is the spoken talk track at the planned seconds).

| Slide | Title | Section | Seconds | Starts | Ends | wpm |
|---|---|---|---|---|---|---|
| 1 | 3D Data Science with Python | Hook | 20 | 0:00 | 0:20 | 126 |
| 2 | 3D used to mean C++. Not anymore | Hook | 35 | 0:20 | 0:55 | 153 |
| 3 | Python is the interface. C++ does the work | Hook | 30 | 0:55 | 1:25 | 126 |
| 4 | The Python 3D ecosystem | Hook | 30 | 1:25 | 1:55 | 160 |
| 5 | Today's case: the Jaarbeurs hall, from a plane | Hook | 65 | 1:55 | 3:00 | 113 |
| 6 | One object, three representations | Hook | 40 | 3:00 | 3:40 | 124 |
| 7 | A 3D project moves through six stages | Hook | 145 | 3:40 | 6:05 | 84 |
| 8 | Four rules of thumb for 3D data | Hook | 45 | 6:05 | 6:50 | 137 |
| 9 | No single library does the whole job | Landscape | 55 | 6:50 | 7:45 | 80 |
| 10 | Use views, not copies | Landscape | 70 | 7:45 | 8:55 | 116 |
| 11 | Six steps turn a point cloud into labels | Pipeline | 25 | 8:55 | 9:20 | 103 |
| 12 | 1 Load: laspy hands you NumPy | Pipeline | 65 | 9:20 | 10:25 | 73 |
| 13 | 2 Voxel downsampling: one average per voxel | Pipeline | 55 | 10:25 | 11:20 | 93 |
| 14 | 3 Ground removal: one plane per tile | Pipeline | 75 | 11:20 | 12:35 | 87 |
| 15 | 4 Clustering: DBSCAN groups what touches | Pipeline | 55 | 12:35 | 13:30 | 75 |
| 16 | 5 Labelling: rules name the clusters | Pipeline | 70 | 13:30 | 14:40 | 126 |
| 17 | 6 Visualisation: PyVista paints every point | Pipeline | 40 | 14:40 | 15:20 | 84 |
| 18 | What the six steps did | Pipeline | 65 | 15:20 | 16:25 | 70 |
| 19 | Expectation vs reality: street furniture | Pipeline | 40 | 16:25 | 17:05 | 162 |
| 20 | A point cloud samples the surface unevenly | Pipeline | 40 | 17:05 | 17:45 | 120 |
| 21 | Quiz: which is faster, and by how much? | Performance | 75 | 17:45 | 19:00 | 55 |
| 22 | How much slower is the loop over rows? | Performance | 80 | 19:00 | 20:20 | 64 |
| 23 | Every trip into compiled code pays a toll | Performance | 95 | 20:20 | 21:55 | 81 |
| 24 | Profile before you vectorise | Performance | 55 | 21:55 | 22:50 | 111 |
| 25 | Will free-threaded Python save my loop? | Performance | 50 | 22:50 | 23:40 | 78 |
| 26 | Loading this area's AHN file outgrows {memory.ram_reference_gb.1|int} GB | RAM | 55 | 23:40 | 24:35 | 75 |
| 27 | Take the four rules home | Close | 60 | 24:35 | 25:35 | 77 |
| 28 | Thank you | Close | 50 | 25:35 | 26:25 | 73 |
| | **Total** | | **1585** | | **26:25** | **95** |

## 2026-10-13: workflow ring replaces the trade-offs and chain slides (31 slides, still 1800 s)

Slide 7 is now the six-stage workflow ring (Acquisition to Application, with loops back), with the tools of the old
chain slide (laspy, NumPy, Open3D, SciPy, PyVista) under their stage and three pipeline renders beside them. The old
slide 10 (laspy loads, Open3D computes, PyVista draws) is gone and its 80 s went to slide 7 (65 to 145 s), so every
`ends_at` from slide 9 on is unchanged; slides 11 and later moved down by one (old 11 is now 10, B-slides unchanged).
The tables below are older snapshots with the previous numbering.

## 2026-10-12 (later): the meme slide (32 slides, still 1800 s)

A new slide 3, the Python-and-C++ unmasking meme (30 s), follows the code comparison (now slide 2): the code slide says
the C++ is still there underneath, the meme and its bullets show where (NumPy's C core, Open3D and VTK in C++, laspy's
Rust decoder). Every slide from the old 3 on moved by one. The 30 s came from the old slide 4 (the Jaarbeurs case, now
slide 5, 95 to 65 s; its talk track was the slowest at 77 wpm, 113 wpm now), so the clock at the end of slide 5 is still
3:00 and every later `ends_at`, checkpoint and skip target is unchanged. The skip-first list is now 26, 25, 27, 18, 11.
The table below is regenerated from `deck/notes.yaml`; the tables further down are older snapshots with the previous
numbering.

## 2026-10-12: mental-model slides join the main deck (31 slides, still 1800 s)

"One object, three representations" (C1, now slide 6) and "A point cloud samples the surface unevenly" (C5, now slide
20) moved from the hidden section into the main deck, 40 s each. Later the former slide 5 (the N×3 array close-up, 65 s) was removed and a benefits-and-limits slide of the three representations (new slide 6, 65 s) added after C1, which became slide 5; slides 7 and later kept their numbers. The 80 s came from the slowest talk tracks: slide 5
(80 to 65 s), slide 18 (75 to 65 s), slide 21 (90 to 75 s), slide 22 (105 to 80 s) and slide 29 (100 to 85 s). Every
slide after 5 moved by one, every slide after 19 by two; the skip-first list and the checkpoints in the notes use the new
numbers. The table below is generated from `deck/notes.yaml` (words are the spoken talk track, wpm at the planned
seconds). The older tables further down are the 2026-10-04 snapshot with the old numbering and are kept as history.

| Slide | Title | Section | Seconds | Starts | Ends | wpm |
|---|---|---|---|---|---|---|
| 1 | 3D Data Science with Python | Hook | 20 | 0:00 | 0:20 | 126 |
| 2 | 3D used to mean C++. Not anymore | Hook | 35 | 0:20 | 0:55 | 153 |
| 3 | Python is the interface. C++ does the work | Hook | 30 | 0:55 | 1:25 | 126 |
| 4 | The Python 3D ecosystem | Hook | 30 | 1:25 | 1:55 | 160 |
| 5 | Today's case: the Jaarbeurs hall, from a plane | Hook | 65 | 1:55 | 3:00 | 113 |
| 6 | One object, three representations | Hook | 40 | 3:00 | 3:40 | 124 |
| 7 | A 3D project moves through six stages | Hook | 65 | 3:40 | 4:45 | 96 |
| 8 | Four rules of thumb for 3D data | Hook | 45 | 4:45 | 5:30 | 137 |
| 9 | No single library does the whole job | Landscape | 55 | 5:30 | 6:25 | 89 |
| 10 | laspy loads, Open3D computes, PyVista draws | Landscape | 80 | 6:25 | 7:45 | 83 |
| 11 | Python passes the array, not the points | Landscape | 70 | 7:45 | 8:55 | 116 |
| 12 | Six steps turn a point cloud into labels | Pipeline | 25 | 8:55 | 9:20 | 103 |
| 13 | 1 Load: laspy hands you NumPy | Pipeline | 65 | 9:20 | 10:25 | 73 |
| 14 | 2 Voxel downsampling: one average per voxel | Pipeline | 55 | 10:25 | 11:20 | 93 |
| 15 | 3 Ground removal: one plane per tile | Pipeline | 75 | 11:20 | 12:35 | 87 |
| 16 | 4 Clustering: DBSCAN groups what touches | Pipeline | 55 | 12:35 | 13:30 | 75 |
| 17 | 5 Labelling: rules name the clusters | Pipeline | 70 | 13:30 | 14:40 | 126 |
| 18 | 6 Visualisation: PyVista paints every point | Pipeline | 40 | 14:40 | 15:20 | 84 |
| 19 | What the six steps did | Pipeline | 65 | 15:20 | 16:25 | 70 |
| 20 | Expectation vs reality: street furniture | Pipeline | 40 | 16:25 | 17:05 | 162 |
| 21 | A point cloud samples the surface unevenly | Pipeline | 40 | 17:05 | 17:45 | 120 |
| 22 | Quiz: which is faster, and by how much? | Performance | 75 | 17:45 | 19:00 | 55 |
| 23 | How much slower is the loop over rows? | Performance | 80 | 19:00 | 20:20 | 64 |
| 24 | Every trip into compiled code pays a toll | Performance | 95 | 20:20 | 21:55 | 81 |
| 25 | Profile before you vectorise | Performance | 55 | 21:55 | 22:50 | 111 |
| 26 | Will free-threaded Python save my loop? | Performance | 50 | 22:50 | 23:40 | 78 |
| 27 | Loading this area's AHN file outgrows {memory.ram_reference_gb.1|int} GB | RAM | 55 | 23:40 | 24:35 | 75 |
| 28 | Stream chunks, keep the first point per voxel | RAM | 75 | 24:35 | 25:50 | 82 |
| 29 | Why it works: memory over time | RAM | 55 | 25:50 | 26:45 | 125 |
| 30 | Six gotchas I hit building this | Close | 85 | 26:45 | 28:10 | 73 |
| 31 | Take the four rules home | Close | 60 | 28:10 | 29:10 | 77 |
| 32 | Copy the pipeline | Close | 50 | 29:10 | 30:00 | 77 |
| | **Total** | | **1800** | | **30:00** | **92** |

| Section | Slides | Seconds |
|---|---|---|
| Hook | 1 to 7 | 330 s |
| Landscape | 8 to 10 | 205 s |
| Pipeline | 11 to 20 | 530 s |
| Performance | 21 to 25 | 355 s |
| RAM | 26 to 28 | 185 s |
| Close | 29 to 31 | 195 s |

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
| 3 | The Python 3D ecosystem | Hook | 30 | 0:45 | 1:15 |  |  | 67 | 134 |
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

If time runs short, cut in this order (each slide's notes carry "Skip-first number N" and the line to say instead;
updated 2026-10-14 for the 31-slide order):

| Order | Slide | Saves | Decide |
|---|---|---|---|
| 1 | 24 free-threaded | 50 s | at the slide 19 checkpoint (leaving after 17:45) |
| 2 | 23 profile | 50 s | at the slide 19 checkpoint (leaving after 17:45) |
| 3 | 25 the full AHN sheet | 55 s | at the slide 19 checkpoint (after 19:25), or on arriving at 25 after 22:50 |
| 4 | 18 paint-back | 35 s | at the end of slide 17, only if already late |
| 5 | 13 views, not copies | 60 s | at the end of slide 12, only if already late |

## Checkpoints (presenter view only, never spoken)

| Where | Talk clock | Action |
|---|---|---|
| Leaving slide 19 | by 14:25 | on time: carry on |
| Leaving slide 19 | after 17:45 | skip 24 and 23 |
| Leaving slide 19 | after 19:25 | also skip 25 |
| Arriving at slide 25 | by 22:50 | later than that: skip slide 25 |
| End of slide 31 | 25:45 | Q&A; slide 31 stays up with the QR code; backups B1 to B8 and C2 to C9 are hidden |

Source: `deck/notes.yaml` (slide 19 and 25 `checkpoint`, `skip` on 13, 18, 23, 24, 25).
