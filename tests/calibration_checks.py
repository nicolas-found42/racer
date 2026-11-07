import hashlib,json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from calibrate_vehicle import adapt
from prepare_gt4_vehicle import pack,unpack

class Calibration(unittest.TestCase):
    def test_uniform_transform_preserves_source_binary_and_pivots(self):
        d={'asset':{'version':'2.0'},'scene':0,'scenes':[{'nodes':[0]}],'nodes':[{'name':'source','translation':[1,2,3]}],'buffers':[{'byteLength':4}]};raw=pack(d,b'ABCD');sha=hashlib.sha256(raw).hexdigest()
        descriptor='RACER_VEHICLE 1\nid "vehicle-'+sha+'"\nname "source"\nmesh "'+sha+'.glb"\nsha256 '+sha+'\nsource_sha256 '+'a'*64+'\nbody -1 0 -3 1 2 3\n'+''.join('wheel '+label+' '+str(x)+' .4 '+str(z)+' .4 .2\n' for label,x,z in [('FL',-1,1.5),('FR',1,1.5),('RL',-1,-1.5),('RR',1,-1.5)])+'groups 1\ngroup 0 -1\n'
        c={'canonical_id':'fixture','source':'manufacturer','applicability':'fixture','model':'Fixture','nominal':{'wheelbase':2.7}}
        out,text,r=adapt(raw,descriptor,c,sha);doc,binary=unpack(out)
        self.assertEqual(binary,b'ABCD');self.assertEqual(doc['nodes'][0],d['nodes'][0]);self.assertEqual(doc['nodes'][1]['children'],[0])
        self.assertEqual(doc['nodes'][1]['scale'],[.9]*3);self.assertEqual(r['factor'],.9)
        wheels=[line.split() for line in text.splitlines() if line.startswith('wheel')]
        self.assertAlmostEqual(float(wheels[0][4]),1.35);self.assertAlmostEqual(float(wheels[0][5]),.36)
        self.assertIn('source_sha256 '+'a'*64,text)
        with self.assertRaises(ValueError):adapt(raw,descriptor,c,'0'*64)
        c['nominal']['wheelbase']=30
        with self.assertRaises(ValueError):adapt(raw,descriptor,c,sha)
if __name__=='__main__':unittest.main()
