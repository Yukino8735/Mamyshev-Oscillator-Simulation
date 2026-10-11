"""Bounded-selection and role-gate tests; no oracle labels, model fits or MATLAB."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from mamyshev_ml import v41_experiment as v


def score(each=.95, joint=.90):
    return {'targets': {t:{'pass_rate':each} for t in v.TARGETS}, 'joint_pass_rate':joint}


class TestV41Experiment(unittest.TestCase):
    def test_every_gate_required_and_inclusive(self):
        core = {g:score(.90) for g in ('historical_core','expanded_proposal')}
        groups = {g:score() for g in v.SPECIAL}
        self.assertTrue(v.development_gate(score(),core,groups)['passed'])
        for g in v.SPECIAL:
            bad = copy.deepcopy(groups); bad[g]['targets'][v.TARGETS[0]]['pass_rate']=.94999
            self.assertFalse(v.development_gate(score(),core,bad)['passed'])
        self.assertFalse(v.development_gate(score(),core,{})['passed'])
        self.assertFalse(v.development_gate(score(joint=.899),core,groups)['passed'])

    def test_selection_size_then_equal_group_error_and_no_fallback_pass(self):
        rows = [{'name':n,'n':size,'gate':{'passed':passed},'equal_group_normalized_rmse':rmse}
                for n,size,passed,rmse in [('B0',512,True,.6),('B1',1024,True,.4),('B2',1024,True,.3)]]
        self.assertEqual(v.choose_candidate(rows)[0]['name'],'B0')
        rows[0]['gate']['passed']=False
        self.assertEqual(v.choose_candidate(rows)[0]['name'],'B2')
        for r in rows:r['gate']['passed']=False
        self.assertIsNone(v.choose_candidate(rows)[0])
        self.assertEqual(v.choose_candidate(rows)[1]['name'],'B2')

    def test_signed_metrics_constant_r2_and_tolerance(self):
        y=np.tile([100.,40.,2.],(4,1)); pred=y+np.array([4.,-2.,0.])
        result=v.statistics(y,pred,{'metrics_protocol':v.v4_protocol()})
        energy=result['targets'][v.TARGETS[0]]
        self.assertEqual(energy['signed_mean'],4.)
        self.assertEqual(energy['pass_rate'],0.)
        self.assertAlmostEqual(energy['normalized_error_quantiles']['max'],4/3)
        self.assertIsNone(energy['r2'])
        self.assertEqual(result['targets'][v.TARGETS[1]]['underprediction_count'],4)

    def test_failed_selection_blocks_holdout_before_directory_or_oracle(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp); (out/'development').mkdir()
            (out/'development/selection.json').write_text(json.dumps({'frozen':True,'selected':None,'development_accuracy_target_met':False}))
            with patch.object(v,'OUT',out),patch.object(v,'load_protocol',return_value={}):
                with self.assertRaises(PermissionError):v.query_role('test',None,{})
            self.assertFalse((out/'samples').exists())

    def test_existing_role_blocks_resampling_before_evaluation(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp); (out/'samples/train').mkdir(parents=True)
            with patch.object(v,'OUT',out):
                with self.assertRaises(FileExistsError):v.query_role('train',None,{})

    def test_constraints_do_not_replace_predictions_and_report_empty_precision(self):
        y=np.array([[90.,45.,1.],[110.,35.,2.]])
        pred=np.array([[95.,45.,1.],[105.,35.,2.]])
        calibration=v.joint_log_calibration(y,pred,.05)
        before=pred.copy(); r=v.constraint_statistics(y,pred,calibration)
        np.testing.assert_array_equal(before,pred)
        self.assertEqual(r['energy_ge100_nJ']['point']['precision'],1.)
        self.assertEqual(r['duration_le40_fs']['point']['recall'],1.)
        self.assertTrue(r['energy_ge100_nJ']['small_group'])


if __name__=='__main__':unittest.main()
