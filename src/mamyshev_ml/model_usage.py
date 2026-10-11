"""Read-only empirical usage annotations; never fits, predicts or calls an oracle.

The frozen artifact loader verifies actual model bytes. This module matches the
declared weight hash exactly and describes its evidence; it is not a model loader
or a per-point accuracy classifier. Unregistered hashes remain explicitly unknown.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "configs/v4_model_usage.json"


def usage_metadata(model_sha256, design=None, *, config_path=DEFAULT_CONFIG):
    """Return independent metadata; no numerical target or model identity changes."""
    content = Path(config_path).read_bytes()
    registry = json.loads(content)
    if registry.get("schema_version") != "mamyshev_model_usage_v1" or not isinstance(registry.get("models"), dict):
        raise ValueError("Invalid model usage registry")
    if not isinstance(model_sha256, str) or not model_sha256:
        raise ValueError("A declared model weight hash is required")
    matched = registry["models"].get(model_sha256)
    provenance = {"schema_version": registry["schema_version"], "usage_version": registry["usage_version"],
                  "registry_sha256": hashlib.sha256(content).hexdigest(), "declared_model_sha256": model_sha256,
                  "matching_rule": "Exact declared weight SHA-256; trusted loader separately verifies actual model bytes"}
    if matched is None:
        return {"prediction_source": "surrogate_prediction", "model_version": "unregistered_model",
                "model_usage": {**provenance, "registry_status": "not_evaluated", "training_target_source": None},
                "validation_scope": {"status": "not_evaluated", "prediction_permitted": True,
                    "accuracy_guaranteed": False, "validated_for_real_solver": False,
                    "per_input_accuracy": "not_established",
                    "reason": "No empirical usage entry matches this model hash; no V4 evidence is transferred to another model."},
                "known_limitations": [{"id": "unregistered_model", "status": "validation_not_evaluated",
                    "interpretation": "Unknown validation scope is not evidence of reliability or model failure."}]}
    if matched.get("model_sha256") != model_sha256:
        raise ValueError("Registry key and declared model hash disagree")
    scope = deepcopy(matched["validation_scope"])
    assessment = {"status": "no_per_input_accuracy_certification", "matched_observational_cautions": [],
                  "absence_of_match_implies_reliable": False}
    if isinstance(design, dict):
        pump, length = design.get("pump_power_W"), design.get("gain_length_m")
        if pump == 4 and length == 4:
            assessment["matched_observational_cautions"].append("fixed_P4_L4_energy")
        if isinstance(pump, (int, float)) and not isinstance(pump, bool) and 4 <= pump < 6:
            assessment["matched_observational_cautions"].append("pump_4_6_observed_bin")
    scope["input_assessment"] = assessment
    return {"prediction_source": "surrogate_prediction", "model_version": matched["model_version"],
            "model_usage": {**provenance, "registry_status": "matched_frozen_hash",
                "training_target_source": matched["training_target_source"],
                "training_target_backend": matched["training_target_backend"],
                "evidence_kind": matched["evidence_kind"], "evidence": deepcopy(matched["evidence"])},
            "validation_scope": scope, "known_limitations": deepcopy(matched["known_limitations"])}


def annotate_prediction(record, model_identity=None, *, config_path=DEFAULT_CONFIG):
    """Copy and annotate an existing Prediction, preserving targets and IDs.

    Also accepts the frozen legacy CLI's model_sha256 field for explicitly
    requested external annotation; neither that CLI nor its old artifacts change.
    """
    if not isinstance(record, dict) or record.get("kind") != "Prediction":
        raise ValueError("Usage annotations apply only to Prediction records")
    identities = [value for value in (model_identity, record.get("model_identity")) if value is not None]
    hashes = [identity.get("sha256") for identity in identities if isinstance(identity, dict)]
    if record.get("model_sha256") is not None:
        hashes.append(record["model_sha256"])
    if not hashes or any(not isinstance(value, str) or not value for value in hashes) or len(set(hashes)) != 1:
        raise ValueError("Prediction model hash is missing or conflicting")
    metadata = usage_metadata(hashes[0], record.get("design"), config_path=config_path)
    result = deepcopy(record)
    for key, value in metadata.items():
        if key in result and result[key] != value:
            raise ValueError("Refusing to replace a different prior usage annotation")
        result[key] = value
    return result
