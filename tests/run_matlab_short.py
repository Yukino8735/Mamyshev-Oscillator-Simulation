"""Serial, bounded MATLAB fixtures, using Phase 1's owned-process-group isolation.

No interpreter path is installed or inferred. Pass the existing MATLAB executable.
All machine logs/records belong under the ignored batch directory, not tests/.
"""
import argparse
import datetime as dt
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BATCH = "repair_001"
TOTAL_LIMIT_S = 600
PROCESS_LIMIT_S = 180
BATCH_LIMITS_S = {"repair_001": 600, "readiness_001": 600,
                  "launchprep_001": 600, "config_waveform_001": 300,
                  "stationarity_001": 300, "accuracy_v4_001": 180}


def batch_directory(name):
    """Keep short-test budgets/evidence separate; not a full-cavity launcher."""
    if name not in BATCH_LIMITS_S:
        raise ValueError("Unknown authorized short-test batch")
    return ROOT / "reports/local/phase2" / name


def remaining_budget(records, total_limit_s=TOTAL_LIMIT_S):
    if any(record["status"] == "running" for record in records):
        raise RuntimeError("Earlier test remains marked running; inspect before retrying")
    return total_limit_s - sum(record["elapsed_s"] for record in records)


def budget_records(batch):
    """Keep unfinalized runner evidence intact; explicit failed reconciliation
    may only debit the full cap after external verification of group absence.
    It never promotes an interrupted attempt to successful completion.
    """
    records = []
    for path in batch.glob("*/runner_record.json"):
        record = json.loads(path.read_text())
        reconciliation = path.with_name("runner_reconciliation.json")
        if record["status"] == "running" and reconciliation.is_file():
            audit = json.loads(reconciliation.read_text())
            if audit.get("status") != "failed" or audit.get("cleanup_verified") is not True or audit.get("elapsed_s") != PROCESS_LIMIT_S:
                raise RuntimeError("Invalid failed-attempt budget reconciliation")
            record = {**record, **audit}
        records.append(record)
    return records


def process_group_state(pgid):
    """A successful, fully parsed process table is required to prove absence."""
    try:
        check = subprocess.run(["/bin/ps", "-axo", "pid=,pgid="],
                               capture_output=True, text=True)
        if check.returncode != 0 or not check.stdout.strip():
            return "unknown"
        groups = []
        for line in check.stdout.splitlines():
            parts = line.split()
            if len(parts) != 2 or not all(part.isdigit() for part in parts):
                return "unknown"
            groups.append(int(parts[1]))
        return "present" if pgid in groups else "absent"
    except (OSError, ValueError):
        return "unknown"


def stop_owned(process):
    """Only accept a Popen started by this runner in a new session."""
    def group_confirmed_absent():
        # macOS may report EPERM when signalling a just-disappeared group.
        # Only a successful read-only process-table check can discharge it;
        # permission errors never authorize ignoring a live/unknown group.
        if process.poll() is None:
            return False
        return process_group_state(process.pid) == "absent"
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        process.wait()
        return
    except PermissionError:
        if group_confirmed_absent():
            return
        raise
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        pass
    # Clean up descendants in this owned group even if its leader already exited.
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    except PermissionError:
        if not group_confirmed_absent():
            raise
    process.wait()


def run_isolated(command, run_dir, env, timeout_s, metadata=None, shutdown_reserve_s=7):
    start = time.monotonic()
    record = {"command": command, "start_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
              "timeout_s": timeout_s, "status": "running", "elapsed_s": 0,
              "full_cavity_runs": 0, "kind": "synthetic_short_test", "stop_events": []}
    if metadata:
        record.update(metadata)
    def save():
        temporary = run_dir / "runner_record.tmp"
        temporary.write_text(json.dumps(record, indent=2) + "\n")
        temporary.replace(run_dir / "runner_record.json")
    stop_reason = "process_exit"
    with (run_dir / "stdout.log").open("w") as log:
        try:
            process = subprocess.Popen(command, cwd=run_dir, env=env, stdout=log,
                                       stderr=subprocess.STDOUT, start_new_session=True)
        except BaseException as exception:
            record.update(end_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
                elapsed_s=time.monotonic()-start, exit_code=None, status="failed",
                stop_reason="process_start_error", error=repr(exception))
            save()
            raise
        try:
            record.update(pid=process.pid, process_group=process.pid)
            save()
            while True:
                elapsed = time.monotonic() - start
                # Record observations before checking exit. Once confirmed, a
                # STOP/deadline cannot be erased by a subsequent graceful exit.
                if (run_dir / "STOP").exists():
                    record["stop_events"].append({"reason": "cancelled", "elapsed_s": elapsed})
                # Include startup, exit and up to 5 s graceful shutdown in the cap.
                if elapsed >= timeout_s - shutdown_reserve_s:
                    record["stop_events"].append({"reason": "timeout", "elapsed_s": elapsed})
                if record["stop_events"]:
                    stop_reason = record["stop_events"][0]["reason"]
                    break
                if process.poll() is not None:
                    break
                time.sleep(0.1)
        except BaseException:
            stop_reason = "runner_interrupted"
            record["stop_events"].append({"reason": stop_reason, "elapsed_s": time.monotonic()-start})
            raise
        finally:
            cleanup_error = None
            try:
                stop_owned(process)
            except BaseException as exception:
                cleanup_error = exception
                record["cleanup_error"] = repr(exception)
                record["cleanup_verified"] = False
            else:
                record["cleanup_verified"] = True
            record.update(end_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
                          elapsed_s=time.monotonic()-start, exit_code=process.returncode,
                          stop_reason=stop_reason,
                          status="completed" if process.returncode == 0 and stop_reason == "process_exit" and cleanup_error is None else "failed")
            save()
            if cleanup_error is not None:
                raise cleanup_error
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_id")
    parser.add_argument("script", type=Path)
    parser.add_argument("--matlab", type=Path, required=True)
    parser.add_argument("--batch", choices=list(BATCH_LIMITS_S), default=DEFAULT_BATCH)
    args = parser.parse_args()
    script = args.script.resolve()
    if not script.is_relative_to(ROOT / "tests/matlab") or not script.is_file():
        parser.error("Only an inspected script under tests/matlab may be launched")
    if not args.run_id.replace("_", "").isalnum():
        parser.error("Invalid run_id")
    batch = batch_directory(args.batch)
    batch.mkdir(parents=True, exist_ok=True)
    with (batch / ".runner.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        records = budget_records(batch)
        if args.batch == "accuracy_v4_001" and len(list(batch.glob("*/input_provenance.json"))) >= 2:
            raise SystemExit("V4 permits at most two MATLAB short processes; no retry budget remains")
        preflight = script.name == "run_launchprep_preflight.m"
        if preflight and any(json.loads(p.read_text()).get("script") == str(script)
                             for p in batch.glob("*/input_provenance.json")):
            raise SystemExit("The one full-configuration preflight is already reserved; do not repeat it")
        total_limit_s = BATCH_LIMITS_S[args.batch]
        timeout = min(PROCESS_LIMIT_S, remaining_budget(records, total_limit_s))
        if timeout <= 7:
            raise SystemExit("MATLAB short-test budget exhausted")
        run_dir = batch / args.run_id
        run_dir.mkdir()  # Refuse overwrite of evidence.
        env = os.environ.copy()
        env.update(PHASE2_ROOT=str(ROOT), PHASE2_OUTPUT_DIR=str(run_dir))
        command = [str(args.matlab.resolve()), "-batch", "run('" + str(script).replace("'", "''") + "')"]
        (run_dir / "input_provenance.json").write_text(json.dumps({
            "batch_id": args.batch,
            "script_sha256": hashlib.sha256(script.read_bytes()).hexdigest(),
            "script": str(script), "remaining_budget_s_before": remaining_budget(records, total_limit_s),
            "batch_total_limit_s": total_limit_s,
            "git_status": subprocess.check_output(["git", "status", "--short"], cwd=ROOT, text=True),
            "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        }, indent=2)+"\n")
        record = run_isolated(command, run_dir, env, timeout,
            metadata={"kind": "initialization_preflight", "propagation_started": False,
                      "full_cavity_attempts": 0} if preflight else None)
        print(json.dumps(record, indent=2), flush=True)
        if record["status"] != "completed":
            raise SystemExit(record["exit_code"] or 1)


if __name__ == "__main__":
    main()
