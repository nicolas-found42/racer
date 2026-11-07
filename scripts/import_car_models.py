#!/usr/bin/env python3
"""Acquire pinned static GLB previews, without asserting gameplay completeness."""
import argparse
from collections import Counter
import hashlib
from http.client import HTTPException
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import struct
import sys
import tempfile
import time
import urllib.request
import uuid

COMMIT = 'ce047799fc550cdf92e4f7b62d97ef5c603e53ad'
CATALOG_SHA = 'fcd6eb5badd4cc120da3daaae315e83b71fb2b9400062b371b73c9f42a442e6c'
DEFAULT_CATALOG = Path(__file__).resolve().parent.parent / 'experiments/2026-11-05-car-models/output/source-catalog.json'
MAX_MODEL = 16 * 1024**2
MAX_BATCH = 32 * 1024**2
BASE = 'https://raw.githubusercontent.com/nicolas-found42/carmodels/{}/dealership/public/'
# User exclusions affect active listing/acquisition, never the retained catalog.
EXCLUDED_GAMES = frozenset({'gran-turismo', 'redline'})

# These exact previews need further adaptation. They remain research inputs,
# unlike the user's excluded families. A repaired preparation can be published
# with an explicit reviewed resolution tied to its new mesh identity.
PLAYER_SOURCE_REQUIREMENTS = {
    'ae131adae1f8ffede6d476f18ce227ef72af5d6755c0de6d1263bf78c892f300': ('gran-turismo-4/benz0001', 'nonstandard_wheel_layout'),
    '34c3dc8164b7a3d529447944c389a303f8cf6b44344d5849d66bfd1329c0f839': ('gran-turismo-4/daih0017', 'nonstandard_wheel_layout'),
    'fd5b7149ed4750bbe714586e811d4ad00c098e70c85ffbc3bf5f8e24291b67b6': ('gran-turismo-4/dmlr0001', 'degenerate_front_wheel_placement'),
    '68f302939f2c13b9e28866bbb136d29890dbebe25caa011444707c3fc26ec363': ('gran-turismo-4/ford0013', 'source_body_pose_unresolved'),
    '972dd5bfe04c42da1e4258e97859f99707d38d04e192c6c742fbb13236816ed9': ('gran-turismo-4/jay_0001', 'body_and_added_wheel_ownership'),
}

def player_preparation_requirement(model_id, source_sha256):
    row = PLAYER_SOURCE_REQUIREMENTS.get(source_sha256)
    # The requirement follows exact source bytes even if a review row aliases
    # their catalog ID. ID edits must not erase known adaptation work.
    return row[1] if row else None

def excluded_model(car):
    return any(car.get(key, '').split('/', 1)[0] in EXCLUDED_GAMES for key in ('game', 'id', 'file'))

class ImportFailure(Exception):
    pass

def relative(value):
    if not isinstance(value, str) or len(value) > 256 or not re.fullmatch(r'[A-Za-z0-9_./ -]+', value):
        raise ImportFailure('invalid_path')
    if value.startswith('/') or any(p in ('', '.', '..') for p in value.split('/')):
        raise ImportFailure('invalid_path')
    return str(PurePosixPath(value))

def load_catalog(path, expected_sha=CATALOG_SHA, commit=COMMIT):
    if not re.fullmatch('[0-9a-f]{64}', expected_sha) or not re.fullmatch('[0-9a-f]{40}', commit):
        raise ImportFailure('invalid_pin')
    with Path(path).open('rb') as stream:
        data = stream.read(16 * 1024**2 + 1)
    if len(data) > 16 * 1024**2 or hashlib.sha256(data).hexdigest() != expected_sha:
        raise ImportFailure('catalog_hash_or_size')
    catalog = json.loads(data)
    cars = catalog.get('cars') if isinstance(catalog, dict) else None
    if not isinstance(cars, list) or len(cars) > 4096:
        raise ImportFailure('catalog_shape')
    seen = set()
    for car in cars:
        if not isinstance(car, dict): raise ImportFailure('catalog_entry')
        key = relative(car.get('id'))
        relative(car.get('game'))
        name = relative(car.get('file'))
        size, digest = car.get('bytes'), car.get('sha256')
        if key in seen or not name.endswith('.glb') or type(size) is not int or size <= 0 or not isinstance(digest, str) or not re.fullmatch('[0-9a-f]{64}', digest):
            raise ImportFailure('catalog_entry')
        if not isinstance(car.get('records', []), list) or len(car.get('records', [])) > 1024:
            raise ImportFailure('catalog_records')
        package = car.get('native_package')
        if package is not None and (not isinstance(package, dict) or type(package.get('bytes')) is not int or package['bytes'] < 0):
            raise ImportFailure('catalog_native_package')
        limits = car.get('claim_limits', [])
        if not isinstance(limits, list) or len(limits) > 64 or any(not isinstance(v, str) or len(v) > 4096 for v in limits):
            raise ImportFailure('catalog_claim_limits')
        seen.add(key)
    return cars

def inventory(cars):
    cars = [car for car in cars if not excluded_model(car)]
    result = {}
    for car in cars:
        group = result.setdefault(car['game'], {'models': 0, 'preview_bytes': 0, 'native_packages': 0, 'native_bytes': 0, 'record_fields': Counter()})
        group['models'] += 1
        group['preview_bytes'] += car['bytes']
        package = car.get('native_package')
        if isinstance(package, dict):
            group['native_packages'] += 1
            group['native_bytes'] += package.get('bytes', 0)
        for record in car.get('records', []):
            if isinstance(record, dict): group['record_fields'].update(record.keys())
    return {'schema': 1, 'families': result, 'models': len(cars), 'preview_bytes': sum(c['bytes'] for c in cars), 'completeness': 'unreviewed-static-preview'}

def safe_dir(path):
    path = Path(path)
    # Refuse symlinks in caller-selected descendants, including the store itself.
    for part in (path, *path.parents):
        if part.is_symlink(): raise ImportFailure('symlink_directory')
        if part.exists() and not part.is_dir(): raise ImportFailure('non_directory')
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.is_symlink(): raise ImportFailure('symlink_directory')
    return path

def read_verified(path, car):
    path = Path(path)
    if any(parent.is_symlink() for parent in path.parents): raise ImportFailure('symlink_directory')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode): raise ImportFailure('nonregular_asset')
        data = stream.read(car['bytes'] + 1)
        after = os.fstat(stream.fileno())
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise ImportFailure('changed_asset')
    validate(data, car)
    return data

def validate(data, car):
    if len(data) != car['bytes']: raise ImportFailure('size_mismatch')
    if hashlib.sha256(data).hexdigest() != car['sha256']: raise ImportFailure('hash_mismatch')
    if len(data) < 20 or struct.unpack_from('<4sII', data) != (b'glTF', 2, len(data)):
        raise ImportFailure('unsupported_glb')
    offset = 12
    while offset < len(data):
        if offset + 8 > len(data): raise ImportFailure('invalid_glb_chunk')
        size, kind = struct.unpack_from('<II', data, offset)
        if offset == 12:
            if kind != 0x4e4f534a or not size: raise ImportFailure('invalid_glb_json')
            try: document = json.loads(data[offset+8:offset+8+size])
            except (ValueError, UnicodeError): raise ImportFailure('invalid_glb_json')
            if not isinstance(document, dict) or (document.get('asset') if isinstance(document.get('asset'), dict) else {}).get('version') != '2.0': raise ImportFailure('invalid_glb_json')
        if size % 4 or offset + 8 + size > len(data): raise ImportFailure('invalid_glb_chunk')
        offset += 8 + size
    if offset != len(data): raise ImportFailure('invalid_glb_chunk')

def acquire(cars, ids, store, *, expected_sha=CATALOG_SHA, commit=COMMIT, cache=None, opener=urllib.request.urlopen, minimum_free=20 * 1024**3):
    if not ids or len(ids) > 16 or len(set(ids)) != len(ids): raise ImportFailure('selection_count')
    by_id = {c['id']: c for c in cars}
    if any(key not in by_id for key in ids): raise ImportFailure('unknown_id')
    selected = [by_id[key] for key in ids]
    if any(excluded_model(car) for car in selected): raise ImportFailure('excluded_source')
    if any(c['bytes'] > MAX_MODEL for c in selected) or sum(c['bytes'] for c in selected) > MAX_BATCH:
        raise ImportFailure('batch_budget')
    store = safe_dir(store)
    objects, receipts = safe_dir(store / 'objects'), safe_dir(store / 'receipts')
    if shutil.disk_usage(store).free < minimum_free: raise ImportFailure('free_space')
    started = time.monotonic()
    results = []
    for car in selected:
        uri = BASE.format(commit) + car['file'].replace(' ', '%20')
        receipt = {'schema': 1, 'source': {'repository': 'nicolas-found42/carmodels', 'commit': commit, 'catalog_sha256': expected_sha, 'uri': uri},
                   'model': {k: car[k] for k in ('id', 'game', 'file', 'bytes', 'sha256')},
                   'completeness': {'status': 'unreviewed-static-preview', 'limitations': car.get('claim_limits', ['No source completeness claims available.'])},
                   'geometry_metadata': {'records': len(car.get('records', [])), 'record_fields': sorted({key for record in car.get('records', []) if isinstance(record, dict) for key in record}), 'authority': 'pinned catalog; geometry and physics not independently verified'},
                   'native_package': 'not acquired; native ZIP import unsupported by this command',
                   'acquisition': {'status': 'failed', 'error_code': None}, 'timestamp_unix': int(time.time())}
        destination = objects / (car['sha256'] + '.glb')
        temporary = None
        try:
            if time.monotonic() - started > 240: raise ImportFailure('batch_deadline')
            if destination.exists() or destination.is_symlink():
                data = read_verified(destination, car)
                status = 'verified-resume'
            else:
                if cache is not None:
                    data = read_verified(Path(cache) / (car['sha256'] + '.glb'), car)
                    status = 'verified-cache'
                else:
                    with opener(uri, timeout=30) as stream:
                        # read1 avoids a trickling peer extending a full-sized read indefinitely.
                        chunks, received = [], 0
                        reader = getattr(stream, 'read1', stream.read)
                        while received <= car['bytes']:
                            if time.monotonic() - started > 240: raise ImportFailure('batch_deadline')
                            chunk = reader(min(65536, car['bytes'] + 1 - received))
                            if not chunk: break
                            chunks.append(chunk)
                            received += len(chunk)
                        data = b''.join(chunks)
                    validate(data, car)
                    status = 'verified-download'
                fd, temporary = tempfile.mkstemp(prefix='.import-', dir=objects)
                with os.fdopen(fd, 'wb') as stream:
                    stream.write(data)
                    stream.flush()
                    os.fsync(stream.fileno())
                read_verified(temporary, car)
                # Atomic no-overwrite publication; concurrent matching writers may resume.
                try: os.link(temporary, destination)
                except FileExistsError: read_verified(destination, car)
            receipt['acquisition'].update(status=status, file='objects/' + destination.name, observed_bytes=len(data), observed_sha256=hashlib.sha256(data).hexdigest())
        except ImportFailure as error:
            receipt['acquisition']['error_code'] = str(error)
        except (OSError, ValueError, HTTPException):
            receipt['acquisition']['error_code'] = 'transport_or_storage_failure'
        finally:
            if temporary is not None:
                try: Path(temporary).unlink(missing_ok=True)
                except OSError:
                    receipt['acquisition'].update(status='failed', error_code='temporary_cleanup_failed')
        path = receipts / (str(uuid.uuid4()) + '.json')
        with path.open('x', encoding='utf-8') as stream:
            os.chmod(path, 0o600)
            json.dump(receipt, stream, indent=2)
            stream.write('\n')
        results.append(receipt)
    return results

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['inventory', 'acquire'])
    parser.add_argument('--catalog', type=Path, default=DEFAULT_CATALOG)
    parser.add_argument('--catalog-sha256', default=CATALOG_SHA)
    parser.add_argument('--commit', default=None)
    parser.add_argument('--store', type=Path)
    parser.add_argument('--cache', type=Path, help='Directory containing SHA256.glb verified cache candidates')
    parser.add_argument('--id', action='append', default=[])
    args = parser.parse_args(argv)
    if args.catalog_sha256 != CATALOG_SHA and args.commit is None:
        parser.error('custom catalog SHA requires explicit --commit')
    args.commit = args.commit or COMMIT
    try:
        cars = load_catalog(args.catalog, args.catalog_sha256, args.commit)
        if args.action == 'inventory': result = inventory(cars)
        else:
            if not args.store: parser.error('acquire requires --store')
            result = acquire(cars, args.id, args.store, expected_sha=args.catalog_sha256, commit=args.commit, cache=args.cache)
        print(json.dumps(result, indent=2))
        return 2 if isinstance(result, list) and any(r['acquisition']['status'] == 'failed' for r in result) else 0
    except (ImportFailure, OSError, ValueError) as error:
        print('import failed: ' + (str(error) if isinstance(error, ImportFailure) else 'invalid_or_unavailable_input'), file=sys.stderr)
        return 2

if __name__ == '__main__': sys.exit(main())
