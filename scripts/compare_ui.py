#!/usr/bin/env python3
"""Build element-by-element sheets: our screenshot beside source-game references.

usage: compare_ui.py SPEC.json OURS_DIR OUT_DIR
SPEC: [{"element": str, "ours": "name", "ours_crop": [x0,y0,x1,y1] (fractions),
        "refs": [["game/file", [x0,y0,x1,y1]|null], ...]}]
References live in experiments/2026-11-08-ui-hud/references/<game>/ (local, gitignored).
"""
import json
import sys
from pathlib import Path
from PIL import Image, ImageDraw

REF = Path(__file__).resolve().parent.parent / "experiments/2026-11-08-ui-hud/references"


def load(path, crop):
    im = Image.open(path).convert("RGB")
    if crop:
        w, h = im.size
        im = im.crop((int(crop[0] * w), int(crop[1] * h), int(crop[2] * w), int(crop[3] * h)))
    return im


def fit(im, width, height):
    s = min(width / im.width, height / im.height)
    return im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.LANCZOS)


def main():
    spec = json.load(open(sys.argv[1]))
    ours_dir, out = Path(sys.argv[2]), Path(sys.argv[3])
    out.mkdir(parents=True, exist_ok=True)
    for item in spec:
        ours = load(ours_dir / f"{item['ours']}.png", item.get("ours_crop"))
        refs = []
        for rel, crop in item["refs"]:
            game, name = rel.split("/", 1)
            path = REF / game / name
            if path.exists():
                refs.append((rel, load(path, crop)))
        col = 380
        cols = min(3, max(1, len(refs)))
        rows = (len(refs) + cols - 1) // cols
        ours_f = fit(ours, 1180, 520)
        cell_h = 230
        width = max(ours_f.width + 20, cols * (col + 10) + 10)
        height = 50 + ours_f.height + 40 + rows * (cell_h + 26) + 10
        sheet = Image.new("RGB", (width, height), (16, 18, 20))
        d = ImageDraw.Draw(sheet)
        d.text((10, 8), f"ELEMENT: {item['element']}", fill=(255, 190, 90))
        d.text((10, 26), f"OURS ({item['ours']})", fill=(120, 220, 230))
        sheet.paste(ours_f, (10, 44))
        y = 44 + ours_f.height + 10
        d.text((10, y), "SOURCE GAMES", fill=(120, 220, 230))
        y += 22
        for i, (rel, im) in enumerate(refs):
            f = fit(im, col, cell_h)
            x = 10 + (i % cols) * (col + 10)
            yy = y + (i // cols) * (cell_h + 26)
            sheet.paste(f, (x, yy))
            d.text((x, yy + f.height + 4), rel[:58], fill=(190, 190, 190))
        sheet.save(out / f"{item['element'].split(' ')[0].lower()}-{item['ours']}.jpg", quality=88)
        print("wrote", item["element"])


if __name__ == "__main__":
    main()
