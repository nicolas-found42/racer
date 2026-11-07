#!/usr/bin/env python3
"""Prepare the proven MCLA ambient350Z assembly; unsupported ownership fails explicitly."""
import argparse
from collections import Counter
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import stat
import sys

# Read-only shared GLB framing/accessor mechanics, not GT4 semantic preparation.
import prepare_gt4_vehicle as glb

PILOT_SHA = '0c65c56fe42205054e251b1569da22343fa314f69151fd798c0857e94fc83703'
PROOF_SHA = 'f3539aa8c1d2fc747071a6963dd9ffe636a6dddd88e4872e7a9a44a8b9319520'
NATIVE_SHA = 'b336bb0506f9bbbdfe7fdffea96f11f4c7132d9e17a7df6586cea31afa0f0d09'
WHEEL_BONES = (4,6,8,10)
LABELS = ('FL','FR','RL','RR')
BINDINGS = (4,4,6,6,8,8,10,10,0,0,0,0,30)

class PreparationError(ValueError): pass

def require(value, reason):
    if not value: raise PreparationError(reason)

def vector(value,size):
    require(isinstance(value,list) and len(value)==size and all(type(v) in (int,float) and math.isfinite(v) for v in value),'nonfinite_vector')
    return value

def prepare(data,catalog_id,name,proof_data,*,source_sha=PILOT_SHA,proof_sha=PROOF_SHA,meters_per_unit=1.0):
    require(hashlib.sha256(data).hexdigest()==source_sha,'unsupported_source_hash')
    require(len(proof_data)<=65536 and hashlib.sha256(proof_data).hexdigest()==proof_sha,'unsupported_native_proof')
    require(type(meters_per_unit) in (int,float) and math.isfinite(meters_per_unit) and .1<=meters_per_unit<=10,'import_scale')
    require(isinstance(catalog_id,str) and re.fullmatch(r'midnight-club-los-angeles/[A-Za-z0-9_-]{1,80}',catalog_id),'catalog_id')
    require(isinstance(name,str) and 0<len(name)<=96 and all(32<=ord(c)<127 for c in name),'name')
    authority='hash-pinned ambient350Z and independently decoded native proof' if source_sha==PILOT_SHA and proof_sha==PROOF_SHA else 'caller-supplied fixture pins; canonical native-asset authority unestablished'
    proof=json.loads(proof_data);d,binary=glb.unpack(data)
    require(isinstance(proof,dict) and proof.get('native_sha256')==NATIVE_SHA and proof.get('model_bindings')==list(BINDINGS),'native_binding_proof')
    skeleton=proof.get('skeleton');properties=proof.get('model_properties')
    require(isinstance(skeleton,list) and 31<=len(skeleton)<=128 and all(isinstance(b,dict) and b.get('index')==i for i,b in enumerate(skeleton)),'native_skeleton')
    require(isinstance(properties,list) and len(properties)==13 and all(isinstance(p,dict) and p.get('model')==i and p.get('skinned') is False for i,p in enumerate(properties)),'native_skinning_unsupported')
    for i,bone in enumerate(WHEEL_BONES):
        row=skeleton[bone]
        require(row.get('name')=='whl_'+str(i) and row.get('parent')==bone-1 and skeleton[bone-1].get('name')=='axl_'+str(i),'native_wheel_identity')
        for field in ('euler','orient'):require(vector(row.get(field),3)==[0,0,0],'native_wheel_rotation_unsupported')
    extras=d.get('extras')
    require(isinstance(extras,dict) and extras.get('profile')=='mcla-xbox360-static-stock-v3' and extras.get('vehicle')==catalog_id.split('/')[1],'source_profile')
    require(not extras.get('wheels') and not extras.get('omitted'),'shared_or_partial_assembly_unsupported')
    parts=extras.get('parts');sources=extras.get('sources')
    require(isinstance(parts,list) and len(parts)==1 and parts[0].get('slot')=='body' and parts[0].get('resource_frame')=='native','native_body_frame')
    require(isinstance(sources,list) and any(isinstance(s,dict) and s.get('file')==parts[0].get('file') and s.get('sha256')==NATIVE_SHA for s in sources),'native_source_join')
    require(not d.get('skins') and not d.get('animations') and not d.get('extensionsRequired'),'runtime_features_unsupported')
    require(isinstance(d.get('buffers'),list) and len(d['buffers'])==1 and isinstance(d['buffers'][0],dict) and 'uri' not in d['buffers'][0] and type(d['buffers'][0].get('byteLength')) is int and d['buffers'][0]['byteLength']<=len(binary),'buffers_unsupported')
    require(isinstance(d.get('nodes'),list) and len(d['nodes'])==13 and d.get('scene',0)==0 and isinstance(d.get('scenes'),list) and len(d['scenes'])==1 and sorted(d['scenes'][0].get('nodes',[]))==list(range(13)),'flat_scene_unsupported')
    for key,limit in (('meshes',256),('accessors',8192),('bufferViews',8192)):
        require(isinstance(d.get(key),list) and 0<len(d[key])<=limit,'structure_unsupported')
    for image in d.get('images',[]):require(isinstance(image,dict) and 'uri' not in image,'external_image')
    g=glb.Geometry(d,binary);roles={};work_vertices=work_indices=0
    def role(index,kind):
        require(type(index) is int and 0<=index<len(d['accessors']) and (index not in roles or roles[index]==kind),'accessor_alias')
        roles[index]=kind
    for mesh in d['meshes']:
        require(isinstance(mesh,dict) and not mesh.get('weights') and isinstance(mesh.get('primitives'),list) and 0<len(mesh['primitives'])<=4096,'mesh_unsupported')
        for p in mesh['primitives']:
            require(isinstance(p,dict) and p.get('mode',4)==4 and not p.get('targets') and set(p.get('extensions',{}))<={'KHR_materials_variants'},'primitive_unsupported')
            attrs=p.get('attributes');require(isinstance(attrs,dict) and 'POSITION' in attrs and set(attrs)<={'POSITION','NORMAL','TANGENT','TEXCOORD_0','TEXCOORD_1','COLOR_0'},'vertex_features_unsupported')
            positions=g.values(attrs['POSITION'],'VEC3',{5126});work_vertices+=len(positions)
            require(work_vertices<=1000000,'vertex_work_budget')
            for attribute,index in attrs.items():
                kind=attribute if attribute in ('POSITION','NORMAL','TANGENT') else 'UNCHANGED'
                role(index,kind)
                if kind!='UNCHANGED':require(len(g.values(index,'VEC4' if kind=='TANGENT' else 'VEC3',{5126}))==len(positions),'vertex_count')
            index=p.get('indices');role(index,'INDICES');accessor=d['accessors'][index]
            require(isinstance(accessor,dict) and type(accessor.get('count')) is int and accessor['count']>0,'index_count')
            work_indices+=accessor['count'];require(work_indices<=3000000,'index_work_budget')
            indices=g.values(index,'SCALAR',{5121,5123,5125})
            require(len(indices)%3==0 and all(row[0]<len(positions) for row in indices),'indices')
    for index,kind in roles.items():
        if kind=='UNCHANGED':continue
        values=g.values(index)
        if kind=='INDICES':
            for i in range(0,len(values),3):values[i+1],values[i+2]=values[i+2],values[i+1]
        else:
            values=[tuple((-v if axis==2 or (kind=='TANGENT' and axis==3) else v)*(meters_per_unit if kind=='POSITION' else 1) for axis,v in enumerate(row)) for row in values]
        g.replace(index,values)
    groups=[];clouds={-1:[],0:[],1:[],2:[],3:[]};centres={};seen_models=set();expanded=vertices=0
    for node_index,node in enumerate(d['nodes']):
        require(isinstance(node,dict) and not any(k in node for k in ('translation','rotation','scale','children','skin','weights','extensions')),'node_transform_unsupported')
        matrix=vector(node.get('matrix'),16)
        require(all(abs(matrix[i]-(1 if i in (0,5,10,15) else 0))<1e-7 for i in range(16) if i not in (12,13,14)),'nontranslation_matrix_unsupported')
        info=node.get('extras');require(isinstance(info,dict),'node_provenance')
        model,bone=info.get('nativeModel'),info.get('nativeBoneIndex')
        require(type(model) is int and 0<=model<13 and model not in seen_models and bone==BINDINGS[model],'native_model_binding')
        seen_models.add(model);wheel=WHEEL_BONES.index(bone) if bone in WHEEL_BONES else -1
        native_center=vector(skeleton[bone].get('model'),3)
        require(max(abs(matrix[12+i]-native_center[i]) for i in range(3))<=1e-5,'native_pose_mismatch')
        translation=[matrix[12]*meters_per_unit,matrix[13]*meters_per_unit,-matrix[14]*meters_per_unit]
        node['matrix']=matrix[:];node['matrix'][12:15]=translation
        if wheel>=0:centres[wheel]=translation
        mesh=node.get('mesh');require(type(mesh) is int and 0<=mesh<len(d['meshes']),'mesh_index')
        groups.append((node_index,wheel))
        for p in d['meshes'][mesh]['primitives']:
            expanded+=d['accessors'][p['indices']]['count'];require(expanded<=1500000,'expanded_index_budget')
            points=g.values(p['attributes']['POSITION'],'VEC3',{5126});vertices+=len(points);require(vertices<=1000000,'instance_vertex_budget')
            clouds[wheel].extend(tuple(p[i]+translation[i] for i in range(3)) for p in points)
    require(Counter(w for _,w in groups)==Counter({-1:5,0:2,1:2,2:2,3:2}) and all(clouds.values()),'complete_group_coverage')
    body=clouds[-1];lower=[min(p[i] for p in body) for i in range(3)];upper=[max(p[i] for p in body) for i in range(3)]
    wheels=[];native_geometry=[]
    for i in range(4):
        center=centres[i];radius=max(math.hypot(p[1]-center[1],p[2]-center[2]) for p in clouds[i]);width=2*max(abs(p[0]-center[0]) for p in clouds[i])
        require(0<radius<2 and 0<width<2 and (center[0]<0 if i%2==0 else center[0]>0) and (center[2]>0 if i<2 else center[2]<0),'wheel_geometry')
        wheels.append({'label':LABELS[i],'center':center[:],'radius':radius,'width':width})
        native_geometry.append({'label':LABELS[i],'native_bone_index':WHEEL_BONES[i],'native_bone_name':skeleton[WHEEL_BONES[i]]['name'],'native_pivot':skeleton[WHEEL_BONES[i]]['model'],'geometry_radius_native_units':radius/meters_per_unit,'geometry_width_native_units':width/meters_per_unit})
    # Tiny native left/right differences remain in geometry; common axle collision radius encloses both.
    for left in (0,2):
        radius=max(wheels[left]['radius'],wheels[left+1]['radius'])
        wheels[left]['radius']=wheels[left+1]['radius']=radius
    lift=max(0,-lower[1],*(w['radius']-w['center'][1] for w in wheels))
    lower[1]+=lift;upper[1]+=lift
    for w in wheels:w['center'][1]+=lift
    require(all(math.isfinite(v) for v in lower+upper) and all(lower[i]<upper[i] for i in range(3)) and lower[1]>=0 and upper[0]-lower[0]<=10 and upper[2]-lower[2]<=30 and upper[1]<=10,'racer_body_geometry')
    require(all(lower[2]<=w['center'][2]<=upper[2] for w in wheels),'racer_axle_containment')
    wheelbase=(wheels[0]['center'][2]+wheels[1]['center'][2]-wheels[2]['center'][2]-wheels[3]['center'][2])/2
    require(.5<=wheelbase<=20,'racer_wheelbase')
    for left in (0,2):require(abs(wheels[left]['center'][1]-wheels[left+1]['center'][1])<=1e-4 and abs(wheels[left]['center'][2]-wheels[left+1]['center'][2])<=1e-4,'racer_axle_alignment')
    d['nodes'].append({'name':'racer_ground_lift','translation':[0,lift,0],'children':list(range(13))});d['scenes'][0]['nodes']=[13]
    extras['racerPreparation']={'schema':1,'role':'traffic','runtime_player_eligible':False,'authority':authority,'source_sha256':source_sha,'native_proof_sha256':proof_sha,'mirror_z':True,'meters_per_native_unit':meters_per_unit,'ground_lift':lift,'ownership':'native LOD model bindings to named wheel bones; static unskinned models'}
    d['buffers'][0]['byteLength']=len(binary);prepared=glb.pack(d,binary);digest=hashlib.sha256(prepared).hexdigest();number=lambda x:format(x,'.17g')
    lines=['RACER_VEHICLE 1','id '+json.dumps('vehicle-'+digest),'name '+json.dumps(name),'mesh '+json.dumps(digest+'.glb'),'sha256 '+digest,'source_sha256 '+source_sha,'body '+' '.join(map(number,lower+upper))]
    lines+=['wheel '+w['label']+' '+' '.join(map(number,w['center']+[w['radius'],w['width']])) for w in wheels]
    lines+=['groups '+str(len(groups))]+['group '+str(index)+' '+str(wheel) for index,wheel in groups]
    native_body_bounds=[lower[0]/meters_per_unit,(lower[1]-lift)/meters_per_unit,lower[2]/meters_per_unit,upper[0]/meters_per_unit,(upper[1]-lift)/meters_per_unit,upper[2]/meters_per_unit]
    receipt={'schema':1,'role':'traffic','runtime_player_eligible':False,'authority':authority,'catalog_id':catalog_id,'source_sha256':source_sha,'prepared_sha256':digest,'native_resource_sha256':NATIVE_SHA,'native_proof_sha256':proof_sha,'source_bytes':len(data),'prepared_bytes':len(prepared),'source_facts':{'bone_geometry':native_geometry,'wheelbase_native_units':wheelbase/meters_per_unit,'front_track_native_units':(centres[1][0]-centres[0][0])/meters_per_unit,'rear_track_native_units':(centres[3][0]-centres[2][0])/meters_per_unit,'body_bounds_native_after_axis_mirror':native_body_bounds,'source_axes':'native Y-up, -Z nose, +X right; pinned exporter claim','native_model_bindings':list(BINDINGS)},'normalization':{'meters_per_native_unit':meters_per_unit,'units_authority':'explicit import assumption; native metre label not established','mirror_z':True,'ground_lift_m':lift,'axle_collision_radius':'maximum actual radial geometry distance of each wheel pair'},'body':lower+upper,'wheels':wheels,'groups':groups,'source_claim_limits':extras.get('claim_limits',[]),'limitations':['Only the hash-pinned ambient350Z/native-proof assembly is supported by default.','Native wheel pivots and rigid ownership are statically proven; runtime animation and tire deformation are unverified.','Cylinders measure native wheel geometry, not a decoded tire-size specification.','No dimensions or scale inferred from screenshots; physical-unit mapping is an explicit import assumption.','Source diffuse/material data retained; renderer and original shader parity unverified.']}
    return prepared,'\n'.join(lines)+'\n',receipt

def read_regular(path,limit):
    path=Path(path);require(not any(p.is_symlink() for p in (path,*path.parents)),'symlink_input')
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(fd,'rb') as stream:
        before=os.fstat(stream.fileno());require(stat.S_ISREG(before.st_mode),'nonregular_input');data=stream.read(limit+1);after=os.fstat(stream.fileno())
    require(len(data)<=limit and len(data)==before.st_size and (before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns),'input_size_or_change')
    return data

def publish(source,catalog_id,name,proof,output,meters_per_unit=1.0,minimum_free=20*1024**3):
    data=read_regular(source,glb.MAX_SOURCE);proof_data=read_regular(proof,65536)
    prepared,descriptor,receipt=prepare(data,catalog_id,name,proof_data,meters_per_unit=meters_per_unit)
    output=Path(output);require(not output.exists() and not output.is_symlink() and not any(p.is_symlink() for p in output.parents),'output_exists_or_symlink')
    require(shutil.disk_usage(output.parent).free>=minimum_free,'free_space');output.mkdir(mode=0o700)
    digest=receipt['prepared_sha256']
    for filename,payload in ((digest+'.glb',prepared),(digest+'.vehicle',descriptor.encode()),(digest+'.json',(json.dumps(receipt,indent=2)+'\n').encode())):
        fd=os.open(output/filename,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'wb') as stream:stream.write(payload)
    return receipt

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for flag in ('source','native-proof','output'):p.add_argument('--'+flag,required=True,type=Path)
    p.add_argument('--id',required=True);p.add_argument('--name',required=True);p.add_argument('--meters-per-unit',type=float,default=1.0,help='Explicit import assumption; native metre label unverified')
    a=p.parse_args(argv)
    try:print(json.dumps(publish(a.source,a.id,a.name,a.native_proof,a.output,a.meters_per_unit),indent=2));return 0
    except (PreparationError,glb.PreparationError) as error:
        code=str(error) if re.fullmatch('[a-z0-9_]{1,80}',str(error)) else 'invalid_input'
        print('MCLA preparation failed: '+code+'; inspect any partial output',file=sys.stderr);return 2
    except (OSError,ValueError,TypeError,KeyError,OverflowError):
        print('MCLA preparation failed: invalid_input_or_storage; inspect any partial output',file=sys.stderr);return 2

if __name__=='__main__':sys.exit(main())
