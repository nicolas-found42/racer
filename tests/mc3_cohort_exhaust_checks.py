#!/usr/bin/env python3
import copy,importlib.util,json,math,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import mc3_cohort_exhaust as x
from prepare_gt4_vehicle import unpack,Geometry,PreparationError
from vehicle_clearance import descriptor
from fit_vehicle_tracks import frames,positions


def fixtures_available():
    paths=[x.wrapper.READER]+[x.SHARED/n for n in x.SHARED_PINS]
    for c,p in x.PINS.items():
        paths.extend(x.COHORT/'glass-v2'/c/(p['mesh']+ext)for ext in('.glb','.vehicle','.json'))
        paths.extend((x.COHORT/'batch-v1'/c/'source.dat',x.COHORT/'batch-v1'/c/'default.carcfg',x.COHORT/'batch-v2'/c/'main.pck'))
    return all(p.is_file()for p in paths)


def native_matrix(bones,index):
    """Independent Euler rotation matrices and parent composition (producer uses quaternions)."""
    b=bones[index];rx,ry,rz=b['rotation_raw'];cx,sx=math.cos(rx),math.sin(rx);cy,sy=math.cos(ry),math.sin(ry);cz,sz=math.cos(rz),math.sin(rz)
    r=[[cz*cy,cz*sy*sx-sz*cx,cz*sy*cx+sz*sx],
       [sz*cy,sz*sy*sx+cz*cx,sz*sy*cx-cz*sx],[-sy,cy*sx,cy*cx]]
    m=[r[k]+[b['local_position'][k]]for k in range(3)]+[[0,0,0,1]]
    if b['parent']is not None:
        a=native_matrix(bones,b['parent']);m=[[sum(a[i][k]*m[k][j]for k in range(4))for j in range(4)]for i in range(4)]
    return m


class ExhaustChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not fixtures_available():raise unittest.SkipTest('Exact retained cohort/shared sources unavailable')

    def test_actual_vertices_winding_and_all_original_preservation(self):
        total=0
        for code in ('vp_saleen_sr_00','vp_esprit_04'):
            reader=x.reader_module();old,text,receipt,bones,proof=x.source_inputs(code,reader);draws,shared=x.decode(reader,code)
            new,newtext,r=x.attach(old,text,receipt,bones,code,draws,shared)
            a,ab=unpack(old);b,bb=unpack(new);self.assertEqual(ab,bb[:len(ab)])
            fields,wheels,roles=descriptor(text);nf,nw,nr=descriptor(newtext)
            self.assertEqual(wheels,nw);self.assertTrue(all(nr[k]==v for k,v in roles.items()))
            _,aw,_=frames(a,roles);_,bw,_=frames(b,nr);before=positions(a,ab,aw);after=positions(b,bb,bw)
            self.assertTrue(all(before[k]==after[k]for k in before))
            g=Geometry(b,bb);policy=b['extras']['racerCohortExhaustPolicy']
            for attachment in policy['attachments']:
                m=native_matrix(bones,attachment['native_bone']);node=b['nodes'][attachment['node']]
                for draw,p in zip(draws,b['meshes'][node['mesh']]['primitives']):
                    got=g.values(p['attributes']['POSITION']);self.assertEqual(len(got),len(draw['positions']))
                    for v,actual in zip(draw['positions'],got):
                        expected=[sum(m[i][k]*v[k]for k in range(3))+m[i][3]for i in range(3)];expected[2]*=-1
                        self.assertLess(max(abs(actual[k]-expected[k])for k in range(3)),2e-7)
                    ids=draw['indices'][:]
                    for i in range(0,len(ids),3):ids[i+1],ids[i+2]=ids[i+2],ids[i+1]
                    self.assertEqual([v[0]for v in g.values(p['indices'])],ids)
                    self.assertEqual(p['material'],len(a['materials'])+draw['material']);total+=len(got)
            restored=copy.deepcopy(b);del restored['extras']['racerCohortExhaustPolicy']
            for key in('nodes','meshes','materials','accessors','bufferViews'):restored[key]=restored[key][:len(a[key])]
            root=a['scenes'][0]['nodes'][0];restored['nodes'][root]=a['nodes'][root];restored['buffers']=a['buffers']
            self.assertEqual(a,restored)
            body=r['body']
            for i,vs in after.items():
                if nr[i][0]=='body':self.assertTrue(all(all(body[k]-2e-6<=v[k]<=body[k+3]+2e-6 for k in range(3))for v in vs))
            self.assertFalse(r['runtime_player_eligible'])
        self.assertEqual(total,272)

    def test_viper_has_source_geometry_but_no_candidate(self):
        mesh,text,r,proof=x.prepare('vp_viper_03');self.assertIsNone(mesh);self.assertIsNone(text)
        self.assertEqual(proof['status'],'held_no_proven_native_attachment_frame')
        self.assertEqual(proof['shared_exhaust']['name'],'ext03_kng_m643330')
        self.assertEqual(len(proof['native_bones']),48)

    def test_unknown_missing_or_duplicate_anchor_rejected(self):
        code='vp_saleen_sr_00';_,_,_,bones,_=x.source_inputs(code,x.reader_module())
        for mode in('rename','duplicate'):
            changed=copy.deepcopy(bones)
            if mode=='rename':changed[19]['name']='nitro_0'
            else:changed[18]['name']='exhst_0'
            with self.assertRaisesRegex(PreparationError,'named_anchor_contract'):x.anchor_frames(changed,code)
        with self.assertRaisesRegex(PreparationError,'unresolved_native_attachment_anchors'):x.anchor_frames(bones,'vp_viper_03')

    def test_source_and_config_pin_tampering_rejected(self):
        original=x.read_regular
        for filename in('default.carcfg','main.pck','source.dat'):
            def read(path,cap):
                b=original(path,cap);return b+b'X'if Path(path).name==filename else b
            with patch.object(x,'read_regular',side_effect=read),self.assertRaisesRegex(PreparationError,'source_input_pins'):
                x.source_inputs('vp_saleen_sr_00',x.reader_module())

    def test_shared_pin_and_material_profile_rejected(self):
        original=x.read_regular
        def read(path,cap):
            b=original(path,cap);return b+b'X'if Path(path).name=='exhaust.ppf'else b
        with patch.object(x,'read_regular',side_effect=read),self.assertRaisesRegex(PreparationError,'shared_input_pins'):x.decode(x.reader_module(),'vp_esprit_04')
        reader=x.reader_module();u32=reader.Pck.u32
        def wrong(self,at):
            v=u32(self,at);return 123 if v==8042160 else v
        with patch.object(reader.Pck,'u32',wrong),self.assertRaisesRegex(PreparationError,'material_profile'):x.decode(reader,'vp_esprit_04')

    def test_root_mutation_rejected(self):
        code='vp_saleen_sr_00';m,t,r,b,_=x.source_inputs(code,x.reader_module());d,p=x.decode(x.reader_module(),code);r['ground_lift']+=.001
        with self.assertRaisesRegex(PreparationError,'ground_root_contract'):x.attach(m,t,r,b,code,d,p)

    def test_failed_validation_retains_bounded_start_outcome(self):
        with tempfile.TemporaryDirectory(dir=x.OUTPUT)as tmp:
            base=Path(tmp);out=base/'attempt'
            with patch.object(x,'OUTPUT',base),patch.object(x,'prepare',side_effect=ValueError('secret arbitrary text')):
                with self.assertRaises(ValueError):x.run(out)
            raw=(out/'lifecycle.json').read_bytes();record=json.loads(raw)
            self.assertEqual(record['status'],'failed');self.assertEqual(record['error_code'],'invalid_data')
            self.assertIn('requested_sources',record);self.assertNotIn(b'secret',raw);self.assertFalse(list(out.rglob('*.glb')))

    def test_complete_budget_rejects_before_payload_writes(self):
        with tempfile.TemporaryDirectory(dir=x.OUTPUT)as tmp:
            base=Path(tmp);out=base/'attempt'
            with patch.object(x,'OUTPUT',base),patch.object(x,'CAP',70000):
                with self.assertRaisesRegex(PreparationError,'complete_payload_budget'):x.run(out)
            self.assertEqual(json.loads((out/'lifecycle.json').read_text())['status'],'failed')
            self.assertFalse(list(out.rglob('*.glb')))

    def test_payload_failure_is_attributed_before_write_and_manifest_has_no_model(self):
        for target,owner in (('vp_saleen_sr_00/native-proof.json','vp_saleen_sr_00'),('manifest.json',None)):
            with self.subTest(target=target),tempfile.TemporaryDirectory(dir=x.OUTPUT)as tmp:
                base=Path(tmp);out=base/'attempt';seen=[]
                def failed_write(path,data):
                    if path.relative_to(out).as_posix()!=target:return
                    row=json.loads((out/'lifecycle.json').read_text())
                    self.assertEqual(row['active_model'],owner);self.assertEqual(row['phase'],'capture')
                    seen.append(target);raise OSError(28,'PRIVATE_SECRET_PATH')
                with patch.object(x,'OUTPUT',base),patch.object(x,'write',side_effect=failed_write),self.assertRaises(OSError):
                    x.run(out)
                raw=(out/'lifecycle.json').read_text();row=json.loads(raw)
                self.assertEqual(seen,[target]);self.assertEqual(row['active_model'],owner)
                self.assertEqual(row['phase'],'capture');self.assertEqual(row['errno'],28)
                self.assertEqual(row['status'],'failed');self.assertEqual(row['error_code'],'io_error')
                self.assertNotIn('PRIVATE_SECRET',raw);self.assertNotIn(str(base),raw)

    def test_model_directory_failure_has_current_owner_before_mkdir(self):
        with tempfile.TemporaryDirectory(dir=x.OUTPUT)as tmp:
            base=Path(tmp);out=base/'attempt';mkdir=Path.mkdir
            def failed_mkdir(path,*args,**kwargs):
                if path==out/'vp_saleen_sr_00':
                    row=json.loads((out/'lifecycle.json').read_text())
                    self.assertEqual(row['active_model'],'vp_saleen_sr_00')
                    self.assertEqual(row['phase'],'capture')
                    raise OSError(28,'PRIVATE_DIRECTORY')
                return mkdir(path,*args,**kwargs)
            with patch.object(x,'OUTPUT',base),patch.object(Path,'mkdir',failed_mkdir),self.assertRaises(OSError):
                x.run(out)
            raw=(out/'lifecycle.json').read_text();row=json.loads(raw)
            self.assertEqual(row['active_model'],'vp_saleen_sr_00');self.assertEqual(row['errno'],28)
            self.assertNotIn('PRIVATE_DIRECTORY',raw);self.assertFalse(list(out.rglob('*.glb')))


if __name__=='__main__':
    if not fixtures_available():print('SKIP: exact MC3 cohort/shared fixtures unavailable',file=sys.stderr);sys.exit(77)
    unittest.main()
