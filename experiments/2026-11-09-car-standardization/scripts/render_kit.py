"""Blender renderer for the car-standardization kit (run with blender -b --python).

One identical lighting/camera rig for every car, so differences in the pictures come from
the models' own geometry and materials, not from the renderer.

blender -b --python render_kit.py -- <models-dir> <analysis.json> <out-dir> <car-key> [engine]

Outputs per car: car_*.png (whole car) and wheel_*.png (front-left wheel sections).
Nothing is modified in the source models; a temporary GLB with uniquified node names is
written next to the output and removed afterwards.
"""
import sys, os, json, math, struct

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import analyze_glb as A  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:]
MODELS, ANALYSIS, OUT, KEY = argv[:4]
ENGINE = argv[4] if len(argv) > 4 else "EEVEE"
os.makedirs(OUT, exist_ok=True)
an = json.load(open(ANALYSIS))[KEY]


def G(x, y, z):  # glTF (X right, Y up, Z nose)  ->  Blender (X, -Z, Y)
    return Vector((x, -z, y))


# ---------------------------------------------------------------- temp GLB with unique node names
def uniquify(src, dst):
    js, bin_ = A.load_glb(src)
    for i, n in enumerate(js["nodes"]):
        n["name"] = "n%03d__%s" % (i, n.get("name", ""))
    j = json.dumps(js, separators=(",", ":")).encode()
    j += b" " * (-len(j) % 4)
    b = bin_ + b"\0" * (-len(bin_) % 4)
    total = 12 + 8 + len(j) + (8 + len(b) if b else 0)
    with open(dst, "wb") as f:
        f.write(b"glTF" + struct.pack("<II", 2, total))
        f.write(struct.pack("<II", len(j), 0x4E4F534A) + j)
        if b:
            f.write(struct.pack("<II", len(b), 0x004E4942) + b)


bpy.ops.wm.read_factory_settings(use_empty=True)
tmp = os.path.join(OUT, "_tmp_%s.glb" % KEY)
uniquify(os.path.join(MODELS, KEY + ".glb"), tmp)
bpy.ops.import_scene.gltf(filepath=tmp)
os.remove(tmp)

objs = {}
for o in bpy.data.objects:
    objs[o.name[:4]] = o if o.name[:4] not in objs else objs[o.name[:4]]  # n000 .. n135

# ---------------------------------------------------------------- classify wheel parts
def kind(name, role):
    n = name.lower()
    if role == "carrier" or "calip" in n or "calli" in n:
        return "caliper"
    if "disc" in n or "rotor" in n:
        return "disc"
    if "tire" in n or "tyre" in n or "tir_car" in n:
        return "tire"
    return "rim"


parts = {w: [] for w in ("FL", "FR", "RL", "RR")}
for w, items in an["wheel_nodes"].items():
    for it in items:
        o = objs.get("n%03d" % it["node"])
        if o is None:
            continue
        parts[w].append((kind(it["name"] or "", it["role"]), o, it))

COMBINED = KEY.startswith("ford")  # one mesh holds both rim and tyre; split by loose part below
if COMBINED:
    # Split the single Ford wheel mesh into loose parts; tread-radius parts are the tyre, the rest the rim.
    wheel_cfg = an["descriptor_wheels"]["FL"]
    for w in parts:
        newparts = []
        for k, o, it in parts[w]:
            bpy.ops.object.select_all(action="DESELECT")
            o.select_set(True)
            bpy.context.view_layer.objects.active = o
            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.mesh.select_all(action="SELECT")
            bpy.ops.mesh.separate(type="LOOSE")
            bpy.ops.object.mode_set(mode="OBJECT")
            for p in bpy.context.selected_objects:
                M = p.matrix_world
                pv = [M @ v.co for v in p.data.vertices]
                wc = an["descriptor_wheels"][w]
                c = G(wc["x"], wc["y"], wc["z"])
                rmax = max(math.hypot(v.y - c.y, v.z - c.z) for v in pv)
                newparts.append(("tire" if rmax > 0.27 else "rim", p, it))
        parts[w] = newparts

# ---------------------------------------------------------------- scene, light, camera
sc = bpy.context.scene
for eng in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
    try:
        sc.render.engine = eng
        break
    except TypeError:
        pass
if ENGINE == "CYCLES":
    sc.render.engine = "CYCLES"
    sc.cycles.samples = 48
    sc.cycles.use_denoising = True
else:
    for attr, val in (("taa_render_samples", 64), ("use_raytracing", True)):
        try:
            setattr(sc.eevee, attr, val)
        except Exception:
            pass
sc.view_settings.view_transform = "Standard"
sc.render.image_settings.file_format = "PNG"
sc.render.film_transparent = False

world = bpy.data.worlds.new("w")
world.use_nodes = True
bg = world.node_tree.nodes["Background"]
bg.inputs[0].default_value = (0.62, 0.64, 0.68, 1)
bg.inputs[1].default_value = 1.0
sc.world = world

def light(name, kind_, loc, energy, size=4, rot_target=Vector((0, 0, 0.5)), color=(1, 1, 1)):
    d = bpy.data.lights.new(name, kind_)
    d.energy = energy
    d.color = color
    if kind_ == "AREA":
        d.size = size
    ob = bpy.data.objects.new(name, d)
    sc.collection.objects.link(ob)
    ob.location = loc
    direction = rot_target - ob.location
    ob.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    return ob

sun = bpy.data.lights.new("sun", "SUN")
sun.energy = 2.0
sun.angle = math.radians(6)
sun_ob = bpy.data.objects.new("sun", sun)
sc.collection.objects.link(sun_ob)
sun_ob.rotation_euler = (math.radians(52), math.radians(8), math.radians(-35))
light("fill", "AREA", Vector((-6, -5, 3.5)), 500, 6)
light("rim", "AREA", Vector((5, 6, 3.0)), 450, 5)

# ground
bpy.ops.mesh.primitive_plane_add(size=800, location=(0, 0, -0.001))
ground = bpy.context.active_object
gm = bpy.data.materials.new("ground")
gm.use_nodes = True
gm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.30, 0.31, 0.33, 1)
gm.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.55
ground.data.materials.append(gm)

cam_d = bpy.data.cameras.new("cam")
cam = bpy.data.objects.new("cam", cam_d)
sc.collection.objects.link(cam)
sc.camera = cam
tt = cam.constraints.new("TRACK_TO")
tt.track_axis = "TRACK_NEGATIVE_Z"
tt.up_axis = "UP_Y"
tgt = bpy.data.objects.new("tgt", None)
sc.collection.objects.link(tgt)
tt.target = tgt


def shoot(name, cam_pos, target, lens=50, res=(1600, 900)):
    cam.location = cam_pos
    tgt.location = target
    cam_d.lens = lens
    cam_d.clip_start = 0.05
    cam_d.clip_end = 100
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.filepath = os.path.join(OUT, name + ".png")
    bpy.ops.render.render(write_still=True)
    print("rendered", sc.render.filepath, flush=True)


# ---------------------------------------------------------------- whole-car views
b = an["descriptor_body"]  # xmin ymin zmin xmax ymax zmax (glTF space)
cx, cz = (b[0] + b[3]) / 2, (b[2] + b[5]) / 2
cy = b[4] * 0.42
L = b[5] - b[2]
target = G(cx, cy, cz)
dist = 1.5 * L
def azel(az_deg, el_deg, d):  # azimuth 0 = from the front, +90 = from the car's right (+X)
    az, el = math.radians(az_deg), math.radians(el_deg)
    return G(cx + d * math.sin(az) * math.cos(el), cy + d * math.sin(el), cz + d * math.cos(az) * math.cos(el))

shoot("car_front34", azel(-38, 11, dist), target)
shoot("car_side", azel(-90, 3, dist * 1.12), target, lens=60)
shoot("car_rear34", azel(142, 12, dist), target)
shoot("car_top", azel(-90, 78, dist * 1.1), target, lens=60)

# ---------------------------------------------------------------- wheel-section views (front-left)
wf = an["descriptor_wheels"]["FL"]
wp = G(wf["x"], wf["y"], wf["z"])           # wheel pivot, Blender space
out_dir = Vector((-1, 0, 0))                # outward from the car for the left wheel
fwd = Vector((0, -1, 0))                    # car nose in Blender space
up = Vector((0, 0, 1))
R = wf["radius"]

def show_only(fl_kinds):
    for o in bpy.data.objects:
        if o.type == "MESH" and o is not ground:
            o.hide_render = True
    ground.hide_render = True
    for k, o, it in parts["FL"]:
        if k in fl_kinds:
            o.hide_render = False

def show_all():
    for o in bpy.data.objects:
        if o.type == "MESH":
            o.hide_render = False

wres = (1200, 900)
# 1. in-context
show_all()
shoot("wheel_context", wp + out_dir * 2.2 + fwd * 1.1 + up * 0.35, wp, lens=70, res=wres)
# 2. assembled, body hidden, three-quarter and straight-on
show_only({"rim", "tire", "disc", "caliper"})
shoot("wheel_assembled_34", wp + out_dir * 1.5 + fwd * 0.55 + up * 0.35, wp, lens=70, res=wres)
shoot("wheel_assembled_side", wp + out_dir * 2.4, wp, lens=70, res=wres)
# 3. rim only / tyre only
show_only({"rim"})
shoot("wheel_rim_only", wp + out_dir * 1.5 + fwd * 0.55 + up * 0.35, wp, lens=70, res=wres)
show_only({"tire"})
shoot("wheel_tire_only", wp + out_dir * 1.5 + fwd * 0.55 + up * 0.35, wp, lens=70, res=wres)
# 4. exploded along the axle: tyre out, rim centre, disc and caliper in
show_only({"rim", "tire", "disc", "caliper"})
shift = {"tire": out_dir * 0.30, "rim": Vector((0, 0, 0)), "disc": -out_dir * 0.18, "caliper": -out_dir * 0.38}
bpy.context.view_layer.update()
orig = {}
for k, o, it in parts["FL"]:
    mw = o.matrix_world.copy()
    orig[o] = mw
    mw.translation = mw.translation + shift[k]
    o.matrix_world = mw
shoot("wheel_exploded", wp + out_dir * 0.4 + fwd * 2.3 + up * 0.55, wp - out_dir * 0.05, lens=60, res=wres)
for o, mw in orig.items():
    o.matrix_world = mw

# summary for the deck
json.dump({"parts": {w: [{"kind": k, "object": o.name, "mesh": it["mesh_name"]} for k, o, it in parts[w]] for w in parts}},
          open(os.path.join(OUT, "parts.json"), "w"), indent=1)
