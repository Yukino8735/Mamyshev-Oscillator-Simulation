function report = test_gain_readiness(output_dir)
%TEST_GAIN_READINESS Deterministic local co-pump regression, never a cavity run.
% Uses the repair_001 32-point fixture unchanged. Only the explicit diagnostic
% gain-segment length/save endpoint is 0.004 m. Dispersion, Kerr and pump/rate
% updates remain real production computations. No mock solver is installed.
% Predeclared comparison rule (unchanged from test_gain_rollback): retry-start
% physical state must be exactly restored; deterministic accepted output uses
% max(abs(actual-reference)) <= 1e-12 + 1e-12*max(abs(reference)).
% B is the real RK4IP kernel supplied with A's production-reached noninitial
% state, not an independently executed outer gain loop or independent solver.
arguments
    output_dir (1,:) char
end
test_dir = fileparts(mfilename('fullpath'));
repo = fileparts(fileparts(test_dir));
addpath(fullfile(test_dir,'helpers'));
addpath(genpath(fullfile(repo,'code','simulation_engine')));
assert(~isfile(fullfile(output_dir,'h01_readiness.json')), ...
    'H01Readiness:ExistingEvidence','Refusing to overwrite this run evidence.');
if ~isfolder(output_dir), mkdir(output_dir); end
f = gain_rollback_fixture();
atol = 1e-12; rtol = 1e-12; segment_end = 0.004;
assert(~isfield(f.sim.adaptive_deltaZ,'test_hook'));
cases = struct('name',{},'passed',{},'identifier',{},'message',{});
report = struct('suite','gain_readiness','full_cavity_runs',0, ...
    'fixture_kind','artificial_deterministic_short_gain_segment', ...
    'fixture_grid_points',numel(f.initial.fields),'segment_end_m',segment_end, ...
    'absolute_tolerance',atol,'relative_tolerance',rtol,'restoration_tolerance',0, ...
    'comparison_B','original_production_RK4IP_from_A_captured_noninitial_start', ...
    'test_termination_exception_used',false,'physical_state','undetermined', ...
    'eligible_as_validated_training_truth',false, ...
    'random_rejection_protocol','not_verified','counterpump_nonzero_branch','not_verified', ...
    'whole_cavity_integration','not_executed');
try
    [A,A_return] = observed_segment(f,segment_end,true);
    [observed,observed_return] = observed_segment(f,segment_end,false);
    no_hook_return = run_segment(f,segment_end);
    origin_index = find(cellfun(@(s)s.z>0,A.before),1);
    assert(~isempty(origin_index),'H01Readiness:MissingNoninitialState');
    origin = A.before{origin_index};
    target_trials = find(cellfun(@(s)s.z==origin.z,A.before));
    assert(numel(target_trials)==3,'H01Readiness:TrialCount', ...
        'Expected two rejected trials then one accepted trial at the same real later start.');
    final_small_step = A.before{target_trials(end)}.deltaZ;
    [B,B_input] = direct_kernel(f,origin,final_small_step);
    add_case('reachable_noninitial_finite_state_and_cache',@reachable);
    add_case('two_rejections_restore_state_and_keep_smaller_step',@rollback);
    add_case('accepted_full_state_matches_direct_production_small_step',@small_step);
    add_case('short_gain_normal_return_advancement_and_saved_outputs',@normal_return);
    add_case('absent_hook_matches_pure_observer_normal_return',@absent_hook);
    report.cases = cases;
    report.passed = sum([cases.passed]); report.failed = sum(~[cases.passed]);
    report.all_passed = all([cases.passed]);
    report.production_origin = struct('z_m',origin.z,'last_deltaZ_m',origin.last_deltaZ, ...
        'a5_elements',numel(origin.a5),'a5_norm',norm(origin.a5(:)), ...
        'first_accepted_z_start_m',A.accepted{1}.z, ...
        'first_accepted_step_m',A.accepted{1}.deltaZ, ...
        'trial_steps_m',cellfun(@(s)s.deltaZ,A.before(target_trials)), ...
        'natural_trial_acceptance',A.original_success(target_trials), ...
        'forced_rejections',A.forced_rejections, ...
        'N2_is_trial_output_not_retry_input',true);
    report.normal_return = struct('A_accepted_steps',numel(A.accepted), ...
        'observer_accepted_steps',numel(observed.accepted), ...
        'A_saved_z_m',A_return.save_z,'observer_saved_z_m',observed_return.save_z, ...
        'A_save_i',A_return.save_i,'observer_save_i',observed_return.save_i, ...
        'save_points',2,'normal_returns',3, ...
        'N2_return_convention','stored final trial N2 divided by N_total');
    save(fullfile(output_dir,'h01_readiness_states.mat'), ...
        'f','A','A_return','observed','observed_return','no_hook_return', ...
        'origin','B','B_input','report');
catch exception
    report.all_passed = false;
    report.execution_error = struct('identifier',exception.identifier,'message',exception.message);
    save(fullfile(output_dir,'h01_readiness_partial.mat'));
    write_report(report);
    rethrow(exception);
end
write_report(report);
assert(report.all_passed,'H01Readiness:RegressionFailure', ...
    'Inspect failed assertions and full state evidence; failures are not passes.');

    function add_case(name,fn)
        item = struct('name',name,'passed',false,'identifier','','message','');
        try, fn(); item.passed=true;
        catch exception, item.identifier=exception.identifier; item.message=exception.message;
        end
        cases(end+1)=item;
    end
    function reachable()
        assert_finite_state(origin,{'signal','a5','pump_forward','pump_backward','z','deltaZ','last_deltaZ'});
        assert(~isempty(origin.a5) && norm(origin.a5(:))>0,'H01Readiness:MissingCache');
        assert(origin.z>0 && origin.z==A.accepted{1}.z+A.accepted{1}.deltaZ, ...
            'H01Readiness:UnadvancedOrigin');
        assert(origin.last_deltaZ==A.accepted{1}.deltaZ,'H01Readiness:WrongPriorStep');
        names={'signal','a5','pump_forward','pump_backward'};
        require_exact(origin,A.accepted{1},names);
        % The first accepted trial has returned to the actual outer loop; z,
        % last_deltaZ and the nonlinear cache have all advanced before capture.
        assert(A.original_success(1) && origin_index==2,'H01Readiness:InitialStepControl');
        require_exact(origin,B_input,{'signal','a5','pump_forward','pump_backward','z','last_deltaZ'});
        assert(B_input.deltaZ==final_small_step,'H01Readiness:WrongDirectStep');
    end
    function rollback()
        assert(A.forced_rejections==2 && all(A.original_success(target_trials)), ...
            'H01Readiness:UnexpectedNaturalRejection');
        names={'signal','a5','pump_forward','pump_backward','z','last_deltaZ'};
        leaks=zeros(1,2); changes=zeros(1,2);
        for k=1:2
            j=target_trials(k); next=target_trials(k+1);
            assert_finite_state(A.before{j},names);
            assert_finite_state(A.after{j},{'signal','a5','pump_forward','pump_backward','N2'});
            assert_finite_state(A.before{next},names);
            require_exact(A.before{next},origin,names);
            changes(k)=A.after{j}.pump_forward-A.before{j}.pump_forward;
            leaks(k)=A.before{next}.pump_forward-origin.pump_forward;
            assert(abs(changes(k))>1e-9,'H01Readiness:IneffectivePumpTrial');
            assert(A.before{next}.deltaZ==A.before{j}.deltaZ/2 && ...
                A.before{next}.deltaZ<A.before{j}.deltaZ,'H01Readiness:LostRetryStep');
        end
        report.rejected_trial_pump_changes_W=changes;
        report.retry_pump_leaks_W=leaks;
        report.retry_start_exact_fields=names;
    end
    function small_step()
        second_accept = A.accepted{2};
        assert(second_accept.z==origin.z && second_accept.deltaZ==final_small_step, ...
            'H01Readiness:WrongAcceptedTrial');
        names={'signal','a5','pump_forward','pump_backward','N2','last_deltaZ'};
        assert_finite_state(second_accept,names); assert_finite_state(B,names);
        report.small_step_comparison=compare_states(second_accept,B,names,atol,rtol);
        assert(all(structfun(@(x)x.passed,report.small_step_comparison)), ...
            'H01Readiness:SmallStepDifference');
    end
    function normal_return()
        report.A_return_checks=check_return(A,A_return,f,segment_end,atol,rtol);
        report.observer_return_checks=check_return(observed,observed_return,f,segment_end,atol,rtol);
    end
    function absent_hook()
        names={'fields','save_i','save_z','save_deltaZ','T_delay','N2'};
        assert_finite_state(observed_return,names); assert_finite_state(no_hook_return,names);
        report.absent_hook_comparison=compare_states(observed_return,no_hook_return,names,atol,rtol);
        report.absent_hook_pump_comparison=compare_states(observed_return.power,no_hook_return.power, ...
            {'pump_forward','pump_backward'},atol,rtol);
        assert(all(structfun(@(x)x.passed,report.absent_hook_comparison)) && ...
            all(structfun(@(x)x.passed,report.absent_hook_pump_comparison)), ...
            'H01Readiness:ObserverChangesProduction');
    end
    function write_report(value)
        fid=fopen(fullfile(output_dir,'h01_readiness.json'),'w');
        assert(fid>=0,'H01Readiness:Output','Cannot open readiness report.');
        cleanup=onCleanup(@()fclose(fid));
        fprintf(fid,'%s\n',jsonencode(value,'PrettyPrint',true));
        disp(jsonencode(value,'PrettyPrint',true));
    end
end

function [trace,result] = observed_segment(f,segment_end,inject_two_rejections)
trace=struct('before',{{}},'after',{{}},'accepted',{{}}, ...
    'original_success',[],'original_opt_deltaZ',[],'forced_rejections',0);
target_z=[];
f.sim.adaptive_deltaZ.test_hook=@observe;
result=run_segment(f,segment_end);
    function [success,next_step]=observe(event,state,success,next_step)
        switch event
            case 'before_trial'
                assert_finite_state(state,{'signal','a5','pump_forward','pump_backward','z','deltaZ','last_deltaZ'});
                trace.before{end+1}=state;
                assert(numel(trace.before)<=20,'H01Readiness:FixtureTrialLimit');
                if isempty(target_z) && state.z>0, target_z=state.z; end
            case 'after_trial'
                assert_finite_state(state,{'signal','a5','pump_forward','pump_backward','N2'});
                trace.after{end+1}=state;
                trace.original_success(end+1)=success;
                trace.original_opt_deltaZ(end+1)=next_step;
                if inject_two_rejections && ~isempty(target_z) && state.z==target_z && trace.forced_rejections<2
                    % Only rejection/retry control is injected, and only after
                    % the unmodified kernel has updated the real field/pumps.
                    success=false; next_step=state.deltaZ/2;
                    trace.forced_rejections=trace.forced_rejections+1;
                end
            case 'after_accept'
                assert_finite_state(state,{'signal','a5','pump_forward','pump_backward','N2','last_deltaZ'});
                trace.accepted{end+1}=state;
                % Continue production centering, z update, saving and return.
        end
    end
end

function result=run_segment(f,segment_end)
[fields,power,save_i,save_z,save_deltaZ,T_delay,N2] = ...
    GMMNLSE_adaptive_rategain(f.sim,f.gain, ...
    f.cross_pump,f.cross_signal,f.overlap,f.N_total,f.FmFnN,f.GammaN, ...
    [0;segment_end],zeros(2,1),2,0,zeros(2,1),f.initial, ...
    f.prefactor,f.omegas,f.D_op,f.SK_info,f.SRa_info,f.SRb_info, ...
    f.haw,f.hbw,f.sponRS_prefactor);
result=struct('fields',fields,'power',power,'save_i',save_i,'save_z',save_z, ...
    'save_deltaZ',save_deltaZ,'T_delay',T_delay,'N2',N2);
end

function [state,input]=direct_kernel(f,origin,step)
% Source every cached/physical state from a genuinely reached later start.
input=origin; input.deltaZ=step;
sim=f.sim; sim.deltaZ=step; sim.last_deltaZ=origin.last_deltaZ;
assert_finite_state(input,{'signal','a5','pump_forward','pump_backward','z','deltaZ','last_deltaZ'});
[signal,a5,pump_forward,pump_backward,opt_deltaZ,success,N2] = ...
    GMMNLSE_RK4IP_rategain_adaptive(origin.signal,f.initial.dt,sim,f.gain, ...
    f.SK_info,f.SRa_info,f.SRb_info,f.haw,f.hbw,f.sponRS_prefactor, ...
    f.prefactor,f.omegas,f.D_op,f.cross_pump,f.cross_signal,f.overlap, ...
    f.N_total,f.FmFnN,f.GammaN,origin.pump_forward,origin.pump_backward,origin.a5,f.dummy);
assert(success,'H01Readiness:DirectKernelRejected');
state=struct('signal',signal,'a5',a5,'pump_forward',pump_forward, ...
    'pump_backward',pump_backward,'N2',N2,'opt_deltaZ',opt_deltaZ, ...
    'z',origin.z,'deltaZ',step,'last_deltaZ',step);
end

function checks=check_return(trace,result,f,segment_end,atol,rtol)
assert(numel(trace.accepted)>=2,'H01Readiness:InsufficientAcceptedSteps');
names={'fields','save_i','save_z','save_deltaZ','T_delay','N2'};
assert_finite_state(result,names);
assert_finite_state(result.power,{'pump_forward','pump_backward'});
for k=2:numel(trace.accepted)
    previous=trace.accepted{k-1}; current=trace.accepted{k};
    assert(current.z==previous.z+previous.deltaZ,'H01Readiness:WrongProgression');
end
last=trace.accepted{end};
assert(last.z+last.deltaZ==segment_end && result.save_z(end)==segment_end, ...
    'H01Readiness:WrongReturnEndpoint');
assert(result.save_i==3 && isequal(size(result.fields),[numel(f.initial.fields),1,2]), ...
    'H01Readiness:WrongSavedShape');
assert(result.save_deltaZ(1)==last.deltaZ && result.T_delay(end)==0, ...
    'H01Readiness:WrongSavedControlState');
actual=struct('signal',result.fields(:,:,end),'pump_forward',result.power.pump_forward(:,:,end), ...
    'pump_backward',result.power.pump_backward(:,:,end),'N2',result.N2(:,:,end));
expected=struct('signal',fft(last.signal),'pump_forward',last.pump_forward, ...
    'pump_backward',last.pump_backward,'N2',last.N2(:,:,1,1,1)/max(f.N_total(:)));
checks=compare_states(actual,expected,{'signal','pump_forward','pump_backward','N2'},atol,rtol);
assert(all(structfun(@(x)x.passed,checks)),'H01Readiness:WrongSavedOutput');
initial=struct('signal',result.fields(:,:,1),'pump_forward',result.power.pump_forward(:,:,1), ...
    'pump_backward',result.power.pump_backward(:,:,1));
expected_initial=struct('signal',fft(f.initial.fields),'pump_forward',f.gain.copump_power, ...
    'pump_backward',f.gain.counterpump_power);
initial_checks=compare_states(initial,expected_initial,{'signal','pump_forward','pump_backward'},atol,rtol);
assert(all(structfun(@(x)x.passed,initial_checks)),'H01Readiness:WrongSavedInitial');
checks.initial=initial_checks;
end

function assert_finite_state(value,names)
for k=1:numel(names)
    data=value.(names{k});
    assert(all(isfinite(data(:))),'H01Readiness:NonFiniteState', ...
        'Nonfinite %s must fail before an equality/error comparison.',names{k});
end
end

function require_exact(actual,reference,names)
assert_finite_state(actual,names); assert_finite_state(reference,names);
for k=1:numel(names)
    assert(isequaln(actual.(names{k}),reference.(names{k})), ...
        'H01Readiness:StateNotExactlyRestored','State %s differed.',names{k});
end
end

function differences=compare_states(actual,reference,names,atol,rtol)
% Finiteness is an explicit prerequisite, including complex real/imag parts.
assert_finite_state(actual,names); assert_finite_state(reference,names);
differences=struct();
for k=1:numel(names)
    name=names{k}; a=actual.(name); b=reference.(name);
    assert(isequal(size(a),size(b)),'H01Readiness:StateShape','Shape differed for %s.',name);
    delta=max(abs(a(:)-b(:))); scale=max(abs(b(:)));
    if isempty(delta), delta=0; scale=0; end
    limit=atol+rtol*scale;
    differences.(name)=struct('max_absolute_difference',delta,'allowed_difference',limit, ...
        'exactly_equal',isequaln(a,b),'passed',delta<=limit);
end
end
