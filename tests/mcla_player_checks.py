#!/usr/bin/env python3
"""Pinned complete-player asset checks; no native game or GPU execution."""
import copy,hashlib,json,math,shlex,struct,sys,unittest,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import prepare_mcla_player as m
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'assets/local/carmodels/objects'/ (m.SOURCE_SHA+'.glb')
PROOF=ROOT/'experiments/2026-11-05-mcla-vehicle/output/player-native-proof.json'

def inspect(source,directory):
    def decode(raw):
        assert raw[:4]==b'glTF' and struct.unpack_from('<I',raw,8)[0]==len(raw);n=struct.unpack_from('<I',raw,12)[0];d=json.loads(raw[20:20+n]);at=20+n;size,kind=struct.unpack_from('<II',raw,at);assert kind==0x004e4942;return d,raw[at+8:at+8+size]
    old,ob=decode(Path(source).read_bytes());directory=Path(directory);tokens=[shlex.split(x) for x in next(directory.glob('*.vehicle')).read_text().splitlines()];fields={x[0]:x[1:] for x in tokens if x[0] not in ('wheel','group')};raw=(directory/fields['mesh'][0]).read_bytes();d,b=decode(raw)
    assert hashlib.sha256(raw).hexdigest()==fields['sha256'][0];assert hashlib.sha256(Path(source).read_bytes()).hexdigest()==fields['source_sha256'][0];assert b[:len(ob)]==ob
    for key in ('images','textures','samplers','extensions'):assert old.get(key)==d.get(key)
    materials=copy.deepcopy(d['materials']);policy=d['extras']['racerPreparation'].get('material_policy')
    if policy:
        for change in policy['changes']:
            index=change['index'];current=materials[index];expected=copy.deepcopy(change['source_material']);shader=expected['extras']['sourceShader'];assert shader in ('CarGlass','BlackOpaqueGlass')
            expected['pbrMetallicRoughness']['baseColorFactor']=[.08,.12,.16,.35] if shader=='CarGlass' else [.025,.025,.03,1.]
            expected['alphaMode']='BLEND' if shader=='CarGlass' else 'OPAQUE';assert current==expected;materials[index]=change['source_material']
    assert materials==old['materials']
    def read(doc,buffer,index):
        a=doc['accessors'][index];v=doc['bufferViews'][a['bufferView']];fmt,size={5121:('B',1),5123:('H',2),5125:('I',4),5126:('f',4)}[a['componentType']];n={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}[a['type']];at=v.get('byteOffset',0)+a.get('byteOffset',0);stride=v.get('byteStride',size*n);return [struct.unpack_from('<'+fmt*n,buffer,at+i*stride) for i in range(a['count'])]
    for mesh in old['meshes']:
        for p in mesh['primitives']:
            for attr,index in p['attributes'].items():
                before=read(old,ob,index);after=read(d,b,index);expected=[tuple(-v if axis==2 or(attr=='TANGENT'and axis==3) else v for axis,v in enumerate(row)) for row in before] if attr in ('POSITION','NORMAL','TANGENT') else before;assert after==expected
            before=read(old,ob,p['indices']);assert read(d,b,p['indices'])==[v for i in range(0,len(before),3) for v in (before[i],before[i+2],before[i+1])]
    groups={int(x[1]):int(x[2]) for x in tokens if x[0]=='group'};wheels={x[1]:list(map(float,x[2:])) for x in tokens if x[0]=='wheel'};bounds=list(map(float,fields['body']));lift=d['nodes'][-1]['translation'][1];vertices=triangles=0
    assert len(groups)==len(old['nodes'])==76 and d['nodes'][-1]['children']==list(range(76))
    for ni,n in enumerate(old['nodes']):
        M=n['matrix'];N=d['nodes'][ni]['matrix'];expected=[-v if(i%4==2)!=(i//4==2) else v for i,v in enumerate(M)]
        fit=d['extras']['racerPreparation'].get('manufacturer_assisted_fit');wheel=groups[ni];factor=1.0
        if fit and wheel>=0:
            factor=fit['wheels'][wheel]['radial_factor'];center=wheels[m.LABELS[wheel]][:3];center[1]-=lift
            ground_policy=d['extras']['racerPreparation'].get('flat_ground_rest')
            if ground_policy and wheel in (0,1):center[1]-=next(row['world_y_delta'] for row in ground_policy['changes'] if row['label']==m.LABELS[wheel])
            for axis in (1,2):
                for col in range(3):expected[col*4+axis]*=factor
                expected[12+axis]=center[axis]+factor*(expected[12+axis]-center[axis])
        ground=d['extras']['racerPreparation'].get('flat_ground_rest');ground_shift=0
        if ground and wheel in (0,1):
            changes=[row for row in ground['changes'] if row['label']==m.LABELS[wheel]];assert len(changes)==1;change=changes[0];assert abs(change['world_y_delta']-(change['radius']-change['center_y_before']))<1e-12
            ground_shift=change['world_y_delta'];expected[13]+=ground_shift
        assert max(abs(a-b) for a,b in zip(N,expected))<1e-12
        for p in old['meshes'][n['mesh']]['primitives']:
            before=read(old,ob,p['attributes']['POSITION']);after=read(d,b,p['attributes']['POSITION']);vertices+=len(before);triangles+=len(read(old,ob,p['indices']))//3
            for a,q in zip(before,after):
                original=[sum(M[j*4+i]*a[j] for j in range(3))+M[12+i] for i in range(3)];point=[sum(N[j*4+i]*q[j] for j in range(3))+N[12+i]+(lift if i==1 else 0) for i in range(3)]
                expected_point=[original[0],original[1],-original[2]]
                if fit and wheel>=0:
                    for axis in (1,2):expected_point[axis]=center[axis]+factor*(expected_point[axis]-center[axis])
                expected_point[1]+=lift+ground_shift
                assert max(abs(point[i]-expected_point[i]) for i in range(3))<1e-7
                if groups[ni]<0:assert all(bounds[i]-1e-8<=point[i]<=bounds[i+3]+1e-8 for i in range(3))
                else:
                    x,y,z,r,w=wheels[m.LABELS[groups[ni]]];assert abs(point[0]-x)<=w/2+1e-8 and math.hypot(point[1]-y,point[2]-z)<=r+1e-8
    return {'prepared_sha256':fields['sha256'][0],'source_sha256':fields['source_sha256'][0],'groups':len(groups),'vertices':vertices,'triangles':triangles,'all_source_geometry_world_normalization_verified':True,'manufacturer_assisted_radial_fit':bool(d['extras']['racerPreparation'].get('manufacturer_assisted_fit')),'all_original_binary_image_data_preserved':True,'material_changes_match_explicit_allowlist':True,'all_descriptor_envelopes_verified':True,'runtime_player_eligible':d['extras']['racerPreparation']['runtime_player_eligible']}

@unittest.skipUnless(SOURCE.exists() and PROOF.exists(),'retained pinned model/native-proof unavailable')
class Checks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.raw=SOURCE.read_bytes();cls.proof=PROOF.read_bytes();cls.d,cls.binary=m.g.unpack(cls.raw)
    def fixture(self):return copy.deepcopy(self.d),json.loads(self.proof)
    def prepare_modified(self,d,p):
        data=m.g.pack(d,self.binary);proof=json.dumps(p).encode();p['source_sha256']=hashlib.sha256(data).hexdigest();proof=json.dumps(p).encode();return m.prepare(data,proof,source_sha=hashlib.sha256(data).hexdigest(),proof_sha=hashlib.sha256(proof).hexdigest())
    def test_pinned_complete_candidate(self):
        raw,descriptor,r=m.prepare(self.raw,self.proof);self.assertEqual(len(r['groups']),76);self.assertEqual(sum(w>=0 for _,w in r['groups']),12);self.assertFalse(r['runtime_player_eligible']);self.assertEqual(r['role'],'player-candidate');self.assertAlmostEqual(r['wheelbase_native_units'],2.630825996398926)
    def test_exact_shader_policy_and_allowlisted_changes(self):
        raw,_,r=m.prepare(self.raw,self.proof,racer_glass_policy=True);d,_=m.g.unpack(raw);changed={x['index'] for x in r['material_changes']}
        expected={i for i,x in enumerate(self.d['materials']) if x.get('extras',{}).get('sourceShader') in ('CarGlass','BlackOpaqueGlass')}
        self.assertEqual(changed,expected);self.assertEqual(changed,{3,10,43,106})
        for i,material in enumerate(d['materials']):
            if i not in changed:self.assertEqual(material,self.d['materials'][i])
        self.assertEqual(d['materials'][86],self.d['materials'][86]);self.assertEqual(d['materials'][137],self.d['materials'][137])
    def test_optional_manufacturer_fit_preserves_body_width_and_native_pivots(self):
        original,_,base=m.prepare(self.raw,self.proof);raw,_,r=m.prepare(self.raw,self.proof,roadster_radius_fit=True)
        self.assertEqual(r['source_native_axle_pivots'],base['source_native_axle_pivots'])
        for i,w in enumerate(r['wheels']):
            self.assertAlmostEqual(w['radius'],.32985 if i<2 else .33885,places=7)
            self.assertEqual(w['width'],base['wheels'][i]['width'])
        self.assertFalse(r['runtime_player_eligible']);self.assertIn('Racer-authored',r['normalization']['manufacturer_assisted_fit']['authority'])
        for i in (0,2,3,5):self.assertEqual(r['body'][i],base['body'][i])
    def test_pins_fail_closed(self):
        with self.assertRaises(m.g.PreparationError):m.prepare(self.raw+b' ',self.proof)
    def test_ambient_and_unknown_omission_rejected(self):
        d,p=self.fixture();d['extras']['vehicle']='va_350z_04'
        with self.assertRaisesRegex(m.g.PreparationError,'not_proven_player'):self.prepare_modified(d,p)
        d,p=self.fixture();d['extras']['omitted'].append('missing-door.xrsc')
        with self.assertRaisesRegex(m.g.PreparationError,'unexplained_omission'):self.prepare_modified(d,p)
    def test_native_binding_pose_and_attachment_rejected(self):
        d,p=self.fixture();d['nodes'][0]['extras']['nativeBoneIndex']=0
        with self.assertRaises(m.g.PreparationError):self.prepare_modified(d,p)
        d,p=self.fixture();d['nodes'][0]['matrix'][12]+=.1
        with self.assertRaisesRegex(m.g.PreparationError,'native_node_pose_mismatch'):self.prepare_modified(d,p)
        d,p=self.fixture();d['extras']['parts'][5]['attachment_native_name']='fake'
        with self.assertRaisesRegex(m.g.PreparationError,'attachment_bone_mismatch'):self.prepare_modified(d,p)
    def test_coordinated_attachment_pose_mutation_rejected(self):
        d,p=self.fixture();part=d['extras']['parts'][5];part['matrix'][12]+=.01
        for n in d['nodes']:
            if n['name'].startswith(part['file']+'@'+part['bone']+'/'):n['matrix'][12]+=.01
        with self.assertRaisesRegex(m.g.PreparationError,'native_attachment_outer_pose'):self.prepare_modified(d,p)
    def test_native_skinning_and_missing_wheels_rejected(self):
        d,p=self.fixture();next(iter(p['resources'].values()))['skinned'][0]=True
        with self.assertRaisesRegex(m.g.PreparationError,'native_source_or_skin'):self.prepare_modified(d,p)
        d,p=self.fixture();d['extras']['wheels'].pop()
        with self.assertRaisesRegex(m.g.PreparationError,'shared_wheel_join'):self.prepare_modified(d,p)
    def test_flat_ground_optional_shift_exact_front_only(self):
        _,_,base=m.prepare(self.raw,self.proof,roadster_radius_fit=True,racer_glass_policy=True)
        raw,_,r=m.prepare(self.raw,self.proof,roadster_radius_fit=True,racer_glass_policy=True,flat_ground_rest=True)
        self.assertEqual(r['body'],base['body']);self.assertEqual(r['wheels'][2:],base['wheels'][2:])
        for i in (0,1):
            self.assertAlmostEqual(r['wheels'][i]['center'][1],r['wheels'][i]['radius']);self.assertAlmostEqual(base['wheels'][i]['center'][1]-r['wheels'][i]['center'][1],.009)
            self.assertEqual(r['wheels'][i]['width'],base['wheels'][i]['width'])
        with self.assertRaisesRegex(m.g.PreparationError,'flat_ground_requires'):m.prepare(self.raw,self.proof,flat_ground_rest=True)
    def test_independent_checker_rejects_coupled_unknown_matrix_change(self):
        raw,descriptor,r=m.prepare(self.raw,self.proof,roadster_radius_fit=True,racer_glass_policy=True,flat_ground_rest=True)
        d,b=m.g.unpack(raw);rear=next(index for index,wheel in r['groups'] if wheel==2);d['nodes'][rear]['matrix'][13]+=.001;changed=m.g.pack(d,b);digest=hashlib.sha256(changed).hexdigest()
        with tempfile.TemporaryDirectory() as temporary:
            directory=Path(temporary);(directory/(digest+'.glb')).write_bytes(changed);(directory/(digest+'.vehicle')).write_text(descriptor.replace(r['prepared_sha256'],digest))
            with self.assertRaises(AssertionError):inspect(SOURCE,directory)
    def test_position_work_budget(self):
        d,p=self.fixture();index=d['meshes'][0]['primitives'][0]['attributes']['POSITION'];d['accessors'][index]['count']=1000001
        with self.assertRaisesRegex(m.g.PreparationError,'position_work_budget'):self.prepare_modified(d,p)
    def test_triangle_budget(self):
        d,p=self.fixture();index=d['meshes'][0]['primitives'][0]['indices'];d['accessors'][index]['count']=1500003
        with self.assertRaisesRegex(m.g.PreparationError,'index_work_budget'):self.prepare_modified(d,p)
    def test_current_actual_artifact(self):
        directory=ROOT/'experiments/2026-11-05-mcla-vehicle/output/player-350z-prepared-v1';self.assertEqual(inspect(SOURCE,directory)['triangles'],103564)

if __name__=='__main__':
    if not SOURCE.is_file() or not PROOF.is_file():
        print('SKIP: retained pinned MCLA player source/native proof unavailable',file=sys.stderr);sys.exit(77)
    if len(sys.argv)>1 and sys.argv[1]=='--inspect':print(json.dumps(inspect(sys.argv[2],sys.argv[3]),indent=2))
    else:unittest.main()
