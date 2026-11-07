#!/usr/bin/env python3
"""Exact retained-source guards for optional Ford source-rest role adaptation."""
import copy,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import ford_static_rest as f
from prepare_gt4_vehicle import unpack
OUT=ROOT/'experiments/2026-11-06-ford-cohort/output'
class Checks(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  if not (OUT/'glb-acquisition.json').exists():raise unittest.SkipTest('retained Ford sources absent')
  rows=json.loads((OUT/'glb-acquisition.json').read_text())+json.loads((OUT/'glb-acquisition-research.json').read_text());cls.docs={}
  for code in ('EX','INDIGO'):
   p=ROOT/next(r['path']for r in rows if r['code']==code)
   if not p.is_file():raise unittest.SkipTest('exact retained source absent')
   cls.docs[code]=unpack(p.read_bytes())[0]
 def run_normalize(self,code,mutate=None):
  d=copy.deepcopy(self.docs[code])
  if mutate:mutate(d)
  return d,f.normalize(d,code,f.PROFILES[code]['source_sha256'])
 def test_preservation(self):
  for code in self.docs:
   before=self.docs[code];after,policy=self.run_normalize(code)
   self.assertEqual(before['meshes'],after['meshes']);self.assertEqual(len(after['nodes']),len(before['nodes'])+4)
   for row in policy['clones']:
    expected=copy.deepcopy(before['nodes'][row['source_node']]);expected.pop('mesh');self.assertEqual(expected,after['nodes'][row['source_node']]);self.assertEqual([],after['nodes'][row['node']]['extras']['sourceNames'])
   if code=='INDIGO':
    for i in (31,119,270):self.assertEqual(before['nodes'][i],after['nodes'][i])
 def test_source_pin(self):
  with self.assertRaises(ValueError):f.normalize(copy.deepcopy(self.docs['EX']),'EX','0'*64)
  with self.assertRaises(ValueError):f.normalize(copy.deepcopy(self.docs['EX']),'F150',f.PROFILES['EX']['source_sha256'])
 def test_native_identity(self):
  for field,value in [('serializedNodeOffset',0),('geometryRecord',0),('sourceNames',['SUSPENSION_WRONG'])]:
   with self.assertRaises(ValueError):self.run_normalize('EX',lambda d:d['nodes'][146]['extras'].__setitem__(field,value))
 def test_alias_identity_and_sharing(self):
  for field,value in [('serializedNodeOffset',0),('geometryRecord',0),('flags',0)]:
   with self.assertRaises(ValueError):self.run_normalize('INDIGO',lambda d:d['nodes'][210]['extras'].__setitem__(field,value))
  with self.assertRaises(ValueError):self.run_normalize('INDIGO',lambda d:d['nodes'][209].__setitem__('children',[]))
  with self.assertRaises(ValueError):self.run_normalize('INDIGO',lambda d:d['nodes'][119].__setitem__('mesh',30))
 def test_active_alias_mesh_sharing(self):
  def mutate(d):
   clone=copy.deepcopy(d['nodes'][210]);d['nodes'].append(clone);d['nodes'][209]['children'].append(len(d['nodes'])-1)
  with self.assertRaises(ValueError):self.run_normalize('INDIGO',mutate)
 def test_mode_type(self):
  from prepare_ford_cohort import prepare_candidate
  with self.assertRaisesRegex(ValueError,'static_suspension_mode'):prepare_candidate(b'','EX',{},static_suspension_rest='yes')
 def test_root_frame(self):
  def mutate(d):
   scene=next(s for s in d['scenes']if s.get('extras',{}).get('sourceTree')==0 and s.get('extras',{}).get('visibilityPreset')=='low_speed');d['nodes'][scene['nodes'][0]]['translation']=[1,0,0]
  with self.assertRaises(ValueError):self.run_normalize('EX',mutate)
if __name__=='__main__':
 result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks));sys.exit(77 if result.skipped else (0 if result.wasSuccessful()else 1))
