function launch_mamyshev_once()
% REAL propagation entry, called only by --execute-real after authorization.
% Merely displaying Python help/dry-run never calls this function.
root=getenv('PHASE2_ROOT'); output_dir=getenv('PHASE2_OUTPUT_DIR');
assert(~isempty(root) && isfolder(output_dir),'Mamyshev:LaunchContext','Missing isolated run directory.');
context=jsondecode(fileread(fullfile(output_dir,'launch_request.json')));
addpath(fullfile(root,'code')); setup_mamyshev_project();
mamyshev_validate_launch_context(context);
mamyshev_source_identity(root,context.source_identity);
rng(context.seed,'twister');
run_mamyshev_recorded(context.requested.PumpPower,context.requested.cw2, ...
    context.requested.plot_on,fullfile(output_dir,'matlab_candidate.json'),[],context);
end
