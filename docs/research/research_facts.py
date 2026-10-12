"""Copy the research numbers that the appendix (B2, B3) and a few notes quote into results/research_facts.json,
so the deck reads them through {research.*} tokens instead of typing them.

Nothing is measured here. Every value is parsed verbatim from a research file in docs/research/ (copied from the
session scratchpad by collect.py) or follows from arithmetic on a project file (float32 steps via np.spacing).
The file is labelled PILOT: single research runs, not final benchmarks. Each group records its source and status
(pilot, synthetic, verified, arithmetic) in the same words as deck/appendix.yaml.

Run:  uv run python docs/research/research_facts.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
TALK = HERE.parents[1]
OUT = TALK / "results" / "research_facts.json"


def read(rel: str) -> str:
    return (HERE / rel).read_text(encoding="utf-8")


def grab(pattern: str, text: str, what: str, flags=0) -> re.Match:
    m = re.search(pattern, text, flags)
    if not m:
        raise SystemExit(f"research_facts: '{what}' not found (pattern {pattern!r})")
    return m


def main() -> int:
    facts: dict = {"label": "PILOT",
                   "note": "values copied verbatim from docs/research/ (single research runs) or computed from "
                           "project files; nothing measured by this script",
                   "script": "docs/research/research_facts.py"}

    # --- big AHN files: LAS headers via 64 KB range requests -----------------------------------------------
    hdr = read("dataset/top_tile_headers.txt")
    m4 = grab(r"ahn4/01_LAZ/C_31HZ2\.LAZ .*?\n\s+LAS [\d.]+ PF \d+ points (\d+)", hdr, "AHN4 C_31HZ2 points", re.S)
    m5 = grab(r"AHN5/01_LAZ/2023_C_31HZ2\.LAZ HTTP 206 bytes \d+ total bytes \d+-\d+/(\d+)\n\s+LAS [\d.]+ PF (\d+) "
              r"points (\d+) mins \[\s*([\d.e+-]+)\s+([\d.e+-]+)\s+[\d.e+-]+\] maxs \[\s*([\d.e+-]+)\s+([\d.e+-]+)",
              hdr, "AHN5 2023_C_31HZ2 header")
    x0, y0, x1, y1 = (float(m5.group(i)) for i in (4, 5, 6, 7))
    facts["ahn4_c_31hz2"] = {"points": int(m4.group(1)), "status": "verified",
                             "source": "dataset/top_tile_headers.txt (LAS header, AHN4 C_31HZ2.LAZ)"}
    facts["ahn5_c_31hz2"] = {"bytes": int(m5.group(1)), "gb": int(m5.group(1)) / 1e9,
                             "points": int(m5.group(3)), "point_format": int(m5.group(2)),
                             "width_km": (x1 - x0) / 1000, "height_km": (y1 - y0) / 1000, "status": "verified",
                             "units": "gb = decimal GB (10^9 bytes); km from the header mins and maxs",
                             "source": "dataset/top_tile_headers.txt (HTTP Content-Range total and LAS header)"}

    # --- the 1 km AHN file on disk ------------------------------------------------------------------------
    vf = json.loads(read("notes/verify_facts.json"))
    facts["tile_1km_file"] = {"bytes": vf["tile_file_bytes"], "mb": vf["tile_file_bytes"] / 1e6, "status": "verified",
                              "units": "mb = decimal MB (10^6 bytes)",
                              "source": "notes/verify_facts.json tile_file_bytes (AHN5_C_135000_455000.COPC.LAZ)"}
    facts["bytes_per_point"] = {"float32_xyz": vf["bytes_float32_xyz"], "float64_xyz": vf["bytes_float64_xyz"],
                                "float32_xyz_plus_uint8_class": vf["bytes_float32_xyz_plus_uint8_class"],
                                "status": "arithmetic", "source": "notes/verify_facts.json (numpy itemsize)"}

    # --- COPC box query over HTTP (AHN4 1 km file, our crop's bbox) -----------------------------------------
    cr = read("dataset/copc_remote.txt")
    mc = grab(r"== AHN4 Utrecht crop C.*?fetched ~([\d.]+) MB in (\d+) HTTP calls, ([\d.]+)s", cr, "COPC fetch", re.S)
    facts["copc_crop"] = {"mb": float(mc.group(1)), "requests": int(mc.group(2)), "seconds": float(mc.group(3)),
                          "status": "pilot", "units": "mb = decimal MB",
                          "source": "dataset/copc_remote.txt (dataset/copc_remote.py, single run)"}

    # --- 0.1 m voxels on the AHN crop (critic's pilot run) ------------------------------------------------
    cm = grab(r"\| C3 \|.*?real AHN5 \(my run\): ([\d.]+) m keeps \*\*([\d.]+) %\*\* of the crop", read("reports/critic.md"),
              "critic C3")
    facts["voxel_0_1"] = {"voxel_m": float(cm.group(1)), "kept_share": float(cm.group(2)) / 100, "status": "pilot",
                          "source": "reports/critic.md C3 (AHN crop, single run)"}

    # --- float32 step size at the crop's RD coordinates (arithmetic) ----------------------------------------
    pj = json.loads((TALK / "results" / "pipeline.json").read_text(encoding="utf-8"))
    ox, oy = pj["crop"]["origin_local"][:2]
    facts["float32_step_m"] = {"x": float(np.spacing(np.float32(ox))), "y": float(np.spacing(np.float32(oy))),
                               "at_rd": [ox, oy], "status": "arithmetic",
                               "source": "np.spacing(np.float32(v)) at results/pipeline.json crop.origin_local; "
                                         "same values in notes/verify_facts.json float32_spacing_m"}

    # --- B3: Open3D tensor API, CUDA against CPU, synthetic 1 M points --------------------------------------
    lib = read("reports/libraries.md")
    row = lambda name: grab(r"\| " + name + r" \| ([^|]+) \| ([^|]+) \|", lib, name)  # noqa: E731
    ms = lambda s: float(grab(r"([\d.]+) ms", s, s).group(1))  # noqa: E731
    vox, seg, dbs = row("voxel downsample"), row("segment_plane"), row("DBSCAN")
    first = grab(r"([\d.]+) ms first call, ([\d.]+) ms second", vox.group(1), "voxel CUDA")
    n_syn = grab(r"Synthetic data: (\d+)M points", lib, "synthetic size")
    facts["open3d_tensor"] = {"n_points": int(n_syn.group(1)) * 1_000_000,
                              "voxel_cuda_first_ms": float(first.group(1)), "voxel_cuda_second_ms": float(first.group(2)),
                              "voxel_cpu_ms": ms(vox.group(2)), "plane_cuda_ms": ms(seg.group(1)),
                              "plane_cpu_ms": ms(seg.group(2)), "dbscan_cuda_ms": ms(dbs.group(1)),
                              "dbscan_cpu_ms": ms(dbs.group(2)), "status": "synthetic",
                              "source": "reports/libraries.md (Open3D tensor API table; libraries/03_open3d_tensor.py, "
                                        "raw output libraries/out_03_open3d_tensor.txt), single runs"}
    kn = grab(r"On CPU, (\d+)k×(\d+)k with k=(\d+) took \*\*([\d.]+) s\*\*, against \*\*([\d.]+) ms\*\* for SciPy", lib,
              "knn_points")
    facts["pytorch3d_knn"] = {"n_points": int(kn.group(1)) * 1000, "k": int(kn.group(3)),
                              "knn_points_s": float(kn.group(4)), "scipy_ms": float(kn.group(5)), "status": "synthetic",
                              "source": "reports/libraries.md (libraries/07_torch_pytorch3d_interop.py), single run; "
                                        "a later single run in libraries/out_07_torch.txt gives similar values"}
    t7 = grab(r"python ([\d.]+) \| torch (\S+) \| pytorch3d (\S+) \| open3d (\S+)", read("libraries/out_07_torch.txt"),
              "versions")
    facts["b3_versions"] = {"python": t7.group(1), "torch": t7.group(2), "pytorch3d": t7.group(3),
                            "open3d": t7.group(4), "open3d_cuda": vf["o3d_build_cuda"]["CUDA_VERSION"],
                            "scipy": vf["versions"]["scipy"], "status": "verified",
                            "source": "libraries/out_07_torch.txt (first line); notes/verify_facts.json "
                                      "(o3d_build_cuda, versions)"}
    OUT.write_text(json.dumps(facts, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(facts, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
