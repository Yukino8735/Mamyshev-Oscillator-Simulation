% Read the actual pending plan, initialize only three selected production rows,
% check legacy initialization, and recompute <=32 already labeled synthetic rows.
% No call to launch_mamyshev_once, run_mamyshev_recorded or propagation kernels.
root=getenv('PHASE2_ROOT'); output_dir=getenv('PHASE2_OUTPUT_DIR');
plan_dir=fullfile(root,'reports','local','demo_10k_release_001','matlab_plan');
addpath(fullfile(root,'code'));setup_mamyshev_project();
addpath(fullfile(root,'code','ml_bridge'));
addpath(fullfile(root,'mamyshev_accuracy_v4','matlab'));
plan=jsondecode(fileread(fullfile(plan_dir,'gmmnlse_pending_plan.json')));
validation=jsondecode(fileread(fullfile(plan_dir,'plan_validation.json')));
assert(strcmp(plan.backend,'gmmnlse') && plan.max_new_real_attempts==0);
assert(numel(plan.designs)==10000 && plan.unique_designs==10000 && plan.input_count==10000);
assert(numel(unique({plan.designs.design_id}))==10000);
assert(strcmp(plan.plan_hash,validation.plan_hash));
integrity=mamyshev_artifact_integrity(plan_dir,{'gmmnlse_pending_plan.json'});
assert(strcmp(integrity.sha256,validation.plan_file_sha256));
features={'pump_power_W','filter_offset_nm','filter2_bw_nm','gain_length_m'};
units={'W','nm','nm','m'};
for k=1:4,assert(strcmp(plan.input_units.(features{k}),units{k}));end
for k=1:numel(plan.designs)
    row=plan.designs(k); config=mamyshev_resolve_config(row.design_config);
    assert(strcmp(row.job_status,'not_run'));
    targets=struct2cell(row.real_targets);assert(all(cellfun(@isempty,targets)));
    assert(config.pump_power_W>=2 && config.pump_power_W<=10);
    assert(config.filter_offset_nm>=2 && config.filter_offset_nm<=16);
    assert(config.filter2_bw_nm>=.5 && config.filter2_bw_nm<=8);
    assert(config.gain_length_m>=1 && config.gain_length_m<=8);
end
checks=struct('name',{},'passed',{});
checks(end+1)=struct('name','all_10000_rows_units_grid_null_targets_unique_IDs','passed',true);
indices=double(validation.selected_zero_based_indices(:))+1;
for k=1:numel(indices)
    row=plan.designs(indices(k));
    assert(strcmp(row.design_id,validation.selected_rows(k).design_id));
    assert(isequal(row.design_config,validation.selected_rows(k).design_config));
    folder=fullfile(output_dir,sprintf('selected_%d',indices(k)));mkdir(folder);
    config=row.design_config;
    context=fixture_context(config,sprintf('selected_%d',indices(k)));
    rng(0,'twister');capture=MamyshevCapture(folder,context);
    value=run_mamyshev_config(config,false,struct('capture',capture,'preflight_only',true));
    assert(~value.propagation_started && isempty(capture.calls));
    B=jsondecode(fileread(fullfile(folder,'configuration.json')));actual=B.configuration;
    assert(actual.gain_rate_eqn.copump_power==config.pump_power_W);
    assert(actual.spectral_filter2.cw==1040-config.filter_offset_nm && actual.spectral_filter2.bw==config.filter2_bw_nm);
    lengths=[actual.fiber_cavity.L0];assert(isequal(lengths,[config.gain_length_m .4 1.5 3.2]));
    expected_trep=sum(lengths)/(1/actual.fiber_cavity(1).betas(2)*1e12);
    assert(actual.gain_rate_eqn.t_rep==expected_trep);
    assert(actual.output_fiber_length_m==.2 && actual.Nt==32768 && actual.time_window_ps==50 && actual.max_rt==50);
    saved=load(fullfile(folder,'configuration.mat'),'gain_param');
    assert(saved.gain_param{1}.copump_power==config.pump_power_W && saved.gain_param{1}.t_rep==expected_trep);
    comparison=jsondecode(fileread(fullfile(folder,'configuration_comparison.json')));assert(comparison.passed);
    checks(end+1)=struct('name',sprintf('actual_initialization_row_%d_no_propagation',indices(k)),'passed',true); %#ok<SAGROW>
end
% Legacy call converts at the boundary to the same default four-input path.
base=mamyshev_resolve_config();folder=fullfile(output_dir,'legacy_default');mkdir(folder);
capture=MamyshevCapture(folder,fixture_context(base,'legacy_default'));
rng(0,'twister');value=run_mamyshev(4,1030,false,struct('capture',capture,'preflight_only',true));
assert(~value.propagation_started && isempty(capture.calls));
B=jsondecode(fileread(fullfile(folder,'configuration.json')));
assert(isequal(B.design_config,base));comparison=jsondecode(fileread(fullfile(folder,'configuration_comparison.json')));assert(comparison.passed);
checks(end+1)=struct('name','legacy_default_production_initialization_compatible','passed',true);
bad=rmfield(base,'pump_power_W');expect_bad(@()mamyshev_resolve_config(bad));
bad=base;bad.pump_power_W=NaN;expect_bad(@()mamyshev_resolve_config(bad));
bad=base;bad.pump_power_mW=4000;expect_bad(@()mamyshev_resolve_config(bad));
bad=base;bad.cw2=1030;expect_bad(@()mamyshev_resolve_config(bad));
bad=base;bad.gain_length_m=4.01;expect_bad(@()mamyshev_resolve_config(bad));
checks(end+1)=struct('name','missing_nonfinite_units_alias_conflict_offgrid_rejected','passed',true);
T=readtable(fullfile(plan_dir,'existing_train_parity_32.csv'),'VariableNamingRule','preserve');
assert(height(T)<=32 && height(T)>0);target_names={'compressed_energy_nJ','compressed_duration_fs','compressed_peak_power_MW'};
errors=zeros(height(T),3);before=rng;
for k=1:height(T)
    design=struct();for j=1:4,design.(features{j})=T.(features{j})(k);end
    [target,metadata]=v3_evaluate_synthetic(design);
    assert(strcmp(metadata.source_kind,'repository_guided_synthetic'));
    for j=1:3
        reference=T.(target_names{j})(k);assert(isfinite(reference));
        errors(k,j)=abs(target.(target_names{j})-reference);
        assert(errors(k,j)<=1e-10+2e-10*abs(reference));
    end
end
assert(isequal(before,rng));
checks(end+1)=struct('name','saved_new_train_32_synthetic_parity_no_new_labels','passed',true);
report=struct('suite','demo10k_plan_no_propagation_and_saved_label_parity','cases',checks,'all_passed',true, ...
    'plan_hash',plan.plan_hash,'plan_rows',10000,'actual_initializations',numel(indices)+1, ...
    'propagation_calls',0,'full_cavity_attempts',0,'matlab_processes',1,'parity_existing_rows',height(T), ...
    'new_research_labels',0,'parity_max_abs_by_target',max(errors,[],1),'parity_atol',1e-10,'parity_rtol',2e-10, ...
    'full_10k_gmmnlse','not_run');
mamyshev_write_diagnostic(fullfile(output_dir,'demo10k_matlab_components.json'),report);disp(report);

function context=fixture_context(config,id)
% Diagnostic context is not execution permission. No launcher consumes it.
context=struct('mode','real','run_id',id,'seed',0,'batch_id','demo10k_initialization_only', ...
    'source_identity',struct('kind','initialization_component_not_launch_identity'), ...
    'requested',struct('PumpPower',config.pump_power_W,'cw2',1040-config.filter_offset_nm,'plot_on',false), ...
    'design_config',config,'save_waveforms',false);
end

function expect_bad(fn)
try,fn();catch exception,assert(startsWith(exception.identifier,'MamyshevConfig:'));return;end
error('Demo10k:ExpectedFailure','Expected invalid configuration rejection.');
end
