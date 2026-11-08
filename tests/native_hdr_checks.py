#!/usr/bin/env python3
"""One hidden native shared-HDR-post technical probe; not a game fidelity test.

Retains frozen executable, exact build-source identities, PPM/PNG and pixel ROIs.
One three-second run,20s deadline,8MiB owned output cap. Never activates windows.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import stat
import subprocess
import time
from PIL import Image,ImageStat

CAP=8*1024**2
BINARY_LIMIT=6*1024**2
ROOT=Path(__file__).resolve().parents[1]


def sha(data):return hashlib.sha256(data).hexdigest()


def local_path(path):
    path=Path(path).absolute()
    return Path('/tmp').resolve().joinpath(*path.parts[2:])if path.parts[1:2]==('tmp',)else path


def regular(path,limit):
    if any(p.is_symlink()for p in (path,*path.parents)):raise ValueError('symlink_refused: '+str(path))
    descriptor=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        info=os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode)or not 0<info.st_size<=limit:raise ValueError('input_size_or_type')
        with os.fdopen(descriptor,'rb',closefd=False)as stream:data=stream.read(limit+1)
        after=os.fstat(descriptor)
        if len(data)!=info.st_size or (info.st_size,info.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):raise ValueError('input_changed')
        return data,stat.S_IMODE(info.st_mode)
    finally:os.close(descriptor)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();binary,mode=regular(local_path(args.binary),BINARY_LIMIT)
    sources={name:regular(ROOT/name,128*1024)[0]for name in ('tests/native_hdr_probe.cpp','src/post_process.h','tests/native_hdr_checks.py')}
    if len(binary)+sum(map(len,sources.values()))+1024*1024>CAP:raise ValueError('probe_preflight_quota')
    output=local_path(args.output)
    if any(p.is_symlink()for p in (output,*output.parents)):raise ValueError('output_symlink_refused')
    # An existing capture directory is always retained; reruns require a new path.
    output.mkdir(parents=True,exist_ok=False)
    frozen=output/'native_hdr_probe';frozen.write_bytes(binary);frozen.chmod(mode|stat.S_IXUSR)
    source_dir=output/'sources';source_dir.mkdir()
    for name,data in sources.items():(source_dir/Path(name).name).write_bytes(data)
    argv=[str(frozen),str(output/'frame.ppm')]
    record={'authority':'Actual native shared-PostProcess technical fixture, not game PBR/native donor equivalence or visual-quality acceptance',
            'argv':argv,'binary_sha256':sha(binary),'source_sha256':{name:sha(data)for name,data in sources.items()},
            'limits':{'output_bytes':CAP,'native_seconds':3,'timeout_seconds':20,'window':[640,360],'hidden':True},'status':'started'}
    (output/'manifest.json').write_text(json.dumps(record,indent=2))
    began=time.monotonic()
    try:
        try:result=subprocess.run(argv,cwd=ROOT,capture_output=True,text=True,timeout=20)
        except subprocess.TimeoutExpired as error:
            raw=(error.stdout or b'')+(error.stderr or b'')
            if isinstance(raw,str):raw=raw.encode()
            (output/'run.log').write_bytes(raw[:128*1024]);raise
        log=result.stdout+result.stderr;(output/'run.log').write_text(log);record.update(returncode=result.returncode,elapsed_seconds=time.monotonic()-began)
        if result.returncode:raise RuntimeError('native HDR probe failed; retained run.log')
        for name,key in [('tests/native_hdr_probe.cpp','probe_source_sha256'),('src/post_process.h','post_source_sha256')]:
            if key+'='+sha(sources[name])not in result.stdout:raise RuntimeError('compiled source identity mismatch: '+name)
        if sha(regular(frozen,BINARY_LIMIT)[0])!=record['binary_sha256']:raise RuntimeError('frozen executable changed')
        for name,data in sources.items():
            if regular(ROOT/name,128*1024)[0]!=data:raise RuntimeError('source changed during probe: '+name)
        ppm,_=regular(output/'frame.ppm',1024*1024);image=Image.open(output/'frame.ppm').convert('RGB')
        if image.size!=(640,360):raise RuntimeError('native drawable dimensions')
        image.save(output/'frame.png');roundtrip=Image.open(output/'frame.png').convert('RGB')
        if roundtrip.tobytes()!=image.tobytes():raise RuntimeError('PNG pixel preservation')
        panels=[]
        for index,radiance in enumerate((1.,4.,8.,1.)):
            box=(index*160+40,100,index*160+120,260);statistics=ImageStat.Stat(image.crop(box))
            expected=255*math.pow(radiance/(radiance+.72),1/2.2)
            error=max(abs(value-expected)for value in statistics.mean)
            panels.append({'index':index,'roi':box,'radiance_after_linear_blend':radiance,'expected_rgb':expected,
                           'mean_rgb':statistics.mean,'stddev_rgb':statistics.stddev,'maximum_mean_error':error})
        record.update(panels=panels,ppm_sha256=sha(ppm),png_sha256=sha((output/'frame.png').read_bytes()),
                      rgba_sha256=sha(image.convert('RGBA').tobytes()))
        if any(panel['maximum_mean_error']>2 or max(panel['stddev_rgb'])>1 for panel in panels):raise AssertionError('neutral HDR analytic ROI mismatch')
        if min(panels[2]['mean_rgb'])-max(panels[1]['mean_rgb'])<5:raise AssertionError('four/eight radiance headroom lost')
        if max(abs(a-b)for a,b in zip(panels[0]['mean_rgb'],panels[3]['mean_rgb']))>1:raise AssertionError('linear alpha blend four*.25 does not equal one')
        record['status']='passed'
    except Exception as error:
        record.update(status='failed',failure=str(error));raise
    finally:
        record['retained_bytes']=sum(path.stat().st_size for path in output.rglob('*')if path.is_file())
        (output/'manifest.json').write_text(json.dumps(record,indent=2))
    if sum(path.stat().st_size for path in output.rglob('*')if path.is_file())>CAP:raise RuntimeError('HDR probe output quota')
    print('PASS: actual shared HDR post neutral1/4/8 headroom and4*.25 linear alpha ROIs; no game visual-fidelity claim')


if __name__=='__main__':main()
