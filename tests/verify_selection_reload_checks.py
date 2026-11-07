#!/usr/bin/env python3
"""verify_selection_reload.py with a stub native binary: index validation, timeout/launch
failure attribution, incremental manifest, repeated-index rejection, truncated events and
captures, and one-line operator errors for output/library mistakes."""
import contextlib
import io
import json
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import verify_selection_reload as v

try:
    import PIL  # noqa: F401
    HAVE_PIL = True
except ImportError:
    HAVE_PIL = False
# Sweeps convert captures with Pillow; library, index, action-script and manifest checks need none.
needs_pillow = unittest.skipUnless(HAVE_PIL, 'Pillow is required for the PPM-to-PNG sweep')

NAMES = [format(i + 1, 'x') * 64 for i in range(5)]
STUB = '''#!{python}
import json,os,sys
from pathlib import Path
a=sys.argv[1:]
def opt(name):return a[a.index(name)+1]
profile=Path(opt('--profile'));lib=Path(opt('--vehicle-library'))
names=[json.loads(l) for l in lib.read_text().splitlines()[2:]]
PPM=b'P6\\n1 1\\n255\\n\\x10\\x20\\x30'
if '--review-script' in a:
    acts=Path(opt('--review-script')).read_text().splitlines()
    left=acts.count('key left');idx=len(names)-left if left else acts.count('key right')
    if os.environ.get('STUB_HANG_INDEX')==str(idx):
        import time;time.sleep(30)
    profile.with_suffix('.txt.vehicle').write_text('vehicle-'+Path(names[idx]).stem+'\\n')
    Path(opt('--review-script')).with_name('selected.ppm').write_bytes(
        b'P6\\n100 100\\n255\\n\\x10' if os.environ.get('STUB_TRUNCATE_INDEX')==str(idx) else PPM)
else:
    saved=profile.with_suffix('.txt.vehicle').read_text().strip()
    hist=Path(opt('--diagnostics-dir'));hist.mkdir(parents=True,exist_ok=True)
    (hist/'e.jsonl').write_text(json.dumps({{'event':'asset_load_end','success':True,'sha256':saved[len('vehicle-'):]}})+'\\n{{"event": "asset_lo')
    Path(opt('--screenshot')).write_bytes(PPM)
'''


class Checks(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='racer-reload-')
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.lib = self.root / 'catalog.racer'
        self.lib.write_text('RACER_VEHICLES 1\n5\n' + ''.join(json.dumps(n + '.vehicle') + '\n' for n in NAMES))
        self.exe = self.root / 'stub-racer'
        self.exe.write_text(STUB.format(python=sys.executable))
        self.exe.chmod(self.exe.stat().st_mode | stat.S_IXUSR)

    def invoke(self, out, *indices, binary=None, extra=()):
        argv = [str(self.root / out), '--binary', str(binary or self.exe), '--library', str(self.lib), *extra]
        for i in indices:
            argv += ['--index', str(i)]
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = v.main(argv)
        return code, [json.loads(line) for line in buf.getvalue().splitlines()]

    @needs_pillow
    def test_wrapping_and_forward_selection_verify_each_car(self):
        code, lines = self.invoke('ok', 0, 1, 3, 4)
        self.assertEqual(code, 0)
        self.assertEqual([r['mesh'] for r in lines], [NAMES[i] for i in (0, 1, 3, 4)])
        self.assertTrue(all(r['verified'] for r in lines), lines)
        manifest = json.loads((self.root / 'ok/manifest.json').read_text())
        self.assertEqual(len(manifest['results']), 4)
        self.assertTrue((self.root / 'ok/car-3/reload.png').is_file())
        self.assertFalse(list((self.root / 'ok').rglob('*.ppm')))

    @needs_pillow
    def test_bad_indices_fail_before_any_directory_is_created(self):
        for indices in ((5,), (-1,), (0, 99), (2, 2)):
            with self.subTest(indices=indices):
                with self.assertRaises(SystemExit) as caught:
                    self.invoke('bad', *indices)
                self.assertIn('--index', str(caught.exception))
                self.assertFalse((self.root / 'bad').exists())

    @needs_pillow
    def test_missing_binary_and_library_are_rejected_up_front(self):
        with self.assertRaises(SystemExit) as caught:
            self.invoke('nobin', 0, binary=self.root / 'missing')
        self.assertIn('binary not found', str(caught.exception))
        self.assertFalse((self.root / 'nobin').exists())

    @needs_pillow
    def test_timeout_is_a_recorded_failure_and_earlier_results_survive(self):
        with patch.dict(os.environ, {'STUB_HANG_INDEX': '1'}):
            code, lines = self.invoke('hang', 0, 1, 2, extra=('--selection-timeout', '1'))
        self.assertEqual(code, 1)
        self.assertEqual([r['verified'] for r in lines], [True, False, True])
        self.assertFalse(lines[1]['checks']['first_exit'])
        self.assertIn('timed out after 1s', (self.root / 'hang/car-1/native1.log').read_text())
        manifest = json.loads((self.root / 'hang/manifest.json').read_text())
        self.assertEqual([r['index'] for r in manifest['results']], [0, 1, 2])

    @needs_pillow
    def test_truncated_capture_is_a_recorded_failure_and_the_sweep_continues(self):
        with patch.dict(os.environ, {'STUB_TRUNCATE_INDEX': '1'}):
            code, lines = self.invoke('trunc', 0, 1, 2)
        self.assertEqual(code, 1)
        self.assertEqual([r['verified'] for r in lines], [True, False, True])
        self.assertFalse(lines[1]['checks']['screens'])
        self.assertIn('selected.ppm', ' '.join(lines[1]['capture_errors']))
        self.assertEqual(lines[0]['capture_errors'], [])
        manifest = json.loads((self.root / 'trunc/manifest.json').read_text())
        self.assertEqual([r['index'] for r in manifest['results']], [0, 1, 2])
        self.assertTrue((self.root / 'trunc/car-1/selected.ppm.corrupt').is_file())
        self.assertFalse(list((self.root / 'trunc').rglob('*.ppm')))

    @needs_pillow
    def test_operator_input_errors_exit_with_one_line_before_anything_runs(self):
        (self.root / 'existing').mkdir()
        bad_line = self.root / 'bad-line.racer'
        bad_line.write_text('RACER_VEHICLES 1\n2\n"a.vehicle"\nnot-json\n')
        short = self.root / 'short.racer'
        short.write_text('RACER_VEHICLES 1\n3\n"a.vehicle"\n')
        header = self.root / 'header.racer'
        header.write_text('NOT_A_LIBRARY\n1\n"a.vehicle"\n')
        count = self.root / 'count.racer'
        count.write_text('RACER_VEHICLES 1\nmany\n"a.vehicle"\n')
        cases = [('existing', self.lib, 'already exists'), ('o-line', bad_line, 'line 4'), ('o-short', short, 'declares 3'),
                 ('o-header', header, 'bad header'), ('o-count', count, 'entry count')]
        for out, library, text in cases:
            with self.subTest(out=out):
                self.lib, saved = library, self.lib
                try:
                    with self.assertRaises(SystemExit) as caught:
                        self.invoke(out, 0)
                finally:
                    self.lib = saved
                self.assertIn(text, str(caught.exception))
                if out != 'existing':
                    self.assertFalse((self.root / out).exists())
        self.assertEqual(list((self.root / 'existing').iterdir()), [])

    def test_library_and_index_validation_run_without_pillow(self):
        bad = {'RACER_VEHICLES 2\n1\n"a.vehicle"\n': 'bad header', 'RACER_VEHICLES 1\nmany\n"a.vehicle"\n': 'entry count',
               'RACER_VEHICLES 1\n2\n"a.vehicle"\nnot-json\n': 'line 4', 'RACER_VEHICLES 1\n1\n7\n': 'non-empty descriptor name',
               'RACER_VEHICLES 1\n3\n"a.vehicle"\n': 'declares 3', '': 'bad header'}
        for text, reason in bad.items():
            with self.subTest(reason=reason, text=text[:24]):
                path = self.root / 'lib-case.racer'
                path.write_text(text)
                with self.assertRaises(SystemExit) as caught:
                    v.library_names(path)
                self.assertIn(reason, str(caught.exception))
        self.assertEqual(v.library_names(self.lib), [n + '.vehicle' for n in NAMES])
        for indices in ((5,), (-1,), (0, 99), (2, 2)):
            with self.subTest(indices=indices):
                with self.assertRaises(SystemExit):
                    v.validate_indices(list(indices), 5)
        v.validate_indices([0, 4, 2], 5)

    def test_selection_actions_step_the_shorter_way_round_the_library(self):
        capture = Path('shot.ppm')
        self.assertEqual(v.selection_actions(0, 5, capture)[3:-3], [])
        forward = v.selection_actions(2, 5, capture)
        self.assertEqual(forward.count('key right'), 2)
        self.assertEqual(forward.count('key left'), 0)
        wrapped = v.selection_actions(4, 5, capture)
        self.assertEqual((wrapped.count('key left'), wrapped.count('key right')), (1, 0))
        self.assertEqual(v.selection_actions(3, 5, capture).count('key left'), 2)
        self.assertEqual(wrapped[-3:], ['wait 1', 'capture shot.ppm', 'quit'])

    def test_manifest_rewrite_is_atomic_and_keeps_earlier_results_when_it_fails(self):
        first = [{'index': 0, 'verified': True}]
        v.write_manifest(self.root, '720', self.exe, self.lib, first)
        before = (self.root / 'manifest.json').read_text()
        with patch.object(v.os, 'replace', side_effect=OSError(28, 'No space left on device')):
            with self.assertRaises(OSError):
                v.write_manifest(self.root, '720', self.exe, self.lib, first + [{'index': 1, 'verified': False}])
        self.assertEqual((self.root / 'manifest.json').read_text(), before)
        self.assertEqual(len(json.loads(before)['results']), 1)
        v.write_manifest(self.root, '720', self.exe, self.lib, first + [{'index': 1, 'verified': True}])
        self.assertEqual(len(json.loads((self.root / 'manifest.json').read_text())['results']), 2)
        self.assertFalse((self.root / 'manifest.json.tmp').exists())

    def test_production_library_passes_the_header_and_count_validation(self):
        production = ROOT / 'assets/local/vehicles/catalog.racer'
        if not production.is_file():
            self.skipTest('production vehicle library absent')
        names = v.library_names(production)
        self.assertEqual(len(names), len(set(names)))
        self.assertTrue(all(n.endswith('.vehicle') for n in names))

    @needs_pillow
    def test_launch_failure_is_recorded_not_raised(self):
        notexec = self.root / 'notexec'
        notexec.write_text('x')
        code, lines = self.invoke('launch', 0, binary=notexec)
        # a non-executable binary is a launch failure per car, reported through the exit status
        self.assertEqual(code, 1)
        self.assertFalse(lines[0]['verified'])
        manifest = json.loads((self.root / 'launch/manifest.json').read_text())
        self.assertFalse(manifest['results'][0]['verified'])
        self.assertIn('launch failed', (self.root / 'launch/car-0/native1.log').read_text())


if __name__ == '__main__':
    unittest.main()
