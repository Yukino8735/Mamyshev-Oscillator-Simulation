"""Artificial release/Prediction components; no oracle, training, or MATLAB."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

from mamyshev_ml import v42_release as release
from mamyshev_ml.v4_evaluators import SurrogateEvaluator
from mamyshev_ml.v4_store import V4Store


class ConstantFixture:
    """Three tagged artificial scalars, not a trained model or physical label."""
    def __init__(self, parameters, domain):
        self.parameters, self.domain = deepcopy(parameters), deepcopy(domain)
        self.family, self.models = "spline_interactions", [None, None, None]

    def predict(self, x):
        return np.tile([100., 39., 2.], (len(x), 1))


class TestV42Release(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.patch = patch.object(release, "ROOT", self.root)
        self.patch.start(); self.addCleanup(self.patch.stop)
        self.batch = self.root / release.BATCH
        self.batch.mkdir(parents=True)
        self.parameters = {"n_knots": 32, "degree": 3, "knots": "uniform",
            "interaction_polynomial_degree": 4, "alpha": .001, "log_targets": True}
        self.domain = {"pump_power_W": [1., 8.], "filter_offset_nm": [1., 15.],
                       "filter2_bw_nm": [.5, 8.], "gain_length_m": [1., 8.]}
        self.selected = "T2_K32_A0001"
        self.sources = {}
        for name in sorted(release.REQUIRED_SOURCES):
            path = self.root / name; path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("# artificial identity fixture only\n")
            self.sources[name] = self.sha(path)
        self.write_json(release.DOMAIN, {"bounds": self.domain})
        self.ids_name = release.BATCH + "/data/T2_training_ids.json"
        self.write_json(self.ids_name, ["d_" + f"{i:024x}" for i in range(1024)])
        self.data = {name: self.sha(self.root / name) for name in (release.DOMAIN, self.ids_name)}
        self.protocol_name = release.BATCH + "/protocol.json"
        self.write_json(self.protocol_name, {"sources": self.sources, "data_hashes": self.data})
        self.model_name = release.BATCH + "/release/model.joblib"
        self.model = self.root / self.model_name
        self.model.parent.mkdir(parents=True)
        self.model.write_bytes(b"artificial model bytes; joblib.load is mocked")
        self.summary_name = release.BATCH + "/evaluation/summary.json"
        self.summary = {"pipeline_completed": True, "development_accuracy_target_met": True,
            "calibration_status": "completed", "test_status": "completed", "accuracy_target_met": True,
            "selected": self.selected, "deployment_replaced": False}
        self.metrics_name = release.BATCH + "/evaluation/final_metrics.json"
        self.metrics = {"selected": self.selected, "model_sha256": self.sha(self.model),
            "gate": {"passed": True}, "metrics": self.statistics(2048),
            "groups": {name: self.statistics(n) for name, n in release.GROUP_COUNTS.items()}}
        self.write_json(self.summary_name, self.summary)
        self.write_json(self.metrics_name, self.metrics)
        self.manifest = {"schema_version": "mamyshev_v42_release_v1", "frozen": True,
            "release_id": "v42_artificial_component_fixture", "selected": self.selected,
            "development_accuracy_target_met": True, "deployment_replaced": False,
            "source_kind": release.SOURCE, "backend_id": release.BACKEND,
            "features": list(release.FEATURES), "targets": list(release.TARGETS),
            "input_units": release.INPUT_UNITS, "units": release.UNITS,
            "model_family": "spline_interactions", "n_train": 1024, "parameters": self.parameters,
            "source_hashes": self.sources, "data_hashes": self.data}
        for kind, name in (("model", self.model_name), ("protocol", self.protocol_name),
                           ("training_ids", self.ids_name), ("evaluation_summary", self.summary_name),
                           ("final_metrics", self.metrics_name)):
            self.manifest[kind + "_path"] = name
            self.manifest[kind + "_sha256"] = self.sha(self.root / name)
        self.selection = self.batch / "release/selection.json"
        self.save_manifest()

    @staticmethod
    def sha(path):
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()

    @staticmethod
    def statistics(n):
        return {"n": n, "joint_pass_rate": 1., "targets": {k: {"pass_rate": 1.} for k in release.TARGETS}}

    def write_json(self, name, value):
        path = self.root / name; path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, allow_nan=False))

    def save_manifest(self):
        self.selection.write_text(json.dumps(self.manifest, allow_nan=False))

    def update_artifact(self, kind, value):
        name = self.manifest[kind + "_path"]
        self.write_json(name, value)
        self.manifest[kind + "_sha256"] = self.sha(self.root / name)
        self.save_manifest()

    def load_fixture(self):
        reference = self.root / "mamyshev_accuracy_v4/reference/models_v4.py"
        with patch.dict("sys.modules", {"models_v4": SimpleNamespace(__file__=str(reference))}), \
                patch("joblib.load", return_value=ConstantFixture(self.parameters, self.domain)) as mocked, \
                patch.object(release.sys, "path", release.sys.path[:]):
            value = release.load_release_evaluator(self.model, self.selection)
        self.assertEqual(mocked.call_count, 1)
        return value

    def test_valid_read_only_verification_and_explicit_loading(self):
        before = {str(p): self.sha(p) for p in self.root.rglob("*") if p.is_file()}
        checked = release.verify_release(self.model, self.selection)
        self.assertEqual(checked["final_metrics"]["model_sha256"], self.sha(self.model))
        self.assertEqual(checked["evaluation_summary"]["test_status"], "completed")
        evaluator = self.load_fixture()
        self.assertIsInstance(evaluator, SurrogateEvaluator)
        self.assertEqual(evaluator.model_identity["sha256"], self.sha(self.model))
        after = {str(p): self.sha(p) for p in self.root.rglob("*") if p.is_file()}
        self.assertEqual(before, after)

    def test_model_source_data_and_protocol_tampering_fail_before_pickle(self):
        for name in (self.model_name, next(iter(self.sources)), release.DOMAIN, self.protocol_name):
            with self.subTest(name=name):
                path = self.root / name; old = path.read_bytes(); path.write_bytes(old + b" ")
                try:
                    with patch("joblib.load") as loader, self.assertRaises(ValueError):
                        release.load_release_evaluator(self.model, self.selection)
                    loader.assert_not_called()
                finally:
                    path.write_bytes(old)

    def test_untrusted_old_paths_and_artifact_traversal_are_refused(self):
        outside = self.root / "reports/local/accuracy_v4_001/model.joblib"
        outside.parent.mkdir(parents=True); outside.write_bytes(self.model.read_bytes())
        with self.assertRaises(PermissionError):
            release.verify_release(outside, self.selection)
        self.manifest["model_path"] = "../model.joblib"; self.save_manifest()
        with self.assertRaises(ValueError):
            release.verify_release(self.model, self.selection)

    def test_unknown_partial_or_development_failed_release_is_not_promoted(self):
        original = deepcopy(self.manifest)
        for changes in ({"frozen": False}, {"selected": None}, {"development_accuracy_target_met": False},
                        {"deployment_replaced": True}, {"source_kind": "repaired_original_backend"}):
            with self.subTest(changes=changes):
                self.manifest = {**deepcopy(original), **changes}; self.save_manifest()
                with self.assertRaises((ValueError, PermissionError)):
                    release.verify_release(self.model, self.selection)
        self.manifest = original; self.save_manifest()
        self.summary["test_status"] = "not_run"
        self.update_artifact("evaluation_summary", self.summary)
        with self.assertRaises(ValueError):
            release.verify_release(self.model, self.selection)

    def test_units_training_ids_and_complete_test_groups_are_required(self):
        original = deepcopy(self.manifest)
        self.manifest["input_units"] = {**release.INPUT_UNITS, "gain_length_m": "cm"}; self.save_manifest()
        with self.assertRaises(ValueError): release.verify_release(self.model, self.selection)
        self.manifest = original; self.save_manifest()
        self.metrics["groups"].pop("near_slice")
        self.update_artifact("final_metrics", self.metrics)
        with self.assertRaises(ValueError): release.verify_release(self.model, self.selection)

    def test_model_identity_and_class_module_are_checked_before_load(self):
        with patch("joblib.load") as loader, self.assertRaises(ValueError):
            release.load_release_evaluator(self.model, self.selection, {"model_id": "wrong", "sha256": "0" * 64})
        loader.assert_not_called()
        with patch.dict("sys.modules", {"models_v4": SimpleNamespace(__file__="/tmp/untrusted_models_v4.py")}), \
                patch("joblib.load") as loader, self.assertRaises(ValueError):
            release.load_release_evaluator(self.model, self.selection)
        loader.assert_not_called()

    def test_prediction_values_ids_and_units_are_unchanged_and_source_stays_separate(self):
        evaluator = self.load_fixture()
        design = dict(zip(release.FEATURES, (4., 10., 3., 4.)))
        plain = SurrogateEvaluator(evaluator.model, evaluator.model_identity).evaluate(design)
        record = evaluator.evaluate(design)
        for key in ("targets", "prediction_id", "model_identity", "design_id", "identity", "units"):
            self.assertEqual(record[key], plain[key])
        self.assertTrue(record["validation_scope"]["accuracy_target_met"])
        self.assertFalse(record["validation_scope"]["accuracy_guaranteed"])
        self.assertNotIn("fixed_P4_L4_energy", json.dumps(record))
        db = V4Store(self.batch / "fixture_predictions.sqlite")
        try:
            db.save_prediction(record)
            with self.assertRaises(ValueError): db.save_evaluation(record)
            saved = json.loads(db.db.execute("SELECT record_json FROM predictions").fetchone()[0])
            self.assertEqual(saved["validation_scope"], record["validation_scope"])
            self.assertEqual(db.db.execute("SELECT COUNT(*) FROM evaluations").fetchone()[0], 0)
        finally:
            db.close()

    def test_failed_final_accuracy_remains_failed_but_predictions_are_permitted(self):
        self.summary["accuracy_target_met"] = False
        self.metrics["gate"]["passed"] = False
        self.metrics["groups"]["near_slice"]["targets"][release.TARGETS[0]]["pass_rate"] = .8
        self.update_artifact("evaluation_summary", self.summary)
        self.update_artifact("final_metrics", self.metrics)
        evaluator = self.load_fixture()
        record = evaluator.evaluate(dict(zip(release.FEATURES, (4., 10., 3., 4.))))
        self.assertEqual(record["targets"], dict(zip(release.TARGETS, (100., 39., 2.))))
        self.assertEqual(record["validation_scope"]["status"], "empirical_fixed_distribution_target_not_met")
        self.assertTrue(record["validation_scope"]["prediction_permitted"])
        self.assertFalse(record["validation_scope"]["accuracy_target_met"])
        self.assertFalse(record["eligible_as_validated_training_truth"])


if __name__ == "__main__":
    unittest.main()
