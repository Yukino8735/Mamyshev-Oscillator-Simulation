from __future__ import annotations
import csv,hashlib,json,sqlite3,sys,tempfile,unittest
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'reference'))
from oracle import FEATURES,TARGETS,load_recipe,evaluate,validate,design_id
from metrics_v4 import report,joint_log_calibration,prediction_intervals,accuracy_gate,wilson
from models_v4 import LogSurrogate
from build_release import build
ROLES={'train':'data/train_pool_4096.csv','validation':'data/validation_1024.csv','calibration':'evaluation_only/calibration_1024.csv','test':'evaluation_only/test_1536.csv','challenge':'evaluation_only/challenge_512.csv'}
def load(p):
    with p.open(newline='') as f:return list(csv.DictReader(f))
class ReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c=load_recipe();cls.p=json.loads((ROOT/'configs/accuracy_protocol.json').read_text());cls.rows={k:load(ROOT/v) for k,v in ROLES.items()}
    def test_role_sizes_and_uniqueness(self):
        self.assertEqual({k:len(v)for k,v in self.rows.items()},{'train':4096,'validation':1024,'calibration':1024,'test':1536,'challenge':512})
        ids=[r['design_id']for v in self.rows.values()for r in v];self.assertEqual(len(ids),len(set(ids)))
    def test_every_label_recomputed(self):
        for v in self.rows.values():
            for r in v:
                d={k:float(r[k])for k in FEATURES};validate(d,self.c);self.assertEqual(design_id(d),r['design_id']);expected=evaluate(d,self.c)
                for k in TARGETS:self.assertEqual(float(r[k]),expected[k]);self.assertTrue(np.isfinite(expected[k])and expected[k]>0)
    def test_source_and_formula_unchanged(self):
        ident=json.loads((ROOT/'provenance/V3_ORACLE_IDENTITY.json').read_text())
        for p,h in ident['files'].items():self.assertEqual(hashlib.sha256((ROOT/p).read_bytes()).hexdigest(),h)
        for v in self.rows.values():
            self.assertTrue(all(r['backend_id']=='mamyshev_repository_guided_synthetic_v3'and r['source_kind']=='repository_guided_synthetic'for r in v))
    def test_preserved_v3_train_validation(self):
        for role,name in [('train','train_pool_512.csv'),('validation','validation_128.csv')]:
            old=load(ROOT/'provenance'/name)
            for a,b in zip(old,self.rows[role]):
                for k in ['design_id','role','region','order_in_role',*FEATURES,*TARGETS]:self.assertEqual(a[k],b[k])
    def test_fresh_holdout_and_anchor_exclusion(self):
        legacy=json.loads((ROOT/'provenance/v3_design_ids.json').read_text());old=set(i for v in legacy.values()for i in v)
        for role in ['calibration','test','challenge']:self.assertTrue(old.isdisjoint(r['design_id']for r in self.rows[role]))
        anchor=design_id(self.c['reference_design']);self.assertNotIn(anchor,[r['design_id']for v in self.rows.values()for r in v])
    def test_candidates_have_no_labels_and_are_disjoint(self):
        rows=load(ROOT/'data/candidates_unlabeled_20000.csv');self.assertEqual(len(rows),20000);ids={r['design_id']for r in rows};self.assertEqual(len(ids),20000)
        self.assertTrue(set(TARGETS).isdisjoint(rows[0]));self.assertTrue(ids.isdisjoint(r['design_id']for v in self.rows.values()for r in v))
    def test_solver_plan_is_not_run(self):
        rows=load(ROOT/'plans/solver_designs_8192.csv');self.assertEqual(len(rows),8192)
        for r in rows:
            self.assertEqual(r['solver_status'],'not_run')
            for k in TARGETS:self.assertEqual(r[k],'')
    def test_nested_train_orders(self):
        m=json.loads((ROOT/'data/training_orders.json').read_text());truth={r['design_id']for r in self.rows['train']};lookup={r['design_id']:r for r in self.rows['train']}
        for order in m['orders'].values():
            self.assertEqual(len(order),4096);self.assertEqual(set(order),truth)
            for n in m['sizes']:self.assertEqual(sum(lookup[i]['region']=='historical_core'for i in order[:n]),n//2)
    def test_db_separation_and_integrity(self):
        for p,expected in [('data/development.sqlite',{'train','validation'}),('evaluation_only/evaluation.sqlite',{'calibration','test','challenge'})]:
            db=sqlite3.connect(f'file:{ROOT/p}?mode=ro',uri=True);self.assertEqual(db.execute('pragma integrity_check').fetchone()[0],'ok');self.assertEqual({r[0]for r in db.execute('select distinct role from designs')},expected);self.assertEqual(db.execute('select count(*)from evaluations').fetchone()[0],sum(len(self.rows[r])for r in expected));db.close()
    def test_error_metrics_and_near_zero(self):
        y=np.array([[100,30,2.0],[0,0,0]],float);p=y+np.array([[3.1,1,.1],[1,.5,.02]])
        m=report(y,p,self.p);self.assertEqual(m['joint_pass_rate'],.5) # first energy exceeds its3nJ limit; second row is inside absolute limits
        perfect=report(y,y,self.p);self.assertEqual(perfect['joint_pass_rate'],1.)
        with self.assertRaises(ValueError):report(y,np.full_like(y,np.nan),self.p)
    def test_conformal_rank_and_joint(self):
        y=np.exp(np.arange(60).reshape(20,3)*.001);p=np.ones((20,3));c=joint_log_calibration(y,p,.1);self.assertEqual(c['rank'],19)
        lo,hi=prediction_intervals(p,c);self.assertEqual(lo.shape,y.shape);self.assertTrue(np.all(lo<=p));self.assertTrue(np.all(hi>=p))
        with self.assertRaises(ValueError):joint_log_calibration(np.zeros((20,3)),p)
    def test_wilson(self):
        lo,hi=wilson(95,100);self.assertLess(lo,.95);self.assertGreater(hi,.95);self.assertEqual(wilson(0,0),[None,None])
    def test_rebuild_csv_exact(self):
        with tempfile.TemporaryDirectory()as d:
            out=Path(d)/'release';build(out)
            for p in [*ROLES.values(),'plans/solver_designs_8192.csv','data/training_orders.json']:
                self.assertEqual((ROOT/p).read_bytes(),(out/p).read_bytes())
    def test_tiny_model_prediction_reload(self):
        import joblib
        rows=self.rows['train'][:64];x=np.array([[float(r[k])for k in FEATURES]for r in rows]);y=np.array([[float(r[k])for k in TARGETS]for r in rows])
        domain=json.loads((ROOT/'configs/domain.json').read_text())['bounds'];m=LogSurrogate('ridge2',domain,self.p['models']['ridge2']).fit(x,y)
        with tempfile.TemporaryDirectory()as d:
            p=Path(d)/'trusted.joblib';joblib.dump(m,p);m2=joblib.load(p);np.testing.assert_array_equal(m.predict(x[:2]),m2.predict(x[:2]))
        bad=x[:2].copy();bad[0,3]=4.15
        with self.assertRaises(ValueError):m.predict(bad)
        bad=x[:2].copy();bad[0,0]=11
        with self.assertRaises(ValueError):m.predict(bad)
    def test_frozen_evaluation_requires_authorization(self):
        from evaluate_frozen import run
        with self.assertRaises(PermissionError):run(Path('none'),Path('none'),Path('none'),False)
if __name__=='__main__':unittest.main(verbosity=2)
