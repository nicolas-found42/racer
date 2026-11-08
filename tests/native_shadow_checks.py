#!/usr/bin/env python3
"""Actual hidden Metal regression: MASK color/cast shadow and flat receiver.

Explicit output is retained, never overwritten. Each of three runs is bounded
at 25s; 640x360 captures and frozen inputs stay below 24MiB. Not a fidelity grade.
"""
import argparse,base64,hashlib,json,shutil,struct,subprocess
from pathlib import Path
from PIL import Image,ImageChops


def fixture(path,positions,rgba,translation=(0,0,0)):
    data=struct.pack('<'+'f'*len(positions),*positions)
    doc={'asset':{'version':'2.0'},'scene':0,'scenes':[{'nodes':[0]}],
         'nodes':[{'mesh':0,'translation':translation}],
         'meshes':[{'primitives':[{'attributes':{'POSITION':0},'material':0}]}],
         'materials':[{'alphaMode':'MASK','alphaCutoff':.5,'pbrMetallicRoughness':
           {'baseColorFactor':rgba,'roughnessFactor':1,'metallicFactor':0}}],
         'buffers':[{'byteLength':len(data),'uri':'data:application/octet-stream;base64,'+base64.b64encode(data).decode()}],
         'bufferViews':[{'buffer':0,'byteLength':len(data)}],
         'accessors':[{'bufferView':0,'componentType':5126,'count':len(positions)//3,'type':'VEC3'}]}
    path.write_text(json.dumps(doc))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--binary',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--receiver-origin',type=float,nargs=3,default=[0,0,0],help='Author source coordinates offset from the mounted world for precision calibration');a=p.parse_args()
    out=a.output.resolve();out.mkdir(exist_ok=False)
    binary=out/'racer';shutil.copy2(a.binary.resolve(),binary)
    identity=hashlib.sha256(binary.read_bytes()).hexdigest()
    # Six independent faces, elevated above a single neutral receiver.
    corners=[(-2,1,-2),(-2,3,-2),(2,3,-2),(2,1,-2),(-2,1,2),(-2,3,2),(2,3,2),(2,1,2)]
    faces=[(0,1,2,3),(4,7,6,5),(0,4,5,1),(3,2,6,7),(1,5,6,2),(0,3,7,4)]
    cube=[v for q in faces for i in (q[0],q[1],q[2],q[0],q[2],q[3]) for v in corners[i]]
    floor=[-100,0,-100,-100,0,100,100,0,100,-100,0,-100,100,0,100,100,0,-100]
    floor=[v-a.receiver_origin[i%3] for i,v in enumerate(floor)]
    fixture(out/'ground.gltf',floor,[.5,.5,.5,1])
    rows=[]
    for name,alpha in [('below',.4999),('equal',.5),('above',.5001)]:
        mesh=out/(name+'.gltf');fixture(mesh,cube,[1,.03,.02,alpha],(0,3,0))
        argv=[str(binary),'--background','--hide-hud','--smoke','4','--window','640','360','--preview-gltf',str(mesh),
              '--world-mesh',str(out/'ground.gltf'),'--camera-view','elevated','--camera-distance','18',
              '--screenshot',str(out/(name+'.ppm')),'--profile',str(out/(name+'.profile')),'--no-diagnostics']
        argv.extend(['--world-origin',*[str(v) for v in a.receiver_origin]])
        result=subprocess.run(argv,capture_output=True,text=True,timeout=25)
        (out/(name+'.log')).write_text(result.stdout+result.stderr)
        rows.append({'argv':argv,'exit':result.returncode})
        if result.returncode:raise RuntimeError('native shadow fixture failed; retained log')
        Image.open(out/(name+'.ppm')).convert('RGB').save(out/(name+'.png'))
    images=[Image.open(out/(name+'.png')).convert('RGB') for name in ['below','equal','above']]
    diff=ImageChops.difference(images[0],images[1]);count=0
    for y in range(80,280):
        for x in range(120,520):
            if 210<=x<370 and 65<=y<215:continue
            if max(diff.getpixel((x,y)))>3:count+=1
    identical=ImageChops.difference(images[1],images[2]).getbbox() is None
    # The no-caster receiver must not contain the former diagonal false shade.
    upper=images[0].getpixel((400,120));lower=images[0].getpixel((400,250))
    neutral=max(abs(a-b) for a,b in zip(upper,lower))<10
    sheet=Image.new('RGB',(1920,360))
    for i,im in enumerate(images):sheet.paste(im,(i*640,0))
    sheet.save(out/'comparison.png')
    (out/'manifest.json').write_text(json.dumps({'binary_sha256':identity,'runs':rows,'ground_changed_pixels_outside_caster':count,
      'equal_above_identical':identical,'below_receiver_uniform':neutral,'output_cap_bytes':24*1024**2},indent=2))
    if sum(f.stat().st_size for f in out.rglob('*') if f.is_file())>24*1024**2:raise RuntimeError('fixture output quota')
    assert identical and count>100 and neutral,'MASK ground shadow or receiver calibration failed'
    print(f'PASS: native MASK cast shadow: {count} ground pixels; equal/above identical; no diagonal false shade')

if __name__=='__main__':main()
