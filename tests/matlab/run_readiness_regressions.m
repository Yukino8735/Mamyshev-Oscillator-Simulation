% readiness_001 only: local production gain fixtures and wrapper components.
% Default full-cavity backend is never invoked by this test script.
root=getenv('PHASE2_ROOT'); output_dir=getenv('PHASE2_OUTPUT_DIR');
addpath(fullfile(root,'tests','matlab'));
addpath(fullfile(root,'code')); setup_mamyshev_project();
gain_readiness=test_gain_readiness(output_dir);
wrapper_readiness=test_wrapper_readiness(output_dir);
gain_repeated=test_gain_rollback('regression',output_dir);
convergence_repeated=test_convergence_safety('after');
contract_repeated=test_result_contract(output_dir);
report=struct('batch','readiness_001','full_cavity_runs',0, ...
    'new_coverage',struct('gain',gain_readiness,'wrapper',wrapper_readiness), ...
    'repeated_regressions',struct('gain',gain_repeated,'convergence',convergence_repeated,'contract',contract_repeated));
fid=fopen(fullfile(output_dir,'readiness_regressions.json'),'w');
assert(fid>=0); fprintf(fid,'%s\n',jsonencode(report)); fclose(fid);
disp(wrapper_readiness); disp(convergence_repeated); disp(contract_repeated);
assert(gain_readiness.all_passed && wrapper_readiness.all_passed && ...
    gain_repeated.all_regression_assertions_passed && convergence_repeated.all_passed && contract_repeated.all_passed, ...
    'Readiness:RegressionFailure','Inspect new and repeated cases separately.');
