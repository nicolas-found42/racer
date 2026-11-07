#!/usr/bin/env python3
"""Prepare the pinned SLRR231 cloudy sky as an explicitly authored unlit preview."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import struct

PINS = {'meshes/skydome.SCX':'289169d2d53b16fb0c370996f1ca13ff5b59c1546314d32e28cb8eb9f0c66047',
        'textures/cloudy_day01.dds':'0e010e5b69b9b596dd7f299652ee868dde20e5e3f575684c712de6e5798d280c',
        '../skydome.rdb':'d8421b4b2d4e27834fc339e87edb459613f78eed1356e51760ad049730402e94'}
MAX_GLB=12*1024**2

def digest(data): return hashlib.sha256(data).hexdigest()

def no_symlinks(path):
    for p in (path,*path.parents):
        if p.is_symlink(): raise ValueError(f'symlink forbidden: {p}')

def read_source(root):
    result={}
    for name,pin in PINS.items():
        p=root/name;no_symlinks(p)
        if not p.is_file() or p.stat().st_size>3*1024**2: raise ValueError('source missing or exceeds bound')
        data=p.read_bytes()
        if len(data)>3*1024**2 or digest(data)!=pin: raise ValueError(f'source hash mismatch: {name}')
        result[name]=data
    return result

def package(positions,uv,indices,png,count,triangles,bounds):
    binary=bytearray();views=[];accessors=[]
    def append(data):
        binary.extend(bytes((-len(binary))%4));offset=len(binary);binary.extend(data)
        views.append({'buffer':0,'byteOffset':offset,'byteLength':len(data)});return len(views)-1
    def accessor(data,kind,component,n,**extra):
        accessors.append(dict(bufferView=append(data),componentType=component,type=kind,count=n,**extra));return len(accessors)-1
    attrs={'POSITION':accessor(positions,'VEC3',5126,count,min=bounds[0],max=bounds[1]),
           'TEXCOORD_0':accessor(uv,'VEC2',5126,count)}
    idx=accessor(indices,'SCALAR',5125,triangles*3);imageview=append(png)
    doc={'asset':{'version':'2.0','generator':'Racer pinned SLRR sky preparer'},'scene':0,'scenes':[{'nodes':[0]}],
         'nodes':[{'mesh':0,'scale':[1,1,1]}],'meshes':[{'primitives':[{'attributes':attrs,'indices':idx,'material':0,'mode':4}]}],
         'materials':[{'name':'source-cloudy-authored-unlit','doubleSided':True,'extensions':{'KHR_materials_unlit':{}},
          'pbrMetallicRoughness':{'baseColorFactor':[1,1,1,1],'baseColorTexture':{'index':0},'metallicFactor':0,'roughnessFactor':1}}],
         'extensionsUsed':['KHR_materials_unlit'],'images':[{'mimeType':'image/png','bufferView':imageview}],
         'textures':[{'source':0,'sampler':0}],'samplers':[{'wrapS':33071,'wrapT':33071,'minFilter':9729,'magFilter':9729}],
         'buffers':[{'byteLength':len(binary)}],'bufferViews':views,'accessors':accessors}
    js=json.dumps(doc,separators=(',',':'),allow_nan=False).encode();js+=b' '*((-len(js))%4);binary.extend(bytes((-len(binary))%4))
    glb=struct.pack('<III',0x46546c67,2,28+len(js)+len(binary))+struct.pack('<II',len(js),0x4e4f534a)+js+struct.pack('<II',len(binary),0x004e4942)+binary
    if len(glb)>MAX_GLB: raise ValueError('GLB exceeds12MiB')
    return glb

def prepare(source):
    from PIL import Image
    inputs=read_source(source);scx=inputs['meshes/skydome.SCX'];dds=inputs['textures/cloudy_day01.dds']
    # Fixed array offsets are admitted only after all three complete source hashes match.
    assert scx[:8]==b'INVO\x03\0\0\0' and struct.unpack_from('<I',scx,144)[0]==376
    positions=b''.join(scx[148+64*i:160+64*i] for i in range(376));uv=b''.join(scx[172+64*i:180+64*i] for i in range(376))
    off=148+64*376;assert struct.unpack_from('<I',scx,off)[0]==350
    indices=scx[off+4:off+4+350*12]
    assert dds[:4]==b'DDS ' and dds[84:88]==b'DXT1' and struct.unpack_from('<II',dds,12)==(2048,2048)
    image=Image.open(io.BytesIO(dds)).convert('RGBA');rgba=image.tobytes()
    if image.size!=(2048,2048) or len(rgba)>16*1024**2: raise ValueError('image exceeds RGBA bound')
    png=io.BytesIO();image.save(png,format='PNG');points=list(struct.iter_unpack('<3f',positions))
    bounds=([min(p[k] for p in points) for k in range(3)],[max(p[k] for p in points) for k in range(3)])
    glb=package(positions,uv,indices,png.getvalue(),376,350,bounds)
    report={'version':1,'sources':PINS,'glb_sha256':digest(glb),'glb_bytes':len(glb),'rgba_sha256':digest(rgba),'rgba_bytes':len(rgba),
            'vertices':376,'triangles':350,'bounds':bounds,'policy':'Source positions/UV/indices and mip0 pixels unchanged. Authored unlit white, clamp/linear, double-sided, root scale1; no V flip.',
            'unknowns':['Native cardinal orientation, camera centering, horizon transform and HDR exposure unverified.','No source normals exported; renderer must use an unlit sky pass.']}
    return glb,(json.dumps(report,indent=2,sort_keys=True)+'\n').encode()

def publish(output,glb,manifest):
    no_symlinks(output)
    names={'sky.glb':glb,'manifest.json':manifest}
    # Preflight the complete pair before making any directory or changing files.
    for name,data in names.items():
        p=output/name;no_symlinks(p)
        if p.exists() and (not p.is_file() or p.stat().st_size!=len(data) or p.read_bytes()!=data): raise ValueError(f'output conflict: {p}')
    output.mkdir(parents=True,exist_ok=True)
    for name,data in names.items():
        p=output/name
        if p.exists(): continue
        # Exclusive final creation prevents overwriting a concurrent writer.
        with p.open('xb') as stream: stream.write(data)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
    glb,manifest=prepare(a.source);publish(a.output,glb,manifest);print(f'Prepared {a.output}/sky.glb ({len(glb)} bytes)')
if __name__=='__main__':main()
