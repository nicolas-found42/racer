import sys,re,collections,struct;sys.path.insert(0,'/Users/nicolas/Documents/github/reverse-engineering/games/racer/experiments/2026-11-08-ui-hud/scripts/mcla-mining')
import rsc
f=rsc.ISO.open('rb')
rows=[]
for e in rsc.TOC:
    if e['directory'] or not e['path'].startswith('/00000000/resources/ui/') or '/textures/' in e['path'] or not e['wordC']&0x80000000: continue
    body,h=rsc.read_resource(e,f)
    strs=[s.decode('latin1') for s in re.findall(rb'[\x20-\x7e]{5,}',body)][:12]
    print(e['path'][len('/00000000/resources/ui/'):],'type',e['word8']&0xff,h['virtual'],h['physical'],body[:8].hex(),strs[:6])
