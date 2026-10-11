#!/usr/bin/env python3
"""Verify and load existing weights once, without fitting or predicting."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from mamyshev_ml.v42_release import load_release_evaluator

MODEL = ROOT/'reports/local/accuracy_v4_2_001/release/model.joblib'
SELECTION = MODEL.with_name('selection.json')
value = load_release_evaluator(MODEL, SELECTION)
expected = 'c236c2d2dd6cb5b59e32bd5ab4f8c3823f7fefc10d7571108a3d6339ee46b2e0'
if value.release['model_sha256'] != expected:
    raise ValueError('V4.3 requested weights do not match')
result = {k: value.release[k] for k in ('selected','parameters','n_train','release_id','model_sha256',
    'protocol_sha256','evaluation_summary_sha256','final_metrics_sha256','source_hashes','data_hashes')}
result.update(verified_and_loaded=True, predictions=0, fits=0, oracle_queries=0, MATLAB_starts=0,
    model_path=str(MODEL), selection_path=str(SELECTION),
    selection_sha256=hashlib.sha256(SELECTION.read_bytes()).hexdigest())
path = ROOT/'reports/local/application_v4_3_001/frozen_asset_check.json'
with path.open('x') as stream:
    stream.write(json.dumps(result, indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ('source_hashes','data_hashes')},indent=2))
