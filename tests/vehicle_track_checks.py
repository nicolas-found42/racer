"""Hierarchical track adaptation: all-vertex affine and carrier invariants."""
import copy,hashlib,math,struct,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import fit_vehicle_tracks as t

def fixture(matrix=False,version=2):
 binary=bytearray();views=[];accessors=[];meshes=[];nodes=[];groups=[]
 for i in range(9):
  offset=len(binary);binary.extend(struct.pack('<9f',-.01,0,0,.01,0,0,0,.01,.01));views.append({'buffer':0,'byteOffset':offset,'byteLength':36});accessors.append({'bufferView':len(views)-1,'componentType':5126,'type':'VEC3','count':3});position=len(accessors)-1;offset=len(binary);binary.extend(struct.pack('<3I',0,1,2));views.append({'buffer':0,'byteOffset':offset,'byteLength':12});accessors.append({'bufferView':len(views)-1,'componentType':5125,'type':'SCALAR','count':3});meshes.append({'primitives':[{'attributes':{'POSITION':position},'indices':len(accessors)-1}]});nodes.append({'mesh':i})
 nodes[0]['translation']=[0,1,0]
 centers=[]
 for wi in range(4):
  hub=1+2*wi;leaf=hub+1;nodes[hub].update(translation=[.75 if wi<2 else -.75,.6,-.6 if wi%2==0 else .6],children=[leaf]);centers.append([-.6 if wi%2==0 else .6,.3,-1.5 if wi<2 else 1.5]);groups.extend([(hub,('carrier'if version==2 else 'wheel'),wi),(leaf,'wheel',wi)])
 root={'rotation':[0,math.sqrt(.5),0,math.sqrt(.5)],'scale':[2,.5,1],'children':[0,1,3,5,7]}
 if matrix:
  m=t.node_matrix(root);root={'matrix':[m[i][j]for j in range(4)for i in range(4)],'children':root['children']}
 nodes.append(root);doc={'asset':{'version':'2.0'},'scene':0,'scenes':[{'nodes':[9]}],'nodes':nodes,'meshes':meshes,'bufferViews':views,'accessors':accessors,'buffers':[{'byteLength':len(binary)}]};raw=t.pack(doc,binary);sha=hashlib.sha256(raw).hexdigest();text=f'RACER_VEHICLE {version}\nid "vehicle-{sha}"\nname "fixture"\nmesh "{sha}.glb"\nsha256 {sha}\nsource_sha256 '+ 'a'*64+'\nbody -3 -3 -3 3 3 3\n';text+=''.join('wheel '+label+' '+' '.join(map(str,c+[.1,.1]))+'\n'for label,c in zip(('FL','FR','RL','RR'),centers));text+='groups 9\ngroup 0 '+('body'if version==2 else '-1')+'\n';text+=''.join(f'group {i} '+(f'{role} '+('FL','FR','RL','RR')[wi]if version==2 else str(wi))+'\n'for i,role,wi in groups)
 return doc,binary,raw,text

def run(raw,text,targets=(1.3,1.3)):
 return t.fit(raw,text,targets,hashlib.sha256(raw).hexdigest(),hashlib.sha256(text.encode()).hexdigest(),'synthetic fixture')

class Checks(unittest.TestCase):
 def test_nonuniform_rotated_carrier_parent_moves_once(self):
  for matrix in (False,True):
   doc,binary,raw,text=fixture(matrix);out,new,r=run(raw,text);d,b=t.unpack(out);self.assertEqual(b,binary);self.assertEqual(r['all_world_positions_verified'],27);self.assertEqual({x['node']for x in r['changes']},{1,3,5,7})
   for wi in range(4):
    hub=1+2*wi;self.assertEqual(d['nodes'][hub+1],doc['nodes'][hub+1]);self.assertAlmostEqual(d['nodes'][hub]['translation'][2]-doc['nodes'][hub]['translation'][2],-.05 if wi%2==0 else .05);self.assertAlmostEqual(d['nodes'][hub]['translation'][0],doc['nodes'][hub]['translation'][0])
   self.assertEqual(d['nodes'][0],doc['nodes'][0]);self.assertEqual([s for s in text.splitlines()if s.startswith('group ')],[s for s in new.splitlines()if s.startswith('group ')])
 def test_mirrored_parent_and_matrix_mount(self):
  doc,binary,raw,text=fixture();old=t.descriptor(text)[0]['sha256'][0];doc['nodes'][9]['scale'][2]=-1
  for i in (1,3,5,7):
   n=doc['nodes'][i];n['translation'][2]*=-1;m=t.node_matrix(n);doc['nodes'][i]={'mesh':n['mesh'],'children':n['children'],'matrix':[m[k][j]for j in range(4)for k in range(4)]}
  raw=t.pack(doc,binary);text=text.replace(old,hashlib.sha256(raw).hexdigest());out,new,r=run(raw,text);d,_=t.unpack(out)
  self.assertEqual(r['all_world_positions_verified'],27)
  for i in (1,3,5,7):self.assertIn('matrix',d['nodes'][i]);self.assertNotIn('translation',d['nodes'][i])
 def test_v1_and_inward_fit(self):
  _,_,raw,text=fixture(version=1);_,_,r=run(raw,text,(1.1,1.1));self.assertAlmostEqual(r['wheels_after'][0][0],-.55)
 def test_reject_shared_unbound_and_nonaffine(self):
  for mutation in (lambda d:d['nodes'][9]['children'].append(1),lambda d:d['nodes'][2].update(mesh=1),lambda d:d['nodes'][9].update(matrix=[1]*16)):
   d,_,_,text=fixture();mutation(d);raw=t.pack(d,fixture()[1]);sha=hashlib.sha256(raw).hexdigest();old=t.descriptor(text)[0]['sha256'][0];text=text.replace(old,sha)
   with self.assertRaises(ValueError):run(raw,text)
 def test_reject_bounds_and_pins(self):
  _,_,raw,text=fixture()
  with self.assertRaisesRegex(ValueError,'track_change_budget'):run(raw,text,(1.5,1.3))
  with self.assertRaisesRegex(ValueError,'source_pin'):t.fit(raw,text,[1.3,1.3],'0'*64,hashlib.sha256(text.encode()).hexdigest(),'fixture')
  with self.assertRaisesRegex(ValueError,'wheel_containment'):run(raw,text.replace('0.1 0.1','0.001 0.001'))
if __name__=='__main__':unittest.main()
