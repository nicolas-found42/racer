#!/usr/bin/env python3
"""Compare a prepared car's measured geometry with attributed nominal dimensions."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import shlex
from prepare_mcla_vehicle import read_regular

def measure(path):
    return measure_bytes(read_regular(path,32768))

def measure_bytes(raw):
    if len(raw)>32768:raise ValueError('descriptor input budget')
    rows=[shlex.split(line) for line in raw.decode().splitlines() if line.strip()]
    if not rows or rows[0] not in (['RACER_VEHICLE','1'],['RACER_VEHICLE','2']):raise ValueError('descriptor version')
    bodies=[row for row in rows if row[0]=='body']
    if len(bodies)!=1:raise ValueError('one body required')
    body=bodies[0]
    b=[float(x) for x in body[1:]]
    wheel_rows=[row for row in rows if row[0]=='wheel']
    if len(wheel_rows)!=4 or any(len(row)!=7 for row in wheel_rows):raise ValueError('four wheel rows required')
    wheels={row[1]:[float(x) for x in row[2:]] for row in wheel_rows}
    if len(b)!=6 or set(wheels)!={'FL','FR','RL','RR'} or any(len(w)!=5 for w in wheels.values()):raise ValueError('geometry fields')
    if not all(math.isfinite(x) for x in b+sum(wheels.values(),[])):raise ValueError('nonfinite geometry')
    if any(b[i]>=b[i+3] for i in range(3)) or b[1]<0:raise ValueError('body bounds')
    if any(w[3]<=0 or w[4]<=0 or w[1]-w[3]<-.002 for w in wheels.values()):raise ValueError('wheel dimensions or clearance')
    if wheels['FL'][0]>=wheels['FR'][0] or wheels['RL'][0]>=wheels['RR'][0] or min(wheels['FL'][2],wheels['FR'][2])<=max(wheels['RL'][2],wheels['RR'][2]):raise ValueError('wheel ordering')
    return {'length':b[5]-b[2],'visible_body_width':b[3]-b[0],
            'body_box_height':b[4]-b[1],'ground_height':max(b[4],*(w[1]+w[3] for w in wheels.values())),
            'wheelbase':(wheels['FL'][2]+wheels['FR'][2]-wheels['RL'][2]-wheels['RR'][2])/2,
            'front_track':wheels['FR'][0]-wheels['FL'][0],'rear_track':wheels['RR'][0]-wheels['RL'][0],
            'minimum_tire_clearance':min(w[1]-w[3] for w in wheels.values()),
            'body_bounds':b,'wheels':wheels}

def compare(measured,canonical):
    values={}
    for metric,target in canonical['nominal'].items():
        if metric=='width':continue
        actual=measured['ground_height' if metric=='height' else metric]
        values[metric]={'nominal':target,'measured':actual,'delta':actual-target,'relative_error':(actual-target)/target}
    checks={key:abs(values[key]['relative_error'])<=(.02 if key in ('wheelbase','front_track','rear_track') else .03)
            for key in ('length','height','wheelbase','front_track','rear_track') if key in values}
    return {'canonical_id':canonical['canonical_id'],'applicability':canonical['applicability'],
            'comparisons':values,'checks':checks,'within_authored_tolerances':all(checks.values()),
            'width_policy':'Visible mesh width is retained; published overall-width convention is not assumed equivalent.',
            'tolerances':'Authored review limits:2%wheelbase/tracks,3%length/groundheight; not proof of native units or exact factory parity.'}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('descriptor',type=Path);p.add_argument('--model-id',required=True)
    p.add_argument('--dimensions',type=Path,default=Path(__file__).parents[1]/'assets/catalog/dimensions.json')
    p.add_argument('--output',type=Path);a=p.parse_args()
    metadata=json.loads(read_regular(a.dimensions,256*1024))
    descriptor=read_regular(a.descriptor,32768);measured=measure_bytes(descriptor)
    canonical=next((v for v in metadata['vehicles'] if a.model_id in v['game_model_ids']),None)
    source_rows=[shlex.split(line) for line in descriptor.decode().splitlines() if line.startswith('source_sha256 ')]
    source_hash=source_rows[0][1] if len(source_rows)==1 and len(source_rows[0])==2 else None
    if canonical and canonical['source_model_sha256'].get(a.model_id)!=source_hash:
        raise ValueError('canonical model identity does not match descriptor source hash')
    report={'schema':1,'model_id':a.model_id,'descriptor_sha256':hashlib.sha256(descriptor).hexdigest(),
            'source_sha256':source_hash,'measurement_scope':'Declared descriptor geometry; use runtime loadVehicleAsset for independent mesh hash and containment checks.',
            'units':'metres','measured':measured,'canonical':compare(measured,canonical) if canonical else None,
            'status':'compared' if canonical else 'manufacturer dimensions unavailable; measured source geometry only'}
    text=json.dumps(report,indent=2,allow_nan=False)+'\n'
    if a.output:
        with a.output.open('x') as out:out.write(text)
    print(text,end='')
    return 0 if not canonical or report['canonical']['within_authored_tolerances'] else 2
if __name__=='__main__':raise SystemExit(main())
