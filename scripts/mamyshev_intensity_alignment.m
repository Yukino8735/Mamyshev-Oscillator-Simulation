function [result,aligned]=mamyshev_intensity_alignment(current,reference,dt_ps)
%MAMYSHEV_INTENSITY_ALIGNMENT Integer cyclic whole-window intensity alignment.
% Shift means circshift(current, shift_samples) to match reference. No scaling,
% smoothing, interpolation, fractional shift or local warping is performed.
assert(isnumeric(current) && isvector(current) && isnumeric(reference) && ...
    isvector(reference) && numel(current)==numel(reference) && numel(current)>=2, ...
    'Stationarity:IntensityShape','Equal nonempty sampled intensity vectors required.');
current=current(:); reference=reference(:); N=numel(current);
assert(isreal(current) && isreal(reference) && all(isfinite(current)) && ...
    all(isfinite(reference)) && all(current>=0) && all(reference>=0), ...
    'Stationarity:IntensityFinite','Intensities must be real, finite, nonnegative.');
assert(isscalar(dt_ps) && isreal(dt_ps) && isfinite(dt_ps) && dt_ps>0, ...
    'Stationarity:Sampling','Positive ps sampling interval required.');
result=struct('status','not_verified','raw_relative_L2',NaN,'aligned_relative_L2',NaN, ...
    'shift_samples',NaN,'shift_ps',NaN,'integer_precision_ps',dt_ps, ...
    'shift_convention','circshift(current,shift_samples) compared with reference', ...
    'tie_relative_tolerance',1e-12,'ambiguity_relative_tolerance',1e-8, ...
    'tie_absolute_tolerance',NaN,'ambiguity_absolute_tolerance',NaN, ...
    'maximum_correlation',NaN,'selected_correlation',NaN, ...
    'tie_lag_count',0,'near_max_local_peak_count',0, ...
    'representative_near_max_lags',[],'lag_list_truncated',false, ...
    'ambiguous',false,'ambiguity_reason','','missing_reason','');
aligned=current; denominator=norm(reference,2); product=norm(current,2)*denominator;
if denominator==0
    result.missing_reason='Reference intensity has zero norm; relative error and alignment undefined.';
    return;
end
result.raw_relative_L2=norm(current-reference,2)/denominator;
correlation=real(ifft(fft(reference).*conj(fft(current))));
assert(all(isfinite(correlation)) && isfinite(product),'Stationarity:CorrelationOverflow','Finite correlation required.');
maximum=max(correlation); tie_tolerance=1e-12*product; ambiguity_tolerance=1e-8*product;
lags=(0:N-1)'; lags(lags>=ceil(N/2))=lags(lags>=ceil(N/2))-N;
ties=find(maximum-correlation<=tie_tolerance);
ordering=sortrows([abs(lags(ties)),lags(ties),ties],[1 2]); selected=ordering(1,3);
shift=lags(selected); aligned=circshift(current,shift);
% Adjacent samples on a broad correlation shoulder are not independent peaks.
% A true plateau/tie remains explicitly ambiguous; a constant correlation has
% all lags tied and is not interpreted as uniquely aligned.
local_max=correlation>=circshift(correlation,1) & correlation>=circshift(correlation,-1);
near=find(local_max & maximum-correlation<=ambiguity_tolerance);
near_lags=sortrows([abs(lags(near)),lags(near)],[1 2]);
result.status='observed'; result.aligned_relative_L2=norm(aligned-reference,2)/denominator;
result.shift_samples=shift; result.shift_ps=shift*dt_ps;
result.tie_absolute_tolerance=tie_tolerance; result.ambiguity_absolute_tolerance=ambiguity_tolerance;
result.maximum_correlation=maximum; result.selected_correlation=correlation(selected);
result.tie_lag_count=numel(ties); result.near_max_local_peak_count=numel(near);
result.representative_near_max_lags=near_lags(1:min(32,end),2)';
result.lag_list_truncated=numel(near)>32;
result.ambiguous=numel(ties)>1 || numel(near)>1;
if numel(ties)>1 && numel(near)>1
    result.ambiguity_reason='Multiple numerical ties and near-maximum local correlation peaks.';
elseif numel(ties)>1
    result.ambiguity_reason='Multiple lags tied within the fixed numerical tie tolerance.';
elseif numel(near)>1
    result.ambiguity_reason='Distinct local correlation maxima within the fixed ambiguity tolerance.';
end
end
