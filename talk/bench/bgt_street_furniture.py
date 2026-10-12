"""What street furniture does the official register list inside the crop's box? -> results/bgt_street_furniture.json

    cd talk && uv run python bench/bgt_street_furniture.py --final            # download, analyse, write the result
    cd talk && uv run python bench/bgt_street_furniture.py --offline --final  # reuse the cached downloads

The pipeline finds 3 street-furniture objects in the 200 m crop. This asks the BGT (Basisregistratie Grootschalige
Topografie, the Dutch large-scale base map) via PDOK's OGC API Features which poles, benches, cabinets and trees it
registers inside the same box (data/fetch_ahn5.py CROP_BBOX_RD, half-open like the crop), keeps only current versions
(eind_registratie empty), and then looks at the AHN points around every registered pole: how many points stand more
than 1.5 m above the local ground within 0.6 m, and how many occupied 0.5 m voxels they make (the pipeline voxel size;
DBSCAN needs min_points = 6). Two cross-checks: the municipality's own street-light export (Gemeente Utrecht OVL
"paaldump" of 25 Nov 2021, CC0) and OpenStreetMap (Overpass; crowd-sourced, ODbL).

Downloads are cached in the system temp dir (never in the repo); --offline reuses them. Downloaded data is parsed with
json / csv only.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

import laspy
import numpy as np
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import DATA_CROP, RESULTS, write_json  # noqa: E402

TALK = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("fetch_ahn5", TALK / "data" / "fetch_ahn5.py")
F = importlib.util.module_from_spec(spec)
spec.loader.exec_module(F)

CACHE = Path(tempfile.gettempdir()) / "talk_bgt_cache"
UA = "pycon-nl-2026-talk-3d-data-science (research script)"
BGT = "https://api.pdok.nl/lv/bgt/ogc/v1"
RD = "http://www.opengis.net/def/crs/EPSG/0/28992"
POLES = "paal"  # BGT collection of poles (lichtmast, afsluitpaal, verkeersbordpaal, ...)
FURNITURE = ["straatmeubilair", "kast", "bord", "mast", "sensor_punt", "installatie", "bak",
             "weginrichtingselement_punt"]
GROUND_LEVEL = ["put"]  # manholes and gullies: in the register, but flat on the ground (not street furniture)
TREES = "vegetatieobject_punt"
OVL_URL = "https://data.utrecht.nl/sites/default/files/open-data/20211125paaldump.csv"
OVL_PAGE = "https://data.overheid.nl/dataset/utrecht-openbare-verlichting"
OVERPASS = "https://overpass-api.de/api/interpreter"
FLIGHT_UTC = "2023-04-05T23:51:00Z"  # AHN strip of the crop (data/README.md)
LICENCE_API = "https://api.pdok.nl/lv/bgt/ogc/v1?f=json"
LICENCE_NGR = ("https://www.nationaalgeoregister.nl/geonetwork/srv/api/records/"
               "2cb4769c-b56e-48fa-8685-c48f61b9a319/formatters/xml")

R_POLE, ABOVE, R_GROUND, VOXEL, MIN_POINTS = 0.6, 1.5, 3.0, 0.5, 6


def fetch(url: str, *, offline: bool, data: bytes | None = None) -> bytes:
    """GET (or POST `data`) with a file cache keyed by the request; --offline reads the cache only."""
    key = hashlib.sha256(url.encode() + (data or b"")).hexdigest()[:20]
    path = CACHE / key
    if path.exists():
        return path.read_bytes()
    if offline:
        raise SystemExit(f"--offline: not cached: {url}")
    req = urllib.request.Request(url, data=data, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as r:
        body = r.read()
    CACHE.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    return body


def bgt_items(collection: str, *, offline: bool, crs: str | None = RD) -> tuple[list[dict], list[str]]:
    """All features of a collection whose geometry intersects the box, following `next` links."""
    q = {"bbox": ",".join(map(str, F.CROP_BBOX_RD)), "bbox-crs": RD, "limit": 1000, "f": "json"}
    if crs:
        q["crs"] = crs
    url = f"{BGT}/collections/{collection}/items?" + urllib.parse.urlencode(q, safe=",:/")
    feats, urls = [], []
    while url:
        urls.append(url)
        page = json.loads(fetch(url, offline=offline))
        feats += page.get("features", [])
        url = next((l["href"] for l in page.get("links", []) if l.get("rel") == "next"), None)
    return feats, urls


def xy(geom: dict) -> tuple[float, float]:
    """Point coordinates, or the vertex mean of a line / polygon (good enough for small objects)."""
    flat = np.asarray(list(_points(geom["coordinates"])), dtype=float)
    return float(flat[:, 0].mean()), float(flat[:, 1].mean())


def _points(c):
    if isinstance(c[0], (int, float)):
        yield c[:2]
    else:
        for s in c:
            yield from _points(s)


def in_box(x: float, y: float) -> bool:
    x0, y0, x1, y1 = F.CROP_BBOX_RD
    return x0 <= x < x1 and y0 <= y < y1  # half-open, as the crop


def current(feats: list[dict]) -> list[dict]:
    """Current versions only (no eind_registratie, no termination_date), strictly inside the box."""
    out = []
    for f in feats:
        p = f["properties"]
        if p.get("eind_registratie") is None and p.get("termination_date") is None:
            x, y = xy(f["geometry"])
            if in_box(x, y):
                out.append({"x_rd": round(x, 2), "y_rd": round(y, 2), "type": p.get("plus_type") or p.get("type"),
                            "bgt_type": p.get("type"), "lokaal_id": p["lokaal_id"], "status": p.get("status"),
                            "_created": p.get("creation_date")})
    return out


def first_created(feats: list[dict]) -> dict[str, str]:
    """Earliest creation_date over all versions of each object (to compare with the AHN flight date)."""
    first: dict[str, str] = {}
    for f in feats:
        p = f["properties"]
        first[p["lokaal_id"]] = min(first.get(p["lokaal_id"], "9999"), p.get("creation_date") or "9999")
    return first


def bgt(offline: bool) -> dict:
    out, urls = {}, []
    for c in [POLES, *FURNITURE, *GROUND_LEVEL, TREES]:
        feats, u = bgt_items(c, offline=offline)
        urls += u
        cur = current(feats)
        first = first_created(feats)
        for o in cur:
            o["collection"] = c
            o["first_created"] = first[o["lokaal_id"]]
            o.pop("_created")
        out[c] = {"n": len(cur), "by_type": dict(Counter(o["type"] for o in cur).most_common()),
                  "n_versions_returned": len(feats),
                  "n_first_registered_after_flight": sum(o["first_created"] > FLIGHT_UTC for o in cur),
                  "items": cur}
    return {"collections": out, "urls": urls}


def rd_to_wgs84_affine(offline: bool) -> np.ndarray:
    """A local affine RD -> lon/lat fitted on the BGT poles PDOK returns in both CRSs (exact to cm over 200 m)."""
    rd, _ = bgt_items(POLES, offline=offline)
    ll, _ = bgt_items(POLES, offline=offline, crs=None)  # default CRS84
    a = {(f["properties"]["lokaal_id"], f["properties"]["version"]): f["geometry"]["coordinates"] for f in rd}
    b = {(f["properties"]["lokaal_id"], f["properties"]["version"]): f["geometry"]["coordinates"] for f in ll}
    keys = sorted(a.keys() & b.keys())
    A = np.array([[a[k][0], a[k][1], 1.0] for k in keys])
    B = np.array([b[k][:2] for k in keys])
    M, *_ = np.linalg.lstsq(A, B, rcond=None)  # lonlat = [x, y, 1] @ M
    return M


def wgs84_to_rd(lon: np.ndarray, lat: np.ndarray, M: np.ndarray) -> np.ndarray:
    lin, t = M[:2], M[2]
    return (np.column_stack([lon, lat]) - t) @ np.linalg.inv(lin)


def ovl(offline: bool) -> dict:
    """Gemeente Utrecht street-light export (CSV, ';', RD x/y), filtered to the box."""
    text = fetch(OVL_URL, offline=offline).decode("utf-8-sig")
    rows = []
    for r in csv.DictReader(io.StringIO(text), delimiter=";"):
        try:
            x, y = float(r["x"].replace(",", ".")), float(r["y"].replace(",", "."))
        except (KeyError, ValueError):
            continue
        if in_box(x, y):
            rows.append({"x_rd": x, "y_rd": y, "type": r.get("Paal type"), "street": r.get("Straat"),
                         "placed": r.get("Plaatsingsdatum"), "collection": "ovl_utrecht"})
    export = {r.get("exportdate") for r in csv.DictReader(io.StringIO(text), delimiter=";")} - {None, ""}
    return {"name": "Gemeente Utrecht, openbare verlichting (OVL) paaldump", "url": OVL_URL, "page": OVL_PAGE,
            "licence": "CC0 1.0 (per data.overheid.nl dataset page)", "export_date": sorted(export),
            "n": len(rows), "by_type": dict(Counter(r["type"] for r in rows).most_common()), "items": rows}


def osm(offline: bool, M: np.ndarray) -> dict:
    """OpenStreetMap nodes with street-furniture tags around the box (Overpass), converted to RD, filtered."""
    corners = np.array([[x, y, 1.0] for x in F.CROP_BBOX_RD[::2] for y in F.CROP_BBOX_RD[1::2]]) @ M
    s, w = corners[:, 1].min() - 0.0005, corners[:, 0].min() - 0.0005
    n, e = corners[:, 1].max() + 0.0005, corners[:, 0].max() + 0.0005
    q = f"[out:json][timeout:60];node({s:.5f},{w:.5f},{n:.5f},{e:.5f})[~\".\"~\".\"];out body;"
    body = urllib.parse.urlencode({"data": q}).encode()
    for attempt in range(3):  # the public Overpass server answers 504 when busy
        try:
            raw = json.loads(fetch(OVERPASS, offline=offline, data=body))
            break
        except urllib.error.HTTPError:
            if attempt == 2:
                raise
            time.sleep(10)
    want = {("highway", "street_lamp"), ("amenity", "bench"), ("amenity", "waste_basket"), ("natural", "tree"),
            ("leisure", "picnic_table"), ("emergency", "fire_hydrant"), ("man_made", "street_cabinet"),
            ("highway", "traffic_signals"), ("man_made", "mast"), ("amenity", "bicycle_parking")}
    el = [x for x in raw.get("elements", []) if "lat" in x]
    rd = wgs84_to_rd(np.array([x["lon"] for x in el]), np.array([x["lat"] for x in el]), M) if el else np.zeros((0, 2))
    items = []
    for x, (ex, ey) in zip(el, rd):
        tags = [f"{k}={v}" for k, v in x.get("tags", {}).items() if (k, v) in want]
        if tags and in_box(ex, ey):
            items.append({"x_rd": round(float(ex), 2), "y_rd": round(float(ey), 2), "type": tags[0], "osm_id": x["id"]})
    return {"name": "OpenStreetMap via Overpass API (crowd-sourced)", "licence": "ODbL 1.0", "url": OVERPASS,
            "query": q, "osm_base": raw.get("osm3s", {}).get("timestamp_osm_base"), "n": len(items),
            "by_type": dict(Counter(i["type"] for i in items).most_common()), "items": items}


def load_crop():
    las = laspy.read(DATA_CROP)
    xyz = np.column_stack([np.asarray(las.x), np.asarray(las.y), np.asarray(las.z)])
    return xyz, np.asarray(las.classification), np.asarray(las.header.mins, dtype=float)


def pole_evidence(poles: list[dict], xyz, cls, mins, point_label, label_names) -> None:
    """Per pole: local ground, AHN points > 1.5 m above it within 0.6 m, occupied 0.5 m voxels, pipeline labels."""
    tree = cKDTree(xyz[:, :2])
    gmask = cls == 2
    gtree, gz = cKDTree(xyz[gmask, :2]), xyz[gmask, 2]
    vox = np.floor((xyz - mins) / VOXEL).astype(np.int64)
    for p in poles:
        c = (p["x_rd"], p["y_rd"])
        g = gtree.query_ball_point(c, R_GROUND)
        ground = float(np.median(gz[g])) if g else float("nan")
        idx = np.asarray(tree.query_ball_point(c, R_POLE), dtype=np.int64)
        up = idx[xyz[idx, 2] > ground + ABOVE] if idx.size else idx
        p["ground_z"] = round(ground, 2)
        p["ground_points_3m"] = len(g)
        p["points_within_0_6m"] = int(idx.size)
        p["points_above_1_5m"] = int(up.size)
        p["voxels_above_1_5m"] = int(len(np.unique(vox[up], axis=0))) if up.size else 0
        p["top_above_ground_m"] = round(float(xyz[up, 2].max() - ground), 2) if up.size else None
        p["ahn_classes_above"] = {str(k): int(v) for k, v in zip(*np.unique(cls[up], return_counts=True))}
        if point_label is not None:
            p["pipeline_labels_above"] = {label_names.get(int(k), str(int(k))): int(v)
                                          for k, v in zip(*np.unique(point_label[up], return_counts=True))}


def histogram(poles: list[dict]) -> dict:
    n = np.array([p["points_above_1_5m"] for p in poles])
    return {"0": int((n == 0).sum()), "1-5": int(((n >= 1) & (n <= 5)).sum()),
            "6-20": int(((n >= 6) & (n <= 20)).sum()), ">20": int((n > 20).sum())}


def nearest(objs: list[dict], ref: list[dict]) -> list[dict]:
    if not ref:
        return []
    t = cKDTree([[r["x_rd"], r["y_rd"]] for r in ref])
    out = []
    for o in objs:
        d, i = t.query([o["x_rd"], o["y_rd"]])
        out.append({"x_rd": o["x_rd"], "y_rd": o["y_rd"], "cluster": o.get("cluster"),
                    "nearest_type": ref[i]["type"], "nearest_collection": ref[i]["collection"],
                    "nearest_x_rd": ref[i]["x_rd"], "nearest_y_rd": ref[i]["y_rd"], "distance_m": round(float(d), 2)})
    return out


def pipeline_labels():
    """Per-point pipeline label from results/labels_crop.npz, if present (index into class_names)."""
    path = RESULTS / "labels_crop.npz"
    if not path.exists():
        return None, {}
    d = np.load(path, allow_pickle=False)
    return d["point_class"], {i: str(n) for i, n in enumerate(d["class_names"])}


def strip(items: list[dict]) -> list[dict]:
    return [{k: v for k, v in i.items() if not k.startswith("_")} for i in items]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--final", action="store_true", help="write results/bgt_street_furniture.json")
    ap.add_argument("--offline", action="store_true", help=f"reuse the cached downloads in {CACHE}")
    args = ap.parse_args()

    b = bgt(args.offline)
    cols = b["collections"]
    poles = cols[POLES]["items"]
    objects = [o for c in FURNITURE for o in cols[c]["items"]]
    licence_api = json.loads(fetch(LICENCE_API, offline=args.offline))
    lic = next((l for l in licence_api.get("links", []) if l.get("rel") == "license"), {})
    ngr = fetch(LICENCE_NGR, offline=args.offline).decode("utf-8", "replace")
    ngr_cc = "creativecommons.org/licenses/by/4.0" in ngr

    xyz, cls, mins = load_crop()
    point_label, names = pipeline_labels()
    pole_evidence(poles, xyz, cls, mins, point_label, names)

    second = ovl(args.offline)
    pole_evidence(second["items"], xyz, cls, mins, point_label, names)
    second["pole_points_histogram"] = histogram(second["items"])
    second["poles_with_6_voxels"] = sum(p["voxels_above_1_5m"] >= MIN_POINTS for p in second["items"])
    lamps = [p for p in poles if p["type"] == "lichtmast"]
    m = nearest(second["items"], lamps)
    second["matched_to_bgt_lichtmast_within_2m"] = sum(x["distance_m"] <= 2 for x in m)
    second["nearest_bgt_lichtmast_m"] = [x["distance_m"] for x in m]

    try:
        third = osm(args.offline, rd_to_wgs84_affine(args.offline))
    except Exception as exc:  # Overpass is a shared public service; the result must not depend on it
        third = {"name": "OpenStreetMap via Overpass API", "error": repr(exc)}

    if third.get("items"):
        osm_trees = [dict(i, collection="osm") for i in third["items"] if i["type"] == "natural=tree"]
        m = nearest(osm_trees, cols[TREES]["items"])
        third["trees_within_2m_of_bgt_tree"] = sum(x["distance_m"] <= 2 for x in m)

    pipe = json.loads((RESULTS / "pipeline.json").read_text(encoding="utf-8"))
    ours = pipe["street_furniture_objects"]
    registered = poles + objects
    out = {
        "label": "FINAL" if args.final else "PILOT", "script": "bench/bgt_street_furniture.py",
        "date_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source": {"name": "BGT (Basisregistratie Grootschalige Topografie) via PDOK OGC API Features",
                   "licence": {"api_landing_page": {"title": lic.get("title"), "href": lic.get("href"),
                                                    "checked_at": LICENCE_API},
                               "dataset_metadata_ngr": {"cc_by_4_0": ngr_cc, "checked_at": LICENCE_NGR,
                                                        "attribution": "Kadaster, Basisregistratie Grootschalige "
                                                                       "Topografie (BGT)"},
                               "note": "the API links CC0 1.0, the NGR dataset metadata says CC BY 4.0 with "
                                       "attribution; attribute 'Kadaster, BGT' to satisfy both"},
                   "urls": b["urls"]},
        "bbox_rd": list(F.CROP_BBOX_RD), "ahn_flight_utc": FLIGHT_UTC,
        "params": {"pole_radius_m": R_POLE, "above_ground_m": ABOVE, "ground_radius_m": R_GROUND,
                   "ground": "median z of AHN class-2 points within ground_radius_m", "voxel_m": VOXEL,
                   "voxel_grid": "floor((xyz - LAS header mins) / 0.5), approximates Open3D voxel_down_sample",
                   "min_points": MIN_POINTS},
        "collections": {c: {k: v for k, v in d.items() if k != "items"} for c, d in cols.items()},
        "poles": strip(poles),
        "objects": strip(objects),
        "ground_level_objects": {c: cols[c]["by_type"] for c in GROUND_LEVEL},
        "pole_points_histogram": histogram(poles),
        "poles_with_6_voxels": sum(p["voxels_above_1_5m"] >= MIN_POINTS for p in poles),
        "poles_with_6_voxels_only_ahn_class_1": sum(p["voxels_above_1_5m"] >= MIN_POINTS
                                                     and set(p["ahn_classes_above"]) == {"1"} for p in poles),
        "poles_first_registered_after_flight": sum(p["first_created"] > FLIGHT_UTC for p in poles),
        "pole_points_histogram_by_type": {t: histogram([p for p in poles if p["type"] == t])
                                          for t in sorted({p["type"] for p in poles})},
        "poles_with_6_voxels_by_type": {t: sum(p["voxels_above_1_5m"] >= MIN_POINTS for p in poles if p["type"] == t)
                                        for t in sorted({p["type"] for p in poles})},
        "our_objects_vs_bgt": nearest(ours, registered),
        "our_objects_vs_bgt_trees": nearest(ours, cols[TREES]["items"]),
        "our_objects_vs_ovl": nearest(ours, second["items"]),
        "missed_candidates": "skipped: results/ holds no coordinates for the 23 missed candidate groups",
        "second_source": second,
        "third_source": third,
        "trees": {"n": cols[TREES]["n"], "by_type": cols[TREES]["by_type"],
                  "n_first_registered_after_flight": cols[TREES]["n_first_registered_after_flight"],
                  "source": "BGT vegetatieobject_punt (current versions)",
                  "pipeline_vegetation_clusters": pipe["n_objects"]["vegetation"]},
        "notes": [
            "BGT returns all versions of an object; only versions without eind_registratie / termination_date count",
            "bbox query = geometry intersects the box; then kept strictly x0 <= x < x1, y0 <= y < y1 like the crop",
            "BGT 'type' for these objects is 'niet-bgt' (optional IMGeo plus-content kept by the municipality); "
            "plus_type is the type shown",
            "first_created after the AHN flight (2023-04-05) means the object may not have stood there when flown",
            "points above 1.5 m within 0.6 m can also be tree canopy or a roof over the pole; see ahn_classes_above "
            "(AHN class 6 = building, 26 = civil structure / kunstwerk)",
            "the OVL export is from 25 Nov 2021 and lists municipal lights only",
            "OSM is crowd-sourced; no highway=street_lamp is mapped here",
        ],
    }
    path = RESULTS / "bgt_street_furniture.json" if args.final else Path("/dev/stdout")
    write_json(path, out, final=args.final)
    summary = {k: out[k] for k in ("pole_points_histogram", "poles_with_6_voxels", "pole_points_histogram_by_type",
                                   "poles_with_6_voxels_by_type", "our_objects_vs_bgt")}
    summary["collections"] = {c: (d["n"], d["by_type"]) for c, d in out["collections"].items()}
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
