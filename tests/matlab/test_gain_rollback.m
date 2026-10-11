function report = test_gain_rollback(mode, output_dir)
%TEST_GAIN_ROLLBACK Exercise actual adaptive gain trial/retry production logic.
% mode='reproduce' records expected assertions violated by the original code;
% mode='regression' requires the fixed implementation to satisfy all assertions.
% This is an artificial deterministic test fixture, never a cavity run/data row.
% Predeclared tolerances: restored state must be isequaln (zero tolerance).
% Deterministic accepted field, derivative, pump, and N2 comparisons use
% abs_error <= 1e-12 + 1e-12*max(abs(reference)); this allows double roundoff
% while remaining many orders below the expected old pump-state leakage.
arguments
    mode (1,:) char {mustBeMember(mode,{'reproduce','regression'})}
    output_dir (1,:) char
end
test_dir = fileparts(mfilename('fullpath'));
repo = fileparts(fileparts(test_dir));
addpath(fullfile(test_dir,'helpers'));
addpath(genpath(fullfile(repo,'code','simulation_engine')));
if ~isfolder(output_dir), mkdir(output_dir); end
f = gain_rollback_fixture();
atol = 1e-12; rtol = 1e-12;
small_step = 0.0005;
reject = observe_step(f,true,small_step);
small = f; small.sim.adaptive_deltaZ.max_deltaZ = 10*small_step;
direct_small = observe_step(small,false,small_step);
control = observe_step(f,false,small_step);
kernel = direct_kernel(f);

assert(numel(reject.before)==2,'H01:FixtureTrials','Expected exactly one rejected trial and one accepted trial.');
assert(numel(direct_small.before)==1 && numel(control.before)==1,...
    'H01:FixtureControl','Control fixture unexpectedly rejected a real numerical step.');
assert(reject.original_success(1) && reject.original_success(2),...
    'H01:FixtureAcceptance','Fixture expected natural numerical acceptance before forced rejection.');
fields_to_restore = {'signal','a5','pump_forward','pump_backward'};
restored = struct();
for i = 1:numel(fields_to_restore)
    name = fields_to_restore{i};
    restored.(name) = isequaln(reject.before{1}.(name),reject.before{2}.(name));
end
restored.z = isequal(reject.before{1}.z,reject.before{2}.z);
restored.last_deltaZ = isequal(reject.before{1}.last_deltaZ,reject.before{2}.last_deltaZ);
pump_change = reject.after{1}.pump_forward-reject.before{1}.pump_forward;
pump_leak = reject.before{2}.pump_forward-reject.before{1}.pump_forward;
comparison_fields = {'signal','a5','pump_forward','pump_backward','N2'};
[small_matches,small_differences] = compare_states(reject.accepted,direct_small.accepted,...
    comparison_fields,atol,rtol);
[control_matches,control_differences] = compare_states(control.accepted,kernel,...
    comparison_fields,atol,rtol);
assertions = struct('production_pump_changed',abs(pump_change)>1e-9,...
    'rejected_state_restored_exactly',all(structfun(@(x)x,restored)),...
    'retry_step_preserved',reject.before{2}.deltaZ==small_step && reject.before{2}.deltaZ<reject.before{1}.deltaZ,...
    'reject_then_small_matches_direct_small',small_matches,...
    'no_rejection_matches_direct_production_kernel',control_matches);
guard_results = struct();
if strcmp(mode,'regression')
    guard_results = check_retry_guards(f);
    assertions.invalid_retry_fails_explicitly = all(structfun(@(x)x.passed,guard_results));
end
report = struct('fixture_kind','artificial_deterministic_single_gain_step',...
    'mode',mode,'full_cavity_runs',0,'production_functions',{{...
    'GMMNLSE_adaptive_rategain','GMMNLSE_RK4IP_rategain_adaptive','solve_gain_rate_eqn_RK4IP'}},...
    'absolute_tolerance',atol,'relative_tolerance',rtol,'restoration_tolerance',0,...
    'assertions',assertions,'restored_fields',restored,...
    'first_trial_pump_change_W',pump_change,'retry_pump_leak_W',pump_leak,...
    'small_step_comparison',small_differences,'control_comparison',control_differences,...
    'retry_guard_results',guard_results,...
    'random_rejection_protocol','not_verified','counterpump_nonzero_branch','not_verified');
report.failed_regression_assertions = fieldnames(assertions);
report.failed_regression_assertions = report.failed_regression_assertions(~structfun(@(x)x,assertions));
report.all_regression_assertions_passed = isempty(report.failed_regression_assertions);
report.original_defect_reproduced = ~restored.pump_forward && abs(pump_leak)>1e-9 && ~small_matches;
save(fullfile(output_dir,['h01_' mode '_states.mat']),...
    'f','reject','direct_small','control','kernel','report');
fid = fopen(fullfile(output_dir,['h01_' mode '.json']),'w');
assert(fid>=0,'H01:Output','Cannot open report JSON.');
cleanup = onCleanup(@()fclose(fid));
fprintf(fid,'%s\n',jsonencode(report,'PrettyPrint',true));
disp(jsonencode(report,'PrettyPrint',true));
if strcmp(mode,'reproduce')
    assert(report.original_defect_reproduced,'H01:ExpectedDefectNotReproduced',...
        'Original defect was not reproduced; do not treat this as failure evidence.');
else
    assert(report.all_regression_assertions_passed,'H01:RegressionFailure',...
        'State rollback regression assertions failed; inspect recorded full states.');
end
end

function results = check_retry_guards(f)
% Each injected controller failure follows a real production gain trial.
cases = struct('nan',NaN,'zero',0,'unchanged',f.sim.deltaZ);
names = fieldnames(cases); results = struct();
for i = 1:numel(names)
    name = names{i}; bad_step = cases.(name); trial_count = 0;
    f.sim.adaptive_deltaZ.test_hook = @inject;
    caught = '';
    try
        GMMNLSE_adaptive_rategain(f.sim,f.gain,...
            f.cross_pump,f.cross_signal,f.overlap,f.N_total,f.FmFnN,f.GammaN,...
            [0;0.002],zeros(2,1),2,0,zeros(2,1),f.initial,...
            f.prefactor,f.omegas,f.D_op,f.SK_info,f.SRa_info,f.SRb_info,...
            f.haw,f.hbw,f.sponRS_prefactor);
    catch err
        caught = err.identifier;
    end
    results.(name) = struct('passed',strcmp(caught,...
        'GMMNLSE_adaptive_rategain:NonProgressingRetry') && trial_count==1,...
        'error_identifier',caught,'real_trials',trial_count);
end
    function [success,next_step] = inject(event,~,success,next_step)
        if strcmp(event,'before_trial') && trial_count>=1
            error('H01:FixtureMissingGuard','Guard did not stop before an invalid retry.');
        elseif strcmp(event,'after_trial')
            trial_count = trial_count+1;
            success = false; next_step = bad_step;
        end
    end
end

function traces = observe_step(f,force_rejection,small_step)
traces = struct('before',{{}},'after',{{}},'original_success',[],...
    'original_opt_deltaZ',[],'accepted',[]);
f.sim.adaptive_deltaZ.test_hook = @observe;
try
    GMMNLSE_adaptive_rategain(f.sim,f.gain,...
        f.cross_pump,f.cross_signal,f.overlap,f.N_total,f.FmFnN,f.GammaN,...
        [0;0.002],zeros(2,1),2,0,zeros(2,1),f.initial,...
        f.prefactor,f.omegas,f.D_op,f.SK_info,f.SRa_info,f.SRb_info,...
        f.haw,f.hbw,f.sponRS_prefactor);
    error('H01:FixtureDidNotStop','Expected fixture observer to stop after one accepted step.');
catch err
    if ~strcmp(err.identifier,'H01:FixtureAcceptedStepCaptured'), rethrow(err); end
end
    function [success,next_step] = observe(event,state,success,next_step)
        switch event
            case 'before_trial'
                traces.before{end+1} = state;
                assert(numel(traces.before)<=3,'H01:FixtureTrialLimit','Unexpected repeated rejection.');
            case 'after_trial'
                traces.after{end+1} = state;
                traces.original_success(end+1) = success;
                traces.original_opt_deltaZ(end+1) = next_step;
                if force_rejection && numel(traces.after)==1
                    success = false; next_step = small_step;
                end
            case 'after_accept'
                traces.accepted = state;
                error('H01:FixtureAcceptedStepCaptured','Fixture stopped after capturing the accepted gain step.');
        end
    end
end

function state = direct_kernel(f)
[signal,a5,pump_forward,pump_backward,opt_deltaZ,success,N2] = ...
    GMMNLSE_RK4IP_rategain_adaptive(f.initial.fields,f.initial.dt,f.sim,f.gain,...
    f.SK_info,f.SRa_info,f.SRb_info,f.haw,f.hbw,f.sponRS_prefactor,...
    f.prefactor,f.omegas,f.D_op,f.cross_pump,f.cross_signal,f.overlap,...
    f.N_total,f.FmFnN,f.GammaN,f.gain.copump_power,0,[],f.dummy);
assert(success,'H01:KernelControl','Direct original production kernel did not accept the fixture.');
state = struct('signal',signal,'a5',a5,'pump_forward',pump_forward,...
    'pump_backward',pump_backward,'N2',N2,'opt_deltaZ',opt_deltaZ);
end

function [all_match,differences] = compare_states(actual,reference,names,atol,rtol)
all_match = true; differences = struct();
for i = 1:numel(names)
    name = names{i}; a = actual.(name); b = reference.(name);
    delta = max(abs(a(:)-b(:))); scale = max(abs(b(:)));
    if isempty(delta), delta=0; scale=0; end
    limit = atol+rtol*scale;
    passed = all(isfinite(a(:))) && all(isfinite(b(:))) && delta<=limit;
    differences.(name) = struct('max_absolute_difference',delta,'allowed_difference',limit,...
        'exactly_equal',isequaln(a,b),'passed',passed);
    all_match = all_match && passed;
end
end
