# 3D Data Science with Python (PyCon NL 2026)

Everything behind the 30-minute talk "3D Data Science with Python" by Sergio Peral at PyCon NL 2026 (15 October,
Jaarbeurs Utrecht): the Jaarbeurs hall in Utrecht and its surroundings, scanned from the air for AHN, turned into
labelled objects (ground, buildings, vegetation, street furniture) entirely in Python, plus the benchmarks behind the
performance and memory slides and the generator of the slide deck.

![The pipeline on the Jaarbeurs crop: load, ground removal, clusters, labels](docs/img/pipeline.png)

*One 200 m AHN5 crop around the Jaarbeurs hall in Utrecht (722 961 points), seen from above: the raw points,
the ground found by tiled RANSAC, DBSCAN clusters, and the final labels. Rebuild the picture with
`uv run python docs/img/make_readme_banner.py`.*

| | |
|---|---|
| Points in, after 0.5 m voxel downsampling | 722 961, 232 180 |
| Ground vs AHN class 2 | precision 0.98, recall 0.94 |
| Buildings vs AHN class 6 | precision 0.83 (a lower bound, AHN files many facade points elsewhere), recall 0.99 |
| Objects found | 58 building roofs, 683 vegetation clusters, 3 street furniture |
| Whole pipeline, load to paint-back | 0.6 s on one laptop |

## License

| Part | License |
|---|---|
| Code (`pipeline/`, `snippets/`, `bench/`, `deck/`, `tests/`) | [MIT](LICENSE) |
| Point cloud (`data/`) and anything derived from it | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), AHN5 from Het Waterschapshuis |
| Logos in `deck/assets/logos/` | Belong to their owners (see its `SOURCES.md`), not covered by MIT |

Wherever the data or anything derived from it is shown, attribute it:

> Point cloud: AHN5, Actueel Hoogtebestand Nederland (ahn.nl), Het Waterschapshuis, CC BY 4.0.
> AHN file 135000_455000, cropped and processed.

What was changed and where the licence is stated: [data/DATA_LICENSE.md](data/DATA_LICENSE.md). This project is not
endorsed by Het Waterschapshuis or AHN.

## Citation

If you use this code or the talk material, please cite it (GitHub's "Cite this repository" reads
[CITATION.cff](CITATION.cff)):

```bibtex
@misc{peral2026_3d_data_science,
  author       = {Peral, Sergio},
  title        = {3D Data Science with Python},
  year         = {2026},
  howpublished = {Talk at PyCon NL 2026, Jaarbeurs Utrecht, 15 October},
  url          = {https://github.com/Sloppy1999/pycon-nl-2026-3d-data-science}
}
```
