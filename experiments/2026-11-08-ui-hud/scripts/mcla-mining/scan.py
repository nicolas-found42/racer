import sys,time,json,collections;sys.path.insert(0,'/Users/nicolas/Documents/github/reverse-engineering/games/racer/experiments/2026-11-08-ui-hud/scripts/mcla-mining')
import rsc,xtd
f=rsc.ISO.open('rb')
tx=[e for e in rsc.TOC if not e['directory'] and e['path'].startswith('/00000000/resources/ui/') and e['wordC']&0x80000000 and (e['word8']&0xff)==9]
rows=[];fail=0
t0=time.time()
for e in tx:
    try:
        body,h=rsc.read_resource(e,f)
        for t in xtd.parse(body):
            rows.append(dict(entry=e['path'],stored=e['size'],virtual=h['virtual'],physical=h['physical'],**{k:t[k] for k in('name','hash','fmt','endian','base','w','h','tiled','pitch')}))
    except Exception as ex:
        fail+=1;rows.append(dict(entry=e['path'],error=str(ex)[:100]))
print('time',time.time()-t0,'fail',fail,'rows',len(rows))
out='/Users/nicolas/Documents/github/reverse-engineering/games/racer/experiments/2026-11-08-ui-hud/output/mcla-ui/texture-catalog.json'
json.dump(rows,open(out,'w'),indent=0)
c=collections.Counter(r.get('name','?').split('/')[0] if 'name' in r else 'ERR' for r in rows);print(c.most_common(40))
c2=collections.Counter(r.get('fmt') for r in rows);print(c2)
