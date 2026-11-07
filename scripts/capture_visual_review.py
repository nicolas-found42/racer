#!/usr/bin/env python3
"""Retain actual hidden game captures beside attributed reference screenshots.

Pixel sanity checks reject failed/black renders; they do not grade visual quality.
Every comparison still needs direct inspection and evidence-backed findings.
"""
import argparse
import hashlib
import io
import json
import math
from pathlib import Path
import shutil
import shlex
import subprocess
from PIL import Image, ImageDraw, ImageStat
from install_cars import regular_bytes


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--binary", type=Path, default=Path("build/racer"))
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--reference-label", required=True)
    parser.add_argument("--vehicle", type=int, default=0, help="Index in the current local catalog")
    parser.add_argument("--vehicle-library", type=Path, help="Optional isolated preview catalog; the selected model is frozen before native runs")
    parser.add_argument("--world-mesh", type=Path, action="append", default=[], help="Optional local static world GLB; repeat up to four")
    parser.add_argument("--sky-mesh", type=Path, help="Optional bounded local skydome GLB; prepared local sky used by default")
    parser.add_argument("--scenery-mesh", type=Path, help="Optional local city scenery; prepared city used by default")
    parser.add_argument("--world-origin", type=float, nargs=3, default=[0, 0, 0], help="Explicit authored scene translation")
    parser.add_argument("--world-heading", type=float, default=0, help="Authored clockwise world heading in degrees")
    parser.add_argument("--expanded-world-capture", action="store_true", help="For qualified multiple world meshes:44MiB frozen inputs/80MiB total; normal capture remains28/64MiB")
    parser.add_argument("--camera-distance", type=float, help="Optional inspection camera distance")
    parser.add_argument("--follow-ground", action="store_true", help="Require complete graded wheel support in explicit source worlds")
    parser.add_argument("--post-neutral", action="store_true", help="Disable authored bloom/grading for pixel calibration")
    args = parser.parse_args()
    if not math.isfinite(args.world_heading) or abs(args.world_heading)>360:
        raise ValueError("Finite world heading within[-360,360] required")
    if args.follow_ground and not args.world_mesh:
        raise ValueError("Ground-follow capture requires an explicit world")
    if args.expanded_world_capture and not 2<=len(args.world_mesh)<=4:
        raise ValueError("Expanded capture requires two to four explicitly qualified world meshes")
    input_limit=(44 if args.expanded_world_capture else 28)*1024**2
    output_limit=(80 if args.expanded_world_capture else 64)*1024**2
    out = args.output.resolve()
    if not out.parent.is_dir() or shutil.disk_usage(out.parent).free < 40 * 1024**3:
        raise ValueError("Existing output parent and 40GiB free required")
    out.mkdir(exist_ok=False)
    def retain(path, data):
        # Reserve36MiB for4 RGB PPMs, PNGs,1800x550 comparison sheets and logs.
        used = sum(p.stat().st_size for p in out.rglob("*") if p.is_file())
        if used + len(data) > input_limit:
            raise ValueError("Frozen inputs exceed declared capture quota; native runs not started")
        path.write_bytes(data)
    binary = args.binary.resolve()
    reference = args.reference.resolve()
    binary_bytes = regular_bytes(binary, 16 * 1024**2)
    reference_bytes = regular_bytes(reference, 8 * 1024**2)
    manifest = {"binary": str(binary), "binary_sha256": hashlib.sha256(binary_bytes).hexdigest(),
                "reference": str(reference), "reference_sha256": hashlib.sha256(reference_bytes).hexdigest(),
                "reference_label": args.reference_label,
                "follow_ground":args.follow_ground,"world_origin": args.world_origin, "world_heading_degrees":args.world_heading,"camera_distance": args.camera_distance,"post_neutral":args.post_neutral,
                "limits": {"runs":4,"per_run_seconds":30,"dimensions":[1280,720],"frozen_input_bytes":input_limit,"output_bytes":output_limit},
                "visual_acceptance": "unresolved; sanity checks do not establish fidelity",
                "runs": []}
    retained = out / "racer"
    retain(retained, binary_bytes)
    retained.chmod(binary.stat().st_mode & 0o777)
    manifest["retained_binary"] = str(retained)
    binary = retained
    # Freeze the selected model instead of consulting a mutable live catalog on
    # every native run. No other car or preparation is copied or promoted.
    project = Path(__file__).resolve().parents[1]
    library = (args.vehicle_library if args.vehicle_library is not None else project / "assets/local/vehicles/catalog.racer").resolve()
    library_bytes = regular_bytes(library, 65536)
    lines = library_bytes.decode().splitlines()
    if len(lines) < 3 or lines[0] != "RACER_VEHICLES 1" or int(lines[1]) != len(lines) - 2:
        raise ValueError("Unexpected native catalog")
    if not 0 <= args.vehicle < int(lines[1]):
        raise ValueError("Selected vehicle index outside catalog")
    descriptor_name = json.loads(lines[2 + args.vehicle])
    descriptor = (library.parent / descriptor_name).resolve()
    if descriptor.parent != library.parent or descriptor.suffix != ".vehicle":
        raise ValueError("Selected descriptor is outside the library")
    descriptor_bytes = regular_bytes(descriptor, 32768)
    fields = {tokens[0]: tokens[1:] for line in descriptor_bytes.decode().splitlines()
              if (tokens := shlex.split(line))}
    mesh = (descriptor.parent / fields["mesh"][0]).resolve()
    if mesh.parent != descriptor.parent or mesh.suffix != ".glb":
        raise ValueError("Selected mesh is outside the library")
    mesh_bytes = regular_bytes(mesh, 32 * 1024**2)
    mesh_hash = hashlib.sha256(mesh_bytes).hexdigest()
    if mesh_hash != fields["sha256"][0]:
        raise ValueError("Selected mesh hash mismatch")
    models = out / "models"
    models.mkdir()
    retain(models / descriptor.name, descriptor_bytes)
    retain(models / mesh.name, mesh_bytes)
    frozen_library = models / "catalog.racer"
    frozen_library.write_text("RACER_VEHICLES 1\n1\n" + json.dumps(descriptor.name) + "\n")
    shaders = out / "shaders"
    shaders.mkdir()
    shader_hashes = {}
    for name in ["vs_cubes.bin", "fs_cubes.bin"]:
        data = regular_bytes((project / ".deps/bgfx/examples/runtime/shaders/metal" / name).resolve(), 65536)
        retain(shaders / name, data)
        shader_hashes[name] = hashlib.sha256(data).hexdigest()
    surface = project / "assets/visual-local/v2/surfaces.rgba"
    frozen_surface = out / "surfaces.rgba"
    if surface.exists():
        retain(frozen_surface, regular_bytes(surface.resolve(), 1048584))
    manifest.update({"catalog": str(library), "catalog_sha256": hashlib.sha256(library_bytes).hexdigest(),
                     "descriptor_sha256": hashlib.sha256(descriptor_bytes).hexdigest(),
                     "mesh_sha256": mesh_hash, "shader_sha256": shader_hashes,
                     "surface_sha256": digest(frozen_surface) if frozen_surface.exists() else None})
    frozen_worlds = []
    frozen_scenery = None
    scenery = args.scenery_mesh if args.scenery_mesh is not None else project / "assets/visual-local/city/city.glb"
    if not args.world_mesh and (args.scenery_mesh is not None or scenery.exists()):
        data = regular_bytes(scenery.resolve(), 12 * 1024**2)
        frozen_scenery = models / "city.glb"
        retain(frozen_scenery, data)
        manifest["scenery_sha256"] = hashlib.sha256(data).hexdigest()
    frozen_sky = None
    sky = args.sky_mesh if args.sky_mesh is not None else project / "assets/visual-local/sky/sky.glb"
    if args.sky_mesh is not None or sky.exists():
        data = regular_bytes(sky.resolve(), 12 * 1024**2)
        frozen_sky = models / "sky.glb"
        retain(frozen_sky, data)
        manifest["sky_mesh_sha256"] = hashlib.sha256(data).hexdigest()
    if len(args.world_mesh)>4:
        raise ValueError("At most four static world meshes")
    for index, world in enumerate(args.world_mesh):
        data = regular_bytes(world.resolve(), 32 * 1024**2)
        frozen_world = models / ("world.glb" if index==0 else "world-"+str(index)+".glb")
        retain(frozen_world, data)
        frozen_worlds.append(frozen_world)
    manifest["world_meshes"]=[{"path":str(p),"sha256":digest(p)} for p in frozen_worlds]
    manifest_path = out / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    with Image.open(io.BytesIO(reference_bytes)) as original:
        ref = original.convert("RGB")
        ref.thumbnail((900, 506))
    for label, view, moving in [("rear", "rear", False), ("front", "front", False),
                                ("side", "left", False), ("motion", "rear", True)]:
        ppm = out / (label + ".ppm")
        argv = [str(binary), "--background", "--smoke", "4", "--window", "1280", "720",
                "--vehicle-library", str(frozen_library), "--vehicle", "0", "--camera-view", view,
                "--shader-dir", str(shaders), "--world-surfaces", str(frozen_surface),
                "--screenshot", str(ppm), "--profile", str(out / (label + "-profile.txt")),
                "--no-diagnostics"]
        if moving:
            argv.append("--autodrive")
        if args.follow_ground:
            argv.append("--follow-ground")
        if args.post_neutral:
            argv.append("--post-neutral")
        if frozen_sky:
            argv.extend(["--sky-mesh", str(frozen_sky)])
        if frozen_scenery:
            argv.extend(["--scenery-mesh", str(frozen_scenery)])
        for frozen_world in frozen_worlds:
            argv.extend(["--world-mesh", str(frozen_world)])
        if frozen_worlds:
            argv.extend(["--world-origin", *[str(v) for v in args.world_origin]])
        if args.world_heading:
            argv.extend(["--world-heading",str(args.world_heading)])
        if args.camera_distance is not None:
            argv.extend(["--camera-distance", str(args.camera_distance)])
        result = subprocess.run(argv, capture_output=True, text=True, timeout=30)
        (out / (label + ".log")).write_text(result.stdout + result.stderr)
        run = {"label": label, "argv": argv, "exit": result.returncode}
        manifest["runs"].append(run)
        manifest_path.write_text(json.dumps(manifest, indent=2))
        if result.returncode:
            raise RuntimeError("Native renderer failed; see retained log")
        with Image.open(ppm) as frame:
            frame.load()
            if frame.size != (1280, 720):
                raise RuntimeError("Unexpected capture size")
            image = frame.convert("RGB")
        crop = image.crop((180, 220, 1100, 650))
        stats = ImageStat.Stat(crop)
        if max(stats.mean) < 12 or max(stats.stddev) < 7:
            raise RuntimeError("Black or uniform scene: native visual probe failed")
        png = out / (label + ".png")
        image.save(png)
        run.update({"png_sha256": digest(png), "ppm_sha256": digest(ppm),
                    "scene_mean": stats.mean, "scene_stddev": stats.stddev})
        sheet = Image.new("RGB", (1800, 550), (15, 20, 25))
        sheet.paste(image.resize((900, 506), Image.Resampling.LANCZOS), (0, 32))
        sheet.paste(ref, (900, 32))
        ImageDraw.Draw(sheet).text((12, 9), "Racer native " + label + " | " + args.reference_label +
                                  " (different scene/camera)", fill="white")
        sheet.save(out / ("comparison-" + label + ".png"))
        manifest_path.write_text(json.dumps(manifest, indent=2))
        if sum(p.stat().st_size for p in out.rglob("*") if p.is_file()) > output_limit:
            raise RuntimeError("Capture output budget exceeded")
    print("PASS: four actual native captures and comparison sheets; visual acceptance unresolved")


if __name__ == "__main__":
    main()
