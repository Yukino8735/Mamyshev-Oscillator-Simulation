function display_data = export_ring_spectrum_display(result_file, fwhm_nm, tail_length_m)
%EXPORT_RING_SPECTRUM_DISPLAY Raw spectrum plus explicitly labelled smoothing.
% export_ring_spectrum_display('.../result.mat', 2, 0)
% Smoothing is ONLY a display operation in the wavelength domain. No fitted
% envelope, artificial notch repair, wavelength shift or amplitude scaling.
if nargin < 2, fwhm_nm = 2; end
if nargin < 3, tail_length_m = 0; end
assert(isscalar(fwhm_nm) && isfinite(fwhm_nm) && fwhm_nm>0);
loaded = load(result_file,'result'); r = loaded.result;
[distance,k] = min(abs(r.cfg.tail_lengths_m-tail_length_m));
assert(distance<1e-9,'Requested tail length is not in this result');
field = r.tail_fields(:,k);
f = r.f_THz; N = numel(f); dt = r.dt_ps;
Sf = abs(fftshift(ifft(field))).^2*(N*dt)^2/1e3;
positive = f>0;
[lambda,index] = sort(299792.458./f(positive));
S = Sf(positive); S = S(index).*299792.458./lambda.^2;
% Use a uniform wavelength grid before convolution: the FFT grid is uniform
% in frequency, not wavelength. The grid spans far beyond the plotted band.
dlambda = min(.05,fwhm_nm/20);
grid_nm = (max(700,lambda(1)):dlambda:min(1500,lambda(end)))';
raw = interp1(lambda,S,grid_nm,'linear',0);
sigma_nm = fwhm_nm/(2*sqrt(2*log(2)));
x = (-ceil(5*sigma_nm/dlambda):ceil(5*sigma_nm/dlambda))'*dlambda;
kernel = exp(-.5*(x/sigma_nm).^2); kernel = kernel/sum(kernel);
smoothed = conv(raw,kernel,'same');
display_data = struct('wavelength_nm',grid_nm,'raw_nJ_per_nm',raw, ...
    'smoothed_nJ_per_nm',smoothed,'smoothing_fwhm_nm',fwhm_nm, ...
    'tail_length_m',tail_length_m,'source_result',result_file, ...
    'simulation_status',r.status,'case_name',r.case_name);
output_dir = fileparts(result_file);
stem = sprintf('display_tail_%03dmm_fwhm_%gnm',round(1000*tail_length_m),fwhm_nm);
save(fullfile(output_dir,[stem '.mat']),'display_data');
writetable(table(grid_nm,raw,smoothed,'VariableNames', ...
    {'Wavelength_nm','Raw_nJ_per_nm','SmoothedDisplay_nJ_per_nm'}),fullfile(output_dir,[stem '.csv']));
fig = figure('Visible','off','Color','w','Position',[50 50 1100 420]);
if isprop(fig,'Theme'), fig.Theme = 'light'; end
tiledlayout(1,2,'TileSpacing','compact');
nexttile;
plot(grid_nm,raw,'Color',[.7 .7 .7],'LineWidth',.7); hold on;
plot(grid_nm,smoothed,'Color',[0 .447 .741],'LineWidth',1.2);
xlim([1000 1180]); ylim([0 max(1.2,max(smoothed)*1.05)]); box on;
xlabel('Wavelength (nm)'); ylabel('Energy spectral density (nJ/nm)');
legend('Raw simulation',sprintf('Gaussian display, FWHM %g nm',fwhm_nm),'Location','northwest');
title('Raw data retained; no amplitude rescaling');
nexttile;
plot(grid_nm,smoothed,'Color',[0 .447 .741],'LineWidth',1.2);
xlim([900 1280]); ylim([0 max(1.2,max(smoothed)*1.05)]); box on;
xlabel('Wavelength (nm)'); ylabel('Energy spectral density (nJ/nm)');
title(sprintf('Smoothed display only | FWHM = %g nm',fwhm_nm));
exportgraphics(fig,fullfile(output_dir,[stem '.png']),'Resolution',180);
close(fig);
fig = figure('Visible','off','Color','w','Position',[50 50 650 420]);
if isprop(fig,'Theme'), fig.Theme = 'light'; end
plot(grid_nm,smoothed,'Color',[0 .447 .741],'LineWidth',1.2);
xlim([900 1280]); ylim([0 max(1.2,max(smoothed)*1.05)]); box on;
xlabel('Wavelength (nm)'); ylabel('Energy Spectral Density (nJ/nm)');
title(sprintf('Smoothed display (Gaussian FWHM %g nm)',fwhm_nm));
exportgraphics(fig,fullfile(output_dir,[stem '_smooth_only.png']),'Resolution',180);
close(fig);
fprintf('Display only: %g nm Gaussian FWHM; original %.5f nJ; smoothed %.5f nJ.\n', ...
    fwhm_nm,trapz(grid_nm,raw),trapz(grid_nm,smoothed));
end
