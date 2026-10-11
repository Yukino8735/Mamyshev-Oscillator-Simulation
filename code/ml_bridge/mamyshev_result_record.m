function record = mamyshev_result_record(legacy, execution, provenance)
%MAMYSHEV_RESULT_RECORD Minimal safe record, not a stability classifier.
% No propagation, no new physical labels. Unavailable numeric values are NaN
% in MATLAB and MUST be serialized by write_mamyshev_record as JSON null.
% Required provenance separates physical identity, numerical implementation
% version and source kind (including synthetic fixtures / historical reads).
required = {'physics_identity_id','numerical_version','source_kind'};
for k = 1:numel(required)
    assert(isfield(provenance,required{k}) && ~isempty(provenance.(required{k})), ...
        'MamyshevRecord:MissingProvenance','Missing %s.',required{k});
end
assert(isstruct(legacy) && isscalar(legacy), 'MamyshevRecord:InvalidLegacy','Expected a scalar result struct.');
assert(isfield(execution,'job_status') && any(strcmp(execution.job_status, ...
    {'completed','failed','timeout','cancelled'})), 'MamyshevRecord:InvalidJobStatus','Unknown execution status.');
record = struct('result_protocol_version','safe_result_v1', ...
    'provenance',provenance,'job_status',execution.job_status, ...
    'stop_reason','','failure_reason',[], 'observation_diagnostics',struct(), ...
    'physical_state','undetermined', ...
    'physical_state_reason','No independently validated physical-state protocol; legacy flags are not ground truth.', ...
    'numerical_validation',struct('status','not_verified', ...
        'reason','Independent grid, time-window and step/tolerance convergence remain unverified.'), ...
    'eligible_as_validated_training_truth',false, ...
    'completed_roundtrips',NaN,'completed_roundtrips_missing_reason','Original entry did not return a round count.', ...
    'legacy_flags',struct());
flags = {'converged','force_stop','pulse_survives','ML_state','energy_rel_fluct'};
for k = 1:numel(flags)
    if isfield(legacy,flags{k})
        record.legacy_flags.(flags{k}) = legacy.(flags{k});
    else
        record.legacy_flags.(flags{k}) = NaN;
    end
end
if isfield(legacy,'rt_num') && isscalar(legacy.rt_num) && isreal(legacy.rt_num) && ...
        isfinite(legacy.rt_num) && legacy.rt_num >= 0 && legacy.rt_num == fix(legacy.rt_num)
    record.completed_roundtrips = legacy.rt_num;
    record.completed_roundtrips_missing_reason = '';
elseif isfield(legacy,'rt_num')
    record.completed_roundtrips_missing_reason = 'Returned round count is not a finite nonnegative integer.';
end
if isfield(execution,'stop_reason')
    record.stop_reason = execution.stop_reason;
end
if isfield(execution,'failure_reason')
    record.failure_reason = execution.failure_reason;
end
if strcmp(record.job_status,'completed') && isempty(record.stop_reason)
    if flag_true(legacy,'converged')
        record.stop_reason = 'legacy_energy_convergence';
    elseif flag_true(legacy,'force_stop')
        record.stop_reason = 'legacy_average_energy_convergence';
    elseif isfield(legacy,'pulse_survives') && isequal(legacy.pulse_survives,false)
        record.stop_reason = 'legacy_energy_below_threshold';
    elseif isfield(execution,'max_rt') && isfinite(record.completed_roundtrips) && record.completed_roundtrips >= execution.max_rt
        record.stop_reason = 'max_rt_reached';
    else
        record.stop_reason = 'insufficient_observation';
    end
elseif isempty(record.stop_reason)
    record.stop_reason = record.job_status;
end

% A successful process must not turn nonfinite physical observations into data.
physical_fields = {'output_energy','output_field','pigtail_output_field','t','compressed_field'};
for k = 1:numel(physical_fields)
    name = physical_fields{k};
    if isfield(legacy,name) && any(~isfinite(legacy.(name)),'all')
        observation_error = struct('identifier','MamyshevRecord:NonFiniteObservation', ...
            'message',['Nonfinite returned observation: ' name]);
        record.observation_diagnostics.nonfinite = observation_error;
        if strcmp(record.job_status,'completed')
            record.job_status = 'failed'; record.stop_reason = 'numerical_error';
            record.failure_reason = observation_error;
        end
        break;
    end
end
metric_input = legacy;
if ~strcmp(record.job_status,'completed')
    % Preserve legacy flags/count and failure provenance, but do not extract
    % final metrics from partial, invalid or interrupted observations.
    metric_input = struct();
end

raw = struct('plane','SF1 rejected port before pigtail','processing','uncompressed');
raw.energy = scalar_metric(metric_input,'output_energy','nJ', ...
    'trapz(abs(field).^2)*dt_ps/1000 before pulse_tracker centering', 'run_mamyshev.output_energy');
raw.fwhm = scalar_metric(metric_input,'fwhm_ps','ps', ...
    'Global span from first to last sample at or above half of maximum intensity; no crossing interpolation', 'run_mamyshev.fwhm_ps');
[raw.peak_power,~] = field_metrics(metric_input,'output_field');
tail = struct('plane','After 0.2 m output pigtail','processing','uncompressed');
[tail.peak_power,tail.energy] = field_metrics(metric_input,'pigtail_output_field');
tail.fwhm = missing_metric('ps','Not extracted by this minimal record adapter','', ...
    'Original result has no separate pigtail raw FWHM scalar.');
compressed = struct('plane','After output pigtail and compressor analysis', ...
    'processing','Legacy idealized Treacy-t compression analysis');
compressed.fwhm = scalar_metric(metric_input,'dechirped_fwhm_fs','fs', ...
    'Legacy compressor local peak half-height width from findpeaks; differs from global raw span', 'run_mamyshev.dechirped_fwhm_fs');
compressed.peak_power = scalar_metric(metric_input,'dechirped_peak_power_W','W', ...
    'Peak from the compressor-analyzed field; not energy divided by width', 'run_mamyshev.dechirped_peak_power_W');
compressed.energy = missing_metric('nJ','Energy of the compressed field','', ...
    'Original entry does not return the compressed field or its energy; upstream energy is not substituted.');
compressed.field = struct('value',NaN,'unit','sqrt(W)', ...
    'missing_reason','Original entry does not return the compressed complex field.');
if isfield(metric_input,'compressed_field') && ~isempty(metric_input.compressed_field)
    [~,compressed.energy]=field_metrics(metric_input,'compressed_field');
    compressed.field=struct('value',NaN,'unit','sqrt(W)', ...
        'missing_reason','Stored as complex MAT array; no inline JSON field.', ...
        'available',true,'artifact','waveforms_final.mat','variable','compressed_field');
end
if isfield(metric_input,'waveform_artifacts'), record.waveform_artifacts=metric_input.waveform_artifacts; end
if isfield(legacy,'observation'), record.observation=legacy.observation; end
record.outputs = struct('sf1_rejected_raw',raw,'pigtail_raw',tail,'compressed_analysis',compressed);
record.references = struct('transform_limited_fwhm',scalar_metric(metric_input,'transform_limited_fwhm_fs','fs', ...
    'Phase-removed ideal reference width; not the achieved compressed pulse', 'run_mamyshev.transform_limited_fwhm_fs'));
% Partial/error observations are not final metrics, even if some are finite.
if ~strcmp(record.job_status,'completed')
    planes = fieldnames(record.outputs);
    for k = 1:numel(planes)
        metrics = {'energy','peak_power','fwhm'};
        for j = 1:numel(metrics)
            record.outputs.(planes{k}).(metrics{j}).value = NaN;
            record.outputs.(planes{k}).(metrics{j}).missing_reason = 'No final metric: execution did not complete successfully.';
        end
    end
    record.references.transform_limited_fwhm.value = NaN;
    record.references.transform_limited_fwhm.missing_reason = 'No final metric: execution did not complete successfully.';
end
end

function yes = flag_true(value, name)
yes = isfield(value,name) && isscalar(value.(name)) && isequal(value.(name),true);
end

function metric = missing_metric(unit,definition,source,reason)
metric = struct('value',NaN,'unit',unit,'definition',definition,'source',source,'missing_reason',reason);
end

function metric = scalar_metric(value,name,unit,definition,source)
metric = missing_metric(unit,definition,source,['Missing or nonfinite legacy field: ' name]);
if isfield(value,name) && isnumeric(value.(name)) && isscalar(value.(name)) && isreal(value.(name)) && isfinite(value.(name))
    metric.value = value.(name); metric.missing_reason = '';
end
end

function [peak,energy] = field_metrics(value,name)
peak = missing_metric('W','max(sum(abs(complex_field).^2,2)) over saved temporal samples', ...
    ['run_mamyshev.' name],'No finite saved complex field.');
energy = missing_metric('nJ','trapz(t_ps,sum(abs(complex_field).^2,2))/1000 on saved field', ...
    ['run_mamyshev.' name ' and t'],'No finite saved field with matching increasing time grid.');
if ~isfield(value,name) || isempty(value.(name)) || any(~isfinite(value.(name)),'all')
    return;
end
field = value.(name);
assert(ismatrix(field),'MamyshevRecord:InvalidFieldShape','Expected one saved temporal field, not propagation history.');
power = sum(abs(field).^2,2);
if any(~isfinite(power))
    error('MamyshevRecord:NonFinitePower','Squared field overflowed.');
end
peak.value = max(power); peak.missing_reason = '';
if isfield(value,'t') && numel(value.t) == size(field,1) && numel(value.t) >= 2 && ...
        all(isfinite(value.t)) && all(diff(value.t(:)) > 0)
    energy.value = trapz(value.t(:),power)/1000;
    if ~isfinite(energy.value)
        error('MamyshevRecord:NonFiniteEnergy','Field energy overflowed.');
    end
    energy.missing_reason = '';
end
end
