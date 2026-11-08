#!/usr/bin/env python3
"""Prepare sixteen hash-pinned local SLRR surfaces; proprietary output stays local.

Uses Pillow's DDS reader. No codec/untile algorithm is implemented here.
Original shader bindings and material scale are unknown: atlas use is authored.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
from PIL import Image

# (file, sha256, expected source size). Tiles 0-7 are the RCRSURF3 set; tiles 8-15 add SLRR window
# grids, a long sign sheet, a brick strip, a shop window and a curtain-glass sheet (non-square sources
# are resampled to 256x256 here; the shader's world-space or tangent-space scale restores the aspect).
# Pinned so a different file fails.
PINS = {
    "asphalt02.dds": ("6676effe04a6d8c11dcd1ec7c1a0aa243529009e30126dd7bc9a41c18802ae5c", (256, 256)),
    "BRICK48.dds": ("f54af44e07a2147f8a841e897c3252abad24f6b84f3923a9c4ce5139a2ceb54f", (256, 256)),
    "stonewall3.dds": ("52bbd5ee908a60e127307a378d8bb92256bfb72db1f9f86146a7e7817fb9f703", (256, 256)),
    "palm1_256.dds": ("f068e6ad4237bc04fd10a2e43f836123486a0c80ebebe7ad750b702fa0c98218", (256, 256)),
    "Hotel_fal.dds": ("7ab57427d78703bda519235ae19a179cf6a69ffd427516d85df0f38e818cdcb7", (256, 256)),
    "3_szurkehazalattikirakat.dds": ("56a70bb6d6f2c75e06dcb006e8a5b36424ec5e6f9a836970c034ca406031e138", (512, 256)),
    "F_Logo.dds": ("cf4091325fd4d03523781eac6f772812b8df5a624790e9736a48878b25fe2768", (256, 256)),
    "beton79.dds": ("3fda645d8b8f4e6ac24a2e61d77b9160b6e6e73ac67f44609651ee1dde4d90c1", (512, 512)),
    "ablakok08.dds": ("507ffeab1df5a5d4f0e27cfd2ff301358f9cd65c78d1cf42fbfcb8409ccb1d9e", (256, 256)),
    "ablakok2.dds": ("d8ccfce961db4b2a2d1550cea23997ad3b6271fc50424d17c32059d1a6122a35", (256, 256)),
    "Long_logos.dds": ("e63b14cc337484daa3a9b0120edaa0dd91d71caf941113f57b36431cd23b3772", (2048, 128)),
    "Fal4.dds": ("508b0ac07f15c0d10bfb76e15216910f723d28d27f9094455ad6fcf5e6c7919b", (64, 256)),
    "aszalon_kirakat.dds": ("270ed703d1cd549cbc175b6dc4d332a42530864e055d6f9bd6a0f45fa1166e98", (256, 128)),
    "ablakok20.dds": ("13f1f7622b27342441cce01539612c1aa845b7eec27b5a93c8838045566524e3", (256, 256)),
    "ablak1.dds": ("d0594f2c12eb8b1c989f94fc374d6eb2b5a4259e640ad6a8695b05ab7c015df4", (512, 512)),
    "ablakok23.dds": ("fcf6797eec459b81d8f083a95c0525e38635022a8537530ea883dc7b4796f5bf", (256, 256)),
}
TILES = ["asphalt", "pavers", "stone", "palm", "siding", "storefront", "sign sheet", "concrete",
         "window grid A", "window grid B", "long sign sheet", "brick strip", "shop window",
         "window grid C", "curtain glass", "window grid D"]


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
    p.add_argument("--output", type=Path, default=Path("assets/visual-local/v4"))
    args = p.parse_args()
    # Validate the whole bounded selection before creating any prepared output.
    atlas = Image.new("RGBA", (256, 4096))
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
        rows.append({"source": str(source.resolve()), "source_sha256": expected, "tile": tile,
                     "role": TILES[tile]})
    encoded = b"RCRSURF4" + atlas.tobytes()
    manifest = {"format": "RCRSURF4, 256x4096 RGBA8, vertical tiles: " + ", ".join(TILES),
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
