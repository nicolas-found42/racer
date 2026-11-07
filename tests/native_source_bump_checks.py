#!/usr/bin/env python3
"""Hidden native material controls: R/A effect, G/B invariance and linear mips.

Ten three-second640x360 runs,20s per child,16MiB retained output. Swatch
geometry/UV scales are authored test fixtures, not native world placement.
Actual source BS/diffuse pixels are pinned. This does not grade game fidelity.
"""
import argparse
import base64
import hashlib
import io
import json
from pathlib import Path
import struct
import subprocess
from PIL import Image, ImageChops, ImageDraw, ImageStat
from native_hdr_checks import local_path, regular

ROOT=Path(__file__).resolve().parents[1]
CAP=16*1024**2
CURB_SHA='c5ef58e5327937ee564d5ebc653c766a9c8d79050bffae33b262d6dd430e31bb'
BS_RGBA='89d99d54abf63ca0313d4942a24a2411797a5278bc0be4ece2d486a51cd9120c'
DIFFUSE_PNG='1803cf79123a7260b59f9f096d9546cac207203535cd5c31c35f49ca3a1aca8b'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def png(image):
    out=io.BytesIO()
    image.save(out,format='PNG')
    return out.getvalue()


def fixture(diffuse,detail,enabled,scale=1):
    blob=bytearray()
    views=[]
    accessors=[]
    primitives=[]
    def accessor(rows,width,kind):
        payload=b''.join(struct.pack('<'+'f'*width,*row)for row in rows)
        index=len(accessors)
        views.append({'buffer':0,'byteOffset':len(blob),'byteLength':len(payload)})
        blob.extend(payload)
        accessors.append({'bufferView':len(views)-1,'componentType':5126,'type':kind,'count':len(rows)})
        return index
    for panel in range(3):
        left=-2.2+panel*1.55
        points=[(left,0,0),(left+1.3,0,0),(left+1.3,2,0),(left,0,0),(left+1.3,2,0),(left,2,0)]
        uvscale=scale*(16 if panel==1 else 1)
        uvs=[(0,0),(uvscale,0),(uvscale,uvscale),(0,0),(uvscale,uvscale),(0,uvscale)]
        attrs={'POSITION':accessor(points,3,'VEC3'),
               'NORMAL':accessor([(0,0,1)]*6,3,'VEC3'),
               'TEXCOORD_0':accessor(uvs,2,'VEC2'),
               'TANGENT':accessor([(1,0,0,-1 if panel==2 else 1)]*6,4,'VEC4')}
        primitives.append({'attributes':attrs,'material':0})
    material={'doubleSided':True,'pbrMetallicRoughness':{'baseColorTexture':{'index':0},'baseColorFactor':[1,1,1,1],
                                                       'metallicFactor':0,'roughnessFactor':1}}
    if enabled:
        material['extensions']={'RACER_source_bump_spec':{'texture':1}}
    doc={'asset':{'version':'2.0'},'scene':0,'scenes':[{'nodes':[0]}],
            'nodes':[{'mesh':0}],'meshes':[{'primitives':primitives}],
            'materials':[material],
            'images':[{'uri':'data:image/png;base64,'+base64.b64encode(data).decode()}for data in (diffuse,detail)],
            'samplers':[{'wrapS':10497,'wrapT':10497,'minFilter':9987,'magFilter':9729}],
            'textures':[{'source':0,'sampler':0},{'source':1,'sampler':0}],
            'buffers':[{'byteLength':len(blob),'uri':'data:application/octet-stream;base64,'+base64.b64encode(blob).decode()}],
            'bufferViews':views,'accessors':accessors,
            'extras':{'authority':'Authored material swatch geometry/UV scale; source pixels, not native world geometry.'}}
    if enabled:
        doc['extensionsUsed']=['RACER_source_bump_spec']
    return doc


def delta(a,b):
    image=ImageChops.difference(a,b)
    extrema=image.getextrema()
    return {'max_channel':max(high for low,high in extrema),
            'pixels_over3':sum(max(pixel)>3 for pixel in image.get_flattened_data())}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary',type=Path,required=True)
    parser.add_argument('--curb',type=Path,required=True)
    parser.add_argument('--bs',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    binary,mode=regular(local_path(args.binary),6*1024**2)
    curb,_=regular(local_path(args.curb),8*1024**2)
    bs,_=regular(local_path(args.bs),128*1024)
    if sha(curb)!=CURB_SHA:
        raise ValueError('curb_input_pin')
    json_size=struct.unpack_from('<I',curb,12)[0]
    doc=json.loads(curb[20:20+json_size])
    offset=20+json_size
    bin_size=struct.unpack_from('<I',curb,offset)[0]
    data=curb[offset+8:offset+8+bin_size]
    diffuse=None
    for image in doc['images']:
        view=doc['bufferViews'][image['bufferView']]
        candidate=data[view.get('byteOffset',0):view.get('byteOffset',0)+view['byteLength']]
        if sha(candidate)==DIFFUSE_PNG:
            diffuse=candidate
            break
    if diffuse is None:
        raise ValueError('source_diffuse_pin')
    with Image.open(io.BytesIO(bs))as image:
        image.load()
        if image.mode!='RGBA'or image.size!=(128,128)or sha(image.tobytes())!=BS_RGBA:
            raise ValueError('source_bs_pixels')
        source=image.copy()
    channels=source.split()
    altered=Image.merge('RGBA',(channels[0],channels[1].point(lambda v:255-v),channels[2].point(lambda v:255-v),channels[3]))
    zero=Image.new('L',source.size,128)
    r_neutral=Image.merge('RGBA',(zero,channels[1],channels[2],channels[3]))
    a_neutral=Image.merge('RGBA',(channels[0],channels[1],channels[2],zero))
    ra_neutral=Image.merge('RGBA',(zero,channels[1],channels[2],zero))
    r_low=Image.merge('RGBA',(Image.new('L',source.size,0),*channels[1:]))
    r_high=Image.merge('RGBA',(Image.new('L',source.size,255),*channels[1:]))
    checker=Image.new('RGBA',(128,128))
    checker.putdata([(255 if (x+y)%2 else 0,132,123,128)for y in range(128)for x in range(128)])
    neutral=Image.new('RGBA',(128,128),(128,132,123,128))
    variants=[('flat',bs,False,1),('source',bs,True,1),('gb-control',png(altered),True,1),
              ('r-neutral',png(r_neutral),True,1),('a-neutral',png(a_neutral),True,1),('ra-neutral',png(ra_neutral),True,1),
              ('r-low',png(r_low),True,1),('r-high',png(r_high),True,1),
              ('mip-checker',png(checker),True,64),('mip-neutral',png(neutral),True,64)]
    out=local_path(args.output)
    if any(p.is_symlink()for p in (out,*out.parents)):
        raise ValueError('output_symlink')
    if len(binary)+9*1024**2>CAP:
        raise ValueError('output_preflight')
    out.mkdir(parents=True,exist_ok=False)
    exe=out/'racer'
    exe.write_bytes(binary)
    exe.chmod(mode)
    source_paths=['src/main.cpp','src/mesh_asset.cpp','src/mesh_asset.h','src/source_bump.h',
                  'src/visual_shader.h','src/texture_upload.h','src/static_texture_pool.h',
                  'tests/native_source_bump_checks.py']
    sources={name:(ROOT/name).read_bytes()for name in source_paths}
    (out/'source-bs.png').write_bytes(bs)
    (out/'source-diffuse.png').write_bytes(diffuse)
    invisible=fixture(diffuse,bs,False)
    invisible['materials'][0]['alphaMode']='MASK'
    invisible['materials'][0]['pbrMetallicRoughness']['baseColorFactor']=[1,1,1,0]
    (out/'invisible.gltf').write_text(json.dumps(invisible))
    manifest={'authority':'Actual hidden Racer material swatches; authored geometry, pinned source images. Not original runtime or game visual equivalence.',
              'binary_sha256':sha(binary),'source_bs_rgba_sha256':BS_RGBA,'source_diffuse_png_sha256':DIFFUSE_PNG,
              'source_sha256':{name:sha(data)for name,data in sources.items()},'cap_bytes':CAP,'runs':[]}
    images={}
    for label,texture,enabled,scale in variants:
        path=out/(label+'.gltf')
        path.write_text(json.dumps(fixture(diffuse,texture,enabled,scale)))
        argv=[str(exe),'--background','--hide-hud','--smoke','3','--window','640','360',
              '--scene','scale','--preview-gltf',str(out/'invisible.gltf'),'--world-mesh',str(path),
              '--sky-mesh','','--world-surfaces','','--camera-view','front','--camera-distance','4',
              '--screenshot',str(out/(label+'.ppm')),'--profile',str(out/(label+'.profile')),'--no-diagnostics']
        row={'label':label,'argv':argv,'fixture_sha256':sha(path.read_bytes())}
        manifest['runs'].append(row)
        try:
            result=subprocess.run(argv,capture_output=True,text=True,timeout=20)
            row['exit']=result.returncode
            (out/(label+'.log')).write_text((result.stdout+result.stderr)[:131072])
            if result.returncode:
                raise RuntimeError('native_source_bump_exit')
            with Image.open(out/(label+'.ppm'))as frame:
                frame.load()
                if frame.size!=(640,360):
                    raise RuntimeError('capture_dimensions')
                image=frame.convert('RGB')
            stats=ImageStat.Stat(image.crop((60,50,580,300)))
            if max(stats.mean)<12 or max(stats.stddev)<5:
                raise RuntimeError('black_or_uniform_capture')
            images[label]=image
            image.save(out/(label+'.png'))
            row['ppm_sha256']=sha((out/(label+'.ppm')).read_bytes())
        finally:
            (out/'manifest.json').write_text(json.dumps(manifest,indent=2))
        if sum(p.stat().st_size for p in out.rglob('*')if p.is_file())>CAP:
            raise RuntimeError('output_quota')
    checks={'source_effect':delta(images['flat'],images['source']),
            'sampled_r_effect':delta(images['source'],images['r-neutral']),
            'sampled_a_effect':delta(images['source'],images['a-neutral']),
            'sampled_ra_effect':delta(images['source'],images['ra-neutral']),
            'authored_r_sensitivity':delta(images['r-low'],images['r-high']),
            'green_blue_invariance':delta(images['source'],images['gb-control']),
            'linear_mip_neutrality':delta(images['mip-checker'],images['mip-neutral'])}
    manifest['checks']=checks
    manifest['source_unchanged_after']=all((ROOT/name).read_bytes()==data for name,data in sources.items())
    sheet=Image.new('RGB',(1920,((len(variants)+2)//3)*384),(15,20,25))
    draw=ImageDraw.Draw(sheet)
    for i,(label,_,_,_)in enumerate(variants):
        x=(i%3)*640;y=(i//3)*384
        sheet.paste(images[label],(x,y+24))
        draw.text((x+8,y+6),label+' | authored swatch, source R/A control',fill='white')
    sheet.save(out/'comparison.png')
    manifest['actual_bytes']=sum(p.stat().st_size for p in out.rglob('*')if p.is_file())
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2))
    assert manifest['source_unchanged_after']and manifest['actual_bytes']<CAP,'identity_or_quota'
    assert checks['source_effect']['pixels_over3']>500,'packed_source_has_no_visible_effect'
    # This source map has sparse R variation: the retained v2 run changes only
    # 15 pixels above three bytes. Require a deterministic source effect and a
    # separate strong one-channel control instead of a source-area assumption.
    assert checks['sampled_r_effect']['pixels_over3']>0,'sampled_r_has_no_visible_effect'
    assert checks['authored_r_sensitivity']['pixels_over3']>1000,'authored_r_control_has_no_visible_effect'
    assert checks['sampled_a_effect']['pixels_over3']>100,'sampled_a_has_no_visible_effect'
    assert checks['sampled_ra_effect']['pixels_over3']>500,'sampled_ra_has_no_visible_effect'
    assert checks['green_blue_invariance']['max_channel']<=1,'green_or_blue_leaks_into_normal'
    assert checks['linear_mip_neutrality']['max_channel']<=1,'packed_mips_are_not_linear_rgba'
    print(json.dumps({'PASS':checks,'visual_acceptance':'unresolved; inspect actual frames and full-game reference comparison'}))


if __name__=='__main__':
    main()
