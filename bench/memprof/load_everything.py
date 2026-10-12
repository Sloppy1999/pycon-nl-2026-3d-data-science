"""Scalene target: load everything, then voxel-downsample (the slide 8-12 way), line for line.

    uv run scalene run -o OUT.json bench/memprof/load_everything.py --- [crop|tile|FILE]

Same four statements as the `pipeline` case of bench/bench_memory.py. Single-threaded Lazrs backend: see chunked.py.
"""
import sys
from pathlib import Path

import laspy
import open3d as o3d

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common import DATA_CROP, DATA_TILE  # noqa: E402

arg = sys.argv[1] if len(sys.argv) > 1 else "tile"
path = {"crop": DATA_CROP, "tile": DATA_TILE}.get(arg, Path(arg))

las = laspy.read(path, laz_backend=laspy.LazBackend.Lazrs)
xyz = las.xyz - las.header.mins
pcd = o3d.geometry.PointCloud(o3d.utility.Vector3dVector(xyz))
down = pcd.voxel_down_sample(0.5)
print(f"{len(down.points)} points kept")
