% Published synthetic scalar consistency only. No model scoring or propagation.
root=getenv('PHASE2_ROOT'); output_dir=getenv('PHASE2_OUTPUT_DIR');
package_root=fullfile(root,'mamyshev_accuracy_v4');
addpath(fullfile(package_root,'matlab'));
before=rng;
test_v4_oracle_parity(package_root);
summary=reproduce_v4_synthetic(package_root,fullfile(output_dir,'recomputed_8192.csv'),true);
assert(isequal(before,rng),'V4:RngChanged','Synthetic parity must not change RNG.');
summary.parity_rows=24;
summary.role_access_purpose='Published label integrity only, no model scoring or selection.';
summary.matlab_processes=1;
summary.full_cavity_runs=0;
fid=fopen(fullfile(output_dir,'parity_summary.json'),'w');
assert(fid>=0); guard=onCleanup(@()fclose(fid));
fprintf(fid,'%s\n',jsonencode(summary,'PrettyPrint',true));
disp(summary);
