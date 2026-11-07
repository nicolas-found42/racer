#!/usr/bin/env python3
"""Explicit Racer parked compression candidate; not a recovered native rest pose."""
import argparse,copy,hashlib,json,os,re,shutil,sys
from pathlib import Path
from prepare_gt4_vehicle import unpack,pack,require,PreparationError
from prepare_mcla_vehicle import read_regular
SOURCE_SHA='ba086fe0712a2c7549b8b5069c6c0bfb48fa9894ed0a19b890553239d7f9dbe6'
CFG_SHA='b0074215c7de997983ec52d6cee5b6fadb8c4634e242e8d2280027292960a6a2'
SPRING_SHA='2947a6828631ac845241993fadcb6e195ee7510f097cd7b298e27a7b6e368ac6'
DESCRIPTOR_SHA='dd001e45d7836d27270fca475f642a9744d3a70faa47d1bad3f8615badb2a8fa'

def adapt(mesh,descriptor,cfg,spring,pose_mode="minimum-travel",clearance_data=None):
    require(hashlib.sha256(mesh).hexdigest()==SOURCE_SHA,'prepared_source_pin')
    require(hashlib.sha256(descriptor.encode()).hexdigest()==DESCRIPTOR_SHA,'descriptor_pin')
    require(hashlib.sha256(spring).hexdigest()==SPRING_SHA,'spring_pin')
    require(hashlib.sha256(cfg).hexdigest()==CFG_SHA,'cfg_pin')
    # Exact source assignment shapes; do not execute Java or derive offset from pixels.
    rows=re.findall(rb'^spring\s+([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)',cfg,re.M)
    require(len(rows)==4 and len(set(rows))==1,'cfg_spring_rows')
    rest=float(rows[0][0]);match=re.search(rb'minlength\s*=\s*Inch2Meter\(2\.0\)',spring)
    require(match is not None and b'spring_SuperDuty_500_front' in spring,'spring_compression_source')
    minimum=2*.0254;require(pose_mode in ('minimum-travel','design-loaded','geometry-bounded'),'pose_mode');selected_length=minimum if pose_mode=='minimum-travel' else 8*.0254;clearance=None
    if pose_mode=='geometry-bounded':
        require(isinstance(clearance_data,bytes) and hashlib.sha256(clearance_data).hexdigest()=='9dc80c4f48c0e0ad5002fbbf63b0447f17f4008df303d1cc32467f92a6c5a411','clearance_proof_pin');clearance=json.loads(clearance_data);verified=clearance['largest_bisection_pass'];require(verified['passes'] and verified['minimum_clearance_after_margin']>=0 and clearance['margin_m']==.005 and len(clearance['steering_samples'])==1101,'clearance_proof');selected_length=rest-verified['delta_y']
    delta=rest-selected_length;require(0<delta<.3,'compression_range')
    d,b=unpack(mesh);old=copy.deepcopy(d['extras']['racerPreparation']);require(old['runtime_player_eligible'] is False,'source_role')
    root=d['scenes'][0]['nodes'];require(root==[32] and d['nodes'][32]['children']==list(range(32)),'source_scene')
    oldlift=d['nodes'][32]['translation'][1];require(oldlift>delta,'ground_lift_range')
    groups={int(line.split()[1]):int(line.split()[2]) for line in descriptor.splitlines() if line.startswith('group ')}
    require(len(groups)==32 and sum(v>=0 for v in groups.values())==8,'source_groups')
    for index,wheel in groups.items():
        if wheel>=0:d['nodes'][index]['matrix'][13]+=delta
    d['nodes'][32]['translation'][1]-=delta
    policy={'schema':1,'authority':'Racer-authored parked compression pose constrained by native configured spring reference and installed spring minimum; NOT native equilibrium/consumer proof','source_prepared_sha256':SOURCE_SHA,'cfg_sha256':CFG_SHA,'spring_sha256':hashlib.sha256(spring).hexdigest(),'cfg_reference_length_m':rest,'installed_minimum_length_m':minimum,'selected_length_m':selected_length,'pose_mode':pose_mode,'baseline_graphics_reference':'CFG.290 used as stated static-reference baseline, NOT native Java override; mapping to native consumer graphics frame remains unknown','installed_java_unloaded_rest_m':{'front':.272795625,'rear':.27950715277777777},'native_unloaded_rest_minus_minimum_m':{'front':.272795625-minimum,'rear':.27950715277777777-minimum},'selected_cfg_reference_delta_is_not_native_rest_minus_minimum':True,'wheel_relative_chassis_y_delta_m':delta,'ground_lift_before':oldlift,'ground_lift_after':oldlift-delta,'world_effect':'wheel geometry remains at same ground-rest pose; entire nonwheel body lowered by compressiondelta','native_equilibrium':'unverified; selected_length_m records this authored pose choice, not recovered native equilibrium','unchanged':['allbinarygeometry/imagebytes','materials','wheelradius/width','nativewheelX/Zpivots'],'omitted_native_consumers':['WheelRef.setArm/setHub native solver','suspension setSlotPos X offsets','native dynamic load/engine assembly'],'eligibility':'candidate; requires root GPU fit review and dynamic-clearance acceptance'}
    if clearance is not None:policy['triangle_clearance']={'report_sha256':hashlib.sha256(clearance_data).hexdigest(),'margin_m':.005,'steering_samples':1101,'selected_result':clearance['largest_bisection_pass'],'limitations':clearance['limitations']}
    d['extras']['racerParkedCompression']=policy
    raw=pack(d,b);sha=hashlib.sha256(raw).hexdigest();lines=[]
    for line in descriptor.splitlines():
        if line.startswith('id '):line='id '+json.dumps('vehicle-'+sha)
        elif line.startswith('mesh '):line='mesh '+json.dumps(sha+'.glb')
        elif line.startswith('sha256 '):line='sha256 '+sha
        elif line.startswith('name '):line='name "Furrano GT54 (Racer parked compression)"'
        elif line.startswith('body '):
            values=list(map(float,line.split()[1:]));values[1]-=delta;values[4]-=delta;require(values[1]>0,'body_ground');line='body '+' '.join(format(v,'.17g') for v in values)
        lines.append(line)
    return raw,'\n'.join(lines)+'\n',{'schema':1,'role':'player-candidate','runtime_player_eligible':False,'prepared_sha256':sha,'source_prepared_sha256':SOURCE_SHA,'policy':policy,'source_preparation':old}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for flag in ('mesh','descriptor','cfg','spring','output'):p.add_argument('--'+flag,type=Path,required=True)
    p.add_argument('--pose',choices=['minimum-travel','design-loaded','geometry-bounded'],default='minimum-travel')
    p.add_argument('--clearance',type=Path)
    a=p.parse_args();raw,text,r=adapt(read_regular(a.mesh,16*1024**2),read_regular(a.descriptor,32768).decode(),read_regular(a.cfg,65536),read_regular(a.spring,65536),a.pose,read_regular(a.clearance,1024*1024) if a.clearance else None)
    require(not a.output.exists() and not any(x.is_symlink() for x in (a.output,*a.output.parents)),'fresh_output');require(shutil.disk_usage(a.output.parent).free>=20*1024**3,'free_space');a.output.mkdir(mode=0o700)
    for suffix,data in (('.glb',raw),('.vehicle',text.encode()),('.json',(json.dumps(r,indent=2)+'\n').encode())):
        fd=os.open(a.output/(r['prepared_sha256']+suffix),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'wb') as f:f.write(data)
    print(json.dumps(r,indent=2))
if __name__=='__main__':main()
