function report=test_observation_control(output_dir)
% Artificial stop decisions plus ONE actual initialization; no propagation.
root=fileparts(fileparts(fileparts(mfilename('fullpath'))));
addpath(fullfile(root,'code')); setup_mamyshev_project(); addpath(fullfile(root,'code','ml_bridge'));
legacy=mamyshev_observation_options();
fixed=struct('observation_mode','fixed_roundtrips','observation_roundtrips',20);
force=struct('convergence',false,'fluctuation',false);
cases=struct('name',{},'passed',{});
invalid={struct(),struct('observation_mode','unknown','observation_roundtrips',20), ...
    struct('observation_mode','legacy','observation_roundtrips',20), ...
    setfield(fixed,'observation_roundtrips',51),setfield(fixed,'observation_roundtrips',NaN), ...
    setfield(fixed,'observation_roundtrips',2.5),setfield(fixed,'observation_roundtrips',true), ...
    setfield(fixed,'pump_power_W',4)}; %#ok<SFLD>
for k=1:numel(invalid), expect(@()mamyshev_observation_options(invalid{k}),'MamyshevObservation:'); end
check('separate_options_reject_unknown_conflicting_invalid_inputs',true);
[stop,reason]=decision(legacy,6,true,force,1);
assert(stop && strcmp(reason,'legacy_energy_convergence'));
f=force; f.convergence=true; [stop,reason]=decision(legacy,10,false,f,1);
assert(stop && strcmp(reason,'legacy_average_energy_convergence'));
f=force; f.fluctuation=true; [stop,~]=decision(legacy,10,false,f,1); assert(~stop);
[stop,reason]=decision(legacy,6,true,force,0); assert(stop && strcmp(reason,'legacy_energy_convergence'));
check('legacy_convergence_order_and_unused_fluctuation_behavior_unchanged',true);
f=force; f.convergence=true;
assert(~decision(fixed,6,true,force,1) && ~decision(fixed,10,false,f,1));
check('fixed_ignores_only_convergence_stops',true);
f=force;f.fluctuation=true;
[stop,reason]=decision(fixed,10,false,f,1);assert(stop && strcmp(reason,'legacy_energy_fluctuation_stop'));
[stop,reason]=decision(fixed,20,true,f,0);assert(stop && strcmp(reason,'legacy_energy_below_threshold'));
[stop,reason]=decision(fixed,20,false,f,1);assert(stop && strcmp(reason,'legacy_energy_fluctuation_stop'));
check('death_and_nonconvergence_force_stop_win_over_budget',true);
[stop,reason]=decision(fixed,19,true,force,1); assert(~stop && isempty(reason));
[stop,reason]=decision(fixed,20,true,force,1); assert(stop && strcmp(reason,'observation_budget_reached'));
check('exact_twentieth_round_budget_not_convergence',true);
expect(@()decision(fixed,6,true,force,NaN),'check_convergence:NonFiniteEnergy');

t=linspace(-2,2,32)'; field=exp(-t.^2); freq=(1:32)'; energies=zeros(50,1);
settings=struct('tol_convergence',1e-4,'tol_fluctuation',5e-4,'min_rt',10);
history=struct('roundtrip',{},'converged',{},'force_stop_convergence',{}, ...
    'force_stop_fluctuation',{},'criterion_reason',{},'stop_reason',{}); first=NaN;
for rt=1:20
    energies(rt)=1;
    [converged,flags,~,diagnostic]=check_convergence(energies,field,freq,t,1e-3,false,settings,1,rt);
    [stop,reason]=decision(fixed,rt,converged,flags,energies(rt));
    if isnan(first) && (converged || flags.convergence), first=rt; end
    history(end+1)=struct('roundtrip',rt,'converged',converged, ...
        'force_stop_convergence',flags.convergence,'force_stop_fluctuation',flags.fluctuation, ...
        'criterion_reason',diagnostic.reason,'stop_reason',reason);
    assert(stop==(rt==20));
end
assert(first==6 && history(end).converged);
bad=field;bad(2)=NaN;
expect(@()check_convergence(energies,bad,freq,t,1e-3,false,settings,1,20),'check_convergence:NonFiniteField');
badE=energies;badE(3)=Inf;
expect(@()check_convergence(badE,field,freq,t,1e-3,false,settings,1,20),'check_convergence:NonFiniteEnergy');
check('real_H04_criterion_runs_all_twenty_and_keeps_first_six_and_finite_errors',true);

folder=fullfile(output_dir,'initialization');mkdir(folder);rng(0,'twister');
config=mamyshev_resolve_config();
context=struct('mode','synthetic_observation_initialization_fixture','run_id','observation_init', ...
    'source_identity',struct('kind','no_propagation_initialization_fixture'), ...
    'requested',struct('PumpPower',4,'cw2',1030,'plot_on',false),'seed',0, ...
    'design_config',config,'observation_options',fixed);
capture=MamyshevCapture(folder,context);
value=run_mamyshev_config(config,false,struct('capture',capture,'preflight_only',true,'observation_options',fixed));
assert(~value.propagation_started && isempty(capture.calls));
B=jsondecode(fileread(fullfile(folder,'configuration.json')));
A=jsondecode(fileread(fullfile(folder,'requested.json')));
assert(isequal(B.observation_options,fixed) && isequal(A.context.observation_options,fixed));
assert(B.configuration.max_rt==50 && B.configuration.Nt==32768 && B.configuration.time_window_ps==50);
for k=1:numel(history), capture.observation_round(history(k)); end
C=jsondecode(fileread(fullfile(folder,'runtime_calls.json')));
assert(isequal(C.observation_options,fixed) && numel(C.observation_history)==20 && ...
    C.observation_first_legacy_convergence_roundtrip==6 && ~C.backend_returned && isempty(C.segment_calls));
check('actual_no_propagation_initialization_and_tagged_fixture_history_wiring',true);

observation=struct('options',fixed,'history',history,'first_legacy_convergence_roundtrip',first, ...
    'stop_reason','observation_budget_reached');
input=struct('observation',observation,'rt_num',20,'converged',true,'force_stop',false, ...
    'pulse_survives',true,'ML_state',1,'energy_rel_fluct',0);
provenance=struct('physics_identity_id','synthetic_observation_fixture', ...
    'numerical_version','synthetic','source_kind','synthetic_control_fixture');
record=mamyshev_result_record(input,struct('job_status','completed','stop_reason',observation.stop_reason),provenance);
assert(strcmp(record.stop_reason,'observation_budget_reached') && record.legacy_flags.converged && ...
    strcmp(record.physical_state,'undetermined') && ~record.eligible_as_validated_training_truth);
record_path=fullfile(output_dir,'observation_control_record.json');write_mamyshev_record(record_path,record);
saved=jsondecode(fileread(record_path));assert(isequal(saved.observation.history,history(:)));
check('safe_result_budget_reason_keeps_true_old_flag_and_roundtrip_json',true);
report=struct('suite','observation_control','cases',cases,'all_passed',true, ...
    'initialization_attempts',1,'propagation_calls',0,'full_cavity_attempts',0, ...
    'artificial_criterion_rounds',20,'first_legacy_convergence_roundtrip',first);
mamyshev_write_diagnostic(fullfile(output_dir,'observation_control_tests.json'),report);
    function check(name,passed)
        assert(passed);cases(end+1)=struct('name',name,'passed',true);
    end
    function [stop,reason]=decision(options,rt,yes,f,e)
        [stop,reason]=mamyshev_observation_decision(options,rt,yes,f,e,.01,50);
    end
end
function expect(fn,prefix)
try,fn();catch exception,assert(startsWith(exception.identifier,prefix));return;end
error('ObservationTest:ExpectedFailure','Expected %s.',prefix);
end
