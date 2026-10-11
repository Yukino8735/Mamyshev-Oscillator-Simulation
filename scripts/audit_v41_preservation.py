#!/usr/bin/env python3
"""End-of-batch read-only hash/data-role audit; no fitting, predictions or oracle."""
import csv
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
from mamyshev_ml.v41_experiment import ROOT, OUT, load_protocol

load_protocol()
snapshot=json.loads((OUT/'start_snapshot.json').read_text())
allowed={'scripts/run_v4_budget.py','src/mamyshev_ml/v4_evaluators.py','docs/SCOPE.md','docs/EXECUTION_STATUS.md'}
changed={};missing=[];same=[]
for name,before in snapshot['sha256'].items():
    path=ROOT/name
    if not path.is_file():missing.append(name);continue
    after=hashlib.sha256(path.read_bytes()).hexdigest()
    if after!=before:changed[name]={'before':before,'after':after}
    else:same.append(name)
events=[json.loads(s) for s in (OUT/'oracle_queries.jsonl').read_text().splitlines()]
reserved=[e['design_id'] for e in events if e['event']=='reserved']
completed=[e['design_id'] for e in events if e['event']=='completed']
if len(reserved)!=len(set(reserved)) or set(reserved)!=set(completed):raise ValueError('Repeated/uncompleted oracle reservation')
role_ids={};databases={}
for role in ('train','dev'):
    with (OUT/'samples'/role/'inputs.csv').open() as stream:role_ids[role]={r['design_id'] for r in csv.DictReader(stream)}
    path=OUT/'samples'/role/'evaluations.sqlite'
    with sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True) as db:
        databases[role]={'evaluations':db.execute('select count(*) from evaluations').fetchone()[0],
                         'predictions':db.execute('select count(*) from predictions').fetchone()[0],
                         'sources':db.execute('select distinct source from evaluations').fetchall()}
prior=set()
with (OUT/'exclusions_before/exclusions.jsonl').open() as stream:
    for line in stream:prior.add(json.loads(line)['canonical_id'])
cross=len(role_ids['train']&role_ids['dev']);old_cross=len(set.union(*role_ids.values())&prior)
absent=[name for name in ('samples/calibration','samples/test','evaluation','final_evaluation.lock') if not (OUT/name).exists()]
old_missing_final=ROOT/'reports/local/phase2/observation_validation_001/observation_001/final_result.json'
branch=subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip()
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
diff=subprocess.run(['git','diff','--check'],cwd=ROOT,capture_output=True,text=True)
newfiles=sorted(p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file()
    and not p.is_relative_to(OUT) and not any(x in p.parts for x in ('.git','__pycache__','.pytest_cache'))
    and p.relative_to(ROOT).as_posix() not in snapshot['sha256'])
historical=[p for p in snapshot['sha256'] if p.startswith(('reports/local/accuracy_v4_001/','mamyshev_accuracy_v4/','reports/local/phase'))]
result={'old_files_checked':len(snapshot['sha256']),'unchanged_count':len(same),'changed':changed,'missing':missing,
        'unapproved_changes':sorted(set(changed)-allowed),'new_files_outside_local_evidence':newfiles,
        'historical_files_checked':len(historical),'historical_all_unchanged':all(p in same for p in historical),
        'physical_numerical_code_all_unchanged':all(p in same for p in snapshot['sha256'] if p.startswith('code/')),
        'frozen_protocol_and_source_checks_passed':True,'branch':branch,'commit':commit,
        'branch_commit_preserved':branch==snapshot['branch'] and commit==snapshot['commit'],
        'queries_reserved':len(reserved),'queries_completed':len(completed),'per_role_database':databases,
        'train_dev_collisions':cross,'new_old_canonical_collisions':old_cross,'holdout_artifacts_absent':absent,
        'historical_observation_final_still_absent':not old_missing_final.exists(),
        'git_diff_check_exit':diff.returncode,'git_diff_check_output':diff.stdout+diff.stderr,
        'new_batch_artifact_bytes_at_check':sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file())}
result['passed']=not missing and not result['unapproved_changes'] and result['historical_all_unchanged'] and result['physical_numerical_code_all_unchanged'] and result['branch_commit_preserved'] and not cross and not old_cross and len(absent)==4 and not old_missing_final.exists() and diff.returncode==0
with (OUT/'preservation_check.json').open('x') as stream:stream.write(json.dumps(result,indent=2)+'\n')
commands=[{k:a.get(k) for k in ('category','label','command')} for a in json.loads((OUT/'budget_ledger.json').read_text())['attempts']]
(OUT/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
print(json.dumps(result,indent=2))
if not result['passed']:raise SystemExit(1)
