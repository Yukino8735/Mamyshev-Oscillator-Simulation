function report=analyze_mamyshev_stationarity(run_dir,output_dir,prefix_reference_run_dir,options)
%ANALYZE_MAMYSHEV_STATIONARITY Offline intensity-shape diagnostics, no labels.
% Only whole-window integer periodic shifts are allowed. No amplitude scaling,
% new propagation, compressor optimization, smoothing or sub-sample alignment.
if nargin<3, prefix_reference_run_dir=''; end
if nargin<4, options=struct(); end
if ~isfield(options,'make_figures'), options.make_figures=true; end
assert(~isfolder(output_dir),'Stationarity:ExistingEvidence','Use a new analysis directory.');
mkdir(output_dir);
manifest=jsondecode(fileread(fullfile(run_dir,'waveform_manifest.json')));
if isempty(manifest.rounds)
    report=struct('analysis_schema_version','mamyshev_stationarity_v1','run_id',manifest.run_id, ...
        'source_identity',manifest.source_identity,'diagnostic_only',true,'completed_saved_rounds',0, ...
        'status','no_saved_rounds','missing_reason','No completed round MAT exists; no stationarity metric can be calculated.', ...
        'rounds',[],'last_five_rounds_summary',[],'endpoint_planes',[], ...
        'physical_state','undetermined','numerical_validation','not_verified', ...
        'eligible_as_validated_training_truth',false,'full_cavity_attempts',0,'propagation_executed',false);
    write_json(fullfile(output_dir,'stationarity.json'),report); return;
end
base=analyze_mamyshev_waveforms(run_dir,fullfile(output_dir,'waveform_checks'),'', ...
    struct('make_figures',options.make_figures,'allow_partial',true));
Nround=numel(manifest.rounds); data=cell(Nround,1); intensities=cell(Nround,2); spectra=cell(Nround,2);
for k=1:Nround
    item=manifest.rounds(k); if iscell(manifest.rounds), item=manifest.rounds{k}; end
    data{k}=load(fullfile(run_dir,item.path)); % base already validated paths, identities, units and all complex samples
    for p=1:2
        if p==1, field=data{k}.pre_tracker_field; else, field=data{k}.post_tracker_field; end
        intensities{k,p}=sum(abs(field).^2,2);
        spectra{k,p}=sum(abs(fftshift(ifft(field,[],1),1)).^2,2)*(size(field,1)*base.grid.dt_ps)^2/1000;
    end
end
t=data{1}.t_ps(:); dt=base.grid.dt_ps; plane_names={'pre_tracker','post_tracker'};
rounds=struct('roundtrip',{},'raw_energy_nJ',{},'pre_tracker',{},'post_tracker',{}); rows={};
for k=1:Nround
    item=struct('roundtrip',k,'raw_energy_nJ',data{k}.raw_energy_nJ,'pre_tracker',[],'post_tracker',[]);
    for p=1:2
        plane=plane_names{p}; intensity=intensities{k,p};
        previous=missing_comparison('No previous completed round.');
        if k>1, previous=compare(intensity,intensities{k-1,p},spectra{k,p},spectra{k-1,p},dt,k-1); end
        fixed=missing_comparison('Round precedes the fixed round-6 reference, or round 6 was not observed.');
        if Nround>=6 && k>=6, fixed=compare(intensity,intensities{6,p},spectra{k,p},spectra{6,p},dt,6); end
        measured=base.rounds(k).(plane);
        region=main_region(intensity,t,dt);
        value=struct('metrics',measured,'main_half_max_region',region, ...
            'previous_round',previous,'fixed_round_6',fixed);
        item.(plane)=value;
        rows{end+1}=csv_row(k,plane,value,data{k}.raw_energy_nJ); %#ok<AGROW>
    end
    rounds(end+1)=item; %#ok<AGROW>
    write_json(fullfile(output_dir,sprintf('round_%04d.json',k)),item);
end
prefix=prefix_check(data,manifest,prefix_reference_run_dir);
if base.final_planes.compressed.available
    ending=load(fullfile(run_dir,manifest.final.path),'compressed_field');
    base.final_planes.compressed.main_half_max_region=main_region(sum(abs(ending.compressed_field).^2,2),t,dt);
else
    base.final_planes.compressed.main_half_max_region=struct('value',NaN, ...
        'missing_reason','No saved same-run compressed field; no reconstruction or repeated optimization.');
end
report=struct('analysis_schema_version','mamyshev_stationarity_v1','run_id',manifest.run_id, ...
    'source_identity',manifest.source_identity,'source_kind','offline_saved_waveform_diagnostics', ...
    'physical_state','undetermined','numerical_validation','not_verified', ...
    'eligible_as_validated_training_truth',false,'full_cavity_attempts',0, ...
    'propagation_executed',false,'compressor_optimization_executed',false, ...
    'run_job_status',base.execution_status,'diagnostic_only',base.diagnostic_only, ...
    'completed_saved_rounds',Nround,'fixed_reference_round',6,'grid',base.grid, ...
    'alignment_protocol',struct('method','FFT circular cross-correlation; integer periodic whole-window shift', ...
        'correlation_formula','real(ifft(fft(reference).*conj(fft(current))))', ...
        'signed_lag_interval','[-floor(N/2), ceil(N/2)-1]', ...
        'shift_applied_to','current intensity: circshift(current, signed_shift_samples)', ...
        'sampling_precision_ps',dt,'fractional_shift',false,'amplitude_scaling',false, ...
        'smoothing',false,'local_warping',false,'tie_relative_tolerance',1e-12, ...
        'ambiguity_relative_tolerance',1e-8, ...
        'tolerance_scale','norm(current,2)*norm(reference,2)', ...
        'tie_selection','minimum absolute signed lag; negative lag first if equal absolute lag', ...
        'ambiguity','multiple numerical ties or distinct local correlation peaks within fixed tolerance', ...
        'fixed_reference_applicability','rounds >=6; earlier rounds retain missing reason'), ...
    'main_region_definition','Periodic connected component of intensity >=0.5*global maximum containing the earliest global-maximum sample; no interpolation', ...
    'main_region_limit','This is a shape diagnostic; component count/local maxima are not pulse counts.', ...
    'rounds',rounds,'last_five_rounds_summary',last_five(rounds), ...
    'raw_energy_source','Unmodified production pre-tracker raw_energy_nJ; separately reported trapz values are offline recomputations.', ...
    'prefix_comparison',prefix,'waveform_checks','waveform_checks/analysis.json', ...
    'endpoint_planes',base.final_planes,'endpoint_scope','Only saved same-run fields; failed-run values remain diagnostics and never replace safe final nulls.', ...
    'figures',{{}});
if options.make_figures, report.figures=figures(output_dir,t,intensities,rounds,dt); end
table_value=struct2table([rows{:}]);
writetable(table_value,fullfile(output_dir,'per_round.csv'));
write_json(fullfile(output_dir,'stationarity.json'),report);
end

function value=compare(current,reference,spectrum,reference_spectrum,dt,reference_round)
value=mamyshev_intensity_alignment(current,reference,dt);
value.reference_round=reference_round;
denominator=norm(reference_spectrum,2);
value.spectral_intensity_relative_L2=NaN;
value.spectral_missing_reason='Reference spectral intensity has zero norm.';
if denominator>0
    value.spectral_intensity_relative_L2=norm(spectrum-reference_spectrum,2)/denominator;
    value.spectral_missing_reason='';
end
end
function value=missing_comparison(reason)
value=struct('status','not_applicable','raw_relative_L2',NaN,'aligned_relative_L2',NaN, ...
    'shift_samples',NaN,'shift_ps',NaN,'ambiguous',false,'ambiguity_reason','', ...
    'reference_round',NaN,'missing_reason',reason,'spectral_intensity_relative_L2',NaN, ...
    'spectral_missing_reason',reason);
end

function value=main_region(power,t,dt)
peak=max(power); indices=find(power==peak); index=indices(1); N=numel(power);
value=struct('threshold_fraction',0.5,'peak_index',index,'peak_time_ps',t(index), ...
    'peak_tie_count',numel(indices),'peak_tie_choice','earliest original sample', ...
    'periodic_adjacency',true,'crosses_time_boundary',false,'whole_window',false, ...
    'start_index',NaN,'end_index',NaN,'sample_count',0,'sample_span_ps',NaN, ...
    'region_energy_sum_nJ',NaN,'region_energy_fraction',NaN,'outside_max_to_peak_ratio',NaN, ...
    'missing_reason','','outside_missing_reason','');
if peak<=0, value.missing_reason='Zero maximum intensity has no main half-maximum region.'; return; end
mask=power>=0.5*peak; rotated=circshift(mask,1-index); rejected=find(~rotated);
if isempty(rejected)
    region=true(N,1); value.whole_window=true; value.start_index=1; value.end_index=N;
else
    selected=false(N,1); selected(1:rejected(1)-1)=true; selected(rejected(end)+1:end)=true;
    region=circshift(selected,index-1);
    value.start_index=find(region & ~circshift(region,1),1);
    value.end_index=find(region & ~circshift(region,-1),1);
    value.crosses_time_boundary=region(1) && region(end);
end
value.sample_count=sum(region); value.sample_span_ps=(value.sample_count-1)*dt;
value.region_energy_sum_nJ=sum(power(region))*dt/1000;
value.region_energy_fraction=sum(power(region))/sum(power);
if all(region), value.outside_missing_reason='No samples outside the main region.';
else, value.outside_max_to_peak_ratio=max(power(~region))/peak; end
end

function row=csv_row(k,plane,value,raw_energy)
m=value.metrics; a=value.previous_round; b=value.fixed_round_6; r=value.main_half_max_region;
row=struct('roundtrip',k,'plane',plane,'production_pre_tracker_energy_nJ',raw_energy,'energy_trapz_nJ',m.energy_trapz_nJ, ...
    'energy_periodic_sum_nJ',m.energy_periodic_sum_nJ,'peak_power_W',m.peak_power_W, ...
    'global_half_max_span_ps',m.global_half_max_span_ps, ...
    'time_left_fraction',m.time_left_energy_fraction,'time_right_fraction',m.time_right_energy_fraction, ...
    'frequency_left_fraction',m.frequency_left_energy_fraction,'frequency_right_fraction',m.frequency_right_energy_fraction, ...
    'main_region_energy_fraction',r.region_energy_fraction,'outside_max_to_peak_ratio',r.outside_max_to_peak_ratio, ...
    'main_region_wraps_boundary',r.crosses_time_boundary,'main_peak_tie_count',r.peak_tie_count, ...
    'previous_raw_L2',a.raw_relative_L2,'previous_aligned_L2',a.aligned_relative_L2, ...
    'previous_shift_samples',a.shift_samples,'previous_shift_ps',a.shift_ps,'previous_ambiguous',a.ambiguous, ...
    'previous_spectrum_L2',a.spectral_intensity_relative_L2,'previous_missing_reason',a.missing_reason, ...
    'fixed6_raw_L2',b.raw_relative_L2,'fixed6_aligned_L2',b.aligned_relative_L2, ...
    'fixed6_shift_samples',b.shift_samples,'fixed6_shift_ps',b.shift_ps,'fixed6_ambiguous',b.ambiguous, ...
    'fixed6_spectrum_L2',b.spectral_intensity_relative_L2,'fixed6_missing_reason',b.missing_reason);
end

function value=last_five(rounds)
indices=max(1,numel(rounds)-4):numel(rounds);
value=struct('rounds',indices,'selection_rule','Last five available completed rounds, or all if fewer; never choose a quiet subwindow.', ...
    'production_raw_energy_nJ',[rounds(indices).raw_energy_nJ], ...
    'pre_tracker',[],'post_tracker',[]);
names={'pre_tracker','post_tracker'};
for p=1:2
    name=names{p}; selected=rounds(indices);
    previous_raw=arrayfun(@(s)s.(name).previous_round.raw_relative_L2,selected);
    previous_aligned=arrayfun(@(s)s.(name).previous_round.aligned_relative_L2,selected);
    value.(name)=struct('peak_power_W',arrayfun(@(s)s.(name).metrics.peak_power_W,selected), ...
        'previous_raw_relative_L2',previous_raw,'previous_aligned_relative_L2',previous_aligned, ...
        'previous_shift_ps',arrayfun(@(s)s.(name).previous_round.shift_ps,selected), ...
        'previous_ambiguous',arrayfun(@(s)s.(name).previous_round.ambiguous,selected), ...
        'fixed6_aligned_relative_L2',arrayfun(@(s)s.(name).fixed_round_6.aligned_relative_L2,selected), ...
        'spectral_intensity_relative_L2',arrayfun(@(s)s.(name).previous_round.spectral_intensity_relative_L2,selected), ...
        'interpretation','Descriptive suffix only; no stability threshold or physical label.');
end
end

function result=prefix_check(data,manifest,reference_dir)
result=struct('reference_dir',reference_dir,'expected_rounds',6,'available_compared_rounds',0, ...
    'status','not_requested','complete',false,'all_observed_checks_passed',false, ...
    'field_absolute_tolerance_sqrtW',1e-10,'field_relative_tolerance',1e-10, ...
    'energy_absolute_tolerance_nJ',1e-10,'energy_relative_tolerance',1e-10, ...
    'coordinates_rule','exact equality including original dimensions','rng_comparison','not performed', ...
    'checks',struct('roundtrip',{},'coordinates_equal',{},'pre_max_abs_error',{},'pre_allowed_error',{}, ...
        'post_max_abs_error',{},'post_allowed_error',{},'energy_abs_error',{},'energy_allowed_error',{},'passed',{}), ...
    'missing_reason','No prefix reference requested.');
if isempty(reference_dir), return; end
reference=jsondecode(fileread(fullfile(reference_dir,'waveform_manifest.json')));
assert(numel(reference.rounds)>=6,'Stationarity:ReferencePrefix','Reference must contain six saved rounds.');
assert(isequaln(reference.design_config,manifest.design_config),'Stationarity:DesignMismatch','Prefix comparison requires identical design inputs.');
n=min(6,numel(data));
for k=1:n
    entry=reference.rounds(k); if iscell(reference.rounds), entry=reference.rounds{k}; end
    assert(ischar(entry.path) && entry.path(1)~='/' && isempty(strfind(entry.path,'..')), ...
        'Stationarity:ReferencePath','Reference MAT path must stay within its run directory.');
    old=load(fullfile(reference_dir,entry.path)); current=data{k};
    assert(strcmp(old.metadata.run_id,reference.run_id) && isequaln(old.metadata.source_identity,reference.source_identity), ...
        'Stationarity:ReferenceIdentity','Reference MAT identity mismatch.');
    coords=isequal(current.t_ps,old.t_ps) && isequal(current.f_THz,old.f_THz) && isequal(current.f0_THz,old.f0_THz);
    [pre_error,pre_tolerance,pre_ok]=field_compare(current.pre_tracker_field,old.pre_tracker_field);
    [post_error,post_tolerance,post_ok]=field_compare(current.post_tracker_field,old.post_tracker_field);
    energy_error=abs(current.raw_energy_nJ-old.raw_energy_nJ); energy_tolerance=1e-10+1e-10*abs(old.raw_energy_nJ);
    check=struct('roundtrip',k,'coordinates_equal',coords,'pre_max_abs_error',pre_error,'pre_allowed_error',pre_tolerance, ...
        'post_max_abs_error',post_error,'post_allowed_error',post_tolerance,'energy_abs_error',energy_error, ...
        'energy_allowed_error',energy_tolerance,'passed',coords && pre_ok && post_ok && isfinite(energy_error) && energy_error<=energy_tolerance);
    result.checks(end+1)=check;
end
result.available_compared_rounds=n; result.complete=n==6;
result.all_observed_checks_passed=all([result.checks.passed]);
result.status='observed'; result.missing_reason='';
if n<6, result.missing_reason='Fewer than six completed rounds were retained; missing prefix rounds are not filled.'; end
end
function [error_value,tolerance,passed]=field_compare(current,reference)
assert(all(isfinite(current(:))) && all(isfinite(reference(:))),'Stationarity:PrefixNonfinite','Prefix fields must be finite before comparison.');
tolerance=1e-10+1e-10*max(abs(reference(:))); error_value=NaN; passed=false;
if isequal(size(current),size(reference)), error_value=max(abs(current(:)-reference(:))); passed=error_value<=tolerance; end
end

function files=figures(output_dir,t,intensities,rounds,dt)
files={'stationarity_differences.png','stationarity_profiles.png','stationarity_regions.png'};
planes={'pre_tracker','post_tracker'}; Nround=numel(rounds); x=1:Nround;
fig=figure('Visible','off','Position',[100 100 1500 1200]); cleanup=onCleanup(@()close(fig));
for p=1:2
    values=[rounds.(planes{p})];
    subplot(4,2,p); plot(x,arrayfun(@(s)s.previous_round.raw_relative_L2,values),'-o',x,arrayfun(@(s)s.previous_round.aligned_relative_L2,values),'-s'); ylabel('Intensity relative L2'); title([planes{p} ': previous round'],'Interpreter','none'); legend('Unaligned','Integer aligned'); grid on;
    subplot(4,2,2+p); plot(x,arrayfun(@(s)s.fixed_round_6.raw_relative_L2,values),'-o',x,arrayfun(@(s)s.fixed_round_6.aligned_relative_L2,values),'-s'); ylabel('Intensity relative L2'); title('Fixed round 6 reference'); grid on;
    subplot(4,2,4+p); plot(x,arrayfun(@(s)s.previous_round.shift_ps,values),'-o',x,arrayfun(@(s)s.fixed_round_6.shift_ps,values),'-s'); ylabel('Applied whole-window shift (ps)'); legend('Previous','Fixed 6'); grid on;
    subplot(4,2,6+p); plot(x,arrayfun(@(s)s.previous_round.spectral_intensity_relative_L2,values),'-o',x,arrayfun(@(s)s.fixed_round_6.spectral_intensity_relative_L2,values),'-s'); ylabel('Spectral intensity relative L2'); xlabel('Completed round'); grid on;
end
sgtitle('Descriptive waveform differences; no physical-state threshold or label'); print(fig,fullfile(output_dir,files{1}),'-dpng','-r120'); clear cleanup;
fig=figure('Visible','off','Position',[100 100 1700 1000]); cleanup=onCleanup(@()close(fig)); colors=turbo(max(2,Nround));
for p=1:2
    subplot(2,2,2*p-1); hold on;
    for k=1:Nround, plot(t,intensities{k,p},'Color',colors(k,:)); end
    title([planes{p} ': full window, no new alignment'],'Interpreter','none'); xlabel('Original time (ps)'); ylabel('Power (W)'); grid on;
    colormap(colors); caxis([1 max(2,Nround)]); colorbar;
    subplot(2,2,2*p); hold on;
    reference=min(6,Nround); reference_power=intensities{reference,p}; [peak,index]=max(reference_power);
    half=find(reference_power>=peak/2); span=min((t(end)-t(1))/4,max(10*dt,3*(t(half(end))-t(half(1)))));
    selection=abs(t-t(index))<=span;
    for k=max(reference,Nround-5):Nround
        [~,aligned]=mamyshev_intensity_alignment(intensities{k,p},reference_power,dt);
        plot(t(selection),aligned(selection),'.-','Color',colors(k,:),'MarkerSize',5);
    end
    title(sprintf('Whole-window aligned to RT %d; last available rounds, raw samples',reference)); xlabel('Reference time samples (ps)'); ylabel('Power (W)'); grid on;
    colormap(colors); caxis([1 max(2,Nround)]); colorbar;
end
sgtitle('Colors encode completed round; no amplitude normalization, interpolation or smoothing'); print(fig,fullfile(output_dir,files{2}),'-dpng','-r120'); clear cleanup;
fig=figure('Visible','off','Position',[100 100 1400 900]); cleanup=onCleanup(@()close(fig));
for p=1:2
    values=[rounds.(planes{p})];
    subplot(2,2,p); plot(x,arrayfun(@(s)s.main_half_max_region.region_energy_fraction,values),'-o',x,arrayfun(@(s)s.main_half_max_region.outside_max_to_peak_ratio,values),'-s'); title(planes{p},'Interpreter','none'); legend('Main >=half-peak region energy fraction','Outside maximum / global maximum'); xlabel('Completed round'); grid on;
end
subplot(2,2,3); plot(x,arrayfun(@(s)s.pre_tracker.metrics.energy_trapz_nJ,rounds),'-o',x,arrayfun(@(s)s.post_tracker.metrics.energy_trapz_nJ,rounds),'-s'); ylabel('Trapz energy (nJ)'); xlabel('Completed round'); legend('Pre tracker','Post tracker'); grid on;
subplot(2,2,4); plot(x,arrayfun(@(s)s.pre_tracker.metrics.peak_power_W,rounds),'-o',x,arrayfun(@(s)s.post_tracker.metrics.peak_power_W,rounds),'-s'); ylabel('Peak power (W)'); xlabel('Completed round'); legend('Pre tracker','Post tracker'); grid on;
sgtitle('Periodic main half-maximum region is a descriptive region, not a pulse count'); print(fig,fullfile(output_dir,files{3}),'-dpng','-r120'); clear cleanup;
end
function write_json(path,value)
assert(~isfile(path) && ~isfile([path '.tmp']),'Stationarity:ExistingEvidence','Refusing existing output.');
bytes=unicode2native([jsonencode(value,'ConvertInfAndNaN',true,'PrettyPrint',true) newline],'UTF-8');
fid=fopen([path '.tmp'],'wb'); assert(fid>=0,'Stationarity:Write','Cannot open temporary output.');
try, count=fwrite(fid,bytes,'uint8'); closed=fclose(fid); fid=-1; assert(count==numel(bytes) && closed==0,'Stationarity:Write','Incomplete JSON write.');
catch exception, if fid>=0, fclose(fid); end; rethrow(exception); end
[ok,message]=movefile([path '.tmp'],path); assert(ok,'Stationarity:Write','%s',message);
end
