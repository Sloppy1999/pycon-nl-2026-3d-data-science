"""Slide 14: 3 Ground removal. One RANSAC plane per 25 m tile, fitted to the tile's low points only, then a
plausibility check relative to the other tiles.

The slide shows the loop of pipeline.steps.remove_ground and calls its second half, steps.check_planes: a plane
tilted more than 15° or more than 2.5 m above the median tile plane is a roof that slipped through, and that tile
borrows the nearest accepted plane. Every height test is relative (to the tile's low percentile, or to the median
plane): local z is metres above the crop's lowest point, not above the terrain, so no absolute height cut-off.
Checks: the slide mask equals steps.remove_ground and results/labels_crop.npz (the scored mask); same parameters
and flagged tiles as results/pipeline.json; two seeded runs agree.
"""

from _setup import check, labels_npz, pipeline_json

import numpy as np
import open3d as o3d

from pipeline import steps
from pipeline.steps import check_planes, tiles

las, xyz, origin = steps.load("crop.laz")
down = steps.downsample(steps.to_open3d(xyz, np.asarray(las.number_of_returns) > 1), 0.5)
P = np.asarray(down.points)
o3d.utility.random.seed(0)

# --- slide ---
fits = []
for i in tiles(P, 25):  # <<
    z0 = np.percentile(P[i, 2], 2)
    low = i[P[i, 2] < z0 + 1.5]
    t = down.select_by_index(low)
    plane, inl = t.segment_plane(
        0.4, 3, 300,
        probability=1.0)
    fits += [(i, low, inl, plane)]
# Plane too steep or > 2.5 m above
# the median? Use nearest good one.
ground, _ = check_planes(P, fits)
# --- end ---

ref, planes = steps.remove_ground(down, 25)
check(np.array_equal(ground, ref), "slide code mask = steps.remove_ground")
again, _ = steps.remove_ground(down, 25)
check(np.array_equal(ref, again), "a second seeded run gives the same mask")
flagged = sum(p.rejected for p in planes)
print(f"{flagged} of {len(planes)} tiles flagged; z_low of flagged tiles:",
      sorted(round(p.z_low, 1) for p in planes if p.rejected))
z = labels_npz()
if z is not None:
    check(np.array_equal(z["voxel_ground"], ground), "slide mask = results/labels_crop.npz (the scored mask)")
pj = pipeline_json()
if pj is not None:
    p = pj["params"]
    check((p["tile"], p["ransac_threshold"], p["ransac_n"], p["ransac_iterations"], p["ransac_probability"],
           p["seed"], p["low_prefilter"]["percentile"], p["low_prefilter"]["window_m"]) == (25.0, 0.4, 3, 300, 1.0, 0, 2.0, 1.5),
          "same parameters as results/pipeline.json")
    check(flagged == pj["tiles_flagged"], f"{flagged} flagged tiles = pipeline.json tiles_flagged")
    print("AHN class 2 point-level agreement:", pj["ground"])
