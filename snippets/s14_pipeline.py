"""Slide 14: the whole pipeline as seven calls to pipeline/steps.py.

Checks: the result equals results/labels_crop.npz, written by pipeline/run.py with the same parameters.
"""

from _setup import check, labels_npz, pipeline_json

import numpy as np

from pipeline.steps import (CLASS_NAMES, cluster, downsample, label, load, paint_back, remove_ground,
                            to_open3d)

# --- slide ---
las, xyz, _ = load("crop.laz")
multi = las.number_of_returns > 1
pcd = to_open3d(xyz, multi)
down = downsample(pcd, 0.5)
ground, _ = remove_ground(down, 25)
ids = cluster(down, ground,
              0.75, 6)
cls, _ = label(down, ground, ids)
full = paint_back(xyz, down, cls)  # <<
# --- end ---

print({CLASS_NAMES[k]: int((full == k).sum()) for k in range(5)})
z = labels_npz()
if z is not None:
    check(np.array_equal(full, z["point_class"]), f"same class for all {len(full)} points as results/labels_crop.npz")
pj = pipeline_json()
if pj is not None:
    check({CLASS_NAMES[k]: int((full == k).sum()) for k in range(5)} == pj["label_points"],
          "same label_points as results/pipeline.json")
