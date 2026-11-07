#!/usr/bin/env python3
"""Hidden Metal regression for false self-shadow ripples on an unoccluded slope.

One4s run,25s deadline,16MiB retained output. The image metric checks this
pinned native fixture; it is not a visual-fidelity or all-GPU quality grade.
"""
import argparse,hashlib,json,math,shutil,subprocess
from pathlib import Path
from PIL import Image,ImageFilter
from native_shadow_checks import fixture


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--binary',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();out=a.output.resolve();out.mkdir(exist_ok=False)
    binary=out/'racer';source=a.binary.resolve()
    if source.stat().st_size>16*1024**2:raise ValueError('fixture executable exceeds16MiB')
    shutil.copy2(source,binary);identity=hashlib.sha256(binary.read_bytes()).hexdigest()
    floor=[-100,30,-100,-100,30,100,100,-30,100,-100,30,-100,100,-30,100,100,-30,-100]
    fixture(out/'slope.gltf',floor,[.5,.5,.5,1])
    fixture(out/'empty.gltf',[-1,1,0,0,2,0,1,1,0],[1,0,0,0])
    argv=[str(binary),'--background','--hide-hud','--smoke','4','--window','640','360',
          '--preview-gltf',str(out/'empty.gltf'),'--world-mesh',str(out/'slope.gltf'),
          '--camera-view','elevated','--camera-distance','18','--screenshot',str(out/'frame.ppm'),
          '--profile',str(out/'profile'),'--no-diagnostics']
    result=subprocess.run(argv,capture_output=True,text=True,timeout=25)
    (out/'run.log').write_text(result.stdout+result.stderr)
    if result.returncode:raise RuntimeError('native slope run failed; retained log')
    image=Image.open(out/'frame.ppm').convert('RGB');image.save(out/'frame.png')
    gray=image.convert('L');blur=gray.filter(ImageFilter.GaussianBlur(2));squared=0;count=0;large=0
    # Exclude HUD panels and the small green event beacon, retaining the smooth
    # untextured receiver where the old PCF produced regular high frequencies.
    for y in range(85,265):
        for x in range(100,540):
            red,green,blue=image.getpixel((x,y))
            if green>red+10:continue
            delta=gray.getpixel((x,y))-blur.getpixel((x,y))
            squared+=delta*delta;count+=1;large+=abs(delta)>2
    rms=math.sqrt(squared/count)
    (out/'manifest.json').write_text(json.dumps({'argv':argv,'binary_sha256':identity,
      'rms_highpass':rms,'pixels_over2':large,'samples':count,'rms_limit':.8,'pixel_limit':250},indent=2))
    if sum(f.stat().st_size for f in out.rglob('*') if f.is_file())>16*1024**2:raise RuntimeError('slope output quota')
    assert rms<.8 and large<250,'unoccluded sloping receiver contains shadow ripples'
    print(f'PASS: native unoccluded slope rms={rms:.6f}, high-frequency pixels={large}/{count}')

if __name__=='__main__':main()
