#!/usr/bin/env python3
"""Partition, immutable-publication and optional exact pinned lamp derivative checks."""
import argparse
import copy
import io
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import prepare_mcla_lamp_preview as lamp

ACTUAL=False
ROOT=Path('/Users/nicolas/Documents/github/reverse-engineering/games/racer')

def fixture():
    pos=[(0.,0.,1.),(1.,0.,1.),(0.,1.,1.)];uv=[(0.,0.),(1.,0.),(0.,1.)];indices=[0,1,2];b=bytearray();d={'accessors':[],'bufferViews':[],'meshes':[{'primitives':[]} ]}
    def a(values,fmt,kind,ct):
        off=len(b);data=b''.join(struct.pack('<'+fmt,*v)for v in values);b.extend(data);d['bufferViews'].append({'byteOffset':off,'byteLength':len(data)});d['accessors'].append({'bufferView':len(d['bufferViews'])-1,'count':len(values),'type':kind,'componentType':ct});return len(d['accessors'])-1
    attrs={'POSITION':a([(x,y,-z)for x,y,z in pos],'3f','VEC3',5126),'TEXCOORD_0':a(uv,'2f','VEC2',5126)};p={'attributes':attrs,'indices':a([(0,),(2,),(1,)],'H','SCALAR',5123)};d['meshes'][0]['primitives']=[p];return d,b,(pos,uv,indices)

def payload(doc,blob,accessor):
    a=doc['accessors'][accessor];v=doc['bufferViews'][a['bufferView']];start=v.get('byteOffset',0)+a.get('byteOffset',0);return bytes(blob[start:start+v['byteLength']])

class Helpers(unittest.TestCase):
    def test_partition_exact_coverage(self):
        indices=[0,1,2,3,4,5,0,2,1];selector=[(2,1)]*3+[(11,1)]*3
        self.assertEqual(lamp.partition(indices,selector),{2:[0,2],11:[1]})
        with self.assertRaisesRegex(ValueError,'mixed_native_lamp_ids'):lamp.partition([0,1,3],selector)
        with self.assertRaisesRegex(ValueError,'native_selector_shape'):lamp.partition([0,1,2],[(.5,1)]*3)
    def test_matching_is_independent_and_unique(self):
        d,b,native=fixture();self.assertEqual(lamp.find_prepared(d,b,native),(0,0))
        d['meshes'][0]['primitives']*=2
        with self.assertRaisesRegex(ValueError,'ambiguous'):lamp.find_prepared(d,b,native)
        d,b,native=fixture();struct.pack_into('<f',b,0,7)
        with self.assertRaisesRegex(ValueError,'missing'):lamp.find_prepared(d,b,native)
    def test_publication_conflicts_idempotence_symlinks(self):
        with tempfile.TemporaryDirectory()as t:
            root=Path(t).resolve();out=root/'out';files={'catalog.racer':b'catalog','manifest.json':b'manifest'};lamp.publish(out,files);times={p.name:p.stat().st_mtime_ns for p in out.iterdir()};lamp.publish(out,files);self.assertEqual(times,{p.name:p.stat().st_mtime_ns for p in out.iterdir()})
            (out/'manifest.json').write_bytes(b'conflict');(out/'catalog.racer').unlink()
            with self.assertRaisesRegex(Exception,'output_conflict'):lamp.publish(out,files)
            self.assertFalse((out/'catalog.racer').exists());self.assertEqual((out/'manifest.json').read_bytes(),b'conflict')
            (root/'link').symlink_to(out,target_is_directory=True)
            with self.assertRaisesRegex(ValueError,'symlink_refused'):lamp.publish(root/'link',files)
            (root/'source-link').symlink_to(root/'missing')
            with self.assertRaisesRegex(Exception,'symlink_refused'):lamp.pinned(root/'source-link','attributes')
            (out/'manifest.json').unlink();(out/'manifest.json').symlink_to(root/'missing')
            with self.assertRaisesRegex(Exception,'symlink_refused'):lamp.publish(out,files)
    def test_pin_and_budget_fail_before_publication(self):
        with self.assertRaisesRegex(ValueError,'input_pin_original'):lamp.derive(b'bad',b'',b'',b'',b'')
        with tempfile.TemporaryDirectory()as t:
            with self.assertRaisesRegex(ValueError,'output_directory_budget'):lamp.publish(Path(t).resolve(),{'catalog.racer':b'x'*(32*1024**2+1)})

@unittest.skipUnless(ACTUAL,'use --actual for pinned native-source/consumer derivative checks')
class Actual(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        paths=[ROOT/'assets/local/carmodels/objects'/f"{lamp.PINS['original']}.glb",ROOT/'assets/local/vehicles'/f"{lamp.PINS['prepared']}.glb",ROOT/'assets/local/vehicles'/f"{lamp.PINS['prepared']}.vehicle",Path('/private/tmp/racer-lamp-uv-qualification/source-attributes.json'),Path('/private/tmp/racer-lamp-qualification/shader28-e4ec3780.png')]
        cls.inputs=[lamp.pinned(p,key)for p,key in zip(paths,lamp.PINS)];cls.files=lamp.derive(*cls.inputs);cls.mesh=next(v for k,v in cls.files.items()if k.endswith('.glb'));cls.before,cls.oldblob=lamp.unpack(cls.inputs[1]);cls.doc,cls.blob=lamp.unpack(cls.mesh);cls.manifest=json.loads(cls.files['manifest.json'])
    def test_entire_source_prefix_nodes_and_materials(self):
        self.assertEqual(self.blob[:len(self.oldblob)],self.oldblob);self.assertEqual(self.doc['nodes'],self.before['nodes']);self.assertEqual(self.doc['scenes'],self.before['scenes']);self.assertEqual(self.doc['materials'][:141],self.before['materials']);self.assertEqual(self.doc['accessors'][:len(self.before['accessors'])],self.before['accessors']);self.assertEqual(self.doc['bufferViews'][:len(self.before['bufferViews'])],self.before['bufferViews'])
    def test_lamp_partitions_preserve_every_ordered_triangle_and_vertex_stream(self):
        for change in self.manifest['partitions']:
            mi,pi=change['prepared_mesh'],change['prepared_primitive'];original=self.before['meshes'][mi]['primitives'][pi];source_indices=[x[0]for x in lamp.rows(self.before,self.oldblob,original['indices'])];seen=[]
            for part in change['partitions']:
                p=self.doc['meshes'][mi]['primitives'][part['new_primitive']];seen.extend(part['triangles']);self.assertEqual([x[0]for x in lamp.rows(self.doc,self.blob,p['indices'])],[source_indices[t*3+k]for t in part['triangles']for k in range(3)])
                self.assertEqual({k:v for k,v in p['attributes'].items()if k!='_RACER_NATIVE_LAMP_DATA'},original['attributes']);selector=lamp.rows(self.doc,self.blob,p['attributes']['_RACER_NATIVE_LAMP_DATA'])
                for t in part['triangles']:self.assertEqual({selector[i]for i in source_indices[t*3:t*3+3]},{(part['id'],1.)})
            self.assertEqual(sorted(seen),list(range(len(source_indices)//3)))
    def test_only_authorized_material_bindings_change(self):
        targets={(x['prepared_mesh'],x['prepared_primitive']):x for x in self.manifest['partitions']};paint={int(k):v for k,v in self.manifest['paint_material_clones'].items()};lens={int(k):v for k,v in self.manifest['lens_material_clones'].items()};self.assertEqual(len(paint),8);self.assertEqual(len(lens),2)
        for mi,m in enumerate(self.before['meshes']):
            cursor=0
            for pi,p in enumerate(m['primitives']):
                if (mi,pi)in targets:cursor+=len(targets[mi,pi]['partitions']);continue
                expected=copy.deepcopy(p)
                if p['material']in paint:expected['material']=paint[p['material']]
                elif p['material']in lens:expected['material']=lens[p['material']]
                self.assertEqual(self.doc['meshes'][mi]['primitives'][cursor],expected);cursor+=1
        for old,new in lens.items():
            self.assertEqual(self.before['materials'][old]['extras']['sourceShader'],'bumpedglass');m=self.doc['materials'][new];self.assertEqual(m['alphaMode'],'BLEND');self.assertEqual(m['pbrMetallicRoughness']['baseColorFactor'][3],.55 if 'taillight0' in m['name'] else .08)
        for old,new in paint.items():
            m=self.doc['materials'][new];self.assertEqual(m['extensions']['KHR_materials_clearcoat']['clearcoatRoughnessFactor'],.1);self.assertEqual(m['pbrMetallicRoughness']['roughnessFactor'],.24);self.assertEqual(m['pbrMetallicRoughness']['metallicFactor'],.25)
        for change in self.manifest['partitions']:
            for part in change['partitions']:
                p=self.doc['meshes'][change['prepared_mesh']]['primitives'][part['new_primitive']];m=self.doc['materials'][p['material']];self.assertNotIn('emissiveFactor',m);self.assertEqual(m['pbrMetallicRoughness']['metallicFactor'],0);self.assertEqual(m['pbrMetallicRoughness']['roughnessFactor'],.16)
    def test_illumination_png_and_descriptor_identity(self):
        image=self.doc['images'][-1];view=self.doc['bufferViews'][image['bufferView']];self.assertEqual(bytes(self.blob[view['byteOffset']:view['byteOffset']+view['byteLength']]),self.inputs[4]);self.assertEqual(Image.open(io.BytesIO(self.inputs[4])).size,(128,128))
        old=self.inputs[2].decode().splitlines();new=next(v for k,v in self.files.items()if k.endswith('.vehicle')).decode().splitlines();self.assertEqual([x for x in old if x.split(' ',1)[0]not in ('id','name','mesh','sha256')],[x for x in new if x.split(' ',1)[0]not in ('id','name','mesh','sha256')]);self.assertIn('source_sha256 '+lamp.PINS['original'],new);self.assertIn('name "2006 Nissan 350Z Roadster"',new)
    def test_authored_rims_change_only_qualified_material_references(self):
        files=lamp.derive(*self.inputs,authored_rims=True);raw=next(v for k,v in files.items()if k.endswith('.glb'));doc,blob=lamp.unpack(raw)
        self.assertEqual(blob,self.blob);self.assertEqual(doc['nodes'],self.doc['nodes']);self.assertEqual(doc['materials'][:-1],self.doc['materials'])
        mapping=doc['extras']['racerAuthoredLampPreview']['authored_rim_material_clones'];self.assertEqual(mapping,{'138':len(doc['materials'])-1})
        new=len(doc['materials'])-1;count=0
        for before,after in zip(self.doc['meshes'],doc['meshes']):
            expected=copy.deepcopy(before)
            for primitive in expected['primitives']:
                if primitive.get('material')==138:primitive['material']=new;count+=1
            self.assertEqual(expected,after)
        self.assertEqual(count,1) # One shared mesh, four independently bound wheel mounts.
        mounts=[n for n in doc['nodes']if 'mesh'in n and any(p.get('material')==new for p in doc['meshes'][n['mesh']]['primitives'])]
        self.assertEqual(len(mounts),4);material=doc['materials'][new]
        self.assertEqual(material['extras']['racerAuthoredAluminum']['original_material'],self.before['materials'][138])
        self.assertEqual(material['pbrMetallicRoughness']['metallicFactor'],.9)
        self.assertEqual(doc['materials'][139:141],self.before['materials'][139:141])
    def test_authored_paint_exact_scope_palette_and_preservation(self):
        for palette,expected in [('silver',[.36,.42,.48,1]),('crimson',[.42,.008,.012,1])]:
            files=lamp.derive(*self.inputs,authored_paint=palette)
            doc,blob=lamp.unpack(next(v for k,v in files.items() if k.endswith('.glb')))
            self.assertEqual(blob,self.blob)
            for key in ('nodes','scenes','meshes','images','textures','samplers','accessors','bufferViews'):
                self.assertEqual(doc[key],self.doc[key])
            self.assertEqual(doc['materials'][:141],self.before['materials'])
            mapping=self.manifest['paint_material_clones'];self.assertEqual({int(k) for k in mapping},{0,28,35,47,64,84,91,120})
            changed=[]
            for i,(old,new) in enumerate(zip(self.doc['materials'],doc['materials'])):
                if old!=new:changed.append(i)
            self.assertEqual(set(changed),set(mapping.values()))
            for old,new in mapping.items():
                material=doc['materials'][new];self.assertEqual(material['name'],self.before['materials'][int(old)]['name'])
                self.assertEqual(material['pbrMetallicRoughness']['baseColorFactor'],expected)
                self.assertEqual(material['pbrMetallicRoughness']['metallicFactor'],0)
                self.assertEqual(material['pbrMetallicRoughness']['roughnessFactor'],.24)
                self.assertEqual(material['extensions'],self.doc['materials'][new]['extensions'])
                self.assertEqual(material['extras']['racerAuthoredPaint']['original_preview_material'],self.before['materials'][int(old)])
            # Optional rim finish composes without affecting geometry or the paint scope.
            rims=lamp.derive(*self.inputs,authored_rims=True,authored_paint=palette)
            rd,rb=lamp.unpack(next(v for k,v in rims.items() if k.endswith('.glb')))
            self.assertEqual(rb,blob);self.assertEqual(rd['materials'][:-1],doc['materials'])
        self.assertEqual(lamp.derive(*self.inputs),self.files)
        legacy=lamp.derive(*self.inputs,authored_rims=True)
        self.assertEqual(json.loads(legacy['manifest.json'])['mesh_sha256'],'7722f262d79758d1ad0d45cbc105d915bd8bad44c914e9ed01bec4199a690008')
        with self.assertRaisesRegex(ValueError,'authored_paint_palette'):lamp.derive(*self.inputs,authored_paint='guess')

    def test_authored_paint_rejects_lookalike_or_changed_binding(self):
        original_pin=lamp.PINS['prepared']
        try:
            for mutation,reason in [('name','paint_family_identity'),('bucket','paint_bucket_or_alpha_identity'),('factor','paint_preview_factor_identity')]:
                doc=copy.deepcopy(self.before)
                if mutation=='name':doc['materials'][0]['name']+='lookalike'
                elif mutation=='bucket':doc['materials'][0]['extras']['sourceDrawBucket']=3
                else:doc['materials'][0]['pbrMetallicRoughness']['baseColorFactor']=[1,1,1,1]
                data=lamp.pack(doc,self.oldblob);lamp.PINS['prepared']=lamp.sha(data);inputs=self.inputs[:];inputs[1]=data
                with self.assertRaisesRegex(ValueError,reason):lamp.derive(*inputs,authored_paint='silver')
        finally:lamp.PINS['prepared']=original_pin

    def test_authored_trim_exact_instances_source_proof_and_scope(self):
        base=lamp.derive(*self.inputs,authored_rims=True,authored_paint='crimson')
        before,oldblob=lamp.unpack(next(v for k,v in base.items()if k.endswith('.glb')))
        files=lamp.derive(*self.inputs,authored_rims=True,authored_paint='crimson',authored_trim=True)
        doc,blob=lamp.unpack(next(v for k,v in files.items()if k.endswith('.glb')))
        self.assertEqual(blob,oldblob)
        for key in ('nodes','scenes','images','textures','samplers','accessors','bufferViews'):
            self.assertEqual(doc[key],before[key])
        self.assertEqual(doc['materials'][:len(before['materials'])],before['materials'])
        proof=doc['extras']['racerAuthoredLampPreview']['authored_trim'];mapping={int(k):v for k,v in proof['material_clones'].items()}
        self.assertEqual(set(mapping),{38,50,67,90});self.assertEqual(len(doc['materials']),len(before['materials'])+4)
        count=0
        for original,actual in zip(before['meshes'],doc['meshes']):
            expected=copy.deepcopy(original)
            for primitive in expected['primitives']:
                if primitive['material']in mapping:primitive['material']=mapping[primitive['material']];count+=1
            self.assertEqual(actual,expected)
        self.assertEqual(count,5)
        self.assertEqual(sum(len(p['bindings'])for p in proof['proof']),5)
        for old,new in mapping.items():
            material=doc['materials'][new];pbr=material['pbrMetallicRoughness']
            self.assertEqual(material['extras']['racerAuthoredTrim']['original_preview_material'],self.before['materials'][old])
            self.assertEqual(pbr['metallicFactor'],0 if old==38 else .95)
            self.assertEqual(pbr['roughnessFactor'],.24 if old==38 else .22)
            self.assertEqual(pbr['baseColorFactor'],[.12,.14,.16,1]if old==38 else[.45,.45,.45,1])
        self.assertEqual(json.loads(base['manifest.json'])['mesh_sha256'],'ad5c5cce1e64656cdbb5da3e6830959df7fea159152d2e355154e814ad5568b9')
        silver=lamp.derive(*self.inputs,authored_rims=True,authored_paint='silver')
        self.assertEqual(json.loads(silver['manifest.json'])['mesh_sha256'],'51276641f5a2e9ff54f6f524689345ba34f9b26b0814974888d70ecf88a94045')

    def test_authored_trim_rejects_changed_node_and_uv(self):
        original_pin=lamp.PINS['prepared']
        try:
            for mutation,reason in [('node','trim_node_identity'),('uv','trim_geometry_uv_identity')]:
                doc=copy.deepcopy(self.before);blob=bytearray(self.oldblob)
                if mutation=='node':doc['nodes'][23]['name']+='lookalike'
                else:
                    p=doc['meshes'][doc['nodes'][23]['mesh']]['primitives'][0];a=doc['accessors'][p['attributes']['TEXCOORD_0']];v=doc['bufferViews'][a['bufferView']];struct.pack_into('<f',blob,v.get('byteOffset',0)+a.get('byteOffset',0),123)
                data=lamp.pack(doc,blob);lamp.PINS['prepared']=lamp.sha(data);inputs=self.inputs[:];inputs[1]=data
                with self.assertRaisesRegex(ValueError,reason):lamp.derive(*inputs,authored_trim=True)
        finally:lamp.PINS['prepared']=original_pin

    def test_all_input_hashes_and_derivative_budget(self):
        for index,key in enumerate(lamp.PINS):
            inputs=self.inputs[:];inputs[index]=inputs[index]+b'changed'
            with self.assertRaisesRegex(ValueError,'input_pin_'+key):lamp.derive(*inputs)
        old=lamp.OUTPUT_LIMIT
        try:
            lamp.OUTPUT_LIMIT=16
            with self.assertRaisesRegex(ValueError,'output_budget'):lamp.derive(*self.inputs)
        finally:lamp.OUTPUT_LIMIT=old

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--actual',action='store_true');a,rest=parser.parse_known_args()
    # Apply the optional integration setting after class definition without hiding failures.
    if a.actual:Actual.__unittest_skip__=False
    unittest.main(argv=[__file__]+rest)
