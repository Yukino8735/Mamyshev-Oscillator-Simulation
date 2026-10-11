#!/usr/bin/env python3
"""Exclusive bounded demo/10k task snapshot; no labels or scientific calls."""
import datetime as dt
import hashlib
import importlib.metadata as meta
import json
from pathlib import Path
import platform
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports/local/demo_10k_release_001'
CAPS={'engineering':600.,'ml':900.,'matlab':180.}

def main():
    started=time.monotonic();OUT.mkdir(exist_ok=False)
    snapshot={}
    for path in ROOT.rglob('*'):
        if not path.is_file() or path.is_relative_to(OUT) or any(p in path.parts for p in ('.git','__pycache__','.pytest_cache')):continue
        relative=path.relative_to(ROOT).as_posix()
        if 'demo10k' in path.name or relative.startswith(('demo/','docs/DEMO_10K','docs/GIT_RELEASE_PLAN')):continue
        snapshot[relative]={'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'bytes':path.stat().st_size}
    review=json.loads((ROOT/'mamyshev_accuracy_v4/DOCUMENT_REVIEW.json').read_text())
    checks={}
    for name,expected in review['documents'].items():
        path=name if name=='README.md' else 'docs/'+name
        checks[name]=snapshot[path]==expected
    frozen={name:snapshot[name] for name in snapshot if name.startswith(('reports/local/mvp_closeout_001/inference_bundle','reports/local/accuracy_v4_2_001/release/','reports/local/accuracy_v4_2_001/evaluation/calibration'))}
    versions={}
    for name in ('numpy','scipy','scikit-learn','matplotlib','joblib','threadpoolctl','streamlit'):
        try:versions[name]=meta.version(name)
        except meta.PackageNotFoundError:versions[name]=None
    git=lambda *a:subprocess.check_output(['git',*a],cwd=ROOT)
    data={'utc':dt.datetime.now(dt.timezone.utc).isoformat(),'python':sys.executable,'version':platform.python_version(),'architecture':platform.machine(),
        'branch':git('branch','--show-current').decode().strip(),'commit':git('rev-parse','HEAD').decode().strip(),
        'git_status':git('status','--short').decode(),'staged_diff_sha256':hashlib.sha256(git('diff','--cached','--binary')).hexdigest(),
        'files':snapshot,'document_review_checks':checks,'frozen_assets':frozen,'dependencies':versions}
    (OUT/'start_snapshot.json').write_text(json.dumps(data,indent=2)+'\n')
    (OUT/'numerical_constraints.txt').write_text(''.join(f'{name}=={version}\n' for name,version in versions.items() if name!='streamlit' and version))
    entry={'category':'engineering','label':'exclusive_snapshot','status':'completed','charged_s':time.monotonic()-started,'command':[sys.executable,__file__]}
    (OUT/'budget_ledger.json').write_text(json.dumps({'caps_s':CAPS,'attempts':[entry]},indent=2)+'\n')
    print(json.dumps({'snapshot_files':len(snapshot),'review_checks':checks,'dependencies':versions,'entry':entry},indent=2))
    if snapshot['reports/local/accuracy_v4_2_001/release/model.joblib']['sha256']!='c236c2d2dd6cb5b59e32bd5ab4f8c3823f7fefc10d7571108a3d6339ee46b2e0':raise SystemExit('Old model mismatch')

if __name__=='__main__':main()
