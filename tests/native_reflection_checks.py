#!/usr/bin/env python3
"""Bounded actual Metal reflection roughness experiment; no untuned pass threshold.

Default prepares only. --execute runs a previously frozen manifest explicitly.
--measure requires a directly inspected interior ROI and records descriptive
metrics only: it never establishes mip filtering or visual fidelity by itself.
"""
import argparse
import base64
import hashlib
import io
import json
import math
import os
from pathlib import Path
import stat
import struct
import subprocess
import threading
from PIL import Image, ImageFilter

CAP=24*1024**2
BINARY_CAP=12*1024**2
FILE_CAP=1024**2
LOG_CAP=128*1024
WIDTH,HEIGHT=640,360


def require(ok,message):
    if not ok:raise ValueError(message)


def sha(data):return hashlib.sha256(data).hexdigest()


def regular(path,limit):
    path=Path(path).absolute();require(not any(p.is_symlink() for p in(path,*path.parents)),'symlink refused; use real absolute path')
    fd=os.open(path,os.O_RDONLY|os.O_NONBLOCK|os.O_NOFOLLOW)
    with os.fdopen(fd,'rb')as stream:
        before=os.fstat(stream.fileno());require(stat.S_ISREG(before.st_mode),'regular file required')
        data=stream.read(limit+1);after=os.fstat(stream.fileno())
    require(len(data)<=limit and len(data)==before.st_size and(before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns),'size or concurrent input change')
    return data


def write_new(path,data):
    path=Path(path)
    if path.exists()or path.is_symlink():require(regular(path,len(data))==data,'output conflict');return
    with path.open('xb')as stream:stream.write(data)


def encoded(value):return(json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()


def quota(root,reserve=0):
    total=0
    for p in root.iterdir():
        require(not p.is_symlink()and p.is_file(),'unexpected output entry')
        total+=p.stat().st_size
        require(total+reserve<=CAP,'24MiB output quota')
    return total


def gltf(groups,materials):
    blob=bytearray();views=[];accessors=[];primitives=[]
    for vertices,normals,material in groups:
        attrs={}
        for name,values in [('POSITION',vertices),('NORMAL',normals)]:
            flat=[v for row in values for v in row];start=len(blob);blob.extend(struct.pack('<'+'f'*len(flat),*flat))
            views.append({'buffer':0,'byteOffset':start,'byteLength':len(blob)-start})
            a={'bufferView':len(views)-1,'componentType':5126,'count':len(values),'type':'VEC3'}
            if name=='POSITION':a.update(min=[min(r[i]for r in values)for i in range(3)],max=[max(r[i]for r in values)for i in range(3)])
            accessors.append(a);attrs[name]=len(accessors)-1
        primitives.append({'attributes':attrs,'material':material})
    return encoded({'asset':{'version':'2.0','generator':'Racer authored reflection calibration'},'scene':0,'scenes':[{'nodes':[0]}],'nodes':[{'mesh':0}],'meshes':[{'primitives':primitives}],'materials':materials,'buffers':[{'byteLength':len(blob),'uri':'data:application/octet-stream;base64,'+base64.b64encode(blob).decode()}],'bufferViews':views,'accessors':accessors})


def quad(a,b,c,d):return[a,b,c,a,c,d]


def material(color,roughness,metal=0,coat=None):
    result={'alphaMode':'OPAQUE','pbrMetallicRoughness':{'baseColorFactor':[*color,1],'roughnessFactor':roughness,'metallicFactor':metal}}
    if coat is not None:result['extensions']={'KHR_materials_clearcoat':{'clearcoatFactor':1,'clearcoatRoughnessFactor':coat}}
    return result


def prepare(binary,out,coat=False):
    raw=regular(binary,BINARY_CAP);out=Path(out).absolute();require(not any(p.is_symlink()for p in(out,*out.parents)),'output symlink')
    require(not out.exists(),'fresh output directory required');out.mkdir(parents=True)
    write_new(out/'racer',raw);(out/'racer').chmod(0o700)
    white=[];black=[]
    for iy in range(32):
        for ix in range(80):
            x=-16+ix*.4;y=iy*.4
            (white if(ix+iy)%2 else black).extend(quad((x,y,-15),(x+.4,y,-15),(x+.4,y+.4,-15),(x,y+.4,-15)))
    floor_white=[];floor_black=[]
    for iz in range(40):
        for ix in range(80):
            x=-16+ix*.4;z=-16+iz*.4
            (floor_white if(ix+iz)%2 else floor_black).extend(quad((x,-.05,z),(x,-.05,z+.4),(x+.4,-.05,z+.4),(x+.4,-.05,z)))
    # Coplanar overlapping receivers would invalidate the contrast experiment.
    ground=quad((-60,-.055,-60),(-60,-.055,60),(60,-.055,60),(60,-.055,-60))
    world=gltf([(white,[(0,0,1)]*len(white),0),(black,[(0,0,1)]*len(black),1),(floor_white,[(0,1,0)]*len(floor_white),0),(floor_black,[(0,1,0)]*len(floor_black),1),(ground,[(0,1,0)]*6,2)],[material([.95]*3,.95),material([.015]*3,.95),material([.18]*3,1)])
    write_new(out/'checker-world.gltf',world)
    plane=quad((-2,.3,0),(-2,3,0),(2,3,0),(2,.3,0))
    variants=[('smooth',.08,None),('middle',.5,None),('rough',1,None)]
    if coat:variants.append(('coat',1,.08))
    inputs={'racer':sha(raw),'checker-world.gltf':sha(world)};runs=[]
    for name,rough,clearcoat in variants:
        fixture=gltf([(plane,[(0,0,-1)]*6,0)],[material([.6]*3,rough,1,clearcoat)])
        filename=name+'.gltf';write_new(out/filename,fixture);inputs[filename]=sha(fixture)
        argv=[str(out/'racer'),'--background','--smoke','4','--window',str(WIDTH),str(HEIGHT),'--hide-hud','--preview-gltf',str(out/filename),'--world-mesh',str(out/'checker-world.gltf'),'--camera-view','rear','--camera-distance','8','--screenshot',str(out/(name+'.ppm')),'--profile',str(out/(name+'.profile')),'--no-diagnostics']
        runs.append({'name':name,'roughness':rough,'metallic':1,'coatRoughness':clearcoat,'argv':argv})
    manifest={'binary_sha256':sha(raw),'binary_bytes':len(raw),'inputs':inputs,'runs':runs,'working_directory':str(Path.cwd()),'per_run_timeout_seconds':25,'child_file_limit':'none; avoid Metal/dyld cache interference','retained_log_cap_bytes':LOG_CAP,'output_cap_bytes':CAP,'fixture':{'plane_bounds':[[-2,.3,0],[2,3,0]],'checker_wall_bounds':[[-16,0,-15],[16,12.8,-15]],'checker_floor_bounds':[[-16,-.05,-16],[16,-.05,0]],'base_ground_y_m':-.055,'checker_cell_m':.4,'wall_behind_camera':True,'cube_center_y_m':1.6,'source_alpha':1,'alphaMode':'OPAQUE'},'interpretation':'Pending actual Metal execution, direct image inspection and qualified nonblank interior crop. No metric pass threshold defined.'}
    plan=encoded(manifest);write_new(out/'prepared.json',plan);write_new(out/'prepared.sha256',(sha(plan)+'\n').encode());quota(out)
    return manifest


def run_child(argv,cwd,log):
    stats={'observed_log_bytes':0,'retained_log_bytes':0,'log_truncated':False}
    try:process=subprocess.Popen(argv,cwd=cwd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    except OSError as error:return dict(stats,exit=None,reason='spawn_error',error=str(error))
    def drain():
        with log.open('xb')as stream:
            while True:
                data=process.stdout.read(8192)
                if not data:break
                stats['observed_log_bytes']+=len(data)
                retained=data[:max(0,LOG_CAP-stats['retained_log_bytes'])]
                stream.write(retained);stats['retained_log_bytes']+=len(retained)
        stats['log_truncated']=stats['observed_log_bytes']>stats['retained_log_bytes']
    reader=threading.Thread(target=drain,daemon=True);reader.start();reason='exited'
    try:code=process.wait(timeout=25)
    except subprocess.TimeoutExpired:
        reason='timeout';process.kill();code=process.wait(timeout=5)
    reader.join(timeout=3)
    stats['log_reader_complete']=not reader.is_alive()
    return dict(stats,exit=code,reason=reason)



def execute(out):
    plan=regular(out/'prepared.json',128*1024);require(sha(plan)==regular(out/'prepared.sha256',65).decode().strip(),'plan drift');manifest=json.loads(plan)
    for name,digest in manifest['inputs'].items():require(Path(name).name==name and sha(regular(out/name,BINARY_CAP))==digest,'frozen input drift')
    require(not(out/'executed.json').exists(),'execution already retained')
    # Existing native renderer could compete for the shared GPU and distort data.
    probe=subprocess.run(['/usr/bin/pgrep','-x','racer'],capture_output=True,timeout=3)
    require(probe.returncode==1,'another Racer process exists or process inventory failed')
    require(all(row['argv'][0]==str(out/'racer') for row in manifest['runs']),'prepared directory moved; frozen argv path mismatch')
    results=[]
    for row in manifest['runs']:
        name=row['name'];quota(out,3*1024**2)
        require(not any((out/(name+suffix)).exists()for suffix in('.ppm','.png','.log','.profile')),'partial run retained; use fresh output')
        log=out/(name+'.log')
        status=run_child(row['argv'],manifest['working_directory'],log)
        result={'name':name,'argv':row['argv'],**status}
        if log.exists():result['log_sha256']=sha(regular(log,LOG_CAP))
        results.append(result)
        # Preserve exit/signal/timeout/spawn evidence even if no screenshot exists.
        write_new(out/(name+'-run.json'),encoded(result))
        require(status['exit']==0 and status['reason']=='exited' and status.get('log_reader_complete',False),'native run failed; retained per-run metadata/log')
        ppm=regular(out/(name+'.ppm'),FILE_CAP)
        with Image.open(io.BytesIO(ppm))as im:
            require(im.size==(WIDTH,HEIGHT),'unexpected capture dimensions');buf=io.BytesIO();im.convert('RGB').save(buf,format='PNG')
        write_new(out/(name+'.png'),buf.getvalue());result['ppm_sha256']=sha(ppm);result['png_sha256']=sha(buf.getvalue());quota(out)
        write_new(out/(name+'-capture.json'),encoded(result))
    write_new(out/'executed.json',encoded({'runs':results,'interpretation':'Captured only; manual interior crop qualification required.'}));return results


def measure(out,roi,note):
    require(len(note.strip())>=20,'record actual image inspection and nonblank crop rationale')
    x,y,w,h=roi;require(0<=x<x+w<=WIDTH and 0<=y<y+h<=HEIGHT and w>=8 and h>=8,'interior crop bounds')
    manifest=json.loads(regular(out/'executed.json',128*1024));rows=[]
    for run in manifest['runs']:
        raw=regular(out/(run['name']+'.png'),FILE_CAP);require(sha(raw)==run['png_sha256'],'capture drift')
        with Image.open(io.BytesIO(raw))as im:
            crop=im.convert('RGB').crop((x,y,x+w,y+h));gray=crop.convert('L');values=list(gray.tobytes());mean=sum(values)/len(values)
            variance=sum((v-mean)**2 for v in values)/len(values)
            hp=ImageFilter.GaussianBlur(1);blur=list(gray.filter(hp).tobytes())
            highpass=math.sqrt(sum((a-b)**2 for a,b in zip(values,blur))/len(values))
            rows.append({'name':run['name'],'png_sha256':sha(raw),'luma_mean':mean,'luma_variance':variance,'luma_min':min(values),'luma_max':max(values),'highpass_rms_sigma1':highpass})
    report={'roi_xywh':roi,'direct_inspection_note':note,'metrics':rows,'qualification':'Descriptive display-space contrast only. No untuned threshold, pass/fail, native BRDF equivalence or fidelity claim.'}
    write_new(out/('metrics-'+'-'.join(map(str,roi))+'.json'),encoded(report));quota(out);return report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--binary',type=Path);p.add_argument('--coat',action='store_true');p.add_argument('--execute',action='store_true');p.add_argument('--measure',type=int,nargs=4,metavar=('X','Y','W','H'));p.add_argument('--crop-note',default='');a=p.parse_args()
    require(sum([a.binary is not None,a.execute,a.measure is not None])==1,'choose prepare (--binary), --execute, or --measure')
    out=a.output.absolute();require(not any(v.is_symlink()for v in(out,*out.parents)),'output symlink; use real absolute path')
    if a.binary:r=prepare(a.binary,out,a.coat)
    elif a.execute:r=execute(out)
    else:r=measure(out,a.measure,a.crop_note)
    print(json.dumps(r,indent=2))


if __name__=='__main__':main()
