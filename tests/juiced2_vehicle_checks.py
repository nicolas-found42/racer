#!/usr/bin/env python3
"""Known-answer native strip/hierarchy validation and optional actual-bundle containment."""
import sys,struct,math,json,hashlib,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from juiced2_vehicle import mesh,hierarchy,records,filename_hash,profile_surface
from prepare_gt4_vehicle import PreparationError,unpack,Geometry

def rejects(fn,data):
 try:fn(data);raise AssertionError('accepted malformed native payload')
 except (PreparationError,UnicodeError,struct.error):pass

def fixture():
 indices=[0,1,2,65535,0,2,3];prefix=struct.pack('>I7HI',7,*indices,1);d=bytearray(128);d[:4]=b'TEST';struct.pack_into('>I',d,36,7);struct.pack_into('>I',d,104,1);struct.pack_into('>3I',d,108,0,0,0);struct.pack_into('>2I',d,120,12,4);return prefix+d+struct.pack('>12f',0,0,0,1,0,0,1,1,0,0,1,0)+bytes(44)

def actual(directory):
 receipt=json.loads((directory/'receipt.json').read_text());raw=(directory/(receipt['prepared_sha256']+'.glb')).read_bytes();assert hashlib.sha256(raw).hexdigest()==receipt['prepared_sha256'];d,b=unpack(raw);g=Geometry(d,b);seen=set();expanded=0
 binding_roles={r['node']:r['role']for r in receipt.get('binding_roles',[])}
 for node,wheel in receipt['groups']:
  role=binding_roles.get(node,'')
  if role.startswith('carrier '):wheel=['FL','FR','RL','RR'].index(role.split()[1])
  assert node not in seen;seen.add(node)
  for primitive in d['meshes'][d['nodes'][node]['mesh']]['primitives']:
   points=g.values(primitive['attributes']['POSITION']);indices=g.values(primitive['indices']);expanded+=len(indices);assert max(x[0]for x in indices)<len(points)
   for p in points:
    if wheel<0:
     assert all(receipt['body'][k]-2e-7<=p[k]<=receipt['body'][k+3]+2e-7 for k in range(3))
    else:
     w=receipt['wheels'][wheel];c=w['center'];assert abs(p[0]-c[0])<=w['width']/2+2e-7 and math.hypot(p[1]-c[1],p[2]-c[2])<=w['radius']+2e-7
 assert expanded<=1500000 and len(d['nodes'])<=4096 and len(seen)==len(d['nodes']) and {x[1]for x in receipt['groups']}=={-1,0,1,2,3}
 assert receipt['textures']>0 and len(receipt['sources'])>30
 if any(n['name'].startswith('TEST_CALLIPER')for n in d['nodes']):
  assert len([n for n in d['nodes']if n['name'].startswith('TEST_CALLIPER')])==4 and len([n for n in d['nodes']if n['name'].startswith('TEST_DISC')])==4
  source_keys={r['key']for r in receipt['sources']};assert {2201934180,2428427892,448338774,633545958}<=source_keys
  if receipt.get('binding_roles'):
   roles={r['node']:r['role']for r in receipt['binding_roles']};assert sum(r.startswith('carrier ')for r in roles.values())==4
   text=(directory/(receipt['prepared_sha256']+'.vehicle')).read_text();assert text.startswith('RACER_VEHICLE 2\n')
   for i,n in enumerate(d['nodes']):
    if n['name'].startswith('TEST_CALLIPER'):assert roles[i]=='carrier '+n['name'][-2:] and 'group '+str(i)+' '+roles[i] in text
    if n['name'].startswith('TEST_DISC'):assert roles[i]=='wheel '+n['name'][-2:]
 print('PASS actual:',len(d['nodes']),'mesh nodes;',expanded,'expanded vertices; all body/wheel vertices contained;',receipt['textures'],'embedded native textures')

def main():
 b=fixture();m=mesh(b);assert m[0]['indices']==[0,1,2,0,2,3] and m[0]['positions'][3]==(0,1,0)
 bad=bytearray(b);struct.pack_into('>H',bad,4,9);rejects(mesh,bad);rejects(mesh,b[:-1]);rejects(mesh,b+bytes(1))
 h=bytearray(140);h[:4]=b'ROOT';struct.pack_into('>16f',h,32,1,0,0,1,0,1,0,2,0,0,1,3,0,0,0,1);h[100:104]=b'NONE';assert hierarchy(h)[0]['matrix'][3:12:4]==[1,2,3];rejects(hierarchy,h[:-1]);bad=bytearray(h);struct.pack_into('>I',bad,136,129);rejects(hierarchy,bad)
 r=struct.pack('>I6I',1,123,0,8,12,4,1);assert records(r,8)[123][0]==0;rejects(lambda x:records(x,7),r)
 assert filename_hash('mesh\\WHEEL_350Z.xem')==1235513822 and filename_hash('MESH\\wheel_350z.XEM')==1235513822
 profile=bytearray(596);profile[:12]=b'TYRE_PROFILE';struct.pack_into('>2I',profile,96,3,13)
 for i in range(13):
  for j in range(3):struct.pack_into('>3f',profile,104+36*i+12*j,i-6,30,0)
 surface=profile_surface(profile,8,1);assert len(surface['positions'])==104 and len(surface['indices'])==576 and abs(surface['positions'][0][1]-.3)<1e-8;rejects(profile_surface,profile[:-1])
 print('PASS known-answer strips/restarts, native transforms, bounds, hashes and malformed extents')
 if len(sys.argv)>1:actual(Path(sys.argv[1]))
if __name__=='__main__':main()
