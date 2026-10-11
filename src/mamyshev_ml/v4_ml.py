"""Accuracy-first local selection and once-only frozen evaluation; no oracle import."""
from __future__ import annotations
import csv
import datetime as dt
import json
from pathlib import Path
import platform
import sys
import time
import warnings

import joblib
import numpy as np
import sklearn
from threadpoolctl import threadpool_limits

from .v4_roles import ROOT, PACKAGE, FEATURES, TARGETS, SOURCE, ReleaseData, sha, verify_frozen

# Reuse the supplied, byte-preserved model/metric implementation. Neither imports oracle.
sys.path.insert(0, str(PACKAGE / 'reference'))
from models_v4 import LogSurrogate
from metrics_v4 import report, accuracy_gate, joint_log_calibration, prediction_intervals, interval_report, wilson


def write(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')
    temporary.replace(path)


def matrices(rows):
    x = np.array([[r[k] for k in FEATURES] for r in rows], float)
    y = np.array([[r[k] for k in TARGETS] for r in rows], float)
    return x, y


def metrics(y, prediction, protocol):
    result = report(y, prediction, protocol)
    result['small_group'] = len(y) < protocol['small_group_minimum']
    result['relative_error_is_fraction_not_percent'] = True
    for j, (target, value) in enumerate(result['targets'].items()):
        # Exact constant truth can have a nonzero sum of centered squares from
        # floating mean rounding (e.g. repeated 1.1); R2 remains undefined.
        if np.ptp(np.asarray(y)[:, j]) == 0:
            value['r2'] = None
        value['r2_missing_reason'] = 'Constant truth; R2 is undefined.' if value['r2'] is None else ''
        value['unit'] = {'compressed_energy_nJ': 'nJ', 'compressed_duration_fs': 'fs', 'compressed_peak_power_MW': 'MW'}[target]
    return result


def grouped(rows, y, prediction, protocol):
    region = np.array([r['region'] for r in rows])
    return {g: metrics(y[region == g], prediction[region == g], protocol) for g in sorted(set(region))}


def predictions_csv(path, rows, y, prediction, lower=None, upper=None):
    with Path(path).open('x', newline='') as stream:
        writer = csv.writer(stream)
        header = ['design_id', 'region', *FEATURES]
        if y is not None:
            header += [k + '_truth' for k in TARGETS]
        header += [k + '_prediction' for k in TARGETS]
        if lower is not None:
            header += [k + '_lower' for k in TARGETS] + [k + '_upper' for k in TARGETS]
        writer.writerow(header)
        for i, row in enumerate(rows):
            values = [row['design_id'], row.get('region', row.get('candidate_group', 'unlabeled')), *[row[k] for k in FEATURES]]
            if y is not None:
                values += y[i].tolist()
            values += prediction[i].tolist()
            if lower is not None:
                values += lower[i].tolist() + upper[i].tolist()
            writer.writerow(values)


def protocol():
    return json.loads((PACKAGE / 'configs/accuracy_protocol.json').read_text())


def learning_sources():
    names = ['src/mamyshev_ml/v4_ml.py', 'src/mamyshev_ml/v4_roles.py', 'scripts/run_v4_ml.py',
             'mamyshev_accuracy_v4/reference/models_v4.py', 'mamyshev_accuracy_v4/reference/metrics_v4.py']
    return {n: sha(ROOT / n) for n in names}


def select(output, deadline_s=300.):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    start = time.monotonic()
    p = protocol()
    domain = json.loads((PACKAGE / 'configs/domain.json').read_text())['bounds']
    orders = json.loads((PACKAGE / 'data/training_orders.json').read_text())['orders']
    source_hashes = learning_sources()
    # Hashing holdout bytes is identity bookkeeping, not label access/scoring.
    split_names = ['data/development.sqlite', 'data/train_pool_4096.csv', 'data/validation_1024.csv',
                   'data/training_orders.json', 'evaluation_only/evaluation.sqlite',
                   'evaluation_only/calibration_1024.csv', 'evaluation_only/test_1536.csv',
                   'evaluation_only/challenge_512.csv', 'configs/domain.json']
    split_hashes = {n: sha(PACKAGE / n) for n in split_names}
    write(output / 'development_freeze.json', {'protocol': p, 'protocol_sha256': sha(PACKAGE / 'configs/accuracy_protocol.json'),
          'sources': source_hashes, 'split_hashes': split_hashes,
          'role_policy': 'Only development DB targets; per-prefix train labels and validation. No evaluation-only labels.',
          'families_selected_after_package_development_comparison': True,
          'versions': {'python': platform.python_version(), 'numpy': np.__version__, 'sklearn': sklearn.__version__, 'joblib': joblib.__version__},
          'threads': 2, 'started_utc': dt.datetime.now(dt.timezone.utc).isoformat()})
    loader = ReleaseData(log_path=output / 'data_access.jsonl')
    validation = loader.read('validation', source_kind=SOURCE)
    xv, yv = matrices(validation)
    results, trained, observed_ids = [], {}, set()
    prediction_count = 0

    def fit_one(family, n, order):
        nonlocal prediction_count
        if time.monotonic() - start >= deadline_s:
            raise TimeoutError('Predeclared local selection budget exhausted; no hidden larger run')
        rows = loader.read('train', source_kind=SOURCE, ids=orders[str(order)][:n])
        observed_ids.update(r['design_id'] for r in rows)
        x, y = matrices(rows)
        started = time.monotonic()
        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter('always')
            model = LogSurrogate(family, domain, p['models'][family], order).fit(x, y)
            fit_s = time.monotonic() - started
            predicted = model.predict(xv)
        prediction_count += len(xv)
        overall = metrics(yv, predicted, p)
        groups = grouped(validation, yv, predicted, p)
        item = {'family': family, 'n': n, 'order': order, 'fit_s': fit_s,
                'elapsed_s': time.monotonic() - started, 'metrics': overall, 'groups': groups,
                'accuracy_gate_passed': accuracy_gate(overall, groups, p),
                'warnings': [str(w.message) for w in captured]}
        results.append(item)
        if order == 11:
            trained[(family, n)] = (model, predicted)
        predictions_csv(output / f'validation_{family}_{n}_order{order}.csv', validation, yv, predicted)
        write(output / 'learning_curve.json', {'results': results, 'unique_train_labels_used': len(observed_ids),
                                             'prediction_count': prediction_count, 'elapsed_s': time.monotonic() - start})
        print(json.dumps({'fit': family, 'n': n, 'order': order, 'gate': item['accuracy_gate_passed'],
                          'joint': overall['joint_pass_rate'], 'elapsed_s': item['elapsed_s']}), flush=True)
        return item

    selected = None
    with threadpool_limits(limits=2):
        for n in p['training_sizes']:
            candidates = [fit_one(family, n, 11) for family in p['model_order']]
            confirmed = []
            for candidate in candidates:
                if candidate['accuracy_gate_passed']:
                    records = [candidate] + [fit_one(candidate['family'], n, order) for order in (22, 33)]
                    if all(r['accuracy_gate_passed'] for r in records):
                        confirmed.append((float(np.mean([r['metrics']['mean_tolerance_normalized_rmse'] for r in records])), candidate))
            if confirmed:
                selected = min(confirmed, key=lambda a: (a[0], p['model_order'].index(a[1]['family'])))[1]
                break
        development_passed = selected is not None
        if selected is None:
            selected = min((r for r in results if r['order'] == 11), key=lambda r: r['metrics']['mean_tolerance_normalized_rmse'])
        model, saved_prediction = trained[(selected['family'], selected['n'])]
        model_path = output / 'model.joblib'
        joblib.dump(model, model_path, compress=3)
        # Only the just-created local artifact is loaded.
        restored = joblib.load(model_path)
        reload_prediction = restored.predict(xv)
        prediction_count += len(xv)
        np.testing.assert_array_equal(saved_prediction, reload_prediction)
        design = {'pump_power_W': 4., 'filter_offset_nm': 10., 'filter2_bw_nm': 3., 'gain_length_m': 4.}
        default_prediction = restored.predict([[design[k] for k in FEATURES]])[0]
        prediction_count += 1
    selection = {'frozen': True, 'model_family': selected['family'], 'n_train': selected['n'], 'production_order': 11,
                 'parameters': p['models'][selected['family']], 'features': FEATURES, 'targets': TARGETS,
                 'feature_transform': 'Declared-domain scaling; training-X-only spline knots/scaler; log positive targets',
                 'development_accuracy_target_met': development_passed,
                 'accuracy_target_met': development_passed, 'accuracy_target_scope': 'development only until frozen final test',
                 'model_sha256': sha(model_path), 'accuracy_protocol_sha256': sha(PACKAGE / 'configs/accuracy_protocol.json'),
                 'training_source_hashes': source_hashes, 'split_hashes': split_hashes,
                 'training_ids': orders['11'][:selected['n']], 'unique_train_labels_used_in_local_selection': len(observed_ids),
                 'unique_validation_labels_used': len(validation), 'local_development_unique_label_union': len(observed_ids) + len(validation),
                 'package_prior_pilot_train_labels_seen': 4096, 'package_prior_pilot_validation_labels_seen': 1024,
                 'prediction_count_including_reload_and_default': prediction_count,
                 'fit_count': len(results), 'reload_prediction_max_abs_error': float(np.max(abs(saved_prediction - reload_prediction))),
                 'source_kind': SOURCE, 'frozen_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
                 'elapsed_s': time.monotonic() - start, 'no_calibration_test_challenge_fitting': True}
    write(output / 'selection.json', selection)
    write(output / 'default_prediction.json', {'kind': 'Prediction', 'design': design,
          'targets_prediction': dict(zip(TARGETS, default_prediction.tolist())), 'model_sha256': selection['model_sha256'],
          'oracle_evaluation': False, 'physical_state': 'undetermined', 'eligible_as_validated_training_truth': False})
    plot_learning(results, output)
    return selection


def intervals_with_units(y, prediction, calibration):
    item = interval_report(y, prediction, calibration)
    lo, hi = prediction_intervals(prediction, calibration)
    inside = (y >= lo) & (y <= hi)
    item['per_target_wilson95'] = {k: wilson(int(inside[:, j].sum()), len(y)) for j, k in enumerate(TARGETS)}
    item['width_original_units'] = {k: {'median': float(np.median(hi[:, j] - lo[:, j])),
                                             'P95': float(np.quantile(hi[:, j] - lo[:, j], .95))} for j, k in enumerate(TARGETS)}
    return item


def constraint_report(y, prediction, calibration):
    lo, hi = prediction_intervals(prediction, calibration)
    truth = y[:, 1] <= 40
    uncertain = (lo[:, 1] <= 40) & (hi[:, 1] > 40)
    result = {'actual_feasible_count': int(truth.sum()), 'n': len(y), 'uncertain_count': int(uncertain.sum()),
              'uncertain_fraction': float(uncertain.mean()), 'scope': 'Synthetic duration task; no physical class/per-candidate guarantee'}
    for name, proposed in [('point_estimate', prediction[:, 1] <= 40), ('interval_screen', hi[:, 1] <= 40)]:
        tp = int((proposed & truth).sum())
        count = int(proposed.sum())
        result[name] = {'proposed': count, 'true_feasible': tp, 'false_feasible': int((proposed & ~truth).sum()),
                        'precision': tp / count if count else None, 'recall': tp / int(truth.sum()) if truth.any() else None,
                        'precision_wilson95': wilson(tp, count), 'recall_wilson95': wilson(tp, int(truth.sum())),
                        'selected_fraction': count / len(y), 'not_selected_count': int((~proposed).sum()),
                        'uncertain_abstentions': int((~proposed & uncertain).sum())}
    return result


def reserve_final_evaluation(model_digest, selection_path, output):
    if len(model_digest) != 64 or any(c not in '0123456789abcdef' for c in model_digest):
        raise ValueError('Invalid trusted model digest')
    locks = ROOT / 'reports/local/accuracy_v4_001/evaluation_locks'
    locks.mkdir(parents=True, exist_ok=True)
    value = {'model_sha256': model_digest, 'out': str(output),
             'reserved_utc': dt.datetime.now(dt.timezone.utc).isoformat()}
    # This batch-global digest lock cannot be bypassed by copying the same
    # weights/selection into a different output/model directory.
    with (locks / (model_digest + '.json')).open('x') as lock:
        lock.write(json.dumps(value) + '\n')
    with (Path(selection_path).parent / 'final_evaluation.lock').open('x') as lock:
        lock.write(json.dumps(value) + '\n')


def final_evaluate(model_path, selection_path, output, authorized=False):
    if not authorized:
        raise PermissionError('Explicit frozen final-evaluation authorization required')
    model_path, selection_path, output = Path(model_path), Path(selection_path), Path(output)
    selection = verify_frozen(model_path, selection_path)
    reserve_final_evaluation(selection['model_sha256'], selection_path, output)
    output.mkdir(parents=True, exist_ok=False)
    write(output / 'selection_snapshot.json', selection)
    start = time.monotonic()
    p = protocol()
    model = joblib.load(model_path)
    data = ReleaseData(evaluation=True, model=model_path, selection=selection_path, log_path=output / 'data_access.jsonl')
    prediction_count = 0
    result = {}
    with threadpool_limits(limits=2):
        calibration_rows = data.read('calibration', source_kind=SOURCE)
        xc, yc = matrices(calibration_rows)
        pc = model.predict(xc)
        prediction_count += len(pc)
        calibration = joint_log_calibration(yc, pc, p['uncertainty']['alpha'])
        calibration['model_sha256'] = selection['model_sha256']
        calibration['elapsed_s'] = time.monotonic() - start
        write(output / 'calibration.json', calibration)
        predictions_csv(output / 'calibration_predictions.csv', calibration_rows, yc, pc)
        for role in ['test', 'challenge']:
            stage = time.monotonic()
            rows = data.read(role, source_kind=SOURCE)
            x, y = matrices(rows)
            predicted = model.predict(x)
            prediction_count += len(predicted)
            overall = metrics(y, predicted, p)
            groups = grouped(rows, y, predicted, p)
            lo, hi = prediction_intervals(predicted, calibration)
            value = {'metrics': overall, 'groups': groups, 'intervals': intervals_with_units(y, predicted, calibration),
                     'duration_constraint': constraint_report(y, predicted, calibration),
                     'group_intervals': {}, 'input_bins': {}, 'threshold_bands': {},
                     'source_kind': SOURCE, 'solver_generalization_error': None,
                     'solver_missing_reason': 'No independent GMMNLSE labels evaluated',
                     'physical_state': 'undetermined', 'numerical_validation': 'not_verified',
                     'eligible_as_validated_training_truth': False}
            regions = np.array([r['region'] for r in rows])
            for group in groups:
                mask = regions == group
                value['group_intervals'][group] = intervals_with_units(y[mask], predicted[mask], calibration)
            if role == 'test':
                value['accuracy_target_met'] = accuracy_gate(overall, groups, p)
            bounds = json.loads((PACKAGE / 'configs/domain.json').read_text())['bounds']
            for j, feature in enumerate(FEATURES):
                edges = np.linspace(*bounds[feature], 5)
                for b in range(4):
                    mask = (x[:, j] >= edges[b]) & ((x[:, j] <= edges[b+1]) if b == 3 else (x[:, j] < edges[b+1]))
                    value['input_bins'][f'{feature}_bin{b+1}'] = {'n': int(mask.sum()), 'small_group': int(mask.sum()) < 50,
                        'interval': edges[b:b+2].tolist(), 'right_inclusive': b == 3,
                        'metrics': metrics(y[mask], predicted[mask], p) if mask.any() else None}
            for name, mask in {'duration_38_42': (y[:, 1] >= 38) & (y[:, 1] <= 42),
                               'energy_95_105': (y[:, 0] >= 95) & (y[:, 0] <= 105)}.items():
                value['threshold_bands'][name] = {'n': int(mask.sum()), 'small_group': int(mask.sum()) < 50,
                    'metrics': metrics(y[mask], predicted[mask], p) if mask.any() else None}
            value['elapsed_s'] = time.monotonic() - stage
            result[role] = value
            predictions_csv(output / f'{role}_predictions.csv', rows, y, predicted, lo, hi)
            write(output / 'final_metrics.json', result)
            plot_evaluation(role, y, predicted, p, output)
        # No oracle calls: optional future candidates remain predictions, not labels.
        with (PACKAGE / 'data/candidates_unlabeled_20000.csv').open(newline='') as stream:
            reader = csv.DictReader(stream)
            if set(TARGETS) & set(reader.fieldnames):
                raise ValueError('Candidate pool must contain X only')
            candidates = list(reader)
        xp = np.array([[float(row[k]) for k in FEATURES] for row in candidates])
        prediction = model.predict(xp)
        prediction_count += len(prediction)
        lower, upper = prediction_intervals(prediction, calibration)
        predictions_csv(output / 'unlabeled_candidate_predictions.csv', candidates, None, prediction, lower, upper)
    summary = {'pipeline_completed': True, 'accuracy_target_met': bool(selection['development_accuracy_target_met'] and result['test']['accuracy_target_met']),
               'main_test_accuracy_target_met': result['test']['accuracy_target_met'],
               'development_accuracy_target_met': selection['development_accuracy_target_met'],
               'prediction_count': prediction_count, 'calibration_rows': len(calibration_rows),
               'test_rows': result['test']['metrics']['n'], 'challenge_rows': result['challenge']['metrics']['n'],
               'candidate_prediction_rows': len(candidates), 'candidate_oracle_calls': 0,
               'model_unchanged_after_calibration': sha(model_path) == selection['model_sha256'],
               'elapsed_s': time.monotonic() - start, 'uncertainty_claim': 'Exchangeable same-reference-distribution marginal joint coverage only',
               'final_evaluation_attempts': 1, 'retraining_after_calibration': False,
               'real_solver_error': None, 'real_solver_wall_clock_savings': None,
               'missing_reason': 'No new full GMMNLSE calls in this V4 batch'}
    write(output / 'summary.json', summary)
    return summary


def predict_design(model_path, selection_path, design):
    selection = verify_frozen(model_path, selection_path)
    if not isinstance(design, dict) or set(design) != set(FEATURES):
        raise ValueError('Exactly four design inputs required')
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not np.isfinite(v) for v in design.values()):
        raise ValueError('Finite real scalars required')
    with threadpool_limits(limits=2):
        model = joblib.load(model_path)
        value = model.predict([[design[k] for k in FEATURES]])[0]
    return {'kind': 'Prediction', 'design': design, 'targets_prediction': dict(zip(TARGETS, value.tolist())),
            'model_sha256': selection['model_sha256'], 'oracle_evaluation': False,
            'eligible_as_validated_training_truth': False}


def plot_learning(results, output):
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(12, 4), constrained_layout=True)
    for family in protocol()['model_order']:
        records = [r for r in results if r['family'] == family and r['order'] == 11]
        axes[0].plot([r['n'] for r in records], [r['metrics']['joint_pass_rate'] for r in records], 'o-', label=family)
        axes[1].plot([r['n'] for r in records], [r['metrics']['mean_tolerance_normalized_rmse'] for r in records], 'o-', label=family)
    axes[0].axhline(.90, ls='--', color='gray', label='joint component of gate')
    axes[0].set(ylabel='Validation joint tolerance pass fraction', xlabel='Training prefix size (order 11)', ylim=(0, 1.02))
    axes[1].set(ylabel='Mean tolerance-normalized RMSE', xlabel='Training prefix size (order 11)', yscale='log')
    for ax in axes:
        ax.grid(alpha=.3)
        ax.legend(fontsize=8)
    fig.savefig(output / 'learning_curve.png', dpi=140)
    plt.close(fig)


def plot_evaluation(role, truth, predicted, p, output):
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 3, figsize=(13, 8), constrained_layout=True)
    for j, target in enumerate(TARGETS):
        axes[0, j].scatter(truth[:, j], predicted[:, j], s=5, alpha=.45)
        limits = [min(truth[:, j].min(), predicted[:, j].min()), max(truth[:, j].max(), predicted[:, j].max())]
        axes[0, j].plot(limits, limits, '--', color='gray')
        axes[0, j].set(title=target, xlabel='Actual synthetic label', ylabel='Frozen model prediction')
        ratio = abs(predicted[:, j]-truth[:, j]) / np.maximum(p['tolerances'][target]['absolute'], p['tolerances'][target]['relative']*abs(truth[:, j]))
        axes[1, j].plot(np.sort(ratio), np.arange(1, len(ratio)+1)/len(ratio))
        axes[1, j].axvline(1, ls='--', color='gray')
        axes[1, j].set(xlabel='Tolerance-normalized absolute error', ylabel='Empirical cumulative fraction')
        for i in range(2):
            axes[i, j].grid(alpha=.3)
    fig.suptitle(role + ': one frozen synthetic-model evaluation; not GMMNLSE accuracy')
    fig.savefig(output / (role + '_errors.png'), dpi=140)
    plt.close(fig)
