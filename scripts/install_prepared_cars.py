#!/usr/bin/env python3
"""Publish hash-pinned, eligible local preparations after native mesh validation.

The repository size inventory is the explicit review boundary. This does not
download models or promote traffic, excluded sources, or unresolved candidates.
Use install_cars.py first for the default library. The same cooperative lock,
immutable artifacts and catalog history are shared with that installer.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import shutil
import tempfile
import time
import uuid
import install_cars as common
import prepare_mcla_player as mcla_player
import prepared_inventory as inventory_format

def publish(root,inventory,ids,validator):
    started=time.monotonic();root=common.source.safe_dir(Path(root).absolute())
    common.require(shutil.disk_usage(root).free>=20*1024**3,'free_space')
    cache=common.source.safe_dir(root/'carmodels');vehicles=common.source.safe_dir(root/'vehicles')
    catalogs=common.source.safe_dir(cache/'catalogs');receipts=common.source.safe_dir(cache/'install-receipts')
    raw=common.regular_bytes(inventory,inventory_format.MAX_BYTES);rows=inventory_format.decode(raw)['vehicles']
    common.require(isinstance(rows,list) and all(isinstance(r,dict) and isinstance(r.get('model_id'),str) for r in rows),'inventory_schema')
    indexed={r['model_id']:r for r in rows}
    common.require(len(indexed)==len(rows),'duplicate_inventory_model')
    common.require(0<len(ids)<=16 and len(set(ids))==len(ids) and all(ident in indexed for ident in ids),'selection_count')
    selected=[indexed[ident] for ident in ids]
    evidence=[];evidence_bytes=0
    for r in selected:
        # Bind policy to the hash-verified descriptor, rather than trusting a
        # separately editable inventory source field. Native validation later
        # checks the complete descriptor and mesh geometry.
        db=common.regular_bytes(Path(r['descriptor']),32768)
        common.require(common.sha(db)==r['descriptor_sha256'],'reviewed_input_changed')
        common.require(common.descriptor_source(db)==r.get('source_sha256'),'descriptor_source_identity')
        common.require(r.get('player_eligible') is True and r.get('role')=='player' and r['model_id'].split('/')[0] not in common.EXCLUDED_GAMES,'not_player_eligible')
        game,separator,code=r['model_id'].partition('/')
        common.require(separator and code and not common.traffic_model({'game':game,'code':code}),'traffic_not_player')
        if game=='midnight-club-los-angeles':
            # Inventory role edits cannot promote ambient assets or invent a new
            # player source. Additional MCLA sources require a reviewed adapter.
            common.require(r['model_id']==mcla_player.ID and r.get('source_sha256')==mcla_player.SOURCE_SHA,'unreviewed_mcla_player_source')
        requirement=common.source.player_preparation_requirement(r['model_id'],r.get('source_sha256'))
        if requirement:
            resolution=r.get('resolved_source_requirements',{}).get(requirement,{})
            common.require(isinstance(resolution,dict) and resolution.get('prepared_sha256')==r.get('prepared_sha256') and isinstance(resolution.get('evidence'),str) and 0<len(resolution['evidence'])<=256,'unresolved_source_requirement')
        if r.get('canonical'):common.require(r['canonical']['within_authored_tolerances'] is True,'scale_conflict')
        refs=r.get('review_evidence',{})
        common.require(isinstance(refs,dict) and len(refs)<=32,'review_evidence_schema')
        for key,path in refs.items():
            common.require(isinstance(key,str) and 0<len(key)<=96 and isinstance(path,str) and 0<len(path)<=4096,'review_evidence_schema')
            data=common.regular_bytes(path,4*1024**2);evidence_bytes+=len(data)
            common.require(evidence_bytes<=16*1024**2,'review_evidence_budget')
            evidence.append((r['model_id'],key,path,data))
    lock=cache/'install.lock';operation=str(uuid.uuid4());fd=os.open(lock,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    info=os.fstat(fd);os.write(fd,common.encoded({'operation':operation,'pid':os.getpid(),'started_unix':int(time.time())}));os.close(fd)
    receipt={'schema':1,'operation':operation,'mode':'reviewed-local-prepared','inventory_sha256':common.sha(raw),'status':'failed','error':None,'models':[],'catalog':None,'limitations':['Trusted repository review inventory and cooperative local store.','Native validator establishes mesh identity, bindings and geometry containment; it does not establish original-game behavior.','Individual atomic publications, not a cross-file power-loss transaction.','Receipt failure after catalog commit does not roll back the catalog; retained ownership manifest supports verified resume.']}
    snapshot='review-'+common.sha(raw)+'.json'
    receipt['inventory_snapshot']='catalogs/'+snapshot
    receipt['review_evidence']=[]
    def check():common.require(time.monotonic()-started<120,'operation_deadline')
    current=vehicles/'catalog.racer'
    try:
        # Retain the actual review input: a SHA alone cannot reconstruct role,
        # fit limits or evidence links after the curated inventory is edited.
        # Content addressing deduplicates retries; earlier reviews are immutable.
        common.immutable(catalogs/snapshot,raw)
        for ident,key,path,data in evidence:
            digest=common.sha(data);name='review-evidence-'+digest+'.data'
            common.immutable(catalogs/name,data)
            receipt['review_evidence'].append({'source_id':ident,'key':key,'original_path':path,
                'sha256':digest,'bytes':len(data),'snapshot':'catalogs/'+name})
        old=common.regular_bytes(current,common.MAX_LIBRARY);oldsha=common.sha(old)
        managed=json.loads(common.regular_bytes(catalogs/(oldsha+'.json'),4*1024**2))
        common.require(managed['catalog_sha256']==oldsha and common.catalog_bytes(managed['entries'])==old,'catalog_manifest')
        entries=managed['entries'];common.validate_entries(entries,vehicles,check);total=len(raw)+evidence_bytes
        for r in selected:
            check()
            desc=Path(r['descriptor']);mesh=desc.with_suffix('.glb')
            db=common.regular_bytes(desc,32768);mb=common.regular_bytes(mesh,32*1024**2);total+=len(db)+len(mb)
            common.require(total<=128*1024**2,'operation_budget');check()
            common.require(common.sha(db)==r['descriptor_sha256'] and common.sha(mb)==r['prepared_sha256'],'reviewed_input_changed')
            entry={'source_id':r['model_id'],'source_sha256':r['source_sha256'],'mesh_sha256':r['prepared_sha256'],'descriptor':desc.name,'descriptor_sha256':r['descriptor_sha256']}
            common.require(desc.name==r['prepared_sha256']+'.vehicle','descriptor_filename')
            common.immutable(vehicles/desc.name,db);common.immutable(vehicles/(r['prepared_sha256']+'.glb'),mb)
            previous=next((e for e in entries if e['mesh_sha256']==entry['mesh_sha256']),None)
            if previous:common.require(previous==entry,'identity_conflict')
            else:
                # Explicitly reviewed upgrades replace this source model's
                # active revision in place; keep the Garage cycle order while
                # retaining old assets/catalogs as immutable history.
                positions=[i for i,e in enumerate(entries) if e.get('source_id')==entry['source_id']]
                common.require(len(positions)<=1,'duplicate_installed_source')
                if positions:entries[positions[0]]=entry
                else:entries.append(entry)
            receipt['models'].append(entry)
        common.validate_entries(entries,vehicles,check);new=common.catalog_bytes(entries);newsha=common.sha(new);check()
        fd,temp=tempfile.mkstemp(prefix='.validate-',dir=vehicles);os.close(fd);temp=Path(temp)
        try:
            temp.write_bytes(new)
            remaining=120-(time.monotonic()-started);common.require(remaining>0,'operation_deadline')
            result=subprocess.run([str(Path(validator).resolve()),str(temp)],capture_output=True,text=True,timeout=min(60,remaining))
            receipt['validation']={'exit':result.returncode,'stdout':result.stdout[:65536],'stderr':result.stderr[:4096],'validator_sha256':common.sha(common.regular_bytes(validator,32*1024**2))}
            common.require(result.returncode==0,'native_validation_failed');check()
        finally:temp.unlink(missing_ok=True)
        check();common.immutable(catalogs/(oldsha+'.racer'),old)
        newmanifest=managed if newsha==oldsha else {**managed,'catalog_sha256':newsha,'entries':entries,'local_review_inventory_sha256':common.sha(raw)}
        common.immutable(catalogs/(newsha+'.racer'),new);common.immutable(catalogs/(newsha+'.json'),common.encoded(newmanifest))
        common.require(common.regular_bytes(current,common.MAX_LIBRARY)==old,'catalog_changed');check()
        if new!=old:
            fd,temp=tempfile.mkstemp(prefix='.catalog-',dir=vehicles)
            try:
                with os.fdopen(fd,'wb') as out:out.write(new);out.flush();os.fsync(out.fileno())
                os.replace(temp,current)
            finally:Path(temp).unlink(missing_ok=True)
        receipt.update(status='installed',catalog={'old_sha256':oldsha,'sha256':newsha,'entries':len(entries)})
    except Exception as error:
        receipt['error']=str(error) if isinstance(error,common.InstallError) else type(error).__name__
    finally:
        now=lock.lstat()
        if (now.st_dev,now.st_ino)==(info.st_dev,info.st_ino):lock.unlink()
        receipt['elapsed_ms']=round((time.monotonic()-started)*1000)
        common.immutable(receipts/(operation+'.json'),common.encoded(receipt))
    return receipt

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=Path('assets/local'));p.add_argument('--inventory',type=Path,default=Path('assets/catalog/prepared-sizes.json'));p.add_argument('--id',action='append',required=True);p.add_argument('--validator',type=Path,default=Path('build/vehicle_validate'));a=p.parse_args()
    r=publish(a.root,a.inventory,a.id,a.validator);print(json.dumps(r,indent=2));return 0 if r['status']=='installed' else 2
if __name__=='__main__':raise SystemExit(main())
