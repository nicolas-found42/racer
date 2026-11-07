import importlib.util
from pathlib import Path
import struct
import sys
sys.dont_write_bytecode=True
spec=importlib.util.spec_from_file_location('assets',Path(__file__).parents[1]/'scripts/slrr_assets.py')
assets=importlib.util.module_from_spec(spec);spec.loader.exec_module(assets)
# Authored independent binary fixture: three positions and one triangle.
header=b'INVO'+struct.pack('<II',4,2)+struct.pack('<IIII',4,28,5,80)
vertices=struct.pack('<IIII',4,52,3,1)+struct.pack('<9f',0,0,0,1,0,0,0,1,0)
indices=struct.pack('<III3H',5,18,3,0,1,2)
fixture=header+vertices+indices
result=assets.scx4(fixture)
assert result['geometry'][0]['triangles']==[(0,1,2)]
assert result['bounds']=={'min':[0.,0.,0.],'max':[1.,1.,0.]}
assert 'f 1 2 3' in assets.obj(result)
for offset,value in [(4,3),(16,999999),(32,9999),(40,0x80000001),(44,0x7fc00000),(94,99)]:
 bad=bytearray(fixture);struct.pack_into('<I' if offset!=94 else '<H',bad,offset,value)
 try:assets.scx4(bad)
 except ValueError:pass
 else:raise AssertionError(('accepted invalid structure',offset))
for shortened in [fixture[:8],fixture[:-1]]:
 try:assets.scx4(shortened)
 except ValueError:pass
 else:raise AssertionError('accepted truncated input')
cfg=assets.cfg(b'# comment\nslot 1 2 3 0 0 0 101 ; named\nattach 0x10 1\nslottype 7\nunknown_extension keep every token\n')
assert cfg['slots'][0]['id']==101 and cfg['slots'][0]['position']==[1.,2.,3.]
assert len(cfg['slots'][0]['rules'])==2 and cfg['commands'][-1]['command']=='unknown_extension'
print('PASS: raw mesh geometry, OBJ indexing, malformed/truncated/range/flag rejection and CFG provenance')
# v3 uses material-sized records, 44-byte base vertices and uint32 faces.
material=struct.pack('<I',56)+bytes(52)
v3=b'INVO'+struct.pack('<I',3)+material+struct.pack('<I',3)
v3+=b''.join(struct.pack('<3f',*p)+bytes(32) for p in [(0,0,0),(1,0,0),(0,0,1)])
v3+=struct.pack('<I3II',1,0,1,2,0)
assert assets.scx(v3)['geometry'][0]['triangles']==[(0,1,2)]
# Influence group4 stores one explicit weight, rather than one word per bit.
bone_header=b'INVO'+struct.pack('<II',4,2)+struct.pack('<IIII',4,28,5,92)
bone_vertices=struct.pack('<IIII',4,64,3,5)+struct.pack('<12f',0,0,0,.5,1,0,0,.5,0,1,0,.5)
bone=assets.scx4(bone_header+bone_vertices+indices)
assert bone['geometry'][0]['positions'][1]==(1.,0.,0.)
assert assets.scx4(b'INVO'+struct.pack('<II',4,0))['bounds'] is None
partial=assets.cfg(b'slot 1 2 3 0 0 0\nattach 1 2\n')
assert partial['issues'] and len(partial['commands'])==2 and not partial['slots']
scene=assets.gltf(assets.scx(v3),.01,.9,True)
assert scene['nodes'][0]['scale']==[-.01,.01,-.01] and scene['nodes'][0]['translation']==[0,.9,0]
assert scene['accessors'][1]['count']==3 and scene['buffers'][0]['uri'].startswith('data:')
print('PASS: v3/v4 bone strides, empty placeholders, missing-slot preservation and embedded glTF export')
# Independent known-answer UV1 bytes; source values may tile outside [0,1].
import base64
uvs=[(.125,.25),(-.5,2.),(1.,.75)]
points=[(0.,0.,0.),(1.,0.,0.),(0.,0.,1.)]
mat=bytearray(material);struct.pack_into('<5H',mat,44,2,3,65535,5,7)
uv3=b'INVO'+struct.pack('<I',3)+mat+struct.pack('<I',3)
uv3+=b''.join(struct.pack('<3f',*point)+bytes(12)+struct.pack('<2f',*uv)+bytes(12) for point,uv in zip(points,uvs))
uv3+=struct.pack('<I3II',1,0,1,2,0)
source3=assets.scx(uv3);mesh3=source3['geometry'][0]
assert mesh3['uv1']==uvs and mesh3['texture_indices']==(2,3,65535,5,7)
assert mesh3['uv1_source']=={'vertex_data_offset':68,'vertex_stride':44,'field_byte_offset':24}
assert mesh3['positions']==points and mesh3['triangles']==[(0,1,2)]
scene=assets.gltf(source3);primitive=scene['meshes'][0]['primitives'][0]
accessor=scene['accessors'][primitive['attributes']['TEXCOORD_0']]
assert accessor['type']=='VEC2' and accessor['count']==len(points) and accessor['componentType']==5126
view=scene['bufferViews'][accessor['bufferView']];blob=base64.b64decode(scene['buffers'][0]['uri'].split(',',1)[1])
assert list(struct.iter_unpack('<ff',blob[view['byteOffset']:view['byteOffset']+view['byteLength']]))==uvs
assert all(view['byteOffset']%4==0 for view in scene['bufferViews'])
assert primitive['extras']['texture_indices']==(2,3,65535,5,7) and primitive['extras']['material_offset']==8
# v4: no influences and all optional fields preceding UV1, respectively.
for flags,prefix in [(1|512,bytes()),(1|4|32|64|128|256|512,struct.pack('<f',.5)+bytes(4+12+4+4))]:
 vertex_payload=b''.join(struct.pack('<3f',*point)+prefix+struct.pack('<2f',*uv) for point,uv in zip(points,uvs))
 size=16+len(vertex_payload);vheader=b'INVO'+struct.pack('<II4I',4,2,4,28,5,28+size)
 fixture_uv=vheader+struct.pack('<4I',4,size,3,flags)+vertex_payload+indices
 decoded=assets.scx4(fixture_uv);assert decoded['geometry'][0]['uv1']==uvs
 assert decoded['geometry'][0]['uv1_source']['field_byte_offset']==12+len(prefix)
 assert decoded['geometry'][0]['positions']==points
 broken=bytearray(fixture_uv);struct.pack_into('<I',broken,28+16+12+len(prefix),0x7fc00000)
 try:assets.scx4(broken)
 except ValueError:pass
 else:raise AssertionError('nonfinite v4 UV accepted')
broken=bytearray(uv3);struct.pack_into('<I',broken,68+24,0x7f800000)
try:assets.scx(broken)
except ValueError:pass
else:raise AssertionError('nonfinite v3 UV accepted')
assert 'TEXCOORD_0' not in assets.gltf(result)['meshes'][0]['primitives'][0]['attributes']
for bad_uv in [[(0.,0.)],[(float('nan'),0.)]*3]:
 bad=dict(source3);bad['geometry']=[dict(mesh3,uv1=bad_uv)]
 try:assets.gltf(bad)
 except ValueError:pass
 else:raise AssertionError('invalid pervertex UV array accepted')
print('PASS: raw v3/v4 UV1 offsets/influence fields, finite/count checks, unchanged topology/material indices and aligned glTF TEXCOORD_0')
