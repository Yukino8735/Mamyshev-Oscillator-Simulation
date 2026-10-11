#!/usr/bin/env python3
"""Short localhost preview driver inside the existing batch process monitor.

This is a bounded service lifetime, not a second scientific supervisor. The
outer run_demo10k_budget/run_v4_budget monitor owns the session/process group.
Only this driver's direct Streamlit child is terminated here; no group signal.
"""
from pathlib import Path
import argparse
import datetime as dt
import hashlib
import json
import os
import signal
import socket
import subprocess
import sys
import time
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]


def save(path, value):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def main():
    started = time.monotonic()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--copy-record", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--wall-s", type=float, default=120)
    args = parser.parse_args()
    if not 10 <= args.wall_s <= 120:
        parser.error("Preview wall clock must be 10..120 seconds, including child cleanup")
    copied = json.loads(args.copy_record.read_text())
    directory = Path(copied["directory"]).resolve()
    if directory.is_relative_to(ROOT) or not (directory / "demo/app.py").is_file():
        raise ValueError("Expected the separately verified outside-repository preview")
    manifest = json.loads((directory / "preview_manifest.json").read_text())
    for entry in manifest["files"]:
        path = directory / entry["path"]
        if path.is_symlink() or not path.resolve().is_relative_to(directory) or hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
            raise ValueError("Standalone preview bytes changed: " + entry["path"])
    args.out.mkdir(parents=True, exist_ok=False)
    stop_path = args.out / "STOP_PREVIEW"
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    url = f"http://127.0.0.1:{port}"
    command = [sys.executable, "-I", "-B", "-m", "streamlit", "run", str(directory / "demo/app.py"),
        "--server.address", "127.0.0.1", "--server.port", str(port), "--server.headless", "true",
        "--browser.gatherUsageStats", "false", "--server.fileWatcherType", "none"]
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    env.update({k: "2" for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
        "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS")})
    record = {"command": command, "cwd": str(directory), "url": url, "status": "starting",
        "start_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "total_wall_limit_s": args.wall_s,
        "cleanup_reserve_inside_wall_s": 5, "new_session": False, "stop_file": str(stop_path),
        "server_ready": False, "public_release_blocked": True, "browser_visual_check": "requires_actual_browser",
        "new_labels": 0, "MATLAB_starts": 0}
    path = args.out / "server_record.json"
    save(path, record)
    child = None
    interrupted = {"signal": None}

    def stopped(signum, frame):
        interrupted["signal"] = signum

    previous = {s: signal.signal(s, stopped) for s in (signal.SIGTERM, signal.SIGINT)}
    try:
        with (args.out / "server_stdout.log").open("x") as log:
            child = subprocess.Popen(command, cwd=directory, env=env, stdout=log,
                stderr=subprocess.STDOUT, start_new_session=False)
            record.update(pid=child.pid, inherited_process_group=os.getpgid(child.pid))
            save(path, record)
            while True:
                elapsed = time.monotonic() - started
                if interrupted["signal"] is not None:
                    record["stop_reason"] = "driver_signal"
                    break
                if stop_path.exists():
                    record["stop_reason"] = "STOP_PREVIEW"
                    break
                if elapsed >= args.wall_s - 5:
                    record["stop_reason"] = "bounded_preview_window_ended"
                    break
                if child.poll() is not None:
                    raise RuntimeError("Streamlit exited before the preview was closed")
                if not record["server_ready"]:
                    try:
                        with urlopen(url + "/_stcore/health", timeout=.5) as response:
                            ready = response.status == 200 and response.read().strip() == b"ok"
                    except OSError:
                        ready = False
                    if ready and child.poll() is None:
                        record.update(server_ready=True, status="ready", ready_elapsed_s=elapsed)
                        save(path, record)
                        print(json.dumps({"status": "ready", "url": url, "stop_file": str(stop_path)}), flush=True)
                time.sleep(.1)
    except BaseException as exc:
        record.update(status="failed", error=repr(exc))
        raise
    finally:
        cleanup_start = time.monotonic()
        cleanup_error = None
        try:
            if child is not None and child.poll() is None:
                child.terminate()
                try:
                    child.wait(timeout=min(3, max(.1, args.wall_s - (time.monotonic() - started))))
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait(timeout=1)
        except BaseException as exc:
            cleanup_error = repr(exc)
        for signum, old in previous.items():
            signal.signal(signum, old)
        record.update(end_utc=dt.datetime.now(dt.timezone.utc).isoformat(), elapsed_s=time.monotonic() - started,
            cleanup_elapsed_s=time.monotonic() - cleanup_start, cleanup_error=cleanup_error,
            child_exit_code=None if child is None else child.poll(),
            child_stopped=child is not None and child.poll() is not None)
        if record["status"] != "failed":
            record["status"] = "preview_closed" if record["server_ready"] and record["child_stopped"] and cleanup_error is None else "failed"
        save(path, record)
        print(json.dumps(record), flush=True)
    if record["status"] != "preview_closed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
