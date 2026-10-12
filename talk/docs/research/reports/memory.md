# PILOT report: fitting millions of points in RAM (synthetic data only)

Every number here is a PILOT measurement on synthetic data, except the spec values and the claims I quote from other sources. Peak and retained memory are the median of 3 repeats. Each case ran in a fresh subprocess, and the min–max spread was under 1% at 10M and 30M. Peak RSS was measured by resetting the kernel high-water mark (`/proc/self/clear_refs` = 5) and then reading VmHWM and VmRSS. The tables give bytes per point as a delta over the state just before each step.

**Run conditions:**
- **Machine and software (logged by the script):** Ryzen 7 5700X (16 threads), 31.3 GiB RAM, Omarchy, kernel 7.2.5, CPython 3.13.15. numpy 2.5.3, laspy 2.7.0, lazrs 0.8.2, open3d 0.20.0, pyvista 0.49.0, vtk 9.7.1.
- **Allocator setting:** `MALLOC_MMAP_THRESHOLD_=1048576`, so large blocks go back to the OS when freed.
- **Timings are rough:** other agents were running at the same time (load average about 2–5).

## 1. LAS point record sizes (primary source)

**Source:** ASPRS LAS 1.4 R16, revision date 27 Aug 2025, from https://github.com/ASPRSorg/LAS/releases/download/1.4.R16/LAS_1_4_r16.pdf. The old asprs.org R15 PDF link now returns 404.

| PDRF | Bytes (minimum) | GPS time | RGB | NIR | Wave packet |
|---|---|---|---|---|---|
| 0 | 20 | – | – | – | – |
| 1 | 28 | ✓ | – | – | – |
| 2 | 26 | – | ✓ | – | – |
| 3 | 34 | ✓ | ✓ | – | – |
| 4 | 57 | ✓ | – | – | ✓ |
| 5 | 63 | ✓ | ✓ | – | ✓ |
| 6 | 30 | ✓ (mandatory) | – | – | – |
| 7 | 36 | ✓ | ✓ | – | – |
| 8 | 38 | ✓ | ✓ | ✓ | – |
| 9 | 59 | ✓ | – | – | ✓ |
| 10 | 67 | ✓ | ✓ | ✓ | ✓ |

- **Extra bytes:** these are minimum sizes. The "Point Data Record Length" field can be larger and carry extra bytes.
- **Coordinates:** X, Y and Z are int32 values, and the spec gives `coordinate = record × scale + offset` (Eq. 1).
- **Colour:** RGB and NIR are uint16 and "should always be normalized to 16 bit values" (spec example: multiply 8-bit values by 256).
- **laspy agrees:** `laspy.PointFormat(i).size` returns exactly the sizes in the table.
- **LAS 1.5 R00 (Aug 2025):** same repository, release 1.5.R00. Its changelog says "Removed support for legacy Point Data Record Formats 0-5."
- **LAZ:** this format is not part of the ASPRS spec. laszip.org says it "is completely lossless", produces files "only 7-20% of the original size", and is Apache 2.0 licensed. I treat the 7–20% as a vendor claim and did not verify it on real data.

## 2. File sizes (synthetic, PDRF 7, 1 mm scale)

| N | LAS bytes | LAZ bytes | LAZ / LAS |
|---|---|---|---|
| 1M | 36,000,375 | 13,232,724 | 0.368 |
| 10M | 360,000,375 | 131,830,028 | 0.366 |
| 30M | 1,080,000,375 | 395,599,065 | 0.366 |
| 1M, point order shuffled | – | 16,445,581 | 0.457 |

- **Synthetic data compresses worse than real data probably does:** RGB and intensity carry independent Gaussian noise per point.
- **Point order matters:** with the same points in random order, the LAZ file was 24% larger.
- **Scene:** a 20 m wide street corridor with road, sidewalks and curb, two facades with recessed windows, trees, lamp poles and parked cars. Density falls off with distance from the scanner path and with height. The file is in acquisition-like order. Density is 1e5 points per metre of street, so 10M points is 100 m of street. This density is my choice, not a measured real-world figure.

## 3. Bytes per point by representation (N = 30M unless noted)

| Representation | Theory | Peak | Retained | Time |
|---|---|---|---|---|
| `laspy.read` of LAS | 36 | 36.0 | 36.0 | 0.28 s |
| `laspy.read` of LAZ, default LazrsParallel backend | 36 | **50.7** | 37.2 | 1.4 s |
| `laspy.read` of LAZ, single-threaded Lazrs backend | 36 | 36.1 | 36.1 | 10.8 s |
| (b) float64 xyz via `np.column_stack((las.x,las.y,las.z))` | +24 | **+48.0** | +24.0 | 0.5 s |
| (b) float64 xyz, preallocated then filled per column | +24 | +32.0 | +24.0 | 0.5 s |
| float32 xyz after subtracting `header.mins` | +12 | +20.0 | +12.0 | 0.4 s |
| (c) Open3D points | +24 | **+48.0** | +24.0 | 0.24 s |
| (c) Open3D points + colors | +48 | +72.0 | +48.0 | 0.5 s |
| (c) Open3D points + colors + normals | +72 | +96.0 | +72.0 | 0.7 s |
| Open3D `estimate_normals` (KNN 16), 10M | +24 | **+114.8** | +24.1 | 10.6 s |
| Open3D legacy `voxel_down_sample(0.1)` | – | +26.7 | +24.5 (output is only about 2.6) | 2.8 s |
| Open3D tensor PointCloud from float32 numpy | 0 (zero-copy) | 0.0 | 0.0 | – |
| Open3D tensor `voxel_down_sample(0.1)` | – | **+105.5** | about +17 | 3.9 s |
| (d) PyVista `PolyData(xyz)`, float64 or float32 | +8 | +8.0 | +8.0 | 0.03 s |
| Chunk-filled float32 xyz + uint8 class, nothing else kept | 13 | 17.1 | 15.9 | 2.8 s |
| Naive pipeline: read LAZ, float64 xyz and RGB, Open3D, voxel 0.1 | – | **161.9** (4.6 GiB) | 160.4 | 6.0 s |
| Load everything, then numpy voxel 0.1 | – | 109.2 (3.1 GiB) | 73.2 | 5.4 s |
| **(e) Chunked voxel 0.1, 1M chunks, the snippet below** | – | **413 MiB total** | 84 MiB | 6.0 s |
| Chunked voxel, searchsorted merge variant | – | 251 MiB total | 84 MiB | 6.3 s |
| Chunked voxel, `np.isin` + `np.union1d` merge (main run) | – | 488 MiB total | 329 MiB | **33.4 s** |

**PyVista detail:** the points share memory with the numpy array (`np.shares_memory` returned True). The extra 8 B/pt are vertex cells: VTK 9.7.1 reports `IsStorage64Bit()` = False, so offsets plus connectivity cost 2 × int32. The JSON field `theory_B_per_pt=16` assumed int64 storage and is wrong; 8 is the correct value.

**Cross-check at smaller N:** at 1M and 10M, every per-point value agreed with the 30M values within about 1 B/pt. The exception is the LAZ read, where fixed overhead dominates at 1M (peak 93, retained 72 B/pt).

### Chunk size (10M points, LAZ, `np.isin` merge)

| Chunk size | Peak | Time |
|---|---|---|
| 250k | 189 MiB | 10.6 s |
| 1M | 252 MiB | 5.2 s |
| 5M | 682 MiB | 2.7 s |

### How chunks were merged, and correctness

- **Within a chunk:** `np.unique(key, return_index=True)` keeps the first point in each voxel.
- **Main-run merge:** keep a sorted array of voxel keys already taken. Each chunk adds only voxels not seen yet, so the result is the global first point per voxel in file order.
- **Snippet merge:** append each chunk's survivors, then run one global `np.unique` at the end. Its stable sort means the earliest chunk wins.
- **Check:** the snippet run gave the same keys, points and classes as the load-everything version (verified at 1M and 10M).
- **Duplicate overhead:** survivors summed over chunks were 1.03× the final count. That is low because the file is in spatial order; on unordered files the count would grow (not measured).

## 4. Voxel size effect (f), 10M points (100 m street)

| Voxel | Points kept (numpy first point) | Fraction | Open3D count (centroid) |
|---|---|---|---|
| 0.02 m | 8,449,388 | 84.5% | 8,462,141 |
| 0.05 m | 4,220,429 | 42.2% | 3,565,485 |
| 0.10 m | 1,433,152 | 14.3% | 1,119,821 |
| 0.20 m | 239,461 | 2.4% | 340,115 |
| 0.50 m | 32,713 | 0.33% | 33,101 |
| 1.00 m | 7,358 | 0.074% | 8,075 |

- **Class balance shifts:** at 0.1 m the share kept is 7.5% of ground, 17.5% of building, 31.5% of vegetation, 12.6% of cars and 1.8% of poles.
- **Density becomes more even:** I measured how unevenly ground points spread over 1 m² cells (coefficient of variation; lower is more even).

| Ground points | CV across 1 m² cells |
|---|---|
| Original | 0.515 |
| Random subsample, same count as the voxel result | 0.521 |
| Voxel 0.1 m | 0.295 |

## 5. Where memory runs out (from measured peaks; nominal GiB with no OS headroom)

| Pipeline | B/pt | 8 GiB | 16 GiB | 32 GiB |
|---|---|---|---|---|
| Naive pipeline (measured) | 162 | 53M pts (0.5 km) | 106M (1.1 km) | 212M (2.1 km) |
| Full Open3D state with normals (summed, not measured as a whole) | 247 | 35M (0.35 km) | 70M (0.7 km) | 139M (1.4 km) |
| `laspy.read` of LAZ | 50.7 | 170M | 339M | 678M |
| `laspy.read` of LAS | 36 | 239M | 477M | 954M |
| float32 xyz + class | 17.1 | 502M | 1.0G | 2.0G |

- **km is at the synthetic density only.** How many points a typical street scan has is UNVERIFIED.
- **Chunked downsampling does not hit this ceiling:** its peak stayed at 0.25–0.41 GiB for 30M points and grows with output size, not with N.

## 6. Trade-offs

| Strategy | Gains (measured) | Costs and limits |
|---|---|---|
| Chunked read | Peak is set by chunk size plus output: 413 MiB vs 3.1 GiB for load-everything, same result | Only works for per-point or streaming operations. Normals, ground removal and clustering need spatial neighbours across chunk edges. Chunks follow file order, which is spatial only if the file is sorted. |
| Voxel downsampling | Output is set by surface area and voxel size, not N (0.1 m keeps 14%). Evens out density. | Thin objects shrink most (poles 1.8% kept). Class balance changes. First-point keeps real attributes; Open3D's centroid creates new coordinates and averaged colours. Counts depend on where the grid starts. |
| Random subsampling | Simple, can stream, gives an exact target count | Keeps the scanner's density bias (CV 0.521) and does not bound memory per area |
| Spatial tiling | Needed for neighbourhood algorithms | Needs pre-tiled files or an index. `laspy.CopcReader.query(bounds, resolution, level)` exists in 2.7.0 (I checked the API; not measured). Overlap costs not measured. |
| float32 with an offset | Halves xyz (12 vs 24 B/pt). Max error 3.8 µm over 100 m. | Without the offset, error reaches 0.25 m (see gotcha 1). Open3D legacy goes back to float64 (24 B/pt). The tensor API is zero-copy but its voxel step peaks at 105 B/pt. |
| Keep only needed fields | 17 B/pt peak vs 60 B/pt retained for full record + float64 xyz | Have to re-read the file if you later need intensity or GPS time |

## 7. Snippet (11 lines, measured at 10M and 30M, matches the load-everything result)

```python
import laspy, numpy as np
v, keys, pts = 0.1, [], []                                             # voxel size in metres
with laspy.open("street.laz") as f:
    lo = f.header.mins; dims = ((f.header.maxs - lo) // v).astype(np.int64) + 1
    for c in f.chunk_iterator(1_000_000):
        xyz = np.column_stack((c.x, c.y, c.z)) - lo                    # float64, local frame
        ijk = (xyz // v).astype(np.int64).T                             # integer voxel coordinates
        k, first = np.unique(np.ravel_multi_index(ijk, dims), return_index=True)
        keys.append(k); pts.append(xyz[first].astype(np.float32))      # 1 point per voxel per chunk
_, first = np.unique(np.concatenate(keys), return_index=True)          # earliest chunk wins
points = np.concatenate(pts)[first]                                    # float32 local; world = points + lo
```

`ravel_multi_index` raises an error instead of silently wrapping if the header bounds are stale. That is a design choice; I did not test it with a bad header.

## 8. Possible gotchas I hit (CANDIDATES)

1. **float32 on world coordinates fails silently.** Northing around 5.8e6 m gave a max error of 0.25 m and easting 0.031 m. After subtracting `header.mins` the error was ≤ 3.8e-6 m.
2. **Hidden temporaries double the peak.** `np.column_stack` peaks at 2× its result (48 vs 24 B/pt), and Open3D `pcd.points = Vector3dVector(a)` also peaks at 2×. The cause is UNVERIFIED (probably temporary plus copy).
3. **Colours grow 4×.** LAS uint16 RGB (6 B/pt in the file) becomes 24 B/pt as float64 numpy plus 24 B/pt inside Open3D. You must also divide by 65535, not 255. How common files with un-normalised 8-bit RGB are is UNVERIFIED.
4. **The default parallel LAZ decoder costs memory.** It peaked at 1.4× the record size (50.7 vs 36 B/pt) but was 7.6× faster than single-threaded. A 2M-point probe showed 2–22 B/pt still held after `del`. The cause is UNVERIFIED.
5. **`decompression_selection` changed nothing I could see.** Asking for xy and z only still returned non-zero RGB and GPS time, yet it ran faster (0.67 s vs 1.42 s). Semantics UNVERIFIED.
6. **The merge method matters a lot.** Merging chunks with `np.isin` + `np.union1d` took 33 s at 30M, against about 6 s for the alternatives. It is also super-linear. The numpy docs say `isin` may pick a lookup-table method whose memory depends on the range of values; whether that caused it here is UNVERIFIED.
7. **Voxel counts depend on grid origin.** numpy and Open3D differ by up to 22% at 0.05–0.2 m, probably from flat synthetic ground meeting voxel boundaries. Separately, 1.4% of kept points changed voxel after a float32 round-trip, because millimetre coordinates fall exactly on 0.1 m boundaries.
8. **Downsampling skews class statistics.** At 0.1 m, 31.5% of vegetation survives against 7.5% of ground.
9. **Memory is not returned after downsampling.** After Open3D legacy `voxel_down_sample`, RSS stayed about 620 MiB above the 78 MiB output. Cause UNVERIFIED.
10. **The tensor API is zero-copy, but its voxel step is expensive:** a transient peak of 105 B/pt, about 4× the legacy API.
11. **PyVista shares memory with the numpy array**, so changing the array changes the mesh. It also adds 8 B/pt of vertex cells.
12. **Point order changes LAZ size by 24%.**
13. **On this machine `/tmp` is tmpfs,** so big LAS files written there use RAM even though process RSS does not show it.

## Files

- `scratchpad/memory/mem_pilot.py` — run with `all`, `extra`, `derive`, `gen`, `case` or `verify`
- `scratchpad/memory/mem_pilot_results.json` — run conditions, every repeat, medians, verify sweep, crossing points
- `scratchpad/memory/snippet_chunked_voxel.py`
- `scratchpad/memory/spec/LAS_1_4_r16.pdf`
- `scratchpad/memory/spec/LAS_1_5_r00.pdf`
- Logs: `run.log` and `run_extra.log`; one-off probes in `probe/`. The large data files have been deleted.

**Sources:**
- https://github.com/ASPRSorg/LAS/releases (1.4.R16, 1.5.R00)
- https://laszip.org/