#!/usr/bin/env python3
"""Exclusive closeout reservation and old-file identities, no scientific calls."""
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
OUT=ROOT/'reports/local/mvp_closeout_001'
OUT.mkdir(exist_ok=False)
new_docs={'docs/USER_GUIDE_ZH.md','docs/ATTRIBUTION_REVIEW.md','docs/CLAIM_EVIDENCE.md','docs/MVP_CLOSEOUT_REPORT.md'}
snapshot={}
for path in ROOT.rglob('*'):
    if not path.is_file() or path.is_relative_to(OUT) or any(p in path.parts for p in ('.git','__pycache__','.pytest_cache')):continue
    relative=path.relative_to(ROOT).as_posix()
    if 'closeout' in path.name or path.name in ('export_mvp_evidence.py','build_mvp_inference_bundle.py') or relative in new_docs:continue
    snapshot[relative]=hashlib.sha256(path.read_bytes()).hexdigest()
review=json.loads((ROOT/'mamyshev_accuracy_v4/V4_3_UPLOAD_REVIEW.json').read_text())
locations={'FROZEN_MODEL_APPLICATION_V4_3_REPORT.md':'docs/FROZEN_MODEL_APPLICATION_V4_3_REPORT.md',
    'candidate_results.csv':'reports/local/application_v4_3_001/candidates/candidate_results.csv',
    'matlab_requests.json':'reports/local/application_v4_3_001/candidates/requests/matlab_requests.json',
    'model.joblib':'reports/local/accuracy_v4_2_001/release/model.joblib'}
checks={name:snapshot[locations[name]]==r['sha256'] and (ROOT/locations[name]).stat().st_size==r['bytes']
        for name,r in review['input_assets'].items()}
data={'utc':dt.datetime.now(dt.timezone.utc).isoformat(),'python':sys.executable,'version':platform.python_version(),
    'architecture':platform.machine(),'branch':subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip(),
    'commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
    'git_status':subprocess.check_output(['git','status','--short'],cwd=ROOT,text=True),'sha256':snapshot,
    'upload_review_checks':checks,'MATLAB_starts':0,'new_oracle_queries':0}
(OUT/'start_snapshot.json').write_text(json.dumps(data,indent=2)+'\n')
entry={'category':'engineering','label':'exclusive_snapshot','status':'completed' if all(checks.values()) else 'failed',
    'charged_s':time.monotonic()-started,'command':[sys.executable,str(Path(__file__).resolve())],
    'full_gmmnlse_calls':0,'matlab_processes':0}
(OUT/'budget_ledger.json').write_text(json.dumps({'caps_s':{'engineering':300.},'attempts':[entry]},indent=2)+'\n')
print(json.dumps({'old_files_hashed':len(snapshot),'upload_review_checks':checks,'entry':entry},indent=2))
if not all(checks.values()):raise SystemExit('Review identity mismatch; reservation retained')
