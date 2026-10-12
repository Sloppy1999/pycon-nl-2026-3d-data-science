# PILOT performance-cliff benchmark: report (synthetic data)

**Verdict:** a general claim of "two orders of magnitude" is **not supported**. When the same C++ kernel is called once per point instead of once for all points, it costs **2–5× for tree queries** (radius count, kNN) and **about 80× for per-point arithmetic** (point-to-plane distance). The batched call can also use `workers=-1`, which adds another 6–8×. Every number below was measured on this machine. No web sources were used.

## Files (all in `scratchpad/perf/`)
- `bench_pilot.py`: the benchmark (scene generator, all variants, harness, equality asserts, conditions).
- `pilot_results.json`: main run with N = 10k, 100k and 1M. It holds conditions, per-variant stats, raw times, factors, load and temperature snapshots, and the log. Runtime was 686 s.
- `rerun_radius.py`, `pilot_rerun_1M_radius_unpinned.json`, `pilot_rerun_1M_radius_pinned_cpu3.json`: two stability re-runs of the 1M radius block. One was unpinned. In the other, the single-thread variants were pinned to CPU 3.
- `summarize.py`: prints the tables. Logs: `pilot_run.log`, `rerun_*.log`.

## Conditions (written to the JSON from code)
- **Machine:** AMD Ryzen 7 5700X, 8 cores / 16 threads, 31.3 GB RAM, Omarchy, kernel 7.2.5-3-omarchy. Governor `performance`, boost on, reported max 4666 MHz.
- **Software:** CPython 3.13.15 with the GIL, numpy 2.5.3 (scipy-openblas 0.3.34), scipy 1.18.1, open3d 0.20.0.
- **Protocol:**
  - 1 warm-up run, then 7 repeats, interleaved in a seeded random order, with `gc.collect()` before each run.
  - Pure-Python variants at 1M: only 3 repeats (each takes about 17 s).
  - Wall time from `perf_counter`; CPU time from `process_time`. CPU/wall above 1 shows hidden threading.
  - Statistic: median and IQR. Factors are median ratios. The "IQR-bounded" range runs from q1(slow)/q3(fast) to q3(slow)/q1(fast).
  - Tree and index builds are timed separately and left out of all query timings. KDTree build at 1M takes 0.31 s.
- **Data:**
  - A street generated with seed 20261015 at 0.10 m spacing (100 points/m²), with 1 cm noise and 0.5% outliers. It has road and raised sidewalks, box buildings, poles and trees.
  - The street gets longer as N grows, so local density stays the same. At 1M it is 185 m long: 36% ground, 45% building, 18% tree, 0.8% pole.
  - At 10k the scene is only a 2.4 m slice with no trees.
- **Parameters:** r = 0.25 m (about 18–19 neighbours including the point itself), k = 16, voxel size 0.20 m.
- **Correctness:** every variant produces exactly the same result as C (asserted). Radius counts, kNN indices, plane distances and voxel inverse indices all match bit-for-bit. Open3D results match SciPy exactly as well.

## Variants
- **A:** pure Python. The radius count uses a uniform grid hash, which is in the same O(N·k) complexity class as a tree. I deliberately did not use an O(N²) brute force, because that would make the factor bigger through the algorithm rather than the boundary.
- **B:** a Python loop with one library call per point, so the boundary is crossed N times.
- **C:** one batched call on 1 thread, so the boundary is crossed once.
- **D:** the same as C with `workers=-1`.
- **E1:** Open3D `KDTreeFlann`, one call per point.
- **E2:** Open3D tensor `NearestNeighborSearch`, batched, with default threads.
- **E2_1t:** E2 limited to one thread with `o3d.utility.set_max_threads(1)`.

## Results (PILOT, synthetic)

**Radius count:** "for every point, count its neighbours within r" (local density, used for the noise filter)

| N | A pure Py | B loop | C 1 call | D workers=-1 | B/C | A/C | C/D | B/D | A/D |
|---|---|---|---|---|---|---|---|---|---|
| 10k | 69.1 ms | 52.0 ms | 17.6 ms | 3.40 ms | 3.0× | 3.9× | 5.2× | 15.3× | 20.3× |
| 100k | 1.01 s | 0.607 s | 0.256 s | 0.040 s | 2.4× | 3.9× | 6.5× | 15.3× | 25.4× |
| 1M (main) | 17.3 s (n=3) | 7.45 s | 3.22 s | 0.49 s | 2.3× (1.9–2.6) | 5.4× | 6.6× (3.9–8.3) | 15.2× | 35.3× |
| 1M re-run | 16.6 s | 6.51 s | 3.01 s | 0.377 s | 2.2× | 5.5× | 8.0× | 17.2× | 43.9× |
| 1M pinned | 15.5 s | 6.59 s | 2.94 s | 0.437 s | 2.2× | 5.3× | 6.7× | 15.1× | 35.5× |

- **Open3D at 1M:** E1 3.43 s, E2 0.359 s, E2_1t 2.32 s.
  - E1/E2 is 9.6×, but E2 runs on 9–12 TBB threads by default.
  - With threads equal, E1/E2_1t is only **1.5×**.
- **Pure Python vs a library in a Python loop:** A is only 1.3–2.3× slower than B. In practice, a C++ library inside a Python loop still runs at roughly pure-Python speed.

**kNN, k=16:** "for every point, find its 16 nearest neighbours" (normals and geometric features)

| N | B loop | C | D | B/C | C/D | B/D | E1 / E2 / E2_1t |
|---|---|---|---|---|---|---|---|
| 10k | 127 ms | 20.8 ms | 3.42 ms | 6.1× | 6.1× | 37.2× | 28.5 / 1.9 / 12.7 ms |
| 100k | 1.35 s | 0.259 s | 0.034 s | 5.2× | 7.6× | 39.6× | 318 / 23 / 163 ms |
| 1M | 14.9 s | 3.09 s | 0.376 s | **4.8× (4.6–5.0)** | **8.2× (7.5–8.6)** | **39.7× (36.3–41.0)** | 3.55 / 0.277 / 2.15 s |

This block has the tightest IQRs, so it is the most robust of the neighbour-search results.

**Point-to-plane distance:** "for every point, how far is it from the ground plane" (the RANSAC and ground-removal inlier test)

| N | A Python floats | B loop with NumPy scalars | C vectorised | B/C | A/C |
|---|---|---|---|---|---|
| 10k | 0.68 ms | 4.56 ms | 0.078 ms | 58.5× | 8.7× |
| 100k | 7.9 ms | 45.3 ms | 0.587 ms | 77.2× (73.8–104.9) | 13.5× |
| 1M | 86.3 ms | 450 ms | 5.71 ms | **78.7× (75.5–84.5)** | 15.1× |

- NumPy scalars inside a loop are 5–7× slower than plain Python floats (B vs A).
- The idiomatic `pts @ n` takes 3.2 ms at 1M, but OpenBLAS runs it on multiple threads (CPU/wall 9.4). It is shown for reference only and is not used in the ratios.

**Voxel indices, v=0.2 m:** a Python dict loop vs `np.floor` + `np.unique(axis=0, return_inverse=True)`

| N | A Python | C `unique(axis=0)` | C2 packed int64 key + 1-D unique | A/C | A/C2 | C/C2 |
|---|---|---|---|---|---|---|
| 10k | 3.79 ms | 5.08 ms | 0.76 ms | **0.7×** | 5.0× | 6.7× |
| 100k | 60.7 ms | 61.5 ms | 6.8 ms | 1.0× | 9.0× | 9.1× |
| 1M | 1.23 s (n=3) | 0.794 s | 0.075 s | 1.5× | 16.4× | 10.6× |

`np.unique(axis=0)` is no faster than the Python loop. It sorts rows as a structured dtype: in NumPy 2.5.3 it views the rows as fields `f0..f2`, see `numpy/lib/_arraysetops_impl.py` lines 313–342. Packing the voxel coordinates into one int64 key fixes this. This could be a gotcha slide: "vectorised" does not always mean fast.

## Where the time goes (per-call overhead)
Measured with `timeit` at N=100k, minimum of 7 runs. These are hot-cache best cases.

| Operation | Cost |
|---|---|
| `for p in pts: pass` (an ndarray row view per iteration) | 42 ns |
| Same loop over a list of tuples | 3.7 ns |
| One pure-Python squared distance plus compare | 100 ns |
| Plane-distance body with NumPy scalars | 362 ns |
| Plane-distance body with Python floats | 74 ns |
| `KDTree.query_ball_point(far point, r, return_length=True)` (no neighbours, almost no kernel work) | **3.04 µs** |
| Same through `cKDTree` directly | 2.83 µs |
| Typical point with 17 neighbours | 5.82 µs |
| `KDTree.query(p, k=16)` | 11.0 µs |
| Open3D `search_radius_vector_3d`, far point | **0.99 µs** |
| Open3D `search_radius_vector_3d`, typical point | 1.41 µs |

- **Kernel work per point inside the batched call:** radius 2.6 µs (100k) and 3.0–3.2 µs (1M). kNN 2.6 µs and 3.1 µs. Plane distance 5.7 ns.
- **The KDTree Python wrapper is not the problem.** It accounts for only about 0.2 µs of the 3 µs, so calling `cKDTree` directly would not rescue the loop.
- **A simple model explains the results:** loop / batch ≈ (fixed cost per crossing + work) / work.
  - Radius: (3.0 + 2.6) / 2.6 ≈ 2.2×, against 2.4× measured.
  - Plane: about 450 ns / 5.7 ns ≈ 79×, against 78.7× measured.
- **The factor depends on neighbour count.** In an r sweep at 100k comparing B with C:

| r | Mean neighbours | B/C |
|---|---|---|
| 0.10 m | 3.2 | 3.1× |
| 0.25 m | 17.3 | 2.4× |
| 0.50 m | 76.5 | 1.8× |
| 1.00 m | 320 | 1.5× |

  More work per call makes the cliff smaller.

## Is "two orders of magnitude" supported?
- **Neighbour search: no.** Crossing the boundary N times instead of once on a single thread costs 2.2–3.0× (radius) and 4.8–6.1× (kNN).
- **Largest honest neighbour-search figures:**
  - Loop vs batched on all cores: 15–17× (radius) and about 40× (kNN).
  - Pure Python vs batched on all cores: 35–44× (SciPy) and 48× (Open3D) at 1M.
- **Arithmetic: close, but not 100×.** The plane-distance loop vs the vectorised version is 77–79× at 100k and 1M. Only the upper IQR bound at 100k goes past 100×.
- **Defensible slide wording:** "about 80×" or "almost two orders of magnitude" for per-point arithmetic, and "2–5×, or 40× once you use all cores" for KD-tree queries.

## Recommended framing for the slides
- **Title:** "Cross the boundary once, not N times."
- **Core idea:** every trip from Python into C++ has a fixed cost: about 3 µs for a SciPy KD-tree call, about 1 µs for Open3D, and about 0.1 µs per NumPy scalar operation. How steep the cliff is depends on that cost divided by the work done per trip.
- **Two-panel chart** (native bar chart, log axis, 1M points, threads stated on the slide):
  1. Ground-plane distance: loop 450 ms vs vectorised 5.7 ms, **79×**.
  2. kNN k=16: loop 14.9 s, one call 3.1 s, `workers=-1` 0.38 s, so **4.8×, then ×8 more, 40× in total**.
- **Punchline:** "a C++ library inside a Python for-loop is still a Python for-loop": A vs B is only 2.3×.
- **Second lever:** only the batched form can use `workers=-1`. That gave 6.6–8.2× on 8 cores / 16 threads, below linear scaling because of boost and SMT.
- **Recommended N:** **1M** for slide numbers. That is realistic scale, larger than the 32 MB L3 cache, and gives times people can feel (15 s vs 0.4 s). Use **100k** for any live demo (kNN: 1.35 s vs 0.034 s). For radius count with the real data, re-measure with the real r and density, because the factor moves with neighbour count.

## Things that could make the comparison unfair, and mitigations
1. **Background load.** Other investigators were running on the same machine: load average 2.2–5.7, and one foreign Python process at 100% during the 1M runs. 1M radius IQRs reached 35% (D: 0.36 s IQR on a 0.49 s median).
   - I re-ran the 1M radius block twice, unpinned and pinned. The ratios held (B/C 2.2–2.3×, C/D 6.6–8.0×) while absolute times moved 10–20%.
   - For the real run: idle machine, no browser or indexers, and keep the load-average and temperature snapshots that the script already records.
2. **Hidden threading.**
   - `workers=-1` gives CPU/wall 10.5–12.7.
   - Open3D tensor NNS is multi-threaded by default (TBB, CPU/wall 9–12). `set_max_threads(1)` brings it to 1.00.
   - NumPy `@` runs on OpenBLAS threads at 1M.
   - So E1 vs E2 (8–15×) mixes the boundary effect with parallelism. Compare with equal threads, use E2_1t, or set `OPENBLAS_NUM_THREADS=1`. Always print the thread count on the slide.
3. **CPU frequency and SMT.** Boost is on, so single-thread runs clock higher than all-core runs, which understates C/D. The 16 threads share 8 cores. Interleaved repeats spread the drift.
   - Disabling boost needs root: **not done**. That is a decision for the real run.
4. **Warm caches.** At 10k the data fits in cache, so per-point batched cost is 1.8 µs, against 3.0–3.2 µs at 1M. The single-point `timeit` numbers are also hot-cache: Open3D shows 1.41 µs per call in `timeit` but 2.5 µs per point in the loop. Quote slide numbers from N ≥ 1M and treat the microbenchmarks as lower bounds.
5. **Algorithm parity.** A uses a grid rather than a tree. B vs C is the clean comparison because the kernel is identical and only the number of crossings differs. Index builds are excluded everywhere.
6. **Pilot artefacts.**
   - The 10k scene has no trees.
   - The plane's x-slope drops the inlier fraction to 2% at 1M. Timing is unaffected because the timed code has no branching.
   - GC stays on during runs, which is realistic.

## Verified gotchas (Open3D 0.20.0, NumPy 2.5.3)
- **`remove_radius_outlier(nb_points=5, radius=r)` threshold:** it keeps exactly the points whose SciPy count (which includes the point itself) is greater than `nb_points`, i.e. at least `nb_points` other points. Checked on the 1M cloud.
- **Docstring return order is wrong:** Open3D `NearestNeighborSearch.fixed_radius_search` returns **(indices, distances, splits)**, but its docstring's Returns section lists (indices, splits, distances). Checked against the output dtypes and shapes.
- **Loop style:** inside the loop, `len(tree.query_ball_point(p, r))` is 5–25% slower than `return_length=True`. Iterating over ndarray rows costs 42 ns per row, compared with 3.7 ns over a list.

**UNVERIFIED (left open for the real run):** behaviour with boost disabled, behaviour on the real dataset's density, and free-threaded Python.