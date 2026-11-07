#!/usr/bin/env python3
"""Resize the owned hidden SDL window through the normal renderer loop.

One bounded20s run,40s deadline,24MiB output. Six actual frames cover medium,odd,
minimum, oversize-wide and restored dimensions. No desktop activation/input.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from PIL import Image,ImageStat


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--binary',type=Path,required=True)
    p.add_argument('--library',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    source=a.binary.resolve()
    if not source.is_file()or source.stat().st_size>12*1024**2:raise ValueError('resize executable bound')
    out=a.output.resolve();out.mkdir(exist_ok=False);binary=out/'racer';binary.write_bytes(source.read_bytes());binary.chmod(source.stat().st_mode&0o777)
    cases=[('initial',640,360),('medium',960,540),('odd',1281,721),('minimum',320,240),('wide',3900,240),('restore',1280,720)]
    commands=['wait .3']
    for index,(name,w,h)in enumerate(cases):
        if index:commands.extend([f'resize {w} {h}','wait .6'])
        commands.append('capture '+str(out/(name+'.ppm')))
    commands.extend(['wait .3','quit']);script=out/'review.txt';script.write_text('\n'.join(commands)+'\n')
    argv=[str(binary),'--background','--window','640','360','--smoke','20','--review-script',str(script),
          '--vehicle-library',str(a.library.resolve()),'--vehicle','0','--profile',str(out/'profile'),'--no-diagnostics']
    run=subprocess.run(argv,capture_output=True,text=True,timeout=40);log=run.stdout+run.stderr;(out/'run.log').write_text(log)
    if run.returncode:raise RuntimeError('native resize failed; retained log')
    records=[]
    for name,w,h in cases:
        path=out/(name+'.ppm');image=Image.open(path).convert('RGB')
        if image.size!=(w,h):raise RuntimeError('actual drawable differs from requested '+name+': '+str(image.size))
        # A differently configured DPI host fails explicitly rather than claiming
        # an oversize transition that it did not actually exercise.
        image.save(out/(name+'.png'));stats=ImageStat.Stat(image.crop((w//4,h//3,3*w//4,2*h//3)))
        if max(stats.mean)<10 or max(stats.stddev)<5:raise RuntimeError('blank resized scene '+name)
        records.append({'name':name,'dimensions':image.size,'sha256':sha(path),'scene_mean':stats.mean,'scene_stddev':stats.stddev})
    (out/'manifest.json').write_text(json.dumps({'argv':argv,'binary_sha256':sha(binary),'frames':records,
         'claim':'Observed these hidden drawable transitions only; physical display/DPI/minimize and readability need separate evidence'},indent=2))
    if sum(f.stat().st_size for f in out.rglob('*')if f.is_file())>24*1024**2:raise RuntimeError('resize output quota')
    print('PASS: actual hidden640x360 ->960x540 ->1281x721 ->320x240 ->3900x240 ->1280x720; six nonblank frames')


if __name__=='__main__':main()
