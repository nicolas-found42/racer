"""Bounded metadata capacity; large corpus fixtures stay in memory.

GPU, network acquisition and player eligibility are not established by these
tests. Consumer checks use tiny mesh fixtures and mock native capture/publish.
"""
import contextlib
import copy
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import prepared_inventory as inventory
import car_coverage
import register_research_preparations as registration
import prepared_install_checks
import research_inventory_checks
import vehicle_capture_checks
import car_coverage_checks


def over_old_limit(document):
    document = copy.deepcopy(document)
    document['fixture_padding'] = 'x' * (256 * 1024)
    raw = json.dumps(document).encode()
    assert 256 * 1024 < len(raw) < 270 * 1024
    return raw


class Checks(unittest.TestCase):
    def helper(self, kind):
        fixture = kind(methodName='runTest')
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        # The registrar fixture uses tearDown instead of addCleanup.
        if kind is research_inventory_checks.Checks:
            self.addCleanup(fixture.tearDown)
        return fixture

    def test_current_and_legacy_shape_preserve_opaque_fields(self):
        raw = (ROOT / 'assets/catalog/prepared-sizes.json').read_bytes()
        document = inventory.decode(raw, require_schema=True)
        self.assertEqual(inventory.encode(document), raw)
        legacy = {'vehicles': [{'model_id': 'fixture/car', 'opaque': [3, 1]}]}
        self.assertEqual(inventory.decode(json.dumps(legacy).encode()), legacy)
        with self.assertRaisesRegex(ValueError, 'inventory_schema'):
            inventory.decode(json.dumps(legacy).encode(), require_schema=True)
        for schema in (True, 2, None):
            with self.subTest(schema=schema), self.assertRaisesRegex(ValueError, 'inventory_schema'):
                inventory.decode(json.dumps({**legacy, 'schema': schema}).encode())

    def test_strict_keys_finite_values_identity_count_and_byte_bounds(self):
        for raw in (b'{"vehicles":[],"vehicles":[]}',
                    b'{"vehicles":[],"x":{"a":1,"a":2}}',
                    b'{"vehicles":[],"x":NaN}',
                    b'{"vehicles":[],"x":1e999}'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                inventory.decode(raw)
        for rows in ([{'model_id': 'x'}, {'model_id': 'x'}],
                     [{'model_id': ''}], [None], [{'model_id': 'x' * 257}]):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                inventory.decode(json.dumps({'vehicles': rows}).encode())
        rows = [{'model_id': str(i)} for i in range(inventory.MAX_RECORDS + 1)]
        with self.assertRaisesRegex(ValueError, 'inventory_count'):
            inventory.decode(json.dumps({'vehicles': rows}).encode())
        with patch.object(inventory, 'MAX_BYTES', 32):
            with self.assertRaisesRegex(ValueError, 'inventory_byte_budget'):
                inventory.decode(b' ' * 33)
            with self.assertRaisesRegex(ValueError, 'result_inventory_budget'):
                inventory.encode({'schema': 1, 'vehicles': [], 'padding': 'x' * 32})

    def test_1200_largest_observed_rows_fit_in_memory_without_promotion(self):
        current = inventory.decode((ROOT / 'assets/catalog/prepared-sizes.json').read_bytes())
        template = max(current['vehicles'], key=lambda r: len(json.dumps(r, indent=2)))
        rows = [dict(template, model_id='capacity-fixture/car' + str(i),
                     role='research-candidate', player_eligible=False) for i in range(1200)]
        raw = inventory.encode({'schema': 1, 'vehicles': rows})
        self.assertGreater(len(raw), 256 * 1024)
        self.assertLess(len(raw), inventory.MAX_BYTES)
        decoded = inventory.decode(raw)
        self.assertEqual(len(decoded['vehicles']), 1200)
        self.assertTrue(all(r['player_eligible'] is False for r in decoded['vehicles']))

    def test_encoder_stops_at_budget_instead_of_serializing_remaining_rows(self):
        document = {'schema': 1, 'vehicles': [], 'opaque': list(range(1000))}
        original = json.JSONEncoder.iterencode
        full_count = sum(1 for _ in original(json.JSONEncoder(indent=2), document))
        observed = []
        def chunks(encoder, value, *args, **kwargs):
            for chunk in original(encoder, value, *args, **kwargs):
                observed.append(1)
                yield chunk
        with patch.object(inventory, 'MAX_BYTES', 128), \
             patch.object(json.JSONEncoder, 'iterencode', chunks), \
             self.assertRaisesRegex(ValueError, 'result_inventory_budget'):
            inventory.encode(document)
        self.assertLess(len(observed), full_count // 2)

    def test_capture_reads_and_retains_real_file_above_old_cap(self):
        f = self.helper(vehicle_capture_checks.Checks)
        raw = over_old_limit({'vehicles': [f.row]})
        f.inventory.write_bytes(raw)
        with patch.object(vehicle_capture_checks.capture.subprocess, 'run', side_effect=f.mock_native):
            self.assertEqual(f.invoke(), 0)
        self.assertEqual((f.root / 'out/inventory.json').read_bytes(), raw)
        manifest = json.loads((f.root / 'out/manifest.json').read_text())
        self.assertEqual(manifest['inventory_sha256'], hashlib.sha256(raw).hexdigest())
        self.assertEqual(f.inventory.read_bytes(), raw)

    def test_publisher_archives_real_file_above_old_cap(self):
        f = self.helper(prepared_install_checks.LocalInstall)
        raw = over_old_limit({'vehicles': [f.row]})
        f.inventory.write_bytes(raw)
        receipt = f.publish()
        self.assertEqual(receipt['status'], 'installed')
        snapshot = f.root / 'store/carmodels' / receipt['inventory_snapshot']
        self.assertEqual(snapshot.read_bytes(), raw)
        self.assertEqual(receipt['inventory_sha256'], hashlib.sha256(raw).hexdigest())
        self.assertEqual(f.inventory.read_bytes(), raw)

    def test_coverage_reads_real_file_above_old_cap_and_keeps_input_hash(self):
        f = car_coverage_checks.Checks(methodName='runTest')
        car = f.car()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            path, out = root / 'inventory.json', root / 'report.json'
            raw = over_old_limit({'vehicles': [f.review(car)]})
            path.write_bytes(raw)
            args = ['car_coverage.py', '--prepared', str(path), '--output', str(out)]
            with patch.object(sys, 'argv', args), \
                 patch.object(car_coverage.source, 'load_catalog', return_value=[car]), \
                 patch.object(car_coverage, 'installation', return_value=({}, {'state': 'unavailable'})), \
                 contextlib.redirect_stdout(io.StringIO()):
                car_coverage.main()
            report = json.loads(out.read_text())
            self.assertEqual(report['inputs']['prepared_inventory_sha256'], hashlib.sha256(raw).hexdigest())
            self.assertTrue(report['models'][0]['reviewed_player_preparation'])
            self.assertEqual(path.read_bytes(), raw)

    def test_registrar_freezes_large_input_and_still_only_adds_research(self):
        f = self.helper(research_inventory_checks.Checks)
        raw = over_old_limit(f.original)
        original, selected = f.root / 'input.json', f.root / 'selection.json'
        original.write_bytes(raw)
        selected.write_bytes(f.inputs()[1])
        out = f.root / 'large-dry'
        report = registration.register(selected, original, out, root=f.root)
        result = inventory.decode((out / 'inventory.json').read_bytes())
        self.assertEqual((out / 'input-inventory.json').read_bytes(), raw)
        self.assertEqual(result['vehicles'][:2], f.original['vehicles'])
        self.assertEqual(result['vehicles'][-1]['role'], 'research-candidate')
        self.assertIs(result['vehicles'][-1]['player_eligible'], False)
        self.assertEqual(report['inventory_limits']['bytes'], inventory.MAX_BYTES)
        self.assertEqual(original.read_bytes(), raw)
        self.assertEqual(json.loads((out / 'lifecycle.json').read_text())['status'], 'completed')

    def test_selection_cap_and_registration_output_peak_remain_bounded(self):
        f = self.helper(research_inventory_checks.Checks)
        a, b = f.inputs()
        with self.assertRaisesRegex(ValueError, 'json_input_budget'):
            registration.prepare_inventory(a, b + b' ' * (registration.MAX_SELECTION + 1), root=f.root)
        original, selected = f.root / 'input.json', f.root / 'selection.json'
        original.write_bytes(a)
        selected.write_bytes(b)
        with patch.object(registration, 'MAX_OUTPUT', 1), self.assertRaisesRegex(ValueError, 'output_budget'):
            registration.register(selected, original, f.root / 'small-budget', root=f.root)
        self.assertEqual(original.read_bytes(), a)
        self.assertFalse((f.root / 'small-budget/inventory.json').exists())
        self.assertEqual(json.loads((f.root / 'small-budget/lifecycle.json').read_text())['status'], 'failed')


if __name__ == '__main__':
    unittest.main()
