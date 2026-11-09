#!/usr/bin/env python3
"""Build a labelled contact sheet from an explicit list of image paths.

usage: contact.py OUT.png COLS TILE LABEL_PREFIX file1.png file2.png ...
Each tile is scaled to fit TILE px, centred on a mid-grey checker, labelled with
the file's basename (wrapped) underneath. Read-only over the inputs.
"""
import sys
from PIL import Image, ImageDraw, ImageFont

out, cols, tile = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
paths = sys.argv[4:]
font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", max(9, tile // 9))
rows = (len(paths) + cols - 1) // cols
label_h = max(22, tile // 4)
sheet = Image.new("RGB", (cols * tile, rows * (tile + label_h)), (40, 42, 46))
draw = ImageDraw.Draw(sheet)
for i, p in enumerate(paths):
    x, y = (i % cols) * tile, (i // cols) * (tile + label_h)
    try:
        im = Image.open(p).convert("RGBA")
    except Exception as exc:  # unreadable inputs stay visible instead of crashing the sheet
        draw.text((x + 4, y + 4), f"ERR {exc}", fill=(255, 80, 80), font=font)
        continue
    im.thumbnail((tile - 8, tile - 8))
    bg = Image.new("RGBA", im.size, (18, 19, 21, 255))
    bg.alpha_composite(im)
    sheet.paste(bg.convert("RGB"), (x + (tile - im.width) // 2, y + (tile - im.height) // 2))
    name = p.rsplit("/", 1)[-1]
    for j, line in enumerate([name[:34], name[34:68]] if len(name) > 34 else [name]):
        draw.text((x + 3, y + tile + 2 + j * 12), line, fill=(220, 220, 220), font=font)
sheet.save(out)
print(out, sheet.size)
