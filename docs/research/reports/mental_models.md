Researched 2026-10-12 (web), for deck slides C1 to C9.

# Mental models and principles of 3D data science with Python: sources

Status key: VERIFIED = read on the page or document itself (PDF text, HTML, or Crossref/registry metadata); UNVERIFIED = only from a search snippet or secondary listing. "Doc version" is what the page header showed on 2026-10-12; documentation pages rarely show a date.

## 1. Representations (C1, C9)

- **Point clouds are unordered sets; models must be permutation invariant.** Qi, Su, Mo, Guibas, "PointNet: Deep Learning on Point Sets for 3D Classification and Segmentation", CVPR 2017 (arXiv v1 2 Dec 2016, v2 10 Apr 2017). https://arxiv.org/abs/1612.00593. Abstract: the network "well respects the permutation invariance of points in the input". VERIFIED.
  - Flags: permutation invariance is a property PointNet designs for; the "unordered" view is a modelling choice. Files (LAS, PLY) do have a storage order, and scan or strip order can carry information.
- **Point cloud = coordinates plus optional attributes, no connectivity.** Open3D 0.20.0 docs, `open3d.geometry.PointCloud`: "A point cloud consists of point coordinates, and optionally point colors and point normals." https://www.open3d.org/docs/latest/python_api/open3d.geometry.PointCloud.html (no date shown, doc version 0.20.0). VERIFIED.
- **Mesh = vertices + faces (connectivity).** Open3D 0.20.0, `TriangleMesh`: "Triangle mesh contains vertices and triangles represented by the indices to the vertices." https://www.open3d.org/docs/latest/python_api/open3d.geometry.TriangleMesh.html (no date shown). VERIFIED.
- **PyVista data model: points + cells; a point cloud is a mesh with no connectivity.** PyVista 0.49.1 docs, "What Is a Mesh?": points are "the vertices of the mesh"; cells define connectivity and can be voxels, triangles, lines or single points; a mesh can have only points, "like a point cloud". https://docs.pyvista.org/user-guide/what-is-a-mesh.html (no date shown, doc version 0.49.1). VERIFIED.
  - Flags: PyVista/VTK use "mesh" for any spatially referenced dataset, including volumes, which differs from the graphics meaning (surface mesh).
- **trimesh: triangle meshes, emphasis on watertight surfaces.** trimesh.org: "a pure Python 3.10+ library for loading and using triangular meshes with an emphasis on watertight surfaces." https://trimesh.org/ (doc version 5.1.1; PyPI release 2 Oct 2026). VERIFIED.
- **Voxel grid = regular grid; resolution set by voxel size; occupancy.** Open3D 0.20.0 voxelization tutorial: "The argument `voxel_size` defines the resolution of the voxel grid"; "A voxel is occupied if at least one point of the point cloud is within the voxel." https://www.open3d.org/docs/latest/tutorial/geometry/voxelization.html (no date shown). VERIFIED.
  - Flags: Open3D's `VoxelGrid` is described as "a collection of voxels which are aligned in grid" and returns only the voxels it holds, so it behaves sparsely; the docs do not say so explicitly (inference). "Dense memory grows cubically" is arithmetic: halving voxel size multiplies dense cell count by 8; state it as such rather than citing it.
- **Sparse voxel structures / sparse convolution.** Choy, Gwak, Savarese, "4D Spatio-Temporal ConvNets: Minkowski Convolutional Neural Networks", CVPR 2019. https://arxiv.org/abs/1904.08755 (submitted Apr 2019). Abstract: they "adopt sparse tensors and propose the generalized sparse convolution". VERIFIED.
  - Flags: the abstract does not make an explicit memory claim; use it for "sparse tensors exist", not for a memory figure.
- **Open3D paper.** Zhou, Park, Koltun, "Open3D: A Modern Library for 3D Data Processing", arXiv:1801.09847, 30 Jan 2018. https://arxiv.org/abs/1801.09847. "a set of carefully selected data structures and algorithms in both C++ and Python". VERIFIED.
- **PyVista paper.** Sullivan and Kaszynski, "PyVista: 3D plotting and mesh analysis through a streamlined interface for the Visualization Toolkit (VTK)", JOSS 4(37), 1450, published 19 May 2019. https://doi.org/10.21105/joss.01450. VERIFIED.
- **Survey for the representation trade-off.** Guo, Wang, Hu, Liu, Liu, Bennamoun, "Deep Learning for 3D Point Clouds: A Survey", IEEE TPAMI 43(12):4338 to 4364, Dec 2021 (arXiv:1912.12033). https://doi.org/10.1109/TPAMI.2020.3005434. Metadata and abstract VERIFIED (Crossref, Semantic Scholar).
  - Flags: I did not re-read the body for its specific taxonomy (point-based vs voxel-based vs multi-view); cite it as a survey, not for a specific sentence. Five years old; deep learning parts are dated.

## 2. LAS and COPC (C2, C9)

- **LAS stores X, Y, Z as int32 with scale and offset in the header.** ASPRS, "LAS Specification 1.4 R16", revision date 27 Aug 2025. https://github.com/ASPRSorg/LAS/releases/download/1.4.R16/LAS_1_4_r16.pdf. Scale factors are doubles "used to scale the corresponding X, Y, and Z int32_t values"; "Xcoordinate = (Xrecord * Xscale) + Xoffset". VERIFIED (PDF text).
  - **Correction:** R15 (July 2019, "errata and typo corrections for R14") is no longer the current LAS 1.4 revision. R16 ("readability improvements and clarifications", August 2025) supersedes it, and **LAS 1.5 R00 was approved in August 2025** (revision date 27 Aug 2025): https://github.com/ASPRSorg/LAS/releases/download/1.5.R00/LAS_1_5_r00.pdf, HTML at https://lasformat.org/. VERIFIED. If the slide cites R15, change it to "LAS 1.4 R16 (2025)" or "LAS 1.5 (2025)". The old asprs.org R15 PDF URL now returns 404.
  - Flags: precision is set by the scale (e.g. 0.01 = cm); large offsets plus float32 elsewhere in the pipeline (e.g. GPU, some viewers) lose precision with RD coordinates around 10^5 m, so subtract a local origin.
- **laspy exposes both forms.** laspy docs: "The dimensions 'X', 'Y', 'Z' are signed integers without the scale and offset applied. To access the coordinates as doubles simply use 'x', 'y', 'z'". https://laspy.readthedocs.io/en/latest/intro.html (no date shown; laspy 2.7.0 on PyPI, 14 Jan 2026). VERIFIED.
- **COPC = LAZ 1.4 organised as a clustered octree.** "Cloud Optimized Point Cloud Specification 1.0", Hobu, Inc., copyright 2021 (no exact date shown). https://copc.io/. "A COPC file is a LAZ 1.4 file that stores point data organized in a clustered octree"; readable "sequentially by any reader than can handle variably-chunked LAZ 1.4"; hierarchy stored in a VLR. VERIFIED.

## 3. Coordinate reference systems and axis conventions (C2)

- **PROJ 6+ respects authority axis order; EPSG:4326 is latitude, longitude.** pyproj 3.7.2 docs, "Gotchas/FAQ", section "Axis order changes in PROJ 6+"; EPSG:4326 axes listed as "Lat[north]" then "Lon[east]". https://pyproj4.github.io/pyproj/stable/gotchas.html (no date shown). VERIFIED.
- **`always_xy=True` forces x, y (lon, lat / easting, northing) order.** pyproj Transformer API: with it, the transform "will accept as input and return as output coordinates using the traditional GIS order". https://pyproj4.github.io/pyproj/stable/api/transformer.html (no date shown). VERIFIED.
  - Flags: RD New (EPSG:28992) is easting, northing, so the axis-order trap mainly bites when converting to or from EPSG:4326.
- **RD New = EPSG:28992; NAP height = EPSG:5709; compound = EPSG:7415 "Amersfoort / RD New + NAP height".** epsg.io (MapTiler mirror of the EPSG dataset), https://epsg.io/7415 (no date shown). VERIFIED.
  - Flags: epsg.io is a mirror; the authoritative registry is https://epsg.org (not fetched). AHN data are delivered in RD New + NAP; check the LAS CRS VLR of each tile rather than assuming.
- **Blender is Z-up.** Blender Manual 2.91, "Viewpoint": "Blender uses a right-angled "Cartesian" coordinate system with the Z axis pointing upwards." https://docs.blender.org/manual/en/2.91/editors/3dview/navigate/viewpoint.html. VERIFIED (old manual version).
  - Flags: the current (5.2 LTS) manual page did not show this sentence in my fetch; "right-handed" appears only in very old Blender API docs, so say "Z-up" only.
- **Unity is Y-up, left-handed.** Unity 6.5 Manual, "Quaternion": "Unity uses a left-handed coordinate system"; "the positive y-axis points up, and the positive z-axis points forward." https://docs.unity3d.com/6000.5/Documentation/Manual/class-Quaternion.html (no date shown). VERIFIED.
- **Open3D camera / OpenGL convention.** Open3D 0.20.0 `PinholeCameraParameters` only says "Camera extrinsic parameters" (4x4). https://www.open3d.org/docs/latest/python_api/open3d.camera.PinholeCameraParameters.html. Convention NOT documented on that page: **unclear, do not put on a slide without another source.**

## 4. Transformations (C3)

- **4x4 homogeneous matrix: 3x3 rotation block, translation in the fourth column, bottom row [0, 0, 0, 1].** Open3D 0.20.0 transformation tutorial: "a general transformation defined by a 4×4 homogeneous transformation matrix using the method `transform`". https://www.open3d.org/docs/latest/tutorial/geometry/transformation.html (no date shown). VERIFIED.
- **`Geometry3D.transform` takes a 4x4 matrix.** Open3D 0.20.0 API: "Apply transformation (4x4 matrix) to the geometry coordinates." https://www.open3d.org/docs/latest/python_api/open3d.geometry.PointCloud.html. VERIFIED.
  - Flags: Open3D `rotate` rotates about a centre (by default the geometry centre), not the origin; the tutorial text describing `center` as a boolean looks outdated relative to the API, so check against the installed version.
- **SciPy Euler sequences: uppercase = intrinsic, lowercase = extrinsic; no mixing.** SciPy 1.18.0, `Rotation.from_euler`: "{'X', 'Y', 'Z'} for intrinsic rotations, or {'x', 'y', 'z'} for extrinsic rotations"; "Extrinsic and intrinsic rotations cannot be mixed in one function call." https://docs.scipy.org/doc/scipy/reference/generated/scipy.spatial.transform.Rotation.from_euler.html (SciPy 1.18.1 on PyPI 21 Aug 2026). VERIFIED.
  - Flags: matches the claim. Extrinsic "xyz" equals intrinsic "ZYX" with the same angles reversed in order; worth a speaker note.
- **SciPy `RigidTransform`: added in 1.16.0, order matters.** SciPy 1.18.0 docs: "Added in version 1.16.0"; accepts `matrix` of shape (..., 4, 4); "When composing transforms, the order is important." https://docs.scipy.org/doc/scipy/reference/generated/scipy.spatial.transform.RigidTransform.html. SciPy 1.16.0 released on PyPI 22 Jun 2025. VERIFIED. Claim confirmed.
- **Composition is not commutative.** Supported by the SciPy sentence above. VERIFIED (for SciPy's wording; the general fact is standard linear algebra).

## 5. Neighbourhoods and scale (C4)

- **Neighbours must be computed; normals via local plane fit (PCA / total least squares) on k nearest neighbours.** Hoppe, DeRose, Duchamp, McDonald, Stuetzle, "Surface reconstruction from unorganized points", SIGGRAPH 1992, Computer Graphics 26(2):71 to 78, July 1992. https://doi.org/10.1145/142920.134011. Metadata VERIFIED (Crossref); method description VERIFIED via Mitra and Nguyen 2003, who summarise Hoppe et al. as the "normal to the fitting plane obtained by applying the total least square method to the k nearest neighbors", with k "chosen manually".
- **Neighbourhood size trades noise against curvature and density.** Mitra and Nguyen, "Estimating surface normals in noisy point cloud data", SoCG 2003, pp. 322 to 328, June 2003. https://doi.org/10.1145/777792.777840, PDF https://geometry.stanford.edu/lgl_2024/papers/mn-esnnpcd-03/mn-esnnpcd-03.pdf. Accuracy "depends on (1) the noise in the PCD, (2) the curvature of the underlying manifold, (3) the density and the distribution of the samples, and (4) the neighborhood size"; the optimal size "can be computed adaptively at each point". VERIFIED (PDF text).
  - Flags: an extended journal version exists (Mitra, Nguyen, Guibas, IJCGA 2004), UNVERIFIED from search snippet.
- **Dimensionality features (linear, planar, scatter) from structure tensor eigenvalues, used to select neighbourhood radius.** Demantké, Mallet, David, Vallet, "Dimensionality Based Scale Selection in 3D LiDAR Point Clouds", ISPRS Archives XXXVIII-5/W12, 97 to 102 (Laser Scanning 2011; online 3 Sep 2012). https://doi.org/10.5194/isprsarchives-XXXVIII-5-W12-97-2011. VERIFIED (abstract page).
- **Optimal per-point neighbourhoods improve classification features.** Weinmann, Jutzi, Hinz, Mallet, "Semantic point cloud interpretation based on optimal neighborhoods, relevant features and efficient classifiers", ISPRS J. Photogramm. Remote Sens. 105:286 to 304, July 2015. https://doi.org/10.1016/j.isprsjprs.2015.01.016. Metadata VERIFIED (Crossref). Content (eigenentropy-based scale selection) UNVERIFIED: abstract is paywalled and was elided in Crossref and Semantic Scholar.
- **Open3D `estimate_normals` with `KDTreeSearchParamHybrid(radius, max_nn)`.** Open3D point cloud tutorial: "`radius = 0.1` and `max_nn = 30` specifies search radius and maximum nearest neighbor". https://www.open3d.org/docs/release/tutorial/geometry/pointcloud.html (doc version shown 0.19.0 at /release/; same API in 0.20.0). VERIFIED.
  - Flags: radius is in data units (metres for AHN); 0.1 m from the tutorial is far too small for AHN at about 10 to 20 pts/m2 (mean spacing about 0.2 to 0.3 m). Normal sign is ambiguous; API notes "Normals are oriented with respect to the input point cloud if normals exist", otherwise orientation needs an explicit step.

## 6. Data quality and uncertainty (C5)

- **AHN4 height accuracy: at most 5 cm systematic and 5 cm stochastic (standard deviation); planimetric about 8 cm systematic, 5 cm stochastic (AHN2 to AHN4); AHN4 density about 10 to 14 pts/m2 (Schiphol 20 to 24).** AHN, "Kwaliteitsbeschrijving", https://www.ahn.nl/kwaliteitsbeschrijving (no date shown; text still says AHN4 "will be" acquired 2020 to 2022, so written before then). VERIFIED.
- **AHN5: base requirement 10 points per m2 (optional 20 pts/m2 lot).** Het Waterschapshuis, "Nota van inlichtingen Actueel Hoogtebestand Nederland (AHN-5)", tender 275983, answer dated 18 Aug 2022: the flight plan is to be "gebaseerd op de basis uitvraag 10 punten per vierkante meter". https://www.tenderned.nl/papi/tenderned-rs-tns/v2/publicaties/275983/documenten/8182998/content. VERIFIED (PDF text).
  - **Correction / gap:** ahn.nl publishes no AHN5-specific accuracy figures (the quality page covers up to AHN4; the dataroom links only the tender documents: https://www.ahn.nl/dataroom). Do not state AHN5 accuracy numbers on a slide; say "AHN4 spec: 5 cm systematic + 5 cm stochastic; AHN5 tendered at at least 10 pts/m2". Measured density in Utrecht will differ; compute it from the crop.
  - Flags: AHN5 acquisition started winter 2022/23 (first part, region north 2023, released 22 Dec 2023: https://www.ahn.nl/eerste-deel-van-ahn-5-is-beschikbaar, VERIFIED). Since AHN5 only roofs are classified as building (Andinasari, van Oosterom, Verbree, ISPRS Archives XLVIII-4/W15-2025, 3D GeoInfo, Sept 2025, https://isprs-archives.copernicus.org/articles/XLVIII-4-W15-2025/9/2025/, VERIFIED PDF text). AHN5 uses a conical scan pattern instead of AHN3/AHN4's sweeping pattern, affecting occlusion (Manders 2023, below).
- **Strip overlap and multiple returns.** AHN, "AHN: The making of", https://www.ahn.nl/ahn-making (no date shown; describes the AHN3 process): strips "overlappen elkaar meestal ergens tussen de 20 en 35%"; vegetation points are often first or intermediate returns because later returns reach the ground. VERIFIED.
  - Flags: overlap zones roughly double density locally, so density is not uniform; describes AHN3, not AHN5.
- **Occlusion of building facades and density variation in AHN.** Manders, "Comparing AHN point clouds for their performance in representing 3D buildings in Zuid-Holland" (AHN3 vs AHN4), MSc thesis, Utrecht University / TU Delft GDMC, 2023. https://www.gdmc.nl/publications/2023/MScThesisNiekManders.pdf. VERIFIED (PDF text). Flags: MSc thesis, not peer reviewed.
- **General LiDAR accuracy standard.** ASPRS Positional Accuracy Standards for Geospatial Data, Edition 2, Version 2 (2024), approved by the ASPRS Board 24 Jun 2024 (Ed. 2 v1 was Aug 2023); removes 95% confidence reporting, raises minimum checkpoints from 20 to 30, removes the pass/fail VVA requirement for lidar, adds a lidar mapping addendum. Source: Geo Week News, 3 Jul 2024, https://www.geoweeknews.com/articles/asprs-edition-2-version-2-positional-accuracy-standards-photogrammetry-remote-sensing-lidar/. VERIFIED on that page; ASPRS's own page/PDF not fetched (old URL 404).
  - **Correction:** the current edition is Edition 2, **Version 2 (2024)**, not "Edition 2, 2023"; the title dropped "Digital" ("Positional Accuracy Standards for Geospatial Data"), per search snippets (UNVERIFIED for the title change). US standard; AHN uses its own spec.

## 7. Computational scale (C6)

- **KD-tree: Bentley 1975.** Bentley, "Multidimensional binary search trees used for associative searching", Communications of the ACM 18(9):509 to 517, Sept 1975. https://doi.org/10.1145/361002.361007. Metadata VERIFIED (Crossref). The O(N log N) build figure is UNVERIFIED from the paper (ACM page 403); it is the textbook result with median splitting.
- **Logarithmic expected query time.** Friedman, Bentley, Finkel, "An Algorithm for Finding Best Matches in Logarithmic Expected Time", ACM TOMS 3(3):209 to 226, 1977. https://doi.org/10.1145/355744.355745. VERIFIED (title/metadata, Crossref).
  - Flags: "expected" under distributional assumptions; worst case is worse, and degrades with dimension.
- **SciPy KDTree.** SciPy 1.18.0, `scipy.spatial.KDTree`: sliding midpoint rule; `leafsize` default 10 switches to brute force; "For large dimensions (20 is already large) do not expect this to run significantly faster than brute force." Cites Maneewongvatana and Mount 1999, not Bentley; gives no Big-O. https://docs.scipy.org/doc/scipy/reference/generated/scipy.spatial.KDTree.html. VERIFIED.
  - Flags: in 3D the KD-tree is in its sweet spot; the warning is about high-dimensional feature spaces.
- **Pairwise distances need O(N^2) memory.** Arithmetic: a full float64 distance matrix for N points is 8 N^2 bytes (1e5 points = 80 GB). No citation needed; state as arithmetic.
- **laspy streaming.** laspy docs: "Sometimes files are big, too big to be read entirely and fit into your RAM"; `LasReader.chunk_iterator()` reads points in chunks. https://laspy.readthedocs.io/en/latest/basic.html (no date shown). VERIFIED.
- **PDAL stream mode.** PDAL docs, "Pipeline": "With standard mode, all input is read into memory before it is processed"; "Stream mode processes points through a pipeline in chunks, which reduces memory requirements"; PDAL uses stream mode if possible, `--nostream` forces standard. https://pdal.io/en/latest/pipeline.html (no date shown). VERIFIED.
  - Flags: only some stages are streamable; any stage needing all points (e.g. some neighbourhood filters) forces standard mode.

## 8. Python library landscape (C7)

- **NumPy as the interchange.** NumPy v2.5 manual, "Interoperability with NumPy": buffer protocol and `__array_interface__` let NumPy wrap foreign memory "zero-copy if possible"; DLPack via `np.from_dlpack` (CPU only for NumPy). https://numpy.org/doc/stable/user/basics.interoperability.html (copyright 2008 to 2026). VERIFIED.
  - Flags: that page does not mention the Array API standard; cite it only for buffer protocol / `__array_interface__` / DLPack. Open3D copies NumPy data into its own `Vector3dVector` (not zero-copy in the legacy API), UNVERIFIED here.
- **laspy:** "Python library for lidar LAS/LAZ IO", NumPy-based API. https://laspy.readthedocs.io/en/latest/ . Latest 2.7.0, 14 Jan 2026 (PyPI). VERIFIED.
- **Open3D:** "an open-source library that supports rapid development of software that deals with 3D data" (data structures, processing, reconstruction, registration, visualisation, ML, GPU, C++ and Python). https://www.open3d.org/docs/latest/introduction.html. VERIFIED.
  - **Release cadence:** 0.17.0 (14 Mar 2023), 0.18.0 (5 Jan 2024), 0.19.0 (8 Jan 2025), **0.20.0 (16 Sep 2026)**, per PyPI https://pypi.org/project/open3d/#history. VERIFIED. Flag: a 20-month gap between 0.19 and 0.20; the project is maintained but releases are infrequent. The /release/ docs URL still showed 0.19.0 while /latest/ showed 0.20.0.
- **PyVista:** "3D plotting and mesh analysis through a streamlined interface for the Visualization Toolkit (VTK)" (JOSS title, above). **Latest 0.49.1, 11 Oct 2026** (0.49.0 on 8 Sep 2026; 0.48.0 on 2 May 2026), per PyPI JSON https://pypi.org/pypi/pyvista/json. VERIFIED. Flag: frequent releases; pin the version used in the talk repo.
- **trimesh:** triangular meshes, watertight emphasis (above). Latest 5.1.1, 2 Oct 2026 (PyPI). VERIFIED.
- **PDAL Python bindings:** execute PDAL pipelines and return results "as Numpy arrays". https://pdal.io/en/latest/python.html (no date shown). Latest `pdal` 3.5.5 on PyPI, 31 Jul 2026. VERIFIED.
  - Flags: needs the PDAL C++ library (usually via conda-forge), unlike laspy's pure pip install.

## 9. Recent educational material (C1, C8)

- **Book.** Florent Poux, "3D Data Science with Python: Building Accurate Digital Environments with 3D Point Cloud Workflows", O'Reilly Media, ISBN 9781098161330. Kriso.ee listing: published 25 Apr 2025. https://www.kriso.ee/db/9781098161330.html. VERIFIED on retailer page; O'Reilly page (https://www.oreilly.com/library/view/3d-data-science/9781098161323/) returned 403, its "April 2025" is UNVERIFIED (snippet).
  - Flags: retailers disagree on date (1 Mar to 20 May 2025) and page count (500 to 690). Cite as "O'Reilly, 2025".
- **Survey.** Guo et al., TPAMI 2021 (section 1). VERIFIED. Flag: for a more recent survey nothing was checked in this pass.

## Summary of corrections

1. LAS 1.4 R15 (July 2019) is superseded by LAS 1.4 R16 (27 Aug 2025), and LAS 1.5 R00 was approved August 2025.
2. ASPRS Positional Accuracy Standards: current is Edition 2, Version 2 (approved 24 Jun 2024), not the 2023 Version 1.
3. AHN5: no official accuracy numbers published on ahn.nl; only the tender requirement of 10 pts/m2 (2022). AHN4 numbers (5 cm + 5 cm, 10 to 14 pts/m2) are the official ones.
4. SciPy `RigidTransform` in 1.16.0 (June 2025): confirmed. Euler case convention: confirmed.
5. Open3D camera axis convention: not documented in the API pages checked; leave off slides.
6. SciPy KDTree docs give no Big-O and cite Maneewongvatana and Mount, not Bentley; cite Bentley 1975 and Friedman et al. 1977 for complexity.
