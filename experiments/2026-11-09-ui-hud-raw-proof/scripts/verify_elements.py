#!/usr/bin/env python3
"""Build the jev verification request for the per-element proof claims.

For every element in output/raw-picks.json the proposition is the element claim
("Racer's E## crop and the listed raw assets are the same interface element
class: ..."); the context item carries the Racer evidence line plus, for each
picked raw asset, its shipped name, size, the earlier asset-classifier verdict
and the 16x8 luminance/alpha thumbnail that verdict saw.

usage: verify_elements.py  ->  writes output/jev-request.json
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "output")

picks = json.load(open(os.path.join(OUT, "raw-picks.json")))
thumb_of = {(c["game"], c["name"]): c.get("thumb", [])
            for c in json.load(open(os.path.join(OUT, "raw-candidates.json")))["candidates"]}
spec = json.load(open(os.path.join(ROOT, "elements.json")))
evidence = {e["id"]: e["evidence"] for e in spec["elements"]}

items, propositions = [], []
for el in picks["elements"]:
    raw_lines = []
    for t in el["raws"]:
        thumb = "\n".join(thumb_of.get((t["game"], t["name"]), []))
        raw_lines.append(
            f"- {t['game'].upper()} {t['name']} {t['w']}x{t['h']} "
            f"(asset classifier: {t['kind']} {t['p_kind']:.2f})\n{thumb}")
    text = (f"RACER element {el['id']} {el['name']} ({el['section']}). "
            f"Racer evidence: {el['evidence']}\n"
            f"Raw counterparts picked from the shipped files:\n" + "\n".join(raw_lines))
    items.append({"id": el["id"], "text": text[:2000]})
    propositions.append(f"[{el['id']}] {el['claim']}")

json.dump({"propositions": propositions, "context": items, "auto_accept": 0.85},
          open(os.path.join(OUT, "jev-request.json"), "w"), indent=1)
print(f"{len(propositions)} propositions, {len(items)} context items")
