function report=test_config_entry(output_dir)
% Six real initialization paths, zero propagation calls; not six designs run.
root=fileparts(fileparts(fileparts(mfilename('fullpath'))));
addpath(fullfile(root,'code')); setup_mamyshev_project();
addpath(fullfile(root,'code','ml_bridge'));
defaults=mamyshev_resolve_config(); cases=struct('name',{},'passed',{});
invalid={rmfield(defaults,'gain_length_m'),setfield(defaults,'cw2',1030), ... %#ok<SFLD>
    setfield(defaults,'pump_power_W',NaN),setfield(defaults,'pump_power_W',-1), ...
    setfield(defaults,'pump_power_W',true),setfield(defaults,'pump_power_W',[4 5]), ...
    setfield(defaults,'filter_offset_nm',1040),setfield(defaults,'filter_offset_nm',1i), ...
    setfield(defaults,'filter2_bw_nm',0),setfield(defaults,'gain_length_m',4.15), ...
    setfield(defaults,'gain_length_m',Inf),setfield(defaults,'gain_length_m',realmin),struct()};
for k=1:numel(invalid)
    rejected=false;
    try, mamyshev_resolve_config(invalid{k});
    catch exception, rejected=startsWith(exception.identifier,'MamyshevConfig:'); end
    assert(rejected,'ConfigTest:InvalidAccepted');
end
rejected=false;
try, run_mamyshev(4,1030,false,[],defaults);
catch exception, rejected=strcmp(exception.identifier,'MamyshevConfig:ConflictingInputs'); end
check('invalid_missing_unknown_conflicting_nonfinite_and_save_grid_rejected',rejected);
[~,resolved]=mamyshev_resolve_config(defaults);
check('offset_definition_and_fixed_passive_length_rule',resolved.sf2_center_nm==1030 && ...
    isequal(resolved.passive_lengths_m,[.4 1.5 3.2]) && resolved.pigtail_length_m==.2);

legacy=initialize('legacy',defaults,true);
normal=initialize('config_default',defaults,false);
check('default_and_legacy_initialization_exact',isequaln(legacy,normal));
fields={'pump_power_W','filter_offset_nm','filter2_bw_nm','gain_length_m'};
values=[4.1 9.5 3.2 4.1];
for k=1:4
    requested=defaults; requested.(fields{k})=values(k);
    actual=initialize(['vary_' fields{k}],requested,false);
    cfg=actual.phase1_config;
    expected_cw=1040-requested.filter_offset_nm;
    assert(cfg.PumpPower_W==requested.pump_power_W && ...
        cfg.gain_rate_eqn.copump_power==requested.pump_power_W && ...
        actual.gain_param{1}.copump_power==requested.pump_power_W && ...
        cfg.cw2_nm==expected_cw && cfg.spectral_filter2.cw==expected_cw && ...
        cfg.spectral_filter2.bw==requested.filter2_bw_nm && ...
        cfg.fiber_cavity(1).L0==requested.gain_length_m && ...
        isequal([cfg.fiber_cavity(2:4).L0],[.4 1.5 3.2]) && cfg.output_fiber_length_m==.2);
    total=sum([cfg.fiber_cavity.L0]); v=1/cfg.fiber_cavity(1).betas(2)*1e12;
    assert(cfg.gain_rate_eqn.t_rep==total/v && actual.gain_param{1}.t_rep==total/v);
    assert(isequal(actual.prop_output,normal.prop_output) && isequal(actual.t,normal.t) && ...
        isequal(actual.f,normal.f) && isequal(actual.lambda,normal.lambda) && ...
        isequal(cfg.rng,normal.phase1_config.rng));
    for j=1:4
        assert(cfg.fiber_cavity(j).SR==normal.phase1_config.fiber_cavity(j).SR && ...
            cfg.fiber_cavity(j).gain_Aeff==normal.phase1_config.fiber_cavity(j).gain_Aeff);
    end
    check(['actual_initialization_and_dependencies_' fields{k}],true);
end

% Nondefault reference checks must reject an unrelated invariant mutation.
reference=fullfile(root,'reports','local','phase1','baseline_001','configuration.mat');
changed=normal; changed.phase1_config.fiber_cavity(2).SR=changed.phase1_config.fiber_cavity(2).SR*1.01;
comparison=mamyshev_compare_configuration(changed,reference,defaults);
check('configuration_comparison_rejects_changed_invariant_SR',~comparison.passed);
report=struct('suite','four_dimensional_config','initialization_attempts',6, ...
    'full_cavity_runs',0,'propagation_calls',0,'cases',cases,'all_passed',all([cases.passed]), ...
    'comparison_rule','Exact actual initialized values; only requested design inputs and named dependencies differ.', ...
    'domain_status','These are no-propagation interface checks, not a validated four-dimensional physical domain.');
mamyshev_write_diagnostic(fullfile(output_dir,'config_entry_tests.json'),report);

    function value=initialize(name,config,legacy_call)
        folder=fullfile(output_dir,name); mkdir(folder);
        rng(0,'twister');
        context=struct('mode','synthetic_initialization_fixture','run_id',name,'seed',0, ...
            'source_identity',struct('kind','initialization_component_not_physical_run'), ...
            'requested',struct('PumpPower',config.pump_power_W, ...
                'cw2',1040-config.filter_offset_nm,'plot_on',false));
        if ~legacy_call, context.design_config=config; end
        capture=MamyshevCapture(folder,context);
        options=struct('capture',capture,'preflight_only',true);
        if legacy_call, result=run_mamyshev(4,1030,false,options);
        else, result=run_mamyshev_config(config,false,options); end
        assert(~result.propagation_started && isempty(capture.calls));
        comparison=jsondecode(fileread(fullfile(folder,'configuration_comparison.json')));
        assert(comparison.passed && isempty(comparison.unexpected_differences));
        value=load(fullfile(folder,'configuration.mat'), ...
            'phase1_config','gain_param','prop_output','t','f','lambda');
    end
    function check(name,passed)
        assert(passed,'ConfigTest:Assertion','%s',name);
        cases(end+1)=struct('name',name,'passed',true);
    end
end
