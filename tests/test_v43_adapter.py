"""Artificial adapter/scan fixtures only: no trained model, oracle or MATLAB."""
from copy import deepcopy
import csv
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from mamyshev_ml import v43_adapter as application
from mamyshev_ml.v42_release import V42ReleaseEvaluator, SOURCE, BACKEND, GROUP_COUNTS
from mamyshev_ml.v4_evaluators import FEATURES, TARGETS, UNITS, SurrogateEvaluator
from mamyshev_ml.v4_scan import execute_scan, make_plan, plot_scan
from mamyshev_ml.v4_store import V4Store


class ArrayFixture:
    """Explicit artificial scalar function for wiring only; never fits anything."""
    def predict(self, values):
        values = np.asarray(values)
        return np.column_stack((100 + values[:, 0], 40 + values[:, 1] / 100, 2 + values[:, 2] / 100))


class TestV43Adapter(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.model_identity = {"model_id": "artificial_adapter_fixture", "sha256": "a" * 64}
        statistics = lambda n: {"n": n, "joint_pass_rate": 1., "targets": {k: {"pass_rate": 1.} for k in TARGETS}}
        self.q = .01
        self.release = {"release_id": "artificial_adapter_fixture", "selected": "fixture", "source_kind": SOURCE,
            "backend_id": BACKEND, "model_sha256": self.model_identity["sha256"],
            "protocol_sha256": "b" * 64, "source_hashes": {"fixture": "c" * 64}, "data_hashes": {"fixture": "d" * 64},
            "evaluation_summary": {"accuracy_target_met": True},
            "final_metrics": {"metrics": statistics(2048), "gate": {"passed": True},
                "groups": {name: statistics(n) for name, n in GROUP_COUNTS.items()},
                "intervals": {"n": 2048, "joint_coverage": 1936 / 2048,
                    "median_relative_interval_width": [2 * math.sinh(self.q)] * 3},
                "group_intervals": {"near_slice": {"n": 256, "joint_coverage": 216 / 256}}},
            "protocol": {"role_quotas": {"calibration": {"fixture": 1024}}, "calibration_alpha": .05,
                         "calibration_rank": 974, "calibration_method": "existing joint_max_absolute_log_residual"},
            "verification": {"final_metrics_path": str(self.root / "final_metrics.json"), "selection_sha256": "e" * 64}}
        for kind in ("protocol", "training_ids", "evaluation_summary", "final_metrics"):
            self.release[kind + "_path"] = "fixture/" + kind
            self.release[kind + "_sha256"] = "f" * 64
        self.calibration = {"n_calibration": 1024, "alpha": .05, "rank": 974,
            "q_joint_log": self.q, "method": "joint_max_absolute_log_residual",
            "model_sha256": self.model_identity["sha256"], "selected": "fixture"}
        self.calibration_path = self.root / "calibration.json"
        self.write_calibration()
        self.design = dict(zip(FEATURES, (4., 10., 3., 4.)))

    def write_calibration(self):
        self.calibration_path.write_text(json.dumps(self.calibration))

    def evaluator(self):
        trusted = V42ReleaseEvaluator(ArrayFixture(), self.model_identity, self.release)
        return application.V43ApplicationEvaluator(trusted)

    def test_calibration_semantic_identity_and_visible_limited_scope(self):
        evaluator = self.evaluator()
        self.assertIsInstance(evaluator, SurrogateEvaluator)
        result = evaluator.evaluate(self.design)
        interval = result["diagnostic_intervals"]
        self.assertEqual(interval["status"], "limited")
        self.assertFalse(interval["per_group_or_per_point_95_percent_guarantee"])
        self.assertEqual(interval["empirical_joint_coverage"]["near_slice"]["covered"], 216)
        self.assertEqual(interval["calibration"]["q_joint_log"], self.q)
        self.assertFalse(interval["calibration"]["old_manifest_direct_calibration_hash"])
        self.assertEqual(result["model_identity"], self.model_identity)
        self.assertEqual(result["input_units"]["gain_length_m"], "m")

    def test_mismatched_q_disables_intervals_but_preserves_point_prediction(self):
        self.calibration["q_joint_log"] = .02
        self.write_calibration()
        result = self.evaluator().evaluate(self.design)
        self.assertEqual(result["job_status"], "predicted")
        self.assertEqual(result["targets"][TARGETS[0]], 104.)
        self.assertIsNone(result["diagnostic_intervals"]["lower"])
        self.assertIn("hash-bound", result["diagnostic_intervals"]["missing_reason"])

    def test_missing_or_wrong_model_calibration_never_borrows_old_q(self):
        self.calibration_path.unlink()
        self.assertEqual(self.evaluator().calibration["status"], "not_available")
        self.calibration["model_sha256"] = "0" * 64
        self.write_calibration()
        self.assertIsNone(self.evaluator().calibration["q_joint_log"])
        self.calibration["model_sha256"] = self.model_identity["sha256"]
        self.calibration["rank"] = 973
        self.write_calibration()
        self.assertIsNone(self.evaluator().calibration["q_joint_log"])

    def test_unknown_nonfinite_outside_and_off_grid_inputs_fail_without_rounding(self):
        evaluator = self.evaluator()
        for bad in ({**self.design, "unknown": 1}, {**self.design, "pump_power_W": float("nan")},
                    {**self.design, "pump_power_W": 11.}, {**self.design, "gain_length_m": 4.01}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                evaluator.evaluate(bad)
        with self.assertRaises(ValueError):
            evaluator.predict_arrays([self.design, {**self.design, "gain_length_m": 4.01}])

    def test_batch_single_arrays_values_ids_and_no_false_fields(self):
        evaluator = self.evaluator()
        designs = [self.design, {**self.design, "pump_power_W": 4.1}]
        arrays = evaluator.predict_arrays(designs)
        records = evaluator.evaluate_many(designs)
        expected = [[r["targets"][k] for k in TARGETS] for r in records]
        np.testing.assert_allclose(arrays["targets"], expected, atol=1e-10, rtol=1e-10)
        np.testing.assert_allclose(arrays["lower"], arrays["targets"] * math.exp(-self.q), atol=0, rtol=0)
        self.assertEqual(evaluator.prediction_rows, 4)
        self.assertTrue(all(r["kind"] == "Prediction" and r["waveforms"] is None for r in records))
        self.assertTrue(all(r["numerical_validation"] == "not_verified" for r in records))

    def test_scan_prediction_database_csv_mat_roundtrip_no_evaluations(self):
        from scipy.io import loadmat
        plan = make_plan(axes={"pump_power_W": [4., 4.1]}, fixed={k: v for k, v in self.design.items() if k != "pump_power_W"})
        store = V4Store(self.root / "scan.sqlite")
        self.addCleanup(store.close)
        result = execute_scan(store, plan, self.evaluator(), scan_id="fixture_scan",
            budget={"max_new_attempts": 2, "total_wall_s": 10}, stop_path=self.root / "STOP")
        self.assertEqual(result["state_counts"], {"predicted": 2})
        self.assertEqual(store.db.execute("SELECT count(*) FROM evaluations").fetchone()[0], 0)
        exports = store.export_scan("fixture_scan", self.root / "export")
        with Path(exports["csv"]).open() as stream:
            rows = list(csv.DictReader(stream))
        mat = loadmat(exports["mat"])
        np.testing.assert_allclose(mat["Y"], [[float(r[k]) for k in TARGETS] for r in rows], atol=0, rtol=0)
        self.assertEqual(mat["X"].shape, (2, 4))
        self.assertEqual(mat["Y"].shape, (2, 3))
        self.assertEqual(json.loads(rows[0]["identity_json"])["numerical_version"], self.model_identity["sha256"])
        self.assertTrue(all(row["source"] == "surrogate_prediction" for row in rows))
        with self.assertRaises(ValueError):
            store.save_evaluation(self.evaluator().evaluate(self.design))

    def test_plot_uses_actual_predicted_values_not_blank_completed_only(self):
        from matplotlib.axes import Axes
        plan = make_plan(axes={"pump_power_W": [4., 4.1]}, fixed={k: v for k, v in self.design.items() if k != "pump_power_W"})
        store = V4Store(self.root / "plot.sqlite")
        self.addCleanup(store.close)
        execute_scan(store, plan, self.evaluator(), scan_id="fixture_plot",
            budget={"max_new_attempts": 2, "total_wall_s": 10}, stop_path=self.root / "STOP")
        original, plotted = Axes.plot, []
        def capture(axis, *args, **kwargs):
            if len(args) >= 2:
                plotted.append(np.asarray(args[1], dtype=float))
            return original(axis, *args, **kwargs)
        with patch.object(Axes, "plot", capture):
            files = plot_scan(store, plan, "fixture_plot", self.root / "plots",
                source_title="Artificial Prediction fixture", limitation_note="Not a physical design sample")
        self.assertEqual(len(files), 3)
        self.assertEqual(len(plotted), 3)
        self.assertTrue(all(np.isfinite(values).all() for values in plotted))
        self.assertTrue(all(Path(path).is_file() for path in files))

    def test_threshold_crossing_uncertain_even_wholly_one_side_requires_confirmation(self):
        record = self.evaluator().evaluate(self.design)
        crossing = application.interval_constraint(record, TARGETS[1], "<=", 40.)
        inside = application.interval_constraint(record, TARGETS[1], "<=", 50.)
        self.assertEqual(crossing["relation"], "uncertain")
        self.assertEqual(inside["relation"], "entirely_on_predicted_feasible_side")
        self.assertTrue(inside["evaluator_confirmation_required"])
        self.assertFalse(inside["guaranteed_feasible"])

    def test_trusted_loader_is_used_and_identity_failure_is_not_suppressed(self):
        trusted = V42ReleaseEvaluator(ArrayFixture(), self.model_identity, self.release)
        with patch.object(application, "load_release_evaluator", return_value=trusted) as load:
            result = application.load_application_evaluator("explicit_model", "explicit_selection")
        load.assert_called_once_with("explicit_model", "explicit_selection")
        self.assertEqual(result.model_identity, self.model_identity)
        with patch.object(application, "load_release_evaluator", side_effect=ValueError("bad hash")), self.assertRaisesRegex(ValueError, "bad hash"):
            application.load_application_evaluator("changed", "selection")


if __name__ == "__main__":
    unittest.main()
