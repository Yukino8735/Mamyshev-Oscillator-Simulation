"""V4.2 staging guards and budget routing; no real fits, oracle or MATLAB."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from mamyshev_ml import v42_experiment as v


class TestV42Flow(unittest.TestCase):
    def test_train_and_dev_queries_forbidden_before_selection_or_oracle(self):
        with patch.object(v,'verify_selected') as selected:
            for role in ('train','dev','challenge'):
                with self.assertRaises(PermissionError):v.query_holdout(role,None,{})
            selected.assert_not_called()

    def test_no_selected_candidate_cannot_open_holdout(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d);(out/'selection.json').write_text(json.dumps({'frozen':True,'selected':None}))
            with patch.object(v,'OUT',out),patch.object(v,'load_protocol',return_value={}):
                with self.assertRaises(PermissionError):v.verify_selected()
            self.assertFalse((out/'samples').exists())

    def test_holdout_requires_reservation_and_prior_calibration(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)
            with patch.object(v,'OUT',out),patch.object(v,'verify_selected',return_value=({},{})),patch.object(v,'guard_holdout_isolation'):
                with self.assertRaises(PermissionError):v.query_holdout('calibration',None,{})
                (out/'final_evaluation.lock').write_text('{}')
                with self.assertRaises(PermissionError):v.query_holdout('test',None,{})
            self.assertFalse((out/'samples').exists())

    def test_actual_baseline_comparison_uses_order_values_and_fixed_tolerance(self):
        import numpy as np
        rows=[{'design_id':'fixture','region':'tagged_artificial',**dict(zip(v.FEATURES,[4.,10.,3.,4.]))}]
        y=np.array([[100.,40.,2.]]);p={'baseline_equivalence':{'atol':1e-10,'rtol':1e-10}}
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'prediction.csv';v.predictions_csv(path,rows,y,y)
            self.assertTrue(v.baseline_check(path,rows,y,y+1e-13,p)['passed'])
            with self.assertRaises(AssertionError):v.baseline_check(path,rows,y,y+.01,p)
            with self.assertRaises(ValueError):v.baseline_check(path,[dict(rows[0],design_id='wrong')],y,y,p)

    def test_budget_adds_only_new_batch_option_and_preserves_default(self):
        # Parsing stops at an intentional nonexistent batch before any process launch.
        import contextlib,io
        root=Path(__file__).resolve().parents[1]
        spec=importlib.util.spec_from_file_location('v42_budget_cli',root/'scripts/run_v4_budget.py')
        mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
        for batch in (None,'accuracy_v4_001','accuracy_v4_1_001','accuracy_v4_2_001'):
            argv=['budget','--timeout-s','1']+(['--batch',batch] if batch else [])+['engineering','fixture','--','-m','unittest']
            with tempfile.TemporaryDirectory() as d,patch.object(mod,'ROOT',Path(d)),patch('sys.argv',argv),contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as error:mod.main()
                self.assertEqual(error.exception.code,2)
                self.assertFalse((Path(d)/'reports').exists())


if __name__=='__main__':unittest.main()
