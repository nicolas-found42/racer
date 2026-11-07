import importlib.util
from pathlib import Path
import tempfile
import struct
import sys
sys.dont_write_bytecode=True
spec=importlib.util.spec_from_file_location('slrr_resources',Path(__file__).parents[1]/'scripts/slrr_resources.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def package(records,links=()):
 header=b'RPAK'+struct.pack('<III',512,len(links),0)
 for i,name in enumerate(links):header+=struct.pack('<I',(i+1)<<16)+name.encode()+b'\0'+bytes(59-len(name))
 count=len(records);table_size=sum(23+len(alias.encode())+1 for rid,kind,alias,text in records);offset=len(header)+16+table_size;table=bytearray();payload=bytearray()
 for rid,kind,alias,text in records:
  data=text.encode();a=alias.encode()+b'\0';table+=struct.pack('<IIBBfIIB',0,rid,kind,0,1,offset,len(data),len(a))+a;payload+=data;offset+=len(data)
 return header+struct.pack('<IIII',table_size,count,0,count)+table+payload
blob=package([(1,14,'body','mesh 0x2\ntexture 0x3\ntexture 0\ntexture 0x3\n'),(2,5,'mesh','sourcefile body.scx\n'),(3,7,'texture','sourcefile paint.png\n')]);parsed=m.parse_rpk(blob);assert len(parsed['resources'])==3
for bad in [b'',blob[:-1],blob[:4]+struct.pack('<I',1)+blob[8:],blob[:8]+struct.pack('<I',2000)+blob[12:]]:
 try:m.parse_rpk(bad);raise AssertionError('accepted malformed package')
 except ValueError:pass
bad=bytearray(blob);struct.pack_into('<I',bad,16+16+14,0)
try:m.parse_rpk(bad);raise AssertionError('bad range accepted')
except ValueError:pass
with tempfile.TemporaryDirectory() as directory:
 root=Path(directory);(root/'car.rpk').write_bytes(blob);(root/'body.scx').write_bytes(b'fixture geometry');(root/'paint.png').write_bytes(b'fixture image')
 resolver=m.ResourceResolver(root);result=resolver.resolve('car.rpk',1);refs=result['references'];assert [e['command'] for e in refs]==['mesh','texture','texture','texture'];assert refs[2]['reference']['status']=='null';assert refs[1]['reference']['identity']==refs[3]['reference']['identity'];assert refs[1]['reference']['sources'][0]['sha256']==m.digest(b'fixture image')
 (root/'other.rpk').write_bytes(package([(3,7,'external','sourcefile paint.png\n')]))
 (root/'external.rpk').write_bytes(package([(1,14,'ref','texture 0x10003\n')],['other.rpk']))
 assert m.ResourceResolver(root).resolve('external.rpk',1)['references'][0]['reference']['identity']=='other.rpk:0x0003'
 (root/'ambiguous.rpk').write_bytes(package([(1,7,'first',''),(1,7,'second','')]))
 assert m.ResourceResolver(root).resolve('ambiguous.rpk',1)['status']=='ambiguous'
 (root/'cycle.rpk').write_bytes(package([(1,14,'cycle','mesh 0x1\n')]))
 for pkg,rid in [('cycle.rpk',1),('car.rpk',999)]:
  try:m.ResourceResolver(root).resolve(pkg,rid);raise AssertionError('cycle/missing accepted')
  except ValueError:pass
 for path in ['../escape','/etc/passwd','C:\\escape']:
  try:resolver.path(path);raise AssertionError('unsafe path')
  except ValueError:pass
 (root/'link.rpk').symlink_to(root/'car.rpk')
 try:resolver.package('link.rpk');raise AssertionError('symlink accepted')
 except ValueError:pass
print('PASS: RPAK512 ranges/header/truncation, exact reference order/null/duplicates, package scope, ambiguous IDs, cycles, missing resources and containment')
