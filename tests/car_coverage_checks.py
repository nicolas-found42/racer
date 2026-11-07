import contextlib,hashlib,io,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import car_coverage as c

class Checks(unittest.TestCase):
    def car(self,game='gran-turismo-4',code='fixture'):
        return {'id':game+'/'+code,'game':game,'code':code,'file':game+'/'+code+'.glb','sha256':'a'*64,'bytes':100,'source_profile':'gt4-ps2-static-car-v2'}
    def review(self,car,eligible=True):
        return {'model_id':car['id'],'source_sha256':car['sha256'],'prepared_sha256':'b'*64,'player_eligible':eligible,'role':'player' if eligible else 'research-candidate'}
    def test_dispatch_and_review_do_not_imply_installation(self):
        car=self.car();row=c.assemble([car],[self.review(car)],{})[0]
        self.assertTrue(row['adapter_dispatch_match']);self.assertTrue(row['reviewed_player_preparation'])
        self.assertEqual(row['row_origin'],'public_catalog')
        self.assertIsNone(row['installed_prepared_sha256']);self.assertIn('not_rerun',row['runtime_acceptance'])
    def test_stale_join_and_duplicate_review_are_errors(self):
        car=self.car();review=self.review(car);review['source_sha256']='c'*64
        row=c.assemble([car],[review],{})[0]
        self.assertEqual(row['source_sha256'],'a'*64);self.assertEqual(row['preparation_input_sha256'],'c'*64)
        self.assertIn('derivation_not_validated',row['source_relationship'])
        with self.assertRaisesRegex(ValueError,'duplicate_prepared_model'):c.assemble([car],[review,review],{})
        with self.assertRaisesRegex(ValueError,'metadata_source_mismatch'):c.assemble([car],[],{},{car['id']:{'preview_sha256':'d'*64}})
    def test_traffic_and_exclusions_remain_distinct(self):
        traffic=self.car('midnight-club-los-angeles','va_fixture');excluded=self.car('redline')
        rows=c.assemble([traffic,excluded],[],{});self.assertEqual(len(rows),1);self.assertEqual(rows[0]['source_role'],'traffic_deferred')
        with self.assertRaisesRegex(ValueError,'traffic_player_conflict'):c.assemble([traffic],[self.review(traffic)],{})
    def test_repaired_revision_never_relabels_installed_bytes(self):
        car=self.car();review=self.review(car);actual={car['id']:{'source_sha256':car['sha256'],'mesh_sha256':'c'*64}}
        row=c.assemble([car],[review],actual)[0];self.assertEqual(row['reviewed_prepared_sha256'],'b'*64);self.assertEqual(row['installed_prepared_sha256'],'c'*64)
    def test_retired_review_does_not_hide_installed_local_bytes(self):
        ident='juiced-2/retained';actual={ident:{'source_sha256':'a'*64,'mesh_sha256':'c'*64}}
        row=c.assemble([],[],actual)[0]
        self.assertEqual(row['model_id'],ident);self.assertEqual(row['installed_prepared_sha256'],'c'*64)
        self.assertEqual(row['row_origin'],'installed_only')
        self.assertFalse(row['reviewed_player_preparation']);self.assertIn('review_record_unavailable',row['runtime_acceptance'])
    def test_local_traffic_cannot_bypass_public_namespace_policy(self):
        car=self.car('midnight-club-los-angeles','va_unlisted')
        with self.assertRaisesRegex(ValueError,'traffic_player_conflict'):c.assemble([],[self.review(car)],{})
        row=c.assemble([],[self.review(car,False)],{})[0];self.assertEqual(row['source_role'],'traffic_deferred');self.assertEqual(row['row_origin'],'local_preparation')
        row=c.assemble([],[],{car['id']:{'source_sha256':'a'*64,'mesh_sha256':'b'*64}})[0]
        self.assertEqual(row['source_role'],'traffic_deferred');self.assertFalse(row['reviewed_player_preparation'])
    def test_reviewed_player_requires_consistent_role(self):
        car=self.car();review=self.review(car);review['role']='research-candidate'
        with self.assertRaisesRegex(ValueError,'review_role_conflict'):c.assemble([car],[review],{})
    def test_report_hashes_the_input_bytes_it_actually_parsed(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp).resolve();prepared=root/'prepared.json';audit=root/'audit.json';out=root/'report.json'
            car=self.car();prepared.write_text(json.dumps({'vehicles':[self.review(car)]}))
            audit.write_text(json.dumps({'catalog_sha256':c.source.CATALOG_SHA,'rows':[]}))
            originals={p:p.read_bytes() for p in (prepared,audit)};read=c.install.regular_bytes
            def read_then_replace(path,limit):
                data=read(path,limit)
                if Path(path) in originals:Path(path).write_text('{}')
                return data
            args=['car_coverage.py','--prepared',str(prepared),'--gt4-audit',str(audit),'--output',str(out)]
            with patch.object(sys,'argv',args),patch.object(c.source,'load_catalog',return_value=[car]),patch.object(c.install,'regular_bytes',side_effect=read_then_replace),patch.object(c,'installation',return_value=({}, {'state':'unavailable'})),contextlib.redirect_stdout(io.StringIO()):c.main()
            result=json.loads(out.read_text());self.assertTrue(result['models'][0]['reviewed_player_preparation'])
            self.assertEqual(result['inputs']['prepared_inventory_sha256'],hashlib.sha256(originals[prepared]).hexdigest())
            self.assertEqual(result['inputs']['gt4_audit_sha256'],hashlib.sha256(originals[audit]).hexdigest())

if __name__=='__main__':unittest.main()
