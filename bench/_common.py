"""Shared helpers for the bench/ scripts (paths, slide regions, statistics, timing, Scalene runs, JSON output).

Imports only NumPy and the standard library: bench_freethreaded.py's workers import it in bare 3.14t venvs."""

from __future__ import annotations

import ast
import gc
import importlib.util
import json
import math
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import numpy as np

TALK = Path(__file__).resolve().parents[1]
DATA_CROP = TALK / "data" / "utrecht_jaarbeurs_200m.laz"
DATA_TILE = TALK / "data" / "AHN5_C_135000_455000.COPC.LAZ"
RESULTS = TALK / "results"
SNIPPETS = TALK / "snippets"

SLIDE_START, SLIDE_END, KEY_MARK = "# --- slide ---", "# --- end ---", "  # <<"


def rel(path: Path) -> str:
    """Path relative to the repo root when possible (keeps result files machine independent)."""
    try:
        return str(Path(path).resolve().relative_to(TALK))
    except ValueError:
        return str(path)


def slide_lines(path: Path) -> list[str]:
    """The lines the deck shows: between the slide markers, key-line marker stripped (CONTRACTS.md)."""
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    starts = [i for i, s in enumerate(lines) if s.strip() == SLIDE_START]
    ends = [i for i, s in enumerate(lines) if s.strip() == SLIDE_END]
    if len(starts) != 1 or len(ends) != 1 or ends[0] <= starts[0]:
        raise ValueError(f"{path}: expected exactly one '{SLIDE_START}' ... '{SLIDE_END}' region")
    region = lines[starts[0] + 1 : ends[0]]
    return [s[: -len(KEY_MARK)] if s.endswith(KEY_MARK) else s for s in region]


def slide_source(path: Path) -> str:
    return "\n".join(slide_lines(path)) + "\n"


def check_budget(path: Path, max_lines: int, max_chars: int) -> dict:
    lines = slide_lines(path)
    widest = max((len(s) for s in lines), default=0)
    return {"lines": len(lines), "max_chars": widest, "ok": len(lines) <= max_lines and widest <= max_chars,
            "budget": {"lines": max_lines, "chars": max_chars}}


def fetch_ahn5():
    """data/fetch_ahn5.py (crop box, tile URL, file names), loaded without making data/ a package."""
    spec = importlib.util.spec_from_file_location("fetch_ahn5", TALK / "data" / "fetch_ahn5.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def region_function(path: Path, args: tuple[str, ...], result: str, extra_globals: dict | None = None,
                    replace: tuple[str, str] | None = None, name: str = "f"):
    """Compile a snippet's slide region, verbatim, as the body of a function `name(*args) -> result`.

    Running it as a function (fast locals) is the way the code would sit in a real pipeline; it is also
    the faster of the two ways to run a loop in CPython, so the measured loop cost is not inflated.
    `replace=(old, new)` builds a variant for sensitivity checks; `old` must occur exactly once.
    The code object carries the snippet's repo-relative path, so profiles show "snippets/s16_loop.py:1(loop)".
    """
    src = slide_source(path)
    if replace is not None:
        if src.count(replace[0]) != 1:
            raise ValueError(f"{path}: variant text {replace[0]!r} must occur exactly once")
        src = src.replace(replace[0], replace[1])
    bound = {t.id for t in ast.walk(ast.parse(src)) if isinstance(t, ast.Name) and isinstance(t.ctx, ast.Store)}
    if result not in bound:
        raise ValueError(f"{path}: slide region never assigns {result!r}")
    code = f"def {name}({', '.join(args)}):\n{textwrap.indent(src, '    ')}    return {result}\n"
    ns = {"np": np, **(extra_globals or {})}
    exec(compile(code, rel(path), "exec"), ns)
    return ns[name], src


def timing_stats(seconds: list[float], threads: int, digits: int = 6) -> dict:
    """T = {median_ms, q1_ms, q3_ms, runs, threads} (CONTRACTS.md) plus min/max and every run."""
    ms = np.asarray(seconds, dtype=float) * 1e3
    q1, med, q3 = np.percentile(ms, [25, 50, 75])  # linear interpolation (numpy default)
    return {"median_ms": float(med), "q1_ms": float(q1), "q3_ms": float(q3), "runs": int(len(ms)),
            "threads": int(threads), "min_ms": float(ms.min()), "max_ms": float(ms.max()),
            "all_ms": [round(float(x), digits) for x in ms]}


def timed(fn, runs: int, warmup: int, collect: bool = True) -> dict:
    """`warmup` untimed calls, then `runs` timed ones (gc.collect() before each if `collect`); timing_stats.
    The result is freed after the clock stops, so the time is making it, not making and freeing it."""
    for _ in range(warmup):
        fn()
    out = []
    for _ in range(runs):
        if collect:
            gc.collect()
        t0 = time.perf_counter()
        r = fn()
        out.append(time.perf_counter() - t0)
        del r
    return timing_stats(out, threads=1)


def factor(slow: dict, fast: dict) -> dict:
    """median ratio and IQR bounds: iqr_low = q1(slow)/q3(fast), iqr_high = q3(slow)/q1(fast)."""
    return {"median": slow["median_ms"] / fast["median_ms"],
            "iqr_low": slow["q1_ms"] / fast["q3_ms"],
            "iqr_high": slow["q3_ms"] / fast["q1_ms"]}


def scalene_run(target: Path, out: Path, opts: tuple[str, ...] = (), target_args: tuple[str, ...] = (),
                expect: str = "") -> tuple[dict, str]:
    """`scalene run OPTS -o OUT TARGET --- ARGS` from the repo root; returns (Scalene's JSON, the target's stdout).
    Fails unless OUT was written and the target printed `expect` (its own success line)."""
    r = subprocess.run([sys.executable, "-m", "scalene", "run", *opts, "-o", str(out), str(target), "---", *target_args],
                       capture_output=True, text=True, cwd=TALK)
    if not out.exists() or expect not in r.stdout:
        raise SystemExit(f"scalene run failed for {rel(target)}:\n{r.stdout[-800:]}\n{r.stderr[-800:]}")
    return json.loads(out.read_text()), r.stdout


def scalene_version() -> str:
    return subprocess.run([sys.executable, "-m", "scalene", "--version"], capture_output=True, text=True).stdout.split()[2]


def _clean(obj):
    if isinstance(obj, dict):
        return {str(k): _clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_clean(v) for v in obj]
    if isinstance(obj, np.generic):
        obj = obj.item()
    if isinstance(obj, float) and not math.isfinite(obj):
        return None
    if isinstance(obj, Path):
        return rel(obj)
    return obj


def guard_out(path: Path, *, final: bool) -> Path:
    """Only --final runs may write into results/ (checked at start and again when writing)."""
    path = Path(path).resolve()
    if RESULTS.resolve() in path.parents and not final:
        raise SystemExit(f"refusing to write a non-final result into {RESULTS}: {path}")
    return path


def write_json(path: Path, obj: dict, *, final: bool) -> Path:
    """Write a result file atomically. Only --final runs may write into results/."""
    path = guard_out(path, final=final)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(_clean(obj), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)
    return path
