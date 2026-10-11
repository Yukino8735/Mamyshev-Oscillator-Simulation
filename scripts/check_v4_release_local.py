"""Local release integrity using the V4-declared cross-language scalar tolerance.
Preserves the upstream exact-byte test failures; does not replace release labels.
"""
import csv
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'mamyshev_accuracy_v4'
sys.path.insert(0, str(PACKAGE / 'reference'))
from oracle import FEATURES, TARGETS, load_recipe, evaluate, design_id
from build_release import build


def read(path):
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))


def main():
    start = time.monotonic()
    output = ROOT / 'reports/local/accuracy_v4_001/release_local_checks.json'
    if output.exists(): raise FileExistsError(output)
    manifest = json.loads((PACKAGE/'MANIFEST.json').read_text())
    errors = [item['path'] for item in manifest['files'] if
              hashlib.sha256((PACKAGE/item['path']).read_bytes()).hexdigest() != item['sha256']
              or (PACKAGE/item['path']).stat().st_size != item['bytes']]
    if errors: raise AssertionError('Release MANIFEST mismatch: ' + repr(errors))
    paths = ['data/train_pool_4096.csv', 'data/validation_1024.csv', 'evaluation_only/calibration_1024.csv',
             'evaluation_only/test_1536.csv', 'evaluation_only/challenge_512.csv']
    max_error = {k: 0. for k in TARGETS}; counts = {k: 0 for k in TARGETS}
    bad = []; rows = 0; recipe = load_recipe()
    for name in paths:
        for row in read(PACKAGE/name):
            design = {k: float(row[k]) for k in FEATURES}
            if design_id(design) != row['design_id']: raise AssertionError('Design hash mismatch')
            actual = evaluate(design, recipe)
            for k in TARGETS:
                reference = float(row[k]); error = abs(actual[k]-reference)
                max_error[k] = max(max_error[k], error)
                counts[k] += error != 0
                if error > 1e-10+2e-10*abs(reference): bad.append([row['design_id'], k, error])
            rows += 1
    nonlabel_mismatches = []; rebuilt_max = {k: 0. for k in TARGETS}; byte_equal = {}
    with tempfile.TemporaryDirectory(prefix='mamyshev_v4_rebuild_') as directory:
        temporary = Path(directory)/'release'
        build(temporary)
        for name in [*paths, 'plans/solver_designs_8192.csv']:
            before, after = read(PACKAGE/name), read(temporary/name)
            if len(before) != len(after): raise AssertionError('Rebuild row count changed: '+name)
            byte_equal[name] = (PACKAGE/name).read_bytes() == (temporary/name).read_bytes()
            for a, b in zip(before, after):
                if set(a) != set(b): raise AssertionError('Rebuild columns changed')
                for k in a:
                    if k in TARGETS and a[k] != '':
                        error = abs(float(a[k])-float(b[k])); rebuilt_max[k] = max(rebuilt_max[k], error)
                        if error > 1e-10+2e-10*abs(float(a[k])): bad.append(['rebuild', a['design_id'], k, error])
                    elif a[k] != b[k]: nonlabel_mismatches.append([name, a.get('design_id'), k])
        if (PACKAGE/'data/training_orders.json').read_bytes() != (temporary/'data/training_orders.json').read_bytes():
            raise AssertionError('Training orders changed')
    value = {'manifest_files_checked': len(manifest['files']), 'manifest_mismatches': errors,
             'rows_checked': rows, 'python_recomputed_max_abs_error': max_error,
             'non_bitwise_equal_value_count_by_target': counts, 'rebuild_max_abs_error': rebuilt_max,
             'nonlabel_rebuild_mismatches': nonlabel_mismatches, 'csv_byte_equal': byte_equal,
             'tolerance': 'Existing V4 MATLAB parity tolerance: 1e-10 + 2e-10*abs(published value)',
             'tolerance_violations': bad, 'all_portability_checks_passed': not bad and not nonlabel_mismatches,
             'upstream_exact_tests_status': 'Two failures retained; cross-platform numeric agreement is not byte equality.',
             'holdout_access': 'Integrity-only, no model predictions, fitting or selection',
             'original_files_written': False, 'full_gmmnlse_calls': 0, 'elapsed_s': time.monotonic()-start}
    value['candidate_rebuild_scope'] = 'Supplied build_release regenerates labeled/solver plans, not the separate inherited X-only candidate CSV; candidate hash/schema/disjointness checked separately.'
    output.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')
    print(json.dumps(value, indent=2))
    if bad or nonlabel_mismatches: raise AssertionError('Release failed declared numerical or exact nonlabel checks')


if __name__ == '__main__': main()
