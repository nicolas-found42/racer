#!/usr/bin/env python3
"""Verify every picked raw asset against the hashes recorded in raw-picks.json.

Checks that (a) the copy under output/raw-picks exists, (b) its sha256 matches
the recorded picked_png_sha256, (c) the decoded extraction source still matches
source_png_sha256, and (d) the MC3 bottom-up flip is declared where expected.
Also checks that every element has at least one pick and a sheet.

usage: verify_picks.py [--strict-mc3]
Exit code 0 only when every element and tile passes.
"""
import hashlib
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "output")
RAW = os.path.normpath(os.path.join(ROOT, "..", "..", "..", "raw"))
EXTRACTS = os.path.normpath(os.path.join(
    ROOT, "..", "2026-11-08-ui-source-extracts", "output"))
MEMBER_ROOTS = {
    "mc3": os.path.join(EXTRACTS, "mc3-ui", "raw", "assets"),
    "gt4": os.path.join(EXTRACTS, "gt4-ui", "raw"),
}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main():
    report = json.load(open(os.path.join(OUT, "raw-picks.json")))
    failures, tiles = [], 0
    for el in report["elements"]:
        if not el["raws"]:
            failures.append(f"{el['id']}: no raw picks")
        if not any(f.startswith(el["id"] + "-") for f in os.listdir(os.path.join(OUT, "sheets"))):
            failures.append(f"{el['id']}: no sheet")
        for t in el["raws"]:
            tiles += 1
            picked = os.path.join(ROOT, t["picked_png"])
            source = os.path.normpath(os.path.join(ROOT, t["source_png"]))
            if not os.path.exists(picked):
                failures.append(f"{el['id']} {t['name']}: missing {t['picked_png']}")
                continue
            if sha256(picked) != t["picked_png_sha256"]:
                failures.append(f"{el['id']} {t['name']}: picked sha256 mismatch")
            if not os.path.exists(source):
                failures.append(f"{el['id']} {t['name']}: missing source {source}")
            elif sha256(source) != t["source_png_sha256"]:
                failures.append(f"{el['id']} {t['name']}: source sha256 mismatch")
            if t["game"] == "mc3" and t["transform"] != "flip-vertical":
                failures.append(f"{el['id']} {t['name']}: MC3 tile without flip")
            if t["game"] != "mc3" and t["transform"] != "none":
                failures.append(f"{el['id']} {t['name']}: unexpected transform")
            if not t.get("raw_member"):
                failures.append(f"{el['id']} {t['name']}: raw member provenance missing")
            elif not t.get("raw_member_sha256") and not t.get("raw_member_note"):
                failures.append(f"{el['id']} {t['name']}: raw member hash missing without a note")
            # Re-hash the retained raw member bytes for MC3, GT4 and SLRR.
            if t["game"] in ("mc3", "gt4", "slrr") and t.get("raw_member_sha256"):
                member = t["raw_member"]
                if t["game"] == "mc3":
                    member = member.split("/", 1)[1]  # drop assets_x.dat/
                    raw_file = os.path.join(MEMBER_ROOTS["mc3"], member)
                elif t["game"] == "gt4":
                    raw_file = os.path.join(MEMBER_ROOTS["gt4"], member)
                else:
                    raw_file = os.path.join(RAW, member)
                if not os.path.isfile(raw_file):
                    failures.append(f"{el['id']} {t['name']}: missing raw member {raw_file}")
                elif sha256(raw_file) != t["raw_member_sha256"]:
                    failures.append(f"{el['id']} {t['name']}: raw member sha256 mismatch")
    used = {os.path.basename(t["picked_png"])
            for el in report["elements"] for t in el["raws"]}
    present = {f for d in os.listdir(os.path.join(OUT, "raw-picks"))
               for f in os.listdir(os.path.join(OUT, "raw-picks", d))}
    for extra in sorted(present - used):
        failures.append(f"unreferenced copy in output/raw-picks: {extra}")
    print(f"{len(report['elements'])} elements, {tiles} tiles checked, "
          f"{len(present)} copies present")
    if failures:
        print("FAIL")
        for f in failures:
            print(" -", f)
        return 1
    print("PASS: every tile copy and every extraction source matches its recorded sha256")
    return 0


if __name__ == "__main__":
    sys.exit(main())
