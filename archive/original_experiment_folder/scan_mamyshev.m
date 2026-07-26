% 扫描 Mamyshev 稳态图：PumpPower vs cw2

clear; clc;

% 扫描参数
PumpPower_list = 3:0.5:7;        % 根据需要改
cw2_list       = 1026:2:1036;    % 滤波器2中心波长扫描

nP = numel(PumpPower_list);
nC = numel(cw2_list);

stable_map   = zeros(nP, nC);    % 1 = 锁模成功, 0 = 无锁模, -1 = 不稳定
energy_map   = zeros(nP, nC);    % 最终输出能量 (nJ)
fwhm_map     = zeros(nP, nC);    % 最终时域 FWHM (ps)
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
        fluct_map(ip, ic)  = res.energy_rel_fluct;
        converged_map(ip, ic) = res.converged;

        % 使用物理锁模状态
        stable_map(ip, ic) = res.ML_state;
    end
end

save('mamyshev_phase_scan.mat', 'PumpPower_list', 'cw2_list', ...
     'stable_map', 'energy_map', 'fwhm_map', ...
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

% 4) 可选：能量相对波动图
figure;
imagesc(cw2_list, PumpPower_list, fluct_map);
set(gca,'YDir','normal');
xlabel('Filter 2 center wavelength cw2 (nm)');
ylabel('Pump Power (W)');
title('Relative energy fluctuation');
colorbar;
