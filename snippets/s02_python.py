"""Slide 2, right column: load a point cloud and voxel-downsample it with Open3D (two lines and a print).

Setup (not on the slide): write the crop as a .pcd file (_setup.write_crop_pcd), because Open3D does not read
LAS/LAZ. The slide code prints "N -> M", like s02_pcl.cpp does on the same crop.pcd.
Checks: the result has as many points as pipeline/run.py's voxel downsampling (results/pipeline.json).
"""

from _setup import check, pipeline_json, write_crop_pcd

import open3d as o3d

# Open3D cannot read the LAZ itself: 0 points and only a warning (gotcha shown on slide 6)
check(len(o3d.io.read_point_cloud("crop.laz").points) == 0, "o3d.io.read_point_cloud('crop.laz') gives 0 points")
xyz = write_crop_pcd("crop.pcd")  # same file s02_pcl.cpp reads (run_all.py)
path = "crop.pcd"

# --- slide ---
pcd = o3d.io.read_point_cloud(path)
down = pcd.voxel_down_sample(0.5)  # <<
print(len(pcd.points), "->",
      len(down.points))
# --- end ---

check(len(pcd.points) == len(xyz), f"read {len(pcd.points)} points from crop.pcd")
pj = pipeline_json()
if pj is not None:
    check(len(down.points) == pj["points_after_voxel"],
          f"{len(down.points)} voxels = pipeline.json points_after_voxel")
