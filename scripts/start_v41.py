#!/usr/bin/env python3
"""Exclusive V4.1 evidence reservation and read-only V4/history freeze."""
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
OUT = ROOT / 'reports/local/accuracy_v4_1_001'
OUT.mkdir(exist_ok=False)
snapshot = {}
for path in ROOT.rglob('*'):
    if not path.is_file() or any(x in path.parts for x in ('.git','__pycache__','.pytest_cache')) or path.is_relative_to(OUT):
        continue
    name = path.relative_to(ROOT).as_posix()
    if 'v41' in path.name or name == 'configs/v4_model_usage.json' or name.endswith('/model_usage.py'):
        continue  # New revision source is not misidentified as an old artifact.
    snapshot[name] = hashlib.sha256(path.read_bytes()).hexdigest()
value = {'utc': dt.datetime.now(dt.timezone.utc).isoformat(), 'python':sys.executable,
         'python_version':platform.python_version(), 'architecture':platform.machine(),
         'branch': subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip(),
         'commit': subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
         'git_status': subprocess.check_output(['git','status','--short'],cwd=ROOT,text=True),
         'sha256':snapshot,'full_gmmnlse_attempts':0,'matlab_processes':0}
(OUT/'start_snapshot.json').write_text(json.dumps(value,indent=2)+'\n')
entry = {'category':'engineering','label':'exclusive_snapshot','status':'completed',
         'charged_s':time.monotonic()-started,'command':[sys.executable,str(Path(__file__).resolve())],
         'full_gmmnlse_calls':0,'matlab_processes':0}
(OUT/'budget_ledger.json').write_text(json.dumps({'caps_s':{'engineering':300.,'ml':900.},'attempts':[entry]},indent=2)+'\n')
print(json.dumps({'files_frozen':len(snapshot),'branch':value['branch'],'elapsed_s':entry['charged_s']},indent=2))
