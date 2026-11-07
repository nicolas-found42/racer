#!/usr/bin/env python3
"""Actual hidden neutral post identity against a frozen pre-post capture.

Two4s1280x720 runs,25s each,24MiB output. This checks pixel continuity,
not overall art quality. The frozen old binary and new binary render the same
scale scene so intentional changes to the authored town cannot mask a defect.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
from PIL import Image,ImageChops,ImageStat
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from install_cars import regular_bytes


def sha(data):return hashlib.sha256(data).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--binary',type=Path,required=True);p.add_argument('--baseline',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    manifest=json.loads(regular_bytes(a.baseline/'manifest.json',65536));run=manifest['runs'][0]
    argv=run['argv'][:]
    def option(key):return Path(argv[argv.index(key)+1])
    def verified(path,digest,limit):
        data=regular_bytes(path,limit)
        if sha(data)!=digest:raise ValueError('baseline input drift: '+str(path))
        return data
    verified(a.baseline/'rear.png',run['png_sha256'],4*1024**2)
    baseline_executable=verified(Path(manifest['retained_binary']),manifest['binary_sha256'],16*1024**2)
    library=option('--vehicle-library');lines=regular_bytes(library,65536).decode().splitlines()
    if lines[:2]!=['RACER_VEHICLES 1','1']or len(lines)!=3:raise ValueError('baseline catalog')
    descriptor=library.parent/json.loads(lines[2]);raw=verified(descriptor,manifest['descriptor_sha256'],32768)
    import shlex
    fields={t[0]:t[1:]for line in raw.decode().splitlines()if(t:=shlex.split(line))}
    verified(descriptor.parent/fields['mesh'][0],manifest['mesh_sha256'],32*1024**2)
    for name,digest in manifest['shader_sha256'].items():verified(option('--shader-dir')/name,digest,65536)
    for option_name,key in [('--world-surfaces','surface_sha256'),('--sky-mesh','sky_mesh_sha256'),('--scenery-mesh','scenery_sha256')]:
        if key in manifest and manifest[key]:verified(option(option_name),manifest[key],12*1024**2)
    if manifest.get('world_meshes'):raise ValueError('neutral fixture expects frozen default city')
    executable=regular_bytes(a.binary.resolve(),16*1024**2)
    if len(executable)+len(baseline_executable)+8*1024**2>24*1024**2:raise ValueError('neutral inputs exceed reserved quota')
    out=a.output.resolve();out.mkdir(exist_ok=False)
    binary=out/'racer';binary.write_bytes(executable);binary.chmod(a.binary.stat().st_mode&0o777)
    old_binary=out/'racer-before';old_binary.write_bytes(baseline_executable);old_binary.chmod(binary.stat().st_mode&0o777)
    argv[0]=str(binary)
    for key,name in [('--screenshot','frame.ppm'),('--profile','profile')]:argv[argv.index(key)+1]=str(out/name)
    argv.extend(['--scene','scale'])
    baseline_argv=argv[:];baseline_argv[0]=str(old_binary)
    for key,name in [('--screenshot','before.ppm'),('--profile','before-profile')]:baseline_argv[baseline_argv.index(key)+1]=str(out/name)
    baseline_result=subprocess.run(baseline_argv,capture_output=True,text=True,timeout=25)
    (out/'before.log').write_text(baseline_result.stdout+baseline_result.stderr)
    if baseline_result.returncode:raise RuntimeError('native baseline failed; retained log')
    argv.append('--post-neutral')
    result=subprocess.run(argv,capture_output=True,text=True,timeout=25)
    (out/'run.log').write_text(result.stdout+result.stderr)
    if result.returncode:raise RuntimeError('native neutral failed; retained log')
    image=Image.open(out/'frame.ppm').convert('RGB');image.save(out/'frame.png')
    before=Image.open(out/'before.ppm').convert('RGB');before.save(out/'before.png')
    if image.size!=before.size:raise RuntimeError('neutral dimensions changed')
    diff=ImageChops.difference(image,before);means=ImageStat.Stat(diff).mean
    maximum=max(hi for lo,hi in diff.getextrema())
    record={'argv':argv,'baseline_argv':baseline_argv,'binary_sha256':sha(executable),
            'baseline_binary_sha256':sha(baseline_executable),'baseline_png_sha256':sha((out/'before.png').read_bytes()),
            'baseline_manifest_sha256':sha(regular_bytes(a.baseline/'manifest.json',65536)),
            'mean_absolute_rgb':means,'maximum_absolute_rgb':maximum,'limits':'max1byte,mean.05perchannel'}
    (out/'manifest.json').write_text(json.dumps(record,indent=2))
    if sum(f.stat().st_size for f in out.rglob('*')if f.is_file())>24*1024**2:raise RuntimeError('neutral output quota')
    assert maximum<=1 and max(means)<.05,'neutral pipeline changed orientation/image/HUD beyond quantization'
    print('PASS: native neutral matches frozen frame within1byte; meanRGB='+str(means))


if __name__=='__main__':main()
