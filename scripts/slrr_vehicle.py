#!/usr/bin/env python3
"""Bounded source-CFG static Furrano inspection assembly, not native simulation."""
import argparse, copy, json, math, re
from pathlib import Path
from slrr_resources import ResourceResolver
from slrr_assets import scx, gltf
from slrr_gltf_materials import binding_chain, texture_slots, attach_diffuse, MAX_EXPORT

def identity(): return [[float(i==j) for j in range(4)] for i in range(4)]
def multiply(a,b): return [[sum(a[i][k]*b[k][j] for k in range(4)) for j in range(4)] for i in range(4)]
def inverse(a):
    b=identity()
    for i in range(3):
        for j in range(3): b[i][j]=a[j][i]
        b[i][3]=-sum(b[i][j]*a[j][3] for j in range(3))
    return b

def pose(values):
    if len(values)!=6 or not all(math.isfinite(v) for v in values): raise ValueError('invalid finite pose')
    x,y,z,yaw,pitch,roll=values
    def rotation(axis,t):
        m=identity();a,b=[i for i in range(3) if i!=axis];c,s=math.cos(t),math.sin(t)
        m[a][a]=m[b][b]=c;m[a][b]=-s if axis!=1 else s;m[b][a]=s if axis!=1 else -s
        return m
    m=multiply(multiply(rotation(1,yaw),rotation(0,pitch)),rotation(2,roll))
    for i,v in enumerate((x,y,z)): m[i][3]=v
    return m

def resource_id(token):
    """CFG resource literal: optional r qualifier on hexadecimal uint32 only."""
    if not isinstance(token,str) or len(token)>64 or not re.fullmatch(r'(?:0[xX][0-9a-fA-F]+[rR]?|0|[1-9][0-9]*)',token):
        raise ValueError('invalid resource literal')
    value=int(token[:-1] if token[-1:] in ('r','R') else token,0)
    if not 0<=value<=0xffffffff:raise ValueError('resource literal outside uint32')
    return value

def config(data):
    out={'slots':{},'attachments':[],'stock':[],'renders':[],'wheels':[],'compatible':[]};current=None
    for line,raw in enumerate(data.decode('cp1252').splitlines(),1):
        text=raw.split('//')[0].split(';')[0].split('#')[0].strip()
        if not text:continue
        t=text.split();cmd=t[0].lower();v=t[1:]
        if cmd=='slot':
            current=int(v[6],0)
            if current in out['slots']: out.setdefault('duplicate_slots',[]).append(current)
            out['slots'][current]={'pose':list(map(float,v[:6])),'line':line,'type':0}
        elif cmd=='slottype':out['slots'][current]['type']=int(v[0],0)
        elif cmd=='attach':out['attachments'].append({'own':current,'resource':resource_id(v[0]),'parent_slot':int(v[1],0),'line':line})
        elif cmd=='compatible':out['compatible'].append({'own':current,'resource':resource_id(v[0]),'parent_slot':int(v[1],0),'line':line})
        elif cmd=='stockpart':out['stock'].append({'id':resource_id(v[0]),'line':line})
        elif cmd in ('render','deformable'):out['renders'].append({'id':resource_id(v[0]),'pose':list(map(float,v[1:7])) if len(v)>=7 else [0.]*6,'command':cmd,'line':line})
        elif cmd=='wheel':out['wheels'].append(list(map(float,v[:6])))
        elif cmd=='steering':out['steering']=list(map(float,v[:6]))
    return out

def slot_frame(cfg,sid):
    if sid in cfg.get('duplicate_slots',[]): raise ValueError('ambiguous duplicate source slot '+str(sid))
    s=cfg['slots'][sid];frame=identity();typ=s['type']
    if typ==11:frame=pose(cfg['steering'])
    elif 101<=typ<=104 or 201<=typ<=204 or 301<=typ<=304:frame=pose(cfg['wheels'][typ%100-1])
    elif typ:raise ValueError('unsupported native slottype '+str(typ))
    return multiply(frame,pose(s['pose']))

def definition(resolver,package,rid):
    key,local=resolver.identify(package,rid);p,_=resolver.package(key);entries=p['resources'][local]
    if len(entries)!=1:raise ValueError('ambiguous part resource')
    e=entries[0];native=[c for c in e['commands'] if c['command']=='native']
    if len(native)!=1:raise ValueError('unique native configuration missing')
    path=native[0]['value'].split()[-1];data,path=resolver.read(path)
    return {'package':key,'id':local,'alias':e['alias'],'cfg_path':path,'cfg':config(data)}

def append_scene(dest,scene,name,matrix):
    offsets={k:len(dest.setdefault(k,[])) for k in ('buffers','bufferViews','accessors','images','samplers','textures','materials','meshes','nodes')}
    for b in scene.get('buffers',[]):dest['buffers'].append(copy.deepcopy(b))
    for b in scene.get('bufferViews',[]):
        b=copy.deepcopy(b);b['buffer']+=offsets['buffers'];dest['bufferViews'].append(b)
    for a in scene.get('accessors',[]):
        a=copy.deepcopy(a);a['bufferView']+=offsets['bufferViews'];dest['accessors'].append(a)
    dest['images'].extend(copy.deepcopy(scene.get('images',[])));dest['samplers'].extend(copy.deepcopy(scene.get('samplers',[])))
    for t in scene.get('textures',[]):
        t=copy.deepcopy(t);t['source']+=offsets['images'];t['sampler']+=offsets['samplers'];dest['textures'].append(t)
    for m in scene.get('materials',[]):
        m=copy.deepcopy(m);tex=m.get('pbrMetallicRoughness',{}).get('baseColorTexture')
        if tex:tex['index']+=offsets['textures']
        dest['materials'].append(m)
    for m in scene['meshes']:
        m=copy.deepcopy(m)
        for p in m['primitives']:
            p['indices']+=offsets['accessors'];p['material']+=offsets['materials']
            p['attributes']={k:v+offsets['accessors'] for k,v in p['attributes'].items()}
        dest['meshes'].append(m)
    dest['nodes'].append({'name':name,'mesh':offsets['meshes'],'matrix':[matrix[i][j] for j in range(4) for i in range(4)]})
    dest['scenes'][0]['nodes'].append(offsets['nodes'])

def assemble(root):
    resolver=ResourceResolver(root);package='cars/racers/Furrano.rpk';chassis=definition(resolver,package,6)
    parts=[dict(chassis,world=identity(),parent=None)];pending=[];issues=[]
    for row in chassis['cfg']['stock']:
        ident=resolver.identify(package,row['id'])
        if ident[0]!=package:continue # generic CFG wheels differ from Java stock selection
        pending.append(definition(resolver,package,row['id']))
    # Exhaust is explicitly added by Java addStockParts; windows/lights use CFG stock list.
    pending.append(definition(resolver,package,0x114))
    while pending:
        progress=False
        for child in pending[:]:
            matches=[]
            for pi,parent in enumerate(parts):
                for a in child['cfg']['attachments']:
                    if resolver.identify(child['package'],a['resource'])==(parent['package'],parent['id']) and a['parent_slot'] in parent['cfg']['slots']:
                        matches.append((pi,parent,a))
            for pi,parent in enumerate(parts):
                for c in child['cfg']['compatible']:
                    for a in parent['cfg']['attachments']:
                        if resolver.identify(child['package'],c['resource'])==resolver.identify(parent['package'],a['resource']) and c['parent_slot']==a['parent_slot']:
                            matches.append((pi,parent,{'own':c['own'],'parent_slot':a['own'],'line':c['line'],'via':'source compatible/parent attach'}))
            if len(matches)==1:
                pi,parent,a=matches[0];world=multiply(parent['world'],multiply(slot_frame(parent['cfg'],a['parent_slot']),inverse(slot_frame(child['cfg'],a['own']))))
                parts.append(dict(child,world=world,parent=pi,attachment=a));pending.remove(child);progress=True
        if not progress:break
    for c in pending:issues.append({'part':c['alias'],'reason':'no unique exact-resource attachment; native inheritance matching not implemented','cfg':c['cfg_path']})
    for n,sid in enumerate((101,102,103,104)):
        rim=definition(resolver,'parts/wheels.rpk',0x316);tyre=definition(resolver,'parts/wheels.rpk',0x3d5)
        rw=multiply(slot_frame(chassis['cfg'],sid),inverse(slot_frame(rim['cfg'],1)))
        parts.append(dict(rim,alias='rim-'+str(n),world=rw,parent=0,source_selection='Furrano_GT54.java stock_parts_list_RGear_wheels[0..3]'))
        tw=multiply(rw,multiply(slot_frame(rim['cfg'],2),inverse(slot_frame(tyre['cfg'],1))))
        parts.append(dict(tyre,alias='tyre-'+str(n),world=tw,parent=len(parts)-1,source_selection='Furrano_GT54.java stock_parts_list_RGear_tyres[0..3]'))
    source_java,_=resolver.read('cars/racers/Furrano_Data/scripts/src/Furrano_GT54.java')
    scene={'asset':{'version':'2.0','generator':'Racer bounded source assembly'},'scene':0,'scenes':[{'nodes':[]}]};report=[]
    for part in parts:
        try:
            renders=part['cfg']['renders'];selected=next((r for r in renders if r['command']=='deformable'),renders[0])
            chain=resolver.resolve(part['package'],selected['id']);source,refs=binding_chain(chain)
            data,_=resolver.read(source['path']);decoded=scx(data)
            single=gltf(decoded,.01);single,binding=attach_diffuse(single,decoded['geometry'],texture_slots(refs),resolver)
            world=multiply(part['world'],pose(selected['pose']))
            # gltf() puts scale on its original node; bake exactly that scale in the combined node.
            scale=identity()
            for i in range(3):scale[i][i]=.01
            append_scene(scene,single,part['alias'],multiply(world,scale))
            report.append({k:v for k,v in part.items() if k!='cfg'}|{'mesh':source,'render':selected,'bindings':binding,'vertices':sum(len(g['positions']) for g in decoded['geometry'])})
        except (ValueError,IndexError,KeyError,OSError) as e:issues.append({'part':part['alias'],'cfg':part['cfg_path'],'reason':str(e)})
    limitations=['Static reference-convention assembly only; supplied native runtime and closed/open moving parts not executed.','No user-measured wheel corrections or guessed missing resources.','Engine, battery, pedals and suspension hardware not yet assembled; visible exterior completeness must be reviewed.','Source material issues remain explicit per primitive; no fabricated texture-index remap.','Stock CFG and Java disagree on generic wheels; explicit Java rim/tyre selection used.']
    scene['extras']={'limitations':limitations,'assembly_issues':issues,'source_part_count':len(report)}
    text=json.dumps(scene,separators=(',',':'),allow_nan=False)
    if len(text.encode())>MAX_EXPORT:raise ValueError('export exceeds32MiB')
    return text,{'parts':report,'issues':issues,'limitations':limitations,'provenance':resolver.provenance(),'source_bytes':resolver.bytes}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True);p.add_argument('--gltf',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args()
    if a.gltf.exists() or a.report.exists() or a.gltf.resolve()==a.report.resolve():raise ValueError('fresh distinct output paths required')
    text,report=assemble(a.root)
    with a.gltf.open('x') as f:f.write(text)
    with a.report.open('x') as f:json.dump(report,f,indent=2,allow_nan=False)
if __name__=='__main__':main()
