% Targeted configuration initializations and artificial waveform components.
root=getenv('PHASE2_ROOT'); output_dir=getenv('PHASE2_OUTPUT_DIR');
addpath(fullfile(root,'code')); setup_mamyshev_project();
addpath(fullfile(root,'code','ml_bridge'),fullfile(root,'tests','matlab'),fullfile(root,'scripts'));
config_dir=fullfile(output_dir,'config_components');mkdir(config_dir);
config_report=test_config_entry(config_dir);assert(config_report.all_passed);
waveform_dir=fullfile(output_dir,'waveform_components');mkdir(waveform_dir);
waveform_report=test_waveform_io(waveform_dir);assert(waveform_report.all_passed);
capture_dir=fullfile(output_dir,'capture_regression');mkdir(capture_dir);
capture_report=test_launchprep_capture(capture_dir);assert(capture_report.all_passed);
contract_dir=fullfile(output_dir,'contract_regression');mkdir(contract_dir);
contract_report=test_result_contract(contract_dir);assert(contract_report.all_passed);
analysis_dir=fullfile(output_dir,'analysis_components');mkdir(analysis_dir);
analysis_report=test_waveform_analysis(analysis_dir);assert(analysis_report.all_passed);
summary=struct('config',config_report,'waveforms',waveform_report,'capture',capture_report, ...
    'result_contract',contract_report,'analysis',analysis_report, ...
    'full_cavity_runs',0,'initialization_attempts',6,'physical_propagation_calls',0);
mamyshev_write_diagnostic(fullfile(output_dir,'component_summary.json'),summary);
disp(summary);
