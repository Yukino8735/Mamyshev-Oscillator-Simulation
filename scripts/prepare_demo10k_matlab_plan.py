#!/usr/bin/env python3
"""Create one local N-row pending GMMNLSE plan from already frozen training X."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from mamyshev_ml.demo10k_plan import chunk_rows, pending_plan, read_input_rows, select_rows, zero_authorization
from mamyshev_ml.v4_evaluators import FEATURES, TARGETS, design_id, digest
from mamyshev_ml.v4_scan import write_plan
from mamyshev_ml.supervisor import execute_authorized_design, validate_live_authorization


def write(path, value):
    with Path(path).open("x") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", required=True, type=Path)
    parser.add_argument("--labels", required=True, type=Path, help="Only <=32 already labeled rows are projected for parity, never into the plan")
    parser.add_argument("--count", type=int, default=10000)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError("No overwrite of an existing pending plan/evidence")
    rows = read_input_rows(args.inputs, expected_count=args.count)
    plan = pending_plan(rows)
    args.out.mkdir(parents=True, exist_ok=False)
    write_plan(plan, args.out / "gmmnlse_pending_plan.json")
    auth = zero_authorization(plan)
    write(args.out / "pending_zero_authorization.json", auth)
    indices = sorted(set((0, args.count // 2, args.count - 1)))
    selected = [plan["designs"][index] for index in indices]
    for index, row in zip(indices, selected):
        assert row["design_config"] == rows[index]["design_config"]
        assert validate_live_authorization(plan, auth, row["design_id"]) == row["design_config"]
    # Existing production authorization refuses before executable/path/reservation checks.
    absent = args.out / "must_not_reserve"
    try:
        execute_authorized_design(matlab="/not_invoked", plan=plan, authorization=auth,
            design_id=selected[0]["design_id"], batch_dir=absent, run_id="never", execute_real=True)
    except PermissionError:
        pass
    else:
        raise AssertionError("Zero permission unexpectedly reached a live attempt")
    assert not absent.exists()
    chunks = list(chunk_rows(plan, chunk_size=256))
    combined = [identifier for chunk in chunks for identifier in chunk["design_ids"]]
    assert combined == [row["design_id"] for row in rows]
    filtered = select_rows(plan, design_ids=[row["design_id"] for row in selected])
    assert filtered["design_ids"] == [row["design_id"] for row in selected]
    # Labels are consumed only as existing parity references, never new evaluations.
    with args.labels.open(newline="") as stream:
        reader = csv.DictReader(stream)
        parity = []
        for row in reader:
            if len(parity) == min(32, args.count):
                break
            d = {key: float(row[key]) for key in FEATURES}
            expected = rows[len(parity)]
            if design_id(d) != expected["design_id"] or row["design_id"] != expected["design_id"]:
                raise ValueError("Saved parity labels and frozen training inputs are not identically ordered")
            parity.append({"design_id": row["design_id"], **d, **{key: float(row[key]) for key in TARGETS}})
    if len(parity) != min(32, args.count):
        raise ValueError("Required existing labeled parity rows are missing")
    with (args.out / "existing_train_parity_32.csv").open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["design_id", *FEATURES, *TARGETS])
        writer.writeheader(); writer.writerows(parity)
    report = {"kind": "pending_original_GMMNLSE_plan_validation", "N": args.count,
        "input_sha256": hashlib.sha256(args.inputs.read_bytes()).hexdigest(), "plan_hash": plan["plan_hash"],
        "plan_file_sha256": hashlib.sha256((args.out / "gmmnlse_pending_plan.json").read_bytes()).hexdigest(),
        "unique_designs": len(combined), "selected_zero_based_indices": indices, "selected_rows": selected,
        "chunks": chunks, "filtered": filtered, "order_hash": digest(combined),
        "all_real_targets_null": True, "live_zero_denial_before_reservation": True,
        "new_research_labels": 0, "new_real_attempts": 0,
        "parity_existing_labels": len(parity), "parity_tolerance": {"atol": 1e-10, "rtol": 2e-10},
        "matlab_status": "not_run", "scope": "Plan/validation only; full 10k GMMNLSE not_run"}
    write(args.out / "plan_validation.json", report)
    print(json.dumps({key: report[key] for key in ("N", "unique_designs", "plan_hash", "new_real_attempts")}))


if __name__ == "__main__":
    main()
