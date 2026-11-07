#!/usr/bin/env python3
"""Opt-in static MC3 LOD0 completion from exact native DAVE filename joins.

This is an authored assembly of main-car references, not a recovered runtime
customization-selection or shared-attachment consumer.
"""
import copy
import hashlib
import math
from pathlib import Path
import struct
from prepare_gt4_vehicle import require, pack
from repair_mc3_vehicle import frames


def assemble(document, binary, native, dat, members, reader, config):
    doc = copy.deepcopy(document); blob = bytearray(binary)
    fields = {}
    slots = ('FrontBumperIdx','RearBumperIdx','SideSkirtIdx','BodyIdx','SpoilerIdx','HoodIdx','TaillightGeomIdx')
    for line in config.decode('ascii').splitlines():
        tokens = line.split()
        if len(tokens) == 2 and tokens[0] in slots:
            require(tokens[0] not in fields, 'duplicate_config_slot'); fields[tokens[0]] = tokens[1]
    require(all(fields.get(k) == '0' for k in slots), 'nondefault_native_config')
    active = doc['scenes'][doc.get('scene', 0)]['nodes']; names = {doc['nodes'][i]['name'] for i in active}
    require(len(names) == len(active), 'duplicate_scene_names')
    rest = frames(native['skeleton']['bones']); joins = []; positions_total = indices_total = 0
    for node in doc['nodes']:
        if 'mesh' in node:
            for p in doc['meshes'][node['mesh']]['primitives']:
                positions_total += doc['accessors'][p['attributes']['POSITION']]['count']
                indices_total += doc['accessors'][p['indices']]['count']
    require(positions_total <= 1000000 and indices_total <= 1500000, 'existing_geometry_budget')
    def add(values, typ, fmt, component):
        blob.extend(b'\0' * (-len(blob) % 4)); offset = len(blob)
        for value in values: blob.extend(struct.pack('<' + fmt, *value))
        require(len(blob) <= 16*1024**2, 'assembled_binary_budget')
        doc['bufferViews'].append({'buffer': 0, 'byteOffset': offset, 'byteLength': len(blob)-offset})
        accessor = {'bufferView': len(doc['bufferViews'])-1, 'componentType': component, 'count': len(values), 'type': typ}
        if typ == 'VEC3': accessor.update(min=[min(v[k] for v in values) for k in range(3)], max=[max(v[k] for v in values) for k in range(3)])
        doc['accessors'].append(accessor); return len(doc['accessors'])-1
    parts = native['lods']['high']; require(len({p['name'] for p in parts}) == len(parts), 'duplicate_native_part')
    for part in parts:
        if part['mesh'] is not None or part['name'] in names: continue
        matches = [r for r in members if Path(r['name']).name.casefold() == (part['name'] + '.pck').casefold()]
        require(len(matches) == 1, 'external_exact_name_join'); row = matches[0]
        payload = dat[row['offset']:row['offset']+row['size']]
        require(hashlib.sha256(payload).hexdigest() == row['sha256'], 'external_source_hash')
        pck = reader.Pck(payload, row['name']); require(pck.kind == 22, 'external_mesh_profile')
        mesh = reader.read_mesh_object(pck, 128); primitives = []
        for draw in mesh['draws']:
            mi = draw['material']; require(0 <= mi < len(doc['materials']) and doc['materials'][mi]['extras']['index'] == mi, 'external_material_index')
            points = []; indices = []; uv = []; integers = []
            for batch in draw['batches']:
                indices.extend(i+len(points) for i in reader.strip_indices(batch)); points.extend(batch['positions'])
                require(len(batch.get('uvs', [])) == len(batch['positions']), 'external_uv_count')
                uv.extend(p[:2] for p in batch['uvs']); integers.extend(batch.get('position_integers', []))
            if not indices: continue
            positions_total += len(points); indices_total += len(indices)
            require(positions_total <= 1000000 and indices_total <= 1500000, 'assembled_geometry_budget')
            normals = [[0., 0., 0.] for p in points]
            for i in range(0, len(indices), 3):
                a,b,c = [points[j] for j in indices[i:i+3]]; u=[b[k]-a[k] for k in range(3)]; v=[c[k]-a[k] for k in range(3)]
                n=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
                for j in indices[i:i+3]: normals[j]=[normals[j][k]+n[k] for k in range(3)]
            normals=[[x/math.sqrt(sum(y*y for y in n)) for x in n] if sum(y*y for y in n)>1e-24 else [0.,1.,0.] for n in normals]
            attrs={'POSITION':add(points,'VEC3','3f',5126),'NORMAL':add(normals,'VEC3','3f',5126),'TEXCOORD_0':add(uv,'VEC2','2f',5126)}
            if integers:
                require(len(integers)==len(points),'external_integer_count'); attrs['_MC3_NATIVE_POSITION']=add(integers,'VEC3','3f',5126)
            primitives.append({'attributes':attrs,'indices':add([(i,) for i in indices],'SCALAR','I',5125),'material':mi,'extras':{'native_external_source_sha256':row['sha256'],'native_material_index':mi}})
        require(primitives and len(doc['nodes'])<4095,'external_node_budget')
        t,q=rest[part['bone']]; index=len(doc['nodes'])
        doc['nodes'].append({'name':part['name'],'mesh':len(doc['meshes']),'translation':t,'rotation':q,'scale':[1,1,1],
                             'extras':{'nativeBone':part['bone'],'sourceNames':[part['name']],'externalSource':copy.deepcopy(row)}})
        doc['meshes'].append({'name':part['name'],'primitives':primitives});active.append(index)
        doc['extras']['records'].append({'role':part['name'],'native_sha256':row['sha256'],'file':row['name']})
        joins.append({'part':part['name'],'node':index,'bone':part['bone'],'member':copy.deepcopy(row)})
    policy={'authority':'Racer-authored static completion of missing main PCK LOD0 references with exact case-insensitive DAVE filename joins and zero native config slot values.',
            'native_config_slots':fields,'joins':joins,'generated_normals':'Area-weighted static normals for appended geometry.',
            'limits':['Native runtime default/customization activation is not recovered.','Shared exhaust/light effects and rim/tire template choices are separate; no complete runtime stock assembly claim.','Original preview materials/images and geometry are retained; native shader execution is not emulated.']}
    doc['extras']['racerExternalAssembly']=policy;doc['buffers'][0]['byteLength']=len(blob)
    result=pack(doc,blob);require(len(result)<=16*1024**2,'assembled_source_budget')
    return result,policy
