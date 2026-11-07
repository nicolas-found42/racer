#!/usr/bin/env python3
"""Native-pinned alias proof and name-order-independent wheel classification."""
import copy,hashlib,json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import mc3_wheel_contract as m
from prepare_gt4_vehicle import unpack,PreparationError
from prepare_source_vehicle import metadata
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'experiments/2026-11-06-mc3-coverage/output';SHA='8a1b7ba44d38815c6c491d3caf9e3b139dbf51c9d74d4c9546b2ee3164d48383'
class Checks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        p=OUT/'source-store/objects'/(SHA+'.glb')
        if not p.is_file()or not(OUT/'350z-native-proof.json').is_file():raise unittest.SkipTest('retained exact source/native proof unavailable')
        raw=p.read_bytes();assert hashlib.sha256(raw).hexdigest()==SHA;cls.d,_=unpack(raw);proof=(OUT/'350z-native-proof.json').read_bytes();assert hashlib.sha256(proof).hexdigest()=='b3c4a48e777a66bf81875e30b713c44e255ac650e24da49e71514b508fd9f767';cls.b=json.loads(proof)['native_skeleton']
    def resolve(self,d=None,b=None):return m.resolve(d or self.d,b or self.b)
    def test_actual_native_binding_and_current_adapter_boundary(self):
        r=self.resolve();self.assertEqual(len(r['evidence']),8);self.assertEqual(len(r['ownership']),24)
        self.assertAlmostEqual(r['centers'][0][0],-.7660970091819763);self.assertAlmostEqual(r['centers'][0][2],-1.315412998199463)
        with self.assertRaisesRegex(PreparationError,'unsupported_mc3_joint'):metadata(self.d,'midnight-club-3-remix/vp_350z_04')
    def test_alias_ordinal_and_node_order_do_not_define_slot(self):
        for names in [('wheel3','wheel2','wheel1','wheel0'),('WHL3','WHL2','WHL1','WHL0'),('whl_03','whl_02','whl_01','whl_00'),('whlR1','whlR0','whlF1','whlF0')]:
            d=copy.deepcopy(self.d);b=copy.deepcopy(self.b);slots=self.resolve();bone_slots={e['native_bone_index']:m.LABELS.index(e['canonical_slot'])for e in slots['evidence']}
            for bone in b:
                if bone['index']in bone_slots:bone['name']=names[bone_slots[bone['index']]]
            for bone in d['extras']['nativeSkeleton']['bones']:
                if bone['index']in bone_slots:bone['name']=names[bone_slots[bone['index']]]
            for node in d['nodes']:
                e=node.get('extras',{})
                if 'nativeWheelJoint'in e:e['nativeWheelJoint']=names[bone_slots[e['nativeBone']]]
            d['scenes'][0]['nodes'].reverse();r=self.resolve(d,b)
            self.assertEqual(r['centers'],slots['centers']);self.assertEqual(r['ownership'],slots['ownership'])
    def test_native_and_preview_pose_mutation_rejected(self):
        d=copy.deepcopy(self.d);d['extras']['nativeSkeleton']['bones'][8]['global_position'][0]+=.01
        with self.assertRaisesRegex(PreparationError,'native_skeleton_join'):self.resolve(d)
        d=copy.deepcopy(self.d);node=next(n for n in d['nodes']if n.get('extras',{}).get('nativeWheelJoint'));node['translation'][2]+=.01
        with self.assertRaisesRegex(PreparationError,'wheel_pose_join'):self.resolve(d)
    def test_duplicate_preview_bone_and_orphan_component_rejected(self):
        d=copy.deepcopy(self.d);d['extras']['nativeSkeleton']['bones'][9]=copy.deepcopy(d['extras']['nativeSkeleton']['bones'][8])
        with self.assertRaisesRegex(PreparationError,'native_skeleton_join'):self.resolve(d)
        d=copy.deepcopy(self.d);node=next(n for n in d['nodes']if n.get('extras',{}).get('nativeWheelJoint'));del node['extras']['nativeWheelJoint']
        with self.assertRaisesRegex(PreparationError,'wheel_component_without_joint'):self.resolve(d)
    def test_source_orientation_not_guessed(self):
        b=copy.deepcopy(self.b);d=copy.deepcopy(self.d)
        for bones in(b,d['extras']['nativeSkeleton']['bones']):
            for bone in bones:
                if bone['name']=='hood':bone['global_position'][2]=1.0
        with self.assertRaisesRegex(PreparationError,'ambiguous_front_axis'):self.resolve(d,b)
        b=copy.deepcopy(self.b);d=copy.deepcopy(self.d)
        for bones in(b,d['extras']['nativeSkeleton']['bones']):
            for bone in bones:
                if bone['name']=='Arm_Front_L':bone['name']='unknown_left'
        with self.assertRaisesRegex(PreparationError,'orientation_anchor_missing'):self.resolve(d,b)
    def test_rotated_ancestor_and_component_gaps_rejected(self):
        b=copy.deepcopy(self.b);d=copy.deepcopy(self.d)
        for bones in(b,d['extras']['nativeSkeleton']['bones']):bones[0]['rotation_raw'][1]=.1
        with self.assertRaisesRegex(PreparationError,'rotated_wheel_frame'):self.resolve(d,b)
        d=copy.deepcopy(self.d);wheel=next(i for i in d['scenes'][0]['nodes']if d['nodes'][i].get('extras',{}).get('nativeWheelJoint'));d['scenes'][0]['nodes'].remove(wheel)
        with self.assertRaisesRegex(PreparationError,'four_complete_wheels'):self.resolve(d)
    def test_duplicate_component_and_unsupported_alias(self):
        d=copy.deepcopy(self.d);w=[n for n in d['nodes']if n.get('extras',{}).get('nativeWheelJoint')];w[1]['extras']['nativeWheelComponent']='rim'
        with self.assertRaisesRegex(PreparationError,'component_ownership'):self.resolve(d)
        d=copy.deepcopy(self.d);w=next(n for n in d['nodes']if n.get('extras',{}).get('nativeWheelJoint'));w['extras']['nativeWheelJoint']='wheel_mystery'
        with self.assertRaisesRegex(PreparationError,'unproved_joint_alias'):self.resolve(d)
if __name__=='__main__':
    if not(OUT/'source-store/objects'/(SHA+'.glb')).is_file()or not(OUT/'350z-native-proof.json').is_file():print('SKIP: retained exact MC3 wheel fixtures unavailable',file=sys.stderr);sys.exit(77)
    unittest.main()
