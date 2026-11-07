#!/usr/bin/env python3
"""juiced2_wheel_state.py / juiced2_wheel_attributions.py: whole-file pins, strict TyreCode parsing,
actionable archive failures, chain-versus-kernel agreement, derived gear comparison and corrected
f4 provenance text (synthetic archives; retained-archive reproduction skips when absent)."""
import hashlib
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import juiced2_wheel_attributions as attributions
import juiced2_wheel_state as state
import new_report
from juiced2_wheel_contract import sizing_fields

PROFILE = {'object436': state.PROFILE_MAX_X, 'object440': state.PROFILE_MIN_Y, 'object444': state.PROFILE_MAX_Y}
CODES = ['195/55R16', '205/55R16', '225/45R18', '225/60R18', '245/45R18', '255/35R19', '355/30R20']


def record(index, front='225/45R18', rear='245/45R18', extra=()):
    fields = [['Mass', 1000], ['PeakBhp', 100, '@', 5000], ['Redline', 7000], ['EngineSize', 2000], *extra,
              ['Location', 'FRONT'], ['TyreCode', front], ['Location', 'REAR'], ['TyreCode', rear]]
    return {'index': index, 'key': format(index, '08x'), 'sha256': format(index, '064x'), 'decoded_fields': fields}


def archive(root, extra_records=()):
    records = [record(i) for i in (755, 922, 664, 517)]
    records.append(record(962, '195/55R16', '195/55R16',
                          [['GearRatios', 3.308, 2.13, 1.48, 1.139, 0.95, 0.816]]))
    records += list(extra_records)
    path = Path(root) / 'handling-parameters.json'
    path.write_text(json.dumps({'parameters': records}))
    return path


def call(module, *argv):
    out = StringIO()
    with patch.object(sys, 'argv', [module.__file__, *argv]), redirect_stdout(out):
        module.main()
    return json.loads(out.getvalue())


class Checks(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='racer-wheelstate-')
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)

    def test_sha256_file_hashes_the_whole_file_and_refuses_to_truncate(self):
        data = bytes(range(256)) * (5 * 4096)  # 5 MiB, larger than one read chunk
        path = self.root / 'big.bin'
        path.write_bytes(data)
        self.assertEqual(state.sha256_file(path, limit=8 * 1024**2), hashlib.sha256(data).hexdigest())
        with self.assertRaises(SystemExit) as caught:
            state.sha256_file(path, limit=len(data) - 1)
        self.assertIn('refusing to hash a prefix', str(caught.exception))
        self.assertEqual(state.sha256_file(path, limit=len(data)), hashlib.sha256(data).hexdigest())
        self.assertFalse(hasattr(state, 'digest'), 'the unused prefix-hashing digest() must stay removed')

    def test_tyre_code_parser_is_strict_and_names_the_code(self):
        for code in ('225/45ZR18', '0/45R18', '225/0R18', '225/45R0', '-225/45R18', '225/45R18 ', '225/45/R18', '', None, 225):
            with self.subTest(code=code):
                with self.assertRaises(ValueError) as caught:
                    state.parse_tyre_code(code)
                self.assertIn(repr(code), str(caught.exception))
        parsed = state.parse_tyre_code('225/45R18')
        self.assertEqual((parsed['W'], parsed['A'], parsed['R']), (225, 45, 18))

    def test_sizing_chain_agrees_with_the_audited_kernel_for_every_tyre(self):
        for code in CODES:
            with self.subTest(code=code):
                chain = state.sizing_chain(state.parse_tyre_code(code))
                out = sizing_fields(PROFILE, chain['f1_width'], chain['f2_aspect'], chain['forwarded_f3'])
                self.assertEqual((chain['xscale'], chain['radial_scale'], chain['extra_424']),
                                 (out['object292'], out['object296'], out['object424']))

    def test_record_fields_ignores_a_tyre_code_before_any_location(self):
        rec = {'decoded_fields': [['TyreCode', '225/45R18'], ['Location', 'FRONT'], ['TyreCode', '195/55R16'], ['Mass', 900]]}
        fields, wheels = state.record_fields(rec)
        self.assertEqual(wheels, {'FRONT': {'TyreCode': '195/55R16'}})
        self.assertEqual(fields['Mass'], [900])

    def test_missing_or_malformed_archive_fails_with_an_actionable_message(self):
        for module in (state, attributions):
            with self.subTest(module=module.__name__, case='missing'):
                with self.assertRaises(SystemExit) as caught:
                    call(module, '--archive', str(self.root / 'absent.json'), '--output', str(self.root / 'o.json'))
                self.assertIn('--archive', str(caught.exception))
                self.assertIn('absent.json', str(caught.exception))
            with self.subTest(module=module.__name__, case='malformed'):
                bad = self.root / 'bad.json'
                bad.write_text('{"not": "an archive"}')
                with self.assertRaises(SystemExit) as caught:
                    call(module, '--archive', str(bad), '--output', str(self.root / 'o2.json'))
                self.assertIn('not a handling-parameters archive', str(caught.exception))
        self.assertFalse((self.root / 'o.json').exists())

    def test_structurally_wrong_archives_are_rejected_by_both_generators_without_output(self):
        good = record(1)
        cases = {
            'list-not-object': ({'parameters': 5}, 'non-empty list'),
            'empty': ({'parameters': []}, 'non-empty list'),
            'record-not-object': ({'parameters': [3]}, 'is not an object'),
            'missing-fields': ({'parameters': [{'index': 1}]}, 'lacks key, sha256, decoded_fields'),
            'bad-index': ({'parameters': [dict(good, index='1')]}, 'non-integer index'),
            'duplicate-index': ({'parameters': [good, dict(good)]}, 'repeats index 1'),
            'fields-not-list': ({'parameters': [dict(good, decoded_fields={})]}, 'non-list decoded_fields'),
            'location-without-value': ({'parameters': [dict(good, decoded_fields=[['Location']])]}, 'Location entry without a value'),
            'unhashable-name': ({'parameters': [dict(good, decoded_fields=[[['x'], 1]])]}, 'non-string name'),
            'location-not-string': ({'parameters': [dict(good, decoded_fields=[['Location', ['x']]])]}, "non-string Location value ['x']"),
            'tyrecode-not-string': ({'parameters': [dict(good, decoded_fields=[['Location', 'FRONT'], ['TyreCode', 5]])]}, 'non-string TyreCode value 5'),
        }
        for module in (state, attributions):
            for name, (document, text) in cases.items():
                with self.subTest(module=module.__name__, case=name):
                    path = self.root / f'{name}.json'
                    path.write_text(json.dumps(document))
                    out = self.root / f'{module.__name__}-{name}.out'
                    with self.assertRaises(SystemExit) as caught:
                        call(module, '--archive', str(path), '--output', str(out))
                    self.assertIn(text, str(caught.exception))
                    self.assertIn(str(path), str(caught.exception))
                    self.assertFalse(out.exists())

    def test_output_path_errors_are_one_line_and_create_nothing_in_both_generators(self):
        path = archive(self.root)
        existing = self.root / 'existing.json'
        existing.write_text('keep')
        for module in (state, attributions):
            cases = [(existing, [], 'already exists'), (self.root / 'nodir' / 'x.json', [], 'directory does not exist'),
                     (self.root / f'{module.__name__}-tiny.json', ['--max-bytes', '10'], 'output budget exceeded')]
            for out, extra, text in cases:
                with self.subTest(module=module.__name__, case=text):
                    with self.assertRaises(SystemExit) as caught:
                        call(module, '--archive', str(path), '--output', str(out), *extra)
                    self.assertIn(text, str(caught.exception))
                    shown = str(caught.exception)
                    if 'budget' in text:
                        self.assertIn(' > 10', shown)
                    else:
                        self.assertIn(str(out if 'already' in text else out.parent), shown)
                    self.assertNotIn('\n', str(caught.exception))
                    self.assertFalse(out.exists() and out != existing)
        self.assertEqual(existing.read_text(), 'keep')

    def test_write_new_report_has_exact_budget_exclusive_create_and_directory_branches(self):
        ok = self.root / 'ok.json'
        new_report.write_new_report(ok, b'1234', 4)  # exactly at the budget is allowed
        self.assertEqual(ok.read_bytes(), b'1234')
        cases = [(ok, b'x', 10, 'already exists'), (self.root, b'x', 10, 'already exists'),
                 (self.root / 'big.json', b'12345', 4, 'output budget exceeded: 5 > 4'),
                 (self.root / 'absent' / 'x.json', b'x', 10, 'output directory does not exist')]
        for path, payload, limit, text in cases:
            with self.subTest(text=text, path=path.name):
                with self.assertRaises(SystemExit) as caught:
                    new_report.write_new_report(path, payload, limit)
                self.assertIn(text, str(caught.exception))
        self.assertEqual(ok.read_bytes(), b'1234')
        self.assertFalse((self.root / 'big.json').exists())
        if os.geteuid() != 0:
            locked = self.root / 'locked'
            locked.mkdir()
            locked.chmod(stat.S_IRUSR | stat.S_IXUSR)
            self.addCleanup(locked.chmod, stat.S_IRWXU)
            with self.assertRaises(SystemExit) as caught:
                new_report.write_new_report(locked / 'x.json', b'x', 10)
            self.assertIn('cannot create', str(caught.exception))
            self.assertFalse((locked / 'x.json').exists())

    def test_attributions_name_every_absent_record_before_writing(self):
        path = self.root / 'few.json'
        path.write_text(json.dumps({'parameters': [record(755), record(1)]}))
        out = self.root / 'few.out'
        with self.assertRaises(SystemExit) as caught:
            call(attributions, '--archive', str(path), '--output', str(out))
        message = str(caught.exception)
        for index in (517, 664, 922, 962):
            self.assertIn(str(index), message)
        self.assertNotIn('755', message)
        self.assertFalse(out.exists())

    def test_malformed_attributed_tyre_codes_are_reported_with_record_model_and_axle_before_writing(self):
        bad = record(922, '225/45R18x', '0/60R18')
        path = self.root / 'badcodes.json'
        path.write_text(json.dumps({'parameters': [record(755), bad, record(664), record(517), record(962)]}))
        out = self.root / 'badcodes.out'
        with self.assertRaises(SystemExit) as caught:
            call(attributions, '--archive', str(path), '--output', str(out))
        message = str(caught.exception)
        self.assertIn('record 922 (juiced-2/CHARGER_RT) FRONT', message)
        self.assertIn("'225/45R18x'", message)
        self.assertIn('REAR', message)
        self.assertIn("'0/60R18'", message)
        self.assertNotIn('\n', message)
        self.assertFalse(out.exists())

    def mutation_fuzz(self, base, rounds, seed):
        """Run both generators over seeded structural mutations of `base`; return (escapes, outcome counts)."""
        import copy
        import random
        rnd = random.Random(seed)
        attributed = [r['record_index'] for r in attributions.ATTRIBUTIONS.values()]
        codes = [5, None, '', '225/45R18x', '0/0R0', [1], {'a': 1}, '\u0662\u0662\u0665/45R18', '1' * 9 + '/45R18', '225/45R18']
        escapes = []
        outcomes = {'ok': 0, 'exit': 0}
        for n in range(rounds):
            doc = copy.deepcopy(base)
            parameters = doc['parameters']
            for _ in range(rnd.randint(1, 3)):
                records = [r for r in parameters if isinstance(r, dict)]
                if rnd.random() < 0.6:
                    records = [r for r in records if r.get('index') in attributed] or records
                target = rnd.choice(records)
                fields = target.get('decoded_fields') if isinstance(target.get('decoded_fields'), list) else []
                kind = rnd.choice(['drop', 'tyre', 'location', 'fields', 'index', 'replace'])
                if kind == 'drop':
                    target.pop(rnd.choice(list(target)), None)
                elif kind == 'tyre':
                    for entry in fields:
                        if isinstance(entry, list) and len(entry) > 1 and entry[0] == 'TyreCode':
                            entry[1] = rnd.choice(codes)
                elif kind == 'location':
                    for entry in fields:
                        if isinstance(entry, list) and len(entry) > 1 and entry[0] == 'Location':
                            entry[1] = rnd.choice([None, 5, ['x'], '', 'FRONT'])
                elif kind == 'fields':
                    target['decoded_fields'] = rnd.choice([None, {}, 'x', [None], [[]], [5]])
                elif kind == 'index':
                    target['index'] = rnd.choice([None, 'a', 1.5, True, -1, 755])
                else:
                    parameters[rnd.randrange(len(parameters))] = rnd.choice([None, 5, 'x', []])
            path = self.root / f'fuzz{n}.json'
            path.write_text(json.dumps(doc))
            for module in (state, attributions):
                out = self.root / f'fuzz{n}-{module.__name__}.out'
                try:
                    call(module, '--archive', str(path), '--output', str(out))
                    outcomes['ok'] += 1
                except SystemExit as error:
                    outcomes['exit'] += 1
                    if '\n' in str(error) or not str(error):
                        escapes.append((n, module.__name__, 'multi-line or empty exit', str(error)[:80]))
                    if out.exists():
                        escapes.append((n, module.__name__, 'output created despite failure', ''))
                except Exception as error:  # noqa: BLE001 - the point of the test is that nothing else escapes
                    escapes.append((n, module.__name__, type(error).__name__, str(error)[:80]))
        return escapes, outcomes

    def test_seeded_mutation_fuzz_ends_only_in_success_or_a_one_line_exit(self):
        escapes, outcomes = self.mutation_fuzz(json.loads(archive(self.root).read_text()), 240, 20261107)
        self.assertEqual(escapes, [])
        self.assertGreater(outcomes['ok'], 5)
        self.assertGreater(outcomes['exit'], 200)

    def test_seeded_mutation_fuzz_of_the_retained_archive_ends_only_in_success_or_a_one_line_exit(self):
        if not state.PARAMETERS.is_file():
            self.skipTest('retained handling archive absent')
        escapes, outcomes = self.mutation_fuzz(json.loads(state.PARAMETERS.read_text()), 500, 20261107)
        self.assertEqual(escapes, [])
        self.assertGreater(outcomes['ok'], 50)
        self.assertGreater(outcomes['exit'], 300)

    def test_attributed_record_without_tyre_code_is_rejected(self):
        untyred = {'index': 922, 'key': 'k', 'sha256': 's', 'decoded_fields': [['Mass', 1]]}
        path = self.root / 'untyred.json'
        path.write_text(json.dumps({'parameters': [record(755), untyred, record(664), record(517), record(962)]}))
        with self.assertRaises(SystemExit) as caught:
            call(attributions, '--archive', str(path), '--output', str(self.root / 'untyred.out'))
        self.assertIn('juiced-2/CHARGER_RT', str(caught.exception))
        self.assertIn('no TyreCode', str(caught.exception))

    def test_tyre_code_parser_rejects_non_ascii_and_oversized_digits_naming_the_code(self):
        for code in ('\u0662\u0662\u0665/\u0664\u0665R\u0661\u0668', '225/45R\uff11\uff18', '9' * 5000 + '/45R18',
                     '1234567/45R18', '225/45R1234567'):
            with self.subTest(code=code[:20]):
                with self.assertRaises(ValueError) as caught:
                    state.parse_tyre_code(code)
                self.assertIn(repr(code), str(caught.exception))
        self.assertEqual(state.parse_tyre_code('225/45R18')['W'], 225)
        self.assertEqual(state.parse_tyre_code('355/30R20')['R'], 20)

    def test_chain_kernel_divergence_guard_survives_python_dash_o(self):
        code = ('import sys; sys.path.insert(0, %r)\n'
                'import juiced2_wheel_attributions as a\n'
                'real = a.sizing_fields\n'
                'a.sizing_fields = lambda *x, **k: dict(real(*x, **k), object424=real(*x, **k)["object424"] + 1e-3)\n'
                'a.kernel_sizing("225/45R18")\n') % str(ROOT / 'scripts')
        env = {'PYTHONDONTWRITEBYTECODE': '1', 'PATH': '/usr/bin:/bin'}
        for flags in ([], ['-O']):
            with self.subTest(flags=flags):
                run = subprocess.run([sys.executable, *flags, '-c', code], capture_output=True, text=True, env=env, timeout=60)
                self.assertNotEqual(run.returncode, 0, run.stdout)
                self.assertIn('chain/kernel divergence', run.stderr)

    def test_published_attribution_labels_and_units_match_their_evidence(self):
        charger = attributions.ATTRIBUTIONS['juiced-2/CHARGER_RT']
        self.assertNotIn('exact-4', charger['confidence'])
        self.assertIn('335 bhp vs factory 340 hp', charger['basis'])
        self.assertTrue(all('exact-4' not in a['confidence'] for a in attributions.ATTRIBUTIONS.values()))
        z4 = attributions.ATTRIBUTIONS['juiced-2/Z4']['factory_reference']
        self.assertEqual(z4['power_ps'], 343)
        self.assertNotIn('power_bhp', z4)
        if state.PARAMETERS.is_file():  # derive the exact-field count from the retained record
            raw, parameters = state.load_parameters(state.PARAMETERS)
            fields, wheels = state.record_fields({r['index']: r for r in parameters}[922])
            ref = charger['factory_reference']
            exact = [fields['EngineSize'][0] == ref['displacement_cc'], fields['Mass'][0] == ref['kerb_weight_kg'],
                     wheels['FRONT']['TyreCode'] == ref['tyre_front'].lstrip('P'), fields['PeakBhp'][0] == ref['power_hp']]
            self.assertEqual(sum(exact), 3)
            self.assertIn('3-of-4', charger['confidence'])

    def test_state_report_pins_the_whole_archive_and_states_the_corrected_f4_trace(self):
        path = archive(self.root, [record(1, '225/45R18', '245/45R18')])
        summary = call(state, '--archive', str(path), '--output', str(self.root / 'state.json'))
        report = json.loads((self.root / 'state.json').read_text())
        self.assertEqual(summary['records'], 6)
        self.assertEqual(report['inputs']['handling_parameters_sha256'], hashlib.sha256(path.read_bytes()).hexdigest())
        self.assertEqual(report['inputs']['handling_parameters_path'], str(path))
        construction = report['f4_trace']['construction']
        self.assertIn('not NULL', construction)
        self.assertIn('car object', construction)
        self.assertNotIn('initialized NULL', construction)

    def test_attributions_derive_tyres_signature_and_gear_comparison_from_the_archive(self):
        stray = record(7, '225/45R18', '245/45R18')
        stray['decoded_fields'].insert(0, ['TyreCode', '999/99R99'])  # before any Location: must not become an axle
        path = archive(self.root, [stray])
        call(attributions, '--archive', str(path), '--output', str(self.root / 'attr.json'))
        report = json.loads((self.root / 'attr.json').read_text())
        self.assertEqual(report['inputs']['handling_archive_sha256'], hashlib.sha256(path.read_bytes()).hexdigest())
        for key in ('kernel_script_sha256', 'state_script_sha256', 'generator_script_sha256'):
            self.assertEqual(len(report['inputs'][key]), 64)
        mini = report['attributions']['juiced-2/MINI']
        self.assertEqual(mini['tyres'], {'FRONT': '195/55R16', 'REAR': '195/55R16'})
        comparison = mini['gear_ratio_comparison']
        self.assertEqual((comparison['identical_positions'], comparison['positions']), (4, 6))
        self.assertEqual(comparison['max_abs_difference'], 0.003)
        text = json.dumps(mini['factory_reference']) + mini['basis'] + mini.get('generation_note', '')
        self.assertNotIn('6/6', text)
        self.assertNotIn('exactly (6', text)
        self.assertNotIn('definitively', text)
        self.assertEqual(report['attributions']['juiced-2/Z4']['tyres'], {'FRONT': '225/45R18', 'REAR': '245/45R18'})
        self.assertNotIn(None, report['attributions']['juiced-2/Z4']['tyres'])

    def test_retained_archive_reproduces_the_retained_v7_data_fields(self):
        v7 = ROOT / 'experiments/2026-11-06-juiced2-wheel-args/output/attributions-v7.json'
        if not state.PARAMETERS.is_file() or not v7.is_file():
            self.skipTest('retained archive or attributions-v7.json absent')
        call(attributions, '--output', str(self.root / 'now.json'))
        now = json.loads((self.root / 'now.json').read_text())['attributions']
        old = json.loads(v7.read_text())['attributions']
        for model, entry in old.items():
            for field in ('record_index', 'tyres', 'record_signature', 'native_sizing_f4_1'):
                self.assertEqual(now[model][field], entry[field], (model, field))


if __name__ == '__main__':
    unittest.main()
