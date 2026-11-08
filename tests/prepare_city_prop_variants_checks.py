#!/usr/bin/env python3
"""Numeric access geometry and exact-source preservation regression checks."""
import copy
import json
import math
from pathlib import Path
import struct
import sys
import tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import prepare_city_prop_variants as stairs
import prepare_city_blocks as city
from prepare_gt4_vehicle import unpack


def check(value, message):
    if not value: raise AssertionError(message)


def rejects(fn):
    try: fn()
    except (ValueError,OSError): return
    raise AssertionError('expected rejection')


def geometry():
    door={'sill':.97,'door_width':1.2,'tangent':(.6,0,.8),'outward':(.8,0,-.6),'center':(3,.97,-2)}
    p,n,uv,ix,design=stairs.access_geometry(door)
    check(design['risers']==6 and math.isclose(design['exposed_rise'],.97/6),'six independently expected rises')
    check(design['width']==1.6 and design['landing_depth']>=.75 and design['tread']>=.27,'access dimensions')
    check(min(v[1] for v in p)==0 and max(v[1] for v in p)==.97,'ground and sill exact')
    check(len(p)==144 and len(ix)==216 and len(uv)==len(n)==len(p),'six closed boxes')
    for start in range(0,len(ix),3):
        a,b,c=(p[ix[start+i]] for i in range(3)); face=stairs.cross(stairs.subtract(b,a),stairs.subtract(c,a))
        check(stairs.dot(face,n[ix[start]])>0,'every triangle outward and nondegenerate')
    check(all(math.isclose(stairs.dot(v,v),1,abs_tol=1e-12) for v in n),'unit oriented normals')
    for index,box in enumerate(design['boxes']):
        check(math.isclose(box['top_y'],.97-index*.97/6),'individual stair elevation')
    rejects(lambda:stairs.access_geometry({**door,'sill':float('nan')}))


def actual(root):
    for variant in 'cd':
        source=(root/('candidate-'+variant)/'frontage.glb').read_bytes()
        files=stairs.prepare(source,variant); original,old=unpack(source); doc,blob=unpack(files['access.glb'])
        manifest=json.loads(files['manifest.json'])
        check(bytes(blob[:len(old)])==bytes(old),'entire original BIN prefix untouched')
        for key in ('nodes','meshes','accessors','bufferViews','materials','scenes','images','textures','samplers'):
            check(doc[key][:len(original[key])]==original[key],key+' prefix unchanged')
        check(len(manifest['source_door_bindings'])==2,'both native wood doors receive access')
        expected_graph=('Appended active scene uses cloned original roots with only the pinned three-row NORMAL fallback plus authored access node.' if variant=='c' else 'Appended active scene reuses original roots plus authored access node.')
        check(manifest['active_graph']==expected_graph and doc['extras']['racerAuthoredEntranceAccess']['active_graph']==expected_graph,'exact variant-specific active graph policy')
        prior=root/('access-'+variant)/'access.glb'
        if prior.exists():
            previous,previous_blob=unpack(prior.read_bytes()); current=copy.deepcopy(doc)
            previous['extras'].pop('racerAuthoredEntranceAccess');current['extras'].pop('racerAuthoredEntranceAccess')
            check(previous==current and bytes(previous_blob)==bytes(blob),'v2 render fields and entire BIN identical; only policy extras changed')
        check(manifest['bounds'][0][1]==0,'city ground contract')
        check(manifest['bounds'][1][0]-manifest['bounds'][0][0]<=23 and manifest['bounds'][1][2]-manifest['bounds'][0][2]<=26,'whole access footprint')
        city.qualify(files['access.glb'],stairs.digest(files['access.glb']))
        if variant=='c':
            repair=manifest['authored_normal_fallback']; oldai=repair['source_accessor']; newai=repair['replacement_accessor']
            _,before=city.accessor(original,old,oldai); _,after=city.accessor(doc,blob,newai)
            check([i for i,(a,b) in enumerate(zip(before,after)) if a!=b]==[715,716,717],'only three exact zero rows differ')
            check(all(struct.unpack('<3f',after[i])==(0.,1.,0.) for i in (715,716,717)),'independent horizontal face normal +Y')
            check(doc['scenes'][doc['scene']]['nodes']!=original['scenes'][original['scene']]['nodes'],'C active cloned graph selects repaired mesh')
        else: check(manifest['authored_normal_fallback'] is None,'D has no normal changes')
        rejects(lambda:stairs.prepare(source[:-1]+bytes([source[-1]^1]),variant))
        with tempfile.TemporaryDirectory(prefix='racer-access-checks-') as temp:
            target=Path(temp).resolve()/'output'; stairs.publish(target,files);stairs.publish(target,files)
            (target/'access.glb').write_bytes(b'conflict');rejects(lambda:stairs.publish(target,files))
            link=Path(temp).resolve()/'link';link.symlink_to(target,target_is_directory=True);rejects(lambda:stairs.publish(link,files))
    print('actual pinned C/D: preservation, both doors, normal repair, strict qualification, bounds, conflicts PASS')


if __name__=='__main__':
    geometry()
    if len(sys.argv)>1: actual(Path(sys.argv[1]))
    print('access geometry checks PASS')
