#!/usr/bin/env python3
"""Hidden native steering/reverse/reset evidence through explicit synthetic input."""
import argparse,hashlib,json,subprocess,time
from pathlib import Path
from verification_lifecycle import VerificationLifecycle
from PIL import Image

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path);p.add_argument('--vehicle',default='0');p.add_argument('--vehicle-library',type=Path);p.add_argument('--binary',type=Path,default=Path('build/racer'));p.add_argument('--camera-view',choices=['rear','left','right','front','elevated'],default='rear');p.add_argument('--require-carrier',action='store_true');a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    with VerificationLifecycle(out) as lifecycle:
        actions=[]
        def capture(name):actions.append('capture '+str(out/(name+'.ppm')))
        actions+=['drive-input 0 0 0','wait .3'];capture('01-rest')
        actions+=['drive-input 1 0 0','wait 2.4','drive-input 1 0 .6','wait 1'];capture('02-right')
        actions+=['drive-input 0 1 0','wait 2','drive-input 0 0 0','wait .3','drive-input 0 1 0','wait 1.8'];capture('03-reverse')
        actions+=['drive-input 0 0 0','key reset','wait .4'];capture('04-reset')
        actions+=['drive-input 1 0 0','wait 2.4','drive-input 1 0 -.6','wait 1'];capture('05-left')
        actions+=['drive-input 0 0 0','key back','wait .3'];capture('06-paused')
        actions+=['key back','drive-input 0 0 0','wait .3','key reset','wait .3'];capture('07-restored')
        actions+=['quit'];script=out/'actions.txt';script.write_text('\n'.join(actions)+'\n')
        exe=a.binary.resolve();cmd=[str(exe),'--background','--vehicle',a.vehicle,'--camera-view',a.camera_view,'--review-script',str(script),'--smoke','35','--window','1280','720','--profile',str(out/'profile.txt'),'--diagnostics-dir',str(out/'history')]
        if a.vehicle_library:cmd+=['--vehicle-library',str(a.vehicle_library.resolve())]
        with (out/'native.log').open('w') as log:r=lifecycle.run(cmd,stdout=log,stderr=subprocess.STDOUT,timeout=40)
        lifecycle.phase('capture')
        captures=[]
        for file in sorted(out.glob('*.ppm')):
            with Image.open(file) as im:
                im.load();png=file.with_suffix('.png');im.save(png)
                with Image.open(png) as check:assert check.tobytes()==im.tobytes()
            captures.append({'file':png.name,'sha256':hashlib.sha256(png.read_bytes()).hexdigest()});file.unlink()
        lifecycle.phase('retrieval')
        events=[json.loads(line) for f in (out/'history').glob('*.jsonl') for line in f.read_text().splitlines()]
        motion=[e for e in events if e.get('event')=='motion'];wheels=[e for e in events if e.get('event')=='wheel_pose']
        checks={'exit':r.returncode==0,'seven_captures':len(captures)==7,'right':any(e['heading']>.1 and e['effective_steer']>.1 for e in motion),'left':any(e['heading']<-.1 and e['effective_steer']<-.1 for e in motion),'reverse':any(e['speed']<-.2 for e in motion),'reset':any(e['speed']==0 and e['travel']==0 and e['heading']==0 for e in motion),'render_alignment':all(e['orientation_error']<.001 for e in motion),'sampled_wheel_pose':bool(wheels),'no_dropped_samples':all(e.get('dropped',0)==0 for e in events)}
        if a.require_carrier:
            carriers=[e for e in events if e.get('event')=='carrier_pose'];by_frame={e['frame']:e for e in wheels}
            checks['carrier_sampled']=bool(carriers)
            checks['carrier_does_not_roll']=bool(carriers) and all(abs(e['radial_x'])<1e-6 and abs(e['radial_y']-1)<1e-6 and abs(e['radial_z'])<1e-6 for e in carriers)
            checks['carrier_follows_wheel_hub']=bool(carriers) and all(e['frame'] in by_frame and all(abs(e[k]-by_frame[e['frame']][k])<1e-6 for k in ['x','y','z','axle_x','axle_z']) for e in carriers)
        manifest={'command':cmd,'build_sha256':hashlib.sha256(exe.read_bytes()).hexdigest(),'asset_outcomes':[e for e in events if e.get('event')=='asset_load_end'],'library_sha256':hashlib.sha256(a.vehicle_library.read_bytes()).hexdigest() if a.vehicle_library else None,'captures':captures,'checks':checks,'all_verified':all(checks.values()),'scope':'Synthetic input drives ordinary physics and renderer. Human controls and original-game dynamics unproven. Assets/executable must be retained separately at the recorded command paths.'}
        (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps(checks));lifecycle.complete(manifest['all_verified']);return 0 if manifest['all_verified'] else 1
if __name__=='__main__':raise SystemExit(main())
