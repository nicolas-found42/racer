#!/usr/bin/env python3
"""Wheel measurements + axial/radial profile plots from analysis.json (PIL only).

Usage: wheel_summary.py <kit-dir>
Writes <kit>/data/wheel_summary.json and <kit>/renders/<car>/wheel_profile.png
"""
import json, os, sys
from PIL import Image, ImageDraw, ImageFont

KIT = sys.argv[1]
an = json.load(open(os.path.join(KIT, "data", "analysis.json")))
INCH = 0.0254
COL = {"rim": (40, 110, 220), "tire": (230, 120, 20), "disc": (30, 160, 80), "caliper": (200, 40, 40)}


def kind(name, role, key=""):
    n = (name or "").lower()
    if "traffic-reference" in key:
        return "tire" if n.endswith("model1") else "rim"
    if role == "carrier" or "calip" in n or "calli" in n:
        return "caliper"
    if "disc" in n or "rotor" in n:
        return "disc"
    if "tire" in n or "tyre" in n or "tir_car" in n:
        return "tire"
    return "rim"


def parts_of(key, w):
    """-> list of (kind, prim) for wheel w. Ford's fused mesh is split per primitive by radius."""
    out = []
    for it in an[key]["wheel_nodes"].get(w, []):
        for p in it["prims"]:
            if key.startswith("ford"):
                out.append(("tire" if p["r_max"] > 0.27 else "rim", p))
            else:
                out.append((kind(it["name"], it["role"], key), p))
    return out


summary = {}
for key, r in an.items():
    d = r["descriptor_wheels"]
    s = {"descriptor": {w: d[w] for w in d}, "per_wheel": {}}
    for w in ("FL", "FR", "RL", "RR"):
        ps = parts_of(key, w)
        by = {}
        for k, p in ps:
            by.setdefault(k, []).append(p)

        def ext(k, f, fn):
            v = [p[f] for p in by.get(k, [])]
            return fn(v) if v else None
        rim_r = ext("rim", "r_max", max)
        tire_ro = ext("tire", "r_max", max)
        tire_ri = None
        if by.get("tire") and not key.startswith("ford"):
            tire_ri = ext("tire", "r_min", min)
        ax_min = ext("tire", "axial_min", min)
        ax_max = ext("tire", "axial_max", max)
        width = (ax_max - ax_min) if ax_min is not None else None
        sw = (tire_ro - rim_r) if (tire_ro and rim_r) else None
        s["per_wheel"][w] = {
            "rim_outer_radius_m": rim_r, "tire_outer_radius_m": tire_ro, "tire_inner_radius_m": tire_ri,
            "tire_axial_width_m": width, "sidewall_height_m": sw,
            "rim_diameter_in": round(2 * rim_r / INCH, 1) if rim_r else None,
            "aspect_ratio_pct": round(100 * sw / width, 1) if (sw and width) else None,
            "tire_rim_radial_overlap_m": round(rim_r - tire_ri, 4) if (rim_r and tire_ri) else None,
            "rim_axial_span_m": [ext("rim", "axial_min", min), ext("rim", "axial_max", max)] if by.get("rim") else None,
            "verts": {k: sum(p["verts"] for p in v) for k, v in by.items()},
            "tris": {k: sum(p["tris"] for p in v) for k, v in by.items()},
            "materials": {k: sorted({p["material"] or "" for p in v}) for k, v in by.items()},
        }
    summary[key] = s

    # ---- profile plot of the front-left wheel
    W, H, M = 1200, 900, 90
    im = Image.new("RGB", (W, H), (250, 250, 250))
    dr = ImageDraw.Draw(im)
    try:
        f = ImageFont.load_default(size=32)
        fs = ImageFont.load_default(size=26)
    except TypeError:
        f = fs = ImageFont.load_default()
    ax0, ax1, r0, r1 = -0.16, 0.16, 0.0, 0.37
    M = 110
    px = lambda a: M + (a - ax0) / (ax1 - ax0) * (W - 2 * M)
    py = lambda r: H - M - (r - r0) / (r1 - r0) * (H - 2 * M)
    for a in range(-150, 151, 50):
        dr.line([(px(a / 1000), M), (px(a / 1000), H - M)], fill=(225, 225, 225))
        dr.text((px(a / 1000) - 24, H - M + 8), str(a), fill=(80, 80, 80), font=fs)
    for rr in range(0, 351, 50):
        dr.line([(M, py(rr / 1000)), (W - M, py(rr / 1000))], fill=(225, 225, 225))
        dr.text((M - 66, py(rr / 1000) - 13), str(rr), fill=(80, 80, 80), font=fs)
    dr.text((W / 2 - 250, H - 50), "axial position, mm (+ = outboard)", fill=(60, 60, 60), font=f)
    dr.text((8, 62), "radius from axle, mm", fill=(60, 60, 60), font=f)
    pf = s["per_wheel"]["FL"]
    def hull(pts):
        pts = sorted(set(pts))
        if len(pts) < 3:
            return pts
        cr = lambda o, a, b: (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
        lo, up = [], []
        for q in pts:
            while len(lo) >= 2 and cr(lo[-2], lo[-1], q) <= 0:
                lo.pop()
            lo.append(q)
        for q in reversed(pts):
            while len(up) >= 2 and cr(up[-2], up[-1], q) <= 0:
                up.pop()
            up.append(q)
        return lo[:-1] + up[:-1]
    tp = [(round(a, 3), round(rr, 3)) for k, p in parts_of(key, "FL") if k == "tire" for (a, rr) in p["profile"] if rr > 0.02]
    if len(tp) >= 3:
        poly = [(px(a), py(rr)) for a, rr in hull(tp)]
        dr.polygon(poly, fill=(253, 232, 205), outline=COL["tire"])
        dr.line(poly + [poly[0]], fill=COL["tire"], width=4)
    for k, p in parts_of(key, "FL"):
        for (a, rr) in p["profile"]:
            x, y = px(a), py(rr)
            dr.ellipse([x - 6, y - 6, x + 6, y + 6], fill=COL[k])
    rdesc = d["FL"]["radius"]
    dr.line([(M, py(rdesc)), (W - M, py(rdesc))], fill=(120, 120, 120), width=2)
    dr.text((W - M - 420, py(rdesc) - 36), "descriptor radius %.0f mm" % (rdesc * 1000), fill=(90, 90, 90), font=fs)
    lx = M + 12
    for k in ("rim", "tire", "disc", "caliper"):
        if any(kk == k for kk, _ in parts_of(key, "FL")):
            dr.ellipse([lx, 18, lx + 22, 40], fill=COL[k])
            dr.text((lx + 30, 10), k if k != "tire" else "tyre", fill=(40, 40, 40), font=f)
            lx += 190
    dr.text((M + 12, 60 + 0), "", fill=(60, 60, 60), font=fs)
    outdir = os.path.join(KIT, "renders", key)
    os.makedirs(outdir, exist_ok=True)
    im.save(os.path.join(outdir, "wheel_profile.png"))

json.dump(summary, open(os.path.join(KIT, "data", "wheel_summary.json"), "w"), indent=1)
for k, s in summary.items():
    p = s["per_wheel"]["FL"]
    print("%-34s rimR=%s tireRo=%s tireRi=%s width=%s sidewall=%s rim\"=%s AR=%s overlap=%s" % (
        k, p["rim_outer_radius_m"], p["tire_outer_radius_m"], p["tire_inner_radius_m"],
        p["tire_axial_width_m"] and round(p["tire_axial_width_m"], 3), p["sidewall_height_m"] and round(p["sidewall_height_m"], 3),
        p["rim_diameter_in"], p["aspect_ratio_pct"], p["tire_rim_radial_overlap_m"]))
