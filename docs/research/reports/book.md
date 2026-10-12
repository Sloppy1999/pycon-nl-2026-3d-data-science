# Reference book review: *3D Data Science with Python* (18 chapter EPUBs)

## 1. Bibliographic facts
- **EPUB metadata, same in all 18 files:** the title is "3D Data Science with Python — Chapter N. …", `dc:creator` is Florent Poux and `dc:publisher` is O'Reilly Media, Inc. **The metadata has no publication date and no ISBN.** The only date is `dcterms:modified` 2026-10-01, which is when these files were generated, not when the book was published. The HTML carries O'Reilly-platform markup (`sbo-rt-content`), so these look like per-chapter extracts from O'Reilly's online reading platform.
- **Checked on the web:**
  - The full title is *3D Data Science with Python: Building Accurate Digital Environments with 3D Point Cloud Workflows*, 1st edition, O'Reilly.
  - ISBN-13 for the paperback is 9781098161330 and for the eBook 9781098161293 (Barnes & Noble page).
  - The year is 2025, with 690 pages ([learngeodata.eu](https://learngeodata.eu/3d-data-science-with-python/), the author's site).
  - The exact day, 20 May 2025, comes only from a search-result summary of the [Amazon listing](https://www.amazon.com/Data-Science-Python-Environments-Workflows/dp/1098161335). I did not open that page, so treat the day as UNVERIFIED.
- **The book title is identical to the talk title "3D Data Science with Python".** A credit slide is advisable, for example "Title shared with F. Poux, O'Reilly 2025; this talk is independent".
- The code and data come from the "3D Data Science Resource Hub" ([learngeodata.eu](https://learngeodata.eu/3d-data-science-with-python), which asks for an email). Chapter 7 says readers may need an email, a password or proof of ownership. Whether the hub's files may be redistributed is UNVERIFIED.
- **The project repo copies a book listing:** `../01_cube.py` is the Chapter 1 cube code. It also drops 4 of the 12 edges and calls `ax.set_label` where it should call `set_xlabel`, `set_ylabel` and `set_zlabel`.

## 2. Datasets (licences as the book states them)
| Ch | Dataset | Source | Licence stated in the book | Notes |
|---|---|---|---|---|
| 1 | Manawatu–Whanganui, NZ 2022–2023 (aerial LiDAR) | OpenTopography (opentopography.org) | **CC BY 4.0** | Exercise: download a small region |
| 3, 4, 5 | AHN4 tiles (34FN2 / 34FN2_18.las; 30HZ1_18_sampled.xyz, 7,103,848 points, LAS classes 1/2/6/9/26) | GeoTiles.nl, NL; zone around Enschede (ch3) | **CC-BY 4.0** (ch5) | Aerial and already classified. Used for the multimodal viewer (ch5) and orthographic projection (ch4) |
| 3, 5 | 3DBAG building meshes (LoD1.2/1.3/2.2) | tudelft3d and 3DGI | **CC BY 4.0** | Paired with AHN |
| 3 | OSM (via Geofabrik), USGS EarthExplorer, Mapillary | — | ODbL; US public domain; CC-BY-SA | Context layers only |
| 11 | `neighborhood.laz`, Vancouver (classes 1–7, EPSG:26910) | City of Vancouver Open Data Portal | **not stated** | Buildings = class 6, ground = class 2 |
| 12 | `KME_planes.xyz`, `KME_cars.xyz` | IGN LiDAR HD (France), subtile | **not stated** | Georeferencing removed; extra attributes added |
| 14 | `3DML_urban_point_cloud.xyz` / `3DML_validation.xyz`, part of Louhans | IGN LiDAR HD | **not stated** | Classes: **ground, vegetation, buildings** |
| 4, 9 | `NAAVIS_EXTERIOR.las/.ply`, "outdoor scene from a mobile mapping LiDAR system" | not stated (NavVis) | **not stated** | Spherical projection (ch4), region growing (ch9) |
| 9 (also 6) | One epoch of a Velodyne VLP-16 scan (ADAS "car" scenario) | not stated | **not stated** | Sparse single sweep |
| 16 | ModelNet10 | Princeton | not stated | Object classification |

**Fit for "raw LiDAR scan of a street":** none of the book's datasets is a raw, street-level scan with a documented licence.
- The closest match to the talk's labels is the Ch14 LiDAR HD Louhans file. But it is aerial, already labelled and preprocessed, and its georeferencing was removed.
- The closest street-level data is NAAVIS_EXTERIOR (mobile mapping), but its source and licence are unknown.
- The AHN tiles (CC-BY 4.0 per the book) are Dutch, which suits PyCon NL, but they are aerial and already classified.
- If you use any of these, take the data from the original open source rather than the book's hub files.

## 3. Methods per pipeline step
**Loading**
- ASCII: `np.loadtxt` with `skiprows` and `max_rows` "to prevent memory shortages" (ch3); `pd.read_csv` (ch4, 5).
- PLY: `o3d.io.read_point_cloud` (ch4).
- LAS/LAZ: `laspy.read`, then `np.vstack((las.x, las.y, las.z)).T`, with colours divided by 65535 (ch4).
- Installed as `pip install laspy[lazrs, laszip]` (ch11). Masks such as `las.classification == 6` and `== 2`, `las.point_format.dimensions`, and the CRS from `las.vlrs[2].string` (ch11).
- `pv.read` for PyVista (ch7).
- The book always re-centres coordinates with `get_center()` and `translate` (ch5, 6, 11) or the minimum bound (ch13).

**Downsampling and cleaning**
- Systematic decimation `iloc[::2]` (ch5).
- `random_down_sample(0.2)` and `voxel_down_sample(voxel_size=0.05)` (ch6).
- An adaptive two-size voxel scheme, 0.05 and 0.02 (ch17).
- `remove_statistical_outlier(16, 10)` (ch6) and `(20, 2.0)` (ch17).
- Normals via `KDTreeSearchParamHybrid(radius=4×nn_distance, max_nn=16)`.

**Ground removal: no CSF, PMF, SMRF, PDAL or DTM grid-minima.** A keyword search over all chapters found zero hits. What the book does instead:
- (a) Reuse the existing LAS class 2 (ch5, ch11). This is its main aerial approach.
- (b) RANSAC plane fitting with `segment_plane(distance_threshold=0.01, ransac_n=3, num_iterations=1000)` (ch12), or a NumPy RANSAC written from scratch (ch9).
  - Threshold heuristic: about 10× the mean kNN spacing (scikit-learn KDTree, k=8).
  - Iteration count from T = log(1−p)/log(1−(1−e)^s).
- (c) A crude `z > mean(z)` mask, with percentile or IQR suggested as more robust (ch12).
- (d) Interactive thresholding on `d_low` and verticality in PyVista (ch7).
  - `d_low` = the point's z minus the lowest z within a 1 m radius in 2D, which is effectively a local column-minimum feature.
- (e) Local ground height: the mean of the 200 (or 50) nearest class-2 points around a segment's lowest centre point (ch11).

**Clustering**
- Open3D `cluster_dbscan`: eps=2, min_points=100 on building points gave 31 clusters (ch11); eps=0.05, min_points=10 on an indoor scene (ch12).
- scikit-learn DBSCAN (eps=0.5, min_samples=2) and KMeans (k-means++, elbow on WCSS, k=2 or 3) (ch12).
- Multi-RANSAC (20 planes) refined with DBSCAN, eps = 10× the threshold (ch12).
- Euclidean clustering: SciPy `KDTree.query_pairs`, then a NetworkX graph and `connected_components`, with radius = 3× mean NN distance and max_neighbors=10. This gave 52 components (ch13).
- Region growing on normals, angle π/6 and distance 0.1 m (ch9).
- SAM on 2D projections (ch13).
- The book says Open3D and scikit-learn DBSCAN times are "almost the same" but gives no numbers.

**Labelling and features**
- Ch7 eigenvalue features (after Weinmann et al.), with λ1 ≥ λ2 ≥ λ3:
  - planarity = (λ2−λ3)/λ1
  - linearity = (λ1−λ2)/λ1
  - omnivariance = (λ1λ2λ3)^(1/3)
  - verticality = 1 − n_z
  - plus `d_high` and `d_low`, all on k=20 neighbourhoods.
- Ch14 random forest with MinMaxScaler and a 60/40 split.
  - Using X, Y, Z, R, G, B only: 98% on the test set but 54% on the validation set (3.1M points).
  - Adding Z, RGB, omnivariance and normal change rate at two scales, NumberOfReturns, planarity and verticality: about 85%. The text mixes up which set ("test" or "validation") each figure belongs to.
- Ch11 per-object attributes: height above local ground, alpha-shape footprint (`alphashape`, alpha=0.5), area, perimeter, and a z histogram to separate roof layers.
- Ch16 PointNet preparation: tiles of 100 m × 100 m with 4,096 points each. XY are centred on the mean, Z has its minimum subtracted, RGB is divided by 255 and intensity is scaled robustly by IQR.

**Visualisation**
- Open3D `draw_geometries`, which blocks the program until the window is closed; tab20 colours per label with noise in black.
- PyVista with `eye_dome_lighting`, `render_points_as_spheres` and `add_mesh_threshold`.
- Matplotlib 3D scatter for small clouds; CloudCompare and Potree outside Python.
- **Nothing on off-screen rendering, fixed cameras or reproducible renders**, which is what the deck needs.

## 4. Performance, memory, GPU and scale
**Book timings.** None of these state the hardware, so re-measure before reusing any of them:
- Ch4: "KD-Tree build 5.21 s, Octree 23.28 s for 10 million points", while the code builds 1 million.
- Ch7, on about 500k points with SciPy `KDTree`:
  - `query` k=20: about 16.7 s
  - `query_ball_point` r=1: about 15 s
  - 2D radius tree: about 2 min
  - **a Python loop over every point running PCA: about 2 min**
- Ch9: region growing in 2.682 s, with no point count given.

**Habits and statements**
- The book often loops over points in Python: the ch4 orthographic and spherical projections, the ch5 voxel-column dictionary loop (which it calls "vectorize"), the ch7 per-point PCA, and ch8's per-point KD queries plus a nested points × triangles loop.
- Ch3 even calls a for loop a "commendable approach" for clarity.
- These make good "before" examples for the performance-cliff section.
- The book never passes SciPy's `workers=-1`. I checked that the parameter exists in SciPy 1.18.1.
- Only one sentence supports the "thin bindings over C++" story: Open3D is "developed in C++ with Python bindings" (ch3).
- Ch12: "We have selected Python over C++ or Julia, and as a result, our system's performance is as it is." Its processing is described as offline.
- Ch2 recommends Java, C++ or Rust if you need more performance.

**Memory**
- Ch4: in-memory vs out-of-core, with chunked `pd.read_csv(chunksize=1000)`.
- Ch4 also says memory mapping "is recommended", but the section it points to contains nothing about it.
- Ch17: tiles with one KD-tree per tile let the author handle "billions of points on modest hardware". This is an anecdote with no numbers.
- Octrees are used for LOD streaming (ch17), Potree 2.0 uses out-of-core loading (ch2), and Fig 1-17 shows octree out-of-core storage.
- Ch2 hardware: at least 16 GB RAM, 64 GB or more for large data; Core i9 or Ryzen 9; RTX 4060 or better; 2 TB NVMe; a cluster or the cloud.

**GPU and other structures**
- Train on GPU or TPU, CPU inference is acceptable (ch1); CUDA (ch15); tiles help GPU parallelism (ch16).
- Octree (Open3D `max_depth=8`) vs KD-tree trade-offs and BVH are covered in ch4.
- Not covered at all (zero keyword hits): nanoflann, faiss, ball tree, voxel hashing or Morton codes, Numba or Cython, multiprocessing or joblib, laspy chunked reading, PDAL pipelines.

## 5. The book's own warnings (reference only, not the speaker's gotchas)
- Huge georeferenced coordinates lose precision and cause rendering glitches, so re-centre first (ch5, 6, 11).
- Random sampling ignores spatial structure (ch6).
- Outlier filters can delete real detail; a lower `std_ratio` filters more aggressively (ch6).
- Neighbourhood size changes feature values, and k=20 may be too small, so consider a radius (ch6, 7).
- Noise distorts high and low points (ch5).
- Polygon area depends on vertex order, and sorting by angle fails on U-shaped buildings (ch5).
- Dropping z assumes flat terrain (ch5).
- Labels are noisy at building edges (ch11).
- Height from a segment's own minimum z is wrong under occlusion; use nearby ground points instead (ch11).
- Fitting planes one after another with RANSAC creates "line" artefacts, fixed with DBSCAN (ch12).
- k-means needs k up front, assumes round clusters and is pulled by the ground; DBSCAN's eps is hard to tune and struggles with varying density (ch12).
- Normals have no fixed sign (ch9).
- Region growing depends on the seed and can over- or under-segment (ch9).
- Skipping normalisation, or feeding raw XY as features, makes models generalise badly (ch6, 14).
- Open3D windows block execution (ch3).
- Library versions drift: tested with conda 23.3.1 and Python 3.9.19 (ch3), while later chapters use 3.10. No library versions are pinned.
- `column_stack` adds overhead on large arrays (ch12).

**Problems in the book's code**, from my own checks, not stated by the book. Avoid copying these listings unchanged:
1. Ch6 says voxel downsampling keeps the input point closest to each voxel's barycenter. In Open3D 0.20.0 it actually returns the centroid of the points in each voxel (tested in `verify_api.py`).
2. Ch6 and ch7 take eigenvectors as rows (`eig_vec[0]`, `_, _, normal = vec`). `np.linalg.eig` returns them as columns (tested). The code also uses `eig` rather than `eigh` on a symmetric matrix, and computes verticality without taking the absolute value of n_z.
3. The Ch4 out-of-core mean starts its counter at 1 and averages chunk means, so the result is biased.
4. The Ch9 RANSAC computes d from the unnormalised normal and is missing parentheses around the distance formula.
5. Ch17 `adaptive_downsample`: `np.var(normals, axis=0)` returns 3 values, not one per point, so the mask has the wrong shape.
6. Ch5 calls `iloc[::2]` "random", which it is not, and describes a "20 cm" voxel while using `voxel_size=2`.
7. Ch14 fits a new MinMaxScaler on the validation set instead of reusing the training scaler.

## 6. Library landscape (for a neutral library map)
- **Ch4 Table 4-3, file format to library:**
  - .ply: open3d, pyvista
  - .las/.laz: laspy
  - .xyz: pandas, numpy
  - .pts: pdal, open3d
  - .e57: pye57, e57, pdal
  - .obj: open3d, pywavefront
  - .pcd: open3d, pcl, pyntcloud
  - The mesh table adds trimesh, plyfile and pygltf.
- **The book's working stack is deliberately small:** NumPy, pandas, Matplotlib and Open3D, plus laspy, PyVista (ch7), SciPy KDTree, scikit-learn and NetworkX.
  - Geospatial: Shapely, GeoPandas, Rasterio, alphashape (ch11).
  - Also CadQuery and Transformers (ch10), PyTorch with PyTorch Geometric (ch15), and SAM (ch13).
- **PyTorch3D is only mentioned in passing (ch12) and trimesh only in the format tables (ch4).** The book adds little on either.
- Ch15 calls PyTorch "currently the most used". It describes Keras as running on TensorFlow or Theano, which is out of date from my own knowledge (I did not check this against Keras docs).
- Desktop and adjacent tools (ch2): CloudCompare, QGIS, Blender, MeshLab, MagicaVoxel, FreeCAD, Unity, Unreal, Potree, ParaView. Reconstruction: RealityCapture, Meshroom, MicMac, OpenMVG, COLMAP, Postshot.

## Files (all under `scratchpad/book/`)
- `convert.py`: EPUB to text converter; output is `txt/01-…txt` to `txt/18-…txt`, about 165k words.
- `metadata.json`: the OPF metadata of every chapter.
- `links.py` and `links.txt`: 525 hyperlinks extracted from the chapters.
- `verify_api.py`: the Open3D, SciPy and NumPy behaviour checks.
- `ch11a.txt`, `ch11b.txt`, `ch14a.txt`: working excerpts, kept local only.

**URLs checked:** https://learngeodata.eu/3d-data-science-with-python/ and https://www.barnesandnoble.com/w/3d-data-science-with-python-florent-poux/1146060854. Search results only, not opened: https://www.amazon.com/Data-Science-Python-Environments-Workflows/dp/1098161335. The Blackwell's page refused the request (HTTP 403).