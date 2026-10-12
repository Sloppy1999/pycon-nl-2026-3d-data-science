"""Small synthetic checks for pipeline/steps.py. Run: uv run --with pytest pytest tests"""

import sys
from pathlib import Path

import numpy as np
import open3d as o3d

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline import steps as S  # noqa: E402


def cloud(xyz, multi=None):
    return S.to_open3d(np.asarray(xyz, float), multi)


def scene():
    """20 x 20 m flat ground, a 6 x 6 x 6 m single-echo box (building), a 2 m wide, 4 m tall many-echo blob (tree)."""
    g = np.mgrid[0:20:0.5, 0:20:0.5].reshape(2, -1).T
    ground = np.c_[g, np.zeros(len(g))]
    b = np.mgrid[2:8:0.5, 2:8:0.5, 0:6.5:0.5].reshape(3, -1).T
    t = np.mgrid[14:16:0.5, 14:16:0.5, 0:4.5:0.5].reshape(3, -1).T
    xyz = np.r_[ground, b[b[:, 2] > 0.2], t[t[:, 2] > 0.2]]
    multi = np.r_[np.zeros(len(ground) + int((b[:, 2] > 0.2).sum())), np.ones(int((t[:, 2] > 0.2).sum()))]
    return xyz, multi


def test_pipeline_labels_ground_building_vegetation():
    xyz, multi = scene()
    pcd = cloud(xyz, multi)
    ground, planes = S.remove_ground(pcd, tile=25.0)
    ids = S.cluster(pcd, ground, eps=0.75, min_points=6)
    classes, info = S.label(pcd, ground, ids)
    P = np.asarray(pcd.points)
    assert len(planes) == 1
    assert (classes[(P[:, 2] == 0)] == S.GROUND).mean() > 0.95
    assert (classes[(P[:, 0] < 8) & (P[:, 2] > 1)] == S.BUILDINGS).all()
    assert (classes[(P[:, 0] > 13) & (P[:, 2] > 1)] == S.VEGETATION).all()


def test_label_without_clusters_does_not_crash():
    pcd = cloud([[0, 0, 0], [1, 0, 0], [0, 1, 0]], np.zeros(3))
    ground = np.array([True, True, True])
    ids = np.full(3, S.NOT_CLUSTERED)
    classes, info = S.label(pcd, ground, ids)
    assert (classes == S.GROUND).all() and info["clusters"] == []


def test_height_above_without_ground_uses_z():
    P = np.array([[0.0, 0, 1], [1, 0, 2]])
    assert np.array_equal(S.height_above(P, np.zeros(2, bool)), [1, 2])


def test_tiny_tile_gets_no_ground_instead_of_crashing():
    xyz, _ = scene()
    xyz = np.r_[xyz, [[26.0, 1.0, 0.0], [26.5, 1.0, 0.0]]]  # a 2-voxel tile
    ground, _ = S.remove_ground(cloud(xyz), tile=25.0)
    assert not ground[-2:].any()


def test_tiles_cover_every_point_once():
    P = np.random.default_rng(0).uniform(0, 100, (500, 3))
    idx = np.concatenate(S.tiles(P, 25.0))
    assert sorted(idx) == list(range(500))


def test_paint_back_gives_nearest_voxel_class():
    full = np.array([[0.1, 0, 0], [4.9, 0, 0]])
    vox = np.array([[0.0, 0, 0], [5.0, 0, 0]])
    assert S.paint_back(full, vox, np.array([S.GROUND, S.BUILDINGS])).tolist() == [S.GROUND, S.BUILDINGS]
