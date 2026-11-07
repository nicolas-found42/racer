"""Bounded four-model selection staging with synthetic GLBs and no native/GPU work."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock,patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
sys.path.insert(0,str(ROOT/'tests'))
import verify_vehicle_selection as v
from gt4_preparation_checks import fixture
from prepare_gt4_vehicle import pack,prepare


class Checks(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(prefix='racer-selection-');self.addCleanup(temp.cleanup)
        self.root=Path(temp.name).resolve();self.source=self.root/'source';self.source.mkdir()
        self.names=[]
        for i in range(6):
            doc,binary=fixture();doc['extras']['fixture_number']=i;doc['extras']['car']='fixture'+str(i)
            mesh,text,receipt=prepare(pack(doc,binary),'gran-turismo-4/fixture'+str(i),'Fixture '+str(i))
            if i==4:text=text.replace(receipt['source_sha256'],v.TARGET_SOURCE)
            name=receipt['prepared_sha256']+'.vehicle';self.names.append(name)
            (self.source/name).write_text(text);(self.source/Path(name).with_suffix('.glb')).write_bytes(mesh)
        self.catalog=self.source/'catalog.racer';self.catalog.write_text('RACER_VEHICLES 1\n6\n'+''.join(json.dumps(n)+'\n'for n in self.names))
        self.original={p.name:p.read_bytes()for p in self.source.iterdir()}

    def assert_inputs_unchanged(self):
        for name,data in self.original.items():self.assertEqual((self.source/name).read_bytes(),data)

    def run_main(self,out,popen,run):
        binary=self.root/'dummy-binary';binary.write_bytes(b'not executed')
        stage=v.stage_selection
        with patch.object(sys,'argv',['verify_vehicle_selection',str(out),'--binary',str(binary)]),\
             patch.object(v,'stage_selection',side_effect=lambda output,**kw:stage(output,self.source,**kw)),\
             patch.object(v.VerificationLifecycle,'popen',side_effect=popen)as spawn,\
             patch.object(v.VerificationLifecycle,'run',side_effect=run)as reload:
            result=v.main()
        return result,spawn,reload

    def test_only_four_models_staged_with_original_indices_and_pins(self):
        history=self.source/'history';history.mkdir();(history/'unrelated.bin').write_bytes(b'not a scenario input')
        (self.source/Path(self.names[3]).with_suffix('.glb')).unlink()
        (self.source/Path(self.names[5]).with_suffix('.glb')).unlink()
        out=self.root/'out';out.mkdir();models,names,identity=v.stage_selection(out,self.source)
        self.assertEqual(names,[self.names[i]for i in (0,1,2,4)])
        self.assertEqual(identity['original_indices'],[0,1,2,4]);self.assertEqual(identity['target_subset_index'],3)
        self.assertEqual(identity['source_library_sha256'],v.common.sha(self.original['catalog.racer']))
        self.assertEqual(identity['subset_library_sha256'],v.common.sha((models/'catalog.racer').read_bytes()))
        expected_reads=len(self.original['catalog.racer'])+sum(len(self.original[n])for n in self.names[:5])
        expected_reads+=sum(len(self.original[str(Path(self.names[i]).with_suffix('.glb'))])for i in (0,1,2,4))
        self.assertEqual(identity['input_read_bytes'],expected_reads);self.assertEqual(identity['input_read_count'],10)
        self.assertEqual(len(list(models.iterdir())),9);self.assertFalse((models/'history').exists())
        for pin in identity['input_pins']:
            self.assertEqual(v.common.sha((models/pin['descriptor']).read_bytes()),pin['descriptor_sha256'])
            self.assertEqual(v.common.sha((models/(pin['mesh_sha256']+'.glb')).read_bytes()),pin['mesh_sha256'])
        self.assertEqual(self.catalog.read_bytes(),self.original['catalog.racer'])

    def test_catalog_schema_count_paths_and_cap_reject_before_staging(self):
        original=self.catalog.read_bytes();lines=original.decode().splitlines()
        variants=[b'RACER_VEHICLES 1\n3001\n',original.replace(b'\n6\n',b'\n5\n',1),
                  ('\n'.join(lines[:2]+[json.dumps('../escape.vehicle')]+lines[3:])+'\n').encode(),
                  ('\n'.join(lines[:3]+[lines[2]]+lines[4:])+'\n').encode(),b'x'*(v.common.MAX_LIBRARY+1)]
        for i,data in enumerate(variants):
            with self.subTest(i=i):
                self.catalog.write_bytes(data);out=self.root/('bad'+str(i));out.mkdir()
                with patch.object(v.common,'immutable')as write,self.assertRaises(ValueError):v.stage_selection(out,self.source)
                write.assert_not_called();self.assertFalse((out/'models').exists())
        self.catalog.write_bytes(original);self.assert_inputs_unchanged()

    def test_target_source_rejection_precedes_copy_and_native(self):
        path=self.source/self.names[4];path.write_text(path.read_text().replace(v.TARGET_SOURCE,'f'*64))
        out=self.root/'failed'
        with patch.object(v.common,'immutable')as write,\
             patch.object(v.VerificationLifecycle,'popen')as spawn,\
             patch.object(v.VerificationLifecycle,'run')as reload:
            binary=self.root/'dummy';binary.write_bytes(b'not executed');stage=v.stage_selection
            with patch.object(sys,'argv',['verify',str(out),'--binary',str(binary)]),\
                 patch.object(v,'stage_selection',side_effect=lambda output,**kw:stage(output,self.source,**kw)),\
                 self.assertRaisesRegex(ValueError,'selection_target_missing'):v.main()
        write.assert_not_called();spawn.assert_not_called();reload.assert_not_called()
        state=json.loads((out/'lifecycle.json').read_text());self.assertEqual(state['status'],'failed');self.assertEqual(state['phase'],'retrieval')
        self.assertFalse((out/'models').exists());self.assertEqual(self.catalog.read_bytes(),self.original['catalog.racer'])

    def test_descriptor_identity_source_and_symlink_rejections(self):
        path=self.source/self.names[0];original=path.read_text()
        for text in [original.replace(Path(self.names[0]).stem+'.glb','../foreign.glb'),
                     original+'source_sha256 '+'f'*64+'\n',original+'sha256 '+'f'*64+'\n']:
            path.write_text(text)
            with self.assertRaises(ValueError):v.selection_plan(self.source)
        path.write_text(original)
        mesh=path.with_suffix('.glb');data=mesh.read_bytes();mesh.unlink();mesh.symlink_to(self.source/Path(self.names[1]).with_suffix('.glb'))
        with self.assertRaisesRegex(ValueError,'symlink'):v.selection_plan(self.source)
        mesh.unlink();mesh.write_bytes(data);self.assert_inputs_unchanged()

    def test_total_byte_cap_and_corrupt_mesh_reject_before_copy(self):
        total=sum(len(self.original[self.names[i]])+len(self.original[str(Path(self.names[i]).with_suffix('.glb'))])for i in (0,1,2,4))
        out=self.root/'out';out.mkdir()
        with patch.object(v,'MAX_MODEL_BYTES',total-1),patch.object(v.common,'immutable')as write,self.assertRaises(ValueError):v.stage_selection(out,self.source)
        write.assert_not_called();self.assertFalse((out/'models').exists())
        mesh=self.source/Path(self.names[4]).with_suffix('.glb');mesh.write_bytes(b'corrupt')
        with patch.object(v.common,'immutable')as write,self.assertRaisesRegex(ValueError,'selection_mesh_hash'):v.stage_selection(out,self.source)
        write.assert_not_called();self.assertFalse((out/'models').exists())

    def test_staged_bytes_are_the_same_snapshots_that_were_pinned(self):
        plan=v.selection_plan(self.source);out=self.root/'out';out.mkdir()
        # A later source edit must not silently change the already-pinned payload.
        path=self.source/self.names[4];path.write_text('changed after successful plan')
        with patch.object(v,'selection_plan',return_value=plan):models,_,identity=v.stage_selection(out,self.source)
        self.assertEqual((models/self.names[4]).read_bytes(),self.original[self.names[4]])
        self.assertEqual(identity['input_pins'][3]['descriptor_sha256'],v.common.sha(self.original[self.names[4]]))
        path.write_bytes(self.original[self.names[4]]);self.assert_inputs_unchanged()

    def test_aggregate_read_budget_rejects_before_copy_or_native(self):
        out=self.root/'read-budget';native=Mock();reload=Mock()
        budget=len(self.original['catalog.racer'])+len(self.original[self.names[0]])-1
        with patch.object(v,'MAX_READ_BYTES',budget),patch.object(v.common,'immutable')as write,\
             self.assertRaisesRegex(ValueError,'file_size_or_change'):
            self.run_main(out,native,reload)
        write.assert_not_called();native.assert_not_called();reload.assert_not_called()
        state=json.loads((out/'lifecycle.json').read_text())
        self.assertEqual(state['active_input'],'descriptor');self.assertEqual(state['descriptor_index'],0)
        self.assertEqual(state['input_read_bytes'],len(self.original['catalog.racer']));self.assertEqual(state['input_read_count'],2)
        self.assertFalse((out/'models').exists());self.assert_inputs_unchanged()

    def test_missing_scanned_descriptor_retains_index_hash_and_no_paths(self):
        # Index3 is scanned to locate the target, even though its mesh is not selected.
        path=self.source/self.names[3];path.unlink();out=self.root/'missing-descriptor';native=Mock();reload=Mock()
        with patch.object(v.common,'immutable')as write,self.assertRaises(FileNotFoundError):self.run_main(out,native,reload)
        write.assert_not_called();native.assert_not_called();reload.assert_not_called()
        raw=(out/'lifecycle.json').read_text();state=json.loads(raw)
        self.assertEqual(state['phase'],'retrieval');self.assertEqual(state['active_input'],'descriptor')
        self.assertEqual(state['descriptor_index'],3);self.assertEqual(state['expected_mesh_sha256'],Path(self.names[3]).stem)
        self.assertEqual(state['source_library_sha256'],v.common.sha(self.original['catalog.racer']))
        self.assertEqual(state['errno'],2);self.assertNotIn(str(self.root),raw)
        path.write_bytes(self.original[self.names[3]]);self.assert_inputs_unchanged()

    def test_late_publication_failure_records_owner_before_write(self):
        cases=[('selection-inputs.json','plan',None,None),
               (self.names[0],'descriptor',0,Path(self.names[0]).stem),
               (str(Path(self.names[4]).with_suffix('.glb')),'mesh',4,Path(self.names[4]).stem),
               ('catalog.racer','catalog',None,None)]
        immutable=v.common.immutable
        for number,(filename,kind,index,digest) in enumerate(cases):
            with self.subTest(kind=kind):
                out=self.root/('write-failure'+str(number));out.mkdir();seen=[]
                def write(path,data):
                    if Path(path).name==filename:
                        state=json.loads((out/'lifecycle.json').read_text())
                        self.assertEqual(state['publication_kind'],kind);self.assertEqual(state['descriptor_index'],index)
                        self.assertEqual(state['expected_mesh_sha256'],digest);seen.append(kind)
                        raise OSError(28,'PRIVATE_PUBLICATION_PATH')
                    return immutable(path,data)
                with patch.object(v.common,'immutable',side_effect=write),self.assertRaises(OSError):
                    with v.VerificationLifecycle(out)as life:
                        life.phase('retrieval');v.stage_selection(out,self.source,lifecycle=life)
                raw=(out/'lifecycle.json').read_text();state=json.loads(raw)
                self.assertEqual(seen,[kind]);self.assertEqual(state['phase'],'capture');self.assertEqual(state['status'],'failed')
                self.assertEqual(state['errno'],28);self.assertEqual(state['publication_kind'],kind)
                self.assertEqual(state['active_input'],kind if kind in('descriptor','mesh')else None)
                self.assertNotIn('PRIVATE_PUBLICATION_PATH',raw);self.assertNotIn(str(self.root),raw)
        self.assert_inputs_unchanged()

    def test_mocked_scenario_keeps_assertions_and_repairs_only_local_target(self):
        out=self.root/'scenario'
        class Process:
            returncode=0
            def poll(self):return 0
        def native(command,**kwargs):
            for line in (out/'actions.txt').read_text().splitlines():
                if line.startswith('capture '):v.Image.new('RGB',(1,1),(20,30,40)).save(Path(line[8:]))
            return Process()
        def reload(command,**kwargs):
            history=out/'reload/history';history.mkdir()
            (history/'events.jsonl').write_text(json.dumps({'event':'asset_load_end','success':True,'sha256':Path(self.names[4]).stem})+'\n')
            (out/'profile/profile.txt.vehicle').write_text('vehicle-'+Path(self.names[4]).stem)
            return subprocess.CompletedProcess(command,0)
        result,spawn,reloaded=self.run_main(out,native,reload)
        self.assertEqual(result,0);spawn.assert_called_once();reloaded.assert_called_once()
        manifest=json.loads((out/'manifest.json').read_text());self.assertTrue(manifest['verified'])
        self.assertEqual(manifest['original_indices'],[0,1,2,4]);self.assertEqual(manifest['target_subset_index'],3)
        self.assertEqual(len(manifest['captures']),13);self.assertEqual(len(list((out/'models').iterdir())),9)
        self.assertEqual((out/'models'/Path(self.names[4]).with_suffix('.glb')).read_bytes(),self.original[str(Path(self.names[4]).with_suffix('.glb'))])
        script=(out/'actions.txt').read_text()
        for assertion in ('Acura NSX','Nissan 350Z','Ford Mustang','previous car retained','UNSAVED car selection','Car selection saved','Juiced 2 Nissan 350Z','MEASUREMENT: 8.000 s'):
            self.assertIn('assert '+assertion,script)
        self.assert_inputs_unchanged()


if __name__=='__main__':unittest.main()
