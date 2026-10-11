"""Artificial diagnostic checks; never load old holdout or query an oracle."""
import copy
import csv
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from mamyshev_ml.v41_diagnostics import (FEATURES, TARGETS, UNITS, SOURCE, BACKEND,
    compare_prediction, prediction_paths, read_saved_csv, residual_summary, scaled, verify_saved_rows,
    verify_evaluator_metadata)

BOUNDS = dict(zip(FEATURES, ([2, 10], [2, 16], [.5, 8], [1, 8])))
PROTOCOL = {"relative_error_floor": dict.fromkeys(TARGETS, 1e-12), "tolerances": {
    TARGETS[0]: {"absolute": 2., "relative": .03},
    TARGETS[1]: {"absolute": 1., "relative": .03},
    TARGETS[2]: {"absolute": .05, "relative": .05}}}


class ArtificialFittedPipeline:
    def __init__(self, j):
        self.j = j
    def fit(self, *args, **kwargs):
        raise AssertionError("Diagnostic must not refit")
    def predict(self, x):
        return 1 + self.j + np.asarray(x).sum(axis=1) / 10


class ArtificialLogModel:
    def __init__(self):
        self.models = [ArtificialFittedPipeline(j) for j in range(3)]
    def fit(self, *args, **kwargs):
        raise AssertionError("Diagnostic must not refit")
    def _x(self, x):
        return scaled(np.asarray(x), BOUNDS)
    def predict(self, x):
        return np.exp(np.column_stack([m.predict(self._x(x)) for m in self.models]))


class ArtificialCLI:
    def __init__(self, model):
        self.model = model
    def evaluate(self, design):
        from mamyshev_ml.v4_evaluators import design_id
        value = self.model.predict([[design[k] for k in FEATURES]])[0]
        return {"kind": "Prediction", "job_status": "predicted", "design_id": design_id(design),
                "design": design, "model_identity": {"sha256": "artificial"},
                "identity": {"source": "surrogate_prediction", "numerical_version": "artificial"},
                "units": UNITS, "targets": dict(zip(TARGETS, value.tolist()))}


def artificial_rows():
    saved, database = [], []
    for i in range(2):
        row = {"design_id": f"artificial_{i}", "region": "artificial_region",
               **dict(zip(FEATURES, [4 + i, 10, 3, 4])),
               **{target + "_truth": (i + 1) * 10. for target in TARGETS}}
        saved.append(row)
        database.append({"design_id": row["design_id"], "role": "challenge", "region": row["region"],
            **{k: row[k] for k in FEATURES}, **{target: row[target + "_truth"] for target in TARGETS},
            "source_kind": SOURCE, "backend_id": BACKEND})
    return saved, database


class V41DiagnosticTests(unittest.TestCase):
    def test_evaluator_source_backend_units_and_plane_are_explicit(self):
        identity = {"source": SOURCE, "backend": BACKEND,
                    "metric_definition": {"units": UNITS, "plane": "constructed_compressed_scalars"}}
        verify_evaluator_metadata(identity)
        for key in ("source", "backend"):
            wrong = copy.deepcopy(identity); wrong[key] = "other"
            with self.assertRaisesRegex(ValueError, "mismatch"):
                verify_evaluator_metadata(wrong)
        wrong = copy.deepcopy(identity)
        wrong["metric_definition"]["units"][TARGETS[0]] = "J"
        with self.assertRaisesRegex(ValueError, "mismatch"):
            verify_evaluator_metadata(wrong)
        wrong = copy.deepcopy(identity); wrong["metric_definition"]["plane"] = "intracavity"
        with self.assertRaisesRegex(ValueError, "mismatch"):
            verify_evaluator_metadata(wrong)

    def test_signed_residual_and_normalized_r(self):
        truth = np.array([[100., 20., 2.], [100., 20., 2.]])
        prediction = np.array([[105., 19., 2.1], [98., 21., 1.8]])
        result = residual_summary(truth, prediction, PROTOCOL)
        energy = result["targets"][TARGETS[0]]
        self.assertEqual(energy["bias_mean_signed"], 1.5)
        self.assertEqual(energy["positive_count"], 1)
        self.assertEqual(energy["negative_count"], 1)
        self.assertEqual(energy["MAE"], 3.5)
        self.assertAlmostEqual(energy["mean_signed_relative"], .015)
        self.assertAlmostEqual(energy["tolerance_ratio_r"]["max"], 5 / 3)
        self.assertEqual(energy["pass_rate"], .5)

    def test_nonfinite_is_not_silently_dropped(self):
        with self.assertRaises(ValueError):
            residual_summary([[np.nan, 1, 1]], [[1, 1, 1]], PROTOCOL)
        with self.assertRaises(ValueError):
            compare_prediction([[1, np.inf, 1]], [[1, 1, 1]])

    def test_ID_join_accepts_reorder_but_rejects_row_mismatch(self):
        saved, database = artificial_rows()
        self.assertTrue(verify_saved_rows(saved, database[::-1], "challenge")["passed"])
        wrong = copy.deepcopy(saved)
        wrong[0]["design_id"], wrong[1]["design_id"] = wrong[1]["design_id"], wrong[0]["design_id"]
        with self.assertRaisesRegex(ValueError, "feature mismatch"):
            verify_saved_rows(wrong, database, "challenge")

    def test_ID_duplicate_missing_and_truth_mismatch_rejected(self):
        saved, database = artificial_rows()
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            verify_saved_rows([saved[0], saved[0]], database, "challenge")
        with self.assertRaisesRegex(ValueError, "sets differ"):
            verify_saved_rows(saved[:1], database, "challenge")
        wrong = copy.deepcopy(saved)
        wrong[0][TARGETS[0] + "_truth"] += 1e-12
        with self.assertRaisesRegex(ValueError, "truth mismatch"):
            verify_saved_rows(wrong, database, "challenge")

    def test_header_mapping_rejects_offset_bandwidth_swap(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "wrong.csv"
            with path.open("w", newline="") as stream:
                csv.writer(stream).writerow(["design_id", "region", FEATURES[0], FEATURES[2], FEATURES[1], FEATURES[3]])
            with self.assertRaisesRegex(ValueError, "order"):
                read_saved_csv(path)

    def test_single_batch_direct_CLI_equivalence_without_fit(self):
        x = np.array([[4, 10, 3, 4], [5, 11, 4, 5]])
        model = ArtificialLogModel()
        saved = model.predict(x)
        with patch.object(ArtificialLogModel, "fit", side_effect=AssertionError("no refit")), \
                patch.object(ArtificialFittedPipeline, "fit", side_effect=AssertionError("no refit")):
            checks, batch = prediction_paths(model, ArtificialCLI(model), x, saved, BOUNDS, "artificial")
        self.assertTrue(all(value["passed"] for value in checks.values()))
        np.testing.assert_array_equal(batch, saved)
        wrong = saved.copy(); wrong[0, 0] += 1e-3
        checks, _ = prediction_paths(model, ArtificialCLI(model), x, wrong, BOUNDS, "artificial")
        self.assertFalse(checks["batch_vs_saved"]["passed"])

    def test_fixed_equivalence_tolerance(self):
        reference = np.array([[100., 10., 1.]])
        self.assertTrue(compare_prediction(reference + 1e-11, reference)["passed"])
        self.assertFalse(compare_prediction(reference + 1e-6, reference)["passed"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
