% Mamyshev oscillator with FBGs (linear cavity) + external GMN amplifier + grating compression
% Author: you
% Date: today

close all; clearvars;

addpath('../../');  % your toolbox path

%% ---------------- Quick knobs ----------------
PumpPower_osc = 4;    % W, cavity pump (steady, easier convergence)
PumpPower_amp = 15;   % W, external amplifier pump (can sweep higher later)

% FBG settings (centers & bandwidths in nm; power reflectivities)
FBG.HR.cw = 1030; FBG.HR.bw = 2.5; FBG.HR.R = 0.55;  % high-reflect
FBG.LR.cw = 1036; FBG.LR.bw = 2.5; FBG.LR.R = 0.15;  % low-reflect

% Initial pulse seed (rough, helps start-up)
tfwhm_ps = 1.0;     % ps
total_energy_nJ = 1;

% Output coupler notion: LR-FBG transmission is our physical output, so here OC isn't used
% (kept for compatibility)
OC = 0.9;

%% ---------------- Gain rate-equation info ----------------
gain_rate_eqn.cross_section_filename = 'Liekki Yb_AV_20160530.txt';
gain_rate_eqn.reuse_data = false;
gain_rate_eqn.linear_oscillator_model = 0;     % start simpler
gain_rate_eqn.core_diameter = 10;              % um
gain_rate_eqn.cladding_diameter = 125;         % um
gain_rate_eqn.core_NA = 0.08;
gain_rate_eqn.absorption_wavelength_to_get_N_total = 920; % nm
gain_rate_eqn.absorption_to_get_N_total = 1.7; % dB/m
gain_rate_eqn.pump_wavelength = 976;           % nm
gain_rate_eqn.copump_power = PumpPower_osc;    % W
gain_rate_eqn.counterpump_power = 0;           % W
gain_rate_eqn.midx = 1;
gain_rate_eqn.mode_volume = 1;
gain_rate_eqn.tau = 840e-6;                    % s
gain_rate_eqn.export_N2 = true;
gain_rate_eqn.ignore_ASE = true;               % faster convergence baseline
gain_rate_eqn.max_iterations = 50;
gain_rate_eqn.tol = 1e-5;
gain_rate_eqn.allow_coupling_to_zero_fields = false;
gain_rate_eqn.verbose = true;

%% ---------------- General sim / fibers ----------------
sim.lambda0 = 1040e-9;                         % m; central ref wavelength
sim.f0 = 2.99792458e-4/sim.lambda0;            % THz
sim.gpu_yes = false;

sim8 = sim;                                    % passive fiber template
sim8.progress_bar_name = 'SMF';
sim8.save_period = 0.1;                        % m
[fiber8,sim8] = load_default_GMMNLSE_propagate([],sim8,'single_mode');
fiber8.MFD = 10.5;                             % um (SMF 8.5/10um ~10.5um MFD)

% Gain fiber template (10/125 Yb)
sim_Gain = sim;
sim_Gain.gain_model = 4;                       % rate-eqn gain
sim_Gain.progress_bar_name = 'Gain (10um)';
sim_Gain.save_period = 0.1;
fiber_Gain.MFD = 11.1;                         % um
[fiber_Gain,sim_Gain] = load_default_GMMNLSE_propagate(fiber_Gain,sim_Gain,'single_mode');

%% ---------------- Linear cavity segments (between HR/LR FBGs) ----------------
% According to your setup:
% HR-FBG -- fiber_8a -- fiber_Gain_a -- fiber_8b -- LR-FBG
% Only the three fibers below are inside the cavity.
fiber_8a = fiber8;       fiber_8a.L0 = 1.0;   % m  long passive near HR side
fiber_Gain_a = fiber_Gain; fiber_Gain_a.L0 = 0.9; % m  oscillator gain
fiber_8b = fiber8;       fiber_8b.L0 = 0.1;   % m  short passive near LR side

fiber_cavity = [fiber_8a, fiber_Gain_a, fiber_8b];
sim_cavity   = [sim8,     sim_Gain,     sim8   ];

%% ---------------- Grid / time / frequency ----------------
max_rt = 400;                 % allow enough roundtrips
Nt = 2^17;
time_window_ps = 50;          % ps
dt_ps = time_window_ps/Nt;
f_THz = sim.f0 + (-Nt/2:Nt/2-1)'/(Nt*dt_ps);
t_ps = (-Nt/2:Nt/2-1)*dt_ps;
c = 299792458;                % m/s
lambda_nm = c./(f_THz*1e12)*1e9;

tol_convergence = 1e-3;
force_stop = struct('tol_convergence',1e-4,'tol_fluctuation',5e-4,'min_rt',300);

%% ---------------- Initial field ----------------
prop_output = build_MMgaussian(tfwhm_ps, time_window_ps, total_energy_nJ, 1, Nt);

%% Saved field information
L0 = sum([fiber_cavity.L0]); % total fiber length
save_num = sum(int64([fiber_cavity.L0]./[sim_cavity.save_period] - length(fiber_cavity))); % the total number of fields to save
save_num = double(save_num);
saved_z = zeros(1,save_num); % the propagation distance to save
field = cell(1,max_rt);
pump = cell(1,max_rt); % the pump power to save
splice_z = cumsum([fiber_cavity.L0]); % where the splice points are
output_field = zeros(Nt,1,max_rt); % the output pulse
max_save_per_fiber = 1000;

%% ---------------- Gain params (need repetition rate estimate) ----------------
c = 299792458; % m/s
v = 1/fiber_cavity(1).betas(2)*1e12; % velocity in the fiber

gain_rate_eqn.t_rep = L0/v * 2; % s; the time required to finish a roundtrip (the inverse repetition rate of the pulse)
                                      % This gain model solves the gain of the fiber under the steady-state condition; therefore, the repetition rate must be high compared to the lifetime of the doped ions.
disp(1/gain_rate_eqn.t_rep)
[gain_rate_eqn,cross_sections_pump,cross_sections,overlap_factor,~] = gain_info( sim_Gain,gain_rate_eqn,ifftshift(lambda_nms,1) );
N_total = 9e7; % Overriding the ion doping density from with the value from the data sheet instead of a calculated value from gain_info.m above where N_total is replaced with ~ given in ions/um^3
gain_param = {gain_rate_eqn,cross_sections_pump,cross_sections,overlap_factor,N_total};

%% ---------------- Storage ----------------
func = analyze_sim; % the container of several analyzing functions
%% ---------------- Roundtrip loop (full round trip, no warmup) ----------------
rt_num = 0; pulse_survives = true;
output_energy_nJ = zeros(max_rt,1);
fig_HR = []; fig_LR = [];

while rt_num < max_rt
    rt_num = rt_num + 1;
    t_iteration_start = tic;
    time_delay_ps = 0;
    current_z = 0; zn = 1;

    % ---------------- 去程：8a -> Gain_a -> 8b ----------------
    warning('off')
    prop_output = GMMNLSE_propagate(fiber_8a,     prop_output, sim8,     gain_param);
    time_delay_ps = time_delay_ps + prop_output.t_delay(end);

    prop_output = GMMNLSE_propagate(fiber_Gain_a, prop_output, sim_Gain, gain_param);
    time_delay_ps = time_delay_ps + prop_output.t_delay(end);

    prop_output = GMMNLSE_propagate(fiber_8b,     prop_output, sim8,     gain_param);
    time_delay_ps = time_delay_ps + prop_output.t_delay(end);
    warning('on')

    % 保存沿程（保持你的逻辑）
    [saved_field,saved_z_this_fiber] = func.extract_saved_field(prop_output.fields,max_save_per_fiber,current_z,prop_output.z);
    field{rt_num}(:,:,zn:zn+size(saved_field,3)-1) = saved_field;
    saved_z(zn:zn+size(saved_field,3)-1) = saved_z_this_fiber; current_z = saved_z_this_fiber(end); zn = zn + size(saved_field,3)-1;

    % ---------------- LR-FBG（输出=透射，反馈=反射） ----------------
    if ~isempty(fig_LR) && ishghandle(fig_LR), close(fig_LR); end
    [prop_output, tx_LR, fig_LR] = fbg_with_R(prop_output, sim.f0, FBG.LR.cw, FBG.LR.bw, FBG.LR.R, true);
    output_field(:,:,rt_num) = tx_LR;

    % ---------------- 回程：8b -> Gain_a -> 8a ----------------
    warning('off')
    prop_output = GMMNLSE_propagate(fiber_8b,     prop_output, sim8,     gain_param);
    time_delay_ps = time_delay_ps + prop_output.t_delay(end);

    prop_output = GMMNLSE_propagate(fiber_Gain_a, prop_output, sim_Gain, gain_param);
    time_delay_ps = time_delay_ps + prop_output.t_delay(end);

    prop_output = GMMNLSE_propagate(fiber_8a,     prop_output, sim8,     gain_param);
    time_delay_ps = time_delay_ps + prop_output.t_delay(end);
    warning('on')

    % 保存沿程（保持你的逻辑）
    [saved_field,saved_z_this_fiber] = func.extract_saved_field(prop_output.fields,max_save_per_fiber,current_z,prop_output.z);
    field{rt_num}(:,:,zn:zn+size(saved_field,3)-1) = saved_field;
    saved_z(zn:zn+size(saved_field,3)-1) = saved_z_this_fiber; current_z = saved_z_this_fiber(end); zn = zn + size(saved_field,3)-1;
    saved_z = saved_z(1:zn);

    % ---------------- HR-FBG（只反射回腔） ----------------
    if ~isempty(fig_HR) && ishghandle(fig_HR), close(fig_HR); end
    [prop_output, ~, fig_HR] = fbg_with_R(prop_output, sim.f0, FBG.HR.cw, FBG.HR.bw, FBG.HR.R, true);

    % ---------------- 能量、收敛、打印、t_rep 校正 ----------------
    output_energy_nJ(rt_num) = trapz(abs(output_field(:,:,rt_num)).^2)*prop_output.dt/1e3; % nJ

    % 让 check_convergence 一定返回 fig：plot_flag = true
    if rt_num ~= 1, try close(fig); end, end
    warning('off'); output_field(:,:,rt_num) = pulse_tracker(output_field(:,:,rt_num)); warning('on');
    [converged_yes, force_stop_yes, fig] = check_convergence( ...
        output_energy_nJ, output_field(:,:,rt_num), f_THz, t_ps, tol_convergence, true, force_stop );

    % 本圈耗时与 t_rep 校正
    t_iteration_end = toc(t_iteration_start); tv = datevec(t_iteration_end/3600/24);
    fprintf(': %1u:%02u:%04.1f   E_out=%.3f nJ\n', tv(4), tv(5), tv(6), output_energy_nJ(rt_num));
    gain_param{1}.t_rep = gain_rate_eqn.t_rep + time_delay_ps*1e-12;

    % 特征长度（可留可删）
    [dispersion_length, nonlinear_length] = characteristic_lengths(abs(output_field(:,1,rt_num)).^2, t_ps, sim.f0, fiber_8a.betas(3,:), 1/fiber_8a.SR);
    fprintf('  L_DL=%4f(m)  L_NL=%4f(m)\n', dispersion_length, nonlinear_length);

    % 终止条件
    if converged_yes || force_stop_yes.convergence
        fprintf('The field has converged!\n'); break;
    end
    if output_energy_nJ(rt_num) < 1e-3
        disp('The pulse dies.'); pulse_survives = false; break;
    end
end


%% ---------------- External GMN amplifier + grating pair compression ----------------
if pulse_survives
    % Amplifier segment (10/125 Yb), length ~3 m as a typical GMN choice
    sim_Amp = sim; sim_Amp.gain_model = 4; sim_Amp.save_period = 0.05; sim_Amp.progress_bar_name = 'GMN Amp (10um)';
    fiber_Amp = fiber_Gain; fiber_Amp.L0 = 1.9;  % m

    % Independent gain params for the amplifier
    gain_rate_eqn_amp = gain_rate_eqn;
    gain_rate_eqn_amp.copump_power = PumpPower_amp;  % W
    gain_param_amp = {gain_rate_eqn_amp, cs_pump, cs_sig, overlap_factor, N_total};

    prop_seed = prop_output;                          % reuse container
    prop_seed.fields = output_field(:,:,rt_num);      % LR-FBG transmission as seed

    prop_after_amp = GMMNLSE_propagate(fiber_Amp, prop_seed, sim_Amp, gain_param_amp);

    % Grating pair compression (use your existing analyzer)
    [~,~,~,~] = analyze_field(t_ps, f_THz, prop_after_amp.fields(:,:,end), 'Treacy-t', pi/6, 1e-6, true);

    % Optional: also analyze raw oscillator transmission
    % [~,~,~,~] = analyze_field(t_ps, f_THz, output_field(:,:,rt_num), 'Treacy-t', pi/6, 1e-6, true);
end

%% ---------------- Helper: FBG with reflection ratio ----------------
% Splits field into in-band (accepted) and out-of-band (rejected) via gaussian_spectral_filter,
% then forms:
%   Reflect field (back into cavity)  = sqrt(R) * (in-band)
%   Transmit field (to outside port)  = (out-of-band) + sqrt(1-R) * (in-band)
% Returns:
%   prop_out: structure with fields replaced by the reflected field for continued propagation
%   tx_out:   the transmitted field (last z-slice), to be used as the physical output
function [prop_out, tx_out, fig_] = fbg_with_R(prop_in, sim_f0, cw_nm, bw_nm, R, do_plot)
    [pm, fig_] = gaussian_spectral_filter(prop_in, sim_f0, cw_nm, bw_nm, 4, do_plot);

    % In-band and out-of-band fields along propagation
    E_acc_all = pm.fields;            % accepted (in-band)
    E_rej_all = pm.rejected_fields;   % rejected (out-of-band)

    % Reflect only from in-band; transmit = out-of-band + in-band leakage
    E_reflect_all = E_acc_all * sqrt(R);
    E_tx_last = E_rej_all(:,:,end) + E_acc_all(:,:,end) * sqrt(1 - R);

    % Continue cavity propagation with reflected field
    pm.fields = E_reflect_all;

    % Optional energy sanity check (comment out if too verbose)
    % Pin  = trapz(abs(E_acc_all(:,:,end) + E_rej_all(:,:,end)).^2)*pm.dt;
    % Pref = trapz(abs(E_reflect_all(:,:,end)).^2)*pm.dt;
    % Ptx  = trapz(abs(E_tx_last).^2)*pm.dt;
    % fprintf('FBG energy check: in=%.3g, ref+tx=%.3g\n', Pin, Pref+Ptx);

    prop_out = pm;
    tx_out   = E_tx_last;
end
