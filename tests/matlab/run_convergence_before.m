% Expected-failure reproduction only; no propagation or physical data.
root = getenv('PHASE2_ROOT');
output_dir = getenv('PHASE2_OUTPUT_DIR');
addpath(fullfile(root,'code')); setup_mamyshev_project();
addpath(fullfile(root,'tests','matlab'));
report = test_convergence_safety('before');
fid = fopen(fullfile(output_dir,'convergence_before.json'),'w');
assert(fid >= 0); fprintf(fid,'%s\n',jsonencode(report)); fclose(fid);
disp(report);
assert(report.passed == 1 && report.failed == 3, ...
    'Repair:UnexpectedReproduction','Expected 1 control pass and 3 failed safety expectations.');
