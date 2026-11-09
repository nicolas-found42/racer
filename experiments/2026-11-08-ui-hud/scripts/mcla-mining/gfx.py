import sys,re,os,hashlib;sys.path.insert(0,'/Users/nicolas/Documents/github/reverse-engineering/games/racer/experiments/2026-11-08-ui-hud/scripts/mcla-mining')
import rsc
OUT=sys.argv[1];os.makedirs(OUT,exist_ok=True)
f=rsc.ISO.open('rb')
for e in rsc.TOC:
    if e['directory'] or not e['path'].startswith('/00000000/resources/ui/') or '/textures/' in e['path'] or '/meshes/' in e['path'] or not e['wordC']&0x80000000: continue
    if (e['word8']&0xff) not in (27,28): continue
    body,h=rsc.read_resource(e,f)
    strs=[s.decode('latin1') for s in re.findall(rb'[\x20-\x7e]{4,}',body)]
    name=e['path'][len('/00000000/resources/ui/'):].replace('/','__')
    open(os.path.join(OUT,name+'.strings.txt'),'w').write('\n'.join(strs))
    print(name,len(strs),h['virtual'],h['physical'],hashlib.sha256(body).hexdigest()[:12])
