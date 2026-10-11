"""V4.2 fixed-data representation comparison and conditional once-only evaluation.

Reuses the frozen model factory, metrics, X-only sampler, Evaluation database
and process budget tools. This module never reads generator internals.
"""
from __future__ import annotations
import csv
import datetime as dt
import json
import os
from pathlib import Path
import platform
import shutil
import time
import warnings

import joblib
import numpy as np
import sklearn
from threadpoolctl import threadpool_limits

from .v4_roles import ROOT, PACKAGE, FEATURES, TARGETS, SOURCE, BACKEND, sha
from .v4_ml import (matrices, predictions_csv, write, protocol as metric_protocol,
                    joint_log_calibration, prediction_intervals, intervals_with_units)
from .v41_experiment import constraint_statistics
from .v41_sampling import GROUPS, QUOTAS, SEEDS, canonical_id, sample_role, write_role
from .v42_data import load_data, input_manifest, inherited_registry, guard_holdout_isolation
from .v42_models import (candidate_specs, make_model, inspect_model, count_statistics,
                         development_gate, select_candidates, compare_alpha_feature_matrices)

OUT=ROOT/'reports/local/accuracy_v4_2_001'
PREVIOUS=ROOT/'reports/local/accuracy_v4_1_001'
CONFIG=ROOT/'configs/accuracy_v4_2_protocol.json'
SPECIAL=('slice','near_slice','outer_faces','corners')
REFERENCE=('historical_core','expanded_proposal')
LIMITS={'physical_state':'undetermined','numerical_validation':'not_verified',
        'eligible_as_validated_training_truth':False}


def now():return dt.datetime.now(dt.timezone.utc).isoformat()


def versions():
    return {'python':platform.python_version(),'numpy':np.__version__,
            'sklearn':sklearn.__version__,'joblib':joblib.__version__}


def sources():
    names=['src/mamyshev_ml/v42_experiment.py','src/mamyshev_ml/v42_models.py',
           'src/mamyshev_ml/v42_data.py','src/mamyshev_ml/v42_release.py',
           'scripts/run_v42.py','scripts/run_v4_budget.py','src/mamyshev_ml/v41_sampling.py',
           'src/mamyshev_ml/v41_experiment.py','src/mamyshev_ml/v4_roles.py',
           'src/mamyshev_ml/v4_ml.py','src/mamyshev_ml/v4_evaluators.py',
           'src/mamyshev_ml/v4_store.py','src/mamyshev_ml/model_usage.py',
           'mamyshev_accuracy_v4/reference/models_v4.py','mamyshev_accuracy_v4/reference/metrics_v4.py']
    return {name:sha(ROOT/name) for name in names}


def exclusive_json(path,value):
    with Path(path).open('x') as stream:stream.write(json.dumps(value,indent=2,allow_nan=False)+'\n')


def freeze():
    if (OUT/'protocol.json').exists() or CONFIG.exists():raise FileExistsError('No protocol refreeze')
    data=load_data(); guard_holdout_isolation()
    folder=OUT/'data';folder.mkdir(exist_ok=False)
    for name in ('T1','T2'):
        exclusive_json(folder/(name+'_training_ids.json'),[r['design_id'] for r in data[name]])
    hashes=input_manifest()
    hashes.update({str((folder/(name+'_training_ids.json')).relative_to(ROOT)):sha(folder/(name+'_training_ids.json')) for name in ('T1','T2')})
    old=json.loads((PREVIOUS/'protocol.json').read_text())
    p={'protocol_id':'accuracy_v4_2_representation_001','frozen_utc':now(),
       'hypothesis':'Only n_knots and Ridge alpha varied after V4.1; not preregistered from project inception',
       'features':FEATURES,'targets':TARGETS,'source_kind':SOURCE,'backend_id':BACKEND,
       'data_hashes':hashes,'sources':sources(),'data_metadata':data['metadata'],
       'matrix':candidate_specs(),'base_parameters':old['hyperparameters'],
       'training_sets':{'T1':'V4.1 B1 exact saved1024 ordered IDs','T2':'V4.1 B2 exact saved1024 ordered IDs'},
       'new_training_labels':0,'new_development_labels':0,'max_new_candidate_fits':10,
       'reference_validation_n':1024,'development_special_n':512,
       'old_test_challenge_scoring':False,'metrics_protocol':metric_protocol(),
       'gate':'Reference overall each>=95%, joint>=90%; core/expanded each>=90%; each special each>=95%, joint>=90%; integer counts determine thresholds',
       'selection':'All12 slots terminal; numerical failures excluded. Min equal-six-group mean target tolerance-normalized RMSE among gate passers. Within1e-12 of minimum: fewerknots, higheralpha, T1.',
       'equal_groups':[*REFERENCE,*SPECIAL],'no_pass':'selected=null; no holdout; diagnostic model only; stop',
       'role_quotas':QUOTAS,'sampling_seeds':SEEDS,'max_sampling_proposals_per_group':100000,
       'authorized_new_roles':['calibration','test'],'max_new_unique_oracle_designs':3072,
       'oracle_seed':0,'calibration_method':'existing joint_max_absolute_log_residual',
       'calibration_alpha':.05,'calibration_rank':974,
       'calibration_test_weights':{'reference_core':.25,'reference_expanded':.25,**{g:.125 for g in SPECIAL}},
       'evaluation_models':['only_frozen_selected'],'evaluation_attempts':1,'no_refit_after_selection':True,
       'baseline_equivalence':{'atol':1e-10,'rtol':1e-10},'runtime_versions':versions(),
       'budget':{'engineering_s':300,'ml_s':900,'threads':2,'MATLAB_starts':0,'GMMNLSE_attempts':0},
       'oracle_hashes':{name:sha(PACKAGE/name) for name in ('reference/oracle.py','configs/generator_recipe.json','configs/domain.json')},
       'deployment_replaced':False,**LIMITS}
    exclusive_json(CONFIG,p);exclusive_json(OUT/'protocol.json',p)
    return {'protocol_sha256':sha(OUT/'protocol.json'),'data_metadata':data['metadata'],'new_labels':0}


def load_protocol():
    p=json.loads((OUT/'protocol.json').read_text())
    if sha(CONFIG)!=sha(OUT/'protocol.json'):raise ValueError('Shared/local protocol mismatch')
    for key in ('sources','data_hashes'):
        for name,digest in p[key].items():
            if sha(ROOT/name)!=digest:raise ValueError('Frozen '+key+' changed: '+name)
    for name,digest in p['oracle_hashes'].items():
        if sha(PACKAGE/name)!=digest:raise ValueError('Frozen oracle/domain changed')
    if versions()!=p['runtime_versions']:raise ValueError('Runtime versions changed')
    return p


def group_metrics(rows,y,pred,groups):
    tags=np.array([r.get('group',r.get('region')) for r in rows])
    return {g:count_statistics(y[tags==g],pred[tags==g]) for g in groups}


def baseline_check(path,rows,y,pred,p):
    with Path(path).open() as stream:saved=list(csv.DictReader(stream))
    if [r['design_id'] for r in rows]!=[r['design_id'] for r in saved]:raise ValueError('Baseline ordered row IDs changed')
    x0=np.array([[float(r[k]) for k in FEATURES] for r in saved])
    y0=np.array([[float(r[k+'_truth']) for k in TARGETS] for r in saved])
    previous=np.array([[float(r[k+'_prediction']) for k in TARGETS] for r in saved])
    np.testing.assert_array_equal(x0,np.array([[r[k] for k in FEATURES] for r in rows]))
    np.testing.assert_array_equal(y0,y)
    if not np.isfinite(previous).all() or not np.isfinite(pred).all():raise ValueError('Nonfinite baseline')
    np.testing.assert_allclose(pred,previous,**p['baseline_equivalence'])
    return {'n':len(rows),'max_abs_difference':float(abs(pred-previous).max()),'passed':True,
            'saved_predictions_sha256':sha(path),**p['baseline_equivalence']}


def base_summary(**extra):
    return {'pipeline_completed':False,'development_accuracy_target_met':False,'accuracy_target_met':False,
            'calibration_status':'not_run','test_status':'not_run','selected':None,
            'deployment_replaced':False,'MATLAB_starts':0,'GMMNLSE_attempts':0,'BO_runs':0,
            'new_training_labels':0,'new_development_labels':0,'new_calibration_labels':0,'new_test_labels':0,
            'training_labels_per_candidate':1024,'training_union_unique':1536,
            'old_reference_validation_labels':1024,'old_special_development_labels':512,
            'old_test_challenge_scoring_rows':0,**LIMITS,**extra}


def compare():
    p=load_protocol();folder=OUT/'development';folder.mkdir(exist_ok=False)
    data=load_data();domain=json.loads((PACKAGE/'configs/domain.json').read_text())['bounds']
    old_selection=json.loads((PREVIOUS/'development/selection.json').read_text())
    old_models={r['name']:r for r in old_selection['candidates']}
    reference,dev=data['reference'],data['dev'];xv,yv=matrices(reference);xd,yd=matrices(dev)
    records=[];feature_checks={};fit_count=0;started=time.monotonic()
    write(OUT/'summary.json',base_summary(status='running',missing_reason='matrix_in_progress'))
    with threadpool_limits(limits=2):
        for spec in p['matrix']:
            slot=folder/spec['slot_id'];slot.mkdir(exist_ok=False)
            record={**spec,'status':'running','numeric_valid':False,'gate':{'passed':False},'started_utc':now()}
            records.append(record);write(folder/'comparison.json',records)
            rows=data[spec['training_set']];x,y=matrices(rows)
            fit_s=0.;warnings_seen=[];slot_start=time.monotonic()
            try:
                with warnings.catch_warnings(record=True) as captured:
                    warnings.simplefilter('always')
                    if spec['reused']:
                        old=old_models[spec['reused']];path=ROOT/old['model_path']
                        if sha(path)!=old['model_sha256']:raise ValueError('Reused model identity mismatch')
                        model=joblib.load(path)
                    else:
                        model=make_model(spec,p['base_parameters'],domain)
                        fit_count+=1
                        record['fit_attempted']=True;write(folder/'comparison.json',records)
                        fit_start=time.monotonic();model.fit(x,y);fit_s=time.monotonic()-fit_start
                        path=slot/'model.joblib';joblib.dump(model,path,compress=3)
                    pred_start=time.monotonic()
                    pt,pv,pd=model.predict(x),model.predict(xv),model.predict(xd)
                    prediction_s=time.monotonic()-pred_start
                    if not all(np.isfinite(a).all() and (a>0).all() for a in (pt,pv,pd)):
                        raise FloatingPointError('Nonfinite/nonpositive predictions retained as failed, never clipped')
                    inspection=inspect_model(model,x)
                    actual_parameters=dict(model.parameters)
                    intended={**p['base_parameters'],'n_knots':spec['n_knots'],'alpha':spec['alpha']}
                    if actual_parameters!=intended:raise ValueError('Candidate parameters differ from registered matrix')
                    check_key=(spec['training_set'],spec['n_knots'])
                    # inspect_model exposes deterministic fitted-transform signatures.
                    signature=inspection['feature_signature']
                    if check_key in feature_checks and feature_checks[check_key]!=signature:
                        raise ValueError('Same training X/knots produced different transforms across alpha')
                    feature_checks[check_key]=signature
                    reuse_checks=None
                    if spec['reused']:
                        base=PREVIOUS/'development'/spec['reused']
                        reuse_checks={'reference':baseline_check(base/'reference_validation_predictions.csv',reference,yv,pv,p),
                                      'dev':baseline_check(base/'new_dev_predictions.csv',dev,yd,pd,p)}
                    restored=joblib.load(path)
                    np.testing.assert_array_equal(pv,restored.predict(xv))
                    np.testing.assert_array_equal(pd,restored.predict(xd))
                    training=count_statistics(y,pt);ref=count_statistics(yv,pv)
                    rg=group_metrics(reference,yv,pv,REFERENCE);sg=group_metrics(dev,yd,pd,SPECIAL)
                    tg=group_metrics(rows,y,pt,[*REFERENCE,*GROUPS])
                    gate=development_gate(ref,rg,sg)
                    score=float(np.mean([rg[g]['mean_tolerance_normalized_rmse'] for g in REFERENCE]
                                         +[sg[g]['mean_tolerance_normalized_rmse'] for g in SPECIAL]))
                    record.update(status='completed',numeric_valid=True,gate=gate,parameters=actual_parameters,
                        training=training,training_groups=tg,reference=ref,reference_groups=rg,new_dev_groups=sg,
                        equal_group_normalized_rmse=score,model_path=str(path.relative_to(ROOT)),model_sha256=sha(path),
                        training_ids_path=str((OUT/'data'/(spec['training_set']+'_training_ids.json')).relative_to(ROOT)),
                        fit_count=int(not spec['reused']),fit_s=fit_s,prediction_s=prediction_s,
                        inspection_path=str((slot/'inspection.json').relative_to(ROOT)),reuse_checks=reuse_checks,
                        reload_max_abs_difference=0.)
                    write(slot/'inspection.json',inspection)
                    predictions_csv(slot/'training_predictions.csv',rows,y,pt)
                    predictions_csv(slot/'reference_predictions.csv',reference,yv,pv)
                    predictions_csv(slot/'dev_predictions.csv',dev,yd,pd)
                warnings_seen=[str(w.message) for w in captured]
            except (ArithmeticError,np.linalg.LinAlgError) as error:
                record.update(status='numerical_failed',error=repr(error),numeric_valid=False,
                              equal_group_normalized_rmse=None,fit_s=fit_s)
                warnings_seen=[str(w.message) for w in captured]
            except BaseException as error:
                record.update(status='blocked',error=repr(error),elapsed_s=time.monotonic()-slot_start)
                write(slot/'result.json',record);write(folder/'comparison.json',records)
                write(OUT/'summary.json',base_summary(status='partial',missing_reason=repr(error),new_candidate_fit_attempts=fit_count))
                raise
            record.update(warnings=warnings_seen,ended_utc=now(),elapsed_s=time.monotonic()-slot_start)
            write(slot/'result.json',record);write(folder/'comparison.json',records)
            print(json.dumps({'slot':spec['slot_id'],'status':record['status'],'gate':record['gate'],
                              'score':record.get('equal_group_normalized_rmse'),'elapsed_s':record['elapsed_s']}),flush=True)
    feature_pairs=compare_alpha_feature_matrices([
        {'slot_id':r['slot_id'],'inspection':json.loads((ROOT/r['inspection_path']).read_text())}
        if r.get('inspection_path') else {'slot_id':r['slot_id']} for r in records])
    write(folder/'feature_pairs.json',feature_pairs)
    decision=select_candidates(records,expected=12)
    selection={**decision,'frozen':True,'protocol_sha256':sha(OUT/'protocol.json'),'sources':p['sources'],
               'data_hashes':p['data_hashes'],'runtime_versions':versions(),'frozen_utc':now(),
               'new_candidate_fit_attempts':fit_count,'reused_candidates':2,'completed_slots':len(records),
               'elapsed_s':time.monotonic()-started,'deployment_replaced':False,'candidates':records}
    if selection.get('selected'):
        selected=next(r for r in records if r['slot_id']==selection['selected'])
        selection.update(selected_model_path=selected['model_path'],model_sha256=selected['model_sha256'],
                         training_ids_path=selected['training_ids_path'],parameters=selected['parameters'])
    exclusive_json(OUT/'selection.json',selection)
    write(OUT/'summary.json',base_summary(status='development_finished',pipeline_completed=True,
          development_accuracy_target_met=bool(selection.get('selected')),selected=selection.get('selected'),
          best_diagnostic=selection.get('best_diagnostic'),matrix_slots=len(records),new_candidate_fit_attempts=fit_count,
          reused_candidates=2,missing_reason='conditional_evaluation_pending' if selection.get('selected') else 'no_development_candidate_passed'))
    return selection


def verify_selected():
    p=load_protocol();s=json.loads((OUT/'selection.json').read_text())
    if not s.get('frozen') or not s.get('selected'):
        raise PermissionError('No passing frozen selection; holdout remains unopened')
    if len(s.get('candidates',[]))!=12 or s['protocol_sha256']!=sha(OUT/'protocol.json'):
        raise ValueError('Incomplete or changed selection')
    fresh=select_candidates(s['candidates'],expected=12)
    if fresh.get('selected')!=s['selected']:raise ValueError('Selection ranking/gate mismatch')
    if sha(ROOT/s['selected_model_path'])!=s['model_sha256']:raise ValueError('Selected weights changed')
    if s['sources']!=p['sources'] or s['data_hashes']!=p['data_hashes']:raise ValueError('Freeze mismatch')
    return p,s


def query_holdout(role,registry,p):
    if role not in ('calibration','test'):raise PermissionError('V4.2 authorizes zero new training/dev labels')
    _,selection=verify_selected();guard_holdout_isolation()
    if not (OUT/'final_evaluation.lock').is_file():raise PermissionError('Final evaluation must be reserved first')
    if role=='test' and not (OUT/'evaluation/calibration.json').is_file():raise PermissionError('Calibration must finish first')
    rows,collisions=sample_role(role,p['sampling_seeds'][role],registry,p)
    # Check available known experimental IDs before the first label, including
    # the entire selected planned X panel, without any look at unqueried Y.
    from .v42_data import ensure_unseen_holdout_designs
    isolation=ensure_unseen_holdout_designs(rows)
    folder=OUT/'samples'/role;write_role(rows,collisions,folder)
    exclusive_json(folder/'isolation_check.json',isolation)
    from .v4_evaluators import SyntheticEvaluator
    from .v4_store import V4Store
    evaluator=SyntheticEvaluator(seed=0);db=V4Store(folder/'evaluations.sqlite')
    ledger=OUT/'oracle_queries.jsonl'
    events=[json.loads(line) for line in ledger.read_text().splitlines()] if ledger.exists() else []
    seen={e['design_id'] for e in events if e['event']=='reserved'}
    if len(seen)+len(rows)>3072:raise RuntimeError('New conditional evaluation budget exceeded')
    labeled=[];start=time.monotonic()
    def event(value):
        with ledger.open('a') as stream:
            stream.write(json.dumps(value,allow_nan=False)+'\n');stream.flush();os.fsync(stream.fileno())
    try:
        for row in rows:
            design={k:row[k] for k in FEATURES};did=row['design_id']
            if did in seen or canonical_id(design)!=did:raise ValueError('Duplicate/mismatched design')
            event({'event':'reserved','role':role,'design_id':did,'utc':now()});seen.add(did)
            record=evaluator.evaluate(design,design_id=did,request_id='v42/'+role+'/'+did)
            if record['job_status']!='completed' or record['cache_hit'] or record['source_kind']!=SOURCE:
                raise ValueError('Expected new successful synthetic evaluation')
            db.save_evaluation(record)
            labeled.append(dict(row,**record['targets'],region=row['group'],source_kind=SOURCE))
            event({'event':'completed','role':role,'design_id':did,'evaluation_id':record['evaluation_id'],'utc':now()})
    except BaseException as error:
        exclusive_json(folder/'error.json',{'error':repr(error),'completed':len(labeled),'reserved':len(seen),'retry_authorized':False})
        raise
    finally:db.close()
    with (folder/'labels.csv').open('x',newline='') as stream:
        w=csv.DictWriter(stream,fieldnames=list(labeled[0]));w.writeheader();w.writerows(labeled)
    write(folder/'accounting.json',{'role':role,'new_labels':len(labeled),'oracle_calls':evaluator.calls,
          'unique_computations':evaluator.unique_computations,'cache_hits':evaluator.cache_hits,
          'elapsed_s':time.monotonic()-start,'identity':evaluator.identity})
    return labeled


def evaluate():
    p,s=verify_selected();guard_holdout_isolation()
    exclusive_json(OUT/'final_evaluation.lock',{'selected':s['selected'],'sha256':s['model_sha256'],'utc':now()})
    folder=OUT/'evaluation';folder.mkdir(exist_ok=False)
    registry,inheritance=inherited_registry(expected_manifest=p['data_hashes'])
    exclusive_json(OUT/'inherited_exclusions.json',inheritance)
    start=time.monotonic();model=joblib.load(ROOT/s['selected_model_path'])
    with threadpool_limits(limits=2):
        cal_rows=query_holdout('calibration',registry,p);xc,yc=matrices(cal_rows);pc=model.predict(xc)
        calibration=joint_log_calibration(yc,pc,.05)
        if calibration['rank']!=974:raise ValueError('Unexpected calibration rank')
        calibration.update(model_sha256=s['model_sha256'],selected=s['selected'])
        exclusive_json(folder/'calibration.json',calibration)
        predictions_csv(folder/'calibration_predictions.csv',cal_rows,yc,pc)
        rows=query_holdout('test',registry,p);x,y=matrices(rows);pred=model.predict(x)
        tags=np.array([r['group'] for r in rows]);reference=np.isin(tags,['reference_core','reference_expanded'])
        groups=group_metrics(rows,y,pred,GROUPS);overall=count_statistics(y,pred)
        reference_metrics=count_statistics(y[reference],pred[reference])
        gate=development_gate(reference_metrics,{'historical_core':groups['reference_core'],
             'expanded_proposal':groups['reference_expanded']},{g:groups[g] for g in SPECIAL})
        lower,upper=prediction_intervals(pred,calibration)
        predictions_csv(folder/'test_predictions.csv',rows,y,pred,lower,upper)
        metrics={'selected':s['selected'],'model_sha256':s['model_sha256'],'gate':gate,
                 'metrics':overall,'groups':groups,'reference':reference_metrics,
                 'intervals':intervals_with_units(y,pred,calibration),'constraints':constraint_statistics(y,pred,calibration),
                 'group_intervals':{g:intervals_with_units(y[tags==g],pred[tags==g],calibration) for g in GROUPS},
                 'group_constraints':{g:constraint_statistics(y[tags==g],pred[tags==g],calibration) for g in GROUPS},
                 'distribution_weights':p['calibration_test_weights'],
                 'scope':'Empirical fixed-stratum synthetic evaluation; no per-input/group95% or real-solver guarantee'}
        exclusive_json(folder/'final_metrics.json',metrics)
        _,s_check=verify_selected()
        if s_check!=s:raise ValueError('Selection changed during evaluation')
    summary=base_summary(pipeline_completed=True,development_accuracy_target_met=True,
        accuracy_target_met=gate['passed'],selected=s['selected'],calibration_status='completed',test_status='completed',
        new_calibration_labels=1024,new_test_labels=2048,new_unique_oracle_labels=3072,
        new_candidate_fit_attempts=s['new_candidate_fit_attempts'],reused_candidates=2,matrix_slots=12,
        final_evaluation_attempts=1,model_unchanged_after_calibration=True,
        evaluation_elapsed_s=time.monotonic()-start,missing_reason=None,
        scope='Only the predefined stratified synthetic distribution; release candidate awaiting review')
    write(OUT/'summary.json',summary)
    # No old full exclusion mapping copy; only newly added IDs and a reference.
    exclusive_json(OUT/'holdout_sampling_summary.json',{'inherited':inheritance,'roles':registry.sampled_roles,
        'new_calibration_test_designs':3072,'mutually_disjoint':True})
    create_release(p,s)
    return summary


def create_release(p,s):
    folder=OUT/'release';folder.mkdir(exist_ok=False)
    model=folder/'model.joblib';shutil.copy2(ROOT/s['selected_model_path'],model)
    manifest={'schema_version':'mamyshev_v42_release_v1','frozen':True,'release_id':'v42_'+s['selected'],
        'selected':s['selected'],'development_accuracy_target_met':True,'deployment_replaced':False,
        'model_path':str(model.relative_to(ROOT)),'model_sha256':s['model_sha256'],
        'protocol_path':str((OUT/'protocol.json').relative_to(ROOT)),'protocol_sha256':sha(OUT/'protocol.json'),
        'training_ids_path':s['training_ids_path'],'training_ids_sha256':sha(ROOT/s['training_ids_path']),
        'data_hashes':p['data_hashes'],'source_hashes':p['sources'],'features':FEATURES,'targets':TARGETS,
        'units':dict(zip(TARGETS,('nJ','fs','MW'))),'input_units':dict(zip(FEATURES,('W','nm','nm','m'))),
        'n_train':1024,'source_kind':SOURCE,'backend_id':BACKEND,'model_family':'spline_interactions',
        'parameters':s['parameters'],'evaluation_summary_path':str((OUT/'summary.json').relative_to(ROOT)),
        'evaluation_summary_sha256':sha(OUT/'summary.json'),'final_metrics_path':str((OUT/'evaluation/final_metrics.json').relative_to(ROOT)),
        'final_metrics_sha256':sha(OUT/'evaluation/final_metrics.json')}
    exclusive_json(folder/'selection.json',manifest)
    from .v42_release import load_release_evaluator
    evaluator=load_release_evaluator(model,folder/'selection.json')
    with (OUT/'evaluation/test_predictions.csv').open() as stream:row=next(csv.DictReader(stream))
    design={k:float(row[k]) for k in FEATURES};prediction=evaluator.evaluate(design)
    np.testing.assert_allclose([prediction['targets'][k] for k in TARGETS],
        [float(row[k+'_prediction']) for k in TARGETS],atol=1e-10,rtol=1e-10)
    exclusive_json(folder/'reload_prediction_check.json',{'passed':True,'source':'Saved first already-scored test row; no new labels/fits',
        'atol':1e-10,'rtol':1e-10,'Prediction':prediction})


def run_evaluation_safely():
    try:return evaluate()
    except BaseException as error:
        # Preserve partial raw evidence. No synthetic success/final is invented.
        exclusive_json(OUT/'evaluation_error.json',{'error':repr(error),'utc':now(),'retry_authorized':False})
        summary=json.loads((OUT/'summary.json').read_text())
        summary.update(pipeline_completed=False,evaluation_error=repr(error),status='evaluation_failed_no_retry')
        if (OUT/'evaluation/calibration.json').exists():summary['calibration_status']='completed'
        else:summary['calibration_status']='failed_or_not_completed'
        if not (OUT/'evaluation/final_metrics.json').exists():
            summary.update(test_status='failed_or_not_completed',accuracy_target_met=False)
        write(OUT/'summary.json',summary)
        raise
