"""Usage metadata and small fixture prediction/scan checks; no fitting or oracle."""
from copy import deepcopy
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from mamyshev_ml.model_usage import DEFAULT_CONFIG, annotate_prediction, usage_metadata
from mamyshev_ml.v4_evaluators import SurrogateEvaluator, design_id, digest
from mamyshev_ml.v4_scan import execute_scan, make_plan
from mamyshev_ml.v4_store import V4Store

MODEL_HASH = "4e0097e404281b3b8eaee075fb1d7f6d7db3e4a817daa823ac04bc5cfd263935"
DEFAULT = {"pump_power_W": 4., "filter_offset_nm": 10., "filter2_bw_nm": 3., "gain_length_m": 4.}


class ConstantFixture:
    """Tagged artificial predictions, never a V4 production weight replacement."""
    def predict(self, X):
        return [[100., 39., 2.] for _ in X]


class ModelUsageTests(unittest.TestCase):
    def test_registry_exact_hash_and_readonly_evidence_agree(self):
        registry = json.loads(DEFAULT_CONFIG.read_text())
        known = registry["models"][MODEL_HASH]
        selection = json.loads((ROOT / known["evidence"]["selection"]["path"]).read_text())
        self.assertEqual(selection["model_sha256"], MODEL_HASH)
        self.assertEqual(hashlib.sha256((ROOT/"reports/local/accuracy_v4_001/models/model.joblib").read_bytes()).hexdigest(), MODEL_HASH)
        for item in known["evidence"].values():
            if isinstance(item, dict):
                self.assertEqual(hashlib.sha256((ROOT/item["path"]).read_bytes()).hexdigest(), item["sha256"])
        metrics = json.loads((ROOT/known["evidence"]["final_metrics"]["path"]).read_text())
        self.assertEqual(known["validation_scope"]["reference_test"]["joint_pass_rate"], metrics["test"]["metrics"]["joint_pass_rate"])
        limitations = {x["id"]: x for x in known["known_limitations"]}
        self.assertEqual(limitations["fixed_P4_L4_energy"]["energy_pass_rate"], metrics["challenge"]["groups"]["fixed_P4_L4"]["targets"]["compressed_energy_nJ"]["pass_rate"])
        self.assertEqual(limitations["pump_4_6_observed_bin"]["energy_pass_rate"], metrics["test"]["input_bins"]["pump_power_W_bin2"]["metrics"]["targets"]["compressed_energy_nJ"]["pass_rate"])

    def test_fixed_hardware_energy_caution_does_not_disable_other_targets(self):
        result = usage_metadata(MODEL_HASH, DEFAULT)
        scope = result["validation_scope"]
        self.assertTrue(scope["prediction_permitted"])
        self.assertFalse(scope["accuracy_guaranteed"])
        self.assertIn("fixed_P4_L4_energy", scope["input_assessment"]["matched_observational_cautions"])
        specific = next(item for item in result["known_limitations"] if item["id"] == "fixed_P4_L4_energy")
        self.assertEqual(specific["affected_targets"], ["compressed_energy_nJ"])

    def test_nearby_inputs_and_pump_bin_are_not_region_bans_or_certificates(self):
        for d in ({**DEFAULT, "gain_length_m": 4.1}, {**DEFAULT, "pump_power_W": 5.},
                  {**DEFAULT, "pump_power_W": 7.}):
            scope = usage_metadata(MODEL_HASH, d)["validation_scope"]
            self.assertTrue(scope["prediction_permitted"])
            self.assertFalse(scope["accuracy_guaranteed"])
            self.assertFalse(scope["input_assessment"]["absence_of_match_implies_reliable"])
            self.assertNotIn("fixed_P4_L4_energy", scope["input_assessment"]["matched_observational_cautions"])
        caution = usage_metadata(MODEL_HASH, {**DEFAULT, "pump_power_W": 5.})["known_limitations"]
        self.assertEqual(next(x for x in caution if x["id"] == "pump_4_6_observed_bin")["status"],
                         "observed_subgroup_shortfall_not_a_region_ban")

    def test_unknown_model_remains_not_evaluated_without_inheriting_v4_rates(self):
        value = usage_metadata("another_fixture_hash", DEFAULT)
        self.assertEqual(value["model_usage"]["registry_status"], "not_evaluated")
        self.assertEqual(value["validation_scope"]["status"], "not_evaluated")
        self.assertNotIn("reference_test", value["validation_scope"])
        self.assertTrue(value["validation_scope"]["prediction_permitted"])
        self.assertFalse(value["validation_scope"]["accuracy_guaranteed"])

    def test_annotations_do_not_mutate_values_ids_or_frozen_cli_record(self):
        original = {"kind": "Prediction", "design": DEFAULT, "model_sha256": MODEL_HASH,
                    "targets_prediction": {"compressed_energy_nJ": 100., "compressed_duration_fs": 39., "compressed_peak_power_MW": 2.},
                    "oracle_evaluation": False, "eligible_as_validated_training_truth": False}
        before = deepcopy(original); result = annotate_prediction(original)
        self.assertEqual(original, before)
        for key, value in before.items(): self.assertEqual(result[key], value)
        self.assertEqual(annotate_prediction(result), result)
        result["known_limitations"][0]["status"] = "changed_copy"
        self.assertNotEqual(annotate_prediction(original)["known_limitations"][0]["status"], "changed_copy")

    def test_conflicting_identity_and_evaluation_annotation_rejected(self):
        record = {"kind": "Prediction", "design": DEFAULT, "model_sha256": MODEL_HASH}
        with self.assertRaises(ValueError): annotate_prediction(record, {"sha256": "different"})
        with self.assertRaises(ValueError): annotate_prediction({"kind": "Evaluation", "model_sha256": MODEL_HASH})
        with self.assertRaises(ValueError): annotate_prediction({"kind": "Prediction"})

    def test_fixture_surrogate_preserves_numeric_output_and_prediction_id(self):
        identity = {"model_id": "tagged_constant_fixture", "sha256": "fixture_only"}
        evaluator = SurrogateEvaluator(ConstantFixture(), identity)
        output = evaluator.evaluate(DEFAULT)
        self.assertEqual(output["targets"], {"compressed_energy_nJ": 100., "compressed_duration_fs": 39., "compressed_peak_power_MW": 2.})
        self.assertEqual(output["prediction_id"], "p_" + digest([design_id(DEFAULT), identity])[:24])
        self.assertEqual(output["model_identity"], identity)
        self.assertEqual(output["identity"], evaluator.identity)
        self.assertEqual(output["model_usage"]["registry_status"], "not_evaluated")

    def test_small_fixture_prediction_scan_persists_scope_without_labels(self):
        identity = {"model_id": "tagged_constant_fixture", "sha256": "fixture_only"}
        evaluator = SurrogateEvaluator(ConstantFixture(), identity)
        plan = make_plan(method="candidates", designs=[DEFAULT, {**DEFAULT, "pump_power_W": 4.1}])
        with tempfile.TemporaryDirectory() as directory:
            store = V4Store(Path(directory)/"predictions.sqlite")
            try:
                result = execute_scan(store, plan, evaluator, scan_id="usage_fixture", budget={"max_new_attempts": 2, "total_wall_s": 10}, stop_path=Path(directory)/"STOP")
                self.assertEqual(result["state_counts"], {"predicted": 2})
                self.assertEqual(store.db.execute("SELECT count(*) FROM evaluations").fetchone()[0], 0)
                for row in store.scan_records("usage_fixture"):
                    self.assertEqual(row["evaluation"]["validation_scope"]["status"], "not_evaluated")
                    self.assertEqual(row["evaluation"]["prediction_source"], "surrogate_prediction")
                    with self.assertRaises(ValueError): store.save_evaluation(row["evaluation"])
                self.assertEqual(store.training_records(source="repository_guided_synthetic"), [])
            finally:
                store.close()


class BudgetBatchRoutingTests(unittest.TestCase):
    def test_default_old_and_explicit_new_batch_select_separate_existing_roots(self):
        # Parser-only denial before mkdir/monitor; no child process or ledger write.
        path = ROOT/"scripts/run_v4_budget.py"
        spec = importlib.util.spec_from_file_location("v41_budget_parser_fixture", path)
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as directory:
            for options, name in (([], "accuracy_v4_001"), (["--batch", "accuracy_v4_1_001"], "accuracy_v4_1_001")):
                args = [str(path), "--timeout-s", "5", *options, "engineering", "fixture", "--", "-m", "unittest"]
                with self.subTest(batch=name), patch.object(module, "ROOT", Path(directory)), patch.object(sys, "argv", args), \
                        patch.object(Path, "is_dir", autospec=True, return_value=False) as exists, contextlib.redirect_stderr(io.StringIO()):
                    with self.assertRaises(SystemExit): module.main()
                    self.assertEqual(exists.call_args.args[0], Path(directory)/"reports/local"/name)
                self.assertEqual(list(Path(directory).iterdir()), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
