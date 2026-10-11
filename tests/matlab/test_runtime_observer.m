function report=test_runtime_observer(output_dir)
%TEST_RUNTIME_OBSERVER Short synthetic production paths, never a cavity run.
% Reuses the unchanged deterministic H01 fixture. Passive fixture is explicitly
% artificial: 32 points, 0.004 m, Raman/noise off. Physics defaults for the real
% cavity are never changed. Exact on/off equality is stricter than the existing
% 1e-12 absolute + 1e-12 relative deterministic comparison rule.
repo=fileparts(fileparts(fileparts(mfilename('fullpath'))));
addpath(fullfile(repo,'tests','matlab','helpers'));
addpath(fullfile(repo,'code','ml_bridge'));
addpath(genpath(fullfile(repo,'code','simulation_engine')));
f=gain_rollback_fixture();
identity=struct('run_id','observer_component_fixture', ...
    'source_kind','synthetic_observer_component_fixture');
saved_rng=rng; restore_rng=onCleanup(@()rng(saved_rng));
rng(17,'twister'); common_rng=rng;
cases=struct('name',{},'passed',{});

% Gain: absence vs independent observer, including actual disk writes.
gain_off=run_gain(f); gain_off_rng=rng;
rng(common_rng);
gain_observer=MamyshevObserver(fullfile(output_dir,'gain_observer.json'),identity);
gain_observer.begin_segment(1,'gain','synthetic_gain');
f_on=f; f_on.sim.readonly_observer=gain_observer;
gain_on=run_gain(f_on); gain_observer.complete_segment(); gain_on_rng=rng;
assert_equal_finite(gain_on,gain_off);
assert(isequal(gain_off_rng,gain_on_rng) && isequal(common_rng,gain_on_rng), ...
    'ObserverTest:RNGChanged');
gain_summary=gain_observer.summary();
assert_balanced(gain_summary,0);
assert(gain_summary.segments{1}.accepted_advanced_steps>1);
assert(gain_summary.segments{1}.runtime_resolutions{1}.initial_deltaZ==0.001);
assert(strcmp(gain_summary.segments{1}.runtime_resolutions{1}.extra.executing_source, ...
    fullfile(repo,'code','simulation_engine','GMMNLSE','Gain_rate_eqn','GMMNLSE_adaptive_rategain.m')));
cases(end+1)=struct('name','gain_absent_on_outputs_saved_state_rng_and_resolved_defaults','passed',true);

% The SAME existing active rejection mechanism is allowed only in synthetic
% tests; the read-only observer receives no control state and returns none.
rng(common_rng); [reject_off,forced_off]=controlled_gain(f,[]); reject_off_rng=rng;
rng(common_rng);
reject_observer=MamyshevObserver(fullfile(output_dir,'gain_reject_observer.json'),identity);
reject_observer.begin_segment(2,'gain','synthetic_gain_active_rejection');
[reject_on,forced_on]=controlled_gain(f,reject_observer);
reject_observer.complete_segment(); reject_on_rng=rng;
assert_equal_finite(reject_on,reject_off);
assert(forced_off==2 && forced_on==2 && isequal(reject_off_rng,reject_on_rng) && ...
    isequal(common_rng,reject_on_rng),'ObserverTest:ControlledRejection');
reject_summary=reject_observer.summary(); assert_balanced(reject_summary,2);
cases(end+1)=struct('name','gain_two_real_rejected_trials_counted_after_decision_rng_unchanged','passed',true);

% Passive path uses the actual dispatcher, loader and full propagation
% function, not a replacement kernel. Distinct pigtail segment identity.
passive_fiber=struct('L0',0.004,'MFD',10.5,'betas',[0;0;0.02]);
passive_sim=struct('gpu_yes',false,'single_yes',false,'gain_model',0, ...
    'pulse_centering',false,'progress_bar',false,'save_period',0.002, ...
    'Raman_model',0,'Raman_sponRS',false,'num_photon_noise_per_band',0);
passive_sim.adaptive_deltaZ=struct('model',true,'threshold',1e-6); % max resolved in production
[passive_fiber,passive_sim]=load_default_GMMNLSE_propagate(passive_fiber,passive_sim,'single_mode');
passive_initial=f.initial; passive_initial.fields=fft(passive_initial.fields);
gain_param={f.gain,f.cross_pump,f.cross_signal,f.overlap,f.N_total};
rng(common_rng); passive_off=GMMNLSE_propagate(passive_fiber,passive_initial,passive_sim,gain_param); passive_off_rng=rng;
rng(common_rng);
capture_dir=fullfile(output_dir,'runtime_calls_component'); mkdir(capture_dir);
capture_context=struct('run_id','synthetic_runtime_calls','mode','synthetic_observer_component', ...
    'source_identity',identity,'source_kind','synthetic_observer_component_fixture');
capture=MamyshevCapture(capture_dir,capture_context);
% Referenced fixture arrays are saved with their explicit synthetic identity;
% this is not a B initialization snapshot or a full-config preflight.
save(fullfile(capture_dir,'configuration.mat'),'gain_param','capture_context');
passive_observer=capture.observer;
passive_on_sim=passive_sim; passive_on_sim.readonly_observer=passive_observer;
capture.propagation_call(1,'passive_2',passive_fiber,passive_initial,passive_on_sim,gain_param);
passive_on=GMMNLSE_propagate(passive_fiber,passive_initial,passive_on_sim,gain_param);
passive_observer.complete_segment(); passive_on_rng=rng;
assert_equal_finite(rmfield(passive_on,'seconds'),rmfield(passive_off,'seconds'));
assert(isequal(passive_off_rng,passive_on_rng) && isequal(common_rng,passive_on_rng), ...
    'ObserverTest:PassiveRNGChanged');
capture.propagation_call(1,'pigtail',passive_fiber,passive_initial,passive_on_sim,{});
pigtail_on=GMMNLSE_propagate(passive_fiber,passive_initial,passive_on_sim);
passive_observer.complete_segment();
assert_equal_finite(rmfield(pigtail_on,'seconds'),rmfield(passive_off,'seconds'));
assert(isequal(rng,common_rng),'ObserverTest:PigtailRNGChanged');
passive_summary=passive_observer.summary(); assert_balanced(passive_summary,0);
assert(strcmp(passive_summary.segments{2}.segment_id,'pigtail'));
resolved=passive_summary.segments{1}.runtime_resolutions{1};
assert(resolved.max_deltaZ==passive_sim.save_period/10 && ...
    resolved.initial_deltaZ==passive_sim.save_period/100 && resolved.threshold==1e-6, ...
    'ObserverTest:RuntimeDefaultNotObserved');
assert(strcmp(resolved.extra.executing_source,fullfile(repo,'code','simulation_engine', ...
    'GMMNLSE','GMMNLSE algorithm','GMMNLSE_propagate_with_adaptive_deltaZ_RK4IP.m')));
cases(end+1)=struct('name','passive_and_pigtail_real_dispatcher_outputs_rng_counts_default_resolution','passed',true);

% Exercise C recording with exactly the arguments used above. The compressor
% observation method is tested on the actual short passive output; the
% compressor itself is deliberately NOT executed or presented as validated.
Nt=numel(passive_initial.fields); dt=passive_initial.dt;
time=((0:Nt-1)'-floor(Nt/2))*dt;
frequency=passive_sim.f0+((0:Nt-1)'-floor(Nt/2))/(Nt*dt);
compressor_field=pigtail_on.fields(:,:,end);
capture.compressor_call(time,frequency,compressor_field,'Treacy-t',pi/6,1e-6,false);
journal=jsondecode(fileread(fullfile(capture_dir,'runtime_calls.json')));
recorded=journal.segment_calls(1);
assert(recorded.roundtrip==1 && strcmp(recorded.segment_id,'passive_2') && ...
    recorded.fiber.L0==passive_fiber.L0 && recorded.sim.adaptive_deltaZ.threshold==passive_sim.adaptive_deltaZ.threshold);
assert(isequal(recorded.fiber.betas,passive_fiber.betas) && recorded.fiber.SR==passive_fiber.SR && ...
    recorded.dt_ps==passive_initial.dt && isequal(recorded.input_field_size(:)',size(passive_initial.fields)));
assert(recorded.gain_rate_eqn.t_rep==gain_param{1}.t_rep && ...
    ~isfield(recorded.sim,'readonly_observer') && isempty(journal.segment_calls(2).gain_rate_eqn));
assert(strcmp(journal.compressor_call.type,'Treacy-t') && journal.compressor_call.incident_angle_rad==pi/6 && ...
    journal.compressor_call.grating_spacing_m==1e-6 && ~journal.compressor_call.plot_on && ...
    isequal(journal.compressor_call.field_size(:)',size(compressor_field)));
assert(isequal(rng,common_rng),'ObserverTest:CallCaptureRNGChanged');
assert(~capture.summary().required_records_complete && ~capture.summary().initialization_observed);
cases(end+1)=struct('name','C_call_arguments_t_rep_pigtail_compressor_metadata_rng','passed',true);

% Active on-disk counts are unknown until a normal boundary flush. A fixture
% exception after the first real trial must remain incomplete, never completed.
pending_path=fullfile(output_dir,'pending_observer.json');
pending=MamyshevObserver(pending_path,identity); pending.begin_segment(1,'gain','synthetic_exception');
f_pending=f; f_pending.sim.readonly_observer=pending;
f_pending.sim.adaptive_deltaZ.test_hook=@stop_after_trial;
try
    run_gain(f_pending);
    error('ObserverTest:ExpectedExceptionMissing','Fixture did not throw.');
catch exception
    assert(strcmp(exception.identifier,'ObserverTest:AfterTrialStop'));
end
active=jsondecode(fileread(pending_path));
assert(~active.counts_complete && ~active.active_segment.normal_completion && ...
    isempty(active.active_segment.trials) && isempty(active.active_segment.accepted_advanced_steps), ...
    'ObserverTest:ActiveCountsNotNull');
pending.abort_segment('synthetic_after_trial_exception'); pending_summary=pending.summary();
partial=pending_summary.segments{1};
assert(~pending_summary.counts_complete && ~partial.normal_completion && ...
    partial.trials==1 && partial.pending_trials==1 && partial.accepted_advanced_steps==0, ...
    'ObserverTest:PendingTrialLost');
assert(isequal(rng,common_rng),'ObserverTest:PendingRNGChanged');
cases(end+1)=struct('name','active_disk_null_counts_and_exception_pending_trial_incomplete','passed',true);

report=struct('suite','runtime_observer','fixture_kind','synthetic_local_gain_and_passive', ...
    'full_cavity_runs',0,'physical_state','undetermined', ...
    'eligible_as_validated_training_truth',false,'cases',cases, ...
    'all_passed',all([cases.passed]),'comparison_tolerance',0, ...
    'excluded_comparison_field','passive output seconds is measured wall time', ...
    'gain',gain_summary,'controlled_rejections',reject_summary,'passive',passive_summary, ...
    'runtime_call_metadata',journal,'compressor_analysis_executed',false, ...
    'partial_exception',pending_summary, ...
    'not_verified',{{'full_cavity_integration','random_rejection_protocol','nonzero_counterpump','pulse_centering_gain_cache'}});
fid=fopen(fullfile(output_dir,'runtime_observer_tests.json'),'w'); assert(fid>=0);
cleanup=onCleanup(@()fclose(fid)); fprintf(fid,'%s\n',jsonencode(report,'PrettyPrint',true));
save(fullfile(output_dir,'runtime_observer_fixture_outputs.mat'),'gain_off','gain_on', ...
    'reject_off','reject_on','passive_off','passive_on','pigtail_on','common_rng', ...
    'gain_off_rng','gain_on_rng','reject_off_rng','reject_on_rng','passive_off_rng','passive_on_rng');
end

function result=run_gain(f)
[fields,power,save_i,save_z,save_deltaZ,T_delay,N2]=GMMNLSE_adaptive_rategain( ...
    f.sim,f.gain,f.cross_pump,f.cross_signal,f.overlap,f.N_total,f.FmFnN,f.GammaN, ...
    [0;0.004],zeros(2,1),2,0,zeros(2,1),f.initial,f.prefactor,f.omegas,f.D_op, ...
    f.SK_info,f.SRa_info,f.SRb_info,f.haw,f.hbw,f.sponRS_prefactor);
result=struct('fields',fields,'power',power,'save_i',save_i,'save_z',save_z, ...
    'save_deltaZ',save_deltaZ,'T_delay',T_delay,'N2',N2);
end

function [result,forced]=controlled_gain(f,observer)
forced=0; target_z=[]; prior_forward=[];
f.sim.adaptive_deltaZ.test_hook=@reject_twice;
if ~isempty(observer), f.sim.readonly_observer=observer; end
result=run_gain(f);
    function [success,next_step]=reject_twice(event,state,success,next_step)
        if strcmp(event,'before_trial')
            if isempty(target_z) && state.z>0, target_z=state.z; end
            prior_forward=state.pump_forward;
        elseif strcmp(event,'after_trial') && ~isempty(target_z) && state.z==target_z && forced<2
            assert(all(isfinite(state.signal(:))) && all(isfinite(state.N2(:))));
            assert(abs(state.pump_forward-prior_forward)>1e-9,'ObserverTest:IneffectiveRejectedTrial');
            success=false; next_step=state.deltaZ/2; forced=forced+1;
        end
    end
end

function [success,next_step]=stop_after_trial(event,~,success,next_step)
if strcmp(event,'after_trial'), error('ObserverTest:AfterTrialStop','Synthetic pending trial.'); end
end

function assert_balanced(summary,rejections)
assert(summary.counts_complete && summary.runtime_resolved_complete && isempty(summary.active_segment));
for k=1:numel(summary.segments)
    s=summary.segments{k};
    assert(s.normal_completion && s.counts_complete && s.pending_trials==0);
    assert(s.trials==s.rejections+s.accepted_advanced_steps && s.rejections==rejections && ...
        s.accepted_advanced_steps>0 && s.last_advanced_z_m==0.004);
end
end

function assert_equal_finite(a,b)
if isstruct(a)
    assert(isequal(fieldnames(a),fieldnames(b)) && isequal(size(a),size(b)));
    names=fieldnames(a);
    for j=1:numel(a), for k=1:numel(names), assert_equal_finite(a(j).(names{k}),b(j).(names{k})); end, end
elseif iscell(a)
    assert(isequal(size(a),size(b)));
    for k=1:numel(a), assert_equal_finite(a{k},b{k}); end
elseif isnumeric(a)
    assert(all(isfinite(a(:))) && all(isfinite(b(:))),'ObserverTest:NonfiniteComparison');
    assert(isequal(a,b),'ObserverTest:ObservedChangesProduction');
else
    assert(isequal(a,b),'ObserverTest:ObservedChangesMetadata');
end
end
