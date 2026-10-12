// Slide 2, left column (shown greyed out): the same two operations in C++ with PCL.
//
// Compiled and run on 2026-10-12 with PCL 1.15.1 and g++ 15.3.0 (conda-forge, user-space micromamba env, see
// docs/HOW_TO_UPDATE.md), no warnings with -Wall -Wextra. Build (snippets/run_all.py does the same):
//   g++ -std=c++17 -O2 -Wall -Wextra s02_pcl.cpp $(pkg-config --cflags --libs pcl_io pcl_filters) -o s02_pcl
// Input: crop.pcd as written by s02_python.py (local coordinates, float32). Observed output:
//   722961 -> 230519      (Open3D on the same file: 722961 -> 232180)
// Both keep one centroid per occupied voxel, but PCL anchors its grid at multiples of the leaf size
// (floor(p / leaf), filters/impl/voxel_grid.hpp) and Open3D at the minimum bound minus half a voxel
// (PointCloud::VoxelDownSample), so the voxels and their count differ.
// Slide region markers in C++: "// --- slide ---" / "// --- end ---".
#include <iostream>

#include <pcl/filters/voxel_grid.h>
#include <pcl/io/pcd_io.h>
#include <pcl/point_types.h>

int main() {
// --- slide ---
using Cloud =
    pcl::PointCloud<pcl::PointXYZ>;
Cloud::Ptr cloud(new Cloud);
Cloud down;
if (pcl::io::loadPCDFile(
    "crop.pcd", *cloud)) return 1;
pcl::VoxelGrid<pcl::PointXYZ> vg;
vg.setInputCloud(cloud);
vg.setLeafSize(0.5f, 0.5f, 0.5f);  // <<
vg.filter(down);
std::cout << cloud->size()
  << " -> " << down.size() << "\n";
// --- end ---
  return 0;
}
