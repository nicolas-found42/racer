#!/usr/bin/env python3
"""Feedback runner provenance checks; native process and image output always mocked."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import prepare_gt4_vehicle as gt4
import gt4_preparation_checks as fixtures


def digest(data):
    return hashlib.sha256(data).hexdigest()


class FakeImage:
    size = (1280, 720)
    def load(self): pass
    def save(self, path): Path(path).write_bytes(b'mocked image bytes')
    def tobytes(self): return b'mocked image bytes'


class FakeProcess:
    returncode = 0
    def poll(self): return 0
    def kill(self): raise AssertionError('unexpected fixture kill')
    def wait(self): return 0


class Checks(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='racer-feedback-check-')
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.descriptors = []
        self.hashes = []
        for code in ('first', 'second'):
            document, buffer = fixtures.fixture()
            document['extras']['car'] = code
            mesh, text, receipt = gt4.prepare(gt4.pack(document, buffer), 'gran-turismo-4/' + code, code)
            path = self.root / (receipt['prepared_sha256'] + '.vehicle')
            path.write_text(text)
            path.with_suffix('.glb').write_bytes(mesh)
            self.descriptors.append(path)
            self.hashes.append(receipt['prepared_sha256'])
        self.library = self.root / 'catalog.racer'
        self.library.write_text('RACER_VEHICLES 1\n2\n' + ''.join(json.dumps(p.name) + '\n' for p in self.descriptors))
        self.binary = self.root / 'mock-native'
        self.binary.write_bytes(b'fixture executable; never executed')
        self.output = self.root / 'out'
        self.launched = None

    def invoke(self, mutation=None, event_sha=None, index=1, name='out'):
        self.output = self.root / name
        def launch(command, **kwargs):
            self.launched = command
            if mutation: mutation(command)
            script = Path(command[command.index('--review-script') + 1])
            for line in script.read_text().splitlines():
                if line.startswith('capture '): Path(line[8:]).write_bytes(b'mocked ppm')
            history = Path(command[command.index('--diagnostics-dir') + 1])
            history.mkdir()
            event = {'event': 'asset_load_end', 'success': True, 'sha256': event_sha or self.hashes[index]}
            (history / 'fixture.jsonl').write_text(json.dumps(event) + '\n')
            return FakeProcess()
        args = ['verify_feedback.py', str(self.output), '--size', '720', '--binary', str(self.binary), '--vehicle-library', str(self.library), '--vehicle', str(index)]
        with patch.object(sys, 'argv', args), patch.object(subprocess, 'Popen', side_effect=launch), patch.object(Image, 'open', return_value=FakeImage()), contextlib.redirect_stdout(io.StringIO()):
            runpy.run_path(str(ROOT / 'scripts/verify_feedback.py'), run_name='__main__')
        return self.manifest()

    def manifest(self):
        return json.loads((self.output / 'manifest.json').read_text())

    def test_nonzero_selection_is_frozen_as_exact_single_entry(self):
        original = self.library.read_bytes()
        result = self.invoke()
        command = self.launched
        frozen = Path(command[command.index('--vehicle-library') + 1])
        self.assertEqual(command[command.index('--vehicle') + 1], '0')
        self.assertEqual(result['source_vehicle_index'], 1)
        self.assertEqual(result['source_library'], str(self.library))
        self.assertEqual(result['library_sha256'], digest(original))
        self.assertEqual(frozen.read_text().splitlines(), ['RACER_VEHICLES 1', '1', json.dumps(self.descriptors[1].name)])
        self.assertEqual(result['expected_mesh_sha256'], self.hashes[1])
        self.assertTrue(result['frozen_inputs_unchanged'])
        self.assertTrue(result['exact_asset_loaded'])
        self.assertEqual(len(result['captures']), 37)

    def test_source_mutations_do_not_change_runtime_bundle(self):
        descriptor = self.descriptors[1].read_bytes()
        mesh = self.descriptors[1].with_suffix('.glb').read_bytes()
        executable = self.binary.read_bytes()
        def mutate(command):
            self.descriptors[1].write_bytes(b'changed source descriptor')
            self.descriptors[1].with_suffix('.glb').write_bytes(b'changed source mesh')
            self.library.write_bytes(b'changed source library')
            self.binary.write_bytes(b'changed source executable')
        result = self.invoke(mutation=mutate)
        self.assertEqual((self.output / 'models' / self.descriptors[1].name).read_bytes(), descriptor)
        self.assertEqual((self.output / 'models' / self.descriptors[1].with_suffix('.glb').name).read_bytes(), mesh)
        self.assertEqual((self.output / 'racer').read_bytes(), executable)
        self.assertEqual(result['descriptor_sha256'], digest(descriptor))
        self.assertEqual(result['build_sha256'], digest(executable))
        self.assertTrue(result['frozen_inputs_unchanged'])

    def test_frozen_input_mutation_rejects_even_matching_mesh_event(self):
        for kind in ('descriptor', 'mesh', 'library', 'executable'):
            with self.subTest(kind=kind):
                def mutate(command):
                    models = self.output / 'models'
                    paths = {'descriptor': models / self.descriptors[1].name,
                             'mesh': models / self.descriptors[1].with_suffix('.glb').name,
                             'library': models / 'catalog.racer', 'executable': Path(command[0])}
                    paths[kind].write_bytes(b'changed frozen input')
                with self.assertRaises(AssertionError): self.invoke(mutation=mutate, name=kind)
                result = self.manifest()
                self.assertTrue(result['exact_asset_loaded'])
                self.assertFalse(result['frozen_inputs_unchanged'])

    def test_other_car_successful_event_is_not_selected_car_evidence(self):
        with self.assertRaises(AssertionError): self.invoke(event_sha=self.hashes[0])
        self.assertFalse(self.manifest()['exact_asset_loaded'])

    def test_invalid_selection_rejected_before_launch(self):
        with self.assertRaisesRegex(ValueError, 'vehicle library or selection'): self.invoke(index=2)
        self.assertIsNone(self.launched)
        self.assertFalse(self.output.exists())

    def test_changed_source_mesh_rejected_before_launch(self):
        self.descriptors[1].with_suffix('.glb').write_bytes(b'wrong mesh')
        with self.assertRaisesRegex(ValueError, 'selected mesh hash mismatch'): self.invoke()
        self.assertIsNone(self.launched)
        self.assertFalse(self.output.exists())


if __name__ == '__main__':
    unittest.main()
