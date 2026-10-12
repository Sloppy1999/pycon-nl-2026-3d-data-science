"""Memory per point on the 1 km AHN5 tile, and the chunked voxel snippet of slide 21.

    uv run python bench/bench_memory.py --final                  # writes results/memory.json
    uv run python bench/bench_memory.py --smoke --out DIR/memory_smoke.json [--file crop|tile|PATH] [--repeats 1]
    uv run python bench/bench_memory.py --case NAME --file PATH   # internal: one case, one JSON line on stdout

Method (as in the memory pilot): every case runs in a FRESH subprocess with MALLOC_MMAP_THRESHOLD_=1048576,
so glibc serves blocks >= 1 MiB with mmap and returns them to the OS on free (checked inside each case with
mallinfo2). In the subprocess numpy, laspy and open3d are imported first (same set for every case, so the
baselines match); then gc.collect(), the kernel high-water mark is reset (write "5" to /proc/self/clear_refs)
and VmRSS is read as the baseline (after gc.collect() and malloc_trim(0)). After the measured step:
    peak     = VmHWM - baseline        (read before anything is freed)
    retained = VmRSS - baseline after gc.collect() and glibc malloc_trim(0), i.e. live data; without the trim,
               freed small blocks stay in RSS (Open3D voxel_down_sample leaves tens of B/pt behind), so the
               untrimmed value is recorded too (retained_untrimmed_bytes, bytes_per_point_untrimmed).
Cases (each repeated `--repeats` times, case order shuffled per repeat with a fixed seed):
    read          laspy.read(file)  (default backend: first of laspy.LazBackend.detect_available())
    xyz           after a laspy.read outside the measurement: xyz = las.xyz - las.header.mins  (float64)
    o3d           after read + xyz: pcd = PointCloud(Vector3dVector(xyz))   (temporary vector freed)
    o3d_v_alive   after read + xyz: v = Vector3dVector(xyz); pcd = PointCloud(v)   (both kept: PointCloud copies)
    pipeline      read -> xyz -> PointCloud(Vector3dVector(xyz)) -> voxel_down_sample(0.5), everything kept
    chunked       the slide region of snippets/s21_chunked.py verbatim; afterwards (not measured) its result is
                  compared with a load-everything reference that keeps the first point per voxel in file order
Statistic: median over repeats (min and max kept). Bytes per point = median delta / points in the file.
Computed, NOT run: totals for 2023_C_31HZ2.LAZ (926 203 338 points, from its LAS header).
"""

from __future__ import annotations

import argparse
import gc
import json
import os
import re
import statistics
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import conditions as cond  # noqa: E402
from _common import DATA_CROP, DATA_TILE, RESULTS, SNIPPETS, check_budget, guard_out, rel, slide_source, write_json  # noqa: E402

SEED = 20261015
VOXEL = 0.5
MALLOC_ENV = {"MALLOC_MMAP_THRESHOLD_": "1048576"}
CASES = ("read", "xyz", "o3d", "o3d_v_alive", "pipeline", "chunked")
S21 = SNIPPETS / "s21_chunked.py"
BIG_FILE = {"name": "2023_C_31HZ2.LAZ", "points": 926_203_338, "point_format": 6,
            "source": "LAS header, 64 KB range request",
            "url": "https://basisdata.nl/hwh-ahn/AHN5/01_LAZ/2023_C_31HZ2.LAZ"}
RAM_REFERENCE_GB = [16, 32]
GIB, MIB = 2**30, 2**20


# ----------------------------------------------------------------------------------------- child side
def _status() -> dict:
    out = {}
    with open("/proc/self/status") as f:
        for line in f:
            if line.startswith(("VmRSS:", "VmHWM:")):
                k, v = line.split(":")
                out[k] = int(v.split()[0]) * 1024
    return out


class Stage:
    """Reset the kernel peak-RSS counter, run the block, report peak and retained bytes over the baseline."""

    def __enter__(self):
        gc.collect()
        malloc_trim()                    # baseline = live data too (earlier set-up garbage handed back)
        with open("/proc/self/clear_refs", "w") as f:
            f.write("5")
        self.baseline = _status()["VmRSS"]
        self.t0 = time.perf_counter()
        return self

    def __exit__(self, *exc):
        self.seconds = time.perf_counter() - self.t0
        self.hwm = _status()["VmHWM"]
        gc.collect()
        self.rss_untrimmed = _status()["VmRSS"]
        self.trimmed = malloc_trim()
        self.rss = _status()["VmRSS"]
        return False

    def result(self) -> dict:
        return {"baseline_bytes": self.baseline, "peak_bytes": self.hwm - self.baseline,
                "retained_bytes": self.rss - self.baseline,
                "retained_untrimmed_bytes": self.rss_untrimmed - self.baseline,
                "malloc_trim": self.trimmed, "seconds": self.seconds}


def malloc_trim() -> bool:
    """Hand freed heap memory back to the OS (glibc malloc_trim(0)), so retained = live data. Small blocks
    (< MALLOC_MMAP_THRESHOLD_) live on the heap and are otherwise kept by the allocator after free."""
    try:
        import ctypes
        ctypes.CDLL("libc.so.6").malloc_trim(0)
        return True
    except Exception:
        return False


def malloc_threshold_fixed() -> bool | None:
    """True if a 2 MiB malloc is mmapped right after a 2 MiB free (fixed threshold); False if glibc's
    dynamic threshold moved it to the heap; None if mallinfo2 is unavailable."""
    try:
        import ctypes

        class MI2(ctypes.Structure):
            _fields_ = [(n, ctypes.c_size_t) for n in ("arena", "ordblks", "smblks", "hblks", "hblkhd",
                                                       "usmblks", "fsmblks", "uordblks", "fordblks", "keepcost")]
        libc = ctypes.CDLL("libc.so.6")
        libc.mallinfo2.restype = MI2
        libc.malloc.restype, libc.malloc.argtypes = ctypes.c_void_p, [ctypes.c_size_t]
        libc.free.argtypes = [ctypes.c_void_p]
        size = 2 * MIB
        libc.free(libc.malloc(size))
        h0 = libc.mallinfo2().hblkhd
        p = libc.malloc(size)
        h1 = libc.mallinfo2().hblkhd
        libc.free(p)
        return h1 - h0 >= size
    except Exception:
        return None


def reference_first_per_voxel(path, v):
    """Load everything; first point (file order) of every voxel, sorted by (i, j, k). Independent of the
    snippet's key: groups by a stable lexsort of the integer voxel indices."""
    import laspy
    las = laspy.read(path)
    xyz = las.xyz - las.header.mins
    ijk = (xyz // v).astype(np.int64)
    order = np.lexsort(ijk.T[::-1])
    s = ijk[order]
    new = np.ones(len(s), bool)
    new[1:] = (s[1:] != s[:-1]).any(axis=1)
    return xyz[order[new]]


def run_case(name: str, path: Path) -> dict:
    import laspy
    import open3d as o3d
    o3d.utility.set_verbosity_level(o3d.utility.VerbosityLevel.Error)
    with laspy.open(path) as f:
        n = int(f.header.point_count)
        pf = f.header.point_format
        rec_len = int(pf.size)
    out = {"case": name, "file": rel(path), "points": n, "point_format": int(pf.id), "record_bytes": rec_len,
           "laz_backend_default": laspy.LazBackend.detect_available()[0].name,
           "malloc_threshold_fixed": malloc_threshold_fixed(),
           "env_malloc": os.environ.get("MALLOC_MMAP_THRESHOLD_")}
    if name == "read":
        with Stage() as s:
            las = laspy.read(path)
        out["records_nbytes"] = int(las.points.array.nbytes)
    elif name == "xyz":
        las = laspy.read(path)
        with Stage() as s:
            xyz = las.xyz - las.header.mins
        out["dtype"], out["nbytes"] = str(xyz.dtype), int(xyz.nbytes)
    elif name in ("o3d", "o3d_v_alive"):
        las = laspy.read(path)
        xyz = las.xyz - las.header.mins
        with Stage() as s:
            if name == "o3d":
                pcd = o3d.geometry.PointCloud(o3d.utility.Vector3dVector(xyz))
            else:
                v = o3d.utility.Vector3dVector(xyz)
                pcd = o3d.geometry.PointCloud(v)
        out["o3d_points"] = len(pcd.points)
    elif name == "pipeline":
        with Stage() as s:
            las = laspy.read(path)
            xyz = las.xyz - las.header.mins
            pcd = o3d.geometry.PointCloud(o3d.utility.Vector3dVector(xyz))
            down = pcd.voxel_down_sample(VOXEL)
        out["kept"] = len(down.points)
        out["voxel"] = VOXEL
    elif name == "chunked":
        src = slide_source(S21)
        ns = {"np": np, "laspy": laspy, "path": str(path)}
        code = compile(src, str(S21), "exec")
        with Stage() as s:
            exec(code, ns)
        points = ns["points"]
        out["kept"] = int(len(points))
        out["voxel"] = float(ns["v"])
        out["chunks"] = len(ns["keys"])
        out["survivors_over_kept"] = sum(len(k) for k in ns["keys"]) / len(points)
        m = re.search(r"chunk_iterator\(([\d_]+)\)", src)
        out["chunk_size"] = int(m.group(1).replace("_", "")) if m else None
        res = s.result()                                   # measurement is complete before the check
        del ns
        t0 = time.perf_counter()
        ref = reference_first_per_voxel(path, out["voxel"])
        out["equals_reference"] = bool(np.array_equal(points, ref))
        out["reference_kept"] = int(len(ref))
        out["reference_seconds"] = time.perf_counter() - t0
        out.update(res)
        return out
    else:
        raise SystemExit(f"unknown case {name!r}")
    out.update(s.result())
    return out


# ----------------------------------------------------------------------------------------- parent side
def spawn(name: str, path: Path, timeout: int = 1800) -> dict:
    env = dict(os.environ, **MALLOC_ENV)
    p = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--case", name, "--file", str(path)],
                       capture_output=True, text=True, env=env, timeout=timeout)
    if p.returncode != 0:
        raise SystemExit(f"case {name} failed:\n{p.stderr[-3000:]}")
    return json.loads(p.stdout.strip().splitlines()[-1])


def med(runs: list[dict], key: str) -> dict:
    vals = [r[key] for r in runs]
    return {"median": statistics.median(vals), "min": min(vals), "max": max(vals)}


def verify_big_file(report: Path | None) -> str | None:
    """Optionally confirm BIG_FILE['points'] against the dataset report's header dump."""
    if report is None:
        return None
    text = Path(report).read_text()
    m = re.search(re.escape(BIG_FILE["name"]) + r".*?\n\s*LAS [\d.]+ PF (\d+) points (\d+)", text)
    if not m:
        raise SystemExit(f"{report}: no header line for {BIG_FILE['name']}")
    pf, pts = int(m.group(1)), int(m.group(2))
    if (pf, pts) != (BIG_FILE["point_format"], BIG_FILE["points"]):
        raise SystemExit(f"{report}: header says PF {pf}, {pts} points; script has {BIG_FILE}")
    return f"{report} (PF {pf}, {pts} points)"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--smoke", action="store_true", help="the crop by default, 1 repeat; never writes to results/")
    mode.add_argument("--final", action="store_true", help="the 1 km tile, 3 repeats, results/memory.json")
    mode.add_argument("--case", choices=CASES, help="internal: run one case in this process")
    ap.add_argument("--file", default=None, help="crop | tile | PATH (default: tile for --final, crop for --smoke)")
    ap.add_argument("--repeats", type=int, default=None, help="fresh subprocesses per case (3 final, 1 smoke)")
    ap.add_argument("--out", type=Path, help="output JSON (required for --smoke)")
    ap.add_argument("--date-utc", help="UTC timestamp to record (default: taken at start)")
    ap.add_argument("--header-report", type=Path, help="optional: file with the big file's header dump to verify")
    ap.add_argument("--force", action="store_true", help="--final even with less than 8 GiB RAM available")
    args = ap.parse_args()

    files = {"crop": DATA_CROP, "tile": DATA_TILE}
    path = Path(files.get(args.file, args.file)) if args.file else (DATA_TILE if (args.final or args.case) else DATA_CROP)
    if args.case:
        print(json.dumps(run_case(args.case, path)))
        return 0

    date_utc = args.date_utc or cond.utc_now()
    load_before = cond.load_avg()
    t_start = time.perf_counter()
    if args.final:
        out_path = args.out or RESULTS / "memory.json"
        repeats = args.repeats or 3
        avail = cond.ram_available_gib() or 0
        if avail < 8 and not args.force:
            print(f"refusing --final: only {avail} GiB RAM available (need about 8; or pass --force)", file=sys.stderr)
            return 3
        if load_before[0] > 1.0:
            print(f"warning: 1-minute load average {load_before[0]} (memory numbers are not timing-sensitive)",
                  file=sys.stderr)
    else:
        if args.out is None:
            ap.error("--smoke needs --out (smoke results never go to results/)")
        out_path, repeats = guard_out(args.out, final=False), args.repeats or 1
    verified = verify_big_file(args.header_report)

    rng = np.random.default_rng(SEED)
    runs = {c: [] for c in CASES}
    for r in range(repeats):
        for j in rng.permutation(len(CASES)):
            c = CASES[j]
            res = spawn(c, path)
            runs[c].append(res)
            print(f"[{time.strftime('%H:%M:%S')}] repeat {r + 1}/{repeats} {c:<12s} peak {res['peak_bytes']/MIB:8.1f} MiB"
                  f"  retained {res['retained_bytes']/MIB:8.1f} MiB  {res['seconds']:.2f} s"
                  + (f"  equals_reference={res['equals_reference']}" if c == "chunked" else ""), flush=True)

    first = runs["read"][0]
    n = first["points"]
    m = {c: {"peak": med(runs[c], "peak_bytes"), "retained": med(runs[c], "retained_bytes"),
             "retained_untrimmed": med(runs[c], "retained_untrimmed_bytes"),
             "seconds": med(runs[c], "seconds"), "baseline": med(runs[c], "baseline_bytes")} for c in CASES}
    bpp = lambda c, k: m[c][k]["median"] / n  # noqa: E731
    bytes_per_point = {
        "laspy_read_peak": bpp("read", "peak"),
        "laspy_read_retained": bpp("read", "retained"),
        "xyz_float64": bpp("xyz", "retained"),
        "open3d_points": bpp("o3d", "retained"),
        "pipeline_retained": bpp("pipeline", "retained"),
    }
    equals = [r["equals_reference"] for r in runs["chunked"]]
    chunk_sizes = {r["chunk_size"] for r in runs["chunked"]}
    tile = {
        "file": first["file"],
        "points": n,
        "point_format": first["point_format"],
        "record_bytes": first["record_bytes"],
        "bytes_per_point": bytes_per_point,
        "naive_peak_mb": m["pipeline"]["peak"]["median"] / MIB,
        "chunked_peak_mb": m["chunked"]["peak"]["median"] / MIB,
        "voxel": VOXEL,
        "chunk_size": chunk_sizes.pop() if len(chunk_sizes) == 1 else sorted(chunk_sizes),
        "chunked_equals_reference": bool(all(equals)),
        # ---- extras (not in CONTRACTS.md)
        "units": "bytes per point = median delta over the post-import baseline / points; MB = MiB (2^20 bytes)",
        "bytes_per_point_peak": {"xyz_float64": bpp("xyz", "peak"), "open3d_points": bpp("o3d", "peak"),
                                 "open3d_points_v_alive": bpp("o3d_v_alive", "peak"),
                                 "pipeline": bpp("pipeline", "peak")},
        "open3d_points_v_alive_retained": bpp("o3d_v_alive", "retained"),
        "bytes_per_point_untrimmed": {"laspy_read_retained": bpp("read", "retained_untrimmed"),
                                      "xyz_float64": bpp("xyz", "retained_untrimmed"),
                                      "open3d_points": bpp("o3d", "retained_untrimmed"),
                                      "pipeline_retained": bpp("pipeline", "retained_untrimmed")},
        "retained_method": "VmRSS after gc.collect() and malloc_trim(0) (live data); *_untrimmed = VmRSS before "
                           "the trim (includes freed blocks the allocator keeps)",
        "naive_retained_mb": m["pipeline"]["retained"]["median"] / MIB,
        "chunked_retained_mb": m["chunked"]["retained"]["median"] / MIB,
        "baseline_mb_after_imports": m["pipeline"]["baseline"]["median"] / MIB,
        "naive_kept_open3d_centroids": runs["pipeline"][0]["kept"],
        "chunked_kept_first_points": runs["chunked"][0]["kept"],
        "chunked_chunks": runs["chunked"][0]["chunks"],
        "chunked_survivors_over_kept": runs["chunked"][0]["survivors_over_kept"],
        "chunked_equals_reference_per_repeat": equals,
        "laz_backend_default": first["laz_backend_default"],
        "snippet": {"file": rel(S21), "source": slide_source(S21), "budget": check_budget(S21, 12, 70)},
        "cases": m,
    }
    npts = BIG_FILE["points"]
    f64 = np.dtype(np.float64).itemsize
    import laspy
    rec6 = laspy.PointFormat(BIG_FILE["point_format"]).size
    big = {
        "name": BIG_FILE["name"], "points": npts, "source": BIG_FILE["source"],
        "computed_gb": {
            "las_records": rec6 * npts / GIB,
            "laspy_read_peak": bytes_per_point["laspy_read_peak"] * npts / GIB,
            "plus_xyz": (rec6 + 3 * f64) * npts / GIB,
            "our_pipeline": bytes_per_point["pipeline_retained"] * npts / GIB,
        },
        # ---- extras
        "computed_gb_extra": {
            "our_pipeline_peak": bpp("pipeline", "peak") * npts / GIB,
            "our_pipeline_untrimmed": bpp("pipeline", "retained_untrimmed") * npts / GIB,
        },
        "status": "computed, not run",
        "formulas": {"las_records": f"{rec6} B (PF{BIG_FILE['point_format']} record, laspy.PointFormat) x points",
                     "laspy_read_peak": "measured laspy_read_peak B/pt on the tile x points",
                     "plus_xyz": f"las_records + {3 * f64} B (3 x float64) x points",
                     "our_pipeline": "measured pipeline_retained B/pt on the tile x points",
                     "unit": "GiB (2^30 bytes)"},
        "url": BIG_FILE["url"], "point_format": BIG_FILE["point_format"], "verified_against": verified,
    }
    load_after = cond.load_avg()
    result = {
        "label": "FINAL" if args.final else "SMOKE (not for the deck)",
        "conditions": cond.collect(
            data=rel(path), n=n, runs=repeats, warmup=0,
            statistic=f"median over {repeats} fresh subprocesses per case (min and max under tile_1km.cases)",
            date_utc=date_utc, load_avg_before=load_before, load_avg_after=load_after,
            extra={"malloc": "MALLOC_MMAP_THRESHOLD_=1048576 in every case subprocess (blocks >= 1 MiB are "
                             "mmapped and returned to the OS on free)",
                   "malloc_threshold_fixed_all_cases": all(r["malloc_threshold_fixed"] for c in CASES for r in runs[c]),
                   "malloc_trim_all_cases": all(r["malloc_trim"] for c in CASES for r in runs[c]),
                   "rss_method": "/proc/self/clear_refs=5, then VmHWM (peak) and VmRSS (retained, after "
                                 "gc.collect() and malloc_trim(0); untrimmed value also kept) from /proc/self/status, "
                                 "minus VmRSS after imports; fresh subprocess per case; imports numpy, laspy, open3d "
                                 "in every case",
                   "case_order": f"seeded (numpy default_rng {SEED}) permutation per repeat"}),
        "tile_1km": tile,
        "big_file": big,
        "ram_reference_gb": RAM_REFERENCE_GB,
        "script": "bench/bench_memory.py",
        "runtime_s": time.perf_counter() - t_start,
    }
    if not tile["chunked_equals_reference"]:
        print("WARNING: chunked result differs from the load-everything reference", file=sys.stderr)
    written = write_json(out_path, result, final=bool(args.final))
    print(f"read peak {bytes_per_point['laspy_read_peak']:.1f} B/pt, retained {bytes_per_point['laspy_read_retained']:.1f};"
          f" xyz {bytes_per_point['xyz_float64']:.1f}; open3d {bytes_per_point['open3d_points']:.1f};"
          f" pipeline retained {bytes_per_point['pipeline_retained']:.1f} B/pt")
    print(f"naive peak {tile['naive_peak_mb']:.0f} MiB, chunked peak {tile['chunked_peak_mb']:.0f} MiB, "
          f"equal {tile['chunked_equals_reference']}; big file our_pipeline {big['computed_gb']['our_pipeline']:.1f} GiB")
    print(f"wrote {written} in {result['runtime_s']:.0f} s")
    return 0 if tile["chunked_equals_reference"] else 4


if __name__ == "__main__":
    sys.exit(main())
