function report = test_result_contract(output_dir)
%TEST_RESULT_CONTRACT Real record/JSON functions, synthetic fields; no cavity.
% Status, IDs and missing values compare exactly. Derived scalar arithmetic
% uses 1e-12 relative/absolute tolerance for deterministic double operations.
root = fileparts(fileparts(fileparts(mfilename('fullpath'))));
addpath(fullfile(root,'code','ml_bridge'));
addpath(fullfile(root,'code')); setup_mamyshev_project();
provenance = struct('physics_identity_id','legacy_ring_phase1_v1', ...
    'numerical_version','synthetic_fixture_not_a_backend_run','source_kind','synthetic_contract_fixture');
t = linspace(-8,8,256)'; field = 2*exp(-t.^2).*exp(0.2i*t.^2);
legacy = struct('t',t,'output_field',field,'pigtail_output_field',0.7*field, ...
    'output_energy',trapz(t,abs(field).^2)/1000,'fwhm_ps',1.2, ...
    'dechirped_fwhm_fs',40,'dechirped_peak_power_W',100, ...
    'transform_limited_fwhm_fs',35,'rt_num',6,'converged',true, ...
    'force_stop',false,'pulse_survives',true,'ML_state',1,'energy_rel_fluct',0);
completed = struct('job_status','completed','max_rt',50);
cases = struct('name',{},'passed',{},'identifier',{},'message',{});
add_case('legacy_success_is_not_stable_single',@legacy_success);
add_case('separate_output_planes_and_true_field_peak',@planes);
add_case('compressed_field_energy_null_reason_roundtrip',@serialized_missing);
add_case('record_writer_refuses_existing_evidence',@overwrite);
add_case('max_rt_is_observation_stop_not_instability',@max_rt);
add_case('insufficient_observation_is_separate',@insufficient);
add_case('timeout_and_cancellation_do_not_return_final_metrics',@operational);
add_case('partial_nonfinite_observation_preserves_stop_reason',@partial_nonfinite);
add_case('noninteger_round_count_not_recorded_as_completed',@invalid_round_count);
add_case('field_power_overflow_is_traceable_numerical_failure',@power_overflow);
add_case('original_cancel_exception_maps_to_cancelled',@user_cancel);
add_case('actual_nonfinite_error_mapped_serialized',@nonfinite_error);
add_case('nonfinite_returned_field_cannot_be_completed',@nonfinite_result);
add_case('nonfinite_energy_cannot_be_completed',@nonfinite_energy);
add_case('rejected_step_no_progress_maps_numerical_error',@no_progress);
add_case('execution_exception_is_not_physical_instability',@execution_error);
add_case('same_energy_single_double_no_stable_single',@single_double);
add_case('empty_failed_result_metrics_remain_null',@failed_empty);
add_case('missing_provenance_rejected',@missing_provenance);
add_case('saved_phase1_result_readonly_legacy_identity',@historical);
report = struct('suite','result_contract','full_cavity_runs',0,'fixture_only',true, ...
    'historical_read_is_new_simulation',false,'cases',cases, ...
    'passed',sum([cases.passed]),'failed',sum(~[cases.passed]),'all_passed',all([cases.passed]));

    function add_case(name,fn)
        item = struct('name',name,'passed',false,'identifier','','message','');
        try, fn(); item.passed = true;
        catch exception, item.identifier = exception.identifier; item.message = exception.message;
        end
        cases(end+1)=item;
    end
    function assert_safe(r)
        assert(strcmp(r.physical_state,'undetermined'));
        assert(strcmp(r.numerical_validation.status,'not_verified'));
        assert(~r.eligible_as_validated_training_truth);
        assert(strcmp(r.result_protocol_version,'safe_result_v1'));
    end
    function legacy_success()
        r = mamyshev_result_record(legacy,completed,provenance);
        assert_safe(r); assert(strcmp(r.job_status,'completed'));
        assert(strcmp(r.stop_reason,'legacy_energy_convergence'));
        assert(r.legacy_flags.ML_state==1 && r.legacy_flags.converged);
        assert(strcmp(r.provenance.physics_identity_id,'legacy_ring_phase1_v1'));
        assert(~strcmp(r.provenance.numerical_version,r.result_protocol_version));
    end
    function planes()
        r = mamyshev_result_record(legacy,completed,provenance);
        raw=r.outputs.sf1_rejected_raw; tail=r.outputs.pigtail_raw; comp=r.outputs.compressed_analysis;
        assert(abs(raw.peak_power.value-max(abs(field).^2))<=1e-12);
        assert(abs(tail.peak_power.value-max(abs(0.7*field).^2))<=1e-12);
        assert(abs(tail.energy.value-trapz(t,abs(0.7*field).^2)/1000)<=1e-12);
        assert(~strcmp(raw.fwhm.definition,comp.fwhm.definition));
        assert(strcmp(raw.fwhm.unit,'ps') && strcmp(comp.fwhm.unit,'fs'));
        assert(comp.peak_power.value==100 && strcmp(comp.peak_power.unit,'W'));
        assert(raw.energy.value==legacy.output_energy && isnan(comp.energy.value));
    end
    function serialized_missing()
        r = mamyshev_result_record(legacy,completed,provenance);
        path=fullfile(output_dir,'contract_success.json');
        write_mamyshev_record(path,r); text=fileread(path); decoded=jsondecode(text);
        assert(contains(text,'"value":null'));
        assert(~contains(text,':NaN') && ~contains(text,':Infinity'));
        assert(isempty(decoded.outputs.compressed_analysis.energy.value));
        assert(isempty(decoded.outputs.compressed_analysis.field.value));
        assert(~isempty(decoded.outputs.compressed_analysis.energy.missing_reason));
        assert(~isempty(decoded.outputs.compressed_analysis.field.missing_reason));
        assert_safe(decoded);
    end
    function overwrite()
        r=mamyshev_result_record(legacy,completed,provenance);
        expect_id(@()write_mamyshev_record(fullfile(output_dir,'contract_success.json'),r), ...
            'MamyshevRecord:ExistingRecord');
    end
    function max_rt()
        value=legacy; value.converged=false; value.rt_num=50;
        r=mamyshev_result_record(value,completed,provenance);
        assert_safe(r); assert(strcmp(r.job_status,'completed') && strcmp(r.stop_reason,'max_rt_reached'));
    end
    function insufficient()
        value=legacy; value.converged=false; value.rt_num=2;
        r=mamyshev_result_record(value,completed,provenance);
        assert_safe(r); assert(strcmp(r.stop_reason,'insufficient_observation'));
    end
    function operational()
        statuses={'timeout','cancelled'};
        for k=1:numel(statuses)
            r=mamyshev_result_record(legacy,struct('job_status',statuses{k}),provenance);
            assert_safe(r); assert(strcmp(r.job_status,statuses{k}));
            assert(isnan(r.outputs.sf1_rejected_raw.energy.value));
            assert(isnan(r.outputs.compressed_analysis.peak_power.value));
            write_mamyshev_record(fullfile(output_dir,['contract_' statuses{k} '.json']),r);
        end
    end
    function nonfinite_error()
        try
            check_convergence(nan(6,1),field,zeros(size(t)),t,1e-3,false);
            error('ContractTest:MissingError','Expected actual production helper to throw.');
        catch exception
            assert(strcmp(exception.identifier,'check_convergence:NonFiniteEnergy'));
            execution=mamyshev_failure_status(exception);
        end
        r=mamyshev_result_record(struct(),execution,provenance);
        assert_safe(r); assert(strcmp(r.job_status,'failed') && strcmp(r.stop_reason,'numerical_error'));
        assert(strcmp(r.failure_reason.identifier,'check_convergence:NonFiniteEnergy'));
        write_mamyshev_record(fullfile(output_dir,'contract_numerical_error.json'),r);
        decoded=jsondecode(fileread(fullfile(output_dir,'contract_numerical_error.json')));
        assert(isempty(decoded.outputs.sf1_rejected_raw.energy.value));
        assert(strcmp(decoded.physical_state,'undetermined'));
    end
    function invalid_round_count()
        value=legacy; value.rt_num=6.5;
        r=mamyshev_result_record(value,completed,provenance);
        assert(isnan(r.completed_roundtrips));
        assert(contains(r.completed_roundtrips_missing_reason,'integer'));
    end
    function power_overflow()
        value=legacy; value.output_field(1)=realmax;
        try
            mamyshev_result_record(value,completed,provenance);
            error('ContractTest:MissingError','Expected overflow to throw.');
        catch exception
            assert(strcmp(exception.identifier,'MamyshevRecord:NonFinitePower'));
            r=mamyshev_result_record(value,mamyshev_failure_status(exception),provenance);
        end
        assert_safe(r); assert(strcmp(r.stop_reason,'numerical_error'));
        assert(strcmp(r.failure_reason.identifier,'MamyshevRecord:NonFinitePower'));
        assert(r.completed_roundtrips==6 && r.legacy_flags.ML_state==1);
        assert(isnan(r.outputs.sf1_rejected_raw.peak_power.value));
    end
    function user_cancel()
        execution=mamyshev_failure_status(MException('GMMNLSE_propagate:ProgressBarBreak','Fixture cancel.'));
        r=mamyshev_result_record(struct(),execution,provenance); assert_safe(r);
        assert(strcmp(r.job_status,'cancelled') && strcmp(r.stop_reason,'user_cancelled'));
    end
    function partial_nonfinite()
        statuses={'timeout','cancelled','failed'};
        for k=1:numel(statuses)
            value=legacy; value.output_field(1)=NaN;
            execution=struct('job_status',statuses{k},'stop_reason','original_stop', ...
                'failure_reason',struct('identifier','Fixture:OriginalReason','message','Preserve this diagnosis.'));
            r=mamyshev_result_record(value,execution,provenance); assert_safe(r);
            assert(strcmp(r.job_status,statuses{k}) && strcmp(r.stop_reason,'original_stop'));
            assert(strcmp(r.failure_reason.identifier,'Fixture:OriginalReason'));
            assert(r.completed_roundtrips==6 && r.legacy_flags.ML_state==1);
            assert(isfield(r.observation_diagnostics,'nonfinite'));
            assert(isnan(r.outputs.sf1_rejected_raw.energy.value));
        end
    end
    function nonfinite_result()
        value=legacy; value.output_field(1)=Inf;
        r=mamyshev_result_record(value,completed,provenance);
        assert_safe(r); assert(strcmp(r.job_status,'failed') && strcmp(r.stop_reason,'numerical_error'));
    end
    function nonfinite_energy()
        value=legacy; value.output_energy=NaN;
        r=mamyshev_result_record(value,completed,provenance);
        assert_safe(r); assert(strcmp(r.job_status,'failed') && strcmp(r.stop_reason,'numerical_error'));
    end
    function no_progress()
        execution=mamyshev_failure_status(MException('GMMNLSE_adaptive_rategain:NonProgressingRetry','Fixture failure.'));
        r=mamyshev_result_record(struct(),execution,provenance);
        assert_safe(r); assert(strcmp(r.stop_reason,'numerical_error'));
    end
    function execution_error()
        execution=mamyshev_failure_status(MException('Fixture:DependencyError','Fixture only.'));
        r=mamyshev_result_record(struct(),execution,provenance);
        assert_safe(r); assert(strcmp(r.stop_reason,'execution_error'));
    end
    function single_double()
        second=exp(-(t-3).^2)+exp(-(t+3).^2);
        second=second*sqrt(sum(abs(field).^2)/sum(abs(second).^2));
        values={field,second};
        for k=1:2
            yes=check_convergence(ones(6,1),values{k},zeros(size(t)),t,1e-3,false);
            assert(yes); value=legacy; value.converged=yes; value.output_field=values{k};
            r=mamyshev_result_record(value,completed,provenance); assert_safe(r);
        end
    end
    function failed_empty()
        r=mamyshev_result_record(struct(),struct('job_status','failed','stop_reason','execution_error'),provenance);
        assert_safe(r); assert(isnan(r.completed_roundtrips));
        assert(isnan(r.outputs.sf1_rejected_raw.peak_power.value));
        assert(~isempty(r.outputs.sf1_rejected_raw.peak_power.missing_reason));
    end
    function missing_provenance()
        expect_id(@()mamyshev_result_record(legacy,completed,struct()),'MamyshevRecord:MissingProvenance');
    end
    function historical()
        path=fullfile(root,'reports','local','phase1','baseline_001','result.mat');
        if ~isfile(path)
            error('ContractTest:MissingHistoricalArtifact','Read-only historical check not executed: Phase 1 artifact absent.');
        end
        saved=load(path,'result');
        p=provenance; p.numerical_version='legacy_pre_repair_phase1'; p.source_kind='read_only_phase1_artifact';
        r=mamyshev_result_record(saved.result,completed,p); assert_safe(r);
        assert(r.outputs.sf1_rejected_raw.energy.value==saved.result.output_energy);
        assert(r.outputs.compressed_analysis.peak_power.value==saved.result.dechirped_peak_power_W);
        assert(isnan(r.outputs.compressed_analysis.energy.value));
        write_mamyshev_record(fullfile(output_dir,'phase1_readonly_contract.json'),r);
        decoded=jsondecode(fileread(fullfile(output_dir,'phase1_readonly_contract.json')));
        assert(strcmp(decoded.provenance.numerical_version,'legacy_pre_repair_phase1'));
        assert(strcmp(decoded.provenance.source_kind,'read_only_phase1_artifact'));
        assert(~strcmp(decoded.provenance.numerical_version,'repair_001_h01_h04'));
        assert(decoded.outputs.sf1_rejected_raw.energy.value==saved.result.output_energy);
    end
end

function expect_id(fn,id)
try, fn();
catch exception, assert(strcmp(exception.identifier,id)); return;
end
error('ContractTest:MissingError','Expected %s.',id);
end
