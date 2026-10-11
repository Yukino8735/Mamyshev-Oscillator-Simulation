% Targeted controls plus directly affected previous safety/wrapper regression.
root=getenv('PHASE2_ROOT');output_dir=getenv('PHASE2_OUTPUT_DIR');
addpath(fullfile(root,'code'));setup_mamyshev_project();
addpath(fullfile(root,'tests','matlab'),fullfile(root,'code','ml_bridge'));
report=test_observation_control(output_dir); assert(report.all_passed);
convergence=test_convergence_safety('after');assert(convergence.all_passed);
mamyshev_write_diagnostic(fullfile(output_dir,'convergence_regression.json'),convergence);
folder=fullfile(output_dir,'result_contract');mkdir(folder);
contract=test_result_contract(folder);assert(contract.all_passed);
mamyshev_write_diagnostic(fullfile(output_dir,'contract_regression.json'),contract);
folder=fullfile(output_dir,'wrapper');mkdir(folder);
wrapper=test_wrapper_readiness(folder);assert(wrapper.all_passed);
mamyshev_write_diagnostic(fullfile(output_dir,'wrapper_regression.json'),wrapper);
disp(report);
