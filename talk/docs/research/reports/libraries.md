# Library facts and API verification (libraries area)

**Summary:** Every API the pipeline needs works in the shared venv, and the PNG renders correctly both on the desktop and with the display variables unset. PyTorch3D has no documented install for CPython 3.13; I only got it to build after patching it. The most useful finds for the speaker are several slow paths caused by the dtype or memory layout of the input array, and the fact that a seeded `segment_plane` is only reproducible with `probability=1.0`.

All files are in `scratchpad/libraries/` (below: `L/`). Synthetic data: 1M points with RD-like offsets (x≈155000, y≈463000) in `L/out/street.laz`. Timings are single runs on this machine (Ryzen 5700X, RTX 3060) and only indicative.

## 1. Library facts

Source: `https://pypi.org/pypi/<name>/json`, fetched 2026-10-01 and saved in `L/pypi/`.

| Lib | Stable (upload) | Python / CPython 3.13 Linux | Licence | Native core | Use it for … | Not for … |
|---|---|---|---|---|---|---|
| open3d | 0.20.0 (2026-09-16) | ≥3.10; cp310–cp314 wheels, `manylinux_2_35` x86_64+aarch64, no sdist. A separate `open3d-cpu` 0.20.0 exists (Linux x86_64 only) | MIT | C++ core, pybind11 bindings. The PyPI wheel is built with CUDA 12.6 (`o3d._build_config`: BUILD_CUDA_MODULE=True, CUDA_VERSION 12.6); `o3d.core.cuda.is_available()` is True here | downsampling, RANSAC, DBSCAN, outlier removal on point clouds | reading LAS/LAZ (see gotchas); GPU speed-up of RANSAC/DBSCAN |
| pyvista | 0.49.0 (2026-09-08) | ≥3.10; pure-Python wheel. Needs vtk ≥9.3.1, <9.8.0, not 9.4.0/9.4.1. vtk 9.7.1 (2026-09-28) has cp313 manylinux wheels | MIT (VTK: BSD 3-clause, Copyright.txt) | VTK (C++/OpenGL) | scripted renders with a fixed camera, off-screen PNGs | point-cloud algorithms (no RANSAC/DBSCAN) |
| trimesh | 5.1.0 (2026-08-31) | ≥3.10; pure-Python wheel; only hard dependency numpy≥1.21 | MIT | NumPy. Optional extras: SciPy/Qhull for hulls, `embreex` (not aarch64) for rays; the embree path is UNVERIFIED (not exercised) | per-cluster geometry: convex hull, oriented bounding box | point-cloud processing (`PointCloud` has no segment/cluster/downsample methods in `dir()`) |
| laspy | 2.7.0 (2026-01-14) | ≥3.10; pure-Python wheel | BSD-2-Clause | NumPy. LAZ only via extras: `lazrs` (0.8.x; Rust laz-rs, MIT; 0.8.2 has cp39–cp314 wheels) or `laszip` (0.3.x) | reading/writing LAS/LAZ, chunked streaming | geometry processing |
| scipy (`spatial.KDTree`) | 1.18.1 (2026-08-21) | ≥3.12; cp312–cp315 plus free-threaded 314t/315t, manylinux + musllinux | BSD-3-Clause (LICENSE.txt) | C++ (`scipy/spatial/ckdtree/src/*.cxx`, `_ckdtree` extension); `KDTree` subclasses `cKDTree` | batch kNN and radius queries on CPU | per-point queries in a Python loop |
| pytorch3d | PyPI: 0.7.4 (2023-05-10), **macOS x86_64 wheels only** (cp38–cp310); GitHub: v0.7.9 (2025-11-28); main still has commits (2026-09-30) | **No documented route for 3.13** (details below) | BSD 3-clause (Meta, LICENSE) | PyTorch plus C++/CUDA extensions. INSTALL.md: "a subset … have CPU implementations" | differentiable 3D ops on GPU tensors in training | CPU-only pipelines, Python 3.13 |

### PyTorch3D install status in 2026

Sources: `INSTALL.md` on main, anaconda.org API, GitHub releases API (saved in `L/web/`).

- **Documented PyTorch range:** 2.1.0–2.4.1.
- **First torch with cp313 wheels:** 2.5.0, so no documented combination includes CPython 3.13. Current torch is 2.14.1 (2026-09-30).
- **Conda (`-c pytorch3d`):** latest build is 0.7.8, linux-64 only, py3.8–3.12, pyt 2.1.0–2.4.1, cu118/cu121. There is no conda build of 0.7.9.
- **fbaipublicfiles wheels:** documented only for the old py38/py39 + PyTorch 1.11 combination. A py313_cu124_pyt260 index URL that I guessed returned 403.
- **Official from-source route:** `pip install "git+https://github.com/facebookresearch/pytorch3d.git@stable"`.
- **What I observed building it:**
  - v0.7.9 against torch 2.14.1+cpu with gcc 16.2.1 fails. `setup.py` uses `-std=c++17` and the ATen headers raise `#error C++20 or later compatible compiler is required` (`L/pt3d_build2.log`). main has the same flag.
  - Changing it to `-std=c++20` (my own patch, `L/pt3d_cxx20.patch`) gives a CPU build in about 2 minutes. `knn_points`, `Pointclouds` and `sample_farthest_points` then run (`L/pt3d_build3_cxx20.log`). The CUDA build is UNVERIFIED.

## 2. Verified API signatures and observations

### laspy 2.7.0 (`L/01_laspy_io.py` → `out_01_laspy.txt`, `out_09_laspy_no_backend.txt`)

- `laspy.read(source, closefd=True, laz_backend=(LazrsParallel, Lazrs), decompression_selection=…, encoding_errors='strict') -> LasData`
- `laspy.open(source, mode='r', closefd=True, laz_backend=None, header=None, do_compress=None, encoding_errors='strict', read_evlrs=True, decompression_selection=…) -> LasReader|LasWriter|LasAppender`
- `LasReader.chunk_iterator(points_per_iteration: int)`: yields `ScaleAwarePointRecord`, which has `.x/.y/.z/.classification` but **no `.xyz`**.
- `LasData.xyz`: builds a new float64 (N,3) array on every access. It is **F-ordered** (not C-contiguous) and does not share memory with the record.
- `las.X` is a raw int32 view on the record. `las.x` is a `ScaledArrayView` (float64 when converted). `classification` is a `SubFieldView` of uint8.
- Writing: `LasData.write(dest, do_compress=None, laz_backend=None)`; a `.laz` suffix means compressed. Streaming filtered output with `LasWriter.write_points(chunk)` works.
- Point format 3 takes 34 B/point; `xyz` float64 adds 24 B/point.
- Round-trip error with scale 0.001 is at most 0.0005 m.
- With only `laspy` installed (no lazrs/laszip): `LaspyException: No LazBackend selected, cannot decompress data`.

### Open3D 0.20.0 legacy API (`L/02_open3d_legacy.py`, `L/08_extra_checks.py`, `L/10_*`, `L/11_*`, `L/12_*`)

- `utility.Vector3dVector(ndarray float64)` always copies.
  - 1M points: float64 C-contiguous ≈ 2–5 ms; F-order ≈ 10 ms.
  - **float32 or int32 input is accepted but takes ≈ 450 ms**; `.astype(float64)` first takes 6.5 ms in total.
  - An (N,2) array raises `RuntimeError` with an empty message.
- `np.asarray(pcd.points)` is a float64, writeable view on Open3D's memory; writing to it changes the cloud.
- `voxel_down_sample(voxel_size) -> PointCloud`: averages points, colours and normals and returns no index map.
- `voxel_down_sample_and_trace(voxel_size, min_bound, max_bound, approximate_class=False) -> (PointCloud, ndarray (M,8), list[IntVector])`.
- `segment_plane(distance_threshold, ransac_n, num_iterations, probability=0.99999999) -> (ndarray float64 (4,), list[int])`.
  - There is **no seed argument**. Global seeding is `o3d.utility.random.seed(seed)`.
- `cluster_dbscan(eps, min_points, print_progress=False) -> IntVector` (int32 via `np.asarray`; −1 means noise). Deterministic across runs.
- `remove_statistical_outlier(nb_neighbors, std_ratio, print_progress=False) -> (PointCloud, list[int])`.
- `compute_nearest_neighbor_distance() -> DoubleVector`.
- `select_by_index(indices, invert=False)`.
- Full-resolution DBSCAN (450k points, eps=0.3): 0.97 s, peak RSS +284 MB.

### Open3D tensor API (`L/03_open3d_tensor.py`)

- `o3c.Tensor.from_numpy(a)` and `t.geometry.PointCloud(tensor)` **share memory** with the numpy array. `o3c.Tensor(a)` copies. F-order input is accepted.
- `t.geometry.PointCloud.from_legacy(pcd, dtype=Float32, device=CPU:0)`: the **default is float32**, which gives 1.55 cm error at RD coordinates.
- `t.voxel_down_sample(voxel_size, reduction='mean')`.
- `t.segment_plane(distance_threshold=0.01, ransac_n=3, num_iterations=100, probability=0.999) -> (Tensor[4] Float64, Tensor Int64)`. **The defaults differ from the legacy API.**
- `t.cluster_dbscan(eps, min_points, print_progress=False) -> Tensor Int32`.
- `t.remove_statistical_outliers(nb_neighbors, std_ratio) -> (PointCloud, bool mask)`. Note the plural "outliers", unlike legacy.
- The docstrings of `segment_plane` and `cluster_dbscan` say "wrapper for a CPU implementation and a copy … will be made".
- CUDA on the RTX 3060, 1M points float32:

| Operation | CUDA | CPU |
|---|---|---|
| voxel downsample | 98 ms first call, 4.2 ms second | 250 ms |
| segment_plane | 62 ms | 68 ms |
| DBSCAN | 721 ms | 748 ms |

- `.numpy()` on a CUDA tensor raises `RuntimeError`; `.cpu().numpy()` is needed.

### SciPy 1.18.1 (`L/05_scipy_kdtree.py`)

- `KDTree(data, leafsize=10, compact_nodes=True, copy_data=False, balanced_tree=True, boxsize=None)`.
  - C-contiguous float64 input is not copied. F-order or float32 input is copied to float64.
- `query(x, k=1, eps=0.0, p=2.0, distance_upper_bound=inf, workers=1) -> (float64, int64)`.
  - `k=1` drops the last dimension; `k=[1]` keeps it.
  - A missing neighbour gives `d=inf`, `i=tree.n`. Passing `n_jobs=` raises `TypeError`.
  - `cKDTree.query` defaults to `workers=None`.
- `query_ball_point(x, r, p=2.0, eps=0.0, workers=1, return_sorted=None, return_length=False)` returns an object array of lists, or int64 counts with `return_length=True` (88 ms vs 377 ms for 100k queries).
- `workers=-1` was 6.5× faster (100k queries, k=8: 190 → 29 ms).
- **Performance cliff:**
  - Looping `tree.query` over 20k points in Python: 260 ms; one call: 3.7 ms (71×).
  - Pure-Python double loop over 2k points: 2.85 s; KDTree build + query: 1.3 ms (~2200×).
  - Results were equal in both comparisons.

### PyVista 0.49.0 / VTK 9.7.1 (`L/04_pyvista_render.py`)

- `Plotter(off_screen=True, window_size=[1920,1080])`, `set_background('#0b0d10')`.
- `add_points(points, style='points', scalars=rgb_uint8, rgb=True, point_size=3, render_points_as_spheres=True)`.
- `pl.camera_position = [(pos), (focal), (view_up)]`.
- `screenshot(filename, transparent_background=None, return_img=True, window_size=None, scale=None)` returns a (1080,1920,3) uint8 array.
- **Headless works.** With DISPLAY and WAYLAND_DISPLAY unset, VTK logs `WARN| bad X server connection` and uses `vtkEGLRenderWindow`. On the desktop it uses `vtkXOpenGLRenderWindow`.
- I looked at `L/out/render_headless.png`: dark background, sphere points, correct framing.
- The camera after rendering equals the one requested, including for the second step (`render_*_noground.png`), so framing can stay identical across steps.
- `PolyData(ndarray)` with the default `deep=False` shares memory for float32 and float64 input; `deep=True` copies.
- **Float precision (`L/out/zoom_compare_local_rawf64_rawf32.png`, viewed):**
  - Raw RD coordinates passed as float64 render the same as local coordinates (16 of 518,400 pixels differ).
  - The same points cast to float32 first give 16,386 differing pixels and visible about 1.5 cm vertical striping.
  - float32 spacing is 0.015625 m at 155000 and 0.03125 m at 463000.

### trimesh 5.1.0 (`L/06_trimesh_interop.py`)

- `PointCloud(vertices, colors=None, metadata=None)`: vertices are a `TrackedArray` that shares memory with the input.
- On one pole: `convex_hull` gives a watertight `Trimesh` in 3.7 ms; `bounding_box_oriented` gives a `Box` with `.primitive.extents` [0.378, 0.4, 5.999].
- `Trimesh(vertices, faces, …, process=True, validate=False, …)`: faces are int64.

### torch / PyTorch3D (`L/07_torch_pytorch3d_interop.py`, run in `L/pt3d-venv`)

- `torch.from_numpy` is zero-copy; `.float()` copies.
- `Pointclouds(points=[t])` keeps the same storage in `points_list()`; float64 input stays float64.
- `knn_points` returns squared distances. On CPU, 100k×100k with k=8 took **29.4 s**, against **55 ms** for SciPy (build + query, `workers=-1`).

## 3. Interop: what copies and what does not

| Conversion | Copies? (observed) |
|---|---|
| laspy → `las.X` | zero-copy (int32 view) |
| laspy → `las.xyz` / `np.asarray(las.x)` | copy, new float64 every access, F-order |
| numpy → Open3D legacy `Vector3dVector` | copy (fast only for float64) |
| Open3D legacy → numpy (`np.asarray(pcd.points)`) | zero-copy, writeable |
| Open3D legacy → PyVista (`PolyData(np.asarray(pcd.points))`) | zero-copy; stayed valid after `del pcd` once (ownership mechanism UNVERIFIED) |
| numpy ↔ Open3D tensor (`Tensor.from_numpy` / `.numpy()`) | zero-copy (CPU) |
| Open3D legacy → tensor (`from_legacy`) | copy, float32 by default |
| Open3D tensor ↔ torch (DLPack: `to_dlpack` / `torch.from_dlpack(o3c_tensor)` / `o3c.Tensor.from_dlpack`) | zero-copy (CPU tested only) |
| numpy → torch (`from_numpy`) | zero-copy; dtype change or `.cuda()` copies |
| numpy → SciPy KDTree | zero-copy if C-contiguous float64, otherwise copy |
| numpy → trimesh.PointCloud | zero-copy |
| trimesh → Open3D mesh (`Vector3iVector`) | copy; int64 faces 173 ms vs int32 0.2 ms (327k faces) |
| Open3D mesh → trimesh (`Trimesh(..., process=False)`) | copy; faces int32 → int64 |
| trimesh → PyVista (`pv.wrap`) | works (memory sharing not checked) |
| Open3D mesh → PyVista (`PolyData.from_regular_faces`) | works (memory sharing not checked) |

**Worth the trouble:**

- **laspy → NumPy (float64, C-contiguous, local origin) → Open3D legacy.** One fast copy, and every pipeline call exists there.
- **Open3D → PyVista** for renders. No copy, a fixed camera, and headless EGL works.
- **SciPy KDTree** for features and neighbour queries. C++ core, `workers=-1`, no copy.
- **trimesh** only for per-object hull and OBB (labelling features).

**Not worth it for this talk:**

- **PyTorch3D in the pipeline.** No supported install for 3.13; needs a source patch; CPU `knn_points` was about 500× slower than SciPy here.
- **Open3D tensor/CUDA for RANSAC/DBSCAN.** CPU wrappers, no speed-up observed. Only voxel downsampling got faster.
- **Mixing legacy and tensor Open3D APIs.** Different defaults and voxel grids (see gotchas).

## 4. FLAG FOR QA

1. **RANSAC reproducibility.** With a seed and the default `probability`, 10 runs gave 4–8 different inlier counts, even with `OMP_NUM_THREADS=1`. With `probability=1.0`, 10 seeded runs were identical, but it took 741 ms vs 113 ms. My explanation (early termination) is inferred, UNVERIFIED. An earlier pair of seeded runs happened to match by chance.
2. **Voxel grid alignment differs.** Legacy anchors the grid at min_bound − v/2, the tensor API at the coordinate origin: 660,146 vs 571,754 voxels at 0.10 m on the same data. A numpy floor formula reproduces both counts exactly. How large the gap is depends on the data (my synthetic ground is thin).
3. **Wheel tags.** The open3d wheel tag `manylinux_2_35` means glibc ≥ 2.35. Which distros that excludes is UNVERIFIED.
4. **Open3D wheel without a GPU or driver.** Behaviour UNVERIFIED (only tested with an RTX 3060). The CUDA timings come from this one GPU.
5. **VTK fallback.** Off-screen fallback without EGL or a GPU (OSMesa) is UNVERIFIED.
6. **PyTorch3D.** The c++20 patch is unofficial; CUDA build UNVERIFIED; behaviour on main after v0.7.9 UNVERIFIED.
7. **Untested paths.** The Open3D PyTorch ops (`BUILD_PYTORCH_OPS=True`) and their torch-version coupling are UNVERIFIED. The trimesh embree path was not exercised.
8. **Timings** are single runs and noisy: `Vector3dVector` float64 ranged 2–7 ms across runs.

## 5. Candidate gotchas (suggestions for the speaker)

- `Vector3dVector` with float32 is about 100–220× slower than float64. Use `.astype(np.float64)` first. CANDIDATE, observed in `L/08_extra_checks.py`.
- trimesh faces are int64, and `Vector3iVector` with int64 is about 800× slower than with int32. CANDIDATE, observed in `L/06_trimesh_interop.py`.
- `o3d.io.read_point_cloud("x.laz")` (and `.las`) returns an empty cloud with only a warning ("unknown file extension"), no exception. CANDIDATE, observed in `L/08_extra_checks.py`.
- `laspy` without `lazrs` or `laszip` cannot read LAZ: `LaspyException`. CANDIDATE, observed in `L/out_09_laspy_no_backend.txt`.
- Chunks from `chunk_iterator` have no `.xyz`; use `.x/.y/.z`. CANDIDATE, observed in `L/01_laspy_io.py`.
- `las.xyz` is F-ordered and copied on every access. Store it once and use `np.ascontiguousarray`. CANDIDATE, observed in `L/01_laspy_io.py`.
- The float32 cast is what breaks RD/UTM coordinates (1.5–3 cm steps). VTK given float64 renders fine. Subtract a local origin. CANDIDATE, observed in `L/04_pyvista_render.py`.
- `t.geometry.PointCloud.from_legacy` silently converts to float32. CANDIDATE, observed in `L/03_open3d_tensor.py`.
- `segment_plane` has no seed argument; `o3d.utility.random.seed` alone does not make it reproducible. CANDIDATE, observed in `L/11_ransac_probability.py`.
- Plane coefficients fitted on raw RD coordinates are hard to read (d = 44.1 for a ground at z ≈ −1.5). CANDIDATE, observed in `L/02_open3d_legacy.py`.
- `.numpy()` on a CUDA Open3D tensor raises an error. CANDIDATE, observed in `L/03_open3d_tensor.py`.
- PyTorch3D `knn_points` returns squared distances. CANDIDATE, observed in `L/07_torch_pytorch3d_interop.py`.
- KDTree: `n_jobs` is gone (use `workers`); `k=1` drops the last dimension. CANDIDATE, observed in `L/05_scipy_kdtree.py`.

## Files

Everything is in `scratchpad/libraries/`:

- **Scripts:** `01_laspy_io.py`, `02_open3d_legacy.py`, `03_open3d_tensor.py`, `04_pyvista_render.py`, `05_scipy_kdtree.py`, `06_trimesh_interop.py`, `07_torch_pytorch3d_interop.py`, `08_extra_checks.py`, `10_ransac_determinism.py`, `11_ransac_probability.py`, `12_dbscan_memory.py`, `pypi_summary.py`
- **Outputs:** `out_00_open3d_doc.txt` … `out_12_dbscan_mem.txt`
- **Images and data:** `out/render_headless.png`, `out/render_desktop.png`, `out/render_*_noground.png`, `out/zoom_compare_local_rawf64_rawf32.png`, `out/street.las`, `out/street.laz`, `out/ground_only.laz`
- **PyTorch3D build:** `pt3d_build2.log`, `pt3d_build3_cxx20.log`, `pt3d_cxx20.patch`
- **Saved sources:** `pypi/*.json`, `web/pt3d_INSTALL.md`, `web/pt3d_conda.json`, `web/pt3d_releases.json`, `web/pt3d_LICENSE`
- **Extra venvs and checkouts:** `pt3d-venv/` (2.2 GB), `laspy-only-venv/`, `pt3d-src/`, `pt3d-src-cxx20/`. The shared venv was not modified.

**URLs checked:**
- `https://pypi.org/pypi/{open3d,open3d-cpu,pyvista,trimesh,laspy,lazrs,scipy,pytorch3d,vtk,torch,numpy}/json`
- `https://api.github.com/repos/facebookresearch/pytorch3d/releases`
- `https://raw.githubusercontent.com/facebookresearch/pytorch3d/main/{INSTALL.md,LICENSE,setup.py}`
- `https://api.anaconda.org/package/pytorch3d/pytorch3d`
- `https://raw.githubusercontent.com/scipy/scipy/v1.18.1/LICENSE.txt`
- `https://api.github.com/repos/scipy/scipy/contents/scipy/spatial/ckdtree/src?ref=v1.18.1`
- `https://raw.githubusercontent.com/Kitware/VTK/master/Copyright.txt`
- `https://api.github.com/repos/laz-rs/laz-rs-python`
- `https://raw.githubusercontent.com/mikedh/trimesh/main/LICENSE.md`
- `https://raw.githubusercontent.com/isl-org/Open3D/main/LICENSE`