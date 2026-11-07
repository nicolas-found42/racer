#!/usr/bin/env python3
"""car_stages.py: evidence-path strictness, family-credit limits, derived (not asserted) report
text, and the player-invariant failure (the three whole-report tests skip without the retained
public catalog or production library; the stage-rule tests always run)."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import car_stages as cs

# Only the tests that run the whole reconciliation need the retained public and production catalogs;
# the stage rules and evidence strictness are exercised on every checkout.
needs_catalogs = unittest.skipUnless(cs.PUBLIC_CATALOG.exists() and cs.CATALOG_PATH.exists(),
                                     'retained public catalog or production vehicle library absent')


def row(model, evidence=None, role='research-candidate', sha='a' * 64, **extra):
    base = {'model_id': model, 'prepared_sha256': sha, 'source_sha256': 'b' * 64, 'descriptor_sha256': 'c' * 64,
            'role': role, 'review_evidence': evidence or {}, 'measured': {'x': 1}}
    base.update(extra)
    return base


class Checks(unittest.TestCase):
    def test_evidence_file_accepts_only_existing_relative_regular_files_inside_the_project(self):
        self.assertTrue(cs.evidence_file('README.md'))
        for bad in ('', '   ', None, 7, '.', 'tests', str(ROOT / 'README.md'),
                    '../../AGENTS.md', '../../../../../../etc/hosts', 'experiments/does-not-exist.json'):
            with self.subTest(value=bad):
                self.assertFalse(cs.evidence_file(bad))

    def test_empty_or_non_file_evidence_grants_neither_discovery_nor_runtime_review(self):
        stages = cs.stage_row(row('juiced-2/XX', {'note': '', 'motion': '', 'native_views': '.', 'garage': 'tests'}),
                              set(), set(), set())['stages']
        self.assertFalse(stages['discovered'])
        self.assertFalse(stages['runtime_reviewed'])
        self.assertIsNone(stages['runtime_basis'])

    def test_real_file_evidence_is_credited_with_its_path(self):
        stages = cs.stage_row(row('juiced-2/XX', {'motion': 'README.md'}), set(), set(), set())['stages']
        self.assertTrue(stages['discovered'])
        self.assertTrue(stages['runtime_reviewed'])
        self.assertEqual(stages['runtime_basis'], 'README.md')

    def test_family_credit_does_not_cover_juiced2_players_beyond_the_350z(self):
        catalog = {'a' * 64}
        z4 = cs.stage_row(row('juiced-2/Z4', role='player', player_eligible=True), catalog, set(), set())['stages']
        self.assertTrue(z4['integrated'])
        self.assertFalse(z4['runtime_reviewed'])
        for model in ('juiced-2/350Z', 'gran-turismo-4/xxxx0000'):
            with self.subTest(model=model):
                stages = cs.stage_row(row(model, role='player', player_eligible=True), catalog, set(), set())['stages']
                self.assertTrue(stages['runtime_reviewed'])

    def test_uninstalled_rows_are_blocked_without_claiming_a_storage_cause(self):
        result = cs.stage_row(row('ford-racing-2/XX'), set(), set(), set())
        self.assertTrue(result['stages']['blocked'])
        text = ' '.join(result['blocked_reasons'])
        self.assertIn('not installed in production catalog', text)
        self.assertNotIn('storage headroom', text.lower())

    def run_main(self, inventory=None):
        temp = tempfile.TemporaryDirectory(prefix='racer-stages-')
        self.addCleanup(temp.cleanup)
        out = Path(temp.name) / 'report.json'
        args = ['car_stages.py', '--output', str(out)]
        with patch.object(sys, 'argv', args):
            if inventory is None:
                cs.main()
            else:
                with patch.object(cs.inventory_format, 'decode', return_value={'vehicles': inventory}):
                    cs.main()
        return json.loads(out.read_text())

    @needs_catalogs
    def test_report_text_and_counts_are_derived_from_the_data(self):
        with open(os.devnull, 'w') as sink, patch('sys.stdout', sink):
            report = self.run_main()
        counts = report['counts']
        self.assertEqual(counts['players'], counts['integrated'] - sum(
            1 for r in report['models'] if r['role'] != 'player' and r['stages']['integrated']))
        self.assertIn('(%d in-scope)' % counts['public_catalog_in_scope'], report['stage_definitions']['discovered'])
        audit = ROOT / 'experiments/2026-11-06-slrr-coverage/output/canonical-chassis-coverage.json'
        if audit.exists():
            chassis = json.loads(audit.read_text())['chassis']
            self.assertEqual(report['slrr_native_audit']['declarations'], len(chassis))
            self.assertIn('SLRR %d declarations' % len(chassis), report['stage_definitions']['discovered'])
        self.assertFalse(any('storage headroom' in limit.lower() for limit in report['limits']))

    @needs_catalogs
    def test_output_path_errors_are_one_line_and_create_nothing(self):
        with tempfile.TemporaryDirectory(prefix='racer-stages-out-') as temp:
            existing = Path(temp) / 'existing.json'
            existing.write_text('keep')
            cases = [(existing, [], 'already exists'), (Path(temp) / 'nodir' / 'x.json', [], 'directory does not exist'),
                     (Path(temp) / 'tiny.json', ['--max-bytes', '10'], 'output budget exceeded')]
            for out, extra, text in cases:
                with self.subTest(case=text):
                    with patch.object(sys, 'argv', ['car_stages.py', '--output', str(out), *extra]):
                        with self.assertRaises(SystemExit) as caught:
                            cs.main()
                    self.assertIn(text, str(caught.exception))
                    self.assertNotIn('\n', str(caught.exception))
                    self.assertFalse(out.exists() and out != existing)
            self.assertEqual(existing.read_text(), 'keep')

    @needs_catalogs
    def test_player_missing_from_the_production_catalog_names_the_offender(self):
        stray = row('gran-turismo-4/zzzz9999', role='player', sha='f' * 64, player_eligible=True)
        with open(os.devnull, 'w') as sink, patch('sys.stdout', sink):
            with self.assertRaises(SystemExit) as caught:
                self.run_main([stray])
        self.assertIn('gran-turismo-4/zzzz9999', str(caught.exception))


if __name__ == '__main__':
    unittest.main()
