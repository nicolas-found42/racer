"""Known template filtering must not alter native wheels, material assets or transforms."""
import copy,hashlib,json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import strip_juiced2_template as s
ROOT=Path(__file__).resolve().parents[1]
SOURCE_DIR=ROOT/'experiments/2026-11-06-juiced2-expansion/output/mx5-hub-rest-v1'
SOURCE_SHA='d7e3cd0bc91ac248bd88e584e7b059a682f72bfaed00e4a34456981878779812'
class Checks(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  p=SOURCE_DIR/(SOURCE_SHA+'.vehicle');cls.text=p.read_text();cls.raw=p.with_suffix('.glb').read_bytes();cls.sha=p.stem;cls.d,cls.b=s.unpack(cls.raw)
 def run_filter(self,doc=None,text=None,template=None):
  raw=self.raw if doc is None else s.pack(doc,self.b);text=self.text if text is None else text;text=text.replace(self.sha,hashlib.sha256(raw).hexdigest());return s.strip(raw,text,hashlib.sha256(raw).hexdigest(),hashlib.sha256(text.encode()).hexdigest(),template or s.TEMPLATE_SHA)
 def test_preservation_and_exact_primitive_subset(self):
  raw,text,r=self.run_filter();d,b=s.unpack(raw);self.assertEqual(self.b,b);self.assertEqual(d['nodes'],self.d['nodes']);self.assertEqual(d['materials'],self.d['materials']);self.assertEqual(d['images'],self.d['images']);self.assertEqual(d['accessors'],self.d['accessors']);changed={c['node']for c in r['changes']};self.assertEqual(len(changed),4)
  for i,n in enumerate(d['nodes']):
   if 'mesh'not in n:continue
   original=self.d['meshes'][n['mesh']];actual=d['meshes'][n['mesh']]
   self.assertEqual(actual,dict(original,primitives=original['primitives'][:1])if i in changed else original)
  oldrows=[x for x in self.text.splitlines()if x.startswith(('wheel ','body ','group '))];newrows=[x for x in text.splitlines()if x.startswith(('wheel ','body ','group '))];self.assertEqual(oldrows,newrows)
 def test_reject_unknown_material_or_node(self):
  for mutate in ('material','node'):
   d=copy.deepcopy(self.d);i=next(i for i,n in enumerate(d['nodes'])if n.get('name')=='ADAPTED_NATIVE_TOYO_TYRE_FL')
   if mutate=='node':d['nodes'][i]['name']='ADAPTED_NATIVE_TOYO_TYRE_UNKNOWN'
   else:d['materials'][d['meshes'][d['nodes'][i]['mesh']]['primitives'][1]['material']]['name']='unknown'
   with self.assertRaises(ValueError):self.run_filter(d)
 def test_reject_missing_binding_and_wrong_native_pin(self):
  with self.assertRaises(ValueError):self.run_filter(template='0'*64)
  text=self.text;index=next(i for i,n in enumerate(self.d['nodes'])if n.get('name')=='ADAPTED_NATIVE_TOYO_TYRE_FL');line=next(x for x in text.splitlines()if x.startswith('group '+str(index)+' '));text=text.replace(line,line.replace('wheel FL','body'))
  with self.assertRaisesRegex(ValueError,'template_binding'):self.run_filter(text=text)
 def test_reject_inactive_template_mesh_alias(self):
  d=copy.deepcopy(self.d);node=next(n for n in d['nodes']if n.get('name')=='ADAPTED_NATIVE_TOYO_TYRE_FL');d['nodes'].append({'name':'UNREACHABLE_RETAINED_SOURCE','mesh':node['mesh']})
  with self.assertRaisesRegex(ValueError,'template_mesh_alias'):self.run_filter(d)
 def test_reject_unexpected_structure_and_shared_mesh(self):
  d=copy.deepcopy(self.d);i=next(i for i,n in enumerate(d['nodes'])if n.get('name')=='ADAPTED_NATIVE_TOYO_TYRE_FL');d['meshes'][d['nodes'][i]['mesh']]['primitives'].reverse()
  with self.assertRaisesRegex(ValueError,'unknown_template_structure'):self.run_filter(d)
  d=copy.deepcopy(self.d);d['nodes'][1]['mesh']=d['nodes'][0]['mesh']
  with self.assertRaisesRegex(ValueError,'unbound_or_shared_mesh'):self.run_filter(d)
if __name__=='__main__':
 if not all((SOURCE_DIR/(SOURCE_SHA+suffix)).is_file()for suffix in('.glb','.vehicle')):
  print('SKIP: retained pinned MX5 tyre-fit source inputs unavailable',file=sys.stderr);sys.exit(77)
 unittest.main()
