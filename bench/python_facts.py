"""Which hand-offs between laspy, NumPy, Open3D and PyVista share memory, and which copy (new slide 8).

    uv run python bench/python_facts.py --final     # writes results/python_facts.json

Runs on the AHN5 crop (data/utrecht_jaarbeurs_200m.laz). Every claim on the slide is a check done here:

* ``las.xyz``: a fresh array on every access (two accesses share no memory), F-ordered (column-major)
* ``o3d.utility.Vector3dVector(xyz)``: always copies (changing the NumPy array afterwards does not change the
  point cloud); timed for float64 C-ordered, float64 F-ordered (as laspy returns it) and float32 input
* ``np.asarray(pcd.points)``: a writeable view on Open3D's own buffer (the buffer protocol: writing to it
  changes the point cloud)
* ``pv.PolyData(pts)``: shares memory with a C-ordered float64 (N, 3) array (and with the Open3D view)

Timings: 1 warm-up and 7 timed runs per variant, median and IQR (numpy.percentile, linear), wall time
(time.perf_counter), gc.collect() before every run. The script waits (up to 10 minutes) for the 1-minute load
average to drop below 1.0 before timing, and records it. Conditions: bench/conditions.py (same keys as
results/bench_cliff.json).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import DATA_CROP, RESULTS, factor, rel, timed, write_json  # noqa: E402
import conditions  # noqa: E402

RUNS, WARMUP = 7, 1
STAT = "median and IQR (numpy.percentile, linear) of wall time over the timed runs"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--final", action="store_true", help="write results/python_facts.json")
    ap.add_argument("--out", type=Path, default=RESULTS / "python_facts.json")
    args = ap.parse_args()

    import laspy
    import open3d as o3d
    import pyvista as pv

    o3d.utility.set_verbosity_level(o3d.utility.VerbosityLevel.Error)
    las = laspy.read(DATA_CROP)
    n = len(las.points)

    # --- laspy -> NumPy: las.xyz builds a new array on every access
    a1, a2 = las.xyz, las.xyz
    xyz_fresh = (a1 is not a2) and not np.shares_memory(a1, a2)
    xyz = las.xyz - las.header.mins                     # as on the Load slide
    facts = {
        "las_xyz": {"fresh_copy_each_access": bool(xyz_fresh), "f_contiguous": bool(a1.flags.f_contiguous),
                    "c_contiguous": bool(a1.flags.c_contiguous), "dtype": str(a1.dtype),
                    "nbytes_mb": a1.nbytes / 1e6},
        "local_xyz": {"f_contiguous": bool(xyz.flags.f_contiguous), "dtype": str(xyz.dtype)},
    }

    # --- NumPy -> Open3D: Vector3dVector copies
    pcd = o3d.geometry.PointCloud(o3d.utility.Vector3dVector(xyz))
    before = np.asarray(pcd.points)[0, 0]
    xyz[0, 0] += 1000.0
    after = np.asarray(pcd.points)[0, 0]
    xyz[0, 0] -= 1000.0
    v3d_copies = bool(before == after) and not np.shares_memory(np.asarray(pcd.points), xyz)
    facts["vector3dvector"] = {"copies": v3d_copies,
                               "check": "xyz[0, 0] += 1000 after the call leaves pcd.points[0][0] unchanged"}

    # --- Open3D -> NumPy: np.asarray(pcd.points) is a writeable view (buffer protocol)
    pts = np.asarray(pcd.points)
    old = pts[0, 0]
    pts[0, 0] = 12345.0
    seen = np.asarray(pcd.points)[0, 0]
    pts[0, 0] = old
    facts["asarray_points"] = {"view": bool(seen == 12345.0), "writeable": bool(pts.flags.writeable),
                               "owndata": bool(pts.flags.owndata),
                               "two_calls_share_memory": bool(np.shares_memory(np.asarray(pcd.points),
                                                                               np.asarray(pcd.points))),
                               "c_contiguous": bool(pts.flags.c_contiguous), "dtype": str(pts.dtype),
                               "check": "pts[0, 0] = 12345 changes pcd.points[0][0]"}

    # --- NumPy -> PyVista: PolyData shares memory with a C-ordered float64 array
    c_xyz = np.ascontiguousarray(xyz)
    poly_c = pv.PolyData(c_xyz)
    poly_f = pv.PolyData(xyz)
    poly_o3d = pv.PolyData(pts)
    facts["polydata"] = {"shares_memory_c_float64": bool(np.shares_memory(poly_c.points, c_xyz)),
                         "shares_memory_f_float64": bool(np.shares_memory(poly_f.points, xyz)),
                         "shares_memory_open3d_view": bool(np.shares_memory(poly_o3d.points, pts))}

    # --- timings (idle machine)
    load_before = conditions.wait_idle()
    snap_before = conditions.snapshot()
    f32 = xyz.astype(np.float32)
    t = {
        "v3d_float64_f": timed(lambda: o3d.utility.Vector3dVector(xyz), RUNS, WARMUP),
        "v3d_float64_c": timed(lambda: o3d.utility.Vector3dVector(c_xyz), RUNS, WARMUP),
        "v3d_float32": timed(lambda: o3d.utility.Vector3dVector(f32), RUNS, WARMUP),
        "las_xyz_access": timed(lambda: las.xyz, RUNS, WARMUP),
        "asarray_points": timed(lambda: np.asarray(pcd.points), RUNS, WARMUP),
        "polydata_c": timed(lambda: pv.PolyData(c_xyz), RUNS, WARMUP),
    }
    load_after = conditions.load_avg()
    facts["timings"] = t
    facts["factor_v3d_float32_vs_float64_c"] = factor(t["v3d_float32"], t["v3d_float64_c"])
    facts["factor_v3d_float32_vs_float64_f"] = factor(t["v3d_float32"], t["v3d_float64_f"])
    facts["n"] = n

    out = {
        "label": "FINAL" if args.final else "PILOT",
        "script": rel(Path(__file__)),
        "conditions": conditions.collect(
            data=rel(DATA_CROP), n=n, runs=RUNS, warmup=WARMUP, statistic=STAT,
            load_avg_before=load_before, load_avg_after=load_after,
            extra={"pyvista": conditions.ver("pyvista"), "snapshot_before": snap_before,
                   "snapshot_after": conditions.snapshot(),
                   "gc": "gc.collect() before every run", "timer": "time.perf_counter",
                   "load_check": {"limit_1min": 1.0, "waited_until": load_before}}),
        **facts,
    }
    if args.final:
        write_json(args.out, out, final=True)
        print("wrote", args.out)
    import json
    print(json.dumps({k: v for k, v in out.items() if k != "conditions"}, indent=1, default=str)[:4000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
