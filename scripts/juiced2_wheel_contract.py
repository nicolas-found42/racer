"""Audit one pinned Juiced2 native wheel-sizing contract, without altering cars.

Register names and object offsets deliberately remain numeric: their incoming
configuration semantics and final shader deformation are not fully recovered.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import stat
import struct
import sys
import zlib

from install_cars import immutable, regular_bytes, require
from verification_lifecycle import VerificationLifecycle

BASE = 0x82000000
IMAGE_SHA = 'ee51a8b7be39967bee04eddb3146116616500fb357d8fc2751fb1fa58eecddc0'
XEX_SHA = 'ae20f2467cc0535872b18517941ac4434f60408cb6d07bf47da799ce1564e574'
PROFILE_SHA = '3dd5f5fdd44a501ed1e15c73e6bd83d7d755887be01e71972e823b120a04c7cf'
SHARED_HEADER_SHA = 'abe96c6f9d9c6422f6fd619436a99efaee12102be4bccc388757fedcbbc62ac2'
DISC_BASE = 265879552
SHARED_SECTOR = 1949278
PROFILE_ROW = (162645771, 36124296, 447, 596, 4, 1)
# Native pre-import memory-image windows, not PE raw-file section offsets.
WINDOWS = {
    0x8210F7D8: '3d608203ed9f07b2c15f01b4c01f01b8c17f01bced6b0028d3df01acc1abf6d43d608203ed3d6828d13f01c838ebf7b43d608205c1a70000ed4a0372c9abd468fdac03723d608205ed9f5024d19f0124fd806818c1abd464eda00372817f00cc2b0b0001ec1d6824d01f0128edac5828d01f012cec0d0024d01f01a841980028419a001c',
    0x82112F0C: '817f00602b0b0000419a0018c1bf0128934b0014eda06824ec0d0028d00b0000817f0064',
    0x822F99A8: '7d8802a69181fff89421ffa0816301442b0b000081630000816b00147d6903a6419a001c4e8004213863ffff38210060',
    0x8204892C: '822e3c28822faec8',
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def f32(value):
    try:
        valid = type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        valid = False
    require(valid, 'finite_register')
    try:
        result = struct.unpack('>f', struct.pack('>f', value))[0]
    except (OverflowError, struct.error):
        raise ValueError('register_float32_range') from None
    require(math.isfinite(result), 'register_float32_range')
    return result


def profile_fields(raw):
    require(len(raw) >= 128 and len(raw) <= 8192, 'profile_extent')
    require(raw[:32].split(b'\0')[0] == b'TYRE_PROFILE', 'profile_name')
    frame = struct.unpack_from('>16f', raw, 32)
    identity = (1., 0., 0., 0., 0., 1., 0., 0., 0., 0., 1., 0., 0., 0., 0., 1.)
    require(frame == identity, 'unsupported_profile_frame')
    kind, count = struct.unpack_from('>2I', raw, 96)
    require(kind == 3 and 2 <= count <= 128, 'profile_layout')
    require(len(raw) == 104 + count * 36 + 24, 'profile_extent')
    knots = [struct.unpack_from('>9f', raw, 104 + i * 36) for i in range(count)]
    require(all(math.isfinite(v) for knot in knots for v in knot), 'profile_finite')
    flag = struct.unpack_from('>I', raw, 104 + count * 36)[0]
    object324 = (~flag) & 1
    samples = count - int(object324 != 0)
    # 8210FD90 initializes these accumulators to0,1000,0. Integer
    # virtual+24 samples yield anchors; handles are not extrema samples.
    max_x = max(0., *(k[0] for k in knots[:samples]))
    min_y = min(1000., *(k[1] for k in knots[:samples]))
    max_y = max(0., *(k[1] for k in knots[:samples]))
    return {'stored_knots': count, 'raw_flag': flag, 'object324': object324,
            'sample_count': samples, 'sampled_indices': list(range(samples)),
            'object436': max_x, 'object440': min_y, 'object444': max_y,
            'original_thickness': f32(max_y - min_y),
            'all_anchor_min_y': min(k[1] for k in knots),
            'scope': 'Native anchor-scan values in unconverted profile coordinates; no continuous-curve extrema, tessellation or physical-unit claim.'}


def sizing_fields(profile, f1, f2, f3):
    """8210F798 arithmetic for positive normal inputs; no argument-unit guess."""
    f1, f2, f3 = map(f32, (f1, f2, f3))
    x, lo, hi = (f32(profile[k]) for k in ('object436', 'object440', 'object444'))
    require(min(f1, f2, f3, x, lo) >= 2.0**-126 and hi > lo, 'unsupported_sizing_domain')
    product = f32(f1 * f2)
    thickness = f32(hi - lo)
    # Native fmul uses the image's double0.1, then frsp; other operations
    # below are single-rounded at each native instruction boundary.
    requested_thickness = f32(product * 0.1)
    x_scale = f32(f1 / f32(x * 20.0))
    radial_scale = f32(f3 / f32(lo * f32(0.7874000072479248)))
    require(radial_scale > 0 and x_scale > 0, 'unsupported_sizing_domain')
    extra = f32(f32(requested_thickness - thickness) / radial_scale)
    return {'input_registers': {'f1': f1, 'f2': f2, 'f3': f3},
            'object292': x_scale, 'object296': radial_scale, 'object300': radial_scale,
            'object424': extra, 'object428': f2, 'object456': f32(f3 - 4.0),
            'material_rad_scale': f32(f32(1.0 / radial_scale) - 1.0),
            'scope': 'Recovered setter/register arithmetic only; incoming configuration/upgrade argument binding, mutable overrides and shader deformation remain unresolved. Not a geometry fit.'}


def verify_image(raw):
    require(len(raw) == 6934016 and sha(raw) == IMAGE_SHA, 'native_image_pin')
    proofs = []
    for address, value in WINDOWS.items():
        expected = bytes.fromhex(value)
        actual = raw[address - BASE:address - BASE + len(expected)]
        require(actual == expected, 'native_window_pin')
        proofs.append({'address': hex(address), 'bytes': len(actual), 'sha256': sha(actual)})
    constants = [(0x8204CB10, 'f', 1.), (0x820200B8, 'f', 1000.),
                 (0x8202F6D4, 'f', 4.), (0x8202F7B4, 'f', 20.),
                 (0x8204D464, 'f', 0.7874000072479248), (0x8204D468, 'd', 0.1)]
    for address, kind, expected in constants:
        require(struct.unpack_from('>' + kind, raw, address - BASE)[0] == expected,
                'native_constant_pin')
    return proofs


def source_profile(path, lifecycle=None):
    # Resolve the explicitly supplied canonical input alias. Never follow paths
    # found inside an archive; only the pinned selected ranges are read.
    if lifecycle:
        lifecycle.record['active_input'] = 'iso'
        lifecycle.checkpoint()
    path = Path(path).resolve(strict=True)
    with path.open('rb') as stream:
        before = os.fstat(stream.fileno())
        require(stat.S_ISREG(before.st_mode) and before.st_size == 7835492352, 'iso_identity')
        def read(offset, size, kind):
            if lifecycle:
                lifecycle.record['active_input'] = kind
                lifecycle.checkpoint()
            require(0 <= offset and offset + size <= before.st_size, 'source_range')
            stream.seek(offset)
            raw = stream.read(size)
            require(len(raw) == size, 'source_read')
            return raw
        xex = read(828153856, 5349376, 'iso-xex')
        require(sha(xex) == XEX_SHA, 'source_xex_pin')
        header = read(DISC_BASE + 1949258 * 2048, 39436, 'shared-header')
        require(sha(header) == SHARED_HEADER_SHA and
                struct.unpack_from('>6I', header, 4 + 24 * 105) == PROFILE_ROW, 'shared_header_pin')
        packed = read(DISC_BASE + SHARED_SECTOR * 2048 + PROFILE_ROW[1], PROFILE_ROW[2], 'tyre-profile')
        decoder = zlib.decompressobj()
        raw = decoder.decompress(packed, PROFILE_ROW[3] + 1)
        require(decoder.eof and not decoder.unused_data and not decoder.unconsumed_tail
                and len(raw) == PROFILE_ROW[3] and sha(raw) == PROFILE_SHA, 'source_profile_pin')
        after = os.fstat(stream.fileno())
        require((before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns), 'source_changed')
    return raw, {'xex_sha256': XEX_SHA, 'shared_header_sha256': SHARED_HEADER_SHA,
                 'profile_sha256': sha(raw), 'packed_sha256': sha(packed),
                 'profile_record': list(PROFILE_ROW), 'profile_ordinal': 105,
                 'iso_mtime_ns': before.st_mtime_ns,
                 'scope': 'Exact selected XEX/header/profile ranges and stable file size/mtime; complete ISO not freshly hashed by this command.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iso', type=Path, required=True)
    parser.add_argument('--image', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--registers', type=float, nargs=3, metavar=('F1', 'F2', 'F3'))
    args = parser.parse_args()
    output = args.output.resolve()
    require(not output.exists(), 'fresh_output_required')
    require(shutil.disk_usage(output.parent).free >= 20 * 1024**3, 'free_space')
    output.mkdir(mode=0o700)
    with VerificationLifecycle(output) as life:
        try:
            tool_sha = sha(regular_bytes(Path(__file__), 128 * 1024))
        except Exception:
            tool_sha = None
        life.record.update(source_tool_sha256=tool_sha, expected_image_sha256=IMAGE_SHA,
                           expected_profile_sha256=PROFILE_SHA, active_input='image')
        life.phase('retrieval'); life.checkpoint()
        image = regular_bytes(args.image, 8 * 1024**2)
        windows = verify_image(image)
        raw, source = source_profile(args.iso, life)
        life.phase('validation')
        fields = profile_fields(raw)
        report = {'schema': 1, 'source_tool_sha256': tool_sha, 'image_sha256': IMAGE_SHA,
                  'native_windows': windows, 'source': source, 'profile_fields': fields,
                  'sizing': sizing_fields(fields, *args.registers) if args.registers else None,
                  'input_register_status': 'Explicit analyst-supplied demonstration, not a recovered car configuration.' if args.registers else 'Not supplied; no incoming-car argument binding claimed.',
                  'limitations': ['No original or translated game execution, shader deformation, source units or tessellation equivalence established.',
                                  'No existing car geometry, eligibility, physics or catalog is changed.',
                                  'Pinned decoded memory image provenance is separately retained; decoder was not rerun by this audit.']}
        payload = (json.dumps(report, indent=2, allow_nan=False) + '\n').encode()
        require(len(payload) + len(raw) <= 32768, 'report_budget')
        life.record['active_input'] = None; life.phase('capture'); life.checkpoint()
        for kind, name, data in (('profile', 'profile.bin', raw), ('report', 'report.json', payload)):
            life.record['publication_kind'] = kind; life.checkpoint()
            immutable(output / name, data)
        life.record['publication_kind'] = None; life.checkpoint()
        life.complete()
    print(json.dumps({'profile_sha256': PROFILE_SHA, 'sample_count': fields['sample_count'], 'output': str(output)}))
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError, struct.error, zlib.error):
        print('Wheel contract audit rejected; inspect retained lifecycle evidence if created.', file=sys.stderr)
        sys.exit(2)
