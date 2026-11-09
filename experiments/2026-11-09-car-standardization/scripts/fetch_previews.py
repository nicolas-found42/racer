#!/usr/bin/env python3
"""Fetch pinned preview GLBs from the carmodels repo and verify them against the catalog.

Usage: fetch_previews.py <catalog.json> <commit> <out-dir> <catalog-id>...
Writes <out-dir>/<code>.glb and <out-dir>/receipt.json (url, bytes, sha256, verified).
Refuses to keep a file whose size or SHA-256 differs from the catalog.
"""
import hashlib, json, os, sys, urllib.request
cat, commit, out = sys.argv[1:4]
ids = sys.argv[4:]
cars = {c["id"]: c for c in json.load(open(cat))["cars"]}
os.makedirs(out, exist_ok=True)
receipt = []
for i in ids:
    c = cars[i]
    url = "https://raw.githubusercontent.com/nicolas-found42/carmodels/%s/dealership/public/%s" % (commit, c["file"])
    data = urllib.request.urlopen(url, timeout=60).read()
    h = hashlib.sha256(data).hexdigest()
    ok = (h == c["sha256"] and len(data) == c["bytes"])
    if ok:
        open(os.path.join(out, c["code"] + ".glb"), "wb").write(data)
    receipt.append({"id": i, "url": url, "bytes": len(data), "sha256": h, "catalog_sha256": c["sha256"], "verified": ok})
    print(i, len(data), h[:12], "OK" if ok else "MISMATCH")
json.dump(receipt, open(os.path.join(out, "receipt.json"), "w"), indent=1)
