import sys,time,json,re,collections,os;sys.path.insert(0,'/Users/nicolas/Documents/github/reverse-engineering/games/racer/experiments/2026-11-08-ui-hud/scripts/mcla-mining')
import rsc,xtd
from pathlib import Path
OUT=Path(sys.argv[1]);OUT.mkdir(parents=True,exist_ok=True)
mode=sys.argv[2] # 'test' or 'all'
f=rsc.ISO.open('rb')
tx=[e for e in rsc.TOC if not e['directory'] and e['path'].startswith('/00000000/resources/ui/') and e['wordC']&0x80000000 and (e['word8']&0xff)==9]
man=[];skips=collections.Counter();total=0
def keep(name):
    if name.startswith('bink'):return False
    if 'dyn_vinyls' in name and 'icon' not in name: return False
    if re.match(r'garage/dyntextures/sh_\d+',name): return False
    return True
for e in tx:
    body,h=rsc.read_resource(e,f)
    for i,t in enumerate(xtd.parse(body)):
        if not keep(t['name']): skips[t['name'].split('/')[0][:12]]+=1; continue
        if mode=='test' and not re.match(r'(shared_(0|1|2|3)\.dds|arial|icon_ingame|navsys/dyntextures/(hk|tutorial))',t['name']): continue
        try: im,msg=xtd.decode(body,h['virtual'],t)
        except Exception as ex: im,msg=None,'err '+str(ex)[:60]
        rec=dict(entry=e['path'].rsplit('/',1)[1],idx=i,name=t['name'],fmt=t['fmt'],w=t['w'],h=t['h'],status=msg)
        if im is not None:
            fn=e['path'].rsplit('/',1)[1]+'_%d_'%i+re.sub(r'[^A-Za-z0-9_.-]','_',t['name'])+'.png'
            im.save(OUT/fn,optimize=False,compress_level=6); rec['png']=fn
        man.append(rec)
json.dump(man,open(OUT/'manifest.json','w'),indent=0)
print(len(man),'converted;',collections.Counter(m['status'] for m in man),'skipped',sum(skips.values()))
