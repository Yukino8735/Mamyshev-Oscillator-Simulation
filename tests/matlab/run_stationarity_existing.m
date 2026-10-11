% Artificial alignment checks followed by read-only analysis of the OLD six rounds.
root=getenv('PHASE2_ROOT'); output_dir=getenv('PHASE2_OUTPUT_DIR');
addpath(fullfile(root,'tests','matlab')); addpath(fullfile(root,'scripts'));
addpath(fullfile(root,'code','ml_bridge'));
tests=test_stationarity_analysis(output_dir); assert(tests.all_passed);
old_run=fullfile(root,'reports','local','phase2','config_waveform_validation_001','config_waveform_001');
report=analyze_mamyshev_stationarity(old_run,fullfile(output_dir,'old_six_rounds'));
assert(report.completed_saved_rounds==6,'Stationarity:OldRunCount','Expected the preserved old six-round run.');
disp(report.last_five_rounds_summary);
