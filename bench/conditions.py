"""Benchmark conditions, collected from the machine (never typed by hand).

Keys follow CONTRACTS.md (`conditions` in results/bench_cliff.json and results/memory.json):
    cpu, cores, threads, ram_gib, os, kernel, governor, boost, python, numpy, scipy, open3d, laspy,
    load_avg_before, load_avg_after, date_utc, data, n, runs, warmup, statistic
Everything else (driver, EPP, temperatures, thread env vars, allocator setting, ...) goes under `extra`.

    uv run python bench/conditions.py          # print the current machine's conditions as JSON
"""

from __future__ import annotations

import json
import os
import platform
import sys
from datetime import datetime, timezone
from glob import glob
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

CPU = Path("/sys/devices/system/cpu")


def _read(path) -> str | None:
    try:
        return Path(path).read_text().strip()
    except OSError:
        return None


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def load_avg() -> list[float]:
    return [round(x, 2) for x in os.getloadavg()]


def cpu_model() -> str | None:
    for line in (_read("/proc/cpuinfo") or "").splitlines():
        if line.startswith("model name"):
            return line.split(":", 1)[1].strip()
    return platform.processor() or None


def physical_cores() -> int | None:
    pairs, phys, core = set(), None, None
    for line in (_read("/proc/cpuinfo") or "").splitlines():
        if line.startswith("physical id"):
            phys = line.split(":", 1)[1].strip()
        elif line.startswith("core id"):
            core = line.split(":", 1)[1].strip()
        elif not line.strip() and core is not None:
            pairs.add((phys, core))
            phys = core = None
    if core is not None:
        pairs.add((phys, core))
    if pairs:
        return len(pairs)
    try:
        import psutil
        return psutil.cpu_count(logical=False)
    except Exception:
        return None


def ram_gib() -> float | None:
    for line in (_read("/proc/meminfo") or "").splitlines():
        if line.startswith("MemTotal:"):
            return round(int(line.split()[1]) * 1024 / 2**30, 1)
    return None


def ram_available_gib() -> float | None:
    for line in (_read("/proc/meminfo") or "").splitlines():
        if line.startswith("MemAvailable:"):
            return round(int(line.split()[1]) * 1024 / 2**30, 1)
    return None


def os_pretty_name() -> str | None:
    for line in (_read("/etc/os-release") or "").splitlines():
        if line.startswith("PRETTY_NAME="):
            return line.split("=", 1)[1].strip().strip('"')
    return platform.system() or None


def _policy_values(name: str) -> list[str]:
    vals = [_read(p) for p in sorted(glob(str(CPU / "cpufreq" / "policy*" / name)))]
    if not vals:
        vals = [_read(p) for p in sorted(glob(str(CPU / "cpu[0-9]*" / "cpufreq" / name)))]
    return [v for v in vals if v is not None]


def _summarise(vals: list[str]) -> str | None:
    if not vals:
        return None
    uniq = sorted(set(vals))
    return uniq[0] if len(uniq) == 1 else "mixed: " + ", ".join(uniq)


def governor() -> str | None:
    return _summarise(_policy_values("scaling_governor"))


def boost() -> dict:
    """Boost state from /sys: global cpufreq/boost, per-policy boost (amd-pstate), or intel_pstate/no_turbo."""
    sources = {}
    g = _read(CPU / "cpufreq" / "boost")
    if g is not None:
        sources[str(CPU / "cpufreq" / "boost")] = g
    per = _policy_values("boost")
    if per:
        sources[str(CPU / "cpufreq" / "policy*" / "boost")] = _summarise(per)
    nt = _read(CPU / "intel_pstate" / "no_turbo")
    if nt is not None:
        sources[str(CPU / "intel_pstate" / "no_turbo")] = nt
    states = set()
    for path, v in sources.items():
        if v is None or v.startswith("mixed"):
            states.add("mixed")
        elif path.endswith("no_turbo"):
            states.add("off" if v == "1" else "on")
        else:
            states.add("on" if v == "1" else "off")
    state = "unknown" if not states else (states.pop() if len(states) == 1 else "mixed")
    return {"state": state, "sources": sources}


def cpu_temp_c() -> float | None:
    for hw in sorted(glob("/sys/class/hwmon/hwmon*")):
        if _read(Path(hw) / "name") in ("k10temp", "coretemp", "zenpower"):
            t = _read(Path(hw) / "temp1_input")
            if t is not None:
                return int(t) / 1000.0
    return None


def ver(dist: str) -> str | None:
    try:
        return version(dist)
    except PackageNotFoundError:
        return None


def snapshot() -> dict:
    """Small state snapshot taken before and after each block."""
    freqs = [int(v) for v in _policy_values("scaling_cur_freq") if v.isdigit()]
    return {"time_utc": utc_now(), "load_avg": load_avg(), "cpu_temp_c": cpu_temp_c(),
            "cpu_freq_mhz_mean": round(sum(freqs) / len(freqs) / 1000.0) if freqs else None,
            "ram_available_gib": ram_available_gib()}


def collect(*, data: str, n: int, runs: int, warmup: int, statistic: str, date_utc: str | None = None,
            load_avg_before: list[float] | None = None, load_avg_after: list[float] | None = None,
            extra: dict | None = None) -> dict:
    b = boost()
    max_khz = _policy_values("cpuinfo_max_freq")
    ext = {
        "boost_sources": b["sources"],
        "scaling_driver": _summarise(_policy_values("scaling_driver")),
        "energy_performance_preference": _summarise(_policy_values("energy_performance_preference")),
        "cpu_max_mhz": round(max(int(v) for v in max_khz) / 1000) if max_khz else None,
        "cpu_temp_c_at_collect": cpu_temp_c(),
        "ram_available_gib_at_collect": ram_available_gib(),
        "affinity_cpus": len(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else None,
        "python_implementation": platform.python_implementation(),
        "python_full": sys.version.split()[0] + " " + " ".join(sys.version.split()[1:]),
        "gil_enabled": getattr(sys, "_is_gil_enabled", lambda: True)(),
        "lazrs": ver("lazrs"),
        "psutil": ver("psutil"),
        "thread_env": {k: os.environ.get(k) for k in
                       ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")},
        "transparent_hugepage": _read("/sys/kernel/mm/transparent_hugepage/enabled"),
    }
    ext.update(extra or {})
    return {
        "cpu": cpu_model(),
        "cores": physical_cores(),
        "threads": os.cpu_count(),
        "ram_gib": ram_gib(),
        "os": os_pretty_name(),
        "kernel": platform.release(),
        "governor": governor(),
        "boost": b["state"],
        "python": platform.python_version(),
        "numpy": ver("numpy"),
        "scipy": ver("scipy"),
        "open3d": ver("open3d"),
        "laspy": ver("laspy"),
        "load_avg_before": load_avg_before if load_avg_before is not None else load_avg(),
        "load_avg_after": load_avg_after,
        "date_utc": date_utc or utc_now(),
        "data": data,
        "n": n,
        "runs": runs,
        "warmup": warmup,
        "statistic": statistic,
        "extra": ext,
    }


if __name__ == "__main__":
    print(json.dumps(collect(data=None, n=None, runs=None, warmup=None, statistic=None,
                             load_avg_after=load_avg()), indent=2))
