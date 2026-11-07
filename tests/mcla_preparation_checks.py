#!/usr/bin/env python3
"""Offline ownership/normalization and full-artifact checks for the MCLA adapter."""
import argparse
import copy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import shlex
import struct
import sys
import tempfile
from unittest.mock import patch
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import prepare_mcla_vehicle as m

def fixture():
    binary=bytearray();views=[];accessors=[]
    def accessor(rows,kind,ctype=5126):
        binary.extend(b'\0'*(-len(binary)%4));start=len(binary);fmt='f' if ctype==5126 else 'H'
        for row in rows:binary.extend(struct.pack('<'+fmt*len(row),*row))
        views.append({'buffer':0,'byteOffset':start,'byteLength':len(binary)-start})
        accessors.append({'componentType':ctype,'type':kind,'count':len(rows),'bufferView':len(views)-1})
        return len(accessors)-1
    tire=accessor([(-.1,0,-.3),(.1,0,.3),(0,.3,0)],'VEC3')
    body=accessor([(-1,0,-2.5),(1,0,-2.5),(0,1,2.5)],'VEC3')
    normal=accessor([(0,0,1)]*3,'VEC3');tangent=accessor([(1,0,0,1)]*3,'VEC4');indices=accessor([(0,),(1,),(2,)],'SCALAR',5123)
    bones=[{'index':i,'name':'vroot' if i==0 else 'driverhead' if i==30 else 'unused','parent':0,'model':[0,0,0],'euler':[0,0,0],'orient':[0,0,0]} for i in range(31)]
    for i,bone in enumerate(m.WHEEL_BONES):
        center=[-1 if i%2==0 else 1,.3,-1.2 if i<2 else 1.2]
        bones[bone].update(name='whl_'+str(i),parent=bone-1,model=center)
        bones[bone-1].update(name='axl_'+str(i),model=center)
    nodes=[]
    for i,bone in enumerate(m.BINDINGS):
        matrix=[1,0,0,0,0,1,0,0,0,0,1,0]+bones[bone]['model']+[1]
        nodes.append({'name':'native/model'+str(i),'mesh':0 if bone in m.WHEEL_BONES else 1,'matrix':matrix,'extras':{'nativeModel':i,'nativeBoneIndex':bone}})
    meshes=[{'primitives':[{'attributes':{'POSITION':p,'NORMAL':normal,'TANGENT':tangent},'indices':indices,'material':0}]} for p in (tire,body)]
    document={'asset':{'version':'2.0'},'scene':0,'scenes':[{'nodes':list(range(13))}],'nodes':nodes,'meshes':meshes,'accessors':accessors,'bufferViews':views,'buffers':[{'byteLength':len(binary)}],'materials':[{'name':'preserve'}],
              'extras':{'profile':'mcla-xbox360-static-stock-v3','vehicle':'fixture','parts':[{'slot':'body','file':'fixture/body.xrsc','resource_frame':'native'}],'sources':[{'file':'fixture/body.xrsc','sha256':m.NATIVE_SHA}],'wheels':[],'omitted':[],'claim_limits':['Static; native metre label unverified.']}}
    proof={'native_sha256':m.NATIVE_SHA,'model_bindings':list(m.BINDINGS),'skeleton':bones,'model_properties':[{'model':i,'skinned':False} for i in range(13)]}
    return document,binary,proof

class Checks(unittest.TestCase):
    def setUp(self):self.d,self.b,self.p=fixture()
    def prepare(self,scale=1):
        data=m.glb.pack(self.d,self.b);proof=json.dumps(self.p).encode()
        return m.prepare(data,'midnight-club-los-angeles/fixture','Fixture',proof,source_sha=hashlib.sha256(data).hexdigest(),proof_sha=hashlib.sha256(proof).hexdigest(),meters_per_unit=scale)
    def test_actual_native_groups_not_names(self):
        prepared,descriptor,r=self.prepare();d,b=m.glb.unpack(prepared)
        self.assertEqual(len(r['groups']),13)
        self.assertEqual(r['role'],'traffic');self.assertFalse(r['runtime_player_eligible'])
        self.assertEqual(d['extras']['racerPreparation']['role'],'traffic');self.assertFalse(d['extras']['racerPreparation']['runtime_player_eligible'])
        self.assertEqual([w for _,w in r['groups']], [0,0,1,1,2,2,3,3,-1,-1,-1,-1,-1])
        self.assertEqual(d['nodes'][0]['matrix'][12],-1)
        self.assertEqual(d['nodes'][0]['matrix'][14],1.2)
        self.assertEqual(r['source_facts']['wheelbase_native_units'],2.4)
        self.assertTrue(all(w['center'][1]>=w['radius'] for w in r['wheels']))
    def test_shared_accessors_once_and_preservation(self):
        prepared,descriptor,r=self.prepare();d,b=m.glb.unpack(prepared);g=m.glb.Geometry(d,b)
        self.assertAlmostEqual(g.values(0)[0][2],.3)
        self.assertEqual(g.values(2)[0],(0,0,-1));self.assertEqual(g.values(3)[0],(1,0,0,-1))
        self.assertEqual(g.values(4),[(0,),(2,),(1,)])
        self.assertEqual(bytes(b[:len(self.b)]),bytes(self.b));self.assertEqual(d['materials'],self.d['materials'])
        self.assertEqual(r['source_claim_limits'],self.d['extras']['claim_limits'])
        self.assertIn('vehicle-'+hashlib.sha256(prepared).hexdigest(),descriptor)
    def test_explicit_scale_keeps_native_facts(self):
        _,_,one=self.prepare();_,_,two=self.prepare(2)
        self.assertAlmostEqual(two['wheels'][0]['radius'],2*one['wheels'][0]['radius'])
        self.assertEqual(two['source_facts']['wheelbase_native_units'],one['source_facts']['wheelbase_native_units'])
        self.assertIn('assumption',two['normalization']['units_authority'])
    def test_publish_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp).resolve();source=root/'source.glb';proof=root/'proof.json'
            source.write_bytes(m.glb.pack(self.d,self.b));proof.write_text(json.dumps(self.p))
            original=m.prepare
            def fixture_prepare(data,key,name,proof_data,**kw):
                return original(data,key,name,proof_data,source_sha=hashlib.sha256(data).hexdigest(),proof_sha=hashlib.sha256(proof_data).hexdigest(),**kw)
            with patch.object(m,'prepare',side_effect=fixture_prepare):
                r=m.publish(source,'midnight-club-los-angeles/fixture','Fixture',proof,root/'out',minimum_free=0)
                self.assertEqual(inspect_actual(source,root/'out')['groups'],13)
                with self.assertRaises(m.PreparationError):m.publish(source,'midnight-club-los-angeles/fixture','Fixture',proof,root/'out',minimum_free=0)
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),r['source_sha256'])
            self.assertEqual((root/'out').stat().st_mode&0o777,0o700)
            self.assertTrue(all(p.stat().st_mode&0o777==0o600 for p in (root/'out').iterdir()))
    def test_source_and_proof_hash_fail_closed(self):
        raw=m.glb.pack(self.d,self.b)
        with self.assertRaises(m.PreparationError):m.prepare(raw,'midnight-club-los-angeles/fixture','Fixture',json.dumps(self.p).encode())
    def test_binding_change_rejected(self):
        self.d['nodes'][0]['extras']['nativeBoneIndex']=0
        with self.assertRaisesRegex(m.PreparationError,'native_model_binding'):self.prepare()
    def test_pose_and_unknown_rotation_rejected(self):
        self.d['nodes'][0]['matrix'][12]+=.01
        with self.assertRaisesRegex(m.PreparationError,'native_pose_mismatch'):self.prepare()
        self.d,self.b,self.p=fixture();self.d['nodes'][0]['matrix'][0]=0
        with self.assertRaisesRegex(m.PreparationError,'nontranslation_matrix'):self.prepare()
    def test_skinning_or_mixed_assembly_rejected(self):
        self.p['model_properties'][0]['skinned']=True
        with self.assertRaisesRegex(m.PreparationError,'native_skinning'):self.prepare()
        self.d,self.b,self.p=fixture();self.d['extras']['omitted']=['unavailable-part']
        with self.assertRaisesRegex(m.PreparationError,'partial_assembly'):self.prepare()
    def test_missing_wheel_or_native_name_rejected(self):
        self.p['skeleton'][4]['name']='unknown'
        with self.assertRaisesRegex(m.PreparationError,'native_wheel_identity'):self.prepare()
    def test_index_budget_and_external_buffer_rejected(self):
        self.d['accessors'][4]['count']=3000003
        with self.assertRaisesRegex(m.PreparationError,'index_work_budget'):self.prepare()
        self.d,self.b,self.p=fixture();self.d['buffers'][0]['uri']='missing.bin'
        with self.assertRaisesRegex(m.PreparationError,'buffers_unsupported'):self.prepare()
    def test_axle_outside_body_rejected(self):
        self.p['skeleton'][4]['model'][2]=-4
        self.d['nodes'][0]['matrix'][14]=self.d['nodes'][1]['matrix'][14]=-4
        with self.assertRaisesRegex(m.PreparationError,'racer_axle_containment'):self.prepare()


def inspect_actual(source,directory):
    """Independent GLB bytes/accessor traversal; does not invoke preparation/Geometry."""
    def decode(data):
        assert data[:4]==b'glTF' and struct.unpack_from('<I',data,8)[0]==len(data)
        n=struct.unpack_from('<I',data,12)[0];d=json.loads(data[20:20+n]);at=20+n
        size,kind=struct.unpack_from('<II',data,at);assert kind==0x004e4942
        return d,data[at+8:at+8+size]
    directory=Path(directory);descriptor=next(directory.glob('*.vehicle'));tokens=[shlex.split(l) for l in descriptor.read_text().splitlines()]
    f={x[0]:x[1:] for x in tokens if x[0] not in ('group','wheel')};raw=(directory/f['mesh'][0]).read_bytes();original=Path(source).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==f['sha256'][0] and hashlib.sha256(original).hexdigest()==f['source_sha256'][0]
    d,b=decode(raw);old,ob=decode(original);assert b[:len(ob)]==ob
    for key in ('materials','images','textures','samplers','extensions'):assert d.get(key)==old.get(key)
    def read(doc,buffer,index):
        a=doc['accessors'][index];v=doc['bufferViews'][a['bufferView']];fmt,unit={5121:('B',1),5123:('H',2),5125:('I',4),5126:('f',4)}[a['componentType']]
        n={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}[a['type']];start=v.get('byteOffset',0)+a.get('byteOffset',0);stride=v.get('byteStride',unit*n)
        return [struct.unpack_from('<'+fmt*n,buffer,start+i*stride) for i in range(a['count'])]
    for mesh in old['meshes']:
        for p in mesh['primitives']:
            for attribute,index in p['attributes'].items():
                before=read(old,ob,index);after=read(d,b,index)
                expected=[tuple(-value if axis==2 or (attribute=='TANGENT' and axis==3) else value for axis,value in enumerate(row)) for row in before] if attribute in ('POSITION','NORMAL','TANGENT') else before
                assert after==expected,attribute
            indices=read(old,ob,p['indices']);assert read(d,b,p['indices'])==[x for i in range(0,len(indices),3) for x in (indices[i],indices[i+2],indices[i+1])]
    groups={int(x[1]):int(x[2]) for x in tokens if x[0]=='group'};assert len(groups)==int(f['groups'][0])==13
    wheels={x[1]:list(map(float,x[2:])) for x in tokens if x[0]=='wheel'};bounds=list(map(float,f['body']));lift=d['nodes'][13]['translation'][1]
    vertices=triangles=0
    for ni,node in enumerate(d['nodes'][:13]):
        assert ni in groups;translation=node['matrix'][12:15]
        assert translation[0]==old['nodes'][ni]['matrix'][12] and translation[1]==old['nodes'][ni]['matrix'][13] and translation[2]==-old['nodes'][ni]['matrix'][14]
        for p in d['meshes'][node['mesh']]['primitives']:
            positions=read(d,b,p['attributes']['POSITION']);vertices+=len(positions);triangles+=len(read(d,b,p['indices']))//3
            for row in positions:
                point=[row[0]+translation[0],row[1]+translation[1]+lift,row[2]+translation[2]]
                if groups[ni]<0:assert all(bounds[i]-1e-9<=point[i]<=bounds[i+3]+1e-9 for i in range(3))
                else:
                    x,y,z,radius,width=wheels[m.LABELS[groups[ni]]]
                    assert abs(point[0]-x)<=width/2+1e-9 and math.hypot(point[1]-y,point[2]-z)<=radius+1e-9
    assert d['scenes'][0]['nodes']==[13] and d['nodes'][13]['children']==list(range(13))
    return {'source_sha256':f['source_sha256'][0],'prepared_sha256':f['sha256'][0],'groups':len(groups),'vertices':vertices,'triangles':triangles,'all_source_attributes_mirror_winding_verified':True,'original_binary_prefix_materials_images_preserved':True,'all_descriptor_body_and_wheel_containment_verified':True,'scope':'static geometry; no renderer/runtime or native-unit equivalence'}

if __name__=='__main__':
    if '--prepared' in sys.argv:
        p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--prepared',required=True);a=p.parse_args();print(json.dumps(inspect_actual(a.source,a.prepared),indent=2))
    else:unittest.main()
