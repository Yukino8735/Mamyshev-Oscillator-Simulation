% Focused analysis fix + affected wrapper compatibility; no initialization/propagation.
root=getenv('PHASE2_ROOT'); output_dir=getenv('PHASE2_OUTPUT_DIR');
addpath(fullfile(root,'code')); setup_mamyshev_project();
addpath(fullfile(root,'code','ml_bridge'),fullfile(root,'scripts'),fullfile(root,'tests','matlab'));
report=test_waveform_analysis(output_dir);
assert(report.all_passed);
wrapper_dir=fullfile(output_dir,'wrapper_regression');mkdir(wrapper_dir);
wrapper=test_wrapper_readiness(wrapper_dir);assert(wrapper.all_passed);
mamyshev_write_diagnostic(fullfile(output_dir,'wrapper_regression.json'),wrapper);
disp(report);
