#!/usr/bin/env python3
"""Preserve an executable and bounded first-party working-tree source snapshot."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import sys

MAX_PAYLOAD = 32 * 1024**2
MAX_FILES = 2048
MAX_DIRECTORIES = 256
MAX_ISSUES = 128
MAX_PATH = 256
SOURCE_SUFFIXES = {'.c', '.cc', '.cpp', '.h', '.hpp', '.mm', '.py', '.sh'}
FIXED = ('CMakeLists.txt', 'references/dependencies.md',
         'third_party/cgltf/cgltf.h', 'third_party/cgltf/LICENSE',
         'third_party/cgltf/SOURCE.json')
SHADERS = tuple('.deps/bgfx/examples/runtime/shaders/metal/' + name
                for name in ('vs_cubes.bin', 'fs_cubes.bin'))

def snapshot(root, executable, destination, max_bytes=MAX_PAYLOAD):
    root, executable, destination = Path(root), Path(executable), Path(destination)
    if not 0 < max_bytes <= MAX_PAYLOAD:
        raise ValueError('payload must be within 1..33554432 bytes')
    # Refuse nesting in any source collection.
    target = destination.resolve()
    if any(target.is_relative_to((root / name).resolve()) for name in ('src','tests','scripts','third_party','.deps')):
        raise ValueError('destination must be outside collected source directories')
    destination.mkdir(mode=0o700, parents=True, exist_ok=False)
    report = {'schema': 1, 'files': [], 'issues': [], 'payload_reserved_bytes': 0,
              'payload_limit_bytes': max_bytes, 'executable_sha256': None,
              'selected_files': 0, 'selected_file_limit': MAX_FILES,
              'traversed_directories': 0, 'directory_limit': MAX_DIRECTORIES,
              'source_relation': 'working-tree-at-copy; matching executable sources unverified',
              'limitations': ['Not an atomic cross-file snapshot or durable backup.',
                             'os.walk directory enumeration allocation is not performance-qualified.',
                             'Only allowlisted source suffixes and named dependencies are selected; no game assets, player profiles or environment files.',
                             'Source content is not automatically redacted; review before sharing.',
                             'Runtime dependencies beyond the named shader pair and cgltf files are not copied.',
                             'Build hashes alone do not establish binary/source correspondence.']}
    def issue(message):
        if len(report['issues']) < MAX_ISSUES - 1:
            report['issues'].append(message[:MAX_PATH + 80])
        elif len(report['issues']) == MAX_ISSUES - 1:
            report['issues'].append('additional issues omitted; evidence incomplete')
    def regular(path):
        # Refuse symlinks in the selected path, not just its final component.
        # System ancestors above the caller's root (macOS /var, for example)
        # are not source entries selected for preservation.
        boundary = root if path.is_relative_to(root) else path.parent
        for part in [path, *path.parents]:
            if part.is_symlink(): return False
            if part == boundary: break
        return stat.S_ISREG(path.lstat().st_mode)
    def copy(source, relative, executable_file=False):
        if report['selected_files'] >= MAX_FILES:
            issue('selected file count cap reached; remaining files omitted'); return
        report['selected_files'] += 1
        if len(relative) > MAX_PATH:
            issue(relative[:MAX_PATH] + ': path length cap omitted'); return
        try:
            if not regular(source):
                issue(relative + ': refused nonregular or symlink source'); return
            fd = os.open(source, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            with os.fdopen(fd, 'rb') as stream:
                before = os.fstat(stream.fileno())
                if not stat.S_ISREG(before.st_mode):
                    issue(relative + ': source changed to nonregular'); return
                data = stream.read(max_bytes - report['payload_reserved_bytes'] + 1)
                after = os.fstat(stream.fileno())
            if len(data) > max_bytes - report['payload_reserved_bytes']:
                issue(relative + ': payload budget omitted'); return
            report['payload_reserved_bytes'] += len(data)  # Includes failed writes.
            output = destination / relative
            output.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            with output.open('xb') as stream:
                os.chmod(output, 0o700 if executable_file else 0o600)
                stream.write(data)
            digest = hashlib.sha256(data).hexdigest()
            copied = hashlib.sha256(output.read_bytes()).hexdigest()
            if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                issue(relative + ': source changed during read')
            if len(data) != before.st_size or copied != digest:
                issue(relative + ': size/hash verification failed')
            report['files'].append({'file': relative, 'bytes': len(data), 'sha256': copied})
            if executable_file: report['executable_sha256'] = copied
        except OSError as error:
            issue(relative + ': unavailable errno=' + str(error.errno))
    copy(executable, 'runtime/racer', True)
    for folder in ('src', 'tests', 'scripts'):
        if report['selected_files'] >= MAX_FILES or report['traversed_directories'] >= MAX_DIRECTORIES:
            issue('source traversal count cap reached; remaining source trees omitted'); break
        base = root / folder
        if not base.is_dir() or base.is_symlink():
            issue(folder + ': source directory unavailable or symlink'); continue
        def traversal_error(error):
            # os.walk otherwise silently drops inaccessible subtrees. Persist
            # only bounded relative context and errno, never arbitrary text.
            try:
                failed = Path(error.filename).relative_to(root)
                location = str(failed)[:160]
            except (TypeError, ValueError):
                location = folder
            issue(location + ': traversal unavailable errno=' + str(error.errno))
        for parent, directories, names in os.walk(base, followlinks=False,
                                                 onerror=traversal_error):
            if report['traversed_directories'] >= MAX_DIRECTORIES:
                issue('directory count cap reached; remaining source entries omitted'); break
            report['traversed_directories'] += 1
            if report['selected_files'] >= MAX_FILES:
                issue('selected file count cap reached; remaining source entries omitted'); break
            for name in list(directories):
                path = Path(parent) / name
                if path.is_symlink():
                    issue(str(path.relative_to(root)) + ': symlink directory refused')
                    directories.remove(name)
                elif name.startswith('.') or name == '__pycache__': directories.remove(name)
            for name in sorted(names):
                if report['selected_files'] >= MAX_FILES:
                    issue('selected file count cap reached; remaining source entries omitted'); break
                if name.startswith('.') or Path(name).suffix not in SOURCE_SUFFIXES: continue
                path = Path(parent) / name
                copy(path, 'source/' + str(path.relative_to(root)))
    for name in FIXED: copy(root / name, 'source/' + name)
    for name in SHADERS: copy(root / name, 'runtime/shaders/' + Path(name).name)
    manifest = destination / 'manifest.json'
    with manifest.open('x') as stream:
        os.chmod(manifest, 0o600)
        json.dump(report, stream, indent=2)
    return report

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--exe', type=Path, default=Path('build/racer'))
    args = parser.parse_args()
    try:
        report = snapshot(Path.cwd(), args.exe, args.output)
    except (OSError, ValueError) as error:
        print(json.dumps({'error':type(error).__name__, 'errno':getattr(error,'errno',None)}), file=sys.stderr)
        return 2
    print(json.dumps({'manifest':str(args.output/'manifest.json'),
                      'executable_sha256':report['executable_sha256'],
                      'issues':report['issues']}))
    return 2 if report['issues'] else 0
if __name__ == '__main__': sys.exit(main())
