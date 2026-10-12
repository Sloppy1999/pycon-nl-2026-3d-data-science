"""What does it cost to read the crop's box from the AHN5 file over HTTP? -> results/copc_remote.json

    uv run python bench/copc_remote.py --final

laspy's CopcReader reads one box of a COPC file with HTTP range requests, without downloading the file. This reads the
crop's own box (data/fetch_ahn5.py CROP_BBOX_RD) from the AHN5 file the talk uses (TILE_URL), counts the bytes of
every response body and the requests, and compares the points with the local crop (same count, same classes).
One run per invocation: the figures depend on the network, so they are indicative (B2 says single run).
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import platform
import sys
import time
from pathlib import Path

import numpy as np
import requests
from laspy import Bounds, CopcReader

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import RESULTS, write_json  # noqa: E402

TALK = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("fetch_ahn5", TALK / "data" / "fetch_ahn5.py")
F = importlib.util.module_from_spec(spec)
spec.loader.exec_module(F)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--final", action="store_true", help="write results/copc_remote.json")
    args = ap.parse_args()
    fetched = {"bytes": 0, "requests": 0}
    orig = requests.Session.request

    def counting(self, method, url, *a, **k):
        r = orig(self, method, url, *a, **k)
        fetched["requests"] += 1
        if method.upper() == "GET":
            fetched["bytes"] += len(r.content)
        return r

    requests.Session.request = counting
    x0, y0, x1, y1 = F.CROP_BBOX_RD
    t0 = time.perf_counter()
    url = requests.head(F.TILE_URL, allow_redirects=True, timeout=30).url
    with CopcReader.open(url) as r:
        pts = r.query(Bounds(mins=np.array([x0, y0]), maxs=np.array([x1, y1])))
    seconds = time.perf_counter() - t0
    import laspy
    local = laspy.read(F.HERE / F.CROP_NAME)
    classes = lambda c: {int(k): int(v) for k, v in zip(*np.unique(np.asarray(c), return_counts=True))}  # noqa: E731
    # CopcReader's box includes the upper edge; the crop is half-open (x0 <= x < x1, as in data/fetch_ahn5.py)
    on_edge = int(np.count_nonzero((np.asarray(pts.x) >= x1) | (np.asarray(pts.y) >= y1)))
    keep = (np.asarray(pts.x) < x1) & (np.asarray(pts.y) < y1)
    remote_classes, local_classes = classes(np.asarray(pts.classification)[keep]), classes(local.classification)
    out = {"label": "FINAL" if args.final else "PILOT", "script": "bench/copc_remote.py",
           "url": F.TILE_URL, "bbox_rd": list(F.CROP_BBOX_RD), "mb": round(fetched["bytes"] / 1e6, 1),
           "requests": fetched["requests"], "seconds": round(seconds, 1), "points": len(pts),
           "points_on_upper_edge": on_edge, "points_half_open": int(keep.sum()),
           "same_points_as_local_crop": bool(int(keep.sum()) == len(local.points)), "classes": remote_classes,
           "classes_equal_local": remote_classes == local_classes,
           "date_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "python": platform.python_version(),
           "note": "bytes = sum of GET response bodies (decompressed by requests if gzip); one run, network dependent"}
    path = write_json(RESULTS / "copc_remote.json" if args.final else Path("/dev/stdout"), out, final=args.final)
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
