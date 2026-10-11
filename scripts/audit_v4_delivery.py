#!/usr/bin/env python3
"""Read-only identity/retention audit; writes only a new local delivery record."""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'reports/local/accuracy_v4_001'
start = json.loads((BASE / 'start_snapshot.json').read_text())
allowed = {'environment.yml', 'pyproject.toml', 'src/mamyshev_ml/supervisor.py',
           'scripts/run_mamyshev_once.py', 'tests/run_matlab_short.py',
           'code/ml_bridge/launch_mamyshev_once.m', 'docs/EXECUTION_STATUS.md', 'docs/SCOPE.md'}
changed, missing = [], []
for name, old in start['sha256'].items():
    path = ROOT / name
    if not path.exists():
        missing.append(name)
    elif hashlib.sha256(path.read_bytes()).hexdigest() != old:
        changed.append(name)
unexpected = sorted(set(changed)-allowed)
diff = subprocess.run(['git', 'diff', '--check'], cwd=ROOT, capture_output=True, text=True)
branch = subprocess.check_output(['git', 'branch', '--show-current'], cwd=ROOT, text=True).strip()
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
new_files = sorted(str(p.relative_to(ROOT)) for directory in ['src', 'scripts', 'tests', 'code', 'docs']
                   for p in (ROOT / directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts
                   and str(p.relative_to(ROOT)) not in start['sha256'])
whitespace = []
for name in new_files:
    if Path(name).suffix not in {'.py', '.m', '.md', '.json'}:
        continue
    for line, text in enumerate((ROOT / name).read_text().splitlines(), 1):
        if text.rstrip() != text:
            whitespace.append({'path': name, 'line': line})
selection = json.loads((BASE / 'models/selection.json').read_text())
model_unchanged = hashlib.sha256((BASE / 'models/model.joblib').read_bytes()).hexdigest() == selection['model_sha256']
learning_source_unchanged = all(hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == digest
                                for p, digest in selection['training_source_hashes'].items())
search_protocol = json.loads((BASE / 'search/frozen_search_protocol.json').read_text())
search_source_unchanged = hashlib.sha256((ROOT / 'src/mamyshev_ml/v4_search.py').read_bytes()).hexdigest() == search_protocol['input_hashes']['search_source']
historical_final = ROOT / 'reports/local/phase2/observation_validation_001/observation_001/final_result.json'
result = {'initial_files_checked': len(start['sha256']), 'changed_existing_files': sorted(changed),
          'unexpected_changed': unexpected, 'missing_original_files': missing, 'new_source_report_files': new_files,
          'git_diff_check_exit': diff.returncode, 'git_diff_check_output': diff.stdout+diff.stderr,
          'new_file_whitespace_findings': whitespace, 'branch': branch, 'commit': commit,
          'branch_commit_unchanged': branch == start['branch'] and commit == start['commit'],
          'old_observation_final_still_missing': not historical_final.exists(),
          'frozen_model_unchanged': model_unchanged, 'frozen_learning_sources_unchanged': learning_source_unchanged,
          'frozen_search_source_unchanged': search_source_unchanged,
          'physical_numerical_production_files_unchanged': not any(p.startswith('code/ring_cavity/') or p.startswith('code/simulation_engine/') for p in changed),
          'versions': {p: importlib.metadata.version(p) for p in ['numpy','scipy','scikit-learn','matplotlib','joblib','threadpoolctl','pip']},
          'python': sys.executable, 'python_version': platform.python_version(), 'architecture': platform.machine(),
          'conda': subprocess.check_output(['/opt/homebrew/Caskroom/miniforge/base/bin/conda','--version'], text=True).strip(),
          'new_full_gmmnlse_attempts': 0}
paths = [p for p in BASE.rglob('*') if p.is_file()]
result['current_local_artifact_files'] = len(paths)
result['current_local_artifact_bytes'] = sum(p.stat().st_size for p in paths)
result['passed'] = (not unexpected and not missing and diff.returncode == 0 and not whitespace
                    and result['branch_commit_unchanged'] and result['old_observation_final_still_missing']
                    and model_unchanged and learning_source_unchanged and search_source_unchanged)
with (BASE / 'delivery_review.json').open('x') as stream:
    stream.write(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
if not result['passed']:
    sys.exit(1)
