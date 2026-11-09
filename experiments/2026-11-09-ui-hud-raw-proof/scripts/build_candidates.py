#!/usr/bin/env python3
"""Build the raw UI/HUD asset candidate inventory for the jevify classification.

Reads only the retained extraction tree of experiment 2026-11-08-ui-source-extracts
and the extraction manifests that record where each decoded PNG came from.
Emits output/raw-candidates.json: one row per shipped UI image (post-prefilter),
with dimensions, alpha coverage, dominant colours, a coarse glyph thumbnail and
the raw-file provenance chain.

usage: build_candidates.py EXTRACTS_ROOT OUTPUT_JSON
"""
import hashlib
import json
import os
import sys
from collections import Counter

from PIL import Image

ROOT = sys.argv[1]
OUT = sys.argv[2]
GAMES = ("mc3", "gt4", "slrr", "mcla")
RAW = os.path.normpath(os.path.join(ROOT, "..", "..", "..", "..", "raw"))


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def features(path):
    im = Image.open(path)
    im.load()
    rgba = im.convert("RGBA")
    w, h = im.size
    total = max(1, w * h)
    small = rgba.resize((16, 8), Image.BILINEAR)
    alpha = [p[3] for p in small.getdata()]
    lum = [int(0.2126 * r + 0.7152 * g + 0.0722 * b) for r, g, b, a in small.getdata()]
    opaque = sum(1 for p in rgba.getdata() if p[3] > 16)
    rgb = rgba.convert("RGB").resize((64, 64), Image.BILINEAR)
    counts = Counter(rgb.quantize(colors=8, method=Image.MEDIANCUT).convert("RGB").getdata())
    colors = [f"#{r:02x}{g:02x}{b:02x}" for (r, g, b), _ in counts.most_common(4)]
    ramp = " .:-=+*#%@"
    if opaque < total * 0.9:  # transparent art: show its silhouette instead of colours
        thumb = "".join(ramp[min(9, a * 10 // 256)] for a in alpha)
    else:
        thumb = "".join(ramp[min(9, l * 10 // 256)] for l in lum)
    return {
        "w": w, "h": h,
        "alpha_pct": round(100.0 * opaque / total, 1),
        "colours": colors,
        "thumb": [thumb[i:i + 16] for i in range(0, 128, 16)],
    }


def mc3(root):
    tex = os.path.join(root, "mc3-ui", "png", "tex")
    manifest = {m["png"].split("/")[-1]: m for m in json.load(open(os.path.join(tex, "_manifest.json")))}
    raw_manifest = []
    for tag in ("a", "b"):
        p = os.path.join(root, "mc3-ui", "raw", "assets", f"_manifest_{tag}.json")
        if os.path.exists(p):
            raw_manifest += json.load(open(p))
    raw_hash = {m["name"]: m["sha256"] for m in raw_manifest}
    rows = []
    for name in sorted(os.listdir(tex)):
        if not name.endswith(".png"):
            continue
        p = os.path.join(tex, name)
        src = manifest.get(name, {}).get("src")
        rows.append(dict(
            game="mc3", name=src or name, path=os.path.relpath(p, root), kind_path="texture_x",
            raw_member=f"assets_x.dat/texture_x/{src}" if src else None,
            raw_member_sha256=raw_hash.get(f"texture_x/{src}") if src else None,
            container="raw/mc3.iso -> assets_x.dat (DAVE)",
        ))
    for name in sorted(os.listdir(os.path.join(root, "mc3-ui", "png", "hudmap"))):
        if not name.endswith(".png"):
            continue
        p = os.path.join(root, "mc3-ui", "png", "hudmap", name)
        rows.append(dict(
            game="mc3", name=name, path=os.path.relpath(p, root), kind_path="city/hudmap.xbpf",
            raw_member="resources/city/hudmap.xbpf", raw_member_sha256=None,
            container="raw/mc3.iso -> resources/city/hudmap.xbpf",
        ))
    return rows


def gt4(root):
    report = json.load(open(os.path.join(root, "gt4-ui", "png", "decode-report.json")))
    extract = {e["path"]: e for e in json.load(open(os.path.join(root, "gt4-ui", "extract-manifest.json")))}
    def group_of(gpb):
        parts = gpb.split("/")[:-1]  # drop file name
        if "race_display" in gpb:
            return "gt4_US_display" if "/gt4/US/" in gpb else "gt4_GB_display"
        return parts[-2] + "_" + parts[-1] + "_" + gpb.split("/")[-1][:-4]

    members = {}
    for gpb, images in report.items():
        group = group_of(gpb)
        container = gpb.replace("output/gt4-ui/raw/", "")
        info = extract.get(container, {})
        for entry in images:
            if entry.get("file"):
                members[(group, entry["file"])] = (entry["name"], info)
    rows = []
    rootdir = os.path.join(root, "gt4-ui", "png")
    for dirpath, _, files in os.walk(rootdir):
        for name in files:
            if not name.endswith(".png"):
                continue
            p = os.path.join(dirpath, name)
            group = os.path.relpath(p, rootdir).split('/')[0]
            entry_name, info = members.get((group, name), (None, {}))
            rows.append(dict(
                game="gt4", name=entry_name or name, path=os.path.relpath(p, root), kind_path="",
                raw_member=info.get("path"), raw_member_sha256=info.get("sha256"),
                container="raw/gran-turidmo-4.iso (GT4.VOL)", iso_offset=info.get("iso_offset"),
            ))
    return rows


def slrr(root):
    log = json.load(open(os.path.join(root, "slrr-ui", "convert-log.json")))
    base = os.path.join(root, "slrr-ui")
    trees = [os.path.join(RAW, t) for t in ("slrr-231", "slrr-221")]

    index = {}
    for tree in trees:
        for dirpath, _, files in os.walk(tree):
            for f in files:
                rel = os.path.relpath(os.path.join(dirpath, f), tree)
                index.setdefault(f.lower(), []).append((os.path.basename(tree), rel))

    def resolve(src):
        """Resolve a tree-relative source path to (tree, rel, sha256).

        Exact paths win. When only the basename is known (the extraction
        flattened several gauge directories), the first tree in preference
        order matches, and within a tree a path under gauges/ is preferred.
        """
        for tree in trees:
            p = os.path.join(tree, src)
            if os.path.isfile(p):
                return os.path.basename(tree), src, sha(p)
        hits = index.get(os.path.basename(src).lower(), [])
        if not hits:
            return None, None, None
        hits.sort(key=lambda h: (trees.index(os.path.join(RAW, h[0])), "gauges" not in h[1], h[1]))
        tree, rel = hits[0]
        return tree, rel, sha(os.path.join(RAW, tree, rel))

    rows = []
    for item in log:
        if "dst" not in item:
            continue
        p = os.path.join(base, item["dst"])
        if not os.path.exists(p) or not p.endswith(".png"):
            continue
        tree, rel, raw_sha = resolve(item["src"])
        rows.append(dict(
            game="slrr", name=item["src"], path=os.path.relpath(p, root), kind_path="",
            raw_member=f"{tree}/{rel}" if tree else item["src"],
            raw_member_sha256=raw_sha,
            container=f"raw/slrr-{tree[-3:] if tree else '231'} (installed tree)",
        ))
    d = os.path.join(base, "gauges")
    if os.path.isdir(d):
        for name in sorted(os.listdir(d)):
            if not name.endswith(".png"):
                continue
            src = "cars/textures/gauges/" + name.replace("__", "/")
            tree, rel, raw_sha = resolve(src)
            rows.append(dict(
                game="slrr", name=f"gauges/{name}", path=os.path.relpath(os.path.join(d, name), root),
                kind_path="gauges", raw_member=f"{tree}/{rel}" if tree else None,
                raw_member_sha256=raw_sha,
                container=f"raw/slrr-{tree[-3:] if tree else '231'} (installed tree)",
            ))
    return rows


def mcla(root):
    tex_manifest = json.load(open(os.path.join(root, "mcla-ui-textures", "manifest.json")))
    catalog = {e["name"]: e for e in json.load(open(os.path.join(root, "mcla-ui", "texture-catalog.json")))}
    by_base = {}
    for e in catalog.values():
        by_base.setdefault(e["name"].rsplit("/", 1)[-1], []).append(e)
    containers = {e["path"]: e for e in json.load(open(os.path.join(root, "mcla-ui", "manifest.json")))}
    rows = []
    for m in tex_manifest:
        if m.get("status") != "ok":
            continue
        p = os.path.join(root, "mcla-ui-textures", m["png"])
        if not os.path.exists(p):
            continue
        entry = catalog.get(m["name"]) or (by_base.get(m["name"].rsplit("/", 1)[-1]) or [{}])[0]
        container_path = entry.get("entry")
        member_name = entry.get("name") or m["name"]
        member = f"{container_path}::{member_name}" if container_path else None
        cont = containers.get(container_path, {}) if container_path else {}
        rows.append(dict(
            game="mcla", name=m["name"], path=os.path.relpath(p, root), kind_path="",
            raw_member=member, raw_member_sha256=cont.get("sha256"),
            raw_member_note=None if cont.get("sha256") else
            "virtual texture member; catalogue records entry/name/format but not a container hash",
            container="raw/midnight-club-la (Xbox 360)", offset=cont.get("offset"),
        ))
    return rows


def main():
    rubric = json.load(open(os.path.join(os.path.dirname(__file__), "..", "rubric.json")))
    pre = rubric["prefilter"]
    removed = Counter()
    all_rows = []
    for game, fn in (("mc3", mc3), ("gt4", gt4), ("slrr", slrr), ("mcla", mcla)):
        for row in fn(ROOT):
            name = (row["name"] or "").lower()
            path = row["path"].lower()
            if any(s in name for s in pre["exclude_name_substrings"]):
                removed[game + ":car_or_decal_art"] += 1
                continue
            if any(s in path for s in pre["exclude_name_substrings"]):
                removed[game + ":car_or_decal_art"] += 1
                continue
            if any("/" + d + "/" in "/" + path for d in pre["exclude_dirs"]):
                removed[game + ":font_dir"] += 1
                continue
            try:
                row.update(features(os.path.join(ROOT, row["path"])))
            except Exception as exc:
                removed[game + f":unreadable({type(exc).__name__})"] += 1
                continue
            row["png_sha256"] = sha(os.path.join(ROOT, row["path"]))
            all_rows.append(row)
    json.dump({"root": ROOT, "prefilter_removed": dict(removed), "candidates": all_rows},
              open(OUT, "w"), indent=0)
    per = Counter(r["game"] for r in all_rows)
    print("candidates", len(all_rows), dict(per), "removed", dict(removed))


if __name__ == "__main__":
    main()
