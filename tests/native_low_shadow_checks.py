#!/usr/bin/env python3
"""Measure native shadows from 3/5/8/10/15cm casters; not a fidelity grade.

Six hidden three-second runs,20s per-run deadline,16MiB retained output.
The no-caster baseline and all low casters share a fixed neutral receiver.
Red caster pixels plus a one-pixel fringe are excluded from darkening counts.
Counts are observations; compare before/after and inspect the actual images.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from PIL import Image, ImageDraw, ImageFilter
from native_hdr_checks import local_path, regular
from native_shadow_checks import fixture

CAP=16*1024**2
ROOT=Path(__file__).resolve().parents[1]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    data,mode=regular(local_path(args.binary),6*1024**2)
    out=local_path(args.output)
    if any(p.is_symlink()for p in (out,*out.parents)):
        raise ValueError('output_symlink_refused')
    if len(data)+8*1024**2>CAP:
        raise ValueError('low_shadow_preflight_quota')
    out.mkdir(parents=True,exist_ok=False)
    binary=out/'racer'
    binary.write_bytes(data)
    binary.chmod(mode)
    source=ROOT/'src/visual_shader.h'
    shader=source.read_bytes()
    (out/'visual_shader.h').write_bytes(shader)
    (out/'native_low_shadow_checks.py').write_bytes(Path(__file__).read_bytes())
    floor=[-100,0,-100,-100,0,100,100,0,100,-100,0,-100,100,0,100,100,0,-100]
    fixture(out/'ground.gltf',floor,[.5,.5,.5,1])
    manifest={'binary_sha256':digest(data),'shader_sha256':digest(shader),
              'output_cap_bytes':CAP,'runs':[],
              'authority':'Actual hidden native low-caster probe. Darkening mask is an authored measurement; host image inspection required. No donor/fidelity claim.'}
    images=[]
    for label,height,alpha in [('baseline',.15,0),('3cm',.03,1),('5cm',.05,1),('8cm',.08,1),('10cm',.10,1),('15cm',.15,1)]:
        corners=[(-.75,height-.01,-.75),(-.75,height,-.75),(.75,height,-.75),(.75,height-.01,-.75),
                 (-.75,height-.01,.75),(-.75,height,.75),(.75,height,.75),(.75,height-.01,.75)]
        faces=[(0,1,2,3),(4,7,6,5),(0,4,5,1),(3,2,6,7),(1,5,6,2),(0,3,7,4)]
        positions=[v for face in faces for i in (face[0],face[1],face[2],face[0],face[2],face[3]) for v in corners[i]]
        mesh=out/(label+'.gltf')
        fixture(mesh,positions,[1,.03,.02,alpha])
        argv=[str(binary),'--background','--hide-hud','--smoke','3','--window','640','360',
              '--preview-gltf',str(mesh),'--world-mesh',str(out/'ground.gltf'),
              '--camera-view','elevated','--camera-distance','8',
              '--screenshot',str(out/(label+'.ppm')),'--profile',str(out/(label+'.profile')),'--no-diagnostics']
        run={'label':label,'height':height,'argv':argv}
        manifest['runs'].append(run)
        try:
            result=subprocess.run(argv,capture_output=True,text=True,timeout=20)
            run['exit']=result.returncode
            (out/(label+'.log')).write_text((result.stdout+result.stderr)[:131072])
            if result.returncode:
                raise RuntimeError('low_shadow_native_exit')
            with Image.open(out/(label+'.ppm'))as image:
                image.load()
                if image.size!=(640,360):
                    raise RuntimeError('low_shadow_dimensions')
                pixels=image.convert('RGB')
            pixels.save(out/(label+'.png'))
            run['ppm_sha256']=digest((out/(label+'.ppm')).read_bytes())
            images.append(pixels)
        finally:
            (out/'manifest.json').write_text(json.dumps(manifest,indent=2))
        if sum(p.stat().st_size for p in out.rglob('*')if p.is_file())>CAP:
            raise RuntimeError('low_shadow_output_quota')
    baseline=images[0]
    for run,image in zip(manifest['runs'][1:],images[1:]):
        mask=Image.new('L',image.size)
        mask.putdata([255 if r>g+10 and r>b+10 else 0 for r,g,b in image.getdata()])
        mask=mask.filter(ImageFilter.MaxFilter(3))
        run['caster_mask_bbox']=mask.getbbox()
        mask.save(out/(run['label']+'-excluded-caster.png'))
        count=0
        max_darkening=0
        for before,after,excluded in zip(baseline.getdata(),image.getdata(),mask.getdata()):
            if excluded:
                continue
            darkening=sum(before)-sum(after)
            if darkening>12:
                count+=1
                max_darkening=max(max_darkening,darkening)
        run['receiver_darkened_pixels']=count
        run['max_sum_rgb_darkening']=max_darkening
    sheet=Image.new('RGB',(1920,768),(15,20,25))
    draw=ImageDraw.Draw(sheet)
    for i,(run,image)in enumerate(zip(manifest['runs'],images)):
        x=(i%3)*640;y=(i//3)*384
        sheet.paste(image,(x,y+24))
        draw.text((x+8,y+6),run['label']+' | receiver dark pixels '+str(run.get('receiver_darkened_pixels','baseline')),fill='white')
    sheet.save(out/'comparison.png')
    manifest['sources_unchanged_after']=source.read_bytes()==shader
    manifest['actual_bytes']=sum(p.stat().st_size for p in out.rglob('*')if p.is_file())
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2))
    if not manifest['sources_unchanged_after']or manifest['actual_bytes']>CAP:
        raise RuntimeError('low_shadow_identity_or_quota')
    print(json.dumps({'low_caster_measurements':[{k:r[k]for k in ('label','receiver_darkened_pixels','max_sum_rgb_darkening')}for r in manifest['runs'][1:]],'visual_acceptance':'unresolved; inspect retained frames'}))


if __name__=='__main__':
    main()
