#!/usr/bin/env python3
"""Bake an explicitly authored 96-house layout; source runtime placement is unknown."""
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

INPUT_LIMIT = 4 * 1024**2
OUTPUT_LIMIT = 12 * 1024**2
VERTEX_LIMIT = 500000
INDEX_LIMIT = 1500000
RGBA_LIMIT = 8 * 1024**2
IDENTITY = (1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1)
FORMATS = {5120:('b',1),5121:('B',1),5122:('h',2),5123:('H',2),5125:('I',4),5126:('f',4)}
WIDTHS = {'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def multiply(a, b):
    return tuple(sum(a[k*4+i]*b[j*4+k] for k in range(4)) for j in range(4) for i in range(4))


def node_matrix(node):
    require(not any(k in node for k in ('skin','weights','extensions')), 'node_runtime_unsupported')
    if 'matrix' in node:
        require(not any(k in node for k in ('translation','rotation','scale')), 'matrix_trs_conflict')
        m = tuple(node['matrix'])
    else:
        t, q, scale = node.get('translation',[0,0,0]), node.get('rotation',[0,0,0,1]), node.get('scale',[1,1,1])
        require(len(t)==3 and len(q)==4 and scale==[1,1,1], 'rigid_transform_required')
        x,y,z,w = q
        require(abs(sum(v*v for v in q)-1)<1e-5, 'unit_quaternion_required')
        m = (1-2*(y*y+z*z),2*(x*y+z*w),2*(x*z-y*w),0,
             2*(x*y-z*w),1-2*(x*x+z*z),2*(y*z+x*w),0,
             2*(x*z+y*w),2*(y*z-x*w),1-2*(x*x+y*y),0,*t,1)
    require(len(m)==16 and all(type(v) in (float,int) and math.isfinite(v) for v in m), 'finite_transform_required')
    require(all(abs(m[i]-v)<1e-6 for i,v in [(3,0),(7,0),(11,0),(15,1)]), 'affine_transform_required')
    for i in range(3):
        for j in range(3):
            require(abs(sum(m[i*4+k]*m[j*4+k] for k in range(3))-(i==j))<1e-5, 'rigid_transform_required')
    det=m[0]*(m[5]*m[10]-m[9]*m[6])-m[4]*(m[1]*m[10]-m[9]*m[2])+m[8]*(m[1]*m[6]-m[5]*m[2])
    require(abs(det-1)<1e-5, 'proper_rotation_required')
    return m


def transform(m, row, normal=False):
    return tuple(sum(m[k*4+i]*row[k] for k in range(3))+(0 if normal else m[12+i]) for i in range(3))


def accessor(doc, blob, index):
    require(type(index) is int and 0<=index<len(doc['accessors']), 'accessor_index')
    a=doc['accessors'][index]
    require(not any(k in a for k in ('sparse','extensions')), 'accessor_unsupported')
    ct, kind=a.get('componentType'),a.get('type')
    require(ct in FORMATS and kind in WIDTHS, 'accessor_format')
    fmt, unit=FORMATS[ct];width=unit*WIDTHS[kind]
    vi=a.get('bufferView');require(type(vi) is int and 0<=vi<len(doc['bufferViews']), 'buffer_view_index')
    v=doc['bufferViews'][vi]
    require(v.get('buffer',0)==0 and 'extensions' not in v, 'buffer_view_unsupported')
    start, length, local, count=v.get('byteOffset',0),v.get('byteLength'),a.get('byteOffset',0),a.get('count')
    require(all(type(x) is int and x>=0 for x in (start,length,local,count)) and 0<count<=VERTEX_LIMIT, 'accessor_bounds')
    stride=v.get('byteStride',width)
    require(type(stride) is int and stride>=width and stride%unit==0 and local%unit==0 and start%unit==0, 'accessor_stride')
    require(start+length<=doc['buffers'][0]['byteLength'] and local+(count-1)*stride+width<=length, 'accessor_bounds')
    rows=[bytes(blob[start+local+i*stride:start+local+i*stride+width]) for i in range(count)]
    if ct==5126:
        require(all(all(math.isfinite(x) for x in struct.unpack('<'+fmt*WIDTHS[kind],r)) for r in rows), 'nonfinite_attribute')
    return {k:copy.deepcopy(a[k]) for k in ('componentType','type','normalized') if k in a},rows


def qualify(data, expected):
    require(len(data)<=INPUT_LIMIT and len(expected)==64 and sha(data)==expected, 'source_pin_or_size')
    doc,blob=unpack(data)
    require(not any(doc.get(k) for k in ('skins','animations','extensionsRequired','extensions')), 'runtime_unsupported')
    require(len(doc.get('buffers',[]))==1 and 'uri' not in doc['buffers'][0] and type(doc['buffers'][0].get('byteLength'))is int and 0<doc['buffers'][0]['byteLength']<=len(blob) and len(blob)-doc['buffers'][0]['byteLength']<=3, 'embedded_buffer_required')
    for key,limit in [('nodes',256),('meshes',256),('accessors',2048),('bufferViews',2048)]:
        require(isinstance(doc.get(key),list) and 0<len(doc[key])<=limit, 'source_structure_budget')
    require(len(doc.get('materials',[]))<=64 and len(doc.get('images',[]))<=64, 'source_material_image_budget')
    for material in doc.get('materials',[]):
        require(material.get('alphaMode','OPAQUE')=='OPAQUE', 'opaque_props_required')
    primitives=[];seen=set();source_vertices=0;source_indices=0
    source_vertex_limit=VERTEX_LIMIT//48
    def visit(index,parent,active):
        nonlocal source_vertices,source_indices
        require(type(index)is int and 0<=index<len(doc['nodes']) and index not in active and index not in seen, 'node_cycle_or_shared')
        seen.add(index);n=doc['nodes'][index];matrix=multiply(parent,node_matrix(n))
        if 'mesh' in n:
            mi=n['mesh'];require(type(mi)is int and 0<=mi<len(doc['meshes']), 'mesh_index')
            for pi,pr in enumerate(doc['meshes'][mi]['primitives']):
                require(pr.get('mode',4)==4 and not any(k in pr for k in ('targets','extensions')), 'triangles_required')
                attrs={};count=None
                position_index=pr.get('attributes',{}).get('POSITION')
                require(type(position_index)is int and 0<=position_index<len(doc['accessors']), 'positions_required')
                source_count=doc['accessors'][position_index].get('count')
                require(type(source_count)is int and 0<source_count<=source_vertex_limit-source_vertices, 'source_vertex_budget')
                source_vertices+=source_count
                for name,ai in sorted(pr['attributes'].items()):
                    spec,rows=accessor(doc,blob,ai);require(count is None or count==len(rows), 'attribute_count');count=len(rows)
                    if name in ('POSITION','NORMAL','TANGENT'):
                        tangent=name=='TANGENT';width=4 if tangent else 3
                        require(spec.get('componentType')==5126 and spec.get('type')==('VEC4'if tangent else'VEC3') and not spec.get('normalized'), 'position_normal_tangent_format')
                        values=[struct.unpack('<'+'f'*width,r)for r in rows]
                        if tangent:require(all(v[3]in(-1.,1.)for v in values),'tangent_handedness')
                        values=[(*transform(matrix,v[:3],name!='POSITION'),*v[3:])for v in values]
                        if name!='POSITION':
                            signs=[v[3:]for v in values]
                            directions=[v[:3]for v in values]
                            require(all(abs(math.hypot(*v)-1)<.01 for v in directions), 'unit_normal_required')
                            values=[(*[x/math.hypot(*v)for x in v],*sign)for v,sign in zip(directions,signs)]
                        rows=[struct.pack('<'+'f'*width,*v)for v in values]
                    attrs[name]=(spec,rows)
                require('POSITION'in attrs, 'positions_required')
                if 'indices'in pr:
                    index_accessor=pr['indices'];require(type(index_accessor)is int and 0<=index_accessor<len(doc['accessors']), 'accessor_index')
                    count_indices=doc['accessors'][index_accessor].get('count')
                    require(type(count_indices)is int and 0<count_indices<=INDEX_LIMIT-source_indices, 'source_index_budget')
                    source_indices+=count_indices
                    spec,rows=accessor(doc,blob,pr['indices']);require(spec.get('type')=='SCALAR' and spec['componentType'] in (5121,5123,5125) and not spec.get('normalized'), 'index_format')
                    indices=[struct.unpack('<'+FORMATS[spec['componentType']][0],r)[0]for r in rows]
                else:
                    require(count<=INDEX_LIMIT-source_indices,'source_index_budget');source_indices+=count
                    indices=list(range(count))
                require(len(indices)%3==0 and all(i<count for i in indices), 'triangle_indices')
                mat=pr.get('material');require(type(mat)is int and 0<=mat<len(doc['materials']), 'material_required')
                primitives.append({'attributes':attrs,'indices':indices,'material':mat,'source_node':index,'source_mesh':mi,'source_primitive':pi})
        for child in n.get('children',[]):visit(child,matrix,active|{index})
    scene=doc.get('scene',0);require(type(scene)is int and 0<=scene<len(doc.get('scenes',[])), 'scene_index')
    for root in doc['scenes'][scene]['nodes']:visit(root,IDENTITY,set())
    require(primitives and sum(len(p['attributes']['POSITION'][1])for p in primitives)<=VERTEX_LIMIT//48, 'source_vertex_budget')
    pts=[struct.unpack('<3f',r)for p in primitives for r in p['attributes']['POSITION'][1]]
    lo=[min(v[i]for v in pts)for i in range(3)];hi=[max(v[i]for v in pts)for i in range(3)]
    require(hi[0]-lo[0]<=23 and hi[2]-lo[2]<=26 and max(abs(v)for v in lo+hi)<1000, 'prop_footprint')
    return {'document':doc,'blob':blob,'primitives':primitives,'bounds':[lo,hi],'sha256':expected}


def triangle_block(points, block):
    """Convex interior rectangle contains the entire triangle, including edges."""
    x,z=block
    require(all(x+7<=p[0]<=x+93 and z+7<=p[2]<=z+93 for p in points), 'road_clearance')


def bake(prop_a, prop_b, fronts=(0,1), authored_glazing=False, extra_props=()):
    props=(prop_a,prop_b,*extra_props)
    require(2<=len(props)<=4,'prop_count')
    require(len(fronts)==len(props) and all(q in range(4)for q in fronts), 'entry_orientation')
    doc={'asset':{'version':'2.0','generator':'Racer authored city block baker'},'buffers':[{}],'bufferViews':[],'accessors':[],'images':[],'textures':[],'samplers':[],'materials':[],'meshes':[],'nodes':[],'scenes':[{'nodes':[0]}],'scene':0}
    blob=bytearray();instances=[];groups={};rgba=0;vertices=0;index_work=0
    def view(data):
        require(len(blob)+3+len(data)<=OUTPUT_LIMIT, 'output_budget')
        blob.extend(b'\0'*(-len(blob)%4));at=len(blob);blob.extend(data);doc['bufferViews'].append({'buffer':0,'byteOffset':at,'byteLength':len(data)});return len(doc['bufferViews'])-1
    offsets=[];glazing=[]
    for prop in props:
        src=prop['document'];offsets.append(len(doc['materials']));image_offset=len(doc['images']);texture_offset=len(doc['textures']);sampler_offset=len(doc['samplers'])
        for image in src.get('images',[]):
            require(image.get('mimeType')=='image/png' and 'uri'not in image and 'extensions'not in image, 'embedded_png_required')
            v=src['bufferViews'][image['bufferView']];require(v.get('buffer',0)==0, 'image_buffer');at=v.get('byteOffset',0);size=v['byteLength'];require(0<=at and 0<size<=INPUT_LIMIT and at+size<=src['buffers'][0]['byteLength'], 'image_bounds');raw=bytes(prop['blob'][at:at+size])
            with Image.open(io.BytesIO(raw))as im:
                require(im.format=='PNG'and 0<im.width<=2048 and 0<im.height<=2048, 'image_dimensions');rgba+=im.width*im.height*4;im.verify()
            require(rgba<=RGBA_LIMIT and len(doc['images'])<64, 'image_budget');entry=copy.deepcopy(image);entry['bufferView']=view(raw);doc['images'].append(entry)
        doc['samplers'].extend(copy.deepcopy(src.get('samplers',[])))
        for t in src.get('textures',[]):
            t=copy.deepcopy(t);require('extensions'not in t and type(t.get('source'))is int and 0<=t['source']<len(src.get('images',[])), 'texture_source');t['source']+=image_offset
            if 'sampler'in t:require(type(t['sampler'])is int and 0<=t['sampler']<len(src.get('samplers',[])), 'sampler_index');t['sampler']+=sampler_offset
            doc['textures'].append(t)
        def remap(value):
            if isinstance(value,dict):
                for k,v in value.items():
                    if k=='extras':continue
                    if k.endswith('Texture') and isinstance(v,dict) and 'index'in v:
                        require(type(v['index'])is int and 0<=v['index']<len(src.get('textures',[])), 'material_texture_index');v['index']+=texture_offset
                    else:remap(v)
            elif isinstance(value,list):
                for v in value:remap(v)
        for mi,m in enumerate(src['materials']):
            m=copy.deepcopy(m);remap(m)
            # Only the qualified dedicated window family. BumpSpec also covers
            # roofs/doors/frames and is not a glass selector. Original material
            # data stays in provenance; these finish values are Racer-authored.
            if authored_glazing and m.get('name')=='CityWindowUpper' and any(
                    s.get('hash')==4059966321 and s.get('texture_name')=='l_sha_window.dds'
                    for s in m.get('extras',{}).get('samplers',[])):
                m.setdefault('extras',{})['racerAuthoredGlazing']={
                    'authority':'Authored dielectric glazing finish; native shader formula unknown',
                    'original_material':copy.deepcopy(src['materials'][mi])}
                m.setdefault('pbrMetallicRoughness',{}).update(roughnessFactor=.16,metallicFactor=0)
                m.setdefault('extensions',{})['KHR_materials_clearcoat']={'clearcoatFactor':.7,'clearcoatRoughnessFactor':.12}
                glazing.append({'source_sha256':prop['sha256'],'source_material':mi,'output_material':len(doc['materials'])})
            doc['materials'].append(m)
    if glazing:doc['extensionsUsed']=['KHR_materials_clearcoat']
    for ix in range(-2,2):
        for iz in range(-2,2):
            for sx in (-1,1):
                for sz in (-1,0,1):
                    source=(ix+iz+(sx!=sz))%len(props);prop=props[source];quarter=((2 if sx<0 else 0)-fronts[source])%4
                    c,s=((1,0),(0,1),(-1,0),(0,-1))[quarter];lo,hi=prop['bounds'];cx,cz=(lo[0]+hi[0])/2,(lo[2]+hi[2])/2;tx,tz=ix*100+50+sx*24,iz*100+50+sz*27
                    matrix=(c,0,-s,0,0,1,0,0,s,0,c,0,tx-c*cx-s*cz,.16-lo[1],tz+s*cx-c*cz,1)
                    instance={'id':len(instances),'source':source,'source_sha256':prop['sha256'],'block':[ix*100,iz*100],'lot_center':[tx,tz],'quarter_turn':quarter,'matrix':matrix};instances.append(instance)
                    for pr in prop['primitives']:
                        attrs={}
                        for name,(spec,rows)in pr['attributes'].items():
                            if name in ('POSITION','NORMAL'):
                                rows=[struct.pack('<3f',*transform(matrix,struct.unpack('<3f',r),name=='NORMAL'))for r in rows]
                            elif name=='TANGENT':
                                rows=[struct.pack('<4f',*transform(matrix,struct.unpack('<4f',r)[:3],True),struct.unpack('<4f',r)[3])for r in rows]
                            attrs[name]=(spec,rows)
                        pts=[struct.unpack('<3f',r)for r in attrs['POSITION'][1]]
                        triangle_block(pts,instance['block'])
                        for i in range(0,len(pr['indices']),3):triangle_block([pts[k]for k in pr['indices'][i:i+3]],instance['block'])
                        key=(source,pr['material'],tuple((n,json.dumps(a[0],sort_keys=True))for n,a in attrs.items()))
                        if key not in groups:groups[key]={'attributes':{n:(spec,[])for n,(spec,_)in attrs.items()},'indices':[],'material':offsets[source]+pr['material'],'provenance':[]}
                        group=groups[key];base=len(group['attributes']['POSITION'][1]);vertices+=len(pts);require(vertices<=VERTEX_LIMIT, 'vertex_budget')
                        for n,(_,rows)in attrs.items():group['attributes'][n][1].extend(rows)
                        index_work+=len(pr['indices']);require(index_work<=INDEX_LIMIT, 'index_budget')
                        group['indices'].extend(base+k for k in pr['indices']);require(len(group['indices'])<=INDEX_LIMIT, 'index_budget')
                        group['provenance'].append({'instance':instance['id'],**{k:pr[k]for k in ('source_node','source_mesh','source_primitive')},'first_index':len(group['indices'])-len(pr['indices']),'index_count':len(pr['indices'])})
    primitives=[]
    for group in groups.values():
        attributes={}
        for n,(spec,rows)in group['attributes'].items():
            a={**spec,'count':len(rows),'bufferView':view(b''.join(rows))}
            if n=='POSITION':
                points=[struct.unpack('<3f',r)for r in rows]
                a['min']=[min(p[i]for p in points)for i in range(3)]
                a['max']=[max(p[i]for p in points)for i in range(3)]
            doc['accessors'].append(a);attributes[n]=len(doc['accessors'])-1
        indices=group['indices'];doc['accessors'].append({'componentType':5125,'type':'SCALAR','count':len(indices),'bufferView':view(struct.pack('<'+'I'*len(indices),*indices))})
        primitives.append({'attributes':attributes,'indices':len(doc['accessors'])-1,'material':group['material'],'mode':4,'extras':{'instances':group['provenance']}})
    doc['meshes']=[{'primitives':primitives}];doc['nodes']=[{'mesh':0,'name':'Racer authored 96-house blocks'}];doc['buffers'][0]['byteLength']=len(blob)
    manifest={'schema':1,'authority':'Racer-authored placements and rotations; native city layout, units and runtime rendering equivalence unknown','sources':[p['sha256']for p in props],'source_provenance':[copy.deepcopy(p['document'].get('extras',{}))for p in props],'normal_policy':'Source direction normalized only within1percent unit-length tolerance; then rigid rotations, no semantic color interpretation','front_quarter_turns':fronts,'instances':instances,'vertices':vertices,'draw_groups':len(groups),'decoded_rgba_bytes':rgba,'limits':{'glb_bytes':OUTPUT_LIMIT,'vertices':VERTEX_LIMIT,'rgba_bytes':RGBA_LIMIT,'images':64}}
    if authored_glazing:manifest['authored_glazing']={'matches':glazing,'policy':'Dedicated CityWindowUpper/l_sha_window only; no blanket BumpSpec change. Native reflection/lighting formula unknown.'}
    doc['extras']={'city_baker':manifest};result=pack(doc,blob);require(len(result)<=OUTPUT_LIMIT, 'output_budget');manifest['city_sha256']=sha(result);manifest['city_bytes']=len(result)
    return result,manifest


def publish(output, data, manifest):
    output=Path(output);require(not any(p.is_symlink()for p in (output,*output.parents)), 'symlink_refused')
    encoded=(json.dumps(manifest,indent=2,sort_keys=True)+'\n').encode();files=[(output/'city.glb',data),(output/'manifest.json',encoded)]
    require(not output.exists()or output.is_dir(), 'output_directory')
    # Both conflicts are checked before either output is published.
    for path,payload in files:
        if path.exists()or path.is_symlink():require(regular_bytes(path,len(payload))==payload, 'output_conflict')
    output.mkdir(parents=True,exist_ok=True)
    for path,payload in files:immutable(path,payload)


def platform_path(path):
    # macOS exposes /tmp as a system alias; reject all other symlink components.
    path=Path(path).absolute()
    if path.parts[1:2]==("tmp",):
        return Path("/tmp").resolve().joinpath(*path.parts[2:])
    return path


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for key,front in zip(('a','b','c','d'),(0,1,1,3)):
        parser.add_argument('--prop-'+key,type=Path,required=key in ('a','b'));parser.add_argument('--sha-'+key,required=key in ('a','b'))
        parser.add_argument('--front-'+key,type=int,choices=range(4),default=front,help='Source entry direction: 0=+X,1=-Z,2=-X,3=+Z; authored outward-X street placement')
    parser.add_argument('--authored-glazing',action='store_true',help='Optional explicitly authored finish on qualified dedicated window materials')
    parser.add_argument('--output',type=Path,required=True);a=parser.parse_args()
    keys=[]
    for k in ('a','b','c','d'):
        path,digest=getattr(a,'prop_'+k),getattr(a,'sha_'+k)
        if bool(path)!=bool(digest):parser.error('--prop-'+k+' and --sha-'+k+' must be supplied together')
        if path:keys.append(k)
    props=[qualify(regular_bytes(platform_path(getattr(a,'prop_'+k)),INPUT_LIMIT),getattr(a,'sha_'+k))for k in keys]
    data,manifest=bake(props[0],props[1],fronts=tuple(getattr(a,'front_'+k)for k in keys),authored_glazing=a.authored_glazing,extra_props=tuple(props[2:]));publish(platform_path(a.output),data,manifest)
    print(json.dumps({'city_sha256':manifest['city_sha256'],'bytes':len(data),'instances':len(manifest['instances']),'groups':manifest['draw_groups']}))


if __name__=='__main__':main()
