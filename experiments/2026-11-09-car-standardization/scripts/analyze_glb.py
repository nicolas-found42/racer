#!/usr/bin/env python3
"""Per-car GLB + .vehicle descriptor analysis for the car-standardization kit.

Stdlib only. For every car it reports the glTF inventory (nodes, meshes, materials,
images, extensions) and, for each of the four wheels, the exact world-space geometry
of every mesh bound to that wheel by the .vehicle descriptor: per-primitive vertex
counts, axial extent, inner/outer radius and a (axial, radial) silhouette profile.

Usage: analyze_glb.py <models-dir> <output.json>
"""
import json, math, struct, sys, os

CT = {5120: ("b", 1), 5121: ("B", 1), 5122: ("h", 2), 5123: ("H", 2), 5125: ("I", 4), 5126: ("f", 4)}
NC = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}


def load_glb(path):
    b = open(path, "rb").read()
    assert b[:4] == b"glTF", path
    off, js, bin_ = 12, None, b""
    while off < len(b):
        n, t = struct.unpack("<II", b[off:off + 8])
        d = b[off + 8:off + 8 + n]
        if t == 0x4E4F534A:
            js = json.loads(d)
        elif t == 0x004E4942:
            bin_ = d
        off += 8 + n
    return js, bin_


def read_accessor(g, bin_, idx):
    a = g["accessors"][idx]
    bv = g["bufferViews"][a["bufferView"]]
    fmt, size = CT[a["componentType"]]
    nc = NC[a["type"]]
    stride = bv.get("byteStride") or size * nc
    base = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
    out = []
    for i in range(a["count"]):
        o = base + i * stride
        out.append(struct.unpack_from("<" + fmt * nc, bin_, o))
    return out


def mat_mul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(4)) for j in range(4)] for i in range(4)]


def node_local(n):
    if "matrix" in n:
        m = n["matrix"]
        return [[m[c * 4 + r] for c in range(4)] for r in range(4)]  # column-major -> rows
    t = n.get("translation", [0, 0, 0])
    q = n.get("rotation", [0, 0, 0, 1])
    s = n.get("scale", [1, 1, 1])
    x, y, z, w = q
    R = [[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
         [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
         [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]]
    return [[R[0][0] * s[0], R[0][1] * s[1], R[0][2] * s[2], t[0]],
            [R[1][0] * s[0], R[1][1] * s[1], R[1][2] * s[2], t[1]],
            [R[2][0] * s[0], R[2][1] * s[1], R[2][2] * s[2], t[2]],
            [0, 0, 0, 1]]


def world_matrices(g):
    nodes = g["nodes"]
    parent = {}
    for i, n in enumerate(nodes):
        for c in n.get("children", []):
            parent[c] = i
    cache = {}

    def wm(i):
        if i in cache:
            return cache[i]
        m = node_local(nodes[i])
        if i in parent:
            m = mat_mul(wm(parent[i]), m)
        cache[i] = m
        return m
    return [wm(i) for i in range(len(nodes))], parent


def parse_vehicle(path):
    d = {"wheels": {}, "groups": {}}
    for line in open(path):
        p = line.split()
        if not p:
            continue
        if p[0] == "name":
            d["name"] = line.split(" ", 1)[1].strip().strip('"')
        elif p[0] == "RACER_VEHICLE":
            d["format"] = int(p[1])
        elif p[0] == "body":
            d["body"] = [float(x) for x in p[1:7]]
        elif p[0] == "wheel":
            d["wheels"][p[1]] = dict(zip(("x", "y", "z", "radius", "width"), map(float, p[2:7])))
        elif p[0] == "group":
            node = int(p[1])
            rest = p[2:]
            if rest[0] in ("body", "-1"):
                d["groups"][node] = ("body", None)
            elif rest[0] == "wheel":
                d["groups"][node] = ("wheel", rest[1])
            elif rest[0] == "carrier":
                d["groups"][node] = ("carrier", rest[1])
            else:
                d["groups"][node] = ("wheel", ["FL", "FR", "RL", "RR"][int(rest[0])])
    return d


def png_size(data):
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return struct.unpack(">II", data[16:24])
    return None


def analyze(glb, veh):
    g, bin_ = load_glb(glb)
    d = parse_vehicle(veh)
    wms, parent = world_matrices(g)
    nodes = g["nodes"]

    images = []
    for im in g.get("images", []):
        sz = None
        if "bufferView" in im:
            bv = g["bufferViews"][im["bufferView"]]
            sz = png_size(bin_[bv.get("byteOffset", 0):bv.get("byteOffset", 0) + 32])
        images.append({"name": im.get("name"), "mime": im.get("mimeType"), "size": sz,
                       "bytes": g["bufferViews"][im["bufferView"]]["byteLength"] if "bufferView" in im else None})
    mats = []
    for m in g.get("materials", []):
        pbr = m.get("pbrMetallicRoughness", {})
        mats.append({"name": m.get("name"), "baseColor": pbr.get("baseColorFactor"),
                     "metallic": pbr.get("metallicFactor"), "roughness": pbr.get("roughnessFactor"),
                     "baseTex": "baseColorTexture" in pbr, "mrTex": "metallicRoughnessTexture" in pbr,
                     "normalTex": "normalTexture" in m, "emissive": m.get("emissiveFactor"),
                     "alpha": m.get("alphaMode", "OPAQUE"), "doubleSided": m.get("doubleSided", False),
                     "extensions": sorted(m.get("extensions", {})), "extras": m.get("extras")})

    res = {"glb": os.path.basename(glb), "descriptor": d.get("name"), "descriptor_format": d.get("format"),
           "glb_bytes": os.path.getsize(glb), "generator": g["asset"].get("generator"),
           "asset_extras": g["asset"].get("extras"), "extensionsUsed": g.get("extensionsUsed", []),
           "counts": {k: len(g.get(k, [])) for k in ("nodes", "meshes", "materials", "images", "textures", "skins", "animations")},
           "images": images, "materials": mats, "descriptor_wheels": d["wheels"], "descriptor_body": d.get("body"),
           "wheel_nodes": {}, "body_node_count": sum(1 for v in d["groups"].values() if v[0] == "body")}

    def bucket(node):
        # which wheel is this node bound to (directly or via a parent in the descriptor)?
        cur = node
        while cur is not None:
            if cur in d["groups"] and d["groups"][cur][0] != "body":
                return d["groups"][cur]
            cur = parent.get(cur)
        return None

    for ni, n in enumerate(nodes):
        if "mesh" not in n:
            continue
        b = bucket(ni)
        if not b:
            continue
        role, w = b
        wheel = d["wheels"][w]
        cx, cy, cz = wheel["x"], wheel["y"], wheel["z"]
        mesh = g["meshes"][n["mesh"]]
        M = wms[ni]
        prims = []
        for pi, p in enumerate(mesh["primitives"]):
            pos = read_accessor(g, bin_, p["attributes"]["POSITION"])
            tri = (g["accessors"][p["indices"]]["count"] // 3) if "indices" in p else len(pos) // 3
            ax, rad, pts = [], [], []
            for v in pos:
                X = M[0][0] * v[0] + M[0][1] * v[1] + M[0][2] * v[2] + M[0][3]
                Y = M[1][0] * v[0] + M[1][1] * v[1] + M[1][2] * v[2] + M[1][3]
                Z = M[2][0] * v[0] + M[2][1] * v[1] + M[2][2] * v[2] + M[2][3]
                a = X - cx
                r = math.hypot(Y - cy, Z - cz)
                ax.append(a); rad.append(r)
            # mirror-normalise: outward axial direction is away from the car centre line
            sgn = 1.0 if cx > 0 else -1.0
            axo = [a * sgn for a in ax]
            step = max(1, len(axo) // 300)
            pts = [(round(axo[i], 4), round(rad[i], 4)) for i in range(0, len(axo), step)]
            mat = mats[p["material"]]["name"] if "material" in p else None
            prims.append({"material": mat, "verts": len(pos), "tris": tri,
                          "axial_min": round(min(axo), 4), "axial_max": round(max(axo), 4),
                          "r_min": round(min(rad), 4), "r_max": round(max(rad), 4), "profile": pts})
        res["wheel_nodes"].setdefault(w, []).append({"node": ni, "name": n.get("name"), "role": role,
                                                     "mesh": n["mesh"], "mesh_name": mesh.get("name"),
                                                     "prims": prims})
    # parent chain info for hub-style rigs
    res["hub_parented"] = any(ni in parent and nodes[parent[ni]].get("name", "").upper().startswith("HUB")
                              for w in res["wheel_nodes"].values() for ni in [x["node"] for x in w])
    return res


if __name__ == "__main__":
    mdir, out = sys.argv[1], sys.argv[2]
    result = {}
    for f in sorted(os.listdir(mdir)):
        if f.endswith(".glb"):
            key = f[:-4]
            result[key] = analyze(os.path.join(mdir, f), os.path.join(mdir, key + ".vehicle"))
    json.dump(result, open(out, "w"), indent=1)
    for k, r in result.items():
        print("==", k, r["counts"], "ext:", r["extensionsUsed"], "gen:", r["generator"])
        for w, items in sorted(r["wheel_nodes"].items()):
            if w != "FL":
                continue
            for it in items:
                for p in it["prims"]:
                    print("  FL", it["role"], it["node"], it["name"], "|", p["material"], "v=%d" % p["verts"],
                          "ax[%.3f,%.3f] r[%.3f,%.3f]" % (p["axial_min"], p["axial_max"], p["r_min"], p["r_max"]))
