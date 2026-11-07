#!/usr/bin/env python3
"""Racer-authored stock tyre fit for exact Juiced 2 preparations.

Per axle, outer radius = the source car's native hub height (native pivot Y/100,
the ground-rest radius), applied radially to every rolling part (rim, tyre,
disc) about the hub; tyre section width = the section width of the attributed
archive record's TyreCode (numeric-signature identity; this equals the sourced
factory width for Z4 and Charger, but the archive's 195 mm MINI and 355 mm
Koenigsegg-rear values differ from the sourced factory 205 and 335 mm). Calipers
never scale. A uniform body lift makes wheel bottoms touch ground. This is NOT
the native renderer's f4/shader sizing, nor factory tyre outer diameter.
"""
import argparse,copy,hashlib,json,math,shlex,sys
from pathlib import Path
import prepare_gt4_vehicle as g
LABELS=('FL','FR','RL','RR')
sha=lambda b:hashlib.sha256(b).hexdigest()
# Section widths (m) from each attributed archive record's TyreCode (numeric-signature hypotheses): front, rear.
# Factory figures from the Firecrawl-sourced attributions differ for MINI (205 mm) and Koenigsegg rear (335 mm).
STOCK_WIDTH={'z4':(.225,.255),'mini':(.195,.195),'charger_rt':(.225,.225),'koenigsegg':(.255,.355)}

# Descriptor `name` of each car's prepared directory (without the " (native source candidate)" suffix): a fit is only
# valid for the preparation it was authored for, so a mistyped car key must not produce another car's widths.
PREPARED_NAME={'z4':'Juiced 2 Z4','mini':'Juiced 2 Cooper S','charger_rt':'Juiced 2 Charger R/T 5.7 V8','koenigsegg':'Juiced 2 CCX'}

def require_prepared_identity(car,toks):
    """SystemExit naming both cars when the prepared descriptor does not belong to `car`."""
    names=[t[1]for t in toks if t[0]=='name'and len(t)>1]
    have=names[0].removesuffix(' (native source candidate)')if names else None
    if have!=PREPARED_NAME[car]:
        raise SystemExit(f'--prepared-dir holds {have!r}, not the {car} preparation ({PREPARED_NAME[car]!r}); refusing to apply its tyre widths')

def points_of(d,geom,index):
    out=[]
    for pr in d['meshes'][d['nodes'][index]['mesh']]['primitives']:
        out.extend(geom.values(pr['attributes']['POSITION'],'VEC3',{5126}))
    return out

def node_point(node,p):
    scale=node.get('scale',[1,1,1]);move=node.get('translation',[0,0,0])
    return [scale[i]*p[i]+move[i] for i in range(3)]

def verify_applied(d,clouds,roles,tyre,info,lift,widths,tol=1e-4):
    """Re-derive each wheel from the node scale/translation actually written (plus the root lift),
    independent of the factors used to build them: outer radius must equal the lifted hub height,
    tyre section width the requested width, and fixed carriers must stay untransformed."""
    root=d['nodes'][-1];g.require(root['name']=='racer_authored_stock_tyre_lift','lift_root')
    for l in LABELS:
        c=info[l][0];cy=c[1]+root['translation'][1];cz=c[2]+root['translation'][2]
        outer=max(math.hypot(node_point(d['nodes'][i],p)[1]+root['translation'][1]-cy,node_point(d['nodes'][i],p)[2]+root['translation'][2]-cz)
                  for i,r in roles.items()if r=='wheel '+l for p in clouds[i])
        width=2*max(abs(node_point(d['nodes'][tyre[l]],p)[0]-c[0])for p in clouds[tyre[l]])
        g.require(abs(outer-cy)<tol,'applied_radius');g.require(abs(width-widths[0 if l in('FL','FR')else 1])<tol,'applied_width')
        g.require(all('scale' not in d['nodes'][i]and'translation' not in d['nodes'][i]for i,r in roles.items()if r=='carrier '+l),'carrier_untouched')

def transform(d0,binary,receipt,roles,widths):
    d=copy.deepcopy(d0);geom=g.Geometry(d,binary)
    g.require(set(roles)==set(range(len(d['nodes']))) and all('translation' not in n and 'scale' not in n for n in d['nodes']),'flat_nodes')
    g.require(len(d['scenes'])==1 and d['scenes'][0]['nodes']==list(range(len(d['nodes']))),'flat_scene')
    clouds={i:points_of(d,geom,i) for i in range(len(d['nodes']))}
    tyre={n['name'].removeprefix('ADAPTED_NATIVE_TOYO_TYRE_'):i for i,n in enumerate(d['nodes'])if n['name'].startswith('ADAPTED_NATIVE_TOYO_TYRE_')}
    g.require(set(tyre)==set(LABELS),'four_tyres')
    piv=receipt['native_wheel_pivots'];wh=receipt['wheels']
    lifts=[];info={}
    for i,l in enumerate(LABELS):
        c=g.finite_vector(wh[i]['center'],3);hub=piv['WHEEL_'+l][1]/100
        g.require(abs(c[0]-piv['WHEEL_'+l][0]/100)<1e-7 and 0.25<hub<0.45,'native_pivot');lifts.append(c[1]-hub);info[l]=(c,hub)
    lift=sum(lifts)/4;g.require(-0.005<=lift<0.1 and max(lifts)-min(lifts)<0.01,'lift_range')
    factors={};lat={}
    for i,l in enumerate(LABELS):
        c,hub=info[l];rad=c[1]-lift  # final hub height == tyre outer radius
        old=max(math.hypot(p[1]-c[1],p[2]-c[2])for p in clouds[tyre[l]]);f=rad/old
        old_w=2*max(abs(p[0]-c[0])for p in clouds[tyre[l]]);lw=widths[0 if l in('FL','FR') else 1]/old_w
        g.require(0.85<=f<=1.2 and 0.7<=lw<=1.6,'factor_range');factors[l]=f;lat[l]=lw
        for idx,role in roles.items():
            if role=='wheel '+l:
                n=d['nodes'][idx];sx=lw if idx==tyre[l] else 1.0
                n['scale']=[sx,f,f];n['translation']=[c[0]*(1-sx),c[1]*(1-f),c[2]*(1-f)]
        fixed=[p for idx,pts in clouds.items()if roles[idx]=='carrier '+l for p in pts]
        g.require(not fixed or max(math.hypot(p[1]-c[1],p[2]-c[2])for p in fixed)<rad,'caliper_inside_wheel')
    root=len(d['nodes']);d['nodes'].append({'name':'racer_authored_stock_tyre_lift','translation':[0,-lift,0],'children':list(range(root))});d['scenes'][0]['nodes']=[root]
    wheels=[]
    for i,l in enumerate(LABELS):
        c=[info[l][0][0],info[l][0][1]-lift,info[l][0][2]];pts=[]
        for idx,pts0 in clouds.items():
            r=roles[idx]
            if r not in('wheel '+l,'carrier '+l):continue
            sx=lat[l]if idx==tyre[l]else 1.0;f=factors[l]if r=='wheel '+l else 1.0
            for p in pts0:pts.append([info[l][0][0]+sx*(p[0]-info[l][0][0]) if r=='wheel '+l else p[0],info[l][0][1]+f*(p[1]-info[l][0][1])-lift if r=='wheel '+l else p[1]-lift,info[l][0][2]+f*(p[2]-info[l][0][2]) if r=='wheel '+l else p[2]])
        radius=c[1];width=2*max(abs(p[0]-c[0])for p in pts)
        wheels.append({'center':c,'radius':radius,'width':width})
    verify_applied(d,clouds,roles,tyre,info,lift,widths)
    # FROZEN WORDING: this authority string is embedded in the published GLB extras (and copied into the inventory limitations),
    # so changing it changes the mesh SHAs. 'sourced stock section width' there means the archive TyreCode width, see the module docstring.
    pol={'schema':1,'authority':'Racer-authored: tyre outer radius = native hub Y/100 ground rest, width = sourced stock section width; NOT native f4/shader or factory outer diameter','uniform_lift':lift,'factors':factors,'lateral':lat,'widths':widths}
    d.setdefault('extras',{})['racerStockTyreFit']=pol
    return d,wheels,pol

def load_prepared(prepared_dir):
    """Pinned prepared-vehicle directory: exactly one GLB and one descriptor plus receipt.json."""
    glbs=sorted(prepared_dir.glob('*.glb'));descs=sorted(prepared_dir.glob('*.vehicle'))
    g.require(len(glbs)==1 and len(descs)==1 and (prepared_dir/'receipt.json').is_file(),'prepared_dir_contents')
    glb,desc=glbs[0],descs[0];receipt=json.loads((prepared_dir/'receipt.json').read_text())
    g.require(all(k in receipt for k in('prepared_sha256','body','wheels','native_wheel_pivots')),'receipt_fields')
    data=glb.read_bytes();g.require(sha(data)==glb.stem==receipt['prepared_sha256'],'pin')
    toks=[shlex.split(l)for l in desc.read_text().splitlines()];roles={int(r[1]):' '.join(r[2:])for r in toks if r[0]=='group'}
    return glb,desc,receipt,data,toks,roles

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('car',choices=sorted(STOCK_WIDTH));p.add_argument('--prepared-dir',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise SystemExit(f'--output already exists: {a.output}; use a new directory')
    try:
        glb,desc,receipt,data,toks,roles=load_prepared(a.prepared_dir)
        require_prepared_identity(a.car,toks)
        d,b=g.unpack(data);new,wheels,pol=transform(d,b,receipt,roles,STOCK_WIDTH[a.car])
        mesh=g.pack(new,b);dg=sha(mesh);num=lambda x:format(x,'.17g')
        lift=pol['uniform_lift'];body=receipt['body'][:];body[1]-=lift;body[4]-=lift
        name=[t for t in toks if t[0]=='name'][0][1].replace(' (native source candidate)','')+' (Racer stock tyre fit)'
        src=[t for t in toks if t[0]=='source_sha256'][0][1]
        lines=['RACER_VEHICLE 2','id '+json.dumps('vehicle-'+dg),'name '+json.dumps(name),'mesh '+json.dumps(dg+'.glb'),'sha256 '+dg,'source_sha256 '+src,'body '+' '.join(map(num,body))]
        lines+=['wheel '+l+' '+' '.join(map(num,w['center']+[w['radius'],w['width']]))for l,w in zip(LABELS,wheels)]
        lines+=['groups '+str(len(roles))]+['group '+str(i)+' '+roles[i]for i in range(len(roles))]
        res={'schema':1,'prepared_sha256':dg,'source_prepared_sha256':glb.stem,'source_descriptor_sha256':sha(desc.read_bytes()),'policy':pol,'wheels':wheels,'body':body}
    except g.PreparationError as error:raise SystemExit(f'fit_juiced2_stock_tyres: {error} (--prepared-dir {a.prepared_dir}); nothing was written')
    except (KeyError,TypeError,IndexError,ValueError,AttributeError) as error:  # damaged receipt/descriptor content, not a tool bug path
        raise SystemExit(f'fit_juiced2_stock_tyres: malformed preparation input ({type(error).__name__}: {error}) in --prepared-dir {a.prepared_dir}; nothing was written')
    a.output.mkdir(parents=True,exist_ok=False)
    (a.output/(dg+'.glb')).write_bytes(mesh);(a.output/(dg+'.vehicle')).write_text('\n'.join(lines)+'\n')
    (a.output/'receipt.json').write_text(json.dumps(res,indent=2)+'\n');print(json.dumps({'car':a.car,'sha':dg,'factors':pol['factors'],'lat':pol['lateral'],'lift':lift,'wheels':[[round(x,4)for x in w['center']+[w['radius'],w['width']]]for w in wheels]}))
if __name__=='__main__':sys.exit(main())
