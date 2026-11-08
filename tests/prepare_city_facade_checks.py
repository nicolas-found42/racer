#!/usr/bin/env python3
"""Source append-only, geometry/buffer and publication-failure checks."""
import copy
import json
import os
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import prepare_city_facade as f
from prepare_gt4_vehicle import unpack


def fixture():
    binary=bytearray(struct.pack('<9f',0,0,0,1,0,0,0,0,1));d={'asset':{'version':'2.0'},'buffers':[{'byteLength':len(binary)}],'bufferViews':[{'buffer':0,'byteOffset':0,'byteLength':len(binary)}],'accessors':[{'bufferView':0,'componentType':5126,'count':3,'type':'VEC3'}],'materials':[{'name':'original','alphaMode':'OPAQUE','pbrMetallicRoughness':{'baseColorFactor':[1,1,1,1],'roughnessFactor':.8,'metallicFactor':0}}],'images':[],'textures':[],'samplers':[],'nodes':[{'name':'old','mesh':0}],'meshes':[{'primitives':[{'attributes':{'POSITION':0},'material':0}]}],'scenes':[{'nodes':[0]}],'scene':0,'extras':{'source':{'omitted_geometries':[128,116]}}}
    g={'stride':40,'position':[(2.,0.,0.),(3.,0.,0.),(2.,0.,1.)],'normal':[(0.,1.,0.)]*3,'texcoord0':[(0.,0.),(1.,0.),(0.,1.)],'texcoord1':[(.1,.2)]*3,'texcoord2':[(3.,4.)]*3,'colour0':[(1,2,3,4)]*3,'colour1':[(5,6,7,8)]*3,'tangent':[(1.,0.,0.)]*3,'indices':[0,1,2]}
    return d,binary,g,bytes(range(120)),struct.pack('>3H',0,1,2)


def accessor(doc,blob,ai):
    a=doc['accessors'][ai];v=doc['bufferViews'][a['bufferView']];return bytes(blob[v['byteOffset']:v['byteOffset']+v['byteLength']])


class FacadeChecks(unittest.TestCase):
    def test_original_prefixes_bindings_and_exact_appended_arrays(self):
        d,b,g,vb,ib=fixture();old=copy.deepcopy(d);original=bytes(b);proof={'native_shader':{'name':'CityGrimeTintDecal','samplers':[{'hash':123,'texture_name':'original'}]}}
        new,blob=f.append_geometry(d,b,g,vb,ib,proof,0)
        self.assertEqual(d,old);self.assertEqual(bytes(b),original);self.assertEqual(bytes(blob[:len(b)]),original)
        for key in ['nodes','meshes','accessors','bufferViews','materials']:self.assertEqual(new[key][:len(old[key])],old[key])
        for key in ['images','textures','samplers']:self.assertEqual(new[key],old[key])
        self.assertEqual(new['extras']['source'],old['extras']['source']);self.assertEqual(new['scenes'][0]['nodes'],[0,1])
        pr=new['meshes'][-1]['primitives'][0]
        for name,key,fmt in [('POSITION','position','3f'),('NORMAL','normal','3f'),('TEXCOORD_0','texcoord0','2f'),('TEXCOORD_1','texcoord1','2f'),('TEXCOORD_2','texcoord2','2f'),('_RACER_SOURCE_COLOR0','colour0','4B'),('_RACER_SOURCE_COLOR1','colour1','4B'),('_RACER_SOURCE_TANGENT','tangent','3f')]:self.assertEqual(accessor(new,blob,pr['attributes'][name]),b''.join(struct.pack('<'+fmt,*v)for v in g[key]))
        self.assertNotIn('TANGENT',pr['attributes']);self.assertEqual(accessor(new,blob,pr['indices']),struct.pack('<3H',*g['indices']))
        rawviews=new['extras']['racerFacadeRestoration']['raw_buffer_views']
        for name,expected in [('vertex',vb),('index',ib)]:
            v=new['bufferViews'][rawviews[name]];self.assertEqual(bytes(blob[v['byteOffset']:v['byteOffset']+v['byteLength']]),expected)
        self.assertEqual(new['materials'][-1]['pbrMetallicRoughness'],old['materials'][0]['pbrMetallicRoughness']);self.assertEqual(new['materials'][-1]['extras']['nativeSourceShader'],proof['native_shader'])

    def test_invalid_source_channels_indices_rawbuffers_and_duplicate(self):
        for mode,error in [('index','index_bounds'),('normal','source_normal'),('uv','channel_shape'),('colour','raw_colour'),('raw','raw_source_buffer'),('duplicate','already_restored')]:
            d,b,g,vb,ib=fixture()
            if mode=='index':g['indices'][2]=30;ib=struct.pack('>3H',*g['indices'])
            elif mode=='normal':g['normal'][0]=(0,0,0)
            elif mode=='uv':g['texcoord1'].pop()
            elif mode=='colour':g['colour0'][0]=(1,2,3,256)
            elif mode=='raw':vb=vb[:-1]
            else:d['nodes'].append({'name':'native_model_128_geometry_0','mesh':0})
            with self.subTest(mode=mode),self.assertRaisesRegex(ValueError,error):f.append_geometry(d,b,g,vb,ib,{},0)

    def test_publication_preflights_all_targets_and_preserves_idempotence(self):
        with tempfile.TemporaryDirectory()as temp:
            root=Path(temp).resolve();out=root/'out';files={'candidate.glb':b'mesh','manifest.json':b'identity'};f.publish(out,files)
            before={p.name:(p.read_bytes(),p.stat().st_mtime_ns)for p in out.iterdir()};f.publish(out,files);self.assertEqual(before,{p.name:(p.read_bytes(),p.stat().st_mtime_ns)for p in out.iterdir()})
            with self.assertRaisesRegex(ValueError,'immutable_conflict'):f.publish(out,{'new.glb':b'new','manifest.json':b'changed'})
            self.assertFalse((out/'new.glb').exists());(root/'link').symlink_to(out,target_is_directory=True)
            with self.assertRaisesRegex(ValueError,'symlink'):f.publish(root/'link',files)
            bad=root/'bad';bad.mkdir();(bad/'manifest.json').mkdir()
            with self.assertRaisesRegex(ValueError,'output_target_type'):f.publish(bad,files)
            self.assertFalse((bad/'candidate.glb').exists())
            with patch.object(f,'OUTPUT_LIMIT',1),self.assertRaisesRegex(ValueError,'output_budget'):f.publish(out,files)

    def test_v4_hash_rejects_before_iso_read_or_output(self):
        with tempfile.TemporaryDirectory()as temp:
            root=Path(temp).resolve();(root/'wrong').write_bytes(b'not expected')
            with self.assertRaisesRegex(ValueError,'v4_pin'):f.prepare(root/'wrong',root/'missing',root,root/'missing2',root/'out')
            self.assertFalse((root/'out').exists())

    @unittest.skipUnless(all(os.environ.get(k)for k in['RACER_FACADE_V4','RACER_FACADE_ISO','RACER_FACADE_REFS','RACER_FACADE_TEXTURE_HELPER']),'set exact pinned artifact paths')
    def test_actual_pinned_source_integrity_and_material_pixel_alias(self):
        args=[Path(os.environ[k])for k in['RACER_FACADE_V4','RACER_FACADE_ISO','RACER_FACADE_REFS','RACER_FACADE_TEXTURE_HELPER']]
        result,report=f.prepare(*args);old,b=unpack(args[0].read_bytes());new,blob=unpack(result)
        self.assertEqual(blob[:len(b)],b)
        for key in['nodes','meshes','accessors','bufferViews','materials','images','textures','samplers']:self.assertEqual(new[key][:len(old[key])],old[key])
        self.assertEqual(new['scenes'][0]['nodes'][:-1],old['scenes'][0]['nodes']);self.assertEqual(report['triangles_added'],859);self.assertEqual(report['vertices_added'],1221);self.assertEqual(report['images_added'],0)
        g,vb,ib,proof=f.native_geometry(args[1],args[2],args[3]);self.assertNotIn('iso_sha256',proof);self.assertEqual(proof['expected_iso_sha256'],f.world.ISO_SHA);self.assertIn('not recomputed',proof['verification_scope']);self.assertEqual(proof['prior_canonical_receipt']['verification_date'],'2026-11-05');pr=new['meshes'][-1]['primitives'][0]
        for name,key,fmt in [('POSITION','position','3f'),('NORMAL','normal','3f'),('TEXCOORD_0','texcoord0','2f'),('TEXCOORD_1','texcoord1','2f'),('TEXCOORD_2','texcoord2','2f'),('_RACER_SOURCE_COLOR0','colour0','4B'),('_RACER_SOURCE_COLOR1','colour1','4B'),('_RACER_SOURCE_TANGENT','tangent','3f')]:self.assertEqual(accessor(new,blob,pr['attributes'][name]),b''.join(struct.pack('<'+fmt,*v)for v in g[key]))
        self.assertEqual(accessor(new,blob,pr['indices']),struct.pack('<2577H',*g['indices']))
        self.assertEqual(new['materials'][-1]['pbrMetallicRoughness']['baseColorTexture'],old['materials'][35]['pbrMetallicRoughness']['baseColorTexture']);self.assertLessEqual(len(result),f.GLB_LIMIT)
        # Source positions independently checked against exact packed big-endian VB.
        self.assertEqual([struct.unpack_from('>3f',vb,i*40)for i in range(1221)],g['position'])


if __name__=='__main__':unittest.main()
