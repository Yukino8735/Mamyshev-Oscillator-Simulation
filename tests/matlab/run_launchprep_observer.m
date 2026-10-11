% launchprep_001: production-engine observer fixtures + existing regressions.
% ZERO cavity runs and no full baseline initialization.
root=getenv('PHASE2_ROOT'); output_dir=getenv('PHASE2_OUTPUT_DIR');
addpath(fullfile(root,'tests','matlab'));
addpath(fullfile(root,'code','ml_bridge'));
addpath(fullfile(root,'code')); setup_mamyshev_project();
observer=test_runtime_observer(output_dir);
capture=test_launchprep_capture(output_dir);
gain_readiness=test_gain_readiness(output_dir);
wrapper_readiness=test_wrapper_readiness(output_dir);
gain_repeated=test_gain_rollback('regression',output_dir);
convergence_repeated=test_convergence_safety('after');
contract_repeated=test_result_contract(output_dir);
report=struct('batch','launchprep_001','full_cavity_runs',0, ...
    'new_coverage',struct('observer',observer,'capture',capture), ...
    'repeated_regressions',struct('gain_readiness',gain_readiness, ...
    'wrapper',wrapper_readiness,'gain',gain_repeated,'convergence',convergence_repeated,'contract',contract_repeated));
mamyshev_write_diagnostic(fullfile(output_dir,'launchprep_regressions.json'),report);
assert(observer.all_passed && capture.all_passed && gain_readiness.all_passed && wrapper_readiness.all_passed && ...
    gain_repeated.all_regression_assertions_passed && convergence_repeated.all_passed && contract_repeated.all_passed, ...
    'Launchprep:RegressionFailure','Inspect new and repeated cases separately.');
disp('launchprep observer + repeated regression component suite passed');
