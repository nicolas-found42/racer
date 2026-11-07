#!/usr/bin/env python3
"""Decode recovered Juiced2 compiled script records; never execute donor code."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import sys
from prepare_mcla_vehicle import read_regular

MAX_INPUT = 16 * 1024**2
MAX_FIELDS = 100000
MAX_STRING = 65536
MAX_OUTPUT = 32 * 1024**2


def decode(data):
    if len(data) > MAX_INPUT:
        raise ValueError('input_budget')
    if len(data) < 12 or data[:4] != b'\x02'*4:
        raise ValueError('not a compiled 02020202 script')
    types, values = struct.unpack_from('>II', data, 4)
    if not 12 <= types < values <= len(data) or data[types:values].rstrip(b'\x00')[-1:] != b'\x03':
        raise ValueError('invalid section bounds or type terminator')
    formats = data[types:values].rstrip(b'\x00')[:-1].decode('ascii').splitlines()
    if len(formats) > MAX_FIELDS or sum(map(len, formats)) > MAX_FIELDS:
        raise ValueError('field_budget')
    if any(c not in 'sif' for line in formats for c in line):
        raise ValueError('unsupported field type')
    if sum(map(len, formats))*4 != len(data)-values:
        raise ValueError('value extent mismatch')
    cursor = values
    string_bytes = 0
    lines = []
    for ordinal, format in enumerate(formats):
        fields = []
        for kind in format:
            location = cursor
            if kind == 's':
                offset = struct.unpack_from('>I', data, cursor)[0]
                if not 12 <= offset < types:
                    raise ValueError('string offset outside string table')
                end = data.find(b'\x00', offset, min(types, offset + MAX_STRING + 1))
                if end < 0: raise ValueError('unterminated string')
                string_bytes += end-offset
                if string_bytes > 8*1024**2:raise ValueError('expanded_string_budget')
                value = data[offset:end].decode('ascii')
                fields.append({'type':kind,'value_offset':location,'string_offset':offset,'value':value})
            else:
                value = struct.unpack_from('>f' if kind=='f' else '>I', data, cursor)[0]
                if kind == 'f' and not math.isfinite(value):
                    raise ValueError('nonfinite_float')
                fields.append({'type':kind,'value_offset':location,'value':value})
            cursor += 4
        lines.append({'ordinal':ordinal,'fields':fields})
    return {'sha256':hashlib.sha256(data).hexdigest(),'string_table':[12,types],
            'type_table':[types,values],'value_table':[values,len(data)],'lines':lines}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('input',type=Path);p.add_argument('output',type=Path)
    args=p.parse_args()
    try:
        result=decode(read_regular(args.input,MAX_INPUT))
        payload=json.dumps(result,indent=2,allow_nan=False)+'\n'
        if len(payload.encode())>MAX_OUTPUT:raise ValueError('output_budget')
        with args.output.open('x') as stream:stream.write(payload)
        return 0
    except (OSError,ValueError,UnicodeError,struct.error):
        print('Juiced2 data rejected: invalid/bounded input or storage failure; incomplete output may remain after a write failure',file=sys.stderr)
        return 2
if __name__=='__main__':sys.exit(main())
