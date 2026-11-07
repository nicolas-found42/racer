#!/usr/bin/env python3
"""Bounded native runs and retrieval checks. Fresh output only; no player saves."""
import argparse
import hashlib
import json
from pathlib import Path
from verification_lifecycle import VerificationLifecycle
import subprocess
import sys
import time
from PIL import Image
from preserve_build import snapshot
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('output', type=Path)
a = p.parse_args()
root = a.output.resolve(); root.mkdir(parents=True, exist_ok=False)
with VerificationLifecycle(root) as lifecycle:
    archive = snapshot(Path.cwd(), Path('build/racer'), root/'build')
    assert not archive['issues'], archive['issues']
    exe = root/'build/runtime/racer'
    build = hashlib.sha256(exe.read_bytes()).hexdigest()
    manifest = []
    deadline = time.monotonic() + 290
    def run(name, flags, actions=None, kill=False):
        out = root/name; out.mkdir()
        cmd = [str(exe), '--shader-dir', str(root/'build/runtime/shaders'), '--background', '--profile', str(out/'profile.txt'), '--diagnostics-dir', str(out/'history')]
        if actions:
            text = actions.replace('$OUT', str(out))
            (out/'actions.txt').write_text(text)
            cmd += ['--review-script',str(out/'actions.txt')]
        cmd += flags
        start = time.monotonic()
        record = {'name':name,'command':cmd,'build_sha256':build,'status':'starting','intentional_kill':kill}
        manifest.append(record); (root/'manifest.json').write_text(json.dumps(manifest,indent=2))
        expired = False
        with (out/'native.log').open('w') as log:
            proc = lifecycle.popen(cmd, stdout=log, stderr=subprocess.STDOUT)
            record.update(status='running',pid=proc.pid)
            (root/'manifest.json').write_text(json.dumps(manifest,indent=2))
            try:
                if kill:
                    time.sleep(3); proc.kill()
                result = proc.wait(timeout=max(.1,min(295,deadline-time.monotonic())))
            except subprocess.TimeoutExpired:
                expired = True; proc.kill(); result = proc.wait()
            finally:
                if proc.poll() is None: proc.kill(); proc.wait()
        lifecycle.process_done(proc, timed_out=expired)
        record.update(status='finished',exit=result,seconds=time.monotonic()-start,deadline_expired=expired)
        (root/'manifest.json').write_text(json.dumps(manifest,indent=2))
        assert not expired and result == (-9 if kill else 0), record
        lifecycle.phase('retrieval')
        query = lifecycle.run([sys.executable,'scripts/diagnostics.py','--root',str(out/'history'),'--summary'],text=True,capture_output=True,kind='retrieval')
        (out/'retrieval.jsonl').write_text(query.stdout)
        rows = [json.loads(line) for line in query.stdout.splitlines()]
        assert query.returncode == 0, query.stderr
        assert not any('dropped events' in issue for r in rows for issue in r['evidence_issues']), rows
        assert any('end missing' in issue for r in rows for issue in r['evidence_issues']) == kill
        lifecycle.phase('capture')
        for ppm in out.glob('*.ppm'):
            im=Image.open(ppm);im.load();png=ppm.with_suffix('.png');im.save(png)
            assert Image.open(png).tobytes()==im.tobytes()
            ppm.unlink()
        return out
    run('controls', ['--verify-controls','--smoke','20'])
    run('keyboard', ['--verify-garage','keyboard','--smoke','60'])
    run('gamepad', ['--verify-garage','gamepad','--smoke','60'])
    for direction in ['right','left']:
        run(direction, ['--autodrive' if direction=='right' else '--autodrive-left','--window','1280','720','--smoke','12'],
            'wait 4.8\ncapture $OUT/turn-start.ppm\nwait 0.6\ncapture $OUT/turn-middle.ppm\nwait 0.6\ncapture $OUT/turn-end.ppm\nwait 0.3\nquit\n')
    run('interrupted', ['--smoke','12','--autodrive'],kill=True)
    run('performance', ['--smoke','14','--benchmark','--autodrive'])
    print(json.dumps({'runs':len(manifest),'build_sha256':build}))
