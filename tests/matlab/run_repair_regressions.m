% Serial repaired production-helper tests. No run_mamyshev/cavity invocation.
root = getenv('PHASE2_ROOT'); output_dir = getenv('PHASE2_OUTPUT_DIR');
addpath(fullfile(root,'tests','matlab'));
addpath(fullfile(root,'code')); setup_mamyshev_project();
gain = test_gain_rollback('regression',output_dir);
convergence = test_convergence_safety('after');
contract = test_result_contract(output_dir);
report = struct('full_cavity_runs',0,'gain',gain, ...
    'convergence',convergence,'contract',contract);
fid=fopen(fullfile(output_dir,'regressions.json'),'w');
assert(fid>=0); fprintf(fid,'%s\n',jsonencode(report)); fclose(fid);
disp(convergence); disp(contract);
assert(gain.all_regression_assertions_passed && convergence.all_passed && contract.all_passed, ...
    'Repair:RegressionFailure','Inspect individual suite cases; failures are not passed tests.');
