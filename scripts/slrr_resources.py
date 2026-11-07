#!/usr/bin/env python3
"""Bounded read-only RPAK512 resolver. IDs retain their declaring package."""
import argparse
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import struct

MAX_FILE = 16 * 1024**2
MAX_TOTAL = 32 * 1024**2

def digest(data): return hashlib.sha256(data).hexdigest()

def parse_rpk(data):
    if len(data) < 16 or len(data) > MAX_FILE or data[:4] != b'RPAK': raise ValueError('not a bounded RPAK file')
    version, count, reserved = struct.unpack_from('<III', data, 4)
    if version != 512 or count > 1024 or reserved != 0: raise ValueError('unsupported RPAK header')
    header = 16 + count * 64
    if header + 16 > len(data): raise ValueError('truncated external table')
    external = {}
    for i in range(count):
        offset = 16 + i * 64; key = struct.unpack_from('<I', data, offset)[0]
        if not key or key & 0xffff or key in external: raise ValueError('invalid external package index')
        name = data[offset+4:offset+64].split(b'\0', 1)[0]
        if not name or len(name) == 60: raise ValueError('unterminated external name')
        external[key] = name.decode('ascii').replace('\\', '/')
    table_bytes, entries, reserved, duplicate_count = struct.unpack_from('<IIII', data, header)
    start = header + 16; end = start + table_bytes
    if reserved or entries != duplicate_count or entries > 65536 or end > len(data): raise ValueError('invalid resource table header')
    resources = {}; position = start; ranges = []
    for _ in range(entries):
        if position + 23 > end: raise ValueError('truncated resource record')
        super_id, resource_id = struct.unpack_from('<II', data, position)
        kind, flags = struct.unpack_from('<BB', data, position+8)
        compatibility = struct.unpack_from('<f', data, position+10)[0]
        offset, size = struct.unpack_from('<II', data, position+14)
        n = data[position+22]; alias = data[position+23:position+23+n]
        if not n or position+23+n > end or alias[-1:] != b'\0' or b'\0' in alias[:-1]: raise ValueError('invalid resource alias')
        if not math.isfinite(compatibility) or offset < end or offset + size > len(data): raise ValueError('invalid resource identity or payload range')
        if size and any(offset < b and offset+size > a for a,b in ranges): raise ValueError('overlapping payloads')
        if size: ranges.append((offset, offset+size))
        payload = data[offset:offset+size]
        if b'\0' in payload: raise ValueError('binary RSD payload unsupported')
        text = payload.decode('cp1252'); commands = []
        for line_number, line in enumerate(text.splitlines(), 1):
            if len(line)>4096 or len(commands)>=4096: raise ValueError('RSD command budget exceeded')
            line = line.split('//',1)[0].strip()
            if not line or line.startswith('#'): continue
            tokens = line.split(None,1); commands.append({'line':line_number,'command':tokens[0].lower(),'value':tokens[1] if len(tokens)>1 else ''})
        entry = {'id':resource_id,'super_id':super_id,'kind':kind,'flags':flags,'compatibility':compatibility,
             'alias':alias[:-1].decode('cp1252'),'record_offset':position,'payload_offset':offset,'payload_bytes':size,
             'payload_sha256':digest(payload),'commands':commands}
        resources.setdefault(resource_id, []).append(entry)
        position += 23 + n
    if position != end: raise ValueError('unconsumed resource table bytes')
    return {'version':version,'external':external,'resources':resources,'table_start':start,'table_end':end,'sha256':digest(data)}

class ResourceResolver:
    def __init__(self, root):
        self.root = Path(root).resolve(); self.packages = {}; self.files = {}; self.bytes = 0
    def path(self, name):
        name = name.replace('\\','/'); path = PurePosixPath(name)
        if not name or path.is_absolute() or '..' in path.parts or ':' in name or '\0' in name: raise ValueError('unsafe source path')
        current = self.root
        for part in path.parts:
            current /= part
            if current.is_symlink(): raise ValueError('symlink source refused')
        full = current.resolve()
        if not full.is_relative_to(self.root): raise ValueError('source outside installation')
        return full
    def read(self, name):
        full = self.path(name); key = full.relative_to(self.root).as_posix()
        if key in self.files: return self.files[key]['data'], key
        if not full.is_file() or full.stat().st_size > MAX_FILE: raise ValueError('source unavailable or over file budget')
        with full.open('rb') as stream: data = stream.read(MAX_FILE+1)
        if len(data)>MAX_FILE or self.bytes+len(data)>MAX_TOTAL: raise ValueError('source byte budget exceeded')
        self.bytes += len(data); self.files[key] = {'data':data,'sha256':digest(data),'bytes':len(data)}
        return data,key
    def package(self, name):
        full=self.path(name); key=full.relative_to(self.root).as_posix()
        if key not in self.packages:
            if len(self.packages)>=64: raise ValueError('package count exceeded')
            data,key=self.read(key); self.packages[key]=parse_rpk(data)
        return self.packages[key],key
    def identify(self, declaring, resource_id):
        if not 0<=resource_id<=0xffffffff: raise ValueError('resource id outside uint32')
        package,key=self.package(declaring)
        if resource_id==0: return None
        prefix=resource_id & 0xffff0000
        if prefix:
            if prefix not in package['external']: raise ValueError('external package index absent')
            key=package['external'][prefix]
            _,key=self.package(key)
        return key,resource_id & 0xffff
    def resolve(self, declaring, resource_id, stack=()):
        identity=self.identify(declaring,resource_id)
        if identity is None: return {'status':'null','source_id':resource_id}
        package,key=self.package(identity[0]); local=identity[1]; qualified=f'{key}:0x{local:04x}'
        if qualified in stack or len(stack)>=16: raise ValueError('resource reference cycle or depth exceeded')
        if local not in package['resources']: raise ValueError('resource not found: '+qualified)
        candidates=package['resources'][local]
        if len(candidates)!=1: return {'status':'ambiguous','identity':qualified,'candidates':candidates,'reason':'duplicate local IDs; native precedence unverified'}
        entry=candidates[0]; out={'status':'resolved','identity':qualified,'package_sha256':package['sha256'],'resource':entry,'references':[],'sources':[]}
        for command in entry['commands']:
            if command['command'] in ['mesh','texture']:
                value=command['value'].split()
                if len(value)!=1: raise ValueError('unsupported resource reference syntax')
                rid=int(value[0],0)
                out['references'].append({'command':command['command'],'line':command['line'],'reference':self.resolve(key,rid,(*stack,qualified))})
            elif command['command']=='sourcefile':
                data,path=self.read(command['value']);out['sources'].append({'path':path,'bytes':len(data),'sha256':digest(data),'line':command['line']})
        return out
    def provenance(self):
        return [{'path':key,'bytes':v['bytes'],'sha256':v['sha256']} for key,v in self.files.items()]

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True);p.add_argument('--package',required=True);p.add_argument('--resource',type=lambda s:int(s,0),required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    resolver=ResourceResolver(a.root);chain=resolver.resolve(a.package,a.resource)
    report={'chain':chain,'provenance':resolver.provenance(),'source_bytes_read':resolver.bytes,'limitations':['Supported RPAK512 text-RSD layout only; native resource behavior not executed.','Reference command order and duplicate texture occurrences retained.','Resource0 is explicit null; no global ID or absent file substitution.']}
    with a.output.open('x') as f:json.dump(report,f,indent=2)
if __name__=='__main__': main()
