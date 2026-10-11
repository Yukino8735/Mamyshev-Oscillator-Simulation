"""Explicit, read-only V4.2 release loading; never replaces the V4 default.

Only a locally created, fully evaluated release is eligible for this loader.
Identity checks precede pickle deserialization. A failed final accuracy gate is
retained as a failed empirical scope, rather than disabling all predictions or
promoting the candidate. No oracle or model fitting is imported here.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import sys

from .v4_evaluators import SurrogateEvaluator

ROOT = Path(__file__).resolve().parents[2]
BATCH = "reports/local/accuracy_v4_2_001"
FEATURES = ("pump_power_W", "filter_offset_nm", "filter2_bw_nm", "gain_length_m")
TARGETS = ("compressed_energy_nJ", "compressed_duration_fs", "compressed_peak_power_MW")
INPUT_UNITS = dict(zip(FEATURES, ("W", "nm", "nm", "m")))
UNITS = dict(zip(TARGETS, ("nJ", "fs", "MW")))
GROUP_COUNTS = {"reference_core": 512, "reference_expanded": 512,
                "slice": 256, "near_slice": 256, "outer_faces": 256, "corners": 256}
SOURCE = "repository_guided_synthetic"
BACKEND = "mamyshev_repository_guided_synthetic_v3"
DOMAIN = "mamyshev_accuracy_v4/configs/domain.json"
REQUIRED_SOURCES = {"src/mamyshev_ml/v42_release.py", "src/mamyshev_ml/v4_evaluators.py",
                    "src/mamyshev_ml/model_usage.py", "mamyshev_accuracy_v4/reference/models_v4.py"}


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _repo_path(name):
    if not isinstance(name, str) or not name:
        raise ValueError("A repository-relative artifact path is required")
    relative = Path(name)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("Absolute or traversing release paths are not accepted")
    path = (ROOT / relative).resolve()
    if not path.is_relative_to(ROOT.resolve()):
        raise PermissionError("Release artifact resolves outside this repository")
    if not path.is_file():
        raise FileNotFoundError(path)
    return path


def _batch_file(path):
    path = Path(path).resolve()
    batch = (ROOT / BATCH).resolve()
    if not batch.is_relative_to(ROOT.resolve()) or not path.is_relative_to(batch) or not path.is_file():
        raise PermissionError("Only existing artifacts within the V4.2 batch are trusted")
    return path


def _match_hash(path, expected):
    if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected) or _sha(path) != expected:
        raise ValueError("Release artifact hash mismatch: " + str(path))


def _hash_map(value, field):
    if not isinstance(value, dict) or not value:
        raise ValueError("A nonempty " + field + " map is required")
    for name, digest in value.items():
        _match_hash(_repo_path(name), digest)


def _statistics(value, n):
    if not isinstance(value, dict) or type(value.get("n")) is not int or value["n"] != n:
        raise ValueError("Final metric sample count mismatch")
    if set(value.get("targets", {})) != set(TARGETS):
        raise ValueError("Final metric target order/schema mismatch")
    rates = [value.get("joint_pass_rate"), *(value["targets"][key].get("pass_rate") for key in TARGETS)]
    if any(isinstance(rate, bool) or not isinstance(rate, (int, float)) or not 0 <= rate <= 1 for rate in rates):
        raise ValueError("Final metrics require finite empirical pass fractions")


def verify_release(model_path, selection_path):
    """Verify paths, hashes, frozen scope and identities without loading weights.

    Return the manifest plus ``verification`` paths and verified copies of
    ``evaluation_summary``, ``final_metrics`` and ``protocol``. These extra keys
    are in-memory results; this function never writes or amends the manifest.
    """
    model_path, selection_path = _batch_file(model_path), _batch_file(selection_path)
    manifest = json.loads(selection_path.read_text())
    if manifest.get("schema_version") != "mamyshev_v42_release_v1" or manifest.get("frozen") is not True:
        raise ValueError("A frozen V4.2 release manifest is required")
    for field in ("release_id", "selected"):
        if not isinstance(manifest.get(field), str) or not manifest[field]:
            raise ValueError("Release identity is missing: " + field)
    if manifest.get("development_accuracy_target_met") is not True or manifest.get("deployment_replaced") is not False:
        raise PermissionError("Only a development-passing, separately retained review candidate may be loaded")
    if manifest.get("source_kind") != SOURCE or manifest.get("backend_id") != BACKEND:
        raise ValueError("V4.2 release target-source identity mismatch")
    if (manifest.get("features") != list(FEATURES) or manifest.get("targets") != list(TARGETS)
            or manifest.get("units") != UNITS or manifest.get("input_units") != INPUT_UNITS):
        raise ValueError("Explicit input/output order and units must match the original four-input model")
    parameters = manifest.get("parameters", {})
    if (manifest.get("model_family") != "spline_interactions" or type(manifest.get("n_train")) is not int
            or manifest["n_train"] != 1024 or parameters.get("n_knots") not in (16, 32, 64)
            or parameters.get("alpha") not in (.1, .001) or parameters.get("degree") != 3
            or parameters.get("knots") != "uniform" or parameters.get("interaction_polynomial_degree") != 4
            or parameters.get("log_targets") is not True):
        raise ValueError("Release does not use the fixed V4.2 representation matrix")
    paths = {}
    for kind in ("model", "protocol", "training_ids", "evaluation_summary", "final_metrics"):
        path = _repo_path(manifest.get(kind + "_path"))
        if kind in ("model", "protocol", "evaluation_summary", "final_metrics"):
            _batch_file(path)
        _match_hash(path, manifest.get(kind + "_sha256"))
        paths[kind + "_path"] = path
    if paths["model_path"] != model_path:
        raise ValueError("Requested weights differ from the release model path")
    sources, data = manifest.get("source_hashes"), manifest.get("data_hashes")
    _hash_map(sources, "source_hashes"); _hash_map(data, "data_hashes")
    if not REQUIRED_SOURCES.issubset(sources) or DOMAIN not in data or manifest["training_ids_path"] not in data:
        raise ValueError("Required source/domain/training-ID identities are absent")
    protocol = json.loads(paths["protocol_path"].read_text())
    if protocol.get("sources") != sources or protocol.get("data_hashes") != data:
        raise ValueError("Release source/data hashes differ from the frozen protocol")
    ids = json.loads(paths["training_ids_path"].read_text())
    if (not isinstance(ids, list) or len(ids) != 1024
            or any(not isinstance(key, str) or not re.fullmatch(r"d_[0-9a-f]{24}", key) for key in ids)
            or len(set(ids)) != 1024):
        raise ValueError("Exactly 1024 distinct canonical training IDs are required")
    summary = json.loads(paths["evaluation_summary_path"].read_text())
    if (summary.get("pipeline_completed") is not True or summary.get("development_accuracy_target_met") is not True
            or summary.get("calibration_status") != "completed" or summary.get("test_status") != "completed"
            or type(summary.get("accuracy_target_met")) is not bool or summary.get("selected") != manifest["selected"]
            or summary.get("deployment_replaced") is not False):
        raise ValueError("Release requires the completed conditional evaluation, including its actual pass/fail")
    final = json.loads(paths["final_metrics_path"].read_text())
    if (final.get("selected") != manifest["selected"] or final.get("model_sha256") != manifest["model_sha256"]
            or type(final.get("gate", {}).get("passed")) is not bool
            or final["gate"]["passed"] != summary["accuracy_target_met"]):
        raise ValueError("Evaluation/model/accuracy identities disagree")
    _statistics(final.get("metrics"), 2048)
    if set(final.get("groups", {})) != set(GROUP_COUNTS):
        raise ValueError("All six fixed test groups are required")
    for name, n in GROUP_COUNTS.items():
        _statistics(final["groups"][name], n)
    result = deepcopy(manifest)
    result.update(verification={**{k: str(v) for k, v in paths.items()},
                               "selection_path": str(selection_path), "selection_sha256": _sha(selection_path)},
                  evaluation_summary=summary, final_metrics=final, protocol=protocol)
    return result


def _scope(verified):
    final = verified["final_metrics"]
    passed = verified["evaluation_summary"]["accuracy_target_met"]
    fractions = lambda value: {"n": value["n"], "joint_pass_rate": value["joint_pass_rate"],
                               "target_pass_rates": {k: value["targets"][k]["pass_rate"] for k in TARGETS}}
    return {"status": "empirical_fixed_distribution_pass" if passed else "empirical_fixed_distribution_target_not_met",
            "prediction_permitted": True, "accuracy_guaranteed": False, "validated_for_real_solver": False,
            "per_input_accuracy": "not_established", "accuracy_target_met": passed,
            "distribution_weights": {name: n / 2048 for name, n in GROUP_COUNTS.items()},
            "test": fractions(final["metrics"]), "groups": {name: fractions(value) for name, value in final["groups"].items()},
            "gate": deepcopy(final["gate"]), "deployment_status": "independent_candidate_pending_review",
            "absence_of_observed_failure_implies_reliable": False}


class V42ReleaseEvaluator(SurrogateEvaluator):
    """The same scalar prediction, with verified V4.2-only evidence metadata."""
    def __init__(self, model, model_identity, verified):
        super().__init__(model, model_identity)
        self.release = deepcopy(verified)

    def evaluate(self, design, **kwargs):
        record = super().evaluate(design, **kwargs)
        # The shared evaluator has added the default registry's unknown scope.
        # Replace ONLY metadata using the independently verified release; never
        # transplant V4's slice failures or change targets, identity, or IDs.
        result = deepcopy(record)
        release = self.release
        result.update(prediction_source="surrogate_prediction", model_version=release["release_id"],
            model_usage={"schema_version": "mamyshev_v42_release_usage_v1", "registry_status": "verified_release_hash",
                "declared_model_sha256": release["model_sha256"], "training_target_source": SOURCE,
                "training_target_backend": BACKEND, "source_hashes": deepcopy(release["source_hashes"]),
                "data_hashes": deepcopy(release["data_hashes"]), "protocol_sha256": release["protocol_sha256"],
                "evidence": {kind: {"path": release[kind + "_path"], "sha256": release[kind + "_sha256"]}
                             for kind in ("protocol", "training_ids", "evaluation_summary", "final_metrics")},
                "selection_sha256": release["verification"]["selection_sha256"],
                "evidence_kind": "fixed_stratified_synthetic_evaluation_not_GMMNLSE_or_experiment"},
            validation_scope=_scope(release),
            known_limitations=[{"id": "synthetic_distribution_only", "interpretation":
                "Empirical results apply to the saved fixed stratified sample and synthetic label source; no arbitrary-input, per-group conditional, active-search, or real-solver accuracy guarantee."},
                {"id": "final_gate_status", "accuracy_target_met": release["evaluation_summary"]["accuracy_target_met"],
                 "interpretation": "The final gate and every test group remain visible; this independent candidate does not replace the V4 default."}])
        return result


def load_release_evaluator(model_path, selection_path, model_identity=None):
    """Verify first, then load one explicit local model for review predictions."""
    verified = verify_release(model_path, selection_path)
    identity = deepcopy(model_identity) if model_identity is not None else {
        "model_id": verified["release_id"], "sha256": verified["model_sha256"]}
    if (not isinstance(identity, dict) or not isinstance(identity.get("model_id"), str)
            or not identity["model_id"] or identity.get("sha256") != verified["model_sha256"]):
        raise ValueError("Prediction identity does not match the verified release weights")
    reference = (ROOT / "mamyshev_accuracy_v4/reference").resolve()
    loaded = sys.modules.get("models_v4")
    if loaded is not None and Path(getattr(loaded, "__file__", "")).resolve() != reference / "models_v4.py":
        raise ValueError("models_v4 was imported from an unverified location")
    if str(reference) not in sys.path:
        sys.path.insert(0, str(reference))
    import joblib
    model = joblib.load(Path(verified["verification"]["model_path"]))
    domain = json.loads(_repo_path(DOMAIN).read_text())["bounds"]
    if (getattr(model, "family", None) != verified["model_family"]
            or getattr(model, "parameters", None) != verified["parameters"]
            or getattr(model, "domain", None) != domain or len(getattr(model, "models", ())) != 3):
        raise ValueError("Loaded model does not match the frozen representation/domain/three-target schema")
    return V42ReleaseEvaluator(model, identity, verified)
