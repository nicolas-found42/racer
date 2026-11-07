#!/usr/bin/env python3
"""Normalize one bounded GT4 static preview; original runtime parity remains unverified."""
import argparse
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import stat
import struct
import sys

MAX_SOURCE = 16 * 1024**2
MAX_OUTPUT = 32 * 1024**2
MAX_INDEX_WORK = 3000000
MAX_INSTANCE_INDICES = 1500000
WHEELS = ('front_left', 'front_right', 'rear_left', 'rear_right')
LABELS = ('FL', 'FR', 'RL', 'RR')

class PreparationError(ValueError): pass

def require(condition, reason):
    if not condition: raise PreparationError(reason)

def finite_vector(value, size):
    require(isinstance(value, list) and len(value) == size and all(type(v) in (int, float) and math.isfinite(v) for v in value), 'invalid_vector')
    return value

def unpack(data):
    require(20 <= len(data) <= MAX_SOURCE, 'source_size')
    require(struct.unpack_from('<4sII', data) == (b'glTF', 2, len(data)), 'glb_header')
    offset, chunks = 12, []
    while offset < len(data):
        require(offset+8 <= len(data), 'glb_chunk')
        size, kind = struct.unpack_from('<II', data, offset)
        require(size % 4 == 0 and offset+8+size <= len(data), 'glb_chunk')
        chunks.append((kind, data[offset+8:offset+8+size])); offset += 8+size
    require(len(chunks) == 2 and chunks[0][0] == 0x4e4f534a and chunks[1][0] == 0x004e4942, 'glb_chunks_unsupported')
    try: document = json.loads(chunks[0][1])
    except (ValueError, UnicodeError): raise PreparationError('glb_json')
    require(isinstance(document, dict) and isinstance(document.get('asset'), dict) and document['asset'].get('version') == '2.0', 'glb_asset')
    return document, bytearray(chunks[1][1])

def pack(document, binary):
    raw = json.dumps(document, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()
    raw += b' ' * (-len(raw) % 4)
    binary = bytes(binary) + b'\0' * (-len(binary) % 4)
    size = 28 + len(raw) + len(binary)
    require(size <= MAX_OUTPUT, 'output_budget')
    return struct.pack('<4sIII', b'glTF', 2, size, len(raw)) + b'JSON' + raw + struct.pack('<I', len(binary)) + b'BIN\0' + binary

class Geometry:
    def __init__(self, document, binary):
        self.document, self.binary = document, binary
    def values(self, index, expected_type=None, components=None):
        d = self.document
        require(type(index) is int and 0 <= index < len(d['accessors']), 'accessor_index')
        a = d['accessors'][index]
        require(isinstance(a, dict) and 'sparse' not in a and not a.get('normalized') and 'extensions' not in a, 'accessor_unsupported')
        sizes = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4}
        formats = {5121: ('B', 1), 5123: ('H', 2), 5125: ('I', 4), 5126: ('f', 4)}
        kind, ct = a.get('type'), a.get('componentType')
        require(kind in sizes and ct in formats and (expected_type is None or kind == expected_type) and (components is None or ct in components), 'accessor_format')
        vi = a.get('bufferView')
        require(type(vi) is int and 0 <= vi < len(d['bufferViews']), 'view_index')
        view = d['bufferViews'][vi]
        require(isinstance(view, dict) and view.get('buffer', 0) == 0 and 'extensions' not in view, 'view_unsupported')
        count, start, length, local = a.get('count'), view.get('byteOffset', 0), view.get('byteLength'), a.get('byteOffset', 0)
        require(all(type(x) is int and x >= 0 for x in (count, start, length, local)) and 0 < count <= 1000000, 'accessor_range')
        fmt, unit = formats[ct]; width = unit * sizes[kind]; stride = view.get('byteStride', width)
        require(type(stride) is int and stride >= width and stride % unit == 0 and local % unit == 0 and start % unit == 0, 'accessor_stride')
        require(start+length <= len(self.binary) and local+(count-1)*stride+width <= length, 'accessor_bounds')
        result = [struct.unpack_from('<'+fmt*sizes[kind], self.binary, start+local+i*stride) for i in range(count)]
        require(all(all(math.isfinite(v) for v in row) for row in result), 'nonfinite_geometry')
        return result
    def replace(self, index, values):
        d = self.document; a = d['accessors'][index]
        fmt = {5121:'B', 5123:'H', 5125:'I', 5126:'f'}[a['componentType']]
        self.binary.extend(b'\0' * (-len(self.binary) % 4)); offset = len(self.binary)
        for row in values: self.binary.extend(struct.pack('<'+fmt*len(row), *row))
        require(len(self.binary) <= MAX_OUTPUT, 'geometry_budget')
        d['bufferViews'].append({'buffer': 0, 'byteOffset': offset, 'byteLength': len(self.binary)-offset})
        a['bufferView'] = len(d['bufferViews'])-1; a.pop('byteOffset', None)
        if a['type'] == 'VEC3' and ('min' in a or 'max' in a):
            a['min'] = [min(v[i] for v in values) for i in range(3)]
            a['max'] = [max(v[i] for v in values) for i in range(3)]

def prepare(data, catalog_id, name):
    require(isinstance(catalog_id, str) and re.fullmatch(r'gran-turismo-4/[A-Za-z0-9_-]{1,80}', catalog_id), 'unsupported_catalog_id')
    require(isinstance(name, str) and 0 < len(name) <= 96 and all(32 <= ord(c) < 127 for c in name), 'invalid_name')
    d, binary = unpack(data)
    require(isinstance(d.get('extras'), dict) and isinstance(d['extras'].get('record'), dict), 'missing_gt4_metadata')
    require(d.get('extras', {}).get('source_profile') == 'gt4-ps2-static-car-v2', 'unsupported_profile')
    require(d['extras'].get('car') == catalog_id.split('/')[1], 'catalog_id_mismatch')
    require(not any(d.get(key) for key in ('animations', 'skins')) and not d.get('extensionsRequired'), 'unsupported_runtime_features')
    require(isinstance(d.get('buffers'), list) and len(d['buffers']) == 1 and isinstance(d['buffers'][0], dict) and 'uri' not in d['buffers'][0] and type(d['buffers'][0].get('byteLength')) is int and d['buffers'][0]['byteLength'] <= len(binary), 'unsupported_buffers')
    for key, cap in (('nodes',256), ('meshes',256), ('accessors',8192), ('bufferViews',8192), ('scenes',16)):
        require(isinstance(d.get(key), list) and 0 < len(d[key]) <= cap, 'unsupported_'+key)
    for image in d.get('images', []): require(isinstance(image, dict) and 'uri' not in image, 'external_image_unsupported')
    g = Geometry(d, binary)
    roles = {}
    geometry_vertices = 0
    geometry_indices = 0
    def role(index, kind):
        require(index not in roles or roles[index] == kind, 'accessor_role_alias')
        roles[index] = kind
    for mesh in d['meshes']:
        require(isinstance(mesh, dict) and not mesh.get('weights') and isinstance(mesh.get('primitives'), list) and 0 < len(mesh['primitives']) <= 4096, 'mesh_unsupported')
        for p in mesh['primitives']:
            require(isinstance(p, dict) and p.get('mode',4) == 4 and not p.get('targets') and set(p.get('extensions', {})) <= {'KHR_materials_variants'}, 'primitive_unsupported')
            attrs = p.get('attributes')
            require(isinstance(attrs, dict) and 'POSITION' in attrs and set(attrs) <= {'POSITION','NORMAL','TANGENT','TEXCOORD_0','TEXCOORD_1','COLOR_0'}, 'attributes_unsupported')
            positions = g.values(attrs['POSITION'], 'VEC3', {5126})
            geometry_vertices += len(positions)
            require(geometry_vertices <= 1000000, 'geometry_work_budget')
            for key, index in attrs.items():
                if key in ('POSITION','NORMAL','TANGENT'):
                    require(len(g.values(index, 'VEC4' if key == 'TANGENT' else 'VEC3', {5126})) == len(positions), 'attribute_count')
                    role(index, key)
                else:
                    role(index, 'UNCHANGED')
            index = p.get('indices')
            require(type(index) is int and 0 <= index < len(d['accessors']) and isinstance(d['accessors'][index], dict), 'index_accessor')
            index_count = d['accessors'][index].get('count')
            require(type(index_count) is int and index_count > 0, 'index_count')
            geometry_indices += index_count
            require(geometry_indices <= MAX_INDEX_WORK, 'geometry_index_work_budget')
            indices = g.values(index, 'SCALAR', {5121,5123,5125})
            require(len(indices) % 3 == 0 and all(row[0] < len(positions) for row in indices), 'triangle_indices')
            role(p['indices'], 'INDICES')
    for index, kind in roles.items():
        if kind == 'UNCHANGED': continue
        values = g.values(index)
        if kind == 'INDICES':
            for i in range(0,len(values),3): values[i+1],values[i+2] = values[i+2],values[i+1]
        else:
            values = [tuple(-v if axis == 2 or (kind == 'TANGENT' and axis == 3) else v for axis,v in enumerate(row)) for row in values]
        g.replace(index, values)
    for node in d['nodes']:
        require(isinstance(node, dict) and not any(k in node for k in ('matrix','rotation','skin','weights','extensions')), 'node_transform_unsupported')
        translation = finite_vector(node.get('translation',[0,0,0]),3)
        scale = finite_vector(node.get('scale',[1,1,1]),3)
        require(all(v != 0 for v in scale), 'zero_scale')
        if 'translation' in node: node['translation'] = [translation[0], translation[1], -translation[2]]
    scene = d.get('scene',0)
    require(type(scene) is int and 0 <= scene < len(d['scenes']), 'default_scene')
    # Validate all scene trees; shared instances are unsupported because one group index must have one world pose.
    poses = {}
    def traverse(index, parent_scale, parent_translation, visiting, output):
        require(len(visiting) < 63, 'scene_depth_unsupported')
        require(type(index) is int and 0 <= index < len(d['nodes']) and index not in visiting and index not in output, 'scene_graph_unsupported')
        node = d['nodes'][index]; local_scale=node.get('scale',[1,1,1]); local_translation=node.get('translation',[0,0,0])
        scale=[parent_scale[i]*local_scale[i] for i in range(3)]
        translation=[parent_translation[i]+parent_scale[i]*local_translation[i] for i in range(3)]
        require(all(math.isfinite(v) for v in scale+translation), 'world_transform_overflow')
        output[index]=(scale,translation)
        require(isinstance(node.get('children',[]),list), 'node_children')
        for child in node.get('children',[]): traverse(child,scale,translation,visiting|{index},output)
    all_scene_nodes=set()
    for scene_index, entry in enumerate(d['scenes']):
        require(isinstance(entry,dict) and isinstance(entry.get('nodes'),list), 'scene_nodes')
        output={}
        for index in entry['nodes']: traverse(index,[1,1,1],[0,0,0],set(),output)
        require(not all_scene_nodes.intersection(output), 'shared_nodes_across_scenes_unsupported')
        all_scene_nodes.update(output)
        if scene_index == scene: poses=output
    groups=[]; points={}; names={}; instanced_vertices=0; instanced_indices=0
    for index,(scale,translation) in poses.items():
        node=d['nodes'][index]
        if 'mesh' not in node: continue
        mesh_index=node['mesh']; require(type(mesh_index) is int and 0 <= mesh_index < len(d['meshes']), 'node_mesh')
        node_name=node.get('name')
        if node_name == 'body': wheel=-1
        else:
            parts=[(i,prefix+'_'+suffix) for i,suffix in enumerate(WHEELS) for prefix in ('wheel','tire')]
            matched=[i for i,value in parts if value == node_name]
            require(len(matched)==1, 'unknown_mesh_group')
            wheel=matched[0]
        require(node_name not in names, 'duplicate_mesh_group')
        names[node_name]=index; groups.append((index,wheel)); cloud=[]
        for p in d['meshes'][mesh_index]['primitives']:
            instanced_indices += d['accessors'][p['indices']]['count']
            require(instanced_indices <= MAX_INSTANCE_INDICES, 'instance_index_work_budget')
            positions = g.values(p['attributes']['POSITION'],'VEC3',{5126})
            instanced_vertices += len(positions)
            require(instanced_vertices <= 1000000, 'instance_work_budget')
            cloud.extend(tuple(row[i]*scale[i]+translation[i] for i in range(3)) for row in positions)
        require(bool(cloud) and all(all(math.isfinite(v) for v in row) for row in cloud), 'empty_or_nonfinite_mesh_group'); points[node_name]=cloud
    require(set(names) == {'body'} | {prefix+'_'+suffix for suffix in WHEELS for prefix in ('wheel','tire')}, 'incomplete_mesh_groups')
    body=points['body']; lower=[min(p[i] for p in body) for i in range(3)]; upper=[max(p[i] for p in body) for i in range(3)]
    source_wheels=d['extras']['record'].get('wheels')
    require(isinstance(source_wheels,list) and len(source_wheels)==4, 'wheel_metadata')
    source_by_name={w.get('name'):w for w in source_wheels if isinstance(w,dict)}
    require(set(source_by_name)==set(WHEELS), 'wheel_metadata')
    wheels=[]; differences=[]
    for i,suffix in enumerate(WHEELS):
        w=source_by_name[suffix]; centre=finite_vector(w.get('centre'),3); centre=[centre[0],centre[1],-centre[2]]
        radius,width=w.get('outer_radius'),w.get('width')
        require(all(type(v) in (int,float) and math.isfinite(v) and 0<v<2 for v in (radius,width)), 'wheel_dimensions')
        require((centre[0]<0 if i%2==0 else centre[0]>0) and (centre[2]>0 if i<2 else centre[2]<0), 'wheel_orientation')
        for prefix in ('wheel','tire'):
            _,origin=poses[names[prefix+'_'+suffix]]
            require(max(abs(origin[j]-centre[j]) for j in range(3))<1e-5, 'wheel_pose_metadata_mismatch')
        tire=points['tire_'+suffix]
        actual_radius=max(math.hypot(p[1]-centre[1],p[2]-centre[2]) for p in tire)
        actual_width=2*max(abs(p[0]-centre[0]) for p in tire)
        require(actual_radius>0 and actual_width>0 and actual_radius<2 and actual_width<2, 'wheel_geometry_bounds')
        assembly=tire+points['wheel_'+suffix]
        assembly_radius=max(math.hypot(p[1]-centre[1],p[2]-centre[2]) for p in assembly)
        assembly_width=2*max(abs(p[0]-centre[0]) for p in assembly)
        final_radius,final_width=max(radius,assembly_radius),max(width,assembly_width)
        require(final_radius < 2 and final_width < 2, 'wheel_assembly_bounds')
        wheels.append({'label':LABELS[i], 'center':centre, 'radius':final_radius, 'width':final_width})
        differences.append({'label':LABELS[i], 'source_radius':radius, 'tire_mesh_radius':actual_radius, 'assembly_radius':assembly_radius, 'chosen_radius':final_radius, 'source_width':width, 'tire_mesh_width':actual_width, 'assembly_width':assembly_width, 'chosen_width':final_width})
    lift=max(0,-lower[1], *(w['radius']-w['center'][1] for w in wheels))
    lower[1]+=lift;upper[1]+=lift
    for w in wheels: w['center'][1]+=lift
    for entry in d['scenes']:
        root=len(d['nodes']);d['nodes'].append({'name':'racer_ground_lift','translation':[0,lift,0],'children':entry['nodes'][:]});entry['nodes']=[root]
    require(all(lower[i] < upper[i] for i in range(3)) and lower[1] >= 0 and upper[0]-lower[0] <= 10 and upper[2]-lower[2] <= 30 and upper[1] <= 10, 'racer_body_geometry')
    require(all(lower[2] <= w['center'][2] <= upper[2] for w in wheels), 'racer_axle_body_length')
    wheelbase=(wheels[0]['center'][2]+wheels[1]['center'][2]-wheels[2]['center'][2]-wheels[3]['center'][2])/2
    require(.5 <= wheelbase <= 20, 'racer_wheelbase')
    for left in (0,2):
        a,b=wheels[left],wheels[left+1]
        require(abs(a['center'][2]-b['center'][2]) <= 1e-4 and abs(a['center'][1]-b['center'][1]) <= 1e-4 and abs(a['radius']-b['radius']) <= 1e-4, 'racer_axle_alignment')
    source_sha=hashlib.sha256(data).hexdigest()
    d['extras']['racerPreparation']={'schema':1,'source_sha256':source_sha,'catalog_id':catalog_id,'mirror_z':True,'ground_lift':lift,'completeness':'static-source-assembly; runtime parity unverified'}
    d['buffers'][0]['byteLength']=len(binary)
    prepared=pack(d,binary);digest=hashlib.sha256(prepared).hexdigest()
    number=lambda v: format(v,'.17g')
    lines=['RACER_VEHICLE 1','id '+json.dumps('vehicle-'+digest),'name '+json.dumps(name),'mesh '+json.dumps(digest+'.glb'),'sha256 '+digest,'source_sha256 '+source_sha,'body '+' '.join(number(v) for v in lower+upper)]
    lines += ['wheel '+w['label']+' '+' '.join(number(v) for v in w['center']+[w['radius'],w['width']]) for w in wheels]
    lines += ['groups '+str(len(groups))]+['group '+str(index)+' '+str(wheel) for index,wheel in sorted(groups)]
    descriptor='\n'.join(lines)+'\n'
    receipt={'schema':1,'catalog_id':catalog_id,'source_sha256':source_sha,'prepared_sha256':digest,'source_bytes':len(data),'prepared_bytes':len(prepared),'body':lower+upper,'wheels':wheels,'ground_lift':lift,'wheel_geometry':differences,'groups':sorted(groups),'source_claim_limits':copy.deepcopy(d['extras'].get('claim_limits',[])),'limitations':['Spec-database wheel placement is an interpretation, not original runtime parity.','Conservative tire cylinders may leave small ground gaps.','Materials and embedded image bytes retained; rendered equivalence unverified.']}
    return prepared,descriptor,receipt

def publish(source,catalog_id,name,output,minimum_free=20*1024**3):
    source,output=Path(source),Path(output)
    require(not source.is_symlink() and stat.S_ISREG(source.stat().st_mode),'source_nonregular')
    fd=os.open(source,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(fd,'rb') as stream:
        before=os.fstat(stream.fileno());data=stream.read(MAX_SOURCE+1);after=os.fstat(stream.fileno())
    require((before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns) and len(data)==before.st_size,'source_changed')
    prepared,descriptor,receipt=prepare(data,catalog_id,name)
    require(not output.exists() and not output.is_symlink(),'output_exists')
    require(not any(p.is_symlink() for p in (output,*output.parents)),'output_symlink')
    require(shutil.disk_usage(output.parent).free>=minimum_free,'free_space')
    output.mkdir(mode=0o700)
    digest=receipt['prepared_sha256']
    for filename,payload in ((digest+'.glb',prepared),(digest+'.vehicle',descriptor.encode()),(digest+'.json',(json.dumps(receipt,indent=2)+'\n').encode())):
        fd=os.open(output/filename,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'wb') as stream: stream.write(payload)
    return receipt

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',required=True,type=Path);p.add_argument('--id',required=True);p.add_argument('--name',required=True);p.add_argument('--output',required=True,type=Path)
    a=p.parse_args(argv)
    try: print(json.dumps(publish(a.source,a.id,a.name,a.output),indent=2));return 0
    except (OSError,ValueError,KeyError,TypeError,struct.error,OverflowError):
        print('GT4 preparation failed; source unsupported/invalid or storage unavailable; inspect any partial output directory',file=sys.stderr);return 2

if __name__=='__main__':sys.exit(main())
