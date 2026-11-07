#!/usr/bin/env python3
"""Bounded research captures; loader success does not grant model eligibility."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
SPECS = [
    ("mc3-track", "experiments/2026-11-05-city-scale/output/corvette-track-fit-v1", "bf016ebbec38b035e17896873d7b447b5d80a88969e55f21d979b71f7acb4a3f"),
    ("slrr-design", "experiments/2026-11-06-slrr-rest-fit/output/source-design-loaded-v2", "070eab95eb02c9017067bf86ccbb0226f9503ddceb843f8d45ee905460f685c1"),
    ("slrr-minimum-FAILED-clearance", "experiments/2026-11-06-slrr-rest-fit/output/source-min-travel-v2", "2e978d44a49a87efbeb817a6b41930eb6e7611df7c84763b7c0d33be28e97af6"),
    ("slrr-geometry", "experiments/2026-11-06-slrr-rest-fit/output/geometry-bounded-v3", "fa11fb11d80c0f9b95258954cf16d628f0f4d1ab56366dd370d1d420f276d642"),
    ("mcla-flat-ground", "experiments/2026-11-05-mcla-vehicle/output/player-roadster-flat-ground-v4", "71a6d4ab044ba95673582f34eb9a11621fe89aeda488bea914964a2e1e6e7bd6"),
]

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    out = Path(__file__).resolve().parent / "output/native-v1"
    assert shutil.disk_usage(out.parent.parent).free >= 20 * 1024**3
    out.mkdir(parents=True, exist_ok=False)
    models = out / "models"
    models.mkdir()
    identities = []
    for label, directory, expected in SPECS:
        for suffix in (".vehicle", ".glb"):
            source = ROOT / directory / (expected + suffix)
            if suffix == ".glb":
                assert sha(source) == expected
            shutil.copyfile(source, models / source.name)
        identities.append({"label": label, "source": directory, "mesh_sha256": expected,
                           "descriptor_sha256": sha(models / (expected + ".vehicle"))})
    library = models / "catalog.racer"
    library.write_text("RACER_VEHICLES 1\n5\n" + "".join('"' + s[2] + '.vehicle"\n' for s in SPECS))
    exe = out / "racer"
    shutil.copy2(ROOT / "build/racer", exe)
    manifest = {"scope": "Research-only fit comparison, not eligibility, donor execution or native handling proof",
                "build_sha256": sha(exe), "models": identities, "runs": []}
    began = time.monotonic()
    for index, (label, _, expected) in enumerate(SPECS):
        for view in ("rear", "front", "left", "elevated"):
            assert time.monotonic() - began < 240
            folder = out / (label + "-" + view)
            folder.mkdir()
            ppm, png = folder / "capture.ppm", folder / "capture.png"
            cmd = [str(exe), "--background", "--vehicle-library", str(library), "--vehicle", str(index),
                   "--scene", "scale", "--camera-view", view, "--smoke", "3.3", "--window", "1280", "720",
                   "--profile", str(folder / "profile.txt"), "--diagnostics-dir", str(folder / "history"),
                   "--screenshot", str(ppm)]
            with (folder / "native.log").open("w") as log:
                run = subprocess.run(cmd, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, timeout=15)
            if ppm.exists():
                with Image.open(ppm) as im:
                    im.load()
                    im.save(png)
                    with Image.open(png) as check:
                        assert check.tobytes() == im.tobytes()
                ppm.unlink()  # PNG is the canonical retained pixel-identical capture.
            events = [json.loads(line) for f in (folder / "history").glob("*.jsonl") for line in f.read_text().splitlines()]
            outcomes = [e for e in events if e.get("event") == "asset_load_end"]
            verified = run.returncode == 0 and png.exists() and any(e.get("success") is True and e.get("sha256") == expected for e in outcomes)
            record = {"label": label, "view": view, "command": cmd, "exit": run.returncode, "asset_outcomes": outcomes,
                      "capture": str(png.relative_to(out)) if png.exists() else None, "capture_sha256": sha(png) if png.exists() else None,
                      "verified": verified}
            manifest["runs"].append(record)
            manifest["elapsed_seconds"] = time.monotonic() - began
            (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
            print(json.dumps({"label": label, "view": view, "verified": verified}), flush=True)
            assert sum(p.stat().st_size for p in out.rglob("*") if p.is_file()) < 128 * 1024**2
    manifest["all_loader_captures_verified"] = all(r["verified"] for r in manifest["runs"])
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return 0 if manifest["all_loader_captures_verified"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
