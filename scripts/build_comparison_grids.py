#!/usr/bin/env python3
"""Build labelled side-by-side grids (reference left, Racer right) from a pairs file.

Usage: build_comparison_grids.py PAIRS.json OUT_DIR [--per-sheet N]
PAIRS.json is a list of {"group": str, "ref": path, "ref_label": str, "racer": path, "racer_label": str}.
Pairs are grouped by "group"; each group yields sheets of up to N pairs (default 6, two columns).
Images are only letterboxed and uniformly scaled; nothing is composited into the frames themselves.
"""
import argparse
import json
from pathlib import Path
from PIL import Image, ImageDraw

CELL_W, CELL_H = 480, 270


def fit(path):
    im = Image.open(path).convert("RGB")
    scale = min(CELL_W / im.width, CELL_H / im.height)
    im = im.resize((max(1, round(im.width * scale)), max(1, round(im.height * scale))), Image.LANCZOS)
    cell = Image.new("RGB", (CELL_W, CELL_H), (10, 12, 16))
    cell.paste(im, ((CELL_W - im.width) // 2, (CELL_H - im.height) // 2))
    return cell


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pairs", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--per-sheet", type=int, default=6)
    args = ap.parse_args()
    pairs = json.loads(args.pairs.read_text())
    args.out.mkdir(parents=True, exist_ok=True)
    groups = {}
    for p in pairs:
        groups.setdefault(p["group"], []).append(p)
    written = []
    for group, items in sorted(groups.items()):
        for sheet_index in range(0, len(items), args.per_sheet):
            chunk = items[sheet_index:sheet_index + args.per_sheet]
            cols = 2
            rows = (len(chunk) + cols - 1) // cols
            pair_w = CELL_W * 2 + 6
            sheet = Image.new("RGB", (cols * pair_w + (cols - 1) * 10, rows * (CELL_H + 20)), (16, 20, 26))
            draw = ImageDraw.Draw(sheet)
            for i, p in enumerate(chunk):
                x = (i % cols) * (pair_w + 10)
                y = (i // cols) * (CELL_H + 20)
                sheet.paste(fit(p["ref"]), (x, y + 18))
                sheet.paste(fit(p["racer"]), (x + CELL_W + 6, y + 18))
                draw.text((x + 3, y + 3), p["ref_label"][:68], fill=(225, 225, 225))
                draw.text((x + CELL_W + 9, y + 3), p["racer_label"][:68], fill=(150, 215, 255))
            name = f"{group}-{sheet_index // args.per_sheet + 1:02d}.jpg"
            sheet.save(args.out / name, quality=88, optimize=True)
            written.append(name)
    print(len(written), "sheets:", ", ".join(written[:6]), "..." if len(written) > 6 else "")


main()
