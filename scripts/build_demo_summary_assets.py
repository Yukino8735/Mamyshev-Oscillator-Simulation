#!/usr/bin/env python3
"""Copy only small historical summaries and existing figures; no evaluation."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--matlab-summary", type=Path, required=True)
    args = parser.parse_args()
    assets = ROOT / "demo/assets"
    assets.mkdir(parents=True, exist_ok=True)
    source = ROOT / "reports/local/application_v4_3_001/candidates/requests/matlab_requests.json"
    original = json.loads(source.read_text())
    rows = []
    for row in original["requests"]:
        rows.append({"scenario": row["scenario_id"], "rank": row["rank"],
            "design_id": row["design_id"], **row["design"], **row["synthetic_targets"],
            "confirmation_source": row["synthetic_identity"]["source"]})
    if not 1 <= len(rows) <= 12:
        raise ValueError("Public historical summary maximum is 12 rows")
    plan_path = ROOT / "reports/local/application_v4_3_001/candidates/frozen_candidate_plan.json"
    plan = json.loads(plan_path.read_text())
    recorded_at = plan.get("created_at", plan.get("frozen_at"))
    if recorded_at is None:
        # Use the persisted start log's timestamp, never a filesystem mtime.
        ledger = json.loads((ROOT / "reports/local/application_v4_3_001/budget_ledger.json").read_text())
        records = ledger["attempts"]
        times = [r.get("start_utc") for r in records if r.get("label") == "candidate_confirmation"]
        recorded_at = next((x for x in times if x), None)
        if recorded_at is None:
            raise ValueError("Historical candidate confirmation start timestamp missing")
    write(assets / "historical_candidates.json", {"model_id": "v42_T2_K64_A0001",
        "n_train": 1024, "source": "repository_guided_synthetic",
        "recorded_at": recorded_at, "timestamp_definition": "Historical candidate-confirmation process start; not an individual design completion timestamp",
        "source_sha256": sha(source),
        "historical_request_sha256": sha(plan_path), "rows": rows,
        "new_model_achievement": False, "physical_confirmation": False})
    scenarios = ROOT / "mamyshev_accuracy_v4/configs/scenarios.json"
    with (assets / "scenarios.json").open("xb") as stream:
        stream.write(scenarios.read_bytes())
    checked = json.loads(args.matlab_summary.read_text())
    summary = {"n_unique_designs": checked["unique_designs"],
        "plan_hash": checked["plan_hash"], "plan_validation_sha256": sha(args.matlab_summary),
        "all_real_targets_null": checked["all_real_targets_null"],
        "max_new_real_attempts": 0, "new_real_attempts": checked["new_real_attempts"],
        "live_zero_denial_before_reservation": checked["live_zero_denial_before_reservation"],
        "full_10k_GMMNLSE": "not_run", "status": "pending_manual_approval",
        "plan_storage": "local_only_not_in_public_preview",
        "functional_scope": ["parameterized plan with exact IDs", "serial per-design persistence",
            "resume skips completed records", "parent-owned final / explicit failures",
            "DB / CSV / MAT exports", "no UI live execution route"],
        "limits": "Historical full single-point evidence and current plan/component checks do not validate a full 10k live scan."}
    if summary["n_unique_designs"] != 10000 or summary["new_real_attempts"] != 0:
        raise ValueError("Expected checked 10000-design pending-only plan")
    write(assets / "matlab_plan_summary.json", summary)
    image = ROOT / "reports/local/accuracy_v4_001/data_chain/demo_001/historical_mat_read/saved_waveforms.png"
    image_to = assets / "historical_waveforms.png"
    if image.is_file():
        with image_to.open("xb") as stream:
            stream.write(image.read_bytes())
        waveform = {"png": image_to.name, "source_sha256": sha(image),
            "caption": "Historical GMMNLSE saved-waveform replay. Fixed prior run; no new propagation and no slider dependence.",
            "source_run": "config_waveform_001", "current_run": False}
    else:
        waveform = {"png": None, "reason": "Historical saved-waveform PNG absent; no recomputation requested."}
    write(assets / "historical_waveform.json", waveform)
    print(json.dumps({"status": "copied_saved_summaries", "historical_rows": len(rows),
        "oracle_calls": 0, "MATLAB_starts": 0, "new_labels": 0}))


if __name__ == "__main__":
    main()
