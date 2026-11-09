#!/usr/bin/env python3
"""Build per-element proof sheets: the Racer element beside its raw-game counterparts.

Reads elements.json (element table with captures, logical crops, preferred raw
assets and jev kinds), the jev asset judgments and the decoded-asset candidate
inventory of experiment 2026-11-08-ui-source-extracts. Writes:

  output/raw-picks/<game>/<file>.png   copies of the chosen decoded raw assets,
                                       transform applied (MC3 texture rows are
                                       stored bottom-up, so they are flipped)
  output/raw-picks.json                the full selection with sha256 of every
                                       source and copied file plus raw-member
                                       provenance
  output/sheets/E##-<slug>.png         one proof sheet per element

usage: build_elements.py [--only E01,E02] [--no-sheets]
Read-only over the extractions; all output stays inside this experiment.
"""
import hashlib
import json
import os
import re
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FONT = "/System/Library/Fonts/Supplemental/Arial.ttf"
MONO = "/System/Library/Fonts/Supplemental/Arial Narrow.ttf"
BG = (22, 24, 28)
PANEL = (31, 34, 39)
FG = (232, 234, 238)
MUTED = (150, 156, 166)
ACCENT = (86, 204, 242)
HUD = (255, 176, 32)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def font(size, mono=False):
    return ImageFont.truetype(MONO if mono else FONT, size)


def wrap(draw, text, width, fnt):
    words, lines, line = text.split(), [], ""
    for w in words:
        trial = (line + " " + w).strip()
        if draw.textlength(trial, font=fnt) <= width:
            line = trial
        else:
            if line:
                lines.append(line)
            line = w
    if line:
        lines.append(line)
    return lines


def scale_to(im, box):
    """Fit image into box without cropping; upscale pixel art with nearest."""
    bw, bh = box
    sw, sh = im.size
    if not sw or not sh:
        return im
    k = min(bw / sw, bh / sh)
    size = (max(1, round(sw * k)), max(1, round(sh * k)))
    resample = Image.NEAREST if k >= 2 else Image.LANCZOS
    return im.resize(size, resample)


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40]


def main():
    args = sys.argv[1:]
    only = set()
    sheets = True
    for i, a in enumerate(args):
        if a == "--only":
            only = {x.strip() for x in args[i + 1].split(",") if x.strip()}
        elif a == "--no-sheets":
            sheets = False
    spec = json.load(open(os.path.join(ROOT, "elements.json")))
    extracts = os.path.normpath(os.path.join(ROOT, spec["extracts"]))
    out_dir = os.path.join(ROOT, spec["out"])
    captures = os.path.join(ROOT, spec["captures"])
    picks_dir = os.path.join(out_dir, "raw-picks")
    sheets_dir = os.path.join(out_dir, "sheets")
    os.makedirs(picks_dir, exist_ok=True)
    os.makedirs(sheets_dir, exist_ok=True)

    cand = json.load(open(os.path.join(ROOT, spec["candidates"])))["candidates"]
    by_name = {(c["game"], c["name"]): c for c in cand}
    judged = json.load(open(os.path.join(ROOT, spec["judgments"])))
    by_rid = {}
    for rid, j in judged.items():
        a = j["answers"]
        by_rid[rid.split("|", 1)[1]] = {
            "kind": a["kind"]["choice"],
            "p_kind": a["kind"]["probabilities"][a["kind"]["choice"]],
            "usable": a["usable_element"]["bool"],
        }
    def judge_of(c):
        return by_rid.get(f"{c['game']}:{c['name']}",
                          {"kind": "unknown", "p_kind": 0.0, "usable": 0.0})

    W, H = spec["canvas"]
    missing = []
    report = {"generated": "build_elements.py", "canvas": [W, H], "elements": []}

    for el in spec["elements"]:
        if only and el["id"] not in only:
            continue
        cap_path = os.path.join(captures, el["capture"])
        if not os.path.exists(cap_path):
            missing.append(f"{el['id']} capture {el['capture']}")
            continue

        chosen, seen = [], set()
        for key in el.get("prefer", []):
            g, n = key.split(":", 1)
            c = by_name.get((g, n))
            if not c:
                missing.append(f"{el['id']} prefer {key}")
                continue
            if min(c["w"], c["h"]) < el.get("min_side", 0):
                print(f"note: {el['id']} skips prefer {key} ({c['w']}x{c['h']} < min_side)")
                continue
            chosen.append(c)
            seen.add((g, n))

        def usable(c):
            return (min(c["w"], c["h"]) >= el.get("min_side", 0)
                    and judge_of(c)["usable"] >= 0.5
                    and judge_of(c)["kind"] in el["kinds"])

        pool = [c for c in cand
                if usable(c) and (c["game"], c["name"]) not in seen
                and (el["id"], c["game"], c["name"]) not in seen]
        ranks = {k: i for i, k in enumerate(el["kinds"])}
        pool.sort(key=lambda c: (ranks[judge_of(c)["kind"]],
                                 -judge_of(c)["p_kind"],
                                 -(c["w"] * c["h"])))
        per_game = {}
        for c in chosen:
            per_game[c["game"]] = per_game.get(c["game"], 0) + 1
        for c in pool:
            if len(chosen) >= el.get("max_n", 4):
                break
            if per_game.get(c["game"], 0) >= 2:
                continue
            chosen.append(c)
            per_game[c["game"]] = per_game.get(c["game"], 0) + 1
        for c in pool:  # second pass: allow a third tile from one game if short
            if len(chosen) >= el.get("max_n", 4):
                break
            if c in chosen:
                continue
            chosen.append(c)
        if not chosen:
            missing.append(f"{el['id']} no raw pick")
            continue

        # Our element crop, in logical canvas pixels.
        shot = Image.open(cap_path).convert("RGBA")
        sx, sy = shot.width / W, shot.height / H
        x, y, cw, ch = el["crop"]
        ours = shot if el.get("full") else shot.crop(
            (round(x * sx), round(y * sy),
             round((x + cw) * sx), round((y + ch) * sy)))

        tiles = []
        for c in chosen:
            src = os.path.join(extracts, c["path"])
            im = Image.open(src).convert("RGBA")
            transform = "none"
            if c["game"] == "mc3":  # Xbox texture rows decode bottom-up
                im = im.transpose(Image.FLIP_TOP_BOTTOM)
                transform = "flip-vertical"
            dst_dir = os.path.join(picks_dir, c["game"])
            os.makedirs(dst_dir, exist_ok=True)
            digest = hashlib.sha1(c['name'].encode()).hexdigest()[:8]
            name = f"{el['id']}-{slug(c['name'].rsplit('.', 1)[0])[:28]}-{digest}.png"
            dst = os.path.join(dst_dir, name)
            im.save(dst)
            tiles.append({
                "game": c["game"], "name": c["name"], "kind": judge_of(c)["kind"],
                "p_kind": round(judge_of(c)["p_kind"], 3),
                "usable": round(judge_of(c)["usable"], 3),
                "w": c["w"], "h": c["h"], "transform": transform,
                "source_png": os.path.join("output", os.path.relpath(src, out_dir)),
                "source_png_sha256": sha256(src),
                "picked_png": os.path.relpath(dst, ROOT),
                "picked_png_sha256": sha256(dst),
                "raw_member": c.get("raw_member"),
                "raw_member_sha256": c.get("raw_member_sha256"),
                "raw_member_note": c.get("raw_member_note"),
                "container": c.get("container"),
            })

        report["elements"].append({
            "id": el["id"], "name": el["name"], "section": el["section"],
            "capture": el["capture"], "crop_logical": el["crop"],
            "evidence": el["evidence"], "claim": el["claim"],
            "raws": tiles,
        })

        if not sheets:
            continue
        # ---- sheet ----
        tw = 236
        cols = len(tiles)
        width = 32 + 470 + 20 + cols * (tw + 12) + 16
        height = 96 + 330 + 56
        im = Image.new("RGB", (width, height), BG)
        d = ImageDraw.Draw(im)
        f_title, f_sub, f_lbl, f_small = font(21), font(13), font(13), font(11)
        d.text((32, 18), f"{el['id']}  {el['name']}", fill=FG, font=f_title)
        where = (f"full {shot.width}x{shot.height} frame" if el.get("full")
                 else f"crop {el['crop']} (logical {W}x{H})")
        d.text((32, 46), f"{el['section']} · {el['capture']} · {where}",
               fill=MUTED, font=f_sub)
        for i, line in enumerate(wrap(d, el["evidence"], width - 64, f_small)[:2]):
            d.text((32, 66 + i * 13), line, fill=MUTED, font=f_small)
        d.rectangle([32, 96 - 6, width - 32, 96 - 5], fill=ACCENT)

        box = (470, 320)
        shown = scale_to(ours, box)
        ox, oy = 32 + (box[0] - shown.width) // 2, 110 + (box[1] - shown.height) // 2
        d.rectangle([ox - 1, oy - 1, ox + shown.width, oy + shown.height], outline=ACCENT)
        im.paste(shown, (ox, oy), shown)
        d.text((32, 110 + box[1] + 6), "RACER (ours)", fill=ACCENT, font=f_lbl)

        for i, t in enumerate(tiles):
            x0 = 32 + 470 + 20 + i * (tw + 12)
            d.rectangle([x0, 110, x0 + tw, 110 + 320], fill=PANEL)
            for cy in range(120, 320, 16):  # subtle checker so dark art stays visible
                for cx in range(x0 + 4, x0 + tw - 4, 16):
                    if ((cx - x0) // 16 + (cy - 120) // 16) % 2 == 0:
                        d.rectangle([cx, cy, cx + 15, cy + 15], fill=(41, 45, 51))
            path = os.path.join(ROOT, t["picked_png"])
            raw = Image.open(path).convert("RGBA")
            shown = scale_to(raw, (tw - 16, 200))
            rx, ry = x0 + (tw - shown.width) // 2, 110 + 10 + (200 - shown.height) // 2
            im.paste(shown, (rx, ry), shown)
            lines = wrap(d, t["name"].rsplit("/", 1)[-1], tw - 12, f_lbl)[:2]
            ty = 110 + 218
            for line in lines:
                d.text((x0 + 6, ty), line, fill=FG, font=f_lbl)
                ty += 15
            if t["kind"] in el["kinds"]:
                meta = f"{t['game'].upper()} {t['w']}x{t['h']} · {t['kind']} {t['p_kind']:.2f}"
            else:
                meta = f"{t['game'].upper()} {t['w']}x{t['h']} · curated (jev {t['kind']} {t['p_kind']:.2f})"
            d.text((x0 + 6, ty + 2), meta, fill=MUTED, font=f_small)
            if t["transform"] != "none":
                d.text((x0 + 6, ty + 15), t["transform"], fill=HUD, font=f_small)

        foot = "raw: " + " · ".join(
            f"{t['game']}:{t['raw_member'] or t['name']}" for t in tiles)
        for i, line in enumerate(wrap(d, foot, width - 64, f_small)[:2]):
            d.text((32, height - 34 + i * 13), line, fill=MUTED, font=f_small)
        out = os.path.join(sheets_dir, f"{el['id']}-{slug(el['name'])}.png")
        im.save(out)
        print(f"{el['id']} {el['name']}: {len(tiles)} raws -> {os.path.relpath(out, ROOT)}")

    json.dump(report, open(os.path.join(out_dir, "raw-picks.json"), "w"), indent=1)
    if not only:
        # Drop copies and sheets that the current element set no longer references,
        # so output/raw-picks equals the manifest that verify_picks.py checks.
        used = {os.path.basename(t["picked_png"])
                for el in report["elements"] for t in el["raws"]}
        for game in os.listdir(picks_dir):
            for f in os.listdir(os.path.join(picks_dir, game)):
                if f not in used:
                    os.remove(os.path.join(picks_dir, game, f))
        used_sheets = {f"{el['id']}-{slug(el['name'])}.png" for el in report["elements"]}
        for f in os.listdir(sheets_dir):
            if f.startswith("E") and f.endswith(".png") and f not in used_sheets:
                os.remove(os.path.join(sheets_dir, f))
    if missing:
        print("MISSING:")
        for m in missing:
            print(" -", m)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
