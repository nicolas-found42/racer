#!/usr/bin/env python3
"""Hash-pinned MCLA player350Z static adapter; traffic sources are rejected."""
import argparse,copy,hashlib,json,math,os,re,shutil,sys
from pathlib import Path
import prepare_gt4_vehicle as g
from prepare_mcla_vehicle import read_regular
SOURCE_SHA='7f4818ad423f9db6802e70a65b6de4c4cb0e38dab4b335f98318a7d8360bd56a'
PROOF_SHA='369718198e7c69b20183668577fc1daa5754f0c1ab19f05287237bcf8b13f32d'
ID='midnight-club-los-angeles/vp_nsn_350z_06'
LABELS=('FL','FR','RL','RR')
IDENTITY=[1.,0.,0.,0.,0.,1.,0.,0.,0.,0.,1.,0.,0.,0.,0.,1.]

def product(a,b):return [sum(a[k*4+i]*b[j*4+k] for k in range(4)) for j in range(4) for i in range(4)]
def inverse(a):
    r=[a[i*4+j] if i<3 and j<3 else float(i==j) for j in range(4) for i in range(4)]
    for i in range(3):r[12+i]=-sum(r[k*4+i]*a[12+k] for k in range(3))
    return r

def proof_ownership(d,proof):
    e=d.get('extras',{});g.require(e.get('vehicle')=='vp_nsn_350z_06' and e.get('profile')=='mcla-xbox360-static-stock-v3','not_proven_player_source')
    resources=proof.get('resources',{});sources={s['file']:s for s in e['sources']}
    for file,row in resources.items():
        g.require(file in sources and row['sha256']==sources[file]['sha256'] and not any(row['skinned']),'native_source_or_skin_mismatch')
    parts=e['parts'];body=resources[parts[0]['file']];bones={b['name']:b for b in body['skeleton']};centers={i:bones['axl_'+str(i)]['model'][:] for i in range(4)}
    # Explicit alternative/occluder omissions only; unknown gaps fail closed.
    allowed={'conv_top0_lod_0.xrsc','door_l_wide0_lod_0.xrsc','door_r_wide0_lod_0.xrsc','hood_wide0_lod_0.xrsc','occluder_0_lod_0.xrsc','widebody0_lod_0.xrsc'}
    g.require({Path(p).name for p in e.get('omitted',[])}==allowed,'unexplained_omission')
    outer_frames={}
    for p in parts:
        g.require(p['file'] in resources,'missing_part_native_proof')
        index=p['attachment_bone_index']
        if index is not None:
            owner=resources[p['attachment_source']]['skeleton'];g.require(0<=index<len(owner) and owner[index]['name']==p['attachment_native_name'],'attachment_bone_mismatch')
            expected_outer=owner[index]['matrix']
            if p['attachment_source']!=parts[0]['file']:
                parents=[q for q in parts if q['file']==p['attachment_source']]
                g.require(len(parents)==1 and p['attachment_source'] in outer_frames,'attachment_parent_chain')
                expected_outer=product(outer_frames[p['attachment_source']],expected_outer)
        else:
            g.require(p['bone']=='resource_root','unproven_root_frame');expected_outer=IDENTITY
        g.require(max(abs(a-b) for a,b in zip(p['matrix'],expected_outer))<1e-5,'native_attachment_outer_pose')
        outer_frames[p['file']]=expected_outer
    ownership={};counts={};seen=set()
    for ni,n in enumerate(d['nodes']):
        name=n['name'];info=n['extras'];model=info['nativeModel'];bone=info['nativeBoneIndex'];wheel=-1
        shared=re.fullmatch(r'(shared/resources/(?:rims/whl_stk_nsn_350z_06|tires/models/tir_car))@axl_([0-3])/model([0-9]+)',name)
        if shared:
            wheel=int(shared[2]);file=shared[1]+'/body_lod_0.xrsc';row=resources[file]
            rows=[w for w in e['wheels'] if w['file']==file and w['bone']=='axl_'+str(wheel)];g.require(len(rows)==1,'shared_wheel_join');w=rows[0]
            g.require(max(abs(w['translation'][i]-centers[wheel][i]) for i in range(3))<1e-7,'native_axle_pose')
            sx,sy,sz=w['scale'];outer=[sx,0,0,0,0,sy,0,0,0,0,sz,0,*w['translation'],1]
            if w['rotation'] is not None:
                g.require(w['rotation']==[0.,1.,0.,0.],'unsupported_wheel_rotation');outer[0]*=-1;outer[10]*=-1
            local=row['skeleton'][bone]['matrix'][:];root=w['root_rebase'];shift=IDENTITY[:];shift[12:15]=[-v for v in root];expected=product(outer,product(shift,local))
            counts[wheel]=counts.get(wheel,0)+1
        else:
            match=re.fullmatch(r'(.+\.xrsc)@([^/]+)/model([0-9]+)',name);g.require(match is not None,'unknown_node_owner');file=match[1];row=resources[file]
            candidates=[p for p in parts if p['file']==file and p['bone']==match[2]];g.require(len(candidates)==1,'part_join');p=candidates[0]
            local=row['skeleton'][bone]['matrix'] if bone is not None else IDENTITY
            if p['resource_frame']=='root-relative':local=product(inverse(row['skeleton'][0]['matrix']),local)
            else:g.require(p['resource_frame']=='native','unsupported_resource_frame')
            expected=product(p['matrix'],local)
        g.require(type(model)is int and 0<=model<len(row['model_bindings']) and row['model_bindings'][model]==bone,'model_binding_mismatch')
        g.require(max(abs(a-b) for a,b in zip(n['matrix'],expected))<1e-5,'native_node_pose_mismatch')
        key=(file,name.split('@',1)[1]);g.require(key not in seen,'duplicate_model_instance');seen.add(key);ownership[ni]=wheel
    g.require(counts=={0:3,1:3,2:3,3:3},'incomplete_shared_wheels')
    return ownership,centers

def prepare(data,proof_data,name="Nissan 350Z Roadster 2006 (MCLA)",*,source_sha=SOURCE_SHA,proof_sha=PROOF_SHA,roadster_radius_fit=False,racer_glass_policy=False,flat_ground_rest=False):
    g.require(hashlib.sha256(data).hexdigest()==source_sha and len(proof_data)<=512*1024 and hashlib.sha256(proof_data).hexdigest()==proof_sha,'source_or_proof_pin')
    g.require(isinstance(name,str) and 0<len(name)<=96 and all(32<=ord(c)<127 for c in name),'name')
    d,binary=g.unpack(data);proof=json.loads(proof_data);g.require(proof['source_sha256']==source_sha,'proof_source_join')
    for key,cap in (('nodes',4095),('meshes',512),('accessors',8192),('bufferViews',8192)):
        g.require(isinstance(d.get(key),list) and 0<len(d[key])<=cap,'structure_budget')
    g.require(not any(d.get(k) for k in ('skins','animations','extensionsRequired')) and len(d['scenes'])==1 and d.get('scene',0)==0 and d['scenes'][0]['nodes']==list(range(len(d['nodes']))),'runtime_or_scene_unsupported')
    g.require(len(d['buffers'])==1 and 'uri' not in d['buffers'][0] and all('uri'not in i for i in d.get('images',[])),'external_resources')
    ownership,centers=proof_ownership(d,proof);geometry=g.Geometry(d,binary);roles={};work=0;position_work=0
    def role(index,kind):g.require(type(index)is int and 0<=index<len(d['accessors']) and (index not in roles or roles[index]==kind),'accessor_alias');roles[index]=kind
    for mesh in d['meshes']:
        for p in mesh['primitives']:
            g.require(p.get('mode',4)==4 and not p.get('targets') and set(p.get('extensions',{}))<={'KHR_materials_variants'},'primitive_unsupported')
            attrs=p['attributes'];g.require('POSITION'in attrs and set(attrs)<={'POSITION','NORMAL','TANGENT','TEXCOORD_0','TEXCOORD_1','COLOR_0'},'attribute_unsupported')
            for attr,index in attrs.items():role(index,attr if attr in ('POSITION','NORMAL','TANGENT') else 'UNCHANGED')
            role(p['indices'],'INDICES');count=d['accessors'][p['indices']]['count'];work+=count;g.require(work<=1500000,'index_work_budget')
            position_count=d['accessors'][attrs['POSITION']]['count'];g.require(type(position_count)is int and position_count>0,'position_count');position_work+=position_count;g.require(position_work<=1000000,'position_work_budget')
            positions=geometry.values(attrs['POSITION'],'VEC3',{5126})
            for attribute in ('NORMAL','TANGENT'):
                if attribute in attrs:g.require(d['accessors'][attrs[attribute]]['count']==position_count,'attribute_count')
            indices=geometry.values(p['indices'],'SCALAR',{5121,5123,5125});g.require(len(indices)%3==0 and all(v[0]<len(positions) for v in indices),'indices')
    for index,kind in roles.items():
        if kind=='UNCHANGED':continue
        values=geometry.values(index,'SCALAR' if kind=='INDICES' else 'VEC4' if kind=='TANGENT' else 'VEC3',{5121,5123,5125} if kind=='INDICES' else {5126})
        if kind=='INDICES':
            for i in range(0,len(values),3):values[i+1],values[i+2]=values[i+2],values[i+1]
        else:values=[tuple(-v if axis==2 or (kind=='TANGENT' and axis==3) else v for axis,v in enumerate(row)) for row in values]
        geometry.replace(index,values)
    clouds={i:[] for i in range(-1,4)};tire_clouds={i:[] for i in range(4)};groups=[];instances=vertices=0
    for ni,n in enumerate(d['nodes']):
        g.require(not any(k in n for k in ('children','skin','weights','translation','rotation','scale','extensions')),'node_unsupported')
        M=g.finite_vector(n['matrix'],16);g.require(all(abs(M[i])<1e-6 for i in (3,7,11)) and abs(M[15]-1)<1e-6,'nonaffine_node')
        n['matrix']=[-v if (i%4==2)!=(i//4==2) else v for i,v in enumerate(M)];M=n['matrix'];wheel=ownership[ni];groups.append((ni,wheel))
        for p in d['meshes'][n['mesh']]['primitives']:
            instances+=d['accessors'][p['indices']]['count'];g.require(instances<=1500000,'expanded_index_budget');points=geometry.values(p['attributes']['POSITION'],'VEC3',{5126});vertices+=len(points);g.require(vertices<=1000000,'vertex_work_budget')
            for point in points:
                world=tuple(sum(M[j*4+i]*point[j] for j in range(3))+M[12+i] for i in range(3));clouds[wheel].append(world)
                if wheel>=0 and n['name'].startswith('shared/resources/tires/'):tire_clouds[wheel].append(world)
    g.require(all(clouds.values()) and all(tire_clouds.values()),'incomplete_groups')
    source_wheel_measurements=[];fit=[]
    for i in range(4):
        c=centers[i][:];c[2]=-c[2];source_radius=max(math.hypot(p[1]-c[1],p[2]-c[2]) for p in tire_clouds[i]);source_width=2*max(abs(p[0]-c[0]) for p in clouds[i]);source_wheel_measurements.append({'label':LABELS[i],'tire_radius':source_radius,'assembly_width':source_width})
        factor=((.32985 if i<2 else .33885)/source_radius) if roadster_radius_fit else 1.0
        if roadster_radius_fit:
            clouds[i]=[tuple(p[0] if axis==0 else c[axis]+factor*(p[axis]-c[axis]) for axis in range(3)) for p in clouds[i]]
            for ni,w in groups:
                if w!=i:continue
                matrix=d['nodes'][ni]['matrix']
                for axis in (1,2):
                    for col in range(3):matrix[col*4+axis]*=factor
                    matrix[12+axis]=c[axis]+factor*(matrix[12+axis]-c[axis])
        fit.append({'label':LABELS[i],'radial_factor':factor,'target_tire_radius':(.32985 if i<2 else .33885) if roadster_radius_fit else None,'width_factor':1.0})
    lo=[min(p[i] for p in clouds[-1]) for i in range(3)];hi=[max(p[i] for p in clouds[-1]) for i in range(3)];wheels=[]
    for i in range(4):
        c=centers[i][:];c[2]=-c[2];radius=max(math.hypot(p[1]-c[1],p[2]-c[2]) for p in clouds[i]);width=2*max(abs(p[0]-c[0]) for p in clouds[i]);g.require(0<radius<2 and 0<width<2,'wheel_dimensions');wheels.append({'label':LABELS[i],'center':c,'radius':radius,'width':width})
    for i in (0,2):wheels[i]['radius']=wheels[i+1]['radius']=max(wheels[i]['radius'],wheels[i+1]['radius'])
    lift=max(0,-lo[1],*(w['radius']-w['center'][1] for w in wheels));source_bounds=lo+hi;lo[1]+=lift;hi[1]+=lift
    for w in wheels:w['center'][1]+=lift
    g.require(all(math.isfinite(v) for v in lo+hi) and all(lo[i]<hi[i] for i in range(3)) and hi[0]-lo[0]<=10 and hi[2]-lo[2]<=30 and hi[1]<=10,'body_geometry')
    for i,w in enumerate(wheels):g.require(lo[2]<=w['center'][2]<=hi[2] and (w['center'][0]<0 if i%2==0 else w['center'][0]>0) and (w['center'][2]>0 if i<2 else w['center'][2]<0),'wheel_orientation')
    wheelbase=(wheels[0]['center'][2]+wheels[1]['center'][2]-wheels[2]['center'][2]-wheels[3]['center'][2])/2;g.require(.5<=wheelbase<=20,'wheelbase')
    for i in (0,2):g.require(abs(wheels[i]['center'][1]-wheels[i+1]['center'][1])<1e-4 and abs(wheels[i]['center'][2]-wheels[i+1]['center'][2])<1e-4,'paired_axles')
    ground_adjustments=[]
    if flat_ground_rest:
        g.require(roadster_radius_fit,'flat_ground_requires_authored_radius_fit')
        for wheel in (0,1):
            gap=wheels[wheel]['center'][1]-wheels[wheel]['radius'];g.require(0<=gap<.05,'front_ground_gap')
            for index,owner in groups:
                if owner==wheel:d['nodes'][index]['matrix'][13]-=gap
            wheels[wheel]['center'][1]-=gap
            ground_adjustments.append({'label':LABELS[wheel],'world_y_delta':-gap,'center_y_before':wheels[wheel]['center'][1]+gap,'center_y_after':wheels[wheel]['center'][1],'radius':wheels[wheel]['radius']})
    e=d['extras'];e['racerPreparation']={'schema':1,'role':'player-candidate','runtime_player_eligible':False,'source_sha256':source_sha,'native_proof_sha256':proof_sha,'ground_lift':lift,'mirror_z':True,'units':'factor1 explicitimportassumption; nativephysicalunitlabelunverified','wheel_sizing':'sourcepreview axle-height/bead approximation retained; cylinders measured from actual rim+tire geometry'}
    if roadster_radius_fit:
        e['racerPreparation']['manufacturer_assisted_fit']={'authority':'Racer-authored adaptation from 2006 US Nissan350ZRoadster standard18inch225/45front245/45rear; not native-runtime tire specification','url':'https://usa.nissannews.com/en-US/releases/2006-nissan-350z-coupe-and-roadster-press-kit','method':'Radial worldY/Z scaling of tyre and corresponding rim about unchanged native axle pivot; body and X width untouched.','wheels':fit,'nominal_widths_m':[.225,.245],'nominal_width_envelope_match':'unknown; no width fitting performed'}
    if flat_ground_rest:
        e['racerPreparation']['flat_ground_rest']={'authority':'Racer-authored exact centerY=chosenradius flat-ground constraint; NOT native suspension proof','changes':ground_adjustments,'scope':'Front rim/tire group worldY only; body, rear, radius, width, X/Z unchanged','original_native_pivots':copy.deepcopy(centers)}
    material_changes=[]
    if racer_glass_policy:
        for index,material in enumerate(d.get('materials',[])):
            shader=material.get('extras',{}).get('sourceShader')
            if shader not in ('CarGlass','BlackOpaqueGlass'):continue
            original=copy.deepcopy(material);material['pbrMetallicRoughness']['baseColorFactor']=[.08,.12,.16,.35] if shader=='CarGlass' else [.025,.025,.03,1.0]
            material['alphaMode']='BLEND' if shader=='CarGlass' else 'OPAQUE'
            material_changes.append({'index':index,'source_material':original,'authored_factor':material['pbrMetallicRoughness']['baseColorFactor'],'authored_alpha_mode':material['alphaMode']})
        e['racerPreparation']['material_policy']={'authority':'Racer-authored exact-sourceShader glass interpretation; native opacity/render equivalence unverified','changes':material_changes,'scope':'CarGlass and BlackOpaqueGlass only; bumpedglass lamps untouched'}
    root=len(d['nodes']);d['nodes'].append({'name':'racer_ground_lift','translation':[0,lift,0],'children':list(range(root))});d['scenes'][0]['nodes']=[root];d['buffers'][0]['byteLength']=len(binary)
    prepared=g.pack(d,binary);digest=hashlib.sha256(prepared).hexdigest();num=lambda v:format(v,'.17g')
    lines=['RACER_VEHICLE 1','id '+json.dumps('vehicle-'+digest),'name '+json.dumps(name),'mesh '+json.dumps(digest+'.glb'),'sha256 '+digest,'source_sha256 '+source_sha,'body '+' '.join(map(num,lo+hi))]
    lines+=['wheel '+w['label']+' '+' '.join(map(num,w['center']+[w['radius'],w['width']])) for w in wheels];lines+=['groups '+str(len(groups))]+['group '+str(n)+' '+str(w) for n,w in groups]
    receipt={'schema':1,'catalog_id':ID,'role':'player-candidate','runtime_player_eligible':False,'source_sha256':source_sha,'native_proof_sha256':proof_sha,'prepared_sha256':digest,'prepared_bytes':len(prepared),'body':lo+hi,'source_body_bounds_after_axis_mirror':source_bounds,'wheels':wheels,'groups':groups,'ground_lift':lift,'source_native_axle_pivots':centers,'source_wheel_measurements':source_wheel_measurements,'radial_fit':fit,'wheelbase_native_units':wheelbase,'material_changes':material_changes,'source_parts':copy.deepcopy(e['parts']),'source_wheel_sizing':copy.deepcopy(e['wheels']),'source_omissions':e['omitted'],'omission_reading':'Alternate convertible top/widebody variants and nonvisible occluder omitted; selected closed-top stock preview preserved.','source_claim_limits':e.get('claim_limits',[]),'normalization':e['racerPreparation'],'limitations':['Complete provided static playerpreview, not native runtime configuration closure.','Shared stock rim/tire sizing is exporter approximation, not decoded tire specification.','Native units factor1 import assumption; use 2006 US Z33 manufacturer references for comparison, not 2002 exact identity.','Player eligibility awaits root GPU/canonical-size review; no traffic model promotion.']}
    return prepared,'\n'.join(lines)+'\n',receipt

def publish(source,proof,output,name="Nissan 350Z Roadster 2006 (MCLA)",minimum_free=20*1024**3,roadster_radius_fit=False,racer_glass_policy=False,flat_ground_rest=False):
    mesh,descriptor,r=prepare(read_regular(source,16*1024**2),read_regular(proof,512*1024),name,roadster_radius_fit=roadster_radius_fit,racer_glass_policy=racer_glass_policy,flat_ground_rest=flat_ground_rest);output=Path(output)
    g.require(not output.exists() and not any(p.is_symlink() for p in (output,*output.parents)),'output_exists_or_symlink');g.require(shutil.disk_usage(output.parent).free>=minimum_free,'free_space');output.mkdir(mode=0o700)
    for suffix,data in (('.glb',mesh),('.vehicle',descriptor.encode()),('.json',(json.dumps(r,indent=2)+'\n').encode())):
        fd=os.open(output/(r['prepared_sha256']+suffix),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'wb') as f:f.write(data)
    return r

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for flag in ('source','native-proof','output'):p.add_argument('--'+flag,type=Path,required=True)
    p.add_argument('--flat-ground-rest',action='store_true');p.add_argument('--racer-glass-policy',action='store_true');p.add_argument('--roadster-radius-fit',action='store_true');p.add_argument('--name',default="Nissan 350Z Roadster 2006 (MCLA)");a=p.parse_args()
    try:print(json.dumps(publish(a.source,a.native_proof,a.output,a.name,roadster_radius_fit=a.roadster_radius_fit,racer_glass_policy=a.racer_glass_policy,flat_ground_rest=a.flat_ground_rest),indent=2));return 0
    except (OSError,ValueError,KeyError,TypeError,IndexError,OverflowError) as error:print('MCLA player preparation failed; unsupported/invalid evidence or storage; partialoutput mayremain',file=sys.stderr);return 2
if __name__=='__main__':sys.exit(main())
