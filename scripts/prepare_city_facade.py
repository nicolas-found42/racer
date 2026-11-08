#!/usr/bin/env python3
"""Restore exact omitted native2300 model128 with an explicitly authored brick base.

Native CityGrimeTintDecal compositing/alpha remain unknown. Source geometry,
raw source buffers and native bindings are retained; adjacent brick01 is an
artist substitution, never relabeled as model128's original diffuse sampler.
"""
import argparse
import copy
import hashlib
import io
import json
import math
import os
from pathlib import Path
import stat
import struct
from PIL import Image
from install_cars import regular_bytes, immutable
from prepare_gt4_vehicle import unpack, pack
import inspect_world_resources as world

V4_SHA='563b849809f605d9a469e26bb85d8f1bbc42ace6d4eda7a79ac7b04568d92984'
WORLD_HELPER_SHA='28d0a7fff462cb48d2ea1b50afe2b42fa4d56f8f8eec6170c742fcf32cbea5d3'
ISO_SIZE=7838695424
OFFSET=2259124224
STORED=2021343
STORED_SHA='ab9f8b36c957ecb9183eefd44cbd2c4bbea4ae4dca3011963cb51ca4ee2548a6'
DECODED=4980736
DECODED_SHA='16630c6a17f808db0f2de1e39cbf888134a999b7f8e44fee06a059554ef78044'
VB_SHA='8e1e3096fc2a99b6132310c6d60ca84d56f915ec72d74356e009d3f55bbeec67'
IB_SHA='cc898211dd784f2ef3542345b368f0d36ba8d45eea2cc80cd862926313116aba'
BRICK_PNG_SHA='8f71950b448ff248b5d0840838884cb3c0f6ab2a6d957c6c5c02dbb9896bd752'
BRICK_RGBA_SHA='ef59b8eb9e9f18301807862d8fe7c0468655131561ae906fc18e69111a2a849f'
GLB_LIMIT=12*1024**2
OUTPUT_LIMIT=16*1024**2
POLICY=('AUTHORED restoration of omitted structural model128: adjacent native model12 '
        'material35 brick01 base image on unchanged source UV0. Native128 has '
        'DiffuseColor plus Decal/Grime/HeightSpecular bindings, no DiffuseSampler. '
        'Brick01 is a substitution; no native blend, alpha, UV scale, tangent '
        'handedness, nightfill or BRDF reconstruction claim. OPAQUE preview only.')


def require(ok,reason):
    if not ok:raise ValueError(reason)


def sha(data):return hashlib.sha256(data).hexdigest()
def encoded(value):return(json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()


def safe(path):
    p=Path(path).absolute();require(not any(x.is_symlink()for x in(p,*p.parents)),'symlink_refused');return p


def source_range(path):
    path=safe(path);fd=os.open(path,os.O_RDONLY|os.O_NONBLOCK|os.O_NOFOLLOW)
    with os.fdopen(fd,'rb')as stream:
        before=os.fstat(stream.fileno());require(stat.S_ISREG(before.st_mode)and before.st_size==ISO_SIZE,'source_iso_size')
        stream.seek(OFFSET);data=stream.read(STORED);after=os.fstat(stream.fileno())
    require(len(data)==STORED and(before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns)and sha(data)==STORED_SHA,'source_range_pin_or_change')
    return data


def native_geometry(iso,references,texture_helper):
    require(sha(regular_bytes(Path(world.__file__).absolute(),128*1024))==WORLD_HELPER_SHA,'world_helper_pin')
    references,texture_helper=safe(references),safe(texture_helper)
    modules=world.helpers(references,texture_helper);raw=source_range(iso)
    header=modules['mcla_lzx'].parse_header(raw);require(header['virtual']+header['physical']==DECODED,'decoded_budget')
    data,header=modules['mcla_lzx'].decompress(raw,expected=DECODED);require(sha(data)==DECODED_SHA,'decoded_pin')
    r,sector=world.decode_sector(data,header,modules)
    matches=[g for g in sector['geometries']if g['model']==128 and g['geometry']==0]
    require(len(matches)==1,'native_geometry_ambiguity');g=matches[0]
    require((g['vertex_count'],g['index_count'],g['stride'],g['shader'])==(1221,2577,40,12),'native_geometry_identity')
    shader=sector['shaders'][12];require(shader['name']=='CityGrimeTintDecal'and shader['draw_bucket']==0,'native_shader_identity')
    expected={(0xa79aeec0,'l_sha_decal_posters_01.dds'),(0xe3381c99,'l_sha_grime_dirt_01.dds'),(0x332ebe1c,'l_ho_ss_wall_brick_red_03_bs.dds')}
    require({(s['hash'],s['texture_name'])for s in shader['samplers']}==expected,'native_sampler_identity')
    piece=r.pointer(16,16);lod=r.pointer(piece+12,32);model=r.offset(world.array(r,lod+24,1024)[128],28);geo=r.offset(world.array(r,model+4,512)[0],80);vb=r.pointer(geo+12,32);ib=r.pointer(geo+28,16)
    vertex_at=r.offset(r.u32(vb+24),1221*40);index_at=r.offset(r.u32(ib+8),2577*2)
    raw_vb=data[vertex_at:vertex_at+1221*40];raw_ib=data[index_at:index_at+2577*2]
    require(sha(raw_vb)==VB_SHA and sha(raw_ib)==IB_SHA,'native_raw_buffers_pin')
    proof={'entry':2300,'expected_iso_sha256':world.ISO_SHA,'verification_scope':'Current call verifies regular ISO size and unchanged metadata, exact selected stored-range SHA256, decoded-range SHA256 and native raw buffers. Full ISO digest is prior canonical identity, not recomputed here.','prior_canonical_receipt':{'path':'games/INPUTS.json','verification_date':'2026-11-05','verification_reference':'games/racer/experiments/2026-11-05-donor-inventory/README.md'},'absolute_offset':OFFSET,'stored_bytes':STORED,'stored_sha256':STORED_SHA,'decoded_bytes':DECODED,'decoded_sha256':DECODED_SHA,'model':128,'geometry':0,'shader':12,'native_shader':shader,'model_offset':model,'geometry_offset':geo,'vertex_array_offset':vertex_at,'vertex_array_bytes':len(raw_vb),'vertex_array_sha256':VB_SHA,'index_array_offset':index_at,'index_array_bytes':len(raw_ib),'index_array_sha256':IB_SHA,'stride':40,'layout':[('position','float3',0),('normal','dec3n',12),('colour0','Colour raw bytes',16),('colour1','Colour raw bytes',20),('texcoord0','half2',24),('texcoord1','half2',28),('texcoord2','half2',32),('tangent','dec3n no handedness inferred',36)],'helpers':world.PINS,'world_helper_sha256':WORLD_HELPER_SHA}
    return g,raw_vb,raw_ib,proof


def brick_identity(doc,blob):
    require(len(doc['materials'])>35,'adjacent_material_missing');mat=doc['materials'][35]
    require(mat['name']=='CityGrime'and any(s.get('hash')==0xf1fe2b71 and s.get('texture_name')=='l_ho_ss_wall_brick_red_01.dds'for s in mat.get('extras',{}).get('samplers',[])),'adjacent_binding')
    nodes=[n for n in doc['nodes']if n.get('name')=='native_model_12_geometry_0'];require(len(nodes)==1 and doc['meshes'][nodes[0]['mesh']]['primitives'][0]['material']==35,'adjacent_geometry_binding')
    binding=mat['pbrMetallicRoughness']['baseColorTexture'];require(binding.get('texCoord',0)==0 and 'extensions'not in binding,'adjacent_uv0')
    image=doc['images'][doc['textures'][binding['index']]['source']];view=doc['bufferViews'][image['bufferView']];png=bytes(blob[view['byteOffset']:view['byteOffset']+view['byteLength']]);require(sha(png)==BRICK_PNG_SHA,'brick_png_pin')
    with Image.open(io.BytesIO(png))as pixels:
        require(pixels.size==(256,256),'brick_dimensions');require(sha(pixels.convert('RGBA').tobytes())==BRICK_RGBA_SHA,'brick_rgba_pin')
    return {'native_adjacent_model':12,'native_adjacent_material':35,'image_name':image.get('name'),'png_sha256':BRICK_PNG_SHA,'rgba_sha256':BRICK_RGBA_SHA,'dimensions':[256,256],'source128_diffuse_binding':False,'uv0_phase_correspondence':'Not proven; no exactsharedvertices withadjacentmodel12. Repeating source128UV0 preserved, authoringmetadataHeightSpecularmap1index0 supports surfaceUV role only.'}


def append_geometry(document,binary,g,raw_vb,raw_ib,provenance,borrowed_material=35):
    d=copy.deepcopy(document);blob=bytearray(binary)
    require(len(d.get('buffers',[]))==1 and 'uri'not in d['buffers'][0] and 0<=len(blob)-d['buffers'][0]['byteLength']<=3,'embedded_buffer')
    count=len(g['position']);require(g.get('stride')==40 and len(raw_vb)==count*40 and len(raw_ib)==len(g['indices'])*2,'raw_source_buffer_size');require(raw_ib==struct.pack('>'+str(len(g['indices']))+'H',*g['indices']),'raw_source_index_match');require(0<count<=2000 and len(g['indices'])>0 and len(g['indices'])%3==0 and len(g['indices'])<=6000,'geometry_budget')
    require(all(type(i)is int and 0<=i<count for i in g['indices']),'index_bounds')
    for key,width in [('position',3),('normal',3),('texcoord0',2),('texcoord1',2),('texcoord2',2),('colour0',4),('colour1',4),('tangent',3)]:
        require(len(g.get(key,[]))==count and all(len(row)==width and all(type(v)in(int,float)and math.isfinite(v)for v in row)for row in g[key]),'source_channel_shape_or_finite')
    require(all(.99<math.hypot(*row)<1.01 for row in g['normal']),'source_normal_direction')
    require(all(type(v)is int and 0<=v<=255 for key in('colour0','colour1')for row in g[key]for v in row),'raw_colour_bytes')
    require(type(borrowed_material)is int and 0<=borrowed_material<len(d['materials']),'borrowed_material')
    require(not any(n.get('name')=='native_model_128_geometry_0'for n in d['nodes']),'already_restored')
    def view(data):
        blob.extend(b'\0'*(-len(blob)%4));i=len(d['bufferViews']);d['bufferViews'].append({'buffer':0,'byteOffset':len(blob),'byteLength':len(data)});blob.extend(data);return i
    attrs={}
    for attr,key,kind,code,fmt in [('POSITION','position','VEC3',5126,'3f'),('NORMAL','normal','VEC3',5126,'3f'),('TEXCOORD_0','texcoord0','VEC2',5126,'2f'),('TEXCOORD_1','texcoord1','VEC2',5126,'2f'),('TEXCOORD_2','texcoord2','VEC2',5126,'2f'),('_RACER_SOURCE_COLOR0','colour0','VEC4',5121,'4B'),('_RACER_SOURCE_COLOR1','colour1','VEC4',5121,'4B'),('_RACER_SOURCE_TANGENT','tangent','VEC3',5126,'3f')]:
        rows=g[key];a={'bufferView':view(b''.join(struct.pack('<'+fmt,*row)for row in rows)),'componentType':code,'count':count,'type':kind}
        if attr=='POSITION':a.update(min=[min(r[k]for r in rows)for k in range(3)],max=[max(r[k]for r in rows)for k in range(3)])
        attrs[attr]=len(d['accessors']);d['accessors'].append(a)
    indices=len(d['accessors']);d['accessors'].append({'bufferView':view(struct.pack('<'+str(len(g['indices']))+'H',*g['indices'])),'componentType':5123,'count':len(g['indices']),'type':'SCALAR'})
    raw_views={'vertex':view(raw_vb),'index':view(raw_ib)}
    clone=copy.deepcopy(d['materials'][borrowed_material]);clone['name']='AUTHORED restored model128 brick base';clone['alphaMode']='OPAQUE';clone['extras']={'nativeSourceShader':copy.deepcopy(provenance.get('native_shader',{})),'racerFacadeRestoration':{'authority':POLICY,'borrowed_material':borrowed_material,'borrowed_material_sha256':sha(encoded(d['materials'][borrowed_material])),'source_model':128,'source_geometry':0,'raw_buffer_views':raw_views,'source_tangent':'Custom3componentoriginaldirectiononly; no standardTANGENThandedness invented.'}}
    material=len(d['materials']);d['materials'].append(clone);mesh=len(d['meshes']);d['meshes'].append({'primitives':[{'attributes':attrs,'indices':indices,'material':material,'mode':4}]});node=len(d['nodes']);d['nodes'].append({'name':'native_model_128_geometry_0','mesh':mesh})
    scene=d.get('scene',0);require(type(scene)is int and 0<=scene<len(d['scenes']),'scene_index');d['scenes'][scene]['nodes'].append(node)
    d.setdefault('extras',{})['racerFacadeRestoration']={'authority':POLICY,'source':provenance,'original_bin_bytes':len(binary),'original_bin_sha256':sha(binary),'restored_model':128,'restored_node':node,'restored_mesh':mesh,'restored_material':material,'raw_buffer_views':raw_views,'historical_omission_records':'Originalextras retained unchanged; originalomitted128record is superseded by this explicit restoration. Model116remainsomitted.'}
    d['buffers'][0]['byteLength']=len(blob)
    return d,blob


def publish(output,files):
    output=safe(output)
    for name in files:
        require(Path(name).name==name,'output_filename');p=output/name
        if p.exists()or p.is_symlink():require(p.is_file()and not p.is_symlink(),'output_target_type')
    require(sum(map(len,files.values()))<=OUTPUT_LIMIT,'output_budget');existing={};used=0
    if output.exists():
        require(output.is_dir(),'output_directory')
        for p in output.rglob('*'):
            require(not p.is_symlink(),'output_symlink');require(p.is_file()or p.is_dir(),'output_entry_type')
            if p.is_file():
                require(p.stat().st_size<=OUTPUT_LIMIT-used,'output_budget');data=regular_bytes(p,OUTPUT_LIMIT-used);used+=len(data)
                if p.parent==output and p.name in files:existing[p.name]=data
        require(all(n not in existing or existing[n]==b for n,b in files.items()),'immutable_conflict')
    require(used+sum(len(b)for n,b in files.items()if n not in existing)<=OUTPUT_LIMIT,'output_budget')
    output.mkdir(parents=True,exist_ok=True)
    for n,b in files.items():require(Path(n).name==n,'output_filename');immutable(output/n,b)


def prepare(source,iso,references,texture_helper,output=None):
    raw=regular_bytes(safe(source),GLB_LIMIT);require(sha(raw)==V4_SHA,'v4_pin');d,b=unpack(raw);borrowed=brick_identity(d,b)
    g,vb,ib,proof=native_geometry(iso,references,texture_helper);proof['borrowed_base']=borrowed;proof['authority']=POLICY
    new,blob=append_geometry(d,b,g,vb,ib,proof);result=pack(new,blob);require(len(result)<=GLB_LIMIT,'glb_budget')
    report={'source_v4_sha256':V4_SHA,'source_v4_bytes':len(raw),'output_sha256':sha(result),'output_bytes':len(result),'source':proof,'authority':POLICY,'vertices_added':len(g['position']),'triangles_added':len(g['indices'])//3,'images_added':0,'original_image_count':len(d['images']),'decoded_rgba_unchanged':True,'source_arrays':'OriginalBINprefix/mesh/node/accessor/material/image/texture/samplerprefixes retained; exactnative128arrays appended, rawpackedVB/IB retained.','visual_acceptance':'Not established. Requires actualsamecamera before/after screenshot and alpha/roof/facade/depth/grade review. No safe drivability/nativecomposition/AAAclaim.'}
    if output is not None:publish(output,{'2300-restored-facade-v5.glb':result,'2300-restored-facade-v5.json':encoded(report)})
    return result,report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--iso',type=Path,required=True);p.add_argument('--references',type=Path,required=True);p.add_argument('--texture-helper',type=Path,required=True);p.add_argument('--output',type=Path);a=p.parse_args();_,report=prepare(a.source,a.iso,a.references,a.texture_helper,a.output);print(json.dumps(report,indent=2))


if __name__=='__main__':main()
