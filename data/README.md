# Data

The running example of the talk is the Jaarbeurs hall in Utrecht and its surroundings, cut from the Dutch national elevation point cloud AHN5.

> Point cloud: AHN5, Actueel Hoogtebestand Nederland (ahn.nl), Het Waterschapshuis, CC BY 4.0.
> AHN file 135000_455000, cropped and processed.

Licence, sources and the list of changes: [DATA_LICENSE.md](DATA_LICENSE.md).

## Files

| File | What | Points | Size | SHA-256 |
|---|---|---|---|---|
| `utrecht_jaarbeurs_200m.laz` | the crop every slide uses (in the repo): the Jaarbeurs hall and its surroundings | 722 961 | 4 336 320 B | `b8dfa077c4c1d5aa471c476af56beda6ced6e53a454f5af35b44cda1896916da` |
| `previous/street_graadt_van_roggenweg_200m.laz` | the first example street (until 2026-10-11)  kept for the ground-plane comparison in `pipeline/run.py`; not used by the deck | 1 239 310 | 7 797 485 B | `b921862176ae30d0f5926dfbd253a081f7e46dd94f585e4a5ac49b320232674d` |
| `utrecht_jaarbeurs_building.laz` | the Jaarbeurs hall building itself (BAG pand 0344100000077882, built 1970) plus a 25 m margin, RD 135722 to 135931 / 455487 to 455679; added 2026-10-11, NOT used by the deck yet | 717 180 | 4 253 167 B | `1d5cf0fd6c008a8ba106babdbf95915cbd1e9b87c1dc5e599bfcc84d17a51575` |
| `AHN5_C_135000_455000.COPC.LAZ` | the 1 km AHN5 tile it comes from (not in the repo, see `.gitignore`) | 21 013 926 | 130 213 150 B | `b326b5a637656ca7052bd71f2d7385e50c922efe631577b1146aad64b045c327` |
| `fetch_ahn5.py` | downloads the tile and writes the crop | | | |

## Get the data

```bash
uv run python data/fetch_ahn5.py --head   # check the official URL only (HEAD request, nothing downloaded)
uv run python data/fetch_ahn5.py          # download the tile (about 130 MB, checksum checked), write the crop if missing
uv run python data/fetch_ahn5.py --building   # write the Jaarbeurs building crop (data/utrecht_jaarbeurs_building.laz)
uv run python data/fetch_ahn5.py --crop-to /tmp/crop.laz --verify-against data/utrecht_jaarbeurs_200m.laz
```

The last command rebuilds the crop from the tile and compares it with the shipped file point for point (all 18
dimensions, byte for byte). Only the header's creation date can differ.

## The crop

- RD New (EPSG:28992) box x 135715 to 135915, y 455475 to 455675 (200 m x 200 m), around the Jaarbeurs hall
  (BAG pand 0344100000077882, Jaarbeursplein 6, built 1970, footprint box x 135747.7 to 135905.8, y 455512.5 to
  455654.0), heights in m NAP; the WKT
  coordinate system record is in the file.
- LAS 1.4, point format 6: x, y, z, intensity, return number, number of returns, classification, scan angle,
  GPS time and flags. **No colour.**
- AHN classes in the crop: 1 (other: vegetation, facades, cars, street furniture) 109 363 points, 2 (ground)
  262 712, 6 (buildings) 338 943, 26 (civil structure, the viaduct) 11 943.
- Flown at night, leaf-off, one strip: GPS time about 23:51 UTC on 5 April 2023 (01:51 CEST on 6 April). AHN delivers the points already classified; the
  pipeline hides those classes and only uses them to score its own labels.

## Gotchas met while cutting the crop

- The tile is COPC. Writing a crop with the tile's header raises
  `NotImplementedError: Writing COPC is not supported`, so `fetch_ahn5.py` builds a fresh LAS 1.4 header and copies
  only the WKT coordinate system record.
- A fresh laspy header resets the global-encoding GPS time type. AHN stores adjusted standard GPS time, so
  `fetch_ahn5.py` copies that bit too; without it the crop differed from the shipped file in that header bit.
- `o3d.io.read_point_cloud("crop.laz")` returns 0 points and only a warning: Open3D does not read LAS/LAZ. Load with
  laspy and hand the NumPy array to Open3D (`pipeline/steps.py`, `load` and `to_open3d`).
