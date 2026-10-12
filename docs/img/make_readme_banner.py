"""Build docs/img/pipeline.png (the README banner) from the renders in renders/.

    uv run python docs/img/make_readme_banner.py
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
FONT = next(iter((ROOT / "deck/qa/fonts").glob("FiraSans-Medium.ttf")), None)
PANELS = [("1  Load", "f1_load.png"), ("2  Ground removal", "f3_ground.png"),
          ("3  Clusters", "f4_clusters.png"), ("4  Labels", "f6_final.png")]
LEGEND = [("Ground", "#4A5F69"), ("Buildings", "#6FA0CC"), ("Vegetation", "#B1CAC5"), ("Street furniture", "#FFFFFF")]
BG, W, GAP, TITLE_H, FOOT_H = "#1C325B", 600, 12, 56, 64

font = ImageFont.truetype(str(FONT), 26) if FONT else ImageFont.load_default(26)
small = ImageFont.truetype(str(FONT), 22) if FONT else ImageFont.load_default(22)
tiles = []
for _, name in PANELS:
    im = Image.open(ROOT / "renders" / name).convert("RGB")
    tiles.append(im.resize((W, round(im.height * W / im.width)), Image.LANCZOS))
H = tiles[0].height
canvas = Image.new("RGB", (len(tiles) * W + (len(tiles) - 1) * GAP, TITLE_H + H + FOOT_H), BG)
d = ImageDraw.Draw(canvas)
for i, ((title, _), im) in enumerate(zip(PANELS, tiles)):
    x = i * (W + GAP)
    canvas.paste(im, (x, TITLE_H))
    d.text((x + 12, 14), title, fill="white", font=font)
x = 12
for label, colour in LEGEND:
    d.rectangle((x, TITLE_H + H + 20, x + 22, TITLE_H + H + 42), fill=colour)
    d.text((x + 32, TITLE_H + H + 16), label, fill="white", font=small)
    x += 32 + int(d.textlength(label, font=small)) + 40
canvas.quantize(256, dither=Image.Dither.NONE).save(ROOT / "docs/img/pipeline.png", optimize=True)
print(canvas.size)
