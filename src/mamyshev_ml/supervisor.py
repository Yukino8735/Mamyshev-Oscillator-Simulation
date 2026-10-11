"""One owned process, one MATLAB candidate, one parent-owned safe_result_v1 final.

No retries, simulator substitutes, or physics classification. Source identity is
captured before launch and checked again before accepting a completed result.
The process-group/budget implementation is the existing short-test monitor.
"""
from copy import deepcopy
import fcntl
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("mamyshev_owned_monitor", ROOT / "tests/run_matlab_short.py")
monitor = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(monitor)
FINALIZER_VERSION = "launchprep_001"
DEFAULT_DESIGN_CONFIG = {"pump_power_W": 4, "filter_offset_nm": 10,
                         "filter2_bw_nm": 3, "gain_length_m": 4}


def validate_design_config(value):
    """Units are explicit in keys; historical ranges are not validated domains."""
    if not isinstance(value, dict) or set(value) != set(DEFAULT_DESIGN_CONFIG):
        raise ValueError("Exactly the four design keys are required; unknown/conflicting/missing fields are rejected")
    if not all(finite_number(item) for item in value.values()):
        raise ValueError("Design inputs must be finite real scalar numbers, not booleans")
    if value["pump_power_W"] < 0 or value["filter2_bw_nm"] <= 0 or value["gain_length_m"] <= 0 or 1040-value["filter_offset_nm"] <= 0:
        raise ValueError("Pump must be nonnegative, bandwidth/length/SF2 center strictly positive")
    # Same storage-grid condition as GMMNLSE_propagate. Do not round the
    # physical length or adjust the existing 0.1 m save period.
    ratio = value["gain_length_m"] / 0.1
    if not math.isfinite(ratio) or ratio < 1 or abs(ratio-round(ratio)) > math.ulp(ratio):
        raise ValueError("Gain length must span at least one inherited 0.1 m save interval and fit that grid")
    return deepcopy(value)


def finite_number(value):
    try:
        return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)
    except OverflowError:
        return False


def validate_observation_options(value):
    """Observation duration is separate from the four physical design inputs."""
    if not isinstance(value, dict) or set(value) != {"observation_mode", "observation_roundtrips"}:
        raise ValueError("Exactly observation_mode and observation_roundtrips are required")
    count = value["observation_roundtrips"]
    if value["observation_mode"] != "fixed_roundtrips" or not finite_number(count) or count != int(count) or not 1 <= count <= 50:
        raise ValueError("Fixed observation requires an integer round count from 1 through the unchanged max_rt=50")
    return deepcopy(value)


def atomic_json(path, value, *, replace=False):
    """fsync then atomically install; hard-link commit refuses existing evidence."""
    path = Path(path)
    fd, temporary = tempfile.mkstemp(prefix=".pending-", suffix=".json", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(value, stream, indent=2, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        if replace:
            os.replace(temporary, path)
        else:
            os.link(temporary, path)  # atomic no-clobber, same filesystem
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def source_identity(root=ROOT):
    files = sorted(p for directory in ("code", "src", "scripts", "configs", "tests")
                   for p in (root / directory).rglob("*")
                   if p.is_file() and p.suffix in {".m", ".py", ".json", ".txt", ".mat", ".ptx", ".cu"}
                   and "__pycache__" not in p.parts)
    entries = [{"path": p.relative_to(root).as_posix(),
                "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]
    digest = hashlib.sha256(json.dumps(entries, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {"digest": digest, "files": entries}


def request_identity(run_id, mode):
    return {"run_id": run_id, "mode": mode, "seed": 0,
            "requested": {"PumpPower": 4, "cw2": 1030, "plot_on": False},
            "source_identity": source_identity(),
            "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "worktree_status": subprocess.check_output(["git", "status", "--short"], cwd=ROOT, text=True),
            "finalizer_version": FINALIZER_VERSION}


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def validate_live_authorization(plan, authorization, design_id):
    """Pure validation; a plan or a dry run is never execution permission."""
    required = {"authorization_id", "plan_hash", "allowed_design_ids", "max_new_attempts",
                "per_run_timeout_s", "total_wall_limit_s"}
    optional = {"seed", "observation_protocol", "save_waveforms"}
    if not isinstance(authorization, dict) or not required <= authorization.keys() or set(authorization)-required-optional:
        raise ValueError("Explicit live authorization fields are missing or unknown")
    payload = {key: value for key, value in plan.items() if key != "plan_hash"}
    if plan.get("plan_hash") != canonical_hash(payload) or authorization["plan_hash"] != plan["plan_hash"]:
        raise ValueError("Authorization must match the complete canonical plan hash")
    identifier = authorization["authorization_id"]
    if not isinstance(identifier, str) or not identifier or not identifier.replace("_", "").replace("-", "").isalnum():
        raise ValueError("Invalid authorization_id")
    allowed = authorization["allowed_design_ids"]
    if not isinstance(allowed, list) or not allowed or any(not isinstance(x, str) or not x for x in allowed) or len(set(allowed)) != len(allowed):
        raise ValueError("Allowed design IDs must be explicit and unique")
    rows = plan.get("designs")
    if not isinstance(rows, list) or any(not isinstance(row, dict) or not isinstance(row.get("design_id"), str) for row in rows):
        raise ValueError("Plan designs are missing or malformed")
    ids = [row["design_id"] for row in rows]
    if len(set(ids)) != len(ids) or not set(allowed) <= set(ids) or design_id not in allowed:
        raise ValueError("Design ID is not uniquely present and authorized")
    count = authorization["max_new_attempts"]
    if not finite_number(count) or count != int(count) or count < 0:
        raise ValueError("max_new_attempts must be a nonnegative integer")
    for key in ("per_run_timeout_s", "total_wall_limit_s"):
        if not finite_number(authorization[key]) or authorization[key] <= 30:
            raise ValueError("Live budgets must include the 30-second reserve")
    if authorization["per_run_timeout_s"] > authorization["total_wall_limit_s"]:
        raise ValueError("Per-run budget exceeds total authorization")
    seed = authorization.get("seed", 0)
    if not finite_number(seed) or seed != int(seed) or not 0 <= seed <= 2**32-1:
        raise ValueError("Seed must be a MATLAB twister uint32 seed")
    if authorization.get("save_waveforms", True) is not True:
        raise ValueError("The live data chain requires waveform retention")
    protocol = authorization.get("observation_protocol", {"mode": "legacy"})
    if protocol != {"mode": "legacy"}:
        if not isinstance(protocol, dict) or set(protocol) != {"mode", "roundtrips"}:
            raise ValueError("Unknown observation protocol")
        validate_observation_options({"observation_mode": protocol["mode"], "observation_roundtrips": protocol["roundtrips"]})
    design = validate_design_config(rows[ids.index(design_id)]["design_config"])
    return design


def execute_authorized_design(*, matlab, plan, authorization, design_id, batch_dir, run_id, execute_real=False):
    """Config-driven serial live entry using the existing single-run supervisor.

    The authorization and debit ledger are rooted by authorization_id, outside
    the caller-chosen batch. Changing batch/run IDs cannot reset the allowance.
    Incomplete attempts are charged their cap and block continuation until a
    separate audit; no automatic retries or historical final reconstruction.
    """
    design = validate_live_authorization(plan, authorization, design_id)
    if execute_real is not True or authorization["max_new_attempts"] == 0:
        raise PermissionError("Real execution is disabled or max_new_attempts=0; no attempt reserved")
    if not isinstance(run_id, str) or not run_id or not run_id.replace("_", "").isalnum():
        raise ValueError("Invalid run ID")
    matlab = Path(matlab).resolve()
    folder = Path(batch_dir).resolve() / run_id
    local_root = (ROOT / "reports/local").resolve()
    if not folder.is_relative_to(local_root) or not matlab.is_file():
        raise ValueError("An existing MATLAB executable and ignored local run directory are required")
    ledger_dir = local_root / "live_authorizations" / authorization["authorization_id"]
    ledger_dir.mkdir(parents=True, exist_ok=True)
    with (ledger_dir / ".runner.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        saved_auth = ledger_dir / "authorization.json"
        if saved_auth.exists():
            if load_json(saved_auth) != authorization:
                raise PermissionError("An authorization ID cannot be changed or reset")
        else:
            atomic_json(saved_auth, authorization)
        if (ledger_dir / "STOP").exists() or (folder.parent / "STOP").exists():
            raise PermissionError("Authorization/scan STOP is present")
        records = [load_json(p) for p in sorted(ledger_dir.glob("attempt_*.json"))]
        if any(record["status"] in {"reserved", "requires_process_audit"} for record in records):
            raise RuntimeError("Unfinalized live attempt requires explicit process/evidence audit; no automatic resume")
        if len(records) >= authorization["max_new_attempts"]:
            raise PermissionError("Authorized new-attempt allowance exhausted")
        if any(record["design_id"] == design_id for record in records):
            raise PermissionError("This authorization already attempted the design; no retry")
        remaining = authorization["total_wall_limit_s"]-sum(record["charged_wall_s"] for record in records)
        timeout = min(authorization["per_run_timeout_s"], remaining)
        if timeout <= 30:
            raise PermissionError("Cumulative live wall budget exhausted")
        if folder.exists():
            raise FileExistsError("Existing run directory cannot be overwritten or resumed")
        folder.parent.mkdir(parents=True, exist_ok=True)
        started = time.monotonic()
        ledger_path = ledger_dir / ("attempt_%06d.json" % (len(records)+1))
        attempt = {"run_id": run_id, "design_id": design_id, "run_dir": str(folder),
                   "status": "reserved", "charged_wall_s": timeout, "timeout_s": timeout}
        atomic_json(ledger_path, attempt)
        try:
            folder.mkdir()  # Ledger already consumes this reservation, even on mkdir/start failure.
            expected = request_identity(run_id, "real")
            expected.update(design_config=design, save_waveforms=True, seed=authorization.get("seed", 0),
                requested={"PumpPower": design["pump_power_W"], "cw2": 1040-design["filter_offset_nm"], "plot_on": False},
                batch_id=folder.parent.name, total_wall_limit_s=timeout,
                shutdown_and_finalization_reserve_s=30,
                live_authorization={"schema_version": "configured_live_v1", "execute_real": True,
                    "authorization": authorization, "authorization_hash": canonical_hash(authorization),
                    "plan_hash": plan["plan_hash"], "design_id": design_id, "attempt_index": len(records)+1,
                    "remaining_total_s_before": remaining, "selected_design": design})
            protocol = authorization.get("observation_protocol", {"mode": "legacy"})
            if protocol["mode"] != "legacy":
                expected["observation_options"] = validate_observation_options({
                    "observation_mode": protocol["mode"], "observation_roundtrips": protocol["roundtrips"]})
            script = ROOT / "code/ml_bridge/launch_mamyshev_once.m"
            expression = "addpath('" + str(script.parent).replace("'", "''") + "'); launch_mamyshev_once"
            final = execute_once([str(matlab), "-batch", expression], folder, expected,
                                 timeout-(time.monotonic()-started))
            status = "requires_process_audit" if final.get("supervisor", {}).get("cleanup_verified") is False else final["job_status"]
            attempt.update(status=status, final_status=final["job_status"], charged_wall_s=time.monotonic()-started)
            atomic_json(ledger_path, attempt, replace=True)
            return {"final_result": final, "final_path": str(folder / "final_result.json"),
                    "runner_path": str(folder / "runner_record.json"), "run_dir": str(folder)}
        except BaseException:
            # A failed final write or unknown process state remains reserved and
            # conservatively debits the full cap; never erase it for a new ID.
            raise


def _blank(expected):
    def metric(unit):
        return {"value": None, "unit": unit, "definition": "Unavailable final observation",
                "source": "", "missing_reason": "No trustworthy completed candidate."}
    record = {"result_protocol_version": "safe_result_v1", "provenance": {
        "run_id": expected["run_id"], "source_identity": expected["source_identity"],
        "source_kind": "repaired_original_backend" if expected["mode"] == "real" else "synthetic_wrapper_component_fixture",
        "physics_identity_id": "legacy_ring_phase1_v1" if expected["mode"] == "real" else "synthetic_wrapper_fixture",
        "numerical_version": "repair_001_h01_h04" if expected["mode"] == "real" else "synthetic_fixture_not_a_backend_run",
        "wrapper_version": "launchprep_001_observability", "observer_version": "launchprep_001_readonly_observer_v1",
        "requested_seed": expected.get("seed", 0),
        "inputs": {"pump_power_W": expected.get("requested", {}).get("PumpPower", 4),
                   "filter2_center_wavelength_nm": expected.get("requested", {}).get("cw2", 1030)}},
        "job_status": "failed", "stop_reason": "execution_error", "failure_reason": None,
        "physical_state": "undetermined", "numerical_validation": {"status": "not_verified"},
        "eligible_as_validated_training_truth": False, "completed_roundtrips": None,
        "completed_roundtrips_missing_reason": "No trustworthy final count.",
        "legacy_flags": {}, "outputs": {plane: {"plane": plane, "processing": processing,
            "energy": metric("nJ"), "peak_power": metric("W"), "fwhm": metric(unit)}
            for plane, processing, unit in (("sf1_rejected_raw", "uncompressed", "ps"),
                ("pigtail_raw", "uncompressed", "ps"), ("compressed_analysis", "legacy compressor analysis", "fs"))},
        "references": {"transform_limited_fwhm": metric("fs")}}
    record["outputs"]["compressed_analysis"]["field"] = metric("sqrt(W)")
    if "design_config" in expected:
        design = validate_design_config(expected["design_config"])
        record["provenance"]["physics_identity_id"] = "ring_legacy_rules_config_v1"
        record["provenance"]["inputs"] = {"pump_power_W": design["pump_power_W"],
            "filter2_center_wavelength_nm": 1040-design["filter_offset_nm"]}
        record["provenance"]["design_config"] = design
    return record


def validate_candidate(candidate, expected):
    if not isinstance(candidate, dict):
        return "candidate_not_object"
    if candidate.get("result_protocol_version") != "safe_result_v1":
        return "candidate_protocol_invalid"
    if not isinstance(candidate.get("job_status"), str) or candidate["job_status"] not in {"completed", "failed", "timeout", "cancelled"}:
        return "candidate_status_invalid"
    prov = candidate.get("provenance", {})
    if not isinstance(prov, dict):
        return "candidate_provenance_invalid"
    blank = _blank(expected)
    for key, value in blank["provenance"].items():
        if prov.get(key) != value:
            return "candidate_identity_mismatch:" + key
    if candidate.get("physical_state") != "undetermined" or candidate.get("eligible_as_validated_training_truth") is not False:
        return "candidate_safety_contract_invalid"
    numerical = candidate.get("numerical_validation")
    if not isinstance(numerical, dict) or numerical.get("status") != "not_verified":
        return "candidate_safety_contract_invalid"
    if not isinstance(candidate.get("stop_reason"), str) or not candidate["stop_reason"]:
        return "candidate_stop_reason_missing"
    count = candidate.get("completed_roundtrips")
    if count is None:
        if not candidate.get("completed_roundtrips_missing_reason"):
            return "candidate_round_count_missing_reason"
    elif not finite_number(count) or count < 0 or count != int(count):
        return "candidate_round_count_invalid"
    outputs = candidate.get("outputs")
    references = candidate.get("references")
    if not isinstance(outputs, dict) or not isinstance(references, dict):
        return "candidate_outputs_invalid"
    items = []
    for plane in blank["outputs"]:
        metrics = outputs.get(plane)
        if not isinstance(metrics, dict):
            return "candidate_metric_contract_invalid"
        for metric in ("energy", "peak_power", "fwhm"):
            items.append((metrics.get(metric), blank["outputs"][plane][metric]["unit"]))
    items.append((references.get("transform_limited_fwhm"), "fs"))
    field = outputs["compressed_analysis"].get("field")
    if not isinstance(field, dict) or field.get("value") is not None or field.get("unit") != "sqrt(W)" or not field.get("missing_reason"):
        return "candidate_compressed_field_contract_invalid"
    for item, unit in items:
        if not isinstance(item, dict) or "value" not in item or not isinstance(item.get("unit"), str) or not isinstance(item.get("missing_reason"), str):
            return "candidate_metric_contract_invalid"
        if item["unit"] != unit:
            return "candidate_metric_unit_mismatch"
        value = item["value"]
        if value is None and not item["missing_reason"]:
            return "candidate_missing_metric_reason"
        if value is not None and not finite_number(value):
            return "candidate_metric_value_invalid"
    return None


def _null_values(obj, reason):
    if isinstance(obj, dict):
        if "value" in obj:
            obj["value"] = None
            obj["missing_reason"] = reason
        for item in obj.values():
            _null_values(item, reason)
    elif isinstance(obj, list):
        for item in obj:
            _null_values(item, reason)


def merge_result(candidate, runner, expected, candidate_error=None, records_error=None):
    """Pure fail-closed merge; first confirmed parent stop always dominates."""
    validation = candidate_error or validate_candidate(candidate, expected)
    valid = validation is None
    result = deepcopy(candidate) if valid else _blank(expected)
    events = runner.get("stop_events", [])
    first = next((e["reason"] for e in events if e.get("reason") in {"timeout", "cancelled", "runner_interrupted"}), None)
    if first is None and runner.get("stop_reason") in {"timeout", "cancelled", "runner_interrupted"}:
        first = runner["stop_reason"]
    status, reason = "failed", "execution_error"
    failure = {"identifier": "Supervisor:ExecutionError", "message": "Process did not finish normally."}
    if first:
        status = first if first in {"timeout", "cancelled"} else "failed"
        reason = first
        failure = {"identifier": "Supervisor:" + first, "message": "First confirmed parent stop; candidate cannot override it."}
    elif runner.get("cleanup_error") or runner.get("cleanup_verified") is False:
        reason = "cleanup_error"
        failure = {"identifier": "Supervisor:CleanupError", "message": str(runner.get("cleanup_error", "Owned process cleanup was not verified."))}
    elif runner.get("exit_code") != 0 or runner.get("status") != "completed":
        if valid and candidate["job_status"] != "completed":
            reason = candidate.get("stop_reason") or reason
            failure = candidate.get("failure_reason") or failure
    elif validation:
        reason = "invalid_candidate"
        failure = {"identifier": "Supervisor:InvalidCandidate", "message": validation}
    elif candidate["job_status"] != "completed":
        status = candidate["job_status"]
        reason = candidate.get("stop_reason") or "candidate_failed"
        failure = candidate.get("failure_reason") or failure
    elif records_error:
        reason = "incomplete_required_records"
        failure = {"identifier": "Supervisor:IncompleteRecords", "message": records_error}
    else:
        status, reason, failure = "completed", candidate["stop_reason"], None
    result.update(job_status=status, stop_reason=reason, failure_reason=failure,
                  physical_state="undetermined", numerical_validation={"status": "not_verified",
                    "reason": "No independent numerical convergence validation."},
                  eligible_as_validated_training_truth=False)
    if status != "completed":
        for key in ("outputs", "references"):
            _null_values(result[key], "No final metric: " + reason)
        field = result["outputs"]["compressed_analysis"]["field"]
        field.pop("artifact", None)
        field.pop("variable", None)
        field["available"] = False
        if "waveform_artifacts" in result:
            result["waveform_artifacts"]["validated_for_final"] = False
        if isinstance(result.get("observation"), dict):
            result["observation"]["validated_for_final"] = False
    result["supervisor"] = {"version": FINALIZER_VERSION, "runner_record": "runner_record.json",
        "candidate_artifact": "matlab_candidate.json", "candidate_valid": valid,
        "candidate_error": validation, "required_records_error": records_error,
        "exit_code": runner.get("exit_code"), "stop_events": events,
        "cleanup_verified": runner.get("cleanup_verified"), "cleanup_error": runner.get("cleanup_error"),
        "exit_candidate_inconsistent": bool(valid and ((runner.get("exit_code") == 0) != (candidate["job_status"] == "completed"))),
        "elapsed_s": runner.get("elapsed_s"), "final_writer": "parent_supervisor"}
    result["progress_provenance"] = {"source": "identity-validated candidate" if valid else None,
        "complete": bool(valid and status == "completed"),
        "reason": "Interrupted or missing records are not complete progress." if status != "completed" else "Normally returned candidate."}
    return result


def load_json(path):
    def invalid(value):
        raise ValueError("Nonstandard JSON constant: " + value)
    def finite_float(value):
        result = float(value)
        if not math.isfinite(result):
            raise ValueError("Nonfinite JSON number")
        return result
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate JSON key: " + key)
            result[key] = value
        return result
    return json.loads(Path(path).read_text(), parse_constant=invalid,
                      parse_float=finite_float, object_pairs_hook=unique_object)


def required_records_error(candidate, expected, run_dir):
    """Real record checks are expanded with the actual MATLAB artifact schema."""
    observation = candidate.get("observability", {})
    if not isinstance(observation, dict) or observation.get("required_records_complete") is not True:
        return "Candidate does not certify complete required observations."
    if expected["mode"] == "synthetic":
        if observation.get("kind") != "synthetic_component":
            return "Synthetic observation identity missing."
        return None
    # No real run can complete before the resolved artifact gate is implemented.
    return verify_real_observability(candidate, expected, run_dir)


def design_reference_configuration(baseline, design):
    """Only declared four-input consequences differ from the legacy reference."""
    design = validate_design_config(design)
    reference = deepcopy(baseline)
    reference["PumpPower_W"] = design["pump_power_W"]
    reference["cw2_nm"] = 1040-design["filter_offset_nm"]
    reference["spectral_filter2"] = {"cw": reference["cw2_nm"], "bw": design["filter2_bw_nm"]}
    reference["fiber_cavity"][0]["L0"] = design["gain_length_m"]
    reference["gain_rate_eqn"]["copump_power"] = design["pump_power_W"]
    # Keep the default reference's exact parsed value; nondefault length uses
    # the same summation order and beta1 group-velocity formula as MATLAB.
    if design["gain_length_m"] != DEFAULT_DESIGN_CONFIG["gain_length_m"]:
        total_length = sum(fiber["L0"] for fiber in reference["fiber_cavity"])
        velocity = 1/reference["fiber_cavity"][0]["betas"][1]*1e12
        reference["gain_rate_eqn"]["t_rep"] = total_length/velocity
    return reference


def verify_design_records(records, expected, baseline, config, rt):
    design = validate_design_config(expected["design_config"])
    requested = {"PumpPower": design["pump_power_W"],
                 "cw2": 1040-design["filter_offset_nm"], "plot_on": False}
    context = records["requested"].get("context", {})
    if "live_authorization" in expected and context.get("live_authorization") != expected["live_authorization"]:
        return "Configured live authorization not preserved in actual A"
    if "live_authorization" in expected:
        actual_rng = records["requested"].get("rng_at_request", {})
        if context.get("seed") != expected["seed"] or actual_rng.get("Type") != "twister" or actual_rng.get("Seed") != expected["seed"]:
            return "Configured live seed/twister request not observed in actual A"
    if expected.get("requested") != requested or context.get("requested") != requested or context.get("design_config") != design:
        return "Four dimensional request conflicts with actual A inputs"
    if context.get("save_waveforms") is not expected.get("save_waveforms"):
        return "Waveform request is not preserved in A"
    observed = records["configuration"]
    if observed.get("design_config") != design:
        return "Four dimensional request differs from actual B design"
    expected_rules = {"model_rules_id": "ring_legacy_rules_config_v1",
        "historical_reference_id": "legacy_ring_phase1_v1",
        "matches_historical_reference": design == DEFAULT_DESIGN_CONFIG,
        "H02_status": "unresolved", "passive_declared_MFD_um": 10.5,
        "passive_SR_derived_MFD_um": 5.95,
        "passive_actual_SR_m_minus2": baseline["fiber_cavity"][1]["SR"],
        "passive_actual_area_m2": 1.0/baseline["fiber_cavity"][1]["SR"],
        "passive_lengths_m": [.4, 1.5, 3.2], "pigtail_length_m": .2,
        "N_total_override": 9e7, "output_port": "1-H", "filter_order": 4}
    rules = observed.get("model_rules")
    if not isinstance(rules, dict) or any(rules.get(key) != value for key, value in expected_rules.items()):
        return "Inherited model rules/H02 identity missing or changed"
    filters = records["runtime_calls"].get("filter_calls")
    if not isinstance(filters, list) or len(filters) != 2*rt:
        return "Actual filter call observations incomplete"
    # Production reaches SF1 after cavity_2, then SF2 after cavity_3.
    sequence = [(k, name) for k in range(1, rt+1) for name in ("sf1", "sf2")]
    for call, (roundtrip, name) in zip(filters, sequence):
        reference = config["spectral_filter"+name[-1]]
        if not isinstance(call, dict) or call.get("roundtrip") != roundtrip or call.get("filter_id") != name or \
                call.get("cw_nm") != reference["cw"] or call.get("bw_nm") != reference["bw"] or \
                call.get("order") != 4 or call.get("plot_on") is not False:
            return "Actual filter invocation differs from resolved design or inherited order"
    return None


def _mat_header_valid(content):
    return len(content) > 128 and content.startswith(b"MATLAB 5.0 MAT-file") and content[126:128] in (b"IM", b"MI")


def _verify_integrity_item(item, folder):
    """Only simple artifact basenames under the owned run directory are accepted."""
    path = item.get("path") if isinstance(item, dict) else None
    if not isinstance(path, str) or not path or Path(path).name != path or path in {".", ".."}:
        raise ValueError("Unsafe artifact path")
    full = Path(folder) / path
    if full.is_symlink() or not full.is_file():
        raise ValueError("Artifact is missing or a symlink: " + path)
    content = full.read_bytes()
    if len(content) != item.get("bytes") or hashlib.sha256(content).hexdigest() != item.get("sha256"):
        raise ValueError("Artifact integrity mismatch: " + path)
    if path.endswith(".mat") and not _mat_header_valid(content):
        raise ValueError("MAT header invalid: " + path)
    return path


def verify_waveform_records(candidate, expected, run_dir, config):
    """Validate bounded saved evidence without interpreting complex MAT arrays."""
    manifest = load_json(Path(run_dir) / "waveform_manifest.json")
    rt = candidate["completed_roundtrips"]
    if manifest.get("schema_version") != "mamyshev_waveforms_v1" or manifest.get("run_id") != expected["run_id"] or \
            manifest.get("source_identity") != expected["source_identity"] or manifest.get("design_config") != expected["design_config"]:
        raise ValueError("Waveform identity/schema mismatch")
    if manifest.get("initialized") is not True or manifest.get("finalized") is not True or manifest.get("completed_roundtrips") != rt:
        raise ValueError("Waveform capture is incomplete")
    if manifest.get("units") != {"field": "sqrt(W)", "t": "ps", "f": "THz", "f0": "THz", "energy": "nJ", "power": "W"}:
        raise ValueError("Waveform units are missing or changed")
    if manifest.get("conventions", {}).get("time_to_frequency") != "fftshift(ifft(A,[],1),1)":
        raise ValueError("Waveform FFT convention is missing or changed")
    planes = manifest.get("planes", {})
    if not isinstance(planes, dict) or not all(isinstance(planes.get(key), str) and planes[key] for key in
            ("pre_tracker_field", "post_tracker_field", "output_field", "pigtail_output_field", "compressed_field")):
        raise ValueError("Waveform processing-plane metadata is missing")
    grid = manifest.get("grid", {})
    if grid.get("sample_count") != config["Nt"] or grid.get("dt_ps") != config["dt_ps"] or \
            grid.get("f0_THz") != config["sim_cavity"][0]["f0"] or \
            grid.get("time_size") != [1, config["Nt"]] or grid.get("frequency_size") != [config["Nt"], 1]:
        raise ValueError("Waveform grid does not match production B")
    rounds, energies = manifest.get("rounds"), manifest.get("raw_energy_history_nJ")
    if isinstance(rounds, dict):
        rounds = [rounds]  # MATLAB serializes a one-element struct array as an object.
    if not isinstance(energies, list):
        energies = [energies]
    if not isinstance(rounds, list) or len(rounds) != rt or len(energies) != rt or not all(finite_number(e) for e in energies):
        raise ValueError("Waveform round/energy history is incomplete")
    artifacts = []
    for number, entry in enumerate(rounds, 1):
        if entry.get("roundtrip") != number or entry.get("path") != f"waveforms_round_{number:04d}.mat" or \
                entry.get("raw_energy_nJ") != energies[number-1] or entry.get("finite") is not True or \
                entry.get("field_size") != [config["Nt"], 1]:
            raise ValueError("Invalid completed-round waveform metadata")
        _verify_integrity_item(entry, run_dir)
        artifacts.append({key: entry[key] for key in ("path", "bytes", "sha256")})
    final = manifest.get("final", {})
    if final.get("path") != "waveforms_final.mat" or final.get("finite") is not True or final.get("field_size") != [config["Nt"], 1]:
        raise ValueError("Invalid final waveform metadata")
    _verify_integrity_item(final, run_dir)
    artifacts.append({key: final[key] for key in ("path", "bytes", "sha256")})
    field = candidate["outputs"]["compressed_analysis"]["field"]
    if final.get("compressed_field_available") is True:
        if field.get("available") is not True or field.get("artifact") != "waveforms_final.mat" or field.get("variable") != "compressed_field" or \
                not finite_number(candidate["outputs"]["compressed_analysis"]["energy"]["value"]):
            raise ValueError("Saved compressed field and candidate reference disagree")
    elif final.get("compressed_field_available") is not False or not final.get("compressed_field_missing_reason"):
        raise ValueError("Missing compressed field needs an explicit reason")
    summary = candidate.get("waveform_artifacts", {})
    if summary.get("manifest_path") != "waveform_manifest.json" or summary.get("finalized") is not True or summary.get("completed_roundtrips") != rt:
        raise ValueError("Candidate waveform references incomplete")
    # The artifact manifest supplies one immutable entry for every MAT and the
    # JSON manifest. Its own hash is in candidate.observability, not self-hashed.
    paths = {"waveform_manifest.json", *(item["path"] for item in artifacts)}
    if not isinstance(summary.get("artifacts"), list) or len(summary["artifacts"]) != len(paths) or set(summary["artifacts"]) != paths:
        raise ValueError("Candidate waveform artifact list incomplete")
    return paths


def verify_observation_records(candidate, expected, records, manifest):
    """Require real per-round evidence; convergence alone cannot finish a fixed observation."""
    if "observation_options" not in expected:
        return None  # Historical default stopping keeps its existing contract.
    try:
        options = validate_observation_options(expected["observation_options"])
        budget = options["observation_roundtrips"]
        rt = candidate.get("completed_roundtrips")
        if not finite_number(rt) or rt != int(rt) or not 1 <= rt <= budget:
            return "Observation completed-round count invalid"
        a = records["requested"].get("context", {})
        b, c = records["configuration"], records["runtime_calls"]
        observed = candidate.get("observation")
        if not isinstance(observed, dict) or any(item.get("observation_options") != options for item in (a, b, c)) or observed.get("options") != options:
            return "Observation request/options differ across A/B/C/candidate"
        history = c.get("observation_history")
        candidate_history = observed.get("history")
        if isinstance(history, dict):
            history = [history]
        if isinstance(candidate_history, dict):
            candidate_history = [candidate_history]
        if not isinstance(history, list) or len(history) != rt or history != candidate_history:
            return "Observation history incomplete or differs from actual C"
        energies = manifest.get("raw_energy_history_nJ")
        if not isinstance(energies, list):
            energies = [energies]
        if manifest.get("completed_roundtrips") != rt or len(energies) != rt or not all(finite_number(e) and e >= 0 for e in energies):
            return "Observation history lacks finite matching completed-round waveform energies"
        threshold = b.get("pulse_death_energy_nJ")
        if threshold != .01:
            return "Inherited pulse-death threshold missing or changed"
        reasons = {"empty_history", "empty_field", "zero_field", "zero_energy_denominator", "energy_not_converged",
                   "insufficient_history", "zero_average_energy_denominator", "energy_converged",
                   "energy_average_converged", "energy_fluctuation_stop"}
        first = None
        terminal = None
        for number, entry in enumerate(history, 1):
            if not isinstance(entry, dict) or not finite_number(entry.get("roundtrip")) or entry.get("roundtrip") != number:
                return "Observation round sequence is invalid"
            flags = [entry.get(key) for key in ("converged", "force_stop_convergence", "force_stop_fluctuation")]
            if not all(isinstance(value, bool) for value in flags) or sum(flags) > 1:
                return "Observation criterion flags missing, nonboolean, or mutually inconsistent"
            converged, averaged, fluctuation = flags
            reason = entry.get("criterion_reason")
            if reason not in reasons:
                return "Observation energy-criterion reason missing or invalid"
            if converged != (reason == "energy_converged") or averaged != (reason == "energy_average_converged") or fluctuation != (reason == "energy_fluctuation_stop"):
                return "Observation criterion flags do not match actual diagnostic reason"
            if first is None and (converged or averaged):
                first = number
            # Fixed mode preserves safety exits even if convergence or the
            # observation budget is reached on the same completed round.
            terminal = "legacy_energy_below_threshold" if energies[number-1] < threshold else \
                "legacy_energy_fluctuation_stop" if fluctuation else \
                "observation_budget_reached" if number == budget else ""
            if entry.get("stop_reason") != terminal:
                return "Observation stop reason does not follow death/fluctuation/budget priority"
            if terminal and number < rt:
                return "Observation continued after a required safety/budget stop"
        if not terminal or candidate.get("stop_reason") != terminal or observed.get("stop_reason") != terminal:
            return "Observation candidate returned prematurely or disagrees with final actual stop"
        if "observation_first_legacy_convergence_roundtrip" not in c or "first_legacy_convergence_roundtrip" not in observed:
            return "Observation first legacy convergence round is missing (explicit null required when absent)"
        reported_first = [c["observation_first_legacy_convergence_roundtrip"], observed["first_legacy_convergence_roundtrip"]]
        if any(value is not None and not finite_number(value) for value in reported_first) or any(value != first for value in reported_first):
            return "Observation first legacy convergence round does not match actual history"
        legacy = candidate.get("legacy_flags", {})
        if legacy.get("converged") is not history[-1]["converged"] or legacy.get("force_stop") is not history[-1]["force_stop_convergence"]:
            return "Legacy final convergence flags were changed by observation mode"
        if legacy.get("pulse_survives") is not (terminal != "legacy_energy_below_threshold"):
            return "Observation stop and pulse-survival flag disagree"
    except (TypeError, ValueError, KeyError, AttributeError) as exc:
        return "Invalid observation record: " + str(exc)
    return None


def verify_real_observability(candidate, expected, run_dir):
    """Inspect saved records, not only the candidate's completeness assertion."""
    try:
        required_artifacts = {"requested.json", "configuration.mat", "configuration.json",
            "configuration_comparison.json", "runtime_calls.json", "runtime_observer.json"}
        if expected.get("save_waveforms") is True:
            # Read B once to determine exact expected dimensions; all records
            # are identity and integrity checked below before success is possible.
            initial = load_json(Path(run_dir) / "configuration.json")
            required_artifacts |= verify_waveform_records(candidate, expected, run_dir, initial["configuration"])
        integrity = candidate.get("observability", {}).get("artifact_integrity")
        if not isinstance(integrity, list) or len(integrity) != len(required_artifacts) or {item.get("path") for item in integrity} != required_artifacts:
            return "Required artifact integrity manifest missing"
        for item in integrity:
            _verify_integrity_item(item, run_dir)
        records = {name: load_json(Path(run_dir) / (name + ".json")) for name in (
            "requested", "configuration", "configuration_comparison", "runtime_calls", "runtime_observer")}
        for name, record in records.items():
            if not isinstance(record, dict):
                return name + " is not an object"
            identity = record.get("identity", record.get("context", record))
            if identity.get("run_id") != expected["run_id"] or identity.get("source_identity") != expected["source_identity"]:
                return name + " identity mismatch"
        mat = (Path(run_dir) / "configuration.mat").read_bytes()
        if not _mat_header_valid(mat):
            return "Actual initialization MAT artifact invalid"
        if records["configuration"].get("status") != "observed" or records["configuration"].get("propagation_started") is not False:
            return "Pre-propagation initialization not captured"
        configuration = records["configuration"]
        config = configuration.get("configuration")
        baseline = load_json(ROOT / "reports/local/phase1/baseline_001/configuration.json")
        def without_path_metadata(value):
            if isinstance(value, dict):
                return {key: without_path_metadata(item) for key, item in value.items()
                        if key not in {"cuda_dir_path", "readonly_observer"}}
            if isinstance(value, list):
                return [without_path_metadata(item) for item in value]
            return value
        reference = design_reference_configuration(baseline, expected["design_config"]) if "design_config" in expected else baseline
        if not isinstance(config, dict) or without_path_metadata(config) != without_path_metadata(reference):
            return "Actual B configuration fields missing or differ from direct baseline_001 JSON"
        for key, shape in (("initial_field", [config["Nt"], 1]), ("time_grid", [1, config["Nt"]]),
                           ("frequency_grid", [config["Nt"], 1]), ("wavelength_grid", [config["Nt"], 1])):
            summary = configuration.get(key, {})
            if summary.get("size") != shape or summary.get("finite") is not True or summary.get("class") != "double":
                return "Missing/invalid actual array summary: " + key
        if not finite_number(configuration.get("gain_info_computed_N_total")) or configuration.get("final_N_total") != config["N_total_ions_per_um3"]:
            return "Gain density observations missing"
        comparison = records["configuration_comparison"]
        if comparison.get("passed") is not True or comparison.get("unexpected_differences") != [] or not comparison.get("checked_leaves", 0):
            return "Baseline parameter content comparison incomplete or failed"
        calls, observer = records["runtime_calls"], records["runtime_observer"]
        if calls.get("backend_returned") is not True or calls.get("compressor_status") != "observed":
            return "Runtime call/compressor capture incomplete"
        compressor = calls.get("compressor_call", {})
        if compressor.get("status") != "observed" or any(compressor.get(key) != config[reference] for key, reference in (
            ("type", "compressor_type"), ("incident_angle_rad", "grating_incident_angle_rad"),
            ("grating_spacing_m", "grating_spacing_m"), ("plot_on", "plot_on"))):
            return "Actual compressor invocation missing or changed"
        if observer.get("counts_complete") is not True or observer.get("runtime_resolved_complete") is not True or observer.get("active_segment") not in (None, []):
            return "Active/incomplete production segment"
        rt = candidate.get("completed_roundtrips")
        if not finite_number(rt) or int(rt) != rt or not 1 <= rt <= 50:
            return "Missing/invalid completed cavity round count"
        if "design_config" in expected:
            design_error = verify_design_records(records, expected, baseline, config, int(rt))
            if design_error:
                return design_error
        if "observation_options" in expected:
            observation_error = verify_observation_records(candidate, expected, records,
                load_json(Path(run_dir) / "waveform_manifest.json"))
            if observation_error:
                return observation_error
        sequence = [(k, f"cavity_{j}") for k in range(1, int(rt)+1) for j in range(1, 5)] + [(int(rt), "pigtail")]
        segments, actual_calls = observer.get("segments"), calls.get("segment_calls")
        if not isinstance(segments, list) or not isinstance(actual_calls, list) or len(segments) != len(sequence) or len(actual_calls) != len(sequence):
            return "Runtime segment count does not match round count plus pigtail"
        for (round_trip, name), segment, call in zip(sequence, segments, actual_calls):
            if segment.get("round_trip") != round_trip or call.get("roundtrip") != round_trip or segment.get("segment_id") != name or call.get("segment_id") != name:
                return "Runtime segment/round identity mismatch"
            if call.get("status") != "observed" or segment.get("normal_completion") is not True or segment.get("counts_complete") is not True:
                return "Segment did not return normally"
            if not isinstance(call.get("fiber"), dict) or not isinstance(call.get("sim"), dict) or call.get("dt_ps") != config["dt_ps"] or call.get("input_field_size") != [config["Nt"], 1]:
                return "Actual propagation invocation missing"
            for key in ("L0", "MFD", "SR", "gain_Aeff"):
                if not finite_number(call["fiber"].get(key)):
                    return "Actual fiber argument missing: " + key
            if not isinstance(call["sim"].get("adaptive_deltaZ"), dict) or "Raman_sponRS" not in call["sim"]:
                return "Actual numerical/random invocation parameters missing"
            index = 1 if name == "pigtail" else int(name[-1])-1
            expected_fiber = deepcopy(config["fiber_cavity"][index])
            if name == "pigtail":
                expected_fiber["L0"] = config["output_fiber_length_m"]
            if without_path_metadata(call["fiber"]) != without_path_metadata(expected_fiber) or without_path_metadata(call["sim"]) != without_path_metadata(config["sim_cavity"][index]):
                return "Runtime fiber/numerical invocation changed from observed B"
            if name != "pigtail":
                if call.get("gain_arrays_match_reference") is not True or not finite_number(call.get("gain_rate_eqn", {}).get("t_rep")):
                    return "Actual gain invocation/reference validation missing"
                actual_gain = deepcopy(call["gain_rate_eqn"])
                initial_gain = deepcopy(config["gain_rate_eqn"])
                # The only evolving gain argument is the original algorithm's
                # t_rep. Pump power and all other resolved gain fields remain checked.
                actual_gain.pop("t_rep", None); initial_gain.pop("t_rep", None)
                if actual_gain != initial_gain:
                    return "Actual gain invocation differs from observed B"
            counts = [segment.get(k) for k in ("trials", "rejections", "accepted_advanced_steps", "pending_trials")]
            if not all(finite_number(n) and n >= 0 and n == int(n) for n in counts):
                return "Incomplete/invalid counts"
            trials, rejected, advanced, pending = counts
            if pending != 0 or advanced <= 0 or trials != rejected + advanced:
                return "Trial/reject/actual advance relationship failed"
            resolved = segment.get("runtime_resolutions")
            if not isinstance(resolved, list) or not resolved:
                return "Effective step defaults not observed"
            for resolution in resolved:
                if resolution.get("status") != "observed" or not all(finite_number(resolution.get(k)) and resolution[k] > 0 for k in ("max_deltaZ", "initial_deltaZ", "threshold")):
                    return "Invalid runtime-resolved step values"
    except (OSError, ValueError, TypeError, AttributeError, KeyError) as exc:
        return "Missing/corrupt required record: " + str(exc)
    return None


def execute_once(command, run_dir, expected, timeout_s, env=None):
    """run_dir must already be reserved exclusively by its single parent owner."""
    run_dir = Path(run_dir)
    supervisor_started = time.monotonic()
    if (run_dir / "final_result.json").exists() or (run_dir / "runner_record.json").exists():
        raise FileExistsError("Refusing to launch into existing process/final evidence")
    atomic_json(run_dir / "launch_request.json", expected)
    environment = dict(os.environ if env is None else env)
    environment.update(PHASE2_ROOT=str(ROOT), PHASE2_OUTPUT_DIR=str(run_dir))
    runner = None
    try:
        try:
            runner = monitor.run_isolated(command, run_dir, environment,
                timeout_s-(time.monotonic()-supervisor_started), metadata={
                "run_id": expected["run_id"], "kind": "single_real_run" if expected["mode"] == "real" else "synthetic_component",
                "full_cavity_runs": 1 if expected["mode"] == "real" else 0,
                "source_identity": expected["source_identity"], "attempt": 1, "max_attempts": 1},
                shutdown_reserve_s=30 if expected["mode"] == "real" else 7)
        except BaseException as monitor_error:
            # Only this just-reserved attempt may be recovered. No historical
            # record repair: the monitor must have persisted a terminal failure.
            saved = load_json(run_dir / "runner_record.json")
            if saved.get("status") != "failed" or not saved.get("cleanup_error") or saved.get("cleanup_verified") is not False:
                raise
            if saved.get("run_id") != expected["run_id"] or saved.get("source_identity") != expected["source_identity"]:
                raise
            runner = saved
            atomic_json(run_dir / "supervisor_error.json", {"status": "failed", "error": repr(monitor_error),
                "runner_record": "runner_record.json", "final_status": "inspect_final_result_json_if_present; never_success"})
        error, candidate = None, None
        try:
            candidate = load_json(run_dir / "matlab_candidate.json")
        except (OSError, ValueError) as exc:
            error = "missing_or_corrupt_candidate: " + str(exc)
        records_error = None
        if runner.get("status") == "completed" and error is None and validate_candidate(candidate, expected) is None:
            records_error = required_records_error(candidate, expected, run_dir)
        if expected["source_identity"] != source_identity():
            records_error = "Source changed during this attempt."
        # The real mode keeps 30 seconds for shutdown + source check + final
        # commit. A parent-observed total deadline also dominates a late result.
        total_elapsed = time.monotonic()-supervisor_started
        if total_elapsed >= timeout_s:
            runner["stop_events"].append({"reason": "timeout", "elapsed_s": total_elapsed,
                                           "source": "supervisor_finalization_deadline"})
            runner.update(status="failed", stop_reason=runner["stop_events"][0]["reason"])
        runner["supervisor_precommit_elapsed_s"] = total_elapsed
        atomic_json(run_dir / "runner_record.json", runner, replace=True)
        final = merge_result(candidate, runner, expected, error, records_error)
        final["supervisor"].update(total_wall_limit_s=timeout_s, precommit_elapsed_s=total_elapsed,
            shutdown_and_finalization_reserve_s=30 if expected["mode"] == "real" else 7)
        atomic_json(run_dir / "final_result.json", final)
        return final
    except BaseException as exc:
        # run_isolated owns cleanup even when writes fail. Never invent success
        # on this path; this secondary file is diagnostic, not a final result.
        try:
            atomic_json(run_dir / "supervisor_error.json", {"status": "failed", "error": repr(exc),
                "runner": runner, "final_status": "absent_or_requires_inspection"})
        except (OSError, ValueError):
            pass
        raise
