#!/usr/bin/env python3
"""Reconcile curated car preparations into explicit per-car pipeline stages.

Stages are derived only from retained records (curated inventory, production
catalog, installed bytes, review evidence); this script invents no acceptance.
It does not run the game, extract sources or promote candidates.
"""
import argparse
import hashlib
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import import_car_models as source
import install_cars as install
import prepared_inventory as inventory_format
from new_report import write_new_report

CATALOG_PATH = ROOT / 'assets/local/vehicles/catalog.racer'
INSTALLED_DIR = ROOT / 'assets/local/vehicles'
PUBLIC_CATALOG = source.DEFAULT_CATALOG

# Retained family-level runtime acceptance pointers (see findings/car-coverage.md).
FAMILY_RUNTIME_REVIEW = {
    'gran-turismo-4': 'experiments/2026-11-06-expanded-acceptance/README.md + fit-review 20 hidden native GPU views',
    'ford-racing-2': 'experiments/2026-11-06-cohort-acceptance/README.md (Lightning 37-image loop, Focus loops); ford-gt-native for GT',
    'midnight-club-los-angeles': 'experiments/2026-11-05-mcla-vehicle/README.md + cohort-acceptance',
    'juiced-2': 'experiments/2026-11-05-juiced2-vehicle/README.md + import-recovery actual new-process reload',
    'midnight-club-3-remix': 'experiments/2026-11-06-mc3-coverage/README.md + fit-review MC3 wheelbase/track mount adaptation',
    'slrr-231': 'experiments/2026-11-06-slrr-rest-fit/README.md (source spring audit, rejected poses, fixed-pose clearance)',
}


def sha_file(path, cap=32 * 1024**2):
    return hashlib.sha256(install.regular_bytes(path, cap)).hexdigest()


def evidence_file(value):
    """A retained evidence path: a non-empty relative path to a regular file inside the project."""
    if not isinstance(value, str) or not value.strip() or Path(value).is_absolute():
        return False
    try:
        path = (ROOT / value).resolve(strict=True)
        path.relative_to(ROOT)
    except (OSError, ValueError):
        return False
    return path.is_file()


def slrr_audit_summary(audit):
    chassis = audit.get('chassis', [])
    return {
        'declarations': len(chassis),
        'packages': audit.get('package_count'),
        'banned_1_classes': sum(1 for c in chassis
                                if (c.get('script_links', {}).get('java') or {}).get('banned_literal_assignments')),
        'evidence': 'experiments/2026-11-06-slrr-coverage/README.md',
        'note': 'SLRR has no public-catalog row; discovery comes from the retained native audit only.',
    }


def stage_row(row, catalog_entries, public_ids, slrr_aliases):
    model = row['model_id']
    family = model.split('/')[0]
    slrr_alias = model.split('/', 1)[1] if family == 'slrr-231' else None
    evidence = row.get('review_evidence') or {}
    # Per-car native manifests are recognised by evidence key (native_views,
    # motion, garage*) or by the legacy path substrings, and must exist.
    manifest_hits = sorted(
        str(v) for k, v in evidence.items()
        if isinstance(v, str) and (k in ('native_views', 'motion') or k.startswith('garage')
                                   or 'native-views' in v or 'motion' in v)
        and evidence_file(v))
    integrated = row['prepared_sha256'] in catalog_entries
    is_player = row.get('role') == 'player'
    if model in public_ids:
        discovered = {'value': True, 'basis': 'pinned-public-catalog'}
    elif slrr_alias and slrr_alias in slrr_aliases:
        discovered = {'value': True, 'basis': 'retained-slrr-native-audit (outside public catalog)'}
    elif any(evidence_file(v) for v in evidence.values()):
        discovered = {'value': True, 'basis': 'retained-experiment-evidence (outside public catalog)'}
    else:
        discovered = {'value': False, 'basis': 'no retained discovery record'}
    runtime_reviewed = False
    runtime_basis = None
    # A family-level pointer only covers a car when its own evidence does not
    # exist; Juiced 2 cars beyond the 350Z need their own manifests.
    needs_own = family == 'juiced-2' and model != 'juiced-2/350Z'
    if is_player and integrated and manifest_hits and needs_own:
        runtime_reviewed = True
        runtime_basis = '; '.join(manifest_hits)
    elif is_player and integrated and not needs_own:
        runtime_reviewed = True
        runtime_basis = FAMILY_RUNTIME_REVIEW.get(family, 'findings/car-coverage.md')
    elif manifest_hits:
        runtime_reviewed = True
        runtime_basis = '; '.join(manifest_hits)
    validated_basis = 'publisher-hash-role-scale-containment' if is_player else (
        'reviewed-measurement' if row.get('reviewed_at_utc_ms') else 'measurement-only')
    blocked_reasons = []
    if not row.get('player_eligible'):
        reason = row.get('eligibility_reason') or 'research-candidate role; no promotion review'
        blocked_reasons.append(reason)
    for lim in row.get('limitations') or []:
        blocked_reasons.append(lim)
    if not integrated and row.get('role') != 'traffic':
        blocked_reasons.append('not installed in production catalog (requires a promotion review and publication decision)')
    return {
        'model_id': model,
        'family': family,
        'role': row.get('role'),
        'stages': {
            'discovered': discovered['value'],
            'discovered_basis': discovered['basis'],
            'extracted': bool(row.get('source_sha256')) and bool(row.get('prepared_sha256')),
            'prepared': bool(row.get('descriptor_sha256')),
            'validated': bool(row.get('measured')),
            'validated_basis': validated_basis,
            'integrated': integrated,
            'runtime_reviewed': runtime_reviewed,
            'runtime_basis': runtime_basis,
            'blocked': bool(blocked_reasons),
        },
        'blocked_reasons': blocked_reasons,
        'provenance': {
            'source_sha256': row.get('source_sha256'),
            'prepared_sha256': row.get('prepared_sha256'),
            'descriptor_sha256': row.get('descriptor_sha256'),
            'descriptor': row.get('descriptor'),
            'unit_authority': row.get('unit_authority'),
            'native_wheel_contract': bool(row.get('native_wheel_contract')),
        },
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--max-bytes', type=int, default=512 * 1024)
    args = p.parse_args()

    inv_raw = install.regular_bytes(ROOT / 'assets/catalog/prepared-sizes.json', inventory_format.MAX_BYTES)
    inventory = inventory_format.decode(inv_raw)['vehicles']
    catalog_raw = install.regular_bytes(CATALOG_PATH, install.MAX_LIBRARY)
    catalog_entries = {Path(json.loads(line)).stem for line in catalog_raw.decode().splitlines()[2:] if line.strip()}
    installed_prepared = {f.stem for f in INSTALLED_DIR.glob('*.vehicle')}

    cars = source.load_catalog(PUBLIC_CATALOG)
    in_scope = [c for c in cars if not source.excluded_model(c)]
    public_ids = {c['id'] for c in in_scope}

    slrr_aliases = set()
    slrr_summary = None
    slrr_audit = ROOT / 'experiments/2026-11-06-slrr-coverage/output/canonical-chassis-coverage.json'
    if slrr_audit.exists():
        audit = json.loads(slrr_audit.read_text())
        slrr_summary = slrr_audit_summary(audit)
        slrr_aliases = {c['alias'] for c in audit.get('chassis', []) if c.get('alias')}

    rows = [stage_row(r, catalog_entries, public_ids, slrr_aliases) for r in inventory]
    players = [r for r in rows if r['role'] == 'player']
    missing = [r['model_id'] for r in players if not r['stages']['integrated']]
    if missing:
        raise SystemExit('player stage invariant violated: players absent from the production catalog: '
                         + ', '.join(missing))

    prepared_ids = {r['model_id'] for r in rows}
    unprepared = [c for c in in_scope if c['id'] not in prepared_ids]
    by_family = {}
    for c in unprepared:
        fam = c['game']
        d = by_family.setdefault(fam, {'discovered_not_extracted': 0, 'adapter_dispatch_match': 0})
        d['discovered_not_extracted'] += 1
        if (c['game'], c.get('source_profile')) in install.ADAPTERS:
            d['adapter_dispatch_match'] += 1

    # Installed join: the .vehicle filename stem follows the prepared_sha256
    # naming convention; file content is the descriptor bytes. A file counts
    # as registered when either relation matches the curated inventory.
    prepared_sha_set = {r['prepared_sha256'] for r in inventory}
    descriptor_owner = {}
    for r in inventory:
        if r.get('descriptor_sha256'):
            descriptor_owner.setdefault(r['descriptor_sha256'], r['model_id'])
    registered_stems = set()
    for stem in installed_prepared:
        content_sha = sha_file(INSTALLED_DIR / (stem + '.vehicle'))
        if stem in prepared_sha_set or content_sha in descriptor_owner:
            registered_stems.add(stem)
    unregistered = sorted(installed_prepared - registered_stems)
    content_only_match = sorted(s for s in registered_stems
                                if s not in prepared_sha_set
                                and sha_file(INSTALLED_DIR / (s + '.vehicle')) in descriptor_owner)
    result = {
        'schema': 1,
        'generated_at_utc_ms': int(time.time() * 1000),
        'inputs': {
            'prepared_inventory_sha256': install.sha(inv_raw),
            'production_catalog_sha256': install.sha(catalog_raw),
            'public_catalog_sha256': source.CATALOG_SHA,
            'tool_source_sha256': sha_file(Path(__file__)),
        },
        'stage_definitions': {
            'discovered': ('present in the pinned public catalog (%d in-scope) or a retained native audit%s'
                           % (len(in_scope), f" (SLRR {slrr_summary['declarations']} declarations)" if slrr_summary else '')),
            'extracted': 'actual source bytes consumed; source and prepared SHA pins exist',
            'prepared': 'a bounded .vehicle descriptor is registered in the curated inventory',
            'validated': 'measured geometry exists; basis states publisher containment, reviewed measurement, or measurement-only',
            'integrated': 'prepared SHA present in the production catalog.racer',
            'runtime_reviewed': 'retained native GPU/motion/full-lock/keyboard evidence at frozen hashes, or family-level retained acceptance for players',
            'blocked': 'explicit remaining acceptance gap (eligibility/limitations/not installed)',
        },
        'counts': {
            'inventory_rows': len(rows),
            'players': len(players),
            'traffic': sum(r['role'] == 'traffic' for r in rows),
            'research_candidates': sum(r['role'] == 'research-candidate' for r in rows),
            'integrated': sum(r['stages']['integrated'] for r in rows),
            'runtime_reviewed': sum(r['stages']['runtime_reviewed'] for r in rows),
            'blocked': sum(r['stages']['blocked'] for r in rows),
            'public_catalog_in_scope': len(in_scope),
            'discovered_not_extracted_total': len(unprepared),
            'installed_unregistered': len(unregistered),
        },
        'installed_content_only_matches': content_only_match,
        'discovered_not_extracted_by_family': by_family,
        'installed_unregistered_prepared_sha256': unregistered,
        'slrr_native_audit': slrr_summary,
        'models': rows,
        'limits': [
            'Stages are record-derived; no game run, extraction or GPU replay occurred in this report.',
            'Player runtime_review uses family-level retained acceptance pointers; per-car manifests remain in their own experiments.',
            'discovered_not_extracted counts public-catalog rows without a curated preparation; they are not playable or reviewed.',
            'Integrating further rows is a separate promotion decision (per-car review and storage allowance); this report neither grants nor measures it.',
        ],
    }
    payload = (json.dumps(result, indent=1, allow_nan=False) + '\n').encode()
    write_new_report(args.output, payload, args.max_bytes)
    print(json.dumps(result['counts']))


if __name__ == '__main__':
    main()
