#!/usr/bin/env python3
"""Prepare four hash-pinned local SLRR surfaces; proprietary output stays local.

Uses Pillow's DDS reader. No codec/untile algorithm is implemented here.
Original shader bindings and material scale are unknown: atlas use is authored.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
from PIL import Image

PINS = {
    "asphalt02.dds": "6676effe04a6d8c11dcd1ec7c1a0aa243529009e30126dd7bc9a41c18802ae5c",
    "BRICK48.dds": "f54af44e07a2147f8a841e897c3252abad24f6b84f3923a9c4ce5139a2ceb54f",
    "stonewall3.dds": "52bbd5ee908a60e127307a378d8bb92256bfb72db1f9f86146a7e7817fb9f703",
    "palm1_256.dds": "f068e6ad4237bc04fd10a2e43f836123486a0c80ebebe7ad750b702fa0c98218",
}


def retained(path, expected):
    if path.is_symlink():
        raise ValueError("Refusing a linked prepared output")
    if not path.exists():
        return False
    if not path.is_file() or path.stat().st_size != len(expected) or path.read_bytes() != expected:
        raise ValueError("Refusing to overwrite different retained output: " + path.name)
    return True


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path, required=True, help="slrr-231/maps/textures")
    p.add_argument("--output", type=Path, default=Path("assets/visual-local/v2"))
    args = p.parse_args()
    # Validate the whole bounded selection before creating any prepared output.
    atlas = Image.new("RGBA", (256, 1024))
    rows = []
    for tile, (name, expected) in enumerate(PINS.items()):
        source = args.source / name
        if not source.is_file() or source.stat().st_size > 1024 * 1024:
            raise ValueError("Missing or oversized selected source")
        data = source.read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError("Selected surface source hash mismatch: " + name)
        with Image.open(io.BytesIO(data)) as image:
            image.load()
            if image.size != (256, 256):
                raise ValueError("Unexpected pinned surface dimensions")
            atlas.paste(image.convert("RGBA"), (0, tile * 256))
        rows.append({"source": str(source.resolve()), "source_sha256": expected, "tile": tile})
    encoded = b"RCRSURF2" + atlas.tobytes()
    manifest = {"format": "RCRSURF2, 256x1024 RGBA8, asphalt/pavers/stone/palm vertical tiles",
                "sha256": hashlib.sha256(encoded).hexdigest(), "sources": rows,
                "provenance": "Local supplied SLRR231; redistribution permission unverified. Do not publish atlas.",
                "adaptation": "Authored Racer mapping, scales and material response; original bindings unknown."}
    args.output.mkdir(parents=True, exist_ok=True)
    path = args.output / "surfaces.rgba"
    manifest_path = args.output / "surfaces.json"
    manifest_bytes = json.dumps(manifest, indent=2).encode()
    has_atlas = retained(path, encoded)
    has_manifest = retained(manifest_path, manifest_bytes)
    if not has_atlas:
        with path.open("xb") as target:
            target.write(encoded)
    if not has_manifest:
        with manifest_path.open("xb") as target:
            target.write(manifest_bytes)
    print(json.dumps(manifest))


if __name__ == "__main__":
    main()
