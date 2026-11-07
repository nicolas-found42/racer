import importlib.util
import hashlib
import json
from pathlib import Path
import tempfile
from unittest.mock import patch
import sys
sys.dont_write_bytecode = True
spec=importlib.util.spec_from_file_location('preserve_build',Path(__file__).parents[1]/'scripts/preserve_build.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
def fixture(root):
 for name in ['src/a.cpp','tests/check.cpp','scripts/probe.py',*module.FIXED,*module.SHADERS]:
  path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'x')
 exe=root/'build/racer';exe.parent.mkdir();exe.write_bytes(b'executable-data');return exe
with tempfile.TemporaryDirectory() as directory:
 root=Path(directory)/'repo';root.mkdir();exe=fixture(root);dest=Path(directory)/'bundle'
 report=module.snapshot(root,exe,dest)
 assert not report['issues'],report
 assert report['executable_sha256']==hashlib.sha256(exe.read_bytes()).hexdigest()
 assert 'unverified' in report['source_relation']
 for e in report['files']:
  p=dest/e['file'];assert hashlib.sha256(p.read_bytes()).hexdigest()==e['sha256'];assert p.stat().st_mode&0o777==(0o700 if e['file']=='runtime/racer' else 0o600)
 assert dest.stat().st_mode&0o777==0o700
 before=(dest/'manifest.json').read_bytes()
 try:module.snapshot(root,exe,dest);raise AssertionError('existing destination accepted')
 except FileExistsError:pass
 assert (dest/'manifest.json').read_bytes()==before
 bounded=module.snapshot(root,exe,Path(directory)/'tiny',3)
 assert bounded['payload_reserved_bytes']<=3 and bounded['issues']
 (root/'src/link.cpp').symlink_to(exe)
 refused=module.snapshot(root,exe,Path(directory)/'links')
 assert any('symlink' in x for x in refused['issues']) and not (Path(directory)/'links/source/src/link.cpp').exists()
 (root/'src/link.cpp').unlink()
 (root/'src/private.env').write_text('do not collect')
 noenv=module.snapshot(root,exe,Path(directory)/'noenv');assert not (Path(directory)/'noenv/source/src/private.env').exists()
 missing=root/module.SHADERS[0];missing.unlink();partial=module.snapshot(root,exe,Path(directory)/'missing')
 assert partial['issues'] and (Path(directory)/'missing/manifest.json').is_file()
 missing.write_bytes(b'x')
 # A write creates real partial output before an injected EIO; original input
 # and existing outputs remain intact, and the reservation still bounds later copies.
 output=Path(directory)/'failed';original_open=Path.open
 class FailedWriter:
  def __init__(self,stream):self.stream=stream
  def __enter__(self):return self
  def write(self,data):self.stream.write(data[:2]);raise OSError(5,'injected partial write')
  def __exit__(self,*args):self.stream.close()
 def failing_open(path,*args,**kwargs):
  stream=original_open(path,*args,**kwargs)
  return FailedWriter(stream) if path==output/'runtime/racer' and args==('xb',) else stream
 with patch.object(Path,'open',failing_open):failed=module.snapshot(root,exe,output,16)
 assert failed['issues'] and failed['payload_reserved_bytes']<=16
 assert (output/'runtime/racer').read_bytes()==b'ex' and exe.read_bytes()==b'executable-data'
 assert json.loads((output/'manifest.json').read_text())['issues']
 # Nonregular sources are rejected without blocking on a FIFO.
 import os
 fifo=root/'src/fifo.cpp';os.mkfifo(fifo)
 nonregular=module.snapshot(root,exe,Path(directory)/'nonregular')
 assert any('nonregular' in i for i in nonregular['issues'])
 fifo.unlink()
 # Observe an actual source change between the reader's two metadata samples.
 original_fstat=os.fstat;calls=[0]
 def changed_fstat(fd):
  calls[0]+=1
  if calls[0]==2:exe.write_bytes(b'changed executable-data')
  return original_fstat(fd)
 with patch.object(os,'fstat',changed_fstat):changed=module.snapshot(root,exe,Path(directory)/'changed')
 assert any('source changed during read' in i for i in changed['issues'])
 # os.walk must retain inaccessible-subtree warnings while copying siblings.
 hidden=root/'src/hidden';hidden.mkdir();(hidden/'lost.cpp').write_bytes(b'not inspected')
 original_scandir=os.scandir
 def denied_scandir(path):
  if Path(path)==hidden:raise PermissionError(13,'injected arbitrary text',str(hidden))
  return original_scandir(path)
 with patch.object(os,'scandir',denied_scandir):
  inaccessible=module.snapshot(root,exe,Path(directory)/'inaccessible')
 assert any('src/hidden: traversal unavailable errno=13'==issue for issue in inaccessible['issues'])
 assert (Path(directory)/'inaccessible/source/src/a.cpp').is_file()
 assert not (Path(directory)/'inaccessible/source/src/hidden/lost.cpp').exists()
 assert json.loads((Path(directory)/'inaccessible/manifest.json').read_text())['issues']
 import contextlib,io
 cli_destination=Path(directory)/'inaccessible-cli'
 with patch.object(os,'scandir',denied_scandir),patch.object(Path,'cwd',return_value=root),patch.object(sys,'argv',['preserve_build',str(cli_destination),'--exe',str(exe)]),contextlib.redirect_stdout(io.StringIO()):
  assert module.main()==2
 assert (cli_destination/'source/src/a.cpp').is_file()


 # File/directory/issue counts are independent of the byte budget.
 with patch.object(module,'MAX_FILES',3):counted=module.snapshot(root,exe,Path(directory)/'counted')
 assert counted['selected_files']<=3 and len(counted['files'])<=3
 assert any('count cap reached' in e for e in counted['issues'])
 with patch.object(module,'MAX_DIRECTORIES',1):limited_dirs=module.snapshot(root,exe,Path(directory)/'limited-dirs')
 assert limited_dirs['traversed_directories']<=1 and limited_dirs['issues']
 with patch.object(module,'MAX_FILES',1),patch.object(module,'MAX_ISSUES',2):limited_issues=module.snapshot(root,exe,Path(directory)/'limited-issues')
 assert len(limited_issues['issues'])==2 and 'additional issues omitted' in limited_issues['issues'][-1]
 long_name=root/'src'/('a'*244+'.cpp');long_name.write_bytes(b'x')
 long_report=module.snapshot(root,exe,Path(directory)/'long-path')
 assert any('path length cap omitted' in e for e in long_report['issues'])
 assert all(len(e['file'])<=module.MAX_PATH for e in long_report['files'])

print("PASS: exact hashes, private modes, bounded reservation, existing/symlink/FIFO refusal, omitted environment, missing shaders, changed-source and partial write manifests")
