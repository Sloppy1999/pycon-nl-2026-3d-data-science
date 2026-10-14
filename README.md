# 3D Data Science with Python (PyCon NL 2026)

Everything behind the 30-minute talk "3D Data Science with Python" by Sergio Peral at PyCon NL 2026 (15 October,
Jaarbeurs Utrecht): the Jaarbeurs hall in Utrecht and its surroundings, scanned from the air for AHN, turned into
labelled objects (ground, buildings, vegetation, street furniture) entirely in Python, plus the benchmarks behind the
performance and memory slides and the generator of the slide deck.

![The pipeline on the Jaarbeurs crop: load, ground removal, clusters, labels](docs/img/pipeline.png)

*One 200 m AHN5 crop around the Jaarbeurs hall in Utrecht (722 961 points), seen from above: the raw points,
the ground found by tiled RANSAC, DBSCAN clusters, and the final labels. Rebuild the picture with
`uv run python docs/img/make_readme_banner.py`.*

Results from the verified macOS rerun: 722 961 points in, 232 180 after 0.5 m voxel downsampling.
Ground agreement with withheld AHN class 2: precision 0.9841, recall 0.9437. Building agreement with
AHN class 6: precision 0.8220, recall 0.9886. These are reference-label comparisons on one crop,
not independent field validation. The rules find 58 roof clusters, 681 vegetation clusters and
3 street-furniture candidates. Runtime was 1.0 s from loading to paint-back in one indicative run;
rendering is excluded. Cluster IDs and fitted planes can differ across platforms.

The presentation retains the original documented Linux performance experiments. Additional macOS
runs, before/after pipeline metrics and remaining limitations are in [the validation report](docs/IMPROVEMENTS.md)
and `results/review/`. No benchmark numbers were fabricated or substituted between environments.

## Reproduce

Run from the repository root:

```bash
uv sync --group qa --group test
uv run python pipeline/run.py          # crop included; evaluation, sweep and fresh-process determinism check
uv run python pipeline/render.py       # real labels, stored camera; needs an OpenGL context
uv run python snippets/run_all.py
uv run python deck/build_deck.py
uv run python deck/qa/setup_fonts.py
uv run --group qa python deck/qa/render.py
uv run python deck/qa/checks.py
uv run --group test pytest tests -q
```

The PDF has 29 visible slides; the PPTX also contains hidden backup slides. LibreOffice is required
for PDF export; PyMuPDF substitutes for Poppler on systems without it. Fira fonts are downloaded by
`setup_fonts.py`. The builder can clone the included master without external skill scripts; its native
package checks do not replace full Office schema validation.

On an idle machine, reproduce the performance measurements with:

```bash
uv run python bench/bench_cliff.py --final
uv run --group profile python bench/profile_loop_scalene.py --final
uv run python bench/bench_freethreaded.py --final --ft FT_VENV/bin/python --gil GIL_VENV/bin/python
```

See the free-threaded script's docstring for matched interpreter environments. Both must have the same
Python release and NumPy version. For an additional full-crop check without replacing published results:
`uv run python bench/bench_cliff.py --smoke --n 722961 --runs 7 --out /tmp/cliff.json`.

Memory measurements require Linux `/proc`, the downloaded 1 km tile and an idle machine:

```bash
uv run python data/fetch_ahn5.py
uv run python bench/bench_memory.py --final
```

Memory values are GiB (2³⁰ bytes). The 74.2 GiB value extrapolates retained load/voxel memory to a
926-million-point file; the file was never processed. The 0.8 GiB chunked peak was measured on the
21-million-point 1 km tile. Chunking keeps first points per voxel, rather than Open3D centroids, and
retains its output in memory. Full dependency/build details: [HOW_TO_UPDATE](docs/HOW_TO_UPDATE.md).

## License

MIT

The code in this repository is licensed under [MIT](LICENSE). Third-party material retains its own license and
copyright notices:

- The AHN5 point cloud in `data/`, and anything derived from it, is licensed under
  [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) by Het Waterschapshuis. What was changed and where the
  licence is stated: [data/DATA_LICENSE.md](data/DATA_LICENSE.md).
- The logos in `deck/assets/logos/` belong to their owners (see its `SOURCES.md`) and are not covered by MIT.

Wherever the data or anything derived from it is shown, attribute it:

> Point cloud: AHN5, Actueel Hoogtebestand Nederland (ahn.nl), Het Waterschapshuis, CC BY 4.0.
> AHN file 135000_455000, cropped and processed.

This project is not endorsed by Het Waterschapshuis or AHN. The MIT licence does not amend the third-party licences.
