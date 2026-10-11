"""Single-run supervisor. --dry-run never launches MATLAB or propagation.

--execute-real is a separate explicit action requiring user authorization.
Component mode uses only tagged synthetic MATLAB fixtures and the independent
launchprep_001 600/180 second serial budget. No automatic retry in either mode.
"""
import argparse
import fcntl
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from mamyshev_ml import supervisor


def main():
    p = argparse.ArgumentParser(description=__doc__)
    action = p.add_mutually_exclusive_group(required=True)
    action.add_argument("--dry-run", action="store_true")
    action.add_argument("--execute-real", action="store_true")
    action.add_argument("--component-script", type=Path)
    p.add_argument("--run-id", required=True)
    p.add_argument("--matlab", type=Path, required=True)
    p.add_argument("--batch-id", choices=["single_validation_001", "single_validation_002", "config_waveform_validation_001", "observation_validation_001"])
    p.add_argument("--timeout-s", type=int, choices=[900, 1800, 3600])
    p.add_argument("--design-config", type=Path,
                   help="Four dimensional request JSON; currently only the authorized default design is launchable")
    p.add_argument("--save-waveforms", action="store_true")
    p.add_argument("--observation-mode", choices=["fixed_roundtrips"])
    p.add_argument("--observation-roundtrips", type=int)
    p.add_argument("--plan", type=Path, help="Canonical configuration-driven live scan plan")
    p.add_argument("--authorization", type=Path, help="Separate explicit live authorization JSON; plans do not authorize execution")
    p.add_argument("--design-id")
    p.add_argument("--batch-directory", type=Path)
    args = p.parse_args()
    if not args.run_id.replace("_", "").isalnum():
        p.error("Invalid run ID")
    configured = (args.plan, args.authorization, args.design_id, args.batch_directory)
    if any(value is not None for value in configured):
        if not all(value is not None for value in configured) or args.component_script or any(
                value is not None for value in (args.batch_id, args.timeout_s, args.design_config,
                                                args.observation_mode, args.observation_roundtrips)) or args.save_waveforms:
            p.error("Configured live mode requires plan/authorization/design-id/batch-directory; no historical overrides")
        try:
            plan = supervisor.load_json(args.plan)
            authorization = supervisor.load_json(args.authorization)
            design = supervisor.validate_live_authorization(plan, authorization, args.design_id)
            if args.dry_run:
                print(json.dumps({"mode": "dry_run", "propagation_started": False, "full_cavity_attempts": 0,
                    "future_directory": str(args.batch_directory.resolve()/args.run_id), "run_id": args.run_id,
                    "design_id": args.design_id, "design_config": design, "authorization": authorization,
                    "execute_real_enabled": False, "save_waveforms": True,
                    "shutdown_and_finalization_reserve_s": 30, "reserve_included_in_timeout": True}, indent=2))
                return
            result = supervisor.execute_authorized_design(matlab=args.matlab, plan=plan, authorization=authorization,
                design_id=args.design_id, batch_dir=args.batch_directory, run_id=args.run_id, execute_real=args.execute_real)
        except (OSError, ValueError, RuntimeError) as exc:
            p.error(str(exc))
        print(json.dumps({"job_status": result["final_result"]["job_status"], "run_id": args.run_id,
                          "final_result": result["final_path"]}, indent=2))
        if result["final_result"]["job_status"] != "completed":
            raise SystemExit(1)
        return
    script = ROOT / "code/ml_bridge/launch_mamyshev_once.m"
    mode = "real"
    batch_id = args.batch_id or "single_validation_001"
    timeout = args.timeout_s if args.timeout_s is not None else 900
    observation_requested = args.observation_mode is not None or args.observation_roundtrips is not None
    if args.component_script and (args.batch_id is not None or args.timeout_s is not None or
                                  args.design_config is not None or args.save_waveforms or observation_requested):
        p.error("Real batch/budget options are not allowed in component mode")
    if observation_requested and batch_id != "observation_validation_001":
        p.error("Observation options require the separately authorized observation_validation_001 batch")
    design = None
    observation = None
    if batch_id in {"config_waveform_validation_001", "observation_validation_001"}:
        expected_run, expected_timeout = ("config_waveform_001", 1800) if batch_id == "config_waveform_validation_001" else ("observation_001", 3600)
        if args.run_id != expected_run or args.timeout_s != expected_timeout or args.design_config is None or not args.save_waveforms:
            p.error(f"{batch_id} requires {expected_run}, explicit {expected_timeout} seconds, design JSON and --save-waveforms")
        try:
            design = supervisor.validate_design_config(supervisor.load_json(args.design_config))
        except (OSError, ValueError, TypeError) as exc:
            p.error("Invalid design configuration: " + str(exc))
        if design != supervisor.DEFAULT_DESIGN_CONFIG:
            p.error("This real batch authorizes only the default design, not a parameter scan")
        if batch_id == "observation_validation_001":
            if args.observation_mode != "fixed_roundtrips" or args.observation_roundtrips != 20:
                p.error("This observation batch requires explicit fixed_roundtrips and exactly 20 rounds")
            observation = supervisor.validate_observation_options({
                "observation_mode": args.observation_mode,
                "observation_roundtrips": args.observation_roundtrips})
    elif args.design_config is not None or args.save_waveforms:
        p.error("Design and waveform arguments require the separately authorized config_waveform batch")
    elif batch_id == "single_validation_002":
        if args.run_id != "validation_002" or args.timeout_s != 1800:
            p.error("single_validation_002 requires validation_002 and explicit --timeout-s 1800")
    elif timeout != 900:
        p.error("The original batch retains its 900 second limit")
    batch = ROOT / "reports/local/phase2" / batch_id
    if args.component_script:
        mode = "synthetic"
        script = args.component_script.resolve()
        if script != ROOT / "tests/matlab/run_launchprep_candidate.m" or not script.is_file():
            p.error("Only the inspected synthetic candidate fixture is allowed in component mode")
        batch = supervisor.monitor.batch_directory("launchprep_001")
    if not args.matlab.is_file() or not script.is_file():
        p.error("Existing MATLAB and script paths are required")
    expression = ("run('" + str(script).replace("'", "''") + "')") if mode == "synthetic" else (
        "addpath('" + str(script.parent).replace("'", "''") + "'); launch_mamyshev_once")
    command = [str(args.matlab.resolve()), "-batch", expression]
    if args.dry_run:
        print(json.dumps({"mode": "dry_run", "propagation_started": False, "full_cavity_attempts": 0,
            "future_command": command, "future_directory": str(batch / args.run_id),
            "backend_mode": mode, "batch_id": batch_id, "run_id": args.run_id,
            "timeout_s": timeout, "shutdown_and_finalization_reserve_s": 30,
            "reserve_included_in_timeout": True, "max_attempts": 1,
            "requested": {"PumpPower": 4, "cw2": 1030, "plot_on": False},
            "seed": 0, "rng_algorithm": "twister",
            "design_config": design, "save_waveforms": bool(args.save_waveforms),
            "observation_options": observation,
            "STOP": str(batch / args.run_id / "STOP")}, indent=2))
        return
    batch.mkdir(parents=True, exist_ok=True)
    with (batch / ".runner.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        records = supervisor.monitor.budget_records(batch)
        if mode == "real":
            # Any prior reserved attempt blocks another, including interrupted
            # startup with no runner file. Never retry a failed real invocation.
            if any(f.is_dir() for f in batch.iterdir()):
                raise SystemExit("Single real attempt already reserved; no retry authorized")
        else:
            timeout = min(180, supervisor.monitor.remaining_budget(records))
            if timeout <= 7:
                raise SystemExit("MATLAB component budget exhausted")
        folder = batch / args.run_id
        folder.mkdir()  # exclusive reservation, no overwrite
        expected = supervisor.request_identity(args.run_id, mode)
        if design is not None:
            expected.update(design_config=design, save_waveforms=True)
        if observation is not None:
            expected["observation_options"] = observation
        expected.update(batch_id=batch.name, total_wall_limit_s=timeout,
                        shutdown_and_finalization_reserve_s=30 if mode == "real" else 7)
        result = supervisor.execute_once(command, folder, expected, timeout)
        print(json.dumps({"job_status": result["job_status"], "run_id": args.run_id,
                          "final_result": str(folder / "final_result.json")}, indent=2))
        if result["job_status"] != "completed":
            raise SystemExit(1)


if __name__ == "__main__":
    main()
