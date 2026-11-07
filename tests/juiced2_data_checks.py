"""Synthetic known-answer offsets/types plus malformed boundary rejection."""
import importlib.util
from pathlib import Path
import struct
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
spec=importlib.util.spec_from_file_location('j',Path(__file__).parents[1]/'scripts/juiced2_data.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
strings=b'key\0value\0';types=12+len(strings);fmt=b'ssif\n\x03';values=types+len(fmt);data=b'\x02'*4+struct.pack('>II',types,values)+strings+fmt+struct.pack('>IIIf',12,16,42,1.5)
r=m.decode(data);assert [f['value'] for f in r['lines'][0]['fields']]==['key','value',42,1.5]
for bad in [data[:-1],data[:values]+struct.pack('>I',999999)+data[values+4:]]:
 try:m.decode(bad)
 except ValueError:pass
 else:raise AssertionError('malformed input accepted')
print('PASS: typed associations, exact float/integer values, source offsets, malformed extents and pointers')

# Fail before publication for nonfinite values and bounded expansion failures.
import contextlib,io,sys,tempfile
from unittest.mock import patch
nan=b'\x02'*4+struct.pack('>II',12,15)+b'f\n\x03'+struct.pack('>f',float('nan'))
try:m.decode(nan)
except ValueError as e:assert str(e)=='nonfinite_float'
else:raise AssertionError('NaN accepted')
for constant,value,reason in [('MAX_INPUT',len(data)-1,'input_budget'),('MAX_FIELDS',1,'field_budget'),('MAX_STRING',1,'unterminated string')]:
 with patch.object(m,constant,value):
  try:m.decode(data)
  except ValueError as e:assert str(e)==reason,(str(e),reason)
  else:raise AssertionError('budget ignored')
with tempfile.TemporaryDirectory()as tmp:
 root=Path(tmp).resolve();source=root/'source.bin';out=root/'output.json';source.write_bytes(nan)
 def run():
  with patch.object(sys,'argv',['juiced2_data',str(source),str(out)]),contextlib.redirect_stderr(io.StringIO()):return m.main()
 assert run()==2 and not out.exists()
 source.write_bytes(data)
 with patch.object(m,'MAX_OUTPUT',1):assert run()==2 and not out.exists()
 assert run()==0;before=out.read_bytes();assert run()==2 and out.read_bytes()==before
 source.unlink();source.symlink_to(out);assert run()==2 and out.read_bytes()==before
print('PASS: finite floats, input/field/string/output budgets, reject-before-open, no overwrite and symlink refusal')
