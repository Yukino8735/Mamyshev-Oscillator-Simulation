#!/usr/bin/env python3
"""Read-only preservation and actual-label accounting; no prediction or fitting."""
import json
from pathlib import Path
import sqlite3
import subprocess
from mamyshev_ml.v42_experiment import ROOT,OUT,sha,load_protocol

p=load_protocol();snap=json.loads((OUT/'start_snapshot.json').read_text())
allowed={'scripts/run_v4_budget.py','docs/SCOPE.md','docs/EXECUTION_STATUS.md'}
changed={};same=[];missing=[]
for name,before in snap['sha256'].items():
    path=ROOT/name
    if not path.is_file():missing.append(name);continue
    after=sha(path)
    if before!=after:changed[name]={'before':before,'after':after}
    else:same.append(name)
selection=json.loads((OUT/'selection.json').read_text());summary=json.loads((OUT/'summary.json').read_text())
events=[json.loads(line) for line in (OUT/'oracle_queries.jsonl').read_text().splitlines()] if (OUT/'oracle_queries.jsonl').exists() else []
reserved=[e for e in events if e['event']=='reserved'];completed=[e for e in events if e['event']=='completed']
counts={role:sum(e['role']==role for e in completed) for role in ('train','dev','calibration','test')}
badqueries=len(reserved)!=len({e['design_id'] for e in reserved}) or {e['design_id'] for e in reserved}!={e['design_id'] for e in completed}
if counts['train'] or counts['dev'] or len(reserved)>3072:badqueries=True
db_counts={}
for role in ('calibration','test'):
    path=OUT/'samples'/role/'evaluations.sqlite'
    if path.exists():
        with sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True) as db:
            db_counts[role]={'evaluations':db.execute('SELECT count(*) FROM evaluations').fetchone()[0],
                             'predictions':db.execute('SELECT count(*) FROM predictions').fetchone()[0],
                             'sources':db.execute('SELECT distinct source FROM evaluations').fetchall()}
old=[name for name in snap['sha256'] if name.startswith(('reports/local/','mamyshev_accuracy_v4/'))]
history_ok=all(name in same for name in old)
branch=subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip()
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
diff=subprocess.run(['git','diff','--check'],cwd=ROOT,capture_output=True,text=True)
release=None
if (OUT/'release/selection.json').exists():
    from mamyshev_ml.v42_release import verify_release
    manifest=verify_release(OUT/'release/model.joblib',OUT/'release/selection.json')
    release={'verified':True,'selected':manifest['selected'],'model_sha256':manifest['model_sha256']}
absent_old=not (ROOT/'reports/local/phase2/observation_validation_001/observation_001/final_result.json').exists()
result={'old_files_checked':len(snap['sha256']),'unchanged_count':len(same),'changed':changed,'missing':missing,
    'unexpected_changed':sorted(set(changed)-allowed),'historical_artifact_files_hashed':len(old),
    'historical_artifacts_unchanged':history_ok,'code_all_unchanged':all(name in same for name in snap['sha256'] if name.startswith('code/')),
    'branch':branch,'commit':commit,'branch_commit_preserved':branch==snap['branch'] and commit==snap['commit'],
    'query_counts':counts,'unique_reserved':len({e['design_id'] for e in reserved}),'completed_events':len(completed),
    'query_accounting_consistent':not badqueries,'databases':db_counts,'release':release,
    'matrix_slots':len(selection['candidates']),'new_actual_candidate_fits':selection['new_candidate_fit_attempts'],
    'old_baseline_slots_reused':selection['reused_candidates'],'summary':summary,
    'historical_observation_final_still_absent':absent_old,
    'git_diff_check_exit':diff.returncode,'git_diff_check_output':diff.stdout+diff.stderr,
    'batch_bytes_at_check':sum(path.stat().st_size for path in OUT.rglob('*') if path.is_file())}
result['passed']=not missing and not result['unexpected_changed'] and history_ok and result['code_all_unchanged'] and result['branch_commit_preserved'] and not badqueries and absent_old and diff.returncode==0
with (OUT/'preservation_check.json').open('x') as stream:stream.write(json.dumps(result,indent=2)+'\n')
commands=[{k:a.get(k) for k in ('category','label','command')} for a in json.loads((OUT/'budget_ledger.json').read_text())['attempts']]
with (OUT/'commands.json').open('x') as stream:stream.write(json.dumps(commands,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ('summary','changed')},indent=2))
if not result['passed']:raise SystemExit(1)
