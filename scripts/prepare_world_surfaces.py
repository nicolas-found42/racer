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

# (file, sha256, expected source size). Tiles 0-3 are the original RCRSURF2 set; tiles 4-7 add the
# facade/sign tiles used by surface ids 8-10 and the neon blades (non-square sources are resampled to
# 256x256 here; the shader's world-space scale restores the aspect). Pinned so a different file fails.
PINS = {
    "asphalt02.dds": ("6676effe04a6d8c11dcd1ec7c1a0aa243529009e30126dd7bc9a41c18802ae5c", (256, 256)),
    "BRICK48.dds": ("f54af44e07a2147f8a841e897c3252abad24f6b84f3923a9c4ce5139a2ceb54f", (256, 256)),
    "stonewall3.dds": ("52bbd5ee908a60e127307a378d8bb92256bfb72db1f9f86146a7e7817fb9f703", (256, 256)),
    "palm1_256.dds": ("f068e6ad4237bc04fd10a2e43f836123486a0c80ebebe7ad750b702fa0c98218", (256, 256)),
    "Hotel_fal.dds": ("7ab57427d78703bda519235ae19a179cf6a69ffd427516d85df0f38e818cdcb7", (256, 256)),
    "3_szurkehazalattikirakat.dds": ("56a70bb6d6f2c75e06dcb006e8a5b36424ec5e6f9a836970c034ca406031e138", (512, 256)),
    "F_Logo.dds": ("cf4091325fd4d03523781eac6f772812b8df5a624790e9736a48878b25fe2768", (256, 256)),
    "beton79.dds": ("3fda645d8b8f4e6ac24a2e61d77b9160b6e6e73ac67f44609651ee1dde4d90c1", (512, 512)),
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
    atlas = Image.new("RGBA", (256, 2048))
    rows = []
    for tile, (name, (expected, size)) in enumerate(PINS.items()):
        source = args.source / name
        if not source.is_file() or source.stat().st_size > 1024 * 1024:
            raise ValueError("Missing or oversized selected source")
        data = source.read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError("Selected surface source hash mismatch: " + name)
        with Image.open(io.BytesIO(data)) as image:
            image.load()
            if image.size != size:
                raise ValueError("Unexpected pinned surface dimensions")
            tile_image = image.convert("RGBA")
            if size != (256, 256):
                tile_image = tile_image.resize((256, 256), Image.LANCZOS)
            atlas.paste(tile_image, (0, tile * 256))
        rows.append({"source": str(source.resolve()), "source_sha256": expected, "tile": tile})
    encoded = b"RCRSURF3" + atlas.tobytes()
    manifest = {"format": "RCRSURF3, 256x2048 RGBA8, vertical tiles: asphalt, pavers, stone, palm, siding, storefront, sign sheet, concrete",
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
