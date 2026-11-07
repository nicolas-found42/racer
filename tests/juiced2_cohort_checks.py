"""Source-independent selector/role failures; no ISO, GPU or playable-roster claim."""
import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from juiced2_cohort import assembly_contract,tyre_materials
from juiced2_vehicle import filename_hash
from juiced2_registry import PROFILES

def fixture():
 def node(name,geometry='NONE',x=0,z=0):return {'name':name,'geometry':geometry,'offset':len(name),'matrix':[1,0,0,x,0,1,0,.3,0,0,1,z,0,0,0,1]}
 nodes=[node('Fixture_ROOT'),node('body','FIXTURE_BODY')]+[node('WHEEL_'+s,x=-1 if s.endswith('L')else 1,z=1 if s.startswith('F')else-1)for s in('FL','FR','RL','RR')]+[node('body_DEAD','FIXTURE_DAMAGED')]
 standard={'FWHEELS':'WHEEL_Fixture','RWHEELS':'WHEEL_Fixture','FTYRES':'TYRE_PROFILE','RTYRES':'TYRE_PROFILE','FCALIPERS':'TEST_CALLIPER','RCALIPERS':'TEST_CALLIPER','FDISCS':'TEST_DISC','RDISCS':'TEST_DISC'}
 keys={filename_hash('mesh\\FIXTURE_BODY.xem'),filename_hash('mesh\\WHEEL_Fixture.xem')};return nodes,standard,keys
class Checks(unittest.TestCase):
 def resolve(self,n=None,s=None,k=None):
  N,S,K=fixture();return assembly_contract('Fixture',n or N,s or S,k if k is not None else K,set(),filename_hash)
 def test_case_preserving_native_join_and_omissions(self):
  r=self.resolve();self.assertEqual(r['status'],'static_selector_supported');self.assertEqual(r['native_root'],'Fixture_ROOT');self.assertFalse(r['runtime_player_eligible']);self.assertEqual([n['name']for n in r['selected_nodes']],['body']);self.assertIn('authored_static_state_exclusion',[n['reason']for n in r['omitted_nodes']])
 def test_shared_lookup_and_missing_mesh(self):
  n,s,k=fixture();body=filename_hash('mesh\\FIXTURE_BODY.xem');r=assembly_contract('Fixture',n,s,k-{body},{body},filename_hash);self.assertEqual(r['selected_nodes'][0]['bank'],'shared')
  self.assertIn('missing_body_mesh:body',self.resolve(k=k-{body})['reasons'])
 def test_duplicate_wheel_and_wrong_side_rejected(self):
  n,s,k=fixture();n.append(copy.deepcopy(n[2]));self.assertIn('four_native_pivots',self.resolve(n)['reasons']);n,s,k=fixture();n[2]['matrix'][3]=1;self.assertIn('native_wheel_side',self.resolve(n)['reasons'])
 def test_nonidentity_native_wheel_frame_is_not_dropped(self):
  n,s,k=fixture();n[2]['matrix'][0]=2;self.assertIn('unsupported_wheel_frame',self.resolve(n)['reasons'])
 def test_no_root_or_front_guessing(self):
  n,s,k=fixture();n[0]['name']='Other_ROOT';self.assertIn('native_root_identity',self.resolve(n)['reasons']);n,s,k=fixture();n[2]['matrix'][11]=-4;self.assertIn('native_front_axis',self.resolve(n)['reasons'])
 def test_brake_tyre_or_distinct_rim_declaration_not_substituted(self):
  for field,value,reason in [('FDISCS','BRAKE_DISC_DRUM','unsupported_brake_declaration'),('RTYRES','UNKNOWN','procedural_tyre_declaration'),('RWHEELS','OTHER','rim_declaration')]:
   n,s,k=fixture();s[field]=value;self.assertIn(reason,self.resolve(s=s)['reasons'])
 def test_unknown_toyo_source_rejected_before_parser(self):
  with self.assertRaisesRegex(ValueError,'shared_toyo_pin'):tyre_materials(b'unknown',lambda b:self.fail('must not parse unknown source'))
 def test_only_six_explicit_profiles(self):
  self.assertEqual(set(PROFILES),{'350Z','MX5','Z4','MINI','CHARGER_RT','KOENIGSEGG'})
if __name__=='__main__':unittest.main()
