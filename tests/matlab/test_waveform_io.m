function report=test_waveform_io(output_dir)
% Artificial complex arrays only: zero propagation or physical design samples.
repo=fileparts(fileparts(fileparts(mfilename('fullpath'))));
addpath(fullfile(repo,'code','ml_bridge'));
assert(isfolder(output_dir),'WaveformTest:Directory');
identity=struct('run_id','synthetic_waveform_fixture', ...
    'source_identity',struct('kind','synthetic_fixture_not_a_physical_run','sha256','fixture'));
config=struct('pump_power_W',4,'filter_offset_nm',10,'filter2_bw_nm',3,'gain_length_m',4);
cases=struct('name',{},'passed',{});
original_rng=rng; restore=onCleanup(@()rng(original_rng)); %#ok<NASGU>
rng(31,'twister'); initial_rng=rng;
[disabled,disabled_rng]=fixture_calculation([],initial_rng);
writer=MamyshevWaveforms(output_dir,identity,config);
[enabled,enabled_rng]=fixture_calculation(writer,initial_rng);
assert(isequal(enabled,disabled) && isequal(enabled_rng,disabled_rng), ...
    'WaveformTest:SaveChangesCalculationOrRNG');
cases(end+1)=item('save_on_off_fixture_calculation_and_rng_exactly_equal');

assert(writer.summary().finalized && writer.summary().completed_roundtrips==2);
manifest=jsondecode(fileread(fullfile(output_dir,'waveform_manifest.json')));
assert(manifest.finalized && manifest.completed_roundtrips==2 && numel(manifest.rounds)==2 && ...
    strcmp(manifest.units.field,'sqrt(W)') && strcmp(manifest.units.t,'ps') && ...
    strcmp(manifest.units.f,'THz') && strcmp(manifest.units.energy,'nJ') && ...
    strcmp(manifest.conventions.time_to_frequency,'fftshift(ifft(A,[],1),1)') && ...
    strcmp(manifest.run_id,identity.run_id) && isequal(manifest.design_config,config));
for k=1:2
    saved=load(fullfile(output_dir,sprintf('waveforms_round_%04d.mat',k)));
    assert(saved.roundtrip==k && isequal(saved.pre_tracker_field,enabled.pre{k}) && ...
        isequal(saved.post_tracker_field,enabled.post{k}) && ~isreal(saved.pre_tracker_field) && ...
        isequal(size(saved.pre_tracker_field),[16 1]) && ...
        isequal(saved.t_ps,enabled.result.t) && isequal(saved.f_THz,enabled.result.f) && ...
        isequal(saved.raw_energy_nJ,enabled.raw(k)) && ...
        strcmp(saved.metadata.run_id,identity.run_id) && ...
        isequal(saved.metadata.source_identity,identity.source_identity));
    hash=mamyshev_artifact_integrity(output_dir,{manifest.rounds(k).path});
    assert(strcmp(manifest.rounds(k).sha256,hash.sha256) && manifest.rounds(k).bytes==hash.bytes);
end
saved=load(fullfile(output_dir,'waveforms_final.mat'));
assert(isequal(saved.output_field,enabled.result.output_field) && ...
    isequal(saved.pigtail_output_field,enabled.result.pigtail_output_field) && ...
    isequal(saved.compressed_field,enabled.compressed) && ...
    isequal(saved.raw_energy_history,enabled.raw) && ...
    saved.output_energy==enabled.result.output_energy && saved.rt_num==2 && ...
    saved.metadata.compressed_field_available && manifest.final.compressed_field_available);
assert(numel(writer.paths())==4 && ~any(contains(writer.paths(),'..')));
cases(end+1)=item('complex_mat_roundtrip_values_dimensions_units_identity_and_hashes');

expect_failure(@()MamyshevWaveforms(output_dir,identity,config),'MamyshevWaveforms:ExistingRecord');
expect_failure(@()writer.round(3,ones(16,1),ones(16,1),1),'MamyshevWaveforms:State');
expect_failure(@()writer.finish(enabled.result,enabled.compressed),'MamyshevWaveforms:State');
cases(end+1)=item('existing_evidence_and_finalized_writer_refuse_overwrite');

invalid_dir=fullfile(output_dir,'invalid_component'); mkdir(invalid_dir);
invalid=MamyshevWaveforms(invalid_dir,identity,config);
t=enabled.result.t; f=enabled.result.f;
expect_failure(@()invalid.initialize(t,f+1,250),'MamyshevWaveforms:Grid');
invalid.initialize(t,f,250); snapshot=rng;
expect_failure(@()invalid.round(2,ones(16,1),ones(16,1),1),'MamyshevWaveforms:Round');
expect_failure(@()invalid.round(1,ones(15,1),ones(16,1),1),'MamyshevWaveforms:Field');
expect_failure(@()invalid.round(1,nan(16,1),ones(16,1),1),'MamyshevWaveforms:Field');
expect_failure(@()invalid.round(1,ones(16,1),ones(16,1),Inf),'MamyshevWaveforms:Energy');
assert(isequal(snapshot,rng));
partial=jsondecode(fileread(fullfile(invalid_dir,'waveform_manifest.json')));
assert(~partial.finalized && partial.completed_roundtrips==0 && isempty(partial.final));
cases(end+1)=item('nonfinite_wrong_dimension_grid_round_and_energy_fail_closed_without_rng');

missing_dir=fullfile(output_dir,'missing_compressed_component'); mkdir(missing_dir);
missing=MamyshevWaveforms(missing_dir,identity,config); missing.initialize(t,f,250);
for k=1:2, missing.round(k,enabled.pre{k},enabled.post{k},enabled.raw(k)); end
missing.finish(enabled.result,[]);
missing_saved=load(fullfile(missing_dir,'waveforms_final.mat'));
assert(isempty(missing_saved.compressed_field) && ...
    ~missing_saved.metadata.compressed_field_available && ...
    ~isempty(missing_saved.metadata.compressed_field_missing_reason));
cases(end+1)=item('unavailable_compressed_field_remains_empty_with_reason');

report=struct('suite','waveform_io','fixture_kind','synthetic_complex_arrays_only', ...
    'full_cavity_runs',0,'propagation_calls',0,'comparison_tolerance',0, ...
    'cases',cases,'all_passed',all([cases.passed]), ...
    'physical_state','undetermined','eligible_as_validated_training_truth',false, ...
    'not_verified',{{'real_cavity_waveform_capture','independent_numerical_convergence','physical_pulse_classification'}});
mamyshev_write_diagnostic(fullfile(output_dir,'waveform_io_tests.json'),report);
end

function [value,after_rng]=fixture_calculation(writer,initial_rng)
rng(initial_rng);
n=16; t=(-n/2:n/2-1)*0.125; f=250+(-n/2:n/2-1)'/(n*0.125);
if ~isempty(writer)
    before=rng; writer.initialize(t,f,250); assert(isequal(before,rng),'WaveformTest:InitializeRNG');
end
field=((1:n)'/n).*exp(1i*(1:n)'/3);
pre=cell(2,1); post=cell(2,1); raw=zeros(2,1);
for k=1:2
    % Explicit artificial arithmetic + random draw tests observational I/O only.
    field=field*(1+rand/100)*exp(1i/10); pre{k}=field;
    raw(k)=trapz(abs(field).^2)*0.125/1000;
    field=circshift(field,k); post{k}=field;
    if ~isempty(writer)
        before=rng; writer.round(k,pre{k},post{k},raw(k));
        assert(isequal(before,rng),'WaveformTest:RoundRNG');
    end
end
result=struct('t',t,'f',f,'output_field',field,'pigtail_output_field',field*0.98, ...
    'output_energy',raw(end),'rt_num',2,'fwhm_ps',0.5, ...
    'dechirped_fwhm_fs',50,'dechirped_peak_power_W',1,'transform_limited_fwhm_fs',40);
compressed=field.*exp(-1i*(1:n)'/5);
if ~isempty(writer)
    before=rng; writer.finish(result,compressed); assert(isequal(before,rng),'WaveformTest:FinishRNG');
end
value=struct('pre',{pre},'post',{post},'raw',raw,'result',result,'compressed',compressed);
after_rng=rng;
end

function value=item(name)
value=struct('name',name,'passed',true);
end

function expect_failure(action,identifier)
try
    action();
catch exception
    assert(strcmp(exception.identifier,identifier),'WaveformTest:UnexpectedFailure', ...
        'Expected %s, received %s.',identifier,exception.identifier);
    return;
end
error('WaveformTest:MissingFailure','Expected %s.',identifier);
end
