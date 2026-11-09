#!/usr/bin/env python3
"""Bounded read-only extraction of selected GT4 UI/HUD files from GT4.VOL inside the ISO.
Index: experiments/2026-11-05-gt4-mc3-data/output/gt4-vol-index.json (prior work, decoded RoFS TOC).
Compression: 8-byte PS2Zip header (c5eef7ff, -size) + raw DEFLATE (kind 2); kind 1 = stored."""
import json,struct,zlib,hashlib,sys,fnmatch
from pathlib import Path
hub=Path('/Users/nicolas/Documents/github/reverse-engineering')
idx=json.load(open(hub/'games/racer/experiments/2026-11-05-gt4-mc3-data/output/gt4-vol-index.json'))
out=Path(__file__).resolve().parent.parent/'output/gt4-ui/raw'
pats=sys.argv[1:]
CAP=64*1024**2;total=0;man=[]
with Path(idx['iso']).open('rb') as f:
  for e in idx['records']:
    if e['kind']==0 or not any(fnmatch.fnmatch(e['path'],p) for p in pats):continue
    assert e['within_volume'] and e['packed_bytes']<=24*1024**2 and e['unpacked_bytes']<=24*1024**2
    off=idx['volume_lba']*2048+e['volume_offset'];f.seek(off);data=f.read(e['packed_bytes'])
    if e['kind']==2:
      assert data[:4]==bytes.fromhex('c5eef7ff') and -struct.unpack_from('<i',data,4)[0]==e['unpacked_bytes']
      d=zlib.decompressobj(-15);plain=d.decompress(data[8:],e['unpacked_bytes']+1);assert len(plain)==e['unpacked_bytes']
    else:plain=data
    total+=len(plain);assert total<CAP
    p=out/e['path'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(plain)
    man.append(dict(path=e['path'],iso_offset=off,packed=e['packed_bytes'],size=len(plain),sha256=hashlib.sha256(plain).hexdigest(),head=plain[:16].hex()))
mp=out.parent/'extract-manifest.json'
old=json.load(open(mp)) if mp.exists() else []
old={x['path']:x for x in old};old.update({x['path']:x for x in man})
json.dump(list(old.values()),open(mp,'w'),indent=1);print(len(man),'files',total,'bytes')
