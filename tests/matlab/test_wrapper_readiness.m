function report = test_wrapper_readiness(output_dir)
%TEST_WRAPPER_READINESS Wrapper/component wiring only. ZERO cavity invocations.
% Every call uses an explicitly tagged artificial backend; the production
% wrapper, record adapter, exception mapper and JSON writer are real.
% IDs/statuses/provenance/forwarded inputs and preserved files compare exactly.
% No numeric approximation or widened tolerance is used in these assertions.
root = fileparts(fileparts(fileparts(mfilename('fullpath'))));
addpath(fullfile(root,'code','ml_bridge'));
addpath(fullfile(root,'code')); setup_mamyshev_project();
resolved_functions=struct('run_mamyshev',which('run_mamyshev'), ...
    'mamyshev_result_record',which('mamyshev_result_record'), ...
    'mamyshev_failure_status',which('mamyshev_failure_status'), ...
    'write_mamyshev_record',which('write_mamyshev_record'));
assert(strcmp(resolved_functions.run_mamyshev,fullfile(root,'code','ring_cavity','scans','run_mamyshev.m')));
for name={'mamyshev_result_record','mamyshev_failure_status','write_mamyshev_record'}
    assert(strcmp(resolved_functions.(name{1}),fullfile(root,'code','ml_bridge',[name{1} '.m'])));
end
t=(-2:2)'; field=exp(-t.^2).*exp(0.2i*t);
legacy=struct('t',t,'output_field',field,'pigtail_output_field',field, ...
    'output_energy',trapz(t,abs(field).^2)/1000,'fwhm_ps',1, ...
    'dechirped_fwhm_fs',NaN,'dechirped_peak_power_W',NaN, ...
    'rt_num',6,'converged',true,'force_stop',false,'pulse_survives',true, ...
    'ML_state',1,'energy_rel_fluct',0);
calls=0;
cases=struct('name',{},'passed',{},'identifier',{},'message',{});
add_case('normal_return_uses_real_record_and_json_with_fixture_provenance',@normal_return);
add_case('ordinary_backend_exception_written_and_rethrown',@ordinary_failure);
add_case('actual_convergence_exception_maps_numerical_failure',@numerical_failure);
add_case('test_only_stop_exception_never_becomes_success',@fixture_stop);
add_case('production_cancel_exception_written_and_rethrown',@cancelled);
add_case('returned_nonfinite_field_writes_failure_then_throws',@nonfinite_return);
add_case('record_adapter_overflow_maps_failure_then_throws',@adapter_overflow);
add_case('json_write_failure_propagates',@write_failure);
add_case('json_write_failure_preserves_backend_error_as_cause',@write_and_backend_failure);
add_case('existing_timeout_record_cannot_be_replaced_by_success',@preserve_terminal);
add_case('untagged_injection_rejected_before_backend',@invalid_injection);
report=struct('suite','wrapper_readiness','full_cavity_runs',0, ...
    'synthetic_backend_calls',calls,'fixture_only',true, ...
    'resolved_functions',resolved_functions, ...
    'default_full_cavity_route','static_checked_not_executed', ...
    'comparison_rule','Exact statuses, identifiers, provenance, input forwarding and file bytes', ...
    'cases',cases,'passed',sum([cases.passed]),'failed',sum(~[cases.passed]), ...
    'all_passed',all([cases.passed]));

    function add_case(name,fn)
        item=struct('name',name,'passed',false,'identifier','','message','');
        try, fn(); item.passed=true;
        catch exception, item.identifier=exception.identifier; item.message=exception.message;
        end
        cases(end+1)=item;
    end
    function options=fixture(fn)
        options=struct('kind','wrapper_component_fixture','backend',fn);
    end
    function value=success_backend(pump,cw,plot_on)
        calls=calls+1;
        assert(pump==4 && cw==1030 && isequal(plot_on,false));
        value=legacy;
    end
    function value=throw_backend(identifier,pump,cw,plot_on)
        success_backend(pump,cw,plot_on);
        error(identifier,'Explicit wrapper component fixture; not a cavity run.');
        value=struct(); %#ok<UNRCH>
    end
    function value=convergence_backend(pump,cw,plot_on)
        value=success_backend(pump,cw,plot_on);
        check_convergence([ones(5,1);NaN],field,zeros(size(t)),t,1e-3,false);
    end
    function value=bad_observation(kind,pump,cw,plot_on)
        value=success_backend(pump,cw,plot_on);
        if strcmp(kind,'nonfinite'), value.output_field(1)=NaN;
        else, value.output_field(1)=realmax;
        end
    end
    function path=output(name)
        path=fullfile(output_dir,['wrapper_' name '.json']);
    end
    function r=read(name)
        r=jsondecode(fileread(output(name)));
        assert(strcmp(r.provenance.source_kind,'synthetic_wrapper_component_fixture'));
        assert(strcmp(r.provenance.numerical_version,'synthetic_fixture_not_a_backend_run'));
        assert(strcmp(r.provenance.physics_identity_id,'synthetic_wrapper_fixture'));
        assert(strcmp(r.provenance.wrapper_version,'readiness_001_failure_propagation'));
        assert(strcmp(r.physical_state,'undetermined') && ~r.eligible_as_validated_training_truth);
    end
    function normal_return()
        [r,value]=run_mamyshev_recorded(4,1030,false,output('normal'),fixture(@success_backend));
        assert(isequaln(value,legacy));
        decoded=read('normal'); assert(strcmp(decoded.job_status,'completed'));
        assert(strcmp(decoded.stop_reason,'legacy_energy_convergence'));
        assert(decoded.outputs.sf1_rejected_raw.energy.value==legacy.output_energy);
        assert(isempty(decoded.outputs.compressed_analysis.energy.value));
        assert(strcmp(r.job_status,'completed'));
    end
    function ordinary_failure()
        check_throw('ordinary','WrapperFixture:BackendError','execution_error', ...
            @(p,c,g)throw_backend('WrapperFixture:BackendError',p,c,g),'failed');
    end
    function numerical_failure()
        check_throw('numerical','check_convergence:NonFiniteEnergy','numerical_error', ...
            @convergence_backend,'failed');
    end
    function fixture_stop()
        check_throw('fixture_stop','H01:FixtureAcceptedStepCaptured','execution_error', ...
            @(p,c,g)throw_backend('H01:FixtureAcceptedStepCaptured',p,c,g),'failed');
    end
    function cancelled()
        check_throw('cancelled','GMMNLSE_propagate:ProgressBarBreak','user_cancelled', ...
            @(p,c,g)throw_backend('GMMNLSE_propagate:ProgressBarBreak',p,c,g),'cancelled');
    end
    function check_throw(name,id,reason,fn,status)
        captured=expect_id(@()run_mamyshev_recorded(4,1030,false,output(name),fixture(fn)),id);
        assert(strcmp(captured.identifier,id));
        r=read(name); assert(strcmp(r.job_status,status) && strcmp(r.stop_reason,reason));
        assert(strcmp(r.failure_reason.identifier,id));
        assert(isempty(r.outputs.sf1_rejected_raw.energy.value));
    end
    function nonfinite_return()
        expect_id(@()run_mamyshev_recorded(4,1030,false,output('nonfinite'), ...
            fixture(@(p,c,g)bad_observation('nonfinite',p,c,g))),'MamyshevRecord:ReturnedFailure');
        r=read('nonfinite'); assert(strcmp(r.job_status,'failed') && strcmp(r.stop_reason,'numerical_error'));
        assert(strcmp(r.failure_reason.identifier,'MamyshevRecord:NonFiniteObservation'));
    end
    function adapter_overflow()
        check_throw('overflow','MamyshevRecord:NonFinitePower','numerical_error', ...
            @(p,c,g)bad_observation('overflow',p,c,g),'failed');
    end
    function write_failure()
        path=fullfile(output_dir,'directory_that_is_not_created','record.json');
        assert(~isfolder(fileparts(path)));
        expect_id(@()run_mamyshev_recorded(4,1030,false,path,fixture(@success_backend)), ...
            'MamyshevRecord:WriteError');
        assert(~isfile(path));
    end
    function write_and_backend_failure()
        path=fullfile(output_dir,'directory_that_is_not_created','record.json');
        exception=expect_id(@()run_mamyshev_recorded(4,1030,false,path, ...
            fixture(@(p,c,g)throw_backend('WrapperFixture:OriginalBackendError',p,c,g))), ...
            'MamyshevRecord:WriteError');
        assert(numel(exception.cause)==1);
        assert(strcmp(exception.cause{1}.identifier,'WrapperFixture:OriginalBackendError'));
    end
    function preserve_terminal()
        p=struct('physics_identity_id','synthetic_wrapper_fixture', ...
            'numerical_version','synthetic_fixture_not_a_backend_run','source_kind','synthetic_timeout_fixture');
        r=mamyshev_result_record(struct(),struct('job_status','timeout'),p);
        path=output('existing_timeout'); write_mamyshev_record(path,r); before=fileread(path);
        expect_id(@()run_mamyshev_recorded(4,1030,false,path,fixture(@success_backend)), ...
            'MamyshevRecord:ExistingRecord');
        assert(strcmp(fileread(path),before));
        decoded=jsondecode(fileread(path)); assert(strcmp(decoded.job_status,'timeout'));
    end
    function invalid_injection()
        before=calls;
        expect_id(@()run_mamyshev_recorded(4,1030,false,output('invalid'),struct('backend',@success_backend)), ...
            'MamyshevRecord:InvalidTestOptions');
        assert(calls==before && ~isfile(output('invalid')));
    end
end

function exception=expect_id(fn,id)
try, fn();
catch exception, assert(strcmp(exception.identifier,id),'WrapperTest:WrongError','Expected %s, got %s.',id,exception.identifier); return;
end
error('WrapperTest:MissingError','Expected %s.',id);
end
