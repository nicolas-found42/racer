import sys
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).parents[1]/'scripts'))
import base64
import hashlib
import struct
import tempfile
import zlib
from slrr_resources import ResourceResolver
from slrr_assets import gltf
from slrr_gltf_materials import attach_diffuse,png_dimensions

def chunk(name,data):return struct.pack('>I',len(data))+name+data+struct.pack('>I',zlib.crc32(name+data)&0xffffffff)
# Independent1x1 opaque red RGBA PNG, including valid chunk checksums.
png=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',1,1,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(b'\x00\xff\x00\x00\xff'))+chunk(b'IEND',b'')
assert png_dimensions(png)==(1,1)
with tempfile.TemporaryDirectory() as directory:
 root=Path(directory)
 for name in ['white','clear','frame','dashboard']:(root/(name+'.png')).write_bytes(png)
 slots=[]
 for i,name in enumerate(['white','clear',None,'frame','dashboard']):
  slots.append({'index':i,'status':'resolved' if name else 'null','sources':[{'path':name+'.png','sha256':hashlib.sha256(png).hexdigest()}] if name else []})
 meshes=[]
 for index in [0,3,4,5,2,65535]:meshes.append({'positions':[(0,0,0),(1,0,0),(0,0,1)],'triangles':[(0,1,2)],'uv1':[(0,0),(1,0),(0,1)],'texture_indices':[index,65535,65535,2,1]})
 result={'version':3,'geometry':meshes,'limitations':[]}
 original=gltf(result);scene,report=attach_diffuse(original,meshes,slots,ResourceResolver(root))
 assert [b['status'] for b in report['bindings']]==['bound','bound','bound','unresolved','unresolved','absent']
 assert [b.get('source_path') for b in report['bindings'][:3]]==['white.png','frame.png','dashboard.png']
 assert report['texture_slots'][2]['status']=='null'
 assert scene['buffers']==original['buffers'] and scene['accessors']==original['accessors']
 assert all(a['attributes']==b['attributes'] and a['indices']==b['indices'] for a,b in zip(scene['meshes'][0]['primitives'],original['meshes'][0]['primitives']))
 assert scene['materials'][3]['extras']['binding']['texture_slot']==5 and 'baseColorTexture' not in scene['materials'][3]['pbrMetallicRoughness']
 for image in scene['images']:assert base64.b64decode(image['uri'].split(',',1)[1])==png
 assert len(scene['images'])==1 # exact byte hash deduplication
 corrupted=[dict(s) for s in slots];corrupted[0]=dict(slots[0],sources=[{'path':'white.png','sha256':'wrong'}])
 _,bad=attach_diffuse(original,meshes,corrupted,ResourceResolver(root));assert bad['bindings'][0]['status']=='unresolved' and 'hash mismatch' in bad['bindings'][0]['reason']
 broken=bytearray(png);broken[29]^=1
 try:png_dimensions(broken)
 except ValueError:pass
 else:raise AssertionError('invalid PNG IHDR accepted')
print('PASS: literal zero-based diffuse binding, null/sentinel/out-of-range preservation, source hash checks, embedded image bytes, unchanged geometry and neutral unresolved material')
