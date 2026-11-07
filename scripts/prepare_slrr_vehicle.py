#!/usr/bin/env python3
"""Preserve the source-backed static Furrano assembly as a grouped runtime candidate."""
import argparse
import base64
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

import prepare_gt4_vehicle as glb
from slrr_vehicle import multiply, pose

SOURCE_SHA='64b977dab3ab894e523406b4e6af13ee51677af366bef326370a8baba4f98b7c'
REPORT_SHA='f7ebdde3cc18b34a2559113397066832b8740d63d927df68df3d61d2436d940f'
CFG_SHA='b0074215c7de997983ec52d6cee5b6fadb8c4634e242e8d2280027292960a6a2'
LABELS=('FL','FR','RL','RR')

class PreparationError(ValueError):pass

def require(value,code):
    if not value:raise PreparationError(code)

def vector(value,length):
    require(isinstance(value,list) and len(value)==length and all(type(v) in (float,int) and math.isfinite(v) for v in value),'nonfinite_vector')
    return value

def wheel_frames(cfg):
    """The native CFG labels each wheel section; no silhouette-based ownership inference."""
    current=None;frames={}
    for raw in cfg.decode('cp1252').splitlines():
        line=raw.strip();match=re.fullmatch(r'#\s*(FL|FR|RL|RR)\s+wheel\s*#',line)
        if match:current=match.group(1)
        tokens=line.split(';')[0].split()
        if tokens and tokens[0]=='wheel':
            require(current is not None and current not in frames and len(tokens)>=7,'cfg_wheel_identity')
            values=[float(v) for v in tokens[1:7]];vector(values,6);frames[current]=values
            current=None
    require(set(frames)==set(LABELS),'cfg_wheel_coverage')
    return frames

def embedded(uri,mime,limit):
    require(isinstance(uri,str) and uri.startswith('data:'+mime+';base64,'),'external_or_unsupported_uri')
    try:data=base64.b64decode(uri.split(',',1)[1],validate=True)
    except ValueError:raise PreparationError('invalid_base64')
    require(0<len(data)<=limit,'embedded_budget')
    return data

def combine(document):
    """Retain every original buffer/image byte while merging into one GLB binary segment."""
    buffers=document.get('buffers');require(isinstance(buffers,list) and 0<len(buffers)<=256,'buffer_count')
    binary=bytearray();starts=[];source_buffers=[]
    for entry in buffers:
        require(isinstance(entry,dict) and type(entry.get('byteLength')) is int,'buffer_shape')
        data=embedded(entry.get('uri'),'application/octet-stream',16*1024**2)
        require(len(data)==entry['byteLength'],'buffer_length');binary.extend(b'\0'*(-len(binary)%4));starts.append(len(binary));binary.extend(data)
        require(len(binary)<=32*1024**2,'combined_buffer_budget');source_buffers.append({'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
    views=document.get('bufferViews');require(isinstance(views,list) and len(views)<=8192,'view_count')
    for view in views:
        require(isinstance(view,dict) and type(view.get('buffer')) is int and 0<=view['buffer']<len(buffers),'view_buffer')
        offset,length=view.get('byteOffset',0),view.get('byteLength')
        require(type(offset) is int and type(length) is int and offset>=0 and length>=0 and offset+length<=buffers[view['buffer']]['byteLength'],'view_bounds')
        view['byteOffset']=starts[view['buffer']]+offset;view['buffer']=0
    images=document.get('images',[]);require(isinstance(images,list) and len(images)<=256,'image_count');source_images=[]
    for image in images:
        require(isinstance(image,dict) and 'bufferView' not in image,'image_shape')
        data=embedded(image.get('uri'),'image/png',16*1024**2);require(data[:8]==b'\x89PNG\r\n\x1a\n','image_png')
        binary.extend(b'\0'*(-len(binary)%4));offset=len(binary);binary.extend(data);require(len(binary)<=32*1024**2,'combined_image_budget')
        views.append({'buffer':0,'byteOffset':offset,'byteLength':len(data)});image['bufferView']=len(views)-1;image['mimeType']='image/png';image.pop('uri')
        source_images.append({'name':image.get('name'),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
    document['buffers']=[{'byteLength':len(binary)}]
    return binary,source_buffers,source_images

def validate_matrix(matrix):
    vector(matrix,16)
    require(all(abs(matrix[i])<1e-10 for i in (3,7,11)) and abs(matrix[15]-1)<1e-10,'nonaffine_matrix')
    # This assembly's mesh-centimetre conversion is an existing uniform0.01 scale.
    columns=[[matrix[j*4+i] for i in range(3)] for j in range(3)]
    require(all(abs(sum(v*v for v in c)-.0001)<1e-10 for c in columns),'source_mesh_scale')
    require(all(abs(sum(columns[i][k]*columns[j][k] for k in range(3)))<1e-10 for i in range(3) for j in range(i)),'source_matrix_shear')
    determinant=sum(columns[0][i]*(columns[1][(i+1)%3]*columns[2][(i+2)%3]-columns[1][(i+2)%3]*columns[2][(i+1)%3]) for i in range(3))
    require(abs(determinant-.000001)<1e-10,'source_matrix_reflection')

def prepare(data,report_data,cfg_data,name='Furrano GT54 (SLRR static)',*,source_sha=SOURCE_SHA,report_sha=REPORT_SHA,cfg_sha=CFG_SHA):
    require(len(data)<=16*1024**2 and hashlib.sha256(data).hexdigest()==source_sha,'source_pin')
    require(len(report_data)<=2*1024**2 and hashlib.sha256(report_data).hexdigest()==report_sha,'report_pin')
    require(len(cfg_data)<=65536 and hashlib.sha256(cfg_data).hexdigest()==cfg_sha,'cfg_pin')
    require(isinstance(name,str) and 0<len(name)<=96 and all(32<=ord(c)<127 for c in name),'name')
    d=json.loads(data);report=json.loads(report_data);frames=wheel_frames(cfg_data)
    require(isinstance(d,dict) and d.get('asset',{}).get('version')=='2.0' and not any(d.get(k) for k in ('skins','animations','extensionsRequired')),'asset_unsupported')
    nodes=d.get('nodes');parts=report.get('parts')
    require(isinstance(nodes,list) and 0<len(nodes)<=4095 and isinstance(parts,list) and len(parts)==len(nodes),'assembly_count')
    require(not report.get('issues') and not d.get('extras',{}).get('assembly_issues'),'unresolved_assembly')
    require(d.get('scene',0)==0 and len(d.get('scenes',[]))==1 and sorted(d['scenes'][0].get('nodes',[]))==list(range(len(nodes))),'flat_scene')
    provenance=report.get('provenance');require(isinstance(provenance,list) and any(p.get('sha256')==cfg_sha and p.get('path')==parts[0].get('cfg_path') for p in provenance),'cfg_provenance')
    for key,limit in (('meshes',4095),('accessors',8192)):
        require(isinstance(d.get(key),list) and 0<len(d[key])<=limit,'structure_unsupported')
    binary,buffers,images=combine(d);g=glb.Geometry(d,binary);roles={};vertex_work=index_work=0
    def role(index,kind):
        require(type(index) is int and 0<=index<len(d['accessors']) and (index not in roles or roles[index]==kind),'accessor_alias');roles[index]=kind
    for mesh in d['meshes']:
        require(isinstance(mesh,dict) and not mesh.get('weights') and isinstance(mesh.get('primitives'),list) and 0<len(mesh['primitives'])<=4096,'mesh_unsupported')
        for primitive in mesh['primitives']:
            require(isinstance(primitive,dict) and primitive.get('mode',4)==4 and not primitive.get('targets') and not primitive.get('extensions'),'primitive_unsupported')
            attrs=primitive.get('attributes');require(isinstance(attrs,dict) and 'POSITION' in attrs and set(attrs)<={'POSITION','NORMAL','TANGENT','TEXCOORD_0','TEXCOORD_1','COLOR_0'},'vertex_features')
            positions=g.values(attrs['POSITION'],'VEC3',{5126});vertex_work+=len(positions);require(vertex_work<=1000000,'vertex_work_budget')
            for attribute,index in attrs.items():
                kind=attribute if attribute in ('POSITION','NORMAL','TANGENT') else 'UNCHANGED';role(index,kind)
                if kind!='UNCHANGED':require(len(g.values(index,'VEC4' if kind=='TANGENT' else 'VEC3',{5126}))==len(positions),'attribute_count')
            index=primitive.get('indices');role(index,'INDICES');count=d['accessors'][index].get('count')
            require(type(count) is int and count>0,'index_count');index_work+=count;require(index_work<=3000000,'index_work_budget')
            indices=g.values(index,'SCALAR',{5121,5123,5125});require(len(indices)%3==0 and all(row[0]<len(positions) for row in indices),'indices')
    for index,kind in roles.items():
        if kind=='UNCHANGED':continue
        values=g.values(index)
        if kind=='INDICES':
            for i in range(0,len(values),3):values[i+1],values[i+2]=values[i+2],values[i+1]
        else:values=[tuple(-v if axis==2 or (kind=='TANGENT' and axis==3) else v for axis,v in enumerate(row)) for row in values]
        g.replace(index,values)
    clouds={-1:[],0:[],1:[],2:[],3:[]};groups=[];aliases=set();vertex_instances=index_instances=0
    for index,(node,part) in enumerate(zip(nodes,parts)):
        require(isinstance(node,dict) and isinstance(part,dict) and node.get('name')==part.get('alias') and node['name'] not in aliases,'part_identity');aliases.add(node['name'])
        require(not any(k in node for k in ('translation','rotation','scale','children','skin','weights','extensions')),'node_features')
        matrix=node.get('matrix');validate_matrix(matrix)
        world=part.get('world');require(isinstance(world,list) and len(world)==4 and all(isinstance(r,list) and len(r)==4 for r in world),'report_world')
        expected=multiply(world,pose(part['render']['pose']))
        for i in range(3):
            for j in range(3):expected[i][j]*=.01
        require(max(abs(matrix[j*4+i]-expected[i][j]) for i in range(4) for j in range(4))<1e-9,'assembly_pose_mismatch')
        match=re.fullmatch(r'(rim|tyre)-([0-3])',node['name']);wheel=int(match.group(2)) if match else -1
        if wheel>=0:
            require(max(abs(world[i][3]-frames[LABELS[wheel]][i]) for i in range(3))<1e-8,'wheel_pivot_mismatch')
            require(part.get('source_selection','').startswith('Furrano_GT54.java stock_parts_list_RGear_'),'wheel_selection_unproven')
        # S M S conjugates arbitrary source rotation while local vertices receive S once.
        node['matrix']=[(-v if (i%4==2) != (i//4==2) else v) for i,v in enumerate(matrix)]
        M=node['matrix'];mesh=node.get('mesh');require(type(mesh) is int and 0<=mesh<len(d['meshes']),'node_mesh');groups.append((index,wheel))
        for primitive in d['meshes'][mesh]['primitives']:
            index_instances+=d['accessors'][primitive['indices']]['count'];require(index_instances<=1500000,'expanded_index_budget')
            positions=g.values(primitive['attributes']['POSITION'],'VEC3',{5126});vertex_instances+=len(positions);require(vertex_instances<=1000000,'instance_vertex_budget')
            for p in positions:
                point=tuple(sum(M[j*4+i]*p[j] for j in range(3))+M[12+i] for i in range(3));require(all(math.isfinite(v) for v in point),'world_overflow');clouds[wheel].append(point)
    counts=Counter(w for _,w in groups);require(all(counts[i]==2 and clouds[i] for i in range(4)) and counts[-1]>0,'wheel_group_coverage')
    lower=[min(p[i] for p in clouds[-1]) for i in range(3)];upper=[max(p[i] for p in clouds[-1]) for i in range(3)];wheels=[];source_geometry=[]
    for i,label in enumerate(LABELS):
        native=frames[label];center=[native[0],native[1],-native[2]]
        radius=max(math.hypot(p[1]-center[1],p[2]-center[2]) for p in clouds[i]);width=2*max(abs(p[0]-center[0]) for p in clouds[i])
        require(0<radius<2 and 0<width<2 and (center[0]<0 if i%2==0 else center[0]>0) and (center[2]>0 if i<2 else center[2]<0),'wheel_geometry')
        wheels.append({'label':label,'center':center,'radius':radius,'width':width});source_geometry.append({'label':label,'cfg_pose':native,'measured_radius':radius,'measured_width':width})
    for left in (0,2):wheels[left]['radius']=wheels[left+1]['radius']=max(wheels[left]['radius'],wheels[left+1]['radius'])
    lift=max(0,-lower[1]+.000001,*(w['radius']-w['center'][1] for w in wheels))
    source_bounds=lower+upper;lower[1]+=lift;upper[1]+=lift
    for w in wheels:w['center'][1]+=lift
    require(all(lower[i]<upper[i] for i in range(3)) and lower[1]>0 and upper[0]-lower[0]<=10 and upper[2]-lower[2]<=30 and upper[1]<=10,'racer_body_geometry')
    require(all(lower[2]<=w['center'][2]<=upper[2] for w in wheels),'racer_axle_containment')
    wheelbase=(wheels[0]['center'][2]+wheels[1]['center'][2]-wheels[2]['center'][2]-wheels[3]['center'][2])/2;require(.5<=wheelbase<=20,'wheelbase')
    for left in (0,2):require(abs(wheels[left]['center'][1]-wheels[left+1]['center'][1])<=1e-4 and abs(wheels[left]['center'][2]-wheels[left+1]['center'][2])<=1e-4,'paired_axles')
    role='player-candidate';blockers=['Native visual/suspension-height review required; source-preserving visible body clearance is unusually high.']
    extras=d.setdefault('extras',{});extras['racerPreparation']={'schema':1,'role':role,'runtime_player_eligible':False,'source_sha256':source_sha,'assembly_report_sha256':report_sha,'chassis_cfg_sha256':cfg_sha,'mirror_z':True,'ground_lift':lift,'eligibility_blockers':blockers}
    root=len(nodes);nodes.append({'name':'racer_ground_lift','translation':[0,lift,0],'children':list(range(root))});d['scenes'][0]['nodes']=[root];d['buffers'][0]['byteLength']=len(binary)
    prepared=glb.pack(d,binary);digest=hashlib.sha256(prepared).hexdigest();number=lambda x:format(x,'.17g')
    lines=['RACER_VEHICLE 1','id '+json.dumps('vehicle-'+digest),'name '+json.dumps(name),'mesh '+json.dumps(digest+'.glb'),'sha256 '+digest,'source_sha256 '+source_sha,'body '+' '.join(map(number,lower+upper))]
    lines+=['wheel '+w['label']+' '+' '.join(map(number,w['center']+[w['radius'],w['width']])) for w in wheels];lines+=['groups '+str(len(groups))]+['group '+str(i)+' '+str(w) for i,w in groups]
    receipt={'schema':1,'role':role,'runtime_player_eligible':False,'eligibility_blockers':blockers,'source_gltf_sha256':source_sha,'assembly_report_sha256':report_sha,'chassis_cfg_sha256':cfg_sha,'prepared_sha256':digest,'source_bytes':len(data),'prepared_bytes':len(prepared),'source_body_bounds_after_axis_mirror':source_bounds,'body':lower+upper,'source_wheel_geometry':source_geometry,'wheels':wheels,'groups':groups,'normalization':{'mirror_z':True,'ground_lift':lift,'minimum_body_clearance_margin':.000001,'source_mesh_scale_preserved':.01,'unit_authority':'Pinned reference convention: SCX centimetres/CFG metres; supplied game runtime not observed.','axle_collision_radius':'conservative maximum of actual rim and tyre vertices on each axle'},'source_buffers':buffers,'source_images':images,'source_provenance':provenance,'assembly_limitations':report.get('limitations',[]),'material_issues':[p.get('bindings',{}).get('issues',[]) for p in parts],'limitations':['Every existing visible assembly vertex and original image/material is retained; internal hardware remains absent as declared upstream.','Source CFG wheel pivots are unchanged; no user-measured or visual-fit correction applied.','High visible-body gap requires native visual comparison before promotion to player catalog.','Native suspension/damage/paint/lighting and GPU rendering equivalence unverified.']}
    return prepared,'\n'.join(lines)+'\n',receipt

def read_regular(path,limit):
    path=Path(path);require(not any(p.is_symlink() for p in (path,*path.parents)),'symlink_input')
    fd=os.open(path,os.O_RDONLY|os.O_NONBLOCK|os.O_NOFOLLOW)
    with os.fdopen(fd,'rb') as stream:
        before=os.fstat(stream.fileno());require(stat.S_ISREG(before.st_mode),'nonregular_input');data=stream.read(limit+1);after=os.fstat(stream.fileno())
    require(len(data)<=limit and len(data)==before.st_size and (before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns),'input_size_or_change');return data

def publish(source,report,cfg,output,name='Furrano GT54 (SLRR static)',minimum_free=20*1024**3):
    prepared,descriptor,receipt=prepare(read_regular(source,16*1024**2),read_regular(report,2*1024**2),read_regular(cfg,65536),name)
    output=Path(output);require(not output.exists() and not output.is_symlink() and not any(p.is_symlink() for p in output.parents),'output_exists_or_symlink');require(shutil.disk_usage(output.parent).free>=minimum_free,'free_space');output.mkdir(mode=0o700)
    digest=receipt['prepared_sha256']
    for filename,payload in ((digest+'.glb',prepared),(digest+'.vehicle',descriptor.encode()),(digest+'.json',(json.dumps(receipt,indent=2)+'\n').encode())):
        fd=os.open(output/filename,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'wb') as out:out.write(payload)
    return receipt

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for flag in ('source','report','cfg','output'):p.add_argument('--'+flag,type=Path,required=True)
    p.add_argument('--name',default='Furrano GT54 (SLRR static)');a=p.parse_args(argv)
    try:print(json.dumps(publish(a.source,a.report,a.cfg,a.output,a.name),indent=2));return 0
    except (PreparationError,glb.PreparationError) as error:print('SLRR preparation failed: '+str(error)+'; inspect any partial output',file=sys.stderr);return 2
    except (OSError,ValueError,TypeError,KeyError,OverflowError):print('SLRR preparation failed: invalid_input_or_storage; inspect any partial output',file=sys.stderr);return 2

if __name__=='__main__':sys.exit(main())
