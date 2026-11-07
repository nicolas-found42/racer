#!/usr/bin/env python3
"""Actual native-byte authority and default-path regression, no network/GPU."""
import copy,hashlib,json,shlex,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import prepare_mc3_vehicle as wrapper
from prepare_source_vehicle import prepare
from unittest.mock import patch
import mc3_exhaust
from repair_mc3_vehicle import frames,rotate
from prepare_gt4_vehicle import PreparationError,unpack,Geometry
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'experiments/2026-11-06-mc3-coverage/output';SHA='8a1b7ba44d38815c6c491d3caf9e3b139dbf51c9d74d4c9546b2ee3164d48383'
def fixtures_available():
    required=[OUT/'source-store/objects'/(SHA+'.glb'),OUT/'350z-native-proof.json',OUT/'vp_350z_04.dat',OUT/'350z-main.pck',wrapper.CATALOG,wrapper.INDEX,wrapper.READER,*[OUT/name for name in mc3_exhaust.PINS],OUT/'350z-exhaust-proof.json',OUT/'350z-exhaust-geometry.json']
    old=ROOT/'experiments/2026-11-05-other-car-families/output'
    required += [old/'assets/objects/b0e50f8c609b770ece74ea511312a11e7b79f6e6fff6331da7ff249ba6328806.glb',OUT/'350z-prepared-v1/470d50d6df2fe47d3641ebc0e73bace988146fa291283bf5a7d9484bcc013e82.glb',OUT/'350z-prepared-v2/45db4980c591f45f7363e2b784f98d14690f7ead422985ea2274296824958c91.glb']
    legacy=list((old/'mc3-prepared-v5').glob('*.vehicle'))
    return bool(legacy)and all(p.is_file()for p in required+[legacy[0],legacy[0].with_suffix('.glb')])
class Checks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=OUT/'source-store/objects'/(SHA+'.glb');cls.proof=OUT/'350z-native-proof.json';cls.dat=OUT/'vp_350z_04.dat';cls.pck=OUT/'350z-main.pck'
        if not fixtures_available():raise unittest.SkipTest('retained exact native/source/historical fixtures unavailable')
    def build(self,output,**changes):
        args={'source':self.source,'source_sha':SHA,'proof_path':self.proof,'dat_path':self.dat,'pck_path':self.pck,'output':output};args.update(changes);return wrapper.build(**args)
    def test_actual_source_preserved_and_valid_artifact_identity(self):
        with tempfile.TemporaryDirectory(dir=OUT)as tmp:
            out=Path(tmp)/'prepared';r=self.build(out);self.assertEqual(r['source_sha256'],SHA);self.assertFalse(r['runtime_player_eligible']);self.assertAlmostEqual(r['wheelbase'],2.630825996398926)
            raw=(out/(r['prepared_sha256']+'.glb')).read_bytes();self.assertEqual(hashlib.sha256(raw).hexdigest(),r['prepared_sha256']);self.assertEqual(r['prepared_sha256'],'45db4980c591f45f7363e2b784f98d14690f7ead422985ea2274296824958c91')
    def test_source_dat_and_pck_tampering_rejected(self):
        with tempfile.TemporaryDirectory(dir=OUT)as tmp:
            out=Path(tmp)/'output'
            with self.assertRaisesRegex(PreparationError,'source_sha'):self.build(out,source_sha='0'*64)
            bad=Path(tmp)/'bad.dat';bad.write_bytes(self.dat.read_bytes()+b'x')
            with self.assertRaisesRegex(PreparationError,'native_dat_pin'):self.build(out,dat_path=bad)
            bad=Path(tmp)/'bad.pck';data=bytearray(self.pck.read_bytes());data[0]^=1;bad.write_bytes(data)
            with self.assertRaisesRegex(PreparationError,'actual_dat_pck_bytes'):self.build(out,pck_path=bad)
            self.assertFalse(out.exists())
    def test_forged_json_bones_not_authoritative(self):
        with tempfile.TemporaryDirectory(dir=OUT)as tmp:
            p=Path(tmp)/'proof.json';proof=json.loads(self.proof.read_text());proof['native_skeleton'][8]['global_position'][0]+=.01;p.write_text(json.dumps(proof))
            with self.assertRaisesRegex(PreparationError,'native_proof_bones'):self.build(Path(tmp)/'out',proof_path=p)
    def test_glass_policy_exact_boundaries_and_binary_preservation(self):
        with tempfile.TemporaryDirectory(dir=OUT)as tmp:
            a=Path(tmp)/'base';b=Path(tmp)/'glass';base=self.build(a);glass=self.build(b,racer_glass=True)
            before,bb=unpack((a/(base['prepared_sha256']+'.glb')).read_bytes());after,ab=unpack((b/(glass['prepared_sha256']+'.glb')).read_bytes());self.assertEqual(bb,ab)
            self.assertEqual(glass['prepared_sha256'],'4b61dd2d2dd25e75a31fc16b68adc8cdaef5bcca814306b846551af9390e1703');self.assertEqual({x['index']for x in glass['racer_glass_policy']['changes']},{6,7})
            for i,material in enumerate(before['materials']):
                expected=copy.deepcopy(material)
                if i in(6,7):expected['alphaMode']='BLEND';expected['pbrMetallicRoughness']['baseColorFactor']=[.08,.12,.16,.45]
                self.assertEqual(after['materials'][i],expected)
            self.assertEqual(after['materials'][23],before['materials'][23])
            for key in('nodes','meshes','accessors','bufferViews','buffers','images','textures','samplers','scenes'):self.assertEqual(before.get(key),after.get(key))
            for key in('body','wheels','groups','wheelbase','source_sha256'):self.assertEqual(base[key],glass[key])
            unknown=copy.deepcopy(before);unknown['materials'][6]['extras']['shader_category']='unknown_glass';original=copy.deepcopy(unknown['materials'][6]);result=wrapper.authored_glass(unknown,SHA)
            self.assertEqual(unknown['materials'][6],original);self.assertEqual([x['index']for x in result['changes']],[7])
            dormant=copy.deepcopy(before);original=copy.deepcopy(dormant['materials'][7]);sample=None
            for mesh in dormant['meshes']:
                for primitive in mesh['primitives']:
                    if primitive.get('material')==7:sample=copy.deepcopy(primitive);primitive['material']=1
            self.assertIsNotNone(sample);dormant['meshes'].append({'primitives':[sample]});dormant['nodes'].append({'name':'dormant-glass','mesh':len(dormant['meshes'])-1});result=wrapper.authored_glass(dormant,SHA)
            self.assertEqual(dormant['materials'][7],original);self.assertEqual([x['index']for x in result['changes']],[6])
    def test_actual_authored_exhaust_addition_preserves_all_originals(self):
        with tempfile.TemporaryDirectory(dir=OUT)as tmp:
            base=self.build(Path(tmp)/'base',racer_glass=True);added=self.build(Path(tmp)/'added',racer_glass=True,authored_stock_exhaust=True);a,ab=unpack((Path(tmp)/'base'/(base['prepared_sha256']+'.glb')).read_bytes());d,b=unpack((Path(tmp)/'added'/(added['prepared_sha256']+'.glb')).read_bytes());self.assertEqual(added['prepared_sha256'],'4e63e3d8f4daef1403293f4c613629119e1e0b92440f6d12cc3f8e05a6a9db23');self.assertEqual(b[:len(ab)],ab)
            for key in('meshes','accessors','bufferViews','images','textures','materials'):self.assertEqual(d[key][:len(a[key])],a[key])
            root=a['scenes'][0]['nodes'][0]
            for i,n in enumerate(a['nodes']):
                if i!=root:self.assertEqual(d['nodes'][i],n)
            self.assertEqual(d['nodes'][root]['children'][:len(a['nodes'][root]['children'])],a['nodes'][root]['children'])
            for key in('body','wheels','source_sha256','wheelbase'):self.assertEqual(base[key],added[key])
            proof=json.loads((OUT/'350z-exhaust-proof.json').read_text());source=json.loads((OUT/'350z-exhaust-geometry.json').read_text());bones=json.loads(self.proof.read_text())['native_skeleton'];rest=frames(bones);g=Geometry(d,b);count=0
            for item in added['static_exhaust_policy']['attachments']:
                t,q=rest[item['native_bone']];node=d['nodes'][item['node']]
                for draw,primitive in zip(source,d['meshes'][node['mesh']]['primitives']):
                    got=g.values(primitive['attributes']['POSITION']);self.assertEqual(len(got),len(draw['positions']))
                    for p,point in zip(draw['positions'],got):
                        v=rotate(q,p);expected=[v[0]+t[0],v[1]+t[1],-(v[2]+t[2])];self.assertLess(max(abs(point[i]-expected[i])for i in range(3)),2e-7);count+=1
                    expected=draw['indices'][:]
                    for i in range(0,len(expected),3):expected[i+1],expected[i+2]=expected[i+2],expected[i+1]
                    self.assertEqual([x[0]for x in g.values(primitive['indices'])],expected)
            self.assertEqual(count,210);self.assertEqual(proof['native_handle'],16777221)
    def test_exhaust_changed_source_and_root_rejected(self):
        real=mc3_exhaust.read_regular
        def changed(path,cap):
            value=real(path,cap)
            return value+b'x'if Path(path).name=='exhaust.ppf'else value
        with patch('mc3_exhaust.read_regular',side_effect=changed),tempfile.TemporaryDirectory(dir=OUT)as tmp:
            with self.assertRaisesRegex(PreparationError,'exhaust_input_pins'):self.build(Path(tmp)/'bad',authored_stock_exhaust=True)
        with tempfile.TemporaryDirectory(dir=OUT)as tmp:
            folder=Path(tmp)/'base';r=self.build(folder);r['ground_lift']+=.001;mesh=(folder/(r['prepared_sha256']+'.glb')).read_bytes();desc=(folder/(r['prepared_sha256']+'.vehicle')).read_text();bones=json.loads(self.proof.read_text())['native_skeleton']
            with self.assertRaisesRegex(PreparationError,'exhaust_ground_root'):mc3_exhaust.attach(mesh,desc,r,bones,None)
    def test_metadata_v2_only_corrects_optional_branch(self):
        old=OUT/'350z-prepared-v1/470d50d6df2fe47d3641ebc0e73bace988146fa291283bf5a7d9484bcc013e82.glb';new=OUT/'350z-prepared-v2/45db4980c591f45f7363e2b784f98d14690f7ead422985ea2274296824958c91.glb'
        if not old.exists()or not new.exists():self.skipTest('retained staged artifacts unavailable')
        a,ab=unpack(old.read_bytes());b,bb=unpack(new.read_bytes());self.assertEqual(ab,bb);a['extras']['racerPreparation']['units']['factor_status']=b['extras']['racerPreparation']['units']['factor_status'];self.assertEqual(a,b)
    def test_default_corvette_glb_and_descriptor_byte_regression(self):
        old=ROOT/'experiments/2026-11-05-other-car-families/output';source=old/'assets/objects/b0e50f8c609b770ece74ea511312a11e7b79f6e6fff6331da7ff249ba6328806.glb';folder=old/'mc3-prepared-v5'
        if not source.is_file():self.skipTest('historical source unavailable')
        descriptor=next(folder.glob('*.vehicle')).read_text();name=shlex.split(next(x for x in descriptor.splitlines()if x.startswith('name ')))[1];raw,text,r=prepare(source.read_bytes(),'midnight-club-3-remix/vp_corvettez06_03',name)
        self.assertEqual((folder/(r['prepared_sha256']+'.glb')).read_bytes(),raw);self.assertEqual(text,descriptor)
if __name__=='__main__':
    if not fixtures_available():print('SKIP: retained exact MC3 source/native/historical fixtures unavailable',file=sys.stderr);sys.exit(77)
    unittest.main()
