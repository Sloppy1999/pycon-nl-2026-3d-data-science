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
| `hero_trim.png` | slides 1 and 5 | all 722 961 raw points, height ramp |
| `hero_jaarbeurs.png` | not used | the same, full 16:9 (for a full-bleed slide) |
| `split_raw.png`, `split_labels.png` | slide 18 | raw / painted-back labels, one camera, one crop box |
| `seq1..6_*.png` | not used (backup) | the six pipeline stages; slide 11 keeps the top-down filmstrip, whose first frame Morphs into slides 12 to 17 |
| `anchors.json` | slide 5 arrow | `pipeline/render.py jaarbeurs_hall` projected with this camera |
| `spec.json` | | cameras, crop boxes, input and output sha256 |
