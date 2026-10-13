"""DBSCAN (Open3D, the pipeline's step 4) vs scikit-learn HDBSCAN and KMeans on the same voxels.

    uv run --group ml python bench/cluster_alternatives.py [--final]    # writes results/cluster_alternatives.json

Reads results/labels_crop.npz: the voxels above the ground (``voxel_cluster`` >= -1) and the DBSCAN ids the pipeline gave
them (-1 = noise). HDBSCAN needs no eps; KMeans needs k, so it gets the number of DBSCAN clusters and no noise.
Agreement with DBSCAN is the adjusted Rand index over the voxels both call clustered. One run each, no warm-up.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import RESULTS, rel, write_json  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--final", action="store_true", help="write results/cluster_alternatives.json")
    args = ap.parse_args()

    from sklearn import __version__ as sk_version
    from sklearn.cluster import HDBSCAN, KMeans
    from sklearn.metrics import adjusted_rand_score

    d = np.load(RESULTS / "labels_crop.npz")
    up = d["voxel_cluster"] >= -1
    P, ref = d["voxel_xyz"][up], d["voxel_cluster"][up]
    k = int(ref.max()) + 1

    def run(name: str, make) -> dict:
        t = time.perf_counter()
        lab = make().fit_predict(P)
        sec = time.perf_counter() - t
        both = (lab >= 0) & (ref >= 0)
        return {"clusters": int(lab.max()) + 1, "noise_share": float((lab < 0).mean()), "seconds": sec,
                "ari_vs_dbscan": float(adjusted_rand_score(ref[both], lab[both]))}

    out = {
        "script": rel(Path(__file__)), "voxels": int(len(P)), "scikit_learn": sk_version,
        "dbscan_open3d": {"clusters": k, "noise_share": float((ref < 0).mean()), "note": "ids from the pipeline"},
        "hdbscan": run("hdbscan", lambda: HDBSCAN(min_cluster_size=6, n_jobs=-1, copy=True)),
        "kmeans": run("kmeans", lambda: KMeans(n_clusters=k, n_init=1, random_state=0)),
    }
    path = write_json(RESULTS / "cluster_alternatives.json" if args.final else RESULTS.parent / "bench" / "out" / "cluster_alternatives.json",
                      out, final=args.final)
    print(f"wrote {path}")
    for name in ("dbscan_open3d", "hdbscan", "kmeans"):
        print(name, {a: round(v, 3) if isinstance(v, float) else v for a, v in out[name].items() if a != "note"})
    return 0


if __name__ == "__main__":
    sys.exit(main())
