#!/usr/bin/env python3
"""Append a normal-only source profile to three exact MCLA façade primitives."""
import argparse
import copy
import io
import json
import math
import os
from pathlib import Path
import stat
import struct
from PIL import Image
import prepare_source_bump as bump
import inspect_world_resources as world
from install_cars import regular_bytes, immutable
from prepare_gt4_vehicle import unpack, pack

SOURCE_SHA='b403afbe2fa4d146032514e00388fc125b5020ec9d7865edc09bcf35bf65548d'
WORLD_SHA='28d0a7fff462cb48d2ea1b50afe2b42fa4d56f8f8eec6170c742fcf32cbea5d3'
BUMP_SHA='b86c5cfe99c1745060ba49d8656142d3e9d58d8a48d376701a16af50ca9c08ff'
OFFSET=2259124224
STORED=2021343
STORED_SHA='ab9f8b36c957ecb9183eefd44cbd2c4bbea4ae4dca3011963cb51ca4ee2548a6'
DECODED=4980736
DECODED_SHA='16630c6a17f808db0f2de1e39cbf888134a999b7f8e44fee06a059554ef78044'
GLB_LIMIT=8*1024**2
DIRECTORY_LIMIT=12*1024**2
PIXEL_LIMIT=128*1024
POLICY=('Source-code/compiled selected-kernel-backed NORMAL ONLY: vertex stage computes '
 'B=cross(T,N)*Tw per vertex; pixel stage normalizes interpolatedN-(2A-1)*interpolatedB-'
 '(2R-1)*interpolatedT. Selected compiled path samples source UV0 unscaled; other permutations '
 'and live runtime UV transforms remain unknown. Original linear RGBA and tangent XYZ plus signed '
 'packed W preserved. G/B retained without specular/exponent/intensity/mixer adoption. Native live '
 'patched declaration, permutation, mipchain, filtering precision and pixel equivalence remain unknown. '
 'Per-model signed-W counts and mixed-triangle counts are recorded in source.frame; mixed-W triangles '
 'are supported by per-vertex B interpolation. No universal same-W constraint is imposed.')
TARGETS={
 111:{'shader':31,'vertices':705,'triangles':444,'BS':'l_ho_ss_misc_whisky_01_bs.dds','size':[128,128],'encoded_sha256':'de715b0d12aebb30ddf447fcc6d492d7900e815eef3da0c1b6b345bea17be9b5','VB_sha256':'be408548b886793ea3e6eb646101ab2a9dc8f24824815ec8422bcb698ed83cc3','Twords_sha256':'2e008ea6f4ce860495a67bf6cacaa3d1ab147f12b07e1f199bf51eb44c47838a'},
 103:{'shader':42,'vertices':56,'triangles':28,'BS':'l_ho_ss_wall_garage_bs.dds','size':[64,64],'encoded_sha256':'20388185ac3bcb192fd5dc3ee975a48371651f90939bce141ff387d01c7bf6e9','VB_sha256':'51657edf013ca0697462cc770405e61f42c8641184077f7f39f47df9c5ba635e','Twords_sha256':'9c7bf55d5ece2e51ddeccf3ddaa4b27658bf8b6c5c5f3a9fb1c81fa8fab41089'},
 25:{'shader':57,'vertices':52,'triangles':28,'BS':'l_ho_ss_door_bodyshop_bs.dds','size':[64,128],'encoded_sha256':'4f7b3a288eb6d8a082703c21081469635a1af7487b1391b47842db8a9bf6ed2b','VB_sha256':'c793398baf8bbd6d511e3b2e56ae05a68360f3d03f9832fde6db7e31c1b686fd','Twords_sha256':'dae170a95ae489eb0dbd0ad5f93b6b4077864683aae188e2724b7e18de4012f6'}}
require=bump.require
sha=bump.sha
encoded=bump.encoded


def source_range(iso):
    iso=bump.safe(iso);fd=os.open(iso,os.O_RDONLY|os.O_NONBLOCK|os.O_NOFOLLOW)
    with os.fdopen(fd,'rb')as stream:
        before=os.fstat(stream.fileno());require(stat.S_ISREG(before.st_mode)and before.st_size==world.ISO_BYTES,'iso_size')
        stream.seek(OFFSET);raw=stream.read(STORED);after=os.fstat(stream.fileno())
    require(len(raw)==STORED and sha(raw)==STORED_SHA and(before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns),'source_range_pin')
    return raw


def frame_rows(g,raw):
    count=len(g['position']);require(g['stride']==28 and len(raw)==count*28 and len(g['normal'])==len(g['tangent'])==count,'frame_size')
    rows=[];nl=[];tl=[];dots=[]
    for i,(n,t)in enumerate(zip(g['normal'],g['tangent'])):
        nw=struct.unpack_from('>I',raw,i*28+12)[0];tw=struct.unpack_from('>I',raw,i*28+24)[0]
        require(all(math.isfinite(v)for v in(*n,*t)),'frame_nonfinite')
        require(struct.pack('<3f',*bump.xyz(nw))==struct.pack('<3f',*n)and struct.pack('<3f',*bump.xyz(tw))==struct.pack('<3f',*t),'frame_source_xyz')
        a,b=math.hypot(*n),math.hypot(*t);require(.98<=a<=1.02 and .98<=b<=1.02,'frame_length')
        dot=abs(sum(x*y for x,y in zip(n,t)))/(a*b);require(dot<=.05,'frame_orthogonality')
        rows.append((*t,float(bump.signed_w(tw))));nl.append(a);tl.append(b);dots.append(dot)
    indices=g['indices'];require(indices and len(indices)%3==0 and all(type(i)is int and 0<=i<count for i in indices),'source_indices')
    mixed=sum(len({rows[j][3]for j in indices[i:i+3]})>1 for i in range(0,len(indices),3))
    return rows,{'normal_length':[min(nl),max(nl)],'tangent_length':[min(tl),max(tl)],'max_abs_dot_ratio':max(dots),'negative_w':sum(r[3]<0 for r in rows),'positive_w':sum(r[3]>0 for r in rows),'mixed_W_triangles':mixed,'mixed_W_policy':'Allowed: renderer computes bitangent per vertex then interpolates B.'}


def native_items(iso,references,texture_helper):
    require(sha(regular_bytes(Path(world.__file__).absolute(),128*1024))==WORLD_SHA,'world_helper_pin')
    require(sha(regular_bytes(Path(bump.__file__).absolute(),128*1024))==BUMP_SHA,'bump_helper_pin')
    modules=world.helpers(bump.safe(references),bump.safe(texture_helper));raw=source_range(iso);h=modules['mcla_lzx'].parse_header(raw);require(h['virtual']+h['physical']==DECODED,'decoded_budget')
    data,h=modules['mcla_lzx'].decompress(raw,expected=DECODED);require(sha(data)==DECODED_SHA,'decoded_pin');reader,sector=world.decode_sector(data,h,modules)
    items={};pixel_work=0
    for model,pin in TARGETS.items():
        matches=[g for g in sector['geometries']if g['model']==model and g['geometry']==0];require(len(matches)==1,'source_geometry_ambiguity');g=matches[0]
        require((g['shader'],g['vertex_count'],g['index_count'])==(pin['shader'],pin['vertices'],pin['triangles']*3),'source_geometry_pin')
        shader=sector['shaders'][g['shader']];require(shader['name']=='CityBumpSpec','source_family')
        bs=[s for s in shader['samplers']if s['hash']==0x332ebe1c];require(len(bs)==1 and bs[0]['texture_name']==pin['BS'],'source_bs_binding')
        key=world.texture_hash(pin['BS']);require(key in sector['textures'],'local_texture_required');tex=sector['textures'][key]
        require([tex['width'],tex['height']]==pin['size']and tex['format']=='dxt5','source_texture_layout')
        encoded_pixels=data[tex['offset']:tex['offset']+tex['stored_extent']];require(sha(encoded_pixels)==pin['encoded_sha256'],'source_encoded_pin')
        f=tex['fetch'];require((f[3]>>1&4095)==0x688 and all((f[0]>>(2+2*i)&3)==0 for i in range(4))and f[3]&1==0 and(f[3]>>13&63)==0 and not(f[5]>>2&1),'source_fetch_identity_unsigned_linear')
        piece=reader.pointer(16,16);lod=reader.pointer(piece+12,32);mp=reader.offset(world.array(reader,lod+24,1024)[model],28);ga=reader.offset(world.array(reader,mp+4,512)[0],80);vb=reader.pointer(ga+12,32);va=reader.offset(reader.u32(vb+24),g['vertex_count']*g['stride']);fv=reader.offset(reader.u32(vb+16),16);rawvb=data[va:va+g['vertex_count']*g['stride']]
        require(data[fv:fv+16]==bytes.fromhex('000040691c000005aa1111111199a996')and sha(rawvb)==pin['VB_sha256'],'source_vb_declaration_pin')
        words=b''.join(rawvb[i*28+24:i*28+28]for i in range(g['vertex_count']));require(sha(words)==pin['Twords_sha256'],'source_tangent_words_pin');tangents,frame=frame_rows(g,rawvb)
        amount=tex['width']*tex['height']*4;pixel_work+=amount;require(pixel_work<=PIXEL_LIMIT,'source_pixel_budget');rgba=modules['mcla_texture'].pixels(reader,tex);require(len(rgba)==amount,'source_pixel_size')
        out=io.BytesIO();Image.frombytes('RGBA',tuple(pin['size']),rgba).save(out,format='PNG');png=out.getvalue();require(len(png)<=128*1024,'png_budget')
        with Image.open(io.BytesIO(png))as im:require(im.mode=='RGBA'and im.tobytes()==rgba,'png_roundtrip')
        proof={'entry':2300,'model':model,'geometry':0,'source_shader':g['shader'],'native_shader':shader,'stride':28,'raw_VB_sha256':sha(rawvb),'Twords_sha256':sha(words),'vertex_offset':va,'declaration_hex':data[fv:fv+16].hex(),'texture_header':tex,'encoded_sha256':sha(encoded_pixels),'rgba_sha256':sha(rgba),'png_sha256':sha(png),'rgba_bytes':amount,'frame':frame,'source_colour':'OriginalColour1 bytes retained in GLB; native channel/alpha/AO/nightfill interpretation unknown and unapplied.'}
        items[model]={'geometry':g,'shader':shader,'tangents':tangents,'png':png,'proof':proof}
    proof={'entry':2300,'expected_iso_sha256':world.ISO_SHA,'prior_canonical_receipt':'games/INPUTS.json donor-inventory2026-11-05','current_verification_scope':'CurrentregularISOsize/unchangedmetadata+exactstored/decodedrangeSHA; wholeISOdigestpriorreceipt only.','absolute_offset':OFFSET,'stored_bytes':STORED,'stored_sha256':STORED_SHA,'decoded_bytes':DECODED,'decoded_sha256':DECODED_SHA,'helpers':world.PINS,'world_helper_sha256':WORLD_SHA,'bump_helper_sha256':BUMP_SHA,'selected_source_RGBA_bytes':pixel_work,'bank_reads':0}
    return items,proof


def match_primitive(doc,binary,model,item):
    nodes=[n for n in doc.get('nodes',[])if n.get('name')==f'native_model_{model}_geometry_0'];require(len(nodes)==1,'prepared_node_ambiguity');node=nodes[0]
    require(not any(k in node for k in('matrix','translation','rotation','scale','children')),'prepared_node_pose');mi=node.get('mesh');require(type(mi)is int and 0<=mi<len(doc['meshes']),'prepared_mesh')
    mesh=doc['meshes'][mi];require(len(mesh.get('primitives',[]))==1,'prepared_primitive_ambiguity');pr=mesh['primitives'][0];require(pr.get('mode',4)==4,'prepared_topology');attrs=pr.get('attributes',{});g=item['geometry']
    for attr,ch,width in[('POSITION','position',3),('NORMAL','normal',3),('TEXCOORD_0','texcoord0',2)]:
        require(attr in attrs,'prepared_attribute_missing');rows=bump.values(doc,binary,attrs[attr],'VEC'+str(width),5126,'f',width)
        require(b''.join(struct.pack('<'+'f'*width,*x)for x in rows)==b''.join(struct.pack('<'+'f'*width,*x)for x in g[ch]),'prepared_source_'+ch+'_mismatch')
    ai=pr.get('indices');require(type(ai)is int and 0<=ai<len(doc['accessors']),'prepared_indices');code=doc['accessors'][ai].get('componentType');require(code in(5123,5125),'prepared_index_type');indices=[x[0]for x in bump.values(doc,binary,ai,'SCALAR',code,'H'if code==5123 else'I',1)];require(indices==g['indices'],'prepared_source_indices_mismatch')
    if'_RACER_SOURCE_COLOR1'in attrs:
        require(bump.values(doc,binary,attrs['_RACER_SOURCE_COLOR1'],'VEC4',5121,'B',4)==g['colour1'],'prepared_source_colour_bytes_mismatch')
    require('TANGENT'not in attrs,'prepared_tangent_conflict');mat=doc['materials'][pr['material']]
    require(mat.get('extras',{}).get('name')=='CityBumpSpec'and mat['extras'].get('samplers')==item['shader']['samplers'],'prepared_source_sampler_mismatch')
    require('normalTexture'not in mat and bump.EXTENSION not in mat.get('extensions',{}),'prepared_material_conflict')
    return mi,pr['material']


def derive(doc,binary,items):
    require(set(items)==set(TARGETS),'selected_models');require(len(doc.get('buffers',[]))==1 and 'uri'not in doc['buffers'][0]and 0<=len(binary)-doc['buffers'][0]['byteLength']<=3,'embedded_buffer')
    matches={model:match_primitive(doc,binary,model,item)for model,item in items.items()};d=copy.deepcopy(doc);blob=bytearray(binary);joins=[]
    def view(data):
        blob.extend(b'\0'*(-len(blob)%4));i=len(d['bufferViews']);d['bufferViews'].append({'buffer':0,'byteOffset':len(blob),'byteLength':len(data)});blob.extend(data);return i
    sampler=len(d.setdefault('samplers',[]));d['samplers'].append({'magFilter':9729,'minFilter':9987,'wrapS':10497,'wrapT':10497})
    for model,item in items.items():
        mi,oldmaterial=matches[model];rows=item['tangents'];g=item['geometry'];require(len(rows)==len(g['position'])and all(len(t)==4 for t in rows),'tangent_count')
        ai=len(d['accessors']);d['accessors'].append({'bufferView':view(b''.join(struct.pack('<4f',*x)for x in rows)),'componentType':5126,'count':len(rows),'type':'VEC4'})
        ii=len(d['images']);d['images'].append({'bufferView':view(item['png']),'mimeType':'image/png','name':TARGETS[model]['BS']+' original packed RGBA'});ti=len(d['textures']);d['textures'].append({'source':ii,'sampler':sampler});mat=copy.deepcopy(doc['materials'][oldmaterial]);mat.setdefault('extensions',{})[bump.EXTENSION]={'texture':ti};mat.setdefault('extras',{})['racerFacadeSourceBumpNormalOnly']={'policy':POLICY,'originalMaterial':oldmaterial,'source':item['proof']};newmaterial=len(d['materials']);d['materials'].append(mat);pr=d['meshes'][mi]['primitives'][0];pr['attributes']['TANGENT']=ai;pr['material']=newmaterial;joins.append({'model':model,'mesh':mi,'primitive':0,'originalMaterial':oldmaterial,'material':newmaterial,'tangentAccessor':ai,'texture':ti})
    require(bump.EXTENSION not in d.get('extensionsRequired',[]),'extension_optional');used=d.setdefault('extensionsUsed',[])
    if bump.EXTENSION not in used:used.append(bump.EXTENSION)
    d['buffers'][0]['byteLength']=len(blob);return d,blob,joins


def prefix_check(old,ob,new,nb,joins):
    require(bytes(nb[:len(ob)])==bytes(ob),'binary_prefix_changed')
    for key in('nodes','scenes','scene'):require(new.get(key)==old.get(key),'scene_changed')
    for key in('materials','accessors','bufferViews','images','textures','samplers'):require(new.get(key,[])[:len(old.get(key,[]))]==old.get(key,[]),'prefix_changed')
    restored=copy.deepcopy(new['meshes'])
    for j in joins:
        pr=restored[j['mesh']]['primitives'][0];pr['attributes'].pop('TANGENT');pr['material']=j['originalMaterial']
    require(restored==old['meshes'],'unselected_primitive_changed')
    for key,value in old.items():
        if key not in('buffers','meshes','materials','accessors','bufferViews','images','textures','samplers','extensionsUsed'):require(new.get(key)==value,'document_changed')
    require(new['buffers'][0]|{'byteLength':old['buffers'][0]['byteLength']}==old['buffers'][0],'buffer_changed')
    require(new.get('extensionsUsed',[])==old.get('extensionsUsed',[])+([]if bump.EXTENSION in old.get('extensionsUsed',[])else[bump.EXTENSION]),'extension_usage')


def build(source,iso,references,texture_helper):
    source=bump.safe(source);raw=regular_bytes(source,GLB_LIMIT);require(sha(raw)==SOURCE_SHA,'source_glb_pin');doc,binary=unpack(raw);items,sourceproof=native_items(iso,references,texture_helper);new,blob,joins=derive(doc,binary,items);prefix_check(doc,binary,new,blob,joins);glb=pack(new,blob);require(len(glb)<=GLB_LIMIT,'glb_budget')
    rgba=0
    for image in new['images']:
        png=bump.view_bytes(new,blob,image['bufferView'])
        with Image.open(io.BytesIO(png))as im:require(im.width<=2048 and im.height<=2048,'image_dimensions');rgba+=im.width*im.height*4
    require(len(new['images'])<=128 and rgba<=32*1024**2,'per_asset_image_budget')
    report={'source_glb_sha256':SOURCE_SHA,'source':sourceproof,'bindings':joins,'models':{model:item['proof']for model,item in items.items()},'output_bytes':len(glb),'output_sha256':sha(glb),'images':len(new['images']),'decoded_RGBA_bytes':rgba,'policy':POLICY,'checks':'PASS freshlydecodedexactsourcePOSITION/NORMAL/UV0/indices/rawColour1 matches BEFORE binding; alloldBIN/document/geometryprefixes unchanged exceptselectedTANGENT/material. SourceTxyz/signedW unchanged inclmixedW; allBSRGBA preserved. Globalactualpool/nativeconsumer/visualquality requiresseparatemeasurement.'}
    files={'facade-source-bump.glb':glb,'manifest.json':encoded(report)}
    for model,item in items.items():files[f'source-{model}-bs.png']=item['png']
    return files,report


def publish(output,files):
    output=bump.safe(output);require(output.parent.is_dir(),'output_parent');require(not output.exists()or output.is_dir(),'output_directory');size=0
    if output.exists():
        for p in output.iterdir():require(p.is_file()and not p.is_symlink(),'output_entry');size+=p.stat().st_size
    for name,data in files.items():
        require(Path(name).name==name and name not in('','.','..'),'output_name');p=output/name
        if p.exists()or p.is_symlink():require(not p.is_symlink()and p.stat().st_size==len(data)and regular_bytes(p,len(data))==data,'immutable_conflict')
        else:size+=len(data)
    require(size<=DIRECTORY_LIMIT,'directory_budget');output.mkdir(exist_ok=True)
    for name,data in files.items():immutable(output/name,data)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--iso',type=Path,required=True);p.add_argument('--helpers',type=Path,required=True);p.add_argument('--texture-helper',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--export',action='store_true');a=p.parse_args();files,report=build(a.source,a.iso,a.helpers,a.texture_helper)
    if a.export:publish(a.output,files)
    print(json.dumps({k:report[k]for k in['output_bytes','output_sha256','images','decoded_RGBA_bytes','bindings']},sort_keys=True))


if __name__=='__main__':main()
