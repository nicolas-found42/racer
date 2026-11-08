#!/usr/bin/env python3
"""Façade source matching/mixed-W/prefix/resource tests; --actual reads pinned source."""
import copy
import io
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import prepare_facade_bump as facade
import prepare_source_bump as bump
from prepare_gt4_vehicle import unpack
ACTUAL='--actual'in sys.argv
if ACTUAL:sys.argv.remove('--actual')


def fixture():
    blob=bytearray();views=[];accessors=[];materials=[];meshes=[];nodes=[];items={}
    def acc(rows,width,code,fmt,kind):
        i=len(accessors);raw=b''.join(struct.pack('<'+fmt*width,*x)for x in rows);views.append({'buffer':0,'byteOffset':len(blob),'byteLength':len(raw)});blob.extend(raw);accessors.append({'bufferView':len(views)-1,'componentType':code,'count':len(rows),'type':kind});return i
    for model,pin in facade.TARGETS.items():
        raw=bytearray();g={'model':model,'geometry':0,'stride':28,'position':[],'normal':[],'texcoord0':[],'colour1':[],'tangent':[],'indices':list(range(6))}
        for i in range(6):
            nw=511<<10;tw=510|((3 if i in(0,4)else 1)<<30);pos=(float(i),float(model),0.);uv=(i*.125,0.);raw.extend(struct.pack('>3fI4B2eI',*pos,nw,1,2,3,4,*uv,tw));g['position'].append(pos);g['normal'].append(bump.xyz(nw));g['tangent'].append(bump.xyz(tw));g['texcoord0'].append(uv);g['colour1'].append((1,2,3,4))
        attrs={'POSITION':acc(g['position'],3,5126,'f','VEC3'),'NORMAL':acc(g['normal'],3,5126,'f','VEC3'),'TEXCOORD_0':acc(g['texcoord0'],2,5126,'f','VEC2'),'_RACER_SOURCE_COLOR1':acc(g['colour1'],4,5121,'B','VEC4')};indices=acc([(i,)for i in g['indices']],1,5123,'H','SCALAR');samplers=[{'hash':0xf1fe2b71,'texture_name':'diffuse.dds'},{'hash':0x332ebe1c,'texture_name':pin['BS']}];shader={'name':'CityBumpSpec','samplers':samplers,'vectors':[],'draw_bucket':0};materials.append({'name':'source','extras':copy.deepcopy(shader),'pbrMetallicRoughness':{'baseColorFactor':[.4,.3,.2,1],'roughnessFactor':.8,'metallicFactor':0},'alphaMode':'OPAQUE'});meshes.append({'primitives':[{'attributes':attrs,'indices':indices,'material':len(materials)-1,'mode':4}]});nodes.append({'name':f'native_model_{model}_geometry_0','mesh':len(meshes)-1});tangents,frame=facade.frame_rows(g,raw);png=io.BytesIO();Image.frombytes('RGBA',(1,1),bytes([128,160,130,128])).save(png,format='PNG');items[model]={'geometry':g,'shader':shader,'tangents':tangents,'png':png.getvalue(),'proof':{'model':model,'frame':frame}}
    meshes.append({'primitives':[copy.deepcopy(meshes[0]['primitives'][0])]});nodes.append({'name':'unselected_shared_material','mesh':len(meshes)-1})
    doc={'asset':{'version':'2.0'},'buffers':[{'byteLength':len(blob)}],'bufferViews':views,'accessors':accessors,'images':[],'textures':[],'samplers':[],'materials':materials,'meshes':meshes,'nodes':nodes,'scenes':[{'nodes':list(range(len(nodes)))}],'scene':0}
    return doc,blob,items


class FacadeChecks(unittest.TestCase):
    def test_source_frame_keeps_mixed_w_and_nonunit_xyz(self):
        d,b,items=fixture()
        for item in items.values():
            self.assertEqual(item['proof']['frame']['mixed_W_triangles'],2)
            self.assertTrue(any(row[3]<0 for row in item['tangents']));self.assertTrue(any(row[3]>0 for row in item['tangents']))
            for row,source in zip(item['tangents'],item['geometry']['tangent']):self.assertEqual(row[:3],source);self.assertLess(row[0],1.)

    def test_append_only_selected_binding_and_extension_contract(self):
        d,b,items=fixture();old=copy.deepcopy(d);prefix=bytes(b);new,blob,joins=facade.derive(d,b,items);facade.prefix_check(d,b,new,blob,joins)
        self.assertEqual(d,old);self.assertEqual(bytes(b),prefix);self.assertEqual(bytes(blob[:len(b)]),prefix);self.assertEqual(new['meshes'][-1],d['meshes'][-1]);self.assertEqual(len(joins),3)
        for join in joins:
            mat=copy.deepcopy(new['materials'][join['material']]);self.assertEqual(mat.pop('extensions'),{bump.EXTENSION:{'texture':join['texture']}});mat['extras'].pop('racerFacadeSourceBumpNormalOnly');self.assertEqual(mat,d['materials'][join['originalMaterial']]);self.assertNotIn('normalTexture',mat);self.assertNotIn('Zero mixed-W',new['materials'][join['material']]['extras']['racerFacadeSourceBumpNormalOnly']['policy']);self.assertIn('mixed-W triangles',new['materials'][join['material']]['extras']['racerFacadeSourceBumpNormalOnly']['policy'])
            rows=bump.values(new,blob,join['tangentAccessor'],'VEC4',5126,'f',4)
            for actual,expected in zip(rows,items[join['model']]['tangents']):self.assertEqual(struct.pack('<4f',*actual),struct.pack('<4f',*expected))

    def test_source_position_normal_uv_and_indices_mutations_abort(self):
        for attr,error in [('POSITION','position'),('NORMAL','normal'),('TEXCOORD_0','texcoord0'),('_RACER_SOURCE_COLOR1','colour_bytes')]:
            d,b,items=fixture();pr=d['meshes'][0]['primitives'][0];ai=pr['attributes'][attr];view=d['bufferViews'][d['accessors'][ai]['bufferView']];b[view['byteOffset']]^=1
            with self.subTest(attr=attr),self.assertRaisesRegex(ValueError,'prepared_source_'+error+'_mismatch'):facade.derive(d,b,items)
        d,b,items=fixture();ai=d['meshes'][0]['primitives'][0]['indices'];v=d['bufferViews'][d['accessors'][ai]['bufferView']];b[v['byteOffset']]=1
        with self.assertRaisesRegex(ValueError,'source_indices_mismatch'):facade.derive(d,b,items)

    def test_ambiguity_binding_transform_and_preexisting_normal_abort(self):
        for mode,error in [('node','node_ambiguity'),('sampler','sampler_mismatch'),('pose','node_pose'),('normal','material_conflict'),('tangent','tangent_conflict')]:
            d,b,items=fixture()
            if mode=='node':d['nodes'].append(copy.deepcopy(d['nodes'][0]))
            if mode=='sampler':d['materials'][0]['extras']['samplers'][1]['texture_name']='wrong.dds'
            if mode=='pose':d['nodes'][0]['translation']=[0,0,0]
            if mode=='normal':d['materials'][0]['normalTexture']={'index':0}
            if mode=='tangent':d['meshes'][0]['primitives'][0]['attributes']['TANGENT']=0
            with self.subTest(mode=mode),self.assertRaisesRegex(ValueError,error):facade.derive(d,b,items)

    def test_unselected_or_binary_prefix_mutations_detected(self):
        d,b,items=fixture();new,blob,joins=facade.derive(d,b,items);new['meshes'][-1]['primitives'][0]['material']=2
        with self.assertRaisesRegex(ValueError,'unselected_primitive'):facade.prefix_check(d,b,new,blob,joins)
        new,blob,joins=facade.derive(d,b,items);blob[0]^=1
        with self.assertRaisesRegex(ValueError,'binary_prefix'):facade.prefix_check(d,b,new,blob,joins)

    def test_output_conflicts_symlinks_idempotence_and_aggregate_budget(self):
        with tempfile.TemporaryDirectory()as temp:
            root=Path(temp).resolve();out=root/'out';files={'candidate':b'original','manifest':b'metadata'};facade.publish(out,files);before={p.name:(p.read_bytes(),p.stat().st_mtime_ns)for p in out.iterdir()};facade.publish(out,files);self.assertEqual(before,{p.name:(p.read_bytes(),p.stat().st_mtime_ns)for p in out.iterdir()})
            with self.assertRaisesRegex(ValueError,'immutable_conflict'):facade.publish(out,{'new':b'new','manifest':b'changed'})
            self.assertFalse((out/'new').exists());(root/'link').symlink_to(out,target_is_directory=True)
            with self.assertRaisesRegex(ValueError,'symlink'):facade.publish(root/'link',files)
            with patch.object(facade,'DIRECTORY_LIMIT',1),self.assertRaisesRegex(ValueError,'directory_budget'):facade.publish(out,files)

    def test_bad_base_pin_stops_before_source_decode(self):
        with tempfile.TemporaryDirectory()as temp:
            p=Path(temp).resolve()/'source';p.write_bytes(b'wrong')
            with patch.object(facade,'native_items')as native,self.assertRaisesRegex(ValueError,'source_glb_pin'):facade.build(p,p,p,p)
            native.assert_not_called()

    @unittest.skipUnless(ACTUAL,'pass --actual for source ISO/GLB/pixel checks')
    def test_actual_source_geometry_pixels_prefix_and_mixed_w(self):
        files,report=facade.build(Path('/private/tmp/racer-world-facade/2300-restored-facade-v5.glb'),Path('/Users/nicolas/Documents/github/reverse-engineering/games/raw/midnight-club-la/Midnight Club - Los Angeles - Complete Edition (USA, Europe).iso'),Path('/Users/nicolas/Documents/github/reverse-engineering/games/racer/experiments/2026-11-05-mcla-vehicle/output/references'),Path('/private/tmp/racer-visual-world-assets/mcla_texture.py'))
        self.assertEqual(set(report['models']),{111,103,25});self.assertEqual(report['models'][111]['frame']['mixed_W_triangles'],64);self.assertNotIn('Zero mixed-W',report['policy']);self.assertEqual((report['models'][111]['frame']['negative_w'],report['models'][111]['frame']['positive_w']),(206,499));self.assertEqual(report['source']['bank_reads'],0);self.assertEqual(report['source']['selected_source_RGBA_bytes'],114688);self.assertLessEqual(report['output_bytes'],facade.GLB_LIMIT)
        old,ob=unpack(Path('/private/tmp/racer-world-facade/2300-restored-facade-v5.glb').read_bytes());new,nb=unpack(files['facade-source-bump.glb']);facade.prefix_check(old,ob,new,nb,report['bindings'])
        for join in report['bindings']:
            image=new['images'][new['textures'][join['texture']]['source']];png=bump.view_bytes(new,nb,image['bufferView']);self.assertEqual(png,files[f"source-{join['model']}-bs.png"])
            with Image.open(io.BytesIO(png))as im:self.assertEqual(bump.sha(im.tobytes()),report['models'][join['model']]['rgba_sha256'])


if __name__=='__main__':unittest.main()
