"""One bounded V4.1 coverage comparison; original V4 evidence stays read-only.

Only train/dev are queried before selection. No generator internals are used by
the model. The existing Evaluation adapter is the sole source of new labels.
"""
from __future__ import annotations
import csv
import datetime as dt
import json
import os
from pathlib import Path
import time
import warnings

import joblib
import numpy as np
from threadpoolctl import threadpool_limits

from .v4_ml import (LogSurrogate, matrices, metrics, predictions_csv, write,
                    protocol as v4_protocol, joint_log_calibration,
                    prediction_intervals, intervals_with_units, wilson)
from .v4_roles import ROOT, PACKAGE, FEATURES, TARGETS, SOURCE, ReleaseData, sha, verify_frozen
from .v41_sampling import (SEEDS, QUOTAS, GROUPS, build_exclusions, sample_role,
                          write_role, canonical_id)

OUT = ROOT / 'reports/local/accuracy_v4_1_001'
OLD = ROOT / 'reports/local/accuracy_v4_001'
CONFIG = ROOT / 'configs/accuracy_v4_1_protocol.json'
SPECIAL = GROUPS[:4]


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def source_hashes():
    names = ['src/mamyshev_ml/v41_experiment.py', 'src/mamyshev_ml/v41_sampling.py',
             'src/mamyshev_ml/v4_evaluators.py', 'src/mamyshev_ml/v4_store.py',
             'src/mamyshev_ml/model_usage.py', 'scripts/run_v41.py', 'scripts/run_v4_budget.py',
             'src/mamyshev_ml/v4_ml.py', 'src/mamyshev_ml/v4_roles.py',
             'mamyshev_accuracy_v4/reference/models_v4.py', 'mamyshev_accuracy_v4/reference/metrics_v4.py']
    return {name: sha(ROOT / name) for name in names}


def freeze(diagnosis_path):
    """Freeze all sampling and stopping rules before any query or new fit."""
    if CONFIG.exists() or (OUT / 'protocol.json').exists():
        raise FileExistsError('Protocol already reserved; do not refreeze after observing labels')
    diagnosis = json.loads(Path(diagnosis_path).read_text())
    # Caller must name the completed diagnostics, retained with its exact hash.
    if diagnosis.get('development_may_proceed') is not True or diagnosis.get('confirmed_wiring_issue') is not False:
        raise ValueError('Successful diagnostics with no confirmed wiring defect required; otherwise review before development')
    selection = verify_frozen(OLD / 'models/model.joblib', OLD / 'models/selection.json')
    order_ids = json.loads((PACKAGE / 'data/training_orders.json').read_text())['orders']['11']
    if selection['training_ids'] != order_ids[:512] or selection['n_train'] != 512:
        raise ValueError('B0 actual training IDs do not equal the required nested order11 prefix')
    p = {'protocol_id': 'targeted_accuracy_v4_1_001', 'frozen_utc': now(),
         'diagnosis_path': str(Path(diagnosis_path).relative_to(ROOT)), 'diagnosis_sha256': sha(diagnosis_path),
         'source_kind': SOURCE, 'features': FEATURES, 'targets': TARGETS,
         'models': {'B0': {'n': 512, 'fit': False, 'model_sha256': selection['model_sha256']},
                    'B1': {'n': 1024, 'fit': True, 'training': 'V4 order11 first1024'},
                    'B2': {'n': 1024, 'fit': True, 'training': 'V4 order11 first512 plus new train512'}},
         'family': selection['model_family'], 'hyperparameters': selection['parameters'],
         'order': 11, 'role_quotas': QUOTAS, 'sampling_seeds': SEEDS,
         'max_sampling_proposals_per_group': 100000, 'max_new_unique_oracle_designs': 4096,
         'oracle_seed': 0, 'metrics_protocol': v4_protocol(),
         'geometry': 'V4 geometry; X-only independent role/group SHA256-seeded streams; continuous coordinates 6 decimals, length integer tenths; endpoint faces balanced over 8 faces; 16 corner neighborhoods, outer5%; expanded excludes core',
         'exclusions': 'All available old labeled X, legacy canonical IDs, anchors, queried search X and candidate20k; every new role mutually disjoint by canonical X-derived ID',
         'development_gate': {'reference_all_each': .95, 'reference_all_joint': .90,
                              'reference_core_expanded_each': .90, 'special_each': .95, 'special_joint': .90},
         'selection_rule': 'Only ALL gates pass; smallest n; equal n lowest equal-six-group mean target tolerance-normalized RMSE; deterministic B0/B1/B2 tie order',
         'tie_groups_equal_weights': ['historical_core', 'expanded_proposal', *SPECIAL],
         'no_pass_action': 'Save best diagnostic candidate; no calibration/test queries, no extra fits or samples',
         'calibration': {'method': 'existing joint max absolute log residual', 'alpha': .05, 'fit_changes': False},
         'final_evaluation_models': ['frozen_selected', 'B0'], 'final_evaluation_attempts': 1,
         'calibration_test_weights': {'reference_core': .25, 'reference_expanded': .25,
                                      **{g: .125 for g in SPECIAL}},
         'final_gate': 'Same reference/special development thresholds; no tuning after failure',
         'prediction_checks': {'atol': 1e-10, 'rtol': 1e-10},
         'budget': {'engineering_s': 300, 'ml_s': 900, 'threads': 2, 'MATLAB_starts': 0, 'GMMNLSE_attempts': 0},
         'sources': source_hashes(), 'unchanged_package_hashes': {name: sha(PACKAGE / name) for name in
           ['reference/oracle.py', 'configs/generator_recipe.json', 'configs/domain.json', 'configs/accuracy_protocol.json', 'data/training_orders.json']},
         'old_selection_sha256': sha(OLD / 'models/selection.json'),
         'B0_training_ids_match_order11_first512': True,
         'scientific_limits': {'physical_state': 'undetermined', 'numerical_validation': 'not_verified',
                               'eligible_as_validated_training_truth': False}}
    text = json.dumps(p, indent=2, allow_nan=False) + '\n'
    # Exclusive files: no alternate protocol or replacing an existing reservation.
    with CONFIG.open('x') as stream: stream.write(text)
    with (OUT / 'protocol.json').open('x') as stream: stream.write(text)
    return p


def load_protocol():
    p = json.loads((OUT / 'protocol.json').read_text())
    if sha(CONFIG) != sha(OUT / 'protocol.json'):
        raise ValueError('Shared/local frozen protocols differ')
    for name, digest in p['sources'].items():
        if sha(ROOT / name) != digest: raise ValueError('Frozen source changed: ' + name)
    for name, digest in p['unchanged_package_hashes'].items():
        if sha(PACKAGE / name) != digest: raise ValueError('Frozen package changed: ' + name)
    if sha(OLD / 'models/selection.json') != p['old_selection_sha256']:
        raise ValueError('Old selection changed')
    verify_frozen(OLD / 'models/model.joblib', OLD / 'models/selection.json')
    return p


def statistics(y, prediction, p):
    value = metrics(y, prediction, p['metrics_protocol'])
    for j, name in enumerate(TARGETS):
        residual = prediction[:, j] - y[:, j]
        relative = residual / np.maximum(abs(y[:, j]), 1e-12)
        t = p['metrics_protocol']['tolerances'][name]
        r = abs(residual) / np.maximum(t['absolute'], t['relative'] * abs(y[:, j]))
        q = lambda a: dict(zip(['P50', 'P90', 'P95', 'max'], map(float, [*np.quantile(a, [.5, .9, .95]), np.max(a)])))
        value['targets'][name].update(signed_mean=float(residual.mean()), signed_relative_mean=float(relative.mean()),
             signed_error_quantiles=q(residual), signed_relative_quantiles=q(relative),
             absolute_error_quantiles=q(abs(residual)), absolute_relative_quantiles=q(abs(relative)),
             normalized_error_quantiles=q(r), overprediction_count=int((residual > 0).sum()),
             underprediction_count=int((residual < 0).sum()))
    return value


def grouped_stats(rows, y, prediction, p):
    groups = np.array([r.get('group', r.get('region')) for r in rows])
    return {g: statistics(y[groups == g], prediction[groups == g], p) for g in sorted(set(groups))}


def rate_gate(value, each, joint=None):
    return all(t['pass_rate'] >= each for t in value['targets'].values()) and (joint is None or value['joint_pass_rate'] >= joint)


def development_gate(reference, reference_groups, special_groups):
    checks = {'reference_all': rate_gate(reference, .95, .90)}
    for g in ['historical_core', 'expanded_proposal']:
        checks['reference_' + g] = g in reference_groups and rate_gate(reference_groups[g], .90)
    for g in SPECIAL:
        checks[g] = g in special_groups and rate_gate(special_groups[g], .95, .90)
    return {'passed': all(checks.values()), 'checks': checks}


def choose_candidate(candidates):
    passing = [v for v in candidates if v['gate']['passed']]
    best = min(candidates, key=lambda v: (v['equal_group_normalized_rmse'], v['name']))
    selected = min(passing, key=lambda v: (v['n'], v['equal_group_normalized_rmse'], v['name'])) if passing else None
    return selected, best


def append_event(path, value):
    with Path(path).open('a') as stream:
        stream.write(json.dumps(value, allow_nan=False) + '\n'); stream.flush(); os.fsync(stream.fileno())


def query_role(role, registry, p):
    """Append-before-query reservations count failures; no overwrite or retries."""
    if role in ('calibration', 'test'):
        verify_selected()
    folder = OUT / 'samples' / role
    if folder.exists(): raise FileExistsError('Role already attempted; no overwrite or repeat query')
    rows, collisions = sample_role(role, p['sampling_seeds'][role], registry, p)
    write_role(rows, collisions, folder)
    from .v4_evaluators import SyntheticEvaluator
    from .v4_store import V4Store
    evaluator = SyntheticEvaluator(seed=p['oracle_seed'])
    ledger = OUT / 'oracle_queries.jsonl'
    existing = [json.loads(line) for line in ledger.read_text().splitlines()] if ledger.exists() else []
    reserved = {e['design_id'] for e in existing if e['event'] == 'reserved'}
    if len(reserved) + len(rows) > p['max_new_unique_oracle_designs']:
        raise RuntimeError('New oracle budget exceeded')
    db = V4Store(folder / 'evaluations.sqlite')
    labeled = []
    started = time.monotonic()
    try:
        for row in rows:
            did = row['design_id']; design = {k: row[k] for k in FEATURES}
            if did in reserved or canonical_id(design) != did: raise ValueError('Repeated/mismatched oracle design')
            append_event(ledger, {'event': 'reserved', 'role': role, 'design_id': did, 'utc': now()})
            reserved.add(did)
            record = evaluator.evaluate(design, design_id=did, request_id=f'v41/{role}/{did}')
            if record['job_status'] != 'completed' or record['cache_hit'] or record['source_kind'] != SOURCE:
                raise ValueError('New role requires a fresh successful synthetic Evaluation')
            db.save_evaluation(record)
            labeled.append(dict(row, **record['targets'], source_kind=SOURCE, region=row['group']))
            append_event(ledger, {'event': 'completed', 'role': role, 'design_id': did,
                                 'evaluation_id': record['evaluation_id'], 'utc': now()})
    finally:
        db.close()
    columns = list(labeled[0])
    with (folder / 'labels.csv').open('x', newline='') as stream:
        w = csv.DictWriter(stream, fieldnames=columns); w.writeheader(); w.writerows(labeled)
    write(folder / 'accounting.json', {'role': role, 'new_labels': len(labeled), 'oracle_calls': evaluator.calls,
          'unique_computations': evaluator.unique_computations, 'cache_hits': evaluator.cache_hits,
          'elapsed_s': time.monotonic()-started, 'identity': evaluator.identity})
    return labeled


def develop():
    p = load_protocol(); folder = OUT / 'development'; folder.mkdir(exist_ok=False)
    started = time.monotonic()
    registry, exclusion_summary = build_exclusions()
    registry.save(OUT / 'exclusions_before')
    write(folder / 'exclusion_summary.json', exclusion_summary)
    train_new = query_role('train', registry, p)
    dev = query_role('dev', registry, p)
    registry.save(OUT / 'exclusions_after_development')
    loader = ReleaseData(log_path=folder / 'old_data_access.jsonl')
    orders = json.loads((PACKAGE / 'data/training_orders.json').read_text())['orders']['11']
    train_old = loader.read('train', source_kind=SOURCE, ids=orders[:1024])
    validation = loader.read('validation', source_kind=SOURCE)
    xv, yv = matrices(validation); xd, yd = matrices(dev)
    domain = json.loads((PACKAGE / 'configs/domain.json').read_text())['bounds']
    records = []; modelpaths = {}
    with threadpool_limits(limits=2):
        for name, rows in [('B0', train_old[:512]), ('B1', train_old), ('B2', train_old[:512]+train_new)]:
            target = folder / name; target.mkdir()
            if set(r['design_id'] for r in rows) & set(r['design_id'] for r in validation+dev):
                raise ValueError('Training/evaluation role collision')
            write(target / 'training_ids.json', [r['design_id'] for r in rows])
            fit_start = time.monotonic()
            with warnings.catch_warnings(record=True) as captured:
                warnings.simplefilter('always')
                if name == 'B0':
                    modelpath = OLD / 'models/model.joblib'; model = joblib.load(modelpath); fit_s = 0.
                else:
                    x, y = matrices(rows)
                    model = LogSurrogate(p['family'], domain, p['hyperparameters'], 11).fit(x, y)
                    fit_s = time.monotonic()-fit_start
                    modelpath = target / 'model.joblib'; joblib.dump(model, modelpath, compress=3)
                pv, pd = model.predict(xv), model.predict(xd)
                restored = joblib.load(modelpath)
                np.testing.assert_array_equal(pv, restored.predict(xv))
                np.testing.assert_array_equal(pd, restored.predict(xd))
            if not np.isfinite(pv).all() or not np.isfinite(pd).all(): raise ValueError('Nonfinite predictions')
            reference = statistics(yv, pv, p)
            rg, sg = grouped_stats(validation, yv, pv, p), grouped_stats(dev, yd, pd, p)
            gate = development_gate(reference, rg, sg)
            score = float(np.mean([rg[g]['mean_tolerance_normalized_rmse'] for g in ['historical_core', 'expanded_proposal']]
                          + [sg[g]['mean_tolerance_normalized_rmse'] for g in SPECIAL]))
            result = {'name': name, 'n': len(rows), 'fit_count': int(name != 'B0'), 'fit_s': fit_s,
                      'reference': reference, 'reference_groups': rg, 'new_dev_groups': sg, 'gate': gate,
                      'equal_group_normalized_rmse': score, 'model_path': str(modelpath.relative_to(ROOT)),
                      'model_sha256': sha(modelpath), 'reload_max_abs_difference': 0.,
                      'warnings': [str(w.message) for w in captured]}
            records.append(result); modelpaths[name] = modelpath
            write(target / 'metrics.json', result)
            predictions_csv(target / 'reference_validation_predictions.csv', validation, yv, pv)
            predictions_csv(target / 'new_dev_predictions.csv', dev, yd, pd)
            write(folder / 'comparison.json', records)
            print(json.dumps({'candidate': name, 'gate': gate, 'score': score, 'fit_s': fit_s}), flush=True)
    selected, best = choose_candidate(records)
    selection = {'frozen': True, 'selected': selected['name'] if selected else None,
         'development_accuracy_target_met': selected is not None, 'best_diagnostic_candidate': best['name'],
         'best_diagnostic_model_path': best['model_path'], 'candidates': records,
         'protocol_sha256': sha(OUT / 'protocol.json'), 'sources': source_hashes(), 'frozen_utc': now(),
         'old_unique_train_labels_used': len(train_old), 'old_validation_labels_used': len(validation),
         'new_train_labels': len(train_new), 'new_dev_labels': len(dev), 'fit_count': 2,
         'elapsed_s': time.monotonic()-started, 'new_holdout_opened': False,
         'stop_reason': 'selected_frozen_for_once_evaluation' if selected else 'development_gates_not_met_no_holdout',
         'accuracy_target_met': False, 'physical_state': 'undetermined', 'numerical_validation': 'not_verified',
         'eligible_as_validated_training_truth': False}
    write(folder / 'selection.json', selection)
    return selection


def verify_selected():
    p = load_protocol()
    s = json.loads((OUT / 'development/selection.json').read_text())
    if not s.get('frozen') or not s.get('development_accuracy_target_met') or not s.get('selected'):
        raise PermissionError('New calibration/test blocked: no candidate passed all development gates')
    if s['protocol_sha256'] != sha(OUT / 'protocol.json') or s['sources'] != source_hashes():
        raise ValueError('Selection identity changed')
    item = next(c for c in s['candidates'] if c['name'] == s['selected'])
    if not item['gate']['passed'] or sha(ROOT / item['model_path']) != item['model_sha256']:
        raise ValueError('Selected candidate identity or gate mismatch')
    return p, s, item


def constraint_statistics(y, pred, cal):
    lower, upper = prediction_intervals(pred, cal)
    result = {}
    for name, truth, point, conservative, uncertain in [
        ('duration_le40_fs', y[:,1] <= 40, pred[:,1] <= 40, upper[:,1] <= 40, (lower[:,1] <= 40)&(upper[:,1]>40)),
        ('energy_ge100_nJ', y[:,0] >= 100, pred[:,0] >= 100, lower[:,0] >= 100, (lower[:,0]<100)&(upper[:,0]>=100))]:
        item = {'n': len(y), 'actual_feasible': int(truth.sum()), 'uncertain_count': int(uncertain.sum()), 'small_group': len(y)<50}
        for kind, proposed in [('point',point), ('interval_screen', conservative)]:
            tp, count, actual = int((truth&proposed).sum()), int(proposed.sum()), int(truth.sum())
            item[kind] = {'selected': count, 'true_feasible': tp, 'false_feasible': int((proposed&~truth).sum()),
                          'precision': tp/count if count else None, 'recall': tp/actual if actual else None,
                          'precision_wilson95': wilson(tp,count), 'recall_wilson95': wilson(tp,actual),
                          'undefined_reason': 'No selected / no actual-feasible cases respectively' if not count or not actual else None,
                          'uncertain_abstentions': int((~proposed&uncertain).sum())}
        result[name] = item
    return result


def evaluate():
    p, selection, item = verify_selected()
    folder = OUT / 'evaluation'; folder.mkdir(exist_ok=False)
    with (OUT / 'final_evaluation.lock').open('x') as stream:
        stream.write(json.dumps({'selected': item['name'], 'sha256': item['model_sha256'], 'utc': now()})+'\n')
    registry, _ = build_exclusions()
    # Restore only already-generated X to exclude across roles; no development labels reopened.
    for role in ('train', 'dev'):
        with (OUT / 'samples' / role / 'inputs.csv').open() as stream:
            for row in csv.DictReader(stream):
                registry.add({k:float(row[k]) for k in FEATURES}, original_id=row['design_id'], source=f'v41/{role}', reason='new_role_'+role)
    cal_rows = query_role('calibration', registry, p)
    xc, yc = matrices(cal_rows)
    models = {'selected': joblib.load(ROOT / item['model_path']), 'B0': joblib.load(OLD / 'models/model.joblib')}
    calibrations = {}
    with threadpool_limits(limits=2):
        for name, model in models.items():
            pc = model.predict(xc); cal = joint_log_calibration(yc, pc, .05)
            calibrations[name] = cal
            write(folder / (name+'_calibration.json'), cal)
            predictions_csv(folder / (name+'_calibration_predictions.csv'), cal_rows, yc, pc)
        rows = query_role('test', registry, p)
        registry.save(OUT / 'exclusions_after_evaluation')
        x, y = matrices(rows); groups = np.array([r['group'] for r in rows]); results = {}
        for name, model in models.items():
            pred = model.predict(x); cal = calibrations[name]; lo, hi = prediction_intervals(pred, cal)
            stats = statistics(y, pred, p); gs = grouped_stats(rows,y,pred,p)
            reference = np.isin(groups,['reference_core','reference_expanded'])
            gate = development_gate(statistics(y[reference], pred[reference], p),
                {'historical_core':gs['reference_core'],'expanded_proposal':gs['reference_expanded']}, gs)
            results[name] = {'metrics':stats, 'groups':gs, 'gate':gate,
                'intervals':intervals_with_units(y,pred,cal), 'constraints':constraint_statistics(y,pred,cal),
                'group_intervals':{g:intervals_with_units(y[groups==g],pred[groups==g],cal) for g in gs},
                'group_constraints':{g:constraint_statistics(y[groups==g],pred[groups==g],cal) for g in gs}}
            predictions_csv(folder / (name+'_test_predictions.csv'),rows,y,pred,lo,hi)
        verify_selected()
    write(folder / 'final_metrics.json', results)
    summary = {'pipeline_completed':True, 'accuracy_target_met':results['selected']['gate']['passed'],
               'model':item['name'], 'new_calibration_labels':len(cal_rows), 'new_test_labels':len(rows),
               'new_unique_oracle_labels_total':4096, 'final_evaluation_attempts':1,
               'weights_unchanged':True, 'scope':'Fixed stratified synthetic evaluation; empirical coverage only',
               **p['scientific_limits']}
    write(folder / 'summary.json', summary)
    return summary
