"""Slide 12: 5 Labelling. Four rules name the clusters; the first rule that fires wins.

The slide region is pipeline.steps.name, verbatim. ``c`` is one cluster (pipeline.steps.Cluster): ``top`` is
its highest point above local ground, ``foot`` its footprint in 1 m cells (m2), ``multi`` its share of
multiple returns (carried through voxel downsampling in a colour channel), ``to_building`` the plan-view
distance to the nearest building point. ``slender``: at most 1.5 m wide, taller than 1.5 m and at least twice
as tall as wide; ``free``: more than 2 m from buildings and 1 m from trees.
Checks: identical source to steps.name, identical classes for every cluster, and the street furniture count
in results/pipeline.json.
"""

import inspect

from _setup import check, pipeline_json, slide_region

import numpy as np

from pipeline import steps
from pipeline.steps import BUILDINGS, STREET_FURNITURE, UNLABELLED, VEGETATION

las, xyz, origin = steps.load("crop.laz")
down = steps.downsample(steps.to_open3d(xyz, np.asarray(las.number_of_returns) > 1), 0.5)
ground, _ = steps.remove_ground(down, 25)
ids = steps.cluster(down, ground, 0.75, 6)
classes, info = steps.label(down, ground, ids)


# --- slide ---
def name(c):
    if c.multi > 0.4 and c.top > 1:  # <<
        return VEGETATION
    if c.foot > 25 and c.top > 2.5:
        return BUILDINGS
    if c.to_building < 2:  # facade
        return BUILDINGS
    if c.slender and c.free:
        return STREET_FURNITURE
    return UNLABELLED
# --- end ---


check(slide_region(__file__) == inspect.getsource(steps.name).splitlines(), "slide code = steps.name, verbatim")
mine = np.array([name(c) for c in info["clusters"]])
check(np.array_equal(mine, info["cluster_classes"]), f"same class for all {len(mine)} clusters")
counts = {steps.CLASS_NAMES[k]: int((mine == k).sum()) for k in (VEGETATION, BUILDINGS, STREET_FURNITURE, UNLABELLED)}
print("clusters per class:", counts)
pj = pipeline_json()
if pj is not None:
    check(pj["n_objects"]["street_furniture"] == counts["street_furniture"],
          f"pipeline.json n_objects.street_furniture = {counts['street_furniture']}")
    for row in pj["street_furniture_objects"]:
        print("street furniture:", row)
