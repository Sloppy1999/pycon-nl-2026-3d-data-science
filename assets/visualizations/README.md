# Oblique point-cloud renders

```bash
uv run python assets/visualizations/make_visuals.py            # all (about 10 s)
uv run python assets/visualizations/make_visuals.py --only hero
```

Same inputs, arrays and palette as `pipeline/render.py` (it is imported, nothing is recomputed). Only the camera
(oblique, azimuth 200°, elevation 28°), eye-dome lighting and a crop box differ. EDL darkens colours at depth
edges, so these images are for the audience, not for the pixel-exact class QA of `renders/`.

| File | Used on | Shows |
|---|---|---|
| `hero_trim.png` | slides 1 and 6 | all 722 961 raw points, height ramp |
| `split_raw.png`, `split_labels.png` | slide 19 | raw / painted-back labels, one camera, one crop box |
| `anchors.json` | slide 6 arrow | `pipeline/render.py jaarbeurs_hall` projected with this camera |
| `spec.json` | | cameras, crop boxes, input and output sha256 |
