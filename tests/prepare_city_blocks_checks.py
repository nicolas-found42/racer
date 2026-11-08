#!/usr/bin/env python3
"""Independent numeric and preservation checks for the authored city baker."""
import copy
import io
import json
import math
from pathlib import Path
import struct
import sys
import tempfile
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import prepare_city_blocks as city
from prepare_gt4_vehicle import unpack,pack


def require(ok,message):
    if not ok:raise AssertionError(message)


def rejected(fn,code):
    try:fn()
    except (ValueError,OSError) as e:
        require(code in str(e),str(e));return
    raise AssertionError('accepted '+code)


def fixture():
    blob=bytearray();doc={'asset':{'version':'2.0'},'buffers':[{}],'bufferViews':[],'accessors':[],'materials':[{'pbrMetallicRoughness':{'baseColorTexture':{'index':0},'roughnessFactor':.8,'metallicFactor':0},'extras':{'native':'unchanged'}}], 'images':[],'textures':[{'source':0,'sampler':0}],'samplers':[{'wrapS':33071,'wrapT':33648}], 'nodes':[{'translation':[2,3,4],'children':[1]},{'translation':[1,0,2],'mesh':0}], 'meshes':[{'primitives':[]}],'scenes':[{'nodes':[0]}],'scene':0}
    def view(data):
        blob.extend(b'\0'*(-len(blob)%4));off=len(blob);blob.extend(data);doc['bufferViews'].append({'buffer':0,'byteOffset':off,'byteLength':len(data)});return len(doc['bufferViews'])-1
    def acc(values,kind,ct,fmt,normalized=False):
        a={'componentType':ct,'type':kind,'count':len(values),'bufferView':view(b''.join(struct.pack('<'+fmt,*r)for r in values))}
        if normalized:a['normalized']=True
        doc['accessors'].append(a);return len(doc['accessors'])-1
    attrs={'POSITION':acc([(0,0,0),(2,0,0),(0,1,2)],'VEC3',5126,'3f'),'NORMAL':acc([(1,0,0)]*3,'VEC3',5126,'3f'),'TEXCOORD_0':acc([(0,.25),(.5,0),(1,1)],'VEC2',5126,'2f'),'_RACER_SOURCE_COLOR1':acc([(1,2,3,4),(5,6,7,8),(9,10,11,12)],'VEC4',5121,'4B',True)}
    doc['meshes'][0]['primitives']=[{'attributes':attrs,'material':0,'indices':acc([(0,),(1,),(2,)],'SCALAR',5123,'H')}]
    out=io.BytesIO();Image.new('RGBA',(2,1),(20,30,40,80)).save(out,format='PNG');png=out.getvalue();doc['images']=[{'bufferView':view(png),'mimeType':'image/png','name':'exact.png'}];doc['buffers'][0]['byteLength']=len(blob)
    return pack(doc,blob),png


def main():
    data,png=fixture();prop=city.qualify(data,city.sha(data));require(prop['bounds']==[[3,3,6],[5,4,8]],'nested node translation baked once')
    baked,manifest=city.bake(prop,prop,fronts=(0,1));require(len(manifest['instances'])==96 and manifest['draw_groups']==2,'96 placements with grouped draw calls')
    four,four_manifest=city.bake(prop,prop,fronts=(0,1,1,3),extra_props=(prop,prop))
    require(len(four_manifest['sources'])==4 and all(sum(i['source']==source for i in four_manifest['instances'])==24 for source in range(4)),'four qualified source variants each occupy24 authored lots')
    four_doc,four_blob=unpack(four)
    require(len(four_doc['materials'])==4 and len(four_doc['images'])==4 and four_manifest['draw_groups']==4,'all four source render bindings retained separately')
    require({p['material']for p in four_doc['meshes'][0]['primitives']}=={0,1,2,3},'four material remaps remain in range')
    rejected(lambda:city.bake(prop,prop,fronts=(0,1),extra_props=(prop,prop)),'entry_orientation')
    rejected(lambda:city.bake(prop,prop,fronts=(0,1,0,1,0),extra_props=(prop,prop,prop)),'prop_count')
    d,b=unpack(baked);pr=d['meshes'][0]['primitives'][0];_,positions=city.accessor(d,b,pr['attributes']['POSITION']);_,normals=city.accessor(d,b,pr['attributes']['NORMAL']);_,uv=city.accessor(d,b,pr['attributes']['TEXCOORD_0']);spec,raw=city.accessor(d,b,pr['attributes']['_RACER_SOURCE_COLOR1'])
    require(all(row['source_node']==1 for primitive in d['meshes'][0]['primitives'] for row in primitive['extras']['instances']), 'provenance retains source scene node, not index accessor')
    for primitive in d['meshes'][0]['primitives']:
        ai=primitive['attributes']['POSITION'];_,rows=city.accessor(d,b,ai);values=[struct.unpack('<3f',r)for r in rows]
        require(d['accessors'][ai]['min']==[min(p[i]for p in values)for i in range(3)]and d['accessors'][ai]['max']==[max(p[i]for p in values)for i in range(3)],'POSITIONbounds equal finalpackedfloat32 data')
    # First instance sourceA at(-174,-177), sourcecenter(4,7), rotated180deg.
    require(struct.unpack('<3f',positions[0])==(-173,.1599999964237213,-176),'independent quarterturn and authored ground anchor')
    require(struct.unpack('<3f',normals[0])==(-1,0,0),'unit normal rotated without translation')
    require(uv[:3]==[struct.pack('<2f',*v)for v in [(0,.25),(.5,0),(1,1)]],'UV bytes preserved')
    require(spec['normalized']and raw[:3]==[bytes(v)for v in [(1,2,3,4),(5,6,7,8),(9,10,11,12)]],'raw color bytes and normalized metadata preserved')
    for image in d['images']:
        v=d['bufferViews'][image['bufferView']];require(bytes(b[v['byteOffset']:v['byteOffset']+v['byteLength']])==png,'embedded PNG exact preservation')
    require(d['samplers']==[{'wrapS':33071,'wrapT':33648}]*2,'sampler preservation')
    require(d['materials'][1]['pbrMetallicRoughness']['baseColorTexture']['index']==1,'material texture remapped per source')
    windows,window_blob=unpack(data)
    windows['materials'][0].update(name='CityWindowUpper',extras={'samplers':[{'hash':4059966321,'texture_name':'l_sha_window.dds'}]})
    window_data=pack(windows,window_blob);window_prop=city.qualify(window_data,city.sha(window_data))
    ordinary,ordinary_manifest=city.bake(window_prop,prop);finished,finished_manifest=city.bake(window_prop,prop,authored_glazing=True)
    ordinary_doc,ordinary_bin=unpack(ordinary);finished_doc,finished_bin=unpack(finished)
    require(ordinary_bin==finished_bin and ordinary_doc['meshes']==finished_doc['meshes'],'window finish changes no geometry, UV or encoded image bytes')
    require(len(finished_manifest['authored_glazing']['matches'])==1 and finished_doc['materials'][1]==ordinary_doc['materials'][1],'only exact dedicated window material changes')
    require(finished_doc['materials'][0]['extras']['racerAuthoredGlazing']['original_material']==windows['materials'][0],'exact source material retained separately from remapped render material')
    require(finished_doc['materials'][0]['pbrMetallicRoughness']['roughnessFactor']==.16 and finished_doc['materials'][0]['extensions']['KHR_materials_clearcoat']['clearcoatFactor']==.7,'explicit authored dielectric finish')
    windows['materials'][0]['name']='CityBumpSpec';mixed_data=pack(windows,window_blob);mixed_prop=city.qualify(mixed_data,city.sha(mixed_data));_,mixed_manifest=city.bake(mixed_prop,prop,authored_glazing=True)
    require(not mixed_manifest['authored_glazing']['matches'],'mixed frame/roof family is not glass')
    metadata_doc,metadata_blob=unpack(data)
    metadata_doc['materials'][0]['extras']['originalTexture']={'index':0}
    metadata_data=pack(metadata_doc,metadata_blob);metadata_prop=city.qualify(metadata_data,city.sha(metadata_data))
    metadata_out,_=city.bake(metadata_prop,metadata_prop);metadata_result,_=unpack(metadata_out)
    require(all(m['extras']==metadata_doc['materials'][0]['extras'] for m in metadata_result['materials']), 'source texture provenance is not render texture info')
    repeated,repeat_blob=unpack(data);repeated['meshes'][0]['primitives']*=4;repeated_data=pack(repeated,repeat_blob)
    old_indices=city.INDEX_LIMIT
    try:
        city.INDEX_LIMIT=8
        rejected(lambda:city.qualify(repeated_data,city.sha(repeated_data)),'source_index_budget')
    finally:city.INDEX_LIMIT=old_indices
    # Individually legal points in different blocks must not bridge the road.
    rejected(lambda:city.triangle_block([(90,0,20),(110,0,20),(90,0,21)],(0,0)),'road_clearance')
    city.triangle_block([(7,0,7),(93,0,7),(7,0,93)],(0,0))
    rejected(lambda:city.triangle_block([(6.999,0,7),(20,0,7),(20,0,20)],(0,0)),'road_clearance')
    rejected(lambda:city.qualify(data,'0'*64),'source_pin_or_size')
    rotated,bb=unpack(data);rotated['nodes'][0]['rotation']=[0,math.sqrt(.5),0,math.sqrt(.5)];rr=pack(rotated,bb);r=city.qualify(rr,city.sha(rr));normal=struct.unpack('<3f',r['primitives'][0]['attributes']['NORMAL'][1][0]);require(abs(normal[0])<1e-6 and normal[1]==0 and abs(normal[2]+1)<1e-6,'nested source rotation independently preserves normal direction')
    tangent=struct.pack('<4f',0,0,1,-1)*3;bb.extend(b'\0'*(-len(bb)%4));offset=len(bb);bb.extend(tangent)
    rotated['bufferViews'].append({'buffer':0,'byteOffset':offset,'byteLength':len(tangent)});rotated['accessors'].append({'bufferView':len(rotated['bufferViews'])-1,'componentType':5126,'type':'VEC4','count':3})
    rotated['meshes'][0]['primitives'][0]['attributes']['TANGENT']=len(rotated['accessors'])-1;rotated['buffers'][0]['byteLength']=len(bb)
    tangent_data=pack(rotated,bb);tangent_prop=city.qualify(tangent_data,city.sha(tangent_data));source_tangent=struct.unpack('<4f',tangent_prop['primitives'][0]['attributes']['TANGENT'][1][0])
    require(abs(source_tangent[0]-1)<1e-6 and abs(source_tangent[2])<1e-6 and source_tangent[3]==-1,'source tangent rotates with direction and preserves handedness')
    tangent_out,_=city.bake(tangent_prop,tangent_prop);td,tb=unpack(tangent_out);_,tangent_rows=city.accessor(td,tb,td['meshes'][0]['primitives'][0]['attributes']['TANGENT']);instance_tangent=struct.unpack('<4f',tangent_rows[0])
    require(abs(instance_tangent[0]+1)<1e-6 and abs(instance_tangent[2])<1e-6 and instance_tangent[3]==-1,'instance quarterturn rotates tangent while preserving handedness')
    invalid,blob=unpack(data);invalid['buffers'][0]['byteLength']=1;bad=pack(invalid,blob);rejected(lambda:city.qualify(bad,city.sha(bad)),'embedded_buffer_required')
    invalid,blob=unpack(data);invalid['nodes'][1]['scale']=[2,1,1];bad=pack(invalid,blob);rejected(lambda:city.qualify(bad,city.sha(bad)),'rigid_transform_required')
    invalid,blob=unpack(data);invalid['materials'][0]['alphaMode']='BLEND';bad=pack(invalid,blob);rejected(lambda:city.qualify(bad,city.sha(bad)),'opaque_props_required')
    invalid,blob=unpack(data);invalid['nodes'][1]['children']=[0];bad=pack(invalid,blob);rejected(lambda:city.qualify(bad,city.sha(bad)),'node_cycle_or_shared')
    wide=copy.deepcopy(prop);wide['bounds'][1][0]=30;wide_data,wide_blob=unpack(data);a=wide_data['accessors'][0];v=wide_data['bufferViews'][a['bufferView']];struct.pack_into('<f',wide_blob,v['byteOffset']+12,30);bad=pack(wide_data,wide_blob);rejected(lambda:city.qualify(bad,city.sha(bad)),'prop_footprint')
    old=city.OUTPUT_LIMIT
    try:
        city.OUTPUT_LIMIT=64;rejected(lambda:city.bake(prop,prop),'output_budget')
    finally:city.OUTPUT_LIMIT=old
    old=city.RGBA_LIMIT
    try:
        city.RGBA_LIMIT=1;rejected(lambda:city.bake(prop,prop),'image_budget')
    finally:city.RGBA_LIMIT=old
    with tempfile.TemporaryDirectory(prefix='racer-city-check-')as tmp:
        p=Path(tmp).resolve();city.publish(p/'out',baked,manifest);city.publish(p/'out',baked,manifest)
        (p/'out/manifest.json').write_text('conflict');rejected(lambda:city.publish(p/'out',baked,manifest),'output_conflict');require((p/'out/city.glb').read_bytes()==baked,'conflict does not alter city')
        (p/'out/city.glb').unlink();rejected(lambda:city.publish(p/'out',baked,manifest),'output_conflict');require(not(p/'out/city.glb').exists(),'preflight both outputs before writing missing city')
        (p/'linked').symlink_to(p/'out',target_is_directory=True);rejected(lambda:city.publish(p/'linked',baked,manifest),'symlink_refused')
        (p/'out/manifest.json').unlink();(p/'out/manifest.json').symlink_to(p/'target');rejected(lambda:city.publish(p/'out',baked,manifest),'symlink_refused')
    print('PASS: nested rigid transforms,96 lots, raw attributes/PNG/sampler preservation, grouped materials, road triangle clearance, conflict/idempotence/symlink boundaries')


if __name__=='__main__':main()
