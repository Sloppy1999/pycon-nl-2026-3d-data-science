"""CPU profile of the slide-19 loop and the one-expression version with Scalene -> results/profile_scalene.json.

    uv run --group profile python bench/profile_loop_scalene.py --final            # writes results/profile_scalene.json
    uv run --group profile python bench/profile_loop_scalene.py --out DIR/p.json   # anywhere outside results/ (smoke)

Runs `scalene run --cpu-only --cpu-sampling-rate 0.001 bench/cpuprof/loop.py --- 30` three times (see that file: the
slide lines of snippets/s16_loop.py and s16_vec.py as two functions on the AHN5 crop, each called 30 times) and stores
the run whose loop line has the median share. Per source line Scalene splits its CPU samples into Python (the
interpreter), native (C code the line calls: NumPy, here) and system (waiting, I/O); the shares are percent of the
WHOLE profiled run, which also holds the imports and reading the LAZ file (the `rest` figure).
Scalene bills a sample to the line the interpreter is executing when it handles the signal, after a long C call
returns: the `for` line and the indexing line (`x, y, z = p[0], p[1], p[2]`) show about 0, and the time of a whole
loop turn lands on the last line, `h[i] = abs(...)`. The slide shows the shares as Scalene reports them.
Replaces cProfile (bench/profile_loop.py, results/profile_loop.json) on slide 22; those files stay as a cross-check.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import conditions as cond  # noqa: E402
from _common import DATA_CROP, RESULTS, TALK, rel, write_json  # noqa: E402

TARGET = TALK / "bench" / "cpuprof" / "loop.py"
REPEATS_RUN, RUNS, RATE = 30, 3, "0.001"
# the lines the slide shows: key -> text the source line must contain
LINES = {"for": "for i, p in enumerate(P):", "unpack": "x, y, z = p[0], p[1], p[2]",
         "loop_body": "h[i] = abs(", "vectorised": "h = np.abs("}


def one_run(outdir: Path, i: int) -> dict:
    out = outdir / f"cpu_{i}.json"
    r = subprocess.run([sys.executable, "-m", "scalene", "run", "--cpu-only", "--cpu-sampling-rate", RATE, "-o", str(out),
                        str(TARGET), "---", str(REPEATS_RUN)], capture_output=True, text=True, cwd=TALK)
    if not out.exists() or "np.array_equal(loop, vectorised): True" not in r.stdout:
        raise SystemExit(f"scalene run failed:\n{r.stdout[-600:]}\n{r.stderr[-600:]}")
    return json.loads(out.read_text())


def line_of(d: dict, needle: str) -> dict:
    fl = d["files"][str(TARGET)]["lines"]
    ln = next(l for l in fl if needle in l["line"] and not l["line"].lstrip().startswith(("def ", "#", "assert")))
    py, nat, sy = ln["n_cpu_percent_python"], ln["n_cpu_percent_c"], ln["n_sys_percent"]
    return {"lineno": ln["lineno"], "code": ln["line"].rstrip().removesuffix("# \\u003c\\u003c").removesuffix("# <<").rstrip()[4:],  # relative to the function body
            "python": round(py, 2), "native": round(nat, 2), "system": round(sy, 2), "total": round(py + nat + sy, 2),
            "samples": len(ln["cpu_samples_list"])}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--final", action="store_true", help="write results/profile_scalene.json")
    mode.add_argument("--out", type=Path, help="output JSON outside results/")
    args = ap.parse_args()
    out = RESULTS / "profile_scalene.json" if args.final else args.out
    t0, before = time.perf_counter(), cond.load_avg()
    with tempfile.TemporaryDirectory() as tmp:
        runs = [one_run(Path(tmp), i) for i in range(RUNS)]
    shares = [line_of(d, LINES["loop_body"])["total"] for d in runs]
    d = sorted(runs, key=lambda r: line_of(r, LINES["loop_body"])["total"])[RUNS // 2]
    lines = {k: line_of(d, v) for k, v in LINES.items()}
    shown = sum(v["total"] for v in lines.values())
    version = subprocess.run([sys.executable, "-m", "scalene", "--version"], capture_output=True, text=True).stdout.split()[2]
    lb, vec = lines["loop_body"]["total"], lines["vectorised"]["total"]
    import laspy
    with laspy.open(DATA_CROP) as f:
        n = f.header.point_count
    result = {
        "label": "FINAL" if args.final else "SMOKE",
        "conditions": cond.collect(
            data=rel(DATA_CROP), n=n, runs=RUNS, warmup=0, statistic="the run with the median loop-line share",
            load_avg_before=before, load_avg_after=cond.load_avg(),
            extra={"scalene": version, "cpu_sampling_rate_s": float(RATE), "repeats_per_run": REPEATS_RUN,
                   "mode": "--cpu-only"}),
        "scalene": version, "script": rel(Path(__file__)), "profiled": rel(TARGET),
        "command": f"scalene run --cpu-only {rel(TARGET)}", "repeats": REPEATS_RUN, "sampling_rate_s": float(RATE),
        "elapsed_s": round(d["elapsed_time_sec"], 2), "lines": lines, "loop_line_shares_all_runs": shares,
        "rest_percent": round(100 - shown, 1),
        "loop_python_fraction": round(lines["loop_body"]["python"] / lb, 3),
        "loop_native_fraction": round(lines["loop_body"]["native"] / lb, 3),
        "factor_loop_vs_vectorised": round(lb / vec, 1),
        "points": n, "runtime_s": time.perf_counter() - t0,
    }
    written = write_json(out, result, final=bool(args.final))
    print(f"wrote {written}: loop line {lb:.1f} % (python {lines['loop_body']['python']:.1f}, native "
          f"{lines['loop_body']['native']:.1f}), vectorised {vec:.2f} %, runs {shares}")


if __name__ == "__main__":
    main()
