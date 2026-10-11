% Five actual initializations, no propagation and no real launch call.
root=getenv('PHASE2_ROOT');output_dir=getenv('PHASE2_OUTPUT_DIR');
addpath(fullfile(root,'code'));setup_mamyshev_project();addpath(fullfile(root,'code','ml_bridge'));
base=mamyshev_resolve_config(); designs=repmat(base,1,5);
designs(2).pump_power_W=4.1;designs(3).filter_offset_nm=9.5;
designs(4).filter2_bw_nm=3.2;designs(5).gain_length_m=4.1;
checks=struct('name',{},'passed',{}); snapshots=cell(1,5);
for k=1:5
    config=designs(k);id=sprintf('fixture_%d',k);folder=fullfile(output_dir,id);mkdir(folder);
    auth=struct('authorization_id','component_only_never_executed','plan_hash','fixture_plan', ...
        'allowed_design_ids',{{id}},'max_new_attempts',1,'per_run_timeout_s',900,'total_wall_limit_s',900);
    context=struct('mode','real','run_id',id,'seed',0,'batch_id','v4_no_propagation_component', ...
        'source_identity',struct('kind','synthetic_live_routing_component_no_propagation'), ...
        'requested',struct('PumpPower',config.pump_power_W,'cw2',1040-config.filter_offset_nm,'plot_on',false), ...
        'design_config',config,'save_waveforms',true,'total_wall_limit_s',900, ...
        'shutdown_and_finalization_reserve_s',30,'live_authorization',struct('schema_version','configured_live_v1', ...
        'execute_real',true,'authorization',auth,'authorization_hash','fixture_not_execution_permission', ...
        'plan_hash','fixture_plan','design_id',id,'attempt_index',1,'remaining_total_s_before',900,'selected_design',config));
    resolved=mamyshev_validate_launch_context(context);assert(isequal(resolved,config));
    rng(0,'twister');capture=MamyshevCapture(folder,context);
    value=run_mamyshev_config(config,false,struct('capture',capture,'preflight_only',true));
    assert(~value.propagation_started && isempty(capture.calls));
    B=jsondecode(fileread(fullfile(folder,'configuration.json')));snapshots{k}=B;
    actual=B.configuration;
    assert(B.design_config.pump_power_W==config.pump_power_W && actual.gain_rate_eqn.copump_power==config.pump_power_W);
    assert(actual.spectral_filter2.cw==1040-config.filter_offset_nm && actual.spectral_filter2.bw==config.filter2_bw_nm);
    lengths=[actual.fiber_cavity.L0];assert(isequal(lengths,[config.gain_length_m,.4,1.5,3.2]));
    assert(actual.output_fiber_length_m==.2 && actual.Nt==32768 && actual.time_window_ps==50 && actual.max_rt==50);
    expected_trep=sum(lengths)/(1/actual.fiber_cavity(1).betas(2)*1e12);
    assert(actual.gain_rate_eqn.t_rep==expected_trep);
    saved=load(fullfile(folder,'configuration.mat'),'gain_param');assert(saved.gain_param{1}.copump_power==config.pump_power_W);
    assert(saved.gain_param{1}.t_rep==expected_trep && ~isfield(B,'observation_options'));
    comparison=jsondecode(fileread(fullfile(folder,'configuration_comparison.json')));assert(comparison.passed);
    checks(end+1)=struct('name',[id '_actual_request_gain_filter_length_and_trep'],'passed',true); %#ok<SAGROW>
end
bad=context;bad.live_authorization.authorization.max_new_attempts=0;expect_rejection(@()mamyshev_validate_launch_context(bad));
bad=context;bad.live_authorization.execute_real=false;expect_rejection(@()mamyshev_validate_launch_context(bad));
bad=context;bad.live_authorization.design_id='not_allowed';expect_rejection(@()mamyshev_validate_launch_context(bad));
bad=context;bad.requested.PumpPower=99;expect_rejection(@()mamyshev_validate_launch_context(bad));
bad=context;bad.total_wall_limit_s=901;expect_rejection(@()mamyshev_validate_launch_context(bad));
bad=context;bad.test_hook=[];expect_rejection(@()mamyshev_validate_launch_context(bad));
bad=context;bad.design_config.gain_length_m=4.15;expect_rejection(@()mamyshev_validate_launch_context(bad));
checks(end+1)=struct('name','seven_invalid_permission_routing_budget_hook_length_cases','passed',true);
legacy=rmfield(context,'live_authorization');legacy.design_config=base;
legacy.requested=struct('PumpPower',4,'cw2',1030,'plot_on',false);
assert(isequal(mamyshev_validate_launch_context(legacy),base));
checks(end+1)=struct('name','historical_default_launch_validation_compatible','passed',true);
report=struct('suite','v4_live_no_propagation_components','cases',checks,'all_passed',true, ...
    'actual_initializations',5,'full_cavity_attempts',0,'propagation_calls',0, ...
    'launch_validator_executed',true,'real_launcher_executed',false, ...
    'runtime_C_propagation_gate','not_run; no propagation authorized');
mamyshev_write_diagnostic(fullfile(output_dir,'v4_live_components.json'),report);disp(report);

function expect_rejection(fn)
try,fn();catch exception,assert(startsWith(exception.identifier,'Mamyshev'));return;end
error('V4LiveTest:ExpectedFailure','Expected authorization/configuration rejection.');
end
