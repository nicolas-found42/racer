#!/usr/bin/env python3
"""Hidden native per-car selection save and new-process reload check (production library).

Selects each requested library index in the garage, quits, then starts a second
process on the same isolated profile and verifies the loaded mesh and saved id.
No desktop input; isolated profile/output; production library is read only.

Indices, the library and the output path are validated before anything is created.
A native launch failure, timeout or unreadable (e.g. truncated) screenshot is recorded
as a failed check for that car, and manifest.json is atomically replaced after every
car so completed results survive a later failure."""
import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path


def run(cmd, log, timeout):
    """Return the exit code, or None when the process could not start or timed out."""
    with log.open('w') as f:
        try:
            return subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, timeout=timeout).returncode
        except subprocess.TimeoutExpired:
            f.write(f'\nverify_selection_reload: timed out after {timeout}s\n')
        except OSError as error:
            f.write(f'\nverify_selection_reload: launch failed: {error}\n')
    return None


def events(hist):
    out = []
    for f in sorted(hist.glob('*.jsonl')):
        for line in f.read_text().splitlines():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue  # a truncated final line from a killed process
    return out


def library_names(lib):
    """Descriptor names of a RACER_VEHICLES library; a damaged header, entry or count is a one-line SystemExit."""
    lines = lib.read_text().splitlines()
    if len(lines) < 2 or lines[0] != 'RACER_VEHICLES 1':
        raise SystemExit(f'{lib} is not a RACER_VEHICLES 1 library (bad header line)')
    try:
        declared = int(lines[1])
    except ValueError:
        raise SystemExit(f'{lib}: line 2 must be the entry count, found {lines[1]!r}')
    names = []
    for number, line in enumerate(lines[2:], start=3):
        try:
            name = json.loads(line)
        except json.JSONDecodeError as error:
            raise SystemExit(f'{lib}: line {number} is not a JSON string ({error.msg})')
        if not isinstance(name, str) or not name:
            raise SystemExit(f'{lib}: line {number} is not a non-empty descriptor name')
        names.append(name)
    if len(names) != declared:
        raise SystemExit(f'{lib}: header declares {declared} entries but {len(names)} are listed')
    return names


def convert_capture(ppm):
    """Convert a PPM capture to PNG and remove the PPM. A truncated or unreadable capture is kept as
    <name>.ppm.corrupt and reported as an error string; success returns None."""
    from PIL import Image
    if not ppm.exists():
        return None
    try:
        with Image.open(ppm) as im:
            im.load()
            im.save(ppm.with_suffix('.png'))
    except (OSError, SyntaxError, ValueError, Image.DecompressionBombError) as error:
        ppm.replace(ppm.with_name(ppm.name + '.corrupt'))
        return f'{ppm.name}: {error}'
    ppm.unlink()
    return None


def validate_indices(indices, count):
    bad = [i for i in indices if not 0 <= i < count]
    if bad:
        raise SystemExit(f'--index {bad} outside the library range 0..{count - 1} ({count} entries)')
    if len(set(indices)) != len(indices):
        raise SystemExit(f'--index repeated: {sorted(indices)}; each car gets one isolated run directory')


def selection_actions(idx, count, capture):
    """Garage input script: open the car selector, step to idx (wrapping left past the midpoint)."""
    steps = count - idx if idx > count // 2 else 0
    acts = ['key back', 'select 2', 'key accept']
    if steps:
        acts += ['select 13', 'key left'] * steps
    else:
        acts += ['select 13', 'key right'] * idx
    return acts + ['wait 1', 'capture ' + str(capture), 'quit']


def write_manifest(out, size, exe, lib, results):
    manifest = {'size': size, 'binary_sha256': hashlib.sha256(exe.read_bytes()).hexdigest(),
                'library_sha256': hashlib.sha256(lib.read_bytes()).hexdigest(), 'results': results}
    scratch = out / 'manifest.json.tmp'
    scratch.write_text(json.dumps(manifest, indent=1))
    os.replace(scratch, out / 'manifest.json')  # atomic: an interrupted rewrite never truncates the earlier manifest


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('output', type=Path)
    p.add_argument('--index', type=int, action='append', required=True)
    p.add_argument('--size', choices=('720', '1080'), default='720')
    p.add_argument('--binary', type=Path, default=Path('build/racer'))
    p.add_argument('--library', type=Path, default=Path('assets/local/vehicles/catalog.racer'))
    p.add_argument('--selection-timeout', type=int, default=90, help='seconds for the selecting process')
    p.add_argument('--reload-timeout', type=int, default=30, help='seconds for the reloading process')
    a = p.parse_args(argv)
    try:
        import PIL  # noqa: F401
    except ImportError:
        raise SystemExit('Pillow is required for PPM-to-PNG conversion (checked before any native run)')
    exe, lib = a.binary.resolve(), a.library.resolve()
    if not exe.is_file():
        raise SystemExit(f'native binary not found: {exe}')
    if not lib.is_file():
        raise SystemExit(f'vehicle library not found: {lib}')
    names = library_names(lib)
    count = len(names)
    validate_indices(a.index, count)
    out = a.output.resolve()
    if out.exists():
        raise SystemExit(f'output path already exists: {out}; use a new directory for each sweep')
    out.mkdir(parents=True)
    w, h = ('1920', '1080') if a.size == '1080' else ('1280', '720')
    results = []
    for idx in a.index:
        d = out / f'car-{idx}'
        (d / 'profile').mkdir(parents=True)
        profile = d / 'profile/profile.txt'
        want = Path(names[idx]).stem
        (d / 'actions.txt').write_text('\n'.join(selection_actions(idx, count, d / 'selected.ppm')) + '\n')
        c1 = [str(exe), '--background', '--vehicle-library', str(lib), '--review-script', str(d / 'actions.txt'),
              '--smoke', '65', '--window', w, h, '--profile', str(profile), '--diagnostics-dir', str(d / 'history1')]
        r1 = run(c1, d / 'native1.log', a.selection_timeout)
        c2 = [str(exe), '--background', '--vehicle-library', str(lib), '--scene', 'garage', '--smoke', '3.4',
              '--window', w, h, '--profile', str(profile), '--diagnostics-dir', str(d / 'history2'),
              '--screenshot', str(d / 'reload.ppm')]
        r2 = run(c2, d / 'native2.log', a.reload_timeout)
        capture_errors = [e for e in (convert_capture(d / (stem + '.ppm')) for stem in ('selected', 'reload')) if e]
        saved_file = profile.with_suffix('.txt.vehicle')
        saved = saved_file.read_text().strip() if saved_file.exists() else None
        ok = [e for e in events(d / 'history2') if e.get('event') == 'asset_load_end' and e.get('success')]
        chk = {'first_exit': r1 == 0, 'reload_exit': r2 == 0, 'selection_saved': saved == 'vehicle-' + want,
               'reloaded_mesh': bool(ok) and ok[0].get('sha256') == want, 'screens': (d / 'reload.png').exists() and not capture_errors}
        results.append({'index': idx, 'mesh': want, 'saved': saved, 'checks': chk, 'capture_errors': capture_errors,
                        'verified': all(chk.values())})
        print(json.dumps(results[-1]), flush=True)
        write_manifest(out, a.size, exe, lib, results)
    return 0 if all(r['verified'] for r in results) else 1


if __name__ == '__main__':
    sys.exit(main())
