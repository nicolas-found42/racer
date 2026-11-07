#!/usr/bin/env python3
"""Hidden native multi-view scale captures, with explicit research-only inputs.

Pillow is required. Each run has an isolated profile and retained JSONL history;
source model files, executable and pixel-identical PNGs are preserved together.
No desktop input, focus activation, remote game execution or runtime networking.
"""
import argparse
import hashlib
import json
from pathlib import Path
from verification_lifecycle import VerificationLifecycle
import shutil
import subprocess
import time
from PIL import Image
from install_cars import regular_bytes, descriptor_source, traffic_model, EXCLUDED_GAMES
from vehicle_clearance import descriptor as parse_descriptor
import prepared_inventory as inventory_format

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('output',type=Path)
    selection=p.add_mutually_exclusive_group()
    selection.add_argument('--inventory',type=Path,default=Path('assets/catalog/prepared-sizes.json'))
    selection.add_argument('--research-descriptor',type=Path,action='append',help='Capture an unapproved candidate without changing its eligibility; repeat for up to seven inputs.')
    p.add_argument('--binary',type=Path,default=Path('build/racer'))
    p.add_argument('--limit',type=int,default=7)
    a=p.parse_args();out=a.output.resolve()
    if not 1<=a.limit<=7:raise ValueError('limit must be within 1..7')
    research=bool(a.research_descriptor)
    inventory_raw=None
    if research:
        if len(a.research_descriptor)>7:raise ValueError('1..7 research inputs required')
        rows=[]
        for desc in a.research_descriptor:
            raw=regular_bytes(desc,32768);fields,_,_=parse_descriptor(raw.decode())
            rows.append({'model_id':'research:'+fields['sha256'][0],'research_label':desc.parent.name,'name':fields['name'][0],
                         'source_sha256':fields['source_sha256'][0],'prepared_sha256':fields['sha256'][0],
                         'descriptor_sha256':hashlib.sha256(raw).hexdigest(),'descriptor':str(desc),
                         'player_eligible':False,'role':'research-candidate'})
    else:
        inventory_raw=regular_bytes(a.inventory,inventory_format.MAX_BYTES)
        rows=[r for r in inventory_format.decode(inventory_raw)['vehicles'] if r.get('player_eligible') is True][:a.limit]
        for row in rows:
            game,separator,code=row['model_id'].partition('/')
            if not separator or not code or row.get('role')!='player' or game in EXCLUDED_GAMES or traffic_model({'game':game,'code':code}):
                raise ValueError('selected inventory role or source policy mismatch')
    if not rows or len(rows)>7:raise ValueError('1..7 selected models required')
    if len({row['model_id'] for row in rows})!=len(rows):raise ValueError('duplicate selected model identity')
    if shutil.disk_usage(out.parent).free<20*1024**3:raise ValueError('20GiB free required')
    out.mkdir(parents=True,exist_ok=False)
    with VerificationLifecycle(out) as lifecycle:
        models=out/'models';models.mkdir();descriptors=[]
        payload=0
        for row in rows:
            desc=Path(row['descriptor']);mesh=desc.with_suffix('.glb')
            db=regular_bytes(desc,32768);mb=regular_bytes(mesh,32*1024**2);payload+=len(db)+len(mb)
            if payload>64*1024**2:raise ValueError('64MiB model batch limit')
            if hashlib.sha256(db).hexdigest()!=row['descriptor_sha256'] or hashlib.sha256(mb).hexdigest()!=row['prepared_sha256']:raise ValueError('selected input hash mismatch')
            if descriptor_source(db)!=row['source_sha256']:raise ValueError('selected descriptor source mismatch')
            for source,data in [(desc,db),(mesh,mb)]:
                target=models/source.name
                if target.exists() and target.read_bytes()!=data:raise ValueError('conflicting frozen filename')
                if not target.exists():target.write_bytes(data)
            descriptors.append(desc.name)
        library=models/'catalog.racer'
        library.write_text('RACER_VEHICLES 1\n'+str(len(rows))+'\n'+''.join(json.dumps(s)+'\n' for s in descriptors))
        if inventory_raw is not None:(out/'inventory.json').write_bytes(inventory_raw)
        original=a.binary.resolve();shutil.copy2(original,out/'racer');exe=out/'racer'
        manifest={'schema':1,'build_sha256':sha(exe),'inventory_sha256':hashlib.sha256(inventory_raw).hexdigest() if inventory_raw is not None else None,'research_only':research,'models':rows,'runs':[],'scope':'Native loader/hash/containment and GPU capture. Research inputs do not grant player eligibility. Factory dimensions compared separately; original game execution unobserved.'}
        began=time.monotonic()
        for index,row in enumerate(rows):
            for view in ['rear','front','left','elevated']:
                if time.monotonic()-began>240:raise TimeoutError('240s batch deadline')
                if sum(p.stat().st_size for p in out.rglob('*') if p.is_file())+6*1024**2>128*1024**2:raise ValueError('128MiB capture batch limit')
                folder=out/(str(index)+'-'+view);folder.mkdir()
                ppm=folder/'capture.ppm';png=folder/'capture.png'
                cmd=[str(exe),'--background','--vehicle-library',str(library),'--vehicle',str(index),'--scene','scale','--camera-view',view,'--smoke','3.3','--window','1280','720','--profile',str(folder/'profile.txt'),'--diagnostics-dir',str(folder/'history'),'--screenshot',str(ppm)]
                with (folder/'native.log').open('w') as log:r=lifecycle.run(cmd,stdout=log,stderr=subprocess.STDOUT,timeout=15)
                record={'model_id':row['model_id'],'view':view,'command':cmd,'exit':r.returncode}
                lifecycle.phase('capture')
                if ppm.exists():
                    with Image.open(ppm) as im:
                        im.load();im.save(png)
                        with Image.open(png) as check:assert check.tobytes()==im.tobytes()
                        record.update(capture=str(png.relative_to(out)),sha256=sha(png),dimensions=list(im.size))
                    ppm.unlink() # pixel-identical PNG is the canonical retained capture
                lifecycle.phase('retrieval')
                events=[]
                for path in (folder/'history').glob('*.jsonl'):
                    for line in path.read_text().splitlines():
                        try:events.append(json.loads(line))
                        except json.JSONDecodeError:record['history_partial']=True
                record['asset_outcomes']=[e for e in events if e.get('event')=='asset_load_end']
                record['verified']=r.returncode==0 and png.exists() and any(e.get('success') is True and e.get('sha256')==row['prepared_sha256'] for e in record['asset_outcomes'])
                manifest['runs'].append(record)
                (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
                print(json.dumps({k:record[k] for k in ['model_id','view','exit','verified']}),flush=True)
        manifest['elapsed_seconds']=time.monotonic()-began
        manifest['all_verified']=all(r['verified'] for r in manifest['runs'])
        (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
        lifecycle.complete(manifest['all_verified'])
        return 0 if manifest['all_verified'] else 1
if __name__=='__main__':raise SystemExit(main())
