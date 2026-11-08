#!/usr/bin/env python3
"""Bounded probe: list MCLA resources/city entries and read the first 32 stored bytes of a sample.
Reads only the retained decoded TOC (../../../2026-11-05-mcla-data/output/named-entries.json, main checkout) and
<=32 bytes per entry from the canonical ISO. No extraction beyond those headers."""
import json, struct, collections, sys
from pathlib import Path
HUB = Path("/Users/nicolas/Documents/github/reverse-engineering")
toc = json.loads((HUB / "games/racer/experiments/2026-11-05-mcla-data/output/named-entries.json").read_text())
iso = HUB / "games/raw/midnight-club-la/Midnight Club - Los Angeles - Complete Edition (USA, Europe).iso"
BASE = 1788608512
city = [e for e in toc if not e["directory"] and e["path"].startswith("/00000000/resources/city")]
print("city files", len(city), "MiB", round(sum(e["size"] for e in city) / 2**20, 1))
sub = collections.Counter("/".join(e["path"].split("/")[3:5]) for e in city)
print("subdirs", sub.most_common(12))
sample = sorted(city, key=lambda e: e["size"])[:: max(1, len(city) // 14)][:14]
out = []
with iso.open("rb") as f:
    for e in sample:
        off = e["word8"] & 0x7fffffff; stored = e["wordC"] & 0xffffff; comp = bool(e["wordC"] & 0x40000000)
        f.seek(BASE + off); head = f.read(32)
        out.append({"path": e["path"], "size": e["size"], "stored": stored, "compressed": comp, "head": head.hex()})
        print(e["size"], stored, comp, head[:16].hex(), e["path"].split("/", 3)[3])
Path("output/city-probe.json").write_text(json.dumps(out, indent=1))
