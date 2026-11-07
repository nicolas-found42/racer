#!/usr/bin/env python3
"""Bounded native evidence loop. Uses SDL menu events and real measured records.
Pillow converts disposable PPMs to pixel-identical canonical PNGs.
"""
import argparse
import hashlib
import json
from pathlib import Path
from verification_lifecycle import VerificationLifecycle
import subprocess
import time
from PIL import Image
from install_cars import regular_bytes
from vehicle_clearance import descriptor as parse_descriptor

parser = argparse.ArgumentParser()
parser.add_argument('output', type=Path)
parser.add_argument('--size', choices=['1080', '720'], default='1080')
parser.add_argument('--binary', type=Path, default=Path('build/racer'))
parser.add_argument('--vehicle-library', type=Path)
parser.add_argument('--vehicle', type=int, default=0)
args = parser.parse_args()
if args.vehicle < 0:raise ValueError('vehicle index must be nonnegative')
library = args.vehicle_library.resolve() if args.vehicle_library else Path('assets/local/vehicles/catalog.racer').resolve()
library_raw = regular_bytes(library,256*1024)
entries = library_raw.decode().splitlines()
if len(entries)<3 or entries[0]!='RACER_VEHICLES 1' or int(entries[1])!=len(entries)-2 or args.vehicle>=len(entries)-2:raise ValueError('vehicle library or selection')
descriptor_name=json.loads(entries[2+args.vehicle])
if not isinstance(descriptor_name,str) or Path(descriptor_name).name!=descriptor_name:raise ValueError('vehicle descriptor path')
descriptor_raw=regular_bytes(library.parent/descriptor_name,32768)
selected,_,_=parse_descriptor(descriptor_raw.decode())
mesh_name=selected['mesh'][0]
if Path(mesh_name).name!=mesh_name:raise ValueError('vehicle mesh path')
mesh_raw=regular_bytes(library.parent/mesh_name,32*1024**2)
if hashlib.sha256(mesh_raw).hexdigest()!=selected['sha256'][0]:raise ValueError('selected mesh hash mismatch')
exe_raw=regular_bytes(args.binary.resolve(),32*1024**2)
out = args.output.resolve()
out.mkdir(parents=True, exist_ok=False)
with VerificationLifecycle(out) as lifecycle:
    profile = out / 'profile' / 'profile.txt'
    profile.parent.mkdir()
    # This scenario never switches cars. Retain exactly the selected input and run
    # a single-entry frozen library, avoiding post-preflight changes in the source
    # store while preserving the requested source index in the manifest.
    models=out/'models';models.mkdir()
    (out/'source-catalog.racer').write_bytes(library_raw)
    (models/descriptor_name).write_bytes(descriptor_raw)
    (models/mesh_name).write_bytes(mesh_raw)
    frozen_library=models/'catalog.racer'
    frozen_library.write_text('RACER_VEHICLES 1\n1\n'+json.dumps(descriptor_name)+'\n')
    frozen_exe=out/'racer';frozen_exe.write_bytes(exe_raw);frozen_exe.chmod(0o700)
    commands = []
    captions = {}
    def key(name): commands.append('key ' + name)
    def select(n): commands.append('select ' + str(n))
    def choose(n): select(n); key('accept')
    def capture(name, assertion=None):
        if assertion: commands.append('assert ' + assertion)
        commands.append('capture ' + str(out / (name + '.ppm')))
        captions[name] = list(commands)
    def result(): commands.append('result')

    key('back'); capture('01-pause'); choose(2); capture('02-clean-garage', 'No pending')
    choose(8); capture('03-empty-comparison', 'No comparable result'); choose(0)
    capture('04-acceleration-countdown', 'COUNTDOWN'); commands.append('running 1')
    capture('05-acceleration-running', 'ACCELERATION MEASUREMENT'); result()
    capture('06-result-A', 'MEASUREMENT: 8.000 s'); choose(0); result()
    capture('07-retry-A', '+0.000 s equal to prior'); choose(1)
    key('right'); select(1)
    for _ in range(4): key('right')
    capture('08-draft-B', 'DRAFT NOT APPLIED'); select(0); key('right')
    capture('09-dirty-choice', 'UNAPPLIED CHANGES'); choose(2)
    capture('10-keep-editing', 'DRAFT NOT APPLIED'); choose(4)
    capture('11-applied-B', 'Applied B: saved'); choose(6)
    capture('12-defaults-draft', 'DRAFT NOT APPLIED'); choose(5)
    capture('13-discard-defaults', 'No pending'); choose(8); choose(0); result()
    capture('14-result-B', 'MEASUREMENT: 6.667 s'); choose(3)
    capture('15-populated-compare', '-1.333 s better than A'); choose(1)
    capture('16-brake-countdown', 'COUNTDOWN'); commands.append('running 0')
    capture('17-brake-lead-in', 'LEAD-IN'); commands.append('running 0.3')
    capture('18-brake-measuring', 'BRAKING MEASUREMENT'); result()
    capture('19-brake-result', 'MEASUREMENT: 38.874 m'); choose(0); result()
    capture('20-brake-retry', '+0.000 m equal to prior'); choose(3)
    capture('21-all-auto-compare', 'matching setup, recorded as A'); choose(3)
    select(0); key('right'); choose(3); key('right'); choose(4); choose(8)
    capture('22-changed-C-missing', 'C [NEXT]'); choose(3); select(0); key('left')
    choose(8); choose(2); capture('23-course-countdown', 'NEXT GATE 1/5')
    commands.append('running 0'); capture('24-course-running', 'COURSE RUNNING')
    commands.append('drive-course on'); commands.append('gate 2')
    capture('25-course-right', 'NEXT GATE 2/5'); key('back'); capture('26-course-paused', 'Paused:')
    choose(0); commands.append('gate 4'); capture('27-course-left', 'NEXT GATE 4/5')
    result(); capture('28-course-finish', 'VALID FINISH'); choose(0)
    commands.append('drive-course off'); key('reset'); capture('29-invalid-reset', 'ATTEMPT NOT SAVED')
    choose(0); key('back'); choose(3); capture('30-invalid-cancel', 'ATTEMPT NOT SAVED'); choose(1)
    # The external runner makes the actual isolated directory unwritable, and later restores it.
    capture('31-lock-ready'); commands.append('wait 1'); choose(1); key('left'); choose(4)
    capture('32-save-error', 'UNSAVED: applied for driving'); choose(8); choose(0); result()
    capture('33-result-save-error', 'Best records NOT saved to disk')
    choose(1); capture('34-unlock-ready'); commands.append('wait 1'); choose(9)
    capture('35-save-recovery', 'Applied B: saved'); choose(8)
    capture('36-return-comparison'); choose(3); capture('37-return-garage'); commands.append('quit')
    script = out / 'actions.txt'; script.write_text('\n'.join(commands) + '\n')
    exe = frozen_exe
    cmd = [str(exe), '--background', '--diagnostics-dir', str(out / 'history'), '--smoke', '290', '--profile', str(profile), '--review-script', str(script)]
    cmd += ['--vehicle-library',str(frozen_library),'--vehicle','0']
    cmd += ['--benchmark'] if args.size == '1080' else ['--window', '1280', '720']
    manifest = {'command': cmd, 'build_sha256': hashlib.sha256(regular_bytes(exe,32*1024**2)).hexdigest(),
                'library_sha256':hashlib.sha256(library_raw).hexdigest(),
                'descriptor_sha256':hashlib.sha256(descriptor_raw).hexdigest(),
                'source_library':str(library),'source_vehicle_index':args.vehicle,
                'frozen_library_sha256':hashlib.sha256(frozen_library.read_bytes()).hexdigest(),
                'expected_mesh_sha256':selected['sha256'][0], 'captures': [],
                'scope':'Synthetic script includes measured-time and gate overrides. Screens verify presentation; human lap, real elapsed test measurements and performance are separate checks. Executable and models must be retained at the recorded paths.'}
    start = time.monotonic()
    converted = set()
    def collect():
        lifecycle.phase('capture')
        for p in out.glob('*.ppm'):
            if p in converted: continue
            try:
                im = Image.open(p); im.load()
            except (OSError, ValueError): continue  # callback may still be writing
            q = p.with_suffix('.png'); im.save(q)
            assert Image.open(q).tobytes() == im.tobytes()
            dimensions = list(im.size)
            assert dimensions == ([1920,1080] if args.size == '1080' else [1280,720]), dimensions
            manifest['captures'].append({'file': q.name, 'dimensions': dimensions,
                'sha256': hashlib.sha256(q.read_bytes()).hexdigest(), 'actions': captions[p.stem]})
            if p.stem == '31-lock-ready': profile.parent.chmod(0o500)
            if p.stem == '34-unlock-ready': profile.parent.chmod(0o700)
            p.unlink()  # checked pixel-identical conversion; no evidence lost
            converted.add(p)
    with (out / 'native.log').open('w') as log:
        process = lifecycle.popen(cmd, stdout=log, stderr=subprocess.STDOUT)
        try:
            while process.poll() is None:
                if time.monotonic() - start > 295: process.kill(); raise TimeoutError('295 s watchdog')
                collect(); time.sleep(.05)
            collect()
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
            profile.parent.chmod(0o700)
    manifest['exit'] = process.returncode
    manifest['elapsed_wall_seconds'] = time.monotonic() - start
    lifecycle.phase('retrieval')
    events=[json.loads(line) for path in (out/'history').glob('*.jsonl') for line in path.read_text().splitlines()]
    loads=[e for e in events if e.get('event')=='asset_load_end']
    manifest['asset_outcomes']=loads
    manifest['exact_asset_loaded']=bool(loads) and all(e.get('success') is True and e.get('sha256')==selected['sha256'][0] for e in loads)
    manifest['frozen_inputs_unchanged']=(regular_bytes(exe,32*1024**2)==exe_raw and
        regular_bytes(models/descriptor_name,32768)==descriptor_raw and
        regular_bytes(models/mesh_name,32*1024**2)==mesh_raw and
        hashlib.sha256(regular_bytes(frozen_library,256*1024)).hexdigest()==manifest['frozen_library_sha256'])
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2))
    print(json.dumps({'exit':process.returncode, 'captures':len(converted), 'seconds':manifest['elapsed_wall_seconds']}))
    lifecycle.phase('validation')
    assert process.returncode == 0
    assert len(converted) == len(captions)
    assert manifest['exact_asset_loaded']
    assert manifest['frozen_inputs_unchanged']
