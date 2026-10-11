% Exactly one authorized full-config initialization; no propagation and no candidate.
root=getenv('PHASE2_ROOT'); output_dir=getenv('PHASE2_OUTPUT_DIR');
addpath(fullfile(root,'code')); setup_mamyshev_project();
addpath(fullfile(root,'code','ml_bridge'));
identity=mamyshev_source_identity(root);
context=struct('run_id','launchprep_full_configuration_preflight','mode','preflight', ...
    'seed',0,'requested',struct('PumpPower',4,'cw2',1030,'plot_on',false), ...
    'source_identity',identity);
[git_status,context.commit]=system(sprintf('git -C "%s" rev-parse HEAD',root));
assert(git_status==0); context.commit=strtrim(context.commit);
[git_status,context.worktree_status]=system(sprintf('git -C "%s" status --short',root));
assert(git_status==0);
rng(context.seed,'twister'); rng_before=rng;
capture=MamyshevCapture(output_dir,context);
result=run_mamyshev(4,1030,false,struct('capture',capture,'preflight_only',true));
assert(~result.propagation_started && result.full_cavity_attempts==0);
assert(result.observability.initialization_observed && result.observability.configuration_comparison_passed);
assert(~result.observability.required_records_complete && result.observability.runtime_call_count==0);
assert(~isfile(fullfile(output_dir,'matlab_candidate.json')));
assert(isequal(rng_before,rng),'Mamyshev:RngChanged','No-propagation capture changed physical RNG.');
snapshot=load(fullfile(output_dir,'configuration.mat'));
assert(snapshot.phase1_config.Nt==32768 && snapshot.phase1_config.time_window_ps==50);
assert(snapshot.phase1_config.max_rt==50);
result.rng_unchanged=true;
result.c_runtime_status='deferred_to_authorized_run';
mamyshev_write_diagnostic(fullfile(output_dir,'preflight_result.json'),result);
disp(result);
