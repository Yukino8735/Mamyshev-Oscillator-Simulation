#!/usr/bin/env python3
"""Exec one inspected short MATLAB script inside the existing budget monitor.

This is not another monitor or live launcher. execve keeps the owned process
group; run_demo10k_budget.py accounts its entire wall time as MATLAB cost.
"""
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/local/demo_10k_release_001"


def main():
    batch = OUT / "matlab_short"
    if not OUT.is_dir() or not (OUT / "matlab_plan/plan_validation.json").is_file():
        raise RuntimeError("Exclusive batch and checked pending plan are required")
    # The outer budget monitor owns the serial lock and 180 s cumulative cap.
    ledger = json.loads((OUT / "budget_ledger.json").read_text())
    running = [entry for entry in ledger["attempts"] if entry["status"] == "running"]
    if len(running) != 1 or running[0]["category"] != "matlab" or running[0]["reserved_cap_s"] > 180:
        raise RuntimeError("Invoke only inside this batch's existing MATLAB budget category")
    batch.mkdir(exist_ok=True)
    reservations = sorted(batch.glob("process_*/reservation.json"))
    if len(reservations) >= 2:
        raise PermissionError("At most two MATLAB short process reservations; no silent retries")
    folder = batch / f"process_{len(reservations) + 1:03d}"
    folder.mkdir(exist_ok=False)
    script = ROOT / "tests/matlab/run_demo10k_plan_components.m"
    matlab = Path("/Applications/MATLAB_R2025a.app/bin/matlab")
    command = [str(matlab), "-singleCompThread", "-batch", "run('" + str(script).replace("'", "''") + "')"]
    record = {"command": command, "script_sha256": hashlib.sha256(script.read_bytes()).hexdigest(),
              "kind": "read_plan_no_propagation_initialization_saved_synthetic_parity",
              "propagation_authorized": False, "full_cavity_runs": 0,
              "parent_budget_category": "matlab", "parent_budget_label": running[0]["label"],
              "numerical_threads": 1, "parpool": False, "gpu": False,
              "status": "reserved_before_exec", "pid": os.getpid()}
    with (folder / "reservation.json").open("x") as stream:
        json.dump(record, stream, indent=2); stream.write("\n")
    environment = os.environ.copy()
    environment.update(PHASE2_ROOT=str(ROOT), PHASE2_OUTPUT_DIR=str(folder))
    sys.stdout.flush(); sys.stderr.flush()
    os.execve(matlab, command, environment)


if __name__ == "__main__":
    main()
