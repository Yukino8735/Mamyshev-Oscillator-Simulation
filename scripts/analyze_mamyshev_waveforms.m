function report=analyze_mamyshev_waveforms(manifest_path,output_dir,reference_result_path,options)
%ANALYZE_MAMYSHEV_WAVEFORMS Read saved complex fields; never propagate/optimize.
% report = analyze_mamyshev_waveforms(manifest_path, output_dir, reference_json)
% Fixed comparisons: rtol=1e-10; E atol=1e-10 nJ, peak atol=1e-7 W,
% global width atol=1e-12 ps, legacy compressor/TL width atol=1e-9 fs.
% Plot every saved sample, without smoothing, interpolation or new alignment.
if nargin<3, reference_result_path=''; end
if nargin<4, options=struct(); end
if ~isfield(options,'make_figures'), options.make_figures=true; end
if ~isfield(options,'allow_partial'), options.allow_partial=false; end
if isfolder(manifest_path), manifest_path=fullfile(manifest_path,'waveform_manifest.json'); end
assert(isfile(manifest_path),'WaveformAnalysis:MissingManifest','Missing waveform manifest.');
if isfolder(output_dir)
    items=dir(output_dir); items=items(~ismember({items.name},{'.','..'}));
    assert(isempty(items),'WaveformAnalysis:ExistingEvidence','Analysis output directory must be new or empty.');
end
if ~isfolder(output_dir), mkdir(output_dir); end
run_dir=fileparts(manifest_path); manifest=jsondecode(fileread(manifest_path));
assert(strcmp(manifest.schema_version,'mamyshev_waveforms_v1'),'WaveformAnalysis:Schema','Diagnostic validation failed.');
assert(manifest.initialized,'WaveformAnalysis:Uninitialized','Diagnostic validation failed.');
tol=struct('relative',1e-10,'energy_nJ',1e-10,'peak_W',1e-7, ...
    'global_width_ps',1e-12,'legacy_width_fs',1e-9,'energy_rel_fluct',1e-12);
checks=empty_checks();
rounds=struct('roundtrip',{},'source_file',{},'pre_tracker',{},'post_tracker',{}, ...
    'pre_intensity_relative_L2_previous',{},'post_intensity_relative_L2_previous',{});
raw={}; post={}; last_grid=[];
for k=1:numel(manifest.rounds)
    entry=manifest.rounds(k); if iscell(manifest.rounds), entry=manifest.rounds{k}; end
    data=load(safe_path(run_dir,entry.path));
    require(data,{'pre_tracker_field','post_tracker_field','roundtrip','raw_energy_nJ','t_ps','f_THz','f0_THz','metadata'});
    verify_waveform_metadata(data.metadata,manifest);
    assert(data.roundtrip==entry.roundtrip && data.roundtrip==k,'WaveformAnalysis:RoundOrder','Diagnostic validation failed.');
    grid=verify_grid(data.t_ps,data.f_THz,data.f0_THz);
    if ~isempty(last_grid), assert(isequal(grid.t,last_grid.t) && isequal(grid.f,last_grid.f),'WaveformAnalysis:GridChanged','Diagnostic validation failed.'); end
    last_grid=grid;
    [pre,raw{k}]=field_metrics(data.pre_tracker_field,grid,'SF1 rejected port, before production pulse_tracker'); %#ok<AGROW>
    [after,post{k}]=field_metrics(data.post_tracker_field,grid,'SF1 rejected port, after production pulse_tracker'); %#ok<AGROW>
    checks(end+1)=number_check(sprintf('round_%d_pre_energy_vs_saved_scalar',k),pre.energy_trapz_nJ,data.raw_energy_nJ,tol.energy_nJ,tol.relative,'nJ'); %#ok<AGROW>
    checks(end+1)=number_check(sprintf('round_%d_pre_energy_vs_manifest',k),pre.energy_trapz_nJ,entry.raw_energy_nJ,tol.energy_nJ,tol.relative,'nJ'); %#ok<AGROW>
    checks(end+1)=number_check(sprintf('round_%d_tracker_periodic_energy',k),after.energy_periodic_sum_nJ,pre.energy_periodic_sum_nJ,tol.energy_nJ,tol.relative,'nJ'); %#ok<AGROW>
    checks=[checks parseval_check(pre,sprintf('round_%d_pre',k),tol) parseval_check(after,sprintf('round_%d_post',k),tol)]; %#ok<AGROW>
    before_change=missing_change(); after_change=missing_change();
    if k>1
        before_change=intensity_change(raw{k}.power,raw{k-1}.power);
        after_change=intensity_change(post{k}.power,post{k-1}.power);
    end
    rounds(k)=struct('roundtrip',k,'source_file',entry.path,'pre_tracker',pre, ... %#ok<AGROW>
        'post_tracker',after,'pre_intensity_relative_L2_previous',before_change, ...
        'post_intensity_relative_L2_previous',after_change);
end
assert(~isempty(rounds),'WaveformAnalysis:NoRounds','No completed saved rounds to analyze.');
checks(end+1)=number_check('manifest_completed_rounds',numel(rounds),manifest.completed_roundtrips,0,0,'round trips');
assert(numel(manifest.raw_energy_history_nJ)==numel(rounds),'WaveformAnalysis:EnergyHistorySize','Diagnostic validation failed.');
for k=1:numel(rounds)
    checks(end+1)=number_check(sprintf('round_%d_manifest_energy_history',k),rounds(k).pre_tracker.energy_trapz_nJ,manifest.raw_energy_history_nJ(k),tol.energy_nJ,tol.relative,'nJ'); %#ok<AGROW>
end
final_planes=struct('sf1_pre_tracker',rounds(end).pre_tracker,'sf1_post_tracker',rounds(end).post_tracker, ...
    'pigtail',missing_plane('Final pigtail MAT not available.'), ...
    'compressed',missing_plane('Compressed field not available; no field is reconstructed.'));
views={raw{end},post{end},[],[]}; final_data=[];
if manifest.finalized && isfield(manifest,'final') && ~isempty(manifest.final.path)
    final_data=load(safe_path(run_dir,manifest.final.path));
    require(final_data,{'output_field','pigtail_output_field','compressed_field','output_energy','rt_num','raw_energy_history','t_ps','f_THz','f0_THz','metadata'});
    verify_waveform_metadata(final_data.metadata,manifest);
    grid=verify_grid(final_data.t_ps,final_data.f_THz,final_data.f0_THz);
    assert(isequal(grid.t,last_grid.t) && isequal(grid.f,last_grid.f),'WaveformAnalysis:FinalGridChanged','Diagnostic validation failed.');
    [final_post,final_view]=field_metrics(final_data.output_field,grid,'SF1 rejected port, post production pulse_tracker');
    checks(end+1)=number_check('final_post_complex_field_vs_last_round',max(abs(final_data.output_field(:)-post{end}.field(:))),0,0,0,'sqrt(W)');
    checks(end+1)=number_check('final_raw_energy_before_tracker',rounds(end).pre_tracker.energy_trapz_nJ,final_data.output_energy,tol.energy_nJ,tol.relative,'nJ');
    checks(end+1)=number_check('final_mat_rounds',final_data.rt_num,numel(rounds),0,0,'round trips');
    assert(numel(final_data.raw_energy_history)==numel(rounds),'WaveformAnalysis:FinalEnergyHistorySize','Diagnostic validation failed.');
    for k=1:numel(rounds)
        checks(end+1)=number_check(sprintf('round_%d_final_energy_history',k),final_data.raw_energy_history(k),manifest.raw_energy_history_nJ(k),tol.energy_nJ,tol.relative,'nJ'); %#ok<AGROW>
    end
    final_planes.sf1_post_tracker=final_post; views{2}=final_view;
    [final_planes.pigtail,views{3}]=field_metrics(final_data.pigtail_output_field,grid,'Output after original 0.2 m pigtail, uncompressed');
    checks=[checks parseval_check(final_planes.pigtail,'pigtail',tol)];
    if manifest.final.compressed_field_available
        assert(~isempty(final_data.compressed_field),'WaveformAnalysis:DeclaredFieldMissing','Diagnostic validation failed.');
        [final_planes.compressed,views{4}]=field_metrics(final_data.compressed_field,grid,'Saved original compressor output, no repeated optimization');
        checks=[checks parseval_check(final_planes.compressed,'compressed',tol)];
    else
        assert(isempty(final_data.compressed_field),'WaveformAnalysis:CompressedAvailabilityConflict','Diagnostic validation failed.');
        final_planes.compressed=missing_plane(manifest.final.compressed_field_missing_reason);
    end
end

current_path=fullfile(run_dir,'final_result.json'); current=[]; execution_status='missing_final';
if isfile(current_path)
    current=jsondecode(fileread(current_path));
    assert(strcmp(current.result_protocol_version,'safe_result_v1'),'WaveformAnalysis:ResultSchema','Diagnostic validation failed.');
    verify_identity(current.provenance,manifest);
    execution_status=current.job_status;
    if ~strcmp(current.job_status,'completed')
        assert(options.allow_partial,'WaveformAnalysis:UnsuccessfulFinal', ...
            'Failed/timed-out scientific metrics cannot be compared as completed outputs.');
        current=[]; % Partial MATs are diagnostics; never restore failed final metrics.
    end
end
checks(end+1)=number_check('recomputed_pretracker_energy_vs_final',final_planes.sf1_pre_tracker.energy_trapz_nJ,metric(current,{'outputs','sf1_rejected_raw','energy','value'}),tol.energy_nJ,tol.relative,'nJ');
checks(end+1)=number_check('recomputed_posttracker_peak_vs_final',final_planes.sf1_post_tracker.peak_power_W,metric(current,{'outputs','sf1_rejected_raw','peak_power','value'}),tol.peak_W,tol.relative,'W');
checks(end+1)=number_check('recomputed_posttracker_global_width_vs_final',final_planes.sf1_post_tracker.global_half_max_span_ps,metric(current,{'outputs','sf1_rejected_raw','fwhm','value'}),tol.global_width_ps,tol.relative,'ps');
checks(end+1)=number_check('recomputed_pigtail_energy_vs_final',final_planes.pigtail.energy_trapz_nJ,metric(current,{'outputs','pigtail_raw','energy','value'}),tol.energy_nJ,tol.relative,'nJ');
checks(end+1)=number_check('recomputed_pigtail_peak_vs_final',final_planes.pigtail.peak_power_W,metric(current,{'outputs','pigtail_raw','peak_power','value'}),tol.peak_W,tol.relative,'W');
checks(end+1)=number_check('recomputed_compressed_peak_vs_final',final_planes.compressed.peak_power_W,metric(current,{'outputs','compressed_analysis','peak_power','value'}),tol.peak_W,tol.relative,'W');
checks(end+1)=number_check('recomputed_compressed_energy_vs_final',final_planes.compressed.energy_trapz_nJ,metric(current,{'outputs','compressed_analysis','energy','value'}),tol.energy_nJ,tol.relative,'nJ');

reference_checks=empty_checks();
if ~isempty(reference_result_path)
    reference=jsondecode(fileread(reference_result_path));
    assert(strcmp(reference.result_protocol_version,'safe_result_v1') && strcmp(reference.job_status,'completed'),'WaveformAnalysis:ReferenceStatus','Diagnostic validation failed.');
    paths={{'outputs','sf1_rejected_raw','energy','value'}, ...
        {'outputs','sf1_rejected_raw','peak_power','value'}, ...
        {'outputs','sf1_rejected_raw','fwhm','value'}, ...
        {'outputs','pigtail_raw','energy','value'}, ...
        {'outputs','pigtail_raw','peak_power','value'}, ...
        {'outputs','compressed_analysis','peak_power','value'}, ...
        {'outputs','compressed_analysis','fwhm','value'}, ...
        {'references','transform_limited_fwhm','value'}, ...
        {'legacy_flags','energy_rel_fluct'},{'completed_roundtrips'}};
    atols=[tol.energy_nJ,tol.peak_W,tol.global_width_ps,tol.energy_nJ,tol.peak_W, ...
        tol.peak_W,tol.legacy_width_fs,tol.legacy_width_fs,tol.energy_rel_fluct,0];
    units={'nJ','W','ps','nJ','W','W','fs','fs','dimensionless','round trips'};
    for k=1:numel(paths)
        comparison_rtol=tol.relative;
        if isequal(paths{k},{'completed_roundtrips'}), comparison_rtol=0; end
        reference_checks(end+1)=number_check(strjoin(paths{k},'.'),metric(current,paths{k}),metric(reference,paths{k}),atols(k),comparison_rtol,units{k}); %#ok<AGROW>
    end
    exact_flags={'converged','force_stop','pulse_survives','ML_state'};
    for k=1:numel(exact_flags)
        path={'legacy_flags',exact_flags{k}};
        reference_checks(end+1)=number_check(strjoin(path,'.'),double(metric(current,path)),double(metric(reference,path)),0,0,'legacy flag'); %#ok<AGROW>
    end
    same_stop=isstruct(current) && isfield(current,'stop_reason') && isfield(reference,'stop_reason') && strcmp(current.stop_reason,reference.stop_reason);
    reference_checks(end+1)=number_check('stop_reason_exact',double(same_stop),1,0,0,'boolean equality');
end
report=struct('analysis_schema_version','mamyshev_waveform_analysis_v1', ...
    'run_id',manifest.run_id,'source_identity',manifest.source_identity,'input_manifest',manifest_path, ...
    'source_kind','offline_recomputation_from_saved_complex_fields','full_cavity_attempts',0, ...
    'execution_status',execution_status,'diagnostic_only',~strcmp(execution_status,'completed') || ~manifest.finalized, ...
    'propagation_executed',false,'compressor_optimization_executed',false, ...
    'physical_state','undetermined','eligible_as_validated_training_truth',false, ...
    'numerical_validation','not_verified','thresholds',tol,'grid',rmfield(last_grid,{'t','f'}), ...
    'conventions',struct('field_unit','sqrt(W)','time_unit','ps','energy_unit','nJ', ...
        'spectrum','fftshift(ifft(A,[],1),1)','PSD','sum(abs(spectrum).^2,2)*(N*dt_ps)^2/1000 in nJ/THz', ...
        'Parseval','periodic discrete sums; trapz estimates are separately reported', ...
        'frequency_axis','absolute THz, including all negative frequencies; no wavelength remapping', ...
        'relative_L2','norm(I_rt-I_previous,2)/norm(I_previous,2); no additional shift or independent normalization', ...
        'post_tracker','Already centered by the production pulse_tracker; analysis adds no alignment', ...
        'width','Global sample half-maximum span; never substituted for compressor local-peak width'), ...
    'rounds',rounds,'final_planes',final_planes,'checks',checks, ...
    'all_recomputation_checks_passed',all(strcmp({checks.status},'passed')), ...
    'reference_result',reference_result_path,'reference_checks',reference_checks, ...
    'all_reference_checks_passed',~isempty(reference_checks) && all(strcmp({reference_checks.status},'passed')), ...
    'compressor_local_width_recomputation',struct('value',NaN,'missing_reason', ...
        'Not recomputed: global span is a different definition; saved legacy local-peak scalar only participates in scalar regression.'), ...
    'figures',{{}});
if options.make_figures
    report.figures=draw_figures(output_dir,last_grid,views,raw,post,rounds);
end
write_json(fullfile(output_dir,'analysis.json'),report);
end

function grid=verify_grid(t,f,f0)
assert(isnumeric(t) && isvector(t) && isnumeric(f) && isvector(f) && numel(t)==numel(f) && numel(t)>=4,'WaveformAnalysis:GridShape','Diagnostic validation failed.');
t=t(:); f=f(:); N=numel(t);
assert(all(isfinite(t)) && all(isfinite(f)) && isscalar(f0) && isfinite(f0) && isreal(f0),'WaveformAnalysis:NonfiniteGrid','Diagnostic validation failed.');
dt=t(2)-t(1); assert(isreal(t) && isreal(f) && dt>0 && all(diff(f)>0),'WaveformAnalysis:GridOrder','Diagnostic validation failed.');
assert(max(abs(diff(t)-dt))<=64*eps(max(1,max(abs(t)))),'WaveformAnalysis:NonuniformGrid','Diagnostic validation failed.');
expected=f0+((-floor(N/2)):(ceil(N/2)-1))'/(N*dt);
assert(max(abs(f-expected))<=128*eps(max(1,max(abs(expected)))),'WaveformAnalysis:FrequencyGrid','Diagnostic validation failed.');
grid=struct('t',t,'f',f,'N',N,'dt_ps',dt,'df_THz',1/(N*dt),'f0_THz',f0, ...
    'time_window_period_ps',N*dt,'negative_frequency_samples',sum(f<0), ...
    'edge_samples_per_side',ceil(0.01*N),'edge_sample_fraction_per_side',ceil(0.01*N)/N);
end

function [value,view]=field_metrics(A,grid,plane)
assert(isnumeric(A) && ismatrix(A) && size(A,1)==grid.N && size(A,2)>=1 && ~isempty(A),'WaveformAnalysis:FieldShape','Diagnostic validation failed.');
assert(all(isfinite(A(:))),'WaveformAnalysis:NonfiniteField','Saved complex field contains NaN/Inf.');
power=sum(abs(A).^2,2); spectrum=fftshift(ifft(A,[],1),1);
psd=sum(abs(spectrum).^2,2)*(grid.N*grid.dt_ps)^2/1000;
assert(all(isfinite(power)) && all(isfinite(psd)),'WaveformAnalysis:PowerOverflow','Diagnostic validation failed.');
peak=max(power); ids=find(power>=peak/2);
[spectral_peak,spectral_peak_index]=max(psd);
width=NaN; width_reason='Zero intensity has no half-maximum width.';
if peak>0, width=grid.t(ids(end))-grid.t(ids(1)); width_reason=''; end
k=grid.edge_samples_per_side;
value=struct('available',true,'plane',plane,'missing_reason','', ...
    'field_size',size(A),'complex_field',~isreal(A),'finite',true, ...
    'energy_trapz_nJ',trapz(grid.t,power)/1000,'energy_periodic_sum_nJ',sum(power)*grid.dt_ps/1000, ...
    'spectral_energy_trapz_nJ',trapz(grid.f,psd),'spectral_energy_periodic_sum_nJ',sum(psd)*grid.df_THz, ...
    'peak_power_W',peak,'global_half_max_span_ps',width,'width_missing_reason',width_reason, ...
    'spectral_peak_frequency_THz',grid.f(spectral_peak_index),'spectral_peak_density_nJ_per_THz',spectral_peak, ...
    'edge_definition','sum-based fractions of discrete energy; ceil(0.01*N) samples per side', ...
    'edge_samples_per_side',k,'edge_actual_sample_fraction_per_side',k/grid.N, ...
    'time_left_energy_fraction',fraction(sum(power(1:k)),sum(power)), ...
    'time_right_energy_fraction',fraction(sum(power(end-k+1:end)),sum(power)), ...
    'frequency_left_energy_fraction',fraction(sum(psd(1:k)),sum(psd)), ...
    'frequency_right_energy_fraction',fraction(sum(psd(end-k+1:end)),sum(psd)), ...
    'edge_missing_reason','');
if sum(power)==0, value.edge_missing_reason='Zero total energy; normalized edge fractions are undefined.'; end
view=struct('field',A,'power',power,'psd',psd);
end

function result=fraction(x,total)
if total>0, result=x/total; else, result=NaN; end
end
function value=missing_plane(reason)
value=struct('available',false,'plane','','missing_reason',reason,'energy_trapz_nJ',NaN, ...
    'energy_periodic_sum_nJ',NaN,'peak_power_W',NaN,'global_half_max_span_ps',NaN);
end
function value=missing_change()
value=struct('value',NaN,'missing_reason','No previous saved round.');
end
function value=intensity_change(current,previous)
denominator=norm(previous,2); value=missing_change();
if denominator>0, value.value=norm(current-previous,2)/denominator; value.missing_reason='';
else, value.missing_reason='Previous intensity has zero norm.'; end
end
function check=parseval_check(plane,name,tol)
check=number_check([name '_discrete_Parseval'],plane.spectral_energy_periodic_sum_nJ,plane.energy_periodic_sum_nJ,tol.energy_nJ,tol.relative,'nJ');
end
function result=empty_checks()
result=struct('name',{},'status',{},'actual',{},'expected',{},'absolute_error',{},'allowed_error',{},'unit',{},'missing_reason',{});
end
function value=number_check(name,actual,expected,atol,rtol,unit)
value=struct('name',name,'status','not_verified','actual',NaN,'expected',NaN, ...
    'absolute_error',NaN,'allowed_error',NaN,'unit',unit,'missing_reason','Missing/nonfinite actual or reference scalar.');
if finite_scalar(actual), value.actual=actual; end
if finite_scalar(expected), value.expected=expected; end
if finite_scalar(actual) && finite_scalar(expected)
    value.absolute_error=abs(actual-expected); value.allowed_error=atol+rtol*abs(expected);
    if value.absolute_error<=value.allowed_error, value.status='passed'; else, value.status='failed'; end
    value.missing_reason='';
end
end
function yes=finite_scalar(value)
yes=(isnumeric(value) || islogical(value)) && isscalar(value) && isreal(value) && isfinite(value);
end
function value=metric(record,path)
value=record;
for k=1:numel(path)
    if ~isstruct(value) || ~isfield(value,path{k}), value=NaN; return; end
    value=value.(path{k});
end
if ~finite_scalar(value), value=NaN; end
end
function require(data,names)
for k=1:numel(names), assert(isfield(data,names{k}),'WaveformAnalysis:MissingVariable','Missing MAT variable %s.',names{k}); end
end
function verify_identity(metadata,manifest)
require(metadata,{'run_id','source_identity'});
assert(strcmp(metadata.run_id,manifest.run_id),'WaveformAnalysis:RunIdentity','Diagnostic validation failed.');
assert(isequaln(metadata.source_identity,manifest.source_identity),'WaveformAnalysis:SourceIdentity','Diagnostic validation failed.');
end
function verify_waveform_metadata(metadata,manifest)
verify_identity(metadata,manifest);
require(metadata,{'schema_version','units','conventions','design_config'});
assert(strcmp(metadata.schema_version,'mamyshev_waveforms_v1'),'WaveformAnalysis:Schema','Diagnostic validation failed.');
assert(strcmp(metadata.units.field,'sqrt(W)') && strcmp(metadata.units.t,'ps') && ...
    strcmp(metadata.units.f,'THz') && strcmp(metadata.units.energy,'nJ'),'WaveformAnalysis:Units','Diagnostic validation failed.');
assert(isequaln(metadata.units,manifest.units) && isequaln(metadata.design_config,manifest.design_config), ...
    'WaveformAnalysis:MetadataMismatch');
assert(strcmp(metadata.conventions.time_to_frequency,'fftshift(ifft(A,[],1),1)'), ...
    'WaveformAnalysis:FFTConvention');
end
function path=safe_path(root,name)
assert(ischar(name) && ~isempty(name) && name(1)~='/' && ...
    isempty(regexp(name,'(^|[/\\])\.\.([/\\]|$)','once')),'WaveformAnalysis:UnsafePath','Diagnostic validation failed.');
path=fullfile(root,name); assert(isfile(path),'WaveformAnalysis:MissingArtifact','Missing %s.',name);
end
function files=draw_figures(output_dir,grid,views,raw,post,rounds)
titles={'SF1 before tracker','SF1 after production tracker','After pigtail','Saved compressed output'};
files={'time_domains.png','frequency_domains.png','round_comparison.png'};
fig=figure('Visible','off','Position',[100 100 1600 950]); cleanup=onCleanup(@()close(fig));
for k=1:4
    subplot(2,3,k);
    if isempty(views{k}), text(0.1,0.5,'Field unavailable; no reconstruction'); axis off;
    else, plot(grid.t,views{k}.power,'-','LineWidth',0.7); xlabel('Time (ps)'); ylabel('Power (W)'); grid_on(); end
    title(titles{k});
end
for plane_index=[4 3]
    subplot(2,3,9-plane_index);
    if isempty(views{plane_index}), text(0.1,0.5,'Field unavailable; no reconstruction'); axis off;
    else
        power=views{plane_index}.power; [peak,index]=max(power); ids=find(power>=peak/2);
        halfspan=min(grid.time_window_period_ps/4,max(10*grid.dt_ps,5*(grid.t(ids(end))-grid.t(ids(1)))));
        selection=abs(grid.t-grid.t(index))<=halfspan;
        plot(grid.t(selection),power(selection),'.-','MarkerSize',7,'LineWidth',0.7);
        xlabel('Original time samples (ps)'); ylabel('Power (W)'); grid_on();
    end
    title([titles{plane_index} ': peak-region view']);
end
sgtitle('Saved samples: no smoothing, interpolation, normalization or extra alignment');
print(fig,fullfile(output_dir,files{1}),'-dpng','-r120'); clear cleanup;
fig=figure('Visible','off','Position',[100 100 1500 900]); cleanup=onCleanup(@()close(fig));
for k=1:4
    subplot(2,2,k);
    if isempty(views{k}), text(0.1,0.5,'Field unavailable; no reconstruction'); axis off;
    else, plot(grid.f,views{k}.psd,'-','LineWidth',0.7); xlabel('Absolute frequency (THz), negative bins retained'); ylabel('Spectral energy density (nJ/THz)'); grid_on(); end
    title(titles{k});
end
sgtitle('fftshift(ifft(A)); PSD = |spectrum|^2 (N dt)^2 / 1000');
print(fig,fullfile(output_dir,files{2}),'-dpng','-r120'); clear cleanup;
fig=figure('Visible','off','Position',[100 100 1500 1050]); cleanup=onCleanup(@()close(fig));
labels=arrayfun(@(x)sprintf('RT %d',x.roundtrip),rounds,'UniformOutput',false);
subplot(3,2,1); hold on; for k=1:numel(raw), plot(grid.t,raw{k}.power); end; title('Before tracker'); xlabel('Time (ps)'); ylabel('Power (W)'); legend(labels,'Location','best'); grid_on();
subplot(3,2,2); hold on; for k=1:numel(post), plot(grid.t,post{k}.power); end; title('After production tracker; no extra alignment'); xlabel('Time (ps)'); ylabel('Power (W)'); grid_on();
subplot(3,2,3); hold on; for k=1:numel(raw), plot(grid.f,raw{k}.psd); end; xlabel('Absolute frequency (THz)'); ylabel('PSD (nJ/THz)'); grid_on();
subplot(3,2,4); hold on; for k=1:numel(post), plot(grid.f,post{k}.psd); end; xlabel('Absolute frequency (THz)'); ylabel('PSD (nJ/THz)'); grid_on();
subplot(3,2,5); plot([rounds.roundtrip],arrayfun(@(x)x.pre_tracker.energy_trapz_nJ,rounds),'-o'); xlabel('Completed round'); ylabel('Pre-tracker energy (nJ)'); grid_on();
subplot(3,2,6); plot([rounds.roundtrip],arrayfun(@(x)x.pre_intensity_relative_L2_previous.value,rounds),'-o'); hold on;
plot([rounds.roundtrip],arrayfun(@(x)x.post_intensity_relative_L2_previous.value,rounds),'-s'); xlabel('Completed round'); ylabel('Intensity relative L2 to previous'); legend('Pre tracker','Post tracker'); grid_on();
sgtitle('Round comparison is diagnostic; no stable-single-pulse classification');
print(fig,fullfile(output_dir,files{3}),'-dpng','-r120'); clear cleanup;
end
function grid_on()
grid on;
end
function write_json(path,value)
assert(~isfile(path),'WaveformAnalysis:ExistingEvidence','Diagnostic validation failed.');
temporary=[path '.tmp']; assert(~isfile(temporary),'WaveformAnalysis:ExistingEvidence','Diagnostic validation failed.');
bytes=unicode2native([jsonencode(value,'ConvertInfAndNaN',true,'PrettyPrint',true) newline],'UTF-8');
fid=fopen(temporary,'wb'); assert(fid>=0,'WaveformAnalysis:WriteError','Diagnostic validation failed.');
try
    count=fwrite(fid,bytes,'uint8'); closed=fclose(fid); fid=-1;
    assert(count==numel(bytes) && closed==0,'WaveformAnalysis:WriteError','Diagnostic validation failed.');
catch exception
    if fid>=0, fclose(fid); end
    rethrow(exception);
end
[ok,message]=movefile(temporary,path); assert(ok,'WaveformAnalysis:WriteError','%s',message);
end
