#!/usr/bin/env python3
"""Opt-in source-backed MC3 exhaust at named native rest anchors; no runtime activation claim."""
import argparse, copy, hashlib, importlib.util, json, math, os, shutil, signal, struct
from pathlib import Path
from prepare_gt4_vehicle import require, unpack, pack
from prepare_mcla_vehicle import read_regular
from repair_mc3_vehicle import archive, frames, rotate
from mc3_cohort_glass import rewrite_descriptor
import prepare_mc3_vehicle as wrapper
from verification_lifecycle import VerificationLifecycle

ROOT=Path(__file__).resolve().parents[1]
COHORT=ROOT/'experiments/2026-11-06-mc3-cohort/output'
SHARED=ROOT/'experiments/2026-11-06-mc3-coverage/output'
OUTPUT=ROOT/'experiments/2026-11-06-mc3-attachments/output'
CAP=12*1024**2
sha=lambda b:hashlib.sha256(b).hexdigest()
SHARED_PINS={'exhaust.ppf':'04245775454c5de72ecdb0743f5c30264778f506a402a93c346e08651c3734d7','decal.pck':'38b61142202993ae2233026ac7f804296f88622fbe7680f57825045912ca7c0a','customexhausts.txt':'379dc7b469af2b8d0e0ceb1c4e9848e291169834375ecf35466e39e2d7c393e1'}
PINS={'vp_saleen_sr_00': {'mesh': '55f268651bb9b80f8e501483102d716013f9f3a49b7a211ae9d53401fcf47eda',
                     'descriptor': 'a02b94b4353513343fcfdae5bbfe55842e7d68564ee9a6af244a50a92b02b6d4',
                     'receipt': 'd0635a5c6e7a07431be6242de6c13c271ddc37e3d1d82ef7b80dd7d5e35263d0',
                     'config': 'cc0feb80493522823815421178094c1949d9bc6c5a8a0e5e50081207a920aeda',
                     'dat': 'a0a5bb048fa45d8f22260d1de60e88718e5171fb1d42c1cb0e332d2b80b4cac8',
                     'pck': '0349a88b8bccb5cb946a5e3429fb9fe9b3266589319f997f95e6ec92bdbeb54b',
                     'source': '0667e928af5946dd298503d6b33da725c976ee06e6af158d4b3894383c9f176a',
                     'index': 26,
                     'name': 'ext_saleen_sr_00',
                     'adapter': '6b1269a26b7b7cb954a4e00cdb9eee4a2d0ad7cadaa350c9d59baca14540eab4',
                     'positions': 60,
                     'indices': 144,
                     'anchors': ['exhst_0', 'exhst_1']},
 'vp_viper_03': {'mesh': '30e76a041dd61622b79845b3b9aee326e476c9cce5e12f507b319f254c49f2e3',
                 'descriptor': 'f9c54e0a28b13bd30ec8a1cb0d9cfbe97b714da9dbb30c3eefc6d43574262db5',
                 'receipt': '3d3fed2e9244d2d8a9fc97c833471699f7c09610bb991c7e79fe45de6a392514',
                 'config': 'd389f6c88a4b897a929f8e80e24630f844e6e1688780e1965113fdc1a93a1bd2',
                 'dat': 'b9e0235888008978fab325075c5711fde6f0bced507182f60a6cff9670e4188e',
                 'pck': 'fc090376ac20166e0014b0f5948b2e36e68b8853b23e7a4d848037b06388fdbb',
                 'source': '8a863c83fc3c2d6afd66e786b40a943de8a732dda21bb6d1d1ddbbab14ac7895',
                 'index': 2,
                 'name': 'ext03_kng_m643330',
                 'adapter': 'e8d5301264270716a21162a813c77ca76a7f5b447ae2e47359e8116b9185c69f',
                 'positions': 109,
                 'indices': 264,
                 'anchors': []},
 'vp_esprit_04': {'mesh': 'c9ad8b932d2135eccf723dd6a8be9c0cf44d783af86605fecd3ef908727316a2',
                  'descriptor': '299c851bc5948820c73f699f1123320f004008b8488f01f24172efb5c209668f',
                  'receipt': 'af45700a4a4c4be030a0b07ac340337b2d44db5f83415953be4b422a4ff2b06a',
                  'config': 'a4f4f58690110b16e6020c7ab66b25c18f6b06283526de5897cc139c5a41f86a',
                  'dat': '333d07e21328ec21396250848adff79277ef7d384d48b845602af04477cc1186',
                  'pck': 'a1b40a11802051cbf4fc5832a12eca1429691c6f5edcf206facad819c624e536',
                  'source': '1b6ad10f7cb439faf8381a65f268c0d2dbc35aa7a64841042a5f1cab63f279eb',
                  'index': 13,
                  'name': 'ext_esprit_04',
                  'adapter': '572c6e27760e8c9eb20556eafce5e0ba53d8d625b88082deba0e3acaadab8f77',
                  'positions': 76,
                  'indices': 168,
                  'anchors': ['Exhst_0', 'Exhst_1']}}


def reader_module():
    data=read_regular(wrapper.READER,1024**2);require(sha(data)==wrapper.READER_SHA,'reader_pin')
    spec=importlib.util.spec_from_file_location('pinned_mc3_attachment_reader',wrapper.READER)
    reader=importlib.util.module_from_spec(spec);spec.loader.exec_module(reader);return reader


def decode(reader, code):
    pin=PINS[code];raw={n:read_regular(SHARED/n,1024**2)for n in SHARED_PINS}
    require(all(sha(raw[n])==digest for n,digest in SHARED_PINS.items()),'shared_input_pins')
    names=[line.strip()for line in raw['customexhausts.txt'].decode('ascii').splitlines()if line.strip()not in('exhausts','{','}')]
    index=pin['index'];require(len(names)==64 and names[index]==pin['name'],'custom_list_join')
    lib=reader.Pck(raw['decal.pck']);require(lib.kind==0x25,'library_profile')
    collection=lib.pointer(lib.u32(128+0x38),8);require(lib.u32(collection+4)==64,'library_count')
    array=lib.pointer(lib.u32(collection),256);library_array=array;row=lib.pointer(lib.u32(array+4*index),16)
    handle=lib.u32(row+12);require(lib.u32(row)==0x7AA718 and handle==((2<<23)|index),'library_handle')
    ppf=raw['exhaust.ppf'];require(ppf[:4]==b'pf05'and struct.unpack_from('<I',ppf,4)[0]==64,'PPF_profile')
    word=struct.unpack_from('<I',ppf,12+4*index)[0];start=(word&0x7ffff)<<11;size=(word>>20)<<11
    require(start>=268 and 0<size<=16384 and start+size<=len(ppf),'PPF_page_range');candidates=[]
    for root in range(start+32,start+size-108,16):
        if struct.unpack_from('<I',ppf,root)[0]!=0x7AA728:continue
        base,kind,version,length=struct.unpack_from('<4I',ppf,root-32)
        if base and kind==0 and version==0 and 108<=length and root+length<=start+size:candidates.append((root,base,length))
    require(len(candidates)==1,'model_root');root,base,length=candidates[0]
    adapter=struct.pack('<4I',base,0,1,length)+bytes(112)+ppf[root:root+length]
    require(sha(adapter)==pin['adapter'],'model_adapter_pin');model=reader.Pck(adapter)
    group=model.pointer(model.u32(144),12);count=model.u16(group+2)
    require(model.u16(group)==0 and model.u32(group+4)==0x7A2228 and 0<count<=16,'mesh_collection')
    array=model.pointer(model.u32(group+8),4*count);mc=model.pointer(model.u32(136),20)
    require(model.u16(mc+8)==2,'material_count');ma=model.pointer(model.u32(mc+4),8);materials=[]
    for i in range(2):
        at=model.pointer(model.u32(ma+i*4),32)
        materials.append({'index':i,'vtable':model.u32(at),'PPF_offset':root+at-128,'first_32_bytes':adapter[at:at+32].hex()})
    require([m['vtable']for m in materials]==[8042160,8004576],'material_profile');draws=[];nv=ni=0
    for i in range(count):
        mesh=reader.read_mesh_object(model,model.pointer(model.u32(array+i*4),24))
        for draw in mesh['draws']:
            points=[];indices=[];uv=[]
            for batch in draw['batches']:
                local=reader.strip_indices(batch);indices.extend(x+len(points)for x in local)
                points.extend(batch['positions']);uv.extend(batch.get('uvs',[]))
            nv+=len(points);ni+=len(indices)
            require(draw['material']in(0,1)and 0<len(points)<=4096 and 0<len(indices)<=16384 and nv<=8192 and ni<=32768,'draw_budget')
            require(len(indices)%3==0 and all(0<=x<len(points)for x in indices),'draw_indices')
            at=root+draw['packet_offset']-128;end=at+draw['packet_bytes']
            require(start<=at<end<=start+size,'packet_range')
            draws.append({'positions':points,'indices':indices,'uv':uv,'material':draw['material'],
                          'packet_PPF_offset':at,'packet_bytes':draw['packet_bytes'],'packet_sha256':sha(ppf[at:end])})
    require(len(draws)==2 and nv==pin['positions'] and ni==pin['indices'],'geometry_pin')
    proof={'shared_sources':SHARED_PINS,'name':names[index],'config_index':index,'collection_root_field':'0x38',
           'library_collection':collection,'library_array':library_array,'decal_handle_row':row,'native_handle':handle,
           'page_index':index,'PPF_page_offset':start,'PPF_page_bytes':size,'PPF_model_root':root,
           'PPF_model_bytes':length,'adapter_sha256':sha(adapter),'native_materials':materials,
           'draws':[{k:v for k,v in d.items()if k not in('positions','indices','uv')}|{'position_count':len(d['positions']),'index_count':len(d['indices'])}for d in draws]}
    return draws,proof


def source_inputs(code, reader):
    require(code in PINS,'unsupported_source');pin=PINS[code];folder=COHORT/'glass-v2'/code
    paths={'mesh':folder/(pin['mesh']+'.glb'),'descriptor':folder/(pin['mesh']+'.vehicle'),
           'receipt':folder/(pin['mesh']+'.json'),'config':COHORT/'batch-v1'/code/'default.carcfg',
           'dat':COHORT/'batch-v1'/code/'source.dat','pck':COHORT/'batch-v2'/code/'main.pck'}
    data={k:read_regular(p,32768 if k in('descriptor','config')else 1024**2 if k=='receipt'else 16*1024**2)for k,p in paths.items()}
    require(sum(map(len,data.values()))<=32*1024**2 and all(sha(v)==pin[k]for k,v in data.items()),'source_input_pins')
    cfg={}
    for line in data['config'].decode('ascii').splitlines():
        words=line.split()
        if len(words)==2:require(words[0]not in cfg,'duplicate_config');cfg[words[0]]=words[1]
    require(cfg.get('TypeName')==code and cfg.get('ExhaustRear')==str(pin['index'])and cfg.get('UseSideExhaust')=='0','native_config_contract')
    members=[m for m in archive(data['dat'])if Path(m['name']).name==code+'.pck']
    require(len(members)==1,'main_member');m=members[0]
    require(data['dat'][m['offset']:m['offset']+m['size']]==data['pck'],'DAT_PCK_join')
    require(read_regular(paths['pck'],16*1024**2)==data['pck'],'pck_changed_before_decode')
    bones=json.loads(json.dumps(reader.read_vehicle(paths['pck'])['skeleton']['bones']))
    require(read_regular(paths['pck'],16*1024**2)==data['pck'],'pck_changed_after_decode')
    for b in bones:
        at=b['offset'];require(0<=at<=len(data['pck'])-68,'bone_range')
        require(struct.unpack_from('<H',data['pck'],at+56)[0]==b['index'],'raw_bone_index')
        for key,delta in(('global_position',0),('local_position',32),('rotation_raw',44)):
            require(list(struct.unpack_from('<3f',data['pck'],at+delta))==b[key],'raw_bone_pose')
    receipt=json.loads(data['receipt']);require(receipt['source_sha256']==pin['source']and receipt['prepared_sha256']==pin['mesh'],'receipt_join')
    proof={'code':code,'source_sha256':pin['source'],'prepared_input_sha256':pin['mesh'],'source_inputs':{k:sha(v)for k,v in data.items()},'native_config_fields':{k:v for k,v in cfg.items()if k.startswith('Exhaust')or k in('TypeName','UseSideExhaust')},'native_bones':bones,'reader_sha256':wrapper.READER_SHA}
    return data['mesh'],data['descriptor'].decode(),receipt,bones,proof


def anchor_frames(bones, code):
    names=PINS[code]['anchors'];require(len(names)==2,'unresolved_native_attachment_anchors')
    matches=[b for b in bones if b['name']in names]
    require(len(matches)==2 and {b['name']for b in matches}==set(names),'named_anchor_contract')
    rest=frames(bones);out=[]
    for name in names:
        b=next(b for b in matches if b['name']==name);t,q=rest[b['index']]
        require(max(abs(t[k]-b['global_position'][k])for k in range(3))<1e-5,'rest_global_join')
        out.append((b,t,q))
    return out


def attach(mesh, text, receipt, bones, code, draws, source_proof):
    pin=PINS[code];require(sha(mesh)==pin['mesh']and sha(text.encode())==pin['descriptor'],'prepared_input_identity')
    anchors=anchor_frames(bones,code);d,b=unpack(mesh);before=copy.deepcopy(d);old_binary=bytes(b);receipt=copy.deepcopy(receipt)
    require(receipt['source_sha256']==pin['source'] and receipt['prepared_sha256']==pin['mesh'],'attachment_receipt_identity')
    roots=d['scenes'][d.get('scene',0)]['nodes'];require(len(roots)==1,'single_ground_root');root=roots[0]
    require(d['nodes'][root].get('name')=='racer_ground_lift' and d['nodes'][root].get('translation')==[0,receipt['ground_lift'],0]
            and not any(k in d['nodes'][root]for k in('matrix','rotation','scale')),'ground_root_contract')
    require('racerCohortExhaustPolicy'not in d['extras'],'already_attached')
    material_start=len(d['materials'])
    for i,vt,factor,metallic,roughness in ((0,8042160,[.42,.44,.46,1],1.,.25),(1,8004576,[.025,.025,.025,1],0.,.85)):
        d['materials'].append({'name':'Racer source exhaust '+('chrome'if i==0 else'black matte'),
            'pbrMetallicRoughness':{'baseColorFactor':factor,'metallicFactor':metallic,'roughnessFactor':roughness},
            'extras':{'native_material_index':i,'native_vtable':vt,'native_PPF_sha256':SHARED_PINS['exhaust.ppf'],
                      'authority':'Authored PBR interpretation; native wrapper/GS shader behavior is not recovered.'}})
    def add(values,typ,fmt,component):
        b.extend(bytes(-len(b)%4));at=len(b)
        for v in values:b.extend(struct.pack('<'+fmt,*v))
        d['bufferViews'].append({'buffer':0,'byteOffset':at,'byteLength':len(b)-at})
        a={'bufferView':len(d['bufferViews'])-1,'componentType':component,'count':len(values),'type':typ}
        if typ=='VEC3':a.update(min=[min(v[k]for v in values)for k in range(3)],max=[max(v[k]for v in values)for k in range(3)])
        d['accessors'].append(a);return len(d['accessors'])-1
    attachments=[];world=[]
    for bone,t,q in anchors:
        primitives=[]
        for draw in draws:
            points=[]
            for v in draw['positions']:
                u=rotate(q,v);points.append([u[0]+t[0],u[1]+t[1],-(u[2]+t[2])])
            ids=draw['indices'][:]
            for at in range(0,len(ids),3):ids[at+1],ids[at+2]=ids[at+2],ids[at+1]
            normals=[[0.,0.,0.]for _ in points]
            for at in range(0,len(ids),3):
                a,c,e=[points[k]for k in ids[at:at+3]];u=[c[k]-a[k]for k in range(3)];v=[e[k]-a[k]for k in range(3)]
                n=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
                for k in ids[at:at+3]:normals[k]=[normals[k][j]+n[j]for j in range(3)]
            normals=[[v/math.sqrt(sum(x*x for x in n))for v in n]if sum(x*x for x in n)>1e-24 else[0.,1.,0.]for n in normals]
            attrs={'POSITION':add(points,'VEC3','3f',5126),'NORMAL':add(normals,'VEC3','3f',5126)}
            if len(draw['uv'])==len(points):attrs['TEXCOORD_0']=add(draw['uv'],'VEC2','2f',5126)
            primitives.append({'attributes':attrs,'indices':add([(i,)for i in ids],'SCALAR','I',5125),'material':material_start+draw['material']})
            world.extend([p[0],p[1]+receipt['ground_lift'],p[2]]for p in points)
        node=len(d['nodes']);d['nodes'].append({'name':'Racer source exhaust '+bone['name'],'mesh':len(d['meshes']),
            'extras':{'native_bone':bone['index'],'native_name':bone['name'],'native_handle':source_proof['native_handle'],'native_PPF_sha256':SHARED_PINS['exhaust.ppf']}})
        d['meshes'].append({'name':pin['name']+' '+bone['name'],'primitives':primitives})
        d['nodes'][root]['children'].append(node);receipt['groups'].append([node,-1])
        attachments.append({'node':node,'native_bone':bone['index'],'name':bone['name'],'translation':t,'quaternion':q,'scale':[1,1,1],'raw_bone_offset':bone['offset']})
    require(len(d['nodes'])<=4096 and len(b)<16*1024**2,'output_geometry_budget')
    body=receipt['body'][:]
    for k in range(3):body[k]=min(body[k],*(p[k]for p in world));body[k+3]=max(body[k+3],*(p[k]for p in world))
    policy={'authority':'Source-informed Racer-authored static attachment. Native runtime index activation and sizing consumers are not traced.',
            'source_prepared_sha256':pin['mesh'],'native_source_proof':source_proof,'attachments':attachments,
            'positions_per_instance':pin['positions'],'triangles_per_instance':pin['indices']//3,
            'normalization':'Full native local rest chain, scale1, existing Z reflection and ground lift; no position or shape tuning.',
            'material_limit':'Two appended authored PBR interpretations; original materials/images unchanged; normals generated from triangles.',
            'unit_limit':'Existing factor1 interpretation remains unproved; no manufacturer calibration or player eligibility.'}
    d['buffers'][0]['byteLength']=len(b);d['extras']['racerCohortExhaustPolicy']=policy
    # Require the full old document to be recoverable by removing only named appendages and bookkeeping.
    restored=copy.deepcopy(d);del restored['extras']['racerCohortExhaustPolicy']
    for key in('nodes','meshes','materials','accessors','bufferViews'):restored[key]=restored[key][:len(before[key])]
    restored['nodes'][root]=before['nodes'][root];restored['buffers']=before['buffers']
    require(restored==before and bytes(b[:len(old_binary)])==old_binary,'old_geometry_preservation')
    result=pack(d,b);digest=sha(result)
    text=rewrite_descriptor(text,pin['mesh'],digest,pin['source']);lines=[]
    for line in text.splitlines():
        if line.startswith(('groups ','group ')):continue
        if line.startswith('body '):line='body '+' '.join(format(x,'.17g')for x in body)
        lines.append(line)
    lines+=['groups '+str(len(receipt['groups']))]+['group '+str(i)+' '+str(w)for i,w in receipt['groups']]
    receipt.update(prepared_sha256=digest,prepared_bytes=len(result),body=body,body_dimensions=[body[k+3]-body[k]for k in range(3)],
        runtime_player_eligible=False,source_prepared_sha256=pin['mesh'],source_BIN_prefix_bytes=len(old_binary),
        cohort_exhaust_policy=policy,auxiliary_source_sha256=SHARED_PINS)
    # Update the conservative union rather than leaving old ground dimensions stale.
    bounds=[body[:3],body[3:]]
    for wheel in receipt['wheels']:
        c=wheel['center'];r=wheel['radius'];hw=wheel['width']/2
        for k,e in enumerate((hw,r,r)):bounds[0][k]=min(bounds[0][k],c[k]-e);bounds[1][k]=max(bounds[1][k],c[k]+e)
    receipt['vehicle_ground_dimensions'].update(width=bounds[1][0]-bounds[0][0],length=bounds[1][2]-bounds[0][2],height=bounds[1][1])
    return result,'\n'.join(lines)+'\n',receipt


def prepare(code):
    reader=reader_module();mesh,text,receipt,bones,proof=source_inputs(code,reader);draws,shared=decode(reader,code)
    proof['shared_exhaust']=shared
    if not PINS[code]['anchors']:
        proof.update(status='held_no_proven_native_attachment_frame',reason='No exhaust-named bone in the exact native skeleton. Nitro/effect anchors are not used as mesh attachment guesses.')
        return None,None,None,proof
    result,definition,receipt=attach(mesh,text,receipt,bones,code,draws,shared)
    proof.update(status='prepared_research_candidate',prepared_sha256=receipt['prepared_sha256'],runtime_player_eligible=False)
    return result,definition,receipt,proof


def retained_size(root):
    total=0
    for p in root.rglob('*'):
        require(not p.is_symlink(),'output_symlink')
        if p.is_file():total+=p.stat().st_size
    return total


def write(path,data):
    require(retained_size(OUTPUT)+len(data)<=CAP,'leaf_budget_before_write')
    with os.fdopen(os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'wb')as f:f.write(data)


def prepare_payloads(output, lifecycle):
    payloads=[];rows=[]
    for code in PINS:
        lifecycle.record['active_model']=code;lifecycle.phase('retrieval')
        mesh,text,receipt,proof=prepare(code);lifecycle.phase('validation')
        row={'code':code,'status':proof['status'],'runtime_player_eligible':False}
        payloads.append((Path(code)/'native-proof.json',(json.dumps(proof,indent=2)+'\n').encode()))
        if mesh is not None:
            digest=receipt['prepared_sha256'];row.update(prepared_sha256=digest,descriptor=str((output/code/(digest+'.vehicle')).resolve()))
            payloads.extend((Path(code)/(digest+ext),data)for ext,data in(('.glb',mesh),('.vehicle',text.encode()),('.json',(json.dumps(receipt,indent=2)+'\n').encode())))
        rows.append(row)
    manifest={'schema':1,'models':rows,'source_tool_sha256':sha(Path(__file__).read_bytes()),'cap_bytes':CAP,
              'scope':'Two optional named-anchor static assemblies and one explicit unresolved placement hold. No native-game, scale, stock activation or player-eligibility claim.'}
    payloads.append((Path('manifest.json'),(json.dumps(manifest,indent=2)+'\n').encode()))
    return payloads,manifest


def run(output):
    output=Path(output)
    require(output.parent==OUTPUT and not output.exists()and not any(p.is_symlink()for p in(output,*output.parents)),'fresh_output_under_leaf')
    require(shutil.disk_usage(OUTPUT).free>=20*1024**3,'free_space')
    # Reserve bounded sidecar space before creating the fresh attempt folder.
    require(retained_size(OUTPUT)+65536<=CAP,'lifecycle_budget')
    output.mkdir(mode=0o700);lifecycle=VerificationLifecycle(output)
    lifecycle.record['requested_sources']=[{'code':c,'source_sha256':p['source'],'prepared_sha256':p['mesh'],'config_sha256':p['config']}for c,p in PINS.items()]
    with lifecycle:
        payloads,manifest=prepare_payloads(output,lifecycle)
        lifecycle.record['active_model']=None;lifecycle.checkpoint()
        require(all(len(b)<=12*1024**2 for _,b in payloads)and retained_size(OUTPUT)+sum(len(b)for _,b in payloads)+65536<=CAP,'complete_payload_budget')
        lifecycle.phase('capture')
        for code in PINS:
            lifecycle.record['active_model']=code;lifecycle.checkpoint()
            (output/code).mkdir(mode=0o700)
        for path,data in payloads:
            lifecycle.record['active_model']=path.parts[0]if len(path.parts)>1 else None
            lifecycle.checkpoint()
            write(output/path,data)
        lifecycle.complete()
    return manifest


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    def deadline(signum,frame):raise TimeoutError('attachment_deadline')
    signal.signal(signal.SIGALRM,deadline);signal.alarm(290)
    try:print(json.dumps(run(args.output.absolute()),indent=2))
    finally:signal.alarm(0)
