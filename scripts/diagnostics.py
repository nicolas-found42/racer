#!/usr/bin/env python3
"""Retrieve Racer's bounded JSONL history; missing evidence never means success."""
import argparse
from collections import Counter
from datetime import datetime
import json
import hashlib
import os
from pathlib import Path
import sys

def milliseconds(text):
    value = datetime.fromisoformat(text.replace('Z', '+00:00'))
    if value.tzinfo is None: raise argparse.ArgumentTypeError('include a UTC offset or Z')
    return int(value.timestamp() * 1000)

def inspect(path):
    rows, issues = [], []
    if path.stat().st_size > 8 * 1024**2:
        return [], ['file exceeds 8 MiB inspection budget; contents unknown']
    with path.open('rb') as stream:
        for line_number, line in enumerate(stream, 1):
            if len(line) > 16384:
                issues.append(f'oversized row {line_number}'); continue
            if not line.endswith(b'\n'):
                issues.append(f'unterminated row {line_number}')
            try:
                row = json.loads(line.decode('utf-8'))
                if row.get('schema') != 1 or not isinstance(row.get('event'), str):
                    raise ValueError('schema')
                for key in ('seq', 'utc_ms', 'operation', 'parent_operation', 'dropped'):
                    if key in row and (type(row[key]) is not int or row[key] < 0):
                        raise ValueError('invalid numeric field')
                rows.append(row)
            except (ValueError, AttributeError, RecursionError):
                issues.append(f'unreadable row {line_number}')
    seq = [r['seq'] for r in rows if 'seq' in r]
    if seq != list(range(1, len(seq) + 1)):
        issues.append('sequence gap, duplicate or out-of-order row')
    if any(r.get('dropped', 0) for r in rows): issues.append('recorder dropped events')
    names = [r['event'] for r in rows]
    if 'recorder_start' not in names: issues.append('start missing')
    if 'recorder_end' not in names: issues.append('end missing: running, interrupted, crash or write failure; cause unknown')
    if 'recording_stopped' in names: issues.append('run quota stopped history')
    if any(r.get('run') != path.stem for r in rows): issues.append('run identifier mismatch')
    if not rows: issues.append('empty history')
    return rows, issues

def preserve(destination, sources, capture_root, byte_limit, selection, source_issues=()):
    """Copy whole selected runs, including damaged bytes; never move or prune."""
    destination.mkdir(mode=0o700, parents=True, exist_ok=False)
    report = {'schema': 1, 'selection': selection, 'files': [], 'captures': [],
              'issues': list(source_issues), 'bytes': 0, 'byte_count_semantics': 'reserved payload, including failed writes',
              'limits': 'Local snapshots, not atomic across files; no executable or profile backup.'}
    if not sources: report['issues'].append('no selected run files; requested evidence unavailable')
    def copy(source, name):
        if source.is_symlink():
            report['issues'].append('symlink refused: ' + name); return None
        try:
            with source.open('rb') as stream:
                before = os.fstat(stream.fileno())
                data = stream.read(byte_limit - report['bytes'] + 1)
                after = os.fstat(stream.fileno())
            if report['bytes'] + len(data) > byte_limit:
                report['issues'].append('byte budget omitted: ' + name); return None
            target = destination / name
            # Reserve before writing: a partial failed write still consumes
            # space and must not let later copies exceed the payload budget.
            report['bytes'] += len(data)
            with target.open('xb') as out:
                os.chmod(target, 0o600); out.write(data)
            if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                report['issues'].append('source changed while copying: ' + name)
            digest = hashlib.sha256(data).hexdigest()
            report['files'].append({'file': name, 'sha256': digest, 'bytes': len(data)})
            return target
        except OSError as error:
            report['issues'].append('copy unavailable: ' + name + ' errno=' + str(error.errno))
            return None
    wanted = set()
    for source in sources:
        target = copy(source, source.name)
        if target:
            rows, issues = inspect(target)
            report['issues'].extend(source.stem + ': ' + issue for issue in issues)
            wanted.update(r['sha256'] for r in rows if r['event'] == 'capture_end'
                          and r.get('success') is True and isinstance(r.get('sha256'), str))
    # Only an explicitly named renderer capture directory is searched. Never
    # follow paths from telemetry or search player/profile/build directories.
    found = set()
    if capture_root:
        scanned = 0
        if not capture_root.is_dir(): report['issues'].append('capture directory unavailable')
        for index, candidate in enumerate(capture_root.glob('*')):
            if index >= 256:
                report['issues'].append('capture scan file budget reached'); break
            try:
                if candidate.is_symlink() or not candidate.is_file(): continue
                with candidate.open('rb') as stream:
                    data = stream.read(byte_limit - scanned + 1)
                scanned += len(data)
                if scanned > byte_limit:
                    report['issues'].append('capture scan byte budget reached'); break
                digest = hashlib.sha256(data).hexdigest()
                if digest in wanted and digest not in found:
                    target = copy(candidate, 'capture-' + digest)
                    if target:
                        if hashlib.sha256(target.read_bytes()).hexdigest() == digest:
                            found.add(digest)
                        else: report['issues'].append('capture changed while copying: ' + digest)
            except OSError as error:
                report['issues'].append('capture unavailable errno=' + str(error.errno))
    report['captures'] = [{'sha256': digest, 'available': digest in found} for digest in sorted(wanted)]
    if wanted - found: report['issues'].append('some recorded captures unavailable; hashes alone cannot recover images')
    manifest = destination / 'manifest.json'
    with manifest.open('x') as out:
        os.chmod(manifest, 0o600); json.dump(report, out, indent=2)
    return report

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=Path.home() / 'Library/Application Support/Racer/Racer/diagnostics')
    p.add_argument('--run'); p.add_argument('--operation', type=int); p.add_argument('--profile')
    p.add_argument('--since', type=milliseconds); p.add_argument('--until', type=milliseconds)
    p.add_argument('--event', action='append'); p.add_argument('--summary', action='store_true')
    p.add_argument('--limit', type=int, default=2000)
    p.add_argument('--bundle', type=Path, help='preserve whole matched runs in a fresh directory')
    p.add_argument('--capture-root', type=Path, help='explicit renderer capture directory for bundle')
    p.add_argument('--bundle-max-mib', type=int, default=64, choices=range(1, 129), metavar='1..128')
    args = p.parse_args()
    if args.bundle: args.summary = True
    matched = count = 0
    sources = []
    source_issues = []
    if args.bundle and args.bundle.resolve().is_relative_to(args.root.resolve()):
        p.error('bundle must be outside the source store')
    paths = sorted(args.root.glob('*.jsonl')) if args.root.is_dir() else []
    for path in paths:
        if args.run and path.stem != args.run: continue
        if path.is_symlink():
            source_issues.append(path.stem + ': symlink refused; contents unknown')
            print(json.dumps({'file':str(path),'evidence':'unavailable','reason':'symlink refused'})); continue
        try: rows, issues = inspect(path)
        except OSError as e:
            source_issues.append(path.stem + ': inspection unavailable errno=' + str(e.errno))
            print(json.dumps({'file':str(path),'evidence':'unavailable','errno':e.errno})); continue
        if args.profile and not any(r.get('profile') == args.profile for r in rows):
            if issues:
                source_issues.append(path.stem + ': profile correlation unknown: ' + '; '.join(issues))
                print(json.dumps({'run':path.stem,'evidence':'profile correlation unknown','evidence_issues':issues}))
            continue
        chosen = [r for r in rows if
                  (args.since is None or r.get('utc_ms', -1) >= args.since) and
                  (args.until is None or r.get('utc_ms', float('inf')) <= args.until) and
                  (args.operation is None or r.get('operation') == args.operation or r.get('parent_operation') == args.operation) and
                  (not args.event or r['event'] in args.event)]
        if not chosen:
            if issues:
                source_issues.append(path.stem + ': no matching readable events: ' + '; '.join(issues))
                print(json.dumps({'run':path.stem,'evidence':'unavailable','evidence_issues':issues}))
                if not rows and not (args.operation is not None or args.profile or args.since or args.until or args.event):
                    sources.append(path)
            continue
        sources.append(path)
        matched += 1
        if args.summary:
            print(json.dumps({'run':path.stem,'file':str(path),'matched_events':len(chosen),
                'events':dict(Counter(r['event'] for r in chosen)), 'evidence_issues':issues,
                'start_utc_ms':next((r.get('utc_ms') for r in rows if 'utc_ms' in r), None),
                'build':[r for r in rows if r['event'] in ('app_start','executable')]}))
        else:
            if issues: print(json.dumps({'run':path.stem,'evidence_issues':issues}), file=sys.stderr)
            for row in chosen:
                if count >= args.limit:
                    print('OUTPUT LIMIT: refine filters; omitted events remain in the store', file=sys.stderr); return 2
                print(json.dumps(row)); count += 1
    bundle_status = 0
    if args.bundle:
        try:
            report = preserve(args.bundle, sources, args.capture_root, args.bundle_max_mib * 1024**2,
                              {k: getattr(args, k) for k in ('run','operation','profile','since','until','event')}, source_issues)
            print(json.dumps({'bundle':str(args.bundle),'files':len(report['files']),'issues':report['issues']}), file=sys.stderr)
            if report['issues']: bundle_status = 2
        except OSError as error:
            print(json.dumps({'bundle':'unavailable','errno':error.errno}), file=sys.stderr); return 1
    if not matched:
        print(json.dumps({'evidence':'unavailable','reason':'no matching retained events; absence is not proof that an operation did not occur'}))
        return 1
    return bundle_status
if __name__ == '__main__': sys.exit(main())
