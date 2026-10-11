"""Current model identity and research-backend integration regressions; no labels."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'demo'))
from mamyshev_ml import demo_inference as inference
from mamyshev_ml.v4_evaluators import RecordedEvaluator, SurrogateEvaluator, GMMNLSEEvaluator
from mamyshev_ml.v4_scan import execute_scan, plot_scan, read_saved_waveform
from ui_logic import DEFAULT, request_key, prediction_csv, pending_requests
from ui_presentation import session_model_conflicts


class CurrentModelControls(unittest.TestCase):
    def test_retired_and_foreign_exports_rejected_without_inference(self):
        for model_id, digest in [('v42_T2_K64_A0001', inference.MODEL_SHA),
                                 (inference.MODEL_ID, '0' * 64), ('fixture', 'fixture')]:
            result = {'model_id': model_id, 'model_sha256': digest, 'predictions': []}
            for operation in (lambda: request_key(model_id, digest, {'design': DEFAULT}),
                              lambda: prediction_csv(result),
                              lambda: pending_requests(result, [], 'fixture')):
                with self.subTest(model=model_id), self.assertRaises(ValueError):
                    operation()

    def test_catalog_rejects_reintroduction_of_retired_model(self):
        catalog = inference.load_catalog(ROOT / 'demo/assets/models')
        foreign = copy.deepcopy(catalog)
        foreign['models']['v42_T2_K64_A0001'] = {'directory': 'v42'}
        with patch.object(inference, '_json', return_value=foreign):
            with self.assertRaises(ValueError):
                inference.load_catalog(ROOT / 'demo/assets/models')

    def test_stale_session_requests_and_results_cannot_be_relabelled(self):
        current = {'model_id': inference.MODEL_ID, 'model_sha256': inference.MODEL_SHA}
        state = {'model_id': inference.MODEL_ID, 'active_model_sha': inference.MODEL_SHA,
                 'baseline_result': dict(current), 'scan_result': {'prediction': dict(current)}}
        self.assertEqual(session_model_conflicts(state, inference.MODEL_ID, inference.MODEL_SHA), [])
        state['scan_result']['prediction']['model_id'] = 'v42_T2_K64_A0001'
        state['pending_request'] = {'source_model_id': 'v42_T2_K64_A0001',
                                    'source_model_sha256': inference.MODEL_SHA}
        self.assertEqual(set(session_model_conflicts(state, inference.MODEL_ID, inference.MODEL_SHA)),
                         {'scan_result', 'pending_request'})

    def test_asset_entry_does_not_rebuild_historical_catalog(self):
        spec = importlib.util.spec_from_file_location('current_asset_builder', ROOT / 'scripts/build_demo_assets.py')
        builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(builder)
        before = (ROOT / 'demo/assets/models/catalog.json').read_bytes()
        with patch.object(builder, '_historical_build', side_effect=AssertionError('Retired builder called')):
            builder.main()
        self.assertEqual((ROOT / 'demo/assets/models/catalog.json').read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
