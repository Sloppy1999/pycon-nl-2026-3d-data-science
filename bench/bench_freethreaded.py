"""Does free-threaded Python save the slide-16 loop? -> results/bench_freethreaded.json

    uv run python bench/bench_freethreaded.py --ft PY_FT --gil PY_GIL --final

PY_FT and PY_GIL are the interpreters of two throw-away venvs with the same CPython release, one free-threaded
build (3.14t, GIL disabled) and one default build (GIL), each with numpy and laspy[lazrs] only (Open3D has no
wheel for 3.14t). Recreate them with uv:

    uv python install 3.14t 3.14
    uv venv --python 3.14t ft/.venv && VIRTUAL_ENV=ft/.venv uv pip install numpy "laspy[lazrs]"
    uv venv --managed-python --python 3.14 ft/.venv-gil && VIRTUAL_ENV=ft/.venv-gil uv pip install numpy "laspy[lazrs]"

Each interpreter runs this file with ``--worker`` and times, on the AHN5 crop (P = las.xyz - las.header.mins, the
slide-8 array, F-ordered), with the plane of results/bench_cliff.json (plane.coefficients, the seeded segment_plane
of snippets/s16_*.py):

* ``loop``: the slide region of snippets/s16_loop.py, compiled verbatim as a function (one thread)
* ``threads_N`` (N = 1, 2, 4, 8, 16): the same loop body over N contiguous slices of P, one slice per task of a
  concurrent.futures.ThreadPoolExecutor(max_workers=N) (pool created before timing; every task writes its own
  slice of one shared output array)
* ``vectorised``: the slide region of snippets/s16_vec.py, compiled verbatim (one call)

1 warm-up round and 7 timed rounds; in every round the variants run in a seeded random order; gc.collect() before
every run; wall time (time.perf_counter); median and IQR (numpy.percentile, linear). Every variant's result is
checked with np.array_equal against the vectorised one. The driver waits for the 1-minute load average to drop
below 1.0 before each interpreter and records it, with the CPU, the builds and sys._is_gil_enabled().
"""

from __future__ import annotations

import argparse
import gc
import json
import subprocess
import sys
import time
from pathlib import Path

from _common import DATA_CROP as CROP, RESULTS, SNIPPETS, factor, region_function, timing_stats  # numpy + stdlib only

HERE = Path(__file__).resolve().parent
THREADS = (1, 2, 4, 8, 16)
RUNS, WARMUP, SEED = 7, 1, 20261015
STAT = "median and IQR (numpy.percentile, linear) of wall time over the timed runs"


def worker() -> dict:
    import numpy as np
    import laspy
    from concurrent.futures import ThreadPoolExecutor

    loop, _ = region_function(SNIPPETS / "s16_loop.py", ("P", "plane"), "h", name="loop")
    vectorised, _ = region_function(SNIPPETS / "s16_vec.py", ("P", "plane"), "h", name="vectorised")

    las = laspy.read(CROP)
    P = las.xyz - las.header.mins
    bench = json.loads((RESULTS / "bench_cliff.json").read_text())
    plane = tuple(float(v) for v in bench["plane"]["coefficients"])

    def threaded(n, pool):
        h = np.empty(len(P))  # distances

        def work(lo, hi):
            a, b, c, d = plane
            for i, p in enumerate(P[lo:hi], lo):  # the slide-16 loop body, over one slice
                x, y, z = p[0], p[1], p[2]
                h[i] = abs(a*x + b*y + c*z + d)

        bounds = [len(P) * k // n for k in range(n + 1)]
        list(pool.map(work, bounds[:-1], bounds[1:]))
        return h

    pools = {n: ThreadPoolExecutor(max_workers=n) for n in THREADS}
    gil_at_start = getattr(sys, "_is_gil_enabled", lambda: True)()
    variants = {"loop": lambda: loop(P, plane), "vectorised": lambda: vectorised(P, plane)}
    for n in THREADS:
        variants[f"threads_{n}"] = (lambda n=n: threaded(n, pools[n]))
    ref = vectorised(P, plane)
    equal = {k: bool(np.array_equal(f(), ref)) for k, f in variants.items()}
    rng = np.random.default_rng(SEED)
    times = {k: [] for k in variants}
    names = list(variants)
    for rnd in range(WARMUP + RUNS):
        for k in rng.permutation(names):
            gc.collect()
            t0 = time.perf_counter()
            variants[k]()
            dt = time.perf_counter() - t0
            if rnd >= WARMUP:
                times[k].append(dt)
    for p in pools.values():
        p.shutdown()

    res = {k: timing_stats(v, int(k.split("_")[1]) if k.startswith("threads_") else 1, digits=4)
           for k, v in times.items()}
    import importlib.metadata as md
    import sysconfig
    return {
        "python": sys.version.split()[0], "python_full": sys.version, "executable_build":
            "free-threaded" if sysconfig.get_config_var("Py_GIL_DISABLED") else "default (GIL)",
        "py_gil_disabled_build": bool(sysconfig.get_config_var("Py_GIL_DISABLED")),
        "gil_enabled_at_end": getattr(sys, "_is_gil_enabled", lambda: True)(),
        "gil_enabled_at_start": gil_at_start,
        "numpy": np.__version__, "laspy": laspy.__version__, "lazrs": md.version("lazrs"),
        "n": int(len(P)), "array": {"how": "las.xyz - las.header.mins", "dtype": str(P.dtype),
                                    "f_contiguous": bool(P.flags.f_contiguous)},
        "plane": list(plane), "equal_to_vectorised": equal, "timings": res,
    }


def run_interpreter(py: str) -> dict:
    import conditions
    before = conditions.wait_idle()
    snap = conditions.snapshot()
    p = subprocess.run([py, str(Path(__file__).resolve()), "--worker"], capture_output=True, text=True, check=True)
    out = json.loads(p.stdout)
    out["load_avg_before"], out["load_avg_after"] = before, conditions.load_avg()
    out["snapshot_before"], out["snapshot_after"] = snap, conditions.snapshot()
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--worker", action="store_true")
    ap.add_argument("--ft", help="free-threaded interpreter")
    ap.add_argument("--gil", help="default-build interpreter of the same release")
    ap.add_argument("--final", action="store_true")
    args = ap.parse_args()
    if args.worker:
        print(json.dumps(worker()))
        return 0
    if not args.ft or not args.gil:
        ap.error("--ft and --gil are required")
    import conditions
    from _common import rel, write_json
    builds = {"free_threaded": run_interpreter(args.ft), "gil": run_interpreter(args.gil)}
    a, b = builds["free_threaded"], builds["gil"]
    if not (a["py_gil_disabled_build"] and not a["gil_enabled_at_start"] and not a["gil_enabled_at_end"]
            and not b["py_gil_disabled_build"] and b["gil_enabled_at_start"] and b["gil_enabled_at_end"]):
        raise SystemExit("Interpreter build/GIL states do not match the comparison labels")
    if any(a[k] != b[k] for k in ("python", "numpy", "laspy", "lazrs", "n", "array", "plane")):
        raise SystemExit("Compared builds must use matching versions, input and plane")
    if not all(all(x["equal_to_vectorised"].values()) for x in builds.values()):
        raise SystemExit("Compared calculations differ; refusing to publish results")
    ft, gil = builds["free_threaded"]["timings"], builds["gil"]["timings"]
    best_n = min(THREADS, key=lambda n: ft[f"threads_{n}"]["median_ms"])
    summary = {
        "best_threads_ft": best_n,
        "ft_speedup_best_vs_loop": factor(ft["loop"], ft[f"threads_{best_n}"]),
        "ft_speedup_vs_loop": {str(n): factor(ft["loop"], ft[f"threads_{n}"]) for n in THREADS},
        "gil_speedup_vs_loop": {str(n): factor(gil["loop"], gil[f"threads_{n}"]) for n in THREADS},
        "ft_vectorised_vs_best_threads": factor(ft[f"threads_{best_n}"], ft["vectorised"]),
        "ft_vectorised_vs_loop": factor(ft["loop"], ft["vectorised"]),
        "ft_loop_vs_gil_loop": factor(ft["loop"], gil["loop"]),
        "all_equal": all(all(b["equal_to_vectorised"].values()) for b in builds.values()),
    }
    lb = [b["load_avg_before"] for b in builds.values()]
    la = [b["load_avg_after"] for b in builds.values()]
    out = {
        "label": "FINAL" if args.final else "PILOT",
        "script": rel(Path(__file__)),
        "question": "Does the free-threaded build make the slide-16 loop over NumPy rows fast, if the loop is "
                    "split over threads?",
        "conditions": conditions.collect(
            data=rel(CROP), n=builds["free_threaded"]["n"], runs=RUNS, warmup=WARMUP, statistic=STAT,
            load_avg_before=lb[0], load_avg_after=la[-1],
            extra={"note": "python/numpy/scipy/open3d keys above describe the driver (project venv); the timed "
                           "interpreters are under builds.*",
                   "load_avg_per_build": {"before": lb, "after": la},
                   "order": f"interleaved: seeded (numpy default_rng {SEED}) permutation of the variants per round",
                   "pool": "ThreadPoolExecutor created before timing, one task per slice",
                   "load_check": {"limit_1min": 1.0}}),
        "threads": list(THREADS),
        "builds": builds,
        "summary": summary,
    }
    if args.final:
        write_json(RESULTS / "bench_freethreaded.json", out, final=True)
        print("wrote results/bench_freethreaded.json")
    for name, b in builds.items():
        t = b["timings"]
        print(name, b["python_full"].split()[0:4], "GIL", b["gil_enabled_at_end"],
              {k: round(v["median_ms"], 1) for k, v in t.items()})
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
