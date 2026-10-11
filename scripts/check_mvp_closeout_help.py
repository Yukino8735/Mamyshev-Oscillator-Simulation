#!/usr/bin/env python3
"""Read CLI help only, through the shared bounded closeout monitor."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports/local/mvp_closeout_001/help'
COMMANDS=[['scripts/v43_scan.py','predict','--help'],['scripts/v43_scan.py','run','--help'],
          ['scripts/v4_scan.py','run','--help'],['scripts/v4_scan.py','waveform','--help'],
          ['scripts/run_v4_ml.py','select','--help'],['scripts/run_v4_search.py','--help']]

def main():
    OUT.mkdir()
    records=[]
    for index,args in enumerate(COMMANDS):
        started=time.monotonic()
        result=subprocess.run([sys.executable,*args],cwd=ROOT,env=os.environ.copy(),capture_output=True,text=True,timeout=8)
        record={'command':[sys.executable,*args],'exit_code':result.returncode,'elapsed_s':time.monotonic()-started,'operation':'help_only'}
        records.append(record)
        (OUT/f'{index}.stdout.log').write_text(result.stdout)
        (OUT/f'{index}.stderr.log').write_text(result.stderr)
        (OUT/'results.json').write_text(json.dumps(records,indent=2)+'\n')
        if result.returncode:raise SystemExit(result.returncode)
    print(json.dumps({'help_commands':len(records),'all_exit_zero':True,'MATLAB_starts':0,'labels':0,'fits':0}))

if __name__=='__main__':main()
