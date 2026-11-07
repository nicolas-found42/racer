#!/usr/bin/env python3
"""Pinned source and independent full-vertex affine tyre-fit acceptance checks."""
import copy,hashlib,json,math,shlex,struct,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import fit_juiced2_tyres as fit
ROOT=Path(__file__).resolve().parents[1];LEAF=ROOT/'experiments/2026-11-06-juiced2-expansion/output';OLD=LEAF/'mx5-prepared-v1'

def decode(raw):
    assert raw[:4]==b'glTF' and struct.unpack_from('<I',raw,8)[0]==len(raw);n=struct.unpack_from('<I',raw,12)[0];doc=json.loads(raw[20:20+n]);size,kind=struct.unpack_from('<II',raw,20+n);assert kind==0x004e4942;return doc,raw[28+n:28+n+size]
def inspect(source,descriptor,receipt_data,prepared,new_descriptor):
    before,oldbin=decode(source);after,newbin=decode(prepared);assert oldbin==newbin
    r=json.loads(receipt_data);oldtokens=[shlex.split(line)for line in descriptor.decode().splitlines()];newtokens=[shlex.split(line)for line in new_descriptor.splitlines()];fields={x[0]:x[1:]for x in newtokens if x[0]not in('group','wheel')};groups={int(x[1]):' '.join(x[2:])for x in newtokens if x[0]=='group'};oldgroups={int(x[1]):' '.join(x[2:])for x in oldtokens if x[0]=='group'};assert groups==oldgroups;wheels={x[1]:list(map(float,x[2:]))for x in newtokens if x[0]=='wheel'};bounds=list(map(float,fields['body']));assert fields['sha256']==[hashlib.sha256(prepared).hexdigest()]
    lift=r['wheels'][0]['center'][1]-r['native_wheel_pivots']['WHEEL_FL'][1]/100
    assert len(after['nodes'])==len(before['nodes'])+1;root=len(before['nodes']);assert after['nodes'][-1]=={'name':'racer_authored_remove_toyo_lift','translation':[0,-lift,0],'children':list(range(root))};assert after['scenes'][0]['nodes']==[root]
    for key in before:
        if key not in ('nodes','scenes','extras'):assert before[key]==after[key]
    for key,value in before['extras'].items():assert after['extras'][key]==value
    assert set(after['extras'])==set(before['extras'])|{'racerHubRestTyreFit'}
    def values(index):
        a=before['accessors'][index];v=before['bufferViews'][a['bufferView']];assert a['componentType']==5126 and a['type']=='VEC3';return [struct.unpack_from('<fff',oldbin,v.get('byteOffset',0)+a.get('byteOffset',0)+j*v.get('byteStride',12))for j in range(a['count'])]
    vertices=0;tyres=0
    for index,oldnode in enumerate(before['nodes']):
        node=after['nodes'][index];tyre=oldnode['name'].startswith('ADAPTED_NATIVE_TOYO_TYRE_');role=groups[index];points=[p for primitive in before['meshes'][oldnode['mesh']]['primitives']for p in values(primitive['attributes']['POSITION'])]
        if tyre:
            label=oldnode['name'][-2:];i=fit.LABELS.index(label);center=r['wheels'][i]['center'];target=r['native_wheel_pivots']['WHEEL_'+label][1]/100;radius=max(math.hypot(p[1]-center[1],p[2]-center[2])for p in points);factor=target/radius
            assert node==dict(oldnode,scale=[1,factor,factor],translation=[0,center[1]*(1-factor),center[2]*(1-factor)]);tyres+=1
        else:assert node==oldnode
        for p in points:
            expected=list(p);actual=list(p)
            if tyre:
                expected[1]=center[1]+factor*(p[1]-center[1]);expected[2]=center[2]+factor*(p[2]-center[2]);actual=[p[k]*node['scale'][k]+node['translation'][k]for k in range(3)]
            actual[1]-=lift;expected[1]-=lift;assert max(abs(a-b)for a,b in zip(actual,expected))<1e-12;assert actual[0]==p[0]
            if role=='body':assert all(bounds[k]-2e-7<=actual[k]<=bounds[k+3]+2e-7 for k in range(3))
            else:
                w=wheels[role.split()[1]];assert abs(actual[0]-w[0])<=w[4]/2+2e-7 and math.hypot(actual[1]-w[1],actual[2]-w[2])<=w[3]+2e-7
            vertices+=1
    assert tyres==4 and vertices==51666
    for label,w in wheels.items():
        native=r['native_wheel_pivots']['WHEEL_'+label];assert max(abs(w[k]-native[k]/100)for k in range(3))<1e-7 and abs(w[1]-w[3])<1e-7
    return {'prepared_sha256':hashlib.sha256(prepared).hexdigest(),'all_world_positions_verified':vertices,'tyre_groups_radial_fit':tyres,'source_BIN_images_materials_meshes_unchanged':True,'body_rim_disc_carrier_nodes_unchanged_except_uniform_parent_shift':True,'native_XZ_pivots_retained':True,'ground_contact_cylinders_verified':True,'limitations':['Source hub Y interpreted as authored tyre ground-rest radius, not source runtime/factory tyre specification.','No GPU/steering clearance or physical-unit authority established.']}

class Checks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not(OLD/'receipt.json').exists():raise unittest.SkipTest('retained pinned source unavailable')
        cls.raw=(OLD/(fit.SOURCE_SHA+'.glb')).read_bytes();cls.descriptor=(OLD/(fit.SOURCE_SHA+'.vehicle')).read_bytes();cls.receipt=(OLD/'receipt.json').read_bytes();cls.r=json.loads(cls.receipt);cls.d,cls.b=fit.g.unpack(cls.raw);cls.roles={int(x[1]):' '.join(x[2:])for x in map(shlex.split,cls.descriptor.decode().splitlines())if x[0]=='group'}
    def transform(self,doc=None,r=None,roles=None):
        r=r or self.r;return fit.transform(doc or self.d,self.b,r['wheels'],r['native_wheel_pivots'],roles or self.roles)
    def test_actual_fullvertex_and_source_pin(self):
        raw,desc,r=fit.prepare(self.raw,self.descriptor,self.receipt);proof=inspect(self.raw,self.descriptor,self.receipt,raw,desc);self.assertEqual(proof['all_world_positions_verified'],51666);self.assertFalse(r['runtime_player_eligible'])
        with self.assertRaisesRegex(fit.g.PreparationError,'source_pins'):fit.prepare(self.raw+b' ',self.descriptor,self.receipt)
    def test_unknown_affine_frame_rejected(self):
        for transform in ({'translation':[0,0,0]},{'matrix':[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1]}):
            d=copy.deepcopy(self.d);d['nodes'][0].update(transform)
            with self.assertRaisesRegex(fit.g.PreparationError,'nonflat_node'):self.transform(d)
    def test_four_wheel_and_role_required(self):
        r=copy.deepcopy(self.r);del r['native_wheel_pivots']['WHEEL_FL']
        with self.assertRaisesRegex(fit.g.PreparationError,'four_wheel_bindings'):self.transform(r=r)
        roles=self.roles.copy();roles[0]='unknown'
        with self.assertRaisesRegex(fit.g.PreparationError,'unknown_binding_role'):self.transform(roles=roles)
    def test_duplicate_tyre_and_missing_tyre_rejected(self):
        d=copy.deepcopy(self.d);indices=[i for i,n in enumerate(d['nodes'])if n['name'].startswith('ADAPTED_NATIVE_TOYO_TYRE_')];d['nodes'][indices[1]]['name']=d['nodes'][indices[0]]['name']
        with self.assertRaisesRegex(fit.g.PreparationError,'ambiguous_tyre'):self.transform(d)
        d=copy.deepcopy(self.d);d['nodes'][indices[0]]['name']='unknown_tyre'
        with self.assertRaisesRegex(fit.g.PreparationError,'four_tyres'):self.transform(d)
    def test_invalid_pivot_and_too_small_target_rejected(self):
        r=copy.deepcopy(self.r);r['native_wheel_pivots']['WHEEL_FL'][0]+=.1
        with self.assertRaisesRegex(fit.g.PreparationError,'native_pivot'):self.transform(r=r)
        r=copy.deepcopy(self.r)
        for label in fit.LABELS:r['native_wheel_pivots']['WHEEL_'+label][1]=23.0
        with self.assertRaisesRegex(fit.g.PreparationError,'target_inside_fixed_wheel_envelope'):self.transform(r=r)
    def test_out_of_range_target_rejected(self):
        for radius in (.09,.8):
            r=copy.deepcopy(self.r);r['native_wheel_pivots']['WHEEL_FL'][1]=radius*100
            with self.assertRaisesRegex(fit.g.PreparationError,'native_pivot'):self.transform(r=r)
    def test_nonuniform_lift_and_budget_rejected(self):
        r=copy.deepcopy(self.r);r['native_wheel_pivots']['WHEEL_FL'][1]+=.1
        with self.assertRaisesRegex(fit.g.PreparationError,'nonuniform_source_lift'):self.transform(r=r)
        d=copy.deepcopy(self.d);index=d['meshes'][0]['primitives'][0]['attributes']['POSITION'];d['accessors'][index]['count']=1000001
        with self.assertRaisesRegex(fit.g.PreparationError,'position_budget'):self.transform(d)
    def test_independent_checker_rejects_recoupled_body_mutation(self):
        raw,desc,r=fit.prepare(self.raw,self.descriptor,self.receipt);d,b=fit.g.unpack(raw);d['nodes'][0]['translation']=[0,.001,0];changed=fit.g.pack(d,b);newsha=hashlib.sha256(changed).hexdigest()
        with self.assertRaises(AssertionError):inspect(self.raw,self.descriptor,self.receipt,changed,desc.replace(r['prepared_sha256'],newsha))
if __name__=='__main__':
    if not all((OLD/name).is_file() for name in (fit.SOURCE_SHA+'.glb',fit.SOURCE_SHA+'.vehicle','receipt.json')):
        print('SKIP: retained pinned MX5 source inputs unavailable',file=sys.stderr);sys.exit(77)
    unittest.main()
