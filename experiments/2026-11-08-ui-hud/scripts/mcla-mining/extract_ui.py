#!/usr/bin/env python3
"""Read-only extraction of MCLA UI entries (non-resource) from the ISO via retained decoded TOC.
Raw-deflate inflate with cap. Writes to OUT/<path>.bin + manifest. Limits: member<=4MiB stored, total<=40MiB."""
import json,zlib,hashlib,sys
from pathlib import Path
HUB=Path("/Users/nicolas/Documents/github/reverse-engineering")
toc=json.loads((HUB/"games/racer/experiments/2026-11-05-mcla-data/output/named-entries.json").read_text())
iso=HUB/"games/raw/midnight-club-la/Midnight Club - Los Angeles - Complete Edition (USA, Europe).iso"
BASE,ARCHIVE=1788608512,2130739200
OUT=Path(sys.argv[1]); OUT.mkdir(parents=True,exist_ok=True)
PREFIX=tuple(sys.argv[2:])
man=[];total=0;skipped=[]
with iso.open('rb') as f:
  for e in toc:
    if e['directory'] or not e['path'].startswith(PREFIX): continue
    if e['wordC']&0x80000000: skipped.append((e['path'],'resource')); continue
    off,stored,comp=e['word8']&0x7fffffff,e['wordC']&0xffffff,bool(e['wordC']&0x40000000)
    if stored>4<<20 or total+stored>40<<20 or off+stored>ARCHIVE: skipped.append((e['path'],'limit')); continue
    f.seek(BASE+off); raw=f.read(stored); total+=stored
    data=raw
    if comp:
        d=zlib.decompressobj(-15); data=d.decompress(raw,(8<<20)+1)
        if len(data)>8<<20 or not d.eof: skipped.append((e['path'],'inflate')); continue
    ok=len(data)==e['size']
    rel=e['path'].replace('/00000000/','').replace('/','__')
    (OUT/(rel+'.bin')).write_bytes(data)
    man.append({'path':e['path'],'size':len(data),'size_match':ok,'compressed':comp,'stored':stored,'offset':off,'sha256':hashlib.sha256(data).hexdigest(),'magic':data[:8].hex(),'file':rel+'.bin'})
(OUT/'manifest.json').write_text(json.dumps(man,indent=1))
print(len(man),'extracted; skipped',len(skipped),'stored MiB',round(total/2**20,2))
import collections;print(collections.Counter(s[1] for s in skipped))
print(collections.Counter(m['magic'][:8] for m in man).most_common(10))
