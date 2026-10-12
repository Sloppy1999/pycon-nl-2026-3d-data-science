"""Memory over time for slide 26: load-everything vs the chunked loop of snippets/s21_chunked.py, 1 km AHN5 tile.

    uv run python bench/bench_memory_trace.py --final                 # writes results/memory_trace.json
    uv run python bench/bench_memory_trace.py --out DIR/trace.json    # anywhere outside results/ (smoke)
    uv run python bench/bench_memory_trace.py --case NAME --file PATH # internal: one traced case (child side)

Why: results/memory.json gives two peak numbers (VmHWM over the post-import baseline). The slide explains WHY
streaming helps with a line chart of memory over time: load-everything climbs to one tall peak, the chunked loop
stays low as a flat sawtooth. This script records those curves for the same two code paths:
    load_everything  the `pipeline` case of bench/bench_memory.py (laspy.read -> float64 xyz -> Open3D copy ->
                     voxel_down_sample(0.5)), the same four statements, run one at a time with a marker after each
    chunked          the slide region of snippets/s21_chunked.py, verbatim (bench_memory.slide_source), run one
                     top-level statement at a time; laspy's LasReader.chunk_iterator is wrapped (not changed) to
                     timestamp the end of every chunk
How: each case runs in a FRESH subprocess with the set-up of bench_memory.py (same imports, MALLOC_MMAP_THRESHOLD_,
gc.collect() + malloc_trim(0), clear_refs=5, baseline = VmRSS right after that). The child prints READY and
waits; the parent starts sampling the child's RSS with psutil every 5 ms, then sends GO. Sampling from the parent
is used (not a thread in the child) because the child's work holds the GIL for long stretches (laspy decoding,
Open3D calls): a sampling thread in the child would stall exactly when memory moves, and would add its own
allocations to the child's RSS. Child and parent share CLOCK_MONOTONIC, so the child's markers line up with the
parent's samples. The child also reports VmHWM at the end, i.e. the same peak bench_memory.py measures; the
sampled peak can only be at or below it (the gap shows how much a 5 ms sampler misses).
Each case is repeated 3 times (alternating order); all peaks are kept, the trace of the median-peak run is stored,
downsampled to <= 400 points by taking the maximum per time bin (keeps the peak exactly).
"""

from __future__ import annotations

import argparse
import ast
import gc
import json
import os
import statistics
import subprocess
import sys
import threading
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import conditions as cond  # noqa: E402
from _common import DATA_TILE, RESULTS, rel, slide_source, write_json  # noqa: E402
from bench_memory import MALLOC_ENV, S21, VOXEL, _status, malloc_threshold_fixed, malloc_trim  # noqa: E402

CASES = ("load_everything", "chunked")
REPEATS = 3
INTERVAL_S = 0.005
MAX_POINTS = 400
MIB = 2**20
CLOCK = time.CLOCK_MONOTONIC


def now() -> float:
    return time.clock_gettime(CLOCK)


# ----------------------------------------------------------------------------------------- child side
# The four statements of the `pipeline` case in bench/bench_memory.py run_case(), copied verbatim; label = marker.
LOAD_EVERYTHING = [
    ("las = laspy.read(path)", "laspy.read"),
    ("xyz = las.xyz - las.header.mins", "float64 xyz"),
    ("pcd = o3d.geometry.PointCloud(o3d.utility.Vector3dVector(xyz))", "Open3D copy"),
    ("down = pcd.voxel_down_sample(VOXEL)", "voxel_down_sample"),
]


def chunked_statements() -> list[tuple[str, str]]:
    """The slide region of s21_chunked.py, split into its top-level statements (source text unchanged)."""
    src = slide_source(S21)
    labels = {0: None, 1: "loop done", 2: "final np.unique", 3: "concatenate"}
    stmts = ast.parse(src).body
    if len(stmts) != 4:
        raise SystemExit(f"{S21}: expected 4 top-level statements in the slide region, found {len(stmts)}")
    return [(ast.get_source_segment(src, s), labels[i]) for i, s in enumerate(stmts)]


def run_case(name: str, path: Path) -> None:
    import laspy
    import open3d as o3d
    o3d.utility.set_verbosity_level(o3d.utility.VerbosityLevel.Error)
    with laspy.open(path) as f:                     # as bench_memory.run_case: header read before the baseline
        n = int(f.header.point_count)
    fixed = malloc_threshold_fixed()
    markers: list[dict] = []

    if name == "load_everything":
        stmts = LOAD_EVERYTHING
        ns = {"np": np, "laspy": laspy, "o3d": o3d, "path": path, "VOXEL": VOXEL}
    elif name == "chunked":
        stmts = chunked_statements()
        ns = {"np": np, "laspy": laspy, "path": str(path)}
        orig = laspy.LasReader.chunk_iterator

        def traced(self, points_per_iteration):      # same iterator; a marker when each chunk's body is done
            it, i = orig(self, points_per_iteration), 0
            while True:
                if i:                                  # resumed: the loop body of chunk i is done
                    markers.append({"t": now(), "label": f"chunk {i}"})
                try:
                    c = next(it)                       # decode of the next chunk happens after the marker
                except StopIteration:
                    return
                i += 1
                yield c
        laspy.LasReader.chunk_iterator = traced
    else:
        raise SystemExit(f"unknown case {name!r}")
    code = [compile(ast.Module(body=ast.parse(s).body, type_ignores=[]), str(S21 if name == "chunked" else __file__),
                    "exec") for s, _ in stmts]

    gc.collect()
    trimmed = malloc_trim()
    with open("/proc/self/clear_refs", "w") as f:
        f.write("5")
    baseline = _status()["VmRSS"]
    print(f"READY {baseline}", flush=True)
    if sys.stdin.readline().strip() != "GO":
        raise SystemExit("parent did not send GO")
    t0 = now()
    for c, (_, label) in zip(code, stmts):
        exec(c, ns)
        if label:
            markers.append({"t": now(), "label": label})
    t_end = now()
    hwm = _status()["VmHWM"]
    out = {"case": name, "points": n, "baseline_bytes": baseline, "hwm_peak_bytes": hwm - baseline,
           "t0": t0, "t_end": t_end, "markers": markers, "malloc_threshold_fixed": fixed, "malloc_trim": trimmed,
           "env_malloc": os.environ.get("MALLOC_MMAP_THRESHOLD_")}
    if name == "chunked":
        out["n_chunks"] = len(ns["keys"])
        out["kept"] = int(len(ns["points"]))
    else:
        out["kept"] = len(ns["down"].points)
    print("RESULT " + json.dumps(out), flush=True)


# ----------------------------------------------------------------------------------------- parent side
def spawn(name: str, path: Path, timeout: int = 600) -> dict:
    import psutil
    env = dict(os.environ, **MALLOC_ENV)
    p = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "--case", name, "--file", str(path)],
                         stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
    line = p.stdout.readline()
    if not line.startswith("READY"):
        p.kill()
        raise SystemExit(f"case {name}: no READY line ({line!r}):\n{p.stderr.read()[-3000:]}")
    proc = psutil.Process(p.pid)
    samples: list[tuple[float, int]] = []
    stop = threading.Event()

    def sample():
        nxt = now()
        while not stop.is_set():
            try:
                samples.append((now(), proc.memory_info().rss))
            except psutil.Error:
                return
            nxt += INTERVAL_S
            time.sleep(max(0.0, nxt - now()))

    th = threading.Thread(target=sample, daemon=True)
    th.start()
    time.sleep(0.05)                                    # a few samples of the idle baseline before GO
    p.stdin.write("GO\n")
    p.stdin.flush()
    result = None
    for line in p.stdout:
        if line.startswith("RESULT "):
            result = json.loads(line[len("RESULT "):])
            break
    stop.set()
    th.join()
    p.wait(timeout=timeout)
    if result is None or p.returncode != 0:
        raise SystemExit(f"case {name} failed:\n{p.stderr.read()[-3000:]}")
    t0, base = result["t0"], result["baseline_bytes"]
    ts = np.array([t for t, _ in samples]) - t0
    mem = (np.array([r for _, r in samples], dtype=float) - base) / MIB
    keep = ts <= result["t_end"] - t0
    result["t"], result["mem"] = ts[keep], mem[keep]
    gaps = np.diff(ts[keep])
    result["sampling"] = {"samples": int(keep.sum()), "median_interval_ms": float(np.median(gaps) * 1e3),
                          "max_interval_ms": float(gaps.max() * 1e3)}
    result["sampled_peak_mib"] = float(mem[keep].max())
    return result


def downsample(t: np.ndarray, m: np.ndarray, n: int = MAX_POINTS) -> tuple[list, list]:
    """At most n points: the maximum of every time bin (with its own t), so the peak survives exactly."""
    if len(t) <= n:
        return [round(float(x), 4) for x in t], [round(float(x), 1) for x in m]
    edges = np.linspace(t[0], t[-1], n + 1)
    idx = np.clip(np.searchsorted(edges, t, side="right") - 1, 0, n - 1)
    ot, om = [], []
    for b in range(n):
        sel = np.flatnonzero(idx == b)
        if len(sel):
            j = sel[np.argmax(m[sel])]
            ot.append(round(float(t[j]), 4))
            om.append(round(float(m[j]), 1))
    return ot, om


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--final", action="store_true", help="write results/memory_trace.json")
    mode.add_argument("--out", type=Path, help="output JSON outside results/")
    mode.add_argument("--case", choices=CASES, help="internal: run one traced case in this process")
    ap.add_argument("--file", type=Path, default=DATA_TILE)
    ap.add_argument("--repeats", type=int, default=REPEATS)
    args = ap.parse_args()
    if args.case:
        run_case(args.case, args.file)
        return 0

    date_utc, load_before, t_start = cond.utc_now(), cond.load_avg(), time.perf_counter()
    runs = {c: [] for c in CASES}
    for r in range(args.repeats):
        for c in (CASES if r % 2 == 0 else CASES[::-1]):
            res = spawn(c, args.file)
            runs[c].append(res)
            print(f"[{time.strftime('%H:%M:%S')}] repeat {r + 1}/{args.repeats} {c:<16s} sampled peak "
                  f"{res['sampled_peak_mib']:7.1f} MiB  VmHWM peak {res['hwm_peak_bytes'] / MIB:7.1f} MiB  "
                  f"{res['t_end'] - res['t0']:.2f} s  {res['sampling']['samples']} samples", flush=True)
    load_after = cond.load_avg()

    mem_json = json.loads((RESULTS / "memory.json").read_text())["tile_1km"]
    ref = {"load_everything": mem_json["naive_peak_mb"], "chunked": mem_json["chunked_peak_mb"]}
    cases = {}
    for c in CASES:
        rs = runs[c]
        peaks = [r["sampled_peak_mib"] for r in rs]
        med = sorted(rs, key=lambda r: r["sampled_peak_mib"])[len(rs) // 2]
        t, m = downsample(med["t"], med["mem"])
        cases[c] = {
            "t_s": t, "mem_mib": m,
            "peak_mib": med["sampled_peak_mib"],
            "peaks_all_runs_mib": peaks,
            "hwm_peak_mib": med["hwm_peak_bytes"] / MIB,
            "hwm_peaks_all_runs_mib": [r["hwm_peak_bytes"] / MIB for r in rs],
            "duration_s": med["t_end"] - med["t0"],
            "durations_all_runs_s": [r["t_end"] - r["t0"] for r in rs],
            "markers": [{"t_s": round(k["t"] - med["t0"], 4), "label": k["label"]} for k in med["markers"]],
            "sampling": med["sampling"],
            "stored_points": len(t),
            "baseline_mib_after_imports": med["baseline_bytes"] / MIB,
            "kept": med["kept"],
            "peak_vs_memory_json": med["hwm_peak_bytes"] / MIB / ref[c] - 1,
        }
        if c == "chunked":
            cases[c]["chunk_size"] = 1_000_000 if "chunk_iterator(1_000_000)" in slide_source(S21) else None
            cases[c]["n_chunks"] = med["n_chunks"]
    within = all(abs(cases[c]["peak_mib"] / ref[c] - 1) <= 0.10 for c in CASES)
    idle = load_before[0] < 1.0
    result = {
        "label": "FINAL" if (args.final and idle) else "PILOT",
        "label_rule": "FINAL only with --final and a 1-minute load average < 1.0 before the run (the run itself "
                      "adds about 1-2 to the load average after)",
        "conditions": cond.collect(
            data=rel(args.file), n=runs[CASES[0]][0]["points"], runs=args.repeats, warmup=0,
            statistic=f"trace of the median-peak run of {args.repeats} fresh subprocesses per case "
                      "(all peaks kept)",
            date_utc=date_utc, load_avg_before=load_before, load_avg_after=load_after,
            extra={"malloc": "MALLOC_MMAP_THRESHOLD_=1048576 in every case subprocess (as bench_memory.py)",
                   "malloc_threshold_fixed_all_cases": all(r["malloc_threshold_fixed"] for c in CASES for r in runs[c]),
                   "malloc_trim_all_cases": all(r["malloc_trim"] for c in CASES for r in runs[c]),
                   "rss_method": "child: gc.collect(), malloc_trim(0), clear_refs=5, baseline VmRSS; parent: "
                                 f"psutil memory_info().rss of the child every {INTERVAL_S * 1e3:.0f} ms "
                                 "(CLOCK_MONOTONIC, shared with the child's markers) from GO until the case ends; "
                                 "child also reports VmHWM - baseline at the end",
                   "downsampling": f"<= {MAX_POINTS} points, maximum per equal-width time bin",
                   "case_order": "alternating per repeat (load_everything first on odd repeats)"}),
        "data": rel(args.file),
        "points": runs[CASES[0]][0]["points"],
        "units": {"t": "s", "mem": "MiB increase over the process after imports"},
        "cases": cases,
        "compare_memory_json": {
            "naive_peak_mb": ref["load_everything"], "chunked_peak_mb": ref["chunked"],
            "sampled_within_10pct": within,
            "note": "memory.json peaks are VmHWM - baseline (MiB). peak_mib here is the highest 5 ms RSS sample, "
                    "so it is at or slightly below hwm_peak_mib (same quantity as memory.json, measured here in the "
                    "same child). load_everything = the memory.json `pipeline` case; chunked = the slide region "
                    "of snippets/s21_chunked.py, run statement by statement.",
        },
        "script": "bench/bench_memory_trace.py",
        "runtime_s": time.perf_counter() - t_start,
    }
    out = RESULTS / "memory_trace.json" if args.final else args.out
    written = write_json(out, result, final=bool(args.final))
    for c in CASES:
        print(f"{c}: sampled peak {cases[c]['peak_mib']:.0f} MiB (memory.json {ref[c]:.0f}), "
              f"VmHWM {cases[c]['hwm_peak_mib']:.0f}, {cases[c]['duration_s']:.2f} s")
    print(f"label {result['label']}, load {load_before} -> {load_after}; wrote {written}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
