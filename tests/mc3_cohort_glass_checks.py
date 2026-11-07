#!/usr/bin/env python3
"""Exact fixture checks for the optional four-car MC3 tint policy."""
import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import mc3_cohort_glass as glass
from prepare_gt4_vehicle import unpack, PreparationError
from vehicle_clearance import descriptor
from fit_vehicle_tracks import frames, positions


def fixtures_available():
    return all((glass.LEAF / 'batch-v1' / c / 'source.dat').is_file() and
               (glass.LEAF / 'batch-v2' / c / 'prepared-v1' / (p['prepared'] + '.glb')).is_file()
               for c, p in glass.PINS.items())


class GlassChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not fixtures_available(): raise unittest.SkipTest('Exact MC3 cohort fixtures unavailable')

    def materials(self, code='vp_fleetline_49'):
        pin = glass.PINS[code]
        source, _ = unpack((glass.LEAF / 'batch-v1' / code / 'source.glb').read_bytes())
        raw = (glass.LEAF / 'batch-v2' / code / 'prepared-v1' / (pin['prepared'] + '.glb')).read_bytes()
        doc, _ = unpack(raw)
        pck = (glass.LEAF / 'batch-v2' / code / 'main.pck').read_bytes()
        return doc, source, pck, code

    def test_actual_four_whole_geometry_and_unrelated_materials(self):
        count = 0
        for code, pin in glass.PINS.items():
            with self.subTest(code=code):
                folder = glass.LEAF / 'batch-v2' / code / 'prepared-v1'
                a, ab = unpack((folder / (pin['prepared'] + '.glb')).read_bytes())
                oldtext = (folder / (pin['prepared'] + '.vehicle')).read_text()
                raw, text, receipt = glass.convert(code); b, bb = unpack(raw)
                self.assertEqual(ab, bb)
                _, _, roles = descriptor(oldtext)
                _, aw, _ = frames(a, roles); _, bw, _ = frames(b, roles)
                ap = positions(a, ab, aw); bp = positions(b, bb, bw)
                self.assertEqual(ap, bp); count += sum(map(len, ap.values()))
                policy = b['extras'].pop('racerCohortGlassPolicy')
                self.assertEqual(b['materials'][pin['material']]['alphaMode'], 'BLEND')
                self.assertEqual(b['materials'][pin['material']]['pbrMetallicRoughness']['baseColorFactor'], glass.TINT)
                b['materials'][pin['material']] = policy['source_material']
                self.assertEqual(a, b)  # Includes normals, indices, textures, unknown and dormant materials.
                restored = glass.rewrite_descriptor(text.decode(), receipt['prepared_sha256'], pin['prepared'], pin['source'])
                self.assertEqual(restored, oldtext)
                self.assertFalse(receipt['runtime_player_eligible'])
        self.assertEqual(count, 43859)

    def test_each_unknown_tuple_component_rejected(self):
        for key in ('name', 'shader_category', 'vtable', 'profile', 'file_offset', 'index'):
            args = self.materials(); doc, original, _, code = args; index = glass.PINS[code]['material']
            for obj in (doc, original):
                m = obj['materials'][index]; target = m if key == 'name' else m['extras']
                target[key] = 'unknown' if isinstance(target[key], str) else target[key] + 1
            with self.subTest(key=key), self.assertRaisesRegex(PreparationError, 'material_exact_tuple'):
                glass.apply_policy(*args)

    def test_inactive_matching_window_is_not_modified(self):
        args = self.materials(); args[0]['scenes'] = [{'nodes': []}]
        before = copy.deepcopy(args[0])
        with self.assertRaisesRegex(PreparationError, 'approved_window_inactive'): glass.apply_policy(*args)
        self.assertEqual(before, args[0])

    def test_raw_native_mutation_and_forged_root_rejected(self):
        doc, source, pck, code = self.materials()
        with self.assertRaisesRegex(PreparationError, 'native_pck_pin'):
            glass.apply_policy(doc, source, pck[:-1] + bytes([pck[-1] ^ 1]), code)
        for obj in (doc, source): obj['materials'][glass.PINS[code]['material']]['extras']['native_material']['root']['class_id'] = 14
        with self.assertRaisesRegex(PreparationError, 'native_material_join'): glass.apply_policy(doc, source, pck, code)

    def test_changed_prepared_or_dat_inputs_rejected(self):
        read = glass.read_regular
        for filename in ('source.dat', glass.PINS['vp_fleetline_49']['prepared'] + '.glb'):
            def changed(path, cap):
                data = read(path, cap)
                return data[:-1] + bytes([data[-1] ^ 1]) if Path(path).name == filename else data
            with self.subTest(filename=filename), patch.object(glass, 'read_regular', side_effect=changed):
                with self.assertRaisesRegex(PreparationError, 'exact_input_pins'): glass.convert('vp_fleetline_49')

    def test_descriptor_reordered_fields_and_duplicate_rejected(self):
        code = 'vp_fleetline_49'; p = glass.PINS[code]
        path = glass.LEAF / 'batch-v2' / code / 'prepared-v1' / (p['prepared'] + '.vehicle')
        rows = path.read_text().splitlines(); rows[1], rows[5] = rows[5], rows[1]
        old = '\n'.join(rows) + '\n'; new = 'a' * 64
        result = glass.rewrite_descriptor(old, p['prepared'], new, p['source'])
        self.assertEqual(glass.rewrite_descriptor(result, new, p['prepared'], p['source']), old)
        with self.assertRaisesRegex(PreparationError, 'descriptor_identity'):
            glass.rewrite_descriptor(old + 'sha256 ' + p['prepared'] + '\n', p['prepared'], new, p['source'])

    def test_budget_rejects_before_creating_output(self):
        path = glass.LEAF / 'test-glass-never-created'
        self.assertFalse(path.exists())
        with patch.object(glass, 'CAP', 0):
            with self.assertRaisesRegex(PreparationError, 'leaf_budget_before_write'):
                glass.publish(path, ['vp_fleetline_49'])
        self.assertFalse(path.exists())


if __name__ == '__main__':
    if not fixtures_available():
        print('SKIP: exact retained MC3 cohort fixtures unavailable', file=sys.stderr); sys.exit(77)
    unittest.main()
