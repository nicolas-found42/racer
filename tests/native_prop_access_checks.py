#!/usr/bin/env python3
"""Capture both authored entrances against the actual intended flat Y0 ground.

Four hidden4s640x360 runs,25s each,24MiB output. Images need direct inspection;
pixel sanity and source geometry do not certify contact or overall art quality.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from PIL import Image,ImageStat
from native_shadow_checks import fixture
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from install_cars import regular_bytes


def sha(data):return hashlib.sha256(data).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--binary',type=Path,required=True)
    p.add_argument('--candidate-c',type=Path,required=True);p.add_argument('--candidate-d',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    executable=regular_bytes(a.binary.resolve(),12*1024**2)
    out=a.output.resolve();out.mkdir(exist_ok=False);binary=out/'racer';binary.write_bytes(executable);binary.chmod(a.binary.stat().st_mode&0o777)
    # A deliberate plane atY0, rather than the renderer's safety filler below
    # every source asset. The transparent preview removes the player car.
    floor=[-100,0,-100,-100,0,100,100,0,100,-100,0,-100,100,0,100,100,0,-100]
    fixture(out/'ground.gltf',floor,[.3,.3,.3,1]);ground=json.loads((out/'ground.gltf').read_text())
    ground['materials'][0]['pbrMetallicRoughness'].update(roughnessFactor=1,metallicFactor=0)
    (out/'ground.gltf').write_text(json.dumps(ground))
    fixture(out/'empty.gltf',[-1,1,0,0,2,0,1,1,0],[1,0,0,0])
    report={'binary_sha256':sha(executable),'ground_y':0,'hidden_hud':True,'transparent_vehicle':True,
            'visual_acceptance':'Pending direct inspection of all footings/sills; this is not a pixel quality grade','runs':[]}
    for variant in ('c','d'):
        source=getattr(a,'candidate_'+variant).resolve();meta_bytes=regular_bytes(source.parent/'manifest.json',256*1024)
        meta=json.loads(meta_bytes);model=regular_bytes(source,4*1024**2)
        if sha(model)!=meta['sha256']or meta['variant']!=variant:raise ValueError('candidate identity')
        frozen=out/('candidate-'+variant+'.glb');frozen.write_bytes(model)
        (out/('candidate-'+variant+'-manifest.json')).write_bytes(meta_bytes)
        bindings=meta['source_door_bindings']
        if len(bindings)!=2:raise ValueError('two exact source doors required')
        for index,binding in enumerate(bindings):
            door,design=binding['door'],binding['design'];x,y,z=door['center'];normal=door['outward']
            if design['footing_y']!=0 or abs(design['top_y']-door['sill'])>1e-6:raise ValueError('access ground/sill contract')
            view=('right'if normal[0]>0 else'left')if abs(normal[0])>abs(normal[2])else('front'if normal[2]>0 else'rear')
            name=variant+'-door-'+str(index);ppm=out/(name+'.ppm')
            argv=[str(binary),'--background','--smoke','4','--window','640','360','--hide-hud',
                  '--preview-gltf',str(out/'empty.gltf'),'--world-mesh',str(frozen),'--world-mesh',str(out/'ground.gltf'),
                  '--world-origin',str(-x),'0',str(-z),'--camera-view',view,'--camera-distance','9',
                  '--screenshot',str(ppm),'--profile',str(out/(name+'-profile')),'--no-diagnostics']
            run=subprocess.run(argv,capture_output=True,text=True,timeout=25);(out/(name+'.log')).write_text(run.stdout+run.stderr)
            record={'name':name,'argv':argv,'exit':run.returncode,'candidate_sha256':sha(model),'door':door,'design':design}
            report['runs'].append(record);(out/'manifest.json').write_text(json.dumps(report,indent=2))
            if run.returncode:raise RuntimeError('native entrance capture failed '+name)
            image=Image.open(ppm).convert('RGB');image.save(ppm.with_suffix('.png'));stats=ImageStat.Stat(image)
            if image.size!=(640,360)or max(stats.mean)<10 or max(stats.stddev)<5:raise RuntimeError('blank entrance capture')
            record.update(png_sha256=sha(ppm.with_suffix('.png').read_bytes()),ppm_sha256=sha(ppm.read_bytes()))
            (out/'manifest.json').write_text(json.dumps(report,indent=2))
            if sum(f.stat().st_size for f in out.rglob('*')if f.is_file())>24*1024**2:raise RuntimeError('access output quota')
            print('captured '+name+' againstY0 withoutHUD',flush=True)
    print('PASS: four actual unobstructed entrance captures; direct contact/quality judgment remains required')


if __name__=='__main__':main()
