"""Run every slide snippet and record the result in results/snippets.json.

    uv run python snippets/run_all.py

Every ``snippets/*.py`` except this file and ``_*.py`` helpers runs in its own subprocess (snippets written by
other parts of the project, such as s16_*.py and s21_*.py, are included when present). For each snippet the
JSON records ``ok``, ``seconds``, ``error`` (last lines of stderr), and the size of the slide region: ``lines``
and ``max_line_len`` after the key-line marker ``  # <<`` is stripped, against the width budget of the
slide's column. ``.cpp`` files are compiled with ``g++ -std=c++17 -O2 -Wall -Wextra ... $(pkg-config --cflags
--libs pcl_io pcl_filters)`` and run in a temporary directory holding ``crop.pcd`` (written by
``_setup.write_crop_pcd``, the same file s02_python.py reads) when a PCL toolchain is found: ``PCL_PREFIX`` (a
conda/micromamba env prefix with ``pcl`` and ``cxx-compiler``; its ``bin/pkg-config``, ``bin/g++`` and ``lib/``
are used) or else the system ``pkg-config`` and ``g++``. Without one they are listed with ``ok: null, status:
"NOT RUN"``. For s02_* snippets the stdout line ``N -> M`` is recorded as ``output_line``.

    PCL_PREFIX=/path/to/env uv run python snippets/run_all.py
s04_repl.py is measured on the transcript it writes (s04_repl.txt), which is what the slide shows.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
import tempfile
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = ROOT / "results" / "snippets.json"
MAX_LINES = 12
WIDTH = {"s21": 70}  # L4 full width; everything else sits in an L5/L7/L8 column
DEFAULT_WIDTH = 35
MARKERS = {".py": ("# --- slide ---", "# --- end ---", "  # <<"), ".cpp": ("// --- slide ---", "// --- end ---", "  // <<")}
DISPLAY = {"s04_repl.py": "s04_repl.txt"}  # the slide shows the transcript, not the script
CXXFLAGS = ["-std=c++17", "-O2", "-Wall", "-Wextra"]
PCL_MODULES = ["pcl_io", "pcl_filters"]
OUTPUT_LINE = re.compile(r"^\d+ -> \d+$")  # s02_*: "points before -> after" printed by the slide code


def output_line(name: str, stdout: str) -> str | None:
    if not name.startswith("s02_"):
        return None
    return next((ln.strip() for ln in stdout.splitlines() if OUTPUT_LINE.match(ln.strip())), None)


def pcl_toolchain() -> dict | None:
    """pkg-config, compiler and environment for building against PCL, or None if PCL is not found."""
    env = dict(os.environ)
    prefix = os.environ.get("PCL_PREFIX")
    pc, cxx = shutil.which("pkg-config"), shutil.which("g++") or shutil.which("c++")
    if prefix:
        pre = Path(prefix)
        pc = str(pre / "bin" / "pkg-config") if (pre / "bin" / "pkg-config").exists() else pc
        cxx = str(pre / "bin" / "g++") if (pre / "bin" / "g++").exists() else cxx
        for var, path in (("PKG_CONFIG_PATH", pre / "lib" / "pkgconfig"), ("LD_LIBRARY_PATH", pre / "lib")):
            env[var] = os.pathsep.join(filter(None, [str(path), env.get(var)]))
    if not pc or not cxx:
        return None
    ver = subprocess.run([pc, "--modversion", "pcl_common"], env=env, capture_output=True, text=True)
    flags = subprocess.run([pc, "--cflags", "--libs", *PCL_MODULES], env=env, capture_output=True, text=True)
    if ver.returncode != 0 or flags.returncode != 0:
        return None
    cv = subprocess.run([cxx, "--version"], capture_output=True, text=True).stdout.splitlines()
    return dict(env=env, cxx=cxx, flags=shlex.split(flags.stdout), pcl_version=ver.stdout.strip(),
                compiler=cv[0] if cv else Path(cxx).name)


def run_cpp(path: Path, tc: dict) -> dict:
    """Write crop.pcd, compile ``path`` against PCL and run it, all in a temporary directory."""
    work = Path(tempfile.mkdtemp(prefix="snippet_cpp_"))
    try:
        t0 = time.perf_counter()
        pcd = subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0, sys.argv[1]); "
                              "import _setup; _setup.write_crop_pcd(sys.argv[2])", str(HERE), str(work / "crop.pcd")],
                             cwd=ROOT, capture_output=True, text=True, timeout=600)
        exe = work / path.stem
        cmd = [tc["cxx"], *CXXFLAGS, str(path), *tc["flags"], "-o", str(exe)]
        build = subprocess.run(cmd, env=tc["env"], capture_output=True, text=True, timeout=600) \
            if pcd.returncode == 0 else pcd
        p = subprocess.run([str(exe)], cwd=work, env=tc["env"], capture_output=True, text=True, timeout=600) \
            if build.returncode == 0 else build
        dt = time.perf_counter() - t0
    finally:
        shutil.rmtree(work, ignore_errors=True)
    err = None if p.returncode == 0 else "\n".join(p.stderr.strip().splitlines()[-6:]) or f"exit code {p.returncode}"
    shown_cmd = " ".join([Path(tc["cxx"]).name, *CXXFLAGS, path.name,
                          f"$(pkg-config --cflags --libs {' '.join(PCL_MODULES)})", "-o", path.stem])
    return dict(ok=p.returncode == 0, status="ran" if p.returncode == 0 else "FAIL", seconds=round(dt, 2),
                error=err, compiler=tc["compiler"], pcl_version=tc["pcl_version"], build_cmd=shown_cmd,
                build_warnings=build.stderr.strip().splitlines()[-6:] if build is not pcd and build.returncode == 0 else [],
                stdout_tail=p.stdout.strip().splitlines()[-3:], output_line=output_line(path.name, p.stdout))


def region(path: Path) -> tuple[list[str], int]:
    start, end, key = MARKERS[path.suffix]
    lines = path.read_text().splitlines()
    s = [i for i, ln in enumerate(lines) if ln.strip() == start]
    e = [i for i, ln in enumerate(lines) if ln.strip() == end]
    if len(s) != 1 or len(e) != 1 or e[0] < s[0]:
        return [], 0
    body = lines[s[0] + 1 : e[0]]
    n_key = sum(ln.endswith(key) for ln in body)
    return [ln[: -len(key)] if ln.endswith(key) else ln for ln in body], n_key


def measure(path: Path) -> dict:
    body, n_key = region(path)
    shown = path.name
    if path.name in DISPLAY and (HERE / DISPLAY[path.name]).exists():
        shown = DISPLAY[path.name]
        key = MARKERS[".py"][2]
        raw = (HERE / shown).read_text().splitlines()
        n_key = sum(ln.endswith(key) for ln in raw)
        body = [ln[: -len(key)] if ln.endswith(key) else ln for ln in raw]
    width = WIDTH.get(path.name.split("_")[0], DEFAULT_WIDTH)
    n, w = len(body), max((len(ln) for ln in body), default=0)
    return dict(lines=n, max_line_len=w, key_lines=n_key, shown=shown,
                budget=dict(max_lines=MAX_LINES, max_line_len=width),
                within_budget=bool(body) and n <= MAX_LINES and w <= width,
                has_region=bool(body))


def main() -> int:
    results: dict = {}
    for path in sorted(HERE.glob("*.py")):
        if path.name == Path(__file__).name or path.name.startswith("_"):
            continue
        t0 = time.perf_counter()
        p = subprocess.run([sys.executable, str(path)], cwd=ROOT, capture_output=True, text=True, timeout=600)
        dt = time.perf_counter() - t0
        err = None if p.returncode == 0 else "\n".join(p.stderr.strip().splitlines()[-6:]) or f"exit code {p.returncode}"
        results[path.name] = dict(ok=p.returncode == 0, seconds=round(dt, 2), error=err, **measure(path),
                                  python=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                                  stdout_tail=p.stdout.strip().splitlines()[-3:])
        if path.name.startswith("s02_"):
            results[path.name]["output_line"] = output_line(path.name, p.stdout)
        print(f"{path.name:20s} {'ok ' if p.returncode == 0 else 'FAIL'} {dt:6.2f} s  "
              f"{results[path.name]['lines']:2d} lines, max {results[path.name]['max_line_len']} chars"
              + ("" if p.returncode == 0 else f"\n{err}"))
    cpps = sorted(HERE.glob("*.cpp"))
    tc = pcl_toolchain() if cpps else None
    for path in cpps:
        start, end, key = MARKERS[path.suffix]
        markers = dict(start=start, end=end, key=key)
        if tc is None:
            results[path.name] = dict(ok=None, status="NOT RUN", seconds=None,
                                      error="no PCL toolchain: pkg-config finds no pcl_common (set PCL_PREFIX)",
                                      **measure(path), markers=markers)
            print(f"{path.name:20s} NOT RUN  {results[path.name]['lines']:2d} lines, "
                  f"max {results[path.name]['max_line_len']} chars")
            continue
        r = results[path.name] = dict(**run_cpp(path, tc), **measure(path), markers=markers)
        print(f"{path.name:20s} {'ok ' if r['ok'] else 'FAIL'} {r['seconds']:6.2f} s  {r['lines']:2d} lines, "
              f"max {r['max_line_len']} chars  (PCL {r['pcl_version']}, {r['compiler']})"
              + ("" if r["ok"] else f"\n{r['error']}") + "".join(f"\n  warning: {w}" for w in r["build_warnings"]))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(results, indent=1, ensure_ascii=False) + "\n")
    bad = [k for k, v in results.items() if v["ok"] is False or (v["ok"] and not v["within_budget"])]
    print("wrote", OUT, "| failing or over budget:", bad or "none")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
