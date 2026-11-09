#!/usr/bin/env python3
"""Contact sheet of captured UI screens: ui_sheet.py DIR OUT NAME [NAME...] (2 columns)."""
import sys
from PIL import Image
d, out, names = sys.argv[1], sys.argv[2], sys.argv[3:]
W, H = 800, 450
rows = (len(names) + 1) // 2
sheet = Image.new("RGB", (W * 2, H * rows), (20, 20, 20))
for i, n in enumerate(names):
    im = Image.open(f"{d}/{n}.png").convert("RGB").resize((W, H), Image.LANCZOS)
    sheet.paste(im, ((i % 2) * W, (i // 2) * H))
sheet.save(out)
