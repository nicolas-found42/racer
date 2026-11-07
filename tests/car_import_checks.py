#!/usr/bin/env python3
"""Offline acquisition invariants using tiny synthetic GLB fixtures."""
import hashlib
import importlib.util
import io
from http.client import IncompleteRead
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('car_import', Path(__file__).resolve().parents[1] / 'scripts/import_car_models.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class ImportChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        payload = b'{"asset":{"version":"2.0"}} '
        self.data = struct.pack('<4sIIII', b'glTF', 2, 20+len(payload), len(payload), 0x4e4f534a) + payload
        self.car = dict(id='family/car', game='family', file='family/car.glb', bytes=len(self.data), sha256=hashlib.sha256(self.data).hexdigest(), records=[])
    def tearDown(self): self.temp.cleanup()
    def run_import(self, **kwargs):
        return m.acquire([self.car], ['family/car'], self.root/'store', minimum_free=0, **kwargs)[0]
    def test_download_resume_and_hash(self):
        calls=[]
        def opener(uri, timeout):
            calls.append(uri)
            return io.BytesIO(self.data)
        first=self.run_import(opener=opener)
        self.assertEqual(first['acquisition']['status'], 'verified-download')
        second=self.run_import(opener=lambda *a, **k: self.fail('resume used network'))
        self.assertEqual(second['acquisition']['status'], 'verified-resume')
        self.assertEqual(len(list((self.root/'store/receipts').glob('*.json'))),2)
        self.assertIn('/dealership/public/family/car.glb', calls[0])
    def test_failed_hash_no_publish(self):
        result=self.run_import(opener=lambda *a, **k: io.BytesIO(b'x'*len(self.data)))
        self.assertEqual(result['acquisition']['error_code'], 'hash_mismatch')
        self.assertEqual(list((self.root/'store/objects').iterdir()), [])
        self.assertEqual(len(list((self.root/'store/receipts').iterdir())), 1)
    def test_existing_unknown_no_overwrite(self):
        self.run_import(opener=lambda *a, **k: io.BytesIO(self.data))
        path=self.root/'store/objects'/(self.car['sha256']+'.glb')
        path.write_bytes(b'unknown')
        result=self.run_import()
        self.assertEqual(result['acquisition']['status'],'failed')
        self.assertEqual(path.read_bytes(), b'unknown')
    def test_symlink_refused(self):
        (self.root/'store').symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(m.ImportFailure): self.run_import()
    def test_budget_and_duplicate(self):
        self.car['bytes']=m.MAX_MODEL+1
        with self.assertRaises(m.ImportFailure): self.run_import()
        with self.assertRaises(m.ImportFailure): m.acquire([self.car],['family/car','family/car'], self.root/'s',minimum_free=0)
    def test_cache(self):
        cache=self.root/'cache'; cache.mkdir()
        (cache/(self.car['sha256']+'.glb')).write_bytes(self.data)
        result=self.run_import(cache=cache,opener=lambda *a,**k:self.fail('cache used network'))
        self.assertEqual(result['acquisition']['status'],'verified-cache')
    def test_catalog_pin_and_paths(self):
        path=self.root/'catalog.json'; path.write_text(json.dumps({'cars':[self.car]}))
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        self.assertEqual(len(m.load_catalog(path,digest)),1)
        with self.assertRaises(m.ImportFailure): m.load_catalog(path)
        for name in ('../car.glb','/car.glb','a//b','a/./b','a%20b','a\\b'):
            with self.assertRaises(m.ImportFailure): m.relative(name)
    def test_excluded_sources_rejected_before_download_or_cache(self):
        for family in ('gran-turismo','redline'):
            for field in ('game','id','file'):
                car=dict(self.car);car[field]=family if field=='game' else family+'/car'+('.glb' if field=='file' else '')
                with self.subTest(family=family,field=field):
                    with self.assertRaisesRegex(m.ImportFailure,'excluded_source'):
                        m.acquire([car],[car['id']],self.root/'excluded',cache=self.root/'missing',minimum_free=0,opener=lambda *a,**k:self.fail('excluded acquisition used network'))
                    self.assertFalse((self.root/'excluded').exists())
    def test_active_inventory_filters_exclusions_but_retains_raw_catalog_and_traffic(self):
        traffic=dict(self.car,id='midnight-club-los-angeles/va_fixture',game='midnight-club-los-angeles',file='midnight-club-los-angeles/va_fixture.glb')
        cars=[self.car,traffic]+[dict(self.car,id=family+'/car',game=family,file=family+'/car.glb') for family in ('gran-turismo','redline')]
        path=self.root/'catalog.json';path.write_text(json.dumps({'cars':cars}));digest=hashlib.sha256(path.read_bytes()).hexdigest()
        self.assertEqual(len(m.load_catalog(path,digest)),4)
        inventory=m.inventory(cars);self.assertEqual(inventory['models'],2);self.assertNotIn('redline',inventory['families']);self.assertNotIn('gran-turismo',inventory['families'])
        with patch('sys.stdout',new_callable=io.StringIO) as output:
            self.assertEqual(m.main(['inventory','--catalog',str(path),'--catalog-sha256',digest,'--commit',m.COMMIT]),0)
            self.assertEqual(json.loads(output.getvalue())['models'],2)
        result=m.acquire(cars,[traffic['id']],self.root/'traffic',minimum_free=0,opener=lambda *a,**k:io.BytesIO(self.data))
        self.assertEqual(result[0]['acquisition']['status'],'verified-download')
    def test_non_glb_rejected_despite_hash(self):
        self.data=b'x'*self.car['bytes']; self.car['sha256']=hashlib.sha256(self.data).hexdigest()
        result=self.run_import(opener=lambda *a,**k:io.BytesIO(self.data))
        self.assertEqual(result['acquisition']['error_code'],'unsupported_glb')

    def test_incomplete_http_retains_receipt(self):
        class Broken(io.BytesIO):
            def read1(self, size): raise IncompleteRead(b'partial')
        result=self.run_import(opener=lambda *a,**k:Broken())
        self.assertEqual(result['acquisition']['error_code'],'transport_or_storage_failure')
        self.assertEqual(len(list((self.root/'store/receipts').glob('*.json'))),1)
    def test_cleanup_failure_retains_receipt(self):
        original=Path.unlink
        def refuse(path, *args, **kwargs):
            if path.name.startswith('.import-'): raise OSError('synthetic')
            return original(path,*args,**kwargs)
        with patch.object(Path,'unlink',refuse):
            result=self.run_import(opener=lambda *a,**k:io.BytesIO(self.data))
        self.assertEqual(result['acquisition']['error_code'],'temporary_cleanup_failed')
        self.assertEqual(len(list((self.root/'store/receipts').glob('*.json'))),1)
    def test_storage_failure_retains_receipt(self):
        with patch.object(m.os,'fsync',side_effect=OSError('synthetic')):
            result=self.run_import(opener=lambda *a,**k:io.BytesIO(self.data))
        self.assertEqual(result['acquisition']['status'],'failed')
        self.assertEqual(list((self.root/'store/objects').iterdir()),[])
    def test_malformed_metadata(self):
        self.car['native_package']={'bytes':'oops'}
        path=self.root/'c.json'; path.write_text(json.dumps({'cars':[self.car]}))
        with self.assertRaises(m.ImportFailure): m.load_catalog(path,hashlib.sha256(path.read_bytes()).hexdigest())
    def test_missing_json_chunk(self):
        data=struct.pack('<4sIIII',b'glTF',2,20,0,0x004e4942)
        self.car.update(bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
        result=self.run_import(opener=lambda *a,**k:io.BytesIO(data))
        self.assertEqual(result['acquisition']['error_code'],'invalid_glb_json')

if __name__=='__main__': unittest.main()
