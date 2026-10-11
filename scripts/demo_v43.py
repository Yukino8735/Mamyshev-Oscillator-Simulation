#!/usr/bin/env python3
"""One small CLI scan demonstration plus saved-prediction/export wiring checks."""
import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import numpy as np
from scipy.io import loadmat

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from mamyshev_ml.v43_adapter import load_application_evaluator
from mamyshev_ml.v4_evaluators import FEATURES, TARGETS, UNITS
from mamyshev_ml.v4_store import V4Store

OUT = ROOT/'reports/local/application_v4_3_001/demonstration'
MODEL = ROOT/'reports/local/accuracy_v4_2_001/release/model.joblib'
SELECTION = MODEL.with_name('selection.json')
ATOL = RTOL = 1e-10


def write(path, value):
    with path.open('x') as stream:
        stream.write(json.dumps(value, indent=2, allow_nan=False)+'\n')


def main():
    OUT.mkdir(exist_ok=False)
    commands = []
    def cli(label, *args):
        command = [sys.executable, str(ROOT/'scripts/v43_scan.py'), *map(str, args)]
        env = os.environ.copy(); env.pop('PYTHONPATH', None)
        started = time.monotonic()
        with (OUT/(label+'.stdout.log')).open('x') as log:
            result = subprocess.run(command, cwd=OUT, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=60)
        row = {'label': label, 'command': command, 'cwd': str(OUT), 'PYTHONPATH_removed': True,
               'elapsed_s': time.monotonic()-started, 'exit_code': result.returncode}
        commands.append(row)
        with (OUT/'commands.jsonl').open('a') as log:
            log.write(json.dumps(row)+'\n')
        if result.returncode:
            raise RuntimeError('CLI failed: '+label)
    model_args = ['--model', MODEL, '--selection', SELECTION]
    default = dict(zip(FEATURES, (4.,10.,3.,4.)))
    write(OUT/'single_input.json', default)
    cli('single_prediction', 'predict', '--input', OUT/'single_input.json', '--out', OUT/'single_prediction.json', *model_args)
    predictor = load_application_evaluator(MODEL, SELECTION)
    batch = [default, {**default, 'pump_power_W': 4.1}, {**default, 'gain_length_m': 4.1}]
    array = predictor.predict_arrays(batch)['targets']
    individual = np.array([[r['targets'][k] for k in TARGETS] for r in predictor.evaluate_many(batch)])
    np.testing.assert_allclose(array, individual, atol=ATOL, rtol=RTOL)
    cli_record = json.loads((OUT/'single_prediction.json').read_text())
    np.testing.assert_allclose(array[0], [cli_record['targets'][k] for k in TARGETS], atol=ATOL, rtol=RTOL)
    # Three saved, already scored predictions only: not new test scoring or truth use.
    saved_path = ROOT/'reports/local/accuracy_v4_2_001/evaluation/test_predictions.csv'
    with saved_path.open(newline='') as stream:
        reader = csv.DictReader(stream)
        saved = [next(reader) for _ in range(3)]
    old_designs = [{k: float(r[k]) for k in FEATURES} for r in saved]
    old_pred = np.array([[float(r[k+'_prediction']) for k in TARGETS] for r in saved])
    new_pred = predictor.predict_arrays(old_designs)['targets']
    np.testing.assert_allclose(new_pred, old_pred, atol=ATOL, rtol=RTOL)
    curves = {
        'curve': {'axes': {'filter2_bw_nm': [.5,1.4,2.3,3.2,4.1,5.,5.9,6.8,8.]},
                  'fixed': {'pump_power_W':4.,'filter_offset_nm':10.,'gain_length_m':4.}},
        'heatmap': {'axes': {'filter_offset_nm':[2.,3.75,5.5,7.25,9.,10.75,12.5,14.25,16.],
                             'filter2_bw_nm':[.5,1.4,2.3,3.2,4.1,5.,5.9,6.8,8.]},
                    'fixed': {'pump_power_W':4.,'gain_length_m':4.}}}
    scans = {}
    for name, spec in curves.items():
        folder = OUT/name; folder.mkdir()
        write(folder/'spec.json', spec)
        cli(name+'_plan', 'plan', '--spec', folder/'spec.json', '--out', folder/'plan.json')
        plan = json.loads((folder/'plan.json').read_text()); count = len(plan['designs'])
        assert count == (9 if name == 'curve' else 81)
        cli(name+'_run', 'run', '--plan', folder/'plan.json', '--db', folder/'predictions.sqlite',
            '--scan-id', name, '--execute', '--max-new-attempts', count, '--total-wall-s', 30,
            '--stop', folder/'STOP', *model_args)
        cli(name+'_export', 'export', '--db', folder/'predictions.sqlite', '--scan-id', name, '--out', folder/'export')
        cli(name+'_plot', 'plot', '--db', folder/'predictions.sqlite', '--scan-id', name,
            '--plan', folder/'plan.json', '--out', folder/'plots')
        store = V4Store(folder/'predictions.sqlite')
        try:
            rows = store.scan_records(name)
            counts = {table: store.db.execute('SELECT COUNT(*) FROM '+table).fetchone()[0]
                      for table in ('evaluations','predictions')}
        finally:
            store.close()
        assert counts == {'evaluations':0,'predictions':count}
        assert all(r['status']=='predicted' and r['evaluation']['kind']=='Prediction' for r in rows)
        with (folder/'export/results.csv').open(newline='') as stream:
            csv_rows = list(csv.DictReader(stream))
        mat = loadmat(folder/'export/results.mat', simplify_cells=True)
        X = np.array([[r['design'][k] for k in FEATURES] for r in rows])
        Y = np.array([[r['evaluation']['targets'][k] for k in TARGETS] for r in rows])
        np.testing.assert_array_equal(mat['X'], X)
        np.testing.assert_array_equal(mat['Y'], Y)
        np.testing.assert_array_equal([[float(r[k]) for k in FEATURES] for r in csv_rows], X)
        np.testing.assert_array_equal([[float(r[k]) for k in TARGETS] for r in csv_rows], Y)
        assert [str(x).strip() for x in mat['feature_names']] == list(FEATURES)
        assert [str(x).strip() for x in mat['target_names']] == list(TARGETS)
        assert [str(x).strip() for x in mat['target_units']] == list(UNITS.values())
        mat_rows = json.loads(str(mat['records_json']))
        for actual, exported, mat_row in zip(rows, csv_rows, mat_rows):
            assert exported['design_id'] == actual['design_id'] == mat_row['design_id']
            assert json.loads(exported['identity_json']) == actual['evaluation']['identity']
            assert json.loads(mat_row['identity_json']) == actual['evaluation']['identity']
            assert actual['evaluation']['model_identity']['sha256'] == predictor.release['model_sha256']
        scans[name] = {'rows':count, 'counts':counts, 'export_reread':'exact_X_Y_ID_identity_units',
            'csv':str(folder/'export/results.csv'), 'mat':str(folder/'export/results.mat'),
            'plots':[str(p) for p in sorted((folder/'plots').glob('*.png'))]}
    result = {'completed': True, 'scans':scans, 'input_units': dict(zip(FEATURES,('W','nm','nm','m'))),
        'single_batch_comparison': {'n':3,'atol':ATOL,'rtol':RTOL,'max_abs_diff':float(np.max(np.abs(array-individual)))},
        'saved_prediction_regression': {'n':3,'atol':ATOL,'rtol':RTOL,'source':str(saved_path),
            'max_abs_diff':float(np.max(np.abs(old_pred-new_pred))), 'new_test_scoring':False},
        'prediction_rows': 1+predictor.prediction_rows+90, 'scan_prediction_rows':90,
        'oracle_queries':0,'new_evaluation_rows':0,'MATLAB_starts':0,
        'model_sha256':predictor.release['model_sha256'], 'calibration':predictor.calibration,
        'adapter_identity':predictor.adapter_identity, 'actual_cli_commands':len(commands)}
    write(OUT/'summary.json', result)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
