#!/usr/bin/env python3
"""Bounded, read-only SLRR CFG/SCX extraction; no game code is executed."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import base64

MAX_FILE = 16 * 1024**2
VERTEX_FIELDS = ((1,12),(32,4),(64,12),
                 (128,4),(256,4),(512,8),(1024,8),(2048,8),(0x40000,12))

def read(path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_FILE:
        raise ValueError('input must be a regular non-symlink file <=16MiB')
    with path.open('rb') as stream:
        data = stream.read(MAX_FILE + 1)
    if len(data) > MAX_FILE: raise ValueError('input grew beyond budget')
    return data

def cfg(data):
    """Retain every command and line; type only explicitly validated syntax."""
    rows, slots, issues = [], [], []
    current = None
    for line_number, line in enumerate(data.decode('cp1252').splitlines(), 1):
        text = line.split('#',1)[0].split(';',1)[0].split('//',1)[0].strip()
        if not text: continue
        tokens = text.split()
        row = {'line':line_number, 'command':tokens[0].lower(), 'arguments':tokens[1:]}
        rows.append(row)
        if row['command'] == 'slot':
            current = None
            try:
                if len(tokens) != 8: raise ValueError('missing or extra slot fields')
                pose = [float(x) for x in tokens[1:7]]
                if not all(math.isfinite(x) for x in pose): raise ValueError('nonfinite slot pose')
                current = {'line':line_number,'position':pose[:3],'rotation':pose[3:],
                           'id':int(tokens[7],0),'rules':[]}
                slots.append(current)
            except ValueError as error:
                issues.append({'line':line_number,'reason':str(error)})
        elif row['command'] in ('attach','slottype','slotdmgmode','compatible','link') and current:
            current['rules'].append(row)
    return {'commands':rows,'slots':slots,'issues':issues,
            'limitations':['Rule tokens are declarations, not proof of native installation behavior.',
                           'Resource IDs remain package-scoped; no RPK resolution implied.']}

def scx4(data):
    if len(data) < 12 or data[:4] != b'INVO': raise ValueError('not an INVO mesh')
    version, count = struct.unpack_from('<II', data, 4)
    if version != 4: raise ValueError(f'SCX version {version} not yet decoded')
    if count > 65536 or 12 + count*8 > len(data): raise ValueError('invalid TOC')
    chunks, geometry, vertices, ranges = [], [], None, []
    uv1, uv_source = None, None
    header_end = 12 + count*8
    for i in range(count):
        kind, offset = struct.unpack_from('<II',data,12+8*i)
        if offset < header_end or offset+8 > len(data): raise ValueError('chunk offset outside file')
        tag, size = struct.unpack_from('<II',data,offset)
        if tag != kind or size < 8 or offset+size > len(data): raise ValueError('chunk header/range mismatch')
        if any(offset < end and offset+size > start for start,end in ranges): raise ValueError('overlapping chunks')
        ranges.append((offset,offset+size))
        chunks.append({'kind':kind,'offset':offset,'bytes':size,
                       'sha256':hashlib.sha256(data[offset:offset+size]).hexdigest()})
        if kind == 4:
            if vertices is not None: raise ValueError('unpaired vertex chunk')
            if size < 16: raise ValueError('short vertex header')
            n, flags = struct.unpack_from('<II',data,offset+8)
            allowed = sum(bit for bit,_ in VERTEX_FIELDS) | 0x1e
            weights = {0:0,2:0,4:4,8:8,16:12}.get(flags & 0x1e)
            if weights is None: raise ValueError('unsupported bone influence group')
            stride = weights + sum(width for bit,width in VERTEX_FIELDS if flags & bit)
            if not flags & 1 or flags & ~allowed or size != 16+n*stride:
                raise ValueError('unsupported vertex flags or size')
            vertices = [struct.unpack_from('<fff',data,offset+16+j*stride) for j in range(n)]
            if not all(math.isfinite(v) for p in vertices for v in p): raise ValueError('nonfinite position')
            uv1, uv_source = None, None
            if flags & 512:
                uv_offset = weights + sum(width for bit,width in VERTEX_FIELDS if bit < 512 and flags & bit)
                uv1 = [struct.unpack_from('<ff',data,offset+16+j*stride+uv_offset) for j in range(n)]
                if not all(math.isfinite(v) for uv in uv1 for v in uv): raise ValueError('nonfinite UV1')
                uv_source = {'vertex_data_offset':offset+16,'vertex_stride':stride,'field_byte_offset':uv_offset,'vertex_flags':flags}
        elif kind == 5:
            if vertices is None or size < 12: raise ValueError('index chunk without vertices')
            n = struct.unpack_from('<I',data,offset+8)[0]
            if n % 3 or size != 12+n*2: raise ValueError('unsupported index layout')
            indices = struct.unpack_from('<'+'H'*n,data,offset+12)
            if any(index >= len(vertices) for index in indices): raise ValueError('index outside vertices')
            mesh = {'positions':vertices,'triangles':[indices[j:j+3] for j in range(0,n,3)]}
            if uv1 is not None: mesh.update(uv1=uv1,uv1_source=uv_source)
            geometry.append(mesh)
            vertices = None
    if vertices is not None or (count and not geometry): raise ValueError('incomplete geometry')
    points = [p for mesh in geometry for p in mesh['positions']]
    return {'version':version,'chunks':chunks,'geometry':geometry,
            'bounds':{'min':[min(p[k] for p in points) for k in range(3)],
                      'max':[max(p[k] for p in points) for k in range(3)]} if points else None,
            'limitations':['Raw source axes and units preserved; no automatic normalization.',
                           'Bind-pose positions and optional raw UV1 decoded; material, rig and native physics behavior unverified.',
                           'UV1 source convention preserved without V flip; texture orientation remains unverified.']}

def scx(data):
    if len(data)<8 or data[:4]!=b'INVO': raise ValueError('not an INVO mesh')
    version=struct.unpack_from('<I',data,4)[0]
    if version==4:return scx4(data)
    if version!=3:raise ValueError(f'SCX version {version} not yet decoded')
    geometry=[];cursor=8;terminated=False
    while cursor+4<=len(data):
        start=cursor;size=struct.unpack_from('<I',data,cursor)[0]
        if size==0:cursor+=4;terminated=True;break
        if size not in (56,104,136) or cursor+size+4>len(data):raise ValueError('unsupported v3 material')
        texture_indices=struct.unpack_from('<5H',data,cursor+44)
        cursor+=size;n=struct.unpack_from('<I',data,cursor)[0];cursor+=4
        stride=44 if size==56 else 64
        if cursor+n*stride+4>len(data):raise ValueError('v3 vertex range exceeds input')
        vertices=[struct.unpack_from('<fff',data,cursor+j*stride) for j in range(n)]
        if not all(math.isfinite(v) for p in vertices for v in p):raise ValueError('nonfinite v3 position')
        uv1=[struct.unpack_from('<ff',data,cursor+j*stride+24) for j in range(n)]
        if not all(math.isfinite(v) for uv in uv1 for v in uv):raise ValueError('nonfinite v3 UV1')
        uv_source={'vertex_data_offset':cursor,'vertex_stride':stride,'field_byte_offset':24}
        cursor+=n*stride;triangles=struct.unpack_from('<I',data,cursor)[0];cursor+=4
        if cursor+triangles*12>len(data):raise ValueError('v3 index range exceeds input')
        faces=[struct.unpack_from('<III',data,cursor+j*12) for j in range(triangles)]
        if any(i>=n for face in faces for i in face):raise ValueError('v3 index outside vertices')
        cursor+=triangles*12
        geometry.append({'positions':vertices,'triangles':faces,
                         'material_offset':start,'texture_indices':texture_indices,'uv1':uv1,'uv1_source':uv_source})
    if not terminated or cursor!=len(data):raise ValueError('v3 missing terminator or unexplained trailing data')
    points=[p for mesh in geometry for p in mesh['positions']]
    return {'version':version,'geometry':geometry,
            'bounds':{'min':[min(p[k] for p in points) for k in range(3)],
                      'max':[max(p[k] for p in points) for k in range(3)]} if points else None,
            'limitations':['Raw source axes and units preserved.',
                           'Geometry, raw UV1 and material texture indices decoded; shading, rig and native physics remain unverified.',
                           'UV1 source convention preserved without V flip; texture orientation remains unverified.']}

def obj(result):
    lines, base = ['# Raw SCX source coordinates; no axis/unit conversion'], 1
    for mesh in result['geometry']:
        lines.extend('v '+' '.join(format(x,'.9g') for x in p) for p in mesh['positions'])
        lines.extend('f '+' '.join(str(base+x) for x in tri) for tri in mesh['triangles'])
        base += len(mesh['positions'])
    return '\n'.join(lines)+'\n'

def gltf(result, scale=1., lift=0., reverse=False):
    if not math.isfinite(scale) or scale<=0 or not math.isfinite(lift):
        raise ValueError('finite positive scale and finite lift required')
    binary=bytearray();views=[];accessors=[];primitives=[]
    def accessor(payload,component,kind,count,target,bounds=None):
        binary.extend(bytes((-len(binary)) % 4))
        offset=len(binary);binary.extend(payload)
        views.append({'buffer':0,'byteOffset':offset,'byteLength':len(payload),'target':target})
        item={'bufferView':len(views)-1,'componentType':component,'type':kind,'count':count}
        if bounds:item.update(min=bounds[0],max=bounds[1])
        accessors.append(item);return len(accessors)-1
    for mesh in result['geometry']:
        points=mesh['positions'];triangles=mesh['triangles']
        if not points or not triangles:continue
        lo=[min(p[k] for p in points) for k in range(3)];hi=[max(p[k] for p in points) for k in range(3)]
        position=accessor(b''.join(struct.pack('<fff',*p) for p in points),5126,'VEC3',len(points),34962,(lo,hi))
        indices=accessor(b''.join(struct.pack('<III',*t) for t in triangles),5125,'SCALAR',3*len(triangles),34963)
        attributes={'POSITION':position}
        if 'uv1' in mesh:
            uv=mesh['uv1']
            if len(uv)!=len(points) or any(len(pair)!=2 or not all(math.isfinite(v) for v in pair) for pair in uv):
                raise ValueError('UV1 must contain one finite pair per vertex')
            attributes['TEXCOORD_0']=accessor(b''.join(struct.pack('<ff',*pair) for pair in uv),5126,'VEC2',len(points),34962)
        extras={'uvConvention':'raw source UV1; orientation not yet texture-reviewed'}
        for name in ('material_offset','texture_indices','uv1_source'):
            if name in mesh:extras[name]=mesh[name]
        primitives.append({'attributes':attributes,'indices':indices,'mode':4,'material':0,'extras':extras})
    if not primitives:raise ValueError('no nonempty triangle geometry to export')
    direction=-1 if reverse else 1
    return {'asset':{'version':'2.0','generator':'Racer donor geometry extractor'},
            'scene':0,'scenes':[{'nodes':[0]}],
            'nodes':[{'mesh':0,'scale':[direction*scale,scale,direction*scale],'translation':[0,lift,0]}],
            'meshes':[{'primitives':primitives}],
            'materials':[{'name':'inspection-neutral','pbrMetallicRoughness':{
                'baseColorFactor':[.7,.7,.7,1],'metallicFactor':0,'roughnessFactor':1},'doubleSided':True}],
            'buffers':[{'byteLength':len(binary),'uri':'data:application/octet-stream;base64,'+base64.b64encode(binary).decode()}],
            'bufferViews':views,'accessors':accessors,
            'extras':{'source_sha256':result.get('sha256'),'source_version':result['version'],
                      'limitations':result['limitations']+['Neutral inspection material is authored, not recovered shading.'],
                      'conversion':{'scale':scale,'lift':lift,'reverse_forward':reverse}}}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('source',type=Path);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--obj',type=Path)
    p.add_argument('--gltf',type=Path)
    p.add_argument('--scale',type=float,default=1.)
    p.add_argument('--lift',type=float,default=0.)
    p.add_argument('--reverse-forward',action='store_true')
    a=p.parse_args();data=read(a.source)
    result=cfg(data) if a.source.suffix.lower()=='.cfg' else scx(data)
    result.update(source=str(a.source.resolve()),sha256=hashlib.sha256(data).hexdigest(),bytes=len(data))
    if (a.obj or a.gltf) and 'geometry' not in result: p.error('geometry export requires a decoded mesh')
    document=gltf(result,a.scale,a.lift,a.reverse_forward) if a.gltf else None
    encoded=json.dumps(document,separators=(',',':')) if document else None
    if encoded and len(encoded)>32*1024**2:raise ValueError('glTF export exceeds32MiB')
    with a.output.open('x') as out: json.dump(result,out,indent=2)
    if a.obj:
        with a.obj.open('x') as out: out.write(obj(result))
    if a.gltf:
        with a.gltf.open('x') as out: out.write(encoded)
if __name__=='__main__':main()
