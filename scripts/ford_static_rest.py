"""Exact EX/INDIGO authored suspension rest lane; no native animation claim."""
import copy,math
from prepare_gt4_vehicle import require,Geometry
from ford_cohort_registry import PROFILES
CORNERS=('FRONT_LEFT','FRONT_RIGHT','BACK_LEFT','BACK_RIGHT')
EXPECTED={
 'EX':{'BACK_RIGHT':(146,1335376,4),'BACK_LEFT':(150,1335608,8),'FRONT_RIGHT':(155,1335888,12),'FRONT_LEFT':(160,1336168,16)},
 'INDIGO':{'FRONT_LEFT':(200,1315268,19),'BACK_LEFT':(204,1315500,24),'BACK_RIGHT':(208,1315732,29),'FRONT_RIGHT':(213,1316004,34)}}
def normalize(doc,code,source_sha):
 require(code in EXPECTED and source_sha==PROFILES[code]['source_sha256'],'static_suspension_source')
 scenes=[s for s in doc['scenes']if s.get('extras',{}).get('sourceTree')==0 and s.get('extras',{}).get('visibilityPreset')=='low_speed'];require(len(scenes)==1 and len(scenes[0]['nodes'])==1,'static_suspension_scene');root=scenes[0]['nodes'][0];nodes=doc['nodes'];require(len(nodes)<=4087,'static_suspension_node_budget');rn=nodes[root];require(rn.get('translation',[0]*3)==[0]*3 and rn.get('scale',[1]*3)==[1]*3 and not any(k in rn for k in('matrix','rotation')),'static_suspension_root')
 frames={};parents={};owners={};found={};mesh_refs={}
 def walk(index,S,T,owner,depth):
  require(type(index)is int and 0<=index<len(nodes)and index not in frames and depth<60,'static_suspension_graph');n=nodes[index];require(not any(k in n for k in('matrix','rotation','skin','weights','extensions')),'static_suspension_transform');s=n.get('scale',[1]*3);t=n.get('translation',[0]*3);require(len(s)==len(t)==3 and all(type(v)in(int,float)and math.isfinite(v)for v in s+t),'static_suspension_frame');ns=[S[k]*s[k]for k in range(3)];nt=[T[k]+S[k]*t[k]for k in range(3)];require(all(math.isfinite(v)for v in ns+nt)and all(v!=0 for v in ns),'static_suspension_frame');frames[index]=(ns,nt);names=n.get('extras',{}).get('sourceNames',[])
  hubs=[x[4:]for x in names if x.startswith('HUB_')];require(len(hubs)<=1,'static_suspension_owner')
  if hubs:owner=hubs[0]
  owners[index]=owner
  if 'mesh'in n:
   mesh_refs.setdefault(n['mesh'],[]).append(index)
   suspension=[x for x in names if x.startswith('SUSPENSION_')]
   if suspension:
    require(len(suspension)==1 and suspension[0][11:]in CORNERS,'static_suspension_names');corner=suspension[0][11:];require(corner not in found and owner==corner,'static_suspension_owner');found[corner]=index
  for child in n.get('children',[]):
   require(child not in parents,'static_suspension_shared_node');parents[child]=index;walk(child,ns,nt,owner,depth+1)
 walk(root,[1]*3,[0]*3,None,0);require(set(found)==set(CORNERS),'static_suspension_names')
 for corner,(index,offset,geometry)in EXPECTED[code].items():
  require(found[corner]==index,'static_suspension_node_identity');n=nodes[index];e=n['extras'];require(e.get('serializedNodeOffset')==offset and e.get('geometryRecord')==geometry and len(mesh_refs[n['mesh']])==1,'static_suspension_node_identity')
 alias=None
 if code=='INDIGO':
  n=nodes[210];e=n['extras'];require(parents.get(210)==209 and owners.get(210)=='BACK_RIGHT'and nodes[209].get('extras',{}).get('sourceNames')==['WHEEL_BACK_RIGHT'],'indigo_unnamed_parent');require((e.get('serializedNodeOffset'),e.get('geometryRecord'),e.get('flags'))==(1315860,32,1)and e.get('sourceNames')==[]and n.get('mesh')==31 and not n.get('children')and mesh_refs.get(31)==[210],'indigo_unnamed_identity');require(nodes[209]['extras'].get('serializedNodeOffset')==1315772 and nodes[209]['extras'].get('geometryRecord')==30,'indigo_unnamed_parent');refs=[i for i,n in enumerate(nodes)if n.get('mesh')==31];require(refs==[31,119,210,270],'indigo_unnamed_references');alias={'node':210,'parent':209,'native_offset':1315860,'geometry_record':32,'flags':1,'original_source_names':[],'mesh_references_preserved':refs,'owner':'BACK_RIGHT','authority':'Exact pinned unnamed drawable inherits its single active named wheel parent; native spin consumer unknown.'}
 # Mutations begin only after every source/frame/owner identity check succeeds.
 clones=[]
 for corner in CORNERS:
  index=found[corner];original=nodes[index];clone=copy.deepcopy(original);clone.pop('children',None);clone['name']='Racer static suspension rest '+corner;clone['translation']=frames[index][1];clone['scale']=frames[index][0];clone['extras']['originalSourceNames']=clone['extras']['sourceNames'][:];clone['extras']['sourceNames']=[];clone['extras']['racerStaticSuspensionSourceNode']=index;ci=len(nodes);nodes.append(clone);original.pop('mesh');rn.setdefault('children',[]).append(ci);clones.append({'node':ci,'source_node':index,'corner':corner,'source_world_scale':frames[index][0],'source_world_translation':frames[index][1]})
 if alias:nodes[210]['extras']['originalSourceNames']=[];nodes[210]['extras']['sourceNames']=['WHEEL_BACK_RIGHT'];nodes[210]['extras']['racerExactUnnamedWheelAlias']=alias
 return {'schema':1,'source_sha256':source_sha,'clones':clones,'exact_unnamed_wheel_alias':alias,'runtime_player_eligible':False,'authority':'Racer-authored fixed suspension source rest pose before wheel-radius fit; not native steering/suspension animation or equilibrium.','limits':['Only four exact named suspension drawables are body-fixed clones; original nodes, source frames and child links remain intact.','Geometry/BIN/materials unchanged; no cylinder inflation, recentering or part removal.','Native static activation, steering linkage, suspension deformation, collision and physical units remain unproved.']}

def contain_roles(doc,binary,bindings,wheels):
 """New opt-in lane must not smuggle oversized source arms into wheel roles."""
 g=Geometry(doc,binary);roles={r['node']:r['role']for r in bindings};seen=set()
 def walk(index,S,T):
  require(index not in seen,'static_rest_result_graph');seen.add(index);n=doc['nodes'][index];s=n.get('scale',[1]*3);t=n.get('translation',[0]*3);ns=[S[k]*s[k]for k in range(3)];nt=[T[k]+S[k]*t[k]for k in range(3)]
  if 'mesh'in n and roles[index]!='body':
   label=roles[index].split()[1];w=wheels[('FL','FR','RL','RR').index(label)];c=w['center']
   for primitive in doc['meshes'][n['mesh']]['primitives']:
    for p in g.values(primitive['attributes']['POSITION']):
     q=[ns[k]*p[k]+nt[k]for k in range(3)];require(abs(q[0]-c[0])<=w['width']/2+1e-7 and math.hypot(q[1]-c[1],q[2]-c[2])<=w['radius']+1e-7,'static_rest_wheel_containment')
  for child in n.get('children',[]):walk(child,ns,nt)
 for root in doc['scenes'][0]['nodes']:walk(root,[1]*3,[0]*3)
