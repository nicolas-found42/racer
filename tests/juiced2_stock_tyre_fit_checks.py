#!/usr/bin/env python3
"""fit_juiced2_stock_tyres.py: pinned reproduction of the four published meshes and
independent verification that rejects tampered node transforms. Tests that need the retained cohort
preparations skip individually; the identity and CLI guards that need none always run."""
import copy
import hashlib
import json
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import fit_juiced2_stock_tyres as fit
import prepare_gt4_vehicle as g

COHORT = ROOT / 'experiments/2026-11-06-juiced2-cohort/output'
INVENTORY = ROOT / 'assets/catalog/prepared-sizes.json'
CARS = {'z4': 'juiced-2/Z4', 'mini': 'juiced-2/MINI', 'charger_rt': 'juiced-2/CHARGER_RT', 'koenigsegg': 'juiced-2/KOENIGSEGG'}
needs_cohort = unittest.skipUnless(
    all((COHORT / f'{car}-prepared-v1/receipt.json').is_file() for car in CARS) and INVENTORY.is_file(),
    'retained Juiced 2 cohort preparations or inventory absent')


def prepared(car):
    glb, desc, receipt, data, toks, roles = fit.load_prepared(COHORT / f'{car}-prepared-v1')
    d, binary = g.unpack(data)
    return d, binary, receipt, roles


def fitted(car):
    d, binary, receipt, roles = prepared(car)
    new, wheels, pol = fit.transform(d, binary, receipt, roles, fit.STOCK_WIDTH[car])
    return d, binary, receipt, roles, new, wheels, pol


def verifier_inputs(car, source, binary, receipt, roles, lift):
    geom = g.Geometry(source, binary)
    clouds = {i: fit.points_of(source, geom, i) for i in range(len(source['nodes']))}
    tyre = {n['name'].removeprefix('ADAPTED_NATIVE_TOYO_TYRE_'): i for i, n in enumerate(source['nodes'])
            if n['name'].startswith('ADAPTED_NATIVE_TOYO_TYRE_')}
    pivots = receipt['native_wheel_pivots']
    info = {l: (receipt['wheels'][i]['center'], pivots['WHEEL_' + l][1] / 100) for i, l in enumerate(fit.LABELS)}
    return clouds, tyre, info


class Checks(unittest.TestCase):
    def test_identity_guard_binds_each_car_to_its_descriptor_name_without_retained_inputs(self):
        def descriptor(name):
            return [['RACER_VEHICLE', '2'], ['name', name + ' (native source candidate)']]
        self.assertEqual(set(fit.PREPARED_NAME), set(CARS))
        for car, expected in fit.PREPARED_NAME.items():
            with self.subTest(car=car, pairing='own'):
                fit.require_prepared_identity(car, descriptor(expected))
            for other, name in fit.PREPARED_NAME.items():
                if other != car:
                    with self.subTest(car=car, other=other):
                        with self.assertRaises(SystemExit) as caught:
                            fit.require_prepared_identity(car, descriptor(name))
                        self.assertIn(expected, str(caught.exception))
                        self.assertIn(name, str(caught.exception))
        with self.assertRaises(SystemExit) as caught:
            fit.require_prepared_identity('z4', [['RACER_VEHICLE', '2']])
        self.assertIn('None', str(caught.exception))

    def test_cli_refuses_absent_prepared_dir_and_existing_output_without_retained_inputs(self):
        with tempfile.TemporaryDirectory(prefix='racer-stockfit-pure-') as temp:
            temp = Path(temp)
            (temp / 'taken').mkdir()
            for prepared_dir, out, text in ((temp / 'absent', 'out', 'prepared_dir_contents'), (temp / 'absent', 'taken', 'already exists')):
                with self.subTest(text=text):
                    argv = ['fit', 'z4', '--prepared-dir', str(prepared_dir), '--output', str(temp / out)]
                    with unittest.mock.patch.object(sys, 'argv', argv):
                        with self.assertRaises(SystemExit) as caught:
                            fit.main()
                    self.assertIn(text, str(caught.exception))
                    self.assertNotIn('\n', str(caught.exception))
            self.assertFalse((temp / 'out').exists())
            self.assertEqual(list((temp / 'taken').iterdir()), [])

    @needs_cohort
    def test_published_meshes_reproduce_their_inventory_pins(self):
        inventory = {row['model_id']: row for row in json.loads(INVENTORY.read_text())['vehicles']}
        for car, model in CARS.items():
            with self.subTest(car=car):
                d, binary, receipt, roles, new, wheels, pol = fitted(car)
                self.assertEqual(hashlib.sha256(g.pack(new, binary)).hexdigest(), inventory[model]['prepared_sha256'])
                self.assertEqual(len(wheels), 4)
                self.assertTrue(all(w['radius'] > 0.25 and w['width'] > 0.15 for w in wheels))

    @needs_cohort
    def test_independent_verification_accepts_the_real_fit_and_rejects_tampering(self):
        d, binary, receipt, roles, new, wheels, pol = fitted('charger_rt')
        clouds, tyre, info = verifier_inputs('charger_rt', d, binary, receipt, roles, pol['uniform_lift'])
        args = (clouds, roles, tyre, info, pol['uniform_lift'], fit.STOCK_WIDTH['charger_rt'])

        fit.verify_applied(new, *args)
        rl = tyre['RL']
        carrier = next(i for i, r in roles.items() if r == 'carrier FL')

        def scale_rl(sx=1.0, sy=1.0):
            def mutate(doc):
                x, y, z = doc['nodes'][rl]['scale']
                doc['nodes'][rl]['scale'] = [x * sx, y * sy, z * sy]
            return mutate

        cases = [
            ('applied_radius', scale_rl(sy=1.03)),
            ('applied_width', scale_rl(sx=1.05)),
            ('carrier_untouched', lambda doc: doc['nodes'][carrier].__setitem__('scale', [1.0, 1.0, 1.0])),
            ('applied_radius', lambda doc: doc['nodes'][-1].__setitem__('translation', [0, -pol['uniform_lift'] - 0.01, 0])),
        ]
        for n, (reason, mutate) in enumerate(cases):
            with self.subTest(case=n, reason=reason):
                doc = copy.deepcopy(new)
                mutate(doc)
                with self.assertRaises(g.PreparationError) as caught:
                    fit.verify_applied(doc, *args)
                self.assertEqual(str(caught.exception), reason)

    @needs_cohort
    def test_a_fit_is_refused_for_a_preparation_that_belongs_to_another_car(self):
        self.assertEqual(set(fit.PREPARED_NAME), set(CARS))
        for car in CARS:
            with self.subTest(car=car, pairing='own'):
                toks = fit.load_prepared(COHORT / f'{car}-prepared-v1')[4]
                fit.require_prepared_identity(car, toks)
        for car in CARS:
            other = next(c for c in CARS if c != car)
            with self.subTest(car=car, pairing='foreign'):
                toks = fit.load_prepared(COHORT / f'{other}-prepared-v1')[4]
                with self.assertRaises(SystemExit) as caught:
                    fit.require_prepared_identity(car, toks)
                self.assertIn(fit.PREPARED_NAME[car], str(caught.exception))
                self.assertIn(fit.PREPARED_NAME[other], str(caught.exception))
        with tempfile.TemporaryDirectory(prefix='racer-stockfit-') as temp:
            out = Path(temp) / 'out'
            argv = ['fit', 'z4', '--prepared-dir', str(COHORT / 'koenigsegg-prepared-v1'), '--output', str(out)]
            with unittest.mock.patch.object(sys, 'argv', argv):
                with self.assertRaises(SystemExit) as caught:
                    fit.main()
            self.assertIn('not the z4 preparation', str(caught.exception))
            self.assertFalse(out.exists())

    @needs_cohort
    def test_cli_failures_are_one_line_messages_naming_the_path_and_create_nothing(self):
        source = COHORT / 'z4-prepared-v1'
        with tempfile.TemporaryDirectory(prefix='racer-stockfit-cli-') as temp:
            temp = Path(temp)
            tampered = temp / 'tampered'
            tampered.mkdir()
            for item in source.iterdir():
                (tampered / item.name).write_bytes(item.read_bytes())
            next(tampered.glob('*.glb')).write_bytes(next(tampered.glob('*.glb')).read_bytes() + b'x')
            no_pivots = temp / 'no-pivots'
            no_pivots.mkdir()
            for item in source.iterdir():
                (no_pivots / item.name).write_bytes(item.read_bytes())
            receipt = json.loads((no_pivots / 'receipt.json').read_text())
            del receipt['native_wheel_pivots']
            (no_pivots / 'receipt.json').write_text(json.dumps(receipt))
            (temp / 'taken').mkdir()
            cases = [(temp / 'absent', 'out-a', 'prepared_dir_contents'), (tampered, 'out-b', 'pin'),
                     (no_pivots, 'out-c', 'receipt_fields'), (source, 'taken', 'already exists')]
            for prepared, out, text in cases:
                with self.subTest(case=text):
                    argv = ['fit', 'z4', '--prepared-dir', str(prepared), '--output', str(temp / out)]
                    with unittest.mock.patch.object(sys, 'argv', argv):
                        with self.assertRaises(SystemExit) as caught:
                            fit.main()
                    shown = str(caught.exception)
                    self.assertIn(text, shown)
                    self.assertNotIn('\n', shown)
                    self.assertIn(str(temp / out) if text == 'already exists' else str(prepared), shown)
                    if out != 'taken':
                        self.assertFalse((temp / out).exists())
            self.assertEqual(list((temp / 'taken').iterdir()), [])

    @needs_cohort
    def test_damaged_receipt_or_descriptor_content_is_one_line_exit_and_creates_nothing(self):
        source = COHORT / 'z4-prepared-v1'

        def damaged(temp, name, edit_receipt=None, edit_descriptor=None):
            folder = temp / name
            folder.mkdir()
            for item in source.iterdir():
                (folder / item.name).write_bytes(item.read_bytes())
            if edit_receipt:
                receipt = json.loads((folder / 'receipt.json').read_text())
                edit_receipt(receipt)
                (folder / 'receipt.json').write_text(json.dumps(receipt))
            if edit_descriptor:
                descriptor = next(folder.glob('*.vehicle'))
                descriptor.write_text(edit_descriptor(descriptor.read_text()))
            return folder

        with tempfile.TemporaryDirectory(prefix='racer-stockfit-damaged-') as temp:
            temp = Path(temp)
            cases = {
                'no-center': damaged(temp, 'no-center', lambda r: r['wheels'][0].pop('center')),
                'body-none': damaged(temp, 'body-none', lambda r: r.__setitem__('body', None)),
                'pivots-str': damaged(temp, 'pivots-str', lambda r: r.__setitem__('native_wheel_pivots', 'x')),
                'group-row': damaged(temp, 'group-row', edit_descriptor=lambda t: t.replace('group 0 ', 'group zero ', 1)),
                'quote': damaged(temp, 'quote', edit_descriptor=lambda t: t + 'name "unterminated\n'),
            }
            for name, folder in cases.items():
                with self.subTest(case=name):
                    out = temp / f'out-{name}'
                    argv = ['fit', 'z4', '--prepared-dir', str(folder), '--output', str(out)]
                    with unittest.mock.patch.object(sys, 'argv', argv):
                        with self.assertRaises(SystemExit) as caught:
                            fit.main()
                    shown = str(caught.exception)
                    self.assertIn('malformed preparation input', shown)
                    self.assertIn(str(folder), shown)
                    self.assertNotIn('\n', shown)
                    self.assertFalse(out.exists())

    @needs_cohort
    def test_seeded_receipt_mutation_fuzz_ends_only_in_success_or_a_one_line_exit(self):
        import random
        rnd = random.Random(7)
        source = COHORT / 'z4-prepared-v1'
        base = json.loads((source / 'receipt.json').read_text())
        junk = [None, 'x', [], {}, -1, 0]

        def mutate(obj, depth=0):
            if isinstance(obj, dict) and obj:
                key = rnd.choice(list(obj))
                if rnd.random() < 0.4 or depth > 3:
                    obj[key] = rnd.choice(junk)
                elif rnd.random() < 0.3:
                    obj.pop(key)
                else:
                    mutate(obj[key], depth + 1)
            elif isinstance(obj, list) and obj:
                i = rnd.randrange(len(obj))
                if rnd.random() < 0.5:
                    obj[i] = rnd.choice(junk)
                else:
                    mutate(obj[i], depth + 1)

        escapes = []
        outcomes = {'ok': 0, 'exit': 0}
        with tempfile.TemporaryDirectory(prefix='racer-stockfit-fuzz-') as temp:
            temp = Path(temp)
            for n in range(60):
                folder = temp / f'p{n}'
                folder.mkdir()
                for item in source.iterdir():
                    if item.name != 'receipt.json':
                        (folder / item.name).symlink_to(item)  # the 5 MB mesh and descriptor stay read-only originals
                receipt = json.loads(json.dumps(base))
                for _ in range(rnd.randint(1, 2)):
                    key = rnd.choice(['body', 'wheels', 'native_wheel_pivots', 'prepared_sha256'])
                    if key == 'prepared_sha256':
                        receipt[key] = rnd.choice([None, 'x', '0' * 64])
                    else:
                        mutate(receipt[key] if isinstance(receipt[key], (dict, list)) else receipt)
                (folder / 'receipt.json').write_text(json.dumps(receipt))
                out = temp / f'o{n}'
                argv = ['fit', 'z4', '--prepared-dir', str(folder), '--output', str(out)]
                try:
                    with unittest.mock.patch.object(sys, 'argv', argv), unittest.mock.patch('sys.stdout', new=__import__('io').StringIO()):
                        fit.main()
                    outcomes['ok'] += 1
                except SystemExit as error:
                    outcomes['exit'] += 1
                    if '\n' in str(error) or out.exists():
                        escapes.append((n, 'multi-line exit or output created', str(error)[:80]))
                except Exception as error:  # noqa: BLE001 - nothing but SystemExit may escape
                    escapes.append((n, type(error).__name__, str(error)[:80]))
        self.assertEqual(escapes, [])
        self.assertGreater(outcomes['exit'], 10)

    @needs_cohort
    def test_prepared_directory_must_hold_exactly_one_mesh_and_descriptor(self):
        with tempfile.TemporaryDirectory(prefix='racer-stockfit-') as temp:
            temp = Path(temp)
            source = COHORT / 'z4-prepared-v1'
            for item in source.iterdir():
                (temp / item.name).write_bytes(item.read_bytes())
            (temp / ('f' * 64 + '.glb')).write_bytes(b'x')
            with self.assertRaises(g.PreparationError) as caught:
                fit.load_prepared(temp)
            self.assertEqual(str(caught.exception), 'prepared_dir_contents')


if __name__ == '__main__':
    unittest.main()
