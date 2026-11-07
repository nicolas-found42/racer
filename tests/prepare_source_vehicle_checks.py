#!/usr/bin/env python3
import copy,json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from prepare_source_vehicle import prepare,metadata,transform,vector
from prepare_gt4_vehicle import unpack,pack,Geometry,PreparationError
ROOT=Path(__file__).resolve().parents[1]/'experiments/2026-11-05-other-car-families/output/assets/objects'
PILOTS=[('1132d3710c2b12310f47807298fe7cff483c32085d88c65a005d3fd3eb736c83','gran-turismo/simulation/_a-a7r'),('b0e50f8c609b770ece74ea511312a11e7b79f6e6fff6331da7ff249ba6328806','midnight-club-3-remix/vp_corvettez06_03')]
class AdapterChecks(unittest.TestCase):
 def test_transform_inverse_scale_normal(self):
  t,s,r=transform({'translation':[1,2,3],'rotation':[0,0,0,1],'scale':[2,3,4]})
  self.assertEqual(vector([1,1,1],s,r,True,t),[3,5,-7])
 def test_pilots_and_enclosure(self):
  for sha,cid in PILOTS:
   source=(ROOT/(sha+'.glb')).read_bytes();out,desc,receipt=prepare(source,cid,'Pilot');d,b=unpack(out);g=Geometry(d,b)
   self.assertEqual(receipt['source_sha256'],sha);self.assertTrue(desc.startswith('RACER_VEHICLE 1\n'));self.assertEqual(len(receipt['wheels']),4)
   self.assertGreater(receipt['wheelbase'],.5);self.assertEqual(receipt['units']['scale_applied'],1.0)
   self.assertEqual(d['extras']['racerPreparation']['units'],receipt['units'])
   if cid.startswith('midnight-club-3-remix/'):
    self.assertEqual(receipt['units']['native_units'],'unverified');self.assertEqual(receipt['units']['chosen_import_factor'],1.0);self.assertIn('assumption',receipt['units']['factor_status']);self.assertEqual(receipt['canonical_scale']['status'],'source_manufacturer_dimension_conflict')
   else:
    self.assertIn('/4096',receipt['units']['source_glb']);self.assertIn('unproven',receipt['units']['physical_unit_parity'])
   for ni,wi in receipt['groups']:
    n=d['nodes'][ni];self.assertNotIn('rotation',n);self.assertNotIn('translation',n)
    for p in d['meshes'][n['mesh']]['primitives']:
     for row in g.values(p['attributes']['POSITION']):
      if wi>=0:
       w=receipt['wheels'][wi];c=w['center'];y=row[1]+receipt['ground_lift'];self.assertLessEqual(((y-c[1])**2+(row[2]-c[2])**2)**.5,w['radius']+1e-6);self.assertLessEqual(abs(row[0]-c[0]),w['width']/2+1e-6)
   original,_=unpack(source)
   # Material definitions and embedded source images are never recolored or replaced.
   self.assertEqual(original['materials'],d['materials']);self.assertEqual(original.get('images'),d.get('images'))
 def test_metadata_tampering(self):
  for sha,cid in PILOTS:
   d,b=unpack((ROOT/(sha+'.glb')).read_bytes())
   with self.assertRaises(PreparationError):prepare(pack(d,b),'wrong/id','Pilot')
   if cid.startswith('gran-turismo/'):
    d['nodes'][0]['extras']['nativePivotPositionMetres'][0]+=.1
   else:d['nodes'][10]['extras']['nativeBone']=0
   with self.assertRaises(PreparationError):prepare(pack(d,b),cid,'Pilot')
 def test_redline_source_config(self):
  root=ROOT.parent.parent;source=(ROOT/'cbcb46815ec2ecdb94f3ca86fb1e0fbf126e18adf1637b4c0fa284405e76dbc4.glb').read_bytes();config=(root/'55ford.car').read_bytes();cid='redline/base/55ford_e0dfc360f3ef'
  out,desc,r=prepare(source,cid,'Pickup',config)
  self.assertFalse(unpack(out)[0]['extras']['racerPreparation']['mirror_z']);self.assertAlmostEqual(r['wheelbase'],2.87)
  self.assertEqual(r['units']['native_units'],'metres');self.assertIn('explicit native configuration',r['units']['source_glb'])
  self.assertEqual(r['wheel_geometry'][0]['source_dimensions'],(.38,.205))
  with self.assertRaises(PreparationError):prepare(source,cid,'Pickup')
  with self.assertRaises(PreparationError):prepare(source,cid,'Pickup',config+b' ')
 def test_duplicate_and_zero_transform(self):
  sha,cid=PILOTS[1];d,b=unpack((ROOT/(sha+'.glb')).read_bytes());d['scenes'][0]['nodes'].append(0)
  with self.assertRaises(PreparationError):prepare(pack(d,b),cid,'Pilot')
  with self.assertRaises(PreparationError):transform({'scale':[0,1,1]})
if __name__=='__main__':unittest.main()
