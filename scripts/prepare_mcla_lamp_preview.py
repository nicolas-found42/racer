#!/usr/bin/env python3
"""Isolated Racer-authored daytime lamps; native palette and shader formula unknown."""
import argparse
import copy
import hashlib
import io
import json
from pathlib import Path
import struct
from PIL import Image
from install_cars import regular_bytes, immutable
from prepare_gt4_vehicle import unpack, pack

PINS={'original':'7f4818ad423f9db6802e70a65b6de4c4cb0e38dab4b335f98318a7d8360bd56a',
      'prepared':'71a6d4ab044ba95673582f34eb9a11621fe89aeda488bea914964a2e1e6e7bd6',
      'descriptor':'955d8f67bf50582d961ab60eba6c7a5d109e3159aa7a764e930ffafe7f1d1bcc',
      'attributes':'d650eb2d11b959b1d4a04a234999cb6cb4302d757c8fa0b96683b2b096d7197c',
      'illumination':'53198e6c3246b658f5fc4f2671cda2ffab3461097e2fe671e2ef874bbe33b826'}
LIMITS={'original':12*1024**2,'prepared':12*1024**2,'descriptor':16384,'attributes':2*1024**2,'illumination':65536}
OUTPUT_LIMIT=12*1024**2
PREFIX='vp_nsn_350z_06/resources/vehicle/vp_nsn_350z_06/'
PAINT=tuple(PREFIX+n+'/shader8' for n in ('body_lod_0.xrsc','bumper_f0_lod_0.xrsc','bumper_r0_lod_0.xrsc','door_l0_lod_0.xrsc','door_r0_lod_0.xrsc','fenders0_lod_0.xrsc','hood0_lod_0.xrsc','skirts0_lod_0.xrsc'))
PALETTES={'silver':(.36,.42,.48),'crimson':(.42,.008,.012)}
NORMAL_PNG_SHA='bdabb4a6cb058ac5e5b9a153fdb075e464411460c5809ab9b56f682eac0110a7'

def require(ok,reason):
    if not ok:raise ValueError(reason)

def sha(data):return hashlib.sha256(data).hexdigest()

def platform_path(path):
    path=Path(path).absolute()
    return Path('/tmp').resolve().joinpath(*path.parts[2:]) if path.parts[1:2]==('tmp',) else path

def pinned(path,key):
    data=regular_bytes(platform_path(path),LIMITS[key]);require(sha(data)==PINS[key],'input_pin_'+key);return data

def rows(doc,blob,index):
    require(type(index)is int and 0<=index<len(doc['accessors']),'accessor_index');a=doc['accessors'][index]
    require(not a.get('sparse') and not a.get('normalized') and a.get('componentType') in (5126,5123,5125),'accessor_format')
    fmt={5126:'f',5123:'H',5125:'I'}[a['componentType']]*{'SCALAR':1,'VEC2':2,'VEC3':3}[a['type']];width=struct.calcsize('<'+fmt);v=doc['bufferViews'][a['bufferView']]
    start=v.get('byteOffset',0)+a.get('byteOffset',0);stride=v.get('byteStride',width);count=a['count'];require(0<count<=500000 and stride>=width and start+(count-1)*stride+width<=len(blob),'accessor_bounds')
    return [struct.unpack_from('<'+fmt,blob,start+i*stride) for i in range(count)]

def data_arrays(doc,blob,primitive):
    attrs=primitive['attributes'];return rows(doc,blob,attrs['POSITION']),rows(doc,blob,attrs['TEXCOORD_0']),[x[0] for x in rows(doc,blob,primitive['indices'])]

def find_prepared(doc,blob,original_arrays):
    pos,uv,indices=original_arrays;expected=[(x,y,-z) for x,y,z in pos];flipped=[v for i in range(0,len(indices),3) for v in (indices[i],indices[i+2],indices[i+1])];matches=[]
    for mi,mesh in enumerate(doc['meshes']):
        for pi,p in enumerate(mesh['primitives']):
            if doc['accessors'][p['attributes']['POSITION']]['count']!=len(pos):continue
            actual=data_arrays(doc,blob,p)
            if actual==(expected,uv,flipped):matches.append((mi,pi))
    require(len(matches)==1,'prepared_lamp_match_ambiguous_or_missing');return matches[0]

def partition(indices,selector):
    require(len(indices)%3==0 and len(selector)<=500000,'partition_budget');groups={}
    for t in range(0,len(indices),3):
        values=[selector[i] for i in indices[t:t+3]];require(all(v==values[0] for v in values),'mixed_native_lamp_ids');ident,aux=values[0]
        require(aux==1 and 0<=ident<=20 and ident==int(ident),'native_selector_shape');groups.setdefault(int(ident),[]).append(t//3)
    return groups

def derive(original,prepared,descriptor,attributes,illumination,authored_rims=False,authored_paint=None,authored_trim=False):
    require(authored_paint is None or authored_paint in PALETTES,'authored_paint_palette')
    for key,data in zip(('original','prepared','descriptor','attributes','illumination'),(original,prepared,descriptor,attributes,illumination)):
        require(len(data)<=LIMITS[key] and sha(data)==PINS[key],'input_pin_'+key)
    od,ob=unpack(original);doc,blob=unpack(prepared);before=copy.deepcopy(doc);prefix=bytes(blob);evidence=json.loads(attributes)
    require(len(doc['materials'])==141,'source_material_count')
    with Image.open(io.BytesIO(illumination))as im:require(im.format=='PNG' and im.size==(128,128),'illumination_dimensions');im.verify()
    require('source_sha256 '+PINS['original'] in descriptor.decode(),'descriptor_source_identity')
    changes=[];targets={}
    for resource in evidence['resources']:
        role='head' if resource['source']['file'].endswith('headlight0_lod_0.xrsc') else 'tail'
        require(role not in [v['role']for v in targets.values()],'duplicate_lamp_role');require(len(resource['geometries'])==1,'lamp_geometry_count');g=resource['geometries'][0];membership=g['channel_statistics']['original_GLTF_membership'];mi,pi=membership['mesh'],membership['primitive'];p=od['meshes'][mi]['primitives'][pi];native=data_arrays(od,ob,p)
        require(sha(b''.join(struct.pack('>3f',*v)for v in native[0]))==g['position_sha256'] and native[1]==[tuple(v)for v in g['source_arrays']['texcoord0']] and native[2]==g['indices'],'native_original_array_map')
        match=find_prepared(doc,blob,native);nodes=[i for i,n in enumerate(doc['nodes'])if n.get('mesh')==match[0]];onodes=[i for i,n in enumerate(od['nodes'])if n.get('mesh')==mi]
        require(len(nodes)==len(onodes)==1 and doc['nodes'][nodes[0]].get('name')==od['nodes'][onodes[0]].get('name'),'lamp_node_binding')
        require(doc['nodes'][nodes[0]].get('extras')==od['nodes'][onodes[0]].get('extras'),'lamp_native_binding')
        pp=doc['meshes'][match[0]]['primitives'][match[1]];require(doc['materials'][pp['material']]['extras'].get('sourceShader')=='CarLight','lamp_shader')
        selector=[tuple(v)for v in g['source_arrays']['texcoord1']];require(len(selector)==len(native[0]),'selector_vertex_count')
        require(match not in targets,'duplicate_lamp_target');targets[match]={'role':role,'selector':selector,'source':resource['source'],'native_model':g['native_model'],'native_geometry':g['native_geometry'],'node':nodes[0]}
    require({v['role']for v in targets.values()}=={'head','tail'},'two_exterior_lamps_required')
    def accessor(payload,kind,ct,count):
        blob.extend(b'\0'*(-len(blob)%4));offset=len(blob);blob.extend(payload);require(len(blob)<=OUTPUT_LIMIT,'output_budget');doc['bufferViews'].append({'buffer':0,'byteOffset':offset,'byteLength':len(payload)});doc['accessors'].append({'bufferView':len(doc['bufferViews'])-1,'componentType':ct,'type':kind,'count':count});return len(doc['accessors'])-1
    blob.extend(b'\0'*(-len(blob)%4));offset=len(blob);blob.extend(illumination);doc['bufferViews'].append({'buffer':0,'byteOffset':offset,'byteLength':len(illumination)});doc.setdefault('images',[]).append({'name':'Original grayscale illumination, authored UV0 contrast','mimeType':'image/png','bufferView':len(doc['bufferViews'])-1});doc.setdefault('samplers',[]).append({'wrapS':10497,'wrapT':10497});doc.setdefault('textures',[]).append({'source':len(doc['images'])-1,'sampler':len(doc['samplers'])-1});texture=len(doc['textures'])-1
    lamp_materials={}
    for role,color in [('head',[.82,.90,1,1]),('tail',[.75,.01,.018,1])]:
        lamp_materials[role]=len(doc['materials']);doc['materials'].append({'name':'Racer authored daytime '+role+' lens','alphaMode':'OPAQUE','doubleSided':True,'pbrMetallicRoughness':{'baseColorFactor':color,'baseColorTexture':{'index':texture,'texCoord':0},'metallicFactor':0,'roughnessFactor':.16},'extensions':{'KHR_materials_clearcoat':{'clearcoatFactor':.8,'clearcoatRoughnessFactor':.12}},'extras':{'authority':'Racer-authored category palette, ALL head IDs coolwhite / ALL rear IDs red; NOT native ID-to-color table. Original grayscale illumination used as authored UV0 basecolor contrast, NOT recovered shader formula. No emission/activation; source normal map unapplied.'}})
    paint={}
    for name in PAINT:
        ids=[i for i,m in enumerate(before['materials'])if m.get('name')==name and m.get('extras',{}).get('sourceShader')=='CarPaintCustomizable'];require(len(ids)==1,'paint_family_identity');old=ids[0];clone=copy.deepcopy(before['materials'][old]);clone['pbrMetallicRoughness'].update(roughnessFactor=.24,metallicFactor=.25);clone.setdefault('extensions',{})['KHR_materials_clearcoat']={'clearcoatFactor':.9,'clearcoatRoughnessFactor':.1};clone.setdefault('extras',{})['racerAuthoredFinish']={'reason':'Preserve current exact-source exterior finish after derivative mesh hash changes','roughness':.24,'metallic':.25,'clearcoat':.9}
        if authored_paint is not None:
            require(before['materials'][old].get('alphaMode')=='OPAQUE' and before['materials'][old].get('extras',{}).get('sourceDrawBucket')==0, 'paint_bucket_or_alpha_identity')
            require(before['materials'][old]['pbrMetallicRoughness']=={'baseColorFactor':[.8,.8,.8,1.0],'metallicFactor':0.0,'roughnessFactor':.7}, 'paint_preview_factor_identity')
            clone['pbrMetallicRoughness'].update(baseColorFactor=[*PALETTES[authored_paint],1],metallicFactor=0)
            clone['extras']['racerAuthoredPaint']={'authority':'Explicit Racer linear-RGB dielectric paint palette, NOT native palette or recovered CarPaintCustomizable formula',
                'palette':authored_paint,'linear_base_color':list(PALETTES[authored_paint]),'metallic':0,'source_material':old,
                'original_preview_material':copy.deepcopy(before['materials'][old])}
            clone['extras']['racerAuthoredFinish']={'reason':'Optional authored dielectric paint palette after derivative mesh hash changes','roughness':.24,'metallic':0,'clearcoat':.9}
        paint[old]=len(doc['materials']);doc['materials'].append(clone)
    # Exact source outer covers occlude the inner lamps when the old preview makes them opaque.
    # This low-alpha treatment is authored, not a recovered native bucket/opacity formula.
    lens={}
    for name in (PREFIX+'headlight0_lod_0.xrsc/shader31',PREFIX+'taillight0_lod_0.xrsc/shader31'):
        ids=[i for i,m in enumerate(before['materials'])if m.get('name')==name and m.get('extras',{}).get('sourceShader')=='bumpedglass' and m.get('extras',{}).get('sourceDrawBucket')==3];require(len(ids)==1,'outer_lens_identity');old=ids[0];tail=name==PREFIX+'taillight0_lod_0.xrsc/shader31';alpha=.55 if tail else .08;clone=copy.deepcopy(before['materials'][old]);clone['alphaMode']='BLEND';clone['pbrMetallicRoughness'].update(baseColorFactor=[.75,.01,.018,alpha] if tail else [.8,.9,1,alpha],roughnessFactor=.16 if tail else .08,metallicFactor=0);clone.setdefault('extensions',{})['KHR_materials_clearcoat']={'clearcoatFactor':.2 if tail else .8,'clearcoatRoughnessFactor':.1};clone.setdefault('extras',{})['racerAuthoredLens']={'authority':'Exact source outer-cover geometry, Racer-authored lowalpha visibility recipe; native opacity/bucket formula unknown','alpha':alpha,'palette':'Racer-authored rear red plastic / head neutral clear, NOT native lookup','source_material':old};lens[old]=len(doc['materials']);doc['materials'].append(clone)
    rims={}
    if authored_rims:
        name='shared/resources/rims/whl_stk_nsn_350z_06/shader0'
        ids=[i for i,m in enumerate(before['materials'])if m.get('name')==name and m.get('extras',{}).get('sourceShader')=='RimMain' and m['extras'].get('sourceDrawBucket')==0]
        require(len(ids)==1,'rim_family_identity');old=ids[0]
        uses=[n for n in before['nodes']if 'mesh'in n and any(p.get('material')==old for p in before['meshes'][n['mesh']]['primitives'])]
        require({n.get('name')for n in uses}=={'shared/resources/rims/whl_stk_nsn_350z_06@axl_'+str(i)+'/model0'for i in range(4)}and len(uses)==4 and all(n.get('extras',{}).get('nativeModel')==0 for n in uses),'rim_mount_qualification')
        clone=copy.deepcopy(before['materials'][old]);clone['pbrMetallicRoughness'].update(baseColorFactor=[.45,.45,.45,1],roughnessFactor=.26,metallicFactor=.9)
        clone.setdefault('extras',{})['racerAuthoredAluminum']={'authority':'Explicit Racer aluminum finish; native palette, UV1 material selectors and BRDF unknown','original_material':copy.deepcopy(before['materials'][old])}
        rims[old]=len(doc['materials']);doc['materials'].append(clone)
    trim={};trim_proof=[]
    if authored_trim:
        bindings=[(38,'bumper_r0_lod_0.xrsc/shader28','CarLight',0,
                   ['bumper_r0_lod_0.xrsc@bumr_bone/model1','bumper_r0_lod_0.xrsc@bumr_bone/model2'],'neutral lens'),
                  (50,'door_l0_lod_0.xrsc/shader6','BrushedMetal',0,['door_l0_lod_0.xrsc@door_l_scissor_anim/model0'],'metal'),
                  (67,'door_r0_lod_0.xrsc/shader6','BrushedMetal',0,['door_r0_lod_0.xrsc@door_r_scissor_anim/model0'],'metal'),
                  (90,'headlight0_lod_0.xrsc/shader25','Chrome',1,['headlight0_lod_0.xrsc@headlights/model3'],'metal')]
        for old,name,shader,bucket,node_names,role in bindings:
            material=before['materials'][old]
            require(material.get('name')==PREFIX+name and material.get('extras',{}).get('sourceShader')==shader and material['extras'].get('sourceDrawBucket')==bucket and material.get('alphaMode')=='OPAQUE','trim_material_identity')
            uses=[(i,n,pi,p) for i,n in enumerate(before['nodes'])if 'mesh'in n for pi,p in enumerate(before['meshes'][n['mesh']]['primitives'])if p.get('material')==old]
            require(sorted(n['name']for _,n,_,_ in uses)==sorted(PREFIX+n for n in node_names),'trim_node_identity')
            proof=[]
            for ni,node,pi,primitive in uses:
                onodes=[n for n in od['nodes']if n.get('name')==node['name']]
                require(len(onodes)==1,'trim_original_node_identity')
                native=od['meshes'][onodes[0]['mesh']]['primitives'][pi]
                require(od['materials'][native['material']].get('name')==material['name'],'trim_original_material_identity')
                pos,uv,indices=data_arrays(od,ob,native)
                flipped=[v for i in range(0,len(indices),3)for v in (indices[i],indices[i+2],indices[i+1])]
                require(data_arrays(before,prefix,primitive)==([(x,y,-z)for x,y,z in pos],uv,flipped),'trim_geometry_uv_identity')
                native_normals=rows(od,ob,native['attributes']['NORMAL']);prepared_normals=rows(before,prefix,primitive['attributes']['NORMAL'])
                require(prepared_normals==[(x,y,-z)for x,y,z in native_normals],'trim_normal_identity')
                proof.append({'prepared_node':ni,'prepared_mesh':node['mesh'],'prepared_primitive':pi,'original_mesh':onodes[0]['mesh'],'original_primitive':pi,
                    'vertices':len(pos),'triangles':len(indices)//3,'position_uv0_indices':'Exact source positions Z-reflected, UV0 unchanged, triangle winding reversed','normals':'Exact source normals Z-reflected; no smoothing',
                    'source_uv0_sha256':sha(b''.join(struct.pack('<2f',*v)for v in uv))})
            clone=copy.deepcopy(material)
            clone['pbrMetallicRoughness'].update(baseColorFactor=[.45,.45,.45,1]if role=='metal'else[.12,.14,.16,1],metallicFactor=.95 if role=='metal'else 0,roughnessFactor=.22 if role=='metal'else .24)
            if role!='metal':clone.setdefault('extensions',{})['KHR_materials_clearcoat']={'clearcoatFactor':.7,'clearcoatRoughnessFactor':.12}
            clone.setdefault('extras',{})['racerAuthoredTrim']={'authority':'Explicit Racer '+role+' finish; native palette, BRDF and lamp activation unknown','original_preview_material':copy.deepcopy(material),'geometry_uv_normal_proof':proof}
            trim[old]=len(doc['materials']);doc['materials'].append(clone);trim_proof.append({'source_material':old,'derived_material':trim[old],'role':role,'bindings':proof})
    for mi,mesh in enumerate(doc['meshes']):
        output=[]
        for pi,p in enumerate(mesh['primitives']):
            if (mi,pi)not in targets:
                p=copy.deepcopy(p)
                if p['material']in paint:p['material']=paint[p['material']]
                elif p['material']in lens:p['material']=lens[p['material']]
                elif p['material']in rims:p['material']=rims[p['material']]
                elif p['material']in trim:p['material']=trim[p['material']]
                output.append(p);continue
            target=targets[mi,pi];selector=target['selector'];stream=accessor(b''.join(struct.pack('<2f',*v)for v in selector),'VEC2',5126,len(selector));indices=[x[0]for x in rows(doc,blob,p['indices'])];groups=partition(indices,selector);partitions=[]
            for ident,ts in sorted(groups.items()):
                clone=copy.deepcopy(p);clone['attributes']['_RACER_NATIVE_LAMP_DATA']=stream;values=[indices[t*3+k]for t in ts for k in range(3)];clone['indices']=accessor(struct.pack('<'+'I'*len(values),*values),'SCALAR',5125,len(values));clone['material']=lamp_materials[target['role']];clone.setdefault('extras',{})['racerAuthoredLamp']={'native_selector_id':ident,'native_selector_aux':1,'source_prepared_mesh':mi,'source_prepared_primitive':pi,'source_triangle_indices':ts,'policy':'Category palette authored; original ID preserved as data, not palette interpretation.'};partitions.append({'id':ident,'triangles':ts,'new_primitive':len(output)});output.append(clone)
            changes.append({'prepared_mesh':mi,'prepared_primitive':pi,'node':target['node'],'role':target['role'],'native_source':target['source'],'native_model':target['native_model'],'native_geometry':target['native_geometry'],'partitions':partitions})
        mesh['primitives']=output
    doc['extensionsUsed']=sorted(set(doc.get('extensionsUsed',[]))|{'KHR_materials_clearcoat'});policy={'authority':'Isolated Racer-authored daytime lamp material preview; native ID palette/FXC/activation unknown','input_pins':PINS,'source_buffer_prefix_sha256':sha(prefix),'source_buffer_prefix_bytes':len(prefix),'partitions':changes,'paint_material_clones':paint,'lens_material_clones':lens,'lens_policy':'Only exact source bumpedglass outer covers: authored neutral head alpha.08 and rear red plastic alpha.55/coat.2; native opacity/palette formula unknown','unapplied_normal_png_sha256':NORMAL_PNG_SHA,'source_identity':PINS['original']}
    if authored_trim:policy['authored_trim']={'material_clones':trim,'proof':trim_proof,'authority':'Authored exact qualified metal handles/headlamp Chrome and neutral rear bumper lens; NOT native color recovery'}
    if authored_rims:policy['authored_rim_material_clones']=rims
    if authored_paint is not None:policy['authored_paint']={'palette':authored_paint,'linear_base_color':list(PALETTES[authored_paint]),'metallic':0,'authority':'Authored dielectric color beneath preserved clearcoat; native palette/BRDF unknown','exact_material_names':list(PAINT)}
    doc.setdefault('extras',{})['racerAuthoredLampPreview']=policy;doc['buffers'][0]['byteLength']=len(blob)
    require(doc['nodes']==before['nodes'] and doc['materials'][:141]==before['materials'] and bytes(blob[:len(prefix)])==prefix,'source_prefix_or_bindings_changed');result=pack(doc,blob);require(len(result)<=OUTPUT_LIMIT,'output_budget');digest=sha(result)
    replacements={'id':'id '+json.dumps('vehicle-'+digest),'name':'name '+json.dumps('2006 Nissan 350Z Roadster'),'mesh':'mesh '+json.dumps(digest+'.glb'),'sha256':'sha256 '+digest};lines=descriptor.decode().splitlines();new='\n'.join(replacements.get(line.split(' ',1)[0],line)for line in lines)+'\n'
    manifest={**policy,'mesh_sha256':digest,'bytes':len(result),'descriptor_sha256':sha(new.encode()),'original_descriptor_sha256':PINS['descriptor'],'geometry_policy':'No original positions/normals/UV0/triangles/node bindings or descriptor dimensions modified. Original lamp index streams retained in buffer prefix; partitions reference same vertex arrays.'}
    return {digest+'.glb':result,digest+'.vehicle':new.encode(),'catalog.racer':('RACER_VEHICLES 1\n1\n'+json.dumps(digest+'.vehicle')+'\n').encode(),'manifest.json':(json.dumps(manifest,indent=2,sort_keys=True)+'\n').encode()}

def publish(output,files):
    output=platform_path(output);require(not any(p.is_symlink()for p in (output,*output.parents)),'symlink_refused');require(sum(len(v)for v in files.values())<=32*1024**2,'output_directory_budget')
    for name,data in files.items():
        path=output/name
        if path.exists()or path.is_symlink():require(regular_bytes(path,len(data))==data,'output_conflict')
    output.mkdir(parents=True,exist_ok=True)
    for name,data in files.items():immutable(output/name,data)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in PINS:p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--authored-trim',action='store_true',help='Optional exact source-qualified metal handles/headlamp Chrome and neutral rear bumper lens')
    p.add_argument('--authored-paint',choices=sorted(PALETTES),help='Optional explicit linear-RGB dielectric palette for exact eight CarPaintCustomizable families')
    p.add_argument('--authored-rims',action='store_true',help='Optional qualified RimMain aluminum finish; badge/rubber preserved')
    p.add_argument('--output',type=Path,required=True);a=p.parse_args();files=derive(*(pinned(getattr(a,key),key)for key in PINS),authored_rims=a.authored_rims,authored_paint=a.authored_paint,authored_trim=a.authored_trim);publish(a.output,files);print(json.dumps({'catalog':str(platform_path(a.output)/'catalog.racer'),'mesh':[k for k in files if k.endswith('.glb')][0],'authority':'Isolated authored preview; no native color lookup or visual success claim'}))
if __name__=='__main__':main()
