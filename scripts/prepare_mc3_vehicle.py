#!/usr/bin/env python3
"""Prepare pinned MC3 PS2 previews only with actual DAT/PCK and native bone proof."""
import argparse,copy,hashlib,importlib.util,json,os,shlex,shutil,sys
from pathlib import Path
from prepare_gt4_vehicle import require,unpack,pack,PreparationError
from prepare_mcla_vehicle import read_regular
from prepare_source_vehicle import prepare
from repair_mc3_vehicle import archive
ROOT=Path(__file__).resolve().parents[1]
CATALOG=ROOT/'experiments/2026-11-05-car-models/output/source-catalog.json'
INDEX=ROOT/'experiments/2026-11-06-mc3-coverage/output/native-index.json'
READER=ROOT/'experiments/2026-11-05-other-car-families/output/reference-mc3_pck.py'
CATALOG_SHA='fcd6eb5badd4cc120da3daaae315e83b71fb2b9400062b371b73c9f42a442e6c'
INDEX_SHA='4d35bc1b59b3661786d5390f1e48ba5ba9746806e052b67d85b1378e5f8d6fa7'
READER_SHA='68c6d61162563023560c4c71cf40bc729e2279918d8c9ef9e433df32de7bebde'
sha=lambda data:hashlib.sha256(data).hexdigest()

GLASS_SOURCE='8a1b7ba44d38815c6c491d3caf9e3b139dbf51c9d74d4c9546b2ee3164d48383'
GLASS_RULES={6:('colored_glass','colored_glass',8038728,'original',25216),7:('car_window','car_window',8038632,'original',26320)}

def authored_glass(doc,source_sha):
    """Exact reviewed source-material allowlist; unknown categories untouched."""
    require(source_sha==GLASS_SOURCE and doc.get('extras',{}).get('source_profile')=='mc3-ps2-static-preview-v1','glass_source_pin')
    active_materials=set();pending=list(doc['scenes'][doc.get('scene',0)]['nodes']);seen=set()
    while pending:
        node_index=pending.pop();require(type(node_index)is int and 0<=node_index<len(doc['nodes'])and node_index not in seen,'glass_active_graph');seen.add(node_index);require(len(seen)<=4096,'glass_active_budget');node=doc['nodes'][node_index];pending.extend(node.get('children',[]))
        if 'mesh'in node:
            require(type(node['mesh'])is int and 0<=node['mesh']<len(doc['meshes']),'glass_mesh')
            active_materials.update(p['material']for p in doc['meshes'][node['mesh']]['primitives'])
    changes=[]
    for index,rule in GLASS_RULES.items():
        if index not in active_materials:continue
        material=doc['materials'][index];e=material.get('extras',{})
        if (material.get('name'),e.get('shader_category'),e.get('vtable'),e.get('profile'),e.get('file_offset'))!=rule or e.get('index')!=index:continue
        original=copy.deepcopy(material);material['pbrMetallicRoughness']['baseColorFactor']=[.08,.12,.16,.45];material['alphaMode']='BLEND'
        changes.append({'index':index,'source_material':original,'authored_baseColorFactor':[.08,.12,.16,.45],'authored_alphaMode':'BLEND'})
    return {'authority':'Racer-authored dark tinted translucent window interpretation; NOT native GS shader/opacity parity','source_sha256':source_sha,'scope':'Only exact reviewed350Z materials6/7 matching name/category/vtable/profile/source offset/index; lamps and all unknown categories untouched.','changes':changes}

def build(source,source_sha,proof_path,dat_path,pck_path,output,*,racer_glass=False,authored_stock_exhaust=False,complete_external_lod0=False,native_config_path=None,output_budget=None):
    data=read_regular(source,16*1024**2);proof_raw=read_regular(proof_path,1024**2);dat=read_regular(dat_path,16*1024**2);pck=read_regular(pck_path,16*1024**2)
    require(len(data)+len(dat)+len(pck)<=32*1024**2,'selected_batch_budget');require(sha(data)==source_sha,'source_sha');proof=json.loads(proof_raw);d,_=unpack(data);code=d['extras']['car'];catalog_raw=read_regular(CATALOG,16*1024**2);index_raw=read_regular(INDEX,16*1024**2);require(sha(catalog_raw)==CATALOG_SHA and sha(index_raw)==INDEX_SHA,'catalog_index_pin')
    matches=[r for r in json.loads(catalog_raw)['cars']if r['id']=='midnight-club-3-remix/'+code];require(len(matches)==1 and matches[0]['sha256']==source_sha and matches[0]['source_profile']=='mc3-ps2-static-preview-v1','catalog_source_join');car=matches[0];require(sha(dat)==car['native_package']['sha256']and len(dat)==car['native_package']['bytes'],'native_dat_pin')
    rows=archive(dat);main=[r for r in rows if Path(r['name']).name==code+'.pck'];require(len(main)==1,'native_main_join');main=main[0];require(dat[main['offset']:main['offset']+main['size']]==pck,'actual_dat_pck_bytes')
    mainrows=[r for r in json.loads(index_raw)['files']if r['file'].startswith(code+'/assets/')and Path(r['file']).name==code+'.pck'];require(len(mainrows)==1 and mainrows[0]['sha256']==sha(pck),'native_pck_index_pin')
    require(proof['source_glb_sha256']==source_sha and proof['native_dat_sha256']==sha(dat)and proof['native_pck_sha256']==sha(pck),'proof_hash_join')
    reader_raw=read_regular(READER,1024**2);require(sha(reader_raw)==READER_SHA,'reader_pin');spec=importlib.util.spec_from_file_location('pinned_mc3_native_reader',READER);reader=importlib.util.module_from_spec(spec);spec.loader.exec_module(reader)
    # Decode the supplied actual PCK, never treat proof JSON as native authority.
    require(read_regular(pck_path,16*1024**2)==pck,'pck_changed_before_decode');native=reader.read_vehicle(Path(pck_path));require(read_regular(pck_path,16*1024**2)==pck,'pck_changed_after_decode');bones=json.loads(json.dumps(native['skeleton']['bones']));require(bones==proof['native_skeleton'],'native_proof_bones')
    name='Nissan 350Z 2004 (MC3; Racer glass)' if racer_glass else 'MC3 '+code+' (native-pose source candidate)'
    prepare_data=data;assembly=None
    require(complete_external_lod0 or native_config_path is None,'unused_native_config')
    if complete_external_lod0:
        require(native_config_path is not None and not racer_glass and not authored_stock_exhaust,'external_assembly_options')
        config=read_regular(native_config_path,65536);indexed=json.loads(index_raw)['files']
        configs=[row for row in indexed if row['file'].endswith('/'+code+'.carcfg')]
        require(configs and all(row['sha256']==sha(config) and row['bytes']==len(config) for row in configs),'native_config_index_pin')
        selected=[row for row in indexed if row['file'].startswith(code+'/assets/')]
        require(len(selected)==len(rows) and len({row['name'] for row in rows})==len(rows),'native_member_count')
        for member in rows:
            matches=[row for row in selected if row['source'].get('name')==member['name']]
            require(len(matches)==1 and matches[0]['sha256']==member['sha256'] and matches[0]['bytes']==member['size'] and all(matches[0]['source'][key]==member[key]for key in('offset','ordinal','size','stored')),'native_external_index_join')
        from mc3_external_parts import assemble
        d,binary=unpack(data);prepare_data,assembly=assemble(d,binary,native,dat,rows,reader,config)
    mesh,descriptor,r=prepare(prepare_data,'midnight-club-3-remix/'+code,name,native_bones=bones)
    if assembly is not None:
        # Keep the public source identity distinct from the derived assembly.
        prepared,binary=unpack(mesh);prepared['extras']['racerPreparation']['source_sha256']=source_sha
        prepared['extras']['racerExternalAssembly']['public_source_sha256']=source_sha
        prepared['extras']['racerExternalAssembly']['assembled_source_sha256']=sha(prepare_data)
        old=r['prepared_sha256'];mesh=pack(prepared,binary);new=sha(mesh)
        descriptor='\n'.join(('source_sha256 '+source_sha if line.startswith('source_sha256 ')else line.replace(old,new))for line in descriptor.splitlines())+'\n'
        r.update(source_sha256=source_sha,source_bytes=len(data),prepared_sha256=new,prepared_bytes=len(mesh),external_assembly=prepared['extras']['racerExternalAssembly'],native_config_sha256=sha(config))
    if racer_glass:
        prepared,binary=unpack(mesh);policy=authored_glass(prepared,source_sha);require(len(policy['changes'])==2,'glass_expected_materials');prepared['extras']['racerGlassPolicy']=policy;old=r['prepared_sha256'];mesh=pack(prepared,binary);new=sha(mesh);descriptor=descriptor.replace(old,new);r['prepared_sha256']=new;r['prepared_bytes']=len(mesh);r['racer_glass_policy']=policy;r['display_name']=name;r['display_year_authority']='Source identifier suffix04; retail trim/year certification not established.'
    r['role']='player-candidate';r['runtime_player_eligible']=False;r['native_authority']={'dat_sha256':sha(dat),'pck_sha256':sha(pck),'proof_sha256':sha(proof_raw),'reader_sha256':READER_SHA,'native_index_sha256':INDEX_SHA,'main_offset':main['offset'],'authority':'Pinned PS2 native package, actual DAT/PCK bytes and independently decoded bones; no Xbox equivalence or native runtime frame/unit proof.'}
    if code=='vp_350z_04':
        r['platform_qualified_comparison']={'source_platform':'MC3 vp_350z_04 identity; exact retail trim/year not independently certified','reference':'Nissan Z33 platform wheelbase 2650 mm; comparison only, not an import calibration','url':'https://usa.nissannews.com/en-US/releases/2006-nissan-350z-coupe-and-roadster-press-kit','reference_wheelbase_m':2.65,'source_wheelbase_native_import_units':r['wheelbase'],'relative_difference':r['wheelbase']/2.65-1,'physical_unit_authority':'Source factor1 remains authored interpretation. Reference is platform-qualified rather than exact2004trim proof.'}
    if authored_stock_exhaust:
        from mc3_exhaust import attach
        mesh,descriptor,r=attach(mesh,descriptor,r,bones,reader)
    payloads=(('.glb',mesh),('.vehicle',descriptor.encode()),('.json',(json.dumps(r,indent=2)+'\n').encode()))
    if output_budget is not None:
        require(type(output_budget)is int and 0<output_budget<=64*1024**2 and sum(len(p)for _,p in payloads)+(len(prepare_data)if assembly is not None else 0)<=output_budget,'requested_output_budget')
    output=Path(output);require(not output.exists()and not any(p.is_symlink()for p in(output,*output.parents)),'output_exists');require(shutil.disk_usage(output.parent).free>=20*1024**3,'free_space');output.mkdir(mode=0o700)
    if assembly is not None:
        fd=os.open(output/'assembled-source.glb',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'wb')as f:f.write(prepare_data)
    for suffix,payload in payloads:
        fd=os.open(output/(r['prepared_sha256']+suffix),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'wb')as f:f.write(payload)
    return r

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for flag in('source','native-proof','native-dat','native-pck','output'):p.add_argument('--'+flag,type=Path,required=True)
    p.add_argument('--source-sha',required=True);p.add_argument('--racer-glass',action='store_true');p.add_argument('--authored-stock-exhaust',action='store_true');p.add_argument('--complete-external-lod0',action='store_true');p.add_argument('--native-config',type=Path);a=p.parse_args()
    try:print(json.dumps(build(a.source,a.source_sha,a.native_proof,a.native_dat,a.native_pck,a.output,racer_glass=a.racer_glass,authored_stock_exhaust=a.authored_stock_exhaust,complete_external_lod0=a.complete_external_lod0,native_config_path=a.native_config),indent=2));return 0
    except(OSError,ValueError,KeyError,TypeError,IndexError,OverflowError):print('MC3 preparation rejected: invalid identity/native proof/geometry or storage failure; partial output may remain',file=sys.stderr);return 2
if __name__=='__main__':sys.exit(main())
