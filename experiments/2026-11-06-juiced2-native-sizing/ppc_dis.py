#!/usr/bin/env python3
"""Disassemble a VA range of the retained decoded text section with llvm-mc (ppc64 BE).
Usage: ppc_dis.py START_HEX COUNT   (COUNT <= 4096; one bounded llvm-mc call, 30 s timeout)
Words llvm-mc rejects print as '?'; the input is one word per line so warnings map back to words."""
import os
import re
import subprocess
import sys
from ppc_scan import code, BASE

MAX_COUNT = 4096
LLVM_MC = os.environ.get('LLVM_MC', '/opt/homebrew/opt/llvm/bin/llvm-mc')
INVALID = re.compile(r'<stdin>:(\d+):\d+: warning: invalid instruction encoding')


def disassemble(words):
    """words: list of 4-byte values. Returns one text per word, '?' where llvm-mc could not decode it."""
    text = '\n'.join(' '.join('0x%02x' % b for b in w) for w in words)
    try:
        r = subprocess.run([LLVM_MC, '--disassemble', '-triple=powerpc64', '-mattr=+altivec'],
                           input=text, capture_output=True, text=True, timeout=30)
    except FileNotFoundError:
        raise SystemExit(f'llvm-mc not found at {LLVM_MC}; install Homebrew llvm or set LLVM_MC')
    except subprocess.TimeoutExpired:
        raise SystemExit('llvm-mc timed out after 30 s')
    bad = {int(m.group(1)) for m in INVALID.finditer(r.stderr)}
    ok = [l.strip() for l in r.stdout.splitlines() if l.strip() and not l.strip().startswith('.')]
    if len(ok) != len(words) - len(bad):
        raise SystemExit(f'llvm-mc output misaligned: {len(ok)} instructions for {len(words)} words ({len(bad)} invalid)')
    it = iter(ok)
    return ['?' if i + 1 in bad else next(it) for i in range(len(words))]


def main(argv):
    if len(argv) != 3:
        raise SystemExit(__doc__)
    try:
        start, count = int(argv[1], 16), int(argv[2])
    except ValueError:
        raise SystemExit(f'START_HEX and COUNT must be a hex address and a decimal count, got {argv[1]!r} {argv[2]!r}\n{__doc__}')
    if not 0 < count <= MAX_COUNT:
        raise SystemExit(f'COUNT must be 1..{MAX_COUNT}, got {count}')
    first, end = start - BASE, start - BASE + 4 * count
    if start % 4 or first < 0 or end > len(code):
        raise SystemExit(f'range {start:#x}+{count} words is outside the text section '
                         f'{BASE:#x}..{BASE + len(code):#x} or not word-aligned')
    words = [code[first + 4 * k:first + 4 * k + 4] for k in range(count)]
    print('\n'.join('%08x  %s  %s' % (start + 4 * k, w.hex(), t)
                    for k, (w, t) in enumerate(zip(words, disassemble(words)))))


if __name__ == '__main__':
    main(sys.argv)
