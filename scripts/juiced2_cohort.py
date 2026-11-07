#!/usr/bin/env python3
"""Conservative native static assembly contract; declarations are not a player roster."""
import math
import hashlib

LABELS=('FL','FR','RL','RR')

def tyre_materials(data,mesh):
    if hashlib.sha256(data).hexdigest()!='d1689b1bff3a0460e1171904c53f41f607693954dc645fded2a3587c7841ab69':raise ValueError('shared_toyo_pin')
    groups=mesh(data)
    if [(g['material'],len(g['positions']),len(g['indices']))for g in groups]!=[('toyo_tyre',729,3840),('OZ_MICHELANGELO',2126,7584),('brake_disc',96,276),('BLACK2',162,480)]:raise ValueError('shared_toyo_composite')
    return ('toyo_tyre',)

def assembly_contract(code,nodes,standard,car_keys,shared_keys,hash_name):
    reasons=[]
    if not nodes or nodes[0]['name'].casefold()!=(str(code)+'_ROOT').casefold():reasons.append('native_root_identity')
    wheels=[n for n in nodes if n['name'].startswith('WHEEL_')]
    pivots={n['name']:n['matrix'][3:12:4]for n in wheels}
    if len(wheels)!=4 or set(pivots)!={'WHEEL_'+s for s in LABELS}:reasons.append('four_native_pivots')
    else:
        if any(any(abs(n['matrix'][r*4+c]-float(r==c))>1e-6 for r in range(3)for c in range(3))for n in wheels):reasons.append('unsupported_wheel_frame')
        if not all(all(math.isfinite(v)for v in p)and(p[0]<0 if s.endswith('L')else p[0]>0)for s in LABELS for p in[pivots['WHEEL_'+s]]):reasons.append('native_wheel_side')
        if not min(pivots['WHEEL_FL'][2],pivots['WHEEL_FR'][2])>max(pivots['WHEEL_RL'][2],pivots['WHEEL_RR'][2]):reasons.append('native_front_axis')
    selected=[];omitted=[]
    for n in nodes:
        reason='transform_only'if n['geometry']=='NONE'else'authored_static_state_exclusion'if any(x in n['name']for x in('_DEAD','LIGHTSON','BRKLIGHT'))else None
        if reason:omitted.append({'name':n['name'],'geometry':n['geometry'],'offset':n['offset'],'reason':reason});continue
        key=hash_name('mesh\\'+n['geometry']+'.xem');bank='car'if key in car_keys else'shared'if key in shared_keys else None
        if bank is None:reasons.append('missing_body_mesh:'+n['name'])
        selected.append({'name':n['name'],'geometry':n['geometry'],'offset':n['offset'],'key':key,'bank':bank})
    if not selected:reasons.append('empty_body_selection')
    front,rear=standard.get('FWHEELS'),standard.get('RWHEELS')
    if not isinstance(front,str)or front!=rear or front.casefold()!=('WHEEL_'+str(code)).casefold():reasons.append('rim_declaration')
    elif hash_name('mesh\\'+front+'.xem')not in car_keys:reasons.append('rim_member_missing')
    if standard.get('FTYRES')!=standard.get('RTYRES')or standard.get('FTYRES')!='TYRE_PROFILE':reasons.append('procedural_tyre_declaration')
    if not standard.get('FCALIPERS')==standard.get('RCALIPERS')=='TEST_CALLIPER'or not standard.get('FDISCS')==standard.get('RDISCS')=='TEST_DISC':reasons.append('unsupported_brake_declaration')
    special=str(code).casefold()in('blank','none','ui_car','ian_car')
    return {'schema':1,'code':code,'status':'deferred_special_declaration'if special else'unsupported_contract'if reasons else'static_selector_supported','reasons':reasons,'role':'source-special-or-placeholder'if special else'source-car-candidate','runtime_player_eligible':False,'native_root':nodes[0]['name']if nodes else None,'selected_nodes':selected,'omitted_nodes':omitted,'native_wheel_pivots':pivots,'standard':standard,'limitations':['Exact static hierarchy/name-hash and declaration availability, not decoded geometry completeness or original runtime behavior.','Explicit existing damaged/emissive name exclusions are authored static-state policy, not recovered native default activation.','Shared Toyo tyre is a declared adaptation; native procedural tyre/rim scale and physical units remain unresolved.']}
