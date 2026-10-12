# 3D Data Science with Python (PyCon NL 2026)

Everything behind the 30-minute talk "3D Data Science with Python" by Sergio Peral at PyCon NL 2026 (15 October,
Jaarbeurs Utrecht): the Jaarbeurs hall in Utrecht and its surroundings, scanned from the air for AHN, turned into labelled objects (ground,
buildings, vegetation, street furniture) entirely in Python, plus the benchmarks behind the performance and memory
slides and the generator of the slide deck.

## What is here

| Folder | What |
|---|---|
| `data/` | the 200 m AHN5 crop the talk uses (`utrecht_jaarbeurs_200m.laz`  722 961 points), `fetch_ahn5.py` to download the 1 km AHN file and rebuild the crop, the data licence |
| `pipeline/` | the six-step pipeline (`steps.py`, `run.py`: load, voxel downsampling, ground removal, clustering, labelling, paint-back) and every render (`render.py`, one fixed camera) |
| `snippets/` | the code shown on the slides, each a runnable file that checks itself; `run_all.py` runs them all |
| `bench/` | the performance-cliff benchmark (`bench_cliff.py`) and the memory benchmark (`bench_memory.py`) |
| `results/` | the numbers: `pipeline.json`, `bench_cliff.json`, `memory.json` (all FINAL), `snippets.json`, `research_facts.json` (research numbers, PILOT) |
| `renders/` | the point-cloud images, label anchors and the render spec |
| `deck/` | the deck generator (`build_deck.py`, `lib/`), its inputs (`content.yaml`, `notes.yaml`, `appendix.yaml`), QA (`qa/`) and the built deck (`out/`) |
| `docs/` | QA notes, open items, timing, how to update, and the research files the notes cite (`docs/research/`) |
| `deck/ecosystem/` | the checked catalogue of the Python 3D ecosystem behind slide 3 and `docs/ECOSYSTEM.md` (`merge.py` builds both; logos in `deck/assets/logos/`) |
| `storyboard.md`, `CONTRACTS.md` | the approved storyboard and the interfaces between the parts |

## Run it

```bash
uv sync
uv run python data/fetch_ahn5.py        # only needed for the 1 km file (memory benchmark); the crop is included
uv run python pipeline/run.py           # results/pipeline.json
uv run python pipeline/render.py        # renders/
uv run python snippets/run_all.py       # every slide snippet
uv run python deck/build_deck.py        # the deck, from deck/template/pycon_nl_2026_master.pptx
```

The full order, including the benchmarks (idle machine only) and the QA render, is in
[docs/HOW_TO_UPDATE.md](docs/HOW_TO_UPDATE.md). Python 3.13, NumPy, SciPy, laspy (with lazrs), Open3D and PyVista;
versions in `uv.lock`.

## Status

The deck builds and passes its checks (`deck/qa/checks.py`: no failures), but it still has speaker placeholders: repo
URL and QR code, contact details, the PyCon NL logo and the gotchas on slide 22. See
[docs/OPEN_ITEMS.md](docs/OPEN_ITEMS.md), [docs/QA_NOTES.md](docs/QA_NOTES.md) and [docs/TIMING.md](docs/TIMING.md).

## Data licence

The point cloud is AHN5 (Actueel Hoogtebestand Nederland, ahn.nl) from Het Waterschapshuis, licensed under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Attribution, wherever the data or anything derived from it is
shown:

> Point cloud: AHN5, Actueel Hoogtebestand Nederland (ahn.nl), Het Waterschapshuis, CC BY 4.0.
> AHN file 135000_455000, cropped and processed.

What was changed and where the licence is stated: [data/DATA_LICENSE.md](data/DATA_LICENSE.md). This project is not
endorsed by Het Waterschapshuis or AHN. The data licence does not cover the code: the code is MIT-licensed, see [LICENSE](LICENSE).

## The slide design

A personal talk in the PyCon NL 2026 style: the conference's palette (navy, blue, sage and neutrals) and fonts
(Fira Sans, Fira Mono for code). The deck builds from `deck/template/pycon_nl_2026_master.pptx`, which
`deck/template/make_master.py` generates; sources, palette, contrast and rules are in
[docs/DESIGN.md](docs/DESIGN.md). Fira Sans and Fira Mono must be installed on the presenting laptop, or embedded with
PowerPoint's "Embed fonts in the file" before the deck travels. The PyCon NL logo is a labelled placeholder until the
file and the organisers' permission exist.

## Before you publish

- Still open: the repo URL and QR code, contact details and the PyCon NL logo (see docs/OPEN_ITEMS.md).
- Git-ignored on purpose: the 1 km AHN file (`data/fetch_ahn5.py` fetches it), the downloaded QA fonts
  (`deck/qa/fonts/`), the QA renders (`deck/out/png/`) and the generated QA reports (`deck/out/*.json`,
  `deck/out/qa_all.pdf`).

## Tests

```bash
uv run --with pytest pytest tests    # synthetic checks of pipeline/steps.py
```
