#!/usr/bin/env python3
"""Prepare one source-qualified curb normal-only pilot; native pixel parity is unknown."""
import argparse
import copy
import hashlib
import io
import json
import math
from pathlib import Path
import struct
from PIL import Image
from install_cars import regular_bytes, immutable
from prepare_gt4_vehicle import unpack, pack

SOURCE_SHA='c5ef58e5327937ee564d5ebc653c766a9c8d79050bffae33b262d6dd430e31bb'
PROOF_SHA='31b774dfdfa484c323ff964af69812b5ae0c1ad0e5a14abd15aacf2eff4fcfd1'
PNG_SHA='0c9aa98f04e27f821595c7a6182b673e294ca2d5465b5649d01d8e31ab75d4b1'
RGBA_SHA='89d99d54abf63ca0313d4942a24a2411797a5278bc0be4ece2d486a51cd9120c'
ENCODED_SHA='c1178f413727d7f5eee3b9c107501bdfeabd3bbd58a0a5115633b353b89b0ab6'
EXTENSION='RACER_source_bump_spec'
GLB_LIMIT=8*1024**2
DIRECTORY_LIMIT=8*1024**2
PNG_LIMIT=128*1024
PROFILE={'vertices':762,'indices':1914,'stride':28,
 'normal_words_sha256':'81ea48a79bffc86a2bf768568fdf0b96d0e3cb755cbba016f3e75007f19fdd01',
 'tangent_words_sha256':'3eada651207801875f3da38c31b2c67e740c7ffaec95c2faeb99e34a4343f509',
 'negative_w':547,'positive_w':215}
POLICY=('Source-code/compiled selected-kernel-backed NORMAL ONLY: vertex stage computes '
 'B=cross(T,N)*Tw per vertex; pixel stage normalizes interpolatedN-(2A-1)*interpolatedB-'
 '(2R-1)*interpolatedT. Selected compiled path samples source UV0 unscaled; other permutations '
 'and live runtime UV transforms remain unknown. Original linear RGBA and tangent XYZ plus signed '
 'packed W preserved. G/B retained without specular/exponent/intensity/mixer adoption. Native live '
 'patched declaration, permutation, mipchain, filtering precision and pixel equivalence remain unknown. '
 'Zero mixed-W triangles qualifies this exact source only; the renderer supports mixed-W triangles '
 'through per-vertex B interpolation, not a universal same-W constraint.')


def require(ok,reason):
    if not ok: raise ValueError(reason)


def sha(data): return hashlib.sha256(data).hexdigest()
def encoded(value): return (json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()


def safe(path):
    p=Path(path).absolute()
    require(not any(x.is_symlink() for x in (p,*p.parents)),'symlink_refused')
    return p


def signed_w(word):
    require(type(word) is int and 0<=word<=0xffffffff,'packed_word')
    value=word>>30
    value=value-4 if value&2 else value
    require(value in (-1,1),'packed_w_not_signed_one')
    return value


def xyz(word):
    return tuple(((v-1024) if v&512 else v)/511 for v in ((word>>s)&1023 for s in (0,10,20)))


def tangent_rows(raw,normals,tangents,indices,profile):
    count=profile['vertices'];stride=profile['stride']
    require(stride==28 and len(raw)==count*stride and len(normals)==len(tangents)==count,'source_frame_size')
    require(len(indices)==profile['indices'] and len(indices)%3==0 and all(type(i)is int and 0<=i<count for i in indices),'source_indices')
    normal_words=b''.join(raw[i*stride+12:i*stride+16] for i in range(count))
    tangent_words=b''.join(raw[i*stride+24:i*stride+28] for i in range(count))
    require(sha(normal_words)==profile['normal_words_sha256'] and sha(tangent_words)==profile['tangent_words_sha256'],'source_packed_words_pin')
    rows=[];ratios=[];nlengths=[];tlengths=[]
    for i,(normal,tangent) in enumerate(zip(normals,tangents)):
        nw=struct.unpack_from('>I',normal_words,i*4)[0];tw=struct.unpack_from('>I',tangent_words,i*4)[0]
        require(len(normal)==len(tangent)==3 and all(math.isfinite(v) for v in (*normal,*tangent)),'source_frame_finite')
        require(struct.pack('<3f',*xyz(nw))==struct.pack('<3f',*normal) and struct.pack('<3f',*xyz(tw))==struct.pack('<3f',*tangent),'source_xyz_packing')
        nl,tl=math.hypot(*normal),math.hypot(*tangent)
        require(.98<=nl<=1.02 and .98<=tl<=1.02,'source_frame_length')
        ratio=abs(sum(a*b for a,b in zip(normal,tangent)))/(nl*tl)
        require(ratio<=.05,'source_frame_orthogonality')
        rows.append((*tangent,float(signed_w(tw))));ratios.append(ratio);nlengths.append(nl);tlengths.append(tl)
    require(sum(r[3]<0 for r in rows)==profile['negative_w'] and sum(r[3]>0 for r in rows)==profile['positive_w'],'source_w_counts')
    require(all(len({rows[j][3] for j in indices[i:i+3]})==1 for i in range(0,len(indices),3)),'mixed_triangle_handedness')
    return rows,{'normal_length':[min(nlengths),max(nlengths)],'tangent_length':[min(tlengths),max(tlengths)],'max_normal_tangent_dot_ratio':max(ratios),'negative_w':profile['negative_w'],'positive_w':profile['positive_w'],'mixed_triangle_handedness':0}


def view_bytes(doc,binary,index):
    require(type(index)is int and 0<=index<len(doc.get('bufferViews',[])),'source_view_index')
    v=doc['bufferViews'][index];start=v.get('byteOffset',0);size=v.get('byteLength')
    require(v.get('buffer')==0 and type(start)is int and type(size)is int and start>=0 and size>=0 and start+size<=len(binary) and 'byteStride'not in v,'source_view_bounds')
    return bytes(binary[start:start+size])


def values(doc,binary,index,kind,code,fmt,width):
    require(type(index)is int and 0<=index<len(doc.get('accessors',[])),'source_accessor_index')
    a=doc['accessors'][index]
    require(a.get('type')==kind and a.get('componentType')==code and 'sparse'not in a and not a.get('normalized',False) and a.get('byteOffset',0)==0,'source_accessor_layout')
    raw=view_bytes(doc,binary,a['bufferView']);require(type(a.get('count'))is int and a['count']>=0 and len(raw)==a['count']*width*struct.calcsize(fmt),'source_accessor_size')
    return list(struct.iter_unpack('<'+fmt*width,raw))


def png_identity(raw,expected_png=PNG_SHA,expected_rgba=RGBA_SHA,size=(128,128)):
    require(len(raw)<=PNG_LIMIT and sha(raw)==expected_png,'source_png_pin')
    with Image.open(io.BytesIO(raw)) as im:
        require(im.format=='PNG' and im.mode=='RGBA' and im.size==size and not getattr(im,'is_animated',False),'source_png_layout')
        rgba=im.tobytes()
    require(sha(rgba)==expected_rgba,'source_rgba_pin')
    return {'dimensions':list(size),'rgba_sha256':sha(rgba),'rgba_bytes':len(rgba),'png_sha256':sha(raw),'texture_role':'LINEAR_RGBA/PackedHeightSpec'}


def derive(doc,binary,png,profile=PROFILE):
    """Callers pin production input/proof before this bounded append transformation."""
    require(len(doc.get('buffers',[]))==1 and 'uri'not in doc['buffers'][0] and 0<=len(binary)-doc['buffers'][0].get('byteLength',-1)<=3,'embedded_buffer')
    nodes=[n for n in doc.get('nodes',[]) if n.get('name')=='native_model_156_geometry_0_restored']
    require(len(nodes)==1,'source_node_ambiguity');mi=nodes[0].get('mesh')
    require(type(mi)is int and 0<=mi<len(doc.get('meshes',[])),'source_mesh')
    mesh=doc['meshes'][mi];require(len(mesh.get('primitives',[]))==1,'source_primitive_ambiguity');pr=mesh['primitives'][0]
    require(pr.get('mode',4)==4 and type(pr.get('material'))is int and 0<=pr['material']<len(doc.get('materials',[])),'source_material')
    material=doc['materials'][pr['material']];samplers=material.get('extras',{}).get('samplers',[])
    require(material.get('extras',{}).get('name')=='CityBumpSpec' and {(s.get('hash'),s.get('texture_name')) for s in samplers}=={(0xf1fe2b71,'l_sha_curb_01.dds'),(0x332ebe1c,'l_sha_curb_01_bs.dds')} and len(samplers)==2,'source_material_binding')
    require('normalTexture'not in material and EXTENSION not in material.get('extensions',{}),'source_material_conflict')
    attrs=pr.get('attributes',{});require({'POSITION','NORMAL','TEXCOORD_0','_RACER_SOURCE_TANGENT'}<=set(attrs) and 'TANGENT'not in attrs,'source_attributes')
    source=mesh.get('extras',{}).get('source',{});require((source.get('entry'),source.get('model'),source.get('geometry'),source.get('source_shader'),source.get('stride'))==(2389,156,0,0,28),'source_geometry_binding')
    rawviews=mesh.get('extras',{}).get('raw_source_bufferViews',{});raw=view_bytes(doc,binary,rawviews.get('vertex'));declaration=view_bytes(doc,binary,rawviews.get('declaration'))
    require(declaration==bytes.fromhex('000040691c000005aa1111111199a996'),'source_declaration')
    normals=values(doc,binary,attrs['NORMAL'],'VEC3',5126,'f',3);tangents=values(doc,binary,attrs['_RACER_SOURCE_TANGENT'],'VEC3',5126,'f',3)
    indices=[r[0] for r in values(doc,binary,pr['indices'],'SCALAR',5123,'H',1)]
    require(view_bytes(doc,binary,rawviews.get('index'))==struct.pack('>'+'H'*len(indices),*indices),'source_raw_indices')
    require(len(values(doc,binary,attrs['POSITION'],'VEC3',5126,'f',3))==len(values(doc,binary,attrs['TEXCOORD_0'],'VEC2',5126,'f',2))==profile['vertices'],'source_attribute_count')
    rows,frame=tangent_rows(raw,normals,tangents,indices,profile)
    d=copy.deepcopy(doc);blob=bytearray(binary)
    def append(data):
        blob.extend(b'\0'*(-len(blob)%4));i=len(d['bufferViews']);d['bufferViews'].append({'buffer':0,'byteOffset':len(blob),'byteLength':len(data)});blob.extend(data);return i
    ai=len(d['accessors']);d['accessors'].append({'bufferView':append(b''.join(struct.pack('<4f',*r) for r in rows)),'componentType':5126,'count':len(rows),'type':'VEC4'})
    ii=len(d['images']);d['images'].append({'bufferView':append(png),'mimeType':'image/png','name':'l_sha_curb_01_bs.dds source packed RGBA'})
    si=len(d.setdefault('samplers',[]));d['samplers'].append({'magFilter':9729,'minFilter':9987,'wrapS':10497,'wrapT':10497})
    ti=len(d['textures']);d['textures'].append({'source':ii,'sampler':si})
    clone=copy.deepcopy(material);clone.setdefault('extensions',{})[EXTENSION]={'texture':ti};clone.setdefault('extras',{})['racerSourceBumpNormalOnly']={'policy':POLICY,'originalMaterial':pr['material'],'sourceTexture':'l_sha_curb_01_bs.dds','sourceRgbaSha256':RGBA_SHA,'frame':frame}
    material_index=len(d['materials']);d['materials'].append(clone);target=d['meshes'][mi]['primitives'][0];target['attributes']['TANGENT']=ai;target['material']=material_index
    require(EXTENSION not in d.get('extensionsRequired',[]),'extension_must_be_optional')
    used=d.setdefault('extensionsUsed',[])
    if EXTENSION not in used:used.append(EXTENSION)
    d['buffers'][0]['byteLength']=len(blob)
    return d,blob,{'mesh':mi,'primitive':0,'originalMaterial':pr['material'],'material':material_index,'tangentAccessor':ai,'texture':ti,'frame':frame}


def prefix_check(old,oldbin,new,newbin,join):
    require(bytes(newbin[:len(oldbin)])==bytes(oldbin),'binary_prefix_changed')
    for key in ('nodes','scenes','scene'):require(new.get(key)==old.get(key),'node_scene_prefix_changed')
    for key in ('materials','accessors','bufferViews','images','textures','samplers'):require(new.get(key,[])[:len(old.get(key,[]))]==old.get(key,[]),'document_prefix_changed')
    meshes=copy.deepcopy(new['meshes']);pr=meshes[join['mesh']]['primitives'][join['primitive']];pr['attributes'].pop('TANGENT');pr['material']=join['originalMaterial'];require(meshes==old['meshes'],'primitive_changes')
    for key,value in old.items():
        if key not in ('buffers','meshes','materials','accessors','bufferViews','images','textures','samplers','extensionsUsed'):require(new.get(key)==value,'document_field_changed')
    require(new['buffers'][0]|{'byteLength':old['buffers'][0]['byteLength']}==old['buffers'][0],'buffer_contract_changed')
    require(new.get('extensionsUsed',[])==old.get('extensionsUsed',[])+([] if EXTENSION in old.get('extensionsUsed',[]) else [EXTENSION]),'extension_usage_changed')


def build(source,png,proof):
    source,png,proof=map(safe,(source,png,proof));raw=regular_bytes(source,GLB_LIMIT);require(sha(raw)==SOURCE_SHA,'source_pin')
    pb=regular_bytes(proof,128*1024);require(sha(pb)==PROOF_SHA,'proof_pin');p=json.loads(pb)
    require(p['selected_model']==156 and p['selected_geometry']==0 and p['secondary']['encoded_sha256']==ENCODED_SHA and p['secondary']['rgba_sha256']==RGBA_SHA and not p['local_override'] and p['shared_match'],'source_profile')
    bs=regular_bytes(png,PNG_LIMIT);pixels=png_identity(bs);doc,binary=unpack(raw);new,blob,join=derive(doc,binary,bs);prefix_check(doc,binary,new,blob,join);glb=pack(new,blob);require(len(glb)<=GLB_LIMIT,'glb_budget')
    report={'source_sha256':SOURCE_SHA,'proof_sha256':PROOF_SHA,'source_profile':p,'texture':pixels,'binding':join,'output_sha256':sha(glb),'output_bytes':len(glb),'source_encoded_sha256':ENCODED_SHA,'policy':POLICY,'checks':'PASS originalBIN/documentprefixes andoriginalgeometry unchanged excepttargetTANGENT/material; signedW/rawXYZ/rawindices/frame qualified; exactsourceBS PNG/RGBA preserved. Nativepixels/consumerload nottestedhere.'}
    return {'curb-source-bump.glb':glb,'manifest.json':encoded(report)},report


def publish(output,files):
    output=safe(output);require(output.parent.is_dir(),'output_parent_missing')
    require(not output.exists()or output.is_dir(),'output_not_directory');existing=0
    if output.exists():
        for entry in output.iterdir():require(entry.is_file()and not entry.is_symlink(),'output_entry');existing+=entry.stat().st_size
    extra=0
    for name,data in files.items():
        require(Path(name).name==name and name not in ('','.','..'),'output_name');target=output/name
        if target.exists()or target.is_symlink():
            require(not target.is_symlink() and target.stat().st_size==len(data),'immutable_conflict')
            require(regular_bytes(target,len(data))==data,'immutable_conflict')
        else:extra+=len(data)
    require(existing+extra<=DIRECTORY_LIMIT,'directory_budget')
    output.mkdir(exist_ok=True)
    for name,data in files.items():immutable(output/name,data)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--png',type=Path,required=True);p.add_argument('--proof',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--export',action='store_true');a=p.parse_args();files,report=build(a.source,a.png,a.proof)
    if a.export:publish(a.output,files)
    print(json.dumps({'exported':a.export,'output_sha256':report['output_sha256'],'output_bytes':report['output_bytes'],'binding':report['binding'],'texture':report['texture']},sort_keys=True))


if __name__=='__main__':main()
