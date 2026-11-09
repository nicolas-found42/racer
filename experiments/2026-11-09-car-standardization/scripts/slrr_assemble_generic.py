#!/usr/bin/env python3
"""Static source-CFG assembly of an SLRR car other than Furrano (same method as scripts/slrr_vehicle.py).

Differences from slrr_vehicle.assemble: package, chassis resource and the Java stock wheel/tyre
resource ids are parameters (read from the car's Java file by the caller), and the exhaust the
Furrano code adds explicitly is not added (it is listed as an issue). A part that cannot be
placed is reported, never guessed.

usage: slrr_assemble_generic.py --root ../raw/slrr-231 --package cars/racers/Kurumma.rpk --chassis 343 \
         --rim 0x400 --tyre-front 0x404 --tyre-rear 0x404 --gltf out.gltf --report out.json
"""
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))
import slrr_vehicle as sv  # noqa: E402
from slrr_resources import ResourceResolver  # noqa: E402
from slrr_assets import scx, gltf  # noqa: E402
from slrr_gltf_materials import binding_chain, texture_slots, attach_diffuse, MAX_EXPORT  # noqa: E402


def assemble(root, package, chassis_rid, rim_id, tyre_front, tyre_rear):
    resolver = ResourceResolver(root)
    chassis = sv.definition(resolver, package, chassis_rid)
    parts = [dict(chassis, world=sv.identity(), parent=None)]
    pending, issues = [], []
    for row in chassis["cfg"]["stock"]:
        ident = resolver.identify(package, row["id"])
        if ident[0] != package:
            continue  # parts from other packages (seats, steering wheel) are not placed
        try:
            pending.append(sv.definition(resolver, package, row["id"]))
        except (ValueError, KeyError, IndexError, OSError) as e:
            issues.append({"part": hex(row["id"]), "reason": "definition: " + str(e)})
    while pending:
        progress = False
        for child in pending[:]:
            matches = []
            for pi, parent in enumerate(parts):
                for a in child["cfg"]["attachments"]:
                    if resolver.identify(child["package"], a["resource"]) == (parent["package"], parent["id"]) and a["parent_slot"] in parent["cfg"]["slots"]:
                        matches.append((pi, parent, a))
            for pi, parent in enumerate(parts):
                for c in child["cfg"]["compatible"]:
                    for a in parent["cfg"]["attachments"]:
                        if resolver.identify(child["package"], c["resource"]) == resolver.identify(parent["package"], a["resource"]) and c["parent_slot"] == a["parent_slot"]:
                            matches.append((pi, parent, {"own": c["own"], "parent_slot": a["own"], "line": c["line"], "via": "source compatible/parent attach"}))
            if len(matches) == 1:
                pi, parent, a = matches[0]
                try:
                    world = sv.multiply(parent["world"], sv.multiply(sv.slot_frame(parent["cfg"], a["parent_slot"]), sv.inverse(sv.slot_frame(child["cfg"], a["own"]))))
                except (ValueError, KeyError, IndexError) as e:
                    issues.append({"part": child["alias"], "reason": "frame: " + str(e)})
                    pending.remove(child)
                    progress = True
                    continue
                parts.append(dict(child, world=world, parent=pi, attachment=a))
                pending.remove(child)
                progress = True
        if not progress:
            break
    for c in pending:
        issues.append({"part": c["alias"], "reason": "no unique exact-resource attachment", "cfg": c["cfg_path"]})
    for n, sid in enumerate((101, 102, 103, 104)):
        rim = sv.definition(resolver, "parts/wheels.rpk", rim_id)
        tyre = sv.definition(resolver, "parts/wheels.rpk", tyre_front if n < 2 else tyre_rear)
        rw = sv.multiply(sv.slot_frame(chassis["cfg"], sid), sv.inverse(sv.slot_frame(rim["cfg"], 1)))
        parts.append(dict(rim, alias="rim-%d" % n, world=rw, parent=0, source_selection="Java stock_parts_list_RGear_wheels"))
        tw = sv.multiply(rw, sv.multiply(sv.slot_frame(rim["cfg"], 2), sv.inverse(sv.slot_frame(tyre["cfg"], 1))))
        parts.append(dict(tyre, alias="tyre-%d" % n, world=tw, parent=len(parts) - 1, source_selection="Java stock_parts_list_RGear_tyres"))
    issues.append({"part": "exhaust", "reason": "exhaust parts selected in Java are not added by this generic assembly"})
    scene = {"asset": {"version": "2.0", "generator": "Racer bounded source assembly (generic SLRR)"}, "scene": 0, "scenes": [{"nodes": []}]}
    report = []
    for part in parts:
        try:
            renders = part["cfg"]["renders"]
            selected = next((r for r in renders if r["command"] == "deformable"), renders[0])
            chain = resolver.resolve(part["package"], selected["id"])
            source, refs = binding_chain(chain)
            data, _ = resolver.read(source["path"])
            decoded = scx(data)
            single = gltf(decoded, .01)
            single, binding = attach_diffuse(single, decoded["geometry"], texture_slots(refs), resolver)
            world = sv.multiply(part["world"], sv.pose(selected["pose"]))
            scale = sv.identity()
            for i in range(3):
                scale[i][i] = .01
            sv.append_scene(scene, single, part["alias"], sv.multiply(world, scale))
            report.append({k: v for k, v in part.items() if k != "cfg"} | {"mesh": source, "render": selected, "bindings": binding,
                                                                              "vertices": sum(len(g["positions"]) for g in decoded["geometry"])})
        except (ValueError, IndexError, KeyError, OSError) as e:
            issues.append({"part": part["alias"], "cfg": part["cfg_path"], "reason": str(e)})
    scene["extras"] = {"assembly_issues": issues, "source_part_count": len(report)}
    text = json.dumps(scene, separators=(",", ":"), allow_nan=False)
    if len(text.encode()) > MAX_EXPORT:
        raise ValueError("export exceeds 32MiB")
    return text, {"parts": report, "issues": issues, "provenance": resolver.provenance(), "source_bytes": resolver.bytes}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--package", required=True)
    p.add_argument("--chassis", type=lambda x: int(x, 0), required=True)
    p.add_argument("--rim", type=lambda x: int(x, 0), required=True)
    p.add_argument("--tyre-front", type=lambda x: int(x, 0), required=True)
    p.add_argument("--tyre-rear", type=lambda x: int(x, 0), required=True)
    p.add_argument("--gltf", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    a = p.parse_args()
    if a.gltf.exists() or a.report.exists():
        raise ValueError("fresh output paths required")
    text, report = assemble(a.root, a.package, a.chassis, a.rim, a.tyre_front, a.tyre_rear)
    with a.gltf.open("x") as f:
        f.write(text)
    with a.report.open("x") as f:
        json.dump(report, f, indent=2, allow_nan=False)
    print("parts placed:", len(report["parts"]), "issues:", len(report["issues"]))
    for i in report["issues"][:12]:
        print("  issue:", i["part"], "-", i["reason"][:100])


if __name__ == "__main__":
    main()
