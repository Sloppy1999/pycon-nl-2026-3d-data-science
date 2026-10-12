"""Performance cliff on the AHN5 crop: crossing into compiled code once per point vs once for all points.

    uv run python bench/bench_cliff.py --final            # idle machine; writes results/bench_cliff.json
    uv run python bench/bench_cliff.py --final --force    # run even if the 1-minute load average is > 1.0
    uv run python bench/bench_cliff.py --smoke --out DIR/bench_cliff_smoke.json [--n 20000] [--runs 2]

Data: data/utrecht_jaarbeurs_200m.laz, all 722 961 points in --final, local origin (las.xyz - header.mins,
exactly as on slide 8; laspy returns that array Fortran-ordered and it is used as is).

Plane block (slides 16 to 18). Plane = Open3D segment_plane on the whole crop, seeded, probability=1.0.
  loop_numpy_rows     the slide region of snippets/s16_loop.py, verbatim, compiled as a function body
  loop_python_floats  the same code on P.tolist() (Python floats; conversion not timed, see sensitivity.tolist)
  vectorised          the slide region of snippets/s16_vec.py, verbatim (element-wise, NOT the @ operator)
  np.array_equal(loop_numpy_rows, vectorised) is asserted; the other equalities are recorded.
  sensitivity: the same pair on a C-contiguous copy, `x, y, z = p` unpacking, and the tolist() cost.
kNN block (slide 18, B4). SciPy KDTree on the same points (build timed separately, never inside a query).
  loop          for every point: tree.query(p, k=16)
  one_call_1t   tree.query(P, k=16, workers=1)
  one_call_all  tree.query(P, k=16, workers=-1); threads = worker threads observed in /proc/self/task
  per_query_us_far / _far_knn / _typical: timeit per call (see knn.per_query_desc in the output).
Protocol: per block, `warmup` runs of each variant then `runs` timed runs, all in a seeded random order per
round; gc.collect() before every run (GC stays on during it); wall = time.perf_counter, CPU =
time.process_time (whole process, so CPU/wall > 1 shows threads); statistic: median and IQR
(numpy.percentile, linear). Factors: median ratio, iqr_low = q1(slow)/q3(fast), iqr_high = q3(slow)/q1(fast).
"""

from __future__ import annotations

import argparse
import gc
import os
import sys
import threading
import time
import timeit
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import conditions as cond  # noqa: E402
from _common import (DATA_CROP, RESULTS, SNIPPETS, check_budget, factor, rel, region_function,  # noqa: E402
                     guard_out, timing_stats, write_json)

SEED = 20261015                   # interleaving order and smoke subsample
PLANE_FIT = {"distance_threshold": 0.3, "ransac_n": 3, "num_iterations": 1000, "probability": 1.0, "seed": 0}
K = 16
R_FAR = 0.5                       # metres; radius / distance bound of the "far" queries
FAR_OFFSET = -1.0e4               # far point = local origin + (-10 km, -10 km, -10 km): nothing within R_FAR
LOAD_LIMIT = 1.0
FINAL_RUNS, FINAL_WARMUP = 7, 1


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def run_block(title: str, variants: list[tuple[str, object, int]], runs: int, warmup: int,
              rng: np.random.Generator) -> tuple[dict, dict, dict]:
    """variants: (name, fn, threads). Returns stats per name, warm-up outputs, before/after snapshots."""
    names = [v[0] for v in variants]
    fns = {v[0]: v[1] for v in variants}
    threads = {v[0]: v[2] for v in variants}
    before = cond.snapshot()
    outputs, warm = {}, {n: [] for n in names}
    for w in range(warmup):
        for j in rng.permutation(len(names)):
            name = names[j]
            gc.collect()
            t0 = time.perf_counter()
            out = fns[name]()
            warm[name].append(time.perf_counter() - t0)
            if w == 0:
                outputs[name] = out
            del out
    log(f"{title}: warm-up done " + ", ".join(f"{n} {warm[n][0]*1e3:.1f} ms" for n in names))
    wall = {n: [] for n in names}
    cpu = {n: [] for n in names}
    for r in range(runs):
        for j in rng.permutation(len(names)):
            name = names[j]
            gc.collect()
            c0 = time.process_time()
            t0 = time.perf_counter()
            out = fns[name]()
            t1 = time.perf_counter()
            c1 = time.process_time()
            del out                                   # freed outside the timed region, for every variant
            wall[name].append(t1 - t0)
            cpu[name].append(c1 - c0)
        log(f"{title}: round {r + 1}/{runs} done")
    after = cond.snapshot()
    res = {}
    for n in names:
        s = timing_stats(wall[n], threads[n])
        s["cpu_over_wall_median"] = float(np.median(np.array(cpu[n]) / np.array(wall[n])))
        s["warmup_ms"] = [round(x * 1e3, 6) for x in warm[n]]
        res[n] = s
        log(f"  {n:<32s} median {s['median_ms']:11.3f} ms  IQR [{s['q1_ms']:.3f}, {s['q3_ms']:.3f}]"
            f"  cpu/wall {s['cpu_over_wall_median']:.2f}")
    return res, outputs, {"before": before, "after": after}


def threads_during(fn) -> tuple[object, int]:
    """Run fn once while sampling /proc/self/task; return its output and the peak number of extra threads."""
    def count() -> int:
        return len(os.listdir("/proc/self/task"))
    stop, peak = threading.Event(), [0]

    def sample():
        while not stop.is_set():
            peak[0] = max(peak[0], count())
            time.sleep(0.0002)
    th = threading.Thread(target=sample, daemon=True)
    th.start()
    time.sleep(0.01)
    base = count()                                     # includes the sampler thread
    out = fn()
    stop.set()
    th.join()
    return out, max(peak[0] - base, 0)


def per_call_us(stmt: str, env: dict, number: int, per: int = 1, repeat: int = 7) -> dict:
    """timeit.repeat (gc disabled by timeit), `number` executions per repeat, `per` calls per execution."""
    t = timeit.repeat(stmt, globals=env, number=number, repeat=repeat)
    us = [x / (number * per) * 1e6 for x in t]
    return {"median_us": float(np.median(us)), "min_us": float(min(us)), "max_us": float(max(us)),
            "repeat": repeat, "calls_per_repeat": number * per, "stmt": stmt}


def knn_loop(tree, P, k):
    out = np.empty((len(P), k), dtype=np.intp)
    for i, p in enumerate(P):
        out[i] = tree.query(p, k=k)[1]
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--smoke", action="store_true", help="small N, few runs; never writes to results/")
    mode.add_argument("--final", action="store_true", help="full crop, 1 warm-up + 7 runs, results/bench_cliff.json")
    ap.add_argument("--force", action="store_true", help=f"--final even if the 1-minute load average > {LOAD_LIMIT}")
    ap.add_argument("--out", type=Path, help="output JSON (required for --smoke)")
    ap.add_argument("--n", type=int, default=20_000, help="--smoke only: number of points (seeded subsample)")
    ap.add_argument("--runs", type=int, default=2, help="--smoke only: timed runs per variant")
    ap.add_argument("--date-utc", help="UTC timestamp to record (default: taken at start)")
    args = ap.parse_args()

    date_utc = args.date_utc or cond.utc_now()
    load_before = cond.load_avg()
    t_start = time.perf_counter()
    if args.final:
        if load_before[0] > LOAD_LIMIT and not args.force:
            print(f"refusing --final: 1-minute load average {load_before[0]} > {LOAD_LIMIT} "
                  "(close other work and retry, or pass --force)", file=sys.stderr)
            return 3
        out_path = args.out or RESULTS / "bench_cliff.json"
        runs, warmup, n_sample, far_calls = FINAL_RUNS, FINAL_WARMUP, 20_000, 20_000
    else:
        if args.out is None:
            ap.error("--smoke needs --out (smoke results never go to results/)")
        out_path = guard_out(args.out, final=False)
        runs, warmup, n_sample, far_calls = args.runs, 1, 2_000, 2_000

    import laspy
    import open3d as o3d
    from scipy.spatial import KDTree
    o3d.utility.set_verbosity_level(o3d.utility.VerbosityLevel.Error)

    budgets = {"s16_loop.py": check_budget(SNIPPETS / "s16_loop.py", 5, 35),
               "s16_vec.py": check_budget(SNIPPETS / "s16_vec.py", 3, 35)}
    f_loop, src_loop = region_function(SNIPPETS / "s16_loop.py", ("P", "plane"), "h")
    f_vec, src_vec = region_function(SNIPPETS / "s16_vec.py", ("P", "plane"), "h")
    f_unpack, src_unpack = region_function(SNIPPETS / "s16_loop.py", ("P", "plane"), "h",
                                           replace=("x, y, z = p[0], p[1], p[2]", "x, y, z = p"))

    # ---- data: whole crop, local origin, exactly as on slide 8
    las = laspy.read(DATA_CROP)
    P_full = las.xyz - las.header.mins
    n_file = len(P_full)
    if args.final:
        P = P_full
    else:
        idx = np.sort(np.random.default_rng(SEED).choice(n_file, min(args.n, n_file), replace=False))
        P = np.asfortranarray(P_full[idx])               # same memory layout as the full array
    N = len(P)
    layout = "F-contiguous" if P.flags.f_contiguous else ("C-contiguous" if P.flags.c_contiguous else "strided")
    log(f"{'FINAL' if args.final else 'SMOKE'}: N={N} of {n_file}, layout {layout}, load {load_before}")

    # ---- plane from a seeded RANSAC on the whole crop (also in smoke mode, so coefficients match)
    pcd = o3d.geometry.PointCloud(o3d.utility.Vector3dVector(P_full))
    o3d.utility.random.seed(PLANE_FIT["seed"])
    t0 = time.perf_counter()
    coeffs, inliers = pcd.segment_plane(PLANE_FIT["distance_threshold"], PLANE_FIT["ransac_n"],
                                        PLANE_FIT["num_iterations"], PLANE_FIT["probability"])
    fit_s = time.perf_counter() - t0
    plane = tuple(float(v) for v in coeffs)
    n_inliers = len(inliers)
    del pcd, inliers
    log(f"plane {plane} ({n_inliers} inliers, {fit_s:.2f} s)")

    rng = np.random.default_rng(SEED)

    # ---- plane block
    L = P.tolist()
    PC = np.ascontiguousarray(P)
    plane_variants = [
        ("loop_numpy_rows", lambda: f_loop(P, plane), 1),
        ("loop_python_floats", lambda: f_loop(L, plane), 1),
        ("vectorised", lambda: f_vec(P, plane), 1),
        ("loop_numpy_rows_c_contiguous", lambda: f_loop(PC, plane), 1),
        ("vectorised_c_contiguous", lambda: f_vec(PC, plane), 1),
        ("loop_numpy_rows_unpack", lambda: f_unpack(P, plane), 1),
        ("tolist", lambda: P.tolist(), 1),
    ]
    ps, pout, psnap = run_block("plane", plane_variants, runs, warmup, rng)
    ref = pout["vectorised"]
    equal = bool(np.array_equal(pout["loop_numpy_rows"], ref))
    eq = {k: bool(np.array_equal(pout[k], ref)) for k in
          ("loop_python_floats", "loop_numpy_rows_c_contiguous", "vectorised_c_contiguous", "loop_numpy_rows_unpack")}
    matmul = np.abs(P @ np.array(plane[:3]) + plane[3])
    matmul_equal, matmul_maxdiff = bool(np.array_equal(matmul, ref)), float(np.abs(matmul - ref).max())
    del pout, ref, matmul, L, PC
    gc.collect()
    if not equal:
        raise SystemExit("ASSERTION FAILED: loop over NumPy rows and the vectorised expression differ")

    plane_res = {
        "n": N,
        "loop_numpy_rows": ps["loop_numpy_rows"],
        "loop_python_floats": ps["loop_python_floats"],
        "vectorised": ps["vectorised"],
        "equal": equal,
        "factor": factor(ps["loop_numpy_rows"], ps["vectorised"]),
        "factor_python_floats": factor(ps["loop_python_floats"], ps["vectorised"]),
        "per_step_ns_loop": ps["loop_numpy_rows"]["median_ms"] * 1e6 / N,
        "per_point_ns_vectorised": ps["vectorised"]["median_ms"] * 1e6 / N,
        "equal_python_floats": eq["loop_python_floats"],
        "per_step_ns_python_floats": ps["loop_python_floats"]["median_ms"] * 1e6 / N,
        "coefficients": list(plane),
        "plane_fit": {**PLANE_FIT, "on": f"whole crop ({n_file} points)", "inliers": n_inliers,
                      "seconds": fit_s, "call": "pcd.segment_plane(0.3, 3, 1000, 1.0) after "
                                                "o3d.utility.random.seed(0)"},
        "array": {"how": "las.xyz - las.header.mins", "dtype": str(P.dtype), "layout": layout,
                  "smoke_subsample": None if args.final else f"seeded ({SEED}) random {N} rows, file order"},
        "snippets": {"loop": {"file": "snippets/s16_loop.py", "source": src_loop, "budget": budgets["s16_loop.py"]},
                     "vectorised": {"file": "snippets/s16_vec.py", "source": src_vec,
                                    "budget": budgets["s16_vec.py"]},
                     "run_as": "slide region verbatim, compiled as a function body f(P, plane) returning h"},
        "matmul_reference": {"expr": "np.abs(P @ (a, b, c) + d)", "equal": matmul_equal,
                             "max_abs_diff": matmul_maxdiff, "note": "not used in any factor"},
        "sensitivity": {
            "loop_numpy_rows_c_contiguous": ps["loop_numpy_rows_c_contiguous"],
            "vectorised_c_contiguous": ps["vectorised_c_contiguous"],
            "factor_c_contiguous": factor(ps["loop_numpy_rows_c_contiguous"], ps["vectorised_c_contiguous"]),
            "loop_numpy_rows_unpack": ps["loop_numpy_rows_unpack"],
            "unpack_source": src_unpack,
            "factor_unpack_vs_loop": factor(ps["loop_numpy_rows_unpack"], ps["loop_numpy_rows"]),
            "tolist": ps["tolist"],
            "equal": eq,
            "note": "C-contiguous = np.ascontiguousarray(P); unpack = the loop with `x, y, z = p`; "
                    "tolist = cost of P.tolist(), excluded from loop_python_floats",
        },
        "snapshots": psnap,
    }

    # ---- kNN block
    t0 = time.perf_counter()
    tree = KDTree(P)
    build_s = time.perf_counter() - t0
    _, extra_threads = threads_during(lambda: tree.query(P, k=K, workers=-1))
    threads_all = extra_threads if extra_threads > 1 else (os.cpu_count() or 1)
    threads_src = ("worker threads observed in /proc/self/task during a workers=-1 call"
                   if extra_threads > 1 else "os.cpu_count() (no threads observed: call too short to sample)")
    knn_variants = [
        ("loop", lambda: knn_loop(tree, P, K), 1),
        ("one_call_1t", lambda: tree.query(P, k=K, workers=1)[1], 1),
        ("one_call_all", lambda: tree.query(P, k=K, workers=-1)[1], threads_all),
    ]
    ks, kout, ksnap = run_block("knn", knn_variants, runs, warmup, rng)
    eq_loop_1t = bool(np.array_equal(kout["loop"], kout["one_call_1t"]))
    eq_1t_all = bool(np.array_equal(kout["one_call_1t"], kout["one_call_all"]))
    del kout
    gc.collect()

    p_far = np.full(3, FAR_OFFSET)
    sample = P[np.random.default_rng(SEED + 1).choice(N, min(n_sample, N), replace=False)]
    env = {"tree": tree, "p_far": p_far, "r": R_FAR, "S": sample, "k": K}
    far_ball = per_call_us("tree.query_ball_point(p_far, r, return_length=True)", env, far_calls)
    far_knn = per_call_us("tree.query(p_far, k=k, distance_upper_bound=r)", env, far_calls)
    typical = per_call_us("for p in S: tree.query(p, k=k)", env, 1, per=len(sample))
    far_answer = {"ball_count": int(tree.query_ball_point(p_far, R_FAR, return_length=True)),
                  "knn_all_inf": bool(np.isinf(tree.query(p_far, k=K, distance_upper_bound=R_FAR)[0]).all())}
    log(f"per call: far ball {far_ball['median_us']:.2f} us, far knn {far_knn['median_us']:.2f} us, "
        f"typical knn {typical['median_us']:.2f} us")

    knn_res = {
        "n": N, "k": K,
        "loop": ks["loop"], "one_call_1t": ks["one_call_1t"], "one_call_all": ks["one_call_all"],
        "factor_loop_vs_1t": factor(ks["loop"], ks["one_call_1t"]),
        "factor_loop_vs_all": factor(ks["loop"], ks["one_call_all"]),
        "factor_1t_vs_all": factor(ks["one_call_1t"], ks["one_call_all"]),
        "per_query_us_far": far_ball["median_us"],
        "per_query_us_typical": typical["median_us"],
        "per_query_us_far_knn": far_knn["median_us"],
        "per_point_us_loop": ks["loop"]["median_ms"] * 1e3 / N,
        "per_point_us_one_call_1t": ks["one_call_1t"]["median_ms"] * 1e3 / N,
        "per_query_desc": {
            "per_query_us_far": f"scipy.spatial.KDTree.query_ball_point(p_far, r={R_FAR}, return_length=True), "
                                f"p_far = local origin + ({FAR_OFFSET:g}, {FAR_OFFSET:g}, {FAR_OFFSET:g}) m, "
                                "answer 0 neighbours (no tree work beyond the root check); "
                                "median over 7 timeit repeats of per-call time, gc disabled by timeit",
            "per_query_us_far_knn": f"KDTree.query(p_far, k={K}, distance_upper_bound={R_FAR}), same p_far, "
                                    "answer: no neighbour (all distances inf); fixed cost of the call the loop uses",
            "per_query_us_typical": f"KDTree.query(p, k={K}) looped over {len(sample)} crop points "
                                    f"(seeded random sample, seed {SEED + 1}); median per call over 7 repeats",
            "far": far_ball, "far_knn": far_knn, "typical": typical, "far_answer": far_answer,
        },
        "equal_loop_vs_1t": eq_loop_1t,
        "equal_1t_vs_all": eq_1t_all,
        "build_s": build_s,
        "threads_all_source": threads_src,
        "tree": "scipy.spatial.KDTree(P) default leafsize, built once, build excluded from every timing",
        "snapshots": ksnap,
    }

    load_after = cond.load_avg()
    statistic = "median and IQR (numpy.percentile, linear) of wall time over the timed runs"
    result = {
        "label": "FINAL" if args.final else "SMOKE (not for the deck)",
        "conditions": cond.collect(
            data=rel(DATA_CROP), n=N, runs=runs, warmup=warmup, statistic=statistic, date_utc=date_utc,
            load_avg_before=load_before, load_avg_after=load_after,
            extra={"load_check": {"limit_1min": LOAD_LIMIT, "value": load_before[0], "forced": bool(args.force),
                                  "applies_to": "--final"},
                   "order": f"interleaved: seeded (numpy default_rng {SEED}) permutation of the variants per round",
                   "gc": "gc.collect() before every run, GC enabled during runs; timeit disables GC",
                   "timers": "wall time.perf_counter, CPU time.process_time (whole process)",
                   "pinning": "none (no taskset); boost and SMT as reported"}),
        "plane": plane_res,
        "knn": knn_res,
        "script": "bench/bench_cliff.py",
        "runtime_s": time.perf_counter() - t_start,
    }
    path = write_json(out_path, result, final=bool(args.final))
    log(f"plane factor {plane_res['factor']['median']:.1f}x (IQR {plane_res['factor']['iqr_low']:.1f} to "
        f"{plane_res['factor']['iqr_high']:.1f}), kNN loop vs 1t {knn_res['factor_loop_vs_1t']['median']:.1f}x, "
        f"vs all {knn_res['factor_loop_vs_all']['median']:.1f}x ({threads_all} threads)")
    log(f"wrote {path} in {result['runtime_s']:.0f} s; load before {load_before}, after {load_after}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
