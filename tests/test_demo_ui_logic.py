"""UI-only schema/planning/export controls; no fitting or backend calls."""
from pathlib import Path
import json
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "demo"))
from ui_logic import (DEFAULT, TARGETS, candidate_plan, scan_plan, pending_requests,
                      prediction_csv, rank_predictions)


class DemoUIControls(unittest.TestCase):
    def test_scan_limits_and_legal_length_grid(self):
        for second, expected in ((None, 21), ("filter2_bw_nm", 441)):
            plan = scan_plan(DEFAULT, "gain_length_m", second, 21)
            self.assertEqual(plan["unique_designs"], expected)
            self.assertTrue(all(abs(r["design_config"]["gain_length_m"] * 10 - round(r["design_config"]["gain_length_m"] * 10)) < 1e-9 for r in plan["designs"]))
        for n in (22, 0, True):
            with self.assertRaises(ValueError):
                scan_plan(DEFAULT, "gain_length_m", count=n)
        with self.assertRaises(ValueError):
            scan_plan(DEFAULT, "gain_length_m", "gain_length_m")

    def test_candidates_have_fixed_inputs_limits_and_no_targets(self):
        scenarios = json.loads((ROOT / "mamyshev_accuracy_v4/configs/scenarios.json").read_text())["scenarios"]
        for scenario in scenarios:
            plan = candidate_plan(scenario, 32, 8, {})
            self.assertLessEqual(plan["unique_designs"], 32)
            for row in plan["designs"]:
                self.assertEqual(set(row), {"design_id", "design_config"})
                self.assertLessEqual(row["design_config"]["pump_power_W"], 8)
                for k, v in scenario["fixed_inputs"].items():
                    self.assertEqual(row["design_config"][k], v)
        with self.assertRaises(ValueError):
            candidate_plan(scenarios[0], 4097, 8, {})
        with self.assertRaises(ValueError):
            candidate_plan(scenarios[2], 32, 8, {"gain_length_m": 5})
        with self.assertRaises(ValueError):
            candidate_plan(scenarios[0], 32, 8, {"gain_length_m": 4.15})

    @patch("ui_logic.require_current_model")
    def test_fixture_export_is_prediction_and_real_targets_null(self, identity_guard):
        # Handwritten UI fixture, not generated or reported research targets.
        row = {"design": DEFAULT, "targets": dict(zip(TARGETS, (120., 30., 2.)))}
        result = {"predictions": [row], "model_id": "fixture", "model_sha256": "fixture", "n_train": 0, "interval_status": "fixture"}
        scenario = {"output_constraints": {TARGETS[1]: {"lte": 40}}, "objective": {"target": TARGETS[2], "direction": "maximize"}}
        ranked = rank_predictions(result, scenario)
        pending = pending_requests(result, ranked, "fixture")
        self.assertEqual(pending["max_new_real_attempts"], 0)
        self.assertIsNone(pending["requests"][0]["real_targets"])
        self.assertIsNone(pending["requests"][0]["evaluation_id"])
        text = prediction_csv(result)
        self.assertIn("Prediction", text)
        self.assertNotIn("Evaluation", text)


if __name__ == "__main__":
    unittest.main()
