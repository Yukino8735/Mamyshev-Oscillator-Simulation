% 扫描 Mamyshev 稳态图：PumpPower vs cw2

clear; clc;

script_dir = fileparts(mfilename('fullpath'));
code_dir = fileparts(fileparts(script_dir));
addpath(code_dir);
[project_root, ~] = setup_mamyshev_project();
result_dir = fullfile(project_root, 'data', 'ring_cavity', 'generated');
if ~isfolder(result_dir)
    mkdir(result_dir);
end

% 扫描参数
PumpPower_list = 3:0.5:7;        % 根据需要改
cw2_list       = 1028:2:1036;    % 对应相对 1040 nm 的 12-4 nm 间隔

nP = numel(PumpPower_list);
nC = numel(cw2_list);

stable_map   = zeros(nP, nC);    % 1 = 锁模成功, 0 = 无锁模, -1 = 不稳定
energy_map   = zeros(nP, nC);    % 最终输出能量 (nJ)
fwhm_map     = zeros(nP, nC);    % 最终时域 FWHM (ps)
dechirped_fwhm_map_fs = nan(nP, nC); % 尾纤后光栅压缩 FWHM (fs)
transform_limited_fwhm_map_fs = nan(nP, nC); % 变换极限 FWHM (fs)
dechirped_peak_power_map_MW = nan(nP, nC); % 压缩峰值功率 (MW)
fluct_map    = zeros(nP, nC);    % 相对能量波动
converged_map = false(nP, nC);   % 数值收敛标记

for ip = 1:nP
    for ic = 1:nC
        PumpPower = PumpPower_list(ip);
        cw2       = cw2_list(ic);

        fprintf('Running Pump = %.2f W, cw2 = %.1f nm...\n', PumpPower, cw2);

        % 第三个参数 false：关闭绘图，用于扫描
        res = run_mamyshev(PumpPower, cw2, false);

        energy_map(ip, ic) = res.output_energy;
        fwhm_map(ip, ic)   = res.fwhm_ps;
        dechirped_fwhm_map_fs(ip, ic) = res.dechirped_fwhm_fs;
        transform_limited_fwhm_map_fs(ip, ic) = ...
            res.transform_limited_fwhm_fs;
        dechirped_peak_power_map_MW(ip, ic) = ...
            res.dechirped_peak_power_W / 1e6;
        fluct_map(ip, ic)  = res.energy_rel_fluct;
        converged_map(ip, ic) = res.converged;

        % 使用物理锁模状态
        stable_map(ip, ic) = res.ML_state;
    end
end

save(fullfile(result_dir, 'mamyshev_phase_scan.mat'), ...
     'PumpPower_list', 'cw2_list', ...
     'stable_map', 'energy_map', 'fwhm_map', ...
     'dechirped_fwhm_map_fs', 'transform_limited_fwhm_map_fs', ...
     'dechirped_peak_power_map_MW', ...
     'fluct_map', 'converged_map');

%% 作图

% 1) 稳态类型图
figure;
imagesc(cw2_list, PumpPower_list, stable_map);
set(gca,'YDir','normal');
xlabel('Filter 2 center wavelength cw2 (nm)');
ylabel('Pump Power (W)');
title('Mode-locking state map: 1=ML, 0=off, -1=unstable');
colorbar;

% 2) 输出能量图
figure;
imagesc(cw2_list, PumpPower_list, energy_map);
set(gca,'YDir','normal');
xlabel('Filter 2 center wavelength cw2 (nm)');
ylabel('Pump Power (W)');
title('Output energy (nJ)');
colorbar;

% 3) FWHM 图（fs）
figure;
imagesc(cw2_list, PumpPower_list, fwhm_map * 1000); % ps → fs
set(gca,'YDir','normal');
xlabel('Filter 2 center wavelength cw2 (nm)');
ylabel('Pump Power (W)');
title('Pulse FWHM (fs, uncompressed)');
colorbar;

% 4) 压缩后脉宽图（fs）
figure;
imagesc(cw2_list, PumpPower_list, dechirped_fwhm_map_fs);
set(gca,'YDir','normal');
xlabel('Filter 2 center wavelength cw2 (nm)');
ylabel('Pump Power (W)');
title('Dechirped pulse FWHM (fs)');
colorbar;

% 5) 压缩后峰值功率图（MW）
figure;
imagesc(cw2_list, PumpPower_list, dechirped_peak_power_map_MW);
set(gca,'YDir','normal');
xlabel('Filter 2 center wavelength cw2 (nm)');
ylabel('Pump Power (W)');
title('Dechirped peak power (MW)');
colorbar;

% 6) 可选：能量相对波动图
figure;
imagesc(cw2_list, PumpPower_list, fluct_map);
set(gca,'YDir','normal');
xlabel('Filter 2 center wavelength cw2 (nm)');
ylabel('Pump Power (W)');
title('Relative energy fluctuation');
colorbar;
