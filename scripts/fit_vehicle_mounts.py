#!/usr/bin/env python3
"""Translate complete wheel mounts to published tracks; preserve every mesh shape.

This is an authored Racer candidate, not recovery of original runtime placement.
Only identity mesh leaves under uniform-scale/translation parents are supported.
"""
import argparse
import collections
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shlex
import shutil

from prepare_gt4_vehicle import Geometry, pack, unpack
from prepare_mcla_vehicle import read_regular

SOURCE_SHA = 'e9a4ddbd6a98e6538217bafe109049522566d7b3fbe102bdb8b0842dec1a4c0f'
DESCRIPTOR_SHA = '9a3f2ce8ab75f8387444885b8ff4d30416a6797f9719b095c21e8eb05be50db8'
LABELS = ('FL', 'FR', 'RL', 'RR')

def require(condition, code):
    if not condition:
        raise ValueError(code)

def numbers(values, count):
    require(len(values) == count, 'number_count')
    out = [float(x) for x in values]
    require(all(math.isfinite(x) for x in out), 'nonfinite_number')
    return out

def descriptor_rows(text, expected):
    require(len(text.encode()) <= 32768, 'descriptor_budget')
    rows = [shlex.split(line) for line in text.splitlines() if line.strip()]
    require(len(rows) >= 12 and rows[0] == ['RACER_VEHICLE', '1'], 'descriptor_version')
    require([row[0] for row in rows[:12]] == ['RACER_VEHICLE','id','name','mesh','sha256','source_sha256','body','wheel','wheel','wheel','wheel','groups'], 'descriptor_schema')
    require(rows[1] == ['id','vehicle-'+expected] and rows[3] == ['mesh',expected+'.glb'] and rows[4] == ['sha256',expected], 'descriptor_identity')
    require(len(rows[2]) == 2 and len(rows[5]) == 2 and re.fullmatch('[0-9a-f]{64}',rows[5][1]), 'descriptor_identity')
    body = numbers(rows[6][1:], 6)
    wheels = []
    for label, row in zip(LABELS, rows[7:11]):
        require(row[:2] == ['wheel',label], 'wheel_order')
        wheels.append(numbers(row[2:], 5))
    require(len(rows[11]) == 2 and int(rows[11][1]) == len(rows)-12, 'group_count')
    groups = {}
    for row in rows[12:]:
        require(len(row) == 3 and row[0] == 'group', 'group_schema')
        node, wheel = map(int,row[1:])
        require(node >= 0 and node not in groups and -1 <= wheel <= 3, 'group_identity')
        groups[node] = wheel
    require(collections.Counter(groups.values()) == collections.Counter({-1:len(groups)-8,0:2,1:2,2:2,3:2}) and len(groups)>8, 'eight_wheel_groups')
    return rows, body, wheels, groups

def leaf_frames(doc, groups):
    nodes = doc['nodes']
    require(0 < len(nodes) <= 4096 and len(doc['scenes']) == 1 and doc.get('scene',0) == 0, 'scene_budget')
    require(not any(doc.get(k) for k in ('skins','animations','extensionsRequired')), 'unsupported_runtime')
    seen, meshes, frames = set(), set(), {}
    def visit(index, scale, translation, depth):
        require(type(index) is int and 0 <= index < len(nodes) and index not in seen and depth < 64, 'shared_or_cyclic_node')
        seen.add(index);node = nodes[index]
        require(not any(k in node for k in ('matrix','rotation','skin','weights','extensions')), 'unsupported_node_frame')
        if 'mesh' in node:
            require(not node.get('children') and node.get('translation',[0,0,0]) == [0,0,0] and node.get('scale',[1,1,1]) == [1,1,1], 'nonidentity_mesh_frame')
            mesh = node['mesh']
            require(type(mesh) is int and 0 <= mesh < len(doc['meshes']) and mesh not in meshes and index in groups, 'shared_or_unbound_mesh')
            meshes.add(mesh);frames[index] = (scale,translation[:]);return
        require(index not in groups and node.get('children'), 'invalid_parent')
        local_scale = numbers(node.get('scale',[1,1,1]),3)
        local_t = numbers(node.get('translation',[0,0,0]),3)
        require(local_scale[0] == local_scale[1] == local_scale[2] and .1 <= local_scale[0] <= 10, 'nonuniform_parent')
        require(local_t[0] == local_t[2] == 0, 'unsupported_parent_translation')
        next_t = [translation[i]+scale*local_t[i] for i in range(3)]
        for child in node['children']:
            visit(child,scale*local_scale[0],next_t,depth+1)
    for root in doc['scenes'][0]['nodes']:
        visit(root,1.,[0.,0.,0.],0)
    require(seen == set(range(len(nodes))) and set(frames) == set(groups) and len(meshes) == len(doc['meshes']), 'incomplete_scene')
    return frames

def fit(raw, text, canonical, *, expected=SOURCE_SHA, descriptor_sha=DESCRIPTOR_SHA):
    require(len(raw) <= 32*1024**2 and hashlib.sha256(raw).hexdigest() == expected, 'source_pin')
    require(hashlib.sha256(text.encode()).hexdigest() == descriptor_sha, 'descriptor_pin')
    rows, body, wheels, groups = descriptor_rows(text,expected)
    targets = numbers([canonical['nominal']['front_track'],canonical['nominal']['rear_track']],2)
    require(all(.5 <= x <= 3 for x in targets), 'target_track')
    doc, binary = unpack(raw);frames = leaf_frames(doc,groups);geometry = Geometry(doc,binary)
    # Verify all original geometry against the supplied descriptor before moving it.
    vertices = indices = 0
    for index, wheel in groups.items():
        scale, translation = frames[index]
        require(.1 <= scale <= 10, 'parent_scale_budget')
        mesh = doc['meshes'][doc['nodes'][index]['mesh']]
        require(not mesh.get('weights') and 0 < len(mesh['primitives']) <= 4096, 'mesh_features')
        for primitive in mesh['primitives']:
            require(primitive.get('mode',4) == 4 and not primitive.get('targets'), 'primitive_features')
            pos = primitive['attributes']['POSITION'];count = doc['accessors'][pos]['count']
            vertices += count;require(0 < count and vertices <= 1000000, 'vertex_budget')
            points = geometry.values(pos,'VEC3',{5126})
            count = doc['accessors'][primitive['indices']]['count'];indices += count
            require(0 < count and count%3 == 0 and indices <= 1500000, 'index_budget')
            require(all(0 <= v[0] < len(points) for v in geometry.values(primitive['indices'],'SCALAR',{5121,5123,5125})), 'index_bounds')
            for point in points:
                world = [scale*point[i]+translation[i] for i in range(3)]
                if wheel < 0:
                    require(all(body[i]-2e-6 <= world[i] <= body[i+3]+2e-6 for i in range(3)), 'body_containment')
                else:
                    c = wheels[wheel]
                    require(abs(world[0]-c[0]) <= c[4]/2+2e-6 and math.hypot(world[1]-c[1],world[2]-c[2]) <= c[3]+2e-6, 'wheel_containment')
    deltas, changes = {}, []
    for axle, left in enumerate((0,2)):
        a,b = wheels[left],wheels[left+1]
        require(a[0] < 0 < b[0] and abs(a[1]-b[1]) < 1e-4 and abs(a[2]-b[2]) < 1e-4, 'paired_axle')
        center = (a[0]+b[0])/2
        for side, wheel in enumerate((left,left+1)):
            target = center+(-.5 if side == 0 else .5)*targets[axle]
            delta = target-wheels[wheel][0]
            require(abs(delta) <= .25 and (delta <= 0 if side == 0 else delta >= 0), 'outward_fit_budget')
            deltas[wheel] = delta;wheels[wheel][0] = target
    for index,wheel in groups.items():
        if wheel < 0:continue
        local_delta = deltas[wheel]/frames[index][0]
        doc['nodes'][index]['translation'] = [local_delta,0,0]
        changes.append({'node':index,'wheel':LABELS[wheel],'world_delta_x':deltas[wheel],'parent_world_uniform_scale':frames[index][0],'local_delta_x':local_delta})
    metadata = {'schema':1,'role':'player-candidate','runtime_player_eligible':False,'input_prepared_sha256':expected,'input_descriptor_sha256':descriptor_sha,'method':'Translate complete rim and tyre groups and their descriptor pivots in world X; no mesh deformation','canonical_id':canonical['canonical_id'],'canonical_source':canonical['source'],'target_tracks':dict(zip(('front','rear'),targets)),'changes':changes,'limitations':['Racer-authored factory-track mount adaptation; original native runtime wheel placement remains unknown.','Body geometry, wheel shapes, Y/Z coordinates, normals, indices, materials and images remain unchanged.','Source and uniform-wheelbase-only preparations are retained unchanged.','Candidate remains ineligible pending GPU wheel-arch fit and physics validation.']}
    doc.setdefault('extras',{})['racerTrackMountFit'] = metadata
    prepared = pack(doc,binary);require(len(prepared) <= 32*1024**2, 'output_budget');digest = hashlib.sha256(prepared).hexdigest()
    rows[1][1] = 'vehicle-'+digest;rows[2][1] = 'MC3 Corvette Z06 (authored factory mounts)';rows[3][1] = digest+'.glb';rows[4][1] = digest
    for row,wheel in zip(rows[7:11],wheels):row[2:] = [format(v,'.17g') for v in wheel]
    descriptor = '\n'.join(' '.join(json.dumps(v) if row[0] in ('id','name','mesh') and i == 1 else v for i,v in enumerate(row)) for row in rows)+'\n'
    return prepared,descriptor,{**metadata,'prepared_sha256':digest,'body':body,'wheels':wheels,'groups':list(groups.items()),'vertices_verified':vertices,'indices_verified':indices}

def publish(descriptor, dimensions, output):
    text = read_regular(descriptor,32768).decode();raw = read_regular(Path(descriptor).with_suffix('.glb'),32*1024**2)
    source = read_regular(dimensions,256*1024);catalog = json.loads(source)
    canonical = next(v for v in catalog['vehicles'] if v['canonical_id'] == 'chevrolet-corvette-2003')
    prepared,text,receipt = fit(raw,text,canonical)
    receipt['dimensions_catalog_sha256'] = hashlib.sha256(source).hexdigest();receipt['canonical_source_record'] = catalog['sources'][canonical['source']]
    output = Path(output)
    require(not output.exists() and not any(p.is_symlink() for p in (output,*output.parents)), 'fresh_output_required')
    require(shutil.disk_usage(output.parent).free >= 20*1024**3, 'disk_budget');output.mkdir(mode=0o700)
    digest = receipt['prepared_sha256']
    for name,data in ((digest+'.glb',prepared),(digest+'.vehicle',text.encode()),('receipt.json',(json.dumps(receipt,indent=2)+'\n').encode())):
        fd = os.open(output/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'wb') as stream:stream.write(data)
    return receipt

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__);parser.add_argument('descriptor',type=Path);parser.add_argument('--dimensions',type=Path,default=Path('assets/catalog/dimensions.json'));parser.add_argument('--output',type=Path,required=True);args = parser.parse_args()
    print(json.dumps(publish(args.descriptor,args.dimensions,args.output),indent=2))
