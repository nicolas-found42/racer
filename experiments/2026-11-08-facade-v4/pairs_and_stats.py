#!/usr/bin/env python3
"""Build pairs and measure stats for the 2026-11-08 facade-v4 / night-lighting / smoke round.

Outputs (under output/):
  pairs-before-after.json   same-name before/after pairs (facade, city, g3 sets)
  pairs-web2.json           category-matched console-reference vs after-frame pairs
  stats.json                per-frame-set mean R/G/B, B-R, HSV saturation (480x270 means)
  sheets/                   comparison grids from both pair sets
"""
import json
import subprocess
import sys
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output"
MATRIX = OUT.parent.parent / "2026-11-07-comparison-matrix"
WEB2 = MATRIX / "references" / "web2"
GRID = ROOT.parent.parent / "scripts" / "build_comparison_grids.py"

SETS = ["before", "after", "before-city", "after-city", "before-g3", "after-g3"]

# --- before/after pairs -------------------------------------------------------------
pairs = []
for a, b in (("before", "after"), ("before-city", "after-city"), ("before-g3", "after-g3")):
    for f in sorted((OUT / a).glob("*.png")):
        other = OUT / b / f.name
        if other.exists():
            pairs.append({"group": f"{a}-vs-{b}", "ref": str(f), "ref_label": f"{a}/{f.stem}",
                          "racer": str(other), "racer_label": f"{b}/{f.stem}"})
(OUT / "pairs-before-after.json").write_text(json.dumps(pairs, indent=1))
print(f"{len(pairs)} before/after pairs")

# --- web2 category pairs ------------------------------------------------------------
CATEGORY_FRAMES = {
    "buildings_facade": ["street-day-rear", "street-day-left", "street-day-right", "loc-a-day",
                         "loc-b-day", "loc-c-day", "loc-d-day", "loc-e-day"],
    "night_street": ["street-night-rear", "street-night-front", "street-night-left",
                     "street-night-right", "loc-a-night", "loc-b-night", "loc-c-night",
                     "neon-night-front", "neon-night-left"],
    "day_street": ["street-day-rear", "street-day-front", "street-day-left", "loc-a-day",
                   "loc-c-day", "loc-e-day"],
    "crowd_props": ["street-day-left", "street-day-right", "street-night-left", "loc-b-day",
                    "loc-d-day"],
    "smoke_skid": ["brake-day-rear", "brake-day-left", "brake-night-rear", "launch-day-left"],
    "wet_road": ["street-night-rear", "street-night-front", "loc-a-night", "loc-c-night"],
    "headlights_lamps": ["street-night-front", "street-night-rear", "neon-night-front",
                         "neon-night-left"],
    "skyline_horizon": ["street-day-rear", "street-dusk-rear", "loc-a-day", "loc-b-day"],
}
manifest = json.loads((WEB2 / "manifest.json").read_text())
web2_pairs = []
for cat, frames in CATEGORY_FRAMES.items():
    refs = [e for e in manifest if e.get("category") == cat]
    pool = []
    for name in frames:
        for base in ("after-g3", "after"):
            p = OUT / base / f"{name}.png"
            if p.exists():
                pool.append(p)
                break
    for i, e in enumerate(refs):
        if not pool:
            break
        frame = pool[i % len(pool)]
        web2_pairs.append({"group": cat, "ref": str(WEB2 / e["file"]),
                           "ref_label": e["file"].split("/")[-1],
                           "racer": str(frame), "racer_label": frame.stem})
(OUT / "pairs-web2.json").write_text(json.dumps(web2_pairs, indent=1))
print(f"{len(web2_pairs)} web2 pairs")

# --- sheets -------------------------------------------------------------------------
sheets = OUT / "sheets"
sheets.mkdir(exist_ok=True)
for pairs_file, tag in (("pairs-before-after.json", "before-after"), ("pairs-web2.json", "web2")):
    r = subprocess.run([sys.executable, str(GRID), str(OUT / pairs_file), str(sheets / tag),
                        "--per-sheet", "6"], capture_output=True, text=True)
    print(tag, "grids:", r.returncode == 0, r.stderr[-200:] if r.returncode else "")

# --- stats --------------------------------------------------------------------------
def stats(path):
    im = Image.open(path).convert("RGB").resize((480, 270))
    px = list(im.getdata())
    n = len(px)
    mr = sum(p[0] for p in px) / n / 255
    mg = sum(p[1] for p in px) / n / 255
    mb = sum(p[2] for p in px) / n / 255
    sat = 0.0
    for r, g, b in px:
        mx, mn = max(r, g, b), min(r, g, b)
        sat += 0.0 if mx == 0 else (mx - mn) / mx
    return {"R": round(mr, 3), "G": round(mg, 3), "B": round(mb, 3),
            "B-R": round(mb - mr, 3), "sat": round(sat / n, 3)}

result = {}
for s in SETS:
    d = OUT / s
    if not d.exists():
        continue
    night = [f for f in d.glob("*.png") if "-night" in f.name or "neon" in f.name]
    day = [f for f in d.glob("*.png") if "-day" in f.name]
    dusk = [f for f in d.glob("*.png") if "-dusk" in f.name]
    for label, group in (("day", day), ("dusk", dusk), ("night", night)):
        if not group:
            continue
        agg = {"R": 0, "G": 0, "B": 0, "B-R": 0, "sat": 0}
        for f in group:
            st = stats(f)
            for k in agg:
                agg[k] += st[k]
        result[f"{s}/{label}"] = {k: round(v / len(group), 3) for k, v in agg.items()}
(OUT / "stats.json").write_text(json.dumps(result, indent=1))
for k in sorted(result):
    print(k, result[k])
