#!/usr/bin/env python3
"""Read-only evidence/Git closeout after computation has stopped; no new tests."""
import hashlib
import importlib.util
import json
from pathlib import Path
import socket
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/local/demo_10k_release_001"
ALLOWED = {".gitignore", "README.md", "docs/USER_GUIDE_ZH.md", "docs/CLAIM_EVIDENCE.md",
           "docs/SCOPE.md", "docs/EXECUTION_STATUS.md"}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def main():
    started = time.monotonic()
    # Save externally reported control-plane latency separately, never rewrite
    # the original monitored attempt ledger to pretend this wait was measured there.
    server = json.loads((OUT / "browser_preview/server_record.json").read_text())
    host, port = server["url"].removeprefix("http://").split(":")
    with socket.socket() as probe:
        probe.settimeout(.25)
        port_open = probe.connect_ex((host, int(port))) == 0
    save(OUT / "browser_preview/visual_check.json", {
        "browser_visual_check": "not_run", "screenshots": [],
        "reason": "CUA getApp(Safari) returned after bounded localhost service had closed; no Demo page inspection occurred",
        "tool_reported_wait_s": 2717.7581, "source": "cua_repl tool wall-time metadata",
        "server_record_preserved": True, "child_stopped": server["child_stopped"],
        "original_port_listening_at_closeout": port_open, "another_preview_started": False,
    })
    save(OUT / "budget_exception.json", {
        "control_plane_tool": "cua_repl getApp Safari", "reported_wait_s": 2717.7581,
        "engineering_cap_s": 600, "inclusive_engineering_wall_budget_exceeded": True,
        "overlap_with_monitored_preview": "yes; cannot sum both as disjoint exact wall time",
        "monitored_ledger_scope": "owned Python/MATLAB/server processes, excluding control-plane latency",
        "action": "No further component/browser/scientific attempts. Read-only Git/preservation and report closeout only.",
    })
    spec = importlib.util.spec_from_file_location("git_review", ROOT / "scripts/review_demo10k_git.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.main()
    before = json.loads((OUT / "start_snapshot.json").read_text())
    changes = []
    for name, old in before["files"].items():
        path = ROOT / name
        if not path.exists() or sha(path) != old["sha256"]:
            changes.append({"path": name, "before_sha256": old["sha256"],
                "after_sha256": sha(path) if path.exists() else None,
                "expected_document_or_ignore_edit": name in ALLOWED})
    git = lambda *args: subprocess.check_output(["git", *args], cwd=ROOT)
    check = subprocess.run(["git", "diff", "--check"], cwd=ROOT, capture_output=True, text=True)
    source_files = []
    for path in ROOT.rglob("*"):
        if (not path.is_file() or any(x in path.parts for x in (".git", "__pycache__", ".pytest_cache"))):
            continue
        name = path.relative_to(ROOT).as_posix()
        if name not in before["files"] and not name.startswith("reports/local/"):
            source_files.append({"path": name, "bytes": path.stat().st_size, "sha256": sha(path)})
    unchanged = len(before["files"]) - len(changes)
    result = {"snapshot_files": len(before["files"]), "unchanged_original_files": unchanged,
        "original_file_changes": changes, "unexpected_changes": [x for x in changes if not x["expected_document_or_ignore_edit"]],
        "branch_preserved": git("branch", "--show-current").decode().strip() == before["branch"],
        "commit_preserved": git("rev-parse", "HEAD").decode().strip() == before["commit"],
        "staged_diff_preserved": hashlib.sha256(git("diff", "--cached", "--binary")).hexdigest() == before["staged_diff_sha256"],
        "git_diff_check_exit": check.returncode, "git_diff_check_output": check.stdout + check.stderr,
        "original_frozen_assets_preserved": all((ROOT/name).exists() and sha(ROOT/name) == old["sha256"] for name, old in before["frozen_assets"].items()),
        "new_nonlocal_files": source_files, "preview_port_closed": not port_open,
        "git_manifest_sha256": sha(OUT / "git_release_manifest.json"),
        "hash_scope": "Evidence and worktree at closeout checkpoint. Later final report/status text edits are documented separately.",
        "closeout_internal_wall_s": time.monotonic() - started}
    save(OUT / "preservation_check.json", result)
    print(json.dumps({key: value for key, value in result.items() if key not in {"new_nonlocal_files", "original_file_changes"}}, indent=2))
    if result["unexpected_changes"] or not all(result[k] for k in ("branch_preserved", "commit_preserved", "staged_diff_preserved", "original_frozen_assets_preserved", "preview_port_closed")) or check.returncode:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
