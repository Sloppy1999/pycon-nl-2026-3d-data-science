"""Slide 12: 3 Ground removal. One RANSAC plane per 25 m tile, fitted to the tile's low points only, and no ground
on a roof.

The slide code is pipeline.steps.remove_ground with a simpler roof rule: z is metres above the crop's lowest point
(the local origin of slide 10), so a tile whose lowest points are 5 m or more up is a roof tile and gets no ground (the last line of the loop
assigns False there; RANSAC has run anyway, as in steps.remove_ground, so the random numbers line up).
steps.remove_ground does this with its plausibility check, which also repairs tilted tiles by borrowing the plane of
the nearest good tile. 5 m separates the tiles the same way here: the accepted tiles' lowest points are below 3.6 m,
the flagged ones' above 6.7 m (checked below).
Checks: the same ground mask as steps.remove_ground in every tile its plausibility check accepts; every voxel that
differs lies in a tile it flagged (the number is printed and checked against results/pipeline.json); two seeded runs
agree.
"""

from _setup import check, labels_npz, pipeline_json

import numpy as np
import open3d as o3d

from pipeline import steps
from pipeline.steps import tiles

las, xyz, origin = steps.load("crop.laz")
down = steps.downsample(steps.to_open3d(xyz, np.asarray(las.number_of_returns) > 1), 0.5)
P = np.asarray(down.points)

# --- slide ---
o3d.utility.random.seed(0)
ground = np.zeros(len(P), bool)
for i in tiles(P, 25):  # <<
    z0 = np.percentile(P[i, 2], 2)
    low = i[P[i, 2] < z0 + 1.5]
    t = down.select_by_index(low)
    _, inl = t.segment_plane(
        0.4, 3, 300,
        probability=1.0)
    ground[low[inl]] = z0 < 5
# --- end ---

ref, planes = steps.remove_ground(down, 25)
tile_of = {tuple(np.floor(P[i[0], :2] / 25).astype(int)): k for k, i in enumerate(tiles(P, 25))}
flagged = {tuple(p.ij) for p in planes if p.rejected}
ij = np.floor(P[:, :2] / 25).astype(int)
differs = ground != ref
in_flagged = np.array([tuple(t) in flagged for t in ij])
z_low = {tuple(p.ij): p.z_low for p in planes}
check(max(z_low[t] for t in z_low if t not in flagged) < 5 <= min(z_low[t] for t in flagged),
      "5 m splits the accepted tiles' z_low from the flagged ones'")
check(not (differs & ~in_flagged).any(), f"same ground mask as steps.remove_ground in all {len(planes) - len(flagged)} "
      f"tiles its plausibility check accepts")
print(f"{int(differs.sum())} of {len(P)} voxels differ, all in the {len(flagged)} of {len(planes)} tiles it flagged")
again, _ = steps.remove_ground(down, 25)
check(np.array_equal(ref, again), "a second seeded run gives the same mask")
pj = pipeline_json()
if pj is not None:
    p = pj["params"]
    check((p["tile"], p["ransac_threshold"], p["ransac_n"], p["ransac_iterations"], p["ransac_probability"],
           p["seed"], p["low_prefilter"]["percentile"], p["low_prefilter"]["window_m"]) == (25.0, 0.4, 3, 300, 1.0, 0, 2.0, 1.5),
          "same parameters as results/pipeline.json")
    check(len(flagged) == pj["tiles_flagged"], f"{len(flagged)} flagged tiles = pipeline.json tiles_flagged")
    z = labels_npz()
    if z is not None:
        check(np.array_equal(z["voxel_ground"], ref), "steps.remove_ground mask = results/labels_crop.npz")
    print("pipeline.json ground: precision", pj["ground"]["precision"], "recall", pj["ground"]["recall"])
