import sys
sys.dont_write_bytecode = True
import importlib.util
import json
from pathlib import Path
import tempfile
spec=importlib.util.spec_from_file_location('query',Path(__file__).parents[1]/'scripts/diagnostics.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
with tempfile.TemporaryDirectory() as directory:
 p=Path(directory)/'run.jsonl'
 def row(event,seq,**kw): return {'schema':1,'run':'run','event':event,'seq':seq,**kw}
 def issues(rows):
  p.write_text(''.join(json.dumps(r)+'\n' for r in rows));return module.inspect(p)[1]
 assert not issues([row('recorder_start',1),row('recorder_end',2)])
 assert any('end missing' in i for i in issues([row('recorder_start',1)]))
 assert any('sequence' in i for i in issues([row('recorder_start',1),row('recorder_end',1)]))
 assert any('dropped' in i for i in issues([row('recorder_start',1),row('recorder_end',2,dropped=2)]))
 p.write_text('{"partial":')
 assert any('unreadable' in i for i in module.inspect(p)[1])
 p.write_bytes((json.dumps(row('recorder_start',1))+'\n').encode()+b'\xff\xfe\n'+(json.dumps(row('recorder_end',3))+'\n').encode())
 retained, warnings=module.inspect(p)
 assert len(retained)==2 and any('unreadable row 2' in i for i in warnings)
 assert any('sequence' in i for i in warnings)
 for field in ('utc_ms','seq','operation','parent_operation','dropped'):
  malformed=row('state',2);malformed[field]='unexpected'
  assert any('unreadable' in i for i in issues([row('recorder_start',1),malformed,row('recorder_end',3)]))
print('PASS: missing ends, truncated/invalid UTF-8 rows, mistyped numeric fields, duplicate/out-of-order sequences and drop detection')
# Whole corrupt stores must expose damage, and bundles must retain run context.
import subprocess
import hashlib
with tempfile.TemporaryDirectory() as directory:
 root=Path(directory);store=root/'history';store.mkdir();captures=root/'captures';captures.mkdir()
 image=b'P6\n1 1\n255\nabc';digest=hashlib.sha256(image).hexdigest();(captures/'app.ppm').write_bytes(image)
 events=[row('recorder_start',1,utc_ms=1),row('command',2,utc_ms=2,operation=7),row('capture_end',3,utc_ms=3,sha256=digest,success=True),row('recorder_end',4,utc_ms=4)]
 (store/'run.jsonl').write_text(''.join(json.dumps(e)+'\n' for e in events));(store/'damaged.jsonl').write_bytes(b'\xff\n')
 command=[sys.executable,str(Path(__file__).parents[1]/'scripts/diagnostics.py'),'--root',str(store)]
 result=subprocess.run(command+['--run','damaged','--summary'],capture_output=True,text=True)
 assert result.returncode==1 and 'unreadable row 1' in result.stdout
 bundle=root/'bundle';result=subprocess.run(command+['--run','run','--operation','7','--limit','1','--bundle',str(bundle),'--capture-root',str(captures)],capture_output=True,text=True)
 assert result.returncode==0,result.stderr
 manifest=json.loads((bundle/'manifest.json').read_text());assert not manifest['issues'],manifest
 assert manifest['captures']==[{'sha256':digest,'available':True}]
 assert (bundle/'run.jsonl').read_bytes()==(store/'run.jsonl').read_bytes()
 assert (bundle/('capture-'+digest)).read_bytes()==image
 assert (bundle/'run.jsonl').stat().st_mode & 0o777==0o600
 assert bundle.stat().st_mode & 0o777==0o700
 # Retrieval still works once the original store has moved.
 store.rename(root/'retained-original')
 query=subprocess.run([sys.executable,str(Path(__file__).parents[1]/'scripts/diagnostics.py'),'--root',str(bundle),'--summary'],capture_output=True,text=True)
 assert query.returncode==0 and json.loads(query.stdout)['matched_events']==4
 assert subprocess.run(command+['--bundle',str(bundle)],capture_output=True).returncode==1
 original=root/'retained-original/run.jsonl'
 missing=module.preserve(root/'missing',[original],None,1024,{})
 assert not missing['captures'][0]['available'] and missing['issues']
 quota=module.preserve(root/'quota',[original],None,10,{})
 assert not quota['files'] and any('budget omitted' in i for i in quota['issues'])
 link=root/'link.jsonl';link.symlink_to(original)
 refused=module.preserve(root/'refused',[link],None,1024,{})
 assert not refused['files'] and 'symlink refused' in refused['issues'][0]
 original.write_text(json.dumps(row('recorder_end',1)))
 assert any('unterminated' in i for i in module.inspect(original)[1])
print('PASS: corrupt-only visibility, whole-run/capture preservation, private modes, moved-store retrieval, missing captures, quotas, symlinks and unterminated tails')
# A real partial output followed by injected EIO must reserve its payload so
# subsequent files cannot bypass the bundle cap.
from unittest.mock import patch
with tempfile.TemporaryDirectory() as directory:
 root=Path(directory);a=root/'a.jsonl';b=root/'b.jsonl';a.write_bytes(b'0123456789');b.write_bytes(b'abcdefghij');dest=root/'failed-copy'
 original_open=Path.open
 class PartialWrite:
  def __init__(self,stream): self.stream=stream
  def __enter__(self): return self
  def write(self,data):
   self.stream.write(data[:5]);raise OSError(5,'injected after partial write')
  def __exit__(self,*args): self.stream.close()
 def failing_open(path,*args,**kwargs):
  stream=original_open(path,*args,**kwargs)
  return PartialWrite(stream) if path==dest/'a.jsonl' and args==('xb',) else stream
 with patch.object(Path,'open',failing_open): result=module.preserve(dest,[a,b],None,15,{})
 assert result['bytes']==10 and not result['files'] and (dest/'a.jsonl').stat().st_size==5
 assert not (dest/'b.jsonl').exists() and any('byte budget omitted' in issue for issue in result['issues'])
print('PASS: partial export write preserves evidence of failure and reserves payload before retry')
# A readable run must not hide rejected or uninspectable neighboring sources.
import contextlib
import io
with tempfile.TemporaryDirectory() as directory:
 root=Path(directory);store=root/'history';store.mkdir()
 valid=[row('recorder_start',1,profile='chosen'),row('recorder_end',2)]
 (store/'run.jsonl').write_text(''.join(json.dumps(e)+'\n' for e in valid))
 link=store/'refused.jsonl';link.symlink_to(store/'run.jsonl')
 def bundle(name,flags=()):
  with patch.object(sys,'argv',['diagnostics','--root',str(store),'--bundle',str(root/name),*flags]),contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
   status=module.main()
  result=json.loads((root/name/'manifest.json').read_text());assert status==2 and result['issues'];return result
 result=bundle('symlink-bundle');assert any('symlink refused' in e for e in result['issues'])
 assert not (root/'symlink-bundle/refused.jsonl').exists()
 unreadable=store/'unreadable.jsonl';unreadable.write_bytes(b'fixture')
 def denied_open(path,*args,**kwargs):
  if path==unreadable and args==('rb',):raise PermissionError(13,'fixture denied')
  return original_open(path,*args,**kwargs)
 with patch.object(Path,'open',denied_open): result=bundle('denied-bundle')
 assert any('inspection unavailable errno=13' in e for e in result['issues'])
 result=bundle('profile-bundle',['--profile','chosen'])
 assert any('profile correlation unknown' in e for e in result['issues'])
print('PASS: mixed valid/unavailable stores preserve refusal and access warnings in manifest and exit2')
