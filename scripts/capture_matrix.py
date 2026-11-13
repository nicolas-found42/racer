#!/usr/bin/env python3
"""Run a fixed matrix of native Racer captures from one frozen build for large reference comparisons.

Usage: capture_matrix.py BASE_DIR OUT_DIR [VEHICLE_INDEX [NAME,NAME,...]]
With a vehicle index (0-4) every scenario name is prefixed "v<N>-"; the optional list limits the run.
BASE_DIR is an output directory of capture_visual_review.py (frozen racer, models, shaders, surfaces).
Writes OUT_DIR/<name>.png and OUT_DIR/matrix.json with each scenario's arguments, description and
category. Frames are actual native captures; nothing is composited or altered beyond PPM->PNG.
"""
import json
import subprocess
import sys
from pathlib import Path
from PIL import Image

base = Path(sys.argv[1]).resolve()
out = Path(sys.argv[2]).resolve()
out.mkdir(parents=True, exist_ok=True)
scripts = Path(__file__).resolve().parent / "review_scripts"
import os
racer = Path(os.environ["RACER_BIN"]).resolve() if os.environ.get("RACER_BIN") else base / "racer"  # RACER_BIN: a newer build than the frozen one
vehicle = int(sys.argv[3]) if len(sys.argv) > 3 else 0
only = set(sys.argv[4].split(",")) if len(sys.argv) > 4 else None
if not 0 <= vehicle <= 4:
    raise SystemExit("vehicle index must be 0-4")
if not racer.exists():
    raise SystemExit("frozen racer missing: " + str(racer))

TIMES = {"day": [], "dusk": ["--time", "dusk"], "night": ["--time", "night"]}
VIEWS = {"rear": "rear", "front": "front", "left": "left", "right": "right", "elevated": "elevated"}
scenarios = []


def add(name, category, description, args, delay=3.0, smoke=5.0, script=None):
    scenarios.append(dict(name=name, category=category, description=description, args=args, delay=delay, smoke=smoke, script=script))


for t, targs in TIMES.items():
    for v in VIEWS:
        add(f"street-{t}-{v}", "street_" + t, f"Racer {t} street, {v} chase camera at 9 m, parked cars and trees", targs + ["--camera-view", v, "--camera-distance", "9"])
    add(f"closeup-{t}-left", "closeup_" + t, f"Racer {t} close-up of the car from the side at 3 m", targs + ["--camera-view", "left", "--camera-distance", "3.2"])
    add(f"closeup-{t}-rear", "closeup_" + t, f"Racer {t} close-up of the car from behind at 4 m", targs + ["--camera-view", "rear", "--camera-distance", "4"])
for colour in ("red", "blue", "black"):
    add(f"paint-{colour}-left", "closeup_day", f"Racer day close-up, {colour} paint, side view", ["--paint", colour, "--camera-view", "left", "--camera-distance", "3.2"])
for t, targs in (("day", []), ("night", ["--time", "night"])):
    for delay in (6, 10, 14):
        add(f"speed-{t}-{delay}s", "speed_" + t, f"Racer {t} at full throttle after {delay} s (speed blur, wider field of view)", targs + ["--camera-view", "rear", "--camera-distance", "7"], delay=delay, smoke=delay + 2, script="full-throttle.review")
    for v in ("rear", "left"):
        add(f"brake-{t}-{v}", "braking_" + t, f"Racer {t} hard braking from speed, {v} view (tyre marks, tyre smoke)", targs + ["--camera-view", v, "--camera-distance", "7"], delay=6.4, smoke=8, script="brake.review")
add("launch-day-left", "braking_day", "Racer day launch from standstill, thin smoke at the rear wheels", ["--camera-view", "left", "--camera-distance", "8"], delay=2.1, smoke=5, script="full-throttle.review")
# Hood (bonnet) camera and other intersections of the road grid (need a build with --camera-view hood / --start-at).
for t, targs in TIMES.items():
    add(f"hood-{t}", "hood_" + t, f"Racer {t} bonnet view looking down the street", targs + ["--camera-view", "hood"])
LOCATIONS = {"a": (200, 100, 90), "b": (-200, -200, 180), "c": (100, 300, 270), "d": (-100, 100, 0), "e": (300, -100, 45),
             "f": (-300, 200, 135), "g": (400, 200, 250), "h": (-400, -300, 15)}
for key, (x, z, heading) in LOCATIONS.items():
    for t, targs in TIMES.items():
        add(f"loc-{key}-{t}", f"location_{key}", f"Racer {t} rear view at x={x} z={z} heading {heading}", targs + ["--camera-view", "rear", "--camera-distance", "9", "--start-at", str(x), str(z), str(heading)])
add("neon-night-front", "street_night", "Racer night near the corner neon pylons, front camera at 5 m", ["--time", "night", "--camera-view", "front", "--camera-distance", "5"])
add("neon-night-left", "street_night", "Racer night near the corner neon pylons, side camera at 5 m", ["--time", "night", "--camera-view", "left", "--camera-distance", "5"])

if only is not None:
    scenarios = [s for s in scenarios if s["name"] in only]
    if not scenarios:
        raise SystemExit("no scenario matches the name list")
if vehicle:
    for s in scenarios:
        s["name"] = f"v{vehicle}-" + s["name"]
records = []
DRY = bool(os.environ.get("DRYRUN"))  # DRYRUN=1: rebuild matrix.json entries from files already on disk, run nothing
for i, s in enumerate(scenarios, 1):
    if DRY:
        present = (out / f"{s['name']}.png").exists()
        records.append(dict(s, ok=present, exit=None, file=f"{s['name']}.png" if present else None))
        continue
    ppm = out / f"{s['name']}.ppm"
    # SURFACES overrides the frozen four-tile base atlas so after-runs can pass
    # a newer RCRSURF (e.g. assets/visual-local/v4/surfaces.rgba); the before
    # run keeps the frozen base file.
    surfaces = Path(os.environ["SURFACES"]).resolve() if os.environ.get("SURFACES") else base / "surfaces.rgba"
    argv = [str(racer), "--background", "--smoke", str(s["smoke"]), "--window", "1280", "720",
            "--vehicle-library", str(base / "models/catalog.racer"), "--vehicle", str(vehicle),
            "--shader-dir", str(base / "shaders"), "--world-surfaces", str(surfaces),
            "--screenshot", str(ppm), "--screenshot-delay", str(s["delay"]),
            "--profile", str(out / f"{s['name']}-profile.txt"), "--no-diagnostics", "--hide-hud"]
    # HIDE_GUIDES=1 additionally passes --hide-guides (needs a binary that
    # accepts it); both sides of a before/after must use the same setting.
    if os.environ.get("HIDE_GUIDES"):
        argv += ["--hide-guides"]
    if os.environ.get("CAMERA_PITCH"):
        argv += ["--camera-pitch", os.environ["CAMERA_PITCH"]]
    argv += ["--sky-mesh", str(base / "models/sky.glb")] + s["args"]
    # NO_SCENERY=1 renders the procedural authored city (buildCityScene) instead of the baked
    # models/city.glb: without it the authored building() geometry and its facade ids never draw.
    if os.environ.get("NO_SCENERY"):
        argv += ["--no-scenery"]
    else:
        argv += ["--scenery-mesh", str(base / "models/city.glb")]
    if s["script"]:
        argv += ["--review-script", str(scripts / s["script"])]
    result = subprocess.run(argv, capture_output=True, text=True, timeout=60)
    ok = ppm.exists() and ppm.stat().st_size > 0
    if ok:
        Image.open(ppm).convert("RGB").save(out / f"{s['name']}.png")
        ppm.unlink()
    (out / f"{s['name']}-profile.txt.career").unlink(missing_ok=True)
    (out / f"{s['name']}-profile.txt").unlink(missing_ok=True)
    records.append(dict(s, ok=ok, exit=result.returncode, file=f"{s['name']}.png" if ok else None))
    print(f"[{i}/{len(scenarios)}] {s['name']} ok={ok} exit={result.returncode}", flush=True)
index_path = out / ("matrix.json" if not vehicle else f"matrix-v{vehicle}.json")
merged = {}
if index_path.exists():  # merge by scenario name so a partial run never drops earlier records
    merged = {r["name"]: r for r in json.loads(index_path.read_text())}
merged.update({r["name"]: r for r in records})
index_path.write_text(json.dumps(list(merged.values()), indent=1))
print("done:", sum(r["ok"] for r in records), "of", len(records), "| index now has", len(merged))
