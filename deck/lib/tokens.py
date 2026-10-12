"""Token resolution for content.yaml / notes.yaml / appendix.yaml.

A token is {file.key.subkey|fmt}; file is one of pipeline, bench, memory, snippets, research, facts, profile, ft
(results/pipeline.json, results/bench_cliff.json, results/memory.json, results/snippets.json,
results/research_facts.json: research numbers copied verbatim by docs/research/research_facts.py, label PILOT;
results/python_facts.json, results/profile_loop.json, results/bench_freethreaded.json,
results/eigen_features.json).
Missing values render as a visible "[file.key.subkey]" and are recorded in `Resolver.missing`.

Formats (content.yaml header):
  int   1 239 310 (no-break space U+00A0 as thousands separator: Fira Sans and Fira Mono have no U+202F)
  pct   94 %      pct1  93.7 %    (fractions <= 1 are scaled by 100)
  f1/f2 one or two decimals
  x     79x (integer, rounded; values below 10 keep one decimal so 4.8 does not become 5)
  ms    5.7 ms / 450 ms / 14.9 s (value in ms)
  ns    450 ns     ns1  3.5 ns (one decimal)     us1  3.0 us (micro sign)
  gb    27.8 GB (value already in GiB)   gb1  MiB value shown as 3.3 GB    mb  985 MB
  m     0.5 m       cm  1.6 cm (value in m)    s1  2.8 s (value in s, one decimal)   sms  value in s shown as ms
  f2t   up to two decimals, trailing zeros dropped (5, 6.25)
  nb    a string value kept on one line (no-break spaces, ' - ' as a minus sign), e.g. an expression
The number and its unit are joined with a no-break space (U+00A0).
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any

NNBSP = "\u00a0"   # thousands separator: a no-break space (U+00A0, in Fira Sans; U+202F is not)
NBSP = " "    # no-break space (number to unit)
MICRO = "µ"
TIMES = "×"
MINUS = "\u2212"  # minus sign (no line break after it, unlike the hyphen-minus)

FILES = {
    "pipeline": "pipeline.json",
    "bench": "bench_cliff.json",
    "memory": "memory.json",
    "snippets": "snippets.json",
    "research": "research_facts.json",
    "facts": "python_facts.json",          # bench/python_facts.py: copy or view at each hand-off, Vector3dVector timings
    "profile": "profile_loop.json",        # bench/profile_loop.py: cProfile of the slide-19 loop
    "ft": "bench_freethreaded.json",       # bench/bench_freethreaded.py: the loop on free-threaded CPython
    "eco": "ecosystem.json",               # deck/ecosystem/merge.py: counts and status of the catalogue (slide 3, B7)
    "copc": "copc_remote.json",            # bench/copc_remote.py: the crop box read from the AHN5 file over HTTP (B2)
    "eigen": "eigen_features.json",        # bench/eigen_features.py: eigenvalue features + Random Forest vs rules (B5)
    "bgt": "bgt_street_furniture.json",    # bench/bgt_street_furniture.py: BGT poles and street furniture in the crop
    "trace": "memory_trace.json",          # bench/bench_memory_trace.py: RSS over time, load everything vs chunked (cross-check)
    "prof": "profile_scalene.json",        # bench/profile_loop_scalene.py: Scalene's CPU profile of the slide-19 loop (slide 22)
    "scalene": "memory_scalene.json",      # bench/bench_memory_scalene.py: Scalene's memory timeline, same two cases (slide 26)
}

TOKEN_RE = re.compile(r"\{([a-z_]+(?:\.[A-Za-z0-9_\-]+)+)(?:\|([a-z0-9]+))?\}")
_MISSING = object()


def fmt_int(v: float) -> str:
    n = int(round(float(v)))
    s = f"{abs(n):,}".replace(",", NNBSP)
    return ("-" if n < 0 else "") + s


def _trim(v: float, nd: int = 2) -> str:
    s = f"{float(v):.{nd}f}".rstrip("0").rstrip(".")
    return s if s not in ("", "-0") else "0"


def format_value(v: Any, fmt: str | None) -> str:
    if isinstance(v, bool):
        return "yes" if v else "no"
    if fmt is None:
        if isinstance(v, int):
            return fmt_int(v)
        if isinstance(v, float):
            return fmt_int(v) if v.is_integer() and abs(v) >= 1000 else _trim(v, 3)
        return str(v)
    if fmt == "nb":                      # a string kept on one line: no-break spaces, and " - " as a minus sign
        return str(v).replace(" - ", NBSP + MINUS + NBSP).replace(" ", NBSP)   # (a hyphen is a line-break point)
    v = float(v)
    if fmt == "int":
        return fmt_int(v)
    if fmt in ("pct", "pct1"):
        p = v * 100 if abs(v) <= 1.0 else v
        return (f"{round(p):d}" if fmt == "pct" else f"{p:.1f}") + NBSP + "%"
    if fmt == "f1":
        return f"{v:.1f}"
    if fmt == "f2":
        return f"{v:.2f}"
    if fmt == "x":
        return (f"{v:.1f}" if abs(v) < 10 else fmt_int(v)) + TIMES
    if fmt == "ms":
        if v < 10:
            return f"{v:.1f}{NBSP}ms"
        if v < 1000:
            return f"{round(v):d}{NBSP}ms"
        return f"{v / 1000:.1f}{NBSP}s"
    if fmt == "ns":
        return fmt_int(v) + NBSP + "ns"
    if fmt == "ns1":
        return f"{v:.1f}{NBSP}ns"
    if fmt == "us1":
        return f"{v:.1f}{NBSP}{MICRO}s"
    if fmt == "gb":
        return f"{v:.1f}{NBSP}GB"
    if fmt == "gb1":
        return f"{v / 1024:.1f}{NBSP}GB"
    if fmt == "mb":
        return fmt_int(v) + NBSP + "MB"
    if fmt == "m":
        return _trim(v, 2) + NBSP + "m"
    if fmt == "cm":
        return f"{v * 100:.1f}{NBSP}cm"
    if fmt == "s1":
        return f"{v:.1f}{NBSP}s"
    if fmt == "sms":                     # a value in seconds shown in ms (as fmt ms)
        return format_value(v * 1000.0, "ms")
    if fmt == "f2t":
        return _trim(v, 2)
    raise ValueError(f"unknown format '{fmt}'")


class Resolver:
    """Loads results/*.json once and resolves tokens; records every miss."""

    def __init__(self, results_dir: Path):
        self.results_dir = Path(results_dir)
        self.data: dict[str, Any] = {}
        self.load_errors: dict[str, str] = {}
        self.labels: dict[str, Any] = {}
        for key, fname in FILES.items():
            p = self.results_dir / fname
            if not p.exists():
                continue
            try:
                self.data[key] = json.loads(p.read_text(encoding="utf-8"))
                if isinstance(self.data[key], dict):
                    self.labels[key] = self.data[key].get("label")
            except Exception as exc:  # malformed result file: report, treat as missing
                self.load_errors[key] = f"{fname}: {exc}"
        self.missing: list[dict] = []
        self.used: list[dict] = []
        self._context = ""

    # -- lookups ------------------------------------------------------------------
    def context(self, where: str):
        self._context = where
        return self

    def lookup(self, path: str) -> Any:
        parts = path.split(".")
        cur: Any = self.data.get(parts[0], _MISSING)
        i = 1
        while i < len(parts):
            p = parts[i]
            if cur is _MISSING or cur is None:
                return _MISSING
            if isinstance(cur, dict):
                # a key that itself holds a dot (a file name such as "s02_pcl.cpp" in snippets.json): the longest
                # run of parts that names a key wins
                for j in range(len(parts), i, -1):
                    k = ".".join(parts[i:j])
                    if k in cur:
                        cur, i = cur[k], j
                        break
                else:
                    return _MISSING
                continue
            elif isinstance(cur, list) and p.isdigit() and int(p) < len(cur):
                cur = cur[int(p)]
            else:
                return _MISSING
            i += 1
        return _MISSING if cur is None else cur

    def number(self, path: str, where: str | None = None) -> float | None:
        """Numeric value of a dotted key (no braces), or None (recorded as missing)."""
        v = self.lookup(path)
        if v is _MISSING or isinstance(v, (dict, list)) or isinstance(v, bool):
            self._miss(path, None, where)
            return None
        try:
            f = float(v)
        except (TypeError, ValueError):
            self._miss(path, None, where)
            return None
        if math.isnan(f):
            self._miss(path, None, where)
            return None
        self.used.append({"token": path, "where": where or self._context, "value": v})
        return f

    def has(self, path: str) -> bool:
        return self.lookup(path) is not _MISSING

    def _miss(self, path, fmt, where):
        self.missing.append({"token": path, "fmt": fmt, "where": where or self._context,
                             "file": FILES.get(path.split(".")[0], "?")})

    # -- string resolution ----------------------------------------------------------
    def resolve(self, text: Any, where: str | None = None) -> Any:
        if not isinstance(text, str) or "{" not in text:
            return text

        def sub(m: re.Match) -> str:
            path, fmt = m.group(1), m.group(2)
            v = self.lookup(path)
            if v is _MISSING or isinstance(v, (dict, list)):
                self._miss(path, fmt, where)
                return f"[{path}]"
            try:
                out = format_value(v, fmt)
            except (TypeError, ValueError):
                self._miss(path, fmt, where)
                return f"[{path}]"
            self.used.append({"token": path, "fmt": fmt, "where": where or self._context, "value": v})
            return out

        return TOKEN_RE.sub(sub, text)

    def resolve_tree(self, obj: Any, where: str | None = None) -> Any:
        if isinstance(obj, dict):
            return {k: self.resolve_tree(v, where) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self.resolve_tree(v, where) for v in obj]
        return self.resolve(obj, where)


def unresolved_in(text: str) -> list[str]:
    """Tokens that survived resolution (should never happen) and [file.key] placeholders."""
    out = [m.group(0) for m in TOKEN_RE.finditer(text)]
    out += re.findall(r"\[(?:pipeline|bench|memory|snippets|research|facts|profile|ft)\.[A-Za-z0-9_.\-]+\]", text)
    return out
