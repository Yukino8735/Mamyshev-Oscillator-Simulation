"""Thin schema/integrity checks only; no fit, prediction, oracle or MATLAB."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from mamyshev_ml import closeout_inference as ci


class TestCloseoutInference(unittest.TestCase):
    def setUp(self):
        self.good = dict(zip(ci.FEATURES, (4, 10, 3, 4)))

    def test_schema_preserves_valid_design(self):
        self.assertEqual(ci.validate_design(self.good), self.good)

    def test_unknown_missing_conflicting_fields_rejected(self):
        for value in ({**self.good, "cw2": 1030}, {k: v for k, v in self.good.items() if k != ci.FEATURES[0]}, None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                ci.validate_design(value)

    def test_invalid_domain_grid_bool_and_nonfinite_rejected(self):
        for key, value in (("pump_power_W", 10.01), ("gain_length_m", 4.15),
                           ("pump_power_W", True), ("pump_power_W", float("nan")),
                           ("pump_power_W", "4")):
            with self.subTest(value=value), self.assertRaises(ValueError):
                ci.validate_design({**self.good, key: value})

    def test_single_list_and_csv_input_agree(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / "single.json").write_text(json.dumps(self.good))
            (tmp / "batch.json").write_text(json.dumps([self.good]))
            (tmp / "batch.csv").write_text(",".join(ci.FEATURES) + "\n4,10,3,4\n")
            self.assertEqual(ci.read_inputs(tmp / "single.json"), ci.read_inputs(tmp / "batch.json"))
            self.assertEqual(ci.read_inputs(tmp / "batch.json"), ci.read_inputs(tmp / "batch.csv"))

    def test_duplicate_json_or_csv_and_empty_input_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "input.json"
            for text in ('{"pump_power_W":4,"pump_power_W":5}', '[]'):
                path.write_text(text)
                with self.assertRaises(ValueError):
                    ci.read_inputs(path)
            path = path.with_suffix(".csv")
            path.write_text("pump_power_W,pump_power_W,filter2_bw_nm,gain_length_m\n4,10,3,4\n")
            with self.assertRaises(ValueError):
                ci.read_inputs(path)

    def test_missing_manifest_fails_before_import(self):
        with tempfile.TemporaryDirectory() as tmp, patch("importlib.util.spec_from_file_location") as imported:
            with self.assertRaises(FileNotFoundError):
                ci.load_model(tmp)
            imported.assert_not_called()

    def test_forged_manifest_cannot_allow_arbitrary_weights(self):
        with tempfile.TemporaryDirectory() as tmp, patch("importlib.util.spec_from_file_location") as imported:
            tmp = Path(tmp)
            files = {}
            for name in ci.FILES:
                (tmp / name).write_text("altered")
                files[name] = ci.sha(tmp / name)
            (tmp / "manifest.json").write_text(json.dumps({"schema_version": "mamyshev_mvp_inference_bundle_v1", "files": files}))
            with self.assertRaisesRegex(ValueError, "fixed trusted identity"):
                ci.load_model(tmp)
            imported.assert_not_called()


if __name__ == "__main__":
    unittest.main()
