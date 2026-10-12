# Completeness critic report: storyboard research round

I re-ran checks only where they affect the storyboard. My scripts are in `scratchpad/critic/`: `v_unique.py`, `v_snippet.py`, `v_density.py` and `v_pipeline.py`. A few other checks (Vector3dVector, CopcReader, voxel centroid, DBSCAN, PyPI) ran inline and were not saved. The project directory was only read, and no git commands were run.

## 1. Contradictions between reports

| # | Topic | Report A | Report B | Resolution |
|---|---|---|---|---|
| C1 | AHN4 licence | book: "CC-BY 4.0" (via GeoTiles, ch5) | dataset: CC0 1.0 | **Dataset is right.** I re-fetched basisdata.nl/hwh-ahn/AUX/bladwijzer: "AHN1/2/3/4, CC0 1.0 … AHN5/6, Creative Commons Naamsvermelding 4.0". The book's statement is secondary and wrong for AHN4. |
| C2 | Size of the performance cliff | libraries: "71×" (loop vs one call) and "~2200×" | perf: about 5× for KD-tree queries, 40× with all cores, 79× for arithmetic | libraries' 71× compares a loop with k=2 against `workers=-1` (16 threads), so it mixes the boundary cost with parallelism. The 2202× compares an O(N²) brute force with a tree, i.e. it changes the algorithm (see `libraries/05_scipy_kdtree.py`). **Neither may be presented as the cost of crossing the boundary.** I re-measured on real AHN5 data: kNN k=16 over 20k points, loop vs one single-thread call is **5.4×**, and vs `workers=-1` it is **21×**. This confirms perf's framing. |
| C3 | How much a voxel step removes | memory: 0.1 m keeps 14.3 % | real AHN5 (my run): 0.1 m keeps **93 %** of the crop and **95.5 %** of the tile | memory's synthetic scene is street-level (MLS) density, about 1e5 pts per metre of street. AHN5 is aerial at 21 pts/m². On the crop: 0.25 m keeps 62.9 %, **0.5 m keeps 25.6 %**, 1.0 m keeps 8.1 %. All of memory's "% kept" and "km per GiB" figures are wrong for AHN. |
| C4 | Is chunked downsampling's memory bounded? | memory: peak 0.25–0.41 GiB at 30M points | real tile (my run) | The snippet is correct on the AHN5 COPC tile: 22 chunks, 4.3 s, survivors 1.02× the final count. But peak RSS is **1586 MiB**, because the output is almost the whole input at 0.1 m. The "bounded peak" story only holds at 0.5 m or larger. |
| C5 | Neighbourhood radius | perf: r=0.25 m gives about 18 neighbours | AHN5 crop | On the crop, r=0.25 m gives a mean of **4.7** neighbours, r=0.5 m gives 18.7, r=1.0 m gives 73.9. Real-data benchmarks should use **r ≈ 0.5 m** to match perf's working point. |
| C6 | Point record size and colour | memory: PDRF 7 (36 B, RGB); "colours grow 4×" | dataset: AHN5 is PF6 (30 B), no RGB | Recompute the memory slide for PF6. The colour gotcha applies only if AHN6 (RGB) is used. |
| C7 | float32 error example | memory: 0.25 m at northing 5.8e6 (UTM-like synthetic data) | libraries and dataset: 1.6 / 3.1 cm at RD coordinates | Use the RD numbers on the slides, since they match the dataset. |
| C8 | Render specification | template: 2190×1792 canvas, navy #0E2841 | libraries: 1920×1080, #0b0d10. dataset renders: 1600×1000, near-black, **green vegetation** | Three different specs. Green is reserved for status by the brand rules (template §7). One spec is needed before any frames are made. |
| C9 | Pipeline length | brief: 6 steps | template: the process-chain helper allows 3–5 | Merge two steps (template suggests labelling + visualisation) or show 2 × 3. |
| C10 | RANSAC defaults | legacy API: probability 0.99999999 | tensor API: 0.999 and 100 iterations; book: 1000 iterations | Pick one API for the code slides. Reproducible renders need a seed plus `probability=1.0` (libraries measured 741 ms vs 113 ms). |

## 2. Spot-checks of the most consequential claims (all done on 2026-10-02)

- **Venue and date: VERIFIED.** pycon-nl.org says "October 15th 2026", "Jaarbeurs Utrecht", Jaarbeursplein 6, 3521 AL Utrecht. The site lists no talk length, recording policy or branding rules, so all three are **UNVERIFIED**.
- **AHN licences: VERIFIED** (see C1).
- **`np.unique(axis=0)` is no faster than a dict loop: VERIFIED.** At 1M points: unique(axis=0) 0.751 s, dict loop 0.537 s, packed int64 key 0.034 s. Perf's gotcha slide holds.
- **`Vector3dVector` with float32 is slow: VERIFIED.** At 1M points: float64 4.8 ms, float32 452 ms, `astype(float64)` first 11.5 ms.
- **Open3D `voxel_down_sample` returns the centroid: VERIFIED.** Points 0.01 and 0.02 in one voxel returned 0.015, which is not an input point. So the book's ch6 description is wrong. The grid is anchored at min − v/2.
- **PyPI facts: VERIFIED.** PyTorch3D's latest PyPI release is 0.7.4 (2023-05-10), with cp38–cp310 wheels for macOS x86_64 only. open3d 0.20.0 is MIT, needs Python ≥3.10 and has cp310–cp314 wheels.
- **laspy COPC API: VERIFIED.**
  - `CopcReader.open(source, http_num_threads=80, _http_strategy='queue', decompression_selection=…)`
  - `.query(bounds=None, resolution=None, level=None)`
  - `laspy.copc.Bounds(mins, maxs)`
  - I did not run a remote read myself.
- **Does the pipeline work on the chosen data?** Nobody had tested it on the real crop, so I did. Results on the 200 m Graadt van Roggenweg crop, scored against AHN's own class 2:
  - Single-plane `segment_plane`, threshold 0.2 m: 0.76 s, precision 0.992, **recall 0.753**.
  - Threshold 0.5 m: precision 0.976, recall 0.850.
  - The ground's height spread (5th to 95th percentile) is about 1.6 m, so **one plane is not enough**.
  - A crude 1 m grid-minimum filter (keep points less than 0.3 m above the cell minimum): precision 0.902, recall 0.991. Flat roofs count as ground.
  - This gives a gotcha slide, and AHN's labels become a built-in score.
  - DBSCAN on the 296,751 class-1 points: eps 0.5 / min_points 5 took 0.11 s, giving 5,117 clusters and 14.1 % noise. eps 1.0 / min_points 10 took 0.18 s, giving 675 clusters, the largest with 40,638 points. That large cluster is probably merged tree rows (inferred), so parameters need tuning.
- **Render feasibility: plausible.** I viewed `dataset/render_C_GraadtvanRoggenweg.png`. It reads well: roofs, trees, cars and road markings are visible, but facades are sparse because the scan is aerial. Its aspect ratio (1.6) and colours do not follow the template spec. Nobody has rendered the 6-step sequence with a fixed camera on the real crop.
- **Native log-axis chart: partly checked.** python-pptx 1.0.2 lists `c:logBase` only inside its internal XML schema (`oxml/chart/axis.py:192`). There is no public API, so perf's "log axis" chart needs a raw XML edit. Not tested: **UNVERIFIED**.

## 3. What is still missing for a storyboard that obeys the brief

**Dataset**
- **"Raw scan" honesty.** AHN is delivered already classified, from the air. The brief says "raw LiDAR scan of a street". The storyboard has to say "we drop AHN's labels, recover them, and score against them", or reword the hook.
- **Which crop.** Pick the final crop and record its RD bounding box on the slide. Whether crop C really lies directly outside the venue is consistent with the class-26 station canopies but is **UNVERIFIED** (pyproj is not in the venv).
- **Vegetation and street furniture.** Class 1 is vegetation, facades, cars and poles mixed together. There is only a heuristic split, no ground truth, and only about 7 pole-like objects in the crop. Street furniture may be too thin to be one of the four labels in the running example.
- **Street-level alternative.** The only CC BY street-level lead (Santiago, Zenodo 13361987) is still open.

**Renders**
- Agree one spec: canvas, background, camera pose, class-colour mapping to brand colours (green needs sign-off), point size per step, and EDL on or off.
- Frames 1–6 on the real crop do not exist yet. Downsampling needs a different point size so the slides still look alike, and this is untested.
- Morph between two images is a crossfade only (inferred).

**Benchmarks**
- All numbers so far are PILOT runs on synthetic data on a loaded machine.
- Still to do: the real run on the AHN5 crop or tile, on an idle machine, with r ≈ 0.5 m. State thread counts on the slide, decide on boost, and fix the chart data structure.
- Decide whether to show the pure-Python vs library-in-a-loop comparison (2.3×) as the punchline.

**Memory**
- Recompute for PF6 at 30 B/pt on the real tile: read peak, float64 xyz, Open3D copy.
- The headline "a 5×6.25 km tile = 926M points ≈ 27.8 GB of records alone" is right. With the parallel decoder (×1.4) or float64 xyz (+24 B/pt) it clearly exceeds 31 GB. This is arithmetic and has not been measured.
- The chunked-voxel slide must use 0.5 m or larger (C3, C4).

**Template mapping**
- The slide-by-slide table (slide → layout → placeholder → asset) does not exist yet.
- No time budget for the 30 minutes: slides per section, how long Q&A takes, live demo or not.
- Corbel, Calibri and Consolas are not on this machine, so the final PDF has to come from PowerPoint on another machine. Who does it, and when?
- Credits slide: the AHN5 CC BY line, the shared book title, and no third-party logos.

**Code correctness**
- The memory snippet is verified on real data.
- The full 6-step pipeline as one runnable script on Python 3.13 does not exist yet.
- Code slides need line-length budgets: 21–23 characters on L10 and 35–38 on L7/L8, per the template report.
- `01_cube.py` in the repo is a book listing with 8 of 12 edges and `ax.set_label` bugs (confirmed). Do not show it.

**Privacy and IP**
- Template metadata contains the author "Madeleine Kann" and a `claude.fileId` entry. Strip both.
- The O'Reilly EPUBs sit untracked in `3d-data-science-with-python-chapters/`, and **`.gitignore` does not exclude them**. Committing or pushing them would distribute copyrighted material.
- `pyproject.toml` carries a personal gmail address. It becomes public if the repo is published as the talk repo.
- The book excerpts (`book/ch11a.txt` and others) must stay local.
- AHN5 itself is low risk: no RGB, night flight. AHN6 is UNVERIFIED.

**Venue and format**
- PyCon NL's slot length (30 minutes including Q&A?), recording policy, and rules on company branding are all **UNVERIFIED**.
- Projector aspect ratio is unknown; the deck is 16:9.

## 4. Decisions only the speaker can make

1. **Dataset and framing of the running example.** Options:
   - AHN5 Jaarbeurs tile: CC BY, "the street outside this building", but aerial, pre-classified and with sparse street furniture.
   - AHN4 same tile: CC0, 37 pts/m².
   - A street-level (MLS) dataset with licence risk, for example Toronto-3D, which is CC BY-NC.

   Related: whether to state openly that the labels are stripped and then scored against AHN, which would replace "raw scan" in the brief.
2. **Branding and delivery toolchain.** Whether to accept the talk-specific breaks from TEQYARD rules: Morph and fades, Consolas, English text, green for vegetation, the claim on the title and closing slides. Also whether to present from **PowerPoint (Morph works) or from PDF (Morph steps become static pages)**, and who exports the final file on a machine with Corbel, Calibri and Consolas. This needs confirmation that PyCon NL allows a company-branded deck.
3. **The performance-cliff message.** "Two orders of magnitude" is not supported. Honest options:
   - "about 80× for per-point arithmetic"
   - "about 5× per tree query, about 40× once all cores are used"
   - "a C++ library inside a Python loop is still a Python loop" (2.3×)

   The speaker has to pick the headline and decide whether numbers come from the real AHN data or from the synthetic benchmark.

Smaller decisions for the speaker:
- Keep the title, which is identical to Poux's O'Reilly 2025 book, with a credit line, or rename the talk.
- Whether a public repo, QR code and shipped 7.8 MB crop exist at all. If yes, clean the EPUBs out of the tree and the personal email out of `pyproject.toml` first.
- Whether to keep PyTorch3D on the library landscape slide given its install status, and whether to do a live demo at 100k points.