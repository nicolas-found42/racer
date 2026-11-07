#!/usr/bin/env python3
"""Regenerate Juiced 2 per-car wheel attributions from one audited implementation.

Commits the attribution evidence as data + derivation: sizing outputs are
computed by importing sizing_fields from the audited contract kernel
(scripts/juiced2_wheel_contract.py), never re-implemented here. Input archive,
kernel and this script are SHA-pinned inside the output. No game execution,
no geometry or inventory change.
"""
import argparse
import hashlib
import json
import time
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from new_report import write_new_report
from juiced2_wheel_contract import sizing_fields  # single audited setter implementation
from juiced2_wheel_state import (  # audited register-derivation chain and shared archive helpers
    PARAMETERS, load_parameters, parse_tyre_code, record_fields, sha256_file, sizing_chain)

ROOT = Path(__file__).resolve().parents[1]

# Audited shared-profile anchors (findings/juiced2-wheel-contract.md); the same
# values the contract kernel itself tests against.
PROFILE = {'object436': 13.3577327728, 'object440': 25.7133712769,
           'object444': 33.3729476929}

# Attribution records: factory references are Firecrawl-sourced (jobs pinned in
# each record); identities remain labeled numeric-signature hypotheses.
ATTRIBUTIONS = {
    'juiced-2/350Z': {
        'record_index': 755, 'confidence': 'strong',
        'basis': ('3498 cc = VQ35DE exact; 225/45R18+245/45R18 = 18-inch OEM sport fitment; '
                  '306 bhp/1624 kg vs factory 287/1456 (game-tuned)'),
        'factory_reference': {
            'model': "Nissan 350Z Z33 (2003 base coupe / VQ35DE)",
            'displacement_cc': 3498, 'power_hp': 287, 'kerb_weight_kg': 1456,
            'redline_rpm': 6600, 'tyre_front': 'P225/50WR17', 'tyre_rear': '235/50WR17',
            'sources': [
                'https://www.thecarconnection.com/specifications/nissan_350z_2003',
                'https://www.centuryu.com/uploads/1/4/4/6/144698822/2005_350z.pdf',
            ],
            'agent_job': '01a1b3c2-805f-72ea-812a-4854348fa8fc',
        },
    },
    'juiced-2/CHARGER_RT': {
        'record_index': 922, 'confidence': 'exact-3-of-4-field',
        'basis': ('5654 cc, 1828 kg and 225/60R18 match the factory 5.7L Hemi (5654 cc, kerb 1828 kg, P225/60R18) exactly; '
                  'the fourth figure differs: record 335 bhp vs factory 340 hp'),
        'factory_reference': {
            'model': 'Dodge Charger R/T LX (2006, 5.7L Hemi)',
            'displacement_cc': 5654, 'power_hp': 340, 'kerb_weight_kg': 1828,
            'tyre_front': 'P225/60R18', 'tyre_rear': 'P225/60R18',
            'sources': [
                'https://www.motorweek.org/road_tests/2006_dodge_charger_program_2440/',
                'https://www.edmunds.com/dodge/charger/2006/st-100518597/features-specs/',
                'https://www.theautochannel.com/news/2005/11/21/148734.html',
                'https://www.thecarconnection.com/specifications/dodge_charger_2006',
            ],
            'agent_job': '01a1b3c2-805f-72ea-812a-4854348fa8fc',
        },
    },
    'juiced-2/KOENIGSEGG': {
        'record_index': 664, 'confidence': 'strong',
        'basis': ('4700 cc, 806 bhp, front 255/35R19 = CCR manufacturer spec; '
                  'rear 355/30R20 deviates from factory 335/30-20'),
        'factory_reference': {
            'model': 'Koenigsegg CCR (2004-2006)',
            'displacement_cc': 4700, 'power_hp': 806, 'kerb_weight_kg': 1230,
            'redline_rpm': 7250, 'tyre_front': '255/35-19 (Y)', 'tyre_rear': '335/30-20 (Y)',
            'sources': [
                'https://www.koenigsegg.com/technical-specifications-ccr',
                'https://www.supercars.net/blog/2004-koenigsegg-ccr/',
            ],
            'agent_job': '01a1b3c2-805f-72ea-812a-4854348fa8fc',
        },
    },
    'juiced-2/Z4': {
        'record_index': 517, 'confidence': 'strong',
        'basis': ('3246 cc = S54B32 exact; 360 bhp @7900 with redline 8000 = Z4 M power rpm/redline exact '
                  '(factory 343 PS @7900); 225/45R18 + 255/40R18 = Z4 M stock fitment exact; '
                  '50/50 front weight distribution matches BMW layout'),
        'factory_reference': {
            'model': 'BMW Z4 M Coupe (E86, 2006-2008; S54B32)',
            'displacement_cc': 3246, 'power_ps': 343, 'power_rpm': 7900,
            'redline_rpm': 8000, 'kerb_weight_kg': 1485,
            'tyre_front': '225/45 ZR18', 'tyre_rear': '255/40 ZR18',
            'sources': [
                'https://www.bmwgroup-classic.com/en/models/bmw-classics/product-description-page.ad-1187-1.bmw-z4-m-coupe-e86.html',
                'https://autocatalogarchive.com/wp-content/uploads/2016/05/BMW-Z4-M-2008.pdf',
                'https://www.billswebspace.com/2007BMWZ4MCoupeRoadsterBrochure.pdf',
            ],
            'note': 'European PS/EU figures used; North American SAE figures documented as market difference.',
            'agent_job': '01a1b3e0-9a0f-7232-bacd-3d73c04976f0',
        },
    },
    'juiced-2/MINI': {
        'record_index': 962, 'confidence': 'strong',
        'basis': ('GearRatios 3.308/2.130/1.480/1.139/0.950/0.816 vs the sourced R56 Cooper S Getrag '
                  'GS6-53BG set 3.308/2.130/1.483/1.139/0.949/0.816: four of six identical to three decimals, '
                  'the other two differ by 0.003 and 0.001 (see gear_ratio_comparison, derived from the record), '
                  'so the set matches within 0.003 in all six positions, not exactly; kerb 1205 kg and redline 6500 rpm exact vs '
                  'factory R56 (BMW press/owner-manual); 162 lb-ft (=220 Nm) @4000 sits ~8% below R56 '
                  'factory 240 Nm with 4000 rpm inside its 1600-5000 plateau; FWD 61:39; 195/55R16 is a '
                  'base-fitment size (sourced Cooper S fitment is 205/45R17); EngineSize 1500 deviates '
                  'from factory 1598 — the only field where this record fails an exact match, unlike the '
                  'other four attributions which match displacement exactly. Record torque units are '
                  'lb-ft, confirmed by Z4M record 269 lb-ft = 365 Nm exact, 350Z 268 lb-ft ~ 371 Nm, '
                  'Charger 375 lb-ft ~ 525 Nm.'),
        'generation_note': ('220 Nm also equals the R53 Cooper S factory torque peak exactly, so the '
                            'torque field alone cannot separate the generations; the within-0.003 gearbox set, '
                            'kerb weight and redline all match R56, making R56 the attributed '
                            'generation with the R53 torque coincidence recorded as residual tension.'),
        'factory_reference': {
            'model': 'MINI Cooper S (R56 hatchback, 2006-2013; N14 1.6 turbo, Getrag GS6-53BG)',
            'displacement_cc': 1598, 'power_bhp': 175, 'power_rpm': 5500,
            'torque_nm': 240, 'torque_rpm': 1600,
            'kerb_weight_kg': 1205, 'redline_rpm': 6500,
            'tyre': '205/45 R17 run-flat (factory Cooper S); record carries 195/55R16 (base-fitment deviation, noted)',
            'gear_ratios': [3.308, 2.130, 1.483, 1.139, 0.949, 0.816],
            'gearbox': 'Getrag GS6-53BG 6-speed manual',
            'sources': [
                'https://www.press.bmwgroup.com/japan/article/attachment/T0013491JA/30327',
                'https://www.press.bmwgroup.com/global/article/attachment/T0022797EN/42556',
                'https://www.miniusa.com/content/dam/mini/PDF/archiveownermanuals/MY02-07/2007_Owners_Manual_Hardtop.pdf',
                'https://www.northamericanmotoring.com/forums/r56-hatch-talk-2007/87431-gear-ratios.html',
                'https://www.press.bmwgroup.com/global/article/attachment/T0127719EN/194927',
            ],
            'exact_matches': ('kerb weight 1205 kg and redline 6500 rpm exact; gearbox ratios identical in 4 of 6 '
                              'positions and within 0.003 in all six'),
            'deviations': ('EngineSize 1500 vs 1598; power @6000 vs @5500; torque 220 vs 240 Nm; '
                           'tyre 195/55R16 vs factory 205/45R17'),
            'ratio_note': ('The R53 (1st-gen) uses a different twin-layshaft box (GS6-85BG); the near-match of the '
                           'record ratio set to the R56 box favours R56-generation, it does not prove it.'),
            'agent_jobs': ['01a1b41a-ce3e-7050-b70f-b3a0f1a5796a', '01a1b41e-964b-727e-b047-2b5efe73b168'],
        },
    },
}


def gear_ratio_comparison(record, factory):
    """Compare the archive record's GearRatios with the sourced factory set, from the data."""
    fields, _ = record_fields(record)
    got = [round(x, 3) for x in fields.get('GearRatios', [])]
    want = factory.get('gear_ratios')
    if not got or not want or len(got) != len(want):
        return None
    diffs = [round(abs(a - b), 3) for a, b in zip(got, want)]
    return {'record': got, 'factory': want, 'identical_positions': sum(d == 0 for d in diffs),
            'positions': len(want), 'max_abs_difference': max(diffs)}


def tyres_of(record):
    _, wheels = record_fields(record)
    return {axle: w['TyreCode'] for axle, w in wheels.items() if 'TyreCode' in w}


def kernel_sizing(tyre_code):
    """Audited chains only: sizing_chain derives the setter registers from the
    parsed TyreCode (f4=1 assumption; f4 unrecovered); sizing_fields computes
    the setter outputs. Neither arithmetic is re-implemented here."""
    chain = sizing_chain(parse_tyre_code(tyre_code))
    out = sizing_fields(PROFILE, chain['f1_width'], chain['f2_aspect'], chain['forwarded_f3'])
    if not (chain['xscale'] == out['object292'] and chain['radial_scale'] == out['object296']
            and chain['extra_424'] == out['object424']):  # explicit raise: an assert vanishes under python -O
        raise RuntimeError(f'chain/kernel divergence for {tyre_code}: sizing_chain and sizing_fields disagree')
    return {'tyre': tyre_code, 'xscale': out['object292'], 'radial_scale': out['object296'],
            'extra_424': out['object424'],
            'note': 'audited sizing_chain registers + kernel sizing_fields; f4=1, multiplier=1.05; not certified geometry'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--max-bytes', type=int, default=64 * 1024)
    p.add_argument('--archive', type=Path, default=PARAMETERS,
                   help='retained handling-parameters.json (default: the Oversteer juiced2-recovery archive)')
    args = p.parse_args()

    raw, parameters = load_parameters(args.archive)
    by_index = {r['index']: r for r in parameters}
    absent = sorted(a['record_index'] for a in ATTRIBUTIONS.values() if a['record_index'] not in by_index)
    if absent:
        raise SystemExit(f'{args.archive} lacks attributed handling record(s) {absent}; the attributions are pinned '
                         'to the retained 94-record juiced2-recovery archive')
    untyred = sorted(m for m, a in ATTRIBUTIONS.items() if not tyres_of(by_index[a['record_index']]))
    if untyred:
        raise SystemExit(f'{args.archive}: attributed record(s) for {untyred} carry no TyreCode')
    malformed = []
    for model, a in ATTRIBUTIONS.items():
        for axle, code in tyres_of(by_index[a['record_index']]).items():
            try:
                parse_tyre_code(code)
            except ValueError as error:
                malformed.append(f'record {a["record_index"]} ({model}) {axle}: {error}')
    if malformed:
        raise SystemExit(f'{args.archive}: ' + '; '.join(malformed))

    result = {
        'schema': 1,
        'generated_at_utc_ms': int(time.time() * 1000),
        'inputs': {
            'handling_archive': str(args.archive),
            'handling_archive_sha256': hashlib.sha256(raw).hexdigest(),
            'kernel_script_sha256': sha256_file(Path(__file__).resolve().parent / 'juiced2_wheel_contract.py'),
            'state_script_sha256': sha256_file(Path(__file__).resolve().parent / 'juiced2_wheel_state.py'),
            'generator_script_sha256': sha256_file(Path(__file__).resolve()),
        },
        'method': ('Sizing outputs computed by importing sizing_fields from the audited contract kernel; '
                   'identities remain numeric-signature hypotheses; no geometry or inventory change.'),
        'attributions': {},
        'unresolved': {},
        'negative_joins': [
            'ordinal-index structural join: zero intersection',
            'ISO filename_hash join (1220 xdvdfs names + variants): zero hits',
            'car-name pattern filename_hash join (~45 patterns vs attributed keys): zero hits',
        ],
    }
    for model, attr in ATTRIBUTIONS.items():
        record = by_index[attr['record_index']]
        entry = dict(attr)
        entry['tyres'] = tyres_of(record)
        fields, _ = record_fields(record)
        entry['record_signature'] = {
            'EngineSize': (fields.get('EngineSize') or [None])[0],
            'PeakBhp': fields.get('PeakBhp'),
            'Redline': (fields.get('Redline') or [None])[0],
            'Mass': (fields.get('Mass') or [None])[0],
        }
        comparison = gear_ratio_comparison(record, attr['factory_reference'])
        if comparison:
            entry['gear_ratio_comparison'] = comparison
        entry['native_sizing_f4_1'] = {axle: kernel_sizing(code)
                                       for axle, code in entry['tyres'].items()}
        entry['identity'] = 'numeric-signature hypothesis (' + attr['confidence'] + ')'
        entry['geometry_applied'] = False
        result['attributions'][model] = entry

    payload = (json.dumps(result, indent=1, allow_nan=False) + '\n').encode()
    write_new_report(args.output, payload, args.max_bytes)
    print(json.dumps({'attributions': len(result['attributions']), 'bytes': len(payload)}))


if __name__ == '__main__':
    main()
