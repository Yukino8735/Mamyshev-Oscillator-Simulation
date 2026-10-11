#!/usr/bin/env python3
"""User-authorized optional UI dependency, with frozen numerical constraints."""
import importlib.metadata as meta
import json
from pathlib import Path
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports/local/demo_10k_release_001/ui_dependency'
NAMES=('numpy','scipy','scikit-learn','matplotlib','joblib','threadpoolctl')

def main():
    OUT.mkdir()
    before={name:meta.version(name) for name in NAMES}
    args=[sys.executable,'-m','pip','install','--disable-pip-version-check','--constraint',str(OUT.parent/'numerical_constraints.txt'),'streamlit>=1.45,<2']
    records=[]
    for label,extra in [('resolve',['--dry-run','--report',str(OUT/'resolution.json')]),('install',['--report',str(OUT/'installed.json')])]:
        started=time.monotonic()
        result=subprocess.run(args+extra,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=100)
        (OUT/f'{label}.log').write_text(result.stdout)
        records.append({'command':args+extra,'exit_code':result.returncode,'elapsed_s':time.monotonic()-started})
        (OUT/'commands.json').write_text(json.dumps(records,indent=2)+'\n')
        if result.returncode:raise SystemExit(result.returncode)
        resolved=json.loads((OUT/('resolution.json' if label=='resolve' else 'installed.json')).read_text())
        for item in resolved['install']:
            name=item['metadata']['name'].lower()
            if name in before and item['metadata']['version']!=before[name]:raise RuntimeError('Frozen numerical dependency conflict')
    after={name:meta.version(name) for name in NAMES}
    if before!=after:raise RuntimeError('Numerical dependency changed')
    (OUT/'result.json').write_text(json.dumps({'before':before,'after':after,'numerical_versions_unchanged':True,'streamlit':meta.version('streamlit'),'commands':records},indent=2)+'\n')
    print(json.dumps({'streamlit':meta.version('streamlit'),'numerical_versions_unchanged':True}))

if __name__=='__main__':main()
