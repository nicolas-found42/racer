#!/usr/bin/env python3
"""Source-preserving world preview contracts; no network or GPU required."""
import argparse
import copy
import io
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import inspect_world_resources as world
from prepare_gt4_vehicle import Geometry, unpack

parser = argparse.ArgumentParser(add_help=False)
parser.add_argument('--pilot-dir', type=Path)
parser.add_argument('--source-iso', type=Path)
parser.add_argument('--native-helpers', type=Path)
parser.add_argument('--texture-helper', type=Path)
options, remaining = parser.parse_known_args()
sys.argv = [sys.argv[0], *remaining]


class Reader:
    """Independent finite virtual-segment fixture reader."""
    def __init__(self, data):
        self.data = data
        self.virtual = len(data)
    def need(self, at, size):
        if at < 0 or at + size > len(self.data):
            raise ValueError('fixture_read_outside')
    def offset(self, value, size=0):
        if value >> 28 != 5:
            raise ValueError('fixture_pointer_segment')
        at = value & 0xfffffff
        self.need(at, size)
        return at
    def unpack(self, fmt, at):
        self.need(at, struct.calcsize('>' + fmt))
        return struct.unpack_from('>' + fmt, self.data, at)
    def u32(self, at): return self.unpack('I', at)[0]
    def u16(self, at): return self.unpack('H', at)[0]
    def u8(self, at): return self.unpack('B', at)[0]
    def pointer(self, at, size=0):
        value = self.u32(at)
        return self.offset(value, size) if value else None


def fixture_sector(sampler=0xf1fe2b71):
    vertices = [(-700., 20., -750.), (-699., 20., -750.), (-700., 21., -750.)]
    return {'models': [], 'bounds': [[-700., 20., -750.], [-699., 21., -750.]],
            'geometries': [{'position': vertices, 'indices': [0, 1, 2], 'shader': 0,
                            'normal': [(0., 0., 1.)] * 3, 'texcoord0': [(0., 0.), (1., 0.), (0., 1.)],
                            'model': 0, 'geometry': 0}],
            'shaders': [{'name': 'CityFixture', 'draw_bucket': 7,
                         'samplers': [{'hash': sampler, 'texture_name': 'facade.dds', 'texture_pointer': 0}]}],
            'textures': {world.texture_hash('facade.dds'): {'width': 2, 'height': 2}}}


class Checks(unittest.TestCase):
    def test_resource_coordinates_reject_flags_and_ranges(self):
        self.assertEqual(world.entry_range((123, 100, 0x1001, 0xc0000000), 5000), (4096, 100))
        for words in [(123, 100, 0x80001001, 0xc0000000), (123, 100, 0x1001, 0x40000000),
                      (123, 100, 0x103f, 0xc0000000), (123, 10, 0x1001, 0xc0000000),
                      (123, world.MEMBER_LIMIT + 1, 0x1001, 0xc0000000)]:
            with self.assertRaises(ValueError): world.entry_range(words, 5000)
        with self.assertRaisesRegex(ValueError, 'resource_range'):
            world.entry_range((123, 100, 0x1001, 0xc0000000), 4100)

    def test_city_selection_requires_real_ancestry_and_complete_tree(self):
        def directory(n, first, count): return (world.joaat(n), 0, 0x80000000 | first, count)
        entries = [(0, 0, 0x80000001, 1), directory('resources', 2, 1),
                   directory('city', 3, 1), directory('sc', 4, 1), (123, 100, 4097, 0xc0000000)]
        self.assertEqual(world.city_indices(entries), {4})
        changed = list(entries);changed[1] = directory('vehicle', 2, 1)
        self.assertEqual(world.city_indices(changed), set())
        changed = list(entries);changed[3] = directory('sc', 0, 1)
        with self.assertRaisesRegex(ValueError, 'cycle_or_range'): world.city_indices(changed)
        changed = list(entries) + [(8, 100, 4097, 0xc0000000)]
        with self.assertRaisesRegex(ValueError, 'unreachable'): world.city_indices(changed)

    def test_array_rejects_overflow_and_segment_crossing(self):
        data = bytearray(32);struct.pack_into('>IHH', data, 0, 0x50000018, 2, 2)
        self.assertEqual(world.array(Reader(data), 0, 4), [0, 0])
        struct.pack_into('>IHH', data, 0, 0x5000001c, 2, 2)
        with self.assertRaisesRegex(ValueError, 'read_outside'): world.array(Reader(data), 0, 4)
        struct.pack_into('>IHH', data, 0, 0x50000018, 3, 2)
        with self.assertRaisesRegex(ValueError, 'array_count'): world.array(Reader(data), 0, 4)

    def test_helper_tampering_is_rejected_before_execution(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'mcla_resource.py').write_text('raise RuntimeError("must not execute")')
            with self.assertRaisesRegex(ValueError, 'helper_identity_mcla_resource'):
                world.helpers(root, root / 'texture.py')

    def test_export_preserves_world_positions_indices_uvs_and_pixel_alpha(self):
        from PIL import Image
        rgba = bytes([255, 0, 0, 0, 0, 255, 0, 64, 0, 0, 255, 128, 255, 255, 255, 255])
        modules = {'mcla_texture': SimpleNamespace(pixels=lambda r, t: rgba)}
        sector = fixture_sector();original = copy.deepcopy(sector)
        raw, stats = world.preview_glb(None, sector, modules, {'entry': 42})
        doc, binary = unpack(raw);geometry = Geometry(doc, binary)
        primitive = doc['meshes'][0]['primitives'][0]
        self.assertEqual(geometry.values(primitive['attributes']['POSITION']), original['geometries'][0]['position'])
        self.assertEqual(geometry.values(primitive['attributes']['TEXCOORD_0']), original['geometries'][0]['texcoord0'])
        self.assertEqual(geometry.values(primitive['indices']), [(0,), (1,), (2,)])
        self.assertNotIn('matrix', doc['nodes'][0])
        self.assertNotIn('translation', doc['nodes'][0])
        self.assertEqual(doc['materials'][0]['extras']['draw_bucket'], 7)
        self.assertEqual(doc['materials'][0]['alphaMode'], 'OPAQUE')
        image_view = doc['bufferViews'][doc['images'][0]['bufferView']]
        png = bytes(binary[image_view['byteOffset']:image_view['byteOffset'] + image_view['byteLength']])
        self.assertEqual(Image.open(io.BytesIO(png)).convert('RGBA').tobytes(), rgba)
        self.assertEqual(stats['decoded_rgba_bytes'], 16)
        self.assertEqual(sector, original)

    def test_shared_texture_reader_is_used_and_duplicate_pixels_share_one_image(self):
        rgba = bytes([255, 200, 100, 64]) * 4
        shared = object()
        seen = []
        def pixels(reader, texture):
            seen.append(reader)
            return rgba
        sector = fixture_sector()
        second = copy.deepcopy(sector['shaders'][0])
        second['samplers'][0]['texture_name'] = 'alias.dds'
        sector['shaders'].append(second)
        first = world.texture_hash('facade.dds');alias = world.texture_hash('alias.dds')
        sector['textures'][alias] = dict(sector['textures'][first])
        sector['texture_readers'] = {first: shared, alias: shared}
        raw, stats = world.preview_glb(None, sector, {'mcla_texture': SimpleNamespace(pixels=pixels)}, {})
        doc, _ = unpack(raw)
        self.assertEqual(seen, [shared, shared])
        self.assertEqual(stats['images'], 1)
        self.assertEqual(stats['decoded_rgba_bytes'], 16)
        self.assertEqual(stats['deduplicated_texture_aliases'], 1)
        bindings = [m['pbrMetallicRoughness']['baseColorTexture']['index'] for m in doc['materials']]
        self.assertEqual(bindings, [0, 0])

    def test_road_control_red_is_grey_only_for_explicit_road_policy(self):
        from PIL import Image
        rgba = bytes([20, 200, 5, 19, 60, 180, 8, 40, 100, 160, 9, 80, 140, 120, 10, 120])
        sector = fixture_sector();sector['road_base'] = True
        road = copy.deepcopy(sector['shaders'][0]);road['name'] = 'CityRoad'
        sector['shaders'].append(road)
        raw, _ = world.preview_glb(None, sector, {'mcla_texture': SimpleNamespace(pixels=lambda r, t: rgba)}, {})
        doc, binary = unpack(raw)
        self.assertEqual(len(doc['images']), 2)
        decoded = []
        for image in doc['images']:
            v = doc['bufferViews'][image['bufferView']]
            decoded.append(Image.open(io.BytesIO(binary[v['byteOffset']:v['byteOffset'] + v['byteLength']])).convert('RGBA').tobytes())
        self.assertEqual(decoded[0], rgba)
        expected = b''.join(bytes([rgba[i], rgba[i], rgba[i], 255]) for i in range(0, len(rgba), 4))
        self.assertEqual(decoded[1], expected)
        self.assertEqual(doc['materials'][1]['extras']['source_control_rgba_sha256'], world.digest(rgba))

    def test_terrain_single_layer_requires_all_original_layers_to_agree(self):
        sector = fixture_sector();sector['terrain_base'] = True
        shader = sector['shaders'][0];shader['name'] = 'CityTerrain'
        shader['samplers'] = [{'hash': h, 'texture_name': 'facade.dds', 'texture_pointer': 0}
                              for h in (0xc9a79fed, 0xf7357b08, 0xa4cfd63a)]
        modules = {'mcla_texture': SimpleNamespace(pixels=lambda r, t: bytes([50, 100, 25, 255]) * 4)}
        raw, stats = world.preview_glb(None, sector, modules, {})
        self.assertEqual(stats['resolved_diffuse_materials'], 1)
        doc, _ = unpack(raw)
        self.assertEqual(len(doc['materials'][0]['extras']['samplers']), 3)
        shader['samplers'][1]['texture_name'] = 'different.dds'
        with self.assertRaisesRegex(ValueError, 'terrain_layers_not_identical'):
            world.preview_glb(None, sector, modules, {})

    def test_source_color_bytes_and_other_uv_sets_are_not_reinterpreted(self):
        sector = fixture_sector();sector['preserve_channels'] = True
        g = sector['geometries'][0]
        g['colour0'] = [(1, 2, 3, 4), (5, 6, 7, 8), (9, 10, 11, 12)]
        g['colour1'] = [(255, 0, 0, 0), (127, 11, 21, 31), (37, 51, 61, 71)]
        g['texcoord1'] = [(1., 0.), (.5, .25), (-2., 8.)]
        g['texcoord2'] = [(.25, 1.), (.25, 2.), (.25, 3.)]
        modules = {'mcla_texture': SimpleNamespace(pixels=lambda r, t: bytes([50, 100, 25, 255]) * 4)}
        raw, _ = world.preview_glb(None, sector, modules, {})
        doc, binary = unpack(raw);geometry = Geometry(doc, binary)
        attributes = doc['meshes'][0]['primitives'][0]['attributes']
        for channel in (0, 1):
            name = '_RACER_SOURCE_COLOR%d' % channel
            self.assertEqual(geometry.values(attributes[name]), g['colour%d' % channel])
            self.assertFalse(doc['accessors'][attributes[name]].get('normalized', False))
        for channel in (1, 2):
            self.assertEqual(geometry.values(attributes['TEXCOORD_%d' % channel]), g['texcoord%d' % channel])
        self.assertNotIn('_RACER_OCCLUSION', attributes)
        self.assertNotIn('COLOR_0', attributes)

    def test_texture_dimensions_are_rejected_before_pixel_codec(self):
        data = bytearray(256)
        struct.pack_into('>I', data, 28, 0x50000080)
        struct.pack_into('>HH', data, 32, 4096, 1)
        with self.assertRaisesRegex(ValueError, 'texture_dimension_budget'):
            world.texture_header(Reader(data), 0, None)

    def test_missing_and_unknown_sampler_do_not_get_substituted(self):
        modules = {'mcla_texture': SimpleNamespace(pixels=lambda r, t: self.fail('unknown texture must not decode'))}
        sector = fixture_sector(sampler=0x12345678)
        raw, stats = world.preview_glb(None, sector, modules, {})
        doc, _ = unpack(raw)
        self.assertEqual(stats['images'], 0)
        self.assertNotIn('baseColorTexture', doc['materials'][0]['pbrMetallicRoughness'])
        self.assertIn('unsupported_diffuse_binding', doc['materials'][0]['extras'])
        sector = fixture_sector();sector['textures'] = {}
        raw, stats = world.preview_glb(None, sector, modules, {})
        self.assertEqual(stats['unresolved_diffuse_materials'], ['facade.dds'])

    def test_rgba_work_bound_precedes_decoder(self):
        sector = fixture_sector();sector['textures'][world.texture_hash('facade.dds')].update(width=4096, height=4096)
        modules = {'mcla_texture': SimpleNamespace(pixels=lambda r, t: self.fail('budget checked too late'))}
        with self.assertRaisesRegex(ValueError, 'preview_rgba_budget'):
            world.preview_glb(None, sector, modules, {})

    @unittest.skipUnless(options.pilot_dir and options.source_iso and options.native_helpers and options.texture_helper,
                         'pass explicit native source/helper paths for full source-correspondence proof')
    def test_actual_source_correspondence_for_all_vertices_channels_and_used_pixels(self):
        from PIL import Image
        self.assertEqual(world.file_digest(options.source_iso), world.ISO_SHA)
        modules = world.helpers(options.native_helpers, options.texture_helper)
        with options.source_iso.open('rb') as source:
            for path in sorted(options.pilot_dir.glob('*.glb')):
                report = json.loads(path.with_suffix('.json').read_text())
                source.seek(report['absolute_offset']);raw = source.read(report['stored_bytes'])
                self.assertEqual(world.digest(raw), report['stored_sha256'])
                decoded, header = modules['mcla_lzx'].decompress(raw)
                self.assertEqual(world.digest(decoded), report['decoded_sha256'])
                reader, sector = world.decode_sector(decoded, header, modules)
                originals = {(g['model'], g['geometry']): g for g in sector['geometries']}
                shared_reader = None;shared_mapping = {}
                if 'shared_bank' in report:
                    bank = report['shared_bank']
                    source.seek(bank['absolute_offset']);raw = source.read(bank['stored_bytes'])
                    self.assertEqual(world.digest(raw), bank['stored_sha256'])
                    decoded, header = modules['mcla_lzx'].decompress(raw)
                    self.assertEqual(world.digest(decoded), bank['decoded_sha256'])
                    shared_reader = modules['mcla_resource'].Resource(decoded, header['virtual'], header['physical'])
                    ptrs = world.array(shared_reader, 24, 1024);hashes = shared_reader.pointer(16, len(ptrs) * 4)
                    shared_mapping = {shared_reader.u32(hashes + i * 4): pointer for i, pointer in enumerate(ptrs)}
                doc, binary = unpack(path.read_bytes());geometry = Geometry(doc, binary)
                observed = set()
                import re
                for node in doc['nodes']:
                    match = re.fullmatch(r'native_model_(\d+)_geometry_(\d+)', node['name'])
                    self.assertIsNotNone(match)
                    key = tuple(map(int, match.groups()));observed.add(key)
                    original = originals[key]
                    primitive = doc['meshes'][node['mesh']]['primitives'][0];attrs = primitive['attributes']
                    self.assertEqual(geometry.values(attrs['POSITION']), original['position'])
                    self.assertEqual([v[0] for v in geometry.values(primitive['indices'])], original['indices'])
                    for attribute, channel in [('NORMAL', 'normal'), ('TEXCOORD_0', 'texcoord0'),
                                               ('TEXCOORD_1', 'texcoord1'), ('TEXCOORD_2', 'texcoord2'),
                                               ('_RACER_SOURCE_COLOR0', 'colour0'), ('_RACER_SOURCE_COLOR1', 'colour1')]:
                        if attribute in attrs:
                            expected_rows = original[channel]
                            if doc['accessors'][attrs[attribute]]['componentType'] == 5126:
                                # Native Dec3N expands to rationals; glTF stores IEEE float32.
                                # Compare the exact required representation, not an arbitrary tolerance.
                                expected_rows = [struct.unpack('<' + 'f' * len(row), struct.pack('<' + 'f' * len(row), *row)) for row in expected_rows]
                            self.assertEqual(geometry.values(attrs[attribute]), expected_rows)
                    self.assertNotIn('_RACER_OCCLUSION', attrs)
                omitted = {(g['model'], g['geometry']) for g in report.get('omitted_geometries', [])}
                self.assertEqual(observed, set(originals) - omitted)
                checked_images = set()
                for material in doc['materials']:
                    binding = material['pbrMetallicRoughness'].get('baseColorTexture')
                    if binding is None: continue
                    image_index = doc['textures'][binding['index']]['source']
                    if image_index in checked_images: continue
                    checked_images.add(image_index)
                    key = material['extras']['diffuse_hash']
                    if key in sector['textures']:
                        texture = sector['textures'][key];texture_reader = reader
                    else:
                        self.assertIn(key, shared_mapping)
                        texture = world.texture_header(shared_reader, shared_reader.offset(shared_mapping[key], 64), modules['mcla_texture'])
                        texture_reader = shared_reader
                    expected = modules['mcla_texture'].pixels(texture_reader, texture)
                    if material['name'] == 'CityRoad' and 'source-informed CityRoad control-red grayscale only' in report.get('preview_policies', []):
                        expected = b''.join(bytes((expected[i], expected[i], expected[i], 255)) for i in range(0, len(expected), 4))
                    image = doc['images'][image_index];v = doc['bufferViews'][image['bufferView']]
                    actual = Image.open(io.BytesIO(binary[v['byteOffset']:v['byteOffset'] + v['byteLength']])).convert('RGBA')
                    self.assertEqual(actual.size, (texture['width'], texture['height']))
                    self.assertEqual(actual.tobytes(), expected)
                print('native-correspondence:', report['entry'], len(observed), 'geometry groups;',
                      sum(len(originals[k]['position']) for k in observed), 'vertices;', len(checked_images), 'source-bound images')

    @unittest.skipUnless(options.pilot_dir, 'pass --pilot-dir to inspect retained actual pilots')
    def test_actual_pilot_geometry_and_images_are_self_contained(self):
        from PIL import Image
        for path in sorted(options.pilot_dir.glob('*.glb')):
            report = json.loads(path.with_suffix('.json').read_text())
            raw = path.read_bytes();doc, binary = unpack(raw);geometry = Geometry(doc, binary)
            self.assertEqual(world.digest(raw), report['glb_sha256'])
            points = [];triangles = 0;rgba = 0
            for node in doc['nodes']:
                self.assertFalse({'matrix', 'translation', 'rotation', 'scale'} & node.keys())
            for mesh in doc['meshes']:
                for primitive in mesh['primitives']:
                    pos = geometry.values(primitive['attributes']['POSITION']);points.extend(pos)
                    indices = geometry.values(primitive['indices']);triangles += len(indices) // 3
                    self.assertTrue(all(0 <= row[0] < len(pos) for row in indices))
            bounds = [[min(v[i] for v in points) for i in range(3)], [max(v[i] for v in points) for i in range(3)]]
            self.assertEqual(bounds, report['bounds'])
            self.assertEqual(len(points), report['vertices'])
            self.assertEqual(triangles, report['triangles'])
            if report.get('omitted_geometries'):
                self.assertEqual(len(points) + sum(g['vertex_count'] for g in report['omitted_geometries']), report['source_vertices'])
                self.assertEqual(triangles + sum(g['index_count'] // 3 for g in report['omitted_geometries']), report['source_triangles'])
                self.assertTrue(all(report['shaders'][g['shader']]['name'] == 'CityGrimeTintDecal' for g in report['omitted_geometries']))
            self.assertLessEqual(len(doc['images']), 128)
            for image in doc['images']:
                self.assertNotIn('uri', image)
                view = doc['bufferViews'][image['bufferView']]
                decoded = Image.open(io.BytesIO(binary[view['byteOffset']:view['byteOffset'] + view['byteLength']]))
                decoded.load();rgba += decoded.width * decoded.height * 4
            self.assertEqual(rgba, report['decoded_rgba_bytes'])
            self.assertLessEqual(rgba, world.RGBA_LIMIT)


if __name__ == '__main__':
    unittest.main(verbosity=2)
