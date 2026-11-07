#!/usr/bin/env python3
"""Bounded pinned PS2 MC3 cohort research; never publishes a player catalog."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import struct
import time
import urllib.request

from prepare_gt4_vehicle import Geometry, require, unpack
from prepare_mcla_vehicle import read_regular
import prepare_mc3_vehicle as wrapper
from repair_mc3_vehicle import archive, frames
from mc3_wheel_contract import resolve

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://raw.githubusercontent.com/nicolas-found42/carmodels/ce047799fc550cdf92e4f7b62d97ef5c603e53ad/'
MEMBER_CAP = 16 * 1024**2
BATCH_CAP = 32 * 1024**2
OUTPUT_CAP = 64 * 1024**2
BUDGET_ROOT = None
sha = lambda b: hashlib.sha256(b).hexdigest()


def retained_size(root):
    return sum(p.stat().st_size for p in root.rglob('*') if p.is_file())


def write(path, data):
    payload = data if isinstance(data, bytes) else (json.dumps(data, indent=2, allow_nan=False) + '\n').encode()
    require(len(payload) <= MEMBER_CAP, 'output_member_budget')
    if BUDGET_ROOT is not None:require(retained_size(BUDGET_ROOT)+len(payload)<=OUTPUT_CAP,'leaf_budget_before_write')
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as f:
        f.write(payload)


def pinned_rows(codes):
    require(1 <= len(codes) <= 4 and len(set(codes)) == len(codes), 'cohort_count')
    raw = read_regular(wrapper.CATALOG, MEMBER_CAP)
    index = read_regular(wrapper.INDEX, MEMBER_CAP)
    require(sha(raw) == wrapper.CATALOG_SHA and sha(index) == wrapper.INDEX_SHA, 'catalog_index_pin')
    cars = json.loads(raw)['cars']; files = json.loads(index)['files']; rows = []
    for code in codes:
        require(code.startswith('vp_') and '/' not in code and code not in ('vp_350z_04', 'vp_corvettez06_03'), 'cohort_scope')
        matches = [c for c in cars if c['id'] == 'midnight-club-3-remix/' + code]
        require(len(matches) == 1 and matches[0]['source_profile'] == 'mc3-ps2-static-preview-v1', 'public_PS2_join')
        car = matches[0]
        wheels=[r for r in car['records'] if 'nativeWheelComponent' in r]
        bones={r['bone'] for r in wheels}
        require(len(bones)==4 and len(wheels)==8 and {(r['bone'],r['nativeWheelComponent'])for r in wheels}=={(b,k)for b in bones for k in('rim','tire')},'four_wheel_catalog_scope')
        configs = [r for r in files if r['file'].endswith('/' + code + '.carcfg')]
        require(configs and len({r['sha256'] for r in configs}) == 1, 'config_identity')
        members = [r for r in files if r['file'].startswith(code + '/assets/')]
        require(members, 'native_index_members')
        rows.append({'code': code, 'catalog': car, 'config': configs[0], 'config_duplicate_paths': [r['file'] for r in configs], 'members': members})
    total = sum(r['catalog']['bytes'] + r['catalog']['native_package']['bytes'] + r['config']['bytes'] for r in rows)
    require(total <= BATCH_CAP, 'selected_source_budget')
    return rows


def acquire(record, prefix, output):
    require(type(record['bytes']) is int and 0 < record['bytes'] <= MEMBER_CAP, 'member_budget')
    name = record['file']
    require(not name.startswith('/') and '..' not in name.split('/'), 'source_path')
    url = BASE + prefix + name
    with urllib.request.urlopen(url, timeout=30) as response:
        data = response.read(record['bytes'] + 1)
    require(len(data) == record['bytes'] and sha(data) == record['sha256'], 'download_identity')
    write(output, data)
    return {'url': url, 'path': str(output.resolve()), 'bytes': len(data), 'sha256': sha(data)}


def native_member_joins(members, indexed):
    result = []
    require(len({r['name'] for r in members}) == len(members), 'duplicate_native_name')
    for member in members:
        matches = [r for r in indexed if r['source'].get('name') == member['name']]
        require(len(matches) == 1, 'native_index_name_join')
        row = matches[0]; source = row['source']
        require(row['sha256'] == member['sha256'] and row['bytes'] == member['size'] and
                all(source[k] == member[k] for k in ('offset', 'ordinal', 'size', 'stored')), 'native_index_range_hash')
        result.append({'member': member, 'index_file': row['file']})
    require(len(result) == len(indexed), 'native_index_member_count')
    return result


def raw_bone_check(pck, bones):
    """Direct range reads crosscheck decoder fields; not a second format discovery."""
    for bone in bones:
        at = bone['offset']
        require(type(at) is int and 0 <= at <= len(pck) - 68, 'bone_range')
        require(struct.unpack_from('<H', pck, at + 56)[0] == bone['index'], 'raw_bone_index')
        for key, delta in (('global_position', 0), ('local_position', 32), ('rotation_raw', 44)):
            require(list(struct.unpack_from('<3f', pck, at + delta)) == list(bone[key]), 'raw_bone_pose')
    return len(bones)


def body_closure(doc, binary, vehicle, dat, members, reader, folder):
    """Exact selected LOD0 arrays and rest frames, with omissions reported explicitly."""
    byname = {Path(r['name']).name.casefold(): r for r in members}
    require(len(byname) == len(members), 'ambiguous_member_basename')
    parts = vehicle['lods']['high']; partmap = {p['name']: p for p in parts}
    require(len(partmap) == len(parts), 'duplicate_native_part')
    active = doc['scenes'][doc.get('scene', 0)]['nodes']
    nodes = [doc['nodes'][i] for i in active if 'nativeWheelJoint' not in doc['nodes'][i].get('extras', {})]
    dormant=[]
    for i,node in enumerate(doc['nodes']):
        if i in active or node.get('name') not in partmap:continue
        part=partmap[node['name']]
        if part['mesh'] is not None and part['mesh']['draws'] and all(doc['materials'][draw['material']].get('extras',{}).get('shader_category')=='drop_shadow' for draw in part['mesh']['draws']):
            dormant.append(part['name'])
    expected = {p['name'] for p in parts if p['name'] not in dormant}
    actual = {n['name'] for n in nodes}
    require(len(actual) == len(nodes), 'duplicate_selected_part')
    report = {'expected_selected_stock_names': sorted(expected), 'missing_selected_stock_names': sorted(expected - actual),
              'unexpected_selected_names': sorted(actual - expected), 'selected_parts': [], 'positions_verified': 0,
              'triangles_verified': 0, 'external_reference_names': [p['name'] for p in parts if p['mesh'] is None],
              'dormant_drop_shadow_names': dormant}
    records = {r['role']: r for r in doc['extras']['records']}
    g = Geometry(doc, binary); rest = frames(vehicle['skeleton']['bones'])
    for node in nodes:
        require(node['name'] in partmap, 'selected_part_native_join')
        part = partmap[node['name']]; external = part['mesh'] is None
        row = byname[(part['name'] + '.pck').casefold()] if external else byname[doc['extras']['car'] + '.pck']
        require(records[node['name']]['native_sha256'] == row['sha256'], 'preview_part_hash')
        if external:
            pck=reader.Pck(dat[row['offset']:row['offset'] + row['size']],row['name']);require(pck.kind==22,'external_mesh_profile');mesh=reader.read_mesh_object(pck,128)
        else:
            mesh = part['mesh']
        t, q = rest[part['bone']]
        require(node['extras']['nativeBone'] == part['bone'] and not node.get('children') and 'matrix' not in node, 'body_part_frame')
        require(max(abs(a-b) for a,b in zip(node.get('translation', [0,0,0]), t)) < 1e-7 and
                max(abs(a-b) for a,b in zip(node.get('rotation', [0,0,0,1]), q)) < 1e-7 and node.get('scale', [1,1,1]) == [1,1,1], 'body_rest_frame')
        draws = []
        for draw in mesh['draws']:
            points = []; indices = []; integers = []
            for batch in draw['batches']:
                indices.extend(i + len(points) for i in reader.strip_indices(batch))
                points.extend(batch['positions']); integers.extend(batch.get('position_integers', []))
            if indices:
                draws.append((draw, points, indices, integers))
        primitives = doc['meshes'][node['mesh']]['primitives']
        require(len(draws) == len(primitives), 'native_draw_count'); nv = nt = 0
        for (draw, points, indices, integers), primitive in zip(draws, primitives):
            require(primitive['material'] == draw['material'], 'native_material_join')
            require([x[0] for x in g.values(primitive['indices'])] == indices, 'native_indices')
            require(g.values(primitive['attributes']['POSITION']) == [struct.unpack('<3f', struct.pack('<3f', *p)) for p in points], 'native_positions')
            if integers:
                require(g.values(primitive['attributes']['_MC3_NATIVE_POSITION']) == [tuple(float(v) for v in p) for p in integers], 'native_integer_positions')
            nv += len(points); nt += len(indices) // 3
        report['selected_parts'].append({'name': node['name'], 'bone': part['bone'], 'native_sha256': row['sha256'], 'external': external, 'positions': nv, 'triangles': nt, 'rest_frame_equal': True})
        report['positions_verified'] += nv; report['triangles_verified'] += nt
        require(report['positions_verified'] <= 1000000 and report['triangles_verified'] <= 500000, 'closure_geometry_budget')
    report['selected_stock_body_closed'] = actual == expected
    report['scope']='All main PCK LOD0 mesh references except retained dormant drop_shadow draws. Static authored selection, not native runtime default activation.'
    return report


def prove(row, folder, reader, source_folder=None):
    source_folder=source_folder or folder
    raw = read_regular(source_folder / 'source.glb', MEMBER_CAP); dat = read_regular(source_folder / 'source.dat', MEMBER_CAP)
    require(sha(raw) == row['catalog']['sha256'] and sha(dat) == row['catalog']['native_package']['sha256'], 'retained_identity')
    doc, binary = unpack(raw); code = row['code']; require(doc['extras']['car'] == code, 'source_code')
    members = archive(dat); joins = native_member_joins(members, row['members'])
    main = [m for m in members if Path(m['name']).name == code + '.pck']; require(len(main) == 1, 'native_main_join'); main = main[0]
    pck = dat[main['offset']:main['offset'] + main['size']]; path = folder / 'main.pck'; write(path, pck)
    vehicle = reader.read_vehicle(path); bones = json.loads(json.dumps(vehicle['skeleton']['bones']))
    raw_bone_check(pck, bones)
    proof = {'source_glb_sha256': sha(raw), 'native_dat_sha256': sha(dat), 'native_pck_sha256': sha(pck),
             'native_skeleton': bones, 'native_members': members, 'index_joins': joins,
             'raw_68_byte_bone_pose_check_count': len(bones), 'reader_sha256': wrapper.READER_SHA,
             'authority': 'Actual pinned PS2 Remix DAT/PCK bytes; static decoder interpretation. No Xbox evidence or native game execution.'}
    write(folder / 'native-proof.json', proof)
    closure = body_closure(doc, binary, vehicle, dat, members, reader, folder); write(folder / 'body-closure.json', closure)
    config = read_regular(source_folder / 'default.carcfg', MEMBER_CAP); require(sha(config) == row['config']['sha256'], 'config_pin')
    keys = {'TypeName','FrontBumperIdx','RearBumperIdx','SideSkirtIdx','BodyIdx','SpoilerIdx','HoodIdx','TaillightGeomIdx','ExhaustRear','UseSideExhaust','WindowTintIdx'}
    fields = {}
    for line in config.decode('ascii').splitlines():
        tokens = line.split()
        if len(tokens) == 2 and tokens[0] in keys:
            require(tokens[0] not in fields, 'duplicate_config_field'); fields[tokens[0]] = tokens[1]
    contract = resolve(doc, bones)
    summary = {'body_closure': closure, 'native_config_selected_fields': fields, 'wheel_contract': contract,
               'limits': ['Stock-named LOD0 selection is a static assembly rule; native default-selection consumer is untraced.',
                          'Shared exhaust, rim and tire source choices are not freshly decoded here; preview lineage is retained, not full runtime stock closure.',
                          'No unit authority, factory fit, shader parity, native steering/suspension or player eligibility claim.']}
    write(folder / 'source-contract.json', summary)
    budget=OUTPUT_CAP-retained_size(BUDGET_ROOT)-1024**2 if BUDGET_ROOT is not None else OUTPUT_CAP
    result = wrapper.build(source_folder / 'source.glb', sha(raw), folder / 'native-proof.json', source_folder / 'source.dat', path, folder / 'prepared-v1',complete_external_lod0=True,native_config_path=source_folder/'default.carcfg',output_budget=budget)
    assembled,ab=unpack((folder/'prepared-v1/assembled-source.glb').read_bytes())
    complete=body_closure(assembled,ab,vehicle,dat,members,reader,folder);write(folder/'assembled-body-closure.json',complete)
    require(complete['selected_stock_body_closed'],'assembled_body_incomplete')
    return {'status': 'prepared_research_candidate', 'prepared_sha256': result['prepared_sha256'], 'descriptor': str((folder / 'prepared-v1' / (result['prepared_sha256'] + '.vehicle')).resolve()), 'wheelbase': result['wheelbase'], 'body_positions_verified': complete['positions_verified'], 'body_triangles_verified': complete['triangles_verified'], 'external_parts_appended':len(result['external_assembly']['joins']),'runtime_player_eligible': False}


def run(codes, output, source_cache=None):
    global BUDGET_ROOT
    rows = pinned_rows(codes); output = Path(output)
    require(not output.exists() and not any(p.is_symlink() for p in (output, *output.parents)), 'fresh_output')
    require(shutil.disk_usage(output.parent).free >= 20*1024**3, 'free_space')
    reader_bytes = read_regular(wrapper.READER, 1024**2); require(sha(reader_bytes) == wrapper.READER_SHA, 'reader_pin')
    BUDGET_ROOT=output.parent;require(retained_size(BUDGET_ROOT)<OUTPUT_CAP-1024**2,'leaf_budget')
    output.mkdir(mode=0o700); write(output / 'selection.json', rows)
    spec = importlib.util.spec_from_file_location('pinned_mc3_cohort_reader', wrapper.READER)
    reader = importlib.util.module_from_spec(spec); spec.loader.exec_module(reader)
    manifest = {'schema': 1, 'catalog_sha256': wrapper.CATALOG_SHA, 'index_sha256': wrapper.INDEX_SHA,
                'source_tool_sha256': sha(Path(__file__).read_bytes()), 'source_platform': 'PS2 Remix pinned public archive',
                'models': [], 'runtime_player_eligible': False}
    for row in rows:
        folder = output / row['code']; folder.mkdir(mode=0o700)
        item = {'code': row['code'], 'source_sha256': row['catalog']['sha256'], 'native_dat_sha256': row['catalog']['native_package']['sha256'], 'status': 'pending'}
        try:
            if source_cache is None:
                item['acquired'] = [acquire(row['catalog'], 'dealership/public/', folder / 'source.glb'),
                                acquire(row['catalog']['native_package'], 'dealership/public/', folder / 'source.dat'),
                                acquire(row['config'], 'games/midnight-club-3-remix/cars/', folder / 'default.carcfg')]
            else:item['retained_source_folder']=str((Path(source_cache)/row['code']).resolve())
            item.update(prove(row, folder, reader,None if source_cache is None else Path(source_cache)/row['code']))
        except TimeoutError:
            item.update(status='deadline_interrupted',reason='cohort_deadline_or_network_timeout');manifest['models'].append(item);write(folder/'status.json',item)
            for pending in rows[len(manifest['models']):]:manifest['models'].append({'code':pending['code'],'status':'not_attempted_after_deadline','source_sha256':pending['catalog']['sha256'],'native_dat_sha256':pending['catalog']['native_package']['sha256']})
            write(output/'manifest.json',manifest)
            raise
        except (ValueError, OSError, KeyError, TypeError, IndexError, struct.error) as error:
            item.update(status='rejected_or_incomplete', error_type=type(error).__name__, reason=str(error)[:200])
        manifest['models'].append(item); write(folder / 'status.json', item)
        size = sum(p.stat().st_size for p in output.rglob('*') if p.is_file())
        require(size <= OUTPUT_CAP, 'leaf_budget')
    manifest['retained_bytes_before_manifest'] = size
    write(output / 'manifest.json', manifest)
    return manifest


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--code', action='append', required=True); p.add_argument('--output', type=Path, required=True);p.add_argument('--source-cache',type=Path); a = p.parse_args()
    def timeout(signum, frame): raise TimeoutError('cohort_deadline')
    signal.signal(signal.SIGALRM, timeout); signal.alarm(290)
    try:
        report = run(a.code, a.output,a.source_cache)
        print(json.dumps(report, indent=2)); raise SystemExit(0 if all(x['status'] == 'prepared_research_candidate' for x in report['models']) else 2)
    finally:
        signal.alarm(0)
