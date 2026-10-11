"""Small artificial fixtures for the fixed matrix; no T1/T2 fit or oracle data."""
import copy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from mamyshev_ml.v42_models import (LogSurrogate, TARGETS, candidate_specs, make_model,
    inspect_model, compare_alpha_feature_matrices, count_statistics, exact_rate,
    development_gate, equal_group_score, rate_gate, select_candidates)

DOMAIN = {"pump_power_W": [2, 10], "filter_offset_nm": [2, 16],
          "filter2_bw_nm": [.5, 8], "gain_length_m": [1, 8]}
BASE = {"n_knots": 16, "degree": 3, "knots": "uniform", "interaction_polynomial_degree": 4,
        "alpha": .1, "log_targets": True, "knots_source": "training input extrema only"}


def decisions(passed=False):
    return [{"slot_id": spec["slot_id"], "status": "completed", "numeric_valid": True,
             "gate": {"passed": passed}, "equal_group_normalized_rmse": 10 + i}
            for i, spec in enumerate(candidate_specs())]


class V42ModelTests(unittest.TestCase):
    def test_frozen_matrix_and_factory_constructs_without_fit_or_oracle(self):
        from mamyshev_ml.v4_evaluators import SyntheticEvaluator
        from mamyshev_ml.v4_roles import ReleaseData
        specs = candidate_specs()
        self.assertEqual(len(specs), 12)
        self.assertEqual(len({spec["slot_id"] for spec in specs}), 12)
        self.assertEqual([spec["reused"] for spec in specs if spec["reused"]], ["B1", "B2"])
        original = copy.deepcopy(BASE)
        with patch.object(LogSurrogate, "fit", side_effect=AssertionError("factory cannot fit")), \
                patch.object(SyntheticEvaluator, "evaluate", side_effect=AssertionError("no oracle")), \
                patch.object(ReleaseData, "read", side_effect=AssertionError("no role data")):
            for spec in specs:
                model = make_model(spec, BASE, DOMAIN)
                self.assertEqual(model.models, [])
                self.assertEqual(model.family, "spline_interactions")
                self.assertEqual(model.parameters["n_knots"], spec["n_knots"])
                self.assertEqual(model.parameters["alpha"], spec["alpha"])
                for key in set(BASE) - {"n_knots", "alpha"}:
                    self.assertEqual(model.parameters[key], BASE[key])
        self.assertEqual(BASE, original)

    def test_factory_rejects_undeclared_parameters_and_unknown_slot(self):
        spec = candidate_specs()[2]
        with self.assertRaisesRegex(ValueError, "parameters differ"):
            make_model({**spec, "alpha": .01}, BASE, DOMAIN)
        with self.assertRaisesRegex(ValueError, "Base parameters"):
            make_model(spec, {**BASE, "degree": 1}, DOMAIN)
        with self.assertRaisesRegex(ValueError, "outside"):
            make_model({**spec, "slot_id": "T1_K128_A01"}, BASE, DOMAIN)

    def test_actual_artificial_feature_dimensions_knots_and_alpha_identity(self):
        from mamyshev_ml.v4_evaluators import SyntheticEvaluator
        from mamyshev_ml.v4_roles import ReleaseData
        # Eight expressly artificial rows, unrelated to actual training/holdout.
        x = np.array([[2 + i, 2 + 1.5 * i, .5 + .8 * i, 1 + .9 * i] for i in range(8)])
        y = np.exp(np.column_stack((1 + x[:, 0] / 20, 2 + x[:, 1] / 100, .1 + x[:, 2] / 20)))
        records = []
        with patch.object(SyntheticEvaluator, "evaluate", side_effect=AssertionError("no oracle")), \
                patch.object(ReleaseData, "read", side_effect=AssertionError("no role data")):
            for spec in candidate_specs()[:6]:
                model = make_model(spec, BASE, DOMAIN).fit(x, y)
                inspection = inspect_model(model, x)
                self.assertEqual(set(inspection["actual_feature_counts"].values()), {spec["expected_features"]})
                self.assertEqual(inspection["n_train"], 8)
                for target in TARGETS:
                    info = inspection["targets"][target]
                    self.assertEqual(info["ridge_settings"]["alpha"], spec["alpha"])
                    self.assertEqual(info["scaler"]["n_samples_seen"], 8)
                    self.assertEqual(info["spline_settings"]["extrapolation"], "constant")
                    self.assertEqual(len(info["actual_knots"]), 4)
                records.append({"slot_id": spec["slot_id"], "inspection": inspection})
        comparison = compare_alpha_feature_matrices(records)
        self.assertFalse(comparison["all_six_pairs_verified"])
        self.assertTrue(comparison["all_verified_pairs_passed"])
        self.assertEqual(sum(pair["verified"] for pair in comparison["pairs"]), 3)
        changed = copy.deepcopy(records)
        changed[1]["inspection"]["targets"][TARGETS[0]]["scaled_feature_matrix_sha256"] = "different"
        self.assertFalse(compare_alpha_feature_matrices(changed)["all_verified_pairs_passed"])

    def test_exact_integer_gate_rejects_rounding_971_of_1024(self):
        y = np.tile([100., 30., 2.], (1024, 1))
        p = y.copy(); p[:53, 0] += 4
        value = count_statistics(y, p)
        self.assertEqual(value["targets"][TARGETS[0]]["passed"], 971)
        self.assertEqual(value["joint_passed"], 971)
        self.assertFalse(rate_gate(value, .95, .90))
        self.assertFalse(exact_rate(972, 1024, .95))
        self.assertTrue(exact_rate(973, 1024, .95))
        value["targets"][TARGETS[0]]["pass_rate"] = .95  # Rounded display never controls decisions.
        self.assertFalse(rate_gate(value, .95, .90))
        self.assertFalse(exact_rate(True, 1, .95))

    def test_empty_and_nonfinite_groups_fail_closed(self):
        value = count_statistics(np.empty((0, 3)), np.empty((0, 3)))
        self.assertEqual(value["n"], 0)
        self.assertIsNone(value["targets"][TARGETS[0]]["passed"])
        self.assertIsNone(value["joint_pass_rate"])
        self.assertFalse(rate_gate(value, .95, .90))
        with self.assertRaisesRegex(FloatingPointError, "finite"):
            count_statistics([[100, 30, 2]], [[np.nan, 30, 2]])
        with self.assertRaisesRegex(ValueError, "shapes"):
            count_statistics([[100, 30, 2]], [[100, 30, 2], [100, 30, 2]])

    def test_development_gate_requires_every_six_group_and_reference_all(self):
        y = np.tile([100., 30., 2.], (20, 1))
        good = count_statistics(y, y)
        rg = {group: copy.deepcopy(good) for group in ("historical_core", "expanded_proposal")}
        sg = {group: copy.deepcopy(good) for group in ("slice", "near_slice", "outer_faces", "corners")}
        self.assertTrue(development_gate(good, rg, sg)["passed"])
        sg["near_slice"]["targets"][TARGETS[0]]["passed"] = 18
        self.assertFalse(development_gate(good, rg, sg)["passed"])
        self.assertFalse(development_gate(good, rg, {k: v for k, v in sg.items() if k != "corners"})["passed"])
        for i, record in enumerate(list(rg.values()) + list(sg.values())):
            record["mean_tolerance_normalized_rmse"] = i + 1
        self.assertEqual(equal_group_score(rg, sg), 3.5)

    def test_selection_requires_complete_matrix_and_no_pass_stops_holdout(self):
        rows = decisions()
        result = select_candidates(rows)
        self.assertTrue(result["matrix_complete"])
        self.assertIsNone(result["selected"])
        self.assertFalse(result["holdout_may_open"])
        self.assertEqual(result["best_diagnostic"], rows[0]["slot_id"])
        rows[0]["gate"]["passed"] = True
        result = select_candidates(rows[:-1])
        self.assertEqual(result["status"], "partial")
        self.assertIsNone(result["selected"])
        self.assertFalse(result["holdout_may_open"])
        rows[-1].update(status="numerical_failed", numeric_valid=False)
        result = select_candidates(rows)
        self.assertTrue(result["matrix_complete"])
        self.assertEqual(result["selected"], rows[0]["slot_id"])
        rows[-1]["status"] = "infrastructure_failed"
        self.assertEqual(select_candidates(rows)["status"], "blocked")
        self.assertIsNone(select_candidates(rows)["selected"])

    def test_score_tie_prioritizes_knots_then_alpha_then_T1(self):
        rows = decisions(True)
        for row in rows:
            row["equal_group_normalized_rmse"] = 100.
        for index in (1, 2, 6):
            rows[index]["equal_group_normalized_rmse"] = 0.
        rows[0]["equal_group_normalized_rmse"] = 1e-12
        self.assertEqual(select_candidates(rows)["selected"], "T1_K16_A01")
        for row in rows:
            row["equal_group_normalized_rmse"] = 100.
        rows[0]["equal_group_normalized_rmse"] = 1.01e-12
        rows[-1]["equal_group_normalized_rmse"] = 0.
        self.assertEqual(select_candidates(rows)["selected"], "T2_K64_A0001")

    def test_invalid_numeric_or_duplicate_slot_cannot_be_selected(self):
        rows = decisions(True)
        rows[0].update(status="numerical_failed", numeric_valid=True)
        with self.assertRaisesRegex(ValueError, "explicitly invalid"):
            select_candidates(rows)
        rows = decisions(True); rows[0]["equal_group_normalized_rmse"] = float("nan")
        with self.assertRaisesRegex(ValueError, "finite"):
            select_candidates(rows)
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            select_candidates(decisions() + [decisions()[0]])


if __name__ == "__main__":
    unittest.main(verbosity=2)
