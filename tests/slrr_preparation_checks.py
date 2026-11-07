#!/usr/bin/env python3
"""Bounded SLRR assembly-to-runtime conversion and independent artifact checks."""
import argparse
import base64
import copy
import hashlib
import io
import json
import math
from pathlib import Path
import shlex
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import prepare_slrr_vehicle as m

PNG=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4z8DwHwAFgAI/ScLbtAAAAABJRU5ErkJggg==')

def fixture():
    binary=bytearray();views=[];accessors=[]
    def accessor(rows,kind,ctype=5126):
        binary.extend(b'\0'*(-len(binary)%4));at=len(binary);fmt='f' if ctype==5126 else 'H'
        for row in rows:binary.extend(struct.pack('<'+fmt*len(row),*row))
        views.append({'buffer':0,'byteOffset':at,'byteLength':len(binary)-at});accessors.append({'componentType':ctype,'type':kind,'count':len(rows),'bufferView':len(views)-1});return len(accessors)-1
    tire=accessor([(-10,0,-34),(10,0,34),(0,34,0)],'VEC3');body=accessor([(-100,-40,-220),(100,-40,-220),(0,50,230)],'VEC3')
    normal=accessor([(0,0,1)]*3,'VEC3');tangent=accessor([(1,0,0,1)]*3,'VEC4');uv=accessor([(0,0),(1,0),(.5,1)],'VEC2');indices=accessor([(0,),(1,),(2,)],'SCALAR',5123)
    frames=[[-.84,-.47,-1.09],[.84,-.47,-1.09],[-.94,-.47,1.62],[.94,-.47,1.62]]
    cfg=('\n'.join('# '+label+' wheel #\nwheel '+' '.join(map(str,frame))+' 0 0 0' for label,frame in zip(m.LABELS,frames))+'\n').encode()
    nodes=[];parts=[]
    for alias,center in [('body',[0,0,0])]+[(prefix+'-'+str(i),center) for i,center in enumerate(frames) for prefix in ('rim','tyre')]:
        world=[[float(i==j) for j in range(4)] for i in range(4)]
        for i in range(3):world[i][3]=center[i]
        matrix=[(.01*world[i][j] if j<3 and i<3 else world[i][j]) for j in range(4) for i in range(4)]
        nodes.append({'name':alias,'mesh':0 if alias=='body' else 1,'matrix':matrix})
        parts.append({'alias':alias,'cfg_path':'chassis.cfg' if alias=='body' else alias+'.cfg','world':world,'render':{'pose':[0]*6},'source_selection':'Furrano_GT54.java stock_parts_list_RGear_wheels[0..3]','bindings':{'issues':[]}})
    meshes=[{'primitives':[{'attributes':{'POSITION':p,'NORMAL':normal,'TANGENT':tangent,'TEXCOORD_0':uv},'indices':indices,'material':0}]} for p in (body,tire)]
    d={'asset':{'version':'2.0'},'scene':0,'scenes':[{'nodes':list(range(9))}],'nodes':nodes,'meshes':meshes,'buffers':[{'byteLength':len(binary),'uri':'data:application/octet-stream;base64,'+base64.b64encode(binary).decode()}],'bufferViews':views,'accessors':accessors,'images':[{'name':'pixel','uri':'data:image/png;base64,'+base64.b64encode(PNG).decode()}],'materials':[{'name':'original','pbrMetallicRoughness':{'baseColorTexture':{'index':0}}}],'textures':[{'source':0}],'extras':{'assembly_issues':[]}}
    report={'parts':parts,'issues':[],'provenance':[{'path':'chassis.cfg','sha256':hashlib.sha256(cfg).hexdigest()}],'limitations':['Static fixture.']}
    return d,report,cfg

class Checks(unittest.TestCase):
    def setUp(self):self.d,self.r,self.cfg=fixture()
    def prepare(self):
        data=json.dumps(self.d).encode();report=json.dumps(self.r).encode()
        return m.prepare(data,report,self.cfg,source_sha=hashlib.sha256(data).hexdigest(),report_sha=hashlib.sha256(report).hexdigest(),cfg_sha=hashlib.sha256(self.cfg).hexdigest())
    def test_groups_pivots_clearance_and_roles(self):
        raw,descriptor,r=self.prepare();d,b=m.glb.unpack(raw)
        self.assertEqual(len(r['groups']),9);self.assertEqual([w for _,w in r['groups']],[-1,0,0,1,1,2,2,3,3])
        self.assertEqual(r['wheels'][0]['center'][0],-.84);self.assertEqual(r['wheels'][0]['center'][2],1.09)
        self.assertTrue(all(w['center'][1]>=w['radius']-1e-12 for w in r['wheels']));self.assertGreater(r['body'][1],0)
        self.assertFalse(r['runtime_player_eligible']);self.assertFalse(d['extras']['racerPreparation']['runtime_player_eligible'])
        self.assertIn('vehicle-'+hashlib.sha256(raw).hexdigest(),descriptor)
    def test_attributes_winding_materials_and_image_bytes(self):
        raw,_,r=self.prepare();d,b=m.glb.unpack(raw);g=m.glb.Geometry(d,b)
        self.assertEqual(g.values(0)[0],(-10,0,34));self.assertEqual(g.values(2)[0],(0,0,-1));self.assertEqual(g.values(3)[0],(1,0,0,-1));self.assertEqual(g.values(5),[(0,),(2,),(1,)])
        self.assertEqual(d['materials'],self.d['materials']);self.assertEqual(d['textures'],self.d['textures'])
        view=d['bufferViews'][d['images'][0]['bufferView']];self.assertEqual(bytes(b[view['byteOffset']:view['byteOffset']+view['byteLength']]),PNG)
    def test_arbitrary_rotation_conjugated(self):
        world=m.pose([0,0,0,.2,.1,.15]);self.r['parts'][0]['world']=world
        self.d['nodes'][0]['matrix']=[world[i][j]*(.01 if i<3 and j<3 else 1) for j in range(4) for i in range(4)]
        raw,_,_=self.prepare();d,b=m.glb.unpack(raw);before=self.d['nodes'][0]['matrix'];after=d['nodes'][0]['matrix']
        self.assertEqual(after,[(-v if (i%4==2)!=(i//4==2) else v) for i,v in enumerate(before)])
    def test_wrong_pins_and_pivot_rejected(self):
        with self.assertRaisesRegex(m.PreparationError,'source_pin'):m.prepare(json.dumps(self.d).encode(),json.dumps(self.r).encode(),self.cfg)
        self.r['parts'][1]['world'][0][3]+=.1;self.d['nodes'][1]['matrix'][12]+=.1
        with self.assertRaisesRegex(m.PreparationError,'wheel_pivot_mismatch'):self.prepare()
    def test_unknown_cfg_labels_and_partial_assembly(self):
        self.cfg=self.cfg.replace(b'# FL wheel #',b'# unknown #')
        with self.assertRaisesRegex(m.PreparationError,'cfg_wheel_identity'):self.prepare()
        self.d,self.r,self.cfg=fixture();self.r['issues']=['missing part']
        with self.assertRaisesRegex(m.PreparationError,'unresolved_assembly'):self.prepare()
    def test_matrix_shear_skin_and_pose_mismatch(self):
        self.d['nodes'][0]['matrix'][0]=.02
        with self.assertRaisesRegex(m.PreparationError,'source_mesh_scale'):self.prepare()
        self.d,self.r,self.cfg=fixture();self.d['nodes'][0]['skin']=0
        with self.assertRaisesRegex(m.PreparationError,'node_features'):self.prepare()
        self.d,self.r,self.cfg=fixture();self.d['nodes'][0]['matrix'][12]=1
        with self.assertRaisesRegex(m.PreparationError,'assembly_pose_mismatch'):self.prepare()
    def test_external_uri_and_index_budget(self):
        self.d['buffers'][0]['uri']='private.bin'
        with self.assertRaisesRegex(m.PreparationError,'external_or_unsupported_uri'):self.prepare()
        self.d,self.r,self.cfg=fixture();self.d['accessors'][5]['count']=3000003
        with self.assertRaisesRegex(m.PreparationError,'index_work_budget'):self.prepare()
    def test_fresh_private_publication(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary).resolve();src=root/'source.gltf';report=root/'source.json';cfg=root/'source.cfg';src.write_text(json.dumps(self.d));report.write_text(json.dumps(self.r));cfg.write_bytes(self.cfg)
            original=m.prepare
            def fake(data,metadata,config,name):return original(data,metadata,config,name,source_sha=hashlib.sha256(data).hexdigest(),report_sha=hashlib.sha256(metadata).hexdigest(),cfg_sha=hashlib.sha256(config).hexdigest())
            with patch.object(m,'prepare',side_effect=fake):
                r=m.publish(src,report,cfg,root/'prepared',minimum_free=0)
                self.assertEqual(inspect_actual(src,root/'prepared')['groups'],9)
                with self.assertRaises(m.PreparationError):m.publish(src,report,cfg,root/'prepared',minimum_free=0)
            self.assertTrue(all(p.stat().st_mode&0o777==0o600 for p in (root/'prepared').iterdir()))


def inspect_actual(source,directory):
    """Independent complete source/prepared accessor, transform, image and containment pass."""
    source=Path(source);directory=Path(directory);original=source.read_bytes();old=json.loads(original);old_buffers=[base64.b64decode(b['uri'].split(',',1)[1],validate=True) for b in old['buffers']]
    descriptor=next(directory.glob('*.vehicle'));tokens=[shlex.split(line) for line in descriptor.read_text().splitlines()];fields={row[0]:row[1:] for row in tokens if row[0] not in ('group','wheel')}
    raw=(directory/fields['mesh'][0]).read_bytes();assert raw[:4]==b'glTF' and struct.unpack_from('<I',raw,8)[0]==len(raw)
    assert hashlib.sha256(raw).hexdigest()==fields['sha256'][0] and hashlib.sha256(original).hexdigest()==fields['source_sha256'][0]
    size=struct.unpack_from('<I',raw,12)[0];d=json.loads(raw[20:20+size]);at=20+size;length,kind=struct.unpack_from('<II',raw,at);assert kind==0x004e4942;b=raw[at+8:at+8+length]
    for key in ('materials','textures','samplers'):assert old.get(key)==d.get(key)
    offset=0
    for buffer in old_buffers:
        offset+=-offset%4;assert b[offset:offset+len(buffer)]==buffer;offset+=len(buffer)
    for before,after in zip(old.get('images',[]),d.get('images',[])):
        image=base64.b64decode(before['uri'].split(',',1)[1],validate=True);view=d['bufferViews'][after['bufferView']]
        assert b[view.get('byteOffset',0):view.get('byteOffset',0)+view['byteLength']]==image
    def read(doc,buffers,index):
        a=doc['accessors'][index];v=doc['bufferViews'][a['bufferView']];binary=buffers[v.get('buffer',0)];fmt,unit={5121:('B',1),5123:('H',2),5125:('I',4),5126:('f',4)}[a['componentType']];n={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}[a['type']];at=v.get('byteOffset',0)+a.get('byteOffset',0);stride=v.get('byteStride',unit*n)
        return [struct.unpack_from('<'+fmt*n,binary,at+i*stride) for i in range(a['count'])]
    for mesh in old['meshes']:
        for primitive in mesh['primitives']:
            for attribute,index in primitive['attributes'].items():
                before=read(old,old_buffers,index);after=read(d,[b],index)
                expected=[tuple(-value if axis==2 or (attribute=='TANGENT' and axis==3) else value for axis,value in enumerate(row)) for row in before] if attribute in ('POSITION','NORMAL','TANGENT') else before
                assert after==expected,attribute
            indices=read(old,old_buffers,primitive['indices']);assert read(d,[b],primitive['indices'])==[v for i in range(0,len(indices),3) for v in (indices[i],indices[i+2],indices[i+1])]
    groups={int(row[1]):int(row[2]) for row in tokens if row[0]=='group'};assert len(groups)==len(old['nodes'])==int(fields['groups'][0]);bounds=list(map(float,fields['body']));wheels={row[1]:list(map(float,row[2:])) for row in tokens if row[0]=='wheel'}
    lift=d['nodes'][-1]['translation'][1];vertices=triangles=0
    for ni,node in enumerate(old['nodes']):
        M=node['matrix'];N=d['nodes'][ni]['matrix'];assert N==[(-v if (i%4==2)!=(i//4==2) else v) for i,v in enumerate(M)]
        for primitive in old['meshes'][node['mesh']]['primitives']:
            before=read(old,old_buffers,primitive['attributes']['POSITION']);after=read(d,[b],primitive['attributes']['POSITION']);vertices+=len(before);triangles+=len(read(old,old_buffers,primitive['indices']))//3
            for p,q in zip(before,after):
                original_point=[sum(M[j*4+i]*p[j] for j in range(3))+M[12+i] for i in range(3)];point=[sum(N[j*4+i]*q[j] for j in range(3))+N[12+i]+(lift if i==1 else 0) for i in range(3)]
                assert all(abs(point[i]-(original_point[i] if i<2 else -original_point[i])-(lift if i==1 else 0))<1e-8 for i in range(3))
                if groups[ni]<0:assert all(bounds[i]-1e-9<=point[i]<=bounds[i+3]+1e-9 for i in range(3))
                else:
                    x,y,z,radius,width=wheels[m.LABELS[groups[ni]]];assert abs(point[0]-x)<=width/2+1e-9 and math.hypot(point[1]-y,point[2]-z)<=radius+1e-9
    assert d['scenes'][0]['nodes']==[len(old['nodes'])] and d['nodes'][-1]['children']==list(range(len(old['nodes'])))
    return {'source_sha256':fields['source_sha256'][0],'prepared_sha256':fields['sha256'][0],'groups':len(groups),'vertices':vertices,'triangles':triangles,'source_buffer_and_image_bytes_preserved':True,'materials_textures_samplers_preserved':True,'all_world_vertices_equal_source_mirror_plus_lift':True,'all_body_wheel_containment_verified':True,'runtime_player_eligible':d['extras']['racerPreparation']['runtime_player_eligible'],'scope':'static geometry only; source suspension-height/native visual review required'}

if __name__=='__main__':
    if '--prepared' in sys.argv:
        p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--prepared',required=True);a=p.parse_args();print(json.dumps(inspect_actual(a.source,a.prepared),indent=2))
    else:unittest.main()
