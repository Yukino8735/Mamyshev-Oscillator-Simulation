% Analyze the one authorized saved run, without propagation or compression.
root=getenv('PHASE2_ROOT'); output_dir=getenv('PHASE2_OUTPUT_DIR');
addpath(fullfile(root,'scripts'));
run_dir=fullfile(root,'reports','local','phase2','config_waveform_validation_001','config_waveform_001');
reference=fullfile(root,'reports','local','phase2','single_validation_002','validation_002','final_result.json');
report=analyze_mamyshev_waveforms(run_dir,fullfile(output_dir,'figures_and_checks'),reference);
disp(struct('all_recomputation_checks_passed',report.all_recomputation_checks_passed, ...
    'all_reference_checks_passed',report.all_reference_checks_passed));
% A failed comparison remains evidence; no physical retry and no tolerance change.
