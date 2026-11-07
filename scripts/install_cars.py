#!/usr/bin/env python3
"""Install reviewed GT4 adapters from the pinned car catalog, never during gameplay."""
import argparse
import hashlib
from http.client import HTTPException
import json
import os
from pathlib import Path
import re
import shutil
import signal
import shlex
import stat
import sys
import tempfile
import time
import urllib.request
import uuid

import import_car_models as source
import prepare_gt4_vehicle as gt4

DEFAULT_IDS = ('gran-turismo-4/acra0014','gran-turismo-4/niss0004')
# Explicit user source exclusions. The pinned input remains immutable, but these
# families are not offered, acquired or dispatched by the player-car installer.
EXCLUDED_GAMES=source.EXCLUDED_GAMES
# Add only independently reviewed preparation functions with the same bounded interface.
ADAPTERS = {('gran-turismo-4','gt4-ps2-static-car-v2'):gt4.prepare}
MAX_CATALOG = 16*1024**2
MAX_OUTPUT = 128*1024**2
MAX_LIBRARY = 256*1024
MAX_ENTRIES = 3000  # Quoted hash filenames must also fit the runtime's 256KiB catalog.

class InstallError(ValueError): pass

def traffic_model(car):
    # User-confirmed MCLA ambient namespace; vpd/vp are not promoted by this.
    return car['game']=='midnight-club-los-angeles' and car.get('code','').startswith('va_')

def require(condition, code):
    if not condition: raise InstallError(code)

def sha(data):return hashlib.sha256(data).hexdigest()

def regular_bytes(path,limit):
    path=Path(path)
    require(not any(p.is_symlink() for p in (path,*path.parents)),'symlink_refused')
    fd=os.open(path,os.O_RDONLY|os.O_NONBLOCK|os.O_NOFOLLOW)
    with os.fdopen(fd,'rb') as stream:
        before=os.fstat(stream.fileno());require(stat.S_ISREG(before.st_mode),'nonregular_refused')
        data=stream.read(limit+1);after=os.fstat(stream.fileno())
    require(len(data)<=limit and len(data)==before.st_size and (before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns),'file_size_or_change')
    return data

def immutable(path,data):
    """No-overwrite publication. An existing exact candidate is a verified resume."""
    path=Path(path)
    if path.exists() or path.is_symlink():
        require(regular_bytes(path,len(data))==data,'immutable_conflict')
        return 'verified-existing'
    fd,temp=tempfile.mkstemp(prefix='.install-',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as out:out.write(data);out.flush();os.fsync(out.fileno())
        require(regular_bytes(temp,len(data))==data,'write_verification')
        try:os.link(temp,path)
        except FileExistsError:require(regular_bytes(path,len(data))==data,'immutable_conflict')
    finally:
        try:Path(temp).unlink(missing_ok=True)
        except OSError:raise InstallError('temporary_cleanup_failed')
    return 'published'

def encoded(value):return (json.dumps(value,sort_keys=True,separators=(',',':'))+'\n').encode()

def descriptor_source(data):
    try:rows=[shlex.split(line) for line in data.decode().splitlines() if line.startswith('source_sha256 ')]
    except (UnicodeError,ValueError):raise InstallError('descriptor_source_identity')
    require(len(rows)==1 and len(rows[0])==2 and re.fullmatch('[0-9a-f]{64}',rows[0][1]),'descriptor_source_identity')
    return rows[0][1]

def catalog_bytes(entries):
    require(0<len(entries)<=MAX_ENTRIES,'library_count')
    data=('RACER_VEHICLES 1\n'+str(len(entries))+'\n'+''.join(json.dumps(e['descriptor'])+'\n' for e in entries)).encode()
    require(len(data)<=MAX_LIBRARY,'library_bytes')
    return data

def validate_entries(entries,vehicles,check):
    require(isinstance(entries,list) and 0<len(entries)<=MAX_ENTRIES,'managed_entries')
    seen=set()
    for entry in entries:
        check();require(isinstance(entry,dict),'managed_entry')
        digest=entry.get('mesh_sha256');desc=entry.get('descriptor');descsha=entry.get('descriptor_sha256')
        require(isinstance(digest,str) and re.fullmatch('[0-9a-f]{64}',digest) and desc==digest+'.vehicle' and isinstance(descsha,str) and re.fullmatch('[0-9a-f]{64}',descsha) and digest not in seen,'managed_entry')
        seen.add(digest)
        require(sha(regular_bytes(vehicles/(digest+'.glb'),gt4.MAX_OUTPUT))==digest,'installed_mesh_modified')
        db=regular_bytes(vehicles/desc,32768)
        require(sha(db)==descsha,'installed_descriptor_modified')
        require(descriptor_source(db)==entry.get('source_sha256'),'descriptor_source_identity')

def pinned_catalog(cache,catalog_path,expected_sha,commit,opener,check):
    require(re.fullmatch('[0-9a-f]{64}',expected_sha) and re.fullmatch('[0-9a-f]{40}',commit),'source_pin')
    target=cache/('catalog-'+expected_sha+'.json')
    if target.exists() or target.is_symlink():
        data=regular_bytes(target,MAX_CATALOG);require(sha(data)==expected_sha,'cached_catalog_modified')
    elif catalog_path is not None:
        data=regular_bytes(catalog_path,MAX_CATALOG);require(sha(data)==expected_sha,'catalog_pin')
    elif expected_sha==source.CATALOG_SHA and source.DEFAULT_CATALOG.exists():
        data=regular_bytes(source.DEFAULT_CATALOG,MAX_CATALOG);require(sha(data)==expected_sha,'catalog_pin')
    else:
        require(expected_sha==source.CATALOG_SHA and commit==source.COMMIT,'custom_catalog_requires_path')
        with opener(source.BASE.format(commit)+'models.json',timeout=30) as stream:
            chunks=[];size=0;reader=getattr(stream,'read1',stream.read)
            while size<=MAX_CATALOG:
                check();chunk=reader(min(65536,MAX_CATALOG+1-size))
                if not chunk:break
                chunks.append(chunk);size+=len(chunk)
            data=b''.join(chunks)
        require(len(data)<=MAX_CATALOG and sha(data)==expected_sha,'downloaded_catalog_pin')
    # Validate shape before retaining a newly supplied catalog.
    if not target.exists():
        fd,temp=tempfile.mkstemp(prefix='.catalog-',dir=cache)
        try:
            with os.fdopen(fd,'wb') as out:out.write(data)
            cars=source.load_catalog(temp,expected_sha,commit)
        finally:Path(temp).unlink(missing_ok=True)
        immutable(target,data)
    else:cars=source.load_catalog(target,expected_sha,commit)
    return cars

def install(root,ids=None,*,catalog_path=None,expected_sha=source.CATALOG_SHA,commit=source.COMMIT,opener=urllib.request.urlopen,minimum_free=20*1024**3,list_only=False):
    root=source.safe_dir(Path(root).absolute());cache=source.safe_dir(root/'carmodels');vehicles=source.safe_dir(root/'vehicles')
    receipts=source.safe_dir(cache/'install-receipts');catalogs=source.safe_dir(cache/'catalogs');prepared_store=source.safe_dir(cache/'prepared')
    require(shutil.disk_usage(root).free>=minimum_free,'free_space')
    operation=str(uuid.uuid4());lock=cache/'install.lock';lockfd=None;lock_identity=None;started=time.monotonic();started_unix=int(time.time())
    tool_hashes={}
    for filename in (__file__,source.__file__,gt4.__file__):
        try:tool_hashes[Path(filename).name]=sha(regular_bytes(filename,256*1024))
        except (OSError,InstallError):tool_hashes[Path(filename).name]=None
    report={'schema':1,'started_unix':started_unix,'pid':os.getpid(),'tool_source_sha256':tool_hashes,'tool_identity_limit':'Source sampled at operation start; atomic executing-code binding unproven.','source_authority':'canonical pinned catalog/commit' if expected_sha==source.CATALOG_SHA and commit==source.COMMIT else 'explicit caller fixture pins; canonical-source relationship unverified','operation':operation,'source_commit':commit,'source_catalog_sha256':expected_sha,'status':'failed','error_code':None,'requested_ids':list(ids or DEFAULT_IDS),'models':[],'catalog':None,'new_payload_bytes':0,'limitations':['Only the reviewed GT4 static adapter is enabled; catalog affiliation is not installation readiness.','All source claims remain static; renderer/game parity is not established by installation.','Trusted local store with cooperative lock; hostile concurrent directory replacement is not protected.','Individual files/catalog are atomically published; power-loss durability is unqualified.','Receipt write failure may follow catalog commit; it does not roll back the catalog, and the retained ownership manifest supports resume.']}
    def check():require(time.monotonic()-started<240,'operation_deadline')
    def timed_opener(uri,timeout=30):
        check();response=opener(uri,timeout=timeout)
        class Checked:
            def __enter__(self):response.__enter__();return self
            def __exit__(self,*args):return response.__exit__(*args)
            def read1(self,n):check();return getattr(response,'read1',response.read)(n)
            read=read1
        return Checked()
    try:
        try:lockfd=os.open(lock,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        except FileExistsError:raise InstallError('install_locked')
        info=os.fstat(lockfd);lock_identity=(info.st_dev,info.st_ino)
        lock_bytes=encoded({'operation':operation,'pid':os.getpid(),'started_unix':started_unix})
        require(os.write(lockfd,lock_bytes)==len(lock_bytes),'lock_write');os.close(lockfd);lockfd=None
        cars=pinned_catalog(cache,catalog_path,expected_sha,commit,timed_opener,check)
        cars=[car for car in cars if not source.excluded_model(car)]
        if list_only:
            report.update(status='inventory',inventory=source.inventory(cars),deferred_traffic_models=sum(traffic_model(c) for c in cars),available=[{'id':c['id'],'game':c['game'],'name':c.get('display_name',c.get('code',c['id'])),'bytes':c['bytes'],'adapter':c['source_profile'] if (c['game'],c.get('source_profile')) in ADAPTERS else 'not-enabled','review_requirement':source.player_preparation_requirement(c['id'],c['sha256'])} for c in cars if not traffic_model(c)])
        else:
            selected=list(ids or DEFAULT_IDS);require(0<len(selected)<=16 and len(set(selected))==len(selected),'selection_count')
            by_id={c['id']:c for c in cars};require(all(key in by_id for key in selected),'unknown_id')
            require(not any(traffic_model(by_id[key]) for key in selected),'traffic_not_player')
            require(all((by_id[key]['game'],by_id[key].get('source_profile')) in ADAPTERS for key in selected),'adapter_not_enabled')
            unresolved=[{'id':key,'requirement':source.player_preparation_requirement(key,by_id[key]['sha256'])} for key in selected if source.player_preparation_requirement(key,by_id[key]['sha256'])]
            if unresolved:report['unresolved_source_requirements']=unresolved
            require(not unresolved,'source_requires_adaptation')
            acquired=source.acquire(cars,selected,cache,expected_sha=expected_sha,commit=commit,opener=timed_opener,minimum_free=minimum_free)
            report['source_attempts']=[{'id':r['model']['id'],'status':r['acquisition']['status'],'error_code':r['acquisition']['error_code']} for r in acquired]
            require(all(r['acquisition']['status']!='failed' for r in acquired),'source_acquisition_failed')
            payload=MAX_CATALOG+8*1024**2+sum(by_id[key]['bytes'] for key in selected);candidates=[]
            for key in selected:
                check();car=by_id[key];raw=source.read_verified(cache/'objects'/(car['sha256']+'.glb'),car)
                name=car.get('display_name',car.get('code',key.split('/')[-1]))
                mesh,descriptor,metadata=ADAPTERS[(car['game'],car.get('source_profile'))](raw,key,name);digest=metadata['prepared_sha256'];desc=descriptor.encode()
                payload+=2*(len(mesh)+len(desc))+len(encoded(metadata));require(payload<=MAX_OUTPUT,'output_budget')
                artifact=source.safe_dir(prepared_store/digest)
                immutable(artifact/(digest+'.glb'),mesh);immutable(artifact/(digest+'.vehicle'),desc)
                entry={'source_id':key,'source_sha256':car['sha256'],'mesh_sha256':digest,'descriptor':digest+'.vehicle','descriptor_sha256':sha(desc)}
                candidates.append((entry,artifact,mesh,desc));report['models'].append({'entry':entry,'preparation':metadata})
            current=vehicles/'catalog.racer';old=regular_bytes(current,MAX_LIBRARY) if current.exists() or current.is_symlink() else None
            entries=[];catalog_metadata={}
            if old is not None:
                oldsha=sha(old);managed=catalogs/(oldsha+'.json')
                if managed.exists() or managed.is_symlink():
                    manifest=json.loads(regular_bytes(managed,4*1024**2))
                    catalog_metadata=manifest
                    require(isinstance(manifest,dict) and manifest.get('schema')==1 and manifest.get('catalog_sha256')==oldsha and manifest.get('source_commit')==commit and manifest.get('source_catalog_sha256')==expected_sha,'catalog_manifest')
                    entries=manifest.get('entries');validate_entries(entries,vehicles,check);require(catalog_bytes(entries)==old,'catalog_manifest_mismatch')
                else:
                    proposed=[c[0] for c in candidates]
                    require(old==catalog_bytes(proposed),'unmanaged_catalog_conflict')
                    # Root-provisioned exact candidate can be adopted only after actual asset verification below.
            existing={e['mesh_sha256'] for e in entries}
            for entry,artifact,mesh,desc in candidates:
                if entry['mesh_sha256'] not in existing:entries.append(entry);existing.add(entry['mesh_sha256'])
                else:require(next(e for e in entries if e['mesh_sha256']==entry['mesh_sha256'])==entry,'managed_identity_conflict')
                immutable(vehicles/(entry['mesh_sha256']+'.glb'),mesh);immutable(vehicles/entry['descriptor'],desc)
            validate_entries(entries,vehicles,check);new=catalog_bytes(entries);newsha=sha(new)
            manifest={**catalog_metadata,'schema':1,'catalog_sha256':newsha,'source_commit':commit,'source_catalog_sha256':expected_sha,'entries':entries}
            # Persist ownership and both catalog versions before replacement. A crash can be reconstructed by current SHA.
            if old is not None:immutable(catalogs/(sha(old)+'.racer'),old)
            immutable(catalogs/(newsha+'.racer'),new);immutable(catalogs/(newsha+'.json'),encoded(manifest))
            check();require((regular_bytes(current,MAX_LIBRARY) if current.exists() or current.is_symlink() else None)==old,'catalog_changed_during_install')
            if old!=new:
                fd,temp=tempfile.mkstemp(prefix='.catalog-',dir=vehicles)
                try:
                    with os.fdopen(fd,'wb') as out:out.write(new);out.flush();os.fsync(out.fileno())
                    require(regular_bytes(temp,MAX_LIBRARY)==new,'catalog_write_verification');os.replace(temp,current)
                finally:Path(temp).unlink(missing_ok=True)
            report.update(status='installed',new_payload_bytes=payload,catalog={'old_sha256':sha(old) if old is not None else None,'sha256':newsha,'entries':len(entries),'status':'verified-existing' if old==new else 'published'})
    except (InstallError,source.ImportFailure,gt4.PreparationError) as error:
        code=str(error);report['error_code']=code if re.fullmatch('[a-z0-9_]{1,80}',code) else 'invalid_input'
    except (OSError,ValueError,TypeError,KeyError,OverflowError,HTTPException):report['error_code']='transport_storage_or_invalid_input'
    finally:
        if lockfd is not None:os.close(lockfd)
        # A failed lock acquisition does not own another invocation's lock.
        try:
            if lock_identity is not None:
                info=lock.lstat();require((info.st_dev,info.st_ino)==lock_identity,'lock_replaced');lock.unlink()
        except (OSError,InstallError):
            report.update(status='failed',error_code='lock_cleanup_failed')
    report['finished_unix']=int(time.time());report['elapsed_ms']=round((time.monotonic()-started)*1000)
    receipt=receipts/(operation+'.json');immutable(receipt,encoded(report));report['receipt']='carmodels/install-receipts/'+receipt.name
    return report

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=Path('assets/local'));p.add_argument('--id',action='append');p.add_argument('--list',action='store_true',dest='list_only');p.add_argument('--catalog',type=Path);p.add_argument('--catalog-sha256');p.add_argument('--commit')
    a=p.parse_args(argv)
    custom=(a.catalog_sha256 is not None and a.catalog_sha256!=source.CATALOG_SHA) or (a.commit is not None and a.commit!=source.COMMIT)
    if custom and (a.catalog is None or a.catalog_sha256 is None or a.commit is None):p.error('custom fixture pins require --catalog, --catalog-sha256 and --commit')
    def alarm(_signum,_frame):raise InstallError('command_deadline')
    previous=signal.signal(signal.SIGALRM,alarm);signal.setitimer(signal.ITIMER_REAL,270)
    try:
        result=install(a.root,a.id,catalog_path=a.catalog,expected_sha=a.catalog_sha256 or source.CATALOG_SHA,commit=a.commit or source.COMMIT,list_only=a.list_only);print(json.dumps(result,indent=2));return 2 if result['status']=='failed' else 0
    except (OSError,ValueError,source.ImportFailure):print('car installation failed; store/receipt unavailable or command deadline reached',file=sys.stderr);return 2
    finally:signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,previous)

if __name__=='__main__':sys.exit(main())
