# Research: four videos (2026-10-11): three by Florent Poux, one SciPy 2016 talk on yt

Requested by the speaker: what in these videos is worth using in the talk. Florent Poux is the author of the O'Reilly
book whose title this talk shares (notes, Q&A "Is this talk based on the O'Reilly book?"). Read from the YouTube
auto-captions (English) with yt-dlp; timestamps are mm:ss into the video. Only summaries are kept here, not the
transcripts.

| Id | Title | Channel, date | Length |
|---|---|---|---|
| V1 | [3D Data for Beginners: Top 11 Tools to Start](https://www.youtube.com/watch?v=-eXas3R3ApA) | Dr. Florent Poux, 2025-04-23 | 19:39 |
| V2 | [How to Build 3D Data Tools in Python: The Ultimate Beginner's Guide](https://www.youtube.com/watch?v=47lJiEcr4nM) | Dr. Florent Poux, 2024-10-03 | 15:52 |
| V3 | [Real-Time 3D Point Cloud Classification for 3D Shapes (PCA + Random Forests): Micro Course](https://www.youtube.com/watch?v=o2fe6faVHEw) | Dr. Florent Poux, 2025-03-20 | 38:18 |
| V4 | [Analysis and Visualization of 3D Data with yt, SciPy 2016](https://www.youtube.com/watch?v=4TTIhOYsOro) | Matthew Turk (Enthought / SciPy), 2016-07-14 | 29:46 |

## V1: where 3D data comes from, and what capturing it costs

- 03:46 to 11:30, open data sources, in four groups: 3D city models; airborne LiDAR (OpenTopography with a filter
  for airborne LiDAR and structure from motion, national open-data portals such as France's, Vancouver's open
  data, and **AHN in the Netherlands**, shown in its viewer); heritage scans (Open Heritage 3D, with licence and
  citation per data set; "Florence as it was"); 3D assets (Sketchfab, TurboSquid, filter for free and
  downloadable); plus external sources (Mapillary, OpenStreetMap, Google Dataset Search, which finds S3DIS).
  Every one carries a licence: cite it.
- 12:30 to 16:00, two ways to capture: **photogrammetry** (match images; very dense, good colour, noise around
  edges; Meshroom, RealityCapture) and **LiDAR** (measure distance and angle per pulse; high precision). Terrestrial
  laser scans can be coloured from images. Generative AI (single image to depth map to point cloud to mesh) is the
  third, "for creative content".
- 16:30 to 18:40, hardware from cheap to expensive: smartphone, DSLR, handheld LiDAR, terrestrial laser scanner,
  mobile mapping (LiDAR + GNSS + IMU + cameras), GNSS receiver, radar. Price rises with automation and the number
  of components to calibrate. The video's figures ("below 50 000", "around 20 000" for a terrestrial scanner) are
  spoken loosely and not used.

For the talk: AHN is one open source among many, so the audience can rerun the pipeline on their own street. The
photogrammetry/LiDAR split explains why slide 14's first rule needs LiDAR: a photo sees one surface per pixel,
a laser pulse returns several echoes through bare branches.

## V2: a minimal Python setup for 3D

- 00:30 to 05:30: Miniconda, one environment with Python 3.10, then **pip only** for the libraries, to avoid
  conflicts: NumPy, SciPy (acceleration structures), Matplotlib, Open3D ("the main library for 3D"), and
  scikit-learn (optional, machine learning). IDE: Spyder, installed with pip, cells run with Shift+Enter.
- 06:30: point clouds as PLY or ASCII, meshes as OBJ, glTF, STL or PLY; data from OpenTopography or Sketchfab.
- 09:00 to 12:30, the workflow every script follows: **load, pre-process, explore, process, visualise, export**.
  Open3D viewer keys: + and - change the point size, N shows normals; `o3d.visualization.draw` (instead of
  `draw_geometries`) opens a viewer with settings (shader, lighting, point size) and a fly mode.
- 12:30: region growing segmentation from a helper module, about 2 s on 200 000 points; export to PLY and XYZ, check
  in CloudCompare.
- 10:20: "you can play with very big point clouds directly locally", no cloud setup needed.

For the talk: the same libraries and the same order of steps as this talk's six (slide 9). The talk uses uv instead
of conda + pip (slide 2); the one-tool-for-installs advice is the same. Not used on a slide: Spyder, CloudCompare.

## V3: PCA features plus a Random Forest instead of deep learning

- 00:37: "perfect if deep learning is overkill and if your hardware is limited": a low computational footprint,
  interpretable results.
- 05:00 to 10:10, pre-processing: statistical outlier removal (kNN mean distance above mean + k standard
  deviations) and normalisation into a unit sphere, because the classifier must see data in the same frame at
  training and at inference.
- 10:10 to 16:30, features: PCA with three components on the whole shape (not for dimensionality reduction).
  The eigenvalues give **linearity, planarity, sphericity**, plus anisotropy and eigenentropy. Box, cylinder, plane
  and sphere get clearly different signatures. This is a global signature per object; PointNet combines a global
  and a local one.
- 18:50 to 25:00, model: `RandomForestClassifier` (100 trees, `random_state=42`, `n_jobs=-1`), a 75/25 split,
  feature importances; trained on synthetic spheres, cylinders and planes in under a second.
- 25:20 to 31:50, inference: time each step; one shape is classified in tens of milliseconds ("close to real
  time"). Must repeat exactly the pre-processing of training. **A box, a class it never saw, comes back as "sphere"
  with 100 % confidence**: a classifier can only answer with the classes it was trained on.
- 32:30 to 37:00, next steps: train on many real data sets, tune hyperparameters, engineer features (use the
  importances), and per-point instead of per-object features for semantic segmentation (KPConv, Point
  Transformer) once there is enough labelled data.

For the talk: the clusters of slide 13 are exactly the "objects" V3 classifies. Tested on this street in
`bench/eigen_features.py` (results/eigen_features.json, backup slide B5): the batched eigenvalue features, and a
Random Forest against the four rules of slide 14, both scored against AHN's building class. The closed-set answer
("box" becomes "sphere") is a gotcha candidate for slide 27 (notes only).

## V4: how a SciPy talk draws an ecosystem (yt, volumetric data)

Added 2026-10-11 as the speaker's reference for the ecosystem slide. The subject (yt, simulation data in astronomy) is
not ours; the way the talk places one project inside the scientific Python ecosystem is.

- 00:00 to 05:48, **layers of representation**: what is on disk (many formats, each with its own layout), how the data
  is organised in memory (grids, particles, octrees, unstructured meshes), then a domain model on top. "Providing
  access to the different layers ... lets people choose the level at which they interact with their data." Our
  version: file format (LAS, LAZ, COPC, PLY) → arrays (N×3) → geometry and neighbours → labels and meshes.
- 03:34: **what it stands on**: Cython ("most of the time is spent in Cython but most of the code is Python"), NumPy,
  SymPy, matplotlib, Jupyter, Girder; and what stands on it downstream (Trident, a spectrum generator, others).
  An ecosystem map shows both directions, not only the libraries one uses.
- 01:50: governance: a NumFOCUS fiscally sponsored project with a code of conduct; about 100 contributors, nearly 300
  papers. The funders (NCSA, Moore Foundation, NSF, NumFOCUS) are named on the last slide: credit for the people and
  organisations behind a library is part of the talk.
- 26:55 to 28:15, Q&A "yt against VTK": VTK does more for visualisation and is C++; yt is "pure Python and Cython",
  opinionated, built for fast quantitative analysis. The same question applies to Open3D (C++ core) against pure
  Python: say which job each does.
- 21:17 to 25:42, community: ~400 users, 115 developers on the dev list; peer review, continuous testing on large data
  sets, mentoring; "product versus project". Not used on a slide.
- Dated: 2016, so no library version or claim in it is used.

For the talk: the ecosystem slide (3) is drawn in layers and ends with a row for the organisations behind the
libraries, as yt's last slides do; the catalogue (docs/ECOSYSTEM.md, backup slides) lets people find the rest.
