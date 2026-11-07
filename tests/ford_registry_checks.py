"""Strict Ford registry and hub contract regressions; actual output mode is explicit."""
import copy,hashlib,json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import prepare_ford_cohort as c
from ford_cohort_registry import PROFILES
from prepare_gt4_vehicle import PreparationError
class Checks(unittest.TestCase):
 def test_all35_source_statuses_and_unknown_approval_rejected(self):
  self.assertEqual(len(PROFILES),35);self.assertEqual(len(c.SUPPORTED_CODES),21)
  self.assertEqual(PROFILES['49_COUPE_MOVIE']['approval_occurrences'],['1','0'])
  for code in ('49_COUPE_MOVIE','COBRA_STOCK','not-a-real-car'):
   if code in c.SUPPORTED_CODES:continue
   with self.assertRaisesRegex(PreparationError,'source_approval_unknown'):c.profile(code)
  self.assertEqual(sum(p['approval_occurrences']==['0']for p in PROFILES.values()),13)
 def test_explicit_research_retains_all_unknown_approval_contracts(self):
  for code,p in PROFILES.items():
   if p['approval_occurrences']==['1']:continue
   with self.assertRaisesRegex(PreparationError,'source_approval_unknown'):c.profile(code)
   contract=c.profile(code,research_any_approval=True);self.assertEqual(contract['source_sha256'],p['source_sha256']);self.assertEqual(len(contract['config_pins']),3)
  with self.assertRaisesRegex(PreparationError,'research_mode'):c.profile('49_COUPE_MOVIE',research_any_approval=1)
 def test_legacy_pins_names_stay_exact(self):
  for code in ('FOCUS_SVT','F150'):
   p=c.profile(code);self.assertEqual(p['source_sha256'],c.PINS[code]);self.assertEqual(p['config_pins'],c.CONFIG_PINS[code]);self.assertEqual(p['name'],c.NAMES[code])
 def hub_fixture(self,carrier):
  nodes=[{'children':[]}]
  for index,suffix in enumerate(c.SUFFIXES):
   h=len(nodes);nodes[0]['children'].append(h);nodes.append({'translation':[index,1,2],'extras':{'sourceNames':['HUB_'+suffix]},'children':[h+1]});nodes.append({'mesh':index+4,'extras':{'sourceNames':['WHEEL_STATIC']}})
   if carrier:nodes[h]['mesh']=index
  return {'nodes':nodes,'scenes':[{'nodes':[0],'extras':{'sourceTree':0,'visibilityPreset':'low_speed'}}]}
 def test_optional_carrier_preserves_hub_static_owner_contract(self):
  for carrier in (False,True):
   d=self.hub_fixture(carrier);before=copy.deepcopy(d);r=c.normalize_assembly(d);self.assertEqual(len(r['static_wheel_owner_aliases']),4);self.assertEqual(len(r['carrier_nodes']),4 if carrier else 0)
   for index,suffix in enumerate(c.SUFFIXES):self.assertIn('WHEEL_'+suffix,d['nodes'][2+2*index]['extras']['sourceNames'])
   if carrier:
    for ci,wi in r['carrier_nodes'].items():self.assertEqual(d['nodes'][ci]['translation'],[wi,1,2]);self.assertEqual(d['nodes'][ci]['mesh'],before['nodes'][1+2*wi]['mesh'])
 def test_reject_duplicate_hub_and_wrong_physics_semantics(self):
  d=self.hub_fixture(False);d['nodes'][3]['extras']['sourceNames']=['HUB_FRONT_LEFT']
  with self.assertRaisesRegex(PreparationError,'hub_owner'):c.normalize_assembly(d)
  physics={'files':[{'file':n,'sha256':v}for n,v in c.CONFIG_PINS['FOCUS_SVT'].items()],'axles':[{'radius':.1,'width':.1}]*2}
  with self.assertRaisesRegex(PreparationError,'config_semantics_pin'):c.prepare_candidate(b'not source','FOCUS_SVT',physics)

def actual(root):
 ROOT=Path(__file__).resolve().parents[1];rows=json.loads((root/'preparation-coverage.json').read_text())['rows'];proof=[]
 for code,folder in [('FOCUS_SVT','focus-prepared-v2'),('F150','f150-prepared-v2')]:
  row=next(r for r in rows if r['code']==code);p=ROOT/row['descriptor'];old=ROOT/'experiments/2026-11-06-ford-expansion/output'/folder/p.name;assert p.read_bytes()==old.read_bytes()and p.with_suffix('.glb').read_bytes()==old.with_suffix('.glb').read_bytes();physics=c.source_physics(root/'config'/code,'ford-racing-2/'+code);regenerated,descriptor,_=c.prepare_candidate((ROOT/row['source_path']).read_bytes(),code,physics);assert regenerated==old.with_suffix('.glb').read_bytes()and descriptor.encode()==old.read_bytes();proof.append({'code':code,'prepared_sha256':p.stem,'GLB_and_descriptor_byte_identical':True,'current_converter_regenerated_exact_legacy_bytes':True})
 return proof
if __name__=='__main__':
 if len(sys.argv)==2:print(json.dumps(actual(Path(sys.argv[1])),indent=2))
 else:unittest.main()
