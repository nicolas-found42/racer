#!/usr/bin/env python3
"""New Ford source ownership/variant cases and whole actual-vertex regression."""
import copy,hashlib,json,math,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import prepare_ford_cohort as c
from prepare_gt4_vehicle import Geometry,PreparationError
class Checks(unittest.TestCase):
 def test_default_material_variants(self):
  d={'extensions':{'KHR_materials_variants':{'variants':[{'name':'default'},{'name':'other'}]}},'materials':[{},{}],'meshes':[{'primitives':[{'material':0,'extensions':{'KHR_materials_variants':{'mappings':[{'material':0,'variants':[0]},{'material':1,'variants':[1]}]}}}]}]};old=copy.deepcopy(d);r=c.default_variants(d);self.assertNotIn('extensions',d['meshes'][0]['primitives'][0]);self.assertEqual(d['materials'],old['materials']);self.assertEqual(len(r['removed_primitive_mappings']),1)
  for mutate in (lambda d:d['meshes'][0]['primitives'][0].update(material=1),lambda d:d['meshes'][0]['primitives'][0]['extensions'].update(unknown={})):
   bad=copy.deepcopy(old);mutate(bad)
   with self.assertRaises(PreparationError):c.default_variants(bad)
 def test_source_pin(self):
  with self.assertRaises(PreparationError):c.prepare_candidate(b'wrong','FOCUS_SVT',{})

def actual(root):
 result=[]
 for code,folder in [('FOCUS_SVT','focus-prepared-v2'),('F150','f150-prepared-v2')]:
  raw=(root/'assets/objects'/(c.PINS[code]+'.glb')).read_bytes();d,b=c.unpack(raw);r=json.loads(next((root/folder).glob('*.json')).read_text());out,ob=c.unpack((root/folder/(r['prepared_sha256']+'.glb')).read_bytes());assert bytes(b)==bytes(ob)
  for key in('materials','images','textures','samplers','accessors','bufferViews'):assert d.get(key)==out.get(key)
  g=Geometry(d,b);new=Geometry(out,ob);policy=r['cohort']['assembly_normalization'];carriers={int(k):v for k,v in policy['carrier_nodes'].items()};raw_to_new={out['nodes'][i]['extras']['racerCarrierSourceNode']:i for i in carriers};roles={v['node']:v['role']for v in r['binding_roles']};scene=next(s for s in d['scenes']if s.get('extras',{}).get('sourceTree')==0 and s.get('extras',{}).get('visibilityPreset')=='low_speed');sourceposes={};poses={}
  def walk(doc,index,parent_s,parent_t,dest):
   n=doc['nodes'][index];s=n.get('scale',[1]*3);t=n.get('translation',[0]*3);S=[s[k]*parent_s[k]for k in range(3)];T=[t[k]*parent_s[k]+parent_t[k]for k in range(3)];dest[index]=(S,T)
   for j in n.get('children',[]):walk(doc,j,S,T,dest)
  walk(d,scene['nodes'][0],[1]*3,[0]*3,sourceposes);walk(out,out['scenes'][0]['nodes'][0],[1]*3,[0]*3,poses);count=0
  for index,(scale,t)in sourceposes.items():
   n=d['nodes'][index]
   if'mesh'not in n:continue
   target=raw_to_new.get(index,index);S,T=poses[target];role=roles[target];assert out['nodes'][target]['mesh']==n['mesh']
   for pr in d['meshes'][n['mesh']]['primitives']:
    for p in g.values(pr['attributes']['POSITION']):
     before=[scale[k]*p[k]+t[k]for k in range(3)];after=[S[k]*p[k]+T[k]for k in range(3)];expected=before[:]
     if role.startswith('wheel '):
      wi=('FL','FR','RL','RR').index(role.split()[1]);center=r['source_hubs'][role.split()[1]];factor=r['wheel_radius_fitting'][wi]['radial_yz_scale']
      for k in(1,2):expected[k]=center[k]+(before[k]-center[k])*factor
     expected[1]+=r['ground_lift'];assert max(abs(after[k]-expected[k])for k in range(3))<1e-7;count+=1
     if role!='body':
      wi=('FL','FR','RL','RR').index(role.split()[1]);w=r['wheels'][wi];assert abs(after[0]-w['center'][0])<=w['width']/2+1e-7 and math.hypot(after[1]-w['center'][1],after[2]-w['center'][2])<=w['radius']+1e-7
  assert len(carriers)==4 and len(policy['static_wheel_owner_aliases'])==4
  result.append({'code':code,'vertices_independently_verified':count,'prepared_sha256':r['prepared_sha256'],'BIN_unchanged':True,'source_world_vertices_follow_only_explicit_radius_fit_and_lift':True,'carrier_wheel_containment':True,'runtime_player_eligible':False})
 return result
if __name__=='__main__':
 if len(sys.argv)>1:print(json.dumps(actual(Path(sys.argv[1])),indent=2))
 else:unittest.main()
