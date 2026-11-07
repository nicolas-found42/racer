#!/usr/bin/env python3
"""Source namespace/configuration pins and retained350Z/MX5 identity checks."""
import copy,hashlib,json,struct,sys,unittest,zlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from juiced2_registry import PROFILES,configuration
from juiced2_vehicle import filename_hash,require,PreparationError

def compiled(lines):
 strings=bytearray();offsets={}
 for line in lines:
  for s in line:
   if s not in offsets:offsets[s]=12+len(strings);strings.extend(s.encode()+b'\0')
 types=12+len(strings);formats=b''.join(b's'*len(line)+b'\n'for line in lines)+b'\x03';values=types+len(formats);return b'\x02'*4+struct.pack('>II',types,values)+strings+formats+b''.join(struct.pack('>I',offsets[s])for line in lines for s in line)
class Sparse:
 def __init__(self,regions):self.regions=regions;self.position=0;self.reads=0
 def seek(self,p):self.position=p
 def read(self,n):self.reads+=1;return self.regions.get(self.position,b'')[:n]
class Checks(unittest.TestCase):
 def fixture(self):
  lines=[['[BeginCar]','FIXTURE','Source fixture']]+[['STANDARD',key,value]for key,value in [('FWHEELS','WHEEL_FIXTURE'),('RWHEELS','WHEEL_FIXTURE'),('FTYRES','TYRE_PROFILE'),('RTYRES','TYRE_PROFILE'),('FCALIPERS','TEST_CALLIPER'),('RCALIPERS','TEST_CALLIPER'),('FDISCS','TEST_DISC'),('RDISCS','TEST_DISC')]];data=compiled(lines);packed=zlib.compress(data);row=(filename_hash('cardefs\\fixture.txt'),24,len(packed),len(data),4,1);profile={'bank':'fixture','script_record':row,'script_ordinal':2,'script_sha256':hashlib.sha256(data).hexdigest(),'configuration_filename':'cardefs\\fixture.txt'};regions={654769*2048+4+48:struct.pack('>6I',*row),654781*2048+24:packed};return profile,regions
 def test_exact_namespace_joins(self):
  self.assertEqual(filename_hash(PROFILES['MX5']['hierarchy']),3563377616);self.assertEqual(filename_hash(PROFILES['350Z']['hierarchy']),3705861116);self.assertEqual(filename_hash('models\\tyre_profile.boh'),162645771)
  for p in PROFILES.values():self.assertEqual(filename_hash(p['configuration_filename']),p['script_record'][0])
 def test_typed_config_join_and_mutations(self):
  profile,regions=self.fixture();r=configuration(Sparse(regions),profile,0,filename_hash,require);self.assertEqual(r['typed']['lines'][0]['fields'][1]['value'],'FIXTURE')
  for key,value in [('script_sha256','0'*64),('configuration_filename','cardefs\\wrong.txt'),('bank','wrong')]:
   bad=copy.deepcopy(profile);bad[key]=value
   with self.assertRaises(PreparationError):configuration(Sparse(regions),bad,0,filename_hash,require)
 def test_budget_before_read(self):
  profile,regions=self.fixture();row=list(profile['script_record']);row[3]=16000001;profile['script_record']=row;s=Sparse(regions)
  with self.assertRaisesRegex(PreparationError,'configuration_budget'):configuration(s,profile,0,filename_hash,require)
  self.assertEqual(s.reads,0)

def actual(root):
 results=[]
 for folder,expected,prior in [('350z-default-regression','9c99d140778180eb5193693a99a56570eccda74a0fe29378067b59ccc70a61e7',Path('experiments/2026-11-05-juiced2-vehicle/output/prepared-v5')),('350z-brakes-regression','6ac33b186ea3189874827d79ce844903e42838779f79c920efc83196cecfbd4c',Path('experiments/2026-11-05-juiced2-vehicle/output/stock-brakes-carriers-v3'))]:
  for suffix in ['.glb','.vehicle']:assert(root/folder/(expected+suffix)).read_bytes()==(prior/(expected+suffix)).read_bytes()
  results.append({'folder':folder,'prepared_sha256':expected,'GLB_and_descriptor_byte_identical':True})
 # Existing independent whole-vertex checker also resolves namedcarrier cylinder roles.
 sys.path.insert(0,str(Path(__file__).parent));from juiced2_vehicle_checks import actual as inspect
 inspect(root/'mx5-prepared-v1');results.append({'folder':'mx5-prepared-v1','prepared_sha256':'c46f0f0e2e77aebc2c4d426cb24be7a676682afadbf809e8f7a51de86568dc9a','actual_body_wheel_carrier_containment':True});return results
if __name__=='__main__':
 if len(sys.argv)>1:print(json.dumps(actual(Path(sys.argv[1])),indent=2))
 else:unittest.main()
