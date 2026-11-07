#!/usr/bin/env python3
"""Local-pinned expansion tests; independent accessor/world-geometry reader."""
import copy,hashlib,json,math,shlex,struct,sys,unittest,tempfile
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import prepare_mcla_expansion as m
ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/'experiments/2026-11-06-mcla-expansion/output'
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
    assert len(groups)==len(old['nodes']) and d['nodes'][-1]['children']==list(range(len(old['nodes'])))
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

class Checks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs={}
        for code,c in m.REGISTRY.items():
            source=OUTPUT/'source-store/objects'/(c['source']+'.glb');proof=OUTPUT/(code+'-native-proof.json')
            if not source.is_file() or not proof.is_file():raise unittest.SkipTest('retained pinned expansion source/proof unavailable')
            cls.inputs[code]=(source.read_bytes(),proof.read_bytes())
    def test_pinned_actual_candidates(self):
        for code,(raw,proof) in self.inputs.items():
            with self.subTest(code=code):
                prepared,descriptor,r=m.prepare(raw,proof,code,racer_glass_policy=True)
                self.assertEqual(r['catalog_id'],'midnight-club-los-angeles/'+code);self.assertFalse(r['runtime_player_eligible']);self.assertEqual(r['role'],'player-candidate')
                with tempfile.TemporaryDirectory() as folder:
                    folder=Path(folder);(folder/(r['prepared_sha256']+'.glb')).write_bytes(prepared);(folder/(r['prepared_sha256']+'.vehicle')).write_text(descriptor)
                    source=folder/'source.glb';source.write_bytes(raw);checked=inspect(source,folder);self.assertTrue(checked['all_descriptor_envelopes_verified'])
    def test_source_pin_and_ambient_rejected(self):
        raw,proof=next(iter(self.inputs.values()))
        with self.assertRaisesRegex(m.g.PreparationError,'unsupported_player_pin'):m.prepare(raw,proof,'va_350z_04')
        with self.assertRaisesRegex(m.g.PreparationError,'source_or_proof_pin'):m.prepare(raw+b' ',proof,'vp_frd_mustang_06')
    def test_distinct_shared_native_model_counts(self):
        for code,(raw,proof) in self.inputs.items():
            d,_=m.g.unpack(raw);groups,centers=m.proof_ownership(d,json.loads(proof),code)
            expected=2 if code=='vp_frd_mustang_06' else 3
            for wheel in range(4):self.assertEqual(list(groups.values()).count(wheel),expected)
    def test_missing_and_duplicate_native_instances_rejected(self):
        for code,(raw,proof) in self.inputs.items():
            d,_=m.g.unpack(raw);p=json.loads(proof);d['nodes'].pop()
            with self.assertRaises(m.g.PreparationError):m.proof_ownership(d,p,code)
            d,_=m.g.unpack(raw);d['nodes'].append(copy.deepcopy(d['nodes'][0]))
            with self.assertRaisesRegex(m.g.PreparationError,'duplicate_model_instance'):m.proof_ownership(d,p,code)
    def test_unexplained_omission_and_ambient_rejected(self):
        for code,(raw,proof) in self.inputs.items():
            d,_=m.g.unpack(raw);p=json.loads(proof);d['extras']['omitted'].append('unknown.xrsc')
            with self.assertRaisesRegex(m.g.PreparationError,'unexplained_omission'):m.proof_ownership(d,p,code)
            d,_=m.g.unpack(raw);d['extras']['vehicle']='va_fake'
            with self.assertRaisesRegex(m.g.PreparationError,'not_proven_player_source'):m.proof_ownership(d,p,code)
    def test_coordinated_attachment_shift_rejected(self):
        for code,(raw,proof) in self.inputs.items():
            d,_=m.g.unpack(raw);p=json.loads(proof);part=next(x for x in d['extras']['parts'] if x['attachment_bone_index'] is not None);part['matrix'][12]+=.01
            for n in d['nodes']:
                if n['name'].startswith(part['file']+'@'+part['bone']+'/'):n['matrix'][12]+=.01
            with self.assertRaisesRegex(m.g.PreparationError,'native_attachment_outer_pose'):m.proof_ownership(d,p,code)
    def test_unskinned_proof_and_shared_pivot_required(self):
        for code,(raw,proof) in self.inputs.items():
            d,_=m.g.unpack(raw);p=json.loads(proof);next(iter(p['resources'].values()))['skinned'][0]=True
            with self.assertRaisesRegex(m.g.PreparationError,'native_source_or_skin'):m.proof_ownership(d,p,code)
            d,_=m.g.unpack(raw);p=json.loads(proof);d['extras']['wheels'][0]['translation'][1]+=.01
            with self.assertRaisesRegex(m.g.PreparationError,'native_axle_pose'):m.proof_ownership(d,p,code)
    def test_published_actual_outputs(self):
        for code,c in m.REGISTRY.items():
            folder=OUTPUT/('mustang-prepared-v1' if 'mustang' in code else 'golf-prepared-v1');self.assertFalse(inspect(OUTPUT/'source-store/objects'/(c['source']+'.glb'),folder)['runtime_player_eligible'])
if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--inspect':print(json.dumps(inspect(sys.argv[2],sys.argv[3]),indent=2))
    else:
        if not all((OUTPUT/'source-store/objects'/(c['source']+'.glb')).is_file() and (OUTPUT/(code+'-native-proof.json')).is_file() and (OUTPUT/('mustang-prepared-v1' if 'mustang' in code else 'golf-prepared-v1')).is_dir() for code,c in m.REGISTRY.items()):
            print('SKIP: retained pinned MCLA expansion inputs/proofs unavailable',file=sys.stderr);sys.exit(77)
        unittest.main()
