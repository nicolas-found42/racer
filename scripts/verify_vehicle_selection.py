#!/usr/bin/env python3
"""Hidden native car-switch, load failure, save retry, livery and reload check."""
import hashlib,json,re,shlex,subprocess,time
from pathlib import Path
from verification_lifecycle import VerificationLifecycle
import install_cars as common
import argparse
from PIL import Image

SOURCE_MODELS = Path('assets/local/vehicles')
TARGET_SOURCE = '878a07afd724d8dd4769362e2cc366d0cf635412d5ac9c972b2266ef1565ba97'
MAX_MODEL_BYTES = 64 * 1024**2
MAX_READ_BYTES = 128 * 1024**2
MAX_DESCRIPTOR = 32768

def input_context(lifecycle,kind,index=None,digest=None):
    if lifecycle:
        lifecycle.record.update(active_input=kind,descriptor_index=index,expected_mesh_sha256=digest)
        lifecycle.checkpoint()

def selection_plan(source=SOURCE_MODELS,lifecycle=None):
    """Read and pin only this scenario's four models before any staging writes."""
    consumed=read_count=0
    def read(path,cap,kind,index=None,digest=None):
        nonlocal consumed,read_count
        input_context(lifecycle,kind,index,digest)
        remaining=MAX_READ_BYTES-consumed
        common.require(remaining>0,'selection_read_budget')
        read_count+=1
        if lifecycle:
            lifecycle.record.update(input_read_count=read_count,input_read_bytes=consumed)
            lifecycle.checkpoint()
        data=common.regular_bytes(path,min(cap,remaining));consumed+=len(data)
        if lifecycle:
            lifecycle.record['input_read_bytes']=consumed;lifecycle.checkpoint()
        return data
    source=Path(source);raw=read(source/'catalog.racer',common.MAX_LIBRARY,'catalog')
    if lifecycle:
        lifecycle.record['source_library_sha256']=common.sha(raw);lifecycle.checkpoint()
    lines=raw.decode('utf-8').splitlines()
    common.require(len(lines)>=2 and lines[0]=='RACER_VEHICLES 1' and
                   re.fullmatch('[0-9]{1,4}',lines[1]),'selection_catalog_header')
    count=int(lines[1]);common.require(4<=count<=common.MAX_ENTRIES and len(lines)==count+2,'selection_catalog_count')
    names=[json.loads(line)for line in lines[2:]]
    common.require(all(isinstance(n,str)and re.fullmatch('[0-9a-f]{64}\\.vehicle',n)for n in names)
                   and len(set(names))==count,'selection_catalog_names')
    selected={};target=None
    for index,name in enumerate(names):
        descriptor=read(source/name,MAX_DESCRIPTOR,'descriptor',index,Path(name).stem)
        source_sha=common.descriptor_source(descriptor)
        if index<3 or source_sha==TARGET_SOURCE:
            fields={}
            for line in descriptor.decode('utf-8').splitlines():
                words=shlex.split(line)
                if words and words[0]in('mesh','sha256'):
                    common.require(words[0]not in fields,'selection_descriptor_duplicate')
                    fields[words[0]]=words[1:]
            digest=Path(name).stem
            common.require(fields.get('mesh')==[digest+'.glb']and fields.get('sha256')==[digest],
                           'selection_descriptor_identity')
            selected[index]=(name,descriptor,source_sha)
        if source_sha==TARGET_SOURCE:
            common.require(index>=3,'selection_target_order');target=index;break
    common.require(target is not None,'selection_target_missing')
    indices=[0,1,2,target];payloads=[];pins=[];total=sum(len(selected[i][1])for i in indices)
    common.require(total<=MAX_MODEL_BYTES,'selection_input_budget')
    for index in indices:
        name,descriptor,source_sha=selected[index];meshname=Path(name).with_suffix('.glb').name
        mesh=read(source/meshname,MAX_MODEL_BYTES-total,'mesh',index,Path(name).stem)
        common.require(common.sha(mesh)==Path(name).stem,'selection_mesh_hash')
        total+=len(mesh);payloads.extend(((name,descriptor),(meshname,mesh)))
        pins.append({'original_index':index,'descriptor':name,'descriptor_sha256':common.sha(descriptor),
                     'descriptor_bytes':len(descriptor),'mesh_sha256':common.sha(mesh),'mesh_bytes':len(mesh),
                     'source_sha256':source_sha})
    subset=('RACER_VEHICLES 1\n4\n'+''.join(json.dumps(names[i])+'\n'for i in indices)).encode()
    identity={'source_library_sha256':common.sha(raw),'original_indices':indices,
              'subset_library_sha256':common.sha(subset),'input_pins':pins,'input_bytes':total,
              'input_byte_cap':MAX_MODEL_BYTES,'target_subset_index':3,
              'input_read_bytes':consumed,'input_read_count':read_count,'input_read_byte_cap':MAX_READ_BYTES}
    return payloads,subset,identity

def stage_selection(output,source=SOURCE_MODELS,lifecycle=None):
    payloads,catalog,identity=selection_plan(source,lifecycle=lifecycle)
    if lifecycle:lifecycle.phase('capture')
    def publication(kind,index=None,digest=None):
        if lifecycle:lifecycle.record['publication_kind']=kind
        input_context(lifecycle,kind if kind in('descriptor','mesh')else None,index,digest)
    # A retained plan identifies inputs even if a later per-file write fails.
    publication('plan')
    common.immutable(output/'selection-inputs.json',(json.dumps(identity,indent=2)+'\n').encode())
    models=output/'models';models.mkdir(mode=0o700)
    for pin,(descriptor,mesh) in zip(identity['input_pins'],zip(payloads[::2],payloads[1::2])):
        for kind,(name,data) in (('descriptor',descriptor),('mesh',mesh)):
            publication(kind,pin['original_index'],pin['mesh_sha256'])
            common.immutable(models/name,data)
    publication('catalog')
    common.immutable(models/'catalog.racer',catalog)
    if lifecycle:lifecycle.record['publication_kind']=None
    input_context(lifecycle,None)
    return models,[json.loads(line)for line in catalog.decode().splitlines()[2:]],identity

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path);p.add_argument('--binary',type=Path,default=Path('build/racer'));a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    with VerificationLifecycle(out) as lifecycle:
        lifecycle.phase('retrieval')
        models,names,input_identity=stage_selection(out,lifecycle=lifecycle);target=3
        bad=models/Path(names[target]).with_suffix('.glb');original=common.regular_bytes(bad,MAX_MODEL_BYTES);bad.write_bytes(b'broken model fixture')
        profile=out/'profile/profile.txt';profile.parent.mkdir();actions=[]
        def key(k):actions.append('key '+k)
        def choose(n):actions.extend(['select '+str(n),'key accept'])
        def capture(name,assertion=None):
            if assertion:actions.append('assert '+assertion)
            actions.append('capture '+str(out/(name+'.ppm')))
        key('back');choose(2);capture('01-garage','Acura NSX')
        actions.append('select 13');key('right');capture('02-nissan','Nissan 350Z')
        actions.append('select 1');key('right');actions.append('select 13');key('right');capture('03-dirty','UNAPPLIED CHANGES');choose(2);capture('04-keep','DRAFT NOT APPLIED')
        actions.append('select 13');key('right');choose(1);capture('05-discard-switch','Ford Mustang')
        for _ in range(target-3):actions.append('select 13');key('right')
        actions.append('select 13');key('right');capture('06-load-failed','previous car retained')
        capture('07-repair-ready');actions.append('wait 1')
        actions.append('select 13');key('right');capture('08-unsaved-switch','UNSAVED car selection')
        capture('09-unlock-ready');actions.append('wait 1');choose(9);capture('10-retry-saved','Car selection saved')
        choose(11);choose(1);capture('11-livery-draft');choose(13);choose(16);capture('12-livery-applied','Juiced 2 Nissan 350Z')
        choose(8);choose(0);actions.append('result');capture('13-measured-juiced2','MEASUREMENT: 8.000 s');actions.append('quit')
        script=out/'actions.txt';script.write_text('\n'.join(actions)+'\n');exe=a.binary.resolve()
        cmd=[str(exe),'--background','--vehicle-library',str(models/'catalog.racer'),'--review-script',str(script),'--smoke','65','--window','1280','720','--profile',str(profile),'--diagnostics-dir',str(out/'history')]
        converted=set();captures=[];began=time.monotonic()
        def collect():
            lifecycle.phase('capture')
            for path in out.glob('*.ppm'):
                if path in converted:continue
                try:
                    with Image.open(path) as im:im.load();pixels=im.tobytes();png=path.with_suffix('.png');im.save(png)
                    with Image.open(png) as check:assert check.tobytes()==pixels
                except (OSError,ValueError):continue
                if path.stem=='07-repair-ready':bad.write_bytes(original);profile.parent.chmod(0o500)
                if path.stem=='09-unlock-ready':profile.parent.chmod(0o700)
                captures.append({'file':png.name,'sha256':hashlib.sha256(png.read_bytes()).hexdigest()});path.unlink();converted.add(path)
        with (out/'native.log').open('w') as log:
            process=lifecycle.popen(cmd,stdout=log,stderr=subprocess.STDOUT)
            try:
                while process.poll() is None:
                    if time.monotonic()-began>70:process.kill();raise TimeoutError('70s native check')
                    collect();time.sleep(.05)
                collect()
            finally:
                if process.poll() is None:process.kill();process.wait()
                profile.parent.chmod(0o700)
        reload=out/'reload';reload.mkdir();reloadcmd=[str(exe),'--background','--vehicle-library',str(models/'catalog.racer'),'--scene','garage','--smoke','3.4','--window','1280','720','--profile',str(profile),'--diagnostics-dir',str(reload/'history'),'--screenshot',str(reload/'capture.ppm')]
        with (reload/'native.log').open('w') as log:reloaded=lifecycle.run(reloadcmd,stdout=log,stderr=subprocess.STDOUT,timeout=12,kind='reload')
        lifecycle.phase('capture')
        if (reload/'capture.ppm').exists():
            with Image.open(reload/'capture.ppm') as im:im.load();im.save(reload/'capture.png')
            (reload/'capture.ppm').unlink()
        lifecycle.phase('retrieval')
        events=[json.loads(line) for f in (reload/'history').glob('*.jsonl') for line in f.read_text().splitlines()]
        loaded=[e for e in events if e.get('event')=='asset_load_end' and e.get('success')]
        saved=profile.with_suffix('.txt.vehicle').read_text().strip()
        checks={'exit':process.returncode==0,'captures':len(captures)==13,'reload_exit':reloaded.returncode==0,'juiced2_reloaded':bool(loaded) and loaded[0]['sha256']==Path(names[target]).stem,'selection_saved':saved=='vehicle-'+Path(names[target]).stem}
        manifest={'command':cmd,'reload_command':reloadcmd,'build_sha256':hashlib.sha256(exe.read_bytes()).hexdigest(),'library_sha256':hashlib.sha256((models/'catalog.racer').read_bytes()).hexdigest(),**input_identity,'selected_prepared_sha256':Path(names[target]).stem,'captures':captures,'checks':checks,'verified':all(checks.values()),'scope':'Synthetic local asset corruption/repair and selection save failure/retry/restart. Only four bounded, hash-pinned scenario inputs are staged; source catalog remains unchanged. Exact staged models and commands retained; use an immutable --binary path for historical replay. Human controls and donor runtime remain unproven.'};(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps(checks));lifecycle.complete(manifest['verified']);return 0 if manifest['verified'] else 1
if __name__=='__main__':raise SystemExit(main())
