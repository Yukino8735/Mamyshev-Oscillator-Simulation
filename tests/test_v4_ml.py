"""Role boundary, fixed metrics and frozen evaluation denial; no holdout scoring."""
import json
from pathlib import Path
import sys
import unittest
import tempfile
from unittest.mock import patch
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from mamyshev_ml.v4_roles import ReleaseData, PACKAGE, SOURCE
from mamyshev_ml.v4_ml import metrics, protocol, final_evaluate, constraint_report, intervals_with_units, reserve_final_evaluation

class V4LearningTests(unittest.TestCase):
    def test_development_roles_and_prefix(self):
        loader = ReleaseData()
        for role in ('test', 'calibration', 'challenge'):
            with self.assertRaises(PermissionError):
                loader.read(role, source_kind=SOURCE)
        with self.assertRaises(PermissionError):
            loader.read('train', source_kind=SOURCE)
        ids = json.loads((PACKAGE/'data/training_orders.json').read_text())['orders']['11'][:3]
        rows = loader.read('train', source_kind=SOURCE, ids=ids)
        self.assertEqual([r['design_id'] for r in rows], ids)
        self.assertEqual(loader.accesses[-1]['rows'], 3)

    def test_wrong_source_and_ids(self):
        loader = ReleaseData()
        with self.assertRaises(PermissionError): loader.read('validation', source_kind='gmmnlse')
        with self.assertRaises(ValueError): loader.read('train', source_kind=SOURCE, ids=['absent'])
        with self.assertRaises(ValueError): loader.read('train', source_kind=SOURCE, ids=['x', 'x'])

    def test_frozen_required(self):
        with self.assertRaises(PermissionError): ReleaseData(evaluation=True)
        with self.assertRaises(PermissionError): final_evaluate(Path('untrusted'), Path('none'), Path('none'), False)

    def test_metrics_edge_rules(self):
        p = protocol()
        y = np.array([[0., 0., 0.], [0., 0., 0.]])
        m = metrics(y, y, p)
        for value in m['targets'].values():
            self.assertIsNone(value['r2']); self.assertTrue(value['r2_missing_reason'])
            self.assertEqual(value['relative_floor_used_count'], 2)
        with self.assertRaises(ValueError): metrics(y, np.full_like(y, np.nan), p)
        decimal = np.full((100, 3), 1.1)
        self.assertTrue(all(x['r2'] is None for x in metrics(decimal, decimal+.01, p)['targets'].values()))

    def test_same_model_cannot_reopen_holdout_in_another_directory(self):
        with tempfile.TemporaryDirectory() as directory, patch('mamyshev_ml.v4_ml.ROOT', Path(directory)):
            first, second = Path(directory)/'first', Path(directory)/'second'
            first.mkdir(); second.mkdir()
            reserve_final_evaluation('a'*64, first/'selection.json', first/'evaluation')
            with self.assertRaises(FileExistsError):
                reserve_final_evaluation('a'*64, second/'selection.json', second/'evaluation')

    def test_constraint_and_interval_counts(self):
        y = np.array([[100., 39., 2.], [100., 41., 2.], [100., 45., 2.]])
        pred = np.array([[100., 38., 2.], [100., 39., 2.], [100., 44., 2.]])
        calibration = {'q_joint_log': .03}
        value = constraint_report(y, pred, calibration)
        self.assertEqual(value['point_estimate']['false_feasible'], 1)
        self.assertEqual(value['point_estimate']['precision'], .5)
        self.assertEqual(value['uncertain_count'], 1)
        self.assertEqual(value['interval_screen']['proposed'], 1)
        report = intervals_with_units(y, pred, calibration)
        self.assertEqual(len(report['per_target_wilson95']), 3)
        self.assertEqual(len(report['width_original_units']), 3)

if __name__ == '__main__': unittest.main(verbosity=2)
