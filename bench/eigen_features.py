"""Could a classifier replace the labelling rules? Eigenvalue features plus a Random Forest (backup slide B5).

    uv run --group ml python bench/eigen_features.py --final    # writes results/eigen_features.json

The idea comes from F. Poux, "Real-Time 3D Point Cloud Classification for 3D Shapes (PCA + Random Forests)"
(YouTube, 2025-03-20): describe a point set by the eigenvalues of its 3 x 3 covariance matrix and let a Random Forest
name it. Poux classifies whole synthetic shapes; here the point sets are the pipeline's clusters of the AHN5 crop.

Reads results/labels_crop.npz (pipeline/run.py: voxels, cluster ids, rule classes, height above ground, multiple
return share) and the AHN classes of the crop (data/utrecht_jaarbeurs_200m.laz, only for scoring, as in
pipeline/steps.score).

* Features per cluster, vectorised over clusters (one ``np.linalg.eigvalsh`` call on a stack of 3 x 3 matrices):
  with eigenvalues l1 >= l2 >= l3, linearity (l1 - l2) / l1, planarity (l2 - l3) / l1, sphericity l3 / l1, and
  verticality 1 - |z of the smallest eigenvector| (needs ``eigh``). The same features with a Python loop over
  clusters (``np.cov`` and ``eigh`` per cluster) are timed for comparison.
* Truth per cluster: AHN's majority class over the cluster's original points (painted back through the voxel
  index). AHN has no vegetation or street furniture class, so the only fair question is building (AHN 6) vs not
  (AHN 1). Clusters whose majority is AHN 2 (ground) or anything else are left out.
* Rules: the pipeline's own answer (rule 2 or 3 = building), no training.
* Random Forest (scikit-learn, 100 trees, random_state 0): spatial cross-validation, the folds are 50 m blocks of the
  crop (GroupKFold on the cluster centroid), so neighbouring fragments of one building never sit on both sides.
  Two feature sets: the four eigenvalue features alone, and those plus the rules' inputs (top, footprint, multiple
  return share). ``HistGradientBoostingClassifier`` runs on the same folds and feature sets. Score: recall per class and balanced accuracy (the classes are unbalanced), weighted by points (every
  original point counts once, the forest is trained with the same weights) and, for comparison, per cluster.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import laspy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import DATA_CROP, RESULTS, TALK, rel, timed, write_json  # noqa: E402
import conditions  # noqa: E402

sys.path.insert(0, str(TALK))
from pipeline.steps import BUILDINGS, CLASS_NAMES, STREET_FURNITURE, UNLABELLED, VEGETATION  # noqa: E402

RUNS, WARMUP = 7, 1
BLOCK_M = 50.0
STAT = "median and IQR (numpy.percentile, linear) of wall time over the timed runs"
FEATURES = ("linearity", "planarity", "sphericity", "verticality")
RULE_INPUTS = ("top", "foot", "multi")


def eigen_features(P: np.ndarray, ids: np.ndarray, n_cl: int) -> dict[str, np.ndarray]:
    """Covariance per cluster from sums (np.bincount), then one batched eigh: no loop over points or clusters."""
    on = ids >= 0
    k, X = ids[on], P[on]
    n = np.bincount(k, minlength=n_cl).astype(float)
    mean = np.stack([np.bincount(k, X[:, j], n_cl) for j in range(3)], axis=1) / n[:, None]
    D = X - mean[k]
    C = np.empty((n_cl, 3, 3))
    for a in range(3):
        for b in range(a, 3):
            C[:, a, b] = C[:, b, a] = np.bincount(k, D[:, a] * D[:, b], n_cl) / n
    w, v = np.linalg.eigh(C)                    # ascending: w[:, 0] = l3, w[:, 2] = l1
    l3, l2, l1 = np.clip(w, 0, None).T
    l1 = np.maximum(l1, 1e-12)
    return dict(linearity=(l1 - l2) / l1, planarity=(l2 - l3) / l1, sphericity=l3 / l1,
                verticality=1 - np.abs(v[:, 2, 0]))


def eigen_features_loop(P: np.ndarray, ids: np.ndarray, n_cl: int) -> dict[str, np.ndarray]:
    """The same features with a Python loop over clusters (each cluster: np.cov and eigh)."""
    order = np.argsort(ids, kind="stable")
    starts = np.searchsorted(ids[order], np.arange(n_cl + 1))
    out = {f: np.empty(n_cl) for f in FEATURES}
    for c in range(n_cl):
        X = P[order[starts[c]:starts[c + 1]]]
        w, v = np.linalg.eigh(np.cov(X, rowvar=False, bias=True))
        l3, l2, l1 = np.clip(w, 0, None)
        l1 = max(l1, 1e-12)
        out["linearity"][c] = (l1 - l2) / l1
        out["planarity"][c] = (l2 - l3) / l1
        out["sphericity"][c] = l3 / l1
        out["verticality"][c] = 1 - abs(v[2, 0])
    return out


def recall(truth: np.ndarray, pred: np.ndarray, cls: int, w: np.ndarray | None = None) -> float:
    s = truth == cls
    w = np.ones(len(truth)) if w is None else w
    return float(w[s][pred[s] == cls].sum() / w[s].sum())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--final", action="store_true", help="write results/eigen_features.json")
    args = ap.parse_args()

    from sklearn import __version__ as sk_version
    from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
    from sklearn.model_selection import GroupKFold, cross_val_predict

    d = np.load(RESULTS / "labels_crop.npz")
    P, ids = d["voxel_xyz"], d["voxel_cluster"]
    cls_cl = d["cluster_class"]
    n_cl = len(cls_cl)
    on = ids >= 0

    # features: batched vs loop, identical answers
    f = eigen_features(P, ids, n_cl)
    f_loop = eigen_features_loop(P, ids, n_cl)
    same = all(np.allclose(f[k], f_loop[k], atol=1e-9) for k in FEATURES[:3])
    vert_diff = int((np.abs(f["verticality"] - f_loop["verticality"]) > 1e-6).sum())
    t_vec = timed(lambda: eigen_features(P, ids, n_cl), RUNS, WARMUP, collect=False)
    t_loop = timed(lambda: eigen_features_loop(P, ids, n_cl), RUNS, WARMUP, collect=False)

    # the rules' inputs, per cluster (same definitions as pipeline/steps.cluster_features)
    k = ids[on]
    top = np.full(n_cl, -np.inf)
    np.maximum.at(top, k, d["voxel_hag"][on])
    cells = np.floor(P[on, :2]).astype(np.int64)
    key = (k.astype(np.int64) << 32) | ((cells[:, 0] + 2**15) << 16) | (cells[:, 1] + 2**15)
    foot = np.bincount(np.unique(key) >> 32, minlength=n_cl).astype(float)
    n_vox = np.bincount(k, minlength=n_cl)
    multi = np.bincount(k, d["voxel_multi"][on], n_cl) / n_vox
    rule_in = dict(top=top, foot=foot, multi=multi)

    # truth: AHN majority class per cluster over the original points
    las = laspy.read(DATA_CROP)
    ahn = np.asarray(las.classification, dtype=np.int64)
    pt_cl = ids[d["point_voxel"]]
    m = pt_cl >= 0
    codes = np.unique(ahn)
    counts = np.stack([np.bincount(pt_cl[m & (ahn == c)], minlength=n_cl) for c in codes], axis=1)
    major = codes[counts.argmax(axis=1)]
    keep = np.isin(major, (1, 6))
    truth = (major[keep] == 6).astype(int)
    w = counts.sum(axis=1)[keep].astype(float)            # original points per cluster

    rules = np.isin(cls_cl[keep], (BUILDINGS,)).astype(int)

    def scores(pred: np.ndarray) -> dict:
        r = {f"{unit}_{c}": recall(truth, pred, i, wt) for unit, wt in (("points", w), ("clusters", None))
             for i, c in ((1, "building_recall"), (0, "other_recall"))}
        r["points_balanced_accuracy"] = (r["points_building_recall"] + r["points_other_recall"]) / 2
        r["clusters_balanced_accuracy"] = (r["clusters_building_recall"] + r["clusters_other_recall"]) / 2
        return r
    blocks = (np.floor(d["cluster_centroid"][keep] / BLOCK_M) @ np.array([1000, 1])).astype(int)
    n_folds = int(min(5, len(np.unique(blocks))))
    cv = GroupKFold(n_splits=n_folds)

    def forest(cols: tuple[str, ...], boosted: bool = False) -> dict:
        X = np.column_stack([{**f, **rule_in}[c][keep] for c in cols])
        model = (HistGradientBoostingClassifier(random_state=0) if boosted
                 else RandomForestClassifier(n_estimators=100, random_state=0, n_jobs=-1))
        pred = cross_val_predict(model, X, truth, cv=cv, groups=blocks, params={"sample_weight": w})
        out = {"features": list(cols), **scores(pred)}
        if not boosted:  # HistGradientBoosting has no feature_importances_
            imp = model.fit(X, truth, sample_weight=w).feature_importances_
            out["importance"] = {c: float(i) for c, i in zip(cols, imp)}
        return out

    rf_eigen = forest(FEATURES)
    rf_all = forest(FEATURES + RULE_INPUTS)
    hgb_eigen = forest(FEATURES, boosted=True)
    hgb_all = forest(FEATURES + RULE_INPUTS, boosted=True)

    per_class = {}
    for code in (BUILDINGS, VEGETATION, STREET_FURNITURE, UNLABELLED):
        sel = cls_cl == code
        per_class[CLASS_NAMES[code]] = {"clusters": int(sel.sum()),
                                        **{c: float(np.median(f[c][sel])) if sel.any() else None for c in FEATURES}}
    per_ahn = {name: {"clusters": int(s.sum()), **{c: float(np.median(f[c][keep][s])) for c in FEATURES}}
               for name, s in (("ahn_building", truth == 1), ("ahn_other", truth == 0))}

    out = {
        "label": "FINAL" if args.final else "PILOT",
        "script": rel(Path(__file__)),
        "idea": "F. Poux, Real-Time 3D Point Cloud Classification for 3D Shapes (PCA + Random Forests), "
                "YouTube o2fe6faVHEw, 2025-03-20",
        "conditions": conditions.collect(data=rel(DATA_CROP), n=int(on.sum()), runs=RUNS, warmup=WARMUP,
                                         statistic=STAT, extra={"scikit_learn": sk_version}),
        "n_clusters": n_cl,
        "voxels_in_clusters": int(on.sum()),
        "features_identical_loop_vs_batched": bool(same),
        "verticality_differs_clusters": vert_diff,
        "verticality_note": "differs only where the two smallest eigenvalues are equal (the eigenvector is arbitrary)",
        "timing": {"batched": t_vec, "loop_over_clusters": t_loop,
                   "factor": t_loop["median_ms"] / t_vec["median_ms"]},
        "median_features_by_rule_class": per_class,
        "median_features_by_ahn_class": per_ahn,
        "scored": {"clusters": int(keep.sum()), "ahn_building": int(truth.sum()),
                   "ahn_other": int((truth == 0).sum()), "points": int(w.sum()),
                   "points_ahn_building": int(w[truth == 1].sum()), "points_ahn_other": int(w[truth == 0].sum()),
                   "left_out": int((~keep).sum()), "left_out_note": "AHN majority class 2 (ground) or other codes"},
        "rules": {**scores(rules), "note": "rule 2 or 3 = building; no training"},
        "forest_eigen_only": rf_eigen,
        "forest_eigen_plus_rule_inputs": rf_all,
        "hgb_eigen_only": hgb_eigen,
        "hgb_eigen_plus_rule_inputs": hgb_all,
        "cv": {"kind": "GroupKFold on 50 m blocks of the cluster centroid", "folds": n_folds,
               "blocks": int(len(np.unique(blocks))), "block_m": BLOCK_M,
               "forest": "RandomForestClassifier(n_estimators=100, random_state=0, n_jobs=-1)",
               "hgb": "HistGradientBoostingClassifier(random_state=0)"},
        "caveats": [
            "AHN has no vegetation class: only building vs not is scored",
            "the rules were tuned on this crop, so their score is in-sample",
            "points_*: every original point counts once (the forest is trained with the same weights); "
            "clusters_*: a 3-voxel fragment counts as much as a roof",
            "AHN files many facade points as class 1, so facade fragments the rules call buildings count as errors",
        ],
    }
    path = write_json(RESULTS / "eigen_features.json" if args.final else RESULTS.parent / "bench" / "out" / "eigen_features.json",
                      out, final=args.final)
    print(f"wrote {path}")
    print({k: out[k] for k in ("features_identical_loop_vs_batched", "scored")})
    print("timing ms:", round(t_vec["median_ms"], 2), "batched;", round(t_loop["median_ms"], 2), "loop")
    for name in ("rules", "forest_eigen_only", "forest_eigen_plus_rule_inputs", "hgb_eigen_only",
                 "hgb_eigen_plus_rule_inputs"):
        print(name, {k: round(v, 3) for k, v in out[name].items() if isinstance(v, float)})
    print("per rule class", per_class)
    print("per AHN class", per_ahn)
    print("importance", rf_all["importance"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
