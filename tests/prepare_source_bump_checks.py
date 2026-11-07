#!/usr/bin/env python3
"""Source-frame, append-only, immutable-output checks; --actual pins retained inputs."""
import copy
import io
import json
import math
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import prepare_source_bump as bump
from prepare_gt4_vehicle import unpack

ACTUAL='--actual' in sys.argv
if ACTUAL:sys.argv.remove('--actual')


def profile(raw):
    count=len(raw)//28
    return {'vertices':count,'indices':count,'stride':28,
      'normal_words_sha256':bump.sha(b''.join(raw[i*28+12:i*28+16] for i in range(count))),
      'tangent_words_sha256':bump.sha(b''.join(raw[i*28+24:i*28+28] for i in range(count))),
      'negative_w':3,'positive_w':3}


def fixture(tangent_word=None):
    raw=bytearray();normals=[];tangents=[]
    for i in range(6):
        nw=511<<10;tw=tangent_word if tangent_word is not None else 511|((1 if i<3 else 3)<<30)
        raw.extend(struct.pack('>3fI4B2eI',float(i),0,0,nw,0,1,2,3,0,0,tw));normals.append(bump.xyz(nw));tangents.append(bump.xyz(tw))
    blob=bytearray();views=[];accessors=[]
    def view(b):
        i=len(views);views.append({'buffer':0,'byteOffset':len(blob),'byteLength':len(b)});blob.extend(b);return i
    def acc(rows,width,code,fmt,kind):
        i=len(accessors);accessors.append({'bufferView':view(b''.join(struct.pack('<'+fmt*width,*r)for r in rows)),'componentType':code,'type':kind,'count':len(rows)});return i
    attrs={'POSITION':acc([(float(i),0.,0.)for i in range(6)],3,5126,'f','VEC3'),'NORMAL':acc(normals,3,5126,'f','VEC3'),'TEXCOORD_0':acc([(0.,0.)]*6,2,5126,'f','VEC2'),'_RACER_SOURCE_TANGENT':acc(tangents,3,5126,'f','VEC3')};indices=acc([(i,)for i in range(6)],1,5123,'H','SCALAR')
    rawviews={'vertex':view(raw),'index':view(struct.pack('>6H',*range(6))),'declaration':view(bytes.fromhex('000040691c000005aa1111111199a996'))}
    material={'name':'curb','extras':{'name':'CityBumpSpec','samplers':[{'hash':0xf1fe2b71,'texture_name':'l_sha_curb_01.dds'},{'hash':0x332ebe1c,'texture_name':'l_sha_curb_01_bs.dds'}]},'pbrMetallicRoughness':{'baseColorFactor':[1,1,1,1],'metallicFactor':0,'roughnessFactor':.8},'alphaMode':'OPAQUE'}
    mesh={'primitives':[{'attributes':attrs,'indices':indices,'material':0,'mode':4}],'extras':{'source':{'entry':2389,'model':156,'geometry':0,'source_shader':0,'stride':28},'raw_source_bufferViews':rawviews}}
    d={'asset':{'version':'2.0'},'buffers':[{'byteLength':len(blob)}],'bufferViews':views,'accessors':accessors,'images':[],'textures':[],'samplers':[],'materials':[material,{'name':'untouched'}],'meshes':[mesh,{'primitives':[{'attributes':{'POSITION':attrs['POSITION']},'material':1}]}],'nodes':[{'name':'native_model_156_geometry_0_restored','mesh':0},{'mesh':1}],'scenes':[{'nodes':[0,1]}],'scene':0}
    return d,blob,bytes(raw)


class BumpChecks(unittest.TestCase):
    def test_signed_two_bits_and_unsigned_word_bounds(self):
        self.assertEqual(bump.signed_w(0x40000000),1);self.assertEqual(bump.signed_w(0xc0000000),-1)
        for word in [0,0x80000000,-1,1<<32,True]:
            with self.subTest(word=word),self.assertRaises(ValueError):bump.signed_w(word)

    def test_source_exact_xyz_and_signed_w_not_normalized(self):
        d,b,raw=fixture();p=d['meshes'][0]['primitives'][0]
        normals=bump.values(d,b,p['attributes']['NORMAL'],'VEC3',5126,'f',3);tangents=bump.values(d,b,p['attributes']['_RACER_SOURCE_TANGENT'],'VEC3',5126,'f',3)
        rows,stats=bump.tangent_rows(raw,normals,tangents,list(range(6)),profile(raw))
        self.assertEqual([r[3] for r in rows],[1,1,1,-1,-1,-1]);self.assertEqual([r[:3] for r in rows],tangents);self.assertEqual(stats['mixed_triangle_handedness'],0)
        bad=bytearray(raw);bad[24]^=1
        with self.assertRaisesRegex(ValueError,'packed_words_pin'):bump.tangent_rows(bad,normals,tangents,list(range(6)),profile(raw))
        with self.assertRaisesRegex(ValueError,'mixed_triangle'):bump.tangent_rows(raw,normals,tangents,[0,1,3,2,4,5],profile(raw))
        with self.assertRaisesRegex(ValueError,'source_indices'):bump.tangent_rows(raw,normals,tangents,[0,1,6,3,4,5],profile(raw))

    def test_nonfinite_unqualified_frame_and_xyz_mutations_fail(self):
        d,b,raw=fixture();p=d['meshes'][0]['primitives'][0];ns=bump.values(d,b,p['attributes']['NORMAL'],'VEC3',5126,'f',3);ts=bump.values(d,b,p['attributes']['_RACER_SOURCE_TANGENT'],'VEC3',5126,'f',3)
        for v,error in [((float('inf'),0,0),'finite'),((.9,0,0),'xyz_packing')]:
            bad=list(ts);bad[0]=v
            with self.subTest(error=error),self.assertRaisesRegex(ValueError,error):bump.tangent_rows(raw,ns,bad,list(range(6)),profile(raw))
        for word,error in [(511|(511<<10)|(1<<30),'frame_length'),(500|(60<<10)|(1<<30),'orthogonality')]:
            dd,bb,rr=fixture(word);pp=dd['meshes'][0]['primitives'][0];nn=bump.values(dd,bb,pp['attributes']['NORMAL'],'VEC3',5126,'f',3);tt=bump.values(dd,bb,pp['attributes']['_RACER_SOURCE_TANGENT'],'VEC3',5126,'f',3)
            with self.subTest(error=error),self.assertRaisesRegex(ValueError,error):bump.tangent_rows(rr,nn,tt,list(range(6)),profile(rr))

    def test_append_contract_prefix_and_only_selected_primitive_changes(self):
        d,b,raw=fixture();old=copy.deepcopy(d);prefix=bytes(b);new,blob,join=bump.derive(d,b,b'qualified png fixture',profile(raw));bump.prefix_check(d,b,new,blob,join)
        self.assertEqual(d,old);self.assertEqual(bytes(b),prefix);self.assertEqual(bytes(blob[:len(b)]),prefix);self.assertEqual(new['meshes'][1],d['meshes'][1])
        extension=new['materials'][join['material']]['extensions'][bump.EXTENSION];self.assertEqual(extension,{'texture':join['texture']});self.assertIs(type(extension['texture']),int);self.assertNotIn('normalTexture',new['materials'][join['material']]);self.assertNotIn('extensionsRequired',new)
        rows=bump.values(new,blob,join['tangentAccessor'],'VEC4',5126,'f',4);self.assertEqual([r[3]for r in rows],[1,1,1,-1,-1,-1])
        bad=copy.deepcopy(new);bad['nodes'][0]['name']='changed'
        with self.assertRaisesRegex(ValueError,'node_scene'):bump.prefix_check(d,b,bad,blob,join)

    def test_ambiguity_missing_declaration_sampler_and_conflict_reject(self):
        for mutation,error in [('duplicate','node_ambiguity'),('normal','material_conflict'),('sampler','material_binding'),('tangent','source_attributes'),('raw','declaration')]:
            d,b,raw=fixture()
            if mutation=='duplicate':d['nodes'].append(copy.deepcopy(d['nodes'][0]))
            if mutation=='normal':d['materials'][0]['normalTexture']={'index':0}
            if mutation=='sampler':d['materials'][0]['extras']['samplers'][1]['texture_name']='other.dds'
            if mutation=='tangent':d['meshes'][0]['primitives'][0]['attributes']['TANGENT']=0
            if mutation=='raw':b[-1]^=1
            with self.subTest(mutation=mutation),self.assertRaisesRegex(ValueError,error):bump.derive(d,b,b'png',profile(raw))

    def test_png_pixels_channels_and_bounds_preserved(self):
        rgba=bytes([100,132,123,179,165,190,132,91]);out=io.BytesIO();Image.frombytes('RGBA',(2,1),rgba).save(out,format='PNG');data=out.getvalue();info=bump.png_identity(data,bump.sha(data),bump.sha(rgba),(2,1));self.assertEqual(info['rgba_bytes'],8)
        with Image.open(io.BytesIO(data))as im:self.assertEqual(im.tobytes(),rgba)
        with self.assertRaisesRegex(ValueError,'rgba_pin'):bump.png_identity(data,bump.sha(data),'0'*64,(2,1))
        with patch.object(bump,'PNG_LIMIT',1),self.assertRaisesRegex(ValueError,'png_pin'):bump.png_identity(data,bump.sha(data),bump.sha(rgba),(2,1))

    def test_publish_preflight_conflict_symlink_quota_and_idempotence(self):
        with tempfile.TemporaryDirectory()as tmp:
            root=Path(tmp).resolve();out=root/'out';files={'curb.glb':b'original','manifest.json':b'metadata'};bump.publish(out,files);before={p.name:(p.read_bytes(),p.stat().st_mtime_ns)for p in out.iterdir()};bump.publish(out,files);self.assertEqual(before,{p.name:(p.read_bytes(),p.stat().st_mtime_ns)for p in out.iterdir()})
            with self.assertRaisesRegex(ValueError,'immutable_conflict'):bump.publish(out,{'new':b'new','manifest.json':b'changed'})
            self.assertFalse((out/'new').exists());(root/'link').symlink_to(out,target_is_directory=True)
            with self.assertRaisesRegex(ValueError,'symlink'):bump.publish(root/'link',files)
            with patch.object(bump,'DIRECTORY_LIMIT',1),self.assertRaisesRegex(ValueError,'directory_budget'):bump.publish(out,files)
            (out/'child').symlink_to(root/'absent')
            with self.assertRaisesRegex(ValueError,'output_entry'):bump.publish(out,files)

    def test_bad_input_pin_has_no_output_effects(self):
        with tempfile.TemporaryDirectory()as tmp:
            p=Path(tmp).resolve()/'input';p.write_bytes(b'wrong')
            with self.assertRaisesRegex(ValueError,'source_pin'):bump.build(p,p,p)

    @unittest.skipUnless(ACTUAL,'pass --actual for retained source/profile/PNG checks')
    def test_actual_pinned_profile_prefix_pixels_and_signed_source(self):
        base=Path('/private/tmp/racer-world-curb/2389-curb-restored.glb');maps=Path('/private/tmp/racer-material-microcode');files,report=bump.build(base,maps/'curb01_bs.png',maps/'binding-proof.json');old,ob=unpack(base.read_bytes());new,nb=unpack(files['curb-source-bump.glb']);bump.prefix_check(old,ob,new,nb,report['binding']);self.assertEqual(report['texture']['rgba_sha256'],bump.RGBA_SHA);self.assertLessEqual(report['output_bytes'],bump.GLB_LIMIT)
        join=report['binding'];rows=bump.values(new,nb,join['tangentAccessor'],'VEC4',5126,'f',4);self.assertEqual(sum(r[3]==-1 for r in rows),547);self.assertEqual(sum(r[3]==1 for r in rows),215)
        for expected,actual in zip(bump.values(old,ob,old['meshes'][join['mesh']]['primitives'][0]['attributes']['_RACER_SOURCE_TANGENT'],'VEC3',5126,'f',3),rows):self.assertEqual(expected,actual[:3])
        im=new['images'][new['textures'][join['texture']]['source']];self.assertEqual(bump.view_bytes(new,nb,im['bufferView']),(maps/'curb01_bs.png').read_bytes())


if __name__=='__main__':unittest.main()
