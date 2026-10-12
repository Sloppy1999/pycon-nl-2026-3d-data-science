"""Shared setup for the slide snippets (never shown on a slide).

Each snippet imports this module first. It
- puts the project root on ``sys.path`` so ``pipeline.steps`` imports,
- moves into a fresh temporary working directory that holds ``crop.laz``, a symlink to
  ``data/utrecht_jaarbeurs_200m.laz`` (so the slide code can say ``laspy.read("crop.laz")``),
- silences Open3D's info messages,
- offers ``slide_region``, ``pipeline_json``, ``labels_npz`` and ``check`` for the checks after the slide code,
  and ``write_crop_pcd`` for the crop.pcd that s02_python.py and s02_pcl.cpp both read.

The slide region of a snippet is the text between the lines ``# --- slide ---`` and ``# --- end ---``
(``// --- slide ---`` and ``// --- end ---`` in C++). A line ending in ``  # <<`` is the highlighted key line;
the deck strips the marker.
"""

from __future__ import annotations

import atexit
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNIPPETS = ROOT / "snippets"
CROP = ROOT / "data" / "utrecht_jaarbeurs_200m.laz"
RESULTS = ROOT / "results"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import open3d as o3d  # noqa: E402

o3d.utility.set_verbosity_level(o3d.utility.VerbosityLevel.Error)

WORK = Path(tempfile.mkdtemp(prefix="snippet_"))
atexit.register(shutil.rmtree, WORK, ignore_errors=True)
(WORK / "crop.laz").symlink_to(CROP)
os.chdir(WORK)

KEY = "  # <<"


def slide_region(path, start="# --- slide ---", end="# --- end ---") -> list[str]:
    """The lines a slide shows, with the key-line marker stripped."""
    lines = Path(path).read_text().splitlines()
    starts = [i for i, ln in enumerate(lines) if ln.strip() == start]
    ends = [i for i, ln in enumerate(lines) if ln.strip() == end]
    if len(starts) != 1 or len(ends) != 1 or ends[0] < starts[0]:
        raise ValueError(f"{path}: expected exactly one {start!r} ... {end!r} region")
    return [ln[: -len(KEY)] if ln.endswith(KEY) else ln for ln in lines[starts[0] + 1 : ends[0]]]


def pipeline_json() -> dict | None:
    p = RESULTS / "pipeline.json"
    return json.loads(p.read_text()) if p.exists() else None


def labels_npz():
    import numpy as np

    p = RESULTS / "labels_crop.npz"
    return np.load(p) if p.exists() else None


def write_crop_pcd(path="crop.pcd"):
    """Write crop.laz as a .pcd in local coordinates (xyz - header.mins); returns that xyz."""
    from pipeline.steps import load, to_open3d

    _, xyz, _ = load(CROP)
    o3d.io.write_point_cloud(str(path), to_open3d(xyz))
    return xyz


def check(condition: bool, message: str) -> None:
    """Fail loudly: run_all.py records the snippet as not ok."""
    if not condition:
        raise AssertionError(message)
    print("ok:", message)
