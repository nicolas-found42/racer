#!/usr/bin/env python3
"""Extract MCLA tuning files (lighting, sky, camera, city, rmptfx) from the canonical ISO using the retained
decoded TOC. Limits: member <= 1 MiB, total <= 8 MiB; raw-deflate members are inflated with a 1 MiB cap.
Writes output/tune/<path>.bin plus output/tune-manifest.json (offsets, sizes, SHA-256 of stored and decoded bytes)."""
import json, zlib, hashlib
from pathlib import Path
HUB = Path("/Users/nicolas/Documents/github/reverse-engineering")
toc = json.loads((HUB / "games/racer/experiments/2026-11-05-mcla-data/output/named-entries.json").read_text())
iso = HUB / "games/raw/midnight-club-la/Midnight Club - Los Angeles - Complete Edition (USA, Europe).iso"
BASE, ARCHIVE = 1788608512, 2130739200
PREFIXES = ("/00000000/tune/lighting", "/00000000/tune/sky", "/00000000/tune/camera", "/00000000/tune/city", "/00000000/tune/rmptfx")
out = Path("output/tune"); out.mkdir(parents=True, exist_ok=True)
manifest, total = [], 0
with iso.open("rb") as f:
    for e in toc:
        if e["directory"] or not e["path"].startswith(PREFIXES) or e["wordC"] & 0x80000000: continue
        off, stored, comp = e["word8"] & 0x7fffffff, e["wordC"] & 0xffffff, bool(e["wordC"] & 0x40000000)
        if stored > 1 << 20 or total + stored > 8 << 20 or off + stored > ARCHIVE: continue
        f.seek(BASE + off); raw = f.read(stored); assert len(raw) == stored; total += stored
        data = raw
        if comp:
            d = zlib.decompressobj(-15); data = d.decompress(raw, (1 << 20) + 1)
            assert len(data) <= 1 << 20 and d.eof
        assert len(data) == e["size"], (e["path"], len(data), e["size"])
        rel = e["path"].replace("/00000000/", "").replace("/", "__")
        (out / (rel + ".bin")).write_bytes(data)
        manifest.append({"path": e["path"], "index": e["index"], "offset": off, "stored": stored, "compressed": comp, "size": len(data),
                         "stored_sha256": hashlib.sha256(raw).hexdigest(), "sha256": hashlib.sha256(data).hexdigest(), "file": rel + ".bin"})
Path("output/tune-manifest.json").write_text(json.dumps(manifest, indent=1))
print("extracted", len(manifest), "stored MiB", round(total / 2**20, 2))
