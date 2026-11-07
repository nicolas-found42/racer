#!/usr/bin/env python3
"""Append explicitly authored access stairs to two exact residential source pilots."""
import argparse
import copy
import hashlib
import io
import json
import math
from pathlib import Path
import struct
from PIL import Image
from install_cars import regular_bytes, immutable
from prepare_city_blocks import accessor, node_matrix, multiply, transform, platform_path, IDENTITY
from prepare_gt4_vehicle import unpack, pack

PINS = {
    'c': '56623728239c2d434e73ccb2ff0367e01d58cb3ff62e18bdc7045de48f246d9e',
    'd': '722df876abe3479dc597fa5ada84a31d4ca4c061f8df6d3693878ed8c79108e2',
}
SELECTORS = {
    'c': {'node': 4, 'mesh': 4, 'material': 4, 'native_model': 99, 'native_triangles': [8, 9, 10, 11], 'fronts': [(1, 0, 0), (0, 0, -1)]},
    'd': {'node': 0, 'mesh': 0, 'material': 0, 'native_model': 11, 'native_triangles': [4, 5, 6, 7], 'fronts': [(-1, 0, 0), (0, 0, 1)]},
}
LIMIT = 4 * 1024**2
RGBA_LIMIT = 8 * 1024**2
VERTEX_LIMIT = 10416


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def subtract(a, b):
    return tuple(x - y for x, y in zip(a, b))


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def values(doc, blob, index):
    spec, rows = accessor(doc, blob, index)
    formats = {5126: 'f', 5123: 'H', 5125: 'I'}
    widths = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3}
    require(spec['componentType'] in formats and spec['type'] in widths, 'source_accessor_format')
    return [struct.unpack('<' + formats[spec['componentType']] * widths[spec['type']], row) for row in rows]


def scene_geometry(doc, blob):
    roots = doc['scenes'][doc.get('scene', 0)]['nodes']
    seen, positions, matrices, vertices = set(), [], {}, 0

    def visit(index, parent):
        nonlocal vertices
        require(type(index) is int and 0 <= index < len(doc['nodes']) and index not in seen, 'scene_cycle_or_shared')
        seen.add(index)
        node = doc['nodes'][index]
        matrix = multiply(parent, node_matrix(node))
        matrices[index] = matrix
        if 'mesh' in node:
            for primitive in doc['meshes'][node['mesh']]['primitives']:
                points = values(doc, blob, primitive['attributes']['POSITION'])
                vertices += len(points)
                require(vertices <= VERTEX_LIMIT, 'vertex_budget')
                positions.extend(transform(matrix, point) for point in points)
        for child in node.get('children', []):
            visit(child, matrix)

    for root in roots:
        visit(root, IDENTITY)
    require(positions, 'empty_scene')
    return positions, matrices, vertices


def doors(doc, blob, variant, matrices):
    selector = SELECTORS[variant]
    node = doc['nodes'][selector['node']]
    require(node.get('mesh') == selector['mesh'], 'door_node_identity')
    primitive = doc['meshes'][selector['mesh']]['primitives'][0]
    require(primitive['material'] == selector['material'], 'door_material_identity')
    proof = primitive.get('extras', {})
    require(proof.get('source_mesh') == selector['native_model'] and proof.get('source_primitive') == 0 and
            proof.get('source_triangle_indices') == selector['native_triangles'], 'door_native_geometry_identity')
    material = doc['materials'][primitive['material']]
    texture = material['pbrMetallicRoughness']['baseColorTexture']['index']
    image = doc['images'][doc['textures'][texture]['source']]
    require(image['name'] == 'l_ho_ss_door_11.dds', 'door_texture_identity')
    points = [transform(matrices[selector['node']], point) for point in values(doc, blob, primitive['attributes']['POSITION'])]
    indices = [row[0] for row in values(doc, blob, primitive['indices'])]
    require(len(indices) == 12, 'door_quad_count')
    result = []
    for pair in range(2):
        selected = indices[pair * 6:(pair + 1) * 6]
        unique = sorted(set(selected))
        require(len(unique) == 4, 'door_quad_shape')
        vertices = [points[index] for index in unique]
        sill = min(point[1] for point in vertices)
        bottom = [point for point in vertices if abs(point[1] - sill) < 1e-5]
        top = [point for point in vertices if point[1] > sill + 2]
        require(len(bottom) == len(top) == 2 and .5 < sill < 1.08, 'door_sill_or_shape')
        first, last = sorted(bottom)
        difference = subtract(last, first)
        width = math.hypot(difference[0], difference[2])
        require(.7 < width < 1.8 and abs(difference[1]) < 1e-5, 'door_width_or_level')
        tangent = (difference[0] / width, 0., difference[2] / width)
        outward = (-tangent[2], 0., tangent[0])
        expected = selector['fronts'][pair]
        if dot(outward, expected) < 0:
            outward = tuple(-value for value in outward)
        require(dot(outward, expected) > .95, 'door_facing_ambiguous')
        result.append({'quad': pair, 'source_node': selector['node'], 'source_mesh': selector['mesh'],
                       'source_primitive': 0, 'source_material': selector['material'],
                       'native_model': selector['native_model'], 'native_geometry': 0,
                       'native_triangles': selector['native_triangles'][pair * 2:pair * 2 + 2],
                       'native_vertex_ids': [proof['source_vertex_indices'][index] for index in unique],
                       'scene_bottom_vertices': bottom, 'scene_quad_vertices': vertices,
                       'center': [(first[axis] + last[axis]) / 2 for axis in range(3)],
                       'sill': sill, 'door_width': width, 'tangent': tangent, 'outward': outward})
    return result


def access_geometry(door):
    sill = door['sill']
    risers = max(6, math.ceil(sill / .18))
    rise, tread, landing = sill / risers, .30, .80
    width = min(2.2, door['door_width'] + .4)
    require(rise <= .18 and tread >= .27 and landing >= .75 and width >= door['door_width'], 'stair_design_bounds')
    positions, normals, uvs, indices, boxes = [], [], [], [], []
    tangent, outward, center = door['tangent'], door['outward'], door['center']

    def point(u, y, distance):
        return (center[0] + tangent[0] * u + outward[0] * distance,
                y, center[2] + tangent[2] * u + outward[2] * distance)

    def box(first, last, height):
        base = 0.
        corners = [point(u, y, distance) for u, y, distance in
                   [(-width / 2, base, first), (width / 2, base, first),
                    (width / 2, height, first), (-width / 2, height, first),
                    (-width / 2, base, last), (width / 2, base, last),
                    (width / 2, height, last), (-width / 2, height, last)]]
        faces = [((0, 3, 2, 1), tuple(-v for v in outward)), ((4, 5, 6, 7), outward),
                 ((0, 4, 7, 3), tuple(-v for v in tangent)), ((1, 2, 6, 5), tangent),
                 ((0, 1, 5, 4), (0, -1, 0)), ((3, 7, 6, 2), (0, 1, 0))]
        for order, normal in faces:
            vertices = [corners[index] for index in order]
            if dot(cross(subtract(vertices[1], vertices[0]), subtract(vertices[2], vertices[0])), normal) < 0:
                vertices.reverse()
            first_index = len(positions)
            positions.extend(vertices)
            normals.extend([normal] * 4)
            u, v = math.dist(vertices[0], vertices[1]), math.dist(vertices[1], vertices[2])
            uvs.extend([(0, 0), (u, 0), (u, v), (0, v)])
            indices.extend(first_index + index for index in (0, 1, 2, 0, 2, 3))
        boxes.append({'outward_range': [first, last], 'top_y': height, 'footing_y': base})

    box(-.025, landing, sill)
    for step in range(1, risers):
        box(landing + (step - 1) * tread, landing + step * tread, sill - step * rise)
    design = {'risers': risers, 'exposed_rise': rise, 'tread': tread, 'landing_depth': landing,
              'width': width, 'footing_y': 0., 'top_y': sill,
              'outward_extension': landing + (risers - 1) * tread, 'boxes': boxes}
    return positions, normals, uvs, indices, design


def prepare(data, variant):
    require(variant in PINS and len(data) <= LIMIT and digest(data) == PINS[variant], 'source_pin_or_size')
    doc, binary = unpack(data)
    original = copy.deepcopy(doc)
    prefix = bytes(binary)
    require('racerAuthoredEntranceAccess' not in doc.get('extras', {}), 'already_derived')
    require(len(doc.get('buffers', [])) == 1 and 'uri' not in doc['buffers'][0], 'embedded_source_required')
    rgba = 0
    for image in doc.get('images', []):
        require(image.get('mimeType') == 'image/png' and 'uri' not in image, 'embedded_png_required')
        view = doc['bufferViews'][image['bufferView']]
        start, size = view.get('byteOffset', 0), view['byteLength']
        with Image.open(io.BytesIO(binary[start:start + size])) as decoded:
            require(decoded.format == 'PNG' and 0 < decoded.width <= 2048 and 0 < decoded.height <= 2048, 'png_dimensions')
            rgba += decoded.width * decoded.height * 4
            decoded.verify()
        require(rgba <= RGBA_LIMIT, 'rgba_budget')
    source_points, matrices, source_vertices = scene_geometry(doc, binary)
    selected_doors = doors(doc, binary, variant, matrices)
    authored_positions, authored_normals, authored_uvs, authored_indices, records = [], [], [], [], []
    for door in selected_doors:
        positions, normals, uvs, indices, design = access_geometry(door)
        offset = len(authored_positions)
        authored_positions.extend(positions)
        authored_normals.extend(normals)
        authored_uvs.extend(uvs)
        authored_indices.extend(index + offset for index in indices)
        records.append({'door': door, 'design': design, 'first_vertex': offset, 'vertex_count': len(positions)})
    require(source_vertices + len(authored_positions) <= VERTEX_LIMIT, 'vertex_budget')
    all_points = source_points + authored_positions
    bounds = [[min(point[axis] for point in all_points) for axis in range(3)],
              [max(point[axis] for point in all_points) for axis in range(3)]]
    require(bounds[1][0] - bounds[0][0] <= 23 and bounds[1][2] - bounds[0][2] <= 26, 'access_footprint')

    def append_accessor(rows, kind, component):
        binary.extend(b'\0' * (-len(binary) % 4))
        start = len(binary)
        width = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3}[kind]
        code = 'f' if component == 5126 else 'I'
        payload = b''.join(struct.pack('<' + code * width, *row) for row in rows)
        require(start + len(payload) <= LIMIT, 'output_budget')
        binary.extend(payload)
        doc['buffers'][0]['byteLength'] = len(binary)
        doc['bufferViews'].append({'buffer': 0, 'byteOffset': start, 'byteLength': len(payload)})
        value = {'bufferView': len(doc['bufferViews']) - 1, 'componentType': component, 'type': kind, 'count': len(rows)}
        if kind == 'VEC3':
            value['min'] = [min(row[axis] for row in rows) for axis in range(3)]
            value['max'] = [max(row[axis] for row in rows) for axis in range(3)]
        doc['accessors'].append(value)
        return len(doc['accessors']) - 1

    normal_repair = None
    active_roots = original['scenes'][original.get('scene', 0)]['nodes']
    if variant == 'c':
        primitive = original['meshes'][2]['primitives'][0]
        proof = primitive.get('extras', {})
        require(proof.get('source_mesh') == 43 and proof.get('source_material') == 0, 'repair_geometry_identity')
        normal_index = primitive['attributes']['NORMAL']
        normal_spec, raw_normals = accessor(original, prefix, normal_index)
        normals = values(original, prefix, normal_index)
        require([i for i, row in enumerate(normals) if dot(row, row) == 0] == [715, 716, 717], 'repair_zero_rows')
        indices = [row[0] for row in values(original, prefix, primitive['indices'])]
        require(indices[457 * 3:458 * 3] == [715, 716, 717] and proof['source_triangle_indices'][457] == 1443,
                'repair_triangle_identity')
        points = values(original, prefix, primitive['attributes']['POSITION'])
        face = cross(subtract(points[716], points[715]), subtract(points[717], points[715]))
        length = math.sqrt(dot(face, face))
        require(length > 1e-12, 'repair_degenerate_face')
        replacement = tuple(component / length for component in face)
        for row in (715, 716, 717):
            normals[row] = replacement
        replacement_index = append_accessor(normals, 'VEC3', 5126)
        # Copy exact untouched rows; only the pinned zero rows acquire float32 fallback normals.
        _, repaired_rows = accessor(doc, binary, replacement_index)
        require(all(raw_normals[i] == repaired_rows[i] for i in range(len(normals)) if i not in (715, 716, 717)), 'repair_changed_other_rows')
        cloned_mesh = copy.deepcopy(original['meshes'][2])
        cloned_mesh['primitives'][0]['attributes']['NORMAL'] = replacement_index
        cloned_mesh_index = len(doc['meshes'])
        doc['meshes'].append(cloned_mesh)
        node_offset = len(doc['nodes'])
        for node in original['nodes']:
            clone = copy.deepcopy(node)
            if clone.get('mesh') == 2:
                clone['mesh'] = cloned_mesh_index
            if 'children' in clone:
                clone['children'] = [index + node_offset for index in clone['children']]
            doc['nodes'].append(clone)
        active_roots = [index + node_offset for index in active_roots]
        normal_repair = {'authority': 'Authored runtime equivalent of MeshAsset zero-normal face fallback; native zero bytes remain preserved',
                         'source_mesh': 2, 'native_model': 43, 'native_triangle': 1443, 'rows': [715, 716, 717],
                         'source_accessor': normal_index, 'replacement_accessor': replacement_index,
                         'replacement_normal': replacement, 'double_area': length}

    attributes = {'POSITION': append_accessor(authored_positions, 'VEC3', 5126),
                  'NORMAL': append_accessor(authored_normals, 'VEC3', 5126),
                  'TEXCOORD_0': append_accessor(authored_uvs, 'VEC2', 5126)}
    indices = append_accessor([(index,) for index in authored_indices], 'SCALAR', 5125)
    material = len(doc['materials'])
    doc['materials'].append({'name': 'Racer authored entrance concrete', 'doubleSided': False,
                             'pbrMetallicRoughness': {'baseColorFactor': [.25, .26, .25, 1], 'roughnessFactor': .9, 'metallicFactor': 0},
                             'extras': {'authority': 'Authored concrete, not a recovered native material', 'uv_policy': 'One UV unit per Racer scene unit on each rectangular face; currently untextured'}})
    doc['meshes'].append({'name': 'Racer authored entrance access', 'primitives': [{'attributes': attributes, 'indices': indices, 'material': material, 'mode': 4}]})
    doc['nodes'].append({'mesh': len(doc['meshes']) - 1, 'name': 'Racer authored entrance access'})
    doc['scenes'].append({'nodes': active_roots + [len(doc['nodes']) - 1]})
    doc['scene'] = len(doc['scenes']) - 1
    policy = {'authority': 'Explicitly authored decorative landing/stairs; no native access, object ownership, physical units or collision behavior recovered',
              'source_sha256': PINS[variant], 'source_bin_prefix_sha256': digest(prefix), 'source_bin_prefix_bytes': len(prefix),
              'source_vertices': source_vertices, 'authored_vertices': len(authored_positions), 'bounds': bounds,
              'source_door_bindings': records, 'decoded_rgba_bytes': rgba, 'authored_normal_fallback': normal_repair,
              'original_arrays': 'All original nodes/meshes/accessors/views/images/materials and BIN prefix retained unchanged.',
              'active_graph': ('Appended active scene uses cloned original roots with only the pinned three-row NORMAL fallback plus authored access node.' if variant == 'c' else 'Appended active scene reuses original roots plus authored access node.')}
    doc.setdefault('extras', {})['racerAuthoredEntranceAccess'] = policy
    doc['buffers'][0]['byteLength'] = len(binary)
    for key in ('nodes', 'meshes', 'accessors', 'bufferViews', 'materials', 'scenes'):
        require(doc[key][:len(original[key])] == original[key], 'source_metadata_changed')
    require(bytes(binary[:len(prefix)]) == prefix, 'source_prefix_changed')
    output = pack(doc, binary)
    require(len(output) <= LIMIT, 'output_budget')
    manifest = {**policy, 'sha256': digest(output), 'bytes': len(output), 'variant': variant}
    return {'access.glb': output, 'manifest.json': (json.dumps(manifest, indent=2, sort_keys=True) + '\n').encode()}


def publish(output, files):
    output = platform_path(output)
    require(not any(path.is_symlink() for path in (output, *output.parents)), 'symlink_refused')
    for name, data in files.items():
        path = output / name
        if path.exists() or path.is_symlink():
            require(regular_bytes(path, len(data)) == data, 'output_conflict')
    output.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        immutable(output / name, data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--variant', choices=sorted(PINS), required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    files = prepare(regular_bytes(platform_path(args.source), LIMIT), args.variant)
    publish(args.output, files)
    print(json.dumps(json.loads(files['manifest.json'])))


if __name__ == '__main__':
    main()
