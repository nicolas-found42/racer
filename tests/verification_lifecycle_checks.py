"""Headless failure provenance checks; never launches Racer or touches real profiles."""
import contextlib
import io
import json
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from verification_lifecycle import VerificationLifecycle, MAX_BYTES
import verification_lifecycle as lifecycle_module

class Checks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
    def tearDown(self): self.temp.cleanup()
    def read(self, out): return json.loads((out/'lifecycle.json').read_text())
    def invoke(self, name, out, *args):
        with patch.object(sys, 'argv', [name, str(out), *map(str,args)]), contextlib.redirect_stdout(io.StringIO()):
            return runpy.run_path(str(ROOT/'scripts'/name), run_name='__main__')

    def test_spawn_timeout_conversion_retain_distinct_outcomes(self):
        for case in ('spawn', 'timeout', 'conversion'):
            with self.subTest(case=case):
                out=self.root/case
                def fake_run(*args, **kwargs):
                    if case=='spawn': raise FileNotFoundError(2, 'PRIVATE_SECRET_PATH')
                    if case=='timeout': raise subprocess.TimeoutExpired(['SECRET_COMMAND'],40)
                    (out/'broken.ppm').write_bytes(b'invalid capture')
                    return subprocess.CompletedProcess([],0)
                with patch('subprocess.run',side_effect=fake_run), self.assertRaises(Exception):
                    self.invoke('verify_vehicle_motion.py',out)
                row=self.read(out);self.assertEqual(row['status'],'failed')
                self.assertEqual(row['phase'],{'spawn':'spawn','timeout':'process','conversion':'capture'}[case])
                self.assertEqual(row['processes'][0]['status'],{'spawn':'spawn_failed','timeout':'timeout','conversion':'returned'}[case])
                self.assertNotIn('SECRET',json.dumps(row));self.assertNotIn(str(self.root),json.dumps(row))
                self.assertTrue((out/'actions.txt').exists())
                if case=='conversion':self.assertTrue((out/'broken.ppm').exists());self.assertEqual(row['processes'][0]['exit'],0)

    def test_motion_success_and_failed_checks_remain_native_policy(self):
        try: from PIL import Image
        except ImportError: self.skipTest('Pillow unavailable; native scripts require it')
        for good in (True,False):
            out=self.root/str(good);exe=self.root/'fixture-exe';exe.write_bytes(b'not executable')
            def fake_run(*args,**kwargs):
                for i in range(7):Image.new('RGB',(2,2)).save(out/(str(i)+'.ppm'))
                history=out/'history';history.mkdir()
                events=[{'event':'wheel_pose'}]
                if good:
                    events += [{'event':'motion','heading':h,'effective_steer':h,'speed':s,'travel':0,'orientation_error':0} for h,s in [(1,1),(-1,-1),(0,0)]]
                (history/'fixture.jsonl').write_text(''.join(json.dumps(e)+'\n' for e in events))
                return subprocess.CompletedProcess([],0)
            with patch('subprocess.run',side_effect=fake_run), self.assertRaises(SystemExit) as caught:
                self.invoke('verify_vehicle_motion.py',out,'--binary',exe)
            self.assertEqual(caught.exception.code,0 if good else 1)
            self.assertEqual(self.read(out)['status'],'completed' if good else 'failed')
            self.assertEqual(json.loads((out/'manifest.json').read_text())['all_verified'],good)

    def test_features_and_diagnostics_spawn_failures_after_snapshot(self):
        def snapshot(root,exe,destination):
            path=destination/'runtime/racer';path.parent.mkdir(parents=True);path.write_bytes(b'fixture')
            return {'issues':[]}
        for name in ('verify_features.py','verify_diagnostics.py'):
            out=self.root/name
            with patch('preserve_build.snapshot',side_effect=snapshot), patch('subprocess.run',side_effect=FileNotFoundError(2,'secret')), patch('subprocess.Popen',side_effect=FileNotFoundError(2,'secret')), self.assertRaises(FileNotFoundError):
                self.invoke(name,out)
            self.assertEqual(self.read(out)['error_code'],'spawn_failed')
            self.assertEqual(self.read(out)['processes'][0]['status'],'spawn_failed')
            self.assertTrue((out/'manifest.json').exists()) # old schema preserved too

    def test_features_conversion_and_retrieval_failures_override_native_finished(self):
        def snapshot(root, exe, destination):
            path=destination/'runtime/racer';path.parent.mkdir(parents=True);path.write_bytes(b'fixture')
            return {'issues':[]}
        for case in ('conversion','retrieval'):
            out=self.root/case
            def fake_run(command, **kwargs):
                if command[0]=='python3': raise subprocess.TimeoutExpired(['private query'],1)
                if case=='conversion': (out/'720/broken.ppm').write_bytes(b'not an image')
                return subprocess.CompletedProcess(command,0)
            with patch('preserve_build.snapshot',side_effect=snapshot), patch('subprocess.run',side_effect=fake_run), self.assertRaises(Exception):
                self.invoke('verify_features.py',out)
            row=self.read(out);self.assertEqual(row['status'],'failed')
            self.assertEqual(row['phase'],'capture' if case=='conversion' else 'retrieval')
            self.assertEqual(json.loads((out/'manifest.json').read_text())[0]['status'],'finished')
            if case=='retrieval':self.assertEqual(row['processes'][-1]['kind'],'retrieval');self.assertTrue(row['processes'][-1]['timeout'])

    def test_selection_preflight_failure_has_no_false_process(self):
        out=self.root/'selection'
        with patch('install_cars.regular_bytes',side_effect=PermissionError(13,'secret')), self.assertRaises(PermissionError):
            self.invoke('verify_vehicle_selection.py',out)
        row=self.read(out);self.assertEqual(row['phase'],'retrieval');self.assertEqual(row['errno'],13)
        self.assertEqual(row['active_input'],'catalog');self.assertIsNone(row['descriptor_index'])
        self.assertNotIn('secret',json.dumps(row))
        self.assertEqual(row['processes'],[])

    def test_recording_failure_preserves_original_exception_and_old_json(self):
        out=self.root/'write';out.mkdir();error=ValueError('original private contents')
        with self.assertRaises(ValueError) as caught:
            with VerificationLifecycle(out) as life:
                before=(out/'lifecycle.json').read_bytes()
                with patch.object(lifecycle_module.os,'replace',side_effect=OSError(28,'private disk')):
                    life.phase('capture')
                    self.assertEqual((out/'lifecycle.json').read_bytes(),before)
                    self.assertFalse((out/'.lifecycle.tmp').exists())
                    raise error
        self.assertIs(caught.exception,error)
        row=self.read(out);self.assertEqual(row['error_code'],'invalid_data');self.assertGreater(row['diagnostic_write_failures'],0)
        self.assertNotIn('private',json.dumps(row))

    def test_checkpoint_persists_context_without_phase_change_and_fails_open(self):
        out=self.root/'checkpoint';out.mkdir()
        with VerificationLifecycle(out) as life:
            life.phase('capture');life.record['active_model']='first'
            life.checkpoint();self.assertEqual(self.read(out)['active_model'],'first')
            life.record['active_model']='second';life.phase('capture')
            self.assertEqual(self.read(out)['active_model'],'first')
            life.checkpoint();self.assertEqual(self.read(out)['active_model'],'second')
            with patch.object(lifecycle_module.os,'replace',side_effect=OSError(28,'PRIVATE_SECRET')):
                life.record['active_model']=None;life.checkpoint()
            self.assertEqual(self.read(out)['active_model'],'second')
            self.assertGreater(life.record['diagnostic_write_failures'],0)
        row=self.read(out);self.assertIsNone(row['active_model'])
        self.assertEqual(row['status'],'completed');self.assertNotIn('PRIVATE_SECRET',json.dumps(row))

    def test_process_cap_phase_guard_and_caller_cleanup_observed(self):
        out=self.root/'bounded';out.mkdir()
        class Process:
            pid=321;returncode=None
            def poll(self):return self.returncode
        proc=Process()
        with VerificationLifecycle(out) as life:
            with patch.object(life,'_write',wraps=life._write) as write:
                for _ in range(100):life.phase('capture')
                self.assertEqual(write.call_count,1)
            with patch.object(lifecycle_module.subprocess,'run',return_value=subprocess.CompletedProcess([],0)):
                for _ in range(70):life.run(['PRIVATE_COMMAND'])
            with patch.object(lifecycle_module.subprocess,'Popen',return_value=proc):life.popen(['PRIVATE_COMMAND'])
            proc.returncode=-9 # owner, not diagnostic helper, terminates process
            life.process_done(proc,timed_out=True)
        row=self.read(out);self.assertEqual(len(row['processes']),64);self.assertEqual(row['omitted_processes'],7)
        self.assertLess((out/'lifecycle.json').stat().st_size,MAX_BYTES)
        self.assertNotIn('PRIVATE',json.dumps(row))

    def test_retrieval_timeout_never_relabels_completed_native_process(self):
        # Check both explicit completion and a process finished before the next
        # subprocess starts; retrieval owns its own timeout in either case.
        for reported in (False,True):
            out=self.root/('retrieval-'+str(reported));out.mkdir()
            class Process:
                pid=123;returncode=0
                def poll(self):return self.returncode
            proc=Process()
            with self.assertRaises(subprocess.TimeoutExpired):
                with VerificationLifecycle(out) as life:
                    with patch.object(lifecycle_module.subprocess,'Popen',return_value=proc):life.popen(['native'])
                    if reported:life.process_done(proc)
                    with patch.object(lifecycle_module.subprocess,'run',side_effect=subprocess.TimeoutExpired(['private'],1)):
                        life.run(['query'],kind='retrieval',timeout=1)
            row=self.read(out)
            self.assertEqual(row['status'],'failed');self.assertEqual(row['phase'],'retrieval')
            self.assertEqual(row['processes'][0]['status'],'returned');self.assertEqual(row['processes'][0]['exit'],0)
            self.assertFalse(row['processes'][0]['timeout']);self.assertTrue(row['processes'][1]['timeout'])

    def test_popen_timeout_keeps_exit_and_does_not_suppress_error(self):
        out=self.root/'popen';out.mkdir()
        class Process:
            pid=123;returncode=None
            def poll(self):return self.returncode
        proc=Process()
        with self.assertRaises(TimeoutError):
            with VerificationLifecycle(out) as life:
                with patch.object(lifecycle_module.subprocess,'Popen',return_value=proc):life.popen(['private'])
                proc.returncode=-9
                raise TimeoutError('private')
        row=self.read(out);self.assertEqual(row['error_code'],'timeout');self.assertEqual(row['processes'][0]['exit'],-9);self.assertTrue(row['processes'][0]['timeout'])

if __name__=='__main__':unittest.main()
