#!/usr/bin/env python3
"""Offline geometry normalization checks, independent of renderer/game execution."""
import copy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import struct
import argparse
import shlex
import sys
import tempfile
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('gt4prepare',Path(__file__).resolve().parents[1]/'scripts/prepare_gt4_vehicle.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def fixture():
    binary=bytearray();views=[];accessors=[]
    def accessor(values,kind,ctype=5126):
        binary.extend(b'\0'*(-len(binary)%4))
        start=len(binary);fmt='f' if ctype==5126 else 'H'
        for row in values: binary.extend(struct.pack('<'+fmt*len(row),*row))
        views.append({'buffer':0,'byteOffset':start,'byteLength':len(binary)-start})
        accessors.append({'bufferView':len(views)-1,'componentType':ctype,'count':len(values),'type':kind})
        return len(accessors)-1
    position=accessor([(-.1,0,-.4),(.1,0,-.4),(0,.4,0)],'VEC3')
    normal=accessor([(0,0,1)]*3,'VEC3')
    tangent=accessor([(1,0,0,1)]*3,'VEC4')
    indices=accessor([(0,),(1,),(2,)],'SCALAR',5123)
    body=accessor([(-.5,0,-2),(.5,0,-2),(0,.4,2)],'VEC3')
    nodes=[{'name':'body','mesh':1}];wheels=[]
    for i,name in enumerate(m.WHEELS):
        center=[-1 if i%2==0 else 1,.2,-1 if i<2 else 1]
        wheels.append({'name':name,'centre':center,'outer_radius':.3,'width':.15})
        for prefix in ('wheel','tire'):nodes.append({'name':prefix+'_'+name,'mesh':0,'translation':center.copy()})
    document={'asset':{'version':'2.0'},'scene':0,'scenes':[{'nodes':list(range(9))}], 'nodes':nodes,
              'meshes':[{'primitives':[{'attributes':{'POSITION':position,'NORMAL':normal,'TANGENT':tangent},'indices':indices,'material':0}]}],
              'accessors':accessors,'bufferViews':views,'buffers':[{'byteLength':len(binary)}],
              'materials':[{'name':'original','pbrMetallicRoughness':{'baseColorFactor':[.2,.3,.4,1]}}],
              'extras':{'source_profile':'gt4-ps2-static-car-v2','car':'fixture','record':{'wheels':wheels},'claim_limits':['Static source interpretations; runtime unverified.']}}
    body_mesh=copy.deepcopy(document['meshes'][0]);body_mesh['primitives'][0]['attributes']['POSITION']=body
    document['meshes'].append(body_mesh)
    return document,binary

class Checks(unittest.TestCase):
    def setUp(self):self.d,self.bin=fixture()
    def prepare(self):return m.prepare(m.pack(self.d,self.bin),'gran-turismo-4/fixture',"Fixture '00")
    def test_mirror_winding_shared_accessors_and_materials(self):
        raw,descriptor,receipt=self.prepare();d,b=m.unpack(raw);g=m.Geometry(d,b)
        self.assertAlmostEqual(g.values(0)[0][0],-.1)
        self.assertAlmostEqual(g.values(0)[0][2],.4)
        self.assertEqual(g.values(1)[0],(0,0,-1))
        self.assertEqual(g.values(2)[0],(1,0,0,-1))
        self.assertEqual(g.values(3),[(0,),(2,),(1,)])
        self.assertEqual(d['materials'],self.d['materials'])
        self.assertEqual(d['extras']['record'],self.d['extras']['record'])
        self.assertEqual(bytes(b[:len(self.bin)]),bytes(self.bin))
        self.assertIn('id "vehicle-'+hashlib.sha256(raw).hexdigest()+'"',descriptor)
        self.assertEqual(receipt['source_sha256'],hashlib.sha256(m.pack(self.d,self.bin)).hexdigest())
    def test_bounds_wheel_groups_and_ground(self):
        raw,descriptor,r=self.prepare();d,b=m.unpack(raw)
        self.assertEqual(len(r['groups']),9)
        self.assertEqual([w['label'] for w in r['wheels']],list(m.LABELS))
        self.assertTrue(all(w['center'][1]-w['radius']>=-1e-12 for w in r['wheels']))
        self.assertTrue(all(w['radius']>.3 and w['width']>.15 for w in r['wheels']))
        self.assertTrue(all(w['center'][0]<0 for w in (r['wheels'][0],r['wheels'][2])))
        self.assertGreater(r['wheels'][0]['center'][2],0)
        self.assertEqual(d['nodes'][9]['children'],list(range(9)))
        self.assertEqual(d['scenes'][0]['nodes'],[9])
        self.assertEqual(r['body'][1],r['ground_lift'])
    def test_wide_rims_enclosed(self):
        self.bin.extend(b'\0'*(-len(self.bin)%4))
        offset=len(self.bin)
        for point in ((-.3,0,-.5),(.3,0,-.5),(0,.5,0)):
            self.bin.extend(struct.pack('<fff',*point))
        self.d['bufferViews'].append({'buffer':0,'byteOffset':offset,'byteLength':36})
        self.d['accessors'].append({'bufferView':len(self.d['bufferViews'])-1,'componentType':5126,'count':3,'type':'VEC3'})
        rim=copy.deepcopy(self.d['meshes'][0]);rim['primitives'][0]['attributes']['POSITION']=len(self.d['accessors'])-1
        self.d['meshes'].append(rim)
        for node in self.d['nodes']:
            if node['name'].startswith('wheel_'):node['mesh']=len(self.d['meshes'])-1
        self.d['buffers'][0]['byteLength']=len(self.bin)
        _,_,r=self.prepare()
        self.assertTrue(all(w['radius']>=.5 and w['width']>=.6 for w in r['wheels']))
    def test_index_work_bounded(self):
        with patch.object(m,'MAX_INDEX_WORK',5):
            with self.assertRaisesRegex(m.PreparationError,'geometry_index_work_budget'):self.prepare()
    def test_instance_indices_and_depth_bounded(self):
        with patch.object(m,'MAX_INSTANCE_INDICES',20):
            with self.assertRaisesRegex(m.PreparationError,'instance_index_work_budget'):self.prepare()
        old_roots=self.d['scenes'][0]['nodes']
        first=len(self.d['nodes'])
        for i in range(65):self.d['nodes'].append({'children':[first+i+1] if i<64 else old_roots})
        self.d['scenes'][0]['nodes']=[first]
        with self.assertRaisesRegex(m.PreparationError,'scene_depth_unsupported'):self.prepare()
    def test_shared_scenes_rejected(self):
        self.d['scenes'].append(copy.deepcopy(self.d['scenes'][0]))
        with self.assertRaisesRegex(m.PreparationError,'shared_nodes_across_scenes'):self.prepare()
    def test_axles_outside_body_rejected(self):
        self.d['nodes'][0]['scale']=[1,1,.1]
        with self.assertRaisesRegex(m.PreparationError,'racer_axle_body_length'):self.prepare()
    def test_rotation_rejected(self):
        self.d['nodes'][1]['rotation']=[0,0,0,1]
        with self.assertRaises(m.PreparationError):self.prepare()
    def test_unknown_and_missing_groups_rejected(self):
        self.d['nodes'][1]['name']='unknown'
        with self.assertRaises(m.PreparationError):self.prepare()
    def test_bad_metadata_and_axis_rejected(self):
        self.d['extras']['record']['wheels'][0]['centre'][0]=1
        with self.assertRaises(m.PreparationError):self.prepare()
    def test_sparse_morph_and_external_rejected(self):
        for change in ('sparse','morph','uri'):
            self.d,self.bin=fixture()
            if change=='sparse':self.d['accessors'][0]['sparse']={}
            elif change=='morph':self.d['meshes'][0]['primitives'][0]['targets']=[{'POSITION':0}]
            else:self.d['buffers'][0]['uri']='private.bin'
            with self.assertRaises(m.PreparationError):self.prepare()
    def test_overflow_and_cycle_rejected(self):
        self.d['accessors'][0]['count']=1000001
        with self.assertRaises(m.PreparationError):self.prepare()
        self.d,self.bin=fixture();self.d['nodes'][0]['children']=[0]
        with self.assertRaises(m.PreparationError):self.prepare()
    def test_publish_fresh_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp).resolve();source=root/'s.glb';source.write_bytes(m.pack(self.d,self.bin))
            r=m.publish(source,'gran-turismo-4/fixture','Fixture',root/'prepared',minimum_free=0)
            mesh=root/'prepared'/(r['prepared_sha256']+'.glb')
            self.assertEqual(hashlib.sha256(mesh.read_bytes()).hexdigest(),r['prepared_sha256'])
            self.assertEqual(len(list((root/'prepared').iterdir())),3)
            self.assertEqual(inspect_real(source,root/'prepared')['mesh_nodes'],9)
            with self.assertRaises(m.PreparationError):m.publish(source,'gran-turismo-4/fixture','Fixture',root/'prepared',minimum_free=0)
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),r['source_sha256'])
    def test_malformed_metadata_container(self):
        self.d['extras']=[]
        with self.assertRaises(m.PreparationError): self.prepare()
    def test_invalid_profile_id_and_name(self):
        raw=m.pack(self.d,self.bin)
        for identifier,name in [('gran-turismo/car','Car'),('gran-turismo-4/fixture','bad\nname'),('gran-turismo-4/other','Car')]:
            with self.assertRaises(m.PreparationError):m.prepare(raw,identifier,name)

def inspect_real(source, directory):
    """Independent struct-based pass over complete source/prepared geometry and descriptor."""
    source=Path(source);directory=Path(directory)
    def decode(data):
        assert data[:4]==b'glTF' and struct.unpack_from('<I',data,8)[0]==len(data)
        size=struct.unpack_from('<I',data,12)[0]
        doc=json.loads(data[20:20+size]);offset=20+size
        length,kind=struct.unpack_from('<II',data,offset)
        assert kind==0x004e4942
        return doc,data[offset+8:offset+8+length]
    descriptors=list(directory.glob('*.vehicle'));assert len(descriptors)==1
    tokens=[shlex.split(line) for line in descriptors[0].read_text().splitlines()]
    fields={line[0]:line[1:] for line in tokens if line[0] not in ('wheel','group')}
    prepared=directory/fields['mesh'][0];raw=prepared.read_bytes();original=source.read_bytes()
    assert hashlib.sha256(raw).hexdigest()==fields['sha256'][0]
    assert hashlib.sha256(original).hexdigest()==fields['source_sha256'][0]
    d,b=decode(raw);old,ob=decode(original)
    assert b[:len(ob)]==ob
    for key in ('materials','images','textures','samplers','extensions'):
        assert d.get(key)==old.get(key),key
    def read(doc,buffer,index):
        a=doc['accessors'][index];view=doc['bufferViews'][a['bufferView']]
        fmt,unit={5121:('B',1),5123:('H',2),5125:('I',4),5126:('f',4)}[a['componentType']]
        width={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}[a['type']]
        start=view.get('byteOffset',0)+a.get('byteOffset',0);stride=view.get('byteStride',width*unit)
        return [struct.unpack_from('<'+fmt*width,buffer,start+i*stride) for i in range(a['count'])]
    primitive_count=0
    for mi,mesh in enumerate(old['meshes']):
        for pi,primitive in enumerate(mesh['primitives']):
            new=d['meshes'][mi]['primitives'][pi];primitive_count+=1
            assert primitive==new
            for attribute,index in primitive['attributes'].items():
                before=read(old,ob,index);after=read(d,b,index)
                expected=[tuple(-v if axis==2 or (attribute=='TANGENT' and axis==3) else v for axis,v in enumerate(row)) for row in before] if attribute in ('POSITION','NORMAL','TANGENT') else before
                assert after==expected,attribute
            before=read(old,ob,primitive['indices']);after=read(d,b,new['indices'])
            expected=[v for i in range(0,len(before),3) for v in (before[i],before[i+2],before[i+1])]
            assert after==expected,'winding'
    group={int(line[1]):int(line[2]) for line in tokens if line[0]=='group'}
    assert int(fields['groups'][0])==len(group)==9
    lower=list(map(float,fields['body'][:3]));upper=list(map(float,fields['body'][3:]))
    wheel_rows={line[1]:list(map(float,line[2:])) for line in tokens if line[0]=='wheel'}
    seen=set();vertices=triangles=0
    def visit(index,scale,translation):
        nonlocal vertices,triangles
        assert index not in seen;seen.add(index)
        node=d['nodes'][index];local=node.get('translation',[0,0,0]);local_scale=node.get('scale',[1,1,1])
        world=[translation[i]+scale[i]*local[i] for i in range(3)];sc=[scale[i]*local_scale[i] for i in range(3)]
        if 'mesh' in node:
            assert index in group
            for primitive in d['meshes'][node['mesh']]['primitives']:
                positions=read(d,b,primitive['attributes']['POSITION']);vertices+=len(positions)
                triangles+=len(read(d,b,primitive['indices']))//3
                if group[index]==-1:
                    for row in positions:
                        point=[row[i]*sc[i]+world[i] for i in range(3)]
                        assert all(lower[i]-1e-9<=point[i]<=upper[i]+1e-9 for i in range(3)),'body bounds'
                else:
                    x,y,z,radius,width=wheel_rows[m.LABELS[group[index]]]
                    for row in positions:
                        point=[row[i]*sc[i]+world[i] for i in range(3)]
                        assert abs(point[0]-x)<=width/2+1e-9, 'wheel width'
                        assert math.hypot(point[1]-y,point[2]-z)<=radius+1e-9, 'wheel radius'
        for child in node.get('children',[]):visit(child,sc,world)
    for node in d['scenes'][d.get('scene',0)]['nodes']:visit(node,[1,1,1],[0,0,0])
    assert set(group)=={i for i in seen if 'mesh' in d['nodes'][i]}
    for line in tokens:
        if line[0]=='wheel':
            x,y,z,radius,width=map(float,line[2:]);assert y>=radius-1e-9 and radius>0 and width>0
    return {'prepared_sha256':fields['sha256'][0], 'source_sha256':fields['source_sha256'][0], 'mesh_nodes':len(group),'unique_primitives':primitive_count,'instanced_vertices':vertices,'instanced_triangles':triangles,'embedded_binary_preserved':True,'materials_preserved':True,'all_geometry_mirrors_and_winding_verified':True,'descriptor_body_bounds_verified':True,'descriptor_all_rim_tire_cylinders_verified':True}

if __name__=='__main__':
    if '--prepared' in sys.argv:
        parser=argparse.ArgumentParser();parser.add_argument('--prepared',required=True);parser.add_argument('--source',required=True)
        args=parser.parse_args();print(json.dumps(inspect_real(args.source,args.prepared),indent=2))
    else:unittest.main()

