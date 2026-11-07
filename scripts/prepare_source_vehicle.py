#!/usr/bin/env python3
"""Bounded GT1/MC3/Redline static source-assembly adapters for Racer vehicle descriptors."""
import argparse,copy,hashlib,json,math,os,re,stat,shutil
from pathlib import Path
from prepare_gt4_vehicle import Geometry,PreparationError,require,finite_vector,unpack,pack,MAX_SOURCE,MAX_OUTPUT
LABELS=('FL','FR','RL','RR')

def transform(node):
    require(not any(k in node for k in ('matrix','skin','weights','extensions')),'unsupported_node')
    t=finite_vector(node.get('translation',[0,0,0]),3);s=finite_vector(node.get('scale',[1,1,1]),3)
    x,y,z,w=finite_vector(node.get('rotation',[0,0,0,1]),4)
    require(abs(x*x+y*y+z*z+w*w-1)<1e-5 and min(s)>0,'unsupported_transform')
    r=[[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)], [2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)], [2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]]
    return t,s,r

def vector(row,s,r,point=False,t=None,mirror=True):
    v=[sum(r[i][j]*s[j]*row[j] for j in range(3)) for i in range(3)]
    if point:v=[v[i]+t[i] for i in range(3)]
    if mirror:v[2]=-v[2]
    return v

def metadata(d,catalog_id,native_config=None,*,native_bones=None):
    extras=d.get('extras',{});profile=extras.get('sourceProfile',extras.get('source_profile'))
    scene=d['scenes'][d.get('scene',0)]['nodes'];require(len(scene)==len(set(scene)),'duplicate_scene_node')
    ownership={};centers={};dimensions={};evidence={}
    if profile=='gran-turismo-native-candidate':
        require(catalog_id=='gran-turismo/'+extras.get('sourceId',''),'catalog_id_mismatch')
        require(extras.get('wheelAssembly',{}).get('basis')=='Native CAR units /4096; entire assembly reflects Z','unknown_gt1_units')
        for index in scene:
            n=d['nodes'][index];e=n.get('extras',{})
            if 'nativeWheelIndex' not in e:ownership[index]=-1;continue
            i=e['nativeWheelIndex'];require(type(i)is int and 0<=i<4 and i not in centers,'gt1_wheel_index')
            c=finite_vector(e.get('nativePivotPositionMetres'),3);raw=finite_vector(e.get('nativePivotPosition'),3)
            require(max(abs(c[j]-raw[j]/4096*(1 if j<2 else -1)) for j in range(3))<1e-8,'gt1_pivot_units')
            width,radius=e.get('nativeWidth'),e.get('nativeRadius');require(type(width)is int and type(radius)is int and min(width,radius)>0,'gt1_dimensions')
            ownership[index]=i;centers[i]=c;dimensions[i]=(radius/4096,width/4096)
            evidence[i]={'node':index,'extras':copy.deepcopy(e),'dimension_rule':'native CAR dimensions /4096; checked against selected source wheel vertices'}
    elif profile=='mc3-ps2-static-preview-v1':
        require(catalog_id=='midnight-club-3-remix/'+extras.get('car',''),'catalog_id_mismatch')
        if native_bones is not None:
            from mc3_wheel_contract import resolve
            contract=resolve(d,native_bones);ownership=contract['ownership'];centers=contract['centers']
            for slot in range(4):
                evidence[slot]={'native_pose_contract':{'orientation_anchors':contract['orientation_anchors'],'frame':contract['frame'],'limits':contract['limits']},'components':[row for row in contract['evidence']if row['canonical_slot']==LABELS[slot]]}
        else:
            skeleton=extras.get('nativeSkeleton',{});bones={b['index']:b for b in skeleton.get('bones',[])};components={}
            for index in scene:
                n=d['nodes'][index];e=n.get('extras',{});joint=e.get('nativeWheelJoint')
                if joint is None:ownership[index]=-1;continue
                require(joint in ('whl00','whl01','whl02','whl03'),'unsupported_mc3_joint');i=int(joint[-1]);kind=e.get('nativeWheelComponent')
                require(kind in ('rim','tire') and (i,kind) not in components,'mc3_component_ownership');components[i,kind]=index
                bone=bones.get(e.get('nativeBone'));require(isinstance(bone,dict) and bone.get('name')==joint,'mc3_joint_bone_mismatch')
                c=finite_vector(bone.get('global_position'),3);t=finite_vector(n.get('translation'),3)
                require(max(abs(c[j]-t[j]) for j in range(3))<1e-7,'mc3_joint_pose_mismatch')
                require(i not in centers or centers[i]==c,'mc3_split_pivot');centers[i]=c;ownership[index]=i
                evidence.setdefault(i,{'bone':copy.deepcopy(bone),'components':[]})['components'].append({'node':index,'kind':kind,'extras':copy.deepcopy(e),'scale':n.get('scale')})
            require(set(components)=={(i,k) for i in range(4) for k in ('rim','tire')},'mc3_missing_components')
    elif profile=='redline-static-car-v1':
        require(catalog_id=='redline/'+extras.get('car',''),'catalog_id_mismatch')
        require(isinstance(native_config,bytes) and len(native_config)<=65536,'redline_native_config_required')
        require(hashlib.sha256(native_config).hexdigest()==extras.get('nativeConfig',{}).get('sha256'),'redline_config_hash')
        text=native_config.decode('cp1252');require('Coordinates are in meters.' in text and 'Z points to the front.' in text,'redline_source_units')
        rows={};current=None
        for line,raw in enumerate(text.splitlines(),1):
            clean=raw.split(';',1)[0].strip()
            if clean.startswith('#'):
                current=int(clean[1:].strip());continue
            if current is None or not clean.startswith('wheels.'):continue
            key,value=clean.split(None,1);target=rows.setdefault(current,{})
            require(key not in target,'duplicate_redline_wheel_field')
            if key=='wheels.pos':value=[float(x.strip())for x in value.strip('{}').split(',')]
            elif key in ('wheels.width','wheels.radius','wheels.maxSuspension'):value=float(value)
            elif key=='wheels.model':value=json.loads(value)
            target[key]={'value':value,'line':line}
        for index in scene:
            n=d['nodes'][index];name=n.get('name','');match=re.fullmatch(r'WHEEL_([0-3])',name)
            if not match:ownership[index]=-1;continue
            i=int(match[1]);row=rows.get(i,{})
            require(all(k in row for k in ('wheels.pos','wheels.radius','wheels.width','wheels.maxSuspension','wheels.model')),'redline_config_fields')
            c=finite_vector(row['wheels.pos']['value'],3)[:];c[1]-=row['wheels.maxSuspension']['value']/2
            radius=row['wheels.radius']['value'];width=row['wheels.width']['value'];require(0<radius<2 and 0<width<2,'redline_dimensions')
            require(max(abs(a-b)for a,b in zip(c,finite_vector(n.get('translation'),3)))<1e-7,'redline_pivot_config_mismatch')
            require(n.get('scale')==[width,radius,radius] and n.get('extras',{}).get('nativeResource')==row['wheels.model']['value'],'redline_model_config_mismatch')
            require(i not in centers,'redline_duplicate_wheel');ownership[index]=i;centers[i]=c;dimensions[i]=(radius,width)
            evidence[i]={'native_config_sha256':extras['nativeConfig']['sha256'],'config_rows':row,'source_node':index,'suspension_rule':'sourceposY minus maxSuspension/2; pinned exporter static preview'}
    else:raise PreparationError('unsupported_source_profile')
    require(set(centers)==set(range(4)),'incomplete_wheels')
    for i,c in centers.items():require((c[0]<0 if i%2==0 else c[0]>0) and ((c[2]>0 if i<2 else c[2]<0) if profile=='redline-static-car-v1' else (c[2]<0 if i<2 else c[2]>0)),'source_wheel_orientation')
    return scene,ownership,centers,dimensions,evidence

def prepare(data,catalog_id,name,native_config=None,*,native_bones=None):
    require(isinstance(name,str) and 0<len(name)<=96 and all(32<=ord(c)<127 for c in name),'invalid_name')
    d,binary=unpack(data)
    require(not any(d.get(k) for k in ('animations','skins','extensionsRequired')),'unsupported_runtime_features')
    for key,cap in [('nodes',512),('meshes',512),('accessors',8192),('bufferViews',8192),('scenes',16)]:require(isinstance(d.get(key),list) and 0<len(d[key])<=cap,'document_budget')
    require(len(d.get('buffers',[]))==1 and 'uri' not in d['buffers'][0],'unsupported_buffer')
    require(all('uri' not in i for i in d.get('images',[])),'external_image')
    selected,ownership,centers,dimensions,evidence=metadata(d,catalog_id,native_config,native_bones=native_bones)
    mirror=not catalog_id.startswith('redline/')
    g=Geometry(d,binary);points={i:[] for i in range(-1,4)};nodes=[];meshes=[];groups=[];index_work=0
    # Bake each selected node to world-space geometry, then mirror Z into Racer's +Z-nose frame.
    # Per-node accessor copies preserve sharing in the source and isolate transformed instances.
    for original in selected:
        require(type(original)is int and 0<=original<len(d['nodes']),'node_index');n=d['nodes'][original]
        require(not n.get('children') and type(n.get('mesh'))is int and 0<=n['mesh']<len(d['meshes']),'unsupported_hierarchy')
        t,s,r=transform(n);mesh=copy.deepcopy(d['meshes'][n['mesh']]);wheel=ownership[original]
        for p in mesh['primitives']:
            require(p.get('mode',4)==4 and not p.get('targets'),'primitive_unsupported')
            attrs=p['attributes'];require('POSITION'in attrs and set(attrs)<={'POSITION','NORMAL','TANGENT','TEXCOORD_0','TEXCOORD_1','COLOR_0','_MC3_NATIVE_NORMAL','_MC3_NATIVE_UV','_MC3_NATIVE_COLOR','_MC3_NATIVE_POSITION'},'attributes_unsupported')
            pos=g.values(attrs['POSITION'],'VEC3',{5126});require(sum(map(len,points.values()))+len(pos)<=1000000,'vertex_budget')
            for key in ('POSITION','NORMAL','TANGENT'):
                if key not in attrs:continue
                old=attrs[key];a=copy.deepcopy(d['accessors'][old]);d['accessors'].append(a);new=len(d['accessors'])-1
                values=g.values(old,'VEC4' if key=='TANGENT' else'VEC3',{5126});require(len(values)==len(pos),'attribute_count')
                out=[]
                for row in values:
                    if key=='POSITION':v=vector(row,s,r,True,t,mirror)
                    else:
                        v=vector(row,[1/q for q in s] if key=='NORMAL' else s,r,mirror=mirror);length=math.sqrt(sum(q*q for q in v));require(length>1e-15,'zero_direction');v=[q/length for q in v]
                    if key=='TANGENT':v.append(-row[3] if mirror else row[3])
                    out.append(v)
                g.replace(new,out);attrs[key]=new
                if key=='POSITION':points[wheel].extend(out)
            indices=g.values(p['indices'],'SCALAR',{5121,5123,5125});index_work+=len(indices)
            require(index_work<=1500000 and len(indices)%3==0 and all(row[0]<len(pos) for row in indices),'indices_budget_or_range')
            d['accessors'].append(copy.deepcopy(d['accessors'][p['indices']]));new=len(d['accessors'])-1
            if mirror:
                for i in range(0,len(indices),3):indices[i+1],indices[i+2]=indices[i+2],indices[i+1]
            g.replace(new,indices);p['indices']=new
        ni=len(nodes);groups.append((ni,wheel));nodes.append({'name':n.get('name','part'),'mesh':len(meshes),'extras':{'source_node':original,'source_extras':n.get('extras',{})}});meshes.append(mesh)
    require(points[-1] and all(points[i] for i in range(4)),'empty_body_or_wheel')
    body=points[-1];lower=[min(p[j]for p in body)for j in range(3)];upper=[max(p[j]for p in body)for j in range(3)];wheels=[];geometry=[]
    for i in range(4):
        c=centers[i][:]
        if mirror:c[2]=-c[2]
        cloud=points[i];radius=max(math.hypot(p[1]-c[1],p[2]-c[2])for p in cloud);width=2*max(abs(p[0]-c[0])for p in cloud)
        require(0<radius<2 and 0<width<2,'wheel_geometry_dimensions')
        if i in dimensions:
            sr,sw=dimensions[i];require(abs(radius-sr)<.05 and abs(width-sw)<.05,'source_wheel_dimension_mismatch');radius=max(radius,sr);width=max(width,sw)
        wheels.append({'label':LABELS[i],'center':c,'radius':radius,'width':width});geometry.append({'label':LABELS[i],'source_dimensions':dimensions.get(i),'bound_rule':'max radial distance and symmetric X extent about explicit native pivot; all rim+tire vertices','evidence':evidence[i]})
    lift=max(0,-lower[1],*(w['radius']-w['center'][1]for w in wheels));lower[1]+=lift;upper[1]+=lift
    for w in wheels:w['center'][1]+=lift
    require(all(lower[j]<upper[j]for j in range(3)) and upper[0]-lower[0]<=10 and upper[2]-lower[2]<=30 and upper[1]<=10,'body_bounds')
    require(all(lower[2]<=w['center'][2]<=upper[2]for w in wheels),'axle_outside_body')
    for i in (0,2):
        a,b=wheels[i:i+2];require(abs(a['center'][2]-b['center'][2])<1e-4 and abs(a['center'][1]-b['center'][1])<1e-4,'asymmetric_axle')
    nodes.append({'name':'racer_ground_lift','translation':[0,lift,0],'children':list(range(len(nodes)))})
    d.update(nodes=nodes,meshes=meshes,scene=0,scenes=[{'nodes':[len(nodes)-1]}]);d['buffers'][0]['byteLength']=len(binary)
    canonical={'status':'manufacturer_comparison_not_performed'}
    if catalog_id=='midnight-club-3-remix/vp_corvettez06_03':
        canonical={'status':'source_manufacturer_dimension_conflict','manufacturer_url':'https://www.gm.com/content/dam/company/no_search/heritage-archive-docs/vehicle-information-kits/chevrolet/2003-Chevrolet-Corvette.pdf','wheelbase_m_from_104_5_in':104.5*.0254,'length_m_from_179_7_in':179.7*.0254,'source_wheelbase_m':(wheels[0]['center'][2]+wheels[1]['center'][2]-wheels[2]['center'][2]-wheels[3]['center'][2])/2,'source_body_length_m':upper[2]-lower[2],'resolution':'No rescale applied; native PCK pivots byte-verified, native runtime frame behavior unknown.'}
    if catalog_id.startswith('gran-turismo/'):
        unit_authority={'source_glb':'pinned exporter metre convention from raw CAR /4096','native_units':'CAR raw unit /4096 convention, crosschecked with retained CARINF millimetre specifications','authority':'pinned gt_model.py and gt_wheels.py; native CARINF metadata','physical_unit_parity':'original game physical unit parity unproven'}
    elif catalog_id.startswith('midnight-club-3-remix/'):
        unit_authority={'source_glb':'source export coordinates; native physical units unverified','native_units':'unverified','authority':'native PCK float positions and pinned static exporter','chosen_import_factor':1.0,'factor_status':('authored import assumption; manufacturer comparison recorded separately and does not prove native units' if native_bones is not None else 'authored import assumption; manufacturer length and wheelbase conflict remains unresolved'),'physical_unit_parity':'unproven'}
    else:
        unit_authority={'source_glb':'metres from explicit native configuration authority','native_units':'metres','authority':'hash-matched native .car comments: Coordinates are in meters; X right, Y up, Z front','physical_unit_parity':'configuration authority verified; original runtime behavior unproven'}
    units=unit_authority|{'source_axes':'Y-up, -Z nose, -X left' if mirror else 'Y-up, +Z nose, -X left','prepared_axes':'Y-up, +Z nose, -X left','scale_applied':1.0,'normalization':'world-space node transform bake, Z reflection, rest ground lift' if mirror else 'world-space node transform bake, source Z retained, rest ground lift'}
    source=hashlib.sha256(data).hexdigest();d['extras']['racerPreparation']={'schema':1,'source_sha256':source,'catalog_id':catalog_id,'mirror_z':mirror,'ground_lift':lift,'adapter':'source-GT1-MC3-Redline-v1','canonical_scale':canonical,'units':units}
    prepared=pack(d,binary);digest=hashlib.sha256(prepared).hexdigest();num=lambda v:format(v,'.17g')
    lines=['RACER_VEHICLE 1','id '+json.dumps('vehicle-'+digest),'name '+json.dumps(name),'mesh '+json.dumps(digest+'.glb'),'sha256 '+digest,'source_sha256 '+source,'body '+' '.join(map(num,lower+upper))]
    lines+=['wheel '+w['label']+' '+' '.join(map(num,w['center']+[w['radius'],w['width']]))for w in wheels];lines+=['groups '+str(len(groups))]+['group '+str(n)+' '+str(w)for n,w in groups]
    receipt={'schema':1,'catalog_id':catalog_id,'source_sha256':source,'prepared_sha256':digest,'source_bytes':len(data),'prepared_bytes':len(prepared),'body':lower+upper,'wheels':wheels,'groups':groups,'wheel_geometry':geometry,'ground_lift':lift,'canonical_scale':canonical,'units':units,'body_dimensions':[upper[j]-lower[j] for j in range(3)],'vehicle_ground_dimensions':{'length':max(upper[2],*(w['center'][2]+w['radius'] for w in wheels))-min(lower[2],*(w['center'][2]-w['radius'] for w in wheels)),'width':max(upper[0],*(w['center'][0]+w['width']/2 for w in wheels))-min(lower[0],*(w['center'][0]-w['width']/2 for w in wheels)),'height':max(upper[1],*(w['center'][1]+w['radius'] for w in wheels)),'interpretation':'union of selected visible mesh body box and conservative wheel cylinders; width may include mirrors; height above authored rest ground'},'source_canonical_metadata':copy.deepcopy(d['extras'].get('nativeMetadata')),'wheelbase':(wheels[0]['center'][2]+wheels[1]['center'][2]-wheels[2]['center'][2]-wheels[3]['center'][2])/2,'source_claim_limits':d['extras'].get('claim_limits',[]),'limitations':['Source static rest poses; supplied original runtime behavior and physics not executed.','Wheel cylinders conservatively enclose selected original rim/tire geometry; no donor mass/grip inferred.','Embedded textures/materials preserved; original shading equivalence unverified.']}
    return prepared,'\n'.join(lines)+'\n',receipt

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('--id',required=True);p.add_argument('--name',required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--native-config',type=Path);a=p.parse_args()
    require(not a.source.is_symlink() and stat.S_ISREG(a.source.stat().st_mode),'source_nonregular');require(a.source.stat().st_size<=MAX_SOURCE,'source_size')
    fd=os.open(a.source,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(fd,'rb') as stream:
        before=os.fstat(stream.fileno());data=stream.read(MAX_SOURCE+1);after=os.fstat(stream.fileno())
    require(stat.S_ISREG(before.st_mode) and (before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns) and len(data)==before.st_size,'source_changed')
    native=None
    if a.native_config:
        require(not a.native_config.is_symlink() and a.native_config.stat().st_size<=65536,'native_config_bounds')
        with a.native_config.open('rb') as f:native=f.read(65537)
    prepared,descriptor,receipt=prepare(data,a.id,a.name,native)
    require(shutil.disk_usage(a.output.parent).free>=20*1024**3,'free_space')
    require(not a.output.exists() and not any(p.is_symlink()for p in (a.output,*a.output.parents)),'output_exists_or_symlink');a.output.mkdir(mode=0o700)
    for suffix,payload in [('.glb',prepared),('.vehicle',descriptor.encode()),('.json',json.dumps(receipt,indent=2).encode())]:
        with (a.output/(receipt['prepared_sha256']+suffix)).open('xb')as f:f.write(payload)
    print(json.dumps(receipt,indent=2))
if __name__=='__main__':main()
