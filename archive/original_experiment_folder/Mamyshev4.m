% new_mamyshev_sim.m
% 线性腔 HR/LR-FBG + GMN amplifier 的"新 Mamyshev"仿真
% 参考: Haig 2021 全光纤自启动 MO；Boulanger 2023 单泵 MOGMA
% 作者：按你工程接口改写，自含关键注释

close all; clearvars;
addpath('../../');

%% 1) 快速配置
Pump_total = 15;        % W，总泵功率（单二极管）。按需修改
Pump_osc   = 6;         % W，分给腔内增益段（LY），自启动更稳
Pump_amp   = Pump_total - Pump_osc;  % W，分给腔后 GMN 放大段（LA）

% 中心波长与频域网格
sim.lambda0 = 1040e-9;             % m
sim.f0 = 2.99792458e-4/sim.lambda0; % THz
sim.gpu_yes = false;

% 采样窗口
max_rt = 200;           % 允许的最大往返数
Nt = 2^17;              % 频域点数
time_window = 50;       % ps
dt = time_window/Nt;
f = sim.f0 + (-Nt/2:Nt/2-1)'/(Nt*dt); % THz
t = (-Nt/2:Nt/2-1)*dt;                 % ps
c = 299792458;
lambda = c./(f*1e12)*1e9;              % nm

tol_convergence = 1e-3;
force_stop = struct('tol_convergence',1e-4,'tol_fluctuation',5e-4,'min_rt',200);

%% 2) 纤芯与材料：被动 SMF 与 Yb 增益光纤
% 被动 8.5/125 SMF (10.5 μm MFD)
sim8 = sim; sim8.progress_bar_name = 'SMF (8.5um)'; sim8.save_period = 0.1;
[fiber8,sim8] = load_default_GMMNLSE_propagate([],sim8,'single_mode');
fiber8.MFD = 10.5;

% 腔内增益段：LY 短（把泵留给放大器）
simGain_osc = sim; simGain_osc.gain_model = 4;
simGain_osc.progress_bar_name = 'Oscillator Gain (10um)';
simGain_osc.save_period = 0.1;
fiberGain_osc.L0  = 0.6;     % m，建议 0.5~1.0，取 0.6 m
fiberGain_osc.MFD = 11.1;
[fiberGain_osc,simGain_osc] = load_default_GMMNLSE_propagate(fiberGain_osc,simGain_osc,'single_mode');

% 腔后 GMN 放大段：LA 长（进入 GMN 演化、利于压缩）
simGain_amp = sim; simGain_amp.gain_model = 4;
simGain_amp.progress_bar_name = 'GMN Amplifier (10um)';
simGain_amp.save_period = 0.1;
fiberGain_amp.L0  = 3.0;     % m，按 Boulanger 2023 的量级
fiberGain_amp.MFD = 11.1;
[fiberGain_amp,simGain_amp] = load_default_GMMNLSE_propagate(fiberGain_amp,simGain_amp,'single_mode');

% 腔内三段 SMF：HR 侧稍长定重复率；gain 后短段以便滤波；LR 后到 gain 的返回段
fiber_8_HR = fiber8; fiber_8_HR.L0 = 1.55; % m，设定 ~50 MHz 重复率
fiber_8a   = fiber8; fiber_8a.L0   = 0.20; % m，增益段后到 FBG1 的短段
fiber_8_LR = fiber8; fiber_8_LR.L0 = 1.50; % m，第二个滤波器到增益前回程

%% 3) FBG 滤波器参数（等效为高斯反射谱）
% HR-FBG：中心 1030 nm，带宽 2.5 nm，近全反
FBG1.cw = 1030;  % nm
FBG1.bw = 2.5;   % nm
FBG1.R  = 0.99;  % 反射率近似
% LR-FBG：中心 1036 nm，带宽 2.5 nm，低反（腔耦合更弱，利于压缩）
FBG2.cw = 1036;  % nm
FBG2.bw = 2.5;   % nm
FBG2.R  = 0.10;  % 低反；按需 5%~20% 微调

% 说明：
% 在实现上继续使用 gaussian_spectral_filter，把"通过"视为保留在当前传播方向的份额，
% "rejected_fields"视为被滤除的一侧。我们约定：
%   FBG1（增益后）：用其 rejected_fields 作为输出耦合端口（等效滤波器的拒绝端口为输出）
%   FBG2（回程）：只做腔内滤波，不取输出

%% 4) 速率方程增益模型参数（腔内与放大段各一份）
base_gain = [];
base_gain.cross_section_filename = 'Liekki Yb_AV_20160530.txt';
base_gain.reuse_data = false;
base_gain.linear_oscillator_model = 0; % 仍用单向等效模型
base_gain.core_diameter = 10;
base_gain.cladding_diameter = 125;
base_gain.core_NA = 0.08;
base_gain.absorption_wavelength_to_get_N_total = 920;
base_gain.absorption_to_get_N_total = 1.7; % dB/m
base_gain.pump_wavelength = 976;
base_gain.midx = 1;
base_gain.mode_volume = 1;
base_gain.tau = 840e-6;
base_gain.export_N2 = true;
base_gain.ignore_ASE = true;
base_gain.max_iterations = 50;
base_gain.tol = 1e-5;
base_gain.allow_coupling_to_zero_fields = false;
base_gain.verbose = true;

% 腔长与往返时间
L_cav = fiberGain_osc.L0 + fiber_8a.L0 + fiber_8_LR.L0 + fiber_8_HR.L0;
vgrp  = 1/fiber_8_HR.betas(2)*1e12;  % 近似
base_gain.t_rep = L_cav/vgrp;

% 计算微分截面与掺杂密度
[gain_osc,csp_osc,cs_osc,overlap_osc,~] = gain_info(simGain_osc,base_gain,ifftshift(lambda,1));
[gain_amp,csp_amp,cs_amp,overlap_amp,~] = gain_info(simGain_amp,base_gain,ifftshift(lambda,1));
N_total = 9e7; % ions/um^3

% 分配泵功率
gain_osc.copump_power = Pump_osc; gain_osc.counterpump_power = 0;
gain_amp.copump_power = Pump_amp; gain_amp.counterpump_power = 0;

gain_param_osc = {gain_osc,csp_osc,cs_osc,overlap_osc,N_total};
gain_param_amp = {gain_amp,csp_amp,cs_amp,overlap_amp,N_total};

%% 5) 腔体序列与初始场
fiber_cavity = [fiber_8_HR, fiberGain_osc, fiber_8a, fiber_8_LR];  % 等效线性腔
sim_cavity   = [sim8,       simGain_osc,  sim8,     sim8      ];

tfwhm0 = 1;     % ps
E0     = 1;     % nJ 初始能量
prop = build_MMgaussian(tfwhm0, time_window, E0, 1, Nt);

% 保存输出
output_field = zeros(Nt,1,max_rt);
output_energy = zeros(max_rt,1);

%% 6) 往返循环
rt = 0; converged = false;
while rt < max_rt
    rt = rt+1;
    % 段 1：HR 侧被动段
    prop = GMMNLSE_propagate(fiber_cavity(1), prop, sim_cavity(1));
    % 段 2：增益段（短 LY）
    prop = GMMNLSE_propagate(fiber_cavity(2), prop, sim_cavity(2), gain_param_osc);
    % 段 3：到 FBG1 的短 SMF
    prop = GMMNLSE_propagate(fiber_cavity(3), prop, sim_cavity(3));

    % FBG1（等效 HR-FBG 在 1030 nm）：取 reject 作为输出端口
    [prop, fig_fbg1] = gaussian_spectral_filter(prop, sim.f0, FBG1.cw, FBG1.bw, 4, true);
    output_field(:,:,rt) = prop.rejected_fields(:,:,end);  % 输出

    % 段 4：回程到 FBG2 的 SMF
    prop = GMMNLSE_propagate(fiber_cavity(4), prop, sim_cavity(4));

    % FBG2（等效 LR-FBG 在 1036 nm）：只做腔内滤波，不取输出
    [prop, fig_fbg2] = gaussian_spectral_filter(prop, sim.f0, FBG2.cw, FBG2.bw, 4, true);

    % 轨迹校正与收敛性检查
    output_field(:,:,rt) = pulse_tracker(output_field(:,:,rt));
    output_energy(rt) = trapz(abs(output_field(:,:,rt)).^2)*prop.dt/1e3;

    [conv_yes, force_stop_yes, ~] = check_convergence(output_energy, output_field(:,:,rt), f, t, tol_convergence, false, force_stop);
    if conv_yes || force_stop_yes.convergence
        converged = true; break;
    end
    if output_energy(rt) < 0.01
        warning('Pulse died'); break;
    end
end

if ~converged
    fprintf('未达到严格收敛，使用最后一趟的输出进入放大器\n');
end
E_out = trapz(abs(output_field(:,:,rt)).^2)*prop.dt/1e3;
fprintf('腔输出能量约 %.2f nJ\n', E_out);

%% 7) 腔后 GMN amplifier
seed = prop;                       % 保留当前 prop 的时间轴等元数据
seed.fields = output_field(:,:,rt);% 以腔输出为种子
amp_out = GMMNLSE_propagate(fiberGain_amp, seed, simGain_amp, gain_param_amp);

% 可选：接一小段短 SMF 去掉残余结构
tail = fiber8; tail.L0 = 0.2;
amp_out = GMMNLSE_propagate(tail, amp_out, sim8);

%% 8) 压缩与分析
[~,~,~,~] = analyze_field(t, f, amp_out.fields(:,:,end), 'Treacy-t', pi/6, 1e-6, true);

% 保存必要变量
% save('new_mamyshev_result.mat','t','f','lambda','output_field','output_energy','amp_out');

