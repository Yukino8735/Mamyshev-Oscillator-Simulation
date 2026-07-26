%% scan_linear_FBG_mamyshev.m
% Four single-parameter scans for linear FBG Mamyshev oscillator
%
% Scans:
% 1. Pump power
% 2. FBG offset: keep HR-FBG fixed at 1030 nm, scan LR-FBG center wavelength
% 3. LR-FBG bandwidth: keep HR-FBG bandwidth fixed, scan LR-FBG bandwidth
% 4. Gain fiber length
%
% Requirement:
% Put this file in the same folder as your original linear_FBG_mamyshev.m

clear; clc; close all;

%% ===================== User settings =====================
baseScript = 'linear1.m';

% Baseline parameters
base.PumpPower  = 4.0;      % W
base.HR_lambda  = 1030;     % nm
base.LR_lambda  = 1036;     % nm
base.HR_bw      = 1.5;      % nm
base.LR_bw      = 1.5;      % nm
base.gainL      = 0.9;      % m

% Fine scan ranges
PumpPower_list = 3.0 : 0.25 : 7.0;     % W
offset_list    = 3.0 : 0.5  : 10.0;    % nm
LR_bw_list     = 0.5 : 0.25 : 4.0;     % nm
gainL_list     = 0.5 : 0.05 : 1.4;     % m

% Output folder
resultFolder = 'scan_results_linear_FBG';
if ~exist(resultFolder, 'dir')
    mkdir(resultFolder);
end

%% ===================== Scan 1: Pump power =====================
fprintf('\n==================== Scan 1: Pump power ====================\n');

scan1 = repmat(empty_result_struct(), numel(PumpPower_list), 1);

for ii = 1:numel(PumpPower_list)
    p = base;
    p.PumpPower = PumpPower_list(ii);

    fprintf('\n[Pump scan] %d/%d: PumpPower = %.2f W\n', ...
        ii, numel(PumpPower_list), p.PumpPower);

    scan1(ii) = run_one_case(baseScript, p, resultFolder, ...
        'pump', p.PumpPower);
end

T_pump = result_to_table(scan1);
writetable(T_pump, fullfile(resultFolder, 'scan_pump_power.csv'));
save(fullfile(resultFolder, 'scan_pump_power.mat'), ...
    'scan1', 'T_pump', 'PumpPower_list');

%% ===================== Scan 2: FBG offset =====================
fprintf('\n==================== Scan 2: FBG offset ====================\n');

scan2 = repmat(empty_result_struct(), numel(offset_list), 1);

for ii = 1:numel(offset_list)
    p = base;
    offset = offset_list(ii);

    p.HR_lambda = 1030;             % fixed
    p.LR_lambda = p.HR_lambda + offset;
    p.HR_bw = 1.5;                  % fixed
    p.LR_bw = 1.5;                  % fixed

    fprintf('\n[Offset scan] %d/%d: offset = %.2f nm, LR.lambda_c = %.2f nm\n', ...
        ii, numel(offset_list), offset, p.LR_lambda);

    scan2(ii) = run_one_case(baseScript, p, resultFolder, ...
        'offset', offset);
end

T_offset = result_to_table(scan2);
writetable(T_offset, fullfile(resultFolder, 'scan_FBG_offset.csv'));
save(fullfile(resultFolder, 'scan_FBG_offset.mat'), ...
    'scan2', 'T_offset', 'offset_list');

%% ===================== Scan 3: LR-FBG bandwidth =====================
fprintf('\n==================== Scan 3: LR-FBG bandwidth ====================\n');

scan3 = repmat(empty_result_struct(), numel(LR_bw_list), 1);

for ii = 1:numel(LR_bw_list)
    p = base;

    p.HR_lambda = 1030;             % fixed
    p.LR_lambda = 1036;             % fixed
    p.HR_bw = 1.5;                  % fixed
    p.LR_bw = LR_bw_list(ii);       % scanned

    fprintf('\n[LR bandwidth scan] %d/%d: LR.bw = %.2f nm\n', ...
        ii, numel(LR_bw_list), p.LR_bw);

    scan3(ii) = run_one_case(baseScript, p, resultFolder, ...
        'LRbw', p.LR_bw);
end

T_LRbw = result_to_table(scan3);
writetable(T_LRbw, fullfile(resultFolder, 'scan_LR_FBG_bandwidth.csv'));
save(fullfile(resultFolder, 'scan_LR_FBG_bandwidth.mat'), ...
    'scan3', 'T_LRbw', 'LR_bw_list');

%% ===================== Scan 4: Gain fiber length =====================
fprintf('\n==================== Scan 4: Gain fiber length ====================\n');

scan4 = repmat(empty_result_struct(), numel(gainL_list), 1);

for ii = 1:numel(gainL_list)
    p = base;
    p.gainL = gainL_list(ii);

    fprintf('\n[Gain length scan] %d/%d: gain fiber length = %.2f m\n', ...
        ii, numel(gainL_list), p.gainL);

    scan4(ii) = run_one_case(baseScript, p, resultFolder, ...
        'gainL', p.gainL);
end

T_gainL = result_to_table(scan4);
writetable(T_gainL, fullfile(resultFolder, 'scan_gain_fiber_length.csv'));
save(fullfile(resultFolder, 'scan_gain_fiber_length.mat'), ...
    'scan4', 'T_gainL', 'gainL_list');

%% ===================== Save all results =====================
save(fullfile(resultFolder, 'all_scan_results.mat'), ...
    'scan1', 'scan2', 'scan3', 'scan4', ...
    'T_pump', 'T_offset', 'T_LRbw', 'T_gainL', ...
    'PumpPower_list', 'offset_list', 'LR_bw_list', 'gainL_list', 'base');

fprintf('\nAll scans finished. Results saved in folder: %s\n', resultFolder);

%% ===================== Quick plotting =====================
plot_scan_result(T_pump,   'PumpPower_W',  'Pump power / W',        resultFolder, 'pump_power');
plot_scan_result(T_offset, 'FBG_offset_nm','FBG offset / nm',       resultFolder, 'FBG_offset');
plot_scan_result(T_LRbw,   'LR_bw_nm',     'LR-FBG bandwidth / nm', resultFolder, 'LR_FBG_bandwidth');
plot_scan_result(T_gainL,  'gainL_m',      'Gain fiber length / m', resultFolder, 'gain_fiber_length');

fprintf('\nFigures saved in folder: %s\n', resultFolder);

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%% Local functions
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

function result = empty_result_struct()
    result = struct();

    result.scan_name = "";
    result.scan_value = NaN;

    result.PumpPower_W = NaN;
    result.HR_lambda_nm = NaN;
    result.LR_lambda_nm = NaN;
    result.FBG_offset_nm = NaN;
    result.HR_bw_nm = NaN;
    result.LR_bw_nm = NaN;
    result.gainL_m = NaN;

    result.converged = false;
    result.pulse_survives = false;
    result.rt_num = NaN;

    result.pulse_energy_nJ = NaN;
    result.peak_power_W = NaN;
    result.pulse_duration_ps = NaN;
    result.output_central_wavelength_nm = NaN;

    result.status = "not_run";
    result.error_message = "";
end

function result = run_one_case(baseScript, p, resultFolder, scanName, scanValue)

    result = empty_result_struct();

    result.scan_name = string(scanName);
    result.scan_value = scanValue;

    result.PumpPower_W = p.PumpPower;
    result.HR_lambda_nm = p.HR_lambda;
    result.LR_lambda_nm = p.LR_lambda;
    result.FBG_offset_nm = p.LR_lambda - p.HR_lambda;
    result.HR_bw_nm = p.HR_bw;
    result.LR_bw_nm = p.LR_bw;
    result.gainL_m = p.gainL;

    [scriptFolder, scriptBaseName, ~] = fileparts(which(baseScript));

    if isempty(scriptFolder)
        scriptFolder = pwd;
        originalPath = fullfile(scriptFolder, baseScript);
    else
        originalPath = fullfile(scriptFolder, [scriptBaseName '.m']);
    end

    if ~exist(originalPath, 'file')
        error('Cannot find original script: %s', originalPath);
    end

    rawCode = fileread(originalPath);

    % Remove clearvars from original script, otherwise it may clear variables
    % inside the temporary run.
    rawCode = regexprep(rawCode, 'close all;\s*clearvars;', 'close all;');
    rawCode = regexprep(rawCode, 'clearvars;', '');

    % Replace main parameters
    rawCode = regexprep(rawCode, ...
        'PumpPower\s*=\s*[^;]+;', ...
        sprintf('PumpPower = %.12g;', p.PumpPower));

    rawCode = regexprep(rawCode, ...
        'HR\.lambda_c\s*=\s*[^;]+;', ...
        sprintf('HR.lambda_c = %.12g;', p.HR_lambda));

    rawCode = regexprep(rawCode, ...
        'LR\.lambda_c\s*=\s*[^;]+;', ...
        sprintf('LR.lambda_c = %.12g;', p.LR_lambda));

    rawCode = regexprep(rawCode, ...
        'HR\.bw\s*=\s*[^;]+;', ...
        sprintf('HR.bw = %.12g;', p.HR_bw));

    rawCode = regexprep(rawCode, ...
        'LR\.bw\s*=\s*[^;]+;', ...
        sprintf('LR.bw = %.12g;', p.LR_bw));

    rawCode = regexprep(rawCode, ...
        'fiber_gain\.L0\s*=\s*[^;]+;', ...
        sprintf('fiber_gain.L0 = %.12g;', p.gainL));

    % Name for this case
    safeValue = strrep(sprintf('%.4f', scanValue), '.', 'p');
    caseName = sprintf('%s_%s', scanName, safeValue);

    tempScript = fullfile(scriptFolder, ['temp_run_' caseName '.m']);
    tempResult = fullfile(resultFolder, ['result_' caseName '.mat']);

    % Append metric extraction code at the end of the temporary script
    metricCode = sprintf('\n\n%%%% ===== Auto-added metric extraction =====\n');
    metricCode = [metricCode, sprintf('try\n')];

    metricCode = [metricCode, sprintf('    scan_result = struct();\n')];

    metricCode = [metricCode, sprintf('    scan_result.converged = exist(''converged_yes'', ''var'') && logical(converged_yes);\n')];
    metricCode = [metricCode, sprintf('    scan_result.pulse_survives = exist(''pulse_survives'', ''var'') && logical(pulse_survives);\n')];
    metricCode = [metricCode, sprintf('    scan_result.rt_num = rt_num;\n')];

    metricCode = [metricCode, sprintf('    E_final = squeeze(output_field(:,:,rt_num));\n')];
    metricCode = [metricCode, sprintf('    I_t = abs(E_final).^2;\n')];
    metricCode = [metricCode, sprintf('    if size(I_t,2) > 1\n')];
    metricCode = [metricCode, sprintf('        I_t = sum(I_t,2);\n')];
    metricCode = [metricCode, sprintf('    end\n')];

    metricCode = [metricCode, sprintf('    scan_result.pulse_energy_nJ = output_energy(rt_num);\n')];
    metricCode = [metricCode, sprintf('    scan_result.peak_power_W = max(I_t);\n')];

    % FWHM duration
    metricCode = [metricCode, sprintf('    if max(I_t) > 0\n')];
    metricCode = [metricCode, sprintf('        halfMax = 0.5 * max(I_t);\n')];
    metricCode = [metricCode, sprintf('        idx = find(I_t >= halfMax);\n')];
    metricCode = [metricCode, sprintf('        if numel(idx) >= 2\n')];
    metricCode = [metricCode, sprintf('            scan_result.pulse_duration_ps = t(idx(end)) - t(idx(1));\n')];
    metricCode = [metricCode, sprintf('        else\n')];
    metricCode = [metricCode, sprintf('            scan_result.pulse_duration_ps = NaN;\n')];
    metricCode = [metricCode, sprintf('        end\n')];
    metricCode = [metricCode, sprintf('    else\n')];
    metricCode = [metricCode, sprintf('        scan_result.pulse_duration_ps = NaN;\n')];
    metricCode = [metricCode, sprintf('    end\n')];

    % Spectral centroid wavelength
    metricCode = [metricCode, sprintf('    Ew = fftshift(fft(E_final, [], 1), 1);\n')];
    metricCode = [metricCode, sprintf('    S_w = abs(Ew).^2;\n')];
    metricCode = [metricCode, sprintf('    if size(S_w,2) > 1\n')];
    metricCode = [metricCode, sprintf('        S_w = sum(S_w,2);\n')];
    metricCode = [metricCode, sprintf('    end\n')];

    metricCode = [metricCode, sprintf('    if sum(S_w) > 0\n')];
    metricCode = [metricCode, sprintf('        scan_result.output_central_wavelength_nm = sum(lambda(:).*S_w(:)) / sum(S_w(:));\n')];
    metricCode = [metricCode, sprintf('    else\n')];
    metricCode = [metricCode, sprintf('        scan_result.output_central_wavelength_nm = NaN;\n')];
    metricCode = [metricCode, sprintf('    end\n')];

    metricCode = [metricCode, sprintf('    save(''%s'', ''scan_result'');\n', tempResult)];
    metricCode = [metricCode, sprintf('catch ME_metric\n')];
    metricCode = [metricCode, sprintf('    scan_result = struct();\n')];
    metricCode = [metricCode, sprintf('    scan_result.converged = false;\n')];
    metricCode = [metricCode, sprintf('    scan_result.pulse_survives = false;\n')];
    metricCode = [metricCode, sprintf('    scan_result.rt_num = NaN;\n')];
    metricCode = [metricCode, sprintf('    scan_result.pulse_energy_nJ = NaN;\n')];
    metricCode = [metricCode, sprintf('    scan_result.peak_power_W = NaN;\n')];
    metricCode = [metricCode, sprintf('    scan_result.pulse_duration_ps = NaN;\n')];
    metricCode = [metricCode, sprintf('    scan_result.output_central_wavelength_nm = NaN;\n')];
    metricCode = [metricCode, sprintf('    scan_result.metric_error = ME_metric.message;\n')];
    metricCode = [metricCode, sprintf('    save(''%s'', ''scan_result'');\n', tempResult)];
    metricCode = [metricCode, sprintf('end\n')];

    finalCode = [rawCode, metricCode];

    fid = fopen(tempScript, 'w');
    if fid < 0
        error('Cannot create temporary script: %s', tempScript);
    end
    fwrite(fid, finalCode);
    fclose(fid);

    oldFolder = pwd;

    try
        cd(scriptFolder);
        run(tempScript);

        if exist(tempResult, 'file')
            loaded = load(tempResult, 'scan_result');
            sr = loaded.scan_result;

            result.converged = sr.converged;
            result.pulse_survives = sr.pulse_survives;
            result.rt_num = sr.rt_num;

            result.pulse_energy_nJ = sr.pulse_energy_nJ;
            result.peak_power_W = sr.peak_power_W;
            result.pulse_duration_ps = sr.pulse_duration_ps;
            result.output_central_wavelength_nm = sr.output_central_wavelength_nm;

            result.status = "success";
        else
            result.status = "failed";
            result.error_message = "Temporary result file was not created.";
        end

    catch ME
        result.status = "error";
        result.error_message = string(ME.message);
        fprintf('\nCase failed: %s = %.4f\n', scanName, scanValue);
        fprintf('Error message: %s\n', ME.message);
    end

    cd(oldFolder);

    % Clean temporary script, but keep .mat result files
    if exist(tempScript, 'file')
        delete(tempScript);
    end
end

function T = result_to_table(R)

    n = numel(R);

    scan_name = strings(n,1);
    scan_value = NaN(n,1);

    PumpPower_W = NaN(n,1);
    HR_lambda_nm = NaN(n,1);
    LR_lambda_nm = NaN(n,1);
    FBG_offset_nm = NaN(n,1);
    HR_bw_nm = NaN(n,1);
    LR_bw_nm = NaN(n,1);
    gainL_m = NaN(n,1);

    converged = false(n,1);
    pulse_survives = false(n,1);
    rt_num = NaN(n,1);

    pulse_energy_nJ = NaN(n,1);
    peak_power_W = NaN(n,1);
    pulse_duration_ps = NaN(n,1);
    output_central_wavelength_nm = NaN(n,1);

    status = strings(n,1);
    error_message = strings(n,1);

    for ii = 1:n
        scan_name(ii) = R(ii).scan_name;
        scan_value(ii) = R(ii).scan_value;

        PumpPower_W(ii) = R(ii).PumpPower_W;
        HR_lambda_nm(ii) = R(ii).HR_lambda_nm;
        LR_lambda_nm(ii) = R(ii).LR_lambda_nm;
        FBG_offset_nm(ii) = R(ii).FBG_offset_nm;
        HR_bw_nm(ii) = R(ii).HR_bw_nm;
        LR_bw_nm(ii) = R(ii).LR_bw_nm;
        gainL_m(ii) = R(ii).gainL_m;

        converged(ii) = R(ii).converged;
        pulse_survives(ii) = R(ii).pulse_survives;
        rt_num(ii) = R(ii).rt_num;

        pulse_energy_nJ(ii) = R(ii).pulse_energy_nJ;
        peak_power_W(ii) = R(ii).peak_power_W;
        pulse_duration_ps(ii) = R(ii).pulse_duration_ps;
        output_central_wavelength_nm(ii) = R(ii).output_central_wavelength_nm;

        status(ii) = R(ii).status;
        error_message(ii) = R(ii).error_message;
    end

    T = table(scan_name, scan_value, ...
        PumpPower_W, HR_lambda_nm, LR_lambda_nm, FBG_offset_nm, ...
        HR_bw_nm, LR_bw_nm, gainL_m, ...
        converged, pulse_survives, rt_num, ...
        pulse_energy_nJ, peak_power_W, pulse_duration_ps, ...
        output_central_wavelength_nm, ...
        status, error_message);
end

function plot_scan_result(T, xName, xLabelText, resultFolder, figPrefix)

    if ~ismember(xName, T.Properties.VariableNames)
        warning('Variable %s not found in table. Skip plotting.', xName);
        return;
    end

    x = T.(xName);

    % Only plot successful cases
    valid = strcmp(string(T.status), "success") & ...
            ~isnan(T.pulse_energy_nJ) & ...
            ~isnan(T.peak_power_W) & ...
            ~isnan(T.pulse_duration_ps) & ...
            ~isnan(T.output_central_wavelength_nm);

    if sum(valid) < 2
        warning('Not enough valid points for %s. Skip plotting.', figPrefix);
        return;
    end

    x = x(valid);

    % 1. Pulse energy
    figure;
    plot(x, T.pulse_energy_nJ(valid), '-o', 'LineWidth', 1.4);
    xlabel(xLabelText);
    ylabel('Pulse energy / nJ');
    grid on;
    title('Pulse energy');
    saveas(gcf, fullfile(resultFolder, [figPrefix '_pulse_energy.png']));

    % 2. Peak power
    figure;
    plot(x, T.peak_power_W(valid), '-o', 'LineWidth', 1.4);
    xlabel(xLabelText);
    ylabel('Peak power / W');
    grid on;
    title('Peak power');
    saveas(gcf, fullfile(resultFolder, [figPrefix '_peak_power.png']));

    % 3. Pulse duration
    figure;
    plot(x, T.pulse_duration_ps(valid), '-o', 'LineWidth', 1.4);
    xlabel(xLabelText);
    ylabel('Pulse duration FWHM / ps');
    grid on;
    title('Pulse duration');
    saveas(gcf, fullfile(resultFolder, [figPrefix '_pulse_duration.png']));

    % 4. Output central wavelength
    figure;
    plot(x, T.output_central_wavelength_nm(valid), '-o', 'LineWidth', 1.4);
    xlabel(xLabelText);
    ylabel('Output central wavelength / nm');
    grid on;
    title('Output central wavelength');
    saveas(gcf, fullfile(resultFolder, [figPrefix '_central_wavelength.png']));
end