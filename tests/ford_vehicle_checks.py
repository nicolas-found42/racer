import copy
import hashlib
import json
import math
from pathlib import Path
import shlex
import struct
import sys
import tempfile
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).parents[1]/'scripts'))
import prepare_ford_vehicle as ford
from prepare_gt4_vehicle import pack,unpack,Geometry,PreparationError


def fixture():
    binary=bytearray();views=[];accessors=[]
    def accessor(rows,kind,ct):
        offset=len(binary);fmt={5126:'f',5123:'H'}[ct]
        for row in rows:binary.extend(struct.pack('<'+fmt*len(row),*row))
        length=len(binary)-offset;binary.extend(b'\0'*(-len(binary)%4));views.append({'buffer':0,'byteOffset':offset,'byteLength':length})
        accessors.append({'bufferView':len(views)-1,'componentType':ct,'count':len(rows),'type':kind});return len(accessors)-1
    body=accessor([(-1,.2,-2),(1,.2,-2),(0,1.2,2),(-1,.3,2)],'VEC3',5126)
    wheel=accessor([(-.1,.3,0),(.1,-.3,0),(.1,0,.3),(-.1,0,-.3)],'VEC3',5126)
    indices=accessor([(0,),(1,),(2,),(0,),(2,),(3,)],'SCALAR',5123)
    meta=lambda names:{'sourceNames':names,'visibilityPreset':'low_speed'}
    nodes=[{'name':'body','mesh':0,'extras':meta([]),'children':[]}]
    for i,suffix in enumerate(ford.WHEELS):
        hub=len(nodes);nodes[0]['children'].append(hub)
        nodes.append({'name':'HUB_'+suffix,'translation':[-.8 if i%2==0 else .8,.31,1 if i<2 else -1], 'extras':meta(['HUB_'+suffix]),'children':[hub+1]})
        nodes.append({'name':'WHEEL_'+suffix,'mesh':1,'extras':meta(['WHEEL_'+suffix])})
    state={'wheelStaticBit':True,'wheelMovingBit':False,'wheelGlobalOverride':0,'brakeLightsOn':False,'reverseLightsOn':False,'exhaustOn':False,'transforms':'original serialized values'}
    d={'asset':{'version':'2.0'},'scene':0,'scenes':[{'nodes':[0],'extras':{'sourceTree':0,'visibilityPreset':'low_speed','stateInputs':state}}], 'nodes':nodes,'meshes':[{'primitives':[{'attributes':{'POSITION':p},'indices':indices}]} for p in (body,wheel)],'accessors':accessors,'bufferViews':views,'buffers':[{'byteLength':len(binary)}],'extras':{'car':'FIXTURE','originalModelSha256':'a'*64,'limits':['Fixture source candidate.']}}
    return d,binary


def rejects(d,b,reason=None,physics=None):
    try:ford.prepare(pack(d,b),'ford-racing-2/FIXTURE','Fixture Ford',physics)
    except (PreparationError,KeyError,TypeError,ValueError) as e:
        if reason:assert str(e)==reason,(str(e),reason)
        return
    raise AssertionError('invalid fixture accepted')


def containment(prepared,receipt):
    d,b=unpack(prepared);g=Geometry(d,b);poses={}
    def visit(i,s,t):
        n=d['nodes'][i];ns=n.get('scale',[1,1,1]);nt=n.get('translation',[0,0,0]);ws=[s[k]*ns[k] for k in range(3)];wt=[t[k]+s[k]*nt[k] for k in range(3)];poses[i]=(ws,wt)
        for child in n.get('children',[]):visit(child,ws,wt)
    for i in d['scenes'][d['scene']]['nodes']:visit(i,[1,1,1],[0,0,0])
    bound=receipt['body']
    for index,wheel in receipt['groups']:
        scale,translation=poses[index]
        for p in d['meshes'][d['nodes'][index]['mesh']]['primitives']:
            for point in g.values(p['attributes']['POSITION']):
                q=[point[k]*scale[k]+translation[k] for k in range(3)]
                if wheel<0:assert all(bound[k]-1e-7<=q[k]<=bound[k+3]+1e-7 for k in range(3))
                else:
                    w=receipt['wheels'][wheel];c=w['center'];assert abs(q[0]-c[0])<=w['width']/2+1e-7;assert math.hypot(q[1]-c[1],q[2]-c[2])<=w['radius']+1e-7


def main():
    d,b=fixture();source=pack(d,b);prepared,descriptor,receipt=ford.prepare(source,'ford-racing-2/FIXTURE','Fixture Ford')
    out,binout=unpack(prepared)
    assert binout==b and out['meshes']==d['meshes'] and out['accessors']==d['accessors']
    assert receipt['groups']==[(0,-1),(2,0),(4,1),(6,2),(8,3)] and receipt['wheelbase']==2
    assert hashlib.sha256(prepared).hexdigest() in descriptor and receipt['source_sha256']==hashlib.sha256(source).hexdigest()
    assert shlex.split(descriptor.splitlines()[1])==['id','vehicle-'+receipt['prepared_sha256']]
    containment(prepared,receipt)
    physics={'axles':[{'radius':.312,'width':.235},{'radius':.324,'width':.243}]}
    fitted,_,fit=ford.prepare(source,'ford-racing-2/FIXTURE','Fixture Ford',physics);containment(fitted,fit)
    assert abs(fit['wheels'][0]['radius']-.312)<1e-7 and abs(fit['wheels'][2]['radius']-.324)<1e-7
    assert fit['wheel_radius_fitting'][0]['lateral_scale']==1 and fit['source_hubs']['FL']==[-.8,.31,1]
    assert fit['ground_lift']>0 and all(w['center'][1]-w['radius']>=-1e-7 for w in fit['wheels'])
    bad=copy.deepcopy(d);bad['scenes'][0]['extras']['visibilityPreset']='all_states';rejects(bad,b,'explicit_low_speed_scene')
    bad=copy.deepcopy(d);bad['nodes'][2]['extras']['sourceNames']=['WHEEL_BACK_RIGHT'];rejects(bad,b,'wheel_owner')
    bad=copy.deepcopy(d);bad['nodes'][1]['translation'][0]=.8;rejects(bad,b,'wheel_side')
    bad=copy.deepcopy(d);bad['nodes'][2]['children']=[0];rejects(bad,b,'source_graph')
    bad=copy.deepcopy(d);bad['accessors'][2]['count']=ford.MAX_INDICES+3;rejects(bad,b,'index_budget')
    bad=copy.deepcopy(d);bad['nodes'][1]['rotation']=[0,0,0,1];rejects(bad,b,'node_transform')
    bad=copy.deepcopy(d);bad['scenes'].append(copy.deepcopy(bad['scenes'][0]));rejects(bad,b,'explicit_low_speed_scene')
    boundary=copy.deepcopy(d);boundary['nodes'].extend({} for _ in range(4095-len(boundary['nodes'])))
    capped,_,_=ford.prepare(pack(boundary,b),'ford-racing-2/FIXTURE','Fixture Ford')
    assert len(unpack(capped)[0]['nodes'])==4096
    boundary['nodes'].append({});rejects(boundary,b,'structure_nodes')
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp).resolve();config=root/'config';config.mkdir()
        (config/'cardata.txt').write_text(':CAR_TYPE FIXTURE\n:CAR_MODEL_YEAR 1973\n:CAR_FRONT_TYRE_TYPE F\n:CAR_BACK_TYRE_TYPE B\n')
        for name,kind,r in [('tyres_front.txt','F',.312),('tyres_back.txt','B',.324)]:
            (config/name).write_text(':TYPE '+kind+'\n:RADIUS '+str(r)+'\n:WIDTH .235\n')
        meta=ford.source_physics(config,'ford-racing-2/FIXTURE');assert meta['year']==1973 and meta['axles'][1]['radius']==.324
        (config/'tyres_back.txt').write_text(':TYPE WRONG\n:RADIUS .324\n:WIDTH .243\n')
        try:ford.source_physics(config,'ford-racing-2/FIXTURE');raise AssertionError('wrong physics join accepted')
        except PreparationError:pass
        path=root/'input.glb';path.write_bytes(source);destination=root/'published'
        report=ford.publish(path,'ford-racing-2/FIXTURE','Fixture Ford',destination,physics,minimum_free=0)
        assert (destination/(report['prepared_sha256']+'.glb')).read_bytes()==fitted
        before=list(destination.iterdir())
        try:ford.publish(path,'ford-racing-2/FIXTURE','Fixture Ford',destination,minimum_free=0);raise AssertionError('overwrite accepted')
        except PreparationError:pass
        assert list(destination.iterdir())==before
    print('PASS: Ford scene/ownership/pivots, unchanged geometry, canonical radius fitting, containment, malformed cases, source joins, publish preservation')
if __name__=='__main__':main()
