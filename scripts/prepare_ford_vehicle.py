#!/usr/bin/env python3
"""Prepare a source-named Ford Racing2 low-speed assembly for Racer (not runtime parity)."""
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
import sys
from prepare_gt4_vehicle import Geometry, PreparationError, finite_vector, pack, require, unpack

WHEELS = ('FRONT_LEFT', 'FRONT_RIGHT', 'BACK_LEFT', 'BACK_RIGHT')
LABELS = ('FL', 'FR', 'RL', 'RR')
MAX_SOURCE = 16 * 1024**2
MAX_INDICES = 1500000
MAX_VERTICES = 1000000


def source_physics(directory, catalog_id):
    """Read only the three named, bounded, verbatim source config blocks."""
    directory = Path(directory)
    require(not any(p.is_symlink() for p in (directory, *directory.parents)), 'physics_symlink')
    fields, provenance = {}, []
    for name in ('cardata.txt', 'tyres_front.txt', 'tyres_back.txt'):
        path = directory / name
        require(not path.is_symlink() and path.is_file() and path.stat().st_size <= 32768, 'physics_file')
        raw = path.read_bytes(); require(len(raw) <= 32768, 'physics_budget')
        table = {}
        wanted = {'CAR_TYPE','CAR_MODEL_YEAR','CAR_FRONT_TYRE_TYPE','CAR_BACK_TYRE_TYPE','INGAME_TEXT_ENUM'} if name == 'cardata.txt' else {'TYPE','RADIUS','WIDTH'}
        for number, line in enumerate(raw.decode('utf8').splitlines(), 1):
            tokens = line.split('//',1)[0].split()
            if not tokens or not tokens[0].startswith(':') or tokens[0][1:] not in wanted: continue
            key = tokens[0][1:]; require(key not in table and len(tokens) == 2, 'physics_field')
            table[key] = {'value':tokens[1], 'line':number}
        fields[name] = table
        provenance.append({'file':name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
    card = fields['cardata.txt']
    require(card.get('CAR_TYPE',{}).get('value') == catalog_id.split('/')[-1], 'physics_car_mismatch')
    result = {'files':provenance,'fields':fields,'year':int(card['CAR_MODEL_YEAR']['value']), 'axles':[]}
    for name, key in (('tyres_front.txt','CAR_FRONT_TYRE_TYPE'),('tyres_back.txt','CAR_BACK_TYRE_TYPE')):
        table = fields[name]
        require(table.get('TYPE',{}).get('value') == card.get(key,{}).get('value'), 'physics_tire_mismatch')
        radius, width = float(table['RADIUS']['value']), float(table['WIDTH']['value'])
        require(all(math.isfinite(v) and 0 < v < 2 for v in (radius,width)), 'physics_dimensions')
        result['axles'].append({'radius':radius,'width':width,'type':table['TYPE']['value']})
    return result


def prepare(data, catalog_id, name, physics=None):
    require(isinstance(catalog_id,str) and re.fullmatch(r'ford-racing-2/[A-Z0-9_]{1,64}',catalog_id), 'catalog_id')
    require(isinstance(name,str) and 0 < len(name) <= 96 and all(32 <= ord(c) < 127 for c in name), 'name')
    d, binary = unpack(data)
    extras = d.get('extras')
    require(isinstance(extras,dict) and extras.get('car') == catalog_id.split('/')[1], 'car_metadata')
    require(isinstance(extras.get('originalModelSha256'),str) and re.fullmatch('[0-9a-f]{64}',extras['originalModelSha256']), 'original_identity')
    require(not any(d.get(key) for key in ('animations','skins','extensionsRequired')), 'runtime_features')
    # Reserve the generated ground-lift root within the runtime's 4096-node cap.
    for key, cap in (('nodes',4095),('meshes',4096),('scenes',64),('accessors',8192),('bufferViews',8192)):
        require(isinstance(d.get(key),list) and 0 < len(d[key]) <= cap, 'structure_'+key)
    require(len(d.get('buffers',[])) == 1 and 'uri' not in d['buffers'][0] and d['buffers'][0].get('byteLength',len(binary)) <= len(binary), 'buffers')
    for image in d.get('images',[]): require(isinstance(image,dict) and 'uri' not in image, 'external_image')
    candidates = [(i,s) for i,s in enumerate(d['scenes']) if isinstance(s,dict) and s.get('extras',{}).get('sourceTree') == 0 and s.get('extras',{}).get('visibilityPreset') == 'low_speed']
    require(len(candidates) == 1, 'explicit_low_speed_scene')
    source_scene, scene = candidates[0]
    state = scene['extras'].get('stateInputs',{})
    require(state.get('wheelStaticBit') is True and state.get('wheelMovingBit') is False and state.get('wheelGlobalOverride') == 0 and state.get('brakeLightsOn') is False and state.get('reverseLightsOn') is False and state.get('exhaustOn') is False and state.get('transforms') == 'original serialized values', 'source_state_inputs')
    require(isinstance(scene.get('nodes'),list) and len(scene['nodes']) == 1, 'source_root')
    g = Geometry(d,binary)
    poses, roles, hubs, wheel_meshes = {}, {}, {}, {}
    index_work = vertex_work = 0
    def traverse(index, scale, translation, wheel, visiting):
        nonlocal index_work, vertex_work
        require(len(visiting) < 63 and type(index) is int and 0 <= index < len(d['nodes']) and index not in visiting and index not in poses, 'source_graph')
        node = d['nodes'][index]
        require(isinstance(node,dict) and not any(k in node for k in ('matrix','rotation','skin','weights','extensions')), 'node_transform')
        ns = finite_vector(node.get('scale',[1,1,1]),3); nt = finite_vector(node.get('translation',[0,0,0]),3)
        require(all(x != 0 for x in ns), 'zero_scale')
        world_scale = [scale[i]*ns[i] for i in range(3)]
        world_translation = [translation[i]+scale[i]*nt[i] for i in range(3)]
        require(all(math.isfinite(x) for x in world_scale+world_translation), 'world_overflow')
        meta = node.get('extras',{}); require(isinstance(meta,dict) and meta.get('visibilityPreset') == 'low_speed', 'node_state_metadata')
        names = meta.get('sourceNames',[])
        require(isinstance(names,list) and len(names)<=32 and all(isinstance(x,str) and len(x)<128 for x in names), 'source_names')
        hub = [i for i,suffix in enumerate(WHEELS) if 'HUB_'+suffix in names]
        rotating = [i for i,suffix in enumerate(WHEELS) if 'WHEEL_'+suffix in names]
        require(len(hub) <= 1 and len(rotating) <= 1, 'ambiguous_wheel_names')
        if hub:
            require(wheel < 0 and hub[0] not in hubs and 'mesh' not in node, 'hub_ownership')
            wheel = hub[0]; hubs[wheel] = (index, world_translation)
        if rotating: require(wheel == rotating[0], 'wheel_owner')
        poses[index] = (world_scale,world_translation)
        if 'mesh' in node:
            if wheel >= 0:
                require(rotating == [wheel], 'wheel_mesh_name')
                wheel_meshes.setdefault(wheel,[]).append(index)
            else:
                require(not any('_ON' in value for value in names), 'light_state_conflict')
            roles[index] = wheel
            mesh = node['mesh']; require(type(mesh) is int and 0 <= mesh < len(d['meshes']), 'mesh_index')
            primitives = d['meshes'][mesh].get('primitives')
            require(isinstance(primitives,list) and 0 < len(primitives) <= 4096, 'mesh_primitives')
            for p in primitives:
                require(isinstance(p,dict) and p.get('mode',4) == 4 and not p.get('targets') and not p.get('extensions'), 'primitive')
                attrs = p.get('attributes'); require(isinstance(attrs,dict) and 'POSITION' in attrs and set(attrs) <= {'POSITION','NORMAL','TEXCOORD_0','TEXCOORD_1','COLOR_0','TANGENT'}, 'attributes')
                ai = p.get('indices'); require(type(ai) is int and 0 <= ai < len(d['accessors']), 'indices')
                count = d['accessors'][ai].get('count'); require(type(count) is int and count > 0, 'index_count')
                index_work += count; require(index_work <= MAX_INDICES, 'index_budget')
                pi = attrs['POSITION']; require(type(pi) is int and 0 <= pi < len(d['accessors']), 'positions')
                count = d['accessors'][pi].get('count'); require(type(count) is int and count > 0, 'position_count')
                vertex_work += count; require(vertex_work <= MAX_VERTICES, 'vertex_budget')
                points = g.values(pi,'VEC3',{5126}); indices=g.values(ai,'SCALAR',{5121,5123,5125})
                require(len(indices)%3 == 0 and all(v[0] < len(points) for v in indices), 'triangle_indices')
        children = node.get('children',[]); require(isinstance(children,list),'children')
        for child in children: traverse(child,world_scale,world_translation,wheel,visiting|{index})
    def cloud(index):
        scale,translation=poses[index];result=[]
        for p in d['meshes'][d['nodes'][index]['mesh']]['primitives']:
            result += [tuple(point[i]*scale[i]+translation[i] for i in range(3)) for point in g.values(p['attributes']['POSITION'],'VEC3',{5126})]
        return result
    traverse(scene['nodes'][0],[1,1,1],[0,0,0],-1,set())
    require(set(hubs) == set(range(4)) and set(wheel_meshes) == set(range(4)) and any(w < 0 for w in roles.values()), 'complete_source_assembly')
    original = {}
    for wheel in range(4):
        pivot=hubs[wheel][1];points=[p for index in wheel_meshes[wheel] for p in cloud(index)]
        original[wheel]={'radius':max(math.hypot(p[1]-pivot[1],p[2]-pivot[2]) for p in points),'width':2*max(abs(p[0]-pivot[0]) for p in points)}
        require(0 < original[wheel]['radius'] < 2 and 0 < original[wheel]['width'] < 2, 'source_wheel_dimensions')
    fitting=[]
    if physics is not None:
        require(isinstance(physics,dict) and isinstance(physics.get('axles'),list) and len(physics['axles']) == 2, 'physics_shape')
        for wheel in range(4):
            target=physics['axles'][wheel//2]['radius'];require(type(target) in (int,float) and math.isfinite(target) and 0 < target < 2,'physics_radius')
            factor=target/original[wheel]['radius'];require(.5 <= factor <= 2,'wheel_fit_scale')
            index=hubs[wheel][0];node=d['nodes'][index];scale=node.get('scale',[1,1,1]);node['scale']=[scale[0],scale[1]*factor,scale[2]*factor]
            fitting.append({'wheel':LABELS[wheel],'source_radius':original[wheel]['radius'],'configured_radius':target,'radial_yz_scale':factor,'source_width':original[wheel]['width'],'configured_tire_width':physics['axles'][wheel//2]['width'],'lateral_scale':1})
        # Refresh poses after deliberate wheel-only radial scaling. Ownership remains unchanged.
        poses.clear();roles.clear();hubs.clear();wheel_meshes.clear();index_work=vertex_work=0
        traverse(scene['nodes'][0],[1,1,1],[0,0,0],-1,set())
    points={i:cloud(i) for i in roles}
    body=[p for i,ps in points.items() if roles[i]<0 for p in ps]
    lower=[min(p[i] for p in body) for i in range(3)];upper=[max(p[i] for p in body) for i in range(3)]
    wheels=[]
    for i in range(4):
        center=hubs[i][1][:];ps=[p for node in wheel_meshes[i] for p in points[node]]
        wheels.append({'label':LABELS[i],'center':center,'radius':max(math.hypot(p[1]-center[1],p[2]-center[2]) for p in ps),'width':2*max(abs(p[0]-center[0]) for p in ps)})
    for left in (0,2):
        radius=max(wheels[left]['radius'],wheels[left+1]['radius']);width=max(wheels[left]['width'],wheels[left+1]['width'])
        for i in (left,left+1):wheels[i]['radius']=radius;wheels[i]['width']=width
    source_body=lower+upper
    lift=max(0,-lower[1],*(w['radius']-w['center'][1] for w in wheels))
    lower[1]+=lift;upper[1]+=lift
    for w in wheels:w['center'][1]+=lift
    require(all(lower[i]<upper[i] for i in range(3)) and lower[1]>=0 and upper[0]-lower[0]<=10 and upper[2]-lower[2]<=30 and upper[1]<=10,'body_bounds')
    require(all(lower[2]<=w['center'][2]<=upper[2] for w in wheels),'axles_within_body')
    for i,w in enumerate(wheels):require(w['center'][0]<0 if i%2==0 else w['center'][0]>0,'wheel_side')
    wheelbase=(wheels[0]['center'][2]+wheels[1]['center'][2]-wheels[2]['center'][2]-wheels[3]['center'][2])/2
    require(.5<=wheelbase<=20,'wheelbase')
    for left in (0,2):
        a,b=wheels[left:left+2];require(abs(a['center'][1]-b['center'][1])<=1e-4 and abs(a['center'][2]-b['center'][2])<=1e-4 and abs(a['radius']-b['radius'])<=1e-4,'axle_alignment')
    root=len(d['nodes']);d['nodes'].append({'name':'racer_ground_lift','translation':[0,lift,0],'children':scene['nodes'][:]})
    d['scene']=0;d['scenes']=[{'name':'Racer source-derived low-speed Ford assembly','nodes':[root]}]
    source_sha=hashlib.sha256(data).hexdigest()
    d['extras']['racerPreparation']={'schema':1,'source_sha256':source_sha,'catalog_id':catalog_id,'source_scene':source_scene,'source_state':copy.deepcopy(scene.get('extras')),'axis_conversion':'identity; named front +Z and named right +X','meters_per_export_unit':1,'ground_lift':lift,'wheel_radius_fit':bool(physics),'limits':'Source-derived assembly state, not original runtime/render parity.'}
    d['buffers'][0]['byteLength']=len(binary);prepared=pack(d,binary);digest=hashlib.sha256(prepared).hexdigest()
    number=lambda v:format(v,'.17g')
    lines=['RACER_VEHICLE 1','id '+json.dumps('vehicle-'+digest),'name '+json.dumps(name),'mesh '+json.dumps(digest+'.glb'),'sha256 '+digest,'source_sha256 '+source_sha,'body '+' '.join(number(v) for v in lower+upper)]
    lines += ['wheel '+w['label']+' '+' '.join(number(v) for v in w['center']+[w['radius'],w['width']]) for w in wheels]
    lines += ['groups '+str(len(roles))]+['group '+str(i)+' '+str(w) for i,w in sorted(roles.items())]
    receipt={'schema':1,'catalog_id':catalog_id,'source_sha256':source_sha,'prepared_sha256':digest,'source_bytes':len(data),'prepared_bytes':len(prepared),'body':lower+upper,'wheels':wheels,'groups':sorted(roles.items()),'source_scene':source_scene,'ground_lift':lift,'wheelbase':wheelbase,'source_hubs':{LABELS[i]:hubs[i][1] for i in range(4)},'source_body_bounds':source_body,'source_wheel_geometry':original,'source_physics':physics,'wheel_radius_fitting':fitting,'rest_ground_clearance':{w['label']:w['center'][1]-w['radius'] for w in wheels},'source_limits':extras.get('limits',[]),'units':{'export_units_per_meter':1,'authority':'Explicit Racer conversion; source front radius ~0.3125 agrees with source-config radius0.312. Original-game unit naming not independently recovered.'},'limitations':['Source-derived low-speed/static wheel state; original runtime transforms and LOD selection unverified.','Original normal/UV/texture/ADC interpretation and GS shading limits remain.','Source tire width is not imposed on complete wheel width; original lateral scale is retained.','Conservative cylinder dimensions and uniform ground lift can leave small ground gaps.']}
    return prepared,'\n'.join(lines)+'\n',receipt


def publish(source,catalog_id,name,output,physics=None,minimum_free=20*1024**3):
    source,output=Path(source),Path(output)
    require(not source.is_symlink() and stat.S_ISREG(source.stat().st_mode),'source_nonregular')
    fd=os.open(source,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(fd,'rb') as stream:
        before=os.fstat(stream.fileno());data=stream.read(MAX_SOURCE+1);after=os.fstat(stream.fileno())
    require((before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns) and len(data)==before.st_size,'source_changed')
    prepared,descriptor,receipt=prepare(data,catalog_id,name,physics)
    require(not output.exists() and not output.is_symlink() and not any(p.is_symlink() for p in (output,*output.parents)),'output_exists_or_symlink')
    require(shutil.disk_usage(output.parent).free>=minimum_free,'free_space')
    output.mkdir(mode=0o700)
    digest=receipt['prepared_sha256']
    for filename,payload in ((digest+'.glb',prepared),(digest+'.vehicle',descriptor.encode()),(digest+'.json',(json.dumps(receipt,indent=2)+'\n').encode())):
        fd=os.open(output/filename,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'wb') as stream:stream.write(payload)
    return receipt


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',required=True,type=Path);p.add_argument('--id',required=True);p.add_argument('--name',required=True);p.add_argument('--output',required=True,type=Path);p.add_argument('--source-config',type=Path)
    a=p.parse_args(argv)
    try:
        physics=source_physics(a.source_config,a.id) if a.source_config else None
        print(json.dumps(publish(a.source,a.id,a.name,a.output,physics),indent=2));return 0
    except (OSError,ValueError,KeyError,TypeError,IndexError,OverflowError):
        print('Ford preparation failed; source unsupported/invalid or storage unavailable; inspect partial output if any',file=sys.stderr);return 2
if __name__=='__main__':sys.exit(main())
