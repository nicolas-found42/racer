#!/usr/bin/env python3
"""Headless capture preflight/provenance tests. Native execution is always mocked."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import verify_vehicle_scale as capture
import prepare_gt4_vehicle as gt4
import gt4_preparation_checks as fixtures


class Checks(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='racer-capture-check-')
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        document, buffer = fixtures.fixture()
        source = gt4.pack(document, buffer)
        mesh, descriptor, receipt = gt4.prepare(source, 'gran-turismo-4/fixture', 'Fixture')
        self.descriptor = self.root / (receipt['prepared_sha256'] + '.vehicle')
        self.descriptor.write_text(descriptor)
        self.descriptor.with_suffix('.glb').write_bytes(mesh)
        self.row = {'model_id': 'gran-turismo-4/fixture', 'role': 'player', 'player_eligible': True,
                    'source_sha256': hashlib.sha256(source).hexdigest(),
                    'prepared_sha256': hashlib.sha256(mesh).hexdigest(),
                    'descriptor_sha256': hashlib.sha256(descriptor.encode()).hexdigest(),
                    'descriptor': str(self.descriptor)}
        self.inventory = self.root / 'inventory.json'
        self.binary = self.root / 'mock-native'
        self.binary.write_bytes(b'fixture only; never executed')
        self.write_inventory()

    def write_inventory(self):
        self.inventory.write_text(json.dumps({'vehicles': [self.row]}))

    def invoke(self, output='out', research=False):
        selection = ['--research-descriptor', str(self.descriptor)] if research else ['--inventory', str(self.inventory)]
        args = ['verify_vehicle_scale.py', str(self.root / output), '--binary', str(self.binary), *selection]
        with patch.object(sys, 'argv', args), patch.object(capture.shutil, 'disk_usage', return_value=SimpleNamespace(free=100 * 1024**3)), contextlib.redirect_stdout(io.StringIO()):
            return capture.main()

    def mock_native(self, command, **kwargs):
        ppm = Path(command[command.index('--screenshot') + 1])
        ppm.write_bytes(b'P6\n1 1\n255\n\x00\x00\x00')
        history = Path(command[command.index('--diagnostics-dir') + 1])
        history.mkdir()
        (history / 'fixture.jsonl').write_text(json.dumps({'event': 'asset_load_end', 'success': True, 'sha256': self.row['prepared_sha256']}) + '\n')
        return SimpleNamespace(returncode=0)

    def test_source_mismatch_rejected_before_native(self):
        self.row['source_sha256'] = '0' * 64
        self.write_inventory()
        with patch.object(capture.subprocess, 'run') as native:
            with self.assertRaisesRegex(ValueError, 'selected descriptor source mismatch'):
                self.invoke()
            native.assert_not_called()

    def test_inventory_role_and_namespace_cannot_promote_traffic(self):
        cases = [('gran-turismo-4/fixture', 'research-candidate'),
                 ('midnight-club-los-angeles/va_fixture', 'player'),
                 ('gran-turismo/fixture', 'player'), ('redline/fixture', 'player')]
        for index, (model, role) in enumerate(cases):
            with self.subTest(model=model, role=role):
                self.row.update(model_id=model, role=role)
                self.write_inventory()
                with patch.object(capture.subprocess, 'run') as native:
                    with self.assertRaisesRegex(ValueError, 'role or source policy mismatch'):
                        self.invoke(str(index))
                    native.assert_not_called()
                    self.assertFalse((self.root / str(index)).exists())

    def test_ineligible_inventory_is_not_selected(self):
        self.row['player_eligible'] = False
        self.write_inventory()
        with patch.object(capture.subprocess, 'run') as native:
            with self.assertRaisesRegex(ValueError, 'selected models required'):
                self.invoke()
            native.assert_not_called()

    def test_inventory_budget_rejected_before_native(self):
        self.inventory.write_bytes(b' ' * 1025)
        with patch.object(capture.inventory_format, 'MAX_BYTES', 1024), patch.object(capture.subprocess, 'run') as native:
            with self.assertRaisesRegex(ValueError, 'file_size_or_change'):
                self.invoke()
            native.assert_not_called()

    def test_retains_hash_of_inventory_bytes_used_even_if_file_changes(self):
        original = self.inventory.read_bytes()
        read = capture.regular_bytes
        def read_then_replace(path, limit):
            data = read(path, limit)
            if Path(path) == self.inventory:
                self.inventory.write_text('{"vehicles": []}')
            return data
        with patch.object(capture, 'regular_bytes', side_effect=read_then_replace), patch.object(capture.subprocess, 'run', side_effect=self.mock_native) as native:
            self.assertEqual(self.invoke(), 0)
            self.assertEqual(native.call_count, 4)
        manifest = json.loads((self.root / 'out/manifest.json').read_text())
        self.assertEqual((self.root / 'out/inventory.json').read_bytes(), original)
        self.assertEqual(manifest['inventory_sha256'], hashlib.sha256(original).hexdigest())
        self.assertTrue(manifest['all_verified'])
        self.assertEqual(manifest['models'][0]['source_sha256'], capture.descriptor_source(self.descriptor.read_bytes()))

    def test_research_capture_does_not_grant_eligibility(self):
        with patch.object(capture.subprocess, 'run', side_effect=self.mock_native):
            self.assertEqual(self.invoke(research=True), 0)
        manifest = json.loads((self.root / 'out/manifest.json').read_text())
        self.assertTrue(manifest['research_only'])
        self.assertIsNone(manifest['inventory_sha256'])
        self.assertFalse(manifest['models'][0]['player_eligible'])
        self.assertEqual(manifest['models'][0]['role'], 'research-candidate')

    def test_same_parent_labels_keep_distinct_research_operations(self):
        paths = []
        hashes = []
        for index in range(2):
            document, buffer = gt4.unpack(self.descriptor.with_suffix('.glb').read_bytes())
            document.setdefault('extras', {})['fixture_revision'] = index
            mesh = gt4.pack(document, buffer)
            digest = hashlib.sha256(mesh).hexdigest()
            folder = self.root / str(index) / 'prepared-v1'
            folder.mkdir(parents=True)
            path = folder / (digest + '.vehicle')
            path.write_text(self.descriptor.read_text().replace(self.row['prepared_sha256'], digest))
            path.with_suffix('.glb').write_bytes(mesh)
            paths.append(path)
            hashes.append(digest)
        def native(command, **kwargs):
            selected = int(command[command.index('--vehicle') + 1])
            result = self.mock_native(command, **kwargs)
            history = Path(command[command.index('--diagnostics-dir') + 1])
            (history / 'fixture.jsonl').write_text(json.dumps({'event': 'asset_load_end', 'success': True, 'sha256': hashes[selected]}) + '\n')
            return result
        args = ['verify_vehicle_scale.py', str(self.root / 'cohort'), '--binary', str(self.binary)]
        for path in paths:
            args += ['--research-descriptor', str(path)]
        with patch.object(sys, 'argv', args), patch.object(capture.shutil, 'disk_usage', return_value=SimpleNamespace(free=100 * 1024**3)), patch.object(capture.subprocess, 'run', side_effect=native), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(capture.main(), 0)
        manifest = json.loads((self.root / 'cohort/manifest.json').read_text())
        self.assertEqual({r['model_id'] for r in manifest['models']}, {'research:' + digest for digest in hashes})
        self.assertEqual({r['research_label'] for r in manifest['models']}, {'prepared-v1'})
        self.assertEqual(len(manifest['runs']), 8)
        self.assertTrue(manifest['all_verified'])
        self.assertEqual({r['model_id'] for r in manifest['runs']}, {r['model_id'] for r in manifest['models']})

    def test_duplicate_research_identity_rejected_before_native(self):
        args = ['verify_vehicle_scale.py', str(self.root / 'duplicate'), '--binary', str(self.binary)]
        for _ in range(2):
            args += ['--research-descriptor', str(self.descriptor)]
        with patch.object(sys, 'argv', args), patch.object(capture.subprocess, 'run') as native:
            with self.assertRaisesRegex(ValueError, 'duplicate selected model identity'):
                capture.main()
            native.assert_not_called()
        self.assertFalse((self.root / 'duplicate').exists())


if __name__ == '__main__':
    unittest.main()
