#!/usr/bin/env python3
"""ppc_dis.py / ppc_scan.py: bounded single-call disassembly with word alignment, input validation, a clear
missing-tool failure, a multiplier scan that pairs lis with same-register uses (loads, stores, addi/ori),
and non-zero usage exits for bad arguments (skips when the retained decoded text section or llvm-mc is absent)."""
import contextlib
import io
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / 'experiments/2026-11-06-juiced2-native-sizing'
sys.path.insert(0, str(EXPERIMENT))
try:
    import ppc_dis
    import ppc_scan
except FileNotFoundError:
    sys.exit(77)
if not os.access(ppc_dis.LLVM_MC, os.X_OK):
    sys.exit(77)


def lis(rd, imm):
    return (15 << 26) | (rd << 21) | imm


def mem(op, rt, ra, disp=0xBE70):
    return (op << 26) | (rt << 21) | (ra << 16) | (disp & 0xFFFF)


def ori(ra, rs, ui=0xBE70):
    """ori rA,rS,UI: RS (source) is bits 21-25, RA (destination) bits 16-20."""
    return (24 << 26) | (rs << 21) | (ra << 16) | ui


class Checks(unittest.TestCase):
    def test_invalid_words_map_back_to_their_own_position(self):
        words = [bytes.fromhex('7d8802a6'), bytes.fromhex('00000000'), bytes.fromhex('38600001'), bytes.fromhex('00000000')]
        self.assertEqual(ppc_dis.disassemble(words), ['mflr 12', '?', 'li 3, 1', '?'])

    def test_range_reproduces_the_retained_constructor_listing(self):
        listing = EXPERIMENT / 'output/ctor-820f0a18.txt'
        if not listing.is_file():
            self.skipTest('retained constructor listing (ignored experiment output) absent')
        retained = listing.read_text().splitlines()[:8]
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            ppc_dis.main(['ppc_dis.py', '820f0a18', '8'])
        normalise = lambda line: ' '.join(line.split())
        self.assertEqual([normalise(l) for l in out.getvalue().splitlines()], [normalise(l) for l in retained])

    def test_count_and_range_are_validated_before_any_process_starts(self):
        with patch.object(ppc_dis.subprocess, 'run', side_effect=AssertionError('llvm-mc must not start')):
            for argv, text in ((['x', '820f0a18', '0'], 'COUNT'), (['x', '820f0a18', str(ppc_dis.MAX_COUNT + 1)], 'COUNT'),
                               (['x', '1000', '4'], 'outside the text section'), (['x', '820f0a19', '2'], 'word-aligned'),
                               (['x', '820f0a18'], 'Usage')):
                with self.subTest(argv=argv):
                    with self.assertRaises(SystemExit) as caught:
                        ppc_dis.main(argv)
                    self.assertIn(text, str(caught.exception))

    def test_missing_llvm_mc_is_reported_not_traced(self):
        with patch.object(ppc_dis, 'LLVM_MC', '/nonexistent/llvm-mc'):
            with self.assertRaises(SystemExit) as caught:
                ppc_dis.disassemble([bytes.fromhex('7d8802a6')])
        self.assertIn('llvm-mc not found', str(caught.exception))

    def test_multiplier_scan_pairs_lis_with_same_register_uses_of_every_kind(self):
        base = 0x1000
        hi = 0x824D
        words = [lis(9, hi), mem(52, 1, 9),            # store (stfs)
                 lis(10, hi), mem(32, 3, 10),          # load (lwz)
                 lis(11, hi), mem(14, 4, 11),          # address-taken (addi)
                 lis(12, 0x824C), ori(13, 12),         # address-taken (lis/ori idiom, destination differs from source)
                 lis(15, 0x824C), ori(15, 15),         # address-taken (lis/ori idiom, same register)
                 lis(16, 0x824C), ori(16, 5),          # not a use: r16 is overwritten from unrelated r5
                 mem(48, 1, 7),                        # same displacement, no lis on r7: not a use
                 lis(13, hi), lis(13, 0x1234), mem(36, 2, 13)]  # register reloaded before the use
        words += [lis(14, hi)] + [0x60000000] * ppc_scan.WINDOW + [mem(36, 2, 14)]  # use beyond the window
        uses = ppc_scan.multiplier_uses(words, base)
        self.assertEqual(uses, [(base + 4, 'store', 'stfs'), (base + 12, 'load', 'lwz'),
                                (base + 20, 'address-taken', 'addi'), (base + 28, 'address-taken', 'ori'),
                                (base + 36, 'address-taken', 'ori')])

    def test_retained_text_section_has_four_multiplier_loads_and_no_writer(self):
        uses = ppc_scan.multiplier_uses()
        kinds = [kind for _, kind, _ in uses]
        self.assertEqual((kinds.count('load'), kinds.count('store'), kinds.count('address-taken')), (4, 0, 0))
        self.assertEqual([hex(a) for a, _, _ in uses], ['0x820f5268', '0x8210cf1c', '0x82147dfc', '0x82294dec'])

    def test_bad_arguments_exit_nonzero_with_usage_and_relocation_is_explained(self):
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
        cases = [(['ppc_scan.py'], 'Usage'), (['ppc_scan.py', 'bogus'], "unknown pattern 'bogus'"),
                 (['ppc_scan.py', 'mult', 'extra'], 'Usage'), (['ppc_dis.py', 'zz', '4'], 'hex address'),
                 (['ppc_dis.py', '820f0a18', 'four'], 'decimal count')]
        for argv, text in cases:
            with self.subTest(argv=argv):
                run = subprocess.run([sys.executable, str(EXPERIMENT / argv[0]), *argv[1:]], capture_output=True, text=True,
                                     env=env, timeout=60)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn(text, run.stderr)
                self.assertNotIn('Traceback', run.stderr)
        relocated = subprocess.run([sys.executable, str(EXPERIMENT / 'ppc_scan.py'), 'mult'], capture_output=True, text=True,
                                   env=dict(env, JUICED2_DECODED_SECTIONS='/nonexistent-decoded-sections'), timeout=60)
        self.assertNotEqual(relocated.returncode, 0)
        self.assertIn('JUICED2_DECODED_SECTIONS', relocated.stderr)


if __name__ == '__main__':
    unittest.main()
