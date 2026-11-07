"""Exercise native CLI paths with generated geometry, never installed game data."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'tests'))
from gt4_preparation_checks import fixture
from prepare_gt4_vehicle import pack, prepare

VALIDATOR = Path(sys.argv.pop(1)).resolve()


class Checks(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='racer-cli-')
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        doc, binary = fixture()
        mesh, text, receipt = prepare(pack(doc, binary), 'gran-turismo-4/fixture', 'CLI fixture')
        self.descriptor = self.root / (receipt['prepared_sha256'] + '.vehicle')
        self.descriptor.write_text(text)
        self.descriptor.with_suffix('.glb').write_bytes(mesh)
        self.catalog = self.root / 'catalog.racer'
        self.catalog.write_text('RACER_VEHICLES 1\n1\n"' + self.descriptor.name + '"\n')

    def run_cli(self, *args):
        return subprocess.run([str(VALIDATOR), *map(str, args)], capture_output=True,
                              text=True, timeout=10, cwd=self.root)

    def test_single_and_library_paths_report_same_checked_mesh(self):
        direct = self.run_cli('--descriptor', self.descriptor)
        library = self.run_cli(self.catalog)
        self.assertEqual(direct.returncode, 0, direct.stderr)
        self.assertEqual(library.returncode, 0, library.stderr)
        self.assertEqual(direct.stdout, library.stdout)
        self.assertIn('sha=' + self.descriptor.stem, direct.stdout)
        self.assertIn('wheelbase=', direct.stdout)

    def test_missing_and_wrong_mesh_fail_without_rewriting_input(self):
        missing = self.run_cli('--descriptor', self.root / 'missing.vehicle')
        self.assertEqual(missing.returncode, 1)
        mesh = self.descriptor.with_suffix('.glb')
        mesh.write_bytes(b'corrupt')
        result = self.run_cli('--descriptor', self.descriptor)
        self.assertEqual(result.returncode, 1)
        self.assertIn('REJECT:', result.stderr)
        self.assertEqual(mesh.read_bytes(), b'corrupt')

    def test_usage_and_existing_path_restriction(self):
        for args in [(), ('--descriptor',), ('--unknown', self.descriptor),
                     ('--descriptor', self.descriptor, 'extra')]:
            with self.subTest(args=args):
                self.assertEqual(self.run_cli(*args).returncode, 2)
        self.descriptor.write_text(self.descriptor.read_text().replace(
            self.descriptor.stem + '.glb', '../foreign.glb'))
        result = self.run_cli('--descriptor', self.descriptor)
        self.assertEqual(result.returncode, 1)
        self.assertIn('vehicle_descriptor_path', result.stderr)


if __name__ == '__main__':
    unittest.main()
