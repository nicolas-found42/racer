#!/usr/bin/env python3
"""Compose a labelled before/after sheet from two retained actual captures.

Usage: compose_before_after.py OUT.png "before label" before.png "after label" after.png [crop x0 y0 x1 y1]
Pixels are never altered beyond optional crop and uniform resize; the sheet is evidence, not a verdict.
"""
import sys
from PIL import Image, ImageDraw

def main():
    a = sys.argv[1:]
    if len(a) not in (5, 9):
        raise SystemExit(__doc__)
    out, bl, bp, al, ap = a[:5]
    box = tuple(int(v) for v in a[5:9]) if len(a) == 9 else None
    imgs = []
    for p in (bp, ap):
        im = Image.open(p).convert("RGB")
        if box:
            im = im.crop(box)
        imgs.append(im)
    w = 900
    imgs = [im.resize((w, round(im.height * w / im.width)), Image.LANCZOS) for im in imgs]
    h = max(im.height for im in imgs)
    sheet = Image.new("RGB", (w * 2 + 6, h + 28), (16, 20, 26))
    d = ImageDraw.Draw(sheet)
    for i, (label, im) in enumerate(zip((bl, al), imgs)):
        sheet.paste(im, (i * (w + 6), 28))
        d.text((i * (w + 6) + 8, 8), label, fill=(235, 235, 235))
    sheet.save(out)

main()
