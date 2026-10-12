"""Profile the slide-16 loop with cProfile (Profile slide) -> results/profile_loop.txt and results/profile_loop.json.

    uv run python bench/profile_loop.py --final

Runs, in bench/, exactly the command the slide shows:

    python -m cProfile -s tottime loop.py

(bench/loop.py: the slide regions of snippets/s16_loop.py and s16_vec.py compiled verbatim as two functions, on
the AHN5 crop). The full output goes to results/profile_loop.txt; the JSON holds the parsed rows, the rows the
slide shows (``display``: real output lines, dedented by the common indent of the shown lines, with one "..."
line where rows are left out) and the conditions. One profiled run: cProfile adds overhead per traced call, so
its times are not benchmark numbers (results/bench_cliff.json has those).
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import DATA_CROP, RESULTS, rel, write_json  # noqa: E402
import conditions  # noqa: E402

HERE = Path(__file__).resolve().parent
CMD_SHOWN = "python -m cProfile -s tottime loop.py"
SHOW = ("s16_loop.py:1(loop)", "builtins.abs}", "s16_vec.py:1(vectorised)")
ROW_RE = re.compile(r"^\s*(\d+(?:/\d+)?)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+(.*)$")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--final", action="store_true", help="write into results/")
    args = ap.parse_args()
    load_before = conditions.wait_idle()
    cmd = [sys.executable, "-m", "cProfile", "-s", "tottime", "loop.py"]
    p = subprocess.run(cmd, cwd=HERE, capture_output=True, text=True, check=True)
    load_after = conditions.load_avg()
    text = p.stdout
    lines = text.splitlines()
    head = next(ln for ln in lines if "function calls" in ln)
    m = re.search(r"(\d+) function calls(?: \((\d+) primitive calls\))? in ([\d.]+) seconds", head)
    total_calls, prim, total_s = int(m.group(1)), int(m.group(2) or m.group(1)), float(m.group(3))
    hdr_i = next(i for i, ln in enumerate(lines) if ln.strip().startswith("ncalls"))
    rows = []
    for ln in lines[hdr_i + 1:]:
        r = ROW_RE.match(ln)
        if not r:
            continue
        rows.append({"rank": len(rows) + 1, "ncalls": r.group(1), "tottime": float(r.group(2)),
                     "percall_tot": float(r.group(3)), "cumtime": float(r.group(4)),
                     "percall_cum": float(r.group(5)), "function": r.group(6), "line": ln})
    picked = {k: next(r for r in rows if r["function"].endswith(k)) for k in SHOW}
    loop, absr, vec = (picked[k] for k in SHOW)
    # the slide's lines: command, summary, header, the picked rows (in rank order, "..." for gaps)
    shown_rows, last = [], 0
    for r in sorted(picked.values(), key=lambda r: r["rank"]):
        if r["rank"] != last + 1:
            shown_rows.append("...")
        shown_rows.append(r["line"])
        last = r["rank"]
    body = [lines[hdr_i]] + shown_rows
    indent = min(len(ln) - len(ln.lstrip()) for ln in body if ln != "...")
    body = [ln if ln == "..." else ln[indent:] for ln in body]
    display = ["$ " + CMD_SHOWN, head.strip()] + body
    out = {
        "label": "FINAL" if args.final else "PILOT",
        "script": rel(Path(__file__)), "profiled": rel(HERE / "loop.py"),
        "command": CMD_SHOWN, "cwd": "bench", "sort": "tottime (internal time)",
        "total_calls": total_calls, "primitive_calls": prim, "total_s": total_s,
        "loop": {"rank": loop["rank"], "ncalls": int(loop["ncalls"]), "tottime_s": loop["tottime"],
                 "cumtime_s": loop["cumtime"], "function": loop["function"]},
        "abs": {"rank": absr["rank"], "ncalls": int(absr["ncalls"]), "tottime_s": absr["tottime"],
                "function": absr["function"]},
        "vectorised": {"rank": vec["rank"], "ncalls": int(vec["ncalls"]), "tottime_s": vec["tottime"],
                       "cumtime_s": vec["cumtime"], "function": vec["function"]},
        "share_loop_cumtime": loop["cumtime"] / total_s,
        "factor_loop_vs_vectorised_cumtime": loop["cumtime"] / vec["cumtime"],
        "display": display,
        "display_note": "real output lines; the shown rows dedented by their common indent; '...' marks rows left out",
        "rows_top10": rows[:10],
        "stdout_file": "results/profile_loop.txt",
        "note": "one profiled run; cProfile adds overhead to every traced call (here builtins.abs), so these "
                "times are not benchmark numbers (results/bench_cliff.json)",
        "conditions": conditions.collect(
            data=rel(DATA_CROP), n=int(absr["ncalls"]), runs=1, warmup=0,
            statistic="one profiled run (cProfile, deterministic profiler)",
            load_avg_before=load_before, load_avg_after=load_after,
            extra={"command": " ".join(cmd), "load_check": {"limit_1min": 1.0, "waited_until": load_before}}),
    }
    if args.final:
        (RESULTS / "profile_loop.txt").write_text(f"$ {CMD_SHOWN}   (cwd: bench)\n" + text, encoding="utf-8")
        write_json(RESULTS / "profile_loop.json", out, final=True)
        print("wrote results/profile_loop.txt and results/profile_loop.json")
    print("\n".join(display))
    print(f"loop share of cumtime {out['share_loop_cumtime']:.3f}, loop/vectorised {out['factor_loop_vs_vectorised_cumtime']:.0f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
