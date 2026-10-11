% No propagation: analyze completed MATs from the separately authorized run.
root=getenv('PHASE2_ROOT'); output_dir=getenv('PHASE2_OUTPUT_DIR');
addpath(fullfile(root,'scripts')); addpath(fullfile(root,'code','ml_bridge'));
old_run=fullfile(root,'reports','local','phase2','config_waveform_validation_001','config_waveform_001');
new_run=fullfile(root,'reports','local','phase2','observation_validation_001','observation_001');
report=analyze_mamyshev_stationarity(new_run,fullfile(output_dir,'observation_rounds'),old_run);
if isfield(report,'prefix_comparison'), disp(report.prefix_comparison); end
if isfield(report,'last_five_rounds_summary'), disp(report.last_five_rounds_summary); end
