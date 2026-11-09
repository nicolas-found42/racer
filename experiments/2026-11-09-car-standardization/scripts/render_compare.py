"""Render any car GLB under the kit's shared rig and measure its mesh extents (Blender, headless).

blender -b --python render_compare.py -- <glb> <out-dir> <label>

Writes <out-dir>/<label>_{front34,side,rear34,front,rear}.png and <out-dir>/<label>_dims.json
(world-space extents of all mesh vertices: length along the nose axis, width, height, and the
lowest/highest points). Dimensions include mirrors, antennas and wheels, so they are mesh extents,
not manufacturer figures. Same lighting rig as render_kit.py.
"""
import sys, os, json, math
import bpy
from mathutils import Vector

glb, out, label = sys.argv[sys.argv.index("--") + 1:][:3]
os.makedirs(out, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb)

lo = Vector((1e9, 1e9, 1e9)); hi = Vector((-1e9, -1e9, -1e9))
for o in bpy.data.objects:
    if o.type != "MESH":
        continue
    for v in o.data.vertices:
        p = o.matrix_world @ v.co
        lo = Vector((min(lo.x, p.x), min(lo.y, p.y), min(lo.z, p.z)))
        hi = Vector((max(hi.x, p.x), max(hi.y, p.y), max(hi.z, p.z)))
# Blender space: X right, Y = -nose axis, Z up (glTF +Z nose -> Blender -Y)
dims = {"length_m": hi.y - lo.y, "width_m": hi.x - lo.x, "height_m": hi.z - lo.z,
        "lowest_m": lo.z, "highest_m": hi.z, "meshes": sum(1 for o in bpy.data.objects if o.type == "MESH")}
json.dump(dims, open(os.path.join(out, label + "_dims.json"), "w"), indent=1)

sc = bpy.context.scene
for eng in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
    try:
        sc.render.engine = eng
        break
    except TypeError:
        pass
try:
    sc.eevee.taa_render_samples = 64
except Exception:
    pass
sc.view_settings.view_transform = "Standard"
sc.render.image_settings.file_format = "PNG"
world = bpy.data.worlds.new("w"); world.use_nodes = True
bg = world.node_tree.nodes["Background"]; bg.inputs[0].default_value = (0.62, 0.64, 0.68, 1); bg.inputs[1].default_value = 1.0
sc.world = world

def light(name, loc, energy, size):
    d = bpy.data.lights.new(name, "AREA"); d.energy = energy; d.size = size
    ob = bpy.data.objects.new(name, d); sc.collection.objects.link(ob); ob.location = loc
    ob.rotation_euler = (Vector((0, 0, 0.5)) - ob.location).to_track_quat("-Z", "Y").to_euler()
sun = bpy.data.lights.new("sun", "SUN"); sun.energy = 2.0; sun.angle = math.radians(6)
so = bpy.data.objects.new("sun", sun); sc.collection.objects.link(so); so.rotation_euler = (math.radians(52), math.radians(8), math.radians(-35))
light("fill", Vector((-6, -5, 3.5)), 500, 6); light("rim", Vector((5, 6, 3.0)), 450, 5)
bpy.ops.mesh.primitive_plane_add(size=800, location=(0, 0, lo.z - 0.001))
g = bpy.context.active_object; gm = bpy.data.materials.new("g"); gm.use_nodes = True
gm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.30, 0.31, 0.33, 1)
gm.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.55; g.data.materials.append(gm)
cd = bpy.data.cameras.new("c"); cam = bpy.data.objects.new("c", cd); sc.collection.objects.link(cam); sc.camera = cam
tt = cam.constraints.new("TRACK_TO"); tt.track_axis = "TRACK_NEGATIVE_Z"; tt.up_axis = "UP_Y"
tg = bpy.data.objects.new("t", None); sc.collection.objects.link(tg); tt.target = tg

cx, cy = (lo.x + hi.x) / 2, (lo.y + hi.y) / 2
cz = lo.z + dims["height_m"] * 0.45
L = dims["length_m"]; dist = 1.5 * L

def shoot(name, az, el, d, lens=50):
    # azimuth 0 = looking at the nose from the front; +90 = from the car's right
    a, e = math.radians(az), math.radians(el)
    cam.location = Vector((cx + d * math.sin(a) * math.cos(e), cy - d * math.cos(a) * math.cos(e), cz + d * math.sin(e)))
    tg.location = Vector((cx, cy, cz)); cd.lens = lens; cd.clip_start = 0.05; cd.clip_end = 200
    sc.render.resolution_x, sc.render.resolution_y = 1280, 720
    sc.render.filepath = os.path.join(out, "%s_%s.png" % (label, name))
    bpy.ops.render.render(write_still=True)

shoot("front34", -38, 11, dist)
shoot("side", -90, 3, dist * 1.12, 60)
shoot("rear34", 142, 12, dist)
shoot("front", 0, 5, dist * 1.1, 60)
shoot("rear", 180, 5, dist * 1.1, 60)
print("DIMS", label, json.dumps(dims))
