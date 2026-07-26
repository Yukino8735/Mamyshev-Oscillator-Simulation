% linear_FBG_mamyshev.m
% Linear FBG Mamyshev oscillator:
% HR-FBG -> passive fiber -> gain fiber -> LR-FBG
%                                      <- gain fiber <- passive fiber <-
%
% Output is taken from the transmitted field of the LR-FBG.

close all; clearvars;
addpath('../../../GMMNLSE algorithm/','../../../user_helpers/');

%% Quick-change parameters
PumpPower = 4;            % W
max_rt = 80;              % maximum round trips
Nt = 2^15;                % number of samples
time_window = 50;         % ps
tol_convergence = 2e-3;   % convergence tolerance
tfwhm = 1;                % ps
total_energy = 1;         % nJ

% FBG parameters
HR.lambda_c = 1030;       % nm
HR.bw = 1.5;              % nm  (intensity FWHM)
HR.Rpeak = 0.55;

LR.lambda_c = 1036;       % nm
LR.bw = 1.5;              % nm
LR.Rpeak = 0.15;

% Optional extra lumped losses (power transmission)
eta_splice_passive_gain = 1.00;
eta_splice_gain_passive = 1.00;
eta_other_roundtrip      = 1.00;

%% Gain info
gain_rate_eqn.cross_section_filename = 'Liekki Yb_AV_20160530.txt';
gain_rate_eqn.reuse_data = false;

% Set BOTH names for compatibility across your local versions
gain_rate_eqn.linear_oscillator = true;
gain_rate_eqn.linear_oscillator_model = 1;

gain_rate_eqn.core_diameter = 10;      % um
gain_rate_eqn.cladding_diameter = 125; % um
gain_rate_eqn.core_NA = 0.08;
gain_rate_eqn.absorption_wavelength_to_get_N_total = 920; % nm
gain_rate_eqn.absorption_to_get_N_total = 1.7;            % dB/m
gain_rate_eqn.pump_wavelength = 976;                      % nm
gain_rate_eqn.midx = 1;
gain_rate_eqn.mode_volume = 1;
gain_rate_eqn.tau = 840e-6;          % s
gain_rate_eqn.export_N2 = true;
gain_rate_eqn.ignore_ASE = true;
gain_rate_eqn.max_iterations = 50;
gain_rate_eqn.tol = 1e-5;
gain_rate_eqn.allow_coupling_to_zero_fields = false;
gain_rate_eqn.verbose = true;

%% Setup fiber parameters
sim.lambda0 = 1033e-9; % place center between the two FBGs
sim.f0 = 2.99792458e-4/sim.lambda0; % THz
sim.gpu_yes = false;

% Passive fiber
sim_passive = sim;
sim_passive.progress_bar_name = 'Passive fiber';
sim_passive.save_period = 0.1; % m
[fiber_passive, sim_passive] = load_default_GMMNLSE_propagate([], sim_passive, 'single_mode');
fiber_passive.MFD = 10.5; % um
fiber_passive.L0 = 1.03;  % m

% Gain fiber
sim_gain = sim;
sim_gain.gain_model = 4;
sim_gain.progress_bar_name = 'Gain fiber';
sim_gain.save_period = 0.1; % m
fiber_gain.L0 = 0.92;       % m
fiber_gain.MFD = 11.1;      % um
[fiber_gain, sim_gain] = load_default_GMMNLSE_propagate(fiber_gain, sim_gain, 'single_mode');

%% General cavity parameters
dt = time_window/Nt;
f = sim.f0 + (-Nt/2:Nt/2-1)'/(Nt*dt);   % THz
t = (-Nt/2:Nt/2-1)'*dt;                 % ps
c = 299792458;                          % m/s
lambda = c./(f*1e12)*1e9;               % nm

force_stop = struct('tol_convergence',1e-4, ...
                    'tol_fluctuation',5e-4, ...
                    'min_rt',500);

%% Initial condition
prop_output = build_MMgaussian(tfwhm, time_window, total_energy, 1, Nt);

%% Saved field information
L_rt = 2*(fiber_passive.L0 + fiber_gain.L0); % one full roundtrip length
save_num_est = ...
    floor(fiber_passive.L0/sim_passive.save_period) + ...
    floor(fiber_gain.L0/sim_gain.save_period) + ...
    floor(fiber_gain.L0/sim_gain.save_period) + ...
    floor(fiber_passive.L0/sim_passive.save_period) + 8;

field = cell(1, max_rt);
saved_z_all = cell(1, max_rt);
output_field = zeros(Nt, 1, max_rt);
output_energy = zeros(max_rt, 1);
pulse_survives = true;

splice_z = [fiber_passive.L0, ...
            fiber_passive.L0 + fiber_gain.L0, ...
            fiber_passive.L0 + fiber_gain.L0 + fiber_gain.L0, ...
            L_rt];

%% Load gain parameters
v = 1/fiber_gain.betas(2)*1e12;   % m/s
gain_rate_eqn.t_rep = L_rt / v;   % s

% Forward pass through gain: assume copump from left side
gain_rate_eqn_fwd = gain_rate_eqn;
gain_rate_eqn_fwd.copump_power = PumpPower;
gain_rate_eqn_fwd.counterpump_power = 0;

% Backward pass through gain: same physical pump now appears counter-pumped
gain_rate_eqn_bwd = gain_rate_eqn;
gain_rate_eqn_bwd.copump_power = 0;
gain_rate_eqn_bwd.counterpump_power = PumpPower;

[gain_rate_eqn_fwd, cross_sections_pump_fwd, cross_sections_fwd, overlap_factor_fwd, ~] = ...
    gain_info(sim_gain, gain_rate_eqn_fwd, ifftshift(lambda,1));

[gain_rate_eqn_bwd, cross_sections_pump_bwd, cross_sections_bwd, overlap_factor_bwd, ~] = ...
    gain_info(sim_gain, gain_rate_eqn_bwd, ifftshift(lambda,1));

N_total = 9e7;
gain_param_fwd = {gain_rate_eqn_fwd, cross_sections_pump_fwd, cross_sections_fwd, overlap_factor_fwd, N_total};
gain_param_bwd = {gain_rate_eqn_bwd, cross_sections_pump_bwd, cross_sections_bwd, overlap_factor_bwd, N_total};

%% Run cavity simulation
func = analyze_sim;
rt_num = 0;

while rt_num < max_rt
    rt_num = rt_num + 1;
    t_iteration_start = tic;

    fprintf('\nIteration %d\n', rt_num);

    current_z = 0;
    z_log = zeros(1, save_num_est);
    zn = 1;
    field_this_rt = [];

    time_delay = 0;

    %% ---------------------------------------------------------------
    % 0) HR-FBG reflection: launch the right-going intracavity field
    %% ---------------------------------------------------------------
    prop_output = apply_lumped_loss(prop_output, eta_other_roundtrip);
    [prop_output, ~] = apply_reflective_FBG(prop_output, sim, HR.lambda_c, HR.bw, HR.Rpeak, false);

    %% ---------------------------------------------------------------
    % 1) Forward passive fiber
    %% ---------------------------------------------------------------
    warning('off');
    prop_output = GMMNLSE_propagate(fiber_passive, prop_output, sim_passive);
    warning('on');

    time_delay = time_delay + get_last_tdelay(prop_output);

    [saved_field, saved_z] = extract_current_saved_field(func, prop_output, save_num_est, current_z);
    field_this_rt = cat(3, field_this_rt, saved_field);
    z_log(zn:zn+numel(saved_z)-1) = saved_z;
    zn = zn + numel(saved_z);
    current_z = saved_z(end);

    prop_output = apply_lumped_loss(prop_output, eta_splice_passive_gain);

    %% ---------------------------------------------------------------
    % 2) Forward gain fiber (copump)
    %% ---------------------------------------------------------------
    warning('off');
    prop_output = GMMNLSE_propagate(fiber_gain, prop_output, sim_gain, gain_param_fwd);
    warning('on');

    time_delay = time_delay + get_last_tdelay(prop_output);

    [saved_field, saved_z] = extract_current_saved_field(func, prop_output, save_num_est, current_z);
    field_this_rt = cat(3, field_this_rt, saved_field);
    z_log(zn:zn+numel(saved_z)-1) = saved_z;
    zn = zn + numel(saved_z);
    current_z = saved_z(end);

    %% ---------------------------------------------------------------
    % 3) LR-FBG: split into transmitted output and reflected return field
    %% ---------------------------------------------------------------
    [prop_back, prop_out] = apply_reflective_FBG(prop_output, sim, LR.lambda_c, LR.bw, LR.Rpeak, true);

    output_field(:,:,rt_num) = get_current_field(prop_out);
    output_energy(rt_num) = trapz(abs(output_field(:,:,rt_num)).^2) * dt / 1e3; % nJ

    prop_output = prop_back;
    prop_output = apply_lumped_loss(prop_output, eta_splice_gain_passive);

    %% ---------------------------------------------------------------
    % 4) Backward gain fiber (counterpump)
    %% ---------------------------------------------------------------
    warning('off');
    prop_output = GMMNLSE_propagate(fiber_gain, prop_output, sim_gain, gain_param_bwd);
    warning('on');

    time_delay = time_delay + get_last_tdelay(prop_output);

    [saved_field, saved_z] = extract_current_saved_field(func, prop_output, save_num_est, current_z);
    field_this_rt = cat(3, field_this_rt, saved_field);
    z_log(zn:zn+numel(saved_z)-1) = saved_z;
    zn = zn + numel(saved_z);
    current_z = saved_z(end);

    %% ---------------------------------------------------------------
    % 5) Backward passive fiber
    %% ---------------------------------------------------------------
    warning('off');
    prop_output = GMMNLSE_propagate(fiber_passive, prop_output, sim_passive);
    warning('on');

    time_delay = time_delay + get_last_tdelay(prop_output);

    [saved_field, saved_z] = extract_current_saved_field(func, prop_output, save_num_est, current_z);
    field_this_rt = cat(3, field_this_rt, saved_field);
    z_log(zn:zn+numel(saved_z)-1) = saved_z;
    zn = zn + numel(saved_z);
    current_z = saved_z(end);

    % keep only actually used z values
    z_log = z_log(1:zn-1);

    field{rt_num} = field_this_rt;
    saved_z_all{rt_num} = z_log;

    %% ---------------------------------------------------------------
    % Convergence check
    %% ---------------------------------------------------------------
    if rt_num ~= 1 && exist('fig_conv','var') && ishghandle(fig_conv)
        close(fig_conv);
    end

    warning('off');
    output_field(:,:,rt_num) = pulse_tracker(output_field(:,:,rt_num));
    warning('on');

    [converged_yes, force_stop_yes, fig_conv] = ...
        check_convergence(output_energy, output_field(:,:,rt_num), f, t, tol_convergence, true, force_stop);

    %% ---------------------------------------------------------------
    % Update repetition rate
    %% ---------------------------------------------------------------
    gain_param_fwd{1}.t_rep = gain_rate_eqn.t_rep + time_delay*1e-12;
    gain_param_bwd{1}.t_rep = gain_rate_eqn.t_rep + time_delay*1e-12;

    %% ---------------------------------------------------------------
    % Diagnostics
    %% ---------------------------------------------------------------
    t_iteration_end = toc(t_iteration_start);
    t_iteration_spent = datevec(t_iteration_end/3600/24);
    fprintf('  Output energy = %.4f nJ\n', output_energy(rt_num));
    fprintf('  Iteration time = %1u:%2u:%3.1f\n', ...
        t_iteration_spent(4), t_iteration_spent(5), t_iteration_spent(6));

    try
        [dispersion_length, nonlinear_length] = ...
            characteristic_lengths(abs(output_field(:,1,rt_num)).^2, t, sim.f0, ...
                                   fiber_passive.betas(3,:), 1/fiber_passive.SR);
        fprintf('  L_DL = %4f m\n', dispersion_length);
        fprintf('  L_NL = %4f m\n', nonlinear_length);
    catch
        % skip if characteristic_lengths expects slightly different format
    end

    if rt_num ~= 1 && exist('fig_evolution','var') && ishghandle(fig_evolution)
        close(fig_evolution);
    end
    try
        fig_evolution = func.analyze_fields_within_cavity(t, f, field{rt_num}, z_log, splice_z);
    catch
        try
            fig_evolution = func.analyze_fields(t, f, field{rt_num}, z_log, splice_z);
        catch
            % ignore plotting failure
        end
    end

    %% ---------------------------------------------------------------
    % Stop conditions
    %% ---------------------------------------------------------------
    if converged_yes || force_stop_yes.convergence
        fprintf('The field has converged!\n');
        break;
    end

    if output_energy(rt_num) < 0.01
        fprintf('The pulse dies.\n');
        pulse_survives = false;
        break;
    end
end

%% Optional output pigtail for passive broadening / spectrum filling
fiber_out = fiber_passive;
fiber_out.L0 = 0.2;

prop_output_out = prop_out; % use transmitted output from LR-FBG
prop_output_out.fields = get_current_field(prop_out);

try
    [~,~,~,~] = analyze_field(t, f, output_field(:,:,rt_num), 'Treacy-t', pi/6, 1e-6, true);
catch
end

prop_output_out = GMMNLSE_propagate(fiber_out, prop_output_out, sim_passive);

%% Optional final analysis
try
    [~,~,~,~] = analyze_field(t, f, get_current_field(prop_output_out), 'Treacy-t', pi/6, 1e-6, true);
catch
end

%% Trim saved arrays
field = field(1:rt_num);
saved_z_all = saved_z_all(1:rt_num);
output_field = output_field(:,:,1:rt_num);
energy = output_energy(arrayfun(@any, output_energy));

%% Optional save
% if pulse_survives
%     save('linear_FBG_mamyshev.mat', ...
%         't','f','lambda','output_field','energy', ...
%         'field','saved_z_all','splice_z', ...
%         'fiber_passive','fiber_gain','sim_passive','sim_gain', ...
%         'gain_param_fwd','gain_param_bwd', ...
%         'HR','LR','-v7.3');
% end

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%% Local helper functions
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

function prop_output = apply_lumped_loss(prop_output, eta_power)
    if eta_power >= 0 && eta_power <= 1
        E = get_current_field(prop_output);
        E = sqrt(eta_power) * E;
        prop_output = set_current_field(prop_output, E);
    else
        error('eta_power must be between 0 and 1.');
    end
end

function [prop_refl, prop_tran] = apply_reflective_FBG(prop_input, sim, lambda_c_nm, bw_nm, Rpeak, plot_yes)
    % Intensity reflectivity:
    % R(lambda) = Rpeak * exp[-4 ln2 ((lambda-lambda_c)/bw)^2]
    %
    % amplitude reflectivity/transmissivity:
    % r = sqrt(R), t = sqrt(1-R)

    E = get_current_field(prop_input);
    Nt = size(E,1);

    dt = prop_input.dt;
    f = sim.f0 + (-Nt/2:Nt/2-1)'/(Nt*dt); % THz
    c = 299792458;
    lambda = c./(f*1e12)*1e9;             % nm

    R = Rpeak * exp(-4*log(2)*((lambda - lambda_c_nm)/bw_nm).^2);
    R = min(max(R, 0), 1);
    T = max(0, 1 - R);

    r = sqrt(R);
    t = sqrt(T);

    Ew = fftshift(fft(E, [], 1), 1);

    if size(Ew,2) > 1
        r = repmat(r, 1, size(Ew,2));
        t = repmat(t, 1, size(Ew,2));
    end

    Ew_refl = Ew .* r;
    Ew_tran = Ew .* t;

    E_refl = ifft(ifftshift(Ew_refl, 1), [], 1);
    E_tran = ifft(ifftshift(Ew_tran, 1), [], 1);

    prop_refl = prop_input;
    prop_tran = prop_input;

    prop_refl = set_current_field(prop_refl, E_refl);
    prop_tran = set_current_field(prop_tran, E_tran);

    if plot_yes
        figure;
        yyaxis left;
        plot(lambda, R, 'LineWidth', 1.2);
        ylabel('Reflectivity');
        yyaxis right;
        plot(lambda, abs(Ew).^2/max(abs(Ew(:)).^2 + eps), '--', 'LineWidth', 1.0);
        ylabel('Normalized spectrum');
        xlabel('\lambda (nm)');
        title(sprintf('Reflective FBG: \\lambda_c = %.2f nm, BW = %.2f nm, R_{peak}=%.2f', ...
            lambda_c_nm, bw_nm, Rpeak));
        grid on;
    end
end

function E = get_current_field(prop_output)
    % Robust extraction of the current field from prop_output.fields
    if isfield(prop_output, 'fields')
        F = prop_output.fields;

        if isstruct(F)
            if isfield(F, 'forward')
                F = F.forward;
            else
                error('prop_output.fields is a struct, but no .forward field was found.');
            end
        end

        if ndims(F) == 3
            E = F(:,:,end);
        else
            E = F;
        end
    else
        error('prop_output has no .fields member.');
    end
end

function prop_output = set_current_field(prop_output, E)
    % Replace current field while keeping prop_output structure
    prop_output.fields = E;
end

function td = get_last_tdelay(prop_output)
    if isfield(prop_output, 't_delay')
        if numel(prop_output.t_delay) >= 1
            td = prop_output.t_delay(end);
        else
            td = 0;
        end
    else
        td = 0;
    end
end

function [saved_field, saved_z] = extract_current_saved_field(func, prop_output, max_save_per_fiber, current_z)
    F = prop_output.fields;
    if isstruct(F)
        if isfield(F, 'forward')
            F = F.forward;
        else
            error('prop_output.fields is a struct, but no .forward field was found.');
        end
    end

    if ndims(F) == 3
        [saved_field, saved_z] = func.extract_saved_field(F, max_save_per_fiber, current_z, prop_output.z);
    else
        saved_field = F;
        if isfield(prop_output, 'z') && ~isempty(prop_output.z)
            saved_z = current_z + prop_output.z(end);
        else
            saved_z = current_z;
        end
    end
end