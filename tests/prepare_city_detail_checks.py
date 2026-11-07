#!/usr/bin/env python3
"""Append-only and failure-boundary checks; optional exact source artifact checks."""
import copy
import hashlib
import io
import os
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import prepare_city_detail as detail
from prepare_gt4_vehicle import unpack


def image(pixels,size):
    out=io.BytesIO();Image.frombytes('RGBA',size,bytes(pixels)).save(out,format='PNG');return out.getvalue()


def scene():
    blob=bytearray();views=[];accessors=[]
    for kind,rows in [('VEC3',[(0.,0.,0.),(1.,0.,0.),(0.,0.,1.)]),('VEC3',[(0.,1.,0.)]*3),('VEC2',[(0.,0.),(1.,0.),(0.,1.)])]:
        start=len(blob)
        for row in rows:blob.extend(struct.pack('<'+'f'*len(row),*row))
        views.append({'buffer':0,'byteOffset':start,'byteLength':len(blob)-start});accessors.append({'bufferView':len(views)-1,'componentType':5126,'count':3,'type':kind})
    materials=[{'name':name,'extras':{'name':'CityGrime','samplers':[{'hash':detail.SAMPLER_HASH,'texture_name':name}]},'pbrMetallicRoughness':{'baseColorFactor':[.2,.3,.4,1]},'alphaMode':'OPAQUE'}for name in detail.MAPS]
    materials.append({'name':'excluded','extras':{'samplers':[{'hash':detail.SAMPLER_HASH,'texture_name':'l_sha_flat_bs.dds'}]}})
    doc={'asset':{'version':'2.0'},'buffers':[{'byteLength':len(blob)}],'bufferViews':views,'accessors':accessors,'materials':materials,'textures':[],'images':[],'nodes':[{'mesh':0}],'scenes':[{'nodes':[0]}],'scene':0,'meshes':[{'primitives':[{'material':i,'attributes':{'POSITION':0,'NORMAL':1,'TEXCOORD_0':2},'extras':{'original':i}}for i in range(4)]}]}
    return doc,blob


class DetailChecks(unittest.TestCase):
    def test_reconstruction_unit_direction_and_source_unchanged(self):
        rgba=bytes([128,2,3,128,150,4,5,100]);raw=image(rgba,(2,1))
        out=detail.normal_png(raw,(2,1),detail.sha(rgba))
        with Image.open(io.BytesIO(out))as result:
            self.assertEqual(result.mode,'RGB');data=result.tobytes()
            self.assertEqual(data[0],128);self.assertEqual(data[1],128)
            self.assertEqual(data[3],150);self.assertEqual(data[4],100)
            for i in range(0,6,3):self.assertLess(abs(sum((v/127.5-1)**2 for v in data[i:i+3])-1),.015)
        self.assertEqual(raw,image(rgba,(2,1)))

    def test_invalid_xy_constant_pin_and_size_rejected(self):
        for rgba,size,pin,error in [(bytes([255,0,0,255]),(1,1),None,'invalid_xy'),(bytes([128,0,0,128]),(1,1),None,'constant_detail'),(bytes([128,0,0,128]),(1,1),'0'*64,'rgba_pin'),(bytes([128,0,0,128]),(2,1),None,'png_pixels')]:
            with self.subTest(error=error),self.assertRaisesRegex(ValueError,error):detail.normal_png(image(rgba,(1,1)),size,pin or detail.sha(rgba))
        with patch.object(detail,'PNG_LIMIT',1),self.assertRaisesRegex(ValueError,'png_size'):detail.normal_png(b'xx',(1,1),'0'*64)

    def test_append_only_and_excluded_material_bindings(self):
        d,b=scene();old=copy.deepcopy(d);prefix=bytes(b)
        normals={n:b'png-'+n.encode()for n in detail.MAPS}
        new,blob,joins=detail.derive(d,b,normals)
        self.assertEqual(d,old);self.assertEqual(bytes(b),prefix);self.assertEqual(bytes(blob[:len(b)]),prefix)
        for key in ['nodes','accessors','scenes']:self.assertEqual(new[key],old[key])
        for key in ['materials','bufferViews','images','textures']:self.assertEqual(new[key][:len(old[key])],old[key])
        self.assertEqual(len(joins),3);self.assertEqual(new['meshes'][0]['primitives'][3],old['meshes'][0]['primitives'][3])
        for i in range(3):
            pr=copy.deepcopy(new['meshes'][0]['primitives'][i]);mi=pr.pop('material');original=copy.deepcopy(old['meshes'][0]['primitives'][i]);original.pop('material');self.assertEqual(pr,original)
            m=copy.deepcopy(new['materials'][mi]);self.assertEqual(m.pop('normalTexture'),{'index':i,'texCoord':0,'scale':.6});m['extras'].pop('racerAuthoredDetail');self.assertEqual(m,old['materials'][i])

    def test_ambiguous_sampler_missing_uv_and_coverage_fail(self):
        for mode,error in [('duplicate','ambiguous_sampler'),('uv','normal_uv0'),('missing','qualified_coverage')]:
            d,b=scene()
            if mode=='duplicate':d['materials'][0]['extras']['samplers']*=2
            elif mode=='uv':d['meshes'][0]['primitives'][0]['attributes'].pop('TEXCOORD_0')
            else:d['materials'].pop(2)
            with self.subTest(mode=mode),self.assertRaisesRegex(ValueError,error):detail.derive(d,b,{n:b'x'for n in detail.MAPS})

    def test_output_idempotence_preflight_conflict_links_budget(self):
        with tempfile.TemporaryDirectory()as temp:
            root=Path(temp).resolve();out=root/'out';files={'city.glb':b'original','manifest.json':b'manifest'}
            detail.publish(out,files);before={p.name:(p.read_bytes(),p.stat().st_mtime_ns)for p in out.iterdir()};detail.publish(out,files)
            self.assertEqual(before,{p.name:(p.read_bytes(),p.stat().st_mtime_ns)for p in out.iterdir()})
            with self.assertRaisesRegex(ValueError,'immutable_conflict'):detail.publish(out,{'new':b'new','manifest.json':b'changed'})
            self.assertFalse((out/'new').exists())
            (root/'link').symlink_to(out,target_is_directory=True)
            with self.assertRaisesRegex(ValueError,'symlink'):detail.publish(root/'link',files)
            (out/'child').symlink_to(root/'missing')
            with self.assertRaisesRegex(ValueError,'output_entry'):detail.publish(out,files)
            (out/'child').unlink()
            with patch.object(detail,'DIRECTORY_LIMIT',1),self.assertRaisesRegex(ValueError,'directory_budget'):detail.publish(out,files)

    def test_input_hash_rejected_without_output(self):
        with tempfile.TemporaryDirectory()as temp:
            root=Path(temp).resolve();(root/'input').write_bytes(b'wrong')
            with self.assertRaisesRegex(ValueError,'source_pin'):detail.prepare(root/'input',root,root/'out')
            self.assertFalse((root/'out').exists())

    @unittest.skipUnless(os.environ.get('RACER_CITY_DETAIL_SOURCE') and os.environ.get('RACER_CITY_DETAIL_MAPS'),'set actual pinned source and map directories')
    def test_actual_pinned_arrays_materials_pixels_and_budget(self):
        with tempfile.TemporaryDirectory()as temp:
            source=Path(os.environ['RACER_CITY_DETAIL_SOURCE']);maps=Path(os.environ['RACER_CITY_DETAIL_MAPS']);out=Path(temp).resolve()/'out'
            report=detail.prepare(source,maps,out);old,b=unpack(source.read_bytes());new,blob=unpack((out/'city.glb').read_bytes())
            self.assertEqual(blob[:len(b)],b)
            for key in ['nodes','accessors','scenes']:self.assertEqual(new[key],old[key])
            for key in ['bufferViews','images','textures','samplers']:self.assertEqual(new.get(key,[])[:len(old.get(key,[]))],old.get(key,[]))
            self.assertEqual(new['materials'][:len(old['materials'])],old['materials'])
            restored=copy.deepcopy(new['meshes'])
            for binding in report['bindings']:restored[binding['mesh']]['primitives'][binding['primitive']]['material']=binding['originalMaterial']
            self.assertEqual(restored,old['meshes']);self.assertEqual(len(report['maps']),3)
            for name,pin in detail.MAPS.items():
                filename=name[:-4]+'.png';self.assertEqual((out/('source-'+filename)).read_bytes(),(maps/filename).read_bytes())
                normal=(out/('normal-'+filename)).read_bytes();self.assertEqual(detail.sha(normal),report['maps'][name]['normalPngSha256'])
                found=[]
                for im in new['images'][len(old['images']):]:
                    view=new['bufferViews'][im['bufferView']];found.append(bytes(blob[view['byteOffset']:view['byteOffset']+view['byteLength']]))
                self.assertIn(normal,found)
            self.assertLessEqual(report['outputBytes'],detail.GLB_LIMIT)
            detail.prepare(source,maps,out)


if __name__=='__main__':unittest.main()
