"""Slide 9: 2 Voxel downsampling. One average point per occupied 0.5 m voxel.

Setup: the cloud from slide 8, built by pipeline.steps (it also carries the multi-return flag as a colour,
which does not change the point positions). Checks: equal to pipeline.steps.downsample and to
results/pipeline.json (points_in, points_after_voxel, params.voxel).
"""

from _setup import check, pipeline_json

import numpy as np

from pipeline import steps

las, xyz, origin = steps.load("crop.laz")
pcd = steps.to_open3d(xyz, np.asarray(las.number_of_returns) > 1)

# --- slide ---
down = pcd.voxel_down_sample(0.5)  # <<
P = np.asarray(down.points)
print(len(xyz), "->", len(P))
# --- end ---

ref = steps.downsample(pcd, 0.5)
check(np.array_equal(P, np.asarray(ref.points)), "same voxels as steps.downsample")
pj = pipeline_json()
if pj is not None:
    check(pj["points_in"] == len(xyz) and pj["points_after_voxel"] == len(P) and pj["params"]["voxel"] == 0.5,
          f"pipeline.json: {pj['points_in']} -> {pj['points_after_voxel']} at {pj['params']['voxel']} m")
