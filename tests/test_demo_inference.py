"""Standalone integrity and actual saved-prediction regression; no new labels."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from mamyshev_ml import demo_inference as inference

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "demo/assets/models"
OUT = ROOT / "reports/local/demo_10k_release_001"


class DemoInferenceInputTests(unittest.TestCase):
    def test_finite_exact_four_inputs_and_length_grid(self):
        base = dict(zip(inference.FEATURES, (4., 10., 3., 4.)))
        self.assertEqual(inference.validate_design(base), base)
        invalid = [dict(base, gain_length_m=4.01), dict(base, pump_power_W=True),
                   dict(base, filter2_bw_nm=float("nan")), dict(base, extra=1),
                   {k: v for k, v in base.items() if k != "gain_length_m"}]
        for value in invalid:
            with self.assertRaises(ValueError): inference.validate_design(value)


@unittest.skipUnless((ASSETS / "catalog.json").is_file(), "Reviewed standalone assets have not been built")
class DemoInferenceAssetTests(unittest.TestCase):
    def test_model_identity_training_and_own_q(self):
        catalog = inference.load_catalog(ASSETS)
        self.assertEqual(catalog["default_model_id"], inference.MODEL_ID)
        self.assertEqual(set(catalog["models"]), {inference.MODEL_ID})
        with self.assertRaises(ValueError):
            inference.verify(ASSETS, "v42_T2_K64_A0001")
        new = inference.verify(ASSETS, inference.MODEL_ID)
        self.assertEqual(new["n_train"], 10000)
        self.assertEqual(new["model_sha256"], inference.MODEL_SHA)
        self.assertEqual(new["calibration"]["model_sha256"], new["model_sha256"])
        self.assertEqual(new["interval_status"], "limited")

    def test_actual_new_saved_prediction_readback_without_fit(self):
        designs = json.loads((OUT / "reload_inputs.json").read_text())
        expected = np.asarray(json.loads((OUT / "reload_predictions.json").read_text()))
        model, _ = inference.load_model(ASSETS, "demo_10k_v1")
        with patch.object(type(model), "fit", side_effect=AssertionError("Runtime may not train")):
            result = inference.predict(ASSETS, "demo_10k_v1", designs)
            actual = np.asarray([[r["targets"][k] for k in inference.TARGETS] for r in result["predictions"]])
            single = np.asarray([[inference.predict(ASSETS, "demo_10k_v1", [d])["predictions"][0]["targets"][k]
                                  for k in inference.TARGETS] for d in designs])
        np.testing.assert_allclose(actual, expected, atol=1e-10, rtol=1e-10)
        np.testing.assert_allclose(single, expected, atol=1e-10, rtol=1e-10)
        self.assertEqual(result["kind"], "Prediction")
        self.assertFalse(result["eligible_as_validated_training_truth"])

    def test_changed_class_and_missing_weight_rejected_before_joblib(self):
        for name, action in (("models_v4.py", "change"), ("model.joblib", "remove")):
            with tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary) / "models"; shutil.copytree(ASSETS, root)
                target = root / "demo_10k_v1" / name
                if action == "change": target.write_text(target.read_text() + "\n# changed\n")
                else: target.unlink()
                with patch("joblib.load", side_effect=AssertionError("Must reject before deserialize")) as load:
                    with self.assertRaises(ValueError): inference.load_model(root, "demo_10k_v1")
                    load.assert_not_called()

    def test_arbitrary_model_path_and_missing_model_rejected(self):
        for name in ("../../other", "uploaded.joblib", "unknown"):
            with self.assertRaises(ValueError): inference.verify(ASSETS, name)


if __name__ == "__main__": unittest.main()
