#!/usr/bin/env python3
"""Hidden Metal direction/continuity probes for the normal-texture consumer.

Twelve4s640x360 runs,25s each,32MiB total. Analytic constant maps isolate
basis orientation from texture artwork. This is not a visual-fidelity grade.
"""
import argparse
import base64
import hashlib
import io
import json
from pathlib import Path
import struct
import subprocess
from PIL import Image,ImageChops,ImageStat
from native_shadow_checks import fixture


def surface(path, color=None, uv_scale=1, back=False, degenerate=False, tangent=None, scale=1, mirror_v=False):
    positions=[(-100,0,-100),(-100,0,100),(100,0,100),(-100,0,-100),(100,0,100),(100,0,-100)]
    uv=[((x+100)/200*uv_scale,(z+100)/200*(-1 if mirror_v else 1))for x,y,z in positions]
    if degenerate:uv=[(0,0)]*6
    if back:
        positions=[positions[i]for i in [0,2,1,3,5,4]];uv=[uv[i]for i in [0,2,1,3,5,4]]
    blob=bytearray();views=[];accessors=[]
    def stream(rows,kind):
        offset=len(blob)
        for row in rows:blob.extend(struct.pack('<'+'f'*len(row),*row))
        views.append({'buffer':0,'byteOffset':offset,'byteLength':len(blob)-offset})
        accessors.append({'bufferView':len(views)-1,'componentType':5126,'count':len(rows),'type':kind})
        return len(accessors)-1
    attrs={'POSITION':stream(positions,'VEC3'),'NORMAL':stream([(0,-1 if back else 1,0)]*6,'VEC3'),'TEXCOORD_0':stream(uv,'VEC2')}
    if tangent:attrs['TANGENT']=stream([tangent]*6,'VEC4')
    mat={'pbrMetallicRoughness':{'baseColorFactor':[.4,.4,.4,1],'metallicFactor':0,'roughnessFactor':1},'doubleSided':True}
    doc={'asset':{'version':'2.0'},'scene':0,'scenes':[{'nodes':[0]}],'nodes':[{'mesh':0}],
         'meshes':[{'primitives':[{'attributes':attrs,'material':0}]}],'materials':[mat],
         'accessors':accessors,'bufferViews':views,'buffers':[{'byteLength':len(blob),'uri':'data:application/octet-stream;base64,'+base64.b64encode(blob).decode()}]}
    if color:
        png=io.BytesIO();Image.new('RGB',(2,2),color).save(png,format='PNG')
        doc.update(images=[{'uri':'data:image/png;base64,'+base64.b64encode(png.getvalue()).decode()}],textures=[{'source':0}])
        mat['normalTexture']={'index':0,'texCoord':0,'scale':scale}
    path.write_text(json.dumps(doc))


def mean(image):return sum(ImageStat.Stat(image.convert('L').crop((120,130,350,220))).mean)


def difference(a,b):
    diff=ImageChops.difference(a,b).crop((120,130,350,220))
    return max(ImageStat.Stat(diff).mean)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--binary',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    source=a.binary.resolve();executable=source.read_bytes()
    if len(executable)>12*1024**2:raise ValueError('normal executable bound')
    out=a.output.resolve();out.mkdir(exist_ok=False);binary=out/'racer';binary.write_bytes(executable);binary.chmod(source.stat().st_mode&0o777)
    fixture(out/'empty.gltf',[-1,1,0,0,2,0,1,1,0],[1,0,0,0])
    x=(204,128,230);z=(128,204,230)
    cases=[('none',{}),('plus_x',{'color':x}),('minus_x',{'color':(51,128,230)}),
           ('tiny_uv',{'color':x,'uv_scale':1e-6}),('degenerate',{'color':x,'degenerate':True}),
           ('back_x',{'color':x,'back':True}),('scale_zero',{'color':x,'scale':0}),
           ('plus_z',{'color':z}),('authored_90',{'color':x,'tangent':(0,0,1,-1)}),
           ('mirror_u',{'color':x,'uv_scale':-1}),('handedness',{'color':z,'tangent':(1,0,0,1)}),
           ('mirror_v',{'color':z,'mirror_v':True})]
    images={};runs=[]
    for name,settings in cases:
        mesh=out/(name+'.gltf');surface(mesh,**settings)
        argv=[str(binary),'--background','--hide-hud','--smoke','4','--window','640','360','--preview-gltf',str(out/'empty.gltf'),
              '--world-mesh',str(mesh),'--camera-view','elevated','--camera-distance','18','--screenshot',str(out/(name+'.ppm')),
              '--profile',str(out/(name+'.profile')),'--no-diagnostics']
        result=subprocess.run(argv,capture_output=True,text=True,timeout=25);(out/(name+'.log')).write_text(result.stdout+result.stderr)
        runs.append({'name':name,'argv':argv,'exit':result.returncode,'mesh_sha256':hashlib.sha256(mesh.read_bytes()).hexdigest()})
        (out/'manifest.json').write_text(json.dumps({'binary_sha256':hashlib.sha256(executable).hexdigest(),'runs':runs},indent=2))
        if result.returncode:raise RuntimeError('native normal failed '+name)
        frame=Image.open(out/(name+'.ppm')).convert('RGB');frame.save(out/(name+'.png'));images[name]=frame
        if frame.size!=(640,360)or mean(frame)<10:raise RuntimeError('blank normal fixture '+name)
        print('captured '+name,flush=True)
        if sum(f.stat().st_size for f in out.rglob('*')if f.is_file())>32*1024**2:raise RuntimeError('normal output quota')
    metrics={'plus_x':mean(images['plus_x']),'minus_x':mean(images['minus_x']),'plus_z':mean(images['plus_z'])}
    for name,other in [('tiny_uv','plus_x'),('degenerate','none'),('scale_zero','none'),('back_x','minus_x'),
                       ('authored_90','plus_z'),('mirror_u','minus_x'),('handedness','mirror_v')]:
        metrics[name+'_delta']=difference(images[name],images[other])
    (out/'metrics.json').write_text(json.dumps(metrics,indent=2))
    assert metrics['minus_x']>metrics['plus_x']+15,'tiltX sign does not follow known sun direction'
    assert metrics['plus_z']>metrics['plus_x']+15,'tiltZ sign does not follow known sun direction'
    for name in ['tiny_uv','degenerate','scale_zero','back_x','authored_90','mirror_u','handedness']:
        assert metrics[name+'_delta']<2,name+' basis differs from analytic equivalent'
    print('PASS: native direction, scale-relative UV, degenerate/zero fallback, back-face full reversal, supplied90degree tangent, mirroredUV/handedness')


if __name__=='__main__':main()
