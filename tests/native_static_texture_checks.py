#!/usr/bin/env python3
"""Prepare/execute a hidden Metal cross-file static-texture sharing experiment.

Default only freezes inputs. --execute needs the shared GPU slot released.
Actual pixels and diagnostic counts establish this narrow integration contract;
manual inspection of clamp/repeat panels remains necessary before visual claims.
"""
import argparse
import base64
import hashlib
import io
import json
from pathlib import Path
import struct
import subprocess
from PIL import Image, ImageChops, PngImagePlugin
import native_reflection_checks as native

CAP=16*1024**2
BINARY_CAP=12*1024**2
SOURCE_RGBA=bytes([255,20,10,255,20,255,10,255,20,10,255,255,240,240,30,255])


def require(ok,reason):
    if not ok:raise ValueError(reason)


def encoded(value):return(json.dumps(value,sort_keys=True,indent=2)+'\n').encode()
def sha(data):return hashlib.sha256(data).hexdigest()


def quota(root,reserve=0):
    total=0
    for path in root.rglob('*'):
        require(not path.is_symlink(),'output symlink')
        if path.is_file():total+=path.stat().st_size
    require(total+reserve<=CAP,'16MiB output quota')
    return total


def png(compression,label):
    out=io.BytesIO();info=PngImagePlugin.PngInfo();info.add_text('fixture',label)
    Image.frombytes('RGBA',(2,2),SOURCE_RGBA).save(out,format='PNG',compress_level=compression,pnginfo=info)
    return out.getvalue()


def fixture(panels,image=None):
    blob=bytearray();views=[];accessors=[];primitives=[]
    def view(data):
        blob.extend(b'\0'*(-len(blob)%4));index=len(views);views.append({'buffer':0,'byteOffset':len(blob),'byteLength':len(data)});blob.extend(data);return index
    materials=[]
    for left,wrap in panels:
        x0,x1=(-3.,-.25)if left else(.25,3.)
        positions=[(x0,.3,0),(x0,3,0),(x1,3,0),(x0,.3,0),(x1,3,0),(x1,.3,0)]
        attrs={}
        for name,rows,kind in [('POSITION',positions,'VEC3'),('NORMAL',[(0,0,-1)]*6,'VEC3'),('TEXCOORD_0',[(0,0),(0,3),(3,3),(0,0),(3,3),(3,0)],'VEC2')]:
            raw=struct.pack('<'+'f'*sum(map(len,rows)),*[v for row in rows for v in row]);accessors.append({'bufferView':view(raw),'componentType':5126,'count':6,'type':kind})
            if name=='POSITION':accessors[-1].update(min=[min(p[k]for p in rows)for k in range(3)],max=[max(p[k]for p in rows)for k in range(3)])
            attrs[name]=len(accessors)-1
        mat={'alphaMode':'OPAQUE','pbrMetallicRoughness':{'baseColorFactor':[1,1,1,1],'metallicFactor':0,'roughnessFactor':1,'baseColorTexture':{'index':len(materials)}}}
        materials.append(mat);primitives.append({'attributes':attrs,'material':len(materials)-1})
    doc={'asset':{'version':'2.0'},'scene':0,'scenes':[{'nodes':[0]}],'nodes':[{'mesh':0}],'meshes':[{'primitives':primitives}],'materials':materials,'samplers':[{'wrapS':w,'wrapT':w}for _,w in panels],'textures':[{'source':0,'sampler':i}for i in range(len(panels))],'images':[{'bufferView':view(image),'mimeType':'image/png'}],'buffers':[{'byteLength':len(blob)}],'bufferViews':views,'accessors':accessors}
    text=json.dumps(doc,separators=(',',':')).encode();text+=b' '*(-len(text)%4);blob.extend(b'\0'*(-len(blob)%4));size=28+len(text)+len(blob)
    return struct.pack('<4sIII',b'glTF',2,size,len(text))+b'JSON'+text+struct.pack('<I',len(blob))+b'BIN\0'+blob


def prepare(binary,out):
    raw=native.regular(binary,BINARY_CAP);require(not out.exists(),'fresh output required');out.mkdir(parents=True)
    native.write_new(out/'racer',raw);(out/'racer').chmod(0o700)
    a,b=png(0,'single encoded source'),png(9,'different bytes same actual pixels')
    require(a!=b and Image.open(io.BytesIO(a)).convert('RGBA').tobytes()==Image.open(io.BytesIO(b)).convert('RGBA').tobytes()==SOURCE_RGBA,'fixture pixel identity')
    files={'combined.glb':fixture([(True,33071),(False,10497)],a),'clamp.glb':fixture([(True,33071)],a),'repeat.glb':fixture([(False,10497)],b)}
    # Zero-opacity MASK preview must neither draw a vehicle nor cast its shadow.
    positions=[-.01,.3,0,.01,.3,0,0,.32,0];data=struct.pack('<9f',*positions)
    invisible={'asset':{'version':'2.0'},'scene':0,'scenes':[{'nodes':[0]}],'nodes':[{'mesh':0}],'meshes':[{'primitives':[{'attributes':{'POSITION':0},'material':0}]}],'materials':[{'alphaMode':'MASK','alphaCutoff':.5,'pbrMetallicRoughness':{'baseColorFactor':[1,1,1,0],'metallicFactor':0,'roughnessFactor':1}}],'buffers':[{'byteLength':len(data),'uri':'data:application/octet-stream;base64,'+base64.b64encode(data).decode()}],'bufferViews':[{'buffer':0,'byteLength':len(data)}],'accessors':[{'bufferView':0,'componentType':5126,'count':3,'type':'VEC3','min':[-.01,.3,0],'max':[.01,.32,0]}]}
    files['invisible.gltf']=encoded(invisible)
    for name,data in files.items():native.write_new(out/name,data)
    runs=[]
    for name,worlds in [('combined',['combined.glb']),('split',['clamp.glb','repeat.glb'])]:
        argv=[str(out/'racer'),'--background','--smoke','4','--window','640','360','--hide-hud','--preview-gltf',str(out/'invisible.gltf'),'--sky-mesh','','--camera-view','rear','--camera-distance','10','--screenshot',str(out/(name+'.ppm')),'--profile',str(out/(name+'.profile')),'--diagnostics-dir',str(out/(name+'-diagnostics'))]
        for world in worlds:argv.extend(['--world-mesh',str(out/world)])
        runs.append({'name':name,'argv':argv,'expected_world_events':len(worlds)})
    plan={'binary_sha256':sha(raw),'binary_bytes':len(raw),'inputs':{name:sha(data)for name,data in files.items()},'helper_source':str(Path(native.__file__).absolute()),'helper_sha256':sha(native.regular(Path(native.__file__).absolute(),128*1024)),'runs':runs,'working_directory':str(Path.cwd()),'rgba_sha256':sha(SOURCE_RGBA),'rgba_bytes':16,'dimensions':[2,2],'distinct_encoded_png_sha256':[sha(a),sha(b)],'contract':'Actual fullgame RGB images differ<=1byte/channel; every world eventstatic_unique_images1/static_unique_rgba_bytes16; combinedoneworld versus splittwoworlds. Independently inspect leftclamp/rightrepeat appearance. No AAAquality claim.'}
    data=encoded(plan);native.write_new(out/'prepared.json',data);native.write_new(out/'prepared.sha256',(sha(data)+'\n').encode());quota(out);return plan


def diagnostics(root,expected):
    files=list(root.glob('*.jsonl'));require(len(files)==1,'one isolated diagnostics journal required')
    records=[json.loads(line)for line in native.regular(files[0],4*1024**2).decode().splitlines()]
    events=[r for r in records if r.get('event')=='world_mesh']
    require(len(events)==expected,'expected actual world-load diagnostics')
    # Fields schema is read from actual runtime records, never mocked flags.
    return records,events


def execute(out):
    data=native.regular(out/'prepared.json',128*1024);require(sha(data)==native.regular(out/'prepared.sha256',65).decode().strip(),'plan drift');plan=json.loads(data)
    require(sha(native.regular(out/'racer',BINARY_CAP))==plan['binary_sha256'],'binary drift')
    require(sha(native.regular(Path(plan['helper_source']),128*1024))==plan['helper_sha256'],'helper drift')
    for name,digest in plan['inputs'].items():require(Path(name).name==name and sha(native.regular(out/name,128*1024))==digest,'fixture drift')
    require(all(r['argv'][0]==str(out/'racer')for r in plan['runs']),'prepared directory moved')
    require(subprocess.run(['/usr/bin/pgrep','-x','racer'],capture_output=True,timeout=3).returncode==1,'shared GPU Racer active or inventoryfailed')
    require(not(out/'result.json').exists(),'retained result exists')
    results=[];images=[]
    for row in plan['runs']:
        name=row['name'];require(not any((out/(name+s)).exists()for s in('.log','.ppm','.png','.profile','-run.json','-diagnostics')),'retained partial run; fresh output required');quota(out,6*1024**2)
        status=native.run_child(row['argv'],plan['working_directory'],out/(name+'.log'));result={'name':name,'argv':row['argv'],**status};native.write_new(out/(name+'-run.json'),encoded(result));require(status['exit']==0 and status['reason']=='exited' and status.get('log_reader_complete',False),'native failure retained')
        raw=native.regular(out/(name+'.ppm'),1024**2)
        with Image.open(io.BytesIO(raw))as im:require(im.size==(640,360),'capture dimensions');image=im.convert('RGB').copy();stream=io.BytesIO();image.save(stream,format='PNG')
        native.write_new(out/(name+'.png'),stream.getvalue());result['ppm_sha256']=sha(raw);result['png_sha256']=sha(stream.getvalue());images.append(image)
        records,events=diagnostics(out/(name+'-diagnostics'),row['expected_world_events']);result['world_events']=events;results.append(result);quota(out)
    counts=[(e.get('static_unique_images'),e.get('static_unique_rgba_bytes'))for r in results for e in r['world_events']]
    difference=ImageChops.difference(*images);maxdiff=max(max(pair)for pair in difference.getextrema());pixels=difference.tobytes();changed=sum(max(pixels[i:i+3])>1 for i in range(0,len(pixels),3))
    report={'binary_sha256':plan['binary_sha256'],'runs':results,'static_count_and_bytes':counts,'max_channel_difference':maxdiff,'pixels_over1byte':changed,'scoped_pass':maxdiff<=1 and all(pair==(1,16)for pair in counts),'visual_review':'Manual clamp/repeat appearance and nonblankpanels still must be inspected. Passingthisnarrowintegrationcheck doesnot establishgamevisualquality.'}
    native.write_new(out/'result.json',encoded(report));quota(out);require(report['scoped_pass'],'actual pixel/count equivalence failed; inspect retained result')
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--binary',type=Path);p.add_argument('--execute',action='store_true');a=p.parse_args();require((a.binary is not None)!=a.execute,'preparewith--binary OR --execute')
    out=a.output.absolute();require(not any(p.is_symlink()for p in(out,*out.parents)),'output symlink; use real absolute path')
    print(json.dumps(execute(out)if a.execute else prepare(a.binary,out),indent=2))


if __name__=='__main__':main()
