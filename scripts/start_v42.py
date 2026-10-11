#!/usr/bin/env python3
"""Exclusive V4.2 reservation and hashes; reuses existing budget ledger format."""
import datetime as dt
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import time

started=time.monotonic()
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports/local/accuracy_v4_2_001'
OUT.mkdir(exist_ok=False)
snapshot={}
for path in ROOT.rglob('*'):
    if not path.is_file() or path.is_relative_to(OUT) or any(x in path.parts for x in ('.git','__pycache__','.pytest_cache')):
        continue
    if 'v42' in path.name:continue
    snapshot[path.relative_to(ROOT).as_posix()]=hashlib.sha256(path.read_bytes()).hexdigest()
review=json.loads((ROOT/'mamyshev_accuracy_v4/UPLOAD_REVIEW_CHECKS.json').read_text())
locations={'ACCURACY_V4_1_TARGETED_REPORT.md':'docs/ACCURACY_V4_1_TARGETED_REPORT.md',
           'selection.json':'reports/local/accuracy_v4_1_001/development/selection.json',
           'summary.json':'reports/local/accuracy_v4_1_001/summary/summary.json'}
checks={name:snapshot[locations[name]]==digest for name,digest in review['inputs'].items()}
value={'utc':dt.datetime.now(dt.timezone.utc).isoformat(),'python':sys.executable,
       'python_version':platform.python_version(),'architecture':platform.machine(),
       'branch':subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip(),
       'commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
       'git_status':subprocess.check_output(['git','status','--short'],cwd=ROOT,text=True),
       'sha256':snapshot,'upload_review_input_hash_checks':checks,
       'copied_historical_data_files':0,'MATLAB_starts':0,'GMMNLSE_attempts':0}
(OUT/'start_snapshot.json').write_text(json.dumps(value,indent=2)+'\n')
entry={'category':'engineering','label':'exclusive_snapshot','status':'completed' if all(checks.values()) else 'failed',
       'charged_s':time.monotonic()-started,'command':[sys.executable,str(Path(__file__).resolve())],
       'full_gmmnlse_calls':0,'matlab_processes':0}
(OUT/'budget_ledger.json').write_text(json.dumps({'caps_s':{'engineering':300.,'ml':900.},'attempts':[entry]},indent=2)+'\n')
print(json.dumps({'old_files_hashed':len(snapshot),'review_hash_checks':checks,'entry':entry},indent=2))
if not all(checks.values()):raise SystemExit('Review input identity mismatch; reservation retained')
