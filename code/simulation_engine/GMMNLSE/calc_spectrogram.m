function [psd,t_spectrogram,f_spectrogram,fig,ax,cb] = calc_spectrogram(t,f,field,varargin)
%CALC_SPECTROGRAM 
% This code computes the spectrogram with fine resolution in both the time 
% and frequency domain of the input field with the convention of Fourier 
% Transform being "ifft".
%
% *This code works only for a pulse.
% Due to a better resolutioin, the sampling in time and frequency can be
% large. I calculate the RMS duration and bandwidth to specifically filter
% out the points with the pulse to save the memory.
%
%   Input arguments:
%
%   t - (N,1); time (ps)
%   f - (N,1); frequency (THz)
%   field - (N,1); the pulse electric field (W)
%
%   Optional input arguments:
%
%       tlim - (1,2) matrix; the range of the time to plot (ps) (default: [])
%       wavelengthlim - (1,2) matrix; the range of the wavelength to plot (nm) (default: [])
%       t_feature - a scalar; the ratio of the tiny pulse structure vs. pulse duration you want to resolve;
%                   the larger the number, the higher the time resolution (default: 50)
%       f_feature - a scalar; the ratio of the tiny spectral structure vs. pulse bandwidth you want to revolve
%                   the larger the number, the higher the frequency resolution (default: 50)
%       plot_yes - true or false; whether to plot or not (default: true)
%       lambda_or_f - true (use wavelength) or false (use frequency);
%                     plot with frequency (THz) or wavelength (nm);
%                     If plot_yes=false, this acts nothing
%                    (default: true)
%       log_yes - true or false; log plot for the spectrogram (default: false)
%
%   *t_feature is limited by having the maximum window to be N/2 (you can't revolve any time structures smaller than the inverse of this)
%   *f_feature is limited by having the minimum window to pulse_duration (you can't resolve any frequency structures smaller than the inverse of this)
%   To resolve finer time structures, you can pad the field with zeros to increase the time window size.
%   To resolve finer frequency structures, you need to obtain your field with a finer sampling.
%
%   Output arguments:
%
%       psd - the power spectral density of the spectrogram
%             Its unit is nJ/nm  if lambda_or_f=true, or
%                         nJ/THz if lambda_or_f=false
%       t_spectrogram - the time sampling points of the spectrogram (ps)
%       f_spectrogram - the frequency sampling points of the spectrogram (THz)
%       fig, ax, cb - the figure, axis, and colorbar handles of the spectrogram
%
% If the sliding window of the stft is too large, it's enough to resolve
% the frequency but unable to resolve the time variations. Vice versa for
% using a small sliding window. This is the limit of stft if the signal
% constains fast varying feature in time or in frequency domain.
% This code calculates the normalized power spectral density (PSD) of the 
% spectrograms of different window sizes and finds the maximum and minimum 
% of each point. If it's a point where there should be signal, it always 
% has some intensity whatever the window size is. If it's a point where 
% there shouldn't be signal but it has some intensity under certain window
% sizes, it must come from the energy spread due to low resolution. In this
% case, find the minimum of intensity of this point from all spectrograms.
%
%
% It calculates if good resolution is achievable with a common stft.
% If not, it'll use the "improved" (multi-resolution) stft based on the paper below:
% Khan, N. A.; Jafri, M. N. & Qazi, S. A.
% "Improved resolution short time Fourier transform",
% 7th International Conference on Emerging Technologies, 1-3  (2011)
%
% This paper normalizes the spectrogram only w.r.t. the intensity.
% I realized that this isn't enough. It confirms good resolution only in
% time but not in frequency. Therefore, I further apply another
% normalization w.r.t. the spectrum. I eventually obtain the result from
% the minimum of these two results to avoid any spread of energy due to
% sliding windows of not enough resolution.
%
%   by Yi-Hao Chen @ Ph.D. candidate in Applied Physics, Cornell University (2021)

%% Input arguments
numvarargin = nargin - 3;
% Set defaults for optional inputs
optargs = {[],[],50,50,true,true,false};
% Now put these defaults into the valuesToUse cell array, 
% and overwrite the ones specified in varargin.
optargs(1:numvarargin) = varargin;
% Place optional args in memorable variable names
[tlim,wavelengthlim,t_feature,f_feature,plot_yes,lambda_or_f,log_yes] = optargs{:};
if nargin < 3 || nargin > 10
    error('analyze_sim:InputArgumentsError',...
          'The number of input arguments doesn''t match the requirements. The minimum of 3 inputs are required.');
end

%% find the pulse
[t,f,field] = useful_part(t,f,field,t_feature);

%% Some calculations
c = 299792.458; % nm/ps
wavelength = c./f; % nm
N = size(field,1);
dt = t(2)-t(1); % ps
factor_correct_unit = (N*dt)^2/1e3; % to make the spectrum of the correct unit "nJ/THz"
                                    % "/1e3" is to make pJ into nJ
factor = c./wavelength.^2; % change the spectrum from frequency domain into wavelength domain
spectrum_f = abs(fftshift(ifft(field),1)).^2*factor_correct_unit;
spectrum_lambda = spectrum_f.*factor;
intensity = abs(field).^2;

%{
f0 = feval(@(x)x(1), ifftshift(f,1));
pulse_phase = unwrap(angle(field));
smooth_range = 50;
pulse_phase = smooth(pulse_phase,smooth_range);

pulse_inst_freq = -(pulse_phase(3:end)-pulse_phase(1:end-2))/(2*dt)/(2*pi)+f0; % THz; I use "central difference" to calculate the slope here
% Remove useless inst. frequency when the intensity is too weak
pulse_inst_freq(intensity(2:end-1)<max(intensity(2:end-1))/100) = NaN;
max_pulse_inst_freq = max(pulse_inst_freq(:));
min_pulse_inst_freq = min(pulse_inst_freq(:));
%}

% -------------------------------------------------------------------------
% Unit explanation:
%   intensity = abs(field).^2;
%   energy = trapz(t,intensity) = trapz(intensity)*dt;       % pJ
%   
%   spectrum_unknown_unit = abs(fftshift(ifft(field),1)).^2;
%
%   Parseval's theorem: sum(intensity) = sum(spectrum_unknown_unit)*N;
%                       * Note that spectrum_unknown_unit is from "ifft".
%   therefore sum(intensity)*dt = sum(spectrum_unknown_unit)*N*dt
%                               = sum(spectrum_unknown_unit)*(N*dt)^2/(N*dt)
%                               = sum(spectrum_unknown_unit)*(N*dt)^2*df
%                               = sum(spectrum_f)*df
%
%   spectrum_f = spectrum_unknown_unit*(N*dt)^2;
%   energy = trapz(f,spectrum_f) = trapz(spectrum_f)*df      % pJ
%                                = trapz(spectrum_f)/(N*dt);
%
%   c = 299792.458;     % nm/ps
%   wavelength = c./f;  % nm
%   spectrum_wavelength = spectrum_f.*(c./wavelength.^2);
%   energy = -trapz(wavelength,spectrum_wavelength);         % pJ
% -------------------------------------------------------------------------

% the upper and lower limit of the plots
max_intensity = max(intensity(:));
min_intensity = min(intensity(:));

% Normalize the spectrum
if lambda_or_f
    spectrum = spectrum_lambda;
else
    spectrum = spectrum_f;
end
max_sp = max(spectrum);
min_sp = min(spectrum);
spectrum = (spectrum-min_sp)./(max_sp-min_sp);

%% spectrogram information: window size, nfft, noverlap, Fs
% Automatically determine the size of the sliding window of the stft
f_stft = (-floor(N/2):ceil(N/2)-1)/N';
tmp = spectrum_f; tmp(tmp<max(tmp)/50) = 0; [bandwidth,f0_pulse] = calc_RMS(f_stft,tmp); bandwidth = bandwidth*2*sqrt(2);
window_sizeMin_highFResolution = max(10,ceil(min(f_feature/bandwidth,N/2))); % minimum window determines the minimum sampling rate under the frequency domian
                                                                             % restriction: window size muct be larger than 10
tmp = intensity; tmp(tmp<max(tmp)/50) = 0; [duration,t0_pulse] = calc_RMS((0:N-1)',tmp); duration = duration*2*sqrt(2);
window_sizeMax = max(10,duration/t_feature); % maximum window determines the minimum sampling rate under the time domian
                                             % restriction: window size muct be larger than 10
window_sizeMin = min(ceil(duration),window_sizeMin_highFResolution); % in case the window becomes too large for resolving the frequency well
                                                                     % If it's too large, this isn't "short-time" Fourier Transform anymore.
if window_sizeMin <= window_sizeMax
    enough_resolution = true;
    window_size = round((window_sizeMin+window_sizeMax)/2); % the window for the common short-time-Fourier-Transform
else % start with the minimum window size; a multiresolution stft will be applied below
    enough_resolution = false;
    window_size = ceil(window_sizeMax);
    nfft_highFResolution = 2^nextpow2(window_sizeMin_highFResolution); % the number of points for fft
end

Fs = 1/dt; % the sampling rate

%% Compute the first spectrogram
% "fft" in Agrawal = "ifft" in MATLAB
% F[x*]=invF[x]*
% And "spectrogram" take "fft operation in MATLAB", so we need to
% transform it into "fft in Agrawal", that is, "ifft in MATLAB".
nfft = max(256,2^nextpow2(window_size)); % the number of points for fft
noverlap = floor(window_size*0.9); % the overlap of the window; I choose to have 90% overlap.
[~,f_tmp,t_tmp,psd] = spectrogram(conj(field),window_size,noverlap,nfft,Fs,'centered','yaxis'); % specifying 'centered' is required in case that the field is real-valued

if enough_resolution
    final_df_tmp = Fs/nfft;
    final_f_tmp = f_tmp;
else
    % The final generated frequency sampling is determined by the largest nfft
    final_df_tmp = Fs/nfft_highFResolution;
    final_f_tmp = (-(ceil(nfft_highFResolution/2)-1):floor(nfft_highFResolution/2))'*final_df_tmp;
end

final_dt_tmp = mean(diff(t_tmp)); % this dt is the finest and is chosen as the final dt in a multi-resolution spectrogram

I_psd = sum(psd,1)*(Fs/nfft);    I_psd(I_psd<max(I_psd)/100) = inf; % intensity from psd
f_psd = sum(psd,2)*final_dt_tmp; f_psd(f_psd<max(f_psd)/100) = inf; % spectrum from psd
normT_psd = psd./I_psd; % transformed into normalized energy w.r.t. the intensity
normF_psd = psd./f_psd; % transformed into normalized energy w.r.t. the spectrum

%% Show only the region with the pulse
% *Important!
% Due to intention to achieve high resolution of this code, the sampling
% can be high. This extremely slows down Matlab and eats up lots of memory
% (up to >30 GB). Hence, it's important to pick only the region that
% contains the useful information
if isempty(tlim)
    useful_t =  (t0_pulse + duration*3*[-1,1])*dt; % time points around the pulse
    
    tlim = useful_t + t(1); tlim(1) = max(t(1),tlim(1)); tlim(2) = min(t(end),tlim(2));
else
    useful_t = tlim - t(1) + final_dt_tmp*[-1,1];
end
% the desired region is determined by the user input, wavelengthlim, or
% automatically selecting points near the pulse
if isempty(wavelengthlim)
    f0_pulse = f0_pulse*Fs; % center frequency
    bandwidth = bandwidth*Fs; % frequency bandwidth
    useful_f =  f0_pulse + bandwidth*3*[-1,1]; % frequency points around the pulse
    
    flim = useful_f + f(floor(N/2)+1); flim(1) = max(f(1),flim(1)); flim(2) = min(f(end),flim(2));
    wavelengthlim = c./[flim(2),flim(1)];
else
    flim = c./[wavelengthlim(2),wavelengthlim(1)];
    useful_f = flim - f(floor(N/2)+1) + final_df_tmp*[-1,1];
end
useful_t_idx = t_tmp>useful_t(1) & t_tmp<useful_t(2);
useful_f_idx = final_f_tmp>useful_f(1) & final_f_tmp<useful_f(2);

% The reason that there are t_spectrogram, f_spectrogram and t_tmp, f_tmp
% is due to the fact that the output t and f of MATLAB spectrogram() 
% always starts with 0 and is centered at 0 respectively. Whereas, 
% t_spectrogram and f_spectrogram are defined by user inputs.
t_spectrogram = t_tmp + t(1);                  t_spectrogram = t_spectrogram(useful_t_idx); % the time points of the spectrogram, which corresponds to the input "t"
f_spectrogram = final_f_tmp + f(floor(N/2)+1); f_spectrogram = f_spectrogram(useful_f_idx); % the frequency points of the spectrogram, which corresponds to the input "f"

final_t_tmp = t_tmp(useful_t_idx); % from "spectrogram()"; start with 0
final_f_tmp = final_f_tmp(useful_f_idx); % from "spectrogram()"; centered with 0

normT_psd = interp2(t_tmp,f_tmp,normT_psd,final_t_tmp,final_f_tmp,'linear',0);
normF_psd = interp2(t_tmp,f_tmp,normF_psd,final_t_tmp,final_f_tmp,'linear',0);

%% Multi-resolution spectrogram
% Use the multiresolution approach from the paper mentioned in the
% comment at the beginning.
if ~enough_resolution
    max_normT_psd = normT_psd; min_normT_psd = normT_psd;
    max_normF_psd = normF_psd; min_normF_psd = normF_psd;

    num_s = 10; % the number of spectrograms of different reolutions to compute
    window_size_all = round(sin(linspace(0,1,num_s)*pi/2).^2*(window_sizeMin-window_sizeMax)+window_sizeMax); % sampled windows are around the minimum and maximum windows
    %window_size_all = round(linspace(window_sizeMax,window_sizeMin,num_s)); % linearly sampled windows from minimum to maximum ones
    for i = 2:num_s
        nfft = max(256,2^nextpow2(window_size_all(i))); % the number of points for fft
        noverlap = floor(window_size_all(i)*0.9); % the overlap of the window; I choose to have 90% overlap.
        [~,f_tmp,t_tmp,psd] = spectrogram(conj(field),window_size_all(i),noverlap,nfft,Fs,'centered','yaxis'); % specifying 'centered' is required in case that the field is real-valued
        
        I_psd = sum(psd,1)*(Fs/nfft);         I_psd(I_psd<max(I_psd)/100) = inf;
        f_psd = sum(psd,2)*mean(diff(t_tmp)); f_psd(f_psd<max(f_psd)/100) = inf;
        normT_psd = psd./I_psd; % transformed into normalized energy w.r.t. the intensity
        normF_psd = psd./f_psd; % transformed into normalized energy w.r.t. the spectrum

        normT_psd = interp2(t_tmp,f_tmp,normT_psd,final_t_tmp,final_f_tmp,'linear',0);
        normF_psd = interp2(t_tmp,f_tmp,normF_psd,final_t_tmp,final_f_tmp,'linear',0);
        
        max_normT_psd = max(cat(3,max_normT_psd,normT_psd),[],3);
        min_normT_psd = min(cat(3,min_normT_psd,normT_psd),[],3);
        max_normF_psd = max(cat(3,max_normF_psd,normF_psd),[],3);
        min_normF_psd = min(cat(3,min_normF_psd,normF_psd),[],3);
    end
    
    % Recover back to the correct unit
    I_spectrogram = interp1(t,intensity,t_spectrogram,'linear',0);
    sf_spectrogram = interp1(f,spectrum_f,f_spectrogram,'linear',0);
    T_psd = (max_normT_psd.*min_normT_psd).*I_spectrogram*final_df_tmp; % use the signal intensity to recover from normalized energy
    F_psd = (max_normF_psd.*min_normF_psd).*sf_spectrogram*final_dt_tmp; % use the signal spectrum to recover from normalized energy
    
    % Normalize them for comparison after multiplying max_psd and min_psd
    current_T_psd_energy = sum(sum(T_psd,1),2);
    current_F_psd_energy = sum(sum(F_psd,1),2);
    calibration_factor_T = 1/current_T_psd_energy;
    calibration_factor_F = 1/current_F_psd_energy;
    T_psd = T_psd*calibration_factor_T;
    F_psd = F_psd*calibration_factor_F;
    psd = min(cat(3,T_psd,F_psd),[],3);
else
    I_spectrogram = interp1(t,intensity,t_spectrogram,'linear',0);
    psd =normT_psd.*I_spectrogram*final_df_tmp; % use the signal intensity to recover from normalized energy
end
% Normalized to the total energy
current_psd_energy = sum(sum(psd,1),2)*final_df_tmp*final_dt_tmp;
original_energy = sum(abs(field).^2)/Fs;
calibration_factor = original_energy/current_psd_energy;
psd = psd*calibration_factor;

%% Finalize the psd
% psd: power spectral density
% To calculate psd, the normalization w.r.t. the sampling window of the
% spectrogram needs to be taken into account. Since the type of the 
% window is chosen by Matlab, I use "psd" output from "spectrogram"
% function instead of calculating it myself.
wavelength_spectrogram = c./f_spectrogram; % nm
factor_spectrogram = c./wavelength_spectrogram.^2; % change the spectrum from frequency domain into wavelength domain
if lambda_or_f
    psd = psd.*factor_spectrogram/1e3; % nJ; it's transformed into the correct unit under wavelength domain
                                       % "/1e3" is to make pJ into nJ.
else
    psd = psd/1e3; % nJ; "/1e3" is to make pJ into nJ.
end

%% Plot
if plot_yes
    % log plot
    if log_yes
        % For log scale, the minimum will be -inf because psd contains
        % zero. Therefore, we need to find the minimum psd value for those
        % being nonzero. The minimum log values is set to be -30.
        min_colormap_psd = min(psd(psd~=0));
        
        psd = 10*log10(psd); psd = psd - max(psd(:));
        min_colormap_psd = max(10*log10(min_colormap_psd),-30);
    end
    
    % start the figure and set its size
    fig = figure('Name','Spectrogram');
    fp = get(fig,'position');
    screen_size = get(0,'ScreenSize');
    original_top = screen_size(4)-fp(2)-fp(4);
    set(gcf,'position',[fp(1) screen_size(4)-original_top-fp(4)*7/4 fp(3)*5.5/4 fp(4)*7/4]);

    % spectrogram
    ax = subplot(3,3,[4,5,7,8]);
    positive_wavelength = find(wavelength_spectrogram>0,1);
    if lambda_or_f
        pcolor(t_spectrogram,wavelength_spectrogram(positive_wavelength:end),psd(positive_wavelength:end,:))
    else
        pcolor(t_spectrogram,f_spectrogram(positive_wavelength:end),psd(positive_wavelength:end,:))
    end
    shading interp; colormap(jet);
    cb = colorbar('location','south','Color','[1 1 1]');
    if log_yes
        caxis([min_colormap_psd,0]);
    end
    %{
    if lambda_or_f
        cb.Label.String = 'PSD (nJ/nm)'; % the unit of the spectrogram colorbar, power spectral density
    else
        cb.Label.String = 'PSD (nJ/THz)'; % the unit of the spectrogram colorbar, power spectral density
    end
    %}
    xlabel('Time (ps)');
    title('Spectrogram');
    set(gca,'fontsize',14);
    % field
    ax2 = subplot(3,3,[1,2]);
    %yyaxis left
    h1_1 = plot(t,intensity); % power (W)
    set(h1_1,'linewidth',2);
    xlim(tlim);
    ylim([min_intensity max_intensity]);
    ylabel('Power (W)');
    %{
    yyaxis right
    h1_2 = plot(t(2:end-1),pulse_inst_freq); % instantaneous frequency (THz)
    set(h1_2,'linewidth',2);
    ylabel('Inst. freq. (THz)');
    ylim([min_pulse_inst_freq,max_pulse_inst_freq]);
    %}
    title('Field');
    set(gca,'fontsize',14);
    % spectrum
    positive_wavelength = find(wavelength>0,1);
    ax3 = subplot(3,3,[6,9]);
    if lambda_or_f
        h2 = plot(spectrum(positive_wavelength:end),wavelength(positive_wavelength:end));
    else
        h2 = plot(spectrum(positive_wavelength:end),f(positive_wavelength:end));
    end
    xlim([0,1]);
    if lambda_or_f
        ylim(wavelengthlim);
        ylabel('Wavelength (nm)');
    else
        ylim(c./[wavelengthlim(2),wavelengthlim(1)]);
        ylabel('Frequency (THz)');
    end
    xlabel('PSD (norm.)');
    set(h2,'linewidth',2); set(gca,'fontsize',14);
    title('Spectrum');

    % link their axes so that they have the same range of x,y-axes
    linkaxes([ax,ax2],'x'); linkaxes([ax,ax3],'y');
    set(ax2,'XTickLabel',''); set(ax3,'YTickLabel','');
end

end

%% helper function
function [t,f,field] = useful_part(t,f,field,t_feature)
% The "field" can have too much unuseful information. This function
% computes the pulse bandwidth and takes only the part that contains the
% pulse.

N = length(f);

min_downsampling_ratio = 1;

intensity = abs(field).^2;
spectrum = abs(fftshift(ifft(field),1)).^2;

% Duration is to make sure that there are enough sampling points in a pulse
duration = calc_RMS(t,intensity)*2*sqrt(2);
npts_in_pulse = ceil(duration/mean(diff(t)));
min_npts_in_pulse = 20;
max_downsampling_ratio = max(1,floor(npts_in_pulse/min_npts_in_pulse));

[bandwidth,f0] = calc_RMS(f,spectrum);
bandwidth = bandwidth*2*sqrt(2);

% Adjust the frequnecy sampling by downsampling
f0_original = f(floor(N/2)+1);
f_offset = f0 - f0_original;
f = f + f_offset; field = field.*exp(1i*2*pi*f_offset*t);
f_downsampling_ratio = max(min_downsampling_ratio,max(1,min(floor(abs(f(end)-f(1))/(bandwidth*t_feature/2)),max_downsampling_ratio)));
field = field(1:f_downsampling_ratio:end);

t = t(1:f_downsampling_ratio:end);
N_new = length(t);
f = f(floor(N/2)+1 - floor(N_new/2) : floor(N/2)+1 + ceil(N_new/2)-1);

end