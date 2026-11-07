#!/usr/bin/env python3
"""Conservative triangle/cylinder clearance for explicit authored Furrano compression."""
import argparse,base64,hashlib,json,math,struct,time
from pathlib import Path
SOURCE_SHA='64b977dab3ab894e523406b4e6af13ee51677af366bef326370a8baba4f98b7c'
CENTERS=((-0.84,-.47,-1.09),(.84,-.47,-1.09),(-.94,-.47,1.62),(.94,-.47,1.62))
RADIUS=.34435003087437055
WIDTH=.2210953890556846

def clip_axial(poly,bound,sign):
    result=[]
    if not poly:return result
    previous=poly[-1];before=sign*previous[0]-bound
    for current in poly:
        after=sign*current[0]-bound
        if (before<=0)!=(after<=0):
            t=before/(before-after);result.append(tuple(previous[i]+t*(current[i]-previous[i]) for i in range(3)))
        if after<=0:result.append(current)
        previous,before=current,after
    return result

def projected_distance(poly):
    if not poly:return math.inf
    points=[(p[1],p[2])for p in poly];best=math.inf;crosses=[];area=0
    for a,b in zip(points,points[1:]+points[:1]):
        cross=a[0]*b[1]-a[1]*b[0];crosses.append(cross);area+=cross
        dx,dy=b[0]-a[0],b[1]-a[1];den=dx*dx+dy*dy;t=max(0,min(1,-(a[0]*dx+a[1]*dy)/den)) if den>0 else 0
        best=min(best,math.hypot(a[0]+t*dx,a[1]+t*dy))
    if abs(area)>1e-15 and (all(v>=-1e-12 for v in crosses)or all(v<=1e-12 for v in crosses)):return 0.
    return best

def triangle_clearance(triangle,center,steering,halfwidth,radius):
    c,s=math.cos(steering),math.sin(steering);local=[]
    for p in triangle:
        X,Y,Z=[p[i]-center[i]for i in range(3)];local.append((c*X-s*Z,Y,s*X+c*Z))
    polygon=clip_axial(clip_axial(local,halfwidth,1),halfwidth,-1)
    return projected_distance(polygon)-radius

def load_triangles(path):
    raw=Path(path).read_bytes();assert len(raw)<=16*1024**2 and hashlib.sha256(raw).hexdigest()==SOURCE_SHA
    d=json.loads(raw);buffers=[base64.b64decode(b['uri'].split(',',1)[1],validate=True)for b in d['buffers']];triangles=[]
    def read(index):
        a=d['accessors'][index];v=d['bufferViews'][a['bufferView']];data=buffers[v['buffer']];fmt,n={5126:('f',3),5125:('I',1)}[a['componentType']];at=v.get('byteOffset',0)+a.get('byteOffset',0);stride=v.get('byteStride',4*n)
        return [struct.unpack_from('<'+fmt*n,data,at+i*stride)for i in range(a['count'])]
    for node in d['nodes']:
        if node['name'].startswith(('rim-','tyre-')):continue
        M=node['matrix']
        for p in d['meshes'][node['mesh']]['primitives']:
            points=[tuple(sum(M[j*4+i]*row[j]for j in range(3))+M[12+i]for i in range(3))for row in read(p['attributes']['POSITION'])];indices=[x[0]for x in read(p['indices'])]
            for i in range(0,len(indices),3):triangles.append((node['name'],tuple(points[j]for j in indices[i:i+3])))
    assert len(triangles)<=100000
    return triangles

def investigate(path,margin=.005,steps=110):
    assert 0<=margin<=.02 and 22<=steps<=220
    start=time.monotonic();triangles=load_triangles(path);caches={}
    # A steering cylinder is inside this sphere around its pivot for every tested yaw.
    sphere=math.hypot(WIDTH/2+margin,RADIUS+margin)
    for wheel,center in enumerate(CENTERS):
        selected=[]
        for name,tri in triangles:
            if all(max(p[i]for p in tri)>=center[i]-sphere and min(p[i]for p in tri)<=center[i]+sphere for i in (0,2)) and max(p[1]for p in tri)>=center[1]-sphere and min(p[1]for p in tri)<=center[1]+.2392+sphere:selected.append((name,tri))
        caches[wheel]=selected
    angles=[-.55+1.1*i/steps for i in range(steps+1)]
    def evaluate(delta):
        best=math.inf;witness=None;tested=0
        for wheel,source in enumerate(CENTERS):
            center=(source[0],source[1]+delta,source[2])
            for angle in angles if wheel<2 else (0.,):
                for name,tri in caches[wheel]:
                    distance=triangle_clearance(tri,center,angle,WIDTH/2+margin,RADIUS+margin);tested+=1
                    if distance<best:best=distance;witness={'wheel':wheel,'steering_rad':angle,'part':name,'triangle':tri}
            if time.monotonic()-start>250:raise RuntimeError('boundedcommand deadline')
        return {'delta_y':delta,'minimum_clearance_after_margin':best,'passes':best>=0,'witness':witness,'triangle_tests':tested}
    baseline=evaluate(0.);design=evaluate(.0868);maximum=evaluate(.2392);history=[baseline,design,maximum]
    scan=[evaluate(.2392*i/48) for i in range(49)]
    safe=[(i,row)for i,row in enumerate(scan)if row['passes']]
    result=None
    if safe:
        index,result=safe[-1]
        if index<48:
            low,high=result['delta_y'],scan[index+1]['delta_y']
            for _ in range(12):
                middle=(low+high)/2;check=evaluate(middle);history.append(check)
                if check['passes']:low=middle;result=check
                else:high=middle
        # Recheck selected pose at .001-radian increments rather than trusting coarse scan.
        angles=[-.55+1.1*i/1100 for i in range(1101)]
        candidate=result['delta_y'];result=None
        for backoff in range(21):
            final=evaluate(max(0,candidate-backoff*.001));history.append(final)
            if final['passes']:
                final['dense_backoff_m']=backoff*.001;result=final;break
    return {'source_sha256':SOURCE_SHA,'body_triangles':len(triangles),'cached_triangles':{str(k):len(v)for k,v in caches.items()},'margin_m':margin,'steering_samples':angles,'history':history,'pose_scan':scan,'largest_bisection_pass':result,'elapsed_seconds':time.monotonic()-start,'limitations':['Conservative cylinder expanded radially and axially; may reject noncolliding detailed tyre/mesh shapes.','Dense discrete steering samples, not continuous-angle proof.','Pose clearance is nonmonotonic:49-point scan locates largest sampled safe bracket then local bisection; not global continuous pose proof. Native equilibrium unproven.','Wheelspin covered by radial envelope; dynamic suspension/body deformation not modeled.']}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=investigate(a.source);
    with a.output.open('x') as out:out.write(json.dumps(r,indent=2)+'\n')
    print(json.dumps({k:r[k]for k in ('body_triangles','cached_triangles','largest_bisection_pass','elapsed_seconds')},indent=2))
if __name__=='__main__':main()
