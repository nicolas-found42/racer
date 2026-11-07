#!/usr/bin/env python3
"""Optional exact-source Racer tint for four MC3 cohort windows; no native GS opacity claim."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import signal
import struct

from prepare_gt4_vehicle import require, unpack, pack
from prepare_mcla_vehicle import read_regular
from repair_mc3_vehicle import archive

ROOT = Path(__file__).resolve().parents[1]
LEAF = ROOT / 'experiments/2026-11-06-mc3-cohort/output'
CAP = 64 * 1024**2
MEMBER = 16 * 1024**2
TINT = [.08, .12, .16, .45]
sha = lambda data: hashlib.sha256(data).hexdigest()
PINS = {'vp_fleetline_49': {'source': '8084216433024b2e8f7c56adadeb0de64bc97eb7ce0d8f37b0f7129c4d44dc1c',
                     'prepared': '6daf44e2c5c5dca77a62f21754ca43e97a9457fe0011206891c439de44201638',
                     'descriptor': '1763e30ac5584093337dbd1e66abfa50c696977f5619c8e243624697ee35857f',
                     'receipt': '74aec01f799356fdb6f3502e7f6e7590198f61ef7ec316ea55b1ceae80a911b0',
                     'dat': '0ffee83a1b34ece2265ff5214cd175ca562c88f86d9ecc58cf16fc7c29486307',
                     'pck': 'b98ccea23d1e7428171c0687f4b05184bf35526bcf54d408e8782fd270478e8b',
                     'material': 11,
                     'offset': 88144},
 'vp_saleen_sr_00': {'source': '0667e928af5946dd298503d6b33da725c976ee06e6af158d4b3894383c9f176a',
                     'prepared': 'e1831751fd03d2066863ceddaab73845275366283a32729f6321773d6d7e3f70',
                     'descriptor': '74dd9dd20a466df5ebd1c0c4c02a5738aebffd7ab56eb45662990e88d3fa17dd',
                     'receipt': '27dad9e22df381b4558e0aec822a1b7b4596dfe24a3d13a2d17d98b53a863291',
                     'dat': 'a0a5bb048fa45d8f22260d1de60e88718e5171fb1d42c1cb0e332d2b80b4cac8',
                     'pck': '0349a88b8bccb5cb946a5e3429fb9fe9b3266589319f997f95e6ec92bdbeb54b',
                     'material': 18,
                     'offset': 91424},
 'vp_viper_03': {'source': '8a863c83fc3c2d6afd66e786b40a943de8a732dda21bb6d1d1ddbbab14ac7895',
                 'prepared': 'e518a38dae10a9eb99e1ec0ea61a5c9b7909bf89b171b02915e7cf6d3bbd75e0',
                 'descriptor': 'ac988394eb35302ee73854274679b9234bc3091f6218e6a089826585f0adae74',
                 'receipt': '5ee144966e3e89d26d9b81bc0ad8addcdd9aa7bcc414efb4a0d9a928c9de7ebb',
                 'dat': 'b9e0235888008978fab325075c5711fde6f0bced507182f60a6cff9670e4188e',
                 'pck': 'fc090376ac20166e0014b0f5948b2e36e68b8853b23e7a4d848037b06388fdbb',
                 'material': 2,
                 'offset': 17504},
 'vp_esprit_04': {'source': '1b6ad10f7cb439faf8381a65f268c0d2dbc35aa7a64841042a5f1cab63f279eb',
                  'prepared': '42028aaaebbe49e87686bed568a1a8a84e04287494077ad0efbaeb48ff93e68d',
                  'descriptor': '0351579d63b7de1746139dcd00506ba3df3b5291b6337ace81755b76de428cd9',
                  'receipt': '5e730fcdfe6b0ef1429fe24b85c90e3c4c9c81e770ed40d510b7225ab347fa82',
                  'dat': '333d07e21328ec21396250848adff79277ef7d384d48b845602af04477cc1186',
                  'pck': 'a1b40a11802051cbf4fc5832a12eca1429691c6f5edcf206facad819c624e536',
                  'material': 5,
                  'offset': 85264}}


def active_draws(doc, material):
    require(0 < len(doc['nodes']) <= 4096, 'node_budget')
    pending = [(i, 0) for i in doc['scenes'][doc.get('scene', 0)]['nodes']]
    seen = set(); draws = []
    while pending:
        i, depth = pending.pop()
        require(type(i) is int and 0 <= i < len(doc['nodes']) and i not in seen and depth < 64, 'active_graph')
        seen.add(i); n = doc['nodes'][i]
        pending.extend((j, depth + 1) for j in n.get('children', []))
        if 'mesh' not in n:
            continue
        mi = n['mesh']; require(type(mi) is int and 0 <= mi < len(doc['meshes']), 'mesh_index')
        for pi, primitive in enumerate(doc['meshes'][mi]['primitives']):
            if primitive.get('material') == material:
                draws.append({'node': i, 'name': n.get('name'), 'mesh': mi, 'primitive': pi})
    return draws


def apply_policy(doc, original, pck, code):
    """Validate the exact approved category and raw witness before changing two properties."""
    pin = PINS[code]; index = pin['material']; offset = pin['offset']
    require(sha(pck) == pin['pck'], 'native_pck_pin')
    require(doc['materials'] == original['materials'], 'source_materials_changed')
    m = doc['materials'][index]; e = m.get('extras', {})
    require((m.get('name'), e.get('shader_category'), e.get('vtable'), e.get('profile'), e.get('file_offset'), e.get('index')) ==
            ('car_window', 'car_window', 8038632, 'original', offset, index), 'material_exact_tuple')
    require(m.get('alphaMode') == 'OPAQUE' and m['pbrMetallicRoughness'].get('baseColorFactor') == [.65, .65, .65, 1.0], 'neutral_window_required')
    native = e['native_material']; root = native['root']
    require(native['source_carrier_sha256'] == pin['pck'] and
            (root.get('source_offset'), root.get('serialized_vtable'), root.get('class_id'), root.get('template')) ==
            (offset, 8038632, 13, 'car_window.shadert'), 'native_material_join')
    require(0 <= offset <= len(pck) - 32 and struct.unpack_from('<I', pck, offset)[0] == 8038632, 'raw_material_vtable')
    draws = active_draws(doc, index); require(draws, 'approved_window_inactive')
    before = copy.deepcopy(m)
    m['pbrMetallicRoughness']['baseColorFactor'] = list(TINT)
    m['alphaMode'] = 'BLEND'
    return {'schema': 1, 'authority': 'Racer-authored tint and alpha; not native GS opacity or shader parity.',
            'source_sha256': pin['source'], 'source_prepared_sha256': pin['prepared'],
            'index': index, 'source_material': before, 'active_draws': draws,
            'authored_baseColorFactor': TINT, 'authored_alphaMode': 'BLEND',
            'native_witness': {'pck_sha256': sha(pck), 'offset': offset, 'serialized_vtable_le': 8038632,
                               'first_32_bytes_hex': pck[offset:offset + 32].hex(),
                               'range_scope': 'First 32 bytes at the pinned material root; not a complete record decoder.'},
            'preserved': 'All other materials, including existing colored glass, lamps, unknown and unused materials.'}


def rewrite_descriptor(text, old, new, source):
    expected = {'id': ['vehicle-' + old], 'mesh': [old + '.glb'], 'sha256': [old], 'source_sha256': [source]}
    replacements = {'id': 'id ' + json.dumps('vehicle-' + new), 'mesh': 'mesh ' + json.dumps(new + '.glb'), 'sha256': 'sha256 ' + new}
    seen = set(); result = []
    for line in text.splitlines():
        words = shlex.split(line)
        if words and words[0] in expected:
            key = words[0]; require(key not in seen and words[1:] == expected[key], 'descriptor_identity')
            seen.add(key); line = replacements.get(key, line)
        result.append(line)
    require(seen == set(expected), 'descriptor_identity_missing')
    return '\n'.join(result) + '\n'


def convert(code, leaf=LEAF):
    require(code in PINS, 'unsupported_source')
    pin = PINS[code]; source_dir = leaf / 'batch-v1' / code
    prepared_dir = leaf / 'batch-v2' / code / 'prepared-v1'
    paths = {'source': source_dir / 'source.glb', 'dat': source_dir / 'source.dat',
             'pck': leaf / 'batch-v2' / code / 'main.pck',
             'prepared': prepared_dir / (pin['prepared'] + '.glb'),
             'descriptor': prepared_dir / (pin['prepared'] + '.vehicle'),
             'receipt': prepared_dir / (pin['prepared'] + '.json')}
    inputs = {key: read_regular(path, 1024**2 if key == 'receipt' else 32768 if key == 'descriptor' else MEMBER) for key, path in paths.items()}
    require(sum(map(len, inputs.values())) <= 32 * 1024**2, 'input_budget')
    require(all(sha(data) == pin[key] for key, data in inputs.items()), 'exact_input_pins')
    members = archive(inputs['dat'])
    matches = [m for m in members if Path(m['name']).name == code + '.pck']
    require(len(matches) == 1, 'native_main_join'); member = matches[0]
    require(inputs['dat'][member['offset']:member['offset'] + member['size']] == inputs['pck'], 'native_dat_range')
    original, _ = unpack(inputs['source']); doc, binary = unpack(inputs['prepared'])
    before = copy.deepcopy(doc)
    require(original['extras']['car'] == code and original['extras']['source_profile'] == 'mc3-ps2-static-preview-v1', 'source_profile')
    require(doc['extras']['racerPreparation']['source_sha256'] == pin['source'], 'prepared_source_join')
    policy = apply_policy(doc, original, inputs['pck'], code)
    require('racerCohortGlassPolicy' not in doc.get('extras', {}), 'already_adapted')
    doc.setdefault('extras', {})['racerCohortGlassPolicy'] = policy
    restored = copy.deepcopy(doc); del restored['extras']['racerCohortGlassPolicy']
    restored['materials'][pin['material']] = policy['source_material']
    require(restored == before, 'unrelated_document_change')
    result = pack(doc, binary); require(len(result) <= MEMBER, 'output_member_budget'); digest = sha(result)
    text = rewrite_descriptor(inputs['descriptor'].decode(), pin['prepared'], digest, pin['source'])
    receipt = json.loads(inputs['receipt'])
    require(receipt['prepared_sha256'] == pin['prepared'] and receipt['source_sha256'] == pin['source'], 'receipt_identity')
    receipt.update(prepared_sha256=digest, prepared_bytes=len(result), runtime_player_eligible=False,
                   racer_cohort_glass_policy=policy, source_prepared_sha256=pin['prepared'],
                   source_descriptor_sha256=pin['descriptor'], source_receipt_sha256=pin['receipt'])
    receipt['glass_preservation'] = {'whole_BIN_equal': unpack(result)[1] == binary,
                                    'all_document_fields_except_one_material_and_named_policy_equal': True,
                                    'descriptor_only_id_mesh_sha_changed': True,
                                    'native_dat_main_member': member}
    return result, text.encode(), receipt


def retained_size(root):
    size = 0
    for p in root.rglob('*'):
        require(not p.is_symlink(), 'output_symlink')
        if p.is_file(): size += p.stat().st_size
    return size


def publish(output, codes, leaf=LEAF):
    output = Path(output); leaf = Path(leaf)
    require(1 <= len(codes) <= 4 and len(set(codes)) == len(codes), 'cohort_count')
    require(output.parent == leaf and not output.exists() and not any(p.is_symlink() for p in (output, *output.parents)), 'fresh_output_under_leaf')
    require(shutil.disk_usage(leaf).free >= 20 * 1024**3, 'free_space')
    payloads = []; rows = []
    for code in codes:
        mesh, definition, receipt = convert(code, leaf); digest = receipt['prepared_sha256']
        payloads.extend([(Path(code) / (digest + ext), data) for ext, data in
                         (('.glb', mesh), ('.vehicle', definition), ('.json', (json.dumps(receipt, indent=2) + '\n').encode()))])
        rows.append({'code': code, 'source_sha256': PINS[code]['source'], 'prepared_sha256': digest,
                     'descriptor': str((output / code / (digest + '.vehicle')).resolve()),
                     'runtime_player_eligible': False, 'changed_material_index': PINS[code]['material']})
    report = {'schema': 1, 'models': rows, 'source_tool_sha256': sha(Path(__file__).read_bytes()),
              'authority': 'Optional Racer-authored tint only. Geometry, native units and shared exhaust limitations unchanged.',
              'retained_bytes_before': retained_size(leaf), 'leaf_cap_bytes': CAP}
    payloads.append((Path('manifest.json'), (json.dumps(report, indent=2) + '\n').encode()))
    require(all(len(data) <= MEMBER for _, data in payloads) and retained_size(leaf) + sum(len(data) for _, data in payloads) <= CAP, 'leaf_budget_before_write')
    output.mkdir(mode=0o700)
    for code in codes: (output / code).mkdir(mode=0o700)
    for path, data in payloads:
        require(retained_size(leaf) + len(data) <= CAP, 'leaf_budget_during_write')
        with os.fdopen(os.open(output / path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'wb') as f: f.write(data)
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--code', action='append', choices=PINS, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    def timeout(signum, frame): raise TimeoutError('cohort_deadline')
    signal.signal(signal.SIGALRM, timeout); signal.alarm(290)
    try: print(json.dumps(publish(a.output.absolute(), a.code), indent=2))
    finally: signal.alarm(0)


if __name__ == '__main__': main()
