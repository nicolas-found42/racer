"""Native-word arithmetic and generated profile fixtures; no game execution."""
import json
import math
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import juiced2_wheel_contract as wheel


def profile(flag=0):
    raw = bytearray(596)
    raw[:12] = b'TYRE_PROFILE'
    struct.pack_into('>16f', raw, 32, *(1. if i % 5 == 0 else 0. for i in range(16)))
    struct.pack_into('>2I', raw, 96, 3, 13)
    for i in range(13):
        anchor = (float(i + 1), 25. + i if i < 12 else 1., 0.)
        struct.pack_into('>9f', raw, 104 + i * 36, *anchor, 999., 999., 0., -999., -999., 0.)
    struct.pack_into('>I', raw, 572, flag)
    return raw


def run_native_sizing_words(fields, inputs):
    """Independent tiny interpreter for the actual pinned straight-line words.

    Only the setter arithmetic window is interpreted. Prologue, external calls,
    following branches and whole-game/FPSCR behavior are outside this fixture.
    """
    memory = {}
    registers = {31: 0x1000}
    floats = {31: wheel.f32(inputs[0]), 30: wheel.f32(inputs[1]), 29: wheel.f32(inputs[2])}
    def put(address, fmt, value): memory[address] = struct.pack('>' + fmt, value)
    def get(address, fmt): return struct.unpack('>' + fmt, memory[address])[0]
    for offset, value in ((436, fields['object436']), (440, fields['object440']), (444, fields['object444'])):
        put(0x1000 + offset, 'f', value)
    put(0x1000 + 204, 'I', 0)
    for address, fmt, value in ((0x8202F6D4, 'f', 4.), (0x8202F7B4, 'f', 20.),
                                (0x8204D464, 'f', 0.7874000072479248), (0x8204D468, 'd', 0.1)):
        put(address, fmt, value)
    words = bytes.fromhex(wheel.WINDOWS[0x8210F7D8])
    for offset in range(0, 0x8210F854 - 0x8210F7D8, 4):
        instruction = int.from_bytes(words[offset:offset + 4], 'big')
        opcode = instruction >> 26
        target, a, b, c = ((instruction >> shift) & 31 for shift in (21, 16, 11, 6))
        immediate = instruction & 65535
        if immediate & 32768: immediate -= 65536
        if opcode in (14, 15):
            registers[target] = ((registers[a] if a else 0) + immediate * (65536 if opcode == 15 else 1)) & 0xffffffff
        elif opcode in (32, 48, 50):
            address = (registers.get(a, 0) + immediate) & 0xffffffff
            if opcode == 32: registers[target] = get(address, 'I')
            else: floats[target] = get(address, 'f' if opcode == 48 else 'd')
        elif opcode == 52:
            put((registers.get(a, 0) + immediate) & 0xffffffff, 'f', floats[target])
        elif opcode == 10:
            pass  # Comparison flags are only consumed after this window.
        elif opcode in (59, 63):
            extended = (instruction >> 1) & 31
            if opcode == 63 and ((instruction >> 1) & 1023) == 12:
                floats[target] = wheel.f32(floats[b])
            elif extended == 25:
                value = floats[a] * floats[c]
                floats[target] = wheel.f32(value) if opcode == 59 else value
            elif opcode == 59 and extended in (18, 20):
                value = floats[a] / floats[b] if extended == 18 else floats[a] - floats[b]
                floats[target] = wheel.f32(value)
            else:
                raise AssertionError('Unsupported native float instruction')
        else:
            raise AssertionError('Unsupported native instruction ' + hex(instruction))
    return {offset: memory[0x1000 + offset] for offset in (292, 296, 300, 424, 428, 456)}


class Checks(unittest.TestCase):
    def test_native_count_excludes_terminal_anchor_for_flag_zero(self):
        fields = wheel.profile_fields(profile())
        self.assertEqual(fields['sample_count'], 12)
        self.assertEqual(fields['sampled_indices'], list(range(12)))
        self.assertEqual((fields['object436'], fields['object440'], fields['object444']), (12., 25., 36.))
        self.assertEqual(fields['all_anchor_min_y'], 1.)

    def test_flag_low_bit_controls_endpoint_without_invented_closed_name(self):
        for flag, count in ((0, 12), (1, 13), (2, 12), (3, 13)):
            with self.subTest(flag=flag):
                fields = wheel.profile_fields(profile(flag))
                self.assertEqual(fields['sample_count'], count)
                self.assertEqual(fields['object440'], 1. if count == 13 else 25.)

    def test_accumulators_use_anchors_not_handles_or_absolute_x(self):
        raw = profile()
        for i in range(13): struct.pack_into('>f', raw, 104 + i * 36, -5.)
        fields = wheel.profile_fields(raw)
        self.assertEqual(fields['object436'], 0.)
        self.assertEqual(fields['object444'], 36.)

    def test_profile_rejects_bad_frame_layout_extent_and_nonfinite_handles(self):
        variants = []
        raw = profile(); raw[0] = 0; variants.append(raw)
        raw = profile(); struct.pack_into('>f', raw, 32, 2.); variants.append(raw)
        raw = profile(); struct.pack_into('>I', raw, 96, 2); variants.append(raw)
        raw = profile(); struct.pack_into('>f', raw, 116, math.nan); variants.append(raw)
        variants.extend((profile()[:-1], b''))
        for raw in variants:
            with self.subTest(length=len(raw)), self.assertRaises(ValueError): wheel.profile_fields(raw)

    def test_kernel_matches_actual_native_words_bit_for_bit(self):
        fields = wheel.profile_fields(profile())
        for inputs in ((225., .45, 17.), (195., .55, 16.), (315., .25, 22.), (200.00003, .333333, 19.00003)):
            expected = run_native_sizing_words(fields, inputs)
            actual = wheel.sizing_fields(fields, *inputs)
            for offset, raw in expected.items():
                with self.subTest(inputs=inputs, field=offset):
                    self.assertEqual(struct.pack('>f', actual['object' + str(offset)]), raw)

    def test_register_domain_is_explicit_and_no_units_are_inferred(self):
        fields = wheel.profile_fields(profile())
        for value in (0., -1., math.inf, math.nan, True, 1e-45, 1e100):
            with self.subTest(value=value), self.assertRaises(ValueError): wheel.sizing_fields(fields, value, .45, 17.)
        self.assertIn('unresolved', wheel.sizing_fields(fields, 225., .45, 17.)['scope'])

    def test_wrong_image_rejected_before_native_window_interpretation(self):
        with self.assertRaisesRegex(ValueError, 'native_image_pin'): wheel.verify_image(b'not a decoded image')

    def test_missing_iso_context_is_not_misattributed_to_image(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            with self.assertRaises(FileNotFoundError):
                with wheel.VerificationLifecycle(root) as life:
                    life.record['active_input'] = 'image'
                    life.phase('retrieval')
                    wheel.source_profile(root / 'PRIVATE_ABSENT.iso', life)
            text = (root / 'lifecycle.json').read_text()
            state = json.loads(text)
            self.assertEqual(state['active_input'], 'iso')
            self.assertEqual(state['status'], 'failed')
            self.assertEqual(state['errno'], 2)
            self.assertNotIn('PRIVATE_ABSENT', text)

    def test_late_report_failure_retains_input_and_publication_owner(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp).resolve() / 'audit'
            args = ['audit', '--iso', 'fixture.iso', '--image', 'fixture.image', '--output', str(out)]
            publish = wheel.immutable
            def fail_report(path, data):
                if Path(path).name == 'report.json': raise OSError(28, 'PRIVATE_REPORT_PATH')
                return publish(path, data)
            with patch.object(sys, 'argv', args), \
                 patch.object(wheel, 'regular_bytes', return_value=b'fixture'), \
                 patch.object(wheel, 'verify_image', return_value=[]), \
                 patch.object(wheel, 'source_profile', return_value=(bytes(profile()), {'fixture': True})), \
                 patch.object(wheel, 'immutable', side_effect=fail_report), \
                 self.assertRaises(OSError):
                wheel.main()
            text = (out / 'lifecycle.json').read_text()
            state = json.loads(text)
            self.assertEqual((state['status'], state['phase'], state['errno']), ('failed', 'capture', 28))
            self.assertEqual(state['publication_kind'], 'report')
            self.assertIsNone(state['active_input'])
            self.assertTrue((out / 'profile.bin').exists())
            self.assertFalse((out / 'report.json').exists())
            self.assertNotIn('PRIVATE_REPORT_PATH', text)


if __name__ == '__main__': unittest.main()
