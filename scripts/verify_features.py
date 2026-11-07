import subprocess,json,hashlib,time
from pathlib import Path
from verification_lifecycle import VerificationLifecycle
from PIL import Image
import argparse
from preserve_build import snapshot
parser=argparse.ArgumentParser(description='Hidden parts/livery/test loops at both sizes; fresh isolated output only.')
parser.add_argument('output',type=Path)
args=parser.parse_args()
base=Path.cwd();root=args.output.resolve();root.mkdir(exist_ok=False,parents=True)
with VerificationLifecycle(root) as lifecycle:
    archive=snapshot(base,base/'build/racer',root/'build')
    assert not archive['issues'],archive['issues']
    exe=root/'build/runtime/racer';build=hashlib.sha256(exe.read_bytes()).hexdigest();manifest=[]
    for label,flags in [('720',['--window','1280','720']),('1080',['--benchmark'])]:
     out=root/label;out.mkdir()
     actions='''capture $O/01-garage.ppm
select 10
key accept
capture $O/02-parts.ppm
select 2
key right
select 4
key accept
assert NO ENGINE
capture $O/03-no-engine.ppm
select 2
key right
key right
key right
select 3
key accept
assert Engine fitted
capture $O/04-upgrade.ppm
select 6
key accept
select 11
key accept
select 1
key accept
select 3
key right
key right
key right
key right
select 8
key left
key left
key left
capture $O/05-livery-draft.ppm
select 0
key right
select 1
key accept
select 10
key accept
capture $O/06-layer-order.ppm
select 13
key accept
assert saved to disk
capture $O/07-applied.ppm
select 16
key accept
capture $O/08-garage-upgrade.ppm
select 8
key accept
select 0
key accept
running 1
capture $O/09-running.ppm
result
capture $O/10-result.ppm
select 3
key accept
capture $O/11-compare.ppm
quit
'''.replace('$O',str(out))
     (out/'actions.txt').write_text(actions)
     cmd=[str(exe),'--shader-dir',str(root/'build/runtime/shaders'),'--background','--profile',str(out/'profile.txt'),'--diagnostics-dir',str(out/'history'),'--scene','garage','--review-script',str(out/'actions.txt'),'--smoke','110']+flags
     began=time.monotonic()
     record={'label':label,'command':cmd,'status':'starting','build_sha256':build,'captures':[]};manifest.append(record)
     (root/'manifest.json').write_text(json.dumps(manifest,indent=2))
     with (out/'native.log').open('w') as log:r=lifecycle.run(cmd,stdout=log,stderr=subprocess.STDOUT,timeout=115)
     record.update(status='finished',exit=r.returncode,seconds=time.monotonic()-began)
     (root/'manifest.json').write_text(json.dumps(manifest,indent=2))
     assert r.returncode==0,(label,(out/'native.log').read_text()[-2500:])
     lifecycle.phase('capture')
     for ppm in sorted(out.glob('*.ppm')):
      image=Image.open(ppm);image.load();png=ppm.with_suffix('.png');image.save(png)
      assert Image.open(png).tobytes()==image.tobytes()
      record['captures'].append({'file':str(png),'size':image.size,'sha256':hashlib.sha256(png.read_bytes()).hexdigest(),'ppm_sha256':hashlib.sha256(ppm.read_bytes()).hexdigest()})
     q=lifecycle.run(['python3','scripts/diagnostics.py','--root',str(out/'history'),'--summary'],text=True,capture_output=True,kind='retrieval')
     (out/'retrieval.jsonl').write_text(q.stdout);assert q.returncode==0,q.stderr
     record['retrieval_exit']=q.returncode
     (root/'manifest.json').write_text(json.dumps(manifest,indent=2))
    print(json.dumps(manifest))
