# Data licence: AHN5, CC BY 4.0

## Attribution (use this line wherever the data or anything derived from it is shown)

> Point cloud: AHN5, Actueel Hoogtebestand Nederland (ahn.nl), Het Waterschapshuis, CC BY 4.0.
> AHN file 135000_455000, cropped and processed.

Licence: Creative Commons Attribution 4.0 International (CC BY 4.0),
https://creativecommons.org/licenses/by/4.0/ (Dutch deed: https://creativecommons.org/licenses/by/4.0/deed.nl).

## Source

| | |
|---|---|
| Dataset | AHN5, Actueel Hoogtebestand Nederland |
| Licensor | Het Waterschapshuis |
| File | `AHN5_C_135000_455000.COPC.LAZ` (1 km x 1 km, RD New lower-left corner 135000, 455000) |
| URL | https://basisdata.nl/hwh-ahn/AHN5_KM/01_LAZ/AHN5_C_135000_455000.COPC.LAZ |
| Size, SHA-256 | 130 213 150 bytes, `b326b5a637656ca7052bd71f2d7385e50c922efe631577b1146aad64b045c327` |

Where the licence is stated (checked 2026-10-01 and 2026-10-02):

- the AHN tile download page, https://basisdata.nl/hwh-ahn/AUX/bladwijzer/index.html:
  "Licenties: AHN1/2/3/4, CC0 1.0; AHN5/6, Creative Commons Naamsvermelding 4.0"
- the Nationaal Georegister metadata record for AHN5, `4995e338-fec7-425e-bb86-eea3875cf114`:
  "Naamsvermelding verplicht, organisatienaam", linking to the CC BY 4.0 deed; the organisation is
  Het Waterschapshuis
- ahn.nl, 2 October 2024 (https://www.ahn.nl/heel-westelijk-nederland-gereed): from AHN5 on, users must name the
  source (AHN) on derived products.

## What was changed

1. **Cropped** to the RD New box x 135715 to 135915  y 455475 to 455675 (200 m x 200 m  the Jaarbeurs hall and its
   surroundings  Utrecht): 722 961 of the tile's 21 013 926 points  in file order.
2. **Rewritten** as a plain LAZ file (LAS 1.4, point format 6) with a fresh header, because laspy cannot write COPC.
   The tile's scales, offsets, GPS time type and WKT coordinate system record (RD New + NAP height) were kept; the
   COPC index records were dropped. No point value was changed: `data/fetch_ahn5.py --verify-against` checks all
   18 point dimensions byte for byte.
3. **Processed** for the talk: voxel downsampling, ground removal, clustering and rule-based labelling
   (`pipeline/`), renders (`renders/`) and numbers (`results/`). AHN's own classification is hidden from the
   pipeline and used only to score our labels against it.

The talk and this repository are not endorsed by Het Waterschapshuis or AHN.

The licence covers the data. The code in this repository is not covered by this file.
