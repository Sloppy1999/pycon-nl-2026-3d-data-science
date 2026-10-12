"""Slide 11: 4 Clustering. DBSCAN on what stands more than 0.3 m above the ground.

Checks: the same cluster ids as pipeline.steps.cluster and the count in results/pipeline.json.
"""

from _setup import check, labels_npz, pipeline_json

import numpy as np

from pipeline import steps
from pipeline.steps import height_above

las, xyz, origin = steps.load("crop.laz")
down = steps.downsample(steps.to_open3d(xyz, np.asarray(las.number_of_returns) > 1), 0.5)
P = np.asarray(down.points)
ground, _ = steps.remove_ground(down, 25)

# --- slide ---
hag = height_above(P, ground)
up = ~ground & (hag > 0.3)
rest = down.select_by_index(
    np.flatnonzero(up))
lab = rest.cluster_dbscan(
    eps=0.75, min_points=6)  # <<
ids = np.asarray(lab)
print(ids.max() + 1, "clusters")
# --- end ---

ref = steps.cluster(down, ground, 0.75, 6)
check(np.array_equal(ids, ref[up]) and (ref[~up] == steps.NOT_CLUSTERED).all(), "same ids as steps.cluster")
pj = pipeline_json()
if pj is not None:
    check(pj["n_clusters"] == ids.max() + 1 and pj["params"]["eps"] == 0.75 and pj["params"]["min_points"] == 6,
          f"pipeline.json n_clusters {pj['n_clusters']}, eps 0.75, min_points 6")
z = labels_npz()
if z is not None:
    check(np.array_equal(z["voxel_cluster"], ref), "same ids as results/labels_crop.npz")
