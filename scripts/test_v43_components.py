#!/usr/bin/env python3
"""Run only affected components; no actual oracle queries, fits or MATLAB."""
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT/'tests')]
loader = unittest.TestLoader()
new = loader.discover(str(ROOT/'tests'), pattern='test_v43_*.py')
old_names = ['test_v42_release']
old_names += ['test_v4_data_chain.TestV4DataChain.'+name for name in (
    'test_validation_no_rounding_or_unknown_fields',
    'test_prediction_cannot_enter_labels_and_source_required',
    'test_plan_shapes_dedup_and_hash',
    'test_failed_surrogate_stays_out_of_oracle_table_and_finalizes_attempt',
    'test_surrogate_cli_freeze_and_hash_gates_before_pickle_loading',
    'test_surrogate_cli_verified_reference_path_precedes_deserialization')]
old_names += ['test_v4_live_supervisor.LiveAuthorization.'+name for name in (
    'test_default_denial_and_zero_allowance_do_not_reserve',
    'test_changed_plan_unauthorized_id_and_unknown_fields_fail')]
old_names += ['test_v4_ml.V4LearningTests.'+name for name in (
    'test_development_roles_and_prefix', 'test_wrong_source_and_ids')]
old = loader.loadTestsFromNames(old_names)
counts = {'new_component_methods': new.countTestCases(), 'existing_regression_methods': old.countTestCases(),
          'actual_oracle_queries': 0, 'MATLAB_starts': 0, 'fits': 0}
result = unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite([new, old]))
counts.update(passed=result.wasSuccessful(), tests_run=result.testsRun,
              failures=len(result.failures), errors=len(result.errors))
print(json.dumps(counts, indent=2))
raise SystemExit(0 if result.wasSuccessful() else 1)
