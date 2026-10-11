function [record, legacy] = run_mamyshev_recorded(PumpPower, cw2, plot_on, record_path, test_options, run_context)
%RUN_MAMYSHEV_RECORDED Minimal real-backend safety wrapper.
% The default entry DOES run the full original cavity. Call only inside an
% externally budgeted isolated process after authorization. record_path is a
% MATLAB candidate, NOT the external supervisor's authoritative final record.
% The supervisor owns timeout/cancellation and must use a different final path.
% Explicit synthetic component fixtures may replace only the backend call.
if nargin < 1, PumpPower = 4; end
if nargin < 2, cw2 = 1030; end
if nargin < 3, plot_on = false; end
if nargin < 4, record_path = ''; end
if nargin < 5, test_options = []; end
if nargin < 6, run_context = []; end
backend = [];
fixture_mode = ~isempty(test_options);
if ~isempty(run_context)
    assert(isstruct(run_context) && isscalar(run_context) && ...
        isfield(run_context,'mode') && any(strcmp(run_context.mode,{'real','synthetic'})), ...
        'MamyshevRecord:InvalidRunContext','Explicit real or synthetic run context required.');
    assert(~strcmp(run_context.mode,'real') || ~fixture_mode, ...
        'MamyshevRecord:RealBackendInjection','Real mode refuses component backend injection.');
    assert(~strcmp(run_context.mode,'synthetic') || fixture_mode, ...
        'MamyshevRecord:SyntheticBackendRequired','Synthetic mode requires an explicit fixture.');
    [~,candidate_name,candidate_ext]=fileparts(record_path);
    assert(strcmp([candidate_name candidate_ext],'matlab_candidate.json'), ...
        'MamyshevRecord:CandidateOwnership','Supervised MATLAB writes only matlab_candidate.json.');
end
if fixture_mode
    assert(isstruct(test_options) && isscalar(test_options) && ...
        isfield(test_options,'kind') && strcmp(test_options.kind,'wrapper_component_fixture') && ...
        isfield(test_options,'backend') && isa(test_options.backend,'function_handle'), ...
        'MamyshevRecord:InvalidTestOptions','Only explicitly tagged component fixtures may inject a backend.');
    backend = test_options.backend;
end
code_root = fileparts(fileparts(mfilename('fullpath')));
addpath(code_root); setup_mamyshev_project();
if ~fixture_mode, backend = @run_mamyshev; end
if ~fixture_mode && ~isempty(run_context) && isfield(run_context,'design_config')
    design_config=mamyshev_resolve_config(run_context.design_config);
    assert(isequal(PumpPower,design_config.pump_power_W) && ...
        isequal(cw2,1040-design_config.filter_offset_nm), ...
        'MamyshevConfig:ConflictingInputs','Legacy request and explicit design conflict.');
    backend=@run_mamyshev_config;
end
backend_info = functions(backend);
identity = jsondecode(fileread(fullfile(fileparts(code_root),'configs','legacy_physics_identity.json')));
provenance = struct('physics_identity_id',identity.physics_identity_id, ...
    'numerical_version','repair_001_h01_h04','source_kind','repaired_original_backend', ...
    'wrapper_version','readiness_001_failure_propagation', ...
    'backend_entrypoint',func2str(backend),'backend_source',backend_info.file, ...
    'physics_identity',identity,'inputs',struct('pump_power_W',PumpPower,'filter2_center_wavelength_nm',cw2), ...
    'rng_before',rng);
if fixture_mode
    provenance.physics_identity_id = 'synthetic_wrapper_fixture';
    provenance.physics_identity = [];
    provenance.numerical_version = 'synthetic_fixture_not_a_backend_run';
    provenance.source_kind = 'synthetic_wrapper_component_fixture';
end
if exist('design_config','var')
    [~,resolved]=mamyshev_resolve_config(design_config);
    provenance.physics_identity_id='ring_legacy_rules_config_v1';
    provenance.design_config=design_config;
    provenance.physics_identity=struct('model_rules_id','ring_legacy_rules_config_v1', ...
        'historical_reference',identity,'matches_historical_reference',resolved.matches_historical_reference, ...
        'design_config',design_config,'H02_status','unresolved');
end
capture=[];
if ~isempty(run_context)
    mamyshev_source_identity(fileparts(code_root),run_context.source_identity);
    assert(strcmp(which('run_mamyshev'),fullfile(code_root,'ring_cavity','scans','run_mamyshev.m')), ...
        'MamyshevRecord:WrongBackend','Resolved backend does not match this repository.');
    if exist('design_config','var')
        assert(strcmp(which('run_mamyshev_config'),fullfile(code_root,'ring_cavity','scans','run_mamyshev_config.m')), ...
            'MamyshevRecord:WrongBackend','Resolved configuration entry does not match this repository.');
    end
    provenance.run_id=run_context.run_id;
    provenance.source_identity=run_context.source_identity;
    provenance.requested_seed=run_context.seed;
    provenance.wrapper_version='launchprep_001_observability';
    provenance.observer_version='launchprep_001_readonly_observer_v1';
    if strcmp(run_context.mode,'real')
        capture=MamyshevCapture(fileparts(record_path),run_context);
    end
end
legacy = struct();
started = tic;
backend_exception = [];
try
    if isempty(capture)
        legacy = backend(PumpPower,cw2,plot_on);
    else
        if exist('design_config','var')
            diagnostic_options=struct('capture',capture,'preflight_only',false);
            if isfield(run_context,'observation_options')
                diagnostic_options.observation_options=mamyshev_observation_options(run_context.observation_options);
            end
            legacy = backend(design_config,plot_on,diagnostic_options);
        else
            legacy = backend(PumpPower,cw2,plot_on,struct('capture',capture,'preflight_only',false));
        end
    end
    execution=struct('job_status','completed','max_rt',50);
    if isfield(legacy,'observation'), execution.stop_reason=legacy.observation.stop_reason; end
    record = mamyshev_result_record(legacy,execution,provenance);
catch exception
    backend_exception = exception;
    if ~isempty(capture)
        try, capture.abort(exception.identifier);
        catch diagnostic_exception, backend_exception=addCause(backend_exception,diagnostic_exception);
        end
    end
    record = mamyshev_result_record(legacy,mamyshev_failure_status(exception),provenance);
end
record.execution_elapsed_s = toc(started);
record.provenance.rng_after=rng;
if ~isempty(capture)
    record.observability=capture.summary();
elseif ~isempty(run_context)
    record.observability=struct('kind','synthetic_component', ...
        'required_records_complete',true,'full_cavity_attempts',0, ...
        'scope','Only wrapper candidate creation was observed; no cavity parameter/counter claim.');
end
try
    if ~isempty(record_path), write_mamyshev_record(record_path,record); end
catch write_exception
    if ~isempty(backend_exception)
        write_exception = addCause(write_exception,backend_exception);
    end
    rethrow(write_exception);
end
% A failed/cancelled candidate must not let MATLAB -batch exit successfully.
% Dedicated fixture-stop exceptions follow the same failure path; only the
% owning fixture harness may catch its own stop identifier as expected.
if ~isempty(backend_exception)
    rethrow(backend_exception);
elseif ~strcmp(record.job_status,'completed')
    error('MamyshevRecord:ReturnedFailure', ...
        'Returned observations failed the result contract: %s (%s).', ...
        record.stop_reason,record.failure_reason.identifier);
end
end
