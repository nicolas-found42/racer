#!/usr/bin/env python3
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import contextlib
import hashlib
import io
import sys
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
spec=importlib.util.spec_from_file_location('scale',ROOT/'scripts/check_car_scale.py')
scale=importlib.util.module_from_spec(spec);spec.loader.exec_module(scale)

class ScaleChecks(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name).resolve()/'car.vehicle'
        self.text='''RACER_VEHICLE 1
body -1 .15 -2.2 1 1.25 2.2
wheel FL -.8 .3 1.3 .3 .2
wheel FR .8 .3 1.3 .3 .2
wheel RL -.8 .3 -1.3 .3 .2
wheel RR .8 .3 -1.3 .3 .2
'''
    def write(self,text):self.path.write_text(text);return scale.measure(self.path)
    def test_ground_height_is_not_body_span(self):
        m=self.write(self.text)
        self.assertEqual(m['ground_height'],1.25);self.assertAlmostEqual(m['body_box_height'],1.10)
        self.assertEqual(m['wheelbase'],2.6);self.assertEqual(m['minimum_tire_clearance'],0)
    def test_report_identity_uses_same_snapshot_as_measurement(self):
        original=(self.text+'source_sha256 '+'a'*64+'\n').encode()
        replacement=original.replace(b'-2.2',b'-3.2').replace(b'2.2\n',b'3.2\n').replace(b'a'*64,b'b'*64)
        self.path.write_bytes(original);dims=self.path.parent/'dims.json';dims.write_text('{"vehicles":[]}');out=self.path.parent/'report.json'
        real=scale.read_regular;reads=[]
        def snapshot(path,limit):
            data=real(path,limit)
            if path==self.path:reads.append(data);self.path.write_bytes(replacement)
            return data
        with patch.object(scale,'read_regular',side_effect=snapshot),patch.object(sys,'argv',['scale',str(self.path),'--model-id','fixture','--dimensions',str(dims),'--output',str(out)]),contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(scale.main(),0)
        report=json.loads(out.read_text());self.assertEqual(len(reads),1)
        self.assertAlmostEqual(report['measured']['length'],4.4);self.assertEqual(report['source_sha256'],'a'*64)
        self.assertEqual(report['descriptor_sha256'],hashlib.sha256(original).hexdigest());self.assertEqual(self.path.read_bytes(),replacement)
    def test_malformed_geometry_is_rejected(self):
        for text in ['',self.text+'body -1 0 -2 1 1 2\n',self.text.replace('wheel FR','wheel FL'),self.text.replace('.3 .2','-.3 .2'),self.text.replace('1 1.25','1 nan'),self.text.replace('-.8 .3 1.3','.8 .3 1.3')]:
            with self.subTest(text=text),self.assertRaises(ValueError):self.write(text)
    def test_factory_conflict_is_not_auto_fit(self):
        m=self.write(self.text);before=dict(m)
        r=scale.compare(m,{'canonical_id':'reference','applicability':'fixture','nominal':{'length':4.4,'width':9,'height':1.25,'wheelbase':2.9}})
        self.assertFalse(r['within_authored_tolerances']);self.assertEqual(m,before)
        self.assertNotIn('width',r['comparisons'])
    def test_track_conflict_cannot_hide_behind_matching_wheelbase(self):
        m=self.write(self.text)
        r=scale.compare(m,{'canonical_id':'reference','applicability':'fixture','nominal':{'length':4.4,'height':1.25,'wheelbase':2.6,'front_track':1.85,'rear_track':1.85}})
        self.assertTrue(r['checks']['wheelbase']);self.assertFalse(r['checks']['front_track'])
        self.assertFalse(r['within_authored_tolerances'])
    def test_canonical_units_and_unique_source_mapping(self):
        d=json.loads((ROOT/'assets/catalog/dimensions.json').read_text());seen=set()
        self.assertEqual(d['units'],'metres');self.assertEqual(d['world_units_per_metre'],1)
        for v in d['vehicles']:
            self.assertIn(v['source'],d['sources'])
            for ident in v['game_model_ids']:
                self.assertNotIn(ident,seen);seen.add(ident)
                self.assertRegex(v['source_model_sha256'][ident],r'^[0-9a-f]{64}$')
            values=v.get('source_values_mm',v.get('source_values_inches'))
            factor=.001 if 'source_values_mm' in v else .0254
            for key,value in values.items():self.assertAlmostEqual(value*factor,v['nominal'][key],places=12)
if __name__=='__main__':unittest.main()
