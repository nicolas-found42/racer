#!/usr/bin/env python3
"""Build README.md and the PDF deck for kit v2 (common car = Nissan 350Z, Ford GT stands in for Ford Racing 2).

Usage: build_kit_docs_v2.py <kit-dir> <scratch-dir>
Reads <kit>/data/analysis.json, <kit>/data/wheel_summary.json, <kit>/renders/*, <kit>/compare/*.
Numbers come from those files; the SELECTION block records what was observed on the models and
what the Jev decision calls returned (copied from the tool outputs).
"""
import html, json, os, subprocess, sys
from PIL import Image, ImageDraw, ImageFont

KIT, SCRATCH = sys.argv[1], sys.argv[2]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze_glb as A  # noqa: E402

AN = json.load(open(os.path.join(KIT, "data", "analysis.json")))
WS = json.load(open(os.path.join(KIT, "data", "wheel_summary.json")))

C350 = "nissan-350z"
ORDER = ["gran-turismo-4_nissan-350z-03", "midnight-club-3_nissan-350z-04", "midnight-club-la_nissan-350z-06-roadster",
         "midnight-club-la_nissan-350z-04-coupe-traffic-reference", "juiced-2_nissan-350z",
         "gran-turismo-4_ford-gt-05", "ford-racing-2_ford-gt", "slrr_furrano-gt54-unmatched"]
GAME = {ORDER[0]: "Gran Turismo 4", ORDER[1]: "Midnight Club 3", ORDER[2]: "Midnight Club LA", ORDER[3]: "Midnight Club LA (traffic)",
        ORDER[4]: "Juiced 2", ORDER[5]: "Gran Turismo 4", ORDER[6]: "Ford Racing 2", ORDER[7]: "SLRR"}
CAR = {ORDER[0]: "Nissan 350Z coupe '03", ORDER[1]: "Nissan 350Z coupe '04", ORDER[2]: "Nissan 350Z Roadster '06",
       ORDER[3]: "Nissan 350Z coupe '04 (traffic, reference only)", ORDER[4]: "Nissan 350Z (tuner body)",
       ORDER[5]: "Ford GT '05", ORDER[6]: "Ford GT", ORDER[7]: "Furrano GT54 (no match)"}
SRCID = {ORDER[0]: "gran-turismo-4/niss0004", ORDER[1]: "midnight-club-3-remix/vp_350z_04", ORDER[2]: "midnight-club-los-angeles/vp_nsn_350z_06",
         ORDER[3]: "midnight-club-los-angeles/va_350z_04", ORDER[4]: "juiced-2/350Z", ORDER[5]: "gran-turismo-4/ford0006",
         ORDER[6]: "ford-racing-2/FORD_GT", ORDER[7]: "slrr-231/Furrano_GT54"}
GROUP = {ORDER[0]: "A", ORDER[1]: "A", ORDER[2]: "A", ORDER[3]: "A", ORDER[4]: "A", ORDER[5]: "B", ORDER[6]: "B", ORDER[7]: "C"}
STATUS = {ORDER[0]: "installed, reviewed player car", ORDER[1]: "installed, reviewed player car",
          ORDER[2]: "installed, reviewed player car", ORDER[3]: "traffic-only; never installed, kit reference",
          ORDER[4]: "installed, reviewed player car", ORDER[5]: "prepared for this kit with the GT4 adapter; not reviewed or installed",
          ORDER[6]: "installed, reviewed player car", ORDER[7]: "installed, reviewed player car (unrelated to the 350Z)"}

mm = lambda v: "—" if v is None else "%.0f" % (v * 1000)
FL = {k: WS[k]["per_wheel"]["FL"] for k in ORDER}
DESC = {k: WS[k]["descriptor"] for k in ORDER}
INCH = 0.0254


def scene_stats(key):
    g, _ = A.load_glb(os.path.join(KIT, "models", key + ".glb"))
    n = g["nodes"]
    seen = set()

    def walk(i):
        seen.add(i)
        for c in n[i].get("children", []):
            walk(c)
    for r in g["scenes"][g.get("scene", 0)]["nodes"]:
        walk(r)
    tris = 0
    for i in seen:
        if "mesh" in n[i]:
            for p in g["meshes"][n[i]["mesh"]]["primitives"]:
                tris += g["accessors"][p["indices"]]["count"] // 3 if "indices" in p else g["accessors"][p["attributes"]["POSITION"]]["count"] // 3
    mats = AN[key]["materials"]
    return {"scene_nodes": len(seen), "all_nodes": len(n), "tris": tris,
            "textured": sum(1 for m in mats if m["baseTex"]), "nonopaque": sum(1 for m in mats if m["alpha"] != "OPAQUE"),
            "metallic": sorted({m["metallic"] for m in mats if m["metallic"] is not None}),
            "rough": sorted({m["roughness"] for m in mats if m["roughness"] is not None}),
            "maxtex": max([i["size"] for i in AN[key]["images"] if i["size"]] or [(0, 0)], key=lambda s: s[0] * s[1])}


ST = {k: scene_stats(k) for k in ORDER}


def tyre_open(key):
    """True when the tyre has no vertices on the inboard half below mid-sidewall (open shell)."""
    p = FL[key]
    ro, ri = p["tire_outer_radius_m"], p["tire_inner_radius_m"]
    if ri is None:
        return None
    pts = []
    for it in AN[key]["wheel_nodes"]["FL"]:
        n = (it["name"] or "").lower()
        is_t = ("tire" in n or "tyre" in n or "tir_car" in n) or ("traffic-reference" in key and n.endswith("model1"))
        if is_t:
            for pr in it["prims"]:
                pts += pr["profile"]
    if not pts:
        return None
    lo, hi = min(a for a, _ in pts), max(a for a, _ in pts)
    mid, cut = (lo + hi) / 2, ro - 0.5 * (ro - ri)
    return not any(a < mid and 0.05 < r < cut for a, r in pts)


OPEN = {k: tyre_open(k) for k in ORDER}
split = [k for k in ORDER if not k.startswith("ford")]
fused = [k for k in ORDER if k.startswith("ford")]


def sw(k):
    return FL[k]["sidewall_height_m"]


def wd(k):
    return FL[k]["tire_axial_width_m"]


matrix = [[(sw(b) / sw(a), wd(b) / wd(a)) for b in split] for a in split]
mvals = [x for r in matrix for x, _ in r if abs(x - 1) > 1e-9]
overlaps = {k: FL[k]["tire_rim_radial_overlap_m"] for k in split}
c350 = ORDER[:5]
rad350 = [FL[k]["tire_outer_radius_m"] for k in c350]
rim350 = [FL[k]["rim_outer_radius_m"] for k in c350]
sw350 = [sw(k) for k in c350]

# ------------------------------------------------------------------ selection evidence (observed + tool outputs)
FAMS = ["Nissan 350Z", "Ford Mustang", "Corvette Z06", "Dodge Viper", "Dodge Charger", "Mitsubishi Lancer Evolution", "VW Golf R32",
        "Honda/Acura NSX", "Nissan Skyline GT-R", "Ford GT", "Saleen S7", "Lamborghini Murcielago", "Lamborghini Gallardo",
        "Camaro Z28", "Pontiac GTO", "Toyota Supra", "Mitsubishi Eclipse", "Mazda RX-7", "Ford Focus", "Dodge Challenger", "Ducati 999"]
GAMES = ["GT4", "MC3", "MCLA", "FR2", "J2"]
PRES = {  # name-based presence, jev_verify over each game's car list (verdict 'verified'); *=low-confidence review flag
    "GT4": {"Nissan 350Z", "Ford Mustang", "Corvette Z06", "Dodge Viper", "Dodge Charger", "Mitsubishi Lancer Evolution", "VW Golf R32", "Honda/Acura NSX",
            "Nissan Skyline GT-R", "Ford GT", "Saleen S7", "Camaro Z28", "Pontiac GTO", "Toyota Supra", "Mitsubishi Eclipse", "Mazda RX-7", "Ford Focus"},
    "MC3": {"Nissan 350Z", "Corvette Z06", "Dodge Viper", "Dodge Charger", "Mitsubishi Lancer Evolution", "VW Golf R32", "Nissan Skyline GT-R", "Saleen S7",
            "Lamborghini Murcielago", "Lamborghini Gallardo", "Camaro Z28", "Pontiac GTO", "Toyota Supra", "Mitsubishi Eclipse", "Ducati 999"},
    "MCLA": {"Nissan 350Z", "Ford Mustang", "Corvette Z06", "Dodge Charger", "Mitsubishi Lancer Evolution", "VW Golf R32", "Nissan Skyline GT-R", "Ford GT",
             "Saleen S7", "Lamborghini Murcielago", "Lamborghini Gallardo", "Camaro Z28", "Pontiac GTO", "Mitsubishi Eclipse", "Mazda RX-7", "Ford Focus",
             "Dodge Challenger", "Ducati 999"},
    "FR2": {"Ford Mustang", "Ford GT", "Ford Focus"},
    "J2": {"Nissan 350Z", "Ford Mustang", "Corvette Z06", "Dodge Viper", "Dodge Charger", "Mitsubishi Lancer Evolution", "VW Golf R32", "Honda/Acura NSX",
           "Nissan Skyline GT-R", "Saleen S7", "Camaro Z28", "Pontiac GTO", "Toyota Supra", "Mitsubishi Eclipse", "Mazda RX-7", "Ford Focus"},
}
COUNT = {f: sum(1 for g in GAMES if f in PRES[g]) for f in FAMS}
SHARED = {g: len(PRES[g]) for g in GAMES}

COPIES = [  # candidate copies examined on the models: (family, game, source id, name/year in source metadata, body style seen, mesh length m, verdict)
    ("350Z", "GT4", "niss0004", "Nissan 350Z (Z33) '03", "coupe", 4.308, "same car"),
    ("350Z", "GT4", "niss0032", "Nissan 350Z Roadster (Z33) '03", "roadster", 4.308, "same car, convertible (not prepared)"),
    ("350Z", "MC3", "vp_350z_04", "code only (vp_350z_04)", "coupe", 4.335, "same car"),
    ("350Z", "MCLA", "vp_nsn_350z_06", "2006 350Z ROADSTER", "roadster", 4.336, "same car, convertible"),
    ("350Z", "MCLA", "va_350z_04", "code only (traffic)", "coupe", 4.297, "same car; traffic-only"),
    ("350Z", "J2", "350Z", "350Z (no year)", "coupe, tuner body kit", 4.300, "same car, modified styling"),
    ("Mustang", "GT4", "ford0011", "Ford Mustang GT '05", "coupe", 4.817, "2005 generation"),
    ("Mustang", "MCLA", "vp_frd_mustang_06", "2005 MUSTANG GT CONVERTIBLE", "convertible", 4.799, "2005 generation, convertible"),
    ("Mustang", "FR2", "MUSTANG_CONCEPT", "code only", "concept coupe, wide fenders", 4.65, "2005-style concept, not the production car"),
    ("Mustang", "FR2", "MACH1_SIXTY", "1973 Mach 1 (Racer descriptor)", "1971-73 fastback", 4.839, "different generation"),
    ("Mustang", "FR2", "MUSTANG_68", "code only", "1968 fastback", 4.78, "different generation"),
    ("Mustang", "J2", "MUSTANG05", "Mustang GT 2005", "not viewable", None, "unverified: no extraction path"),
    ("Ford GT", "GT4", "ford0006 / ford0015", "Ford GT '05 (two entries)", "coupe", 4.62, "same car"),
    ("Ford GT", "MCLA", "vp_frd_gt_06", "2006 GT", "coupe", 4.643, "same car"),
    ("Ford GT", "FR2", "FORD_GT", "code only", "coupe, GT40 livery", 4.616, "same car"),
    ("SLRR", "SLRR", "Kurumma_Z35C", "in-game text: year-2000 racing Kurumma Z3, 4.2L V6", "fastback coupe, split rear lights", 4.50, "not a 350Z (Jev 0.98 contradicted)"),
    ("SLRR", "SLRR", "Stallion_3_5_Turbo", "in-game text: enhanced Stallion 3.2L, turbo V6", "short fastback, big wing", 3.97, "not a Mustang (Jev 0.92 contradicted)"),
]

JEV = [  # (round, tool, question, outcome, how used)
    ("1 names", "jev_verify x5", "Does each game's car list contain each of 21 car models?", "17/15/18/3/16 verified for GT4/MC3/MCLA/FR2/J2; low-confidence flags on MC3 Lancer Evo and Ducati, MCLA Ford GT, Camaro Z28, Ducati", "candidate coverage table"),
    ("1 names", "jev_noul", "Are SLRR cars fictional stand-ins (Kurumma Z35C, Stallion, Badge GTO ...)?", "0.53-0.82, all 'uncertain'", "no SLRR match accepted"),
    ("1 names", "jev_decide", "Common car?", "nissan-350z 0.69 (confidence 0.64); Ford Racing 2 requirement contradicted", "kept as leading candidate"),
    ("1 names", "jev_decide", "Bridge game?", "gt4 0.90, mcla 0.06", "kept"),
    ("1 names", "jev_decide", "Ford Racing 2 stand-in?", "MACH1_SIXTY (1973) 0.93", "REJECTED: the models show a different generation than every other game's Mustang"),
    ("1 names", "jev_decide", "SLRR stand-in?", "no-match 0.66, kurumma-z35c 0.08", "SLRR stays unmatched"),
    ("2 models", "jev_noul", "Same generation across copies?", "350Z all same generation 0.69; Mustang GT '05 / MCLA / J2 same S197 0.81; Mach 1 is a different generation 0.66; Mustang concept is an S197 prototype 0.54", "flagged uncertainty; resolved by looking at the meshes"),
    ("2 models", "jev_decide", "Common car (model-verified evidence)?", "ford-gt-2005 0.51, nissan-350z 0.25, mustang 0.00 (confidence 0.41; recommended pick contradicted 'most games')", "split verdict; truth table below decides: widest coverage = 350Z, Ford GT covers the game it lacks"),
    ("2 models", "jev_decide", "Ford Racing 2 stand-in (model-verified evidence)?", "none 0.76, fr2-ford-gt 0.20, mustang-concept 0.02, mach1-1973 0.00", "no candidate satisfies every requirement; Ford GT is the only mesh-verified identical car in the bridge game that is installed"),
    ("2 models", "jev_decide", "MCLA 350Z to use?", "use-both 0.53, traffic coupe 0.39, roadster 0.01", "roadster (allowed player car) plus the traffic coupe as a labelled reference"),
    ("3 SLRR", "jev_verify", "Is the assembled Kurumma Z35C a 350Z, or the Stallion 3.5 Turbo a 2005 Mustang? (measured lengths, in-game text, my notes on the renders)", "Z35C is a 350Z: contradicted 0.98; length within 2%: contradicted 0.73; set in 2000 before the Z33: verified 0.91; Stallion is a 2005 Mustang: contradicted 0.92; length within 5%: contradicted 0.95", "neither SLRR car is a match"),
    ("3 SLRR", "jev_decide", "Which SLRR car represents SLRR?", "no-match-keep-furrano 0.98, all other options 0.00-0.01", "SLRR stays unmatched; Furrano kept for wheel coverage"),
]

# ------------------------------------------------------------------ comparison sheets from the compare renders
CMP = os.path.join(KIT, "compare")


def sheet(rows, views, out, tw=560):
    try:
        f = ImageFont.load_default(size=22)
    except TypeError:
        f = ImageFont.load_default()
    ims = []
    for label, key in rows:
        r = []
        for v in views:
            im = Image.open(os.path.join(CMP, "%s_%s.png" % (key, v))).convert("RGB")
            im = im.resize((tw, int(im.height * tw / im.width)))
            d = ImageDraw.Draw(im)
            d.rectangle([0, 0, tw, 30], fill=(20, 32, 46))
            d.text((8, 3), label, fill=(255, 255, 255), font=f)
            r.append(im)
        ims.append(r)
    h = ims[0][0].height
    sh = Image.new("RGB", (tw * len(views), h * len(rows)), (20, 20, 20))
    for j, r in enumerate(ims):
        for i, im in enumerate(r):
            sh.paste(im, (i * tw, j * h))
    sh.save(out)


sheet([("GT4 niss0004 '03 coupe", "gt4_350z_03"), ("GT4 niss0032 '03 roadster", "gt4_350z_roadster_03"), ("MC3 vp_350z_04 coupe", "mc3_350z_04"),
       ("MCLA vp_nsn_350z_06 2006 roadster", "mcla_350z_roadster_06"), ("MCLA va_350z_04 coupe (traffic)", "mcla_350z_coupe_04_traffic"), ("Juiced 2 350Z coupe", "j2_350z")],
      ["front34", "rear34", "side"], os.path.join(CMP, "sheet_350z.png"), 520)
sheet([("FR2 MACH1_SIXTY (1973)", "fr2_mach1_sixty"), ("FR2 MUSTANG_68 (1968)", "fr2_mustang_68"), ("FR2 MUSTANG_CONCEPT", "fr2_mustang_concept"),
       ("GT4 ford0011 Mustang GT '05", "gt4_mustang_gt_05"), ("MCLA 2005 Mustang GT convertible", "mcla_mustang_gt_conv_05")],
      ["front34", "side", "rear34"], os.path.join(CMP, "sheet_mustang.png"), 520)
sheet([("FR2 FORD_GT", "fr2_ford_gt"), ("GT4 ford0006 Ford GT '05", "gt4_ford_gt_05_a"), ("GT4 ford0015 Ford GT '05", "gt4_ford_gt_05_b"),
       ("MCLA vp_frd_gt_06 2006 GT", "mcla_ford_gt_06")], ["front34", "side", "rear34"], os.path.join(CMP, "sheet_ford_gt.png"), 520)

sheet([("SLRR Kurumma Z35C (assembled)", "slrr_kurumma_z35c"), ("SLRR Stallion 3.5 Turbo (assembled)", "slrr_stallion_3_5_turbo"),
       ("GT4 350Z '03 (for scale)", "gt4_350z_03"), ("GT4 Mustang GT '05 (for scale)", "gt4_mustang_gt_05")],
      ["front34", "side", "rear34"], os.path.join(CMP, "sheet_slrr.png"), 520)

# ------------------------------------------------------------------ per-car notes
CARS = {
    ORDER[0]: ["Same exporter and node layout as the NSX in kit v1: `wheel_*` (rim) and `tire_*` per corner, one mesh each, pivot-centred.",
               "Rim is a 990-vertex shell offset outboard of the hub plane; the tyre is an open shell (no inboard sidewall) whose inner radius reaches %s mm inside the rim." % mm(overlaps[ORDER[0]]),
               "308 materials (all roughness 0.7 / metallic 0), 110 images; windows render as flat colours as on every GT4 car.",
               "A second GT4 entry, `niss0032`, is the 2003 roadster of the same car (not prepared)."],
    ORDER[1]: ["`whl_N_rim_0` and `whl_N_tire_0` per corner; the rim is a multi-primitive chrome assembly (6 primitives incl. an overlay and an inner shell).",
               "Rim outer radius equals the tyre inner radius (%s mm): a clean seat. Tyre outer radius %s mm is the largest of the five 350Z copies." % (mm(FL[ORDER[1]]["rim_outer_radius_m"]), mm(FL[ORDER[1]]["tire_outer_radius_m"])),
               "The tyre is an open shell; 95 materials, 15 images; no glTF extensions.",
               "Visually the same pre-facelift coupe as the GT4 car (headlamps, tail lamps, bumper grille)."],
    ORDER[2]: ["Three nodes per corner: rim `model0`, a 9-vertex `model1`, and `tir_car` (a generic shared tyre resource).",
               "Convertible body (black soft top), so it does not match the three coupes; headlight meshes are untextured in this preparation (white front end).",
               "Rim outer radius equals the tyre inner radius; descriptor wheel pose is a Racer 'authored fit'.",
               "141 materials with `sourceShader` metadata; every factor is metallic 0 / roughness 0.7."],
    ORDER[3]: ["Traffic-namespace model: the user's rule keeps `va_` models out of player installation and selection, so this entry is a comparison reference only and nothing here installs it.",
               "Matches the other copies' body style (coupe, 4.30 m). Wheel parts are `model0` (rim) and `model1` (tyre) inside `body_lod_0`; the rim is a multi-spoke design unlike the other 350Z rims.",
               "Only 14 materials and 6 images; the tyre is widest of the 350Z copies (%s mm)." % mm(wd(ORDER[3]))],
    ORDER[4]: ["Per corner: `WHEEL_*` (rim), `ADAPTED_NATIVE_TOYO_TYRE_*`, `TEST_DISC_*` (rolling) and `TEST_CALIPER_*` (steering-only carrier); descriptor format v2.",
               "The tyre is the shared Toyo template filtered to rubber; its outer radius (%s mm) is the smallest of the 350Z copies and it overlaps the rim barrel by %s mm." % (mm(FL[ORDER[4]]["tire_outer_radius_m"]), mm(overlaps[ORDER[4]])),
               "Tuner styling (wide fender flares, dark lower body, deep-dish wheels): the same Z33 platform but not a stock look.",
               "Every material is metallic 0.15 / roughness 0.55; glass is an authored tint."],
    ORDER[5]: ["Prepared for this kit with `scripts/prepare_gt4_vehicle.py` (the same adapter the NSX and GT4 350Z use). It is NOT one of Racer's reviewed or installed cars and has no scale review.",
               "Same GT4 layout as the NSX/350Z: `wheel_*` + `tire_*`; the tyre is an open shell overlapping the rim by %s mm. Two GT4 entries (ford0006, ford0015) are both '05 Ford GT; this kit uses ford0006." % mm(overlaps[ORDER[5]]),
               "356 materials, 163 images, `KHR_materials_variants`."],
    ORDER[6]: ["Installed, reviewed player car; the Ford exporter writes one fused `WHEEL_STATIC` mesh per corner (13 primitives, one atlas material `FORDGT_512`), so the rim/tyre split in this kit is a radius heuristic.",
               "The file holds 254 nodes, only a fraction reachable from the scene root; a `BRAKE_GLOW` plane sits behind each wheel.",
               "Mesh length 4.616 m matches the GT4 '05 (4.62 m) and the MCLA 2006 GT (4.64 m); wheels differ: tyre width %s mm here against %s mm on the GT4 copy." % (mm(wd(ORDER[6])), mm(wd(ORDER[5])))],
    ORDER[7]: ["Not a match for either group: SLRR has no real-model cars (all fictional brands) and no SLRR car was verified as a 350Z or Ford GT.",
               "Kept so the wheel standard still covers SLRR: separate rim (5,904 vertices) and closed tyre with a 116 mm sidewall.",
               "Racer-authored parked pose; materials are one `source-diffuse` entry per primitive on mostly default-white textures."],
}
WHEEL_HOW = {
    ORDER[0]: "`wheel_*`/`tire_*` nodes per corner, pivot-centred (GT4 exporter).",
    ORDER[1]: "`whl_N_rim_0`/`whl_N_tire_0` per corner; Racer-authored track mounts.",
    ORDER[2]: "Rim `model0` + `model1` + generic `tir_car` tyre per corner.",
    ORDER[3]: "`body_lod_0` `model0` (rim) and `model1` (tyre) per corner.",
    ORDER[4]: "Rim, Toyo template tyre, rolling disc and steering-only caliper per corner; descriptor v2.",
    ORDER[5]: "`wheel_*`/`tire_*` nodes per corner (GT4 exporter, prepared for this kit).",
    ORDER[6]: "One fused `WHEEL_STATIC` mesh per corner under a hub node; split by radius heuristic.",
    ORDER[7]: "`rim-N` and `tyre-N` per corner, pivot-centred.",
}


def rel(car, name):
    return "renders/%s/%s.png" % (car, name)


def md_table(head, rows):
    out = ["| " + " | ".join(head) + " |", "|" + "|".join("---" for _ in head) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def rng(vals):
    return "%.0f–%.0f" % (min(vals) * 1000, max(vals) * 1000)


# ------------------------------------------------------------------ README
def build_readme():
    L = []
    w = L.append
    w("# Car and wheel standardization kit, v2: one car across the games\n")
    w("Kit v1 (`../car-standardization-kit/`) used one unrelated car per game. v2 replaces it with **the same car in as many games as the models show**, so the differences you see are differences in how each game stores that car, not differences between cars. Goal unchanged: each car its own file, one lighting/material model, rim and tyre separate, any tyre on any rim resized to match.\n")
    w("These are Racer's prepared GLBs (axes, units, wheel mounts and some fits authored by Racer) plus a few unmodified previews from the carmodels repo. The models are copyrighted game assets and live under the gitignored `assets/local/`.\n")
    w("## How the cars were chosen\n")
    w("**Names were not trusted.** A first pass matched car names with Jev; the models then overturned one of its picks (see the decision log). The final choice rests on the meshes: same model, same generation, same body style, checked on renders and measured extents under one rig. Years come from the source metadata where it has them (GT4 names, MCLA UI strings), otherwise from the model.\n")
    w("1. **Candidate coverage by name (Jev verify, 21 car families, 5 games with real cars; SLRR has only fictional brands).** The widest families reach 4 of 5: " +
      ", ".join("%s (%d)" % (f, c) for f, c in sorted(COUNT.items(), key=lambda x: -x[1])[:12] if c >= 4) + ". No family is in all five.\n")
    w(md_table(["Family"] + GAMES + ["Games"], [[f] + ["✓" if f in PRES[g] else "" for g in GAMES] + [COUNT[f]] for f in FAMS if COUNT[f] >= 3]) + "\n")
    w("2. **Model check.** Each copy of the three finalists was rendered and measured:\n")
    w(md_table(["Family", "Game", "Source", "Name / year in source", "Body seen", "Mesh length m", "Verdict"],
               [[a, b, "`%s`" % c, d, e, ("%.2f" % f_) if f_ else "—", g] for a, b, c, d, e, f_, g in COPIES]) + "\n")
    w("![350Z copies](compare/sheet_350z.png)\n")
    w("![Mustang generations](compare/sheet_mustang.png)\n")
    w("![Ford GT copies](compare/sheet_ford_gt.png)\n")
    w("What the models show: the five 350Z copies are one car (lengths within 1%), but MCLA's only player copy is a **roadster** while GT4/MC3/Juiced 2 are coupes; Juiced 2's has tuner styling. The only Mustang Ford Racing 2 ships as a player car is a **1973 Mach 1**, a different generation from the 2005 Mustang GT in GT4 and MCLA, so name matching it to the others would have been wrong. The **Ford GT** is the same 2005/06 production car in GT4 (two entries), MCLA and Ford Racing 2.\n")
    w("3. **Truth table (code).** Common car = family with the widest model-verified coverage; games without it get a stand-in that is a mesh-verified identical car in the bridge game; body-style mismatches are kept but labelled.\n")
    w(md_table(["Game", "Has the 350Z?", "Entry in this kit", "Why"], [
        ["Gran Turismo 4 (bridge game)", "yes, coupe '03", "350Z coupe `niss0004`", "also holds the Ford GT and the 350Z roadster, so it links both groups"],
        ["Midnight Club 3", "yes, coupe", "350Z `vp_350z_04`", "—"],
        ["Midnight Club LA", "roadster '06 (player), coupe '04 (traffic)", "roadster + traffic coupe (reference only)", "body style differs from the other three; the traffic coupe matches but is never installed"],
        ["Juiced 2", "yes, tuner body", "350Z", "same platform, modified styling"],
        ["Ford Racing 2", "no (Ford only)", "Ford GT", "mesh-identical to the GT4 '05 and MCLA 2006 GT copies; 1973 Mach 1 rejected on year"],
        ["SLRR", "no (fictional brands)", "Furrano GT54, unmatched", "Kurumma Z35C (4.50 m) and Stallion 3.5 Turbo (3.97 m) were assembled and inspected: neither is a 350Z or a Mustang"]]) + "\n")
    w("![SLRR candidates](compare/sheet_slrr.png)\n")
    w("**Bridge game: Gran Turismo 4.** It has verified copies of the 350Z (coupe and roadster), the Ford GT (two entries) and the Mustang, and the most cars overall (730). By the name-based count MCLA led by one family (%d against %d); with the models, both hold all three finalists, and Jev preferred GT4 (0.90 against 0.06).\n" % (SHARED["MCLA"], SHARED["GT4"]))
    w("### Jev decision log\n")
    w(md_table(["Round", "Tool", "Question", "Outcome", "Use"], [list(j) for j in JEV]) + "\n")
    w("Jev saw text only (names, measured extents and my notes on what the renders showed), never the images. Several outcomes were low-confidence or contradicted one of the stated requirements; I decided with the truth table above and say so where I overrode the top probability.\n")
    w("## What is in this folder\n")
    w(md_table(["Path", "Contents"], [
        ["`README.md`", "This document."],
        ["`car-standardization-deck.pdf`", "Slide deck: selection evidence, per-car views and wheel sections, comparison tables, proposed standard."],
        ["`models/`", "Eight GLBs with their `.vehicle` descriptors (wheel pivots, radius, width, node-to-wheel bindings)."],
        ["`renders/<car>/`", "Ten renders per car under one rig (4 whole-car, 5 front-left wheel views) and a `wheel_profile.png`."],
        ["`compare/`", "Renders and mesh extents of every candidate copy, including unprepared previews, and the three comparison sheets."],
        ["`sources/`", "Seven unmodified preview GLBs fetched from the carmodels repo at the pinned commit, SHA-256-verified (`receipt.json`)."],
        ["`prepared/`", "Output of `prepare_gt4_vehicle.py` for GT4 Ford GT ford0006."],
        ["`slrr/`", "Static assemblies of SLRR Kurumma Z35C and Stallion 3.5 Turbo (.gltf plus part/provenance reports) from `slrr_assemble_generic.py`."],
        ["`data/`", "`analysis.json` (glTF inventory and wheel geometry) and `wheel_summary.json` (rim/tyre measurements, all four wheels)."],
        ["`tools/`", "The scripts that produced everything."]]) + "\n")
    w("## Findings from the wheels (350Z first)\n")
    w("- **Same car, five different wheel setups.** Across the five 350Z copies the tyre outer radius runs %s mm, the rim outer radius %s mm and the visible sidewall %s mm; the rim designs are all different (6-spoke, 5-spoke, multi-spoke, dark 5-spoke, chrome)." % (rng(rad350), rng(rim350), rng(sw350)))
    ov = ", ".join("%s %s mm" % (GAME[k], mm(v)) for k, v in overlaps.items() if v and v > 0.02)
    w("- **Rim and tyre do not meet cleanly in several games**: tyre inner radius inside the rim by %s; the other split-mesh cars meet within 3 mm." % ov)
    op = [GAME[k] + (" (traffic)" if "traffic" in k else "") + (" Ford GT" if k == ORDER[5] else "") for k in ORDER if OPEN[k]]
    w("- **Open tyres** (no inboard sidewall or bead): %s. Closed: %s." % (", ".join(op), ", ".join(GAME[k] + (" Ford GT" if k == ORDER[5] else "") for k in ORDER if OPEN[k] is False)))
    w("- **Ford Racing 2 is fused**: rim and tyre are one mesh with one material; the split here is a radius heuristic.")
    w("- **Nothing in any file says what a rim or tyre is**: wheel identity lives in the `.vehicle` sidecar (pivot, radius = tyre outer radius, width).")
    w("- **Materials are uniform factors** (GT4 0 / 0.7, MC3 0 / 0.6 …, Juiced 2 0.15 / 0.55, MCLA 0 / 0.7, Ford 0 / 1.0, SLRR 0 / 1.0) with per-game metadata and no metallic-roughness textures.")
    w("- **Only Juiced 2 has brake parts** (rolling disc, steering-only caliper carrier).\n")
    w("## Structure, materials and wheels (front-left)\n")
    rows = []
    for k in ORDER:
        r, s = AN[k], ST[k]
        rows.append([GAME[k] + (" Ford GT" if k == ORDER[5] else ""), CAR[k], "%d (%d in scene)" % (s["all_nodes"], s["scene_nodes"]), "{:,}".format(s["tris"]),
                     "%d / %d" % (s["textured"], r["counts"]["materials"]), r["counts"]["images"], ", ".join(r["extensionsUsed"]) or "none"])
    w(md_table(["Game", "Car", "Nodes", "Triangles", "Textured / total mats", "Images", "Extensions"], rows) + "\n")
    rows = []
    for k in ORDER:
        p, d = FL[k], DESC[k]["FL"]
        rows.append([GAME[k] + (" Ford GT" if k == ORDER[5] else ""), mm(d["radius"]), mm(d["width"]), mm(p["rim_outer_radius_m"]), mm(p["tire_inner_radius_m"]), mm(p["tire_outer_radius_m"]),
                     mm(p["sidewall_height_m"]), mm(p["tire_axial_width_m"]), "—" if p["tire_rim_radial_overlap_m"] is None else mm(p["tire_rim_radial_overlap_m"]),
                     "closed" if OPEN[k] is False else ("open" if OPEN[k] else "n/a"), p["rim_diameter_in"],
                     ", ".join("%s %s" % (a, "{:,}".format(b)) for a, b in p["verts"].items())])
    w(md_table(["Game", "Desc. radius mm", "Desc. width mm", "Rim outer mm", "Tyre inner mm", "Tyre outer mm", "Sidewall mm", "Tyre width mm", "Overlap mm", "Tyre shell", "Rim ⌀ in (mesh)", "Vertices"], rows) + "\n")
    w("'Rim ⌀' is twice the rim mesh's outer radius and not a recovered nominal rim size; the Ford GT row (fused mesh) uses a radius heuristic; tyre inner radius and overlap are not measurable there.\n")
    for k in ORDER:
        w("## %s — %s%s\n" % (GAME[k] + (" Ford GT" if k == ORDER[5] else ""), CAR[k], ""))
        w("`%s` · source `%s` · %s.\n" % (AN[k]["glb"], SRCID[k], STATUS[k]))
        w("![front 3/4](%s) ![side](%s)\n" % (rel(k, "car_front34"), rel(k, "car_side")))
        w("![rear 3/4](%s) ![top](%s)\n" % (rel(k, "car_rear34"), rel(k, "car_top")))
        w("**Wheel build:** " + WHEEL_HOW[k] + "\n")
        for f in CARS[k]:
            w("- " + f)
        w("")
        w("![context](%s) ![assembled](%s)\n" % (rel(k, "wheel_context"), rel(k, "wheel_assembled_34")))
        w("![rim only](%s) ![tyre only](%s)\n" % (rel(k, "wheel_rim_only"), rel(k, "wheel_tire_only")))
        w("![exploded](%s) ![profile](%s)\n" % (rel(k, "wheel_exploded"), rel(k, "wheel_profile")))
    w("## Proposed standard\n")
    w(md_table(["File", "Holds", "Key data"], [
        ["`<id>.car.glb`", "Body, glass, lights, interior; **no wheel geometry**", "Four `mount_FL/FR/RL/RR` empties at the hub centre (outboard = +X local; FL/RL rotated 180° about Y); `extras`: wheelbase, track, ride height, default rim/tyre spec per axle, arch clearance, provenance."],
        ["`<id>.rim.glb`", "Rim (barrel + face), origin on the hub mounting face, axle +X, metres", "diameter, width, offset (ET), bead-seat radius, hub bore, bolt pattern."],
        ["`<id>.tire.glb`", "One tyre on a normalised profile", "per-vertex profile coordinates (u across the tread −1..1, v from bead seat 0 to tread 1); tread and branding in textures."],
        ["`<id>.brake.glb` (optional)", "Disc (rolls) and caliper (steering carrier)", "mount offsets and barrel clearance."]]) + "\n")
    w("Tyre fitting: for rim diameter `D`, section width `w`, aspect `a`: sidewall `h = a·w`, bead radius `D/2`, outer radius `D/2 + h`; each vertex goes to radius `D/2 + v·h`, axial `u·w/2`. Three independent parameters are needed.\n")
    w("Why uniform scaling fails, measured on these cars (sidewall / width scale to put the row car's tyre on the column car's rim keeping the column car's outer radius, front-left; the fused Ford GT excluded):\n")
    head = ["Tyre from \\ rim of"] + [GAME[k] + (" Ford GT" if k == ORDER[5] else "") + (" (traffic)" if k == ORDER[3] else "") for k in split]
    rows = []
    for a, row in zip(split, matrix):
        rows.append([GAME[a] + (" Ford GT" if a == ORDER[5] else "") + (" (traffic)" if a == ORDER[3] else "")] + ["%.2f / %.2f" % (x, y) for x, y in row])
    w(md_table(head, rows) + "\n")
    w("Sidewall factors span %.2f–%.2f, so a single scale cannot fit tyres between cars, even between copies of the same 350Z.\n" % (min(mvals), max(mvals)))
    w("Materials: shared slot library on core glTF PBR plus clearcoat, alpha/transmission and emissive strength (`paint_body`, `paint_trim`, `chrome`, `glass_clear`, `glass_tint`, `rubber_tire`, `rim_alloy`, `rim_chrome`, `brake_disc`, `caliper_paint`, `plastic_black`, `lamp_head`, `lamp_tail`, `interior`); per-game mapping from `gt4_material`, MC3 `shader_category`, MCLA `sourceShader`, material names (Juiced 2, Ford) or texture path (SLRR).\n")
    w("## Migration plan\n")
    for i, t in enumerate(["Freeze the spec and write a validator (axes, units, node names, extras schema, rim/tyre seam, arch clearance).",
                           "Pilot on the GT4 350Z: it has separate rim/tyre nodes, a same-car copy in four other games and a ready roadster twin; normalise the rim, author its missing barrel, build the first normalised tyre.",
                           "Normalise the other 350Z rims (MC3, MCLA roadster and coupe, Juiced 2); keep each donor pair as that car's stock set. Then the Ford GT pair (GT4, Ford Racing 2 needs a manual split).",
                           "Strip wheels into `.car.glb` with mounts; re-run Racer's scale, clearance and containment checks.",
                           "Remap materials into slots per game; render every car with the reference rig and compare to golden images.",
                           "Engine: assemble rim + tyre per mount, resize tyres at load, add the wheel spec to the physics identity hash and saved-profile schema; garage wheel swap.",
                           "Extend to the remaining installed cars, then research candidates."], 1):
        w("%d. %s" % (i, t))
    w("")
    w("## Limits and open decisions\n")
    for t in ["Jev saw only text. The identity checks rely on renders and measured extents that I looked at; I did not run an automated shape comparison.",
              "Not verified: Juiced 2's Mustang GT 2005 (no extraction path for it), 68 of SLRR's 70 cars (only Kurumma Z35C and Stallion 3.5 Turbo were assembled and inspected; both static assemblies lack exhaust parts and the Stallion lost one part, so their sizes are approximate), whether any 350Z copy is a facelift (2007+) body, and the real trim/year of MC3's and Juiced 2's 350Z.",
              "GT4 Ford GT `ford0006` was prepared with the existing GT4 adapter for this kit only; it has no scale review and is not in Racer's catalog. The MCLA Ford GT 2006 and the Mustangs are viewed as unprepared previews, so their wheels are not measured.",
              "The MCLA traffic coupe is included for comparison only and is not installed or offered as a player car.",
              "Measurements come from prepared meshes (some Racer-authored fits); 'rim diameter' is derived from mesh radii.",
              "Renders use Blender's glTF importer under a studio rig, not Racer's renderer; Ford Racing 2's rim/tyre split is a radius heuristic.",
              "Decisions for you: nominal spec units (mm or inches); stock wheel sets per car file; whether to keep the traffic coupe in the kit; whether to assemble more SLRR cars (Jev saw no reason to, 0.01)."]:
        w("- " + t)
    w("")
    w("## Reproduce\n")
    w("```sh\ncd games/racer\nK=assets/local/car-standardization-kit-v2; S=experiments/2026-11-09-car-standardization/scripts\npython3 -I $S/fetch_previews.py <catalog.json> ce047799fc550cdf92e4f7b62d97ef5c603e53ad $K/sources <catalog-id>...\npython3 -I $S/analyze_glb.py $K/models $K/data/analysis.json\nsh $S/render_all.sh $PWD/$K          # Blender 5.2\npython3 -I $S/wheel_summary.py $K\npython3 -I $S/build_kit_docs_v2.py $K <scratch-dir>\n```\n")
    open(os.path.join(KIT, "README.md"), "w").write("\n".join(L))
    json.dump({"jev_model": "typesafe/jev-1.14-20261014", "decisions": [dict(zip(("round", "tool", "question", "outcome", "use"), j)) for j in JEV],
               "name_coverage": {f: sorted(g for g in GAMES if f in PRES[g]) for f in FAMS}, "copies_examined": [list(c) for c in COPIES]},
              open(os.path.join(KIT, "data", "selection-evidence.json"), "w"), indent=1)


# ------------------------------------------------------------------ deck
IMG = os.path.join(SCRATCH, "deck_img_v2")
os.makedirs(IMG, exist_ok=True)


def jpg(path, width, tag):
    out = os.path.join(IMG, "%s_%d.jpg" % (tag, width))
    im = Image.open(path).convert("RGB")
    im = im.resize((width, int(im.height * width / im.width)), Image.LANCZOS)
    im.save(out, quality=88)
    return out


def rj(car, name, width):
    return jpg(os.path.join(KIT, rel(car, name)), width, car + "__" + name)


E = html.escape


def md_inline(t):
    import re
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", E(t))


CSS = """
@page { size: 1280px 720px; margin: 0 }
* { box-sizing: border-box }
body { margin: 0; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; color: #1b1f24; font-size: 19px; line-height: 1.4 }
.slide { width: 1280px; height: 720px; page-break-after: always; overflow: hidden; position: relative; background: #fff }
.hd { height: 82px; background: #14202e; color: #fff; padding: 16px 44px 0 44px }
.hd .kick { font-size: 13px; letter-spacing: 2px; text-transform: uppercase; color: #8fb4d9 }
.hd h2 { margin: 2px 0 0 0; font-size: 28px; font-weight: 700 }
.bd { padding: 18px 44px 0 44px }
.ft { position: absolute; bottom: 10px; left: 44px; right: 44px; font-size: 11px; color: #6b7785; display: flex; justify-content: space-between }
table { border-collapse: collapse; width: 100%; font-size: 15px }
th { background: #eaf0f6; text-align: left; padding: 5px 7px; border-bottom: 2px solid #b9c7d6 }
td { padding: 4px 7px; border-bottom: 1px solid #dde4ec; vertical-align: top }
code { background: #eef1f5; padding: 0 4px; border-radius: 3px; font-size: 0.9em }
ul { margin: 6px 0; padding-left: 22px } li { margin: 4px 0 }
.cols { display: flex; gap: 26px } .cols > div { flex: 1 }
.g2 { display: grid; grid-template-columns: 1fr 1fr; gap: 10px } .g3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px }
.g2 img, .g3 img { width: 100%; display: block; border: 1px solid #cfd8e2 }
.cap { font-size: 12px; color: #5b6673; margin-top: 2px }
.big { font-size: 50px; font-weight: 800; line-height: 1.05 } .sub { font-size: 21px; color: #cfdceb }
.pill { display: inline-block; background: #e8f1fb; border: 1px solid #b6cfe8; border-radius: 12px; padding: 1px 10px; font-size: 13px; margin-right: 6px }
.box { border: 1px solid #c9d4e0; border-radius: 6px; padding: 10px 14px; background: #f7f9fc }
.kv { font-size: 16px } .bad { color: #b3261e; font-weight: 700 } .ok { color: #1f7a3d; font-weight: 700 }
.dia { display: flex; gap: 14px; align-items: stretch } .dia .n { flex: 1; border: 2px solid #2b4a6b; border-radius: 8px; padding: 10px; background: #f2f7fc; font-size: 16px }
.dia .n h4 { margin: 0 0 6px 0; font-size: 18px; color: #14202e } .arrow { align-self: center; font-size: 28px; color: #2b4a6b }
"""
SL = []


def slide(kick, title, body):
    SL.append('<section class="slide"><div class="hd"><div class="kick">%s</div><h2>%s</h2></div><div class="bd">%s</div>'
              '<div class="ft"><span>Car &amp; wheel standardization kit v2 &middot; Racer</span><span>%d</span></div></section>' % (E(kick), E(title), body, len(SL) + 1))


def table(head, rows, style=""):
    return '<table style="%s"><tr>%s</tr>%s</table>' % (style, "".join("<th>%s</th>" % E(str(h)) for h in head),
                                                       "".join("<tr>%s</tr>" % "".join("<td>%s</td>" % c for c in r) for r in rows))


def lab(k):
    return GAME[k] + (" Ford GT" if k == ORDER[5] else "")


def build_deck():
    SL.append('<section class="slide" style="background:#14202e;color:#fff"><div style="padding:140px 80px"><div style="color:#8fb4d9;letter-spacing:3px;text-transform:uppercase;font-size:15px">Racer &middot; asset standardization &middot; v2</div>'
              '<div class="big" style="margin-top:14px">One car across the games.<br>Rims and tyres that fit anything.</div>'
              '<div class="sub" style="margin-top:30px">The Nissan 350Z in four games, the Ford GT standing in for Ford Racing 2 &mdash; chosen by looking at the models, not the names.</div>'
              '<div style="margin-top:56px;color:#8fb4d9;font-size:16px">GT4 &middot; MC3 &middot; MCLA &middot; Juiced 2 &middot; Ford Racing 2 &middot; SLRR<br>One Blender rig &middot; exact mesh geometry &middot; Jev decision log</div></div></section>')
    slide("Selection", "What changed from v1",
          '<div class="cols"><div><ul><li><b>v1:</b> one unrelated car per game, so differences mixed car and game.</li><li><b>v2:</b> the same car wherever the models show it.</li>'
          '<li>No car is in every game. The 350Z is in four (GT4, MC3, MCLA, Juiced 2); Ford Racing 2 and SLRR lack it.</li><li>Ford Racing 2 gets the <b>Ford GT</b>, a mesh-identical car in GT4 and MCLA; GT4 is the bridge game.</li><li>SLRR stays unmatched.</li></ul></div>'
          '<div class="box kv"><b>Rule you gave</b><ul><li>A car in all games; if not, the odd game out gets another matching candidate.</li><li>Bridge game = the one with the most cars in common.</li><li>Do not trust names; years matter; look at the models.</li><li>Jev for every decision.</li></ul>'
          '<p><b>What happened:</b> name matching picked a 1973 Mach 1 for Ford Racing 2. The models showed it is a different generation, so that pick was dropped.</p></div></div>')
    top = [f for f, c in sorted(COUNT.items(), key=lambda x: -x[1]) if c >= 4]
    rows = [[E(f)] + ["&#10003;" if f in PRES[g] else "" for g in GAMES] + [COUNT[f]] for f in FAMS if COUNT[f] >= 3]
    slide("Selection", "Step 1: coverage by name (Jev verify over each game's car list)",
          '<div class="cols"><div>' + table(["Family"] + GAMES + ["Games"], rows, "font-size:13px") + '</div><div><ul class="kv"><li>21 families tested against 5 games with real cars (SLRR has only fictional brands).</li>'
          '<li>Widest coverage: 4 of 5 for %d families; none is in all 5.</li><li>Ford Racing 2 only shares Mustang, Ford GT and Focus with the others.</li><li>Names are weak evidence: MC3 and FR2 have no years, MCLA and GT4 sometimes do.</li></ul></div></div>' % len(top))
    slide("Selection", "Step 2: look at the models. 350Z copies",
          '<img src="%s" style="width:520px;display:block;margin:0 auto"><div class="cap" style="text-align:center">same rig for every row; front 3/4, rear 3/4, side</div>' % jpg(os.path.join(CMP, "sheet_350z.png"), 1500, "sheet350"))
    rows = [[a, b, "<code>%s</code>" % E(c), E(d), E(e), ("%.2f" % f_) if f_ else "&mdash;", E(g)] for a, b, c, d, e, f_, g in COPIES if a == "350Z"]
    slide("Selection", "350Z: one car, but MCLA's player copy is a convertible",
          table(["Family", "Game", "Source", "Name / year in source", "Body seen", "Length m", "Verdict"], rows) +
          '<ul style="margin-top:14px"><li>All six copies are the Z33 and agree within 1% in length (4.30&ndash;4.34 m).</li><li>MCLA&rsquo;s only allowed copy is a <b>roadster</b>; its coupe is traffic-only and never becomes a player car, so it is kept as a labelled reference.</li>'
          '<li>Juiced 2&rsquo;s car is the same platform with tuner styling.</li></ul>')
    slide("Selection", "Step 2: look at the models. Mustang generations",
          '<img src="%s" style="width:590px;display:block;margin:0 auto"><div class="cap" style="text-align:center">FR2 ships a 1973 Mach 1 and a 1968 fastback as playable Mustangs; GT4 and MCLA have the 2005 car. A name match would have paired them.</div>' % jpg(os.path.join(CMP, "sheet_mustang.png"), 1500, "sheetmust"))
    slide("Selection", "Step 2: look at the models. Ford GT",
          '<img src="%s" style="width:640px;display:block;margin:0 auto"><div class="cap" style="text-align:center">Same production Ford GT in Ford Racing 2, GT4 (two entries) and MCLA (2006 GT); mesh lengths 4.62, 4.62, 4.64 m</div>' % jpg(os.path.join(CMP, "sheet_ford_gt.png"), 1500, "sheetgt"))
    rows = [[a, b, "<code>%s</code>" % E(c), E(d), E(e), ("%.2f" % f_) if f_ else "&mdash;", E(g)] for a, b, c, d, e, f_, g in COPIES if a not in ("350Z", "SLRR")]
    slide("Selection", "Mustang and Ford GT copies compared",
          table(["Family", "Game", "Source", "Name / year in source", "Body seen", "Length m", "Verdict"], rows, "font-size:14px"))
    slide("Selection", "SLRR: two candidates assembled and inspected",
          '<img src="%s" style="width:600px;float:left;margin-right:24px"><ul class="kv"><li><b>Kurumma Z35C</b>: 4.50 m long (350Z copies 4.30&ndash;4.34 m); fastback with split rear lights, nothing like the 350Z&rsquo;s round tail lamps. In-game text: a year-2000 racing Kurumma Z3, before the real Z33.</li>'
          '<li><b>Stallion 3.5 Turbo</b>: 3.97 m long against 4.80&ndash;4.82 m for the 2005 Mustang copies.</li>'
          '<li>Jev: Z35C is a 350Z, contradicted 0.98; Stallion is a 2005 Mustang, contradicted 0.92; decision <b>no match</b> 0.98.</li>'
          '<li>Assembled from SLRR&rsquo;s own CFG/RPK files (29 and 33 parts) without exhausts; the Stallion lost one part. 68 other SLRR cars not inspected.</li></ul>' % jpg(os.path.join(CMP, "sheet_slrr.png"), 1500, "sheetslrr"))
    slide("Selection", "Truth table and final picks",
          table(["Game", "350Z?", "Kit entry", "Why"], [
              ["GT4 (bridge)", "yes, coupe '03", "350Z coupe", "also has Ford GT and a roadster twin: links both groups"],
              ["MC3", "yes, coupe", "350Z", "&mdash;"], ["MCLA", "roadster '06; coupe '04 (traffic)", "roadster + traffic coupe (reference)", "body style differs; coupe never installed"],
              ["Juiced 2", "yes, tuner body", "350Z", "same platform"], ["Ford Racing 2", "no", "Ford GT", "mesh-identical to GT4 and MCLA copies"], ["SLRR", "no", "Furrano (unmatched)", "Kurumma Z35C and Stallion inspected: no match"]]) +
          '<p class="kv" style="margin-top:12px"><b>Bridge game: GT4.</b> Verified copies of 350Z, Ford GT and Mustang, 730 cars. By name count MCLA led by one family (%d vs %d); Jev preferred GT4 0.90 to 0.06.</p>' % (SHARED["MCLA"], SHARED["GT4"]))
    slide("Selection", "Jev decision log",
          table(["Round", "Question", "Outcome", "Use"], [[E(a), E(c), E(d), E(e)] for a, b, c, d, e in JEV], "font-size:11.5px") +
          '<div class="cap" style="margin-top:6px">Jev saw text only (names, measured extents, my notes on the renders). Where its top pick contradicted a requirement I applied the truth table and said so.</div>')
    slide("Kit", "The eight cars", table(["#", "Game", "Car", "Source", "Status"], [[i + 1, E(lab(k)), E(CAR[k]), "<code>%s</code>" % E(SRCID[k]), E(STATUS[k])] for i, k in enumerate(ORDER)]) +
          '<p class="kv" style="margin-top:12px">Group A: the 350Z. Group B: the Ford GT pair (Ford Racing 2 stand-in plus its GT4 bridge copy). Group C: SLRR unmatched.</p>')
    rows = []
    for k in ORDER:
        r, s = AN[k], ST[k]
        rows.append([E(lab(k)), "%d <span class='cap'>(%d)</span>" % (s["all_nodes"], s["scene_nodes"]), "{:,}".format(s["tris"]), "%d / %d" % (s["textured"], r["counts"]["materials"]),
                     "%d <span class='cap'>max %dx%d</span>" % (r["counts"]["images"], *s["maxtex"]), E(", ".join(r["extensionsUsed"]) or "none"),
                     "/".join("%g" % x for x in s["metallic"]) + " / " + "/".join("%g" % x for x in s["rough"])])
    slide("Comparison", "Structure and materials", table(["Game", "Nodes (in scene)", "Triangles", "Textured / mats", "Images", "Extensions", "Metallic / rough"], rows) +
          '<p class="kv" style="margin-top:10px">Every car has one metallic/roughness pair and no metallic-roughness texture; useful material meaning sits in per-game metadata.</p>')
    rows = []
    for k in ORDER:
        p, d = FL[k], DESC[k]["FL"]
        ov = p["tire_rim_radial_overlap_m"]
        rows.append([E(lab(k)), mm(d["radius"]), mm(d["width"]), mm(p["rim_outer_radius_m"]), mm(p["tire_inner_radius_m"]), mm(p["tire_outer_radius_m"]), mm(p["sidewall_height_m"]), mm(p["tire_axial_width_m"]),
                     "&mdash;" if ov is None else ("<span class='bad'>%s</span>" % mm(ov) if ov > 0.02 else mm(ov)), "closed" if OPEN[k] is False else ("open" if OPEN[k] else "n/a")])
    slide("Wheels", "Wheel measurements, front-left (mm)", table(["Game", "Desc. radius", "Desc. width", "Rim outer", "Tyre inner", "Tyre outer", "Sidewall", "Tyre width", "Overlap", "Tyre shell"], rows) +
          '<p class="kv" style="margin-top:10px"><b>Same 350Z, different wheels:</b> tyre outer radius %s mm, rim outer radius %s mm, sidewall %s mm across the five copies. Overlap = rim outer radius &minus; tyre inner radius (red &gt; 20 mm). Ford GT row is a fused mesh (heuristic split).</p>' % (rng(rad350), rng(rim350), rng(sw350)))
    imgs = "".join('<div><img src="%s"><div class="cap">%s</div></div>' % (rj(k, "wheel_profile", 520), E(lab(k) + " " + CAR[k])) for k in ORDER)
    slide("Wheels", "Axial / radial profiles of the eight front-left wheels",
          '<div class="g3" style="width:960px;margin:0 auto">%s</div><div class="cap" style="text-align:center">Tyre shading = convex hull of tyre vertices; a hull that stops short of the inboard side means the tyre has no inboard sidewall.</div>' % imgs)
    for k in ORDER:
        s = ST[k]
        meta = ('<span class="pill">%s</span><span class="pill">%d nodes</span><span class="pill">%s tris</span><span class="pill">%d materials</span><span class="pill">%d images</span>' %
                (E(AN[k]["glb"][:60]), s["all_nodes"], "{:,}".format(s["tris"]), AN[k]["counts"]["materials"], AN[k]["counts"]["images"]))
        views = "".join('<div><img src="%s"><div class="cap">%s</div></div>' % (rj(k, n, 760), t) for n, t in (("car_front34", "front 3/4"), ("car_side", "side"), ("car_rear34", "rear 3/4"), ("car_top", "top")))
        slide(lab(k), CAR[k] + ": the car", '<div style="margin-bottom:8px">%s</div><div class="g2" style="width:900px;margin:0 auto">%s</div>' % (meta, views))
        wimgs = "".join('<div><img src="%s"><div class="cap">%s</div></div>' % (rj(k, n, 560), t) for n, t in
                        (("wheel_context", "in context"), ("wheel_assembled_34", "assembled"), ("wheel_exploded", "exploded along the axle"),
                         ("wheel_rim_only", "rim only"), ("wheel_tire_only", "tyre only"), ("wheel_profile", "axial / radial profile")))
        p = FL[k]
        strip = "tyre &Oslash; %s mm &middot; width %s mm &middot; sidewall %s mm &middot; rim outer %s mm &middot; overlap %s" % (
            mm((p["tire_outer_radius_m"] or 0) * 2), mm(p["tire_axial_width_m"]), mm(p["sidewall_height_m"]), mm(p["rim_outer_radius_m"]),
            "n/a (fused)" if p["tire_rim_radial_overlap_m"] is None else mm(p["tire_rim_radial_overlap_m"]) + " mm")
        slide(lab(k), CAR[k] + ": wheel sections", '<div class="g3" style="width:1010px;margin:0 auto">%s</div><div class="kv" style="margin-top:8px;text-align:center">%s</div>' % (wimgs, strip))
        facts = "".join("<li>%s</li>" % md_inline(f) for f in CARS[k])
        slide(lab(k), CAR[k] + ": how its wheel is built",
              '<div class="cols"><div><div class="box"><b>Structure.</b> %s</div><ul style="margin-top:10px;font-size:17px">%s</ul></div>'
              '<div style="flex:0 0 400px"><img src="%s" style="width:100%%;border:1px solid #cfd8e2"><div class="cap">front-left profile</div></div></div>' % (md_inline(WHEEL_HOW[k]), facts, rj(k, "wheel_profile", 560)))
    slide("Analysis", "What blocks interchangeable wheels",
          '<ul><li><b>No rim or tyre data:</b> diameter, width, offset, bead radius and tyre spec are stored nowhere; only the tyre outer radius and width, in the sidecar.</li>'
          '<li><b>Same car, different wheels:</b> tyre outer radius %s mm, rim outer radius %s mm, sidewall %s mm across five 350Z copies.</li>'
          '<li><b>No seam contract:</b> overlaps of %s mm in the games that overlap, 0 where they meet.</li>'
          '<li><b>Open tyres</b> in GT4, MC3 and Ford: no inboard sidewall or bead, so they cannot move as-is.</li><li><b>Fused wheels</b> in Ford Racing 2.</li>'
          '<li><b>Shared-nothing materials</b> and per-game metadata; <b>brakes</b> only in Juiced 2.</li></ul>' % (rng(rad350), rng(rim350), rng(sw350), ", ".join(mm(v) for v in overlaps.values() if v and v > 0.02)))
    slide("Proposal", "Target file architecture",
          '<div class="dia"><div class="n"><h4>&lt;id&gt;.car.glb</h4>Body, glass, lights, interior. <b>No wheels.</b><br><br>Four <code>mount_FL/FR/RL/RR</code> empties at the hub centre.<br><br><code>extras</code>: wheelbase, track, ride height, default rim/tyre spec, arch clearance, provenance.</div>'
          '<div class="arrow">+</div><div class="n"><h4>&lt;id&gt;.rim.glb</h4>Barrel + face, origin on the mounting face, axle +X, metres.<br><br>diameter, width, offset, bead radius, hub bore, bolt pattern.</div>'
          '<div class="arrow">+</div><div class="n"><h4>&lt;id&gt;.tire.glb</h4>Normalised profile with per-vertex (u, v); tread and branding in textures.</div>'
          '<div class="arrow">+</div><div class="n"><h4>&lt;id&gt;.brake.glb</h4>Optional: rolling disc and steering caliper.</div></div>'
          '<div class="box" style="margin-top:16px"><b>Stock sets.</b> Each donor car keeps its own rim + tyre as the stock set, so converting a car never loses its look.</div>')
    slide("Proposal", "Tyre fitting: three independent parameters",
          '<div class="cols"><div><p>For rim diameter <b>D</b>, section width <b>w</b>, aspect <b>a</b>:</p><ul><li>sidewall <b>h = a &middot; w</b></li><li>bead radius <b>D / 2</b></li><li>outer radius <b>D / 2 + h</b></li></ul>'
          '<div class="box"><code>radius = D/2 + v &middot; h</code><br><code>axial = u &middot; w / 2</code></div><p style="margin-top:10px">Tread vertices stay at v = 1; pattern and branding are textures.</p></div>'
          '<div><p><b>Why one scale is not enough.</b></p><ul><li>Visible sidewall across the cars: %s mm.</li><li>Rim outer radius: %s mm.</li><li>Tyre width: %s mm.</li></ul><p>Bead radius, sidewall and width must vary independently.</p></div></div>' %
          (rng([sw(k) for k in split]), rng([FL[k]["rim_outer_radius_m"] for k in split]), rng([wd(k) for k in split])))
    head = ["Row tyre on column rim"] + [GAME[k] + (" GT" if k == ORDER[5] else "") + (" (tr.)" if k == ORDER[3] else "") for k in split]
    rows = []
    for a, row in zip(split, matrix):
        cells = ["<span class='%s'>%.2f</span> / %.2f" % ("bad" if (x < 0.6 or x > 1.6) else "", x, y) for x, y in row]
        rows.append([GAME[a] + (" GT" if a == ORDER[5] else "") + (" (tr.)" if a == ORDER[3] else "")] + cells)
    slide("Proposal", "Retargeting matrix: sidewall / width scale needed",
          table(head, rows, "font-size:13px") + '<p class="kv" style="margin-top:10px">Row car&rsquo;s tyre on the column car&rsquo;s rim, keeping the column car&rsquo;s outer radius (front-left; fused Ford GT excluded). Red = outside 0.6&ndash;1.6. Range %.2f&ndash;%.2f, even between copies of the same 350Z.</p>' % (min(mvals), max(mvals)))
    slide("Proposal", "One material and lighting model",
          '<div class="cols"><div><p><b>Slot library</b> on core glTF PBR plus clearcoat, alpha/transmission and emissive strength:</p><p><span class="pill">paint_body</span><span class="pill">paint_trim</span><span class="pill">chrome</span><span class="pill">glass_clear</span><span class="pill">glass_tint</span><span class="pill">rubber_tire</span><span class="pill">rim_alloy</span><span class="pill">rim_chrome</span><span class="pill">brake_disc</span><span class="pill">caliper_paint</span><span class="pill">plastic_black</span><span class="pill">lamp_head</span><span class="pill">lamp_tail</span><span class="pill">interior</span></p>'
          '<p>Each primitive carries <code>extras.racer_material_slot</code>; one engine-side environment for every scene.</p></div><div>' +
          table(["Game", "Slot mapping source"], [["GT4", "<code>gt4_material</code> + alpha mode"], ["MC3", "<code>shader_category</code>"], ["MCLA", "<code>sourceShader</code>"], ["Juiced 2", "material names"], ["Ford", "material names"], ["SLRR", "texture path / hash"]]) + '</div></div>')
    steps = ["Freeze the spec; write a validator.", "Pilot on the GT4 350Z (separate rim/tyre nodes, same-car copies in four other games, roadster twin): normalise the rim, author the barrel, build the first normalised tyre.",
             "Normalise the other 350Z rims (MC3, MCLA roadster and coupe, Juiced 2); keep each donor pair as the stock set; then the Ford GT pair.", "Strip wheels into <code>.car.glb</code> with mounts; re-run Racer&rsquo;s scale, clearance and containment checks.",
             "Remap materials into slots per game; golden-image comparison under the reference rig.", "Engine: assemble rim + tyre per mount, resize at load, wheel spec in the physics identity hash and saved profile; garage wheel swap.", "Extend to the other installed cars."]
    slide("Plan", "Migration plan", "<ol>%s</ol>" % "".join("<li style='margin:7px 0'>%s</li>" % s for s in steps))
    slide("Plan", "Limits and decisions needed",
          '<div class="cols"><div><h3 style="margin:0 0 4px 0">Limits</h3><ul class="kv"><li>Jev saw text only; identity checks rely on renders and extents I looked at, not an automated shape comparison.</li><li>Not verified: Juiced 2 Mustang, 68 of 70 SLRR cars, facelift status of the 350Zs, real year of MC3 and Juiced 2.</li>'
          '<li>GT4 Ford GT was prepared for this kit only; no scale review, not in Racer&rsquo;s catalog.</li><li>MCLA traffic coupe is a comparison reference, never installed.</li><li>Rim &lsquo;diameter&rsquo; derives from mesh radii; renders are Blender, not Racer.</li></ul></div>'
          '<div><h3 style="margin:0 0 4px 0">Decisions for you</h3><ul class="kv"><li>Spec units: mm or inches.</li><li>Default stock wheel set inside each car file?</li><li>Keep the traffic coupe in the kit?</li><li>Assemble more SLRR cars? (Jev: no match among the two tried; no reason to expand, 0.01.)</li></ul></div></div>')
    doc = "<!doctype html><html><head><meta charset='utf-8'><style>%s</style></head><body>%s</body></html>" % (CSS, "".join(SL))
    hp = os.path.join(SCRATCH, "deck_v2.html")
    open(hp, "w").write(doc)
    pdf = os.path.join(KIT, "car-standardization-deck.pdf")
    chrome = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    subprocess.run([chrome, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--allow-file-access-from-files",
                    "--print-to-pdf=" + pdf, "file://" + hp], check=True, capture_output=True)
    print("slides:", len(SL), "pdf bytes:", os.path.getsize(pdf))


build_readme()
build_deck()
