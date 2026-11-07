#!/usr/bin/env python3
"""Pinned GT4 metadata coverage; never downloads, prepares or promotes a vehicle."""
import argparse,collections,hashlib,json
from pathlib import Path
import gt4_metadata as g
CATALOG_SHA='fcd6eb5badd4cc120da3daaae315e83b71fb2b9400062b371b73c9f42a442e6c'
INDEX_SHA='d6483838ea99983fde8223588475aef1c74ca1b2b1ce66319a7611709a3381c3'

def indexed(rows,key):
    result={}
    for row in rows:
        k=row[key];g.need(k not in result,'duplicate_'+key);result[k]=row
    return result

def audit(catalog,index,decoded):
    cars=indexed([r for r in catalog['cars']if r['game']=='gran-turismo-4'],'code')
    native=indexed(index['vehicles'],'id');models=decoded['models']
    g.need(set(cars)==set(native)==set(models),'missing_or_extra_model_join')
    g.need(decoded['source_build']==index['source'],'source_build_mismatch')
    files=collections.defaultdict(list)
    for f in index['files']:
        code=f['file'].split('/')[0]
        if code in cars:files[code].append(f)
    rows=[]
    for code in sorted(cars):
        c=cars[code];m=models[code];ch=m['chassis_raw'];tr=m['tires_raw']
        # This is a declared exporter-placement hypothesis. Raw fields and table
        # joins remain available even when its four-wheel geometry is implausible.
        ft=(ch['treadF']-tr['front']['width_raw']*5)/1000
        rt=(ch['treadR']-tr['rear']['width_raw']*5)/1000
        wb=ch['wheelbase']/1000
        flags=[]
        if m['chassis_flags']['WheelLayout']!=0:flags.append('nonstandard_raw_WheelLayout')
        if min(ft,rt)<=0:flags.append('nonpositive_inferred_track')
        elif min(ft,rt)<.1:flags.append('near_coincident_inferred_pair')
        dispatch=(c['source_profile'],c['game'])==('gt4-ps2-static-car-v2','gran-turismo-4')
        rows.append({'code':code,'catalog_id':c['id'],'catalog_name':c['display_name'],'source_profile':c['source_profile'],'source_variant':c['source_variant'],'adapter_dispatch_match':dispatch,'actual_model_preparation':'not_established_by_metadata_audit','runtime_or_factory_validation':False,'preview_sha256':c['sha256'],'preview_bytes':c['bytes'],'preview_triangles':sum(r['triangles']for r in c['records']),'native_package':c['native_package'],'native_roles':native[code]['roles'],'native_files':files[code],'native_specdb':m,'placement_hypothesis':{'basis':'raw WB and tread interpreted in millimetres; tire width byte interpreted as 5 millimetres; centre track=tread-tirewidth; four wheel pairs centred on half wheelbase. This is NOT native consumer/frame/unit proof.','wheelbase_m':wb,'front_track_m':ft,'rear_track_m':rt,'wheel_centres_xz_m':{'FL':[-ft/2,wb/2],'FR':[ft/2,wb/2],'RL':[-rt/2,-wb/2],'RR':[rt/2,-wb/2]},'y':'unknown_without_ride_height_and_tire_encoding_contract'},'review_flags':flags})
    choices=collections.defaultdict(list)
    def choose(row,why):choices[row['code']].append(why)
    for row in rows:
        for flag in row['review_flags']:choose(row,flag)
    for field in ('wheelbase','length','height','mass'):
        ordered=sorted(rows,key=lambda r:(r['native_specdb']['chassis_raw'][field],r['code']))
        choose(ordered[0],'minimum_raw_'+field);choose(ordered[-1],'maximum_raw_'+field)
    for key in ('preview_bytes','preview_triangles'):
        choose(min(rows,key=lambda r:(r[key],r['code'])),'minimum_'+key);choose(max(rows,key=lambda r:(r[key],r['code'])),'maximum_'+key)
    choose(max(rows,key=lambda r:(r['native_specdb']['factory_paint_rows'],r['code'])),'maximum_native_paint_rows')
    names=collections.defaultdict(list);hashes=collections.defaultdict(list)
    for r in rows:names[r['catalog_name']].append(r['code']);hashes[r['preview_sha256']].append(r['code'])
    return {'schema':1,'catalog_sha256':CATALOG_SHA,'native_index_sha256':INDEX_SHA,'metadata_manifest_sha256':g.MANIFEST_SHA256,'native_source_build':index['source'],'counts':{'catalog_gt4':len(rows),'adapter_dispatch_matches':sum(r['adapter_dispatch_match']for r in rows),'joined_native_specs':len(models),'models_prepared_by_this_audit':0,'native_runtime_validations':0},'raw_WheelLayout_codes':{str(v):[r['code']for r in rows if r['native_specdb']['chassis_flags']['WheelLayout']==v]for v in sorted({r['native_specdb']['chassis_flags']['WheelLayout']for r in rows})},'native_role_combination_counts':dict(collections.Counter('|'.join(r['native_roles'])for r in rows)),'duplicate_display_names':{k:v for k,v in names.items()if len(v)>1},'duplicate_preview_hashes':{k:v for k,v in hashes.items()if len(v)>1},'field_selected_cohort':dict(choices),'rows':rows,'limits':['All 730 match adapter dispatch, but metadata coverage does not validate their GLBs, complete source variants, playability or factory dimensions.','Raw WheelLayout values have no proved native-consumer semantics here; value 2 is not automatically translated to a wheel count.','Current four-wheel adapter requires exactly nine active groups, four distinct metadata wheel keys and positive front/rear left-right orientation; unusual topology needs a separate contract.','Source EU SCES_517.19/GT4_EU2560 has 730 GenericCar rows; retained local US2560 evidence has 722. No cross-build row-ID equivalence is assumed.','Paint rows are database variants; open/race/menu roles are retained native files. The showroom preview alone does not establish all variants.']}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--catalog',type=Path,required=True);p.add_argument('--native-index',type=Path,required=True);p.add_argument('--metadata-folder',type=Path,required=True);p.add_argument('--metadata-manifest',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    result=audit(json.loads(g.read(a.catalog,CATALOG_SHA)),json.loads(g.read(a.native_index,INDEX_SHA)),g.join_specs(a.metadata_folder,a.metadata_manifest));payload=json.dumps(result,indent=2,allow_nan=False)+'\n';g.need(len(payload.encode())<=32*1024**2,'output_budget')
    with a.output.open('x')as f:f.write(payload)
    print(json.dumps({'counts':result['counts'],'field_selected_cohort':result['field_selected_cohort']}))
if __name__=='__main__':main()
