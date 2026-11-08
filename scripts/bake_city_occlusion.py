#!/usr/bin/env python3
"""Authored bounded ambient visibility, not recovered native game occlusion."""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import struct
from install_cars import regular_bytes, immutable
from prepare_city_blocks import qualify, platform_path
from prepare_gt4_vehicle import pack

VERTEX_LIMIT=5000
SOURCE_TRIANGLE_LIMIT=6000
INDEX_LIMIT=150000
OUTPUT_LIMIT=4*1024**2
RAYS=16
RADIUS=3.0
BIAS=.03
EDGE=3.0


def require(ok,reason):
    if not ok:raise ValueError(reason)


def add(a,b):return tuple(x+y for x,y in zip(a,b))
def sub(a,b):return tuple(x-y for x,y in zip(a,b))
def scale(a,s):return tuple(x*s for x in a)
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def cross(a,b):return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def unit(a):
    length=math.hypot(*a);require(math.isfinite(length)and length>1e-10,'degenerate_normal');return scale(a,1/length)


def hemisphere(normal):
    n=unit(normal);t=unit(cross((0,1,0)if abs(n[1])<.9 else(1,0,0),n));b=cross(n,t);rays=[]
    for i in range(RAYS):
        bits=i;v=0;den=2
        while bits:v+=(bits&1)/den;bits>>=1;den*=2
        r=math.sqrt((i+.5)/RAYS);phi=2*math.pi*v
        rays.append(add(add(scale(t,r*math.cos(phi)),scale(b,r*math.sin(phi))),scale(n,math.sqrt(1-r*r))))
    return rays


class Occluders:
    def __init__(self,triangles,ground=True):
        require(0<len(triangles)<=SOURCE_TRIANGLE_LIMIT,'occluder_triangle_budget');self.triangles=triangles;self.ground=ground;self.tests=0;self.visits=0
        def build(indices):
            lo=tuple(min(triangles[i][j][k]for i in indices for j in range(3))for k in range(3));hi=tuple(max(triangles[i][j][k]for i in indices for j in range(3))for k in range(3))
            if len(indices)<=8:return(lo,hi,indices,None)
            axis=max(range(3),key=lambda k:hi[k]-lo[k]);indices=sorted(indices,key=lambda i:sum(v[axis]for v in triangles[i]));half=len(indices)//2
            return(lo,hi,build(indices[:half]),build(indices[half:]))
        self.root=build(list(range(len(triangles))))

    def blocked(self,origin,direction):
        if self.ground and abs(direction[1])>1e-10:
            distance=-origin[1]/direction[1]
            if 1e-6<distance<=RADIUS:return True
        def box(lo,hi):
            near,far=0.0,RADIUS
            for k in range(3):
                if abs(direction[k])<1e-12:
                    if not lo[k]-1e-7<=origin[k]<=hi[k]+1e-7:return False
                else:
                    a,b=(lo[k]-origin[k])/direction[k],(hi[k]-origin[k])/direction[k]
                    near=max(near,min(a,b));far=min(far,max(a,b))
                    if far<near:return False
            return True
        def hit(triangle):
            self.tests+=1;require(self.tests<=4000000,'ray_triangle_work_budget')
            a,b,c=triangle;e1,e2=sub(b,a),sub(c,a);p=cross(direction,e2);det=dot(e1,p)
            if abs(det)<1e-10:return False
            inv=1/det;s=sub(origin,a);u=dot(s,p)*inv
            if u<0 or u>1:return False
            q=cross(s,e1);v=dot(direction,q)*inv
            if v<0 or u+v>1:return False
            distance=dot(e2,q)*inv
            return 1e-6<distance<=RADIUS
        stack=[self.root]
        while stack:
            self.visits+=1;require(self.visits<=8000000,'ray_node_work_budget')
            lo,hi,left,right=stack.pop()
            if not box(lo,hi):continue
            if right is None:
                if any(hit(self.triangles[i])for i in left):return True
            else:stack.extend((left,right))
        return False

    def visibility(self,point,normal):
        origin=add(point,scale(unit(normal),BIAS))
        return sum(not self.blocked(origin,d)for d in hemisphere(normal))/RAYS


def subdivide(points):
    """Return barycentric triangles using deterministic longest-edge bisection."""
    queue=[((1.,0.,0.),(0.,1.,0.),(0.,0.,1.))];out=[]
    def position(w):return tuple(sum(w[j]*points[j][k]for j in range(3))for k in range(3))
    while queue:
        tri=queue.pop();p=[position(w)for w in tri];edges=[(dot(sub(p[i],p[j]),sub(p[i],p[j])),i,j)for i,j in [(0,1),(1,2),(2,0)]];length,i,j=max(edges)
        if length<=EDGE*EDGE+1e-9:out.append(tri)
        else:
            k=3-i-j;mid=scale(add(tri[i],tri[j]),.5);queue.extend(((tri[i],mid,tri[k]),(mid,tri[j],tri[k])))
        require(len(queue)+len(out)<=10000,'tessellation_work_budget')
    return out


def bake(data,expected):
    prop=qualify(data,expected);doc=copy.deepcopy(prop['document']);blob=bytearray(prop['blob']);original_prefix=bytes(blob)
    require('racerAuthoredAmbientVisibility'not in doc.get('extras',{}),'already_baked')
    require(abs(prop['bounds'][0][1])<=1e-4,'ground_anchor_required')
    require(sum(len(p['indices'])//3 for p in prop['primitives'])<=SOURCE_TRIANGLE_LIMIT,'occluder_triangle_budget')
    triangles=[];sources=[]
    for pi,primitive in enumerate(prop['primitives']):
        attrs=primitive['attributes'];positions=[struct.unpack('<3f',r)for r in attrs['POSITION'][1]];normals=[struct.unpack('<3f',r)for r in attrs['NORMAL'][1]]if'NORMAL'in attrs else None
        if'TEXCOORD_0'in attrs:
            spec,raw=attrs['TEXCOORD_0'];require(spec.get('componentType')==5126 and spec.get('type')=='VEC2'and not spec.get('normalized'),'uv0_float2_required');uv=[struct.unpack('<2f',r)for r in raw]
        else:uv=None
        for ti in range(0,len(primitive['indices']),3):
            ids=primitive['indices'][ti:ti+3];points=[positions[i]for i in ids];face=unit(cross(sub(points[1],points[0]),sub(points[2],points[0])))
            require(all(all(math.isfinite(x)for x in p)for p in points),'nonfinite_triangle');triangles.append(points)
            sources.append({'primitive':pi,'triangle':ti//3,'indices':ids,'points':points,'normals':[normals[i]for i in ids]if normals else[face]*3,'uv':[uv[i]for i in ids]if uv else None,'material':primitive['material']})
    occluders=Occluders(triangles);groups={};audit=[];total=0;index_work=0
    for source in sources:
        key=source['primitive'];group=groups.setdefault(key,{'vertices':[],'indices':[],'lookup':{},'material':source['material'],'has_uv':source['uv']is not None})
        for triangle in subdivide(source['points']):
            index_work+=3;require(index_work<=INDEX_LIMIT,'derived_index_budget')
            for bary in triangle:
                interpolate=lambda rows:tuple(sum(bary[j]*rows[j][k]for j in range(3))for k in range(len(rows[0])))
                point=interpolate(source['points']);normal=unit(interpolate(source['normals']));uv=interpolate(source['uv'])if source['uv']else None
                vertexkey=struct.pack('<6f',*point,*normal)+(struct.pack('<2f',*uv)if uv else b'')
                if vertexkey not in group['lookup']:
                    total+=1;require(total<=VERTEX_LIMIT,'derived_vertex_budget');index=len(group['vertices']);group['lookup'][vertexkey]=index
                    visibility=occluders.visibility(point,normal);group['vertices'].append((point,normal,uv,visibility));audit.append({'runtime_primitive':key,'runtime_vertex':index,'source_primitive':source['primitive'],'source_triangle':source['triangle'],'source_vertex_indices':source['indices'],'barycentric':bary})
                group['indices'].append(group['lookup'][vertexkey])
    def accessor(rows,kind):
        width={'SCALAR':1,'VEC2':2,'VEC3':3}[kind];blob.extend(b'\0'*(-len(blob)%4));at=len(blob)
        require(at+len(rows)*width*4<=OUTPUT_LIMIT,'output_budget')
        blob.extend(b''.join(struct.pack('<'+str(width)+'f',*r)for r in rows));doc['bufferViews'].append({'buffer':0,'byteOffset':at,'byteLength':len(blob)-at});a={'bufferView':len(doc['bufferViews'])-1,'componentType':5126,'count':len(rows),'type':kind}
        if kind=='VEC3':a['min']=[min(r[k]for r in rows)for k in range(3)];a['max']=[max(r[k]for r in rows)for k in range(3)]
        doc['accessors'].append(a);return len(doc['accessors'])-1
    runtime=[];histogram={str(i):0 for i in range(RAYS+1)}
    for group in groups.values():
        vs=group['vertices'];attrs={'POSITION':accessor([v[0]for v in vs],'VEC3'),'NORMAL':accessor([v[1]for v in vs],'VEC3'),'_RACER_OCCLUSION':accessor([(v[3],)for v in vs],'SCALAR')}
        if group['has_uv']:attrs['TEXCOORD_0']=accessor([v[2]for v in vs],'VEC2')
        for v in vs:histogram[str(round(v[3]*RAYS))]+=1
        blob.extend(b'\0'*(-len(blob)%4));at=len(blob);blob.extend(struct.pack('<'+'I'*len(group['indices']),*group['indices']));require(len(blob)<=OUTPUT_LIMIT,'output_budget');doc['bufferViews'].append({'buffer':0,'byteOffset':at,'byteLength':len(blob)-at});doc['accessors'].append({'bufferView':len(doc['bufferViews'])-1,'componentType':5125,'count':len(group['indices']),'type':'SCALAR'})
        runtime.append({'attributes':attrs,'indices':len(doc['accessors'])-1,'material':group['material'],'mode':4})
    policy={'authority':'Racer-authored offline ambient visibility, NOT recovered native AO','source_sha256':expected,'original_bin_prefix_bytes':len(original_prefix),'original_bin_prefix_sha256':hashlib.sha256(original_prefix).hexdigest(),'derived_vertices':total,'rays':RAYS,'radius_m':RADIUS,'bias_m':BIAS,'maximum_edge_m':EDGE,'ground_plane_y':0,'histogram_visible_rays':histogram,'ray_triangle_tests':occluders.tests,'ray_node_visits':occluders.visits,'historical_attributes':'Original nodes/meshes/accessors/images/materials and BIN prefix retained unchanged; new runtime contains POSITION/NORMAL/UV0 and authored AO only. Unknown raw colors/UV1/2 not interpolated or interpreted.'}
    audit_doc={'policy':policy,'vertices':audit};audit_bytes=(json.dumps(audit_doc,separators=(',',':'))+'\n').encode();policy['sidecar_sha256']=hashlib.sha256(audit_bytes).hexdigest()
    doc['meshes'].append({'name':'Derived authored ambient visibility','primitives':runtime});doc['nodes'].append({'mesh':len(doc['meshes'])-1,'name':'Derived authored ambient visibility'});doc['scenes'].append({'nodes':[len(doc['nodes'])-1]});doc['scene']=len(doc['scenes'])-1;doc['buffers'][0]['byteLength']=len(blob);doc.setdefault('extras',{})['racerAuthoredAmbientVisibility']=policy
    result=pack(doc,blob);require(len(result)<=OUTPUT_LIMIT,'output_budget');return result,audit_bytes


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--sha256',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    source=regular_bytes(platform_path(a.source),OUTPUT_LIMIT);result,audit=bake(source,a.sha256);output=platform_path(a.output)
    require(not any(x.is_symlink()for x in(output,*output.parents)),'symlink_refused');payloads=[(output/'ambient.glb',result),(output/'ambient-audit.json',audit)]
    for file,payload in payloads:
        if file.exists()or file.is_symlink():require(regular_bytes(file,len(payload))==payload,'output_conflict')
    output.mkdir(parents=True,exist_ok=True)
    for file,payload in payloads:immutable(file,payload)
    print(json.dumps({'sha256':hashlib.sha256(result).hexdigest(),'bytes':len(result),'sidecar_bytes':len(audit)}))


if __name__=='__main__':main()
