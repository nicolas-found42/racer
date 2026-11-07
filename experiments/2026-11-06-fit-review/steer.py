#!/usr/bin/env python3
"""Frozen hidden maximum-steer views; research evidence, not publication."""
import hashlib,json,shlex,shutil,subprocess,time
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    out=Path(__file__).resolve().parent/'output/steer-v2'
    assert shutil.disk_usage(out.parent).free>20*1024**3
    out.mkdir(exist_ok=False);models=out/'models';models.mkdir()
    installed=ROOT/'assets/local/vehicles/catalog.racer'
    rows=shlex.split(installed.read_text());assert rows[:2]==['RACER_VEHICLES','1'];assert int(rows[2])==len(rows)-3
    paths=[installed.parent/n for n in rows[3:]]
    # Research replacements only, production is unchanged by this script.
    paths[3]=next((ROOT/'experiments/2026-11-05-mcla-vehicle/output/player-roadster-flat-ground-v4').glob('*.vehicle'))
    paths += [next((ROOT/'experiments/2026-11-05-city-scale/output/corvette-track-fit-v1').glob('*.vehicle')),
              next((ROOT/'experiments/2026-11-06-slrr-rest-fit/output/geometry-bounded-v4').glob('*.vehicle'))]
    assert len(paths)==7
    identities=[]
    for desc in paths:
        mesh=desc.with_suffix('.glb');assert sha(mesh)==mesh.stem
        for p in (desc,mesh):shutil.copyfile(p,models/p.name)
        identities.append({'descriptor_source':str(desc.relative_to(ROOT)),'descriptor_sha256':sha(desc),'mesh_sha256':sha(mesh)})
    catalog=models/'catalog.racer';catalog.write_text('RACER_VEHICLES 1\n7\n'+''.join(json.dumps(p.name)+'\n' for p in paths))
    exe=out/'racer';shutil.copy2(ROOT/'experiments/2026-11-06-fit-review/output/native-v1/racer',exe)
    manifest={'scope':'Research-only rigid wheel/body fit at rest; no original-game shader/handling or exact mesh-intersection proof','models':identities,'build_sha256':sha(exe),'runs':[]};start=time.monotonic()
    for i,row in enumerate(identities):
        assert time.monotonic()-start<240
        folder=out/str(i);folder.mkdir();script=folder/'actions.txt'
        lines=['drive-input 0 0 0','wait .5','capture '+str(folder/'01-straight.ppm'),
               'drive-input 0 0 1','wait 1.2','capture '+str(folder/'02-right.ppm'),
               'drive-input 0 0 -1','wait 2','capture '+str(folder/'03-left.ppm'),'quit']
        script.write_text('\n'.join(lines)+'\n')
        cmd=[str(exe),'--background','--vehicle-library',str(catalog),'--vehicle',str(i),'--scene','scale',
             '--camera-view','front','--window','2560','1440','--smoke','9','--review-script',str(script),
             '--profile',str(folder/'profile.txt'),'--diagnostics-dir',str(folder/'history')]
        with (folder/'native.log').open('w') as log:run=subprocess.run(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=15)
        captures=[]
        for p in sorted(folder.glob('*.ppm')):
            png=p.with_suffix('.png')
            with Image.open(p) as im:
                im.load();im.save(png)
                with Image.open(png) as check:assert check.tobytes()==im.tobytes()
            p.unlink();captures.append({'file':png.name,'sha256':sha(png)})
        events=[json.loads(line)for f in(folder/'history').glob('*.jsonl')for line in f.read_text().splitlines()]
        poses=[e for e in events if e.get('event')=='wheel_pose'];motion=[e for e in events if e.get('event')=='motion']
        checks={'exit':run.returncode==0,'captures':len(captures)==3,'right_limit':any(e['steering']>.549 for e in poses),
                'left_limit':any(e['steering']<-.549 for e in poses),'stationary':bool(motion)and all(e['speed']==0 for e in motion),
                'exact_asset':any(e.get('event')=='asset_load_end'and e.get('success')and e.get('sha256')==row['mesh_sha256']for e in events)}
        manifest['runs'].append({'model':i,'command':cmd,'captures':captures,'checks':checks})
        manifest['elapsed_seconds']=time.monotonic()-start
        (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
        print(i,checks,flush=True)
        assert sum(p.stat().st_size for p in out.parent.rglob('*')if p.is_file())<128*1024**2
    manifest['all_verified']=all(all(r['checks'].values())for r in manifest['runs']);(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return 0 if manifest['all_verified']else 1
if __name__=='__main__':raise SystemExit(main())
