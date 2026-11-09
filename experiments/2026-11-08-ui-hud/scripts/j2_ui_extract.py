"""Extract Juiced 2 (Xbox 360) UI archives: catalog, strings, typed UI scripts, selected PNGs.

usage: j2_ui_extract.py <raw_dir_with_jfs> <out_dir>
Needs ReverseBox venv python (PIL+numpy): tools/reversebox/run j2_ui_extract.py ...
Bounded: reads ~57 MiB of ui*.jfs, writes text catalogs only (PNG selection done by caller).
"""
import hashlib
import json
import math
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from j2_tex import decode_texture, load_archive  # noqa: E402

ARCHIVES = ['ui_ingame', 'ui_frontend', 'ui', 'ui_startup', 'ui_loader']


def parse_script(data):
    types, values = struct.unpack_from('>II', data, 4)
    formats = data[types:values].rstrip(b'\x00')[:-1].decode('ascii').splitlines()
    assert sum(map(len, formats)) * 4 == len(data) - values
    cur = values
    lines = []
    for fmt in formats:
        toks = []
        for k in fmt:
            if k == 's':
                off = struct.unpack_from('>I', data, cur)[0]
                end = data.index(b'\x00', off)
                toks.append(data[off:end].decode('latin-1'))
            elif k == 'f':
                v = struct.unpack_from('>f', data, cur)[0]
                toks.append(('%.4f' % v).rstrip('0').rstrip('.') if math.isfinite(v) else 'nan')
            else:
                toks.append(str(struct.unpack_from('>I', data, cur)[0]))
            cur += 4
        lines.append(' '.join(toks))
    return lines


def main(raw, out):
    raw, out = Path(raw), Path(out)
    (out / 'text').mkdir(parents=True, exist_ok=True)
    cat = []
    for arch in ARCHIVES:
        strings_out = []
        scripts_out = []
        for i, r, d in load_archive(str(raw / arch)):
            magic = struct.unpack('>I', d[:4])[0]
            row = dict(archive=arch, index=i, hash=r[0], offset=r[1], packed=r[2], size=r[3],
                       sha256=hashlib.sha256(d).hexdigest()[:16], magic=hex(magic))
            if (magic >> 8) == 0x1a2001 or magic == 0x18280186:
                row['kind'] = 'texture'
                row['w'], row['h'] = struct.unpack('>II', d[4:12])
                row['fmt'] = {0x52: 'DXT1', 0x53: 'DXT3', 0x54: 'DXT5', 0x71: 'DXN', 0x186: 'ARGB8'}.get(
                    magic & 0xff if magic != 0x18280186 else 0x186)
            elif magic == 0x02020202:
                row['kind'] = 'script'
                try:
                    lines = parse_script(d)
                    scripts_out.append('#### %s[%d] hash=%08x lines=%d' % (arch, i, r[0], len(lines)))
                    scripts_out.extend(lines)
                except Exception as e:
                    row['kind'] = 'script-error:' + str(e)
            elif d[:2] == b'\x00 ' and d[2:3] == b'\x00':  # UTF-16BE table starting with a space
                row['kind'] = 'strings'
                txt = d.decode('utf-16-be', errors='replace')
                strings_out.append('#### %s[%d] hash=%08x' % (arch, i, r[0]))
                strings_out.append(txt.replace('\r\n', '\n'))
            elif d[:1] == b'[':
                row['kind'] = 'ini'
                scripts_out.append('#### %s[%d] INI hash=%08x' % (arch, i, r[0]))
                scripts_out.append(d.decode('latin-1').replace('\r\n', '\n'))
            elif magic in (0x9d, 0x40, 0x2c, 0x2f) or (magic < 0x400 and len(d) > 12 and d[2:3] == b'\x00'):
                row['kind'] = 'fonttable?'
            else:
                row['kind'] = 'other'
            cat.append(row)
        (out / 'text' / (arch + '_scripts.txt')).write_text('\n'.join(scripts_out), encoding='utf-8')
        (out / 'text' / (arch + '_strings.txt')).write_text('\n'.join(strings_out), encoding='utf-8')
    (out / 'catalog.json').write_text(json.dumps(cat, indent=0))
    from collections import Counter
    print(Counter((c['archive'], c['kind']) for c in cat))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
