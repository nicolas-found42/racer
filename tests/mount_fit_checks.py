"""Track-only mount fitting: inverse-parent mapping and independent whole-vertex checks."""
import copy
import hashlib
import json
import math
from pathlib import Path
import shlex
import struct
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import fit_vehicle_mounts as m

def fixture():
    binary=bytearray();views=[];accessors=[];meshes=[];nodes=[]
    centers=[[-.6,.35,.75],[.6,.35,.75],[-.6,.35,-.75],[.6,.35,-.75]]
    for i in range(9):
        if i==0:points=[[-2,.3,-3],[2,.3,-3],[0,2,3]]
        else:
            c=centers[(i-1)//2];p=[c[0]*2,(c[1]-.05)*2,c[2]*2]
            points=[[p[0]-.02,p[1],p[2]],[p[0]+.02,p[1],p[2]],[p[0],p[1]+.02,p[2]+.02]]
        start=len(binary);binary.extend(struct.pack('<9f',*(x for p in points for x in p)));views.append({'buffer':0,'byteOffset':start,'byteLength':36});accessors.append({'bufferView':len(views)-1,'componentType':5126,'type':'VEC3','count':3});pos=len(accessors)-1
        start=len(binary);binary.extend(struct.pack('<3I',0,1,2));views.append({'buffer':0,'byteOffset':start,'byteLength':12});accessors.append({'bufferView':len(views)-1,'componentType':5125,'type':'SCALAR','count':3})
        meshes.append({'primitives':[{'attributes':{'POSITION':pos},'indices':len(accessors)-1}]});nodes.append({'name':'part'+str(i),'mesh':i})
    nodes.extend([{'translation':[0,.1,0],'children':list(range(9))},{'scale':[.5]*3,'children':[9]}])
    doc={'asset':{'version':'2.0'},'scene':0,'scenes':[{'nodes':[10]}],'nodes':nodes,'meshes':meshes,'accessors':accessors,'bufferViews':views,'buffers':[{'byteLength':len(binary)}]}
    canonical={'canonical_id':'fixture','source':'manufacturer-fixture','nominal':{'front_track':1.4,'rear_track':1.5}}
    return doc,binary,centers,canonical

def generate(doc,binary,centers,canonical):
    raw=m.pack(doc,binary);sha=hashlib.sha256(raw).hexdigest()
    desc='RACER_VEHICLE 1\nid "vehicle-'+sha+'"\nname "fixture"\nmesh "'+sha+'.glb"\nsha256 '+sha+'\nsource_sha256 '+'a'*64+'\nbody -1 .19 -1.5 1 1.06 1.5\n'
    desc+=''.join('wheel '+label+' '+' '.join(map(str,c+[.1,.1]))+'\n' for label,c in zip(m.LABELS,centers))
    desc+='groups 9\ngroup 0 -1\n'+''.join('group '+str(i)+' '+str((i-1)//2)+'\n'for i in range(1,9))
    return raw,desc,m.fit(raw,desc,canonical,expected=sha,descriptor_sha=hashlib.sha256(desc.encode()).hexdigest())

class Checks(unittest.TestCase):
    def test_inverse_uniform_parent_and_body_unchanged(self):
        d,b,c,target=fixture();raw,text,(out,new,r)=generate(d,b,c,target);doc,binary=m.unpack(out)
        self.assertEqual(binary,b);self.assertEqual(doc['nodes'][0],d['nodes'][0]);self.assertEqual(doc['nodes'][9:],d['nodes'][9:])
        for index in (1,2):self.assertAlmostEqual(doc['nodes'][index]['translation'][0],-.2)
        self.assertAlmostEqual(doc['nodes'][7]['translation'][0],.3)
        self.assertEqual(r['wheels'][0][1:],c[0][1:]+[.1,.1]);self.assertAlmostEqual(r['wheels'][0][0],-.7)
        self.assertFalse(r['runtime_player_eligible']);self.assertEqual(doc['extras']['racerTrackMountFit']['runtime_player_eligible'],False)
        self.assertEqual(next(x for x in new.splitlines()if x.startswith('body ')),next(x for x in text.splitlines()if x.startswith('body ')))
    def test_reject_nonuniform_rotated_or_nonidentity_frames(self):
        for mutate in (lambda d:d['nodes'][10].update(scale=[.5,.6,.5]),lambda d:d['nodes'][9].update(rotation=[0,0,0,1]),lambda d:d['nodes'][1].update(translation=[.1,0,0])):
            d,b,c,t=fixture();mutate(d)
            with self.assertRaises(ValueError):generate(d,b,c,t)
    def test_reject_shared_mesh_or_shared_node(self):
        for mutate in (lambda d:d['nodes'][2].update(mesh=1),lambda d:d['nodes'][9]['children'].append(1)):
            d,b,c,t=fixture();mutate(d)
            with self.assertRaises(ValueError):generate(d,b,c,t)
    def test_reject_wrong_pins_or_enclosure(self):
        d,b,c,t=fixture();raw,text,_=generate(d,b,c,t)
        with self.assertRaisesRegex(ValueError,'source_pin'):m.fit(raw,text,t)
        c[0][0]-=.2
        with self.assertRaisesRegex(ValueError,'wheel_containment'):generate(d,b,c,t)
    def test_reject_inward_or_excessive_fit(self):
        for track in (.9,2.8):
            d,b,c,t=fixture();t['nominal']['front_track']=track
            with self.assertRaisesRegex(ValueError,'outward_fit_budget'):generate(d,b,c,t)
    def test_reject_position_budget_before_decode(self):
        d,b,c,t=fixture();d['accessors'][0]['count']=1000001
        with self.assertRaisesRegex(ValueError,'vertex_budget'):generate(d,b,c,t)

def inspect(source_descriptor,output_descriptor):
    """Independent binary, metadata and every transformed vertex comparison."""
    def load(path):
        rows=[shlex.split(x)for x in Path(path).read_text().splitlines()];fields={r[0]:r[1:]for r in rows if r[0]not in ('group','wheel')};raw=Path(path).with_suffix('.glb').read_bytes();assert hashlib.sha256(raw).hexdigest()==fields['sha256'][0];size=struct.unpack_from('<I',raw,12)[0];doc=json.loads(raw[20:20+size]);return rows,doc,raw[28+size:]
    old,a,ab=load(source_descriptor);new,d,db=load(output_descriptor);assert ab==db
    for key in a:
        if key not in ('nodes','extras'):assert a[key]==d[key],key
    before_extra=copy.deepcopy(d['extras']);metadata=before_extra.pop('racerTrackMountFit');assert before_extra==a.get('extras',{})
    groups={int(r[1]):int(r[2])for r in old if r[0]=='group'};assert [r for r in old if r[0]=='group']==[r for r in new if r[0]=='group']
    old_w=[list(map(float,r[2:]))for r in old if r[0]=='wheel'];new_w=[list(map(float,r[2:]))for r in new if r[0]=='wheel'];assert next(r for r in old if r[0]=='body')==next(r for r in new if r[0]=='body')
    for x,y in zip(old_w,new_w):assert x[1:]==y[1:]
    def transforms(doc):
        result={}
        def visit(i,s,t):
            n=doc['nodes'][i];local=n.get('translation',[0,0,0]);shift=[t[k]+s*local[k]for k in range(3)];scale=s*n.get('scale',[1,1,1])[0];result[i]=(scale,shift)
            for child in n.get('children',[]):visit(child,scale,shift)
        for root in doc['scenes'][0]['nodes']:visit(root,1,[0,0,0])
        return result
    A,B=transforms(a),transforms(d);vertices=0
    for i,n in enumerate(a['nodes']):
        if i not in groups or groups[i]<0:assert n==d['nodes'][i]
        else:
            check=copy.deepcopy(d['nodes'][i]);check.pop('translation');original=copy.deepcopy(n);original.pop('translation',None);assert check==original
        if 'mesh'not in n:continue
        delta=0 if groups[i]<0 else new_w[groups[i]][0]-old_w[groups[i]][0]
        for primitive in a['meshes'][n['mesh']]['primitives']:
            acc=a['accessors'][primitive['attributes']['POSITION']];view=a['bufferViews'][acc['bufferView']]
            for j in range(acc['count']):
                point=struct.unpack_from('<3f',ab,view.get('byteOffset',0)+acc.get('byteOffset',0)+j*view.get('byteStride',12));before=[point[k]*A[i][0]+A[i][1][k]for k in range(3)];after=[point[k]*B[i][0]+B[i][1][k]for k in range(3)];assert max(abs(after[k]-before[k]-(delta if k==0 else 0))for k in range(3))<1e-9;vertices+=1
                if groups[i]>=0:
                    c=new_w[groups[i]];assert abs(after[0]-c[0])<=c[4]/2+2e-6 and math.hypot(after[1]-c[1],after[2]-c[2])<=c[3]+2e-6
    assert not metadata['runtime_player_eligible']
    return {'vertices':vertices,'binary_materials_images_indices_normals_unchanged':True,'body_world_vertices_unchanged':True,'wheel_world_vertices_only_declared_delta_x':True,'wheel_enclosures_verified':True,'front_track':new_w[1][0]-new_w[0][0],'rear_track':new_w[3][0]-new_w[2][0],'runtime_player_eligible':False}

if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--inspect':
        print(json.dumps(inspect(sys.argv[2],sys.argv[3]),indent=2))
    else:unittest.main()
