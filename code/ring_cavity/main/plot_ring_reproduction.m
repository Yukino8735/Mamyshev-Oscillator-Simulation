function metrics = plot_ring_reproduction(result,output_dir)
%PLOT_RING_REPRODUCTION Plot raw spectra, with no fitted/smoothed/scaled data.
f = result.f_THz; N = numel(f); dt = result.dt_ps;
keep = f>0;
[lambda,order] = sort(299792.458./f(keep));
fields = [result.before_SF1,result.transmitted_SF1,result.rejected_SF1,result.tail_fields];
Sf = abs(fftshift(ifft(fields,[],1),1)).^2*(N*dt)^2/1e3;
S = Sf(keep,:); S = S(order,:).*299792.458./lambda.^2;
labels = [{'Before SF1','Transmitted SF1','Rejected SF1'}, ...
    arrayfun(@(L) sprintf('Output + %.2f m fiber',L),result.cfg.tail_lengths_m,'UniformOutput',false)];
metrics = zeros(size(fields,2),8);
for k = 1:size(fields,2)
    [peak,imax] = max(S(:,k));
    above = find(S(:,k)>peak*.1);
    bounds = [NaN NaN];
    if ~isempty(above), bounds = lambda(above([1 end])).'; end
    near1040 = lambda>1037 & lambda<1043;
    shoulder = lambda>1046 & lambda<1054;
    edge = [1:ceil(.02*N),floor(.98*N):N];
    metrics(k,:) = [sum(abs(fields(:,k)).^2)*dt/1e3,trapz(lambda,S(:,k)), ...
        peak,lambda(imax),bounds, ...
        min(S(near1040,k))/max(mean(S(shoulder,k)),eps), ...
        sum(abs(fields(edge,k)).^2)/sum(abs(fields(:,k)).^2)];
end
tab = array2table(metrics,'VariableNames',{'Energy_nJ','SpectralIntegral_nJ', ...
    'Peak_nJ_per_nm','Peak_nm','TenPercentLeft_nm','TenPercentRight_nm', ...
    'NotchRatio_1040_to_1050','TimeEdgeEnergyFraction'},'RowNames',labels);
writetable(tab,fullfile(output_dir,'metrics.csv'),'WriteRowNames',true);
spectra_table = array2table([lambda,S],'VariableNames', ...
    [{'Wavelength_nm'},matlab.lang.makeValidName(labels)]);
writetable(spectra_table,fullfile(output_dir,'raw_spectra.csv'));
writematrix(result.history,fullfile(output_dir,'convergence.csv'));
fig = light_figure([50 50 1100 700]);
tiledlayout(2,2,'TileSpacing','compact');
nexttile; plot(lambda,S(:,1:3),'LineWidth',1); xlim([990 1190]);
xlabel('Wavelength (nm)'); ylabel('Energy spectral density (nJ/nm)');
legend(labels(1:3),'Location','best'); title('Sampling ports (raw spectra)');
nexttile; plot(lambda,S(:,4:end),'LineWidth',1); xlim([990 1190]);
xlabel('Wavelength (nm)'); ylabel('Energy spectral density (nJ/nm)');
legend(labels(4:end),'Location','best'); title('Output pigtail comparison (raw)');
nexttile; plot(result.history(:,1),result.history(:,2:3),'LineWidth',1.2);
xlabel('Roundtrip'); ylabel('Energy (nJ)'); legend('Output','Cavity return');
nexttile; semilogy(result.history(:,1),result.history(:,4:5),'LineWidth',1.2);
yline(result.cfg.tolerance,'k--'); xlabel('Roundtrip'); ylabel('Relative change');
legend('Energy','Spectrum','Tolerance');
sgtitle(sprintf('%s | %s | %d roundtrips',strrep(result.case_name,'_',' '),result.status,result.rt));
exportgraphics(fig,fullfile(output_dir,'diagnostics.png'),'Resolution',150); close(fig);
for k = 1:numel(result.cfg.tail_lengths_m)
    fig = light_figure([50 50 650 420]);
    plot(lambda,S(:,k+3),'Color',[0 .447 .741],'LineWidth',1.2);
    xlim([900 1280]); ylim([0 max(1.2,1.05*max(S(:,k+3)))]); box on;
    xlabel('Wavelength (nm)'); ylabel('Energy Spectral Density (nJ/nm)');
    exportgraphics(fig,fullfile(output_dir,sprintf('spectrum_tail_%03dmm.png',round(1000*result.cfg.tail_lengths_m(k)))),'Resolution',180);
    close(fig);
end
disp(tab);
end

function fig = light_figure(position)
fig = figure('Color','w','Position',position);
if isprop(fig,'Theme'), fig.Theme = 'light'; end
set(fig,'DefaultAxesColor','w','DefaultAxesXColor','k','DefaultAxesYColor','k', ...
    'DefaultTextColor','k','DefaultLegendColor','w','DefaultLegendTextColor','k');
end
