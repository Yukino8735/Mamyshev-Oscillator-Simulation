% Configuration comparison / identity / writer components; no initialization.
root=getenv('PHASE2_ROOT'); output_dir=getenv('PHASE2_OUTPUT_DIR');
addpath(fullfile(root,'tests','matlab'));
addpath(fullfile(root,'code','ml_bridge'));
report=test_launchprep_capture(output_dir);
assert(report.all_passed);
disp(report);
