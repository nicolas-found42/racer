#!/usr/bin/env python3
"""Pair every agent-gathered reference (references/web2/manifest.json) with a Racer matrix frame by category.

Usage: make_comparison_pairs_web2.py [OUT_PAIRS.json]
Each reference category has a pool of Racer frames (from output/matrix, including the v1-v4 other-car
captures when present); the frames are cycled so that many distinct Racer frames are used. The pairing is by
category only, so a frame is a nearest available view, not a matching scenario (Racer has no cockpit view).
"""
import json
import sys
from pathlib import Path

HUB = Path(__file__).resolve().parents[1] / "experiments" / "2026-11-07-comparison-matrix"
REFS = HUB / "references" / "web2"
MATRIX = HUB / "output" / "matrix"


def pool(*names):
    out = []
    for n in names:
        out.append(n)
        for v in (1, 2, 3, 4):
            if (MATRIX / f"v{v}-{n}.png").exists():
                out.append(f"v{v}-{n}")
    return [n for n in out if (MATRIX / f"{n}.png").exists()]


NIGHT = pool("street-night-rear", "street-night-front", "street-night-left", "street-night-right", "street-night-elevated",
             "neon-night-front", "neon-night-left", "closeup-night-left", "closeup-night-rear")
DAY = pool("street-day-rear", "street-day-front", "street-day-left", "street-day-right", "street-day-elevated", "closeup-day-rear")
POOLS = {
    "night_street": NIGHT,
    "headlights_lamps": pool("closeup-night-rear", "neon-night-front", "street-night-front", "closeup-dusk-rear", "street-night-rear"),
    "dusk": pool("street-dusk-rear", "street-dusk-left", "street-dusk-right", "street-dusk-front", "street-dusk-elevated", "closeup-dusk-left", "closeup-dusk-rear"),
    "day_street": DAY,
    "buildings_facade": DAY,
    "skyline_horizon": DAY,
    "trees_vegetation": DAY,
    "crowd_props": DAY,
    "other": DAY,
    "replay": DAY,
    "wet_road": pool("speed-day-10s", "speed-day-14s", "speed-day-6s", "street-night-rear", "street-day-rear"),
    "smoke_skid": pool("brake-day-left", "brake-day-rear", "brake-night-rear", "brake-night-left", "launch-day-left"),
    "motion_blur": pool("speed-day-14s", "speed-day-10s", "speed-day-6s", "speed-night-14s", "speed-night-10s", "speed-night-6s"),
    "car_closeup": pool("closeup-day-left", "closeup-day-rear", "closeup-dusk-left", "closeup-night-rear", "paint-red-left", "paint-blue-left", "paint-black-left", "closeup-night-left"),
    "wheel_closeup": pool("closeup-day-left", "paint-red-left", "paint-blue-left", "paint-black-left", "closeup-dusk-left", "closeup-night-left"),
    "garage": pool("garage-ui", "closeup-night-left", "paint-black-left", "paint-red-left"),
    "cockpit_dash": pool("street-day-rear", "street-night-rear", "closeup-day-rear", "street-dusk-rear"),
}


def main():
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else HUB / "pairs-web2.json"
    manifest = json.loads((REFS / "manifest.json").read_text())
    counters = {}
    pairs = []
    for entry in manifest:
        category = entry["category"]
        frames = POOLS[category]
        i = counters.get(category, 0)
        counters[category] = i + 1
        frame = frames[i % len(frames)]
        ref = REFS / entry["file"]
        if not ref.exists():
            raise SystemExit(f"missing reference {ref}")
        pairs.append({"group": "w2-" + category, "ref": str(ref), "ref_label": Path(entry["file"]).stem,
                      "racer": str(MATRIX / f"{frame}.png"), "racer_label": "Racer " + frame})
    out.write_text(json.dumps(pairs, indent=1))
    print(len(pairs), "pairs;", len({p["racer"] for p in pairs}), "distinct Racer frames;", len(counters), "categories ->", out)


main()
