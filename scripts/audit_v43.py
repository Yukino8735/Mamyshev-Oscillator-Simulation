#!/usr/bin/env python3
"""Preservation and persisted-event accounting only; no model prediction or labels."""
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from mamyshev_ml.v42_release import verify_release

OUT = ROOT/'reports/local/application_v4_3_001'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
read = lambda p: json.loads(Path(p).read_text())
snapshot = read(OUT/'start_snapshot.json')
allowed = {'src/mamyshev_ml/v4_scan.py','docs/EXECUTION_STATUS.md','docs/SCOPE.md'}
changed = {}; same=[]; missing=[]
for relative,before in snapshot['sha256'].items():
    path=ROOT/relative
    if not path.is_file(): missing.append(relative); continue
    after=sha(path)
    if before==after: same.append(relative)
    else: changed[relative]={'before':before,'after':after}
history=[r for r in snapshot['sha256'] if r.startswith(('reports/local/','mamyshev_accuracy_v4/'))]
model=ROOT/'reports/local/accuracy_v4_2_001/release/model.joblib'
release=verify_release(model,model.with_name('selection.json'))
demo=read(OUT/'demonstration/summary.json')
candidate=read(OUT/'candidates/candidate_summary.json')
plan=read(OUT/'candidates/frozen_candidate_plan.json')
queries=[json.loads(line) for line in (OUT/'candidates/oracle_queries.jsonl').read_text().splitlines()]
reserved=[r for r in queries if r['event']=='reserved']
terminal=[r for r in queries if r['event'] in ('completed','failed')]
events=[json.loads(line) for line in (OUT/'candidates/events.jsonl').read_text().splitlines()]
with sqlite3.connect((OUT/'candidates/candidate_verification.sqlite').resolve().as_uri()+'?mode=ro',uri=True) as db:
    db_counts={t:db.execute('SELECT COUNT(*) FROM '+t).fetchone()[0] for t in ('evaluations','predictions')}
planned={(s['id'],m,i,did) for s in plan['scenarios'] for m in ('model','random')
         for i,did in enumerate(plan['choices'][s['id']][m],1)}
actual={(e['scenario_id'],e['method'],e['method_index'],e['design_id']) for e in events}
query_ok=(len(reserved)<=64 and len(terminal)==len(reserved)==len(events)==candidate['logical_queries']
    and len({r['request_id'] for r in reserved})==len(reserved) and actual==planned
    and all(r['role']=='candidate_verification' for r in queries)
    and db_counts['evaluations']==candidate['unique_oracle_computations'])
requests=read(OUT/'candidates/requests/matlab_requests.json')
request_ok=(requests['max_new_real_attempts']==0 and all(r['status']=='pending_manual_approval'
    and r['real_targets'] is None and r['max_new_real_attempts']==0 for r in requests['requests']))
for s in plan['scenarios']:
    request_ok &= sum(r['scenario_id']==s['id'] for r in requests['requests'])<=3
branch=subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip()
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
diff=subprocess.run(['git','diff','--check'],cwd=ROOT,capture_output=True,text=True)
result={'old_files_checked':len(snapshot['sha256']),'unchanged_count':len(same),'changed':changed,
    'missing':missing,'unexpected_changes':sorted(set(changed)-allowed),
    'historical_artifact_count':len(history),'historical_artifacts_unchanged':all(p in same for p in history),
    'production_physics_unchanged':all(p in same for p in snapshot['sha256'] if p.startswith('code/')),
    'old_budget_unchanged':'scripts/run_v4_budget.py' in same,
    'release_verified':True,'model_sha256':release['model_sha256'],
    'branch_commit_preserved':branch==snapshot['branch'] and commit==snapshot['commit'],
    'query_accounting_consistent':query_ok,'query_events_reserved':len(reserved),'unique_queried_designs':len({e['design_id'] for e in events}),
    'candidate_database':db_counts,'zero_real_requests_checked':bool(request_ok),
    'git_diff_check_exit':diff.returncode,'git_diff_check_output':diff.stdout+diff.stderr,
    'batch_bytes_at_check':sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file())}
result['application_source_hashes']={str(p.relative_to(ROOT)):sha(p)
    for pattern in ('src/mamyshev_ml/v43_*.py','scripts/*v43*.py','tests/test_v43_*.py')
    for p in sorted(ROOT.glob(pattern))}
result['application_source_hashes']['src/mamyshev_ml/v4_scan.py']=sha(ROOT/'src/mamyshev_ml/v4_scan.py')
result['passed']=not missing and not result['unexpected_changes'] and all(result[k] for k in
    ('historical_artifacts_unchanged','production_physics_unchanged','old_budget_unchanged','release_verified',
     'branch_commit_preserved','query_accounting_consistent','zero_real_requests_checked')) and diff.returncode==0
summary={'pipeline_completed':result['passed'] and demo['completed'] and candidate['pipeline_completed'],
    'candidate_goal_improved':candidate['candidate_goal_improved'],'deployment_replaced':False,
    'new_training_labels':0,'new_development_labels':0,'new_calibration_labels':0,'new_test_labels':0,
    'new_fits':0,'recalibration_runs':0,'BO_runs':0,'MATLAB_starts':0,'GMMNLSE_attempts':0,
    'candidate_verification_logical_queries':candidate['logical_queries'],
    'new_unique_candidate_designs':candidate['unique_oracle_computations'],
    'candidate_cache_hits':candidate['cache_hits'],'candidate_failures':candidate['failed_queries'],
    'new_prediction_rows':demo['prediction_rows']+candidate['prediction_rows'],
    'scan_prediction_rows':demo['scan_prediction_rows'],'requests_exported':candidate['requests_exported'],
    'physical_state':'undetermined','numerical_validation':'not_verified','eligible_as_validated_training_truth':False,
    'phase2':'in_progress','deep_physical_validation':'deferred','intervals':'limited',
    'no_new_random_test_accuracy_claim':True,'model_sha256':release['model_sha256']}
for name,value in (('preservation_check.json',result),('summary.json',summary)):
    with (OUT/name).open('x') as stream: stream.write(json.dumps(value,indent=2)+'\n')
commands={'python_invocation':'/opt/homebrew/Caskroom/miniforge/base/bin/conda run -n mamyshev-ml --no-capture-output python',
    'budget_jobs':[{k:a.get(k) for k in ('category','label','command')} for a in read(OUT/'budget_ledger.json')['attempts']],
    'actual_scan_cli_commands':[json.loads(line) for line in (OUT/'demonstration/commands.jsonl').read_text().splitlines()]}
with (OUT/'commands.json').open('x') as stream: stream.write(json.dumps(commands,indent=2)+'\n')
print(json.dumps(result,indent=2))
print(json.dumps(summary,indent=2))
if not result['passed']: raise SystemExit(1)
