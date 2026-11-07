#!/usr/bin/env python3
"""Offline pinned acquisition/preparation/catalog lifecycle checks."""
import copy
import contextlib
import hashlib
import io
import json
from pathlib import Path
import tempfile
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import install_cars as m
import gt4_preparation_checks as fixtures

class Checks(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name).resolve();self.assets={};self.cars=[]
        for code in ('fixture','fixture2'):
            d,b=fixtures.fixture();d['extras']['car']=code;raw=m.gt4.pack(d,b)
            entry={'id':'gran-turismo-4/'+code,'game':'gran-turismo-4','code':code,'display_name':code,'source_profile':'gt4-ps2-static-car-v2','file':'gran-turismo-4/'+code+'.glb','bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'records':[]}
            self.cars.append(entry);self.assets[entry['file']]=raw
        self.catalog=self.root/'source.json';self.write_catalog()
    def tearDown(self):self.temp.cleanup()
    def write_catalog(self):
        self.catalog.write_text(json.dumps({'cars':self.cars}));self.pin=hashlib.sha256(self.catalog.read_bytes()).hexdigest()
    def opener(self,uri,timeout):
        name=uri.split('/dealership/public/')[1]
        if name=='models.json':return io.BytesIO(self.catalog.read_bytes())
        return io.BytesIO(self.assets[name])
    def install(self,ids=None,**kw):
        return m.install(self.root/'store',ids or [self.cars[0]['id']],catalog_path=self.catalog,expected_sha=self.pin,commit='1'*40,opener=self.opener,minimum_free=0,**kw)
    def test_install_resume_private_and_no_network(self):
        first=self.install();self.assertEqual(first['status'],'installed')
        self.assertGreaterEqual(first['finished_unix'],first['started_unix']);self.assertGreaterEqual(first['elapsed_ms'],0)
        self.assertEqual(len(first['tool_source_sha256']),3);self.assertTrue(all(first['tool_source_sha256'].values()))
        catalog=self.root/'store/vehicles/catalog.racer';original=catalog.read_bytes()
        with patch.object(self,'opener',side_effect=AssertionError('unexpected network')):second=self.install()
        self.assertEqual(second['status'],'installed');self.assertEqual(second['catalog']['status'],'verified-existing');self.assertEqual(catalog.read_bytes(),original)
        self.assertEqual(len(list((self.root/'store/carmodels/install-receipts').glob('*.json'))),2)
        self.assertTrue(all(p.stat().st_mode&0o777==0o600 for p in (self.root/'store/vehicles').iterdir()))
    def test_changed_descriptor_refused(self):
        self.install();vehicles=self.root/'store/vehicles';catalog=(vehicles/'catalog.racer').read_bytes()
        descriptor=next(vehicles.glob('*.vehicle'));descriptor.write_bytes(b'changed')
        result=self.install();self.assertEqual(result['status'],'failed');self.assertEqual(descriptor.read_bytes(),b'changed');self.assertEqual((vehicles/'catalog.racer').read_bytes(),catalog)
    def test_unmanaged_catalog_conflict_preserved(self):
        vehicles=self.root/'store/vehicles';vehicles.mkdir(parents=True);(vehicles/'catalog.racer').write_bytes(b'unknown catalog')
        result=self.install();self.assertEqual(result['error_code'],'unmanaged_catalog_conflict');self.assertEqual((vehicles/'catalog.racer').read_bytes(),b'unknown catalog')
        self.assertEqual(list(vehicles.glob('*.glb')),[])
    def test_exact_root_catalog_adopted(self):
        raw=self.assets[self.cars[0]['file']];mesh,descriptor,r=m.gt4.prepare(raw,self.cars[0]['id'],'fixture')
        entry={'descriptor':r['prepared_sha256']+'.vehicle'};vehicles=self.root/'store/vehicles';vehicles.mkdir(parents=True)
        (vehicles/(r['prepared_sha256']+'.glb')).write_bytes(mesh);(vehicles/entry['descriptor']).write_text(descriptor)
        (vehicles/'catalog.racer').write_bytes(m.catalog_bytes([entry]))
        result=self.install();self.assertEqual(result['status'],'installed');self.assertEqual(result['catalog']['status'],'verified-existing')
    def test_catalog_addition_retains_old_and_resume_after_failure(self):
        self.install();vehicles=self.root/'store/vehicles';old=(vehicles/'catalog.racer').read_bytes()
        with patch.object(m.os,'replace',side_effect=OSError('synthetic')):failed=self.install([self.cars[1]['id']])
        self.assertEqual(failed['status'],'failed');self.assertEqual((vehicles/'catalog.racer').read_bytes(),old)
        self.assertEqual((self.root/'store/carmodels/catalogs'/(m.sha(old)+'.racer')).read_bytes(),old)
        result=self.install([self.cars[1]['id']]);self.assertEqual(result['status'],'installed');self.assertEqual(result['catalog']['entries'],2)
        self.assertEqual(len(list(vehicles.glob('*.glb'))),2)
    def test_changed_mesh_and_output_budget_refused(self):
        self.install();vehicles=self.root/'store/vehicles';catalog=(vehicles/'catalog.racer').read_bytes();mesh=next(vehicles.glob('*.glb'));mesh.write_bytes(b'changed')
        result=self.install();self.assertEqual(result['error_code'],'installed_mesh_modified');self.assertEqual(mesh.read_bytes(),b'changed');self.assertEqual((vehicles/'catalog.racer').read_bytes(),catalog)
        other=self.root/'budget'
        with patch.object(m,'MAX_OUTPUT',1):
            result=m.install(other,[self.cars[0]['id']],catalog_path=self.catalog,expected_sha=self.pin,commit='1'*40,opener=self.opener,minimum_free=0)
        self.assertEqual(result['error_code'],'output_budget');self.assertFalse((other/'vehicles/catalog.racer').exists());self.assertFalse((other/'carmodels/install.lock').exists())
    def test_cli_custom_commit_requires_all_pin_flags(self):
        with patch.object(m,'install') as call,contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):m.main(['--commit','2'*40])
            with self.assertRaises(SystemExit):m.main(['--catalog',str(self.catalog),'--catalog-sha256',self.pin])
        call.assert_not_called()
    def test_foreign_lock_not_removed(self):
        cache=self.root/'store/carmodels';cache.mkdir(parents=True);lock=cache/'install.lock';lock.write_bytes(b'other-operation')
        result=self.install();self.assertEqual(result['error_code'],'install_locked');self.assertEqual(lock.read_bytes(),b'other-operation')
    def test_unsupported_family_and_bad_pin(self):
        self.cars[0].update(game='ford-racing-2');self.write_catalog()
        result=self.install();self.assertEqual(result['error_code'],'adapter_not_enabled')
        result=m.install(self.root/'other',[self.cars[0]['id']],catalog_path=self.catalog,expected_sha='0'*64,commit='1'*40,opener=self.opener,minimum_free=0)
        self.assertEqual(result['error_code'],'catalog_pin')
    def test_source_failure_retains_receipt_and_no_catalog(self):
        self.assets[self.cars[0]['file']]=b'x'*self.cars[0]['bytes']
        result=self.install();self.assertEqual(result['error_code'],'source_acquisition_failed')
        self.assertFalse((self.root/'store/vehicles/catalog.racer').exists())
        self.assertTrue(list((self.root/'store/carmodels/receipts').glob('*.json')))
    def test_catalog_fetch_mock_and_inventory(self):
        with patch.object(m.source,'CATALOG_SHA',self.pin),patch.object(m.source,'COMMIT','1'*40),patch.object(m.source,'DEFAULT_CATALOG',self.root/'absent'):
            result=m.install(self.root/'fetch',catalog_path=None,expected_sha=self.pin,commit='1'*40,opener=self.opener,minimum_free=0,list_only=True)
        self.assertEqual(result['status'],'inventory');self.assertEqual(result['inventory']['models'],2)
    def test_symlink_refused(self):
        (self.root/'store').symlink_to(self.root,target_is_directory=True)
        with self.assertRaises(m.source.ImportFailure):self.install()
    def test_user_excluded_sources_and_ambient_traffic_not_offered(self):
        self.cars[0].update(game='gran-turismo')
        self.cars[1].update(game='midnight-club-los-angeles',code='va_fixture')
        self.write_catalog()
        result=self.install(list_only=True)
        self.assertEqual(result['inventory']['models'],1)
        self.assertEqual(result['available'],[])
        self.assertEqual(result['deferred_traffic_models'],1)
        self.assertEqual(self.install([self.cars[0]['id']])['error_code'],'unknown_id')
        self.assertEqual(self.install([self.cars[1]['id']])['error_code'],'traffic_not_player')
    def test_known_adaptation_requirement_precedes_model_acquisition(self):
        car=self.cars[0]
        with patch.dict(m.source.PLAYER_SOURCE_REQUIREMENTS,{car['sha256']:(car['id'],'source_pose_fixture')}):
            listing=self.install(list_only=True)
            self.assertEqual(listing['available'][0]['review_requirement'],'source_pose_fixture')
            with patch.object(m.source,'acquire',side_effect=AssertionError('unresolved source acquisition')):
                result=self.install()
            self.assertEqual(result['error_code'],'source_requires_adaptation')
            self.assertEqual(result['unresolved_source_requirements'],[{'id':car['id'],'requirement':'source_pose_fixture'}])
            self.assertFalse((self.root/'store/vehicles/catalog.racer').exists())

if __name__=='__main__':unittest.main()
