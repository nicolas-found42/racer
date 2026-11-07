#!/usr/bin/env python3
"""Pinned static vehicle triangle/cylinder diagnostics; no equilibrium or dynamic fit claim."""
import argparse,collections,hashlib,json,math,shlex,time
from pathlib import Path
from prepare_gt4_vehicle import Geometry,unpack
from prepare_mcla_vehicle import read_regular
from slrr_clearance import triangle_clearance,clip_axial,projected_distance
LABELS=('FL','FR','RL','RR')
def radial_extents(triangle,center,steering,halfwidth):
 c,s=math.cos(steering),math.sin(steering);local=[]
 for p in triangle:
  x,y,z=[p[k]-center[k]for k in range(3)];local.append((c*x-s*z,y,s*x+c*z))
 poly=clip_axial(clip_axial(local,halfwidth,1),halfwidth,-1)
 return (projected_distance(poly),max((math.hypot(p[1],p[2])for p in poly),default=-math.inf))
def require(c,reason):
 if not c:raise ValueError(reason)
def finite(v,n):
 require(isinstance(v,list)and len(v)==n and all(type(x)in(int,float)and math.isfinite(x)for x in v),'finite_vector');return v
def descriptor(text):
 rows=[shlex.split(s)for s in text.splitlines()if s.strip()];require(len(rows)>=12 and rows[0]in[['RACER_VEHICLE','1'],['RACER_VEHICLE','2']],'descriptor_version');version=int(rows[0][1]);require([r[0]for r in rows[:12]]==['RACER_VEHICLE','id','name','mesh','sha256','source_sha256','body','wheel','wheel','wheel','wheel','groups'],'descriptor_schema');fields={r[0]:r[1:]for r in rows[:7]};digest=fields['sha256'][0];require(len(digest)==64 and all(c in'0123456789abcdef'for c in digest)and fields['id']==['vehicle-'+digest]and fields['mesh']==[digest+'.glb'],'descriptor_identity');wheels=[]
 for label,row in zip(LABELS,rows[7:11]):
  require(row[:2]==['wheel',label]and len(row)==7,'wheel_schema');v=list(map(float,row[2:]));finite(v,5);require(0<v[3]<5 and 0<v[4]<5,'wheel_dimensions');wheels.append(v)
 require(len(rows[11])==2 and int(rows[11][1])==len(rows)-12 and 0<int(rows[11][1])<=4096,'group_count');roles={}
 for row in rows[12:]:
  require(row[0]=='group' and len(row)in(3,4),'group_schema');i=int(row[1]);require(i not in roles and 0<=i<4096,'group_index')
  if version==1:
   require(len(row)==3 and int(row[2])in(-1,0,1,2,3),'group_role');roles[i]=('body',None)if row[2]=='-1'else('wheel',int(row[2]))
  elif row[2]=='body':require(len(row)==3,'body_role');roles[i]=('body',None)
  else:require(len(row)==4 and row[2]in('wheel','carrier')and row[3]in LABELS,'named_role');roles[i]=(row[2],LABELS.index(row[3]))
 require({w for role,w in roles.values()if role=='wheel'}==set(range(4)),'wheel_role_coverage');return fields,wheels,roles

def multiply(a,b):return[[sum(a[i][k]*b[k][j]for k in range(4))for j in range(4)]for i in range(4)]
def node_matrix(n):
 if 'matrix'in n:
  require(not any(k in n for k in('translation','rotation','scale')),'matrix_trs');v=finite(n['matrix'],16);m=[[v[j*4+i]for j in range(4)]for i in range(4)]
 else:
  x,y,z,w=finite(n.get('rotation',[0,0,0,1]),4);require(abs(x*x+y*y+z*z+w*w-1)<1e-5,'quaternion');s=finite(n.get('scale',[1,1,1]),3);t=finite(n.get('translation',[0,0,0]),3);r=[[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],[2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],[2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]];m=[[r[i][j]*s[j]for j in range(3)]+[t[i]]for i in range(3)]+[[0,0,0,1]]
 require(m[3]==[0,0,0,1] and all(math.isfinite(x)and abs(x)<=1e6 for row in m for x in row),'affine');det=sum(m[0][i]*(m[1][(i+1)%3]*m[2][(i+2)%3]-m[1][(i+2)%3]*m[2][(i+1)%3])for i in range(3));require(abs(det)>1e-15,'singular_frame');return m

def load(path,expected,triangle_roles=('body',)):
 raw=read_regular(path,32768);require(hashlib.sha256(raw).hexdigest()==expected,'descriptor_pin');fields,wheels,roles=descriptor(raw.decode());mesh=path.parent/fields['mesh'][0];data=read_regular(mesh,16*1024**2);require(hashlib.sha256(data).hexdigest()==fields['sha256'][0],'mesh_pin');d,b=unpack(data);require(not any(d.get(k)for k in('skins','animations','extensionsRequired')),'unsupported_animation');nodes=d['nodes'];require(0<len(nodes)<=4096,'node_budget');g=Geometry(d,b);seen=set();bound=set();triangles=[];counts=collections.Counter();positions=indices=0
 def visit(i,parent,depth):
  nonlocal positions,indices
  require(type(i)is int and 0<=i<len(nodes)and i not in seen and depth<64,'scene_graph');seen.add(i);n=nodes[i];require(not any(n.get(k)for k in('skin','weights','extensions')),'node_features');m=multiply(parent,node_matrix(n))
  if 'mesh'in n:
   require(i in roles,'unbound_mesh');bound.add(i);role,_=roles[i];mi=n['mesh'];require(type(mi)is int and 0<=mi<len(d['meshes']),'mesh_index')
   for pi,p in enumerate(d['meshes'][mi]['primitives']):
    require(p.get('mode',4)==4 and not p.get('targets'),'triangle_mode');points=g.values(p['attributes']['POSITION'],'VEC3',{5126});positions+=len(points);require(positions<=1000000,'position_budget');ids=[x[0]for x in g.values(p['indices'],'SCALAR',{5121,5123,5125})];indices+=len(ids);require(indices<=1500000 and len(ids)%3==0 and all(0<=j<len(points)for j in ids),'index_budget')
    if role in triangle_roles:
     world=[tuple(sum(m[k][j]*v[j]for j in range(3))+m[k][3]for k in range(3))for v in points];name=n.get('name',str(i))
     for off in range(0,len(ids),3):triangles.append({'node':i,'name':name,'primitive':pi,'triangle_index':off//3,'points':tuple(world[j]for j in ids[off:off+3]),'role':role,'wheel':roles[i][1],'material_index':p.get('material'),'material_name':d.get('materials',[])[p['material']].get('name') if 'material'in p else None});counts[name]+=int(role=='body')
  for j in n.get('children',[]):visit(j,m,depth+1)
 scene=d.get('scene',0);require(type(scene)is int and 0<=scene<len(d['scenes']),'scene_index')
 for i in d['scenes'][scene]['nodes']:visit(i,[[int(a==c)for c in range(4)]for a in range(4)],0)
 require(bound==set(roles),'unreachable_binding');return wheels,triangles,{'descriptor_sha256':expected,'mesh_sha256':fields['sha256'][0],'source_sha256':fields['source_sha256'][0],'name':fields['name'][0],'positions_decoded':positions,'expanded_indices_decoded':indices,'body_triangles':sum(r['role']=='body'for r in triangles),'body_parts':{k:v for k,v in counts.items()if v},'carrier_nodes_excluded':[i for i,(r,w)in roles.items()if r=='carrier']}

def inspect(path,expected,steps=110,margin=0.,timeout=250):
 require(type(steps)is int and 110<=steps<=1100 and 0<=margin<=.02 and 0<timeout<=250,'diagnostic_bounds');start=time.monotonic();wheels,triangles,identity=load(Path(path),expected);angles=[-.55+1.1*i/steps for i in range(steps+1)];results=[];tests=0
 for wi,w in enumerate(wheels):
  center=w[:3];half=w[4]/2+margin;radius=w[3]+margin;sphere=math.hypot(half,radius);selected=[]
  for row in triangles:
   tri=row['points']
   if all(max(p[k]for p in tri)>=center[k]-sphere and min(p[k]for p in tri)<=center[k]+sphere for k in range(3)):selected.append(row)
  best=math.inf;witness=None;overlaps=collections.Counter();bands=collections.Counter();outerparts=collections.Counter();outerwitness=None;outerbest=math.inf;tested_angles=angles if wi<2 else[0.]
  for angle in tested_angles:
   for row in selected:
    value=triangle_clearance(row['points'],center,angle,half,radius);tests+=1
    if value<0:
     overlaps[row['name']]+=1;low,high=radial_extents(row['points'],center,angle,half);kind='inner_volume_only' if high<.75*w[3] else 'outer_band_potential';bands[kind]+=1
     if kind=='outer_band_potential':
      outerparts[row['name']]+=1
      if value<outerbest:outerbest=value;outerwitness={**row,'steering_rad':angle,'radial_min_m':low,'radial_max_m':high,'radial_excess_after_margin_m':value,'classification':kind}
    if value<best:best=value;witness={**row,'steering_rad':angle,'radial_excess_m':value}
   if time.monotonic()-start>timeout:raise RuntimeError('clearance_deadline: incomplete evidence; no complete report')
  results.append({'wheel':LABELS[wi],'center':center,'radius':w[3],'width':w[4],'selected_triangles':len(selected),'steering_samples':len(tested_angles),'minimum_radial_excess_after_margin_m':best if math.isfinite(best)else None,'overlap_sample_count':sum(overlaps.values()),'overlapping_parts':dict(overlaps),'overlap_band_counts':dict(bands),'outer_band_parts':dict(outerparts),'outer_band_witness':outerwitness,'witness':witness})
 return {'schema':1,**identity,'margin_m':margin,'front_steering_angles_rad':angles,'rear_steering_angles_rad':[0.],'wheels':results,'triangle_angle_tests':tests,'elapsed_seconds':time.monotonic()-start,'limits':['Authored band heuristic: clipped triangle radial maximum below0.75*R is inner_volume_only; other filled-cylinder overlaps are outer_band_potential, not actual tyre-surface intersection proof.',
'Diagnostic intersection witnesses against conservative rigid wheel cylinders, not immediate source defects or exact tyre shape collisions.','All reachable descriptor BODY meshes tested; CARRIER meshes excluded. Missing/uninstalled source components remain outside evidence.','Discrete front steering samples only, not continuous-angle or suspension-travel proof. Wheelspin covered by radial envelope.','Radial excess after axial slab clipping is not exact3D Euclidean surface distance; axial/radial expansion is conservative.','Native equilibrium, deformation, physics and actual-game rendering are not established.']}

def triangle_contacts(a,b,tolerance=1e-8):
 """Vectorized triangle SAT, including coplanar edge axes; degenerate pairs excluded."""
 import numpy as np
 a=np.asarray(a,dtype=float);b=np.asarray(b,dtype=float);ea=np.roll(a,-1,axis=1)-a;eb=np.roll(b,-1,axis=1)-b;na=np.cross(ea[:,0],ea[:,1]);nb=np.cross(eb[:,0],eb[:,1]);la=np.linalg.norm(na,axis=1);lb=np.linalg.norm(nb,axis=1);valid=(la>1e-12)&(lb>1e-12);na=na/np.maximum(la[:,None],1e-300);nb=nb/np.maximum(lb[:,None],1e-300);axes=[na,nb]
 for i in range(3):
  for j in range(3):axes.append(np.cross(ea[:,i],eb[:,j]))
 # Coplanar triangles need in-plane edge normals in addition to ordinary3D SAT.
 for i in range(3):axes.extend([np.cross(na,ea[:,i]),np.cross(nb,eb[:,i])])
 overlap=valid.copy()
 for axis in axes:
  length=np.linalg.norm(axis,axis=1);axis=axis/np.maximum(length[:,None],1e-300);pa=np.einsum('nvi,ni->nv',a,axis);pb=np.einsum('nvi,ni->nv',b,axis);separate=(pa.max(1)<pb.min(1)-tolerance)|(pb.max(1)<pa.min(1)-tolerance);overlap&=~(separate&(length>1e-12))
 coplanar=valid&(np.linalg.norm(np.cross(na,nb),axis=1)<1e-8)&(np.abs(np.einsum('ni,ni->n',b[:,0]-a[:,0],na))<=tolerance)
 return overlap,coplanar,~valid

def proper_crossings(a,b,tolerance=1e-8):
 """Strict plane straddles AND positive intersection-line overlap; endpoint touches excluded."""
 import numpy as np
 a=np.asarray(a,dtype=float);b=np.asarray(b,dtype=float);na=np.cross(a[:,1]-a[:,0],a[:,2]-a[:,0]);nb=np.cross(b[:,1]-b[:,0],b[:,2]-b[:,0]);na/=np.maximum(np.linalg.norm(na,axis=1)[:,None],1e-300);nb/=np.maximum(np.linalg.norm(nb,axis=1)[:,None],1e-300);da=np.einsum('nvi,ni->nv',a-b[:,0,None,:],nb);db=np.einsum('nvi,ni->nv',b-a[:,0,None,:],na)
 axis=np.cross(na,nb);axis/=np.maximum(np.linalg.norm(axis,axis=1)[:,None],1e-300)
 def interval(points,distances):
  projections=np.einsum('nvi,ni->nv',points,axis);low=np.full(len(points),np.inf);high=np.full(len(points),-np.inf)
  for i in range(3):
   at=np.abs(distances[:,i])<=tolerance;low=np.minimum(low,np.where(at,projections[:,i],np.inf));high=np.maximum(high,np.where(at,projections[:,i],-np.inf))
   j=(i+1)%3;cross=(distances[:,i]*distances[:,j])<0;den=distances[:,i]-distances[:,j];t=np.divide(distances[:,i],den,out=np.zeros_like(den),where=den!=0);value=projections[:,i]+t*(projections[:,j]-projections[:,i]);low=np.minimum(low,np.where(cross,value,np.inf));high=np.maximum(high,np.where(cross,value,-np.inf))
  return low,high
 al,ah=interval(a,da);bl,bh=interval(b,db);length=np.minimum(ah,bh)-np.maximum(al,bl)
 return(da.min(1)<-tolerance)&(da.max(1)>tolerance)&(db.min(1)<-tolerance)&(db.max(1)>tolerance)&(length>tolerance)

def inspect_surfaces(path,expected,angles=(-.55,0.,.55),timeout=250):
 """Actual rigid rolling triangles against body; contact/touch diagnostic, not penetration depth."""
 import numpy as np
 require(1<=len(angles)<=111 and all(math.isfinite(x)and abs(x)<=.55 for x in angles)and 0<timeout<=250,'surface_angles');start=time.monotonic();wheels,rows,identity=load(Path(path),expected,('body','wheel'))
 def deadline():
  if time.monotonic()-start>timeout:raise RuntimeError('surface_deadline: incomplete evidence')
 deadline();body=[r for r in rows if r['role']=='body'];bp=np.array([r['points']for r in body]);blo,bhi=bp.min(1),bp.max(1);results=[];pairs_total=0
 for wi,w in enumerate(wheels):
  source=[r for r in rows if r['role']=='wheel'and r['wheel']==wi];require(source,'wheel_surface_missing');original=np.array([r['points']for r in source]);c=np.array(w[:3]);samples=[]
  for angle in angles if wi<2 else(0.,):
   deadline()
   co,si=math.cos(angle),math.sin(angle);p=original-c;wp=p.copy();wp[:,:,0]=co*p[:,:,0]+si*p[:,:,2];wp[:,:,2]=-si*p[:,:,0]+co*p[:,:,2];wp+=c;lo,hi=wp.min(1),wp.max(1);sphere=max(np.linalg.norm((original-c).reshape(-1,3),axis=1));keep=np.all((bhi>=c-sphere)&(blo<=c+sphere),axis=1);bodyids=np.nonzero(keep)[0];require(len(bodyids)*len(source)<=16000000,'surface_pair_memory_budget');mask=np.ones((len(bodyids),len(source)),dtype=bool)
   for axis in range(3):mask&=(bhi[bodyids,axis,None]>=lo[None,:,axis]-1e-8)&(blo[bodyids,axis,None]<=hi[None,:,axis]+1e-8)
   bi,ti=np.nonzero(mask);pairs_total+=len(bi);require(pairs_total<=5000000,'surface_pair_budget');hits=degenerates=coplanars=proper_count=0;witnesses=[];parts=collections.Counter()
   for off in range(0,len(bi),1024):
    ids=bodyids[bi[off:off+1024]];ws=ti[off:off+1024];contact,coplanar,invalid=triangle_contacts(bp[ids],wp[ws]);proper=contact&proper_crossings(bp[ids],wp[ws]);proper_count+=int(proper.sum());degenerates+=int(invalid.sum());coplanars+=int((contact&coplanar).sum());hits+=int(contact.sum())
    for j in np.nonzero(contact)[0]:
     row=body[int(ids[j])];parts[row['name']]+=1
     if len(witnesses)<8:witnesses.append({'body':row,'rolling':{**source[int(ws[j])],'points':wp[int(ws[j])].tolist()},'coplanar':bool(coplanar[j]),'proper_transverse_crossing':bool(proper[j])})
    deadline()
   samples.append({'steering_rad':angle,'aabb_pairs':len(bi),'contacts_including_touch':hits,'proper_transverse_crossings':proper_count,'coplanar_contacts':coplanars,'degenerate_pairs_excluded':degenerates,'contact_parts':dict(parts),'witnesses':witnesses})
   deadline()
  results.append({'wheel':LABELS[wi],'rolling_triangles':len(source),'samples':samples})
 elapsed=time.monotonic()-start
 if elapsed>timeout:raise RuntimeError('surface_deadline: incomplete evidence')
 return {'schema':1,**identity,'body_triangles':len(body),'wheels':results,'pair_tests':pairs_total,'elapsed_seconds':elapsed,'limits':['Actual rigid rolling-group triangles, including rim/disc geometry; intended internal components can contact and are not automatically defects.','SAT includes coplanar cases and touching within1e−8metres; proper transverse classification additionally requires positive intersection-line overlap, not merely plane straddles. No penetration depth or intended mechanical exclusions recovered.','Degenerate triangles excluded and counted; sparse steering only as explicitly listed; no wheelspin/suspension/deformation/continuous proof.','NumPy local dependency; pair/deadline limits fail explicitly rather than publish incomplete success.']}

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('descriptor',type=Path);p.add_argument('--descriptor-sha256',required=True);p.add_argument('--steps',type=int,default=110);p.add_argument('--margin',type=float,default=0);p.add_argument('--surfaces',action='store_true');p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 if a.surfaces:
  require(1<=a.steps<=110,'surface_step_budget');r=inspect_surfaces(a.descriptor,a.descriptor_sha256,angles=[-.55+1.1*i/a.steps for i in range(a.steps+1)])
 else:r=inspect(a.descriptor,a.descriptor_sha256,a.steps,a.margin)
 payload=json.dumps(r,indent=2,allow_nan=False)+'\n';require(len(payload.encode())<16*1024**2,'report_budget');a.output.parent.mkdir(parents=True,exist_ok=True)
 with a.output.open('x')as f:f.write(payload)
 print(json.dumps({'mesh_sha256':r['mesh_sha256'],'elapsed_seconds':r['elapsed_seconds'],'report':str(a.output)}))
