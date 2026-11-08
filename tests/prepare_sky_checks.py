#!/usr/bin/env python3
"""Packaging/safe-publication checks, plus optional exact original-source proof."""
import argparse,importlib.util,io,json,struct,tempfile,unittest
from unittest.mock import patch
from pathlib import Path
spec=importlib.util.spec_from_file_location('sky',Path(__file__).parents[1]/'scripts/prepare_sky.py');sky=importlib.util.module_from_spec(spec);spec.loader.exec_module(sky)
SOURCE=None

def unpack(data):
    magic,version,total=struct.unpack_from('<III',data);assert (magic,version,total)==(0x46546c67,2,len(data))
    n,tag=struct.unpack_from('<II',data,12);assert tag==0x4e4f534a
    doc=json.loads(data[20:20+n]);size,tag=struct.unpack_from('<II',data,20+n);assert tag==0x004e4942 and size==len(data)-28-n
    return doc,data[28+n:]
def accessor(doc,binary,n):
    a=doc['accessors'][n];v=doc['bufferViews'][a['bufferView']];start=v.get('byteOffset',0);return binary[start:start+v['byteLength']]

class SkyChecks(unittest.TestCase):
    def test_packaging(self):
        pos=struct.pack('<9f',0,0,0,1,0,0,0,1,0);uv=struct.pack('<6f',0,0,1,0,0,1);idx=struct.pack('<3I',0,1,2)
        doc,b=unpack(sky.package(pos,uv,idx,b'png-test',3,1,([0,0,0],[1,1,0])))
        p=doc['meshes'][0]['primitives'][0]
        self.assertEqual(accessor(doc,b,p['attributes']['POSITION']),pos);self.assertEqual(accessor(doc,b,p['attributes']['TEXCOORD_0']),uv);self.assertEqual(accessor(doc,b,p['indices']),idx)
        self.assertEqual(doc['samplers'][0]['wrapS'],33071);self.assertIn('KHR_materials_unlit',doc['materials'][0]['extensions'])
    def test_idempotent(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t).resolve()/'out';sky.publish(p,b'a',b'b');before={x.name:(x.read_bytes(),x.stat().st_mtime_ns) for x in p.iterdir()};sky.publish(p,b'a',b'b')
            self.assertEqual(before,{x.name:(x.read_bytes(),x.stat().st_mtime_ns) for x in p.iterdir()})
    def test_pair_conflict_preflight(self):
        for conflict in ['sky.glb','manifest.json']:
            with tempfile.TemporaryDirectory() as t:
                p=Path(t).resolve();(p/conflict).write_bytes(b'original')
                with self.assertRaises(ValueError):sky.publish(p,b'a',b'b')
                self.assertEqual(list(p.iterdir()),[p/conflict]);self.assertEqual((p/conflict).read_bytes(),b'original')
    def test_symlink(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t).resolve();(p/'real').mkdir();(p/'link').symlink_to(p/'real',target_is_directory=True)
            with self.assertRaises(ValueError):sky.publish(p/'link',b'a',b'b')
            (p/'real'/'sky.glb').symlink_to(p/'missing')
            with self.assertRaises(ValueError):sky.publish(p/'real',b'a',b'b')
            self.assertFalse((p/'real'/'manifest.json').exists())
    def test_conflict_size_precedes_read(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t).resolve();(p/'sky.glb').write_bytes(b'larger retained data')
            with patch.object(Path,'read_bytes',side_effect=AssertionError('must reject size before read')):
                with self.assertRaisesRegex(ValueError,'output conflict'):sky.publish(p,b'a',b'b')
            self.assertFalse((p/'manifest.json').exists())
    def test_pin_rejects_before_decode(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t).resolve();(p/'meshes').mkdir();(p/'meshes/skydome.SCX').write_bytes(b'bad')
            with self.assertRaisesRegex(ValueError,'hash mismatch'):sky.prepare(p)
    def test_actual_arrays_pixels(self):
        if SOURCE is None:self.skipTest('--source not supplied')
        from PIL import Image
        glb,report=sky.prepare(SOURCE);doc,b=unpack(glb);raw=(SOURCE/'meshes/skydome.SCX').read_bytes();p=doc['meshes'][0]['primitives'][0]
        self.assertEqual(accessor(doc,b,p['attributes']['POSITION']),b''.join(raw[148+64*i:160+64*i] for i in range(376)))
        self.assertEqual(accessor(doc,b,p['attributes']['TEXCOORD_0']),b''.join(raw[172+64*i:180+64*i] for i in range(376)))
        off=148+64*376+4;self.assertEqual(accessor(doc,b,p['indices']),raw[off:off+350*12])
        v=doc['bufferViews'][doc['images'][0]['bufferView']];png=b[v['byteOffset']:v['byteOffset']+v['byteLength']]
        self.assertEqual(Image.open(io.BytesIO(png)).convert('RGBA').tobytes(),Image.open(SOURCE/'textures/cloudy_day01.dds').convert('RGBA').tobytes())
        self.assertLessEqual(len(glb),12*1024**2);self.assertEqual(json.loads(report)['rgba_bytes'],16*1024**2)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path);a,rest=p.parse_known_args();SOURCE=a.source;unittest.main(argv=[__file__]+rest)
