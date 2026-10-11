#!/usr/bin/env python3
"""Check the frozen own model through Prediction storage; no fitting/oracle calls."""
import json
from pathlib import Path
import sys
import joblib
import numpy as np
from threadpoolctl import threadpool_limits

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'mamyshev_accuracy_v4/reference'))
from mamyshev_ml.v4_roles import verify_frozen
from mamyshev_ml.v4_evaluators import SurrogateEvaluator
from mamyshev_ml.v4_store import V4Store

base = ROOT / 'reports/local/accuracy_v4_001'
model_path = base / 'models/model.joblib'
selection = verify_frozen(model_path, base / 'models/selection.json')
expected = json.loads((base / 'models/default_prediction.json').read_text())
with threadpool_limits(limits=2):
    evaluator = SurrogateEvaluator(joblib.load(model_path), {
        'model_id': 'v4_frozen_spline_order11_n512', 'sha256': selection['model_sha256'],
        'selection': str(base / 'models/selection.json')})
    record = evaluator.evaluate(expected['design'])
assert record['targets'] == expected['targets_prediction']
store = V4Store(base / 'data_chain/demo_001/evaluations.sqlite')
before = store.db.execute('SELECT count(*) FROM evaluations').fetchone()[0]
pid = store.save_prediction(record)
assert store.db.execute('SELECT count(*) FROM evaluations').fetchone()[0] == before
assert store.db.execute('SELECT count(*) FROM predictions').fetchone()[0] == 1
synthetic = store.training_records(source='repository_guided_synthetic')
assert all(r['kind'] == 'Evaluation' and r['identity']['source'] == 'repository_guided_synthetic' for r in synthetic)
result = {'passed': True, 'prediction_count': 1, 'new_oracle_calls': 0,
          'prediction_id': pid, 'record': record, 'evaluation_rows_unchanged': before,
          'explicit_source_training_rows': len(synthetic), 'full_gmmnlse_runs': 0}
with (base / 'data_chain/frozen_prediction_store.json').open('x') as stream:
    stream.write(json.dumps(result, indent=2, allow_nan=False) + '\n')
store.close()
print(json.dumps(result, indent=2))
