#!/usr/bin/env python3
"""Local SCX/RPK diffuse inspection export; unresolved slots stay untextured."""
import argparse
import copy
import base64
import hashlib
import json
from pathlib import Path
import struct
import zlib
from slrr_resources import ResourceResolver
from slrr_assets import scx, gltf

MAX_EXPORT = 32 * 1024**2
CHANNELS = ('diffuse','bump','specular','reflection','diffuse_layer2')
LIMITS = [
    'Zero-based slots follow inspected reference implementations; supplied native game behavior not executed.',
    'Only diffuse PNG is bound; secondary mix, reflection, bump and specular behavior remains unimplemented.',
    'Raw UV1 is unflipped; orientation remains unknown until source texture review.',
    'REPEAT sampling and white/gray neutral PBR factors are authored inspection choices, not recovered sampler/color-space semantics.'
]

def binding_chain(node):
    if node.get('status') != 'resolved': raise ValueError('mesh/render resource unresolved')
    own = [r for r in node['references'] if r['command']=='texture']
    meshes = [s for s in node['sources'] if s['path'].lower().endswith('.scx')]
    children = [r['reference'] for r in node['references'] if r['command']=='mesh']
    if meshes:
        if len(meshes)!=1 or children: raise ValueError('ambiguous SCX source chain')
        return meshes[0], own
    if len(children)!=1: raise ValueError('exactly one mesh reference required')
    source, inherited = binding_chain(children[0])
    return source, own if own else inherited

def texture_slots(references):
    result=[]
    for index,reference in enumerate(references):
        resource=reference['reference'];sources=resource.get('sources',[])
        row={'index':index,'declaration_line':reference['line'],'status':resource['status'],
             'resource':resource.get('identity'),'sources':sources}
        result.append(row)
    return result

def png_dimensions(data):
    if len(data)<33 or data[:8]!=b'\x89PNG\r\n\x1a\n' or data[8:16]!=b'\x00\x00\x00\rIHDR':
        raise ValueError('source is not a PNG with IHDR')
    if zlib.crc32(data[12:29]) & 0xffffffff != struct.unpack_from('>I',data,29)[0]:
        raise ValueError('PNG IHDR checksum mismatch')
    width,height=struct.unpack_from('>II',data,16)
    if not 0<width<=8192 or not 0<height<=8192: raise ValueError('PNG dimensions outside inspection budget')
    return width,height

def attach_diffuse(scene, geometry, slots, resolver):
    scene=copy.deepcopy(scene);issues=[];materials=[];images=[];textures=[];cache={};bindings=[]
    primitives=scene['meshes'][0]['primitives']
    usable=[mesh for mesh in geometry if mesh['positions'] and mesh['triangles']]
    if len(usable)!=len(primitives): raise ValueError('geometry/primitive count mismatch')
    for ordinal,(mesh,primitive) in enumerate(zip(usable,primitives)):
        indices=mesh.get('texture_indices')
        binding={'primitive':ordinal,'channels':dict(zip(CHANNELS,indices)) if indices else {},
                 'status':'unresolved','texture_slot':indices[0] if indices else None}
        material={'name':'source-diffuse-'+str(ordinal),'doubleSided':True,
                  'pbrMetallicRoughness':{'baseColorFactor':[.7,.7,.7,1.], 'metallicFactor':0.,'roughnessFactor':1.}}
        index=indices[0] if indices else None
        reason=None
        if index in (65535,4294967295): binding['status']='absent';reason='source diffuse absent-map sentinel'
        elif index is None: reason='source diffuse index unavailable'
        elif type(index) is not int or not 0<=index<len(slots): reason='source diffuse index outside declared texture table'
        else:
            slot=slots[index];sources=slot.get('sources',[])
            if slot.get('status')=='null':reason='source diffuse slot explicitly null'
            elif slot.get('status')!='resolved' or len(sources)!=1:reason='source diffuse slot unresolved or ambiguous'
            elif not sources[0]['path'].lower().endswith('.png'):reason='only original PNG diffuse payloads supported'
            elif 'TEXCOORD_0' not in primitive['attributes']:reason='UV1 unavailable; no invented mapping'
            else:
                source=sources[0]
                try:
                    data,path=resolver.read(source['path']);digest=hashlib.sha256(data).hexdigest()
                    if digest!=source['sha256']:raise ValueError('selected source hash mismatch')
                    width,height=png_dimensions(data)
                    if digest not in cache:
                        cache[digest]=len(textures)
                        images.append({'name':path,'uri':'data:image/png;base64,'+base64.b64encode(data).decode(),
                                       'extras':{'sha256':digest,'source_path':path,'width':width,'height':height}})
                        textures.append({'source':len(images)-1,'sampler':0})
                    material['pbrMetallicRoughness'].update(baseColorFactor=[1.,1.,1.,1.],baseColorTexture={'index':cache[digest],'texCoord':0})
                    binding.update(status='bound',source_path=path,sha256=digest,width=width,height=height)
                except (ValueError,OSError) as error: reason=str(error)
        if reason:
            binding['reason']=reason
            issues.append({'primitive':ordinal,'slot':index,'reason':reason})
        material['extras']={'binding':binding,'factor_provenance':'authored neutral inspection factor'}
        primitive['material']=len(materials);materials.append(material);bindings.append(binding)
    scene['materials']=materials
    if images:
        scene['images']=images;scene['textures']=textures
        scene['samplers']=[{'wrapS':10497,'wrapT':10497}]
    scene.setdefault('extras',{}).update(texture_slots=slots,material_bindings=bindings,
                                       material_issues=issues,material_limitations=LIMITS)
    encoded=json.dumps(scene,separators=(',',':'),allow_nan=False)
    if len(encoded.encode())>MAX_EXPORT:raise ValueError('glTF export exceeds32MiB')
    return scene,{'bindings':bindings,'issues':issues,'texture_slots':slots,'limitations':LIMITS}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,required=True);p.add_argument('--package',required=True)
    p.add_argument('--resource',type=lambda s:int(s,0),required=True)
    p.add_argument('--gltf',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--scale',type=float,default=1.);p.add_argument('--lift',type=float,default=0.)
    p.add_argument('--reverse-forward',action='store_true');a=p.parse_args()
    if a.gltf.resolve()==a.output.resolve():raise ValueError('glTF and report paths must differ')
    if a.gltf.exists() or a.output.exists():raise ValueError('output paths must be fresh')
    resolver=ResourceResolver(a.root);chain=resolver.resolve(a.package,a.resource);source,refs=binding_chain(chain)
    data,key=resolver.read(source['path'])
    if hashlib.sha256(data).hexdigest()!=source['sha256']:raise ValueError('SCX source hash mismatch')
    decoded=scx(data);decoded['sha256']=source['sha256']
    scene=gltf(decoded,a.scale,a.lift,a.reverse_forward)
    scene,report=attach_diffuse(scene,decoded['geometry'],texture_slots(refs),resolver)
    report.update(mesh=source,resource=chain['identity'],provenance=resolver.provenance(),source_bytes_read=resolver.bytes)
    with a.gltf.open('x') as out:json.dump(scene,out,separators=(',',':'),allow_nan=False)
    with a.output.open('x') as out:json.dump(report,out,indent=2,allow_nan=False)
if __name__=='__main__':main()
