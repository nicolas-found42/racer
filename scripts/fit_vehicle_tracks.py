#!/usr/bin/env python3
"""Pinned, shape-preserving authored wheel/carrier track adaptation."""
import argparse,copy,hashlib,json,math,shlex,shutil
from pathlib import Path
from prepare_gt4_vehicle import Geometry,pack,unpack
from prepare_mcla_vehicle import read_regular
from vehicle_clearance import descriptor,node_matrix,multiply,require
I=[[int(i==j) for j in range(4)] for i in range(4)]
def inverse_delta(m,delta):
 a=[r[:3] for r in m[:3]];b=[delta,0.,0.]
 for col in range(3):
  pivot=max(range(col,3),key=lambda r:abs(a[r][col]));require(abs(a[pivot][col])>1e-12,'singular_parent');a[col],a[pivot]=a[pivot],a[col];b[col],b[pivot]=b[pivot],b[col];q=a[col][col];a[col]=[v/q for v in a[col]];b[col]/=q
  for row in range(3):
   if row==col:continue
   q=a[row][col];a[row]=[a[row][j]-q*a[col][j] for j in range(3)];b[row]-=q*b[col]
 require(all(math.isfinite(x) and abs(x)<=100 for x in b),'local_delta_budget');return b

def frames(doc,roles):
 require(not any(doc.get(k) for k in ('animations','skins','extensionsRequired')),'unsupported_runtime');nodes=doc['nodes'];require(0<len(nodes)<=4096,'node_budget');seen=set();parents={};world={};owners={};meshes=set()
 def visit(i,parent,depth):
  require(type(i)is int and 0<=i<len(nodes) and i not in seen and depth<64,'shared_DAG_or_depth');seen.add(i);n=nodes[i];require(not any(n.get(k)for k in ('skin','weights','extensions')),'node_features');parents[i]=parent;world[i]=multiply(I if parent is None else world[parent],node_matrix(n));owned=set()
  if 'mesh'in n:
   require(i in roles and type(n['mesh'])is int and 0<=n['mesh']<len(doc['meshes']) and n['mesh']not in meshes,'unbound_or_shared_mesh');meshes.add(n['mesh']);owned.add(roles[i][1])
  else:require(i not in roles,'binding_without_mesh')
  for child in n.get('children',[]):owned.update(visit(child,i,depth+1))
  owners[i]=owned;return owned
 require(len(doc.get('scenes',[]))==1 and doc.get('scene',0)==0,'scene');
 for root in doc['scenes'][0]['nodes']:visit(root,None,0)
 require(set(roles)=={i for i in seen if 'mesh'in nodes[i]},'incomplete_scene');return parents,world,owners

def positions(doc,binary,world):
 g=Geometry(doc,binary);out={};indices=0;count=0
 for ni,m in world.items():
  if 'mesh'not in doc['nodes'][ni]:continue
  values=[]
  for p in doc['meshes'][doc['nodes'][ni]['mesh']]['primitives']:
   require(p.get('mode',4)==4 and not p.get('targets'),'primitive');count+=doc['accessors'][p['attributes']['POSITION']]['count'];require(count<=1000000,'position_budget');v=g.values(p['attributes']['POSITION'],'VEC3',{5126});require(indices+doc['accessors'][p['indices']]['count']<=1500000,'index_budget');ids=g.values(p['indices'],'SCALAR',{5121,5123,5125});indices+=len(ids);require(indices<=1500000 and len(ids)%3==0 and all(0<=x[0]<len(v)for x in ids),'indices');values.extend([[sum(m[k][j]*a[j]for j in range(3))+m[k][3]for k in range(3)]for a in v])
  out[ni]=values
 return out

def fit(raw,text,targets,source_sha,descriptor_sha,authority):
 require(len(raw)<=32*1024**2 and hashlib.sha256(raw).hexdigest()==source_sha,'source_pin');require(len(text.encode())<=32768 and hashlib.sha256(text.encode()).hexdigest()==descriptor_sha,'descriptor_pin');require(isinstance(authority,str) and 0<len(authority)<=4096,'authority');fields,wheels,roles=descriptor(text);require(any(role=='body'for role,wi in roles.values()),'body_required');require(fields['sha256']==[source_sha],'mesh_identity');require(len(targets)==2 and all(math.isfinite(x)and .5<=x<=3 for x in targets),'targets');doc,binary=unpack(raw);require(len(doc.get('buffers',[]))==1 and 'uri'not in doc['buffers'][0] and all('uri'not in i for i in doc.get('images',[])),'external_resources');parents,world,owners=frames(doc,roles);old=positions(doc,binary,world);body=list(map(float,fields['body']));require(len(body)==6 and all(math.isfinite(x)for x in body),'body');
 for ni,points in old.items():
  wi=roles[ni][1]
  for point in points:
   if wi is None:require(all(body[k]-2e-6<=point[k]<=body[k+3]+2e-6 for k in range(3)),'body_containment')
   else:
    w=wheels[wi];require(abs(point[0]-w[0])<=w[4]/2+2e-6 and math.hypot(point[1]-w[1],point[2]-w[2])<=w[3]+2e-6,'wheel_containment')
 deltas={};before=copy.deepcopy(wheels)
 for axle,left in enumerate((0,2)):
  a,b=wheels[left:left+2];track=b[0]-a[0];require(a[0]<0<b[0]and abs(a[1]-b[1])<1e-4 and abs(a[2]-b[2])<1e-4,'axle');require(abs(targets[axle]/track-1)<=.15,'track_change_budget');mid=(a[0]+b[0])/2
  for wi,sign in ((left,-1),(left+1,1)):
   target=mid+sign*targets[axle]/2;delta=target-wheels[wi][0];require(abs(delta)<=.25,'offset_budget');deltas[wi]=delta;wheels[wi][0]=target
 changes=[]
 def move(i):
  owned=owners[i]
  if len(owned)==1 and None not in owned:
   wi=next(iter(owned));parent=parents[i];local=inverse_delta(I if parent is None else world[parent],deltas[wi]);n=doc['nodes'][i]
   if 'matrix'in n:
    for j in range(3):n['matrix'][12+j]+=local[j]
   else:n['translation']=[n.get('translation',[0,0,0])[j]+local[j]for j in range(3)]
   changes.append({'node':i,'wheel':wi,'world_delta_x':deltas[wi],'local_delta':local});return
  for child in doc['nodes'][i].get('children',[]):move(child)
 for root in doc['scenes'][0]['nodes']:move(root)
 _,newworld,_=frames(doc,roles);new=positions(doc,binary,newworld);verified=0
 for ni,points in old.items():
  wi=roles[ni][1];dx=0 if wi is None else deltas[wi]
  for a,b in zip(points,new[ni]):require(max(abs(b[k]-a[k]-(dx if k==0 else 0))for k in range(3))<1e-9,'world_delta_mismatch');verified+=1
 receipt={'schema':1,'input_sha256':source_sha,'input_descriptor_sha256':descriptor_sha,'authority':authority,'targets':targets,'wheels_before':before,'wheels_after':wheels,'changes':changes,'all_world_positions_verified':verified,'binary_unchanged':True,'runtime_player_eligible':False,'limitations':['Authored factory-track adaptation; not original native placement or equilibrium proof.','Only disjoint wheel/carrier subtrees and descriptor pivot X changed; body and all mesh binary data unchanged.','Candidate requires native loader, GPU and motion acceptance.']};doc.setdefault('extras',{})['racerTrackFit']=receipt;result=pack(doc,binary);require(len(result)<=32*1024**2,'output_budget');digest=hashlib.sha256(result).hexdigest();rows=[shlex.split(s)for s in text.splitlines()if s.strip()];rows[1][1]='vehicle-'+digest;rows[3][1]=digest+'.glb';rows[4][1]=digest
 for row,w in zip(rows[7:11],wheels):row[2:]=[format(v,'.17g')for v in w]
 out='\n'.join(' '.join(json.dumps(v)if row[0]in('id','name','mesh')and j==1 else v for j,v in enumerate(row))for row in rows)+'\n';receipt['prepared_sha256']=digest;return result,out,receipt
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('descriptor',type=Path);p.add_argument('--source-sha256',required=True);p.add_argument('--descriptor-sha256',required=True);p.add_argument('--front',type=float,required=True);p.add_argument('--rear',type=float,required=True);p.add_argument('--authority',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();require(not a.output.exists() and not any(p.is_symlink()for p in (a.output,*a.output.parents)),'fresh_output');require(shutil.disk_usage(a.output.parent).free>=20*1024**3,'disk_budget');raw=read_regular(a.descriptor.with_suffix('.glb'),32*1024**2);text=read_regular(a.descriptor,32768).decode();r,t,e=fit(raw,text,[a.front,a.rear],a.source_sha256,a.descriptor_sha256,a.authority);a.output.mkdir();(a.output/(e['prepared_sha256']+'.glb')).write_bytes(r);(a.output/(e['prepared_sha256']+'.vehicle')).write_text(t);(a.output/'receipt.json').write_text(json.dumps(e,indent=2)+'\n');print(json.dumps(e,indent=2))
