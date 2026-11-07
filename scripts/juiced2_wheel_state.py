#!/usr/bin/env python3
"""Recover per-car Juiced 2 stock wheel state and derive native sizing outputs.

Static, bounded analysis only: reads the retained 94-record handling archive
(Oversteer juiced2-recovery) and applies the audited wheel-contract chain
(findings/juiced2-wheel-contract.md). No game execution, no geometry change.
"""
import argparse
import hashlib
import json
import re
import struct
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from new_report import write_new_report

ROOT = Path(__file__).resolve().parents[1]
RECOVERY = Path('/Users/nicolas/Documents/github/oversteer/artifacts/juiced2-recovery')
PARAMETERS = RECOVERY / 'handling-parameters.json'

# Audited shared-profile anchors (findings/juiced2-wheel-contract.md).
PROFILE_MAX_X = 13.3577327728
PROFILE_MIN_Y = 25.7133712769
PROFILE_MAX_Y = 33.3729476929
RADIAL_CONSTANT = 0.7874000072479248  # decoded f32 at 0x8204D464
GLOBAL_MULTIPLIER_INIT = 1.05         # mutable global 0x824CBE70, race-time value unobserved


def f32(value):
    return struct.unpack('>f', struct.pack('>f', value))[0]


def sha256_file(path, limit=64 * 1024**2):
    """SHA-256 of the whole file. A file larger than `limit` is refused rather than hashed as a prefix."""
    h = hashlib.sha256()
    total = 0
    with open(path, 'rb') as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b''):
            total += len(chunk)
            if total > limit:
                raise SystemExit(f'{path} exceeds the {limit}-byte pin limit; refusing to hash a prefix')
            h.update(chunk)
    return h.hexdigest()


RECORD_KEYS = ('index', 'key', 'sha256', 'decoded_fields')


def validate_parameters(path, parameters):
    """Reject archives that are not a non-empty list of handling records; every failure names the archive."""
    if not isinstance(parameters, list) or not parameters:
        raise SystemExit(f'{path}: "parameters" must be a non-empty list of handling records')
    seen = set()
    for position, record in enumerate(parameters):
        problem = None
        if not isinstance(record, dict):
            problem = 'is not an object'
        else:
            missing = [k for k in RECORD_KEYS if k not in record]
            if missing:
                problem = 'lacks ' + ', '.join(missing)
            elif not isinstance(record['index'], int) or isinstance(record['index'], bool):
                problem = 'has a non-integer index'
            elif record['index'] in seen:
                problem = f'repeats index {record["index"]}'
            elif not isinstance(record['decoded_fields'], list):
                problem = 'has non-list decoded_fields'
            else:
                for entry in record['decoded_fields']:
                    if not isinstance(entry, list):
                        continue  # record_fields ignores non-list entries
                    if entry and not isinstance(entry[0], str):
                        problem = f'has a field entry with a non-string name {entry[0]!r}'
                    elif entry and entry[0] in ('Location', 'TyreCode') and len(entry) < 2:
                        problem = f'has a {entry[0]} entry without a value'
                    elif entry and entry[0] in ('Location', 'TyreCode') and not isinstance(entry[1], str):
                        problem = f'has a non-string {entry[0]} value {entry[1]!r}'
                    if problem:
                        break
        if problem:
            ident = record.get('index', position) if isinstance(record, dict) else position
            raise SystemExit(f'{path}: parameters[{position}] (record {ident}) {problem}; '
                             'not a handling-parameters archive')
        seen.add(record['index'])


def load_parameters(path):
    """Return (raw bytes, parameter records) of the retained handling archive with actionable failures."""
    try:
        raw = Path(path).read_bytes()
    except OSError as error:
        raise SystemExit(f'handling archive unreadable: {path} ({error.strerror}); pass --archive PATH to the '
                         'Oversteer juiced2-recovery handling-parameters.json')
    try:
        parameters = json.loads(raw)['parameters']
    except (ValueError, KeyError, TypeError):
        raise SystemExit(f'{path} is not a handling-parameters archive (no JSON "parameters" list)')
    validate_parameters(path, parameters)
    return raw, parameters


def record_fields(record):
    fields = {}
    axle = None
    wheels = {}
    for entry in record['decoded_fields']:
        if not isinstance(entry, list) or not entry:
            continue
        if entry[0] == 'Location':
            axle = entry[1]
            wheels[axle] = {}
        elif entry[0] == 'TyreCode' and axle:
            wheels[axle]['TyreCode'] = entry[1]
        else:
            fields[entry[0]] = entry[1:]
    return fields, wheels


TYRE_CODE = re.compile(r'([0-9]{1,6})/([0-9]{1,6})R([0-9]{1,6})')  # ASCII digits only, as the native %d/%dR%d parser reads


def parse_tyre_code(code):
    """Audited parser chain: %d/%dR%d -> field60/64/68/72 (strictly positive ASCII-digit inputs of at most six digits)."""
    match = TYRE_CODE.fullmatch(code) if isinstance(code, str) else None
    if not match or not all(int(g) > 0 for g in match.groups()):
        raise ValueError(f'unsupported TyreCode {code!r}: expected positive ASCII %d/%dR%d (at most six digits each), '
                         'e.g. 225/45R18')
    w, a, r = (int(g) for g in match.groups())
    field60 = f32(w * 0.001)                 # width m
    field64 = f32(a * 0.01)                  # aspect ratio
    field68 = f32(field60 * field64)         # sidewall m
    field72 = f32(f32(r * 0.0254) * 0.5 + field68)  # fma(rim_in*.0254, .5, sidewall)
    return {'W': w, 'A': a, 'R': r, 'field60': field60, 'field64': field64,
            'field68': field68, 'field72': field72}


def sizing_chain(tyre, multiplier=GLOBAL_MULTIPLIER_INIT, f4=1.0):
    """Renderer 820F1DB0 -> 820F51C8 -> setter 8210F798, audited float order.

    f4 (configuration multiplier at context+684+192/+176) is unrecovered; the
    result is reported as a formula in f4 plus values at the f4=1 assumption.
    """
    f1 = f32(tyre['field60'] * 1000.0)       # = W (mm)
    f2 = tyre['field64']
    f3_in = f32(f32(tyre['field72'] - f32(tyre['field60'] * tyre['field64'])) * 78.74015808105469)
    f10 = f32(f32(tyre['R'] * 25.4) * multiplier)
    f9 = f32(f1 * f2)
    two_wa = f32(2.0 * f9)
    corr = f32(two_wa * f4)
    # forwarded f3 = (f10 + two_wa - corr) / 25.4, per-instruction f32
    num = f32(f32(f10 + two_wa) - corr)
    f3 = f32(num / 25.4)
    xscale = f32(f1 / f32(PROFILE_MAX_X * 20.0))
    radial = f32(f3 / f32(PROFILE_MIN_Y * RADIAL_CONSTANT))
    # Audited kernel (scripts/juiced2_wheel_contract.py sizing_fields):
    # requested_thickness = f32(f32(f1*f2) * 0.1); extra424 =
    # f32((requested_thickness - f32(maxY-minY)) / radial_scale).
    requested_thickness = f32(f32(f1 * f2) * 0.1)
    thickness = f32(PROFILE_MAX_Y - PROFILE_MIN_Y)
    extra = f32(f32(requested_thickness - thickness) / radial) if radial else None
    return {'f1_width': f1, 'f2_aspect': f2, 'f3_radius_in': f3_in,
            'forwarded_f3': f3, 'xscale': xscale, 'radial_scale': radial,
            'extra_424': extra, 'assumptions': {'multiplier': multiplier, 'f4': f4,
            'f4_note': 'unrecovered; values at f4=1 cancel the 2*W*A correction'}}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--max-bytes', type=int, default=256 * 1024)
    p.add_argument('--archive', type=Path, default=PARAMETERS,
                   help='retained handling-parameters.json (default: the Oversteer juiced2-recovery archive)')
    args = p.parse_args()

    raw, params = load_parameters(args.archive)
    rows = []
    for record in params:
        fields, wheels = record_fields(record)
        row = {'index': record['index'], 'key': record['key'],
               'sha256': record['sha256'], 'mass': (fields.get('Mass') or [None])[0],
               'peak_bhp': (fields.get('PeakBhp') or [None])[0],
               'engine_cc': (fields.get('EngineSize') or [None])[0],
               'redline': (fields.get('Redline') or [None])[0],
               'tyres': {axle: w.get('TyreCode') for axle, w in wheels.items()}}
        rows.append(row)

    result = {
        'schema': 1,
        'generated_at_utc_ms': int(time.time() * 1000),
        'scope': 'Static per-car stock wheel state from the retained 94-record handling archive; audited sizing chain applied; no game execution or geometry change.',
        'inputs': {
            'handling_parameters_sha256': hashlib.sha256(raw).hexdigest(),
            'handling_parameters_path': str(args.archive),
            'public_recovery_findings': 'oversteer/artifacts/juiced2-recovery/FINDINGS.md (93/94 records carry TyreCode)',
            'wheel_contract': 'findings/juiced2-wheel-contract.md (profile anchors, setter rounding, input bridge)',
        },
        'f4_trace': {
            'origin': 'renderer 820F1DB0 loads f4 from [context+684]+192 (selector 0/1) or +176 (otherwise) before calling 820F51C8',
            'construction': ('static trace (experiments/2026-11-06-juiced2-native-sizing/README.md): context+684 is the wheel '
                             'constructor 820f0a28 second argument, the 9672-byte car object (not NULL; the earlier '
                             'sub_821BC5xx NULL stores belong to other classes sharing offset 684). Car-object +176/+192 '
                             'default to 1.0f in constructor 82109860, are copied from a looked-up per-car record by '
                             '82194718 and reset to 0.5f on another path: f4 is data-driven per car and f4=1 is an '
                             'unverified assumption'),
            'multiplier_global': '0x824CBE70 initial float32 1.05 confirmed at decoded-image offset 0x4CBE70; bounded lis/addi scan found no direct writer; race-time value unobserved',
        },
        'record_count': len(rows),
        'records_with_tyre_code': sum(1 for r in rows if any(r['tyres'].values())),
        'records': rows,
        'limits': [
            'Record-to-car identity is not archive-joined; attributions are labeled hypotheses from numeric signatures and factory tyre fitment.',
            'f4 and the race-time multiplier are unrecovered; sizing outputs are formulas in f4 with f4=1 values, not certified stock geometry.',
            'Upgrade-level selection of these records remains unverified; these are the archive base records.',
        ],
    }
    payload = (json.dumps(result, indent=1, allow_nan=False) + '\n').encode()
    write_new_report(args.output, payload, args.max_bytes)
    print(json.dumps({'records': len(rows),
                      'with_tyre': result['records_with_tyre_code'],
                      'bytes': len(payload)}))


if __name__ == '__main__':
    main()
