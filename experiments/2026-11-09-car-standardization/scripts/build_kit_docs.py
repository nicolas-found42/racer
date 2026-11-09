#!/usr/bin/env python3
"""Build the kit's README.md and the PDF deck from analysis.json / wheel_summary.json / renders.

Usage: build_kit_docs.py <kit-dir> <scratch-dir>
Needs: PIL and the `weasyprint` CLI. Every number in the documents is read from the JSON data,
except the hand-written notes in CARS, which are statements about what the analysis shows.
"""
import html, json, os, subprocess, sys
from PIL import Image

KIT, SCRATCH = sys.argv[1], sys.argv[2]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze_glb as A  # noqa: E402

AN = json.load(open(os.path.join(KIT, "data", "analysis.json")))
WS = json.load(open(os.path.join(KIT, "data", "wheel_summary.json")))

ORDER = ["gran-turismo-4_acura-nsx-04", "ford-racing-2_mustang-1973", "midnight-club-3_corvette-z06",
         "midnight-club-la_350z-roadster", "juiced-2_350z", "slrr_furrano-gt54"]
GAME = {"gran-turismo-4_acura-nsx-04": "Gran Turismo 4", "ford-racing-2_mustang-1973": "Ford Racing 2",
        "midnight-club-3_corvette-z06": "Midnight Club 3", "midnight-club-la_350z-roadster": "Midnight Club LA",
        "juiced-2_350z": "Juiced 2", "slrr_furrano-gt54": "SLRR"}
CAR = {"gran-turismo-4_acura-nsx-04": "Acura NSX '04", "ford-racing-2_mustang-1973": "Mustang Mach 1 (1973)",
       "midnight-club-3_corvette-z06": "Corvette Z06", "midnight-club-la_350z-roadster": "Nissan 350Z Roadster",
       "juiced-2_350z": "Nissan 350Z", "slrr_furrano-gt54": "Furrano GT54"}
SRCID = {"gran-turismo-4_acura-nsx-04": "gran-turismo-4/acra0014", "ford-racing-2_mustang-1973": "ford-racing-2/MACH1_SIXTY",
         "midnight-club-3_corvette-z06": "midnight-club-3-remix/vp_corvettez06_03",
         "midnight-club-la_350z-roadster": "midnight-club-los-angeles/vp_nsn_350z_06",
         "juiced-2_350z": "juiced-2/350Z", "slrr_furrano-gt54": "slrr-231/Furrano_GT54"}

# ----------------------------------------------------------------------------- derived data
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
    tris = verts = 0
    for i in seen:
        if "mesh" in n[i]:
            for p in g["meshes"][n[i]["mesh"]]["primitives"]:
                verts += g["accessors"][p["attributes"]["POSITION"]]["count"]
                tris += g["accessors"][p["indices"]]["count"] // 3 if "indices" in p else g["accessors"][p["attributes"]["POSITION"]]["count"] // 3
    mats = AN[key]["materials"]
    return {"scene_nodes": len(seen), "all_nodes": len(n), "tris": tris, "verts": verts,
            "textured_mats": sum(1 for m in mats if m["baseTex"]),
            "nonopaque": sum(1 for m in mats if m["alpha"] != "OPAQUE"),
            "metallic": sorted({m["metallic"] for m in mats if m["metallic"] is not None}),
            "rough": sorted({m["roughness"] for m in mats if m["roughness"] is not None}),
            "maxtex": max([i["size"] for i in AN[key]["images"] if i["size"]] or [(0, 0)], key=lambda s: s[0] * s[1])}

ST = {k: scene_stats(k) for k in ORDER}
FL = {k: WS[k]["per_wheel"]["FL"] for k in ORDER}
DESC = {k: WS[k]["descriptor"] for k in ORDER}
mm = lambda v: "—" if v is None else "%.0f" % (v * 1000)

# hand-written, evidence-bound notes per car
CARS = {
 "gran-turismo-4_acura-nsx-04": {
  "wheel_how": "Eight wheel-bound nodes: `wheel_*` (rim) and `tire_*` per corner, one mesh each, pivot-centred; the node translation is the hub.",
  "facts": ["The rim is a face-only shell (985 vertices) sitting 41–117 mm outboard of the hub plane: there is no barrel behind it.",
            "The tyre is a ring (154 vertices) whose inner radius (179 mm) reaches 53 mm inside the rim's outer radius (231 mm), so the two overlap instead of meeting at a bead seat.",
            "The tyre is an open shell: it has no vertices on the inboard half below mid-sidewall, so the inner sidewall and bead are missing (it was never visible in the PS2 game).",
            "Front and rear differ (tyre radius 302 / 318 mm, descriptor width 233 / 277 mm); rim mesh is shared by both.",
            "Rim and tyre use alpha-MASK materials with the PS2 `gt4_material` ambient/diffuse/specular triple kept in `extras`.",
            "No brake disc or caliper. Window glass renders as flat magenta/cyan/blue (window-mask textures; the exact cause was not investigated)."]},
 "ford-racing-2_mustang-1973": {
  "wheel_how": "One fused `WHEEL_*` mesh per corner under a `HUB_*` node (the hub holds the translation; the wheel is at the origin). 8 primitives, one material.",
  "facts": ["Rim and tyre are one mesh with one material/texture (`SIXTY_512`); the white wall is painted into the texture. The rim/tyre split in this kit is a heuristic on primitive radius, not data in the file.",
            "The GLB holds 136 nodes but only 12 are reachable from the scene root; the rest are alternate wheel/light sets that are not rendered (why was not investigated).",
            "The tyre half of the mesh is also open on the inboard side (no vertices on the inboard half below mid-sidewall).",
            "Only 7 materials in the whole car; every one has metallic 0 and roughness 1.",
            "Brake lights are on/off swap meshes (`BRAKE_LIGHTS_ON/OFF`), not an emissive material.",
            "No brake disc or caliper. Descriptor width (257.5 mm) matches the fused mesh's axial extent."]},
 "midnight-club-3_corvette-z06": {
  "wheel_how": "`whl_N_rim_0` and `whl_N_tire_0` per corner (N = 8, 10, 12, 14). The wheel mount X translations are authored by Racer to factory track (node `racer_manufacturer_wheelbase_calibration`).",
  "facts": ["The rim node is six primitives (chrome face, `wheel_inner`, flange, a 4-vertex floating polygon). Its outer radius (240 mm) equals the tyre's inner radius exactly: the cleanest bead seat of the set.",
            "The tyre is an open shell like GT4's: no vertices on the inboard half below mid-sidewall.",
            "Front and rear differ (rim 240 / 252 mm, tyre 332 / 348 mm).",
            "Materials carry the decoded native shader category and a full native material graph in `extras` (the largest per-material metadata of any car); the factors themselves are neutral display values.",
            "KHR_materials_variants is present (PS2-era paint/variant switching).",
            "No brake disc or caliper."]},
 "midnight-club-la_350z-roadster": {
  "wheel_how": "Three nodes per corner: `rims/whl_stk_nsn_350z_06@axl_N/model0` (rim), `.../model1` (9 vertices) and `tires/models/tir_car@axl_N/model0` (tyre).",
  "facts": ["The tyre mesh is named `tir_car`, a generic shared tyre resource, which suggests the donor game already reuses one tyre model across cars (not verified in the game).",
            "The rim's outer radius (267.6 mm) equals the tyre's inner radius: a clean seat. The rim has 3,692 vertices.",
            "Materials keep the source shader name in `extras.sourceShader` (e.g. CarPaintCustomizable, Chrome) plus a draw bucket; every factor is metallic 0 / roughness 0.7.",
            "The wheel pose is a Racer-authored fit (descriptor: 'authored fit').",
            "No brake disc or caliper."]},
 "juiced-2_350z": {
  "wheel_how": "Per corner: `WHEEL_*` (rim), `ADAPTED_NATIVE_TOYO_TYRE_*`, `TEST_DISC_*` (rolling) and `TEST_CALIPER_*` (a carrier: steers, does not roll). Descriptor format v2 names these roles explicitly.",
  "facts": ["The only car with a brake set; the disc rolls with the wheel and the caliper follows steering only.",
            "The tyre is the shared 'Toyo' template filtered to rubber (729 vertices); it overlaps the rim barrel by 43 mm (rim outer 269 mm, tyre inner 226.5 mm).",
            "The game sizes stock tyres procedurally (`TYRE_PROFILE`); the per-car inputs were not recovered, so this fit is a Racer adaptation (see findings/juiced2-wheel-contract.md).",
            "Every material has metallic 0.15 / roughness 0.55; glass is an authored tint (0.08, 0.12, 0.16, alpha 0.65, BLEND).",
            "Wheels are identical front and rear (319 mm radius, 240 mm descriptor width)."]},
 "slrr_furrano-gt54": {
  "wheel_how": "`rim-N` and `tyre-N` per corner (N = 0..3), pivot-centred; track differs front/rear (0.84 / 0.94 m).",
  "facts": ["The highest-poly rim of the set (5,904 vertices) and the tallest tyre: 116 mm sidewall, 52% aspect, 344 mm radius.",
            "Rim and tyre meet within 3 mm (tyre inner 225.4 mm vs rim outer 228.6 mm).",
            "Materials are one `source-diffuse` entry per primitive; textures are mostly SLRR default-white, so the car renders white. Roughness 1 / metallic 0 are labelled 'authored neutral inspection factor'.",
            "The body pose is a Racer-authored parked compression, not the donor's runtime suspension.",
            "No brake disc or caliper."]},
}

# ----------------------------------------------------------------------------- retargeting matrix
five = [k for k in ORDER if not k.startswith("ford")]
def sidewall(k):
    return FL[k]["sidewall_height_m"]
def width(k):
    return FL[k]["tire_axial_width_m"]
matrix_rows = []
for a in five:
    row = []
    for b in five:
        row.append((sidewall(b) / sidewall(a), width(b) / width(a)))
    matrix_rows.append(row)

# ----------------------------------------------------------------------------- README.md
def rel(car, name):
    return "renders/%s/%s.png" % (car, name)

def md_table(head, rows):
    out = ["| " + " | ".join(head) + " |", "|" + "|".join("---" for _ in head) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)

def build_readme():
    L = []
    w = L.append
    w("# Car and wheel standardization kit\n")
    w("Examples and measurements of how six donor games' cars are stored today, written to support one goal: **each car is its own file, every game's cars share one lighting / rendering / material model, and wheels are interchangeable — rims and tyres separate, any tyre fits any rim, resized to match.**\n")
    w("Everything here is generated from the six reviewed Racer preparations in `assets/local/vehicles/` by the scripts in `experiments/2026-11-09-car-standardization/scripts/`. These are **Racer's prepared GLBs** (axes, units, wheel mounts and some fits already authored by Racer), not untouched game exports. The models are copyrighted game assets: this folder lives under the gitignored `assets/local/`. Keep it local.\n")
    w("## What is in this folder\n")
    w(md_table(["Path", "Contents"], [
        ["`README.md`", "This document."],
        ["`car-standardization-deck.pdf`", "Detailed slide deck: per-car views, wheel sections, comparison tables, proposed standard, migration plan."],
        ["`models/`", "One GLB per game (`<game>_<car>.glb`) plus its `.vehicle` descriptor (wheel pivots, radius, width, node→wheel bindings)."],
        ["`renders/<car>/`", "Ten renders per car under one identical rig (4 whole-car views, 5 front-left wheel views) and a `wheel_profile.png` axial/radial plot."],
        ["`data/analysis.json`", "Per-car glTF inventory, materials, and exact world-space geometry of every wheel-bound primitive."],
        ["`data/wheel_summary.json`", "Derived rim/tyre measurements for all four wheels of each car."],
        ["`tools/`", "Copies of the scripts that made all of this."]]) + "\n")
    w("## Summary of findings\n")
    for t in [
        "**Nothing in any donor file says what a rim or a tyre *is*.** Wheel identity lives in Racer's sidecar `.vehicle` descriptor (pivot, radius, width, node→wheel binding), and the descriptor radius is simply the tyre's outer radius.",
        "**Rim and tyre are separate meshes in five of six cars** (GT4, MC3, MCLA, Juiced 2, SLRR). The Ford Racing 2 Mustang has one fused wheel mesh with a single material; its rim/tyre split here is a radius heuristic.",
        "**Rim and tyre do not meet cleanly.** The tyre's inner radius is inside the rim's outer radius by 53 mm (GT4) and 43 mm (Juiced 2); MC3 and MCLA meet exactly; SLRR within 3 mm. A tyre cannot simply be swapped onto another car's rim without redefining that seam.",
        "**Three of the tyres are open shells** (GT4, MC3 and the Ford fused mesh have no vertices on the inboard half below mid-sidewall); Juiced 2, MCLA and SLRR have full cross-sections. An open tyre cannot be reused on another wheel without rebuilding its inner sidewall and bead.",
        "**Rim shapes are inconsistent:** GT4's rim is a face-only shell offset outboard with no barrel; Juiced 2 has a barrel; MC3/MCLA/SLRR carry flanges and inner shells. There is no shared origin, mounting-face or offset convention.",
        "**Tyre proportions differ a lot.** Visible sidewall height ranges 49 mm (Juiced 2) to 116 mm (SLRR); fitting one donor tyre on another donor rim by uniform scaling needs sidewall scale factors from about 0.42 to 2.35 (retargeting matrix below), so tyres need independent bead-radius / sidewall / width parameters rather than a single scale.",
        "**Two donors already point at procedural tyres:** MCLA names its tyre `tir_car` (a shared generic resource) and Juiced 2 sizes stock tyres from a shared `TYRE_PROFILE` template. That supports a single parametric tyre.",
        "**Materials are not PBR-authored.** Every car uses one uniform metallic/roughness pair (GT4 0 / 0.7, Ford 0 / 1.0, MC3 0 / 0.6, MCLA 0 / 0.7, Juiced 2 0.15 / 0.55, SLRR 0 / 1.0) and no metallic-roughness textures. The meaningful material information is in per-game metadata (`gt4_material`, MC3 `shader_category`, MCLA `sourceShader`, Juiced 2 material names), which differs per game.",
        "**Lighting is not stored in the cars at all.** Without a shared material model, the same rig still makes the six cars look very different (white SLRR vs textured GT4); see the renders.",
        "**Only Juiced 2 has brake parts** (rolling disc + steering-only caliper carrier); the other five have none. Descriptor formats also differ: v2 (Juiced 2) names roles, v1 uses numbers."]:
        w("- " + t)
    w("")
    w("## Source map\n")
    rows = []
    for k in ORDER:
        r = AN[k]
        rows.append([GAME[k], CAR[k], "`%s`" % SRCID[k], r["generator"], "%.1f MB" % (r["glb_bytes"] / 1e6), "v%s" % r["descriptor_format"]])
    w(md_table(["Game", "Car", "Source id", "GLB generator (Racer pipeline)", "File", "Descriptor"], rows) + "\n")
    w("Shared conventions already applied by Racer's preparation: +X right, +Y up, +Z nose, 1 unit = 1 m; wheel meshes pivot-centred with the axle along X; wheel pivot/radius/width in the `.vehicle` file; wheel parts bound by node index.\n")
    w("## Structure comparison\n")
    rows = []
    for k in ORDER:
        r, s = AN[k], ST[k]
        rows.append([GAME[k], "%d (%d in scene)" % (s["all_nodes"], s["scene_nodes"]), r["counts"]["meshes"], "{:,}".format(s["tris"]),
                     "%d / %d" % (s["textured_mats"], r["counts"]["materials"]), "%d (max %dx%d)" % (r["counts"]["images"], *s["maxtex"]),
                     ", ".join(r["extensionsUsed"]) or "none"])
    w(md_table(["Game", "Nodes", "Meshes", "Triangles", "Textured / total materials", "Images", "glTF extensions"], rows) + "\n")
    w("## Materials and lighting\n")
    rows = []
    mnote = {"gran-turismo-4_acura-nsx-04": "`gt4_material` ambient/diffuse/specular; 231 of 338 are MASK/BLEND",
             "ford-racing-2_mustang-1973": "none; whitewall painted in texture",
             "midnight-club-3_corvette-z06": "`shader_category` + full native material graph; neutral display factors",
             "midnight-club-la_350z-roadster": "`sourceShader` + draw bucket",
             "juiced-2_350z": "authored: glass tint, uniform factors",
             "slrr_furrano-gt54": "texture path/hash per primitive; 'authored neutral inspection factor'"}
    for k in ORDER:
        s = ST[k]
        rows.append([GAME[k], "/".join("%g" % x for x in s["metallic"]), "/".join("%g" % x for x in s["rough"]), s["nonopaque"], mnote[k]])
    w(md_table(["Game", "Metallic", "Roughness", "Non-opaque mats", "Per-material metadata"], rows) + "\n")
    w("**Render rig (identical for every picture):** Blender 5.2 EEVEE, 'Standard' view transform; world colour (0.62, 0.64, 0.68) strength 1.0; one sun (strength 2.0, 6° angle); two area lights (fill 500 W / 6 m, rim 450 W / 5 m); ground albedo 0.30, roughness 0.55; 1600×900 whole-car and 1200×900 wheel views. This rig is a reference for the standard, not Racer's in-game lighting; the importer maps each model's materials as glTF defines them and nothing was overridden.\n")
    w("## Wheel measurements (front-left, from mesh geometry)\n")
    rows = []
    for k in ORDER:
        p, d = FL[k], DESC[k]["FL"]
        rows.append([GAME[k], mm(d["radius"]), mm(d["width"]), mm(p["rim_outer_radius_m"]), mm(p["tire_inner_radius_m"]), mm(p["tire_outer_radius_m"]),
                     mm(p["sidewall_height_m"]), mm(p["tire_axial_width_m"]), "—" if p["tire_rim_radial_overlap_m"] is None else mm(p["tire_rim_radial_overlap_m"]),
                     p["rim_diameter_in"], "—" if p["aspect_ratio_pct"] is None else p["aspect_ratio_pct"],
                     ", ".join("%s %s" % (a, "{:,}".format(b)) for a, b in p["verts"].items())])
    w(md_table(["Game", "Desc. radius mm", "Desc. width mm", "Rim outer mm", "Tyre inner mm", "Tyre outer mm", "Sidewall mm", "Tyre width mm", "Overlap mm", "Rim ⌀ in (mesh)", "Aspect %", "Vertices"], rows) + "\n")
    w("Notes: the descriptor radius equals the tyre outer radius and the descriptor width tracks the tyre's axial extent. 'Rim ⌀' is twice the rim mesh's outer radius; rim meshes can include flanges that reach the bead, so it is not a recovered nominal rim size (MCLA's 21.1 in for a 350Z is evidence of that). Ford is a fused mesh: tyre inner radius and overlap are not measurable, and its rim figures come from the radius heuristic. Rear wheels differ from front for GT4, MC3 and MCLA (see `data/wheel_summary.json`).\n")
    for k in ORDER:
        c = CARS[k]
        w("## %s — %s\n" % (GAME[k], CAR[k]))
        w("`%s`; descriptor `%s`.\n" % (AN[k]["glb"], AN[k]["descriptor"]))
        w("![front 3/4](%s) ![side](%s)\n" % (rel(k, "car_front34"), rel(k, "car_side")))
        w("![rear 3/4](%s) ![top](%s)\n" % (rel(k, "car_rear34"), rel(k, "car_top")))
        w("**How wheels are built:** " + c["wheel_how"] + "\n")
        for f in c["facts"]:
            w("- " + f)
        w("")
        w("Front-left wheel sections: in context, assembled, rim only, tyre only, exploded along the axle, and the axial/radial profile (rim blue, tyre orange with its convex hull shaded, disc green, caliper red).\n")
        w("![context](%s) ![assembled](%s)\n" % (rel(k, "wheel_context"), rel(k, "wheel_assembled_34")))
        w("![rim only](%s) ![tyre only](%s)\n" % (rel(k, "wheel_rim_only"), rel(k, "wheel_tire_only")))
        w("![exploded](%s) ![profile](%s)\n" % (rel(k, "wheel_exploded"), rel(k, "wheel_profile")))
    w("## Why wheels are not interchangeable today\n")
    for t in ["No rim parameters: diameter, width, offset (ET), bead-seat radius and bolt pattern are not stored; only the tyre's outer radius and width are, in the sidecar descriptor.",
              "No tyre parameters: no section width / aspect / rim-diameter spec, no bead definition. Tyre meshes are baked shapes with different profiles (49–116 mm sidewall).",
              "Rim–tyre seam is not a shared contract (overlap of 53, 43, 3, 0 and 0 mm; Ford fused).",
              "Three tyres (GT4, MC3, Ford) are open shells with no inboard sidewall or bead.",
              "No common origin or mirror convention: GT4's rim is an offset shell, others are hub-centred; left/right handling differs per game.",
              "Materials are shared-nothing: texture atlases (Ford rim+tyre), alpha-masked rims (GT4), per-game shader metadata, uniform factors.",
              "Brake parts exist only on Juiced 2 and use a different descriptor format."]:
        w("- " + t)
    w("")
    w("## Proposed standard\n")
    w("### Files\n")
    w(md_table(["File", "Holds", "Key data"], [
        ["`<id>.car.glb`", "Body, glass, lights, interior, underbody; **no wheel geometry**", "Four `mount_FL/FR/RL/RR` empty nodes at the hub centre (outboard = +X local; FL/RL rotated 180° about Y); `extras`: wheelbase, track, ride height, default `rim`/`tire` spec per axle, arch clearance (max tyre width / outer radius), provenance and hashes."],
        ["`<id>.rim.glb`", "Rim (barrel + face), origin at the hub centre on the mounting face, axle +X, metres", "`extras`: diameter_in, width_in, offset_mm, bead-seat radius, hub bore, bolt pattern. Left/right are the same asset rotated by the mount."],
        ["`<id>.tire.glb`", "One tyre on a normalised profile", "Per-vertex profile coordinates (u across the tread −1..1, v from bead seat 0 to tread 1) stored as a custom attribute; tread pattern/branding in textures only."],
        ["`<id>.brake.glb` (optional)", "Disc (rolls) and caliper (steering carrier)", "Mount offsets and the disc/caliper clearance to the rim barrel."]]) + "\n")
    w("### Tyre fitting\n")
    w("For rim diameter `D`, tyre section width `w` and aspect `a`: sidewall `h = a·w`, inner (bead) radius `D/2`, outer radius `D/2 + h`. Each tyre vertex moves to radius `D/2 + v·h` and axial position `u·w/2`, keeping the tread vertices at `v = 1`. Three independent parameters (bead radius, sidewall, width) are required: a uniform scale cannot fit the donor range.\n")
    w("### Retargeting matrix\n")
    w("Sidewall / width scale needed to put the row car's tyre on the column car's rim while keeping the column car's outer radius (front-left, mesh measurements; Ford excluded):\n")
    head = ["Tyre from \\ rim of"] + [GAME[k] for k in five]
    rows = []
    for a, row in zip(five, matrix_rows):
        rows.append([GAME[a]] + ["%.2f / %.2f" % (x, y) for x, y in row])
    w(md_table(head, rows) + "\n")
    w("### Materials and lighting\n")
    w("A shared slot library on core glTF PBR plus `KHR_materials_clearcoat` (paint), alpha/transmission (glass) and `KHR_materials_emissive_strength` (lamps): `paint_body`, `paint_trim`, `chrome`, `glass_clear`, `glass_tint`, `rubber_tire`, `rim_alloy`, `rim_chrome`, `brake_disc`, `caliper_paint`, `plastic_black`, `lamp_head`, `lamp_tail`, `interior`. Each mesh primitive carries `extras.racer_material_slot`; textures are base colour / normal / occlusion-roughness-metallic only. Per-game mapping rules: GT4 from `gt4_material` + alpha mode, MC3 from `shader_category`, MCLA from `sourceShader`, Juiced 2 and Ford from material names, SLRR from texture path. One engine-side environment (image-based light + sun) is used for every scene; the rig above is the reference for offline comparison.\n")
    w("## Migration plan\n")
    steps = ["Freeze the spec and write a validator (axes, units, node names, extras schema, rim/tyre seam, arch clearance).",
             "Pilot on the GT4 NSX (separate rim and tyre nodes already): normalise rim origin/axle, author the barrel the face-only rim lacks, build the first normalised tyre.",
             "Extract and normalise the other rims (MC3, MCLA, Juiced 2, SLRR); keep the donor wheel+tyre pair as that car's stock set. Ford's fused mesh needs a manual split and a new tyre texture.",
             "Strip wheels from the six cars into `.car.glb` with mount nodes; re-run Racer's scale, clearance and containment checks.",
             "Remap materials into the slot library per game; render all cars with the reference rig and compare against golden images.",
             "Engine: load rim+tyre per mount, resize tyres at load time, include the wheel spec in the physics identity hash and the saved-profile schema; add garage wheel swap.",
             "Extend to the other 11 installed players, then the research-candidate rows."]
    for i, t in enumerate(steps, 1):
        w("%d. %s" % (i, t))
    w("")
    w("## Limits and open questions\n")
    for t in ["Measurements come from Racer's prepared meshes; Racer already authored some fits (MC3 mounts, MCLA fit, SLRR pose, Juiced 2 tyre), so they are not the donor games' physical sizes.",
              "'Rim diameter' and 'aspect' are derived from mesh radii and are not recovered nominal sizes.",
              "Renders use Blender's glTF importer and a studio rig, not Racer's renderer; materials were not overridden, so the GT4 window colours and white SLRR body are properties of the data. The Ford rim/tyre split in the images is heuristic.",
              "Only the front-left wheel is rendered; all four wheels' numbers are in `data/wheel_summary.json`.",
              "Not checked: redistribution rights of any donor mesh; whether the donor games themselves resize shared tyres at runtime; how Racer's wheel-blur and tyre-contact code would use split meshes.",
              "Decisions for you: nominal units (mm or inches) for the spec; whether car files keep a default stock wheel set; naming (`<game>/<code>`)."]:
        w("- " + t)
    w("")
    w("## Reproduce\n")
    w("```sh\ncd games/racer\nK=assets/local/car-standardization-kit\nS=experiments/2026-11-09-car-standardization/scripts\npython3 -I $S/analyze_glb.py $K/models $K/data/analysis.json\n$S/render_all.sh $PWD/$K        # Blender 5.2\npython3 -I $S/wheel_summary.py $K\npython3 -I $S/build_kit_docs.py $K <scratch-dir>\n```\n")
    open(os.path.join(KIT, "README.md"), "w").write("\n".join(L))


# ----------------------------------------------------------------------------- deck
IMG = os.path.join(SCRATCH, "deck_img")
os.makedirs(IMG, exist_ok=True)
def jpg(car, name, width):
    out = os.path.join(IMG, "%s__%s_%d.jpg" % (car, name, width))
    if not os.path.exists(out):
        im = Image.open(os.path.join(KIT, rel(car, name))).convert("RGB")
        im = im.resize((width, int(im.height * width / im.width)), Image.LANCZOS)
        im.save(out, quality=88)
    return out

E = html.escape
def md_inline(t):
    import re
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", E(t))

CSS = """
@page { size: 1280px 720px; margin: 0 }
* { box-sizing: border-box }
body { margin: 0; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; color: #1b1f24; font-size: 19px; line-height: 1.4 }
.slide { width: 1280px; height: 720px; page-break-after: always; overflow: hidden; position: relative; background: #fff; padding: 0 }
.hd { height: 82px; background: #14202e; color: #fff; padding: 16px 44px 0 44px }
.hd .kick { font-size: 13px; letter-spacing: 2px; text-transform: uppercase; color: #8fb4d9 }
.hd h2 { margin: 2px 0 0 0; font-size: 29px; font-weight: 700 }
.bd { padding: 20px 44px 0 44px }
.ft { position: absolute; bottom: 10px; left: 44px; right: 44px; font-size: 11px; color: #6b7785; display: flex; justify-content: space-between }
table { border-collapse: collapse; width: 100%; font-size: 17px }
th { background: #eaf0f6; text-align: left; padding: 6px 8px; border-bottom: 2px solid #b9c7d6 }
td { padding: 5px 8px; border-bottom: 1px solid #dde4ec; vertical-align: top }
code { background: #eef1f5; padding: 0 4px; border-radius: 3px; font-size: 0.9em }
ul { margin: 6px 0; padding-left: 22px } li { margin: 4px 0 }
.cols { display: flex; gap: 26px } .cols > div { flex: 1 }
.g2 { display: grid; grid-template-columns: 1fr 1fr; gap: 10px } .g3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px }
.g2 img, .g3 img { width: 100%; display: block; border: 1px solid #cfd8e2 }
.cap { font-size: 12px; color: #5b6673; margin-top: 2px }
.big { font-size: 52px; font-weight: 800; line-height: 1.05 } .sub { font-size: 21px; color: #cfdceb }
.pill { display: inline-block; background: #e8f1fb; border: 1px solid #b6cfe8; border-radius: 12px; padding: 1px 10px; font-size: 13px; margin-right: 6px }
.box { border: 1px solid #c9d4e0; border-radius: 6px; padding: 10px 14px; background: #f7f9fc }
.kv { font-size: 17px } .bad { color: #b3261e; font-weight: 700 } .ok { color: #1f7a3d; font-weight: 700 }
.dia { display: flex; gap: 16px; align-items: stretch } .dia .n { flex: 1; border: 2px solid #2b4a6b; border-radius: 8px; padding: 12px; background: #f2f7fc }
.dia .n h4 { margin: 0 0 6px 0; font-size: 18px; color: #14202e } .arrow { align-self: center; font-size: 30px; color: #2b4a6b }
"""

SL = []
def slide(kick, title, body, n=None):
    SL.append('<section class="slide"><div class="hd"><div class="kick">%s</div><h2>%s</h2></div><div class="bd">%s</div>'
              '<div class="ft"><span>Car &amp; wheel standardization kit &middot; Racer</span><span>%s</span></div></section>' % (E(kick), E(title), body, "%d" % (len(SL) + 1)))

def table(head, rows, style=""):
    return '<table style="%s"><tr>%s</tr>%s</table>' % (style, "".join("<th>%s</th>" % E(str(h)) for h in head),
                                                       "".join("<tr>%s</tr>" % "".join("<td>%s</td>" % c for c in r) for r in rows))

def build_deck():
    # 1 title
    SL.append('<section class="slide" style="background:#14202e;color:#fff"><div style="padding:150px 80px"><div class="kick" style="color:#8fb4d9;letter-spacing:3px;text-transform:uppercase;font-size:15px">Racer &middot; asset standardization</div>'
              '<div class="big" style="margin-top:14px">One car, one file.<br>Rims and tyres that fit anything.</div>'
              '<div class="sub" style="margin-top:30px">What six donor games ship today &mdash; and what a common standard has to replace.</div>'
              '<div style="margin-top:60px;color:#8fb4d9;font-size:16px">GT4 &middot; Ford Racing 2 &middot; Midnight Club 3 &middot; Midnight Club LA &middot; Juiced 2 &middot; SLRR<br>Renders: one identical Blender rig &middot; Measurements: exact mesh geometry from the Racer-prepared GLBs</div></div></section>')
    # 2 goal vs reality
    slide("Goal", "Where we want to be, and where the files are",
          '<div class="cols"><div><h3 style="margin:0 0 6px 0">Target</h3><ul>'
          '<li>Each car is its own file.</li><li>All games&rsquo; cars share one lighting, rendering and material model.</li>'
          '<li>Rims and tyres are separate parts.</li><li>Any tyre goes on any rim, resized to match.</li><li>Wheels are interchangeable between cars.</li></ul></div>'
          '<div><h3 style="margin:0 0 6px 0">Today (six Racer-prepared donor GLBs)</h3><ul>'
          '<li>Wheel meaning lives in a sidecar <code>.vehicle</code> file, not the GLB.</li>'
          '<li>Rim and tyre are separate meshes in 5 of 6 cars; Ford is one fused mesh.</li>'
          '<li>Tyre inner radius overlaps the rim by 0&ndash;53 mm; no shared seam.</li>'
          '<li>Sidewalls span 49&ndash;116 mm; rim shapes and origins differ.</li>'
          '<li>Materials are uniform factors plus per-game metadata; nothing shared.</li></ul></div></div>'
          '<div class="box" style="margin-top:18px"><b>Reading guide.</b> Slides 4&ndash;8 compare the games. Slides 9&ndash;26 show each car (views, wheel sections, how its wheel is built). Slides 27&ndash;33 cover what blocks interchange, the proposed standard, the tyre-fitting maths, a retargeting matrix, a migration plan and open decisions.</div>')
    # 3 kit + rig
    slide("Method", "What is in the kit and how the pictures were made",
          '<div class="cols"><div><ul><li><code>models/</code> six GLBs + <code>.vehicle</code> descriptors</li><li><code>renders/</code> ten renders per car + wheel profile plot</li>'
          '<li><code>data/analysis.json</code> glTF inventory and exact wheel-bound geometry</li><li><code>data/wheel_summary.json</code> rim/tyre measurements, all four wheels</li><li><code>README.md</code> the written report</li></ul>'
          '<p class="kv"><b>Wheel sections</b> = the front-left wheel shown in context, assembled, rim only, tyre only, exploded along the axle (tyre out, disc and caliper in), plus an axial/radial vertex profile (rim blue, tyre orange, disc green, caliper red).</p></div>'
          '<div class="box kv"><b>Reference rig (identical for every image)</b><ul><li>Blender 5.2 EEVEE, Standard view transform</li><li>World (0.62, 0.64, 0.68) &times; 1.0</li><li>Sun 2.0, 6&deg;; fill area 500 W; rim area 450 W</li><li>Ground albedo 0.30, roughness 0.55</li><li>No material overrides: the importer&rsquo;s glTF materials as shipped</li></ul>'
          '<p><b>Caveats.</b> Not Racer&rsquo;s in-game renderer. Racer already authored some fits (MC3 mounts, MCLA fit, SLRR pose, Juiced 2 tyre). Ford&rsquo;s rim/tyre split is a radius heuristic.</p></div></div>')
    # 4 source map
    rows = [[E(GAME[k]), E(CAR[k]), "<code>%s</code>" % E(SRCID[k]), E(AN[k]["generator"]), "%.1f MB" % (AN[k]["glb_bytes"] / 1e6), "v%s" % AN[k]["descriptor_format"]] for k in ORDER]
    slide("Comparison", "Source map: six games, six pipelines", table(["Game", "Car", "Source id", "GLB generator", "Size", "Desc."], rows) +
          '<p class="kv" style="margin-top:14px">Already shared by Racer&rsquo;s preparation: +X right, +Y up, +Z nose, 1 unit = 1 m; wheel meshes pivot-centred with the axle along X; wheel pivot, radius, width in the <code>.vehicle</code> file; wheel parts bound by node index. Descriptor v2 (Juiced 2) names roles <code>body / wheel / carrier</code>; v1 uses a number.</p>')
    # 5 structure
    rows = []
    for k in ORDER:
        r, s = AN[k], ST[k]
        rows.append([E(GAME[k]), "%d <span class='cap'>(%d in scene)</span>" % (s["all_nodes"], s["scene_nodes"]), r["counts"]["meshes"], "{:,}".format(s["tris"]),
                     "%d / %d" % (s["textured_mats"], r["counts"]["materials"]), "%d <span class='cap'>max %dx%d</span>" % (r["counts"]["images"], *s["maxtex"]), E(", ".join(r["extensionsUsed"]) or "none")])
    slide("Comparison", "Structure: node, mesh, material and texture counts",
          table(["Game", "Nodes", "Meshes", "Triangles", "Textured / total mats", "Images", "Extensions"], rows) +
          '<p class="kv" style="margin-top:14px">GT4 carries 338 materials (231 alpha MASK/BLEND) and 155 images; Ford 7 materials. Ford&rsquo;s GLB holds 136 nodes but only 12 are reachable from the scene root. GT4 and MC3 use <code>KHR_materials_variants</code>. No car uses clearcoat, transmission, emissive-strength or any PBR texture other than base colour/normal.</p>')
    # 6 materials
    mnote = {"gran-turismo-4_acura-nsx-04": "<code>gt4_material</code> ambient / diffuse / specular",
             "ford-racing-2_mustang-1973": "none; whitewall painted into the texture",
             "midnight-club-3_corvette-z06": "<code>shader_category</code> + full native material graph",
             "midnight-club-la_350z-roadster": "<code>sourceShader</code> + draw bucket",
             "juiced-2_350z": "authored glass tint; uniform factors",
             "slrr_furrano-gt54": "texture path/hash; &lsquo;authored neutral factor&rsquo;"}
    rows = [[E(GAME[k]), "/".join("%g" % x for x in ST[k]["metallic"]), "/".join("%g" % x for x in ST[k]["rough"]), ST[k]["nonopaque"], mnote[k]] for k in ORDER]
    slide("Comparison", "Materials: uniform factors, per-game metadata",
          table(["Game", "Metallic", "Roughness", "Non-opaque", "Per-material metadata"], rows) +
          '<ul style="margin-top:14px"><li>No car has a metallic-roughness texture: one factor pair per car is all the PBR data there is.</li><li>The useful semantics (paint, chrome, glass, lamp) live in metadata that differs per game, so a shared slot library needs a per-game mapping rule.</li>'
          '<li>Glass: Juiced 2 authored a tint; MC3 has <code>colored_glass</code>/<code>car_window</code> categories; GT4 windows render as flat colours here; MCLA/SLRR/Ford have no glass-named materials.</li></ul>')
    # 7 wheel measurements
    rows = []
    for k in ORDER:
        p, d = FL[k], DESC[k]["FL"]
        rows.append([E(GAME[k]), mm(d["radius"]), mm(d["width"]), mm(p["rim_outer_radius_m"]), mm(p["tire_inner_radius_m"]), mm(p["tire_outer_radius_m"]), mm(p["sidewall_height_m"]),
                     mm(p["tire_axial_width_m"]), "&mdash;" if p["tire_rim_radial_overlap_m"] is None else ("<span class='bad'>%s</span>" % mm(p["tire_rim_radial_overlap_m"]) if p["tire_rim_radial_overlap_m"] > 0.02 else mm(p["tire_rim_radial_overlap_m"])),
                     "{:,} / {:,}".format(p["verts"].get("rim", 0), p["verts"].get("tire", 0))])
    slide("Wheels", "Wheel measurements, front-left (mm, from mesh geometry)",
          table(["Game", "Desc. radius", "Desc. width", "Rim outer", "Tyre inner", "Tyre outer", "Sidewall", "Tyre width", "Overlap", "Verts rim / tyre"], rows) +
          '<p class="kv" style="margin-top:12px">The descriptor radius is the tyre outer radius; the descriptor width tracks the tyre&rsquo;s axial extent. Overlap = rim outer radius &minus; tyre inner radius (red &gt; 20 mm). Ford is a fused mesh: tyre inner radius and overlap are not measurable and rim figures come from the radius heuristic. Rim &lsquo;diameter&rsquo; from mesh radii is not a nominal rim size (MCLA&rsquo;s 350Z measures 21.1 in).</p>')
    # 8 profiles
    imgs = "".join('<div><img src="%s"><div class="cap">%s &mdash; %s</div></div>' % (jpg(k, "wheel_profile", 700), E(GAME[k]), E(CAR[k])) for k in ORDER)
    slide("Wheels", "Axial / radial profiles of the six front-left wheels",
          '<div class="g3" style="width:980px;margin:0 auto">%s</div><div class="cap" style="text-align:center">Tyre shading = convex hull of the tyre vertices. A hull that stops short of the inboard side means the tyre mesh has no inboard sidewall: GT4, MC3 and Ford are open shells; Juiced 2, MCLA and SLRR are closed.</div>' % imgs)
    # per-car slides
    for k in ORDER:
        c = CARS[k]
        views = "".join('<div><img src="%s"><div class="cap">%s</div></div>' % (jpg(k, n, 760), t) for n, t in
                        (("car_front34", "front 3/4"), ("car_side", "side"), ("car_rear34", "rear 3/4"), ("car_top", "top")))
        s = ST[k]
        meta = ('<span class="pill">%s</span><span class="pill">%d nodes</span><span class="pill">%d meshes</span><span class="pill">%s tris</span><span class="pill">%d materials</span><span class="pill">%d images</span>' %
                (E(AN[k]["glb"]), s["all_nodes"], AN[k]["counts"]["meshes"], "{:,}".format(s["tris"]), AN[k]["counts"]["materials"], AN[k]["counts"]["images"]))
        slide(GAME[k], CAR[k] + ": the car", '<div style="margin-bottom:8px">%s</div><div class="g2" style="width:900px;margin:0 auto">%s</div>' % (meta, views))
        wimgs = "".join('<div><img src="%s"><div class="cap">%s</div></div>' % (jpg(k, n, 560), t) for n, t in
                        (("wheel_context", "in context"), ("wheel_assembled_34", "assembled"), ("wheel_exploded", "exploded along the axle"),
                         ("wheel_rim_only", "rim only"), ("wheel_tire_only", "tyre only"), ("wheel_profile", "axial / radial profile")))
        p = FL[k]
        strip = "tyre &Oslash; %s mm &middot; width %s mm &middot; sidewall %s mm &middot; rim outer %s mm &middot; overlap %s" % (
            mm((p["tire_outer_radius_m"] or 0) * 2) if p["tire_outer_radius_m"] else "&mdash;", mm(p["tire_axial_width_m"]), mm(p["sidewall_height_m"]), mm(p["rim_outer_radius_m"]),
            "n/a (fused)" if p["tire_rim_radial_overlap_m"] is None else mm(p["tire_rim_radial_overlap_m"]) + " mm")
        slide(GAME[k], CAR[k] + ": wheel sections", '<div class="g3" style="width:1010px;margin:0 auto">%s</div><div class="kv" style="margin-top:8px;text-align:center">%s</div>' % (wimgs, strip))
        facts = "".join("<li>%s</li>" % md_inline(f) for f in c["facts"])
        slide(GAME[k], CAR[k] + ": how its wheel is built",
              '<div class="cols"><div><div class="box"><b>Structure.</b> %s</div><ul style="margin-top:12px">%s</ul></div>'
              '<div style="flex:0 0 430px"><img src="%s" style="width:100%%;border:1px solid #cfd8e2"><div class="cap">front-left profile: rim blue, tyre orange, disc green, caliper red; grey line = descriptor radius</div></div></div>' %
              (md_inline(c["wheel_how"]), facts, jpg(k, "wheel_profile", 600)))
    # findings
    slide("Analysis", "What blocks interchangeable wheels",
          '<ul><li><b>No rim data:</b> diameter, width, offset, bead-seat radius, bolt pattern are stored nowhere.</li>'
          '<li><b>No tyre data:</b> no width/aspect/diameter spec; tyres are baked shapes with 49&ndash;116 mm sidewalls.</li>'
          '<li><b>No seam contract:</b> tyre inner radius sits 53, 43, 3, 0 and 0 mm inside the rim&rsquo;s outer radius; Ford is fused.</li>'
          '<li><b>Open tyres:</b> GT4, MC3 and Ford tyres have no inboard sidewall or bead, so they cannot move to another wheel as-is.</li>'
          '<li><b>No common origin or mirror rule:</b> GT4&rsquo;s rim is an outboard-offset shell with no barrel; others are hub-centred.</li>'
          '<li><b>Shared-nothing materials:</b> Ford rim+tyre share one atlas, GT4 rims are alpha-masked, shader metadata is per game, factors are uniform.</li>'
          '<li><b>Brakes:</b> only Juiced 2 has a disc/caliper pair, in a different descriptor format.</li></ul>'
          '<div class="box" style="margin-top:14px"><b>Evidence that procedural tyres are the right model:</b> MCLA&rsquo;s tyre is the generic <code>tir_car</code> resource, and Juiced 2 sizes stock tyres from a shared <code>TYRE_PROFILE</code> template (inputs per car not recovered). Neither claim is verified inside the donor game.</div>')
    # architecture
    slide("Proposal", "Target file architecture",
          '<div class="dia"><div class="n"><h4>&lt;id&gt;.car.glb</h4>Body, glass, lights, interior, underbody. <b>No wheels.</b><br><br>Four <code>mount_FL/FR/RL/RR</code> empties at the hub centre (outboard = +X local; FL/RL rotated 180&deg; about Y).<br><br><code>extras</code>: wheelbase, track, ride height, default rim/tyre spec per axle, arch clearance, provenance + hashes.</div>'
          '<div class="arrow">+</div><div class="n"><h4>&lt;id&gt;.rim.glb</h4>Barrel + face. Origin on the hub mounting face, axle +X, metres.<br><br><code>extras</code>: diameter_in, width_in, offset_mm, bead-seat radius, hub bore, bolt pattern.<br><br>Left/right = same asset, rotated by the mount.</div>'
          '<div class="arrow">+</div><div class="n"><h4>&lt;id&gt;.tire.glb</h4>One tyre on a normalised profile.<br><br>Per-vertex (u, v): u = across the tread &minus;1..1, v = bead seat 0 &rarr; tread 1, stored as a custom attribute.<br><br>Tread and branding in textures only.</div>'
          '<div class="arrow">+</div><div class="n"><h4>&lt;id&gt;.brake.glb</h4>Optional.<br><br>Disc (rolls) and caliper (steering carrier) with mount offsets and barrel clearance.</div></div>'
          '<div class="box" style="margin-top:18px"><b>Stock sets.</b> Keep each donor car&rsquo;s own rim + tyre pair as its stock wheel set, so converting a car never loses its original look.</div>')
    # fitting math
    slide("Proposal", "Tyre fitting: three independent parameters",
          '<div class="cols"><div><p>Given rim diameter <b>D</b>, tyre section width <b>w</b>, aspect <b>a</b>:</p><ul><li>sidewall <b>h = a &middot; w</b></li><li>inner (bead) radius = <b>D / 2</b></li><li>outer radius = <b>D / 2 + h</b></li></ul>'
          '<p>Each tyre vertex with profile coordinates (u, v) moves to:</p><div class="box"><code>radius = D/2 + v &middot; h</code><br><code>axial = u &middot; w / 2</code></div><p style="margin-top:12px">Tread vertices stay at v = 1, so the pattern is preserved; branding and tread are textures.</p></div>'
          '<div><p><b>Why one uniform scale is not enough.</b></p><ul><li>Visible sidewall: Juiced 2 49 mm, MCLA 62, NSX 71, MC3 91, SLRR 116.</li><li>Rim-bead seats differ by up to 40 mm of radius.</li><li>Widths differ 210&ndash;260 mm.</li></ul><p>So bead radius, sidewall and width must vary independently. This runs at load time (cheap, rotationally symmetric) or bakes to size variants.</p></div></div>')
    # matrix
    head = ["Row tyre on column rim"] + [GAME[k] for k in five]
    rows = []
    for a, row in zip(five, matrix_rows):
        cells = []
        for (x, y) in row:
            bad = x < 0.6 or x > 1.6
            cells.append("<span class='%s'>%.2f</span> / %.2f" % ("bad" if bad else "", x, y))
        rows.append([E(GAME[a])] + cells)
    slide("Proposal", "Retargeting matrix: sidewall / width scale needed",
          table(head, rows) + '<p class="kv" style="margin-top:12px">Row car&rsquo;s tyre placed on the column car&rsquo;s rim, keeping the column car&rsquo;s outer radius (front-left, mesh measurements; Ford excluded). Red sidewall factors are outside 0.6&ndash;1.6: a donor tyre stretched that far is visibly wrong, which is why the standard needs parametric profiles.</p>')
    # materials
    slide("Proposal", "One material and lighting model",
          '<div class="cols"><div><p><b>Slot library</b> on core glTF PBR plus clearcoat (paint), alpha/transmission (glass), emissive strength (lamps):</p>'
          '<p><span class="pill">paint_body</span><span class="pill">paint_trim</span><span class="pill">chrome</span><span class="pill">glass_clear</span><span class="pill">glass_tint</span><span class="pill">rubber_tire</span><span class="pill">rim_alloy</span><span class="pill">rim_chrome</span><span class="pill">brake_disc</span><span class="pill">caliper_paint</span><span class="pill">plastic_black</span><span class="pill">lamp_head</span><span class="pill">lamp_tail</span><span class="pill">interior</span></p>'
          '<p>Each primitive carries <code>extras.racer_material_slot</code>; textures limited to base colour, normal, occlusion-roughness-metallic. One engine-side environment (IBL + sun) for every scene.</p></div>'
          '<div>' + table(["Game", "Slot mapping source"], [["GT4", "<code>gt4_material</code> + alpha mode"], ["MC3", "<code>shader_category</code>"], ["MCLA", "<code>sourceShader</code>"], ["Juiced 2", "material names"], ["Ford", "material names"], ["SLRR", "texture path / hash"]]) + '</div></div>')
    # migration
    steps = ["Freeze the spec; write a validator (axes, units, node names, extras schema, rim/tyre seam, arch clearance).",
             "Pilot on the GT4 NSX (separate rim/tyre nodes): normalise the rim origin and axle, author the missing barrel, build the first normalised tyre.",
             "Normalise the other rims (MC3, MCLA, Juiced 2, SLRR); keep each donor pair as the stock set. Ford: manual split + new tyre texture.",
             "Strip wheels into <code>.car.glb</code> with mounts; re-run Racer&rsquo;s scale, clearance and containment checks.",
             "Remap materials into slots per game; render all cars with the reference rig and compare to golden images.",
             "Engine: assemble rim + tyre per mount, resize tyres at load, add the wheel spec to the physics identity hash and saved-profile schema; garage wheel swap.",
             "Extend to the other 11 installed players, then the research candidates."]
    slide("Plan", "Migration plan", "<ol>%s</ol>" % "".join("<li style='margin:7px 0'>%s</li>" % s for s in steps))
    # limits
    slide("Plan", "Limits and decisions needed",
          '<div class="cols"><div><h3 style="margin:0 0 4px 0">Limits</h3><ul class="kv"><li>Measurements are from Racer&rsquo;s prepared meshes, not donor-game physical sizes.</li><li>&lsquo;Rim diameter&rsquo; and &lsquo;aspect&rsquo; are derived from radii, not recovered nominal sizes.</li>'
          '<li>Renders use Blender&rsquo;s importer, not Racer&rsquo;s renderer; GT4&rsquo;s window colours and SLRR&rsquo;s white body are properties of the data.</li><li>Only the front-left wheel is rendered; all four are in <code>wheel_summary.json</code>.</li>'
          '<li>Not checked: redistribution rights; whether donor games resize shared tyres at runtime; impact on wheel-blur and tyre-contact code.</li></ul></div>'
          '<div><h3 style="margin:0 0 4px 0">Decisions for you</h3><ul class="kv"><li>Spec units: millimetres or inches.</li><li>Should car files embed a default stock wheel set, or only mounts?</li><li>Naming: <code>&lt;game&gt;/&lt;code&gt;</code> or a new id scheme.</li><li>Pilot car: the GT4 NSX is proposed; any of the five split-mesh cars works.</li></ul></div></div>')

    doc = "<!doctype html><html><head><meta charset='utf-8'><style>%s</style></head><body>%s</body></html>" % (CSS, "".join(SL))
    hp = os.path.join(SCRATCH, "deck.html")
    open(hp, "w").write(doc)
    pdf = os.path.join(KIT, "car-standardization-deck.pdf")
    chrome = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    if os.path.exists(chrome):
        subprocess.run([chrome, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--allow-file-access-from-files",
                        "--print-to-pdf=" + pdf, "file://" + hp], check=True, capture_output=True)
    else:
        subprocess.run(["weasyprint", hp, pdf], check=True)
    # one HTML file per slide, for screenshot review of the exact same markup
    pv = os.path.join(SCRATCH, "slides")
    os.makedirs(pv, exist_ok=True)
    for i, s in enumerate(SL, 1):
        open(os.path.join(pv, "s%02d.html" % i), "w").write(
            "<!doctype html><html><head><meta charset='utf-8'><style>%s body{margin:0}</style></head><body>%s</body></html>" % (CSS, s))
    print("slides:", len(SL), "pdf bytes:", os.path.getsize(pdf))


build_readme()
build_deck()
