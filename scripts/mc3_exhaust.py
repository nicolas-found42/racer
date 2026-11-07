#!/usr/bin/env python3
"""Source-informed authored MC3 350Z static exhaust; runtime activation unproved."""
import hashlib,json,math,struct
from pathlib import Path
from prepare_gt4_vehicle import require,unpack,pack
from prepare_mcla_vehicle import read_regular
from repair_mc3_vehicle import frames,rotate
ROOT=Path(__file__).resolve().parents[1];LEAF=ROOT/'experiments/2026-11-06-mc3-coverage/output'
PINS={'exhaust.ppf':'04245775454c5de72ecdb0743f5c30264778f506a402a93c346e08651c3734d7','decal.pck':'38b61142202993ae2233026ac7f804296f88622fbe7680f57825045912ca7c0a','customexhausts.txt':'379dc7b469af2b8d0e0ceb1c4e9848e291169834375ecf35466e39e2d7c393e1','350z-default.carcfg':'5bac8cee6ec9bafe334eebc26ae0e24145b2762c46763016733111a6ff20c066'}
SOURCE='8a1b7ba44d38815c6c491d3caf9e3b139dbf51c9d74d4c9546b2ee3164d48383'
sha=lambda data:hashlib.sha256(data).hexdigest()

def decode(reader):
    raw={name:read_regular(LEAF/name,1024**2)for name in PINS}
    require(all(sha(raw[name])==digest for name,digest in PINS.items()),'exhaust_input_pins')
    names=[line.strip()for line in raw['customexhausts.txt'].decode().splitlines()if line.strip()not in('exhausts','{','}')]
    fields={}
    for line in raw['350z-default.carcfg'].decode().splitlines():
        tokens=line.split()
        if len(tokens)==2:require(tokens[0]not in fields,'duplicate_exhaust_config_field');fields[tokens[0]]=tokens[1]
    require(fields.get('TypeName')=='vp_350z_04'and fields.get('ExhaustRear')=='5'and fields.get('UseSideExhaust')=='0'and len(names)==64 and names[5]=='ext_350z_04','exhaust_config_join')
    library=reader.Pck(raw['decal.pck']);require(library.kind==0x25,'exhaust_library_kind');collection=library.pointer(library.u32(128+0x38),8);require(library.u32(collection+4)==64,'exhaust_library_count');array=library.pointer(library.u32(collection),256);row=library.pointer(library.u32(array+20),16);require(library.u32(row)==0x7AA718,'exhaust_handle_class');handle=library.u32(row+12);require(handle==16777221,'exhaust_handle_pin')
    ppf=raw['exhaust.ppf'];require(ppf[:4]==b'pf05'and struct.unpack_from('<I',ppf,4)[0]==64,'exhaust_ppf_profile');word=struct.unpack_from('<I',ppf,12+4*(handle&0x7fffff))[0];start=(word&0x7ffff)<<11;size=(word>>20)<<11;require(start>=268 and 0<size<=16384 and start+size<=len(ppf),'exhaust_page_range');candidates=[]
    for root in range(start+32,start+size-108,16):
        if struct.unpack_from('<I',ppf,root)[0]!=0x7AA728:continue
        base,kind,version,length=struct.unpack_from('<4I',ppf,root-32)
        if base and kind==0 and version==0 and 108<=length and root+length<=start+size:candidates.append((root,base,length))
    require(len(candidates)==1,'exhaust_model_root');root,base,length=candidates[0];adapter=struct.pack('<4I',base,0,1,length)+bytes(112)+ppf[root:root+length];model=reader.Pck(adapter);group=model.pointer(model.u32(144),12);count=model.u16(group+2);require(model.u16(group)==0 and model.u32(group+4)==0x7A2228 and 0<count<=16,'exhaust_mesh_collection');array=model.pointer(model.u32(group+8),4*count);draws=[]
    mc=model.pointer(model.u32(136),20);require(model.u16(mc+8)==2,'exhaust_material_count');ma=model.pointer(model.u32(mc+4),8);vtables=[model.u32(model.pointer(model.u32(ma+i*4)))for i in range(2)];require(vtables==[8042160,8004576],'exhaust_material_pins')
    for i in range(count):
        mesh=reader.read_mesh_object(model,model.pointer(model.u32(array+i*4),24))
        for draw in mesh['draws']:
            points=[];indices=[];uv=[]
            for batch in draw['batches']:
                local=reader.strip_indices(batch);indices.extend(x+len(points)for x in local);points.extend(batch['positions']);uv.extend(batch.get('uvs',[]))
            require(draw['material']in(0,1)and 0<len(points)<=4096 and 0<len(indices)<=16384,'exhaust_draw_budget');draws.append({'positions':points,'indices':indices,'uv':uv,'material':draw['material'],'packet_PPF_offset':root+draw['packet_offset']-128})
    require(len(draws)==2 and sum(len(d['positions'])for d in draws)==105 and sum(len(d['indices'])for d in draws)==204,'exhaust_geometry_pin')
    return draws,{'sources':PINS,'source_name':names[5],'config_index':5,'library_collection_root_field':'0x38','library_handle_row':row,'native_handle':handle,'archive_code':2,'PPF_page':5,'PPF_page_offset':start,'PPF_model_root':root,'PPF_model_bytes':length,'native_material_vtables':vtables,'adapter_sha256':sha(adapter),'PPF_offset_rule':'model_root + adapter_offset -128'}

def attach(mesh,descriptor,receipt,bones,reader):
    require(receipt['source_sha256']==SOURCE,'exhaust_source');d,b=unpack(mesh);old_length=len(b);root=d['scenes'][0]['nodes'];require(len(root)==1,'exhaust_scene');root=root[0];require(d['nodes'][root].get('name')=='racer_ground_lift'and d['nodes'][root].get('translation')==[0,receipt['ground_lift'],0],'exhaust_ground_root');draws,proof=decode(reader);rest=frames(bones);anchors={bone['name']:bone for bone in bones if bone['name']in('exst0','exst1')};require(len(anchors)==2,'exhaust_anchors')
    # New PBR materials are explicitly authored; native wrapper shader0 and GS
    # reflection/lighting are not substituted with a claim of shader parity.
    material_start=len(d['materials']);d['materials'] += [{'name':'Racer native-exhaust chrome interpretation','pbrMetallicRoughness':{'baseColorFactor':[.42,.44,.46,1],'metallicFactor':1.,'roughnessFactor':.25},'extras':{'sourcePPF':PINS['exhaust.ppf'],'sourceMaterialIndex':0,'sourceVtable':8042160,'authority':'Authored PBR interpretation; original wrapper/GS shading unresolved.'}},{'name':'Racer native-exhaust black-matte interpretation','pbrMetallicRoughness':{'baseColorFactor':[.025,.025,.025,1],'metallicFactor':0.,'roughnessFactor':.85},'extras':{'sourcePPF':PINS['exhaust.ppf'],'sourceMaterialIndex':1,'sourceVtable':8004576,'authority':'Authored PBR interpretation; native black_matte shader identity, GS shading unresolved.'}}]
    def add(values,typ,fmt,component):
        b.extend(bytes(-len(b)%4));at=len(b)
        for row in values:b.extend(struct.pack('<'+fmt,*row))
        d['bufferViews'].append({'buffer':0,'byteOffset':at,'byteLength':len(b)-at});accessor={'bufferView':len(d['bufferViews'])-1,'componentType':component,'count':len(values),'type':typ}
        if typ=='VEC3':accessor.update(min=[min(v[i]for v in values)for i in range(3)],max=[max(v[i]for v in values)for i in range(3)])
        d['accessors'].append(accessor);return len(d['accessors'])-1
    added=[];world_points=[]
    for name in('exst0','exst1'):
        bone=anchors[name];t,q=rest[bone['index']];require(max(abs(t[i]-bone['global_position'][i])for i in range(3))<1e-5,'exhaust_rest_translation');primitives=[]
        for draw in draws:
            points=[]
            for point in draw['positions']:
                v=rotate(q,point);points.append([v[0]+t[0],v[1]+t[1],-(v[2]+t[2])])
            indices=draw['indices'][:]
            for i in range(0,len(indices),3):indices[i+1],indices[i+2]=indices[i+2],indices[i+1]
            normals=[[0.,0.,0.]for _ in points]
            for i in range(0,len(indices),3):
                a,c,e=[points[k]for k in indices[i:i+3]];u=[c[j]-a[j]for j in range(3)];v=[e[j]-a[j]for j in range(3)];n=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
                for k in indices[i:i+3]:normals[k]=[normals[k][j]+n[j]for j in range(3)]
            normals=[[v/math.sqrt(sum(x*x for x in n))for v in n]if sum(x*x for x in n)>1e-24 else[0.,1.,0.]for n in normals];attrs={'POSITION':add(points,'VEC3','3f',5126),'NORMAL':add(normals,'VEC3','3f',5126)}
            if len(draw['uv'])==len(points):attrs['TEXCOORD_0']=add(draw['uv'],'VEC2','2f',5126)
            primitives.append({'attributes':attrs,'indices':add([(i,)for i in indices],'SCALAR','I',5125),'material':material_start+draw['material']});world_points.extend([p[0],p[1]+receipt['ground_lift'],p[2]]for p in points)
        node=len(d['nodes']);d['nodes'].append({'name':'Racer_source_exhaust_'+name,'mesh':len(d['meshes']),'extras':{'nativeBone':bone['index'],'sourcePPF':PINS['exhaust.ppf'],'nativeHandle':16777221}});d['meshes'].append({'name':'source_ext_350z_04_'+name,'primitives':primitives});d['nodes'][root]['children'].append(node);receipt['groups'].append((node,-1));added.append({'node':node,'native_bone':bone['index'],'native_name':name,'native_translation':t,'native_rotation_quaternion':q,'scale':[1,1,1]})
    body=receipt['body'][:]
    for i in range(3):body[i]=min(body[i],*(p[i]for p in world_points));body[i+3]=max(body[i+3],*(p[i]for p in world_points))
    require(len(b)<=16*1024**2,'exhaust_output_budget');d['buffers'][0]['byteLength']=len(b);policy={'authority':'Source-informed Racer-authored static exhaust attachment; native runtime activation/index consumer not independently traced','source_association':proof,'attachments':added,'source_positions_per_instance':105,'source_triangles_per_instance':68,'normalization':'Native local positions and full native rest bone frames, then existing Z reflection/ground lift; factor1 retained; no placement or scale tuning.','material_authority':'Two explicit appended PBR interpretations; all original materials/images unchanged; native GS parity unproved.'};d['extras']['racerStaticExhaustPolicy']=policy;old=receipt['prepared_sha256'];prepared=pack(d,b);digest=sha(prepared);receipt['prepared_sha256']=digest;receipt['prepared_bytes']=len(prepared);receipt['body']=body;receipt['body_dimensions']=[body[i+3]-body[i]for i in range(3)];receipt['static_exhaust_policy']=policy;receipt['auxiliary_source_sha256']=PINS;receipt['source_BIN_prefix_bytes']=old_length
    lines=descriptor.splitlines();num=lambda x:format(x,'.17g');lines=[line.replace(old,digest)for line in lines if not line.startswith('groups ')and not line.startswith('group ')];lines=[('body '+' '.join(map(num,body)))if line.startswith('body ')else line for line in lines];lines+=['groups '+str(len(receipt['groups']))]+['group '+str(i)+' '+str(w)for i,w in receipt['groups']]
    return prepared,'\n'.join(lines)+'\n',receipt
