#!/usr/bin/env python3
"""Compact aggregate preservation receipts; reuse existing hashing, no experiments."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/local/demo_ux_001"
spec = importlib.util.spec_from_file_location("prior_preservation", ROOT / "scripts/finalize_demo10k_review.py")
prior = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prior)
sha = prior.sha
GROUPS = {
    "model_and_demo_assets": ["demo/assets"],
    "production_and_materials": ["code", "third_party"],
    "historical_evidence": ["reports/local"],
    "data_recipe_scientific_python": ["data", "results", "archive", "mamyshev_accuracy_v4/reference",
        "mamyshev_accuracy_v4/configs", "mamyshev_accuracy_v4/data", "mamyshev_accuracy_v4/evaluation_only",
        "src/mamyshev_ml", "configs"],
}
EDITABLE = ["demo/app.py", "demo/ui_logic.py", "README.md", "docs/USER_GUIDE_ZH.md",
            "docs/EXECUTION_STATUS.md", "docs/SCOPE.md"]


def write(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def snapshot():
    groups = {}
    for name, roots in GROUPS.items():
        digest = hashlib.sha256(); count = total = 0
        files = sorted({p for r in roots for p in (ROOT / r).rglob("*") if p.is_file()
            and not p.is_relative_to(OUT) and not {"__pycache__", ".pytest_cache"}.intersection(p.parts)})
        for p in files:
            raw = p.read_bytes()
            digest.update(p.relative_to(ROOT).as_posix().encode() + b"\0" + hashlib.sha256(raw).digest())
            count += 1; total += len(raw)
        groups[name] = {"files": count, "bytes": total, "aggregate_sha256": digest.hexdigest()}
    return {"groups": groups, "branch": git("branch", "--show-current").decode().strip(),
        "commit": git("rev-parse", "HEAD").decode().strip(),
        "staged_diff_sha256": hashlib.sha256(git("diff", "--cached", "--binary")).hexdigest(),
        "editable": {p: {"sha256": sha(ROOT/p), "bytes": (ROOT/p).stat().st_size} for p in EDITABLE},
        "loader_sha256": sha(ROOT/"src/mamyshev_ml/demo_inference.py"),
        "cli_sha256": sha(ROOT/"demo/predict.py"),
        "model_10k_sha256": sha(ROOT/"demo/assets/models/demo_10k_v1/model.joblib")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["start", "check"])
    mode = parser.parse_args().mode
    started = time.monotonic()
    if mode == "start":
        OUT.mkdir(exist_ok=False)
        before = snapshot()
        if before["model_10k_sha256"] != "9885e8f258fa10de0a69844b70fa72242fcc64267d9db1e6c07dd4bd4609b6d0":
            raise ValueError("Unexpected model identity")
        before["git_status"] = git("status", "--short").decode()
        write(OUT/"start_snapshot.json", before)
        backup = OUT/"before"; backup.mkdir()
        # Only the six intended editable files, not a copy of the historical evidence.
        for name in EDITABLE:
            p = backup/name; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes((ROOT/name).read_bytes())
        write(OUT/"budget_ledger.json", {"caps_s": {"engineering": 300.}, "attempts": [{
            "category": "engineering", "label": "exclusive_snapshot", "status": "completed",
            "charged_s": time.monotonic()-started, "command": [__file__, "start"], "full_gmmnlse_calls": 0}]})
        print(json.dumps({"status": "snapshot_saved", "groups": before["groups"]}))
    else:
        before = json.loads((OUT/"start_snapshot.json").read_text()); after = snapshot()
        same = {name: before["groups"][name] == now for name, now in after["groups"].items()}
        keys = ("branch", "commit", "staged_diff_sha256", "loader_sha256", "cli_sha256", "model_10k_sha256")
        same.update({name: before[name] == after[name] for name in keys})
        check = subprocess.run(["git", "diff", "--check"], cwd=ROOT, capture_output=True, text=True)
        record = {"preserved": same, "after": after, "git_diff_check_exit": check.returncode,
            "git_diff_check_output": check.stdout+check.stderr, "internal_wall_s": time.monotonic()-started}
        write(OUT/"preservation_check.json", record)
        print(json.dumps({"preserved": same, "git_diff_check_exit": check.returncode}))
        if not all(same.values()) or check.returncode:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
