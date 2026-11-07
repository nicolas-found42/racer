#!/usr/bin/env python3
"""Offline adversarial cohort checks and independent complete world-position check."""
import copy
import hashlib
import io
import importlib.util
import json
import math
from pathlib import Path
import shlex
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import mc3_cohort as c
import mc3_external_parts as external
from mc3_wheel_contract import resolve
from prepare_gt4_vehicle import Geometry,PreparationError,unpack
BASE=ROOT/'experiments/2026-11-06-mc3-cohort/output'
CODES=('vp_fleetline_49','vp_saleen_sr_00','vp_viper_03','vp_esprit_04')


def fixtures_available():
    paths=[c.wrapper.CATALOG,c.wrapper.INDEX,c.wrapper.READER,BASE/'batch-v2/manifest.json']
    for code in CODES:
        paths += [BASE/'batch-v1'/code/name for name in('source.glb','source.dat','default.carcfg','main.pck')]
        paths += [BASE/'batch-v2'/code/name for name in('status.json','native-proof.json','main.pck')]
        folder=BASE/'batch-v2'/code/'prepared-v1'
        paths.append(folder/'assembled-source.glb')
        try:
            digest=json.loads((folder.parent/'status.json').read_text())['prepared_sha256']
        except (OSError,ValueError,KeyError,TypeError):return False
        paths += [folder/(digest+suffix)for suffix in('.glb','.vehicle','.json')]
    return all(p.is_file()for p in paths)


def cli():
    if not fixtures_available():
        print('SKIP: retained exact MC3 cohort fixtures unavailable',file=sys.stderr)
        return 77
    unittest.main()
    return 0


class FixtureReportingChecks(unittest.TestCase):
    def test_missing_required_fixture_returns_77_without_running_suite(self):
        actual=Path.is_file
        missing=BASE/'batch-v1/vp_viper_03/source.dat'
        with patch.object(Path,'is_file',lambda p:False if p==missing else actual(p)),patch('unittest.main')as runner,patch('sys.stderr',io.StringIO()):
            self.assertFalse(fixtures_available());self.assertEqual(cli(),77);runner.assert_not_called()


def world(node,point):
    x,y,z,w=node.get('rotation',[0,0,0,1]);s=node.get('scale',[1,1,1]);t=node.get('translation',[0,0,0]);v=[point[i]*s[i]for i in range(3)]
    cross=[y*v[2]-z*v[1],z*v[0]-x*v[2],x*v[1]-y*v[0]]
    double=[y*cross[2]-z*cross[1],z*cross[0]-x*cross[2],x*cross[1]-y*cross[0]]
    return [v[i]+2*w*cross[i]+2*double[i]+t[i]for i in range(3)]


def inspect(code):
    source=BASE/'batch-v1'/code;folder=BASE/'batch-v2'/code/'prepared-v1'
    status=json.loads((folder.parent/'status.json').read_text());digest=status['prepared_sha256']
    raw=(folder/(digest+'.glb')).read_bytes();assert hashlib.sha256(raw).hexdigest()==digest
    receipt=json.loads((folder/(digest+'.json')).read_text());lines=[shlex.split(x)for x in(folder/(digest+'.vehicle')).read_text().splitlines()]
    assert next(x[1]for x in lines if x[0]=='source_sha256')==hashlib.sha256((source/'source.glb').read_bytes()).hexdigest()==receipt['source_sha256']
    assert next(x[1]for x in lines if x[0]=='sha256')==digest and next(x[1]for x in lines if x[0]=='mesh')==digest+'.glb'
    original,ob=unpack((source/'source.glb').read_bytes());a,ab=unpack((folder/'assembled-source.glb').read_bytes());d,b=unpack(raw)
    assert ab[:len(ob)]==ob
    assert a['nodes'][:len(original['nodes'])]==original['nodes']
    for key in('materials','images','textures','samplers'):
        assert a.get(key)==original.get(key)==d.get(key)
    ag=Geometry(a,ab);g=Geometry(d,b);lift=receipt['ground_lift'];count=triangles=0;error=0.;body=[];clouds={i:[]for i in range(4)}
    active=a['scenes'][a.get('scene',0)]['nodes'];assert len(active)==len(receipt['groups'])
    assert d['nodes'][-1]=={'name':'racer_ground_lift','translation':[0,lift,0],'children':list(range(len(active)))}
    for i,source_index in enumerate(active):
        node=a['nodes'][source_index];out=d['nodes'][i];assert out['extras']['source_node']==source_index
        assert receipt['groups'][i][0]==i;slot=receipt['groups'][i][1]
        before=a['meshes'][node['mesh']]['primitives'];after=d['meshes'][out['mesh']]['primitives'];assert len(before)==len(after)
        for p,q in zip(before,after):
            assert p['material']==q['material'];ps=ag.values(p['attributes']['POSITION']);qs=g.values(q['attributes']['POSITION']);assert len(ps)==len(qs)
            for v,got in zip(ps,qs):
                w=world(node,v);expected=[w[0],w[1]+lift,-w[2]];got=[got[0],got[1]+lift,got[2]]
                e=max(abs(got[k]-expected[k])for k in range(3));assert e<2e-6;error=max(error,e);count+=1
                (body if slot<0 else clouds[slot]).append(got)
            indices=[v[0]for v in ag.values(p['indices'])];expected=[]
            for k in range(0,len(indices),3):expected.extend((indices[k],indices[k+2],indices[k+1]))
            assert [v[0]for v in g.values(q['indices'])]==expected;triangles+=len(indices)//3
    for p in body:assert all(receipt['body'][k]-2e-6<=p[k]<=receipt['body'][k+3]+2e-6 for k in range(3))
    for i,points in clouds.items():
        w=receipt['wheels'][i];assert points
        for p in points:
            assert abs(p[0]-w['center'][0])<=w['width']/2+2e-6
            assert math.hypot(p[1]-w['center'][1],p[2]-w['center'][2])<=w['radius']+2e-6
    assert receipt['runtime_player_eligible'] is False
    return {'code':code,'prepared_sha256':digest,'world_positions_verified':count,'triangles_verified':triangles,'maximum_position_error':error,'body_and_four_wheel_enclosures':True,'original_binary_prefix_nodes_materials_images_preserved':True,'descriptor_public_source_and_prepared_identity':True}


class Checks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not fixtures_available():raise unittest.SkipTest('retained exact cohort fixtures unavailable')
        cls.rows=c.pinned_rows(CODES)
        assert hashlib.sha256(c.wrapper.READER.read_bytes()).hexdigest()==c.wrapper.READER_SHA
        spec=importlib.util.spec_from_file_location('pinned_test_reader',c.wrapper.READER);cls.reader=importlib.util.module_from_spec(spec);spec.loader.exec_module(cls.reader)
    def fixture(self,code='vp_viper_03'):
        folder=BASE/'batch-v1'/code;d,b=unpack((folder/'source.glb').read_bytes());dat=(folder/'source.dat').read_bytes();native=self.reader.read_vehicle(folder/'main.pck');return folder,d,b,dat,native,c.archive(dat)
    def test_all_actual_world_vertices_and_source_preservation(self):
        for code in CODES:
            with self.subTest(code=code):self.assertGreater(inspect(code)['world_positions_verified'],5000)
    def test_duplicate_and_out_of_scope_selection(self):
        for codes in([CODES[0]]*2,['vp_350z_04'],['vp_skully_01'],['va_traffic'],['../bad'],list(CODES)+['vp_more']):
            with self.assertRaises(PreparationError):c.pinned_rows(codes)
    def test_native_member_offset_or_name_cannot_be_rebound(self):
        folder,d,b,dat,native,members=self.fixture();row=next(r for r in self.rows if r['code']=='vp_viper_03');c.native_member_joins(members,row['members'])
        bad=copy.deepcopy(members);bad[0]['offset']+=4
        with self.assertRaisesRegex(PreparationError,'native_index_range_hash'):c.native_member_joins(bad,row['members'])
        bad=copy.deepcopy(members);bad[0]['name']='unknown'
        with self.assertRaisesRegex(PreparationError,'native_index_name_join'):c.native_member_joins(bad,row['members'])
    def test_raw_bones_and_coupled_orientation_mutation(self):
        folder,d,b,dat,native,members=self.fixture();bones=json.loads(json.dumps(native['skeleton']['bones']));raw=(folder/'main.pck').read_bytes();c.raw_bone_check(raw,bones)
        bad=copy.deepcopy(bones);bad[2]['global_position'][2]*=-1
        with self.assertRaisesRegex(PreparationError,'raw_bone_pose'):c.raw_bone_check(raw,bad)
        d['extras']['nativeSkeleton']['bones'][2]['global_position'][2]*=-1
        with self.assertRaisesRegex(PreparationError,'ambiguous_front_axis'):resolve(d,bad)
    def test_unknown_duplicate_external_names_and_material_rejected(self):
        folder,d,b,dat,native,members=self.fixture();config=(folder/'default.carcfg').read_bytes();part=next(p for p in native['lods']['high']if p['mesh']is None)
        bad=copy.deepcopy(native);next(p for p in bad['lods']['high']if p['mesh']is None)['name']='unknown.mesh'
        with self.assertRaisesRegex(PreparationError,'external_exact_name_join'):external.assemble(d,b,bad,dat,members,self.reader,config)
        match=next(r for r in members if Path(r['name']).name.casefold()==(part['name']+'.pck').casefold())
        with self.assertRaisesRegex(PreparationError,'external_exact_name_join'):external.assemble(d,b,native,dat,members+[match],self.reader,config)
        bad=copy.deepcopy(d)
        for m in bad['materials']:m['extras']['index']=-1
        with self.assertRaisesRegex(PreparationError,'external_material_index'):external.assemble(bad,b,native,dat,members,self.reader,config)
    def test_nondefault_configuration_is_not_silently_selected(self):
        folder,d,b,dat,native,members=self.fixture();config=(folder/'default.carcfg').read_bytes()
        with self.assertRaisesRegex(PreparationError,'duplicate_config_slot'):external.assemble(d,b,native,dat,members,self.reader,config+b'\nHoodIdx 1\n')
        with self.assertRaisesRegex(PreparationError,'nondefault_native_config'):external.assemble(d,b,native,dat,members,self.reader,b'HoodIdx 1\n')
    def test_wrapper_config_identity_and_output_budget_before_write(self):
        source=BASE/'batch-v1/vp_viper_03';proof=BASE/'batch-v2/vp_viper_03/native-proof.json';digest=hashlib.sha256((source/'source.glb').read_bytes()).hexdigest()
        with tempfile.TemporaryDirectory(dir=BASE)as tmp:
            output=Path(tmp)/'prepared';bad=Path(tmp)/'config';bad.write_bytes((source/'default.carcfg').read_bytes()+b'x')
            args=(source/'source.glb',digest,proof,source/'source.dat',source/'main.pck',output)
            with self.assertRaisesRegex(PreparationError,'native_config_index_pin'):c.wrapper.build(*args,complete_external_lod0=True,native_config_path=bad)
            with self.assertRaisesRegex(PreparationError,'requested_output_budget'):c.wrapper.build(*args,complete_external_lod0=True,native_config_path=source/'default.carcfg',output_budget=1)
            self.assertFalse(output.exists())
    def test_failed_frame_is_not_replaced_by_unlabelled_wheel_order(self):
        folder,d,b,dat,native,members=self.fixture();bones=json.loads(json.dumps(native['skeleton']['bones']))
        bones[2]['name']='unknown_front';d['extras']['nativeSkeleton']['bones'][2]['name']='unknown_front'
        with self.assertRaisesRegex(PreparationError,'orientation_anchor_missing'):resolve(d,bones)
    def test_current_optional_producer_reproduces_retained_candidates(self):
        for code in CODES:
            source=BASE/'batch-v1'/code;verified=BASE/'batch-v2'/code;status=json.loads((verified/'status.json').read_text())
            with self.subTest(code=code),tempfile.TemporaryDirectory(dir=BASE)as tmp:
                out=Path(tmp)/'prepared';r=c.wrapper.build(source/'source.glb',status['source_sha256'],verified/'native-proof.json',source/'source.dat',verified/'main.pck',out,complete_external_lod0=True,native_config_path=source/'default.carcfg',output_budget=16*1024**2)
                self.assertEqual(r['prepared_sha256'],status['prepared_sha256'])
                for path in out.iterdir():self.assertEqual(path.read_bytes(),(verified/'prepared-v1'/path.name).read_bytes())


if __name__=='__main__':sys.exit(cli())
