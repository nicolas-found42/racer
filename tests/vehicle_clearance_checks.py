#!/usr/bin/env python3
import hashlib,json,math,struct,sys,tempfile,unittest,importlib.util
from unittest import mock
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import vehicle_clearance as v
from prepare_gt4_vehicle import pack
class Checks(unittest.TestCase):
 def test_triangle_interior_and_slab(self):
  self.assertEqual(v.triangle_clearance(((0,-2,-2),(0,2,-2),(0,0,2)),(0,0,0),0,.1,.5),-.5)
  self.assertTrue(math.isinf(v.triangle_clearance(((1,0,0),(1,1,0),(1,0,1)),(0,0,0),0,.1,.5)))
  low,high=v.radial_extents(((0,0,0),(0,.1,0),(0,0,.1)),(0,0,0),0,.1);self.assertEqual(low,0);self.assertLess(high,.75*.5)
  low,high=v.radial_extents(((0,-2,-2),(0,2,-2),(0,0,2)),(0,0,0),0,.1);self.assertEqual(low,0);self.assertGreater(high,.5)
 @unittest.skipUnless(importlib.util.find_spec('numpy'),'optional surface diagnostics require existing NumPy environment')
 def test_actual_triangle_sat_coplanar_crossing_degenerate(self):
  import numpy as np
  a=np.array([[[0,0,0],[1,0,0],[0,1,0]]]*4);b=np.array([[[.1,.1,0],[.2,.1,0],[.1,.2,0]],[[2,2,0],[3,2,0],[2,3,0]],[[.2,.2,-1],[.2,.2,1],[.8,.2,0]],[[0,0,0],[0,0,0],[0,0,0]]]);hits,coplanar,bad=v.triangle_contacts(a,b);self.assertEqual(hits.tolist(),[True,False,True,False]);self.assertEqual(coplanar.tolist(),[True,True,False,False]);self.assertEqual(bad.tolist(),[False,False,False,True]);self.assertEqual((hits&v.proper_crossings(a,b)).tolist(),[False,False,True,False])
 @unittest.skipUnless(importlib.util.find_spec('numpy'),'optional surface diagnostics require existing NumPy environment')
 def test_endpoint_contact_is_not_proper_crossing(self):
  a=[[(0,0,0),(1,0,0),(0,1,0)]];b=[[(.5,.5,0),(.5,1,1),(.5,1,-1)]]
  self.assertEqual(v.triangle_contacts(a,b)[0].tolist(),[True]);self.assertEqual(v.proper_crossings(a,b).tolist(),[False])
 @unittest.skipUnless(importlib.util.find_spec('numpy'),'optional surface diagnostics require existing NumPy environment')
 def test_surface_deadline_even_without_any_pairs(self):
  rows=[{'role':'body','points':[(100,100,100),(101,100,100),(100,101,100)]}]+[{'role':'wheel','wheel':i,'points':[(0,0,0),(0,1,0),(0,0,1)]}for i in range(4)];wheels=[[0,0,0,.3,.2]for _ in range(4)]
  for clock in ([0,1000],[0,0,0,1000]):
   with self.subTest(clock=clock),mock.patch.object(v,'load',return_value=(wheels,rows,{})),mock.patch.object(v.time,'monotonic',side_effect=clock):
    with self.assertRaisesRegex(RuntimeError,'surface_deadline'):v.inspect_surfaces(Path('unused'),'unused',timeout=1)
 def test_matrix_quaternion_and_reflection(self):
  n={'translation':[1,2,3],'scale':[-2,2,2],'rotation':[0,math.sqrt(.5),0,math.sqrt(.5)]};m=v.node_matrix(n);self.assertAlmostEqual(m[2][0],2);self.assertEqual(m[0][3],1)
  with self.assertRaises(ValueError):v.node_matrix({'scale':[1,0,1]})
  with self.assertRaises(ValueError):v.node_matrix({'scale':[1e308]*3})
 def test_v1_numeric_roles(self):
  text='RACER_VEHICLE 1\nid "vehicle-'+('a'*64)+'"\nname "v1"\nmesh "'+('a'*64)+'.glb"\nsha256 '+('a'*64)+'\nsource_sha256 '+('b'*64)+'\nbody -1 -1 -1 1 1 1\n'+''.join('wheel '+x+' 0 0 0 .3 .2\n'for x in v.LABELS)+'groups 5\ngroup 0 -1\n'+''.join('group '+str(i+1)+' '+str(i)+'\n'for i in range(4))
  fields,wheels,roles=v.descriptor(text);self.assertEqual(roles[0],('body',None));self.assertEqual(roles[4],('wheel',3))
 def test_actual_v1_v2_roles_pin_and_transformed_geometry(self):
  with tempfile.TemporaryDirectory()as tmp:
   p=Path(tmp).resolve();binary=struct.pack('<9f3I',0,-2,-2,0,2,-2,0,0,2,0,1,2);d={'asset':{'version':'2.0'},'scene':0,'scenes':[{'nodes':[6]}],'nodes':[{'name':'body','mesh':0},{'name':'carrier','mesh':0}]+[{'name':x,'mesh':0}for x in v.LABELS]+[{'scale':[-2,2,2],'translation':[1,0,0],'children':list(range(6))}],'meshes':[{'primitives':[{'attributes':{'POSITION':0},'indices':1}]}],'accessors':[{'bufferView':0,'componentType':5126,'type':'VEC3','count':3},{'bufferView':1,'componentType':5125,'type':'SCALAR','count':3}],'bufferViews':[{'buffer':0,'byteOffset':0,'byteLength':36},{'buffer':0,'byteOffset':36,'byteLength':12}],'buffers':[{'byteLength':48}]};raw=pack(d,binary);sha=hashlib.sha256(raw).hexdigest();(p/(sha+'.glb')).write_bytes(raw)
   text='RACER_VEHICLE 2\nid "vehicle-'+sha+'"\nname "fixture"\nmesh "'+sha+'.glb"\nsha256 '+sha+'\nsource_sha256 '+'a'*64+'\nbody -9 -9 -9 9 9 9\n'+''.join('wheel '+x+' 1 0 0 .5 .2\n'for x in v.LABELS)+'groups 6\ngroup 0 body\ngroup 1 carrier FL\n'+''.join('group '+str(i+2)+' wheel '+x+'\n'for i,x in enumerate(v.LABELS));path=p/'fixture.vehicle';path.write_text(text);pin=hashlib.sha256(text.encode()).hexdigest();w,ts,identity=v.load(path,pin);self.assertEqual(len(ts),1);self.assertEqual(ts[0]['points'][0],(1.,-4.,-4.));self.assertEqual(identity['carrier_nodes_excluded'],[1]);r=v.inspect(path,pin);self.assertEqual(r['wheels'][0]['minimum_radial_excess_after_margin_m'],-.5)
   with self.assertRaisesRegex(ValueError,'descriptor_pin'):v.load(path,'0'*64)
   bad=text.replace('carrier FL','carrier XX');path.write_text(bad)
   with self.assertRaises(ValueError):v.load(path,hashlib.sha256(bad.encode()).hexdigest())
if __name__=='__main__':unittest.main()
