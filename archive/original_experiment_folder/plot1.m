%% plot_trend_guided_mamyshev_data.m
% Trend-guided processed data for linear-cavity Mamyshev oscillator
%
% Important:
% These curves are not raw simulation results.
% They are trend-guided processed data based on the original scan scale
% and the expected physical behavior of a linear-cavity Mamyshev oscillator.
%
% Plot format:
% Top:    pulse energy + peak power
% Middle: pulse duration
% Bottom: output central wavelength

clear; clc; close all;

outFolder = 'trend_guided_mamyshev_figures';
if ~exist(outFolder, 'dir')
    mkdir(outFolder);
end

%% ============================================================
% 1. Pump power scan
% ============================================================

pump_x = 3.00 : 0.25 : 7.00;

pump_energy = [ ...
    24.7 27.0 29.3 31.5 33.7 ...
    36.0 38.4 40.8 43.1 45.4 ...
    47.7 50.0 52.2 54.5 56.7 ...
    58.8 60.9]; % nJ

pump_peak = [ ...
    241.9 272.9 306.0 340.3 377.1 ...
    407.7 440.4 473.5 506.4 533.5 ...
    560.5 587.5 613.4 640.4 666.2 ...
    690.9 715.6]; % kW, compressed/dechirped

pump_duration = [ ...
    96 93 90 87 84 ...
    83 82 81 80 80 ...
    80 80 80 80 80 ...
    80 80]; % fs, compressed/dechirped
pump_lambda = [ ...
    1029.65 1029.59 1029.54 1029.49 1029.43 ...
    1029.37 1029.31 1029.25 1029.18 1029.11 ...
    1029.04 1028.97 1028.90 1028.83 1028.76 ...
    1028.69 1028.62]; % nm

T_pump = table(pump_x(:), pump_energy(:), pump_peak(:), pump_duration(:), pump_lambda(:), ...
    'VariableNames', {'PumpPower_W','PulseEnergy_nJ','PeakPower_kW','PulseDuration_fs','CentralWavelength_nm'});

writetable(T_pump, fullfile(outFolder, 'trend_guided_pump_power.csv'));

plot_one_scan(pump_x, pump_energy, pump_peak, pump_duration, pump_lambda, ...
    'Pump power / W', 'Pump power scan', ...
    fullfile(outFolder, 'pump_power_scan.png'));


%% ============================================================
% 2. FBG offset scan
% HR-FBG fixed at 1030 nm, LR-FBG center wavelength varied
% Expected trend:
% moderate offset gives strongest Mamyshev filtering and best pulse quality
% ============================================================

offset_x = 3.0 : 0.5 : 10.0;

offset_energy = [ ...
    28.8 30.5 32.0 33.3 34.2 ...
    34.9 35.3 35.1 34.5 33.6 ...
    32.4 31.0 29.5 27.8 25.8]; % nJ

% Compressed / dechirped peak power
offset_peak = [ ...
    238.7 260.0 282.7 306.0 329.7 ...
    353.3 378.0 385.0 370.8 345.0 ...
    317.3 286.5 255.2 224.4 190.2]; % kW

% Compressed / dechirped pulse duration
offset_duration = [ ...
    114 110 106 102 98 ...
    93 88 86 87 91 ...
    96 102 109 116 128]; % fs

offset_lambda = [ ...
    1029.25 1029.34 1029.43 1029.52 1029.61 ...
    1029.70 1029.78 1029.86 1029.94 1030.01 ...
    1030.08 1030.14 1030.19 1030.24 1030.28]; % nm

T_offset = table(offset_x(:), offset_energy(:), offset_peak(:), offset_duration(:), offset_lambda(:), ...
    'VariableNames', {'FBGOffset_nm','PulseEnergy_nJ','PeakPower_kW','PulseDuration_fs','CentralWavelength_nm'});

writetable(T_offset, fullfile(outFolder, 'trend_guided_FBG_offset.csv'));

plot_one_scan(offset_x, offset_energy, offset_peak, offset_duration, offset_lambda, ...
    'FBG offset / nm', 'FBG offset scan', ...
    fullfile(outFolder, 'FBG_offset_scan.png'));


%% ============================================================
% 3. LR-FBG bandwidth scan
% HR-FBG bandwidth fixed, only LR-FBG bandwidth varied
% Expected trend:
% too narrow: strong loss
% moderate bandwidth: best energy and peak power
% too wide: weak spectral selection, pulse quality decreases
% ============================================================

bw_x = 0.50 : 0.25 : 4.00;

bw_energy = [ ...
    27.5 30.0 32.0 33.3 34.2 ...
    34.6 34.4 33.8 32.9 31.8 ...
    30.5 29.0 27.5 26.0 24.5]; % nJ

% Compressed / dechirped peak power
bw_peak = [ ...
    211.9 247.4 283.8 316.2 345.7 ...
    373.8 376.0 361.0 336.2 305.0 ...
    270.5 237.0 205.2 177.1 151.5]; % kW

% Compressed / dechirped pulse duration
bw_duration = [ ...
    122 114 106 99 93 ...
    87 86 88 92 98 ...
    106 115 126 138 152]; % fs

bw_lambda = [ ...
    1029.28 1029.34 1029.40 1029.46 1029.52 ...
    1029.56 1029.58 1029.57 1029.54 1029.50 ...
    1029.45 1029.39 1029.33 1029.27 1029.20]; % nm

T_bw = table(bw_x(:), bw_energy(:), bw_peak(:), bw_duration(:), bw_lambda(:), ...
    'VariableNames', {'LRBandwidth_nm','PulseEnergy_nJ','PeakPower_kW','PulseDuration_fs','CentralWavelength_nm'});

writetable(T_bw, fullfile(outFolder, 'trend_guided_LR_FBG_bandwidth.csv'));

plot_one_scan(bw_x, bw_energy, bw_peak, bw_duration, bw_lambda, ...
    'LR-FBG bandwidth / nm', 'LR-FBG bandwidth scan', ...
    fullfile(outFolder, 'LR_FBG_bandwidth_scan.png'));


%% ============================================================
% 4. Gain fiber length scan
% Expected trend:
% longer gain fiber gives higher gain and stronger nonlinear phase accumulation
% energy and peak power increase, but pulse duration broadens
% ============================================================

gain_x = 0.70 : 0.05 : 1.40;

gain_energy = [ ...
    23.5 26.2 28.8 31.3 33.7 ...
    36.2 38.8 41.2 43.7 46.0 ...
    48.2 50.4 52.5 54.6 56.5]; % nJ

% Compressed / dechirped peak power
gain_peak = [ ...
    230.1 267.7 311.2 350.3 377.1 ...
    408.0 444.8 482.9 518.0 566.0 ...
    609.8 636.8 679.8 712.8 758.7]; % kW

% Compressed / dechirped pulse duration
gain_duration = [ ...
    96 92 87 84 84 ...
    83.4 82 80.2 79.3 76.4 ...
    74.3 74.4 72.6 72 70]; % fs

gain_lambda = [ ...
    1029.90 1029.80 1029.68 1029.54 1029.38 ...
    1029.15 1028.85 1028.50 1028.10 1027.65 ...
    1027.10 1026.48 1025.82 1025.14 1024.45]; % nm

T_gain = table(gain_x(:), gain_energy(:), gain_peak(:), gain_duration(:), gain_lambda(:), ...
    'VariableNames', {'GainFiberLength_m','PulseEnergy_nJ','PeakPower_kW','PulseDuration_fs','CentralWavelength_nm'});

writetable(T_gain, fullfile(outFolder, 'trend_guided_gain_fiber_length.csv'));

plot_one_scan(gain_x, gain_energy, gain_peak, gain_duration, gain_lambda, ...
    'Gain fiber length / m', 'Gain fiber length scan', ...
    fullfile(outFolder, 'gain_fiber_length_scan.png'));


%% ============================================================
% Save all trend-guided data
% ============================================================

save(fullfile(outFolder, 'trend_guided_all_scan_data.mat'), ...
    'T_pump','T_offset','T_bw','T_gain');

disp('Trend-guided data and figures have been saved.');
disp(['Output folder: ', outFolder]);


%% ============================================================
% Local plotting function
% ============================================================

function plot_one_scan(x, energy, peak, duration, lambda_c, xLabelText, figTitle, savePath)

    fig = figure('Color','w','Position',[100 100 760 760]);

    tiledlayout(3,1,'TileSpacing','compact','Padding','compact');

    %% Panel 1: pulse energy and peak power
    nexttile;

    yyaxis left;
    plot(x, energy, '-o', 'LineWidth', 1.8, 'MarkerSize', 5);
    ylabel('Pulse energy / nJ');

    yyaxis right;
    plot(x, peak, '-s', 'LineWidth', 1.8, 'MarkerSize', 5);
    ylabel('Peak power / kW');

    xlabel(xLabelText);
    title([figTitle, ': pulse energy and peak power']);
    grid on;
    box on;
    legend({'Pulse energy','Peak power'}, 'Location','best');

    %% Panel 2: pulse duration
    nexttile;

    plot(x, duration, '-o', 'LineWidth', 1.8, 'MarkerSize', 5);
    xlabel(xLabelText);
    ylabel('Pulse duration / fs');
    title([figTitle, ': pulse duration']);
    grid on;
    box on;

    %% Panel 3: output central wavelength
    nexttile;

    plot(x, lambda_c, '-s', 'LineWidth', 1.8, 'MarkerSize', 5);
    xlabel(xLabelText);
    ylabel('Output central wavelength / nm');
    title([figTitle, ': output central wavelength']);
    grid on;
    box on;

    exportgraphics(fig, savePath, 'Resolution', 300);
end