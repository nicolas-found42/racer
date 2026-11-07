#!/usr/bin/env python3
"""Report scoped car evidence; dispatch, metadata, byte identity and runtime differ."""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import time
import import_car_models as source
import install_cars as install
import prepared_inventory as inventory_format

ROOT=Path(__file__).resolve().parents[1]

def digest(path):
    return hashlib.sha256(install.regular_bytes(path,32*1024**2)).hexdigest()

def installation(root):
    """A managed catalog and file hashes prove installed bytes, not GPU behavior."""
    try:
        vehicles=root/'vehicles';raw=install.regular_bytes(vehicles/'catalog.racer',install.MAX_LIBRARY)
        sha=install.sha(raw);manifest=json.loads(install.regular_bytes(root/'carmodels/catalogs'/(sha+'.json'),4*1024**2))
        install.require(manifest.get('catalog_sha256')==sha and install.catalog_bytes(manifest['entries'])==raw,'catalog_manifest_mismatch')
        began=time.monotonic()
        def check():install.require(time.monotonic()-began<30,'installation_inspection_deadline')
        install.validate_entries(manifest['entries'],vehicles,check)
        indexed={r['source_id']:r for r in manifest['entries']}
        install.require(len(indexed)==len(manifest['entries']),'duplicate_installed_source')
        return indexed,{'state':'managed_bytes_verified','catalog_sha256':sha,'scope':'Catalog ownership and actual mesh/descriptor hashes; runtime not rerun.'}
    except FileNotFoundError:
        return {},{'state':'unavailable','reason':'catalog_or_referenced_file_missing'}
    except (OSError,ValueError,KeyError,TypeError) as error:
        return {},{'state':'unknown','reason':str(error) if isinstance(error,install.InstallError) else type(error).__name__}

def assemble(cars,prepared,installed,metadata=None):
    """Pure evidence join. Review flags never create installed/runtime evidence."""
    metadata=metadata or {};prepared_index={r['model_id']:r for r in prepared}
    if len(prepared_index)!=len(prepared):raise ValueError('duplicate_prepared_model')
    if any(r.get('player_eligible') and r.get('role')!='player' for r in prepared):raise ValueError('review_role_conflict')
    rows=[];public_ids=set()
    for car in cars:
        if source.excluded_model(car):continue
        ident=car['id'];public_ids.add(ident);review=prepared_index.get(ident)
        relation='no_preparation_record' if review is None else 'exact_preview_input' if review['source_sha256']==car['sha256'] else 'different_preparation_input; derivation_not_validated_by_report'
        traffic=install.traffic_model(car)
        if traffic and (review or {}).get('player_eligible'):raise ValueError('traffic_player_conflict')
        actual=installed.get(ident);meta=metadata.get(ident)
        if meta and meta.get('preview_sha256')!=car['sha256']:raise ValueError('metadata_source_mismatch')
        rows.append({'model_id':ident,'name':car.get('display_name',car['code']),'family':car['game'],'row_origin':'public_catalog',
            'source_sha256':car['sha256'],'source_bytes':car['bytes'],'source_variant':car.get('source_variant'),
            'preparation_input_sha256':review.get('source_sha256') if review else None,'source_relationship':relation,
            'source_role':'traffic_deferred' if traffic else 'player_namespace_unverified',
            'adapter_dispatch_match':(car['game'],car.get('source_profile')) in install.ADAPTERS,
            'adaptation_requirement':source.player_preparation_requirement(ident,car['sha256']),
            'reviewed_player_preparation':bool(review and review.get('player_eligible')),
            'reviewed_prepared_sha256':review.get('prepared_sha256') if review else None,
            'installed_prepared_sha256':actual.get('mesh_sha256') if actual else None,
            'installed_input_sha256':actual.get('source_sha256') if actual else None,
            'native_metadata':meta,
            'runtime_acceptance':'not_rerun_by_this_report; consult exact native manifests'})
    # Local ISO/source conversions need their own evidence namespace, not a fake
    # public-catalog match. A held research candidate is not implicitly added.
    for ident,review in prepared_index.items():
        if ident in public_ids:continue
        if ident.split('/',1)[0] in source.EXCLUDED_GAMES:raise ValueError('excluded_preparation')
        game,separator,code=ident.partition('/')
        if not separator or not code:raise ValueError('preparation_model_id')
        traffic=install.traffic_model({'game':game,'code':code})
        if traffic and review.get('player_eligible'):raise ValueError('traffic_player_conflict')
        actual=installed.get(ident)
        rows.append({'model_id':ident,'name':ident,'family':ident.split('/',1)[0],'row_origin':'local_preparation',
            'source_sha256':review['source_sha256'],'source_role':'traffic_deferred' if traffic else 'local_source_conversion',
            'adapter_dispatch_match':False,'adaptation_requirement':None,
            'reviewed_player_preparation':bool(review.get('player_eligible')),
            'reviewed_prepared_sha256':review.get('prepared_sha256'),
            'installed_prepared_sha256':actual.get('mesh_sha256') if actual else None,
            'native_metadata':None,'runtime_acceptance':'not_rerun_by_this_report; consult exact native manifests'})
    # An older retained installation may outlive its review-inventory row.
    # Preserve its verified bytes as a separate state; never infer review or
    # runtime acceptance from installation, and never silently drop it.
    for ident,actual in installed.items():
        if ident in public_ids or ident in prepared_index:continue
        game,separator,code=ident.partition('/')
        if not separator or not code:raise ValueError('installed_model_id')
        if game in source.EXCLUDED_GAMES:raise ValueError('excluded_installed_source')
        traffic=install.traffic_model({'game':game,'code':code})
        rows.append({'model_id':ident,'name':ident,'family':game,'row_origin':'installed_only',
            'source_sha256':actual['source_sha256'],
            'source_role':'traffic_deferred' if traffic else 'installed_without_catalog_or_review_record',
            'adapter_dispatch_match':False,'adaptation_requirement':source.player_preparation_requirement(ident,actual['source_sha256']),
            'reviewed_player_preparation':False,'reviewed_prepared_sha256':None,
            'installed_prepared_sha256':actual['mesh_sha256'],
            'installed_input_sha256':actual['source_sha256'],
            'native_metadata':None,'runtime_acceptance':'not_rerun_by_this_report; review_record_unavailable'})
    return sorted(rows,key=lambda r:r['model_id'])

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--catalog',type=Path,default=source.DEFAULT_CATALOG)
    p.add_argument('--prepared',type=Path,default=ROOT/'assets/catalog/prepared-sizes.json')
    p.add_argument('--local-root',type=Path,default=ROOT/'assets/local')
    p.add_argument('--gt4-audit',type=Path);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();cars=source.load_catalog(a.catalog);prepared_raw=install.regular_bytes(a.prepared,inventory_format.MAX_BYTES);prepared=inventory_format.decode(prepared_raw)['vehicles']
    metadata={};inputs={'catalog_sha256':source.CATALOG_SHA,'prepared_inventory_sha256':install.sha(prepared_raw)}
    if a.gt4_audit:
        audit_raw=install.regular_bytes(a.gt4_audit,32*1024**2);audit=json.loads(audit_raw)
        if audit.get('catalog_sha256')!=source.CATALOG_SHA:raise ValueError('metadata_catalog_mismatch')
        for row in audit['rows']:
            ident=row['catalog_id']
            if ident in metadata:raise ValueError('duplicate_metadata_model')
            metadata[ident]={'preview_sha256':row['preview_sha256'],'source_build':audit['native_source_build']['boot'],
                'raw_chassis':row['native_specdb']['chassis_raw'],'raw_WheelLayout':row['native_specdb']['chassis_flags']['WheelLayout'],
                'placement_hypothesis':row['placement_hypothesis'],'review_flags':row['review_flags'],
                'scope':'Decoded game-table declarations and explicit placement hypothesis, not factory or runtime validation.'}
        inputs['gt4_audit_sha256']=install.sha(audit_raw)
    installed,status=installation(a.local_root);rows=assemble(cars,prepared,installed,metadata)
    result={'schema':1,'generated_at_utc_ms':int(time.time()*1000),'inputs':inputs,
        'tool_source_samples':{Path(p).name:digest(Path(p)) for p in (__file__,source.__file__,install.__file__)},
        'tool_source_sample_scope':'Files sampled during report generation, not atomic executing-code or whole-input snapshot attestation.',
        'installation':status,'counts':{
        'public_catalog_in_scope':sum(not source.excluded_model(c) for c in cars),
        'deferred_traffic':sum(r['source_role']=='traffic_deferred' for r in rows),
        'decoded_native_metadata':sum(r['native_metadata'] is not None for r in rows),
        'reviewed_player_preparations':sum(r['reviewed_player_preparation'] for r in rows),
        'installed_byte_verified':sum(r['installed_prepared_sha256'] is not None for r in rows),
            'different_preparation_inputs':sum('different_preparation_input' in r.get('source_relationship','') for r in rows),
        'known_adaptation_requirements':sum(bool(r['adaptation_requirement']) for r in rows)},
        'families':dict(collections.Counter(r['family'] for r in rows)),
        'families_scope':'All evidence rows, including local conversions and installed-only records; not public catalog coverage.',
        'public_catalog_families':dict(collections.Counter(r['family'] for r in rows if r['row_origin']=='public_catalog')),
        'local_preparation_families':dict(collections.Counter(r['family'] for r in rows if r['row_origin']=='local_preparation')),
        'installed_only_families':dict(collections.Counter(r['family'] for r in rows if r['row_origin']=='installed_only')),'models':rows,
        'limits':['This is a scoped join of retained inputs, not a claim of every car in every game.',
            'No raw-source acquisition or GPU/physics replay occurs. Missing records remain unreviewed.',
            'Installed hash evidence can disagree with review inventory; inspect both identities.',
            'Separate source-family audits cover configurations/axles; they are not playable rosters.']}
    payload=json.dumps(result,indent=2,allow_nan=False)+'\n'
    if len(payload.encode())>8*1024**2:raise ValueError('report_budget')
    with a.output.open('x') as f:f.write(payload)
    print(json.dumps({'counts':result['counts'],'installation':status}))

if __name__=='__main__':main()
