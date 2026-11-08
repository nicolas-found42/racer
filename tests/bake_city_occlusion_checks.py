#!/usr/bin/env python3
import copy
import hashlib
import io
import json
import math
from pathlib import Path
import struct
import sys
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import bake_city_occlusion as ao
from prepare_gt4_vehicle import pack,unpack
from prepare_city_blocks import accessor,qualify
from PIL import Image


def require(ok,message):
    if not ok:raise AssertionError(message)


def reject(fn,code):
    try:fn()
    except(ValueError,OverflowError)as e:
        require(code in str(e),str(e));return
    raise AssertionError('accepted '+code)


def box(center=(0,0,0),extent=1):
    c=[(center[0]+x*extent,center[1]+y*extent,center[2]+z*extent)for x,y,z in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]]
    return [[c[f[i]]for i in tri]for f in [(0,3,2,1),(4,5,6,7),(0,4,7,3),(1,2,6,5),(3,7,6,2),(0,1,5,4)]for tri in [(0,1,2),(0,2,3)]]


def fixture():
    binary=bytearray();d={'asset':{'version':'2.0'},'buffers':[{}],'bufferViews':[],'accessors':[],'nodes':[{'mesh':0}],'meshes':[{'primitives':[]}],'scenes':[{'nodes':[0]}],'scene':0,'materials':[{'pbrMetallicRoughness':{'baseColorTexture':{'index':0}}}],'textures':[{'source':0}],'images':[],'extras':{'source':'untouched'}}
    def view(data):
        binary.extend(b'\0'*(-len(binary)%4));at=len(binary);binary.extend(data);d['bufferViews'].append({'buffer':0,'byteOffset':at,'byteLength':len(data)});return len(d['bufferViews'])-1
    def acc(rows,kind,fmt):
        vi=view(b''.join(struct.pack('<'+fmt,*r)for r in rows));d['accessors'].append({'bufferView':vi,'componentType':5126,'count':len(rows),'type':kind});return len(d['accessors'])-1
    attrs={'POSITION':acc([(0,0,0),(0,0,6),(6,0,0)],'VEC3','3f'),'NORMAL':acc([(0,1,0)]*3,'VEC3','3f'),'TEXCOORD_0':acc([(0,0),(0,1),(1,0)],'VEC2','2f'),'TEXCOORD_1':acc([(.7,.2)]*3,'VEC2','2f'),'_RACER_SOURCE_COLOR1':acc([(7,8,9,10)]*3,'VEC4','4f')}
    d['meshes'][0]['primitives']=[{'attributes':attrs,'material':0}];im=io.BytesIO();Image.new('RGBA',(1,1),(20,30,40,80)).save(im,format='PNG');d['images']=[{'bufferView':view(im.getvalue()),'mimeType':'image/png'}];d['buffers'][0]['byteLength']=len(binary);return pack(d,binary)


def main():
    plane=[((-10,0,-10),(-10,0,10),(10,0,10)),((-10,0,-10),(10,0,10),(10,0,-10))]
    require(ao.Occluders(plane).visibility((0,0,0),(0,1,0))==1,'open plane full ambient visibility')
    require(ao.Occluders(box(),ground=False).visibility((0,0,0),(0,1,0))==0,'closed box blocks all rays')
    wall=[((1,-5,-5),(1,5,-5),(1,5,5)),((1,-5,-5),(1,5,5),(1,-5,5))]
    partial=ao.Occluders(wall,ground=False).visibility((0,0,0),(0,1,0));require(0<partial<1,'near wall partly blocks hemisphere')
    far=[tuple((x+3,y,z)for x,y,z in tri)for tri in wall];require(ao.Occluders(far,ground=False).visibility((0,0,0),(0,1,0))==1,'wall beyond3m radius excluded')
    require(ao.Occluders(plane).visibility((0,1,0),(0,-1,0))<1,'analytic ground occludes downward hemisphere')
    require(ao.Occluders(plane).visibility((0,-1,0),(0,1,0))<1,'opaque ground also blocks upward rays from below')
    original=fixture();old,prefix=unpack(original);result,audit=ao.bake(original,hashlib.sha256(original).hexdigest());new,blob=unpack(result);a=json.loads(audit)
    require(bytes(blob[:len(prefix)])==bytes(prefix),'entire original BIN prefix byte preserved')
    for key in ['nodes','meshes','accessors','bufferViews','scenes']:
        require(new[key][:len(old[key])]==old[key],'historical '+key+' unchanged')
    for key in ['images','materials','textures']:require(new[key]==old[key],'source '+key+' unchanged')
    require(new['extras']['source']=='untouched','original metadata retained')
    require(new['scene']==len(old['scenes']),'new default scene leaves historical scene unreachable')
    runtime=new['meshes'][-1]['primitives'][0];require(set(runtime['attributes'])=={'POSITION','NORMAL','TEXCOORD_0','_RACER_OCCLUSION'},'unknown source channels not interpreted/interpolated')
    _,position_rows=accessor(new,blob,runtime['attributes']['POSITION']);positions=[struct.unpack('<3f',r)for r in position_rows];_,uv_rows=accessor(new,blob,runtime['attributes']['TEXCOORD_0']);uv=[struct.unpack('<2f',r)for r in uv_rows];_,occ=accessor(new,blob,runtime['attributes']['_RACER_OCCLUSION']);require(all(struct.unpack('<f',r)[0]==1 for r in occ),'derived open plane stays fully visible')
    for row in a['vertices']:
        w=row['barycentric'];i=row['runtime_vertex'];require(abs(sum(w)-1)<1e-10 and min(w)>=0,'barycentric map valid')
        expected=(6*w[2],0,6*w[1]);require(max(abs(x-y)for x,y in zip(positions[i],expected))<1e-6,'derived position equals independent barycentric reconstruction');require(uv[i]==(w[2],w[1]),'derived UV equals independent barycentric interpolation')
    _,idx=accessor(new,blob,runtime['indices']);indices=[struct.unpack('<I',r)[0]for r in idx]
    for at in range(0,len(indices),3):
        tri=[positions[i]for i in indices[at:at+3]]
        require(max(math.dist(tri[i],tri[j])for i,j in [(0,1),(1,2),(2,0)])<=3.000001,'all derived edges<=3m')
    reject(lambda:ao.bake(result,hashlib.sha256(result).hexdigest()),'already_baked')
    d,b=unpack(original);d['scenes'][0]['nodes']=[0,0];bad=pack(d,b);reject(lambda:ao.bake(bad,hashlib.sha256(bad).hexdigest()),'node_cycle_or_shared')
    d,b=unpack(original);d['nodes'][0]['translation']=[0,1,0];bad=pack(d,b)
    reject(lambda:ao.bake(bad,hashlib.sha256(bad).hexdigest()),'ground_anchor_required')
    d,b=unpack(original);b.extend(b'\0'*(-len(b)%4));at=len(b);b.extend(bytes([0,1,2])*6001)
    d['bufferViews'].append({'buffer':0,'byteOffset':at,'byteLength':18003});d['accessors'].append({'bufferView':len(d['bufferViews'])-1,'componentType':5121,'type':'SCALAR','count':18003})
    d['meshes'][0]['primitives'][0]['indices']=len(d['accessors'])-1;d['buffers'][0]['byteLength']=len(b);bad=pack(d,b)
    with patch.object(ao,'unit',side_effect=AssertionError('oversized source must reject before face reconstruction')):
        reject(lambda:ao.bake(bad,hashlib.sha256(bad).hexdigest()),'occluder_triangle_budget')
    old_index_limit=ao.INDEX_LIMIT
    try:
        ao.INDEX_LIMIT=9
        reject(lambda:ao.bake(original,hashlib.sha256(original).hexdigest()),'derived_index_budget')
    finally:ao.INDEX_LIMIT=old_index_limit
    for kind in ['degenerate','nonfinite']:
        d,b=unpack(original);v=d['bufferViews'][d['accessors'][0]['bufferView']];off=v['byteOffset']
        if kind=='degenerate':b[off:off+36]=b'\0'*36
        else:struct.pack_into('<f',b,off,float('nan'))
        bad=pack(d,b);reject(lambda:ao.bake(bad,hashlib.sha256(bad).hexdigest()),'degenerate_normal'if kind=='degenerate'else'nonfinite_attribute')
    print('PASS: open/closed/partial/radius/ground visibility,<=3m tessellation,barycentric position+UV audit,historicalBIN/PNG/material preservation,repeated/nonfinite/degenerate rejection')


if __name__=='__main__':main()
