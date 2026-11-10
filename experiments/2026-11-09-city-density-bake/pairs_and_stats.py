#!/usr/bin/env python3
"""Pairs, sheets and density proxies for the 2026-11-09 city-density re-bake.

Outputs (all under this experiment's ignored output/):
  pairs-before-after.json / sheets/before-after/  -- 37 before/after pairs
  pairs-web2-{after,before}.json / sheets/web2-{after,before}/ -- console pairs
  sheets/triples/ -- before | after | console reference rows per category
  stats.json -- per-set channel means plus two density proxies

Proxies are deliberately coarse and are labelled as such in the README:
  sky_upper    fraction of the top 40% of the frame matching a sky colour rule
               (denser street walls leave less sky above the canyon)
  facade_edges fraction of strong edge pixels in the middle band (x 15-85%,
               y 25-60%); window grids and storefronts raise it, smooth sky
               and haze lower it
Neither proxy is a visual-quality grade.
"""
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output"
WEB2 = ROOT / "references" / "web2"
GRID = ROOT.parent.parent / "scripts" / "build_comparison_grids.py"
CELL = (480, 270)

# Racer frames paired against each console category (facade-v4 keeps the same
# scenario->category discipline; every name below exists in this round's
# capture set).
CATEGORY_FRAMES = {
    "buildings_facade": ["street-day-rear", "street-day-left", "street-day-right",
                         "loc-a-day", "loc-b-day", "loc-c-day", "loc-d-day", "loc-e-day"],
    "day_street": ["street-day-rear", "street-day-front", "street-day-left",
                   "loc-a-day", "loc-c-day", "loc-e-day", "hood-day"],
    "night_street": ["street-night-rear", "street-night-front", "street-night-left",
                     "street-night-right", "loc-a-night", "loc-b-night", "loc-c-night",
                     "neon-night-front", "neon-night-left"],
    "crowd_props": ["street-day-left", "street-day-right", "street-night-left",
                    "loc-b-day", "loc-d-day"],
    "smoke_skid": ["brake-day-rear", "brake-day-left", "brake-night-rear", "launch-day-left"],
    "wet_road": ["street-night-rear", "street-night-front", "loc-a-night", "loc-c-night"],
    "headlights_lamps": ["street-night-front", "street-night-rear", "neon-night-front",
                         "neon-night-left"],
    "skyline_horizon": ["street-day-elevated", "street-night-elevated", "street-dusk-rear",
                        "loc-a-day", "loc-b-day"],
    # Non-city frames get the nearest generic street frame only so the console
    # set is fully sheeted; they are excluded from density stats below.
    "other": ["street-day-rear", "hood-dusk"],
}


def scenario_names():
    before = {p.stem for p in (OUT / "before").glob("*.png")}
    after = {p.stem for p in (OUT / "after").glob("*.png")}
    return before, after


def build_pairs(before, after):
    pairs = [{"group": "before-vs-after", "ref": str(OUT / "before" / f"{n}.png"),
              "ref_label": f"before/{n}", "racer": str(OUT / "after" / f"{n}.png"),
              "racer_label": f"after/{n}"} for n in sorted(before & after)]
    (OUT / "pairs-before-after.json").write_text(json.dumps(pairs, indent=1))
    print(f"{len(pairs)} before/after pairs")

    manifest = json.loads((WEB2 / "manifest.json").read_text())
    for side in ("after", "before"):
        rows = []
        for cat, frames in CATEGORY_FRAMES.items():
            refs = [e for e in manifest if e.get("category") == cat]
            pool = [f for f in frames if (OUT / side / f"{f}.png").exists()]
            if not refs or not pool:
                print(f"skip {side}/{cat}: refs={len(refs)} frames={len(pool)}")
                continue
            for i, ref in enumerate(refs):
                racer = pool[i % len(pool)]
                rows.append({"group": f"w2-{cat}",
                             "ref": str(WEB2 / ref["file"]),
                             "ref_label": f"{ref['game']}/{ref['file'].split('/')[-1][:-4]}",
                             "racer": str(OUT / side / f"{racer}.png"),
                             "racer_label": f"{side}/{racer}"})
        (OUT / f"pairs-web2-{side}.json").write_text(json.dumps(rows, indent=1))
        print(f"{len(rows)} console pairs ({side} side)")


def build_sheets():
    for pairs, tag in (("pairs-before-after.json", "before-after"),
                       ("pairs-web2-after.json", "web2-after"),
                       ("pairs-web2-before.json", "web2-before")):
        r = subprocess.run([sys.executable, str(GRID), str(OUT / pairs),
                            str(OUT / "sheets" / tag), "--per-sheet", "6"],
                           capture_output=True, text=True)
        print(f"{tag} grids ok={r.returncode == 0}",
              (r.stderr or "")[-200:] if r.returncode else "")


def build_triples():
    """"before | after | console reference" rows, one sheet per category."""
    manifest = json.loads((WEB2 / "manifest.json").read_text())
    sheets = OUT / "sheets" / "triples"
    sheets.mkdir(parents=True, exist_ok=True)
    for cat, frames in CATEGORY_FRAMES.items():
        if cat == "other":
            continue
        refs = [e for e in manifest if e.get("category") == cat]
        pool = [f for f in frames
                if (OUT / "after" / f"{f}.png").exists()
                and (OUT / "before" / f"{f}.png").exists()]
        if not refs or not pool:
            continue
        rows = min(4, len(refs), len(pool))
        sheet = Image.new("RGB", (CELL[0] * 3, CELL[1] * rows + 18 * rows),
                          (10, 12, 16))
        draw = ImageDraw.Draw(sheet)
        for r in range(rows):
            ref = refs[r * len(refs) // rows]
            name = pool[r % len(pool)]
            for c, (path, label) in enumerate((
                    (OUT / "before" / f"{name}.png", f"before {name}"),
                    (OUT / "after" / f"{name}.png", f"after {name}"),
                    (WEB2 / ref["file"], f"console {ref['game']}" ))):
                im = Image.open(path).convert("RGB")
                scale = min(CELL[0] / im.width, CELL[1] / im.height)
                im = im.resize((max(1, round(im.width * scale)),
                                max(1, round(im.height * scale))), Image.LANCZOS)
                cell = Image.new("RGB", CELL, (10, 12, 16))
                cell.paste(im, ((CELL[0] - im.width) // 2, (CELL[1] - im.height) // 2))
                y = r * (CELL[1] + 18) + 18
                sheet.paste(cell, (c * CELL[0], y))
                draw.text((c * CELL[0] + 6, y - 14), label, fill=(220, 220, 220))
        sheet.save(sheets / f"{cat}.jpg", quality=88)
        print(f"triple sheet {cat}: {rows} rows")


def _fit(im):
    im = im.convert("RGB")
    scale = min(CELL[0] / im.width, CELL[1] / im.height)
    return im.resize((max(1, round(im.width * scale)),
                      max(1, round(im.height * scale))), Image.LANCZOS)


def _sky_rule(r, g, b, night):
    if night:
        return b > r + 3 and b > 12 and b < 130 and g <= b + 4
    return b > r + 6 and b > 90 and g > r


def frame_stats(path, night):
    im = _fit(Image.open(path))
    w, h = im.size
    px = im.load()
    sky = n = 0
    for y in range(int(h * .02), int(h * .42)):
        for x in range(w):
            r, g, b = px[x, y]
            n += 1
            sky += 1 if _sky_rule(r, g, b, night) else 0
    edges = im.convert("L").filter(ImageFilter.FIND_EDGES)
    ep = edges.load()
    strong = en = 0
    for y in range(int(h * .25), int(h * .60)):
        for x in range(int(w * .15), int(w * .85)):
            en += 1
            strong += 1 if ep[x, y] > 40 else 0
    small = im.resize((480, 270))
    channels = small.split()
    means = [sum(ch.getdata()) / (480 * 270) for ch in channels]
    sat = 0.0
    sp = small.load()
    for y in range(0, 270, 4):
        for x in range(0, 480, 4):
            r, g, b = sp[x, y]
            mx, mn = max(r, g, b), min(r, g, b)
            sat += 0 if mx == 0 else (mx - mn) / mx
    sat /= (270 // 4) * (480 // 4)
    return {"sky_upper": round(sky / max(n, 1), 3),
            "facade_edges": round(strong / max(en, 1), 3),
            "R": round(means[0], 3), "G": round(means[1], 3),
            "B": round(means[2], 3), "sat": round(sat, 3),
            "night": night}


def stats():
    manifest = {e["file"]: e for e in json.loads((WEB2 / "manifest.json").read_text())}
    result = {}
    for side in ("before", "after"):
        for name in sorted(p.stem for p in (OUT / side).glob("*.png")):
            night = "night" in name
            result[f"{side}/{name}"] = frame_stats(OUT / side / f"{name}.png", night)
    for f, e in sorted(manifest.items()):
        if e["category"] == "other":
            continue
        result[f"console/{e['category']}/{f}"] = frame_stats(
            WEB2 / f, "night" in e["category"] or "night" in f)
    (OUT / "stats.json").write_text(json.dumps(result, indent=1))

    def agg(pred):
        rows = [v for k, v in result.items() if pred(k, v)]
        if not rows:
            return None
        return {key: round(sum(r[key] for r in rows) / len(rows), 3)
                for key in ("sky_upper", "facade_edges", "R", "G", "B", "sat")}

    summary = {}
    for side in ("before", "after"):
        for daynight in ("day", "night"):
            summary[f"{side}/{daynight}"] = agg(
                lambda k, v, s=side, dn=daynight: k.startswith(s + "/") and
                (v["night"] == (dn == "night")))
    for cat in CATEGORY_FRAMES:
        if cat == "other":
            continue
        summary[f"console/{cat}"] = agg(
            lambda k, v, c=cat: k.startswith(f"console/{c}/"))
    summary["before/street_all"] = agg(
        lambda k, v: k.startswith("before/street-") or k.startswith("before/loc-"))
    summary["after/street_all"] = agg(
        lambda k, v: k.startswith("after/street-") or k.startswith("after/loc-"))
    summary["console/canyon_or_dense"] = agg(
        lambda k, v: k.startswith(("console/buildings_facade/",
                                   "console/day_street/", "console/night_street/",
                                   "console/skyline_horizon/")))
    (OUT / "summary.json").write_text(json.dumps(summary, indent=1))
    for key in sorted(summary):
        print(key, summary[key])


def main():
    before, after = scenario_names()
    build_pairs(before, after)
    build_sheets()
    build_triples()
    stats()


if __name__ == "__main__":
    main()
