"""Sweep KMeans k and HDBSCAN min_cluster_size against the pipeline's DBSCAN: agreement (ARI) vs seconds.

    uv run --group ml python bench/cluster_sweep.py     # writes bench/out/cluster_sweep.json (pilot only)

Same voxels and reference as cluster_alternatives.py. One run per setting, no warm-up.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import RESULTS, write_json  # noqa: E402

from sklearn.cluster import HDBSCAN, KMeans  # noqa: E402
from sklearn.metrics import adjusted_rand_score  # noqa: E402

d = np.load(RESULTS / "labels_crop.npz")
up = d["voxel_cluster"] >= -1
P, ref = d["voxel_xyz"][up], d["voxel_cluster"][up]


def run(model) -> dict:
    t = time.perf_counter()
    lab = model.fit_predict(P)
    sec = time.perf_counter() - t
    both = (lab >= 0) & (ref >= 0)
    r = {"clusters": int(lab.max()) + 1, "noise_share": round(float((lab < 0).mean()), 3), "seconds": round(sec, 1),
         "ari": round(float(adjusted_rand_score(ref[both], lab[both])), 3)}
    print(r, flush=True)
    return r


out = {"kmeans": {}, "hdbscan": {}}
for k in (64, 256, 1024, 4096):
    print("kmeans k", k, end=" ")
    out["kmeans"][k] = run(KMeans(n_clusters=k, n_init=1, random_state=0))
for m in (3, 6, 12, 24, 48):
    print("hdbscan min_cluster_size", m, end=" ")
    out["hdbscan"][m] = run(HDBSCAN(min_cluster_size=m, n_jobs=-1, copy=True))
print(write_json(RESULTS.parent / "bench" / "out" / "cluster_sweep.json", out, final=False))
