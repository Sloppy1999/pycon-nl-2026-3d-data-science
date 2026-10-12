# Dataset for the running example: AHN5 1×1 km tile at Jaarbeurs Utrecht recommended, AHN4 as fallback

Checked 2026-10-01. Data downloaded: about 240 MB in total (one 130 MB tile, two partial COPC reads of 36 MB and 43 MB, about 26 MB of index files, plus a few small reads). Nothing was published or committed, and no git commands were run.

## 1. AHN (the main candidate, checked on primary sources)

**Licence (confirmed on two primary sources):**
- The official AHN tile-download page ([basisdata.nl/hwh-ahn/AUX/bladwijzer/index.html](https://basisdata.nl/hwh-ahn/AUX/bladwijzer/index.html)) says verbatim: *"Licenties: AHN1/2/3/4, CC0 1.0; AHN5/6, Creative Commons Naamsvermelding 4.0"*.
- The Nationaal Georegister metadata says the same:
  - AHN5 record `4995e338-fec7-425e-bb86-eea3875cf114` and AHN6 record `934a540d-…`: *"Naamsvermelding verplicht, organisatienaam"*, linking to https://creativecommons.org/licenses/by/4.0/deed.nl. The organisation named is **Het Waterschapshuis**.
  - AHN4 record `c2408619-…`: *"Geen beperkingen"*, linking to CC0 1.0.
- ahn.nl, 02-10-2024 (https://www.ahn.nl/heel-westelijk-nederland-gereed): *"Bij AHN5 en de AHN-versies die nog volgen, zijn gebruikers … verplicht om de bron (AHN) te vermelden bij afgeleide producten."* ("From AHN5 on, users must name the source (AHN) on derived products.")
- ahn.nl, 13-10-2025 (https://www.ahn.nl/eerste-deel-ahn-6-beschikbaar): AHN6 is released under CC Naamsvermelding 4.0 (CC BY 4.0).

**Status in 2026:**
- **AHN5** is published in parts.
  - The old 5×6.25 km tile index lists AHN5 LAZ files for 973 of 1407 tiles (499 with prefix "2023", 474 with prefix "2024").
  - 1×1 km AHN5 tiles returned HTTP 200 for Utrecht, Maastricht, Amersfoort and 093000_436000.
  - They returned 403 (not present) for the two north-east tiles I tried: Groningen 233000_582000 and Enschede 258000_471000.
  - I found no ahn.nl statement that AHN5 covers the whole country: **UNVERIFIED**.
- **AHN6**:
  - The first part (north-east Netherlands) was released 13-10-2025.
  - The AHN6 tile index plans 14,191 tiles for 2025, 12,869 for 2026 and 13,189 for 2027.
  - Utrecht and Amsterdam tiles are planned for 2026 and returned 403, so they are not yet available.
  - The latest ahn.nl news item is "Congres 2026" (3 June 2026).

**Class codes:**
- The AHN4 acquisition spec (`AHN4_inwinning.pdf`, chapter 9, ASPRS LAS 1.4 codes) defines: 0 created/never classified, 1 Unclassified ("Overig"), 2 Ground ("Maaiveld"), 6 Building ("Bebouwing"), 9 Water, 26 Civil structure ("Kunstwerken").
- The spec defines "overig" as: *"vegetatie, straatmeubilair, auto's, GSM-masten, personen, dieren, hoogspanningsmasten en –kabels"* (vegetation, street furniture, cars, phone masts, people, animals, power pylons and cables).
- The dataroom says power lines have been told apart since AHN4. **Code 14 did not appear in any sample I read**, so its use is UNVERIFIED.
- The spec requires a leaf-off flight ("bladloze seizoen"), at least 10 pt/m², and that street furniture goes into "overig".

**Direct fetch (no registration).** Base URL `https://basisdata.nl/hwh-ahn/`. Each request returns a 307 redirect to `fsn1.your-objectstorage.com`, which serves byte ranges (`accept-ranges: bytes`). URL patterns, found in the tile viewer's JS and tested with HEAD requests:
- AHN5 1×1 km COPC: `AHN5_KM/01_LAZ/AHN5_C_{xmin:06d}_{ymin:06d}.COPC.LAZ` (RD lower-left corner)
- AHN4 1×1 km COPC: `AHN4_KM/01_LAZ/AHN4_C_{x}_{y}.COPC.LAZ`
- AHN6: `AHN6/01_LAZ/AHN6_2025_C_{x}_{y}.COPC.LAZ` (a plain `.LAZ` also exists)

Tested files:

| File | Size | Points | Point format |
|---|---|---|---|
| AHN5 tile 135000_455000 | 130,213,150 B | 21,013,926 | PF6 |
| AHN4 tile 135000_455000 | 305,552,607 B | 33,507,029 | PF6 |
| AHN6 Groningen 233000_582000 | 361,328,960 B | 27,921,566 | PF7 (RGB) |
| AHN5 5×6.25 km tile `2023_C_31HZ2.LAZ` | 5,068,977,788 B | 926,203,338 | PF6 |
| AHN4 5×6.25 km tile `C_31HZ2.LAZ` | 9,952,399,556 B | 1,290,104,537 | PF1 |

The two 5×6.25 km tile rows come from the file header only, read with a 64 KB range request.

**The downloaded tile, read with laspy 2.7.0.** File: `AHN5_C_135000_455000.COPC.LAZ` (sha256 `b326b5a6…c327`). It covers Jaarbeurs Utrecht, the PyCon NL 2026 venue; date and venue confirmed on pycon-nl.org.
- LAS 1.4, PF6, no RGB. Scale 0.001 on all axes; offset (135500, 455500, 0).
- CRS from the WKT record in the file: `COMPOUNDCRS["Amersfoort / RD New + NAP height"]`, i.e. EPSG:7415. pyproj is not in the venv, so I read the WKT string directly.
- Extent x 135000–136000, y 455000–456000, z −1.17 to 121.24 m NAP.
- Classes:

| Class | Points | Share |
|---|---|---|
| 1 | 4,273,112 | 20.3 % |
| 2 | 9,506,286 | 45.2 % |
| 6 | 6,891,905 | 32.8 % |
| 9 | 1,040 | ~0 % |
| 26 | 341,583 | 1.6 % (station canopies, a canal bridge) |

- Density: 21.0 pts/m² for all returns, 18.2 pts/m² for first returns.
- GPS time decodes to 2023-04-05, 23:35–23:52 GPS, which is about 01:35 local time. It was a **night flight**, so very few people or moving cars.
- Reading the full tile took 1.0 s with the parallel lazrs backend and added 679 MB to process memory (30 bytes per point).

**Is a street with trees and street furniture visible?** Yes for trees, buildings and cars. Street furniture is visible but thin.
- Crop C, Graadt van Roggenweg, directly north of Jaarbeurs: 200×200 m, x 135330–135530, y 455450–455650.
  - 1,239,310 points (31 pts/m²).
  - 80 % of class-1 points have multiple returns, which points to vegetation.
  - The remaining 60.5k single-return class-1 points are building facades, cars and poles. **So class 1 does not mean vegetation.**
- A rough cluster heuristic (my own, not ground truth) found:
  - 258 tree-like clusters up to 33 m tall
  - 16 car-sized blobs
  - only 7 isolated pole-like objects, with 9–66 points each
- Lamp posts show up as a few dozen points at most, and many merge into tree crowns.
- The comparison crops (Croeselaan, and Leidsekade with its canal and tree row) look similar.
- The same crop in AHN4 is denser: 37.3 pts/m², all-returns density (fetched by bbox over HTTP: 36 MB, 55 range requests, 2.8 s).
- AHN6 Groningen sample: 27.5 pts/m², real RGB colours, daytime flight (2025-03-07).

**Privacy:** low risk.
- AHN5 has no RGB.
- At ~18 first-return pts/m² from the air, a person is a handful of points and licence plates cannot be resolved.
- People and cars are in class 1 by spec.
- AHN6 adds colour from aerial imagery. I expect the same low risk, but did not check it: UNVERIFIED.

**GeoTiles (TU Delft mirror)** labels AHN5 as "Het Waterschapshuis, CC-BY" and AHN4 as "public domain". Its coloured point clouds are *"a new product created by GeoTiles"* with no explicit licence: **UNVERIFIED**, so avoid them.

## 2. Other candidates

| Dataset | Sensor | Licence (primary source) | Registration | Fit / privacy |
|---|---|---|---|---|
| **Toronto-3D** ([GitHub README](https://github.com/WeikaiTan/Toronto-3D)) | MLS (Teledyne Optech Maverick), ~78.3M pts, ~1 km road | "CC BY-NC 4.0" | None stated; OneDrive or Baidu download | 8 classes (Road, Road marking, Natural, Building, Utility line, Pole, Car, Fence) map well. Has RGB; README notes RGB artefacts on moving vehicles. File format UNVERIFIED. **NC is risky with a company template.** |
| **Paris-Lille-3D** ([npm3d.fr](https://npm3d.fr/paris-lille-3d)) | MLS; 50 training classes, 10 coarse | "CC-BY-NC-ND-3.0" (FR) | Shared link with a password | ND blocks publishing derived crops and renders. Reject. |
| **KITTI-360** ([cvlibs](https://www.cvlibs.net/datasets/kitti-360/)) | Velodyne HDL-64E, SICK pushbroom, cameras | "CC BY-NC-SA 3.0" | Yes, with stated purpose (GDPR) | Camera imagery means faces and plates are a risk. Reject. |
| **TUM-MLS-2016** ([Fraunhofer IOSB](https://www.iosb.fraunhofer.de/en/competences/image-exploitation/object-recognition/3d-data/datasets/tum-mls-2016.html)) | 2× HDL-64E; 1.735B pts in 17,756 PCD files, 62 GB | "CC BY-NC-SA 4.0" | FTP access by email request | NC-SA. Reject. |
| **DALES** ([project page](https://sites.google.com/a/udayton.edu/vasari1/research/earth-vision/dales)) | ALS (City of Surrey); ~0.5B pts, 10 km², 29+11 tiles | "licensed under Creative Commons 3.0. This data may not be used for commercial purposes." | Request form | Aerial and North American. Reject. |
| **Semantic3D** | TLS | **UNVERIFIED**: semantic3d.net redirects to an ETH server that returns 401 | n/a | Site unreachable. Reject. |
| **SensatUrban** ([GitHub](https://github.com/QingyongHu/SensatUrban)) | UAV **photogrammetry**, not LiDAR; 13 classes incl. street furniture; PLY | Repo is MIT; separate data licence **UNVERIFIED** | Google Form | Not LiDAR. Reject. |
| **H3D Hessigheim** ([ifp](https://ifpwww.ifp.uni-stuttgart.de/benchmark/hessigheim/default.aspx)) | UAV LiDAR, 800 pts/m², RGB, 11 classes | Data licence not on public pages: **UNVERIFIED** (the CC BY found by search may refer to the paper) | Required | A village, not a street. Reject. |
| **Amsterdam municipal point cloud** ([API docs](https://api.data.amsterdam.nl/v1/docs/datasets/puntenwolk@v1.html)) | MLS (provider "georizon" in 2025); 100×100 m LAZ tiles (e.g. 1.84M pts / 12 MB); colour taken from panorama photos | Not a standard licence: "openbaar, tenzij anders aangegeven / behoudens uitzonderingen" (public unless stated otherwise / with exceptions) | None for metadata | 21,272 tiles listed in `metadata_2025`, 0 in `metadata_2026`. The file host `files.lidar.data.amsterdam.nl` does not exist in public DNS (checked via dns.google), so **the files cannot be downloaded**. Street-level colour from panoramas means people and cars; plate readability UNVERIFIED. Reject for now. |
| **Amsterdam-AI-Team demo tiles** ([repo](https://github.com/Amsterdam-AI-Team/Urban_PointCloud_Processing)) | MLS, CycloMedia; two 50×50 m LAZ files (43 MB, 71 MB) | Code is GPL-3.0; the data is only *"courtesy of CycloMedia"* with no licence | n/a | Do not redistribute. |
| **Santiago Urban Dataset** ([Zenodo 13361987](https://zenodo.org/records/13361987)) | MLS + handheld, 2 km of streets, 8 classes incl. poles | Record is CC BY 4.0, but it **holds only the paper PDF** | n/a | Data location UNVERIFIED. The only CC BY street-level LiDAR lead I found; worth a follow-up. |

**What the licence types allow:** (a) branded talk, (b) derived renders and code in a public repo, (c) redistributing a small crop.
- **CC BY 4.0 (AHN5/6)** allows all three, commercial use included. You must:
  - credit the source and link the licence
  - say what you changed
  - not imply that AHN endorses Teqyard (CC BY 4.0 §2(a)(6))
- **CC0 (AHN4)** allows all three with no conditions.
- **NC datasets:** company-branded slides and a repo owned by a company employee are a grey area under "NonCommercial". This is not legal advice.
- **ND:** forbids (b) and (c).
- **SA:** derivatives must use the same licence.

## 3. Findings for the storyboard

- **"Fits in RAM" slide:** one 5×6.25 km AHN5 tile has 926,203,338 points. At 30 bytes per point that is about 27.8 GB of raw point records (my arithmetic), close to the machine's 31 GB before any float64 xyz copies. One 1×1 km tile is 21M points and +679 MB. This gives a natural "chunked reads" story.
- **COPC demo:** the 1×1 km files are COPC (Cloud-Optimized Point Cloud), so `laspy.CopcReader.open(url).query(Bounds(...))` fetches only one bbox over HTTP. It needs `requests`, which is installed in the venv.
- **Gotchas actually hit:**
  - Writing a crop with `laspy.LasData(copc_header)` raises `NotImplementedError: Writing COPC is not supported`. Build a fresh header and copy only the WKT CRS record.
  - float32 spacing at RD coordinates is 1.6 cm for x and 3.1 cm for y, so subtract an offset before converting to float32.
  - Class 1 mixes vegetation, facades, cars and poles. The "labelling" step has to separate them, for example by number of returns, height above ground and verticality.
  - Leaf-off and night flights mean trees are mostly branches.

## 4. Ranked recommendation

1. **AHN5, 1×1 km tile 135000_455000 (Jaarbeurs Utrecht, the conference venue), CC BY 4.0.**
   - Dutch, and it is "the street outside this building".
   - Direct download with no registration; commercial use allowed.
   - No RGB and a night flight, so no privacy issue.
   - Shows all four classes. Ground and buildings come pre-labelled; vegetation and street furniture have to be derived from class 1, which suits the pipeline.
   - Ship the 7.8 MB, 200 m crop (Graadt van Roggenweg) in the repo with a `DATA_LICENSE` note.
   - Weakness: sparse street furniture. Say so on the "gotchas" slide.
2. **AHN4, same tile, CC0 1.0.**
   - 60 % more points (33.5M) and 37 pts/m² in the crop; no conditions attached.
   - Use it if you want denser poles or zero attribution friction.
   - Alternative if colour matters more than location: an AHN6 tile in the north-east (e.g. Groningen 233000_582000), CC BY 4.0, with RGB.

**Slide source line (AHN5):**
> Point cloud: AHN5 – Actueel Hoogtebestand Nederland (ahn.nl), Het Waterschapshuis, licensed CC BY 4.0 (creativecommons.org/licenses/by/4.0). Tile 135000_455000, cropped and processed.

If AHN4 is used: "Point cloud: AHN4 – Actueel Hoogtebestand Nederland (ahn.nl), CC0 1.0." The credit is optional under CC0 but good practice.

Files are in `scratchpad/dataset/`:
- `AHN5_C_135000_455000.COPC.LAZ` – the downloaded tile
- `ahn5_utrecht_jaarbeurs_200m_crop.laz` – 1,239,310 pts, 7.8 MB, plain LAZ
- `inspect_AHN5_135000_455000.txt` – header and class report
- `ahn5_tile_classmap.png`, `ahn5_tile_class1_height.png` – top-down views of the tile
- `render_C_GraadtvanRoggenweg.png`, `render_A_Croeselaan.png`, `render_B_Leidsekade.png` – dark-background renders of the three crops
- `crop_analysis.json`, `pole_analysis.json` – crop statistics and the tree/pole/car heuristic
- `copc_remote.txt`, `copc_ahn6_rgb.txt`, `top_tile_headers.txt` – remote COPC reads and big-tile headers
- `AHN4_inwinning.pdf` / `AHN4_inwinning.txt` – the AHN4 acquisition spec
- `bladwijzer.gpkg`, `bladwijzer_AHN6.gpkg` – AHN tile indexes
- `bladwijzer.js` – tile viewer JS
- Scripts: `inspect_ahn.py`, `overview.py`, `crop_analysis.py`, `poles.py`, `render.py`, `copc_remote.py`, `rd.py`