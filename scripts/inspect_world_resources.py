#!/usr/bin/env python3
"""Bounded MCLA RPF3 city-sector pilot, preserving native coordinates.

City root/piece/LOD field mapping: Raskulk/MCLA-Tools xcs2obj.py at
68419ceef619c3a947062c1e9ecf44007839a274 (screened primary format reference).
Geometry and Xenos decoding use explicitly supplied, hash-pinned qualified
helpers; this script neither downloads dependencies nor executes their CLIs.
Only diffuse base maps are previewed. Original shader names, buckets and all
sampler bindings remain in the report. Layered road/terrain, lighting, alpha,
normal/specular and other original shader behavior are not reconstructed.
"""
import argparse
import hashlib
import importlib.util
import io
import json
import math
from pathlib import Path
import struct
import sys

ISO_SHA = '877a9415f695d27f8170d04d3f18aab13e2b4de3cbabda824e04c9338b2914e9'
ISO_BYTES = 7838695424
TOC_SHA = '0b484391fc986849deee863b52351cef828d4e8d37b7091d322d1c0f828c6623'
ARCHIVE_OFFSET = 1788608512
ARCHIVE_BYTES = 2130739200
ENTRY_COUNT = 23931
MEMBER_LIMIT = 8 * 1024 * 1024
OUTPUT_LIMIT = 48 * 1024 * 1024
SHARED_ENTRY = 2111
SHARED_STORED_LIMIT = 16 * 1024 * 1024
SHARED_DECODED_LIMIT = 32 * 1024 * 1024
PIXEL_WORK_LIMIT = 128 * 1024 * 1024
RGBA_LIMIT = 32 * 1024 * 1024
PINS = {
    'mcla_resource': '620dc3c6b1ed07059190c3fa61dabdfaae8fc9436e4726225cec00257a74ebd7',
    'mcla_lzx': 'c97b2effec18386fec32a9e488bb3172fec6fe6b3cf8cf1e7aefcfe776cc3dd5',
    'mcla_model': '4d645003cbe3cca2b567c440891bc3fadf1e4f2ac4bc2017586a107f057e540d',
    'mcla_texture': '12c0629e46017854df6c719783e7c3111e62063c8d3aa2346531bef159ff9469',
}


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def file_digest(path):
    h = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(4 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def read_small(path, limit):
    require(path.is_file() and not path.is_symlink(), 'input_not_regular')
    require(path.stat().st_size <= limit, 'input_byte_budget')
    with path.open('rb') as source:
        data = source.read(limit + 1)
    require(len(data) <= limit, 'input_byte_budget')
    return data


def helpers(directory, texture_path):
    loaded = {}
    for name in ('mcla_resource', 'mcla_lzx', 'mcla_model', 'mcla_texture'):
        path = texture_path if name == 'mcla_texture' else directory / (name + '.py')
        require(digest(read_small(path, 65536)) == PINS[name], 'helper_identity_' + name)
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        sys.modules[name] = module
        loaded[name] = module
    return loaded


def joaat(text):
    h = 0
    for byte in text.lower().encode('ascii'):
        h = (h + byte) & 0xffffffff
        h = (h + (h << 10)) & 0xffffffff
        h ^= h >> 6
    h = (h + (h << 3)) & 0xffffffff
    h ^= h >> 11
    return (h + (h << 15)) & 0xffffffff


def entry_range(words, archive_bytes=ARCHIVE_BYTES):
    _, stored, offset, flags = words
    require(not offset & 0x80000000, 'entry_is_directory')
    require(flags & 0xc0000000 == 0xc0000000, 'entry_not_resource')
    require(offset & 255 == 1, 'unsupported_resource_version')
    at = offset & 0x7fffff00
    require(20 <= stored <= MEMBER_LIMIT and at + stored <= archive_bytes, 'resource_range')
    return at, stored


def toc_entries(data):
    require(len(data) == 382976 and digest(data) == TOC_SHA, 'decoded_toc_identity')
    return [struct.unpack_from('<4I', data, i * 16) for i in range(ENTRY_COUNT)]


def city_indices(entries):
    """Traverse validated TOC ancestry; hash labels alone never identify geometry."""
    seen, result = set(), set()
    target = [joaat(s) for s in ('resources', 'city', 'sc')]
    def visit(index, chain):
        require(0 <= index < len(entries) and index not in seen, 'toc_tree_cycle_or_range')
        seen.add(index)
        name, _, word8, flags = entries[index]
        if word8 & 0x80000000:
            start, count = word8 & 0x7fffffff, flags & 0x3fffffff
            require(start + count <= len(entries), 'toc_directory_range')
            next_chain = chain + ([name] if index else [])
            for child in range(start, start + count):
                visit(child, next_chain)
        elif chain == target:
            result.add(index)
    visit(0, [])
    require(len(seen) == len(entries), 'toc_unreachable_entries')
    return result


def array(r, at, limit):
    pointer, count, capacity = r.unpack('IHH', at)
    require(count <= capacity <= limit, 'array_count_budget')
    require(count == 0 or pointer != 0, 'array_missing_pointer')
    base = r.offset(pointer, count * 4) if pointer else None
    return [] if not count else [r.u32(base + i * 4) for i in range(count)]


def name(r, pointer):
    if not pointer:
        return ''
    at = r.offset(pointer)
    end = r.data.find(b'\0', at, min(at + 257, r.virtual))
    require(end >= at, 'string_length_budget')
    value = r.data[at:end]
    require(all(32 <= b < 127 for b in value), 'string_not_ascii')
    return value.decode('ascii')


def texture_header(r, at, codec):
    """City texture VFT differs from cars; validate D3D fetch fields directly."""
    r.need(at, 64)
    d3d = r.pointer(at + 28, 52)
    require(d3d is not None, 'dictionary_texture_is_stub')
    width, height = r.unpack('2H', at + 32)
    require(0 < width <= 2048 and 0 < height <= 2048, 'texture_dimension_budget')
    fetch = r.unpack('6I', d3d + 28)
    code, swap = fetch[1] & 63, (fetch[1] >> 6) & 3
    require(code in codec.FORMATS, 'texture_format_unsupported')
    kind, block, block_bytes, expected_swap = codec.FORMATS[code]
    require(swap == expected_swap and fetch[0] >> 31 == 1, 'texture_layout_unsupported')
    require(((fetch[2] & 8191) + 1, ((fetch[2] >> 13) & 8191) + 1) == (width, height), 'texture_header_disagreement')
    pitch = ((fetch[0] >> 22) & 511) * 32
    require(pitch >= width and pitch % block == 0 and not fetch[1] & 0xf00, 'texture_pitch_alignment')
    shift = codec.packed_offset(width, height)
    packed = (shift[0] // block, shift[1] // block)
    columns = pitch // block
    extent = codec.tiled_extent(columns, (width + block - 1) // block + packed[0],
                                 (height + block - 1) // block + packed[1], block_bytes)
    base = r.offset(fetch[1] & 0xfffff000, extent)
    return dict(name=name(r, r.u32(at + 24)), width=width, height=height,
                format=kind, offset=base, block=block, block_bytes=block_bytes,
                columns=columns, packed=packed, fetch=list(fetch), source_at=at,
                stored_extent=extent)


def decode_sector(data, header, modules):
    require(header['type'] == 1, 'not_city_resource_type')
    r = modules['mcla_resource'].Resource(data, header['virtual'], header['physical'])
    require(r.u32(0) == 0x10b75c00, 'unsupported_city_root_vft')
    piece = r.pointer(16, 16)
    require(piece is not None, 'missing_sector_piece')
    shader_group, lod_map = r.pointer(piece + 8, 16), r.pointer(piece + 12, 32)
    require(shader_group is not None and lod_map is not None, 'missing_city_drawable')
    model_pointers = array(r, lod_map + 24, 1024)
    shader_pointers = array(r, shader_group + 8, 512)
    require(model_pointers and shader_pointers, 'empty_city_drawable')
    shaders = []
    for pointer in shader_pointers:
        at = r.offset(pointer, 60)
        count = r.u16(at + 24)
        require(count <= 128, 'shader_parameter_budget')
        values = r.pointer(at + 16, count * 4)
        types = r.pointer(at + 28, count)
        hashes = r.pointer(at + 36, count * 4)
        require(not count or all(v is not None for v in (values, types, hashes)), 'missing_shader_parameters')
        samplers, vectors = [], []
        for i in range(count):
            if r.u8(types + i) == 0:
                tex = r.pointer(values + i * 4, 32)
                samplers.append({'hash': r.u32(hashes + i * 4),
                                 'texture_name': name(r, r.u32(tex + 24)) if tex is not None else '',
                                 'texture_pointer': r.u32(values + i * 4)})
            else:
                kind = r.u8(types + i)
                require(kind <= 32, 'shader_vector_work_budget')
                pointer = r.pointer(values + i * 4, kind * 16)
                vectors.append({'hash': r.u32(hashes + i * 4), 'type': kind,
                                'raw_big_endian_hex': r.data[pointer:pointer + kind * 16].hex() if pointer is not None else None})
        shaders.append({'name': name(r, r.u32(at + 48)), 'draw_bucket': r.u8(at + 9), 'samplers': samplers, 'vectors': vectors})
    dictionary = r.pointer(8, 32)
    textures = {}
    if dictionary is not None:
        tex_pointers = array(r, dictionary + 24, 128)
        hashes_at = r.pointer(dictionary + 16, len(tex_pointers) * 4)
        require(r.u16(dictionary + 20) == len(tex_pointers) and (not tex_pointers or hashes_at is not None), 'dictionary_hash_count')
        for i, pointer in enumerate(tex_pointers):
            key = r.u32(hashes_at + i * 4)
            require(key not in textures, 'duplicate_texture_hash')
            textures[key] = texture_header(r, r.offset(pointer, 64), modules['mcla_texture'])
    models, geometries, vertices, indices = [], [], 0, 0
    for model_index, pointer in enumerate(model_pointers):
        at = r.offset(pointer, 28)
        geo_pointers = array(r, at + 4, 512)
        require(geo_pointers and len(geo_pointers) == r.u16(at + 26), 'geometry_count_disagreement')
        for gp in geo_pointers:
            ga = r.offset(gp, 80)
            vertices += r.u16(ga + 52)
            indices += r.u32(ga + 44)
        require(vertices <= 150000 and indices <= 450000 and len(geometries) + len(geo_pointers) <= 512, 'city_geometry_work_budget')
        model = modules['mcla_model'].model(r, at)
        require(not model['skinned'] and model['matrix_count'] == 0, 'city_skinning_or_matrix_unsupported')
        for geometry_index, g in enumerate(model['geometries']):
            require(type(g['shader']) is int and 0 <= g['shader'] < len(shaders), 'shader_index_range')
            require(all(math.isfinite(v) for p in g['position'] for v in p), 'nonfinite_position')
            for channel in ('normal', 'texcoord0'):
                if channel in g:
                    require(all(math.isfinite(v) for p in g[channel] for v in p), 'nonfinite_vertex_attribute')
            geometries.append(dict(g, model=model_index, geometry=geometry_index))
        models.append({'geometry_count': len(model['geometries']), 'sphere': model['sphere']})
    require(geometries, 'city_without_geometry')
    points = [p for g in geometries for p in g['position']]
    bounds = [[min(p[i] for p in points) for i in range(3)], [max(p[i] for p in points) for i in range(3)]]
    return r, dict(models=models, geometries=geometries, shaders=shaders, textures=textures, bounds=bounds)


def texture_hash(value):
    value = value.lower()
    if value.endswith('.dds'):
        value = value[:-4]
    return joaat(value + '.dds')


def preview_glb(r, sector, modules, provenance):
    from PIL import Image
    blob = bytearray()
    doc = dict(asset={'version': '2.0', 'generator': 'Racer bounded MCLA city pilot'},
               buffers=[{}], bufferViews=[], accessors=[], images=[], samplers=[{'wrapS': 10497, 'wrapT': 10497}],
               textures=[], materials=[], meshes=[], nodes=[], scenes=[{'nodes': []}], scene=0,
               extras={'source': provenance, 'source_coordinates': 'Native XYZ unchanged; no centering, axis conversion, scale, or placement invented.',
                       'limitations': ['Diffuse-only opaque authored preview. Native blending/lighting/material layering is not reconstructed.',
                                       'Terrain multi-sampler, decals, normal/specular maps and missing external texture dependencies remain explicit.',
                                       'Resource geometry is static; native streaming/LOD/physics behavior is unverified.'],
                       'preview_policies': sector.get('preview_policies', []),
                       'omitted_geometries': sector.get('omitted_geometries', []),
                       'raw_color_layout': 'Custom SOURCE_COLOR attributes preserve four consecutive native bytes; type9 is Colour, not UByte4. ARGB/RGBA channel meaning is not inferred.'})
    def view(data):
        blob.extend(b'\0' * (-len(blob) % 4))
        index = len(doc['bufferViews'])
        doc['bufferViews'].append({'buffer': 0, 'byteOffset': len(blob), 'byteLength': len(data)})
        blob.extend(data)
        return index
    def accessor(rows, kind, code, fmt):
        values = [v for row in rows for v in row]
        data = struct.pack('<' + str(len(values)) + fmt, *values)
        a = {'bufferView': view(data), 'componentType': code, 'count': len(rows), 'type': kind}
        if kind == 'VEC3':
            a['min'] = [min(row[i] for row in rows) for i in range(3)]
            a['max'] = [max(row[i] for row in rows) for i in range(3)]
        doc['accessors'].append(a)
        return len(doc['accessors']) - 1
    images = {}
    pixel_images = {}
    rgba_bytes = pixel_work = 0
    for shader in sector['shaders']:
        material = {'name': shader['name'], 'pbrMetallicRoughness': {'baseColorFactor': [1, 1, 1, 1], 'metallicFactor': 0, 'roughnessFactor': .8},
                    'alphaMode': 'OPAQUE', 'doubleSided': True,
                    'extras': dict(shader, preview_alpha_policy='Authored opaque preview; original bucket and source texture alpha retained, native semantics unverified.')}
        diffuse = [s for s in shader['samplers'] if s['hash'] == 0xf1fe2b71 and s['texture_name']]
        road_base = sector.get('road_base', False) and shader['name'] == 'CityRoad'
        if sector.get('terrain_base', False) and shader['name'] == 'CityTerrain':
            layers = [s for s in shader['samplers'] if s['hash'] in (0xc9a79fed, 0xf7357b08, 0xa4cfd63a)]
            require(len(layers) == 3 and len({s['texture_name'].lower() for s in layers}) == 1, 'terrain_layers_not_identical')
            diffuse = [layers[0]]
            material['extras']['racer_preview_policy'] = 'Authored single-layer grass using original identical A/B/C diffuse asset and UV0; native channel-map blend/scales not reproduced.'
        if road_base:
            material['extras']['racer_preview_policy'] = 'Source-informed grayscale base from control red, alpha255, UV0 retained. Matches primary CodeX GetAlbedo(control,null); original FXC/UV1 markings not reconstructed.'
        if len(diffuse) == 1:
            key = texture_hash(diffuse[0]['texture_name'])
            tex = sector['textures'].get(key)
            if tex is not None:
                cache_key = (key, 'road-red-gray' if road_base else 'native')
                if cache_key not in images:
                    amount = tex['width'] * tex['height'] * 4
                    require(amount <= RGBA_LIMIT, 'preview_rgba_budget')
                    pixel_work += amount
                    require(pixel_work <= PIXEL_WORK_LIMIT, 'preview_pixel_work_budget')
                    source_reader = sector.get('texture_readers', {}).get(key, r)
                    pixels = modules['mcla_texture'].pixels(source_reader, tex)
                    require(len(pixels) == amount, 'texture_decoder_size')
                    original_rgba_sha = digest(pixels)
                    if road_base:
                        red = pixels[0::4]
                        generated = bytearray(amount)
                        generated[0::4] = red;generated[1::4] = red;generated[2::4] = red
                        generated[3::4] = bytes([255]) * len(red)
                        pixels = bytes(generated)
                        material['extras']['source_control_rgba_sha256'] = original_rgba_sha
                        material['extras']['road_base_rgba_sha256'] = digest(pixels)
                        material['extras']['road_primary_source_sha256'] = 'c7c15654200f003a162137820a1c24cf280a8031502f908e2f65a862f8a8b166'
                    identity = (tex['width'], tex['height'], digest(pixels))
                    if identity not in pixel_images:
                        require(rgba_bytes + amount <= RGBA_LIMIT, 'preview_rgba_budget')
                        require(len(doc['images']) < 128, 'preview_image_count_budget')
                        rgba_bytes += amount
                        image = Image.frombytes('RGBA', (tex['width'], tex['height']), pixels)
                        encoded = io.BytesIO();image.save(encoded, format='PNG')
                        doc['images'].append({'bufferView': view(encoded.getvalue()), 'mimeType': 'image/png', 'name': diffuse[0]['texture_name']})
                        doc['textures'].append({'source': len(doc['images']) - 1, 'sampler': 0})
                        pixel_images[identity] = len(doc['textures']) - 1
                    images[cache_key] = pixel_images[identity]
                material['pbrMetallicRoughness']['baseColorTexture'] = {'index': images[cache_key]}
                material['extras']['diffuse_hash'] = key
            else:
                material['extras']['unresolved_diffuse'] = diffuse[0]['texture_name']
        elif shader['samplers']:
            material['extras']['unsupported_diffuse_binding'] = 'No unique exact DiffuseSampler; layered samplers are not collapsed.'
        doc['materials'].append(material)
    for g in sector['geometries']:
        attrs = {'POSITION': accessor(g['position'], 'VEC3', 5126, 'f')}
        if 'normal' in g:
            attrs['NORMAL'] = accessor(g['normal'], 'VEC3', 5126, 'f')
        if 'texcoord0' in g:
            attrs['TEXCOORD_0'] = accessor(g['texcoord0'], 'VEC2', 5126, 'f')
        if sector.get('preserve_channels', False):
            for i in (1, 2):
                if 'texcoord%d' % i in g:
                    attrs['TEXCOORD_%d' % i] = accessor(g['texcoord%d' % i], 'VEC2', 5126, 'f')
            for i in (0, 1):
                if 'colour%d' % i in g:
                    attrs['_RACER_SOURCE_COLOR%d' % i] = accessor(g['colour%d' % i], 'VEC4', 5121, 'B')
        primitive = {'attributes': attrs, 'indices': accessor([(v,) for v in g['indices']], 'SCALAR', 5123, 'H'), 'material': g['shader'], 'mode': 4}
        doc['meshes'].append({'primitives': [primitive]})
        doc['nodes'].append({'mesh': len(doc['meshes']) - 1, 'name': 'native_model_%d_geometry_%d' % (g['model'], g['geometry'])})
        doc['scenes'][0]['nodes'].append(len(doc['nodes']) - 1)
    doc['buffers'][0]['byteLength'] = len(blob)
    text = json.dumps(doc, separators=(',', ':'), allow_nan=False).encode()
    text += b' ' * (-len(text) % 4);blob.extend(b'\0' * (-len(blob) % 4))
    total = 12 + 8 + len(text) + 8 + len(blob)
    require(total <= 32 * 1024 * 1024, 'preview_glb_budget')
    result = struct.pack('<III', 0x46546c67, 2, total) + struct.pack('<II', len(text), 0x4e4f534a) + text + struct.pack('<II', len(blob), 0x004e4942) + blob
    return result, {'images': len(doc['images']), 'decoded_rgba_bytes': rgba_bytes,
                    'pixel_work_bytes': pixel_work, 'deduplicated_texture_aliases': len(images) - len(doc['images']),
                    'resolved_diffuse_materials': sum('baseColorTexture' in m['pbrMetallicRoughness'] for m in doc['materials']),
                    'unresolved_diffuse_materials': [m['extras']['unresolved_diffuse'] for m in doc['materials'] if 'unresolved_diffuse' in m['extras']]}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--iso', type=Path, required=True)
    ap.add_argument('--toc', type=Path, required=True)
    ap.add_argument('--helpers', type=Path, required=True)
    ap.add_argument('--texture-helper', type=Path, required=True)
    ap.add_argument('--entry', type=int, action='append', required=True)
    ap.add_argument('--shared-entry', type=int, choices=[SHARED_ENTRY])
    ap.add_argument('--reconstruct-road-base', action='store_true')
    ap.add_argument('--single-layer-terrain', action='store_true')
    ap.add_argument('--omit-tint-decals', action='store_true')
    ap.add_argument('--preserve-source-channels', action='store_true')
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--budget-root', type=Path)
    args = ap.parse_args()
    require(1 <= len(args.entry) <= 4 and len(set(args.entry)) == len(args.entry), 'entry_selection_budget')
    require(args.iso.is_file() and not args.iso.is_symlink() and args.iso.stat().st_size == ISO_BYTES, 'iso_size_or_type')
    require(file_digest(args.iso) == ISO_SHA, 'iso_identity')
    entries = toc_entries(read_small(args.toc, 512 * 1024))
    city = city_indices(entries)
    require(all(i in city for i in args.entry), 'entry_not_city_member')
    modules = helpers(args.helpers, args.texture_helper)
    args.output.mkdir(mode=0o700, parents=False, exist_ok=False)
    budget = args.budget_root or args.output
    require(budget.resolve() == args.output.resolve() or budget.resolve() in args.output.resolve().parents, 'budget_root_must_contain_output')
    def write(filename, data):
        used = sum(p.stat().st_size for p in budget.rglob('*') if p.is_file())
        require(used + len(data) <= OUTPUT_LIMIT, 'output_byte_budget')
        with (args.output / filename).open('xb') as dest:
            dest.write(data)
    reports = []
    with args.iso.open('rb') as source:
        source.seek(ARCHIVE_OFFSET)
        archive_header = source.read(20)
        require(struct.unpack_from('<4sII', archive_header) == (b'RPF3', 382976, ENTRY_COUNT), 'archive_header_identity')
        shared = None
        if args.shared_entry is not None:
            words = entries[SHARED_ENTRY]
            require(SHARED_ENTRY in city and not words[2] & 0x80000000 and words[3] & 0xc0000000 == 0xc0000000,
                    'shared_bank_entry_identity')
            offset, size = words[2] & 0x7fffff00, words[1]
            require(20 <= size <= SHARED_STORED_LIMIT and offset + size <= ARCHIVE_BYTES, 'shared_bank_range')
            source.seek(ARCHIVE_OFFSET + offset);raw = source.read(size)
            require(len(raw) == size, 'shared_bank_short_read')
            header = modules['mcla_lzx'].parse_header(raw)
            expected = header['virtual'] + header['physical']
            require(header['type'] == 1 and header['flag'] == words[3] and expected <= SHARED_DECODED_LIMIT,
                    'shared_bank_decoded_budget_or_type')
            bank_provenance = dict(entry=SHARED_ENTRY, iso_sha256=ISO_SHA, absolute_offset=ARCHIVE_OFFSET + offset,
                                   archive_offset=offset, stored_bytes=size, stored_sha256=digest(raw), header=header)
            write('shared-bank-before-decode.json', json.dumps(dict(bank_provenance,
                  intent='Approved exact2111 stored16MiB/decodedmemory32MiB; no full bank file copy; workeroutput48MiB for newv3. '
                         'Prior partial metadata joins matched all63missing2300 and47missing1948 diffuse bindings. '
                         'Only needed texture pixels will be decoded; pixel-work128MiB/nativeRGBA32MiB bounds.'), indent=2).encode())
            decoded, header = modules['mcla_lzx'].decompress(raw, expected=expected)
            bank = modules['mcla_resource'].Resource(decoded, header['virtual'], header['physical'])
            require(bank.u32(0) == 0xec505900, 'shared_bank_dictionary_root')
            pointers = array(bank, 24, 1024)
            hashes_at = bank.pointer(16, len(pointers) * 4)
            require(hashes_at is not None and bank.u16(20) == len(pointers), 'shared_bank_hash_count')
            mapping = {}
            for i, pointer in enumerate(pointers):
                key = bank.u32(hashes_at + i * 4)
                require(key not in mapping, 'shared_bank_duplicate_hash')
                bank.offset(pointer, 64)
                mapping[key] = pointer
            bank_provenance.update(decoded_sha256=digest(decoded), dictionary_hash_count=len(mapping))
            shared = (bank, mapping, bank_provenance)
            write('shared-bank.json', json.dumps(bank_provenance, indent=2).encode())
        for index in args.entry:
            words = entries[index]
            offset, size = entry_range(words)
            source.seek(ARCHIVE_OFFSET + offset);raw = source.read(size)
            require(len(raw) == size, 'resource_short_read')
            header = modules['mcla_lzx'].parse_header(raw)
            expected = header['virtual'] + header['physical']
            require(0 < expected <= MEMBER_LIMIT and header['flag'] == words[3], 'resource_decoded_budget_or_flag')
            decoded, header = modules['mcla_lzx'].decompress(raw, expected=expected)
            r, sector = decode_sector(decoded, header, modules)
            source_bounds = sector['bounds']
            source_vertices = sum(g['vertex_count'] for g in sector['geometries'])
            source_triangles = sum(g['index_count'] // 3 for g in sector['geometries'])
            sector['road_base'] = args.reconstruct_road_base
            sector['terrain_base'] = args.single_layer_terrain
            sector['preserve_channels'] = args.preserve_source_channels
            sector['preview_policies'] = [name for flag, name in (
                (args.reconstruct_road_base, 'source-informed CityRoad control-red grayscale only'),
                (args.single_layer_terrain, 'authored single identical grass layer for CityTerrain UV0'),
                (args.omit_tint_decals, 'omit unsupported CityGrimeTintDecal overlay geometry'),
                (args.preserve_source_channels, 'preserve raw native color bytes and UV1/UV2 custom attributes')) if flag]
            sector['omitted_geometries'] = []
            if args.omit_tint_decals:
                selected = []
                for g in sector['geometries']:
                    if sector['shaders'][g['shader']]['name'] == 'CityGrimeTintDecal':
                        sector['omitted_geometries'].append({k: g[k] for k in ('model', 'geometry', 'shader', 'vertex_count', 'index_count')})
                    else:
                        selected.append(g)
                sector['geometries'] = selected
                points = [p for g in selected for p in g['position']]
                sector['bounds'] = [[min(p[i] for p in points) for i in range(3)], [max(p[i] for p in points) for i in range(3)]]
            shared_joins = []
            if shared is not None:
                bank, mapping, bank_provenance = shared
                sector['texture_readers'] = {}
                local_texture_hashes = set(sector['textures'])
                for shader in sector['shaders']:
                    for sampler in shader['samplers']:
                        permitted = (0xf1fe2b71, 0xa79aeec0, 0xc9a79fed, 0xf7357b08, 0xa4cfd63a) if args.single_layer_terrain else (0xf1fe2b71,)
                        if sampler['hash'] not in permitted or not sampler['texture_name']:
                            continue
                        key = texture_hash(sampler['texture_name'])
                        local = key in local_texture_hashes
                        shared_joins.append(dict(name=sampler['texture_name'], hash=key, local=local,
                                                 shared_present=key in mapping))
                        if not local and key in mapping:
                            meta = texture_header(bank, bank.offset(mapping[key], 64), modules['mcla_texture'])
                            meta['source_entry'] = SHARED_ENTRY
                            sector['textures'][key] = meta
                            sector['texture_readers'][key] = bank
            provenance = dict(iso_sha256=ISO_SHA, decoded_toc_sha256=TOC_SHA, entry=index,
                              archive_offset=offset, absolute_offset=ARCHIVE_OFFSET + offset, stored_bytes=size,
                              stored_sha256=digest(raw), decoded_sha256=digest(decoded), header=header)
            if shared is not None:
                provenance['shared_bank'] = shared[2]
            glb, stats = preview_glb(r, sector, modules, provenance)
            write('%d.glb' % index, glb)
            report = dict(provenance, bounds=sector['bounds'], source_bounds=source_bounds, source_vertices=source_vertices, source_triangles=source_triangles,
                          preview_policies=sector['preview_policies'], omitted_geometries=sector['omitted_geometries'],
                          models=sector['models'], shaders=sector['shaders'], shared_joins=shared_joins,
                          textures=sector['textures'], vertices=sum(g['vertex_count'] for g in sector['geometries']),
                          triangles=sum(g['index_count'] // 3 for g in sector['geometries']), glb_bytes=len(glb), glb_sha256=digest(glb), **stats)
            write('%d.json' % index, json.dumps(report, indent=2, allow_nan=False).encode())
            reports.append({k: report[k] for k in ('entry', 'vertices', 'triangles', 'glb_bytes', 'images', 'decoded_rgba_bytes', 'resolved_diffuse_materials', 'unresolved_diffuse_materials', 'bounds')})
    write('manifest.json', json.dumps({'helpers': PINS, 'pilots': reports}, indent=2).encode())
    print(json.dumps(reports, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, struct.error) as error:
        print('world-resource inspection failed: ' + str(error), file=sys.stderr)
        sys.exit(2)
