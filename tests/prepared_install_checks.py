import contextlib,hashlib,io,json,sys,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import install_prepared_cars as local
import car_install_checks as fixture_module

class LocalInstall(unittest.TestCase):
    def setUp(self):
        self.f=fixture_module.Checks();self.f.setUp();self.addCleanup(self.f.tearDown);self.f.install()
        self.root=self.f.root;self.validator=self.root/'validator';self.validator.write_bytes(b'fixture validator')
        car=self.f.cars[1];raw=self.f.assets[car['file']];mesh,desc,r=local.common.gt4.prepare(raw,car['id'],'fixture2')
        self.prepared=self.root/'prepared';self.prepared.mkdir();self.descriptor=self.prepared/(r['prepared_sha256']+'.vehicle');self.descriptor.write_text(desc);self.descriptor.with_suffix('.glb').write_bytes(mesh)
        self.row={'model_id':car['id'],'source_sha256':car['sha256'],'role':'player','player_eligible':True,'prepared_sha256':r['prepared_sha256'],'descriptor_sha256':hashlib.sha256(desc.encode()).hexdigest(),'descriptor':str(self.descriptor),'canonical':None}
        self.inventory=self.root/'inventory.json';self.write()
    def write(self):self.inventory.write_text(json.dumps({'vehicles':[self.row]}))
    def publish(self,ok=True):
        with patch.object(local.subprocess,'run',return_value=SimpleNamespace(returncode=0 if ok else 1,stdout='native result',stderr='')):
            return local.publish(self.root/'store',self.inventory,[self.row['model_id']],self.validator)
    def test_publish_and_resume_with_shared_installer(self):
        self.assertEqual(self.publish()['status'],'installed');self.assertEqual(self.publish()['status'],'installed')
        self.row['eligibility_reason']='additional review context';self.write()
        self.assertEqual(self.publish()['status'],'installed')
        self.assertEqual(self.f.install()['catalog']['entries'],2)
    def test_historical_review_bytes_survive_curated_file_changes(self):
        proof=self.root/'review.json';proof.write_text('{"review":"first"}')
        self.row['review_evidence']={'fit':str(proof)};self.write();old_inventory=self.inventory.read_bytes();old_proof=proof.read_bytes()
        first=self.publish();self.assertEqual(first['status'],'installed')
        proof.write_text('{"review":"second"}');self.row['eligibility_reason']='updated evidence';self.write()
        second=self.publish();self.assertEqual(second['status'],'installed');self.assertEqual(first['catalog']['sha256'],second['catalog']['sha256'])
        cache=self.root/'store/carmodels'
        self.assertEqual((cache/first['inventory_snapshot']).read_bytes(),old_inventory)
        self.assertEqual((cache/first['review_evidence'][0]['snapshot']).read_bytes(),old_proof)
        self.assertEqual((cache/second['inventory_snapshot']).read_bytes(),self.inventory.read_bytes())
        self.assertEqual((cache/second['review_evidence'][0]['snapshot']).read_bytes(),proof.read_bytes())
    def test_missing_review_evidence_cannot_publish(self):
        catalog=self.root/'store/vehicles/catalog.racer';old=catalog.read_bytes()
        self.row['review_evidence']={'fit':str(self.root/'missing.json')};self.write()
        with patch.object(local.subprocess,'run') as native:
            with self.assertRaises(FileNotFoundError):local.publish(self.root/'store',self.inventory,[self.row['model_id']],self.validator)
            native.assert_not_called()
        self.assertEqual(catalog.read_bytes(),old)
    def test_native_validation_failure_retains_original_catalog(self):
        p=self.root/'store/vehicles/catalog.racer';old=p.read_bytes();r=self.publish(False)
        self.assertEqual(r['error'],'native_validation_failed');self.assertEqual(p.read_bytes(),old)
        self.assertFalse((self.root/'store/carmodels/install.lock').exists())
    def test_role_conflict_modified_input_and_foreign_lock(self):
        self.row['player_eligible']=False;self.write()
        with self.assertRaises(local.common.InstallError):self.publish()
        self.row['player_eligible']=True;self.write();self.descriptor.write_text('changed')
        with self.assertRaisesRegex(local.common.InstallError,'reviewed_input_changed'):self.publish()
        # Restore verified input before testing a foreign cooperative lock.
        car=self.f.cars[1];mesh,text,_=local.common.gt4.prepare(self.f.assets[car['file']],car['id'],'fixture2');self.descriptor.write_text(text)
        lock=self.root/'store/carmodels/install.lock';lock.write_text('foreign')
        with self.assertRaises(FileExistsError):self.publish()
        self.assertEqual(lock.read_text(),'foreign')
    def test_duplicate_inventory_cannot_hide_missing_requested_model(self):
        self.inventory.write_text(json.dumps({'vehicles':[self.row,self.row]}))
        with self.assertRaisesRegex(local.common.InstallError,'duplicate_inventory_model'):
            local.publish(self.root/'store',self.inventory,[self.row['model_id'],'missing/model'],self.validator)
    def test_inventory_player_flags_cannot_override_source_exclusions(self):
        catalog=self.root/'store/vehicles/catalog.racer';old=catalog.read_bytes()
        before={p.name for p in (self.root/'store/vehicles').iterdir()}
        for model,reason in [('gran-turismo/fixture','not_player_eligible'),('redline/fixture','not_player_eligible'),('midnight-club-los-angeles/va_350z_04','traffic_not_player'),('midnight-club-los-angeles/vp_fake','unreviewed_mcla_player_source'),(local.mcla_player.ID,'unreviewed_mcla_player_source')]:
            with self.subTest(model=model):
                self.row.update(model_id=model,role='player',player_eligible=True);self.write()
                with patch.object(local.subprocess,'run') as validator:
                    with self.assertRaisesRegex(local.common.InstallError,reason):
                        local.publish(self.root/'store',self.inventory,[model],self.validator)
                    validator.assert_not_called()
                self.assertEqual(catalog.read_bytes(),old)
                self.assertEqual({p.name for p in (self.root/'store/vehicles').iterdir()},before)
                self.assertFalse((self.root/'store/carmodels/install.lock').exists())
    def test_validator_over_deadline_keeps_original_catalog(self):
        catalog=self.root/'store/vehicles/catalog.racer';old=catalog.read_bytes();clock=[0]
        def validator(*args,**kwargs):
            self.assertLessEqual(kwargs['timeout'],60);clock[0]=181
            return SimpleNamespace(returncode=0,stdout='late valid result',stderr='')
        with patch.object(local.time,'monotonic',side_effect=lambda:clock[0]),patch.object(local.subprocess,'run',side_effect=validator):
            result=local.publish(self.root/'store',self.inventory,[self.row['model_id']],self.validator)
        self.assertEqual(result['status'],'failed');self.assertEqual(result['error'],'operation_deadline');self.assertEqual(catalog.read_bytes(),old)
    def test_adaptation_requirement_needs_mesh_bound_review_resolution(self):
        row=self.row
        with patch.dict(local.common.source.PLAYER_SOURCE_REQUIREMENTS,{row['source_sha256']:(row['model_id'],'source_pose_fixture')}):
            with self.assertRaisesRegex(local.common.InstallError,'unresolved_source_requirement'):self.publish()
            row['resolved_source_requirements']={'source_pose_fixture':{'prepared_sha256':'0'*64,'evidence':'fixture review'}};self.write()
            with self.assertRaisesRegex(local.common.InstallError,'unresolved_source_requirement'):self.publish()
            row['resolved_source_requirements']['source_pose_fixture']['prepared_sha256']=row['prepared_sha256'];self.write()
            self.assertEqual(self.publish()['status'],'installed')
    def test_source_alias_or_inventory_hash_edit_cannot_clear_requirement(self):
        row=self.row
        with patch.dict(local.common.source.PLAYER_SOURCE_REQUIREMENTS,{row['source_sha256']:(row['model_id'],'source_pose_fixture')}):
            row['model_id']='gran-turismo-4/alias';self.write()
            with self.assertRaisesRegex(local.common.InstallError,'unresolved_source_requirement'):self.publish()
            row['source_sha256']='0'*64;self.write()
            with self.assertRaisesRegex(local.common.InstallError,'descriptor_source_identity'):self.publish()
    def test_reviewed_upgrade_replaces_source_revision_and_preserves_history(self):
        # Upgrade the first entry: remove+append would visibly reorder Garage.
        self.assertEqual(self.f.install([self.f.cars[1]['id']])['status'],'installed')
        car=self.f.cars[0]
        mesh,desc,r=local.common.gt4.prepare(self.f.assets[car['file']],car['id'],car['display_name'])
        self.descriptor=self.prepared/(r['prepared_sha256']+'.vehicle')
        self.descriptor.write_text(desc);self.descriptor.with_suffix('.glb').write_bytes(mesh)
        self.row.update(model_id=car['id'],source_sha256=car['sha256'],prepared_sha256=r['prepared_sha256'],descriptor=str(self.descriptor),descriptor_sha256=hashlib.sha256(desc.encode()).hexdigest());self.write()
        baseline=self.root/'store/vehicles/catalog.racer';baseline_sha=local.common.sha(baseline.read_bytes())
        baseline_sources=[e['source_id'] for e in json.loads((self.root/'store/carmodels/catalogs'/(baseline_sha+'.json')).read_text())['entries']]
        self.assertEqual(self.publish()['status'],'installed')
        catalog=self.root/'store/vehicles/catalog.racer';old=catalog.read_bytes();oldsha=local.common.sha(old)
        old_sources=[e['source_id'] for e in json.loads((self.root/'store/carmodels/catalogs'/(oldsha+'.json')).read_text())['entries']]
        self.assertEqual(old_sources,baseline_sources,'first-entry preparation changed Garage cycle order')
        oldmesh=self.row['prepared_sha256'];mesh=self.descriptor.with_suffix('.glb');raw=mesh.read_bytes()
        # Distinct valid GLB preparation metadata creates a new mesh identity.
        doc,binary=local.common.gt4.unpack(raw);doc.setdefault('extras',{})['reviewed_revision']=2
        prepared=local.common.gt4.pack(doc,binary);sha=hashlib.sha256(prepared).hexdigest()
        text=self.descriptor.read_text().replace(oldmesh,sha)
        self.descriptor=self.prepared/(sha+'.vehicle');self.descriptor.write_text(text);self.descriptor.with_suffix('.glb').write_bytes(prepared)
        self.row.update(prepared_sha256=sha,descriptor=str(self.descriptor),descriptor_sha256=hashlib.sha256(text.encode()).hexdigest());self.write()
        result=self.publish();self.assertEqual(result['status'],'installed');self.assertEqual(result['catalog']['entries'],2)
        new_sources=[e['source_id'] for e in json.loads((self.root/'store/carmodels/catalogs'/(result['catalog']['sha256']+'.json')).read_text())['entries']]
        self.assertEqual(new_sources,old_sources,'reviewed upgrade changed Garage cycle order')
        self.assertNotIn(oldmesh,catalog.read_text());self.assertIn(sha,catalog.read_text())
        self.assertTrue((self.root/'store/vehicles'/(oldmesh+'.glb')).exists())
        self.assertEqual((self.root/'store/carmodels/catalogs'/(oldsha+'.racer')).read_bytes(),old)
if __name__=='__main__':unittest.main()
