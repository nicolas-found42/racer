#!/usr/bin/env python3
"""Uniform manufacturer-wheelbase adaptation of an explicitly pinned preparation.

Does not establish original-game units or exact factory body/trim parity. Never
stretches individual axes or moves wheels independently of the complete model.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
from prepare_gt4_vehicle import unpack,pack
from check_car_scale import measure,compare

def adapt(raw,descriptor,canonical,expected):
    if len(raw)>32*1024**2 or hashlib.sha256(raw).hexdigest()!=expected:raise ValueError('prepared input hash mismatch')
    rows=[shlex.split(line) for line in descriptor.splitlines() if line.strip()]
    if len(descriptor)>32768 or rows[0] not in (['RACER_VEHICLE','1'],['RACER_VEHICLE','2']):raise ValueError('descriptor schema')
    fields={row[0]:row[1:] for row in rows if row[0] not in ('group','wheel')}
    if fields.get('sha256')!=[expected] or fields.get('id')!=['vehicle-'+expected]:raise ValueError('descriptor identity')
    wheels=[row for row in rows if row[0]=='wheel']
    if len(wheels)!=4 or [w[1] for w in wheels]!=['FL','FR','RL','RR']:raise ValueError('wheel order')
    numbers=[list(map(float,w[2:])) for w in wheels]
    old=(numbers[0][2]+numbers[1][2]-numbers[2][2]-numbers[3][2])/2
    factor=canonical['nominal']['wheelbase']/old
    if not .5<=factor<=2:raise ValueError('calibration factor outside review range')
    doc,binary=unpack(raw);nodes=doc['nodes'];scene=doc['scenes'][doc.get('scene',0)];roots=scene['nodes'][:]
    if len(nodes)>=4096:raise ValueError('node budget')
    def depth(index,seen):
        if index in seen:raise ValueError('node cycle')
        if len(seen)>=63:raise ValueError('node depth budget')
        for child in nodes[index].get('children',[]):depth(child,seen|{index})
    for root in roots:depth(root,set())
    scene['nodes']=[len(nodes)];nodes.append({'name':'racer_manufacturer_wheelbase_calibration','scale':[factor]*3,'children':roots})
    metadata={'schema':1,'method':'one uniform scale from published manufacturer wheelbase','input_prepared_sha256':expected,'factor':factor,'original_wheelbase':old,'target_wheelbase':canonical['nominal']['wheelbase'],'canonical_id':canonical['canonical_id'],'source':canonical['source'],'applicability':canonical['applicability'],'limitations':['Authored Racer adaptation, not proof of original-game metres or runtime parity.','Original shape and relative pivots preserved; remaining body/variant differences not fitted.','Unscaled source retained separately.']}
    doc.setdefault('extras',{})['racerScaleCalibration']=metadata
    prepared=pack(doc,binary);digest=hashlib.sha256(prepared).hexdigest()
    for row in rows:
        if row[0]=='id':row[1]='vehicle-'+digest
        elif row[0]=='mesh':row[1]=digest+'.glb'
        elif row[0]=='sha256':row[1]=digest
        elif row[0]=='body':row[1:]=[format(float(v)*factor,'.17g') for v in row[1:]]
        elif row[0]=='wheel':row[2:]=[format(float(v)*factor,'.17g') for v in row[2:]]
        elif row[0]=='name':row[1]=(canonical.get('model','Vehicle')+' (factory scale)')[:96]
    text='\n'.join(' '.join(json.dumps(v) if row[0] in ('id','mesh','name') and i==1 else v for i,v in enumerate(row)) for row in rows)+'\n'
    metadata['prepared_sha256']=digest
    return prepared,text,metadata

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('descriptor',type=Path);p.add_argument('--expected-sha256',required=True);p.add_argument('--model-id',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists() or any(p.is_symlink() for p in (a.output,*a.output.parents,a.descriptor)):raise ValueError('fresh regular output/input required')
    canonical=next(v for v in json.loads(Path('assets/catalog/dimensions.json').read_text())['vehicles'] if a.model_id in v['game_model_ids'])
    mesh=a.descriptor.with_suffix('.glb')
    if mesh.is_symlink() or mesh.stat().st_size>32*1024**2:raise ValueError('mesh budget')
    raw,text,receipt=adapt(mesh.read_bytes(),a.descriptor.read_text(),canonical,a.expected_sha256)
    a.output.mkdir(mode=0o700);digest=receipt['prepared_sha256'];desc=a.output/(digest+'.vehicle')
    (a.output/(digest+'.glb')).write_bytes(raw);desc.write_text(text);receipt['comparisons']=compare(measure(desc),canonical)
    (a.output/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt,indent=2))
if __name__=='__main__':main()
