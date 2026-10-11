#!/usr/bin/env python3
"""Reserve one application batch and preserve prior bytes; no model inference."""
import datetime as dt
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import time

started = time.monotonic()
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'reports/local/application_v4_3_001'
OUT.mkdir(exist_ok=False)
snapshot = {}
for path in ROOT.rglob('*'):
    if not path.is_file() or path.is_relative_to(OUT) or any(p in path.parts for p in ('.git', '__pycache__', '.pytest_cache')):
        continue
    if 'v43' in path.name:
        continue  # These newly authored application files are recorded separately.
    snapshot[path.relative_to(ROOT).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
review = json.loads((ROOT / 'mamyshev_accuracy_v4/V4_2_UPLOAD_REVIEW.json').read_text())
locations = {'ACCURACY_V4_2_REPRESENTATION_REPORT.md': 'docs/ACCURACY_V4_2_REPRESENTATION_REPORT.md',
             'summary.json': 'reports/local/accuracy_v4_2_001/summary.json',
             'selection.json': 'reports/local/accuracy_v4_2_001/release/selection.json'}
checks = {name: snapshot[locations[name]] == item['sha256'] and (ROOT / locations[name]).stat().st_size == item['bytes']
          for name, item in review['inputs'].items()}
value = {'utc': dt.datetime.now(dt.timezone.utc).isoformat(), 'python': sys.executable,
    'python_version': platform.python_version(), 'architecture': platform.machine(),
    'branch': subprocess.check_output(['git', 'branch', '--show-current'], cwd=ROOT, text=True).strip(),
    'commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
    'git_status': subprocess.check_output(['git', 'status', '--short'], cwd=ROOT, text=True),
    'sha256': snapshot, 'upload_review_input_hash_checks': checks, 'MATLAB_starts': 0, 'GMMNLSE_attempts': 0}
(OUT / 'start_snapshot.json').write_text(json.dumps(value, indent=2) + '\n')
entry = {'category': 'engineering', 'label': 'exclusive_snapshot', 'status': 'completed' if all(checks.values()) else 'failed',
         'charged_s': time.monotonic()-started, 'command': [sys.executable, str(Path(__file__).resolve())],
         'full_gmmnlse_calls': 0, 'matlab_processes': 0}
(OUT / 'budget_ledger.json').write_text(json.dumps({'caps_s': {'engineering': 300., 'ml': 300.}, 'attempts': [entry]}, indent=2)+'\n')
print(json.dumps({'old_files_hashed': len(snapshot), 'review_checks': checks, 'entry': entry}, indent=2))
if not all(checks.values()):
    raise SystemExit('Review input identity mismatch; reservation retained')
