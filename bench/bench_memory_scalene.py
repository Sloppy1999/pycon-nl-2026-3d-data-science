"""Memory over a run as Scalene sees it: load-everything vs the chunked loop of slide 25, 1 km AHN5 tile.

    uv run --group profile python bench/bench_memory_scalene.py --final               # writes results/memory_scalene.json
    uv run --group profile python bench/bench_memory_scalene.py --out DIR/scalene.json   # anywhere outside results/ (smoke)

Why: slide 26 shows WHY streaming helps, as the memory curve of a profiler (https://github.com/plasma-umass/scalene)
instead of a hand-made sampler. The two targets are bench/memprof/load_everything.py (laspy.read -> float64 xyz ->
Open3D copy -> voxel_down_sample(0.5), as the `pipeline` case of bench_memory.py) and bench/memprof/chunked.py
(the slide lines of snippets/s21_chunked.py, verbatim, checked by the target itself).
How: `scalene run -o OUT.json TARGET --- tile`, three runs per case (alternating), the run with the median peak is
stored. The target directory must not have "scalene" in its path (Scalene skips such files and records no memory).
Scalene's memory mode hangs in laspy's parallel LAZ decoder, so the targets use laspy's single-threaded Lazrs backend.

What Scalene measures: its footprint is the allocation count (mallocs minus frees it sees), sampled when it changes by
about 1 MiB. It is NOT the resident set size that bench_memory.py reads (VmHWM): frees that Scalene does not see
(here, most likely the Rust LAZ decoder's) keep the footprint high, so the chunked curve sits above the RSS peak
(results/memory.json). Scalene's x axis is the order of its memory samples, not wall time (its samples carry the
running total of bytes allocated, which jumps in bursts, so that total makes a poor axis). The stored curve uses
"progress" = the sample's rank as a percentage, as Scalene's own timeline does; seconds are stored per case as
`duration_s`.
Stored per case: peak_mib (the highest stored sample; scalene_max_footprint_mib is Scalene's own maximum, which falls between samples), peak_line, the curve (`t_s` = progress %, `mem_mib`), `markers`
at the first sample of named lines, and `lines` (per source line: peak, bytes allocated, CPU share).
"""

from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import conditions as cond  # noqa: E402
from _common import DATA_TILE, RESULTS, TALK, rel, write_json  # noqa: E402

REPEATS = 3
TARGETS = {"load_everything": TALK / "bench" / "memprof" / "load_everything.py",
           "chunked": TALK / "bench" / "memprof" / "chunked.py"}
# first sample of these source lines marks the phase on the curve (label -> text that must be in the line)
# (lines Scalene sees late in the run fall after its last stored sample, so only early lines are marked)
MARKERS = {"load_everything": {"Open3D copy": "PointCloud("}, "chunked": {"chunk loop": "chunk_iterator"}}


def run_scalene(case: str, outdir: Path, i: int) -> dict:
    out = outdir / f"{case}_{i}.json"
    t0 = time.perf_counter()
    r = subprocess.run([sys.executable, "-m", "scalene", "run", "-o", str(out), str(TARGETS[case]), "---", "tile"],
                       capture_output=True, text=True, cwd=TALK)
    if not out.exists() or "points kept" not in r.stdout:
        raise SystemExit(f"scalene run failed for {case}:\n{r.stdout[-800:]}\n{r.stderr[-800:]}")
    d = json.loads(out.read_text())
    d["_wall_s"] = time.perf_counter() - t0
    d["_kept"] = int(r.stdout.split(" points kept")[0].split()[-1])
    return d


def summarise(case: str, d: dict) -> dict:
    target = str(TARGETS[case])
    fl = d["files"][target]["lines"]
    xs = [s[0] for s in d["samples"]]
    n_s = len(xs)
    prog = [100.0 * i / (n_s - 1) for i in range(n_s)]      # sample order, as Scalene's own timeline
    mem = [s[1] for s in d["samples"]]
    markers = []
    for label, needle in MARKERS[case].items():
        ln = next((l for l in fl if needle in l["line"] and l.get("memory_samples")), None)
        if ln is None:
            continue
        x = ln["memory_samples"][0][0]
        k = next((i for i, v in enumerate(xs) if v >= x), n_s - 1)     # first sample at or after the line's first
        markers.append({"t_s": round(prog[k], 2), "label": label, "line": ln["lineno"]})
    lines = [{"lineno": l["lineno"], "line": l["line"].rstrip(), "peak_mb": round(l["n_peak_mb"], 1),
              "malloc_mb": round(l["n_malloc_mb"], 1),
              "cpu_percent": round(l["n_cpu_percent_c"] + l["n_cpu_percent_python"], 1)}
             for l in fl if l["n_peak_mb"] > 0.5 or l["n_malloc_mb"] > 1 or l["n_cpu_percent_c"] + l["n_cpu_percent_python"] > 0.5]
    return {"t_s": [round(p, 2) for p in prog], "mem_mib": [round(m, 1) for m in mem],
            "peak_mib": round(max(mem), 1), "scalene_max_footprint_mib": round(d["max_footprint_mb"], 1),
            "peak_line": d["max_footprint_lineno"],
            "peak_line_text": next((l["line"].strip() for l in fl if l["lineno"] == d["max_footprint_lineno"]), None),
            "duration_s": round(d["elapsed_time_sec"], 2), "kept": d["_kept"], "markers": markers, "lines": lines}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--final", action="store_true", help="write results/memory_scalene.json")
    mode.add_argument("--out", type=Path, help="output JSON outside results/")
    ap.add_argument("--repeats", type=int, default=REPEATS)
    args = ap.parse_args()
    out = RESULTS / "memory_scalene.json" if args.final else args.out
    import laspy
    with laspy.open(DATA_TILE) as f:
        n = f.header.point_count
    t0 = time.perf_counter()
    before = cond.load_avg()
    runs: dict[str, list[dict]] = {c: [] for c in TARGETS}
    with tempfile.TemporaryDirectory() as tmp:
        for i in range(args.repeats):
            order = list(TARGETS) if i % 2 == 0 else list(reversed(TARGETS))
            for case in order:
                runs[case].append(run_scalene(case, Path(tmp), i))
                print(f"{case} run {i}: peak {max(x[1] for x in runs[case][-1]['samples']):.0f} MB", flush=True)
    cases, peaks = {}, {}
    for case, rs in runs.items():
        pk = [max(x[1] for x in r["samples"]) for r in rs]
        med = sorted(rs, key=lambda r: max(x[1] for x in r["samples"]))[len(rs) // 2]
        cases[case] = summarise(case, med) | {"peaks_all_runs_mib": [round(p, 1) for p in pk]}
        peaks[case] = statistics.median(pk)
    scalene_version = subprocess.run([sys.executable, "-m", "scalene", "--version"], capture_output=True, text=True).stdout.split()[2]
    result = {
        "label": "FINAL" if args.final else "SMOKE",
        "conditions": cond.collect(
            data=rel(DATA_TILE), n=n, runs=args.repeats, warmup=0,
            statistic="the run with the median peak of the runs per case",
            load_avg_before=before, load_avg_after=cond.load_avg(),
            extra={"scalene": scalene_version, "laz_backend": "Lazrs (single-threaded; LazrsParallel hangs under Scalene)"}),
        "data": rel(DATA_TILE), "points": n,
        "units": {"mem_mib": "Scalene footprint, MiB (2^20 B), not RSS", "t_s": "progress through the run, percent of Scalene's memory samples (not wall time)"},
        "scalene": scalene_version,
        "cases": cases,
        "peak_ratio": peaks["load_everything"] / peaks["chunked"],
        "script": rel(Path(__file__)), "runtime_s": time.perf_counter() - t0,
    }
    written = write_json(out, result, final=bool(args.final))
    print(f"wrote {written}: load everything {peaks['load_everything']:.0f} MiB, chunked {peaks['chunked']:.0f} MiB, "
          f"ratio {result['peak_ratio']:.2f}")


if __name__ == "__main__":
    main()
