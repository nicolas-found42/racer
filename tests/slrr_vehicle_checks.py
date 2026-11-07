#!/usr/bin/env python3
import json,math,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from slrr_vehicle import pose,inverse,multiply,identity,config,slot_frame,append_scene
class AssemblyChecks(unittest.TestCase):
 def test_inverse_and_ypr(self):
  m=pose([1,2,3,.3,-.2,.7]);p=multiply(m,inverse(m))
  for i in range(4):
   for j in range(4):self.assertAlmostEqual(p[i][j],float(i==j),places=12)
  self.assertAlmostEqual(pose([0,0,0,math.pi/2,0,0])[0][2],1.)
 def test_parent_child_pivots(self):
  parent=pose([1,2,3,0,0,0]);child=pose([.1,.2,.3,0,0,0]);m=multiply(parent,inverse(child))
  self.assertAlmostEqual(m[0][3],.9);self.assertAlmostEqual(m[2][3],2.7)
 def test_finite_and_duplicate(self):
  with self.assertRaises(ValueError):pose([0,0,0,math.nan,0,0])
  c=config(b'slot 0 0 0 0 0 0 1\nslot 1 0 0 0 0 0 1\n')
  with self.assertRaises(ValueError):slot_frame(c,1)
 def test_wheel_frame(self):
  c=config(b'wheel 1 2 3 0 0 0\nslot .1 0 0 0 0 0 101\nslottype 101\n')
  self.assertAlmostEqual(slot_frame(c,101)[0][3],1.1)
 def test_remapping(self):
  s={'buffers':[{'uri':'data:','byteLength':0}],'bufferViews':[{'buffer':0}],'accessors':[{'bufferView':0}], 'materials':[{}], 'meshes':[{'primitives':[{'indices':0,'attributes':{'POSITION':0},'material':0}]}]}
  d={'scenes':[{'nodes':[]}]}
  append_scene(d,s,'a',identity());append_scene(d,s,'b',identity())
  p=d['meshes'][1]['primitives'][0];self.assertEqual(p['indices'],1);self.assertEqual(p['attributes']['POSITION'],1);self.assertEqual(p['material'],1)
  self.assertEqual(d['bufferViews'][1]['buffer'],1);self.assertEqual(d['accessors'][1]['bufferView'],1)
if __name__=='__main__':unittest.main()
