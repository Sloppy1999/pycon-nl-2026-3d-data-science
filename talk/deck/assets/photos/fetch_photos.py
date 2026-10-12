"""Fetch the two street photos of slide 18 from Wikimedia Commons (licence and author read from the API).

    uv run --with pillow python deck/assets/photos/fetch_photos.py

Writes street_day.jpg, street_night.jpg (1600 px wide) and photos.json (author, licence, URL), which build_deck.py
reads for the credit line. Both photos show Jaarbeursplein, Utrecht, a few metres from the 200 m crop box.
"""
import io
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
PHOTOS = {
    "street_day": "Utrecht 15 59 39 986000.jpeg",
    "street_night": "Jaarbeursplein en Beatrixtheater Utrecht (oktober 2014).jpg",
}


def get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "talk-prep/1.0 (personal conference talk)"})
    return urllib.request.urlopen(req, timeout=60).read()


meta = {}
for key, title in PHOTOS.items():
    q = ("https://commons.wikimedia.org/w/api.php?action=query&prop=imageinfo&iiprop=url|extmetadata&iiurlwidth=1600"
         "&format=json&titles=File:" + urllib.parse.quote(title))
    info = list(json.loads(get(q))["query"]["pages"].values())[0]["imageinfo"][0]
    m = info["extmetadata"]
    Image.open(io.BytesIO(get(info["thumburl"]))).convert("RGB").save(HERE / f"{key}.jpg", quality=88)
    meta[key] = {"title": title, "author": re.sub("<[^>]+>", "", m["Artist"]["value"]).strip(),
                 "licence": m["LicenseShortName"]["value"], "licence_url": m.get("LicenseUrl", {}).get("value"),
                 "page": info["descriptionurl"], "date": m.get("DateTimeOriginal", {}).get("value", "")[:10]}
(HERE / "photos.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(json.dumps(meta, indent=2, ensure_ascii=False))
