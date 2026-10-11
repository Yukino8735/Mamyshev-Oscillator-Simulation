"""Source-separated scalar evaluators. Only GMMNLSE invokes the existing supervisor."""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "mamyshev_accuracy_v4"
FEATURES = ("pump_power_W", "filter_offset_nm", "filter2_bw_nm", "gain_length_m")
TARGETS = ("compressed_energy_nJ", "compressed_duration_fs", "compressed_peak_power_MW")
UNITS = dict(zip(TARGETS, ("nJ", "fs", "MW")))
IDENTITY_FIELDS = ("source", "backend", "numerical_version", "seed", "observation_protocol", "metric_definition")


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def validate_design(design):
    if set(design) != set(FEATURES):
        raise ValueError("Exactly four design fields required; no aliases or silently ignored fields.")
    domain = json.loads((PACKAGE / "configs/domain.json").read_text())
    result = {}
    for key in FEATURES:
        x = design[key]
        if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
            raise ValueError(f"{key}: finite real required")
        lo, hi = domain["bounds"][key]
        if not lo <= x <= hi:
            raise ValueError(f"{key}: outside declared exploratory domain [{lo}, {hi}]")
        result[key] = float(x)
    grid = result["gain_length_m"] / domain["gain_length_step_m"]
    if abs(grid - round(grid)) > 1e-9:
        raise ValueError("Gain length must already be on the 0.1 m save grid; no implicit rounding.")
    return result


def design_id(design):
    return "d_" + digest(validate_design(design))[:24]


def identity_key(identity):
    if set(identity) != set(IDENTITY_FIELDS) or any(identity[k] is None for k in IDENTITY_FIELDS):
        raise ValueError("Exact source/backend/version/seed/observation/metric identity required.")
    return digest(identity)


def null_evaluation(design, identity, reason, status="not_available"):
    d = validate_design(design)
    return {"kind": "Evaluation", "design": d, "design_id": design_id(d), "identity": identity,
            "source_kind": identity["source"], "job_status": status,
            "targets": dict.fromkeys(TARGETS), "units": UNITS, "missing_reason": reason,
            "artifacts": [], "waveforms": None, "waveforms_missing_reason": reason,
            "physical_state": "undetermined", "numerical_validation": "not_verified",
            "eligible_as_validated_training_truth": False}


class SyntheticEvaluator:
    """Frozen V3 oracle, evaluated on demand; cached events still count as calls."""
    def __init__(self, seed=0):
        self.seed = seed
        self.calls = self.unique_computations = self.cache_hits = 0
        self.cache = {}
        path = PACKAGE / "reference/oracle.py"
        spec = importlib.util.spec_from_file_location("_mamyshev_v4_frozen_oracle", path)
        self.oracle = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.oracle)
        self.identity = {"source": "repository_guided_synthetic", "backend": "mamyshev_repository_guided_synthetic_v3",
                         "numerical_version": hashlib.sha256(path.read_bytes()).hexdigest(), "seed": seed,
                         "observation_protocol": {"kind": "deterministic_scalar_formula", "noise": False},
                         "metric_definition": {"plane": "constructed_compressed_scalars", "units": UNITS,
                                               "recipe_sha256": hashlib.sha256((PACKAGE / "configs/generator_recipe.json").read_bytes()).hexdigest()}}

    def evaluate(self, design, **kwargs):
        d = validate_design(design); did = design_id(d)
        if kwargs.get("design_id", did) != did or kwargs.get("seed", self.seed) != self.seed:
            raise ValueError("Explicit design_id/seed conflicts with evaluator identity")
        self.calls += 1
        hit = did in self.cache
        if hit:
            self.cache_hits += 1
        else:
            record = null_evaluation(d, self.identity, "", "completed")
            record["targets"] = self.oracle.evaluate(d)
            record["waveforms_missing_reason"] = "Scalar synthetic oracle computes no complex fields."
            record["evaluation_id"] = "e_" + digest([did, self.identity])[:24]
            self.cache[did] = record
            self.unique_computations += 1
        result = copy.deepcopy(self.cache[did])
        result.update(cache_hit=hit, request_id=kwargs.get("request_id"), logical_call=self.calls)
        return result

    def evaluate_targets(self, design):
        return self.evaluate(design)["targets"]


class RecordedEvaluator:
    def __init__(self, store, identity):
        identity_key(identity)
        self.store, self.identity = store, copy.deepcopy(identity)

    def evaluate(self, design, **kwargs):
        result = self.store.lookup(design, self.identity)
        if result is None:
            return null_evaluation(design, self.identity, "No exact design/source/backend/version/seed/observation/metric match; no fallback.")
        return result


class SurrogateEvaluator:
    """The caller supplies its own trusted fitted model; never imports an oracle."""
    def __init__(self, model, model_identity):
        self.model, self.model_identity = model, copy.deepcopy(model_identity)
        self.identity = {"source": "surrogate_prediction", "backend": model_identity["model_id"],
                         "numerical_version": model_identity["sha256"], "seed": 0,
                         "observation_protocol": {"kind": "prediction_only"}, "metric_definition": UNITS}

    def evaluate(self, design, **kwargs):
        import numpy as np
        from .model_usage import annotate_prediction
        d = validate_design(design)
        y = np.asarray(self.model.predict(np.array([[d[k] for k in FEATURES]])), dtype=float).reshape(-1)
        if len(y) != 3 or not np.isfinite(y).all() or (y <= 0).any():
            raise ValueError("Prediction must contain three finite positive scalar values")
        record = {"kind": "Prediction", "design": d, "design_id": design_id(d), "identity": self.identity,
                "prediction_id": "p_" + digest([design_id(d), self.model_identity])[:24],
                "model_identity": self.model_identity, "targets": dict(zip(TARGETS, y.tolist())),
                "units": UNITS, "job_status": "predicted", "waveforms": None,
                "waveforms_missing_reason": "Scalar prediction; no propagated field exists.",
                "eligible_as_validated_training_truth": False}
        return annotate_prediction(record)


def import_safe_result(final_path):
    """Read only: retain historical identity and exact plane definitions, verify MAT references."""
    path = Path(final_path).resolve()
    if path.name != "final_result.json":
        raise ValueError("Only the parent final_result.json can be imported; candidate is never a final")
    final = json.loads(path.read_text()); request = json.loads((path.parent / "launch_request.json").read_text())
    if final.get("result_protocol_version") != "safe_result_v1":
        raise ValueError("Expected parent safe_result_v1")
    provenance = final["provenance"]
    parent = final.get("supervisor", {})
    if parent.get("final_writer") != "parent_supervisor" or parent.get("runner_record") != "runner_record.json":
        raise ValueError("Verified parent writer and original runner reference required")
    runner_path = path.parent / "runner_record.json"
    runner = json.loads(runner_path.read_text())
    if any(record.get("run_id") != request["run_id"] or record.get("source_identity") != request["source_identity"] for record in (provenance, runner)):
        raise ValueError("Parent/request/runner run or source identity mismatch")
    if provenance.get("requested_seed") != request.get("seed"):
        raise ValueError("Final and request seed identity differ")
    if parent.get("exit_code") != runner.get("exit_code") or parent.get("stop_events", []) != runner.get("stop_events", []):
        raise ValueError("Parent and runner exit/stop events disagree")
    stops = [e.get("reason") for e in runner.get("stop_events", []) if e.get("reason") in ("timeout", "cancelled", "runner_interrupted")]
    if not stops and runner.get("stop_reason") in ("timeout", "cancelled", "runner_interrupted"):
        stops = [runner["stop_reason"]]
    if stops and final["job_status"] != (stops[0] if stops[0] != "runner_interrupted" else "failed"):
        raise ValueError("Parent final does not preserve first runner stop")
    if final["job_status"] == "completed" and (runner.get("status") != "completed" or runner.get("exit_code") != 0 or
            runner.get("cleanup_verified") is not True or runner.get("cleanup_error") or stops or
            parent.get("candidate_valid") is not True or parent.get("required_records_error") is not None):
        raise ValueError("Completed final lacks consistent clean runner/candidate gate")
    if "design_config" not in request:
        raise ValueError("No explicit four-input request identity; historical partial design cannot be invented")
    d = validate_design(request["design_config"])
    if provenance.get("design_config", request["design_config"] if final["job_status"] != "completed" else None) != request["design_config"]:
        raise ValueError("Final and request design differ")
    if provenance["source_identity"] != request["source_identity"]:
        raise ValueError("Final and request source identity differ")
    compressed = final["outputs"]["compressed_analysis"]
    definitions = {name: {k: compressed[name].get(k) for k in ("unit", "definition", "source")}
                   for name in ("energy", "fwhm", "peak_power")}
    definitions.update(plane=compressed["plane"], processing=compressed["processing"])
    protocol = request.get("observation_protocol", {"mode": "legacy", "max_rt": 50, "stopping": "legacy_energy_stop"})
    if "observation_options" in request:
        options = request["observation_options"]
        protocol = {"mode": options["observation_mode"], "roundtrips": options["observation_roundtrips"]}
    backend = provenance.get("backend_entrypoint")
    if backend is None:
        if final["job_status"] == "completed":
            raise ValueError("Completed final lacks actual backend entrypoint")
        backend = {"requested_entrypoint": "run_mamyshev_config" if request.get("mode") == "real" else "component_request",
                   "actual_entrypoint": "not_observed", "reason": "Parent failure record has no trusted backend candidate."}
    identity = {"source": provenance.get("source_kind", "parent_failure_source_not_observed"), "backend": backend,
                "numerical_version": {"version": provenance.get("numerical_version", "not_observed"), "source_digest": provenance["source_identity"]["digest"]},
                "seed": request["seed"], "observation_protocol": protocol,
                "metric_definition": definitions}
    result = null_evaluation(d, identity, "", final["job_status"])
    result.update(run_id=provenance["run_id"], final_path=str(path), stop_reason=final["stop_reason"],
                  completed_roundtrips=final.get("completed_roundtrips"), outputs=final["outputs"],
                  source_identity=provenance["source_identity"],
                  evaluation_id="e_" + digest([str(path), hashlib.sha256(path.read_bytes()).hexdigest()])[:24])
    if final["job_status"] == "completed":
        for target, key, unit, scale in zip(TARGETS, ("energy", "fwhm", "peak_power"), ("nJ", "fs", "W"), (1, 1, 1e-6)):
            metric = compressed[key]
            if metric["unit"] != unit:
                raise ValueError(f"Unexpected {key} unit")
            value = metric["value"]
            if value is not None and (not isinstance(value, (float, int)) or not math.isfinite(value)):
                raise ValueError("Nonfinite final metric")
            result["targets"][target] = None if value is None else value * scale
        result["metric_missing_reasons"] = {target: compressed[key].get("missing_reason", "") for target, key in zip(TARGETS, ("energy", "fwhm", "peak_power"))}
    else:
        result["missing_reason"] = f"Parent final is {final['job_status']}; candidate values are not labels."
    artifacts = [{"path": str(p), "sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "kind": kind}
                 for p, kind in ((path, "parent_final"), (runner_path, "runner_record"), (path.parent / "launch_request.json", "original_request"))]
    waveform = final.get("waveform_artifacts", {})
    if waveform.get("manifest_path"):
        manifest_path = _safe_artifact_path(path.parent, waveform["manifest_path"])
        manifest = json.loads(manifest_path.read_text())
        if manifest["run_id"] != provenance["run_id"] or manifest["source_identity"] != provenance["source_identity"] or manifest["design_config"] != request["design_config"]:
            raise ValueError("Waveform identity mismatch")
        if manifest["units"]["field"] != "sqrt(W)" or manifest["units"]["t"] != "ps" or manifest["units"]["f"] != "THz":
            raise ValueError("Waveform unit mismatch")
        entries = manifest["rounds"] + ([manifest["final"]] if manifest.get("final") else [])
        for entry in entries:
            artifact = _safe_artifact_path(path.parent, entry["path"]); content = artifact.read_bytes()
            if len(content) != entry["bytes"] or hashlib.sha256(content).hexdigest() != entry["sha256"]:
                raise ValueError("Waveform hash/size mismatch")
            if not content.startswith(b"MATLAB 5.0 MAT-file"):
                raise ValueError("Expected actual v7 MAT field artifact")
            artifacts.append({"path": str(artifact), "sha256": entry["sha256"], "bytes": entry["bytes"], "kind": "complex_mat"})
        result["waveforms"] = {"manifest": str(manifest_path), "finalized": manifest["finalized"], "final": manifest.get("final"), "rounds": len(manifest["rounds"])}
        result["waveforms_missing_reason"] = "" if manifest["finalized"] else "Partial saved rounds only; no final field."
    result["artifacts"] = artifacts
    return result


def _safe_artifact_path(root, name):
    if not isinstance(name, str) or not name:
        raise ValueError("Nonempty relative artifact path required")
    relative = Path(name)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("Unsafe waveform reference")
    resolved = (root / relative).resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise ValueError("Artifact symlink escapes the original run")
    return resolved


class GMMNLSEEvaluator:
    """Complete live adapter; real authorization is separate and defaults disabled."""
    def __init__(self, *, plan, authorization, batch_dir, execute_real=False, matlab="/Applications/MATLAB_R2025a.app/bin/matlab"):
        from .supervisor import source_identity
        self.plan, self.authorization, self.batch_dir = plan, authorization, Path(batch_dir)
        self.execute_real, self.matlab = execute_real, matlab
        protocol = authorization.get("observation_protocol", {"mode": "legacy"})
        if protocol == {"mode": "legacy"}:
            protocol = {"mode": "legacy", "max_rt": 50, "stopping": "legacy_energy_stop"}
        definitions = {
            "energy": {"unit": "nJ", "definition": "trapz(t_ps,sum(abs(complex_field).^2,2))/1000 on saved field", "source": "run_mamyshev.compressed_field and t"},
            "fwhm": {"unit": "fs", "definition": "Legacy compressor local peak half-height width from findpeaks; differs from global raw span", "source": "run_mamyshev.dechirped_fwhm_fs"},
            "peak_power": {"unit": "W", "definition": "Peak from the compressor-analyzed field; not energy divided by width", "source": "run_mamyshev.dechirped_peak_power_W"},
            "plane": "After output pigtail and compressor analysis", "processing": "Legacy idealized Treacy-t compression analysis"}
        self.identity = {"source": "repaired_original_backend", "backend": "run_mamyshev_config",
                         "numerical_version": {"version": "repair_001_h01_h04", "source_digest": source_identity()["digest"]},
                         "seed": authorization.get("seed", 0), "observation_protocol": protocol, "metric_definition": definitions}

    def evaluate(self, design, **kwargs):
        from .supervisor import execute_authorized_design
        did = design_id(design)
        response = execute_authorized_design(matlab=self.matlab, plan=self.plan, authorization=self.authorization,
            design_id=did, batch_dir=self.batch_dir, run_id=kwargs.get("run_id", "scan_" + did), execute_real=self.execute_real)
        return import_safe_result(response["final_path"])
