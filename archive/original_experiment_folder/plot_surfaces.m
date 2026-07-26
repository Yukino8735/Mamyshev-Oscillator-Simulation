%% plot_surfaces.m
clear; clc;

% 1. 读入扫描结果
load('mamyshev_phase_scan.mat');  
% 现在有：PumpPower_list, cw2_list, 
%         energy_map, fwhm_map, fluct_map, stable_map

% 2. 生成网格（X: cw2, Y: Pump）
[CW2, PP] = meshgrid(cw2_list, PumpPower_list);

%% 可选：做一次插值，让 surface 看起来更平滑（不改原始数据，只用于作图）
do_interp = false;

if do_interp
    % 放大网格密度
    cw2_fine = linspace(min(cw2_list), max(cw2_list), 101);
    PP_fine  = linspace(min(PumpPower_list), max(PumpPower_list), 101);
    [CW2_fine, PP_fine] = meshgrid(cw2_fine, PP_fine);

    energy_Z  = interp2(CW2, PP, energy_map, CW2_fine, PP_fine, 'linear');
    fwhm_Z    = interp2(CW2, PP, fwhm_map*1000, CW2_fine, PP_fine, 'linear'); % ps->fs
    fluct_Z   = interp2(CW2, PP, fluct_map, CW2_fine, PP_fine, 'linear');
    % stable_map 是离散的，不插值，保持原始格点
else
    CW2_fine = CW2; PP_fine = PP;
    energy_Z = energy_map;
    fwhm_Z   = fwhm_map*1000;   % ps -> fs
    fluct_Z  = fluct_map;
end

%% 3. 输出能量的 3D surface
figure;
surf(CW2_fine, PP_fine, energy_Z);
shading interp;      % 颜色/面插值让图更顺滑
xlabel('Filter 2 center wavelength cw_2 (nm)');
ylabel('Pump Power (W)');
zlabel('Output energy (nJ)');
title('Output energy surface');
colorbar;
view(135,30);        % 视角可以自己调

%% 4. 未压缩脉宽 (fs) 的 3D surface
figure;
surf(CW2_fine, PP_fine, fwhm_Z);
shading interp;
xlabel('Filter 2 center wavelength cw_2 (nm)');
ylabel('Pump Power (W)');
zlabel('Pulse FWHM (fs, uncompressed)');
title('Pulse FWHM surface');
colorbar;
view(135,30);

%% 5. 相对能量波动的 3D surface
figure;
surf(CW2_fine, PP_fine, fluct_Z);
shading interp;
xlabel('Filter 2 center wavelength cw_2 (nm)');
ylabel('Pump Power (W)');
zlabel('Relative energy fluctuation');
title('Relative energy fluctuation surface');
colorbar;
view(135,30);

%% 6. 锁模状态的 3D surface（离散）
% 这里不插值，防止把 1/0/-1 弄成奇怪的小数
figure;
surf(CW2, PP, stable_map);
shading flat;    % 离散平面，不插值
xlabel('Filter 2 center wavelength cw_2 (nm)');
ylabel('Pump Power (W)');
zlabel('Mode-locking state');
title('Mode-locking state surface (1=ML, 0=off, -1=unstable)');
colorbar;
caxis([-1 1]);   % 颜色条固定在 [-1,1]
view(135,30);
