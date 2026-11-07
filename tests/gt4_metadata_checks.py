#!/usr/bin/env python3
"""Independent synthetic format checks and pinned EU corpus joins; no network."""
import copy,hashlib,json,struct,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import gt4_metadata as g
import audit_gt4_coverage as audit

def idi(keys,table=6):
    texts=bytearray();entries=bytearray()
    for key in keys:
        entries+=struct.pack('<II',len(texts),key);texts+=b'\0\0'+str(key).encode()+b'\0'
    return b'GTID'+struct.pack('<III',len(keys),0,table)+entries+texts

def compressed(decoded,width=3,template=b'abc'):
    # A complete eight-bit codebook makes encoded symbols transparent. LSB-first
    # nine-bit fixtures separately exercise the decoder's non-lookup path.
    lookup=b''.join(bytes((i,8))for i in range(256))
    book=struct.pack('<II',520,0)+lookup
    templates=struct.pack('<II',8+len(template),0)+template
    return b'GTDB'+struct.pack('<HHII',1,0,1,width)+struct.pack('<II',7,0)+book+templates+bytes((len(decoded),))+decoded

class Checks(unittest.TestCase):
    def test_raw_rows_and_duplicate_ids(self):
        data=b'GTDB'+struct.pack('<HHII',0,0,2,3)+struct.pack('<IIII',7,0,8,3)+b'abcdef'
        self.assertEqual(g.Table(data,idi([7,8])).rows(),[(7,b'abc'),(8,b'def')])
        with self.assertRaisesRegex(ValueError,'duplicate_row_id'):g.unique([(1,b'a'),(1,b'b')])
        with self.assertRaisesRegex(ValueError,'duplicate_label_id'):g.labels(idi([1,1]))
    def test_compression_modes(self):
        for encoded,result in [(b'\0',b'abc'),(b'\x40XYZ',b'XYZ'),(b'\x80\x05XZ',b'XbZ')]:
            self.assertEqual(g.Table(compressed(encoded),idi([7])).rows(),[(7,result)])
    def test_long_huffman_code(self):
        book=struct.pack('<II',528,1)+bytes(512)+struct.pack('<BBHI',9,0,0,0)
        data=b'GTDB'+struct.pack('<HHII',1,0,1,3)+struct.pack('<II',7,0)+book+struct.pack('<II',11,0)+b'abc'+b'\x01\0\0'
        self.assertEqual(g.Table(data,idi([7])).rows(),[(7,b'abc')])
        with self.assertRaisesRegex(ValueError,'huffman_bits_outside_row'):g.Table(data[:-1],idi([7])).rows()
    def test_malformed_patches_and_templates(self):
        for encoded,reason in [(b'\x80\x01','patch_value_short'),(b'\x80\0X','patch_unused_symbols'),(b'\x3f','template_slot'),(b'\xc0','compression_kind'),(b'\x40X','literal_row_short')]:
            with self.subTest(reason=reason),self.assertRaisesRegex(ValueError,reason):g.Table(compressed(encoded),idi([7])).rows()
    def test_limits_offsets_and_pins(self):
        data=b'GTDB'+struct.pack('<HHII',0,0,100000,4096)
        with self.assertRaisesRegex(ValueError,'decoded_table_budget'):g.Table(data,idi([7]))
        data=bytearray(compressed(b'\0'));struct.pack_into('<I',data,20,1000000)
        with self.assertRaisesRegex(ValueError,'row_offsets'):g.Table(data,idi([7]))
        with tempfile.TemporaryDirectory()as folder:
            p=Path(folder)/'a';p.write_bytes(b'abc')
            with self.assertRaisesRegex(ValueError,'input_pin'):g.read(p,'0'*64)
            link=Path(folder)/'b';link.symlink_to(p)
            with self.assertRaisesRegex(ValueError,'regular_input'):g.read(link)
    def test_strings(self):
        data=b'GTST'+struct.pack('<III',2,1,0)+struct.pack('<II',0,6)+b'\0\0one\0\0\0two\0'
        self.assertEqual(g.strings(data),['one','two'])
        with self.assertRaisesRegex(ValueError,'string_terminator'):g.strings(data[:-1])
    def test_pinned_actual_corpus(self):
        out=ROOT/'experiments/2026-11-06-gt4-coverage/output'
        if not(out/'metadata-acquisition.json').exists():self.skipTest('retained corpus unavailable')
        report=g.join_specs(out/'specdb-eu',out/'metadata-acquisition.json');models=report['models']
        self.assertEqual(len(models),730)
        self.assertEqual(report['source_build']['sha256'],'efcb2ac8428be5f4c67f3d5e97f941f4c267015ab92ea0cc1c624d75cb830ef5')
        for code,label,wb,front,layout in [('benz0001','patent_motor_wagen_886',1450,1449,2),('dmlr0001','motor_carriage_886',1300,50,0),('daih0017','midget_mp5_63',1905,151,2)]:
            m=models[code];self.assertEqual((m['label'],m['chassis_raw']['wheelbase'],m['chassis_raw']['treadF'],m['chassis_flags']['WheelLayout']),(label,wb,front,layout))
        catalog=json.loads((ROOT/'experiments/2026-11-05-car-models/output/source-catalog.json').read_bytes())
        self.assertEqual(set(models),{r['code']for r in catalog['cars']if r['game']=='gran-turismo-4'})
    def test_audit_missing_duplicate_and_build_joins(self):
        out=ROOT/'experiments/2026-11-06-gt4-coverage/output'
        if not(out/'metadata-acquisition.json').exists():self.skipTest('retained corpus unavailable')
        catalog=json.loads(g.read(ROOT/'experiments/2026-11-05-car-models/output/source-catalog.json',audit.CATALOG_SHA))
        index=json.loads(g.read(out/'cars-index.json',audit.INDEX_SHA));decoded=g.join_specs(out/'specdb-eu',out/'metadata-acquisition.json')
        result=audit.audit(catalog,index,decoded)
        self.assertEqual(result['counts']['adapter_dispatch_matches'],730)
        self.assertEqual(result['counts']['models_prepared_by_this_audit'],0)
        self.assertEqual(result['raw_WheelLayout_codes']['2'],['benz0001','daih0017'])
        nsx=next(r for r in result['rows']if r['code']=='acra0014')
        self.assertEqual(nsx['placement_hypothesis']['front_track_m'],1.508)
        bad=copy.deepcopy(decoded);del bad['models']['benz0001']
        with self.assertRaisesRegex(ValueError,'missing_or_extra_model_join'):audit.audit(catalog,index,bad)
        bad=copy.deepcopy(index);bad['vehicles'].append(bad['vehicles'][0])
        with self.assertRaisesRegex(ValueError,'duplicate_id'):audit.audit(catalog,bad,decoded)
        bad=copy.deepcopy(decoded);bad['source_build']['boot']='US'
        with self.assertRaisesRegex(ValueError,'source_build_mismatch'):audit.audit(catalog,index,bad)
        with tempfile.TemporaryDirectory()as d:
            p=Path(d)/'manifest.json';p.write_text('{}')
            with self.assertRaisesRegex(ValueError,'input_pin'):g.join_specs(out/'specdb-eu',p)

if __name__=='__main__':unittest.main()
