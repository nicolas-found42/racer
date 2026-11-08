#!/usr/bin/env python3
"""Prepare isolated AUTHORED city R/A normal detail; native packing is unknown."""
import argparse
import copy
import hashlib
import io
import json
import math
from pathlib import Path
from PIL import Image
from install_cars import regular_bytes, immutable
from prepare_gt4_vehicle import unpack, pack, Geometry

SOURCE_SHA = '7f08d102378083757722ddf35e2815ae55fd9242535de0ab21258002abe9fccc'
SOURCE_SHAS = frozenset((SOURCE_SHA,
    # Same pinned A/B props plus qualified, stair-equipped C/D; authored layout.
    '797f6b90eeaae72de153035203b14cda7af0568f8f7122b5d8b3ae9cacda8fd3'))
GLB_LIMIT = 12*1024**2
DIRECTORY_LIMIT = 16*1024**2
PNG_LIMIT = 256*1024
SAMPLER_HASH = 0x332ebe1c
POLICY = ('AUTHORED X=R/127.5-1,Y=A/127.5-1,Z=positive sqrt(1-X*X-Y*Y); '
          'normalTexture UV0 scale .6. Native packing, signs, channel swizzles and BRDF unknown. '
          'G/B source channels retained unchanged; no base-color, alpha or geometry change.')
# Pinned decoder PNG bytes and RGBA pixels from independently retained source-proof.json.
MAPS = {
 'l_sha_wall_stucco_white_bs.dds': (64,64,'e06d00ba953e19c913d24a56607eb21f2a059b356baa30cfd9d3c5c224b221c8','741ee60713c24294d9f9f9898c9f935d8b9c96368bc4c40dab9029bf575d9272'),
 'l_be_sc_garagedoor_09_bs.dds': (128,128,'46e796514fb2cf682edc9dcda23f30e232fcbc39aa237c00458346262c1b7f5d','a19a62880d1ee0a8fa0098055b66d809291f5b33584ef506767d6f2f9469e584'),
 'l_ho_ss_wall_rock_01_bs.dds': (64,64,'10874ce64e47c82c60e4c9b07feba6f51ff04afdf7fbb1a639879d265b628b41','ce85f26fb1606d73a04b9eb66945827a113f76d60152ff9a9c963a5b54958354')}


def require(ok, reason):
    if not ok: raise ValueError(reason)


def sha(data): return hashlib.sha256(data).hexdigest()


def normal_png(data, size, pixel_sha):
    require(len(data)<=PNG_LIMIT and data.startswith(b'\x89PNG\r\n\x1a\n'), 'png_size_or_format')
    with Image.open(io.BytesIO(data)) as image:
        require(image.format=='PNG' and image.size==size and image.mode=='RGBA' and not getattr(image,'is_animated',False), 'png_pixels')
        rgba=image.tobytes()
    require(sha(rgba)==pixel_sha, 'rgba_pin')
    out=bytearray()
    for r,g,b,a in zip(rgba[::4],rgba[1::4],rgba[2::4],rgba[3::4]):
        x,y=r/127.5-1,a/127.5-1
        require(x*x+y*y<=1, 'invalid_xy')
        z=math.sqrt(1-x*x-y*y)
        out.extend(round((v*.5+.5)*255) for v in (x,y,z))
    require(len(set(bytes(out)[i:i+3] for i in range(0,len(out),3)))>1, 'constant_detail')
    output=io.BytesIO();Image.frombytes('RGB',size,bytes(out)).save(output,format='PNG')
    return output.getvalue()


def derive(doc, binary, normals):
    """Append-only document transformation; callers pin the full source before use."""
    d=copy.deepcopy(doc);blob=bytearray(binary);geometry=Geometry(doc,binary)
    require(len(d.get('buffers',[]))==1 and 'uri' not in d['buffers'][0] and 0<=len(blob)-d['buffers'][0]['byteLength']<=3, 'embedded_buffer')
    material_map={};joins=[];used=set();normal_indices={}
    for mi,m in enumerate(doc.get('materials',[])):
        matches=[s for s in m.get('extras',{}).get('samplers',[]) if s.get('hash')==SAMPLER_HASH]
        require(len(matches)<=1, 'ambiguous_sampler')
        if not matches or matches[0].get('texture_name') not in MAPS: continue
        require(m.get('extras',{}).get('name') in ('CityGrime','CityBumpSpec') and 'normalTexture' not in m, 'material_contract')
        name=matches[0]['texture_name'];require(name in normals,'missing_normal')
        if name not in used:
            raw=normals[name];blob.extend(b'\0'*(-len(blob)%4));start=len(blob);blob.extend(raw)
            vi=len(d['bufferViews']);d['bufferViews'].append({'buffer':0,'byteOffset':start,'byteLength':len(raw)})
            ii=len(d['images']);d['images'].append({'bufferView':vi,'mimeType':'image/png','name':'AUTHORED '+name+' R-A normal'})
            if not used:
                sampler=len(d.setdefault('samplers',[]));d['samplers'].append({'magFilter':9729,'minFilter':9729,'wrapS':10497,'wrapT':10497})
            ti=len(d['textures']);d['textures'].append({'source':ii,'sampler':sampler})
            used.add(name);normal_indices[name]=ti
        clone=copy.deepcopy(m);clone['normalTexture']={'index':normal_indices[name],'texCoord':0,'scale':.6}
        clone.setdefault('extras',{})['racerAuthoredDetail']={'policy':POLICY,'originalMaterial':mi,'sourceTexture':name,'samplerHash':SAMPLER_HASH,'sourceRgbaSha256':MAPS[name][3],'annotation':{'UvSetName':'map1','UvSetIndex':0}}
        material_map[mi]=len(d['materials']);d['materials'].append(clone)
    for mesh_index,mesh in enumerate(d['meshes']):
        for primitive_index,pr in enumerate(mesh['primitives']):
            original=pr.get('material')
            if original not in material_map: continue
            attrs=pr.get('attributes',{});require('NORMAL'in attrs and 'TEXCOORD_0'in attrs,'normal_uv0_required')
            uv=geometry.values(attrs['TEXCOORD_0'],'VEC2',(5126,));pos=geometry.values(attrs['POSITION'],'VEC3',(5126,));n=geometry.values(attrs['NORMAL'],'VEC3',(5126,))
            require(len(uv)==len(pos)==len(n) and all(abs(math.hypot(*v)-1)<.01 for v in n),'attribute_contract')
            pr['material']=material_map[original];joins.append({'mesh':mesh_index,'primitive':primitive_index,'originalMaterial':original,'material':pr['material']})
    require(used==set(MAPS) and joins, 'qualified_coverage')
    d['buffers'][0]['byteLength']=len(blob)
    return d,blob,joins

def safe_path(path):
    p=Path(path).absolute()
    require(not any(x.is_symlink() for x in (p,*p.parents)), 'symlink_refused')
    return p


def prepare(source, maps, output):
    source,maps,output=map(safe_path,(source,maps,output))
    raw=regular_bytes(source,GLB_LIMIT);source_sha=sha(raw);require(source_sha in SOURCE_SHAS,'source_pin')
    doc,binary=unpack(raw);files={};normals={};pins={}
    for name,(w,h,file_sha,pixel_sha) in MAPS.items():
        filename=name[:-4]+'.png';original=regular_bytes(maps/filename,PNG_LIMIT)
        require(sha(original)==file_sha,'png_pin')
        normal=normal_png(original,(w,h),pixel_sha);normals[name]=normal
        files['source-'+filename]=original;files['normal-'+filename]=normal
        pins[name]={'originalPngSha256':file_sha,'originalRgbaSha256':pixel_sha,'normalPngSha256':sha(normal),'size':[w,h]}
    d,blob,joins=derive(doc,binary,normals);result=pack(d,blob)
    require(len(result)<=GLB_LIMIT,'glb_budget')
    manifest={'policy':POLICY,'sourceSha256':source_sha,'sourceBytes':len(raw),'originalBinSha256':sha(binary),'originalBinBytes':len(binary),'outputSha256':sha(result),'outputBytes':len(result),'maps':pins,'bindings':joins,'excluded':{'l_ho_ss_door_10_11_bs.dds':'3 invalid XY pixels','l_sha_flat_bs.dds':'constant; no useful detail'},'nativeUnknowns':['channel packing and sign','fetch component swizzle','lighting/BRDF','runtime shader instruction formula'],'visualAcceptance':'Not established: requires actual running Racer screenshots after normalTexture consumer integration.'}
    files['city.glb']=result;files['manifest.json']=(json.dumps(manifest,indent=2,sort_keys=True)+'\n').encode()
    publish(output,files)
    return manifest


def publish(output, files):
    output=safe_path(output)
    require(all(Path(n).name==n for n in files),'output_filename')
    require(sum(map(len,files.values()))<=DIRECTORY_LIMIT,'directory_budget')
    existing={}
    if output.exists():
        require(output.is_dir(),'output_directory')
        retained=0
        for p in output.iterdir():
            require(p.is_file() and not p.is_symlink(),'output_entry')
            require(p.stat().st_size<=DIRECTORY_LIMIT-retained,'directory_budget')
            existing[p.name]=regular_bytes(p,DIRECTORY_LIMIT-retained);retained+=len(existing[p.name])
        require(sum(len(v) for k,v in existing.items() if k not in files)+sum(map(len,files.values()))<=DIRECTORY_LIMIT,'directory_budget')
        # Check ALL conflicts before publishing any output.
        require(all(n not in existing or existing[n]==v for n,v in files.items()),'immutable_conflict')
    output.mkdir(parents=True,exist_ok=True);safe_path(output)
    for n,v in files.items(): immutable(output/n,v)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--maps',type=Path,required=True,help='Pinned original RGBA PNG directory')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(prepare(args.source,args.maps,args.output),indent=2))


if __name__=='__main__':main()
