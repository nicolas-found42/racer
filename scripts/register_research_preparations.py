#!/usr/bin/env python3
"""Dry registration of existing exact preparations; never promotes or applies an inventory."""
import argparse
import copy
import json
import re
import shutil
import signal
import sys
import time
from pathlib import Path, PurePosixPath

import install_cars as common
from check_car_scale import measure_bytes
from vehicle_clearance import descriptor
from verification_lifecycle import VerificationLifecycle
import prepared_inventory as inventory_format

ROOT = Path(__file__).resolve().parents[1]
CATALOG = common.source.DEFAULT_CATALOG
CATALOG_SHA = common.source.CATALOG_SHA
MAX_SELECTION = 256 * 1024
MAX_MESH = 32 * 1024**2
MAX_BATCH = 128 * 1024**2
MAX_OUTPUT = 3 * inventory_format.MAX_BYTES + MAX_SELECTION + 2 * 1024**2
MAX_EVIDENCE = 2 * 1024**2
FIELDS = {'model_id', 'descriptor', 'expected_mesh_sha256', 'expected_descriptor_sha256',
          'expected_source_sha256', 'source_kind', 'evidence', 'limits'}
require = common.require


strict_json = inventory_format.strict_json


def digest(value):
    require(isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value), 'sha256_schema')
    return value


def relative(value):
    require(isinstance(value, str) and 0 < len(value) <= 512 and
            all(ord(c) >= 32 for c in value) and '\\' not in value, 'relative_path')
    path = PurePosixPath(value)
    require(not path.is_absolute() and path.as_posix() == value and
            all(part not in ('', '.', '..') for part in value.split('/')), 'relative_path')
    return Path(value)


def model_id(value):
    require(isinstance(value, str) and re.fullmatch('[a-z0-9-]+/[A-Za-z0-9_-]{1,96}', value), 'model_id_schema')
    return value.split('/', 1)


class Reads:
    """Charge every actual read; cache evidence identities without retaining evidence bodies."""
    def __init__(self): self.consumed = 0; self.evidence = {}
    def read(self, path, cap):
        remaining = MAX_BATCH - self.consumed
        require(remaining > 0, 'input_batch_budget')
        raw = common.regular_bytes(path, min(cap, remaining)); self.consumed += len(raw)
        return raw
    def evidence_identity(self, root, record):
        require(isinstance(record, dict) and set(record) == {'path', 'sha256'}, 'evidence_schema')
        path = relative(record['path']); expected = digest(record['sha256'])
        key = path.as_posix()
        if key not in self.evidence:
            data = self.read(root / path, MAX_EVIDENCE)
            self.evidence[key] = {'path': key, 'sha256': common.sha(data), 'bytes': len(data)}
        result = self.evidence[key]
        require(result['sha256'] == expected, 'evidence_hash_mismatch')
        return result.copy()


def public_catalog(reads):
    raw = reads.read(CATALOG, common.MAX_CATALOG)
    require(common.sha(raw) == CATALOG_SHA, 'catalog_pin')
    doc = strict_json(raw); rows = doc.get('cars') if isinstance(doc, dict) else None
    require(isinstance(rows, list) and len(rows) <= 4096, 'catalog_schema')
    indexed = {}
    for row in rows:
        require(isinstance(row, dict), 'catalog_row')
        # Historical excluded entries include nested identifiers. They are not
        # candidate namespaces and must not prevent registering in-scope rows.
        if common.source.excluded_model(row): continue
        ident = row.get('id'); game, code = model_id(ident)
        require(ident not in indexed and row.get('game') == game, 'catalog_identity')
        digest(row.get('sha256')); indexed[ident] = row
    return indexed


def candidate(row, root, reads, catalog):
    require(isinstance(row, dict) and set(row) == FIELDS, 'selection_row_fields')
    game, code = model_id(row['model_id'])
    require(game not in common.EXCLUDED_GAMES, 'excluded_source')
    require(not common.traffic_model({'game': game, 'code': code}), 'ambient_traffic_not_research_player')
    source = digest(row['expected_source_sha256']); meshsha = digest(row['expected_mesh_sha256'])
    descsha = digest(row['expected_descriptor_sha256']); kind = row['source_kind']
    if kind == 'public-catalog':
        source_row = catalog.get(row['model_id'])
        require(source_row is not None and source_row['sha256'] == source, 'public_source_join')
    else:
        require(kind == 'local-juiced-2' and game == 'juiced-2', 'local_source_family')
    path = relative(row['descriptor'])
    require(path.name == meshsha + '.vehicle', 'descriptor_filename')
    db = reads.read(root / path, 32768)
    require(common.sha(db) == descsha, 'descriptor_hash_mismatch')
    require(common.descriptor_source(db) == source, 'descriptor_source_mismatch')
    fields, _, _ = descriptor(db.decode())
    require(all(len(fields[key]) == 1 for key in ('id', 'name', 'mesh', 'sha256', 'source_sha256')), 'descriptor_identity_fields')
    require(fields['sha256'] == [meshsha] and fields['mesh'] == [meshsha + '.glb'], 'descriptor_mesh_identity')
    measured = measure_bytes(db)  # Same bytes that supplied the descriptor hash and source identity.
    mb = reads.read((root / path).parent / fields['mesh'][0], MAX_MESH)
    require(common.sha(mb) == meshsha, 'mesh_hash_mismatch')
    evidence = row['evidence']; limits = row['limits']
    require(isinstance(evidence, list) and 1 <= len(evidence) <= 16, 'evidence_count')
    identities = [reads.evidence_identity(root, item) for item in evidence]
    require(len({item['path'] for item in identities}) == len(identities), 'duplicate_evidence_path')
    require(isinstance(limits, list) and 1 <= len(limits) <= 16 and
            all(isinstance(item, str) and 0 < len(item) <= 1024 and all(ord(c) >= 32 for c in item) for item in limits), 'limits_schema')
    return {'model_id': row['model_id'], 'source_sha256': source, 'prepared_sha256': meshsha,
            'descriptor_sha256': descsha, 'descriptor': path.as_posix(),
            'role': 'research-candidate', 'player_eligible': False, 'canonical': None,
            'unit_authority': 'Measured descriptor geometry in Racer coordinates; native physical units and factory applicability are unproven.',
            'measured': measured, 'measurement_scope': 'Declared descriptor geometry and exact mesh hash. No independent mesh containment or native runtime validation performed by this registrar.',
            'source_authority': {'kind': kind, 'catalog_sha256': CATALOG_SHA if kind == 'public-catalog' else None,
                                 'limits': 'Local Juiced 2 source identity is explicitly supplied and descriptor-bound; no public-catalog membership claim.' if kind == 'local-juiced-2' else 'Exact pinned public catalog model/source join; not original-game activation or completeness certification.'},
            'review_evidence': {'evidence_' + str(i): item['path'] for i, item in enumerate(identities)},
            'review_evidence_identity': identities, 'limitations': list(limits),
            'eligibility_reason': 'Research registration only. Supplied review evidence is retained by path/hash, not semantically certified. Explicit separate review is required for player eligibility.',
            'source_preparation_requirement': common.source.player_preparation_requirement(row['model_id'], source)}


def prepare_inventory(inventory_raw, selection_raw, root=ROOT, lifecycle=None):
    require(len(selection_raw) <= MAX_SELECTION, 'json_input_budget')
    inventory = inventory_format.decode(inventory_raw, require_schema=True)
    selection = strict_json(selection_raw)
    require(isinstance(selection, dict) and set(selection) == {'schema', 'preparations'} and type(selection['schema']) is int and selection['schema'] == 1, 'selection_schema')
    requested = selection['preparations']; require(isinstance(requested, list) and 1 <= len(requested) <= 64, 'selection_count')
    existing = {}; ids = set()
    for row in inventory['vehicles']:
        require(isinstance(row, dict), 'inventory_row'); model_id(row.get('model_id'))
        require(row['model_id'] not in existing, 'duplicate_inventory_id'); existing[row['model_id']] = row
    for row in requested:
        require(isinstance(row, dict) and set(row) == FIELDS, 'selection_row_fields'); model_id(row['model_id'])
        require(row['model_id'] not in ids, 'duplicate_selection_id'); ids.add(row['model_id'])
    reads = Reads(); reads.consumed = len(inventory_raw) + len(selection_raw)
    catalog = public_catalog(reads)
    result = copy.deepcopy(inventory); outcomes = []; additions = 0
    for request in requested:
        if lifecycle:
            lifecycle.record['active_model'] = request['model_id']; lifecycle.checkpoint()
        new = candidate(request, root, reads, catalog)
        old = existing.get(new['model_id'])
        if old is not None:
            differences = [key for key in ('source_sha256', 'prepared_sha256', 'descriptor_sha256') if old.get(key) != new[key]]
            outcomes.append({'model_id': new['model_id'], 'status': 'conflict_preserved' if differences else 'already_registered',
                             'differing_identity_fields': differences,
                             'existing_identity': {key: old.get(key) for key in differences},
                             'selected_identity': {key: new[key] for key in differences}})
        else:
            result['vehicles'].append(new); additions += 1
            outcomes.append({'model_id': new['model_id'], 'status': 'added_research_candidate'})
    require(result['vehicles'][:len(inventory['vehicles'])] == inventory['vehicles'], 'existing_rows_changed')
    data = inventory_format.encode(result) if additions else inventory_raw
    report = {'schema': 1, 'mode': 'dry-research-registration', 'inventory_input_sha256': common.sha(inventory_raw),
              'selection_sha256': common.sha(selection_raw), 'catalog_sha256': CATALOG_SHA,
              'inventory_output_sha256': common.sha(data), 'existing_rows': len(inventory['vehicles']),
              'added_rows': additions, 'total_rows': len(result['vehicles']), 'outcomes': outcomes,
              'input_bytes_consumed': reads.consumed, 'evidence_files': list(reads.evidence.values()),
              'existing_rows_semantically_unchanged': True, 'in_place_applied': False,
              'inventory_limits': {'bytes': inventory_format.MAX_BYTES, 'records': inventory_format.MAX_RECORDS},
              'limits': ['Registration is not native verification, a factory-size comparison or eligibility approval.',
                         'Measurements and identities share the same descriptor read. Mesh bytes are hash checked, not decoded by this command.',
                         'Evidence files are retained in place by path and sampled SHA; their claims are not automatically certified.',
                         'Individual reads are bounded regular-file snapshots, not an atomic filesystem version or durable backup.']}
    return data, report


def register(selection, inventory, output, *, root=ROOT):
    output = Path(output).absolute()
    require(not output.exists() and not any(p.is_symlink() for p in (output, *output.parents)), 'fresh_output_required')
    require(output.parent.is_dir() and shutil.disk_usage(output.parent).free >= 20 * 1024**3, 'output_parent_or_free_space')
    output.mkdir(mode=0o700)
    with VerificationLifecycle(output) as life:
        frozen = {}
        for kind, path, filename in (('inventory', inventory, 'input-inventory.json'),
                                     ('selection', selection, 'selection.json')):
            life.record['active_input'] = kind
            life.phase('retrieval'); life.checkpoint()
            raw = common.regular_bytes(path, inventory_format.MAX_BYTES if kind == 'inventory' else MAX_SELECTION)
            life.record[kind + '_sha256'] = common.sha(raw); life.checkpoint()
            life.phase('capture')
            common.immutable(output / filename, raw)
            frozen[kind] = raw
        life.record['active_input'] = None; life.checkpoint()
        original, selected = frozen['inventory'], frozen['selection']
        life.phase('validation'); data, report = prepare_inventory(original, selected, Path(root), life)
        life.record['active_model'] = None; life.checkpoint()
        report.update(finished_unix_ms=int(time.time()*1000), source_tool_sha256=common.sha(Path(__file__).read_bytes()))
        report_data = (json.dumps(report, indent=2, allow_nan=False) + '\n').encode()
        payloads = (('inventory.json', data), ('report.json', report_data))
        # Charge retained snapshots and the largest immutable temporary, whose
        # hard-link publication can momentarily expose two names for its bytes.
        retained = len(original) + len(selected) + sum(len(b) for _, b in payloads)
        peak = retained + max(len(original), len(selected), *(len(b) for _, b in payloads))
        require(peak + 65536 <= MAX_OUTPUT, 'output_budget')
        life.phase('capture')
        for name, payload in payloads: common.immutable(output / name, payload)
        life.complete()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--selection', type=Path, required=True); parser.add_argument('--inventory', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True); args = parser.parse_args()
    def timeout(signum, frame): raise TimeoutError('registration_deadline')
    signal.signal(signal.SIGALRM, timeout); signal.alarm(290)
    try:
        report = register(args.selection, args.inventory, args.output)
        print(json.dumps({'added_rows': report['added_rows'], 'total_rows': report['total_rows'], 'inventory_output_sha256': report['inventory_output_sha256']}))
        return 0
    except (OSError, ValueError, TypeError, KeyError, IndexError, RecursionError):
        print('Research registration rejected; inspect bounded lifecycle evidence if created.', file=sys.stderr); return 2
    finally: signal.alarm(0)


if __name__ == '__main__': sys.exit(main())
