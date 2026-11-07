#!/usr/bin/env python3
"""Pinned MX5 Racer-authored hub-rest tyre fit; not native suspension/factory proof."""
import argparse,copy,hashlib,json,math,os,shlex,shutil,sys
from pathlib import Path
import prepare_gt4_vehicle as g
from prepare_mcla_vehicle import read_regular
SOURCE_SHA='c46f0f0e2e77aebc2c4d426cb24be7a676682afadbf809e8f7a51de86568dc9a'
DESCRIPTOR_SHA='76ea78946cf64dd6492a710637111a718543e23891c22cabaebdab57b56953f2'
RECEIPT_SHA='93daf99d576ad2c69469a5435ce1f0ab6fdb9477e0353cc363c0f86e7722f1e2'
HIERARCHY_SHA='6bb8de745892db834cdc1dc077a9e5277aa06c37d3ee838aaa4eb2605d53b709'
LABELS=('FL','FR','RL','RR')
sha=lambda b:hashlib.sha256(b).hexdigest()

def transform(doc,binary,wheels,pivots,roles):
    """Bounded affine transformation over baked world-space source geometry."""
    d=copy.deepcopy(doc);g.require(len(d.get('nodes',[]))<=4095 and len(d.get('meshes',[]))<=512,'structure_budget')
    g.require(len(d.get('scenes',[]))==1 and d.get('scene',0)==0 and d['scenes'][0]['nodes']==list(range(len(d['nodes']))),'flat_scene')
    g.require(not any(d.get(k)for k in ('skins','animations','extensionsRequired')),'unsupported_runtime_features')
    g.require(len(wheels)==4 and set(pivots)=={'WHEEL_'+x for x in LABELS} and set(roles)==set(range(len(d['nodes']))),'four_wheel_bindings')
    g.require(all(value in {'body',*('wheel '+x for x in LABELS),*('carrier '+x for x in LABELS)}for value in roles.values()),'unknown_binding_role')
    geom=g.Geometry(d,binary);clouds={};tyres={};work=position_work=0
    for index,node in enumerate(d['nodes']):
        g.require(set(node)=={'name','mesh'} and type(node['mesh'])is int and 0<=node['mesh']<len(d['meshes']),'nonflat_node')
        points=[]
        for primitive in d['meshes'][node['mesh']]['primitives']:
            g.require(primitive.get('mode',4)==4 and not primitive.get('targets')and not primitive.get('extensions'),'primitive_features')
            count=d['accessors'][primitive['indices']]['count'];work+=count;g.require(work<=1500000,'geometry_budget')
            position_work+=d['accessors'][primitive['attributes']['POSITION']]['count'];g.require(position_work<=1000000,'position_budget')
            values=geom.values(primitive['attributes']['POSITION'],'VEC3',{5126});points.extend(values)
        g.require(points,'empty_mesh');clouds[index]=points
        if node['name'].startswith('ADAPTED_NATIVE_TOYO_TYRE_'):
            label=node['name'].removeprefix('ADAPTED_NATIVE_TOYO_TYRE_');g.require(label in LABELS and label not in tyres and roles[index]=='wheel '+label,'ambiguous_tyre');tyres[label]=index
    g.require(set(tyres)==set(LABELS),'four_tyres')
    g.require(sum(map(len,clouds.values()))<=1000000,'position_budget')
    lifts=[];targets=[];factors=[]
    for i,label in enumerate(LABELS):
        w=wheels[i];c=g.finite_vector(w['center'],3);native=g.finite_vector(pivots['WHEEL_'+label],3);target=native[1]/100
        g.require(0.1<target<.7 and abs(c[0]-native[0]/100)<1e-7 and abs(c[2]-native[2]/100)<1e-7,'native_pivot')
        lift=c[1]-target;g.require(0<=lift<.1,'ground_lift');lifts.append(lift)
        old_radius=max(math.hypot(p[1]-c[1],p[2]-c[2])for p in clouds[tyres[label]])
        g.require(.1<old_radius<.7 and target<=old_radius and old_radius<=float(w['radius'])+1e-6,'tyre_radius')
        fixed=[p for index,points in clouds.items()if roles[index] in ('wheel '+label,'carrier '+label)and index!=tyres[label]for p in points]
        g.require(fixed and max(math.hypot(p[1]-c[1],p[2]-c[2])for p in fixed)<target-1e-6,'target_inside_fixed_wheel_envelope')
        factor=target/old_radius;g.require(.5<=factor<=1,'radial_factor');node=d['nodes'][tyres[label]];node['scale']=[1,factor,factor];node['translation']=[0,c[1]*(1-factor),c[2]*(1-factor)];targets.append(target);factors.append(factor)
    g.require(max(lifts)-min(lifts)<1e-6,'nonuniform_source_lift');lift=lifts[0];body=[];new_wheels=[]
    for i,label in enumerate(LABELS):
        c=wheels[i]['center'][:];c[1]-=lift;points=[]
        for index,oldpoints in clouds.items():
            if roles[index] not in ('wheel '+label,'carrier '+label):continue
            for p in oldpoints:
                q=list(p)
                if index==tyres[label]:
                    q[1]=wheels[i]['center'][1]+factors[i]*(p[1]-wheels[i]['center'][1]);q[2]=c[2]+factors[i]*(p[2]-c[2])
                q[1]-=lift;points.append(q)
        radius=max(math.hypot(p[1]-c[1],p[2]-c[2])for p in points);width=2*max(abs(p[0]-c[0])for p in points)
        g.require(abs(radius-targets[i])<1e-7 and c[1]-radius>=-2e-7,'ground_contact');new_wheels.append({'center':c,'radius':radius,'width':width})
    for index,points in clouds.items():
        if roles[index]=='body':body.extend(points)
    g.require(body,'body_missing');bounds=[min(p[i]for p in body)-(lift if i==1 else 0)for i in range(3)]+[max(p[i]for p in body)-(lift if i==1 else 0)for i in range(3)]
    # Prior descriptor includes fixed calipers in body envelope; preserve that
    # semantic projection externally while wheel-cylinder checks include carriers.
    root=len(d['nodes']);d['nodes'].append({'name':'racer_authored_remove_toyo_lift','translation':[0,-lift,0],'children':list(range(root))});d['scenes'][0]['nodes']=[root]
    policy={'schema':1,'authority':'Racer-authored tyre outer-radius=source native hubY/100 ground-rest constraint; NOT native suspension/consumer or factory tyre proof','role':'player-candidate','runtime_player_eligible':False,'source_prepared_sha256':SOURCE_SHA,'source_native_hierarchy_sha256':HIERARCHY_SHA,'removed_uniform_lift':lift,'source_native_pivots':pivots,'tyre_nodes':tyres,'radial_factors':dict(zip(LABELS,factors)),'target_radii':dict(zip(LABELS,targets)),'scope':'Whole source root Y shift only; Toyo tyre group radial worldYZ fit about unchanged source pivots; body/rims/discs/carriers shape, X/Z, width and source BIN/images/materials unchanged.','units':'100native units/metre is retained interpretation, not recovered native physical-unit authority.'}
    d.setdefault('extras',{})['racerHubRestTyreFit']=policy
    return d,new_wheels,bounds,policy

def prepare(data,descriptor,receipt_data):
    g.require(sha(data)==SOURCE_SHA and sha(descriptor)==DESCRIPTOR_SHA and sha(receipt_data)==RECEIPT_SHA,'source_pins');r=json.loads(receipt_data);g.require(r['prepared_sha256']==SOURCE_SHA,'receipt_join')
    tokens=[shlex.split(line)for line in descriptor.decode().splitlines()];g.require(tokens[0]==['RACER_VEHICLE','2'],'descriptor_version');roles={int(row[1]):' '.join(row[2:])for row in tokens if row[0]=='group'}
    d,b=g.unpack(data);g.require(d['extras']['hierarchy_sha256']==HIERARCHY_SHA and d['extras']['native_wheel_pivots']==r['native_wheel_pivots'],'native_proof_join')
    g.require(d['extras']['sourceCarConfiguration']['sha256']=='0700b3cfb7d312edb4688d2fa073003932316eae5efcbcf171f67dad95751360','typed_config_pin')
    new,wheels,bounds,policy=transform(d,b,r['wheels'],r['native_wheel_pivots'],roles);lift=policy['removed_uniform_lift'];bounds=r['body'][:];bounds[1]-=lift;bounds[4]-=lift
    prepared=g.pack(new,b);digest=sha(prepared);num=lambda x:format(x,'.17g')
    lines=['RACER_VEHICLE 2','id '+json.dumps('vehicle-'+digest),'name "Juiced 2 Mazda MX-5 (Racer hub-rest tyre fit)"','mesh '+json.dumps(digest+'.glb'),'sha256 '+digest,'source_sha256 '+HIERARCHY_SHA,'body '+' '.join(map(num,bounds))]
    lines+=['wheel '+label+' '+' '.join(map(num,w['center']+[w['radius'],w['width']]))for label,w in zip(LABELS,wheels)];lines+=['groups '+str(len(roles))]+['group '+str(i)+' '+roles[i]for i in range(len(roles))]
    result={'schema':1,'prepared_sha256':digest,'source_prepared_sha256':SOURCE_SHA,'source_descriptor_sha256':DESCRIPTOR_SHA,'source_receipt_sha256':RECEIPT_SHA,'role':'player-candidate','runtime_player_eligible':False,'body':bounds,'wheels':wheels,'groups':roles,'policy':policy,'source_typed_configuration':d['extras']['sourceCarConfiguration'],'source_member_proof':'Canonical 48members/hierarchy/worldpositions independently verified in mcla-independent-mx5-geometry.json; original source proof retained, not native runtime validation.'}
    return prepared,'\n'.join(lines)+'\n',result

def publish(source,descriptor,receipt,output):
    mesh,text,r=prepare(read_regular(source,16*1024**2),read_regular(descriptor,65536),read_regular(receipt,1024**2));output=Path(output);g.require(not output.exists()and not any(p.is_symlink()for p in(output,*output.parents)),'output_exists');g.require(shutil.disk_usage(output.parent).free>=20*1024**3,'free_space');output.mkdir(mode=0o700)
    for suffix,payload in(('.glb',mesh),('.vehicle',text.encode()),('.json',(json.dumps(r,indent=2)+'\n').encode())):
        fd=os.open(output/(r['prepared_sha256']+suffix),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'wb')as stream:stream.write(payload)
    return r

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for flag in('source','descriptor','receipt','output'):p.add_argument('--'+flag,type=Path,required=True)
    a=p.parse_args()
    try:print(json.dumps(publish(a.source,a.descriptor,a.receipt,a.output),indent=2));return 0
    except(OSError,ValueError,KeyError,TypeError,IndexError,OverflowError):print('Juiced2 fit rejected; unsupported evidence/geometry or storage failure; partialoutput may remain',file=sys.stderr);return 2
if __name__=='__main__':sys.exit(main())
