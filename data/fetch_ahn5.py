"""Download the AHN5 tile and cut the 200 m crop the talk uses.

    uv run python data/fetch_ahn5.py              # download the tile if missing, write the crop if missing
    uv run python data/fetch_ahn5.py --head       # only check the official URL (HEAD request, nothing downloaded)
    uv run python data/fetch_ahn5.py --crop-to OUT.laz --verify-against data/utrecht_jaarbeurs_200m.laz

Source: AHN5 (Actueel Hoogtebestand Nederland), Het Waterschapshuis, licence CC BY 4.0
(https://creativecommons.org/licenses/by/4.0/). Tile 135000_455000 (RD New lower-left corner, 1 km x 1 km),
served as COPC by https://basisdata.nl/hwh-ahn/, which answers with a 307 redirect to an object store. No
registration is needed. See data/DATA_LICENSE.md for the attribution and what was changed.

The crop: every point with x0 <= x < x1 and y0 <= y < y1 (``CROP_BBOX_RD``), in file order, all 18 point
dimensions unchanged. Gotcha: the tile is COPC, and laspy cannot write COPC (``laspy.LasData(copc_header)``
then ``write`` raises ``NotImplementedError: Writing COPC is not supported``), so the crop gets a fresh LAS 1.4
header (point format 6, the tile's scales, offsets and GPS time type) plus a copy of the tile's WKT CRS record
(EPSG:28992 RD New + NAP height). The COPC info and hierarchy records are dropped; the result is a plain LAZ.
Only the header's creation date differs between two runs on different days.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import urllib.request
from pathlib import Path

import laspy
import numpy as np

HERE = Path(__file__).resolve().parent
TILE_NAME = "AHN5_C_135000_455000.COPC.LAZ"
TILE_URL = f"https://basisdata.nl/hwh-ahn/AHN5_KM/01_LAZ/{TILE_NAME}"
TILE_BYTES = 130_213_150
TILE_SHA256 = "b326b5a637656ca7052bd71f2d7385e50c922efe631577b1146aad64b045c327"
CROP_NAME = "utrecht_jaarbeurs_200m.laz"
# The crop: a 200 m square around the Jaarbeurs hall building (Jaarbeursplein 6, BAG pand 0344100000077882, built
# 1970, footprint bbox 135747.7, 455512.5 to 135905.8, 455654.0 from the PDOK BAG WFS, checked 2026-10-11). The whole
# hall fits with 9 to 37 m to spare; the box leans west and south, where the trees and streets are.
CROP_BBOX_RD = (135715, 455475, 135915, 455675)  # x0, y0, x1, y1 (RD New, metres)
# Until 2026-10-11 the crop was a street north-west of the halls, Graadt van Roggenweg, RD 135330, 455450 to
# 135530, 455650 (1 239 310 points; kept as data/previous/street_graadt_van_roggenweg_200m.laz, not used).
PREVIOUS_STREET_BBOX_RD = (135330, 455450, 135530, 455650)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def head(url: str = TILE_URL) -> dict:
    """HEAD request (redirects followed). Downloads nothing."""
    req = urllib.request.Request(url, method="HEAD")
    with urllib.request.urlopen(req, timeout=60) as r:
        return dict(status=r.status, final_url=r.geturl(), content_length=int(r.headers.get("Content-Length", -1)),
                    accept_ranges=r.headers.get("Accept-Ranges"), last_modified=r.headers.get("Last-Modified"))


def download(dest: Path, url: str = TILE_URL) -> Path:
    """Stream the tile to ``dest`` (about 130 MB) and check its size and SHA-256."""
    if dest.exists() and dest.stat().st_size == TILE_BYTES and sha256(dest) == TILE_SHA256:
        print(f"{dest.name}: already present, checksum OK")
        return dest
    tmp = dest.with_suffix(dest.suffix + ".part")
    with urllib.request.urlopen(url, timeout=120) as r, open(tmp, "wb") as f:
        while block := r.read(1 << 20):
            f.write(block)
    if tmp.stat().st_size != TILE_BYTES or sha256(tmp) != TILE_SHA256:
        raise RuntimeError(f"{tmp}: size or SHA-256 does not match the tile used for the talk")
    tmp.replace(dest)
    return dest


def write_crop(src: Path, dest: Path, bbox=CROP_BBOX_RD) -> int:
    """Cut ``bbox`` out of ``src`` and write it as plain LAZ with a fresh header. Returns the point count."""
    las = laspy.read(src)
    x0, y0, x1, y1 = bbox
    x, y = np.asarray(las.x), np.asarray(las.y)
    keep = (x >= x0) & (x < x1) & (y >= y0) & (y < y1)
    header = laspy.LasHeader(point_format=las.header.point_format.id, version="1.4")
    header.scales = las.header.scales
    header.offsets = las.header.offsets
    wkt = [v for v in las.header.vlrs if isinstance(v, laspy.vlrs.known.WktCoordinateSystemVlr)]
    if len(wkt) != 1:
        raise RuntimeError(f"expected one WKT CRS record in {src}, found {len(wkt)}")
    header.vlrs.append(wkt[0])
    header.global_encoding.wkt = True
    # keep the time base: AHN stores adjusted standard GPS time (global encoding bit 0); a fresh header
    # would otherwise silently switch gps_time to "GPS week time"
    header.global_encoding.gps_time_type = las.header.global_encoding.gps_time_type
    crop = laspy.LasData(header)
    crop.points = las.points[keep].copy()
    crop.update_header()
    crop.write(dest)
    return int(keep.sum())


def compare(a: Path, b: Path) -> dict:
    """Point-for-point comparison of two LAS/LAZ files: every dimension, in order, plus the header essentials."""
    la, lb = laspy.read(a), laspy.read(b)
    ha, hb = la.header, lb.header
    dims = list(la.point_format.dimension_names)
    same_dims = dims == list(lb.point_format.dimension_names)
    dim_equal = {d: bool(np.array_equal(np.asarray(la[d]), np.asarray(lb[d]))) for d in dims} if same_dims else {}
    wkt = lambda h: [v.string for v in h.vlrs if isinstance(v, laspy.vlrs.known.WktCoordinateSystemVlr)]  # noqa: E731
    out = dict(points=(len(la.points), len(lb.points)), point_format=(ha.point_format.id, hb.point_format.id),
               version=(str(ha.version), str(hb.version)),
               scales_equal=bool(np.array_equal(ha.scales, hb.scales)),
               offsets_equal=bool(np.array_equal(ha.offsets, hb.offsets)),
               mins_equal=bool(np.array_equal(ha.mins, hb.mins)), maxs_equal=bool(np.array_equal(ha.maxs, hb.maxs)),
               global_encoding=(int(ha.global_encoding.value), int(hb.global_encoding.value)),
               wkt_equal=wkt(ha) == wkt(hb) and len(wkt(ha)) == 1,
               record_bytes_equal=bool(la.points.array.tobytes() == lb.points.array.tobytes()),
               dimensions_equal=all(dim_equal.values()) and same_dims, dimensions_checked=len(dim_equal))
    out["identical_points"] = (out["points"][0] == out["points"][1] and out["record_bytes_equal"]
                               and out["dimensions_equal"] and out["scales_equal"] and out["offsets_equal"]
                               and out["wkt_equal"] and out["global_encoding"][0] == out["global_encoding"][1])
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--head", action="store_true", help="only send a HEAD request to the official URL")
    ap.add_argument("--tile", type=Path, default=HERE / TILE_NAME, help="where the tile is (or will be) stored")
    ap.add_argument("--crop-to", type=Path, default=None, help="write the crop here (default data/" + CROP_NAME + ")")
    ap.add_argument("--verify-against", type=Path, default=None, help="compare the written crop with this file")
    args = ap.parse_args()
    if args.head:
        info = head()
        print(info)
        ok = info["status"] == 200 and info["content_length"] == TILE_BYTES
        print("URL OK, size matches the talk's tile" if ok else "URL answered, but the size differs")
        return 0 if ok else 1
    download(args.tile)
    dest = args.crop_to or HERE / CROP_NAME
    if dest.exists() and args.crop_to is None:
        print(f"{dest.name}: already present (pass --crop-to to write it elsewhere)")
    else:
        n = write_crop(args.tile, dest)
        print(f"wrote {dest} ({n} points)")
    if args.verify_against:
        res = compare(dest, args.verify_against)
        print(res)
        return 0 if res["identical_points"] else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
