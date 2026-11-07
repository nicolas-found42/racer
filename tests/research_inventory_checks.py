#!/usr/bin/env python3
"""Synthetic identity/policy checks. Fixture meshes intentionally test hashes, not native geometry."""
import copy,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import register_research_preparations as r


class Checks(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name).resolve()
        self.source='a'*64;self.mesh=b'bounded fixture mesh; not a renderer-valid GLB';self.meshsha=r.common.sha(self.mesh)
        (self.root/(self.meshsha+'.glb')).write_bytes(self.mesh)
        self.desc=self.root/(self.meshsha+'.vehicle')
        self.desc.write_text('\n'.join(['RACER_VEHICLE 1','id "vehicle-'+self.meshsha+'"','name "Fixture"','mesh "'+self.meshsha+'.glb"','sha256 '+self.meshsha,'source_sha256 '+self.source,'body -1 0.1 -2 1 1 2','wheel FL -0.8 0.3 1 0.3 0.2','wheel FR 0.8 0.3 1 0.3 0.2','wheel RL -0.8 0.3 -1 0.3 0.2','wheel RR 0.8 0.3 -1 0.3 0.2','groups 5','group 0 -1','group 1 0','group 2 1','group 3 2','group 4 3'])+'\n')
        self.evidence=self.root/'proof.json';self.evidence.write_text('{"fixture":true}')
        catalog={'cars':[{'id':game+'/'+code,'game':game,'sha256':self.source}for game,code in [('ford-racing-2','TEST'),('midnight-club-los-angeles','va_TEST'),('gran-turismo','simulation/NESTED'),('redline','TEST')]]}
        self.catalog=self.root/'catalog.json';self.catalog.write_text(json.dumps(catalog))
        self.patches=[patch.object(r,'CATALOG',self.catalog),patch.object(r,'CATALOG_SHA',r.common.sha(self.catalog.read_bytes()))]
        for p in self.patches:p.start()
        self.original={'schema':1,'units':'metres','vehicles':[{'model_id':'ford-racing-2/EXISTING','role':'player','player_eligible':True,'opaque_preserved':{'custom':[3,2,1]}},{'model_id':'midnight-club-los-angeles/va_OLD','role':'traffic','player_eligible':False}],'other_metadata':'preserve me'}
        self.row={'model_id':'ford-racing-2/TEST','descriptor':self.desc.name,'expected_mesh_sha256':self.meshsha,'expected_descriptor_sha256':r.common.sha(self.desc.read_bytes()),'expected_source_sha256':self.source,'source_kind':'public-catalog','evidence':[{'path':'proof.json','sha256':r.common.sha(self.evidence.read_bytes())}],'limits':['Fixture source proof is not runtime certification.']}
    def tearDown(self):
        for p in reversed(self.patches):p.stop()
        self.tmp.cleanup()
    def inputs(self,row=None,inventory=None):
        return json.dumps(self.original if inventory is None else inventory).encode(),json.dumps({'schema':1,'preparations':[self.row if row is None else row]}).encode()
    def prepare(self,row=None,inventory=None):return r.prepare_inventory(*self.inputs(row,inventory),root=self.root)

    def test_new_row_forced_research_and_existing_rows_preserved(self):
        raw,report=self.prepare();d=json.loads(raw);self.assertEqual(d['vehicles'][:2],self.original['vehicles']);self.assertEqual(d['other_metadata'],'preserve me')
        new=d['vehicles'][-1];self.assertIs(new['player_eligible'],False);self.assertEqual(new['role'],'research-candidate');self.assertIsNone(new['canonical'])
        self.assertEqual(new['measured']['wheelbase'],2);self.assertEqual(new['source_sha256'],self.source)
        self.assertEqual(report['added_rows'],1);self.assertEqual(len(report['evidence_files']),1)
        self.assertEqual(new['review_evidence_identity'][0]['sha256'],self.row['evidence'][0]['sha256'])

    def test_existing_identity_idempotence_and_conflicts_never_replace(self):
        first,_=self.prepare();same,report=r.prepare_inventory(first,self.inputs()[1],root=self.root)
        self.assertEqual(first,same);self.assertEqual(report['outcomes'][0]['status'],'already_registered')
        inventory=copy.deepcopy(self.original);old={'model_id':self.row['model_id'],'source_sha256':'b'*64,'prepared_sha256':'c'*64,'descriptor_sha256':'d'*64,'player_eligible':True,'role':'player'};inventory['vehicles'].append(old)
        raw,report=self.prepare(inventory=inventory);self.assertEqual(raw,self.inputs(inventory=inventory)[0]);self.assertEqual(json.loads(raw),inventory)
        outcome=report['outcomes'][0];self.assertEqual(outcome['status'],'conflict_preserved');self.assertEqual(set(outcome['differing_identity_fields']),{'source_sha256','prepared_sha256','descriptor_sha256'})

    def test_excluded_ambient_and_local_namespace_guards(self):
        for ident,kind,code in [('gran-turismo/TEST','public-catalog','excluded_source'),('redline/TEST','public-catalog','excluded_source'),('midnight-club-los-angeles/va_TEST','public-catalog','ambient_traffic'),('ford-racing-2/TEST','local-juiced-2','local_source_family')]:
            row=copy.deepcopy(self.row);row.update(model_id=ident,source_kind=kind)
            with self.subTest(ident=ident),self.assertRaisesRegex(ValueError,code):self.prepare(row)
        row=copy.deepcopy(self.row);row.update(model_id='juiced-2/LOCAL',source_kind='local-juiced-2')
        raw,_=self.prepare(row);self.assertEqual(json.loads(raw)['vehicles'][-1]['source_authority']['kind'],'local-juiced-2')

    def test_catalog_and_descriptor_source_mismatch_rejected(self):
        row=copy.deepcopy(self.row);row['expected_source_sha256']='b'*64
        with self.assertRaisesRegex(ValueError,'public_source_join'):self.prepare(row)
        self.desc.write_text(self.desc.read_text().replace('source_sha256 '+self.source,'source_sha256 '+'b'*64));self.row['expected_descriptor_sha256']=r.common.sha(self.desc.read_bytes())
        with self.assertRaisesRegex(ValueError,'descriptor_source_mismatch'):self.prepare()

    def test_mesh_descriptor_evidence_hashes_are_actually_checked(self):
        for field,reason in [('expected_descriptor_sha256','descriptor_hash'),('evidence','evidence_hash')]:
            row=copy.deepcopy(self.row)
            if field=='evidence':row[field][0]['sha256']='0'*64
            else:row[field]='0'*64
            with self.assertRaisesRegex(ValueError,reason):self.prepare(row)
        self.desc.with_suffix('.glb').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'mesh_hash'):self.prepare()

    def test_unknown_fields_duplicates_and_nonfinite_json_rejected(self):
        for key in ('player_eligible','canonical','misspelled_limit'):
            row=copy.deepcopy(self.row);row[key]=True
            with self.assertRaisesRegex(ValueError,'selection_row_fields'):self.prepare(row)
        a,b=self.inputs();s=json.loads(b);s['preparations']*=2
        with self.assertRaisesRegex(ValueError,'duplicate_selection_id'):r.prepare_inventory(a,json.dumps(s).encode(),root=self.root)
        for value in (b'{"schema":1,"schema":1}',b'{"bad":NaN}',b'{"bad":1e999}'):
            with self.assertRaises(ValueError):r.prepare_inventory(value,b,root=self.root)

    def test_nonfinite_descriptor_and_oversize_are_rejected(self):
        self.desc.write_text(self.desc.read_text().replace('body -1 0.1','body nan 0.1'));self.row['expected_descriptor_sha256']=r.common.sha(self.desc.read_bytes())
        with self.assertRaisesRegex(ValueError,'nonfinite'):self.prepare()
        a,b=self.inputs()
        with patch.object(r.inventory_format,'MAX_BYTES',len(a)-1),self.assertRaisesRegex(ValueError,'inventory_byte_budget'):r.prepare_inventory(a,b,root=self.root)
        with self.assertRaisesRegex(ValueError,'json_input_budget'):r.prepare_inventory(a,b+b' '*(r.MAX_SELECTION+1),root=self.root)
        self.desc.write_text(self.desc.read_text().replace('body nan','body -1'));self.row['expected_descriptor_sha256']=r.common.sha(self.desc.read_bytes())
        with patch.object(r,'MAX_MESH',len(self.mesh)-1),self.assertRaisesRegex(ValueError,'file_size'):self.prepare()
        with patch.object(r,'MAX_BATCH',len(a)+len(b)+10),self.assertRaises(ValueError):self.prepare()

    def test_relative_paths_and_symlinks_rejected(self):
        for name in ('../proof.json','/proof.json','./proof.json','a//proof.json'):
            row=copy.deepcopy(self.row);row['evidence'][0]['path']=name
            with self.assertRaisesRegex(ValueError,'relative_path'):self.prepare(row)
        link=self.root/'link.json';link.symlink_to(self.evidence);row=copy.deepcopy(self.row);row['evidence'][0]['path']='link.json'
        with self.assertRaisesRegex(ValueError,'symlink'):self.prepare(row)

    def test_same_read_measurement_and_fresh_atomic_output_no_apply(self):
        inventory,selection=self.inputs();ip=self.root/'inventory.json';sp=self.root/'selection.json';ip.write_bytes(inventory);sp.write_bytes(selection);out=self.root/'output'
        original=r.common.regular_bytes;reads=[]
        def read(path,limit):reads.append(Path(path));return original(path,limit)
        with patch.object(r.common,'regular_bytes',side_effect=read):report=r.register(sp,ip,out,root=self.root)
        self.assertEqual(reads.count(self.desc),1);self.assertEqual(reads.count(self.desc.with_suffix('.glb')),1)
        self.assertEqual(ip.read_bytes(),inventory);self.assertEqual(sp.read_bytes(),selection)
        self.assertEqual(json.loads((out/'lifecycle.json').read_text())['status'],'completed');self.assertFalse(report['in_place_applied'])
        before={p.name:p.read_bytes()for p in out.iterdir()}
        with self.assertRaisesRegex(ValueError,'fresh_output_required'):r.register(sp,ip,out,root=self.root)
        self.assertEqual(before,{p.name:p.read_bytes()for p in out.iterdir()})
        out2=self.root/'second';r.register(sp,out/'inventory.json',out2,root=self.root)
        self.assertEqual((out/'inventory.json').read_bytes(),(out2/'inventory.json').read_bytes())

    def test_validation_failure_retains_inputs_but_never_output_inventory(self):
        row=copy.deepcopy(self.row);row['player_eligible']=True
        inventory,selection=self.inputs(row);ip=self.root/'inventory.json';sp=self.root/'selection.json'
        ip.write_bytes(inventory);sp.write_bytes(selection);out=self.root/'failed'
        with self.assertRaisesRegex(ValueError,'selection_row_fields'):r.register(sp,ip,out,root=self.root)
        self.assertEqual((out/'input-inventory.json').read_bytes(),inventory)
        self.assertEqual((out/'selection.json').read_bytes(),selection)
        self.assertFalse((out/'inventory.json').exists())
        state=json.loads((out/'lifecycle.json').read_text());self.assertEqual(state['status'],'failed')
        self.assertEqual(state['phase'],'validation');self.assertEqual(state['error_code'],'invalid_data')

    def test_missing_input_identifies_read_and_preserves_prior_snapshot(self):
        inventory,selection=self.inputs();ip=self.root/'inventory.json';sp=self.root/'selection.json'
        ip.write_bytes(inventory);sp.write_bytes(selection)
        for missing in ('inventory','selection'):
            with self.subTest(missing=missing):
                out=self.root/('missing-'+missing);absent=self.root/('PRIVATE_MISSING_'+missing)
                with self.assertRaises(FileNotFoundError):
                    r.register(absent if missing=='selection' else sp,
                               absent if missing=='inventory' else ip,out,root=self.root)
                raw=(out/'lifecycle.json').read_text();state=json.loads(raw)
                self.assertEqual(state['active_input'],missing);self.assertEqual(state['phase'],'retrieval')
                self.assertEqual(state['status'],'failed');self.assertEqual(state['error_code'],'io_error');self.assertEqual(state['errno'],2)
                self.assertFalse((out/'inventory.json').exists());self.assertFalse((out/'report.json').exists())
                self.assertFalse((out/'selection.json').exists());self.assertNotIn('PRIVATE_MISSING',raw);self.assertNotIn(str(self.root),raw)
                if missing=='selection':
                    self.assertEqual((out/'input-inventory.json').read_bytes(),inventory)
                    self.assertEqual(state['inventory_sha256'],r.common.sha(inventory))
                else:
                    self.assertFalse((out/'input-inventory.json').exists());self.assertNotIn('inventory_sha256',state)
                self.assertEqual(ip.read_bytes(),inventory);self.assertEqual(sp.read_bytes(),selection)

    def test_late_report_failure_preserves_inputs_and_marks_partial_dry_output(self):
        inventory,selection=self.inputs();ip=self.root/'inventory.json';sp=self.root/'selection.json'
        ip.write_bytes(inventory);sp.write_bytes(selection);out=self.root/'late-failure';immutable=r.common.immutable
        def write(path,data):
            if Path(path).name=='report.json':raise OSError(28,'PRIVATE_REPORT_PATH')
            return immutable(path,data)
        with patch.object(r.common,'immutable',side_effect=write),self.assertRaises(OSError):r.register(sp,ip,out,root=self.root)
        raw=(out/'lifecycle.json').read_text();state=json.loads(raw)
        self.assertEqual(state['status'],'failed');self.assertEqual(state['phase'],'capture');self.assertEqual(state['errno'],28)
        self.assertIsNone(state['active_input']);self.assertIsNone(state['active_model']);self.assertNotIn('PRIVATE_REPORT_PATH',raw)
        self.assertTrue((out/'inventory.json').is_file());self.assertFalse((out/'report.json').exists())
        self.assertEqual((out/'input-inventory.json').read_bytes(),inventory);self.assertEqual((out/'selection.json').read_bytes(),selection)
        self.assertEqual(ip.read_bytes(),inventory);self.assertEqual(sp.read_bytes(),selection)

    def test_unavailable_lifecycle_still_retains_dry_result_and_inputs(self):
        import verification_lifecycle
        inventory,selection=self.inputs();ip=self.root/'inventory.json';sp=self.root/'selection.json'
        ip.write_bytes(inventory);sp.write_bytes(selection);out=self.root/'no-sidecar'
        with patch.object(verification_lifecycle.os,'replace',side_effect=OSError(28,'PRIVATE_SIDECAR_PATH')):
            report=r.register(sp,ip,out,root=self.root)
        self.assertFalse((out/'lifecycle.json').exists());self.assertFalse((out/'.lifecycle.tmp').exists())
        self.assertEqual(json.loads((out/'report.json').read_text()),report)
        self.assertEqual(r.common.sha((out/'inventory.json').read_bytes()),report['inventory_output_sha256'])
        self.assertEqual((out/'input-inventory.json').read_bytes(),inventory);self.assertEqual((out/'selection.json').read_bytes(),selection)
        self.assertEqual(ip.read_bytes(),inventory);self.assertEqual(sp.read_bytes(),selection)
        self.assertNotIn('PRIVATE_SIDECAR_PATH',(out/'report.json').read_text())


if __name__=='__main__':unittest.main()
