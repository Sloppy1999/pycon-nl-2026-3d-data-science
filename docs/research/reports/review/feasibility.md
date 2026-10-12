FEASIBILITY REVIEW (all pipeline numbers are PROTOTYPE: one run on one crop, untuned, not benchmarks)
Work dir: scratchpad/review/feasibility/ (written as F/ below). Nothing was published, committed or pushed.

## 1. Venue facts
- PDOK Locatieserver gives "Jaarbeursplein 6, 3521AL" as RD **135784.464, 455538.933**. pyproj 3.8.0 in my own uv venv converts the PDOK and Nominatim lat/lon to 135784.46, 455538.93 and 135784.57, 455539.06, so the sources agree.
- The point is **inside AHN tile 135000_455000**.
- That address is a *nevenadres* (secondary address). The main address is Croeselaan 8. It sits in BAG building 0344100000077882 (built 1970), which OSM node 2711678285 names the **Beatrixgebouw**.
- **The talk room is "Polar"**, inside the Jaarbeurs exhibition and conference centre across Croeselaan (pycon-nl.org/practical-information). Where Polar sits inside the complex is UNVERIFIED. The hall complex is one BAG building, 0344100000021405, with a 108,370 m² footprint and a bbox of 135290–135790 × 454940–455423, so it cannot fit in a 200 m crop.
- **Crop C** has its centre at (135430, 455550).
  - It is **354.6 m from the address point** and 319.9 m from the Beatrix building.
  - It is **127 m from the hall building's edge**; the hall's north tip is at 135428.7, 455423.0.
  - The crop's south edge is **27 m from the hall**.
  - Graadt van Roggenweg runs along the hall's north-west side.
- **Candidate crops** (F/candidate_crops.json, F/previews/contact_sheet.png):

| Crop | bbox | Points | Class 1 / 2 / 6 / 26 | Tree proxy* | Verdict |
|---|---|---|---|---|---|
| **C (storyboard)** | 135330–135530 / 455450–455650 | 1,239,310 | 296,751 / 808,952 / 133,607 / 0 | **206,462** | **Keep** |
| V3 (whole Beatrix building + Croeselaan) | 135706–135906 / 455455–455655 | 731,772 | 111,305 / 260,050 / 352,538 / 7,879 | 48,905 | Reject |
| C3 (hall's north tip) | 135330–135530 / 455400–455600 | 1,242,320 | 241,624 / 813,617 / 187,079 / 0 | 151,292 | Fallback |

  *Tree proxy = class-1 points with multiple returns, more than 3 m above ground.
  - V3 contains the venue address building, but it has 4× fewer tree points, two tower cranes and a building under construction whose floor slabs are class 1. No crop is better than C.
  - C3 shows a featureless hall-roof triangle and a parking deck.

## 2. Prototype pipeline (F/proto_pipeline.py, F/render_states.py)
Environment: Ryzen 7 5700X, 16 threads, 31 GB RAM, Python 3.13.15, laspy 2.7.0, open3d 0.20.0, numpy 2.5.3, pyvista 0.49.0.

**Main run** (F/metrics_main.json):
- **Voxel downsampling:** 0.25 m keeps 774,947 points (62.5 %). 0.5 m keeps 316,342 (25.5 %).
- **Ground removal:** tiled RANSAC on 25 m tiles (64 tiles).
  - Each tile only considers points within 3 m of its 2nd-percentile height.
  - `segment_plane(0.2, 3, 300, probability=1.0)` after `o3d.utility.random.seed(0)`.
  - Ground band is −1.0 to +0.35 m around the plane.
- **Clustering:** DBSCAN with eps 0.75 and min_points 8 gives **1,400 clusters** and 25,265 noise voxels.
- **Score against AHN, point level:**
  - Ground vs class 2: **precision 0.989, recall 0.937**.
  - Buildings vs class 6: **precision 0.848, recall 0.976**.
- **Labelling:** 32 building, 918 vegetation, 167 "furniture" and 283 unlabelled clusters.
- **Time:** 3.4 s end to end, single run.

**Parameter sweep** (point-level precision/recall):
- **Tile size:**
  - 50 m / 16 tiles: ground 0.987/0.886, buildings 0.720/0.972
  - 12.5 m / 256 tiles: ground 0.986/0.960, buildings 0.818/0.973
- **Without the low-point pre-filter:** 8 of 64 tiles returned a tilted plane or one more than 2.5 m above the median ground (a roof). This is a real gotcha.
- **0.5 m voxels with eps 1.0:** every building fuses with its trees, and **building recall drops to 0.091**. With eps 0.75 it recovers to 0.815/0.913. Gotcha: eps has to scale with the voxel size.
- **Verified gotcha:** `voxel_down_sample` anchors its grid at min − v/2. `voxel_down_sample_and_trace` given min_bound returns a different count (779,126 vs 774,947). Passing `mn - v/2` makes the two identical.

**What I saw in the renders:**
- **The sequence reads as one continuous object.** The camera is identical in every frame (checked after rendering).
- **Frame 2 cannot be told apart from frame 1** at 0.25 m. A close-up does show the difference (F/renders/voxel_closeup_raw_025_050.png: 53,054 → 32,489 → 13,336 points).
- **Ground errors are visible.** Raised platforms about 0.4 m high (AHN class 2), a raised plaza and a ramp survive ground removal. The plaza and ramp are then labelled vegetation (green plates), and the parking-deck floors also turn partly green.
- **Trees mostly separate from buildings.** Only 1.0 % of vegetation points are AHN class 6, and the tree row beside the building stays green.
- **Street furniture is essentially absent** (F/furniture_audit.json, F/renders/furniture_map.png):
  - 62 pole-like clusters: **60 sit within 2 m of a building facade** (facade fragments). 2 stand free; both are fragments 3–4.4 m up.
  - 33 car-sized clusters: 16 stand free, mostly a row of parked cars on the west edge, about 2.4 × 4.1 m and 1.5 m high.
  - 72 "other small" clusters: 31 next to trees, 13 next to buildings, 28 free-standing.
  - Furniture is 4,841 voxels in total, 0.6 % of the scene.
- **Eye-dome lighting failed** (main_6_final_edl.png comes out dark and speckled). The sphere render (main_6_final_spheres.png) works but is almost identical to frame 5.
- **No people are visible**, which is consistent with the night flight.

**Four-class verdict:** "street furniture" is **not realistic on AHN5**. What the rule finds is cars plus facade noise, with at most 2 real poles. Rename the fourth class **"cars and small objects"** everywhere. This changes the abstract's wording, so the speaker has to decide.

**Camera** (crop-local metres: origin at RD (135330, 455450), z is NAP; view up already orthogonal after render):
- **L7 frame, 1588×1792:** position (17.61, −126.37, 350.04), focal point (100, 100, 6), view up (0, 0, 1), view angle 30°. That is azimuth 20° east of south, elevation 55°, distance 420 m. Point size 2 px.
- **Hook frame, 2400×1137 (recommended option B):** position (214.24, −144.99, 195.28), focal point (100, 100, 6), view up (0, 0, 1), view angle 30°.
- **Colours:**
  - Background #0E2841.
  - Ground #6B7280, buildings #F95759, vegetation #41AE49 (needs brand sign-off), small objects #FFCE2C, unlabelled #3A4A66.
  - Height ramp #5F7BDB → #B6C4F2 → #F1F1F2 → #FFCE2C over 0–30 m.
- **Grayscale:** luma is 136 for coral, 130 for green and 114 for ground, so they collapse in grayscale. Direct labels are mandatory. F/renders_main.json has label anchor pixels.

## 3. Storyboard fixes
- **Slide 3**
  - Problem: "street outside this building" is false (355 m from the address, and Polar's position is unknown). "Raw" is also wrong, because AHN arrives already classified.
  - Title: **"One street beside Jaarbeurs, scanned from the air"**.
  - Support line: **"AHN's labels removed, rebuilt in Python, scored against AHN."**
  - Visual: F/renders/main_hookB_az-25_el35_D330_split.png. Replace the "you are here" pin with an arrow on the bottom edge reading "Jaarbeurs halls, 30 m".
  - Time: 80 s.
- **Slide 7**
  - Problem: six steps, but frame 2 looks the same as frame 1 and frame 6 the same as frame 5.
  - Title: **"Five steps from raw scan to labels"**.
  - Visual: 5 thumbnails (states 1–5).
  - Time: 45 s.
- **Slide 9**
  - Problem: no visible change in the fixed frame.
  - Keep the Morph frame and add a 3-panel close-up strip (raw | 0.25 m | 0.5 m).
  - Hero number: **1,239,310 → 774,947 points**.
  - Time: 55 s.
- **Slide 10**
  - Problem: "[16]" tiles is the weakest option.
  - Code: 64 tiles of 25 m.
  - Support line: **"Scored against AHN ground: [98.9] % precision, [93.7] % recall."** Keep the brackets until the final run.
  - Notes: the roof-capture gotcha (8 of 64 tiles).
  - Time: 95 s (+25).
- **Slide 11**
  - Hero number: **[1,400] clusters**.
  - Code: `cluster_dbscan(eps=0.75, min_points=8)`.
  - Notes: the eps-scales-with-voxel gotcha (recall 0.091).
  - Time: 55 s.
- **Slide 12**
  - Title: **"5 Labelling: four rules, four classes"**.
  - Support line: **"Pulses slip through bare branches, so trees echo several times."** The flight was leaf-off, so "leaves" is wrong.
  - Legend: ground · buildings · trees · cars and small objects.
  - Visual: main_6_final_spheres.png.
  - Time: 95 s (+25).
- **Slide 13**
  - Delete it as a pipeline step: EDL failed and the sphere render duplicates slide 12.
  - Move the camera code (`Plotter(off_screen=True)`, `camera_position`, `screenshot`) to slide 14 and add "renders: PyVista" to the source line.
  - Time: 0 s (−50).
- **Slide 14**
  - Hero number (optional): **[3.4 s] end to end on 1.24 M points**. It needs a proper repeated run before it goes on a slide.
- **Terminology line (storyboard header):** change "street furniture" to "cars and small objects". The terminology list also has an extra term, "labelling", that the brief does not ask for.
- **Timing:** the total stays at 1800 s. The skip-first list should replace 13 with 9.

## 4. Files
- **Scripts:** F/proto_pipeline.py, F/render_states.py, F/extra_renders.py, F/furniture_audit.py, F/candidate_crops.py, F/distances.py, F/venue_rd.py
- **Metrics:** F/feasibility_summary.json (everything combined), F/metrics_*.json, F/venue_facts.json, F/candidate_crops.json
- **Renders, L7 frames (F/renders/):** main_1_load_raw.png, main_2_voxel.png, main_3_ground.png, main_4_clusters.png, main_5_labels.png, main_6_final_spheres.png, main_6_final_edl.png (rejected)
- **Renders, hook (F/renders/):** main_hookB_az-25_el35_D330_split.png (recommended), main_hookA_az20_el35_D330_split.png, main_hook_split_2400x1137.png
- **Diagnostics:** F/renders/voxel_closeup_raw_025_050.png, F/renders/furniture_map.png, F/venue_area_map.png