import json,struct,sys
from pathlib import Path
# reviewed stdlib-only RSC5/LZX decoder retained by the 2026-11-05 MCLA vehicle experiment (read-only reuse)
sys.path.insert(0,"/Users/nicolas/Documents/github/reverse-engineering/games/racer/experiments/2026-11-05-mcla-vehicle/output/references")
import mcla_lzx
HUB=Path("/Users/nicolas/Documents/github/reverse-engineering")
TOC=json.loads((HUB/"games/racer/experiments/2026-11-05-mcla-data/output/named-entries.json").read_text())
ISO=HUB/"games/raw/midnight-club-la/Midnight Club - Los Angeles - Complete Edition (USA, Europe).iso"
BASE=1788608512
def read_resource(e, f):
    off=e['word8']&0x7fffff00
    f.seek(BASE+off); raw=f.read(e['size'])
    assert raw[:4]==b'\x05CSR', raw[:4]
    h=mcla_lzx.parse_header(raw)
    body,h=mcla_lzx.decompress(raw,expected=h['virtual']+h['physical'])
    return body,h
