% This code finds the mode-locked state of a Mamyshev Oscillator

% A Mamyshev laser typically contains a sequence of small core passive fibers with spectral filters, 
% an isolator, short gain fiber (GMN regime), following by an output
% coupler, and an initial spectral filter.
%
% This file uses the rate-equation gain model for the gain fiber.

close all; clearvars;

addpath(genpath(fileparts(mfilename('fullpath'))));
    
%% Quick Change variables
PumpPower = 4; %(W)

%wa = 5.55; % (um) the radius of the MFD of 10um fiber
%wb = 5.25; % (um) the radius of the MFD of the 8.5um fiber
%eta = 4*(wa^2*wb^2)/(wa^2+wb^2)^2; %Estimated loss factor for large to small fiber core


%% Gain info
gain_rate_eqn.cross_section_filename = 'Liekki Yb_AV_20160530.txt'; % specify the folder with the eigenmode profiles
gain_rate_eqn.reuse_data = false; % For a ring or linear cavity, the pulse will enter a steady state eventually.
                                  % If reusing the pump and ASE data from the previous roundtrip, the convergence can be much faster, especially for counterpumping.
gain_rate_eqn.linear_oscillator_model = 0; % For a linear oscillator, there are pulses from both directions simultaneously, which will deplete the gain;
                                           % therefore , the backward-propagating pulses need to be taken into account.
gain_rate_eqn.core_diameter = 10; % um
gain_rate_eqn.cladding_diameter = 125; % um
gain_rate_eqn.core_NA = 0.08;
gain_rate_eqn.absorption_wavelength_to_get_N_total = 920; % nm
gain_rate_eqn.absorption_to_get_N_total = 1.7; % dB/m
gain_rate_eqn.pump_wavelength = 976; % nm
gain_rate_eqn.copump_power = PumpPower; % W
gain_rate_eqn.counterpump_power = 0; % W
gain_rate_eqn.midx = 1; % the mode index
gain_rate_eqn.mode_volume = 1; % the total number of available spatial modes in the fiber
gain_rate_eqn.tau = 840e-6; % lifetime of Yb in F_(5/2) state (Paschotta et al., "Lifetme quenching in Yb-doped fibers"); in "s"
gain_rate_eqn.export_N2 = true; % whether to export N2, the ion density in the upper state or not
gain_rate_eqn.ignore_ASE = true;
gain_rate_eqn.max_iterations = 50; % For counterpumping or considering ASE, iterations are required.
gain_rate_eqn.tol = 1e-5; % the tolerance for the iteration
gain_rate_eqn.allow_coupling_to_zero_fields = false; % set this to false all the time for now
gain_rate_eqn.verbose = true; % show the information(final pulse energy) during iterations of computing the gain

%% Setup fiber parameters
% General parameters
sim.lambda0 = 1060e-9; % m; center wavelength
sim.f0 = 2.99792458e-4/sim.lambda0; % THz; center frequency
sim.gpu_yes = false; % 
sim8 = sim; % for the passive fibers
sim8.progress_bar_name = 'SMF (8.5um)';
sim8.save_period = 0.01; % m
[fiber8,sim8] = load_default_GMMNLSE_propagate([],sim8,'single_mode'); % for the passive fibers
fiber8.MFD = 10.5; % (um)

% Gain fiber
sim_Gain = sim;
sim_Gain.gain_model = 4; % use the rate-eqn-gain model
sim_Gain.progress_bar_name = 'Gain (10um)';
sim_Gain.save_period = 0.01; % m
fiber_Gain.MFD = 11.1; % (um)
[fiber_Gain,sim_Gain] = load_default_GMMNLSE_propagate(fiber_Gain,sim_Gain,'single_mode'); % for the gain fibers


% Oscillator SMF 
fiber_8a = fiber8;
fiber_8a.L0 = 1.03; %(m)

% Oscillator Gain fiber_a
fiber_Gain_a = fiber_Gain;
fiber_Gain_a.L0 = 0.92; %(m)

% Short SMF (Gain fiber_a to LR-FBG)
fiber_8b = fiber8;
fiber_8b.L0 = 0.02; %(m)

% Short SMF (Gain LR-FBG to Gain fiber_b )
fiber_8c = fiber8;
fiber_8c.L0 = 0.02; %(m)

% Amplifier SMF 
fiber_Gain_b = fiber_Gain;
fiber_Gain_b.L0 = 1.85; %(m)

%Putting fibers together
fiber_cavity = [fiber_8a fiber_Gain_a fiber_8b];
sim_cavity = [sim8 sim_Gain sim8];

%% Setup general cavity parameters
max_rt = 50; % maximum roundtrips (in case it doesn't converge)
Nt = 2^17; % the number of points
time_window = 50; % ps
dt = time_window/Nt;
f = sim.f0+(-Nt/2:Nt/2-1)'/(Nt*dt); % THz
t = (-Nt/2:Nt/2-1)*dt; % ps
c = 299792458; % m/s
lambda = c./(f*1e12)*1e9; % nm
tol_convergence = 1e-3; % the tolerance of the convergence of the output pulse
force_stop = struct('tol_convergence',1e-4,'tol_fluctuation',5e-4,'min_rt',500); % Stop the code earlier before reaching max_rt if it's too fluctuating or almost converged.
                                                                                 % Start checking the convergence after min_rt.

%% FBG parameters

%% Setup initial conditions
tfwhm = 0.7; % ps
total_energy = 0.7; % nJ

prop_output = build_MMgaussian(tfwhm, time_window, total_energy,1,Nt);
OC = 0.9; % Output coupling ratio

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

%% Load gain parameters
c = 299792458; % m/s
v = 1/fiber_cavity(1).betas(2)*1e12; % velocity in the fiber

gain_rate_eqn.t_rep = 2*L0/v; % s; the time required to finish a roundtrip (the inverse repetition rate of the pulse)
                                      % This gain model solves the gain of the fiber under the steady-state condition; therefore, the repetition rate must be high compared to the lifetime of the doped ions.
disp(1/gain_rate_eqn.t_rep)
[gain_rate_eqn,cross_sections_pump,cross_sections,overlap_factor,~] = gain_info( sim_Gain,gain_rate_eqn,ifftshift(lambda,1) );
N_total = 9e7; % Overriding the ion doping density from with the value from the data sheet instead of a calculated value from gain_info.m above where N_total is replaced with ~ given in ions/um^3
gain_param = {gain_rate_eqn,cross_sections_pump,cross_sections,overlap_factor,N_total};

%% Run the cavity simulation

func = analyze_sim; % the container of several analyzing functions

% Initialize some parameters
output_energy = zeros(max_rt,1);
rt_num = 0;
pulse_survives = true;
% Set reflection
R_HR = 0.55; 
R_LR = 0.15; 
while rt_num < max_rt
    time_delay = 0;
    current_z = 0;
    zn = 1;
    rt_num = rt_num + 1;
    
    t_iteration_start = tic;
    cprintf('*[1 0.5 0.31]','Iteration %d', rt_num);
    % -----------------------------------------------------------------
    for j = 1:3
        warning('off')
        prop_output = GMMNLSE_propagate(fiber_cavity(j), prop_output, sim_cavity(j),gain_param);
        warning('on')

        time_delay = time_delay + prop_output.t_delay(end);
            
        % Save the information
        [saved_field,saved_z_this_fiber] = func.extract_saved_field(prop_output.fields,max_save_per_fiber,current_z,prop_output.z);
        Nsv = size(saved_field,3);
        field{rt_num}(:,:,zn:zn+Nsv-1) = saved_field;
        saved_z(zn:zn+Nsv-1)           = saved_z_this_fiber;
        zn = zn + Nsv;
    end

    % Through LR
    Ein    = prop_output.fields(:,1,end);              % FBG 前的输入场
    [Eref, Etrn] = fbg_split(Ein, lambda, 1036, 2.3, R_LR);

    % 留腔 = 反射（回到腔里走返程）
    prop_output.fields(:,1,end)          = Eref;

    % 出腔 = 透射（主输出 / GMN 放大器种子）
    output_field(:,1,rt_num)             = Etrn;
    amp_seed_lastRT                      = Etrn;

    for j = 3:-1:1
        warning('off')
        prop_output = GMMNLSE_propagate(fiber_cavity(j), prop_output, sim_cavity(j), gain_param);
        warning('on')
        time_delay = time_delay + prop_output.t_delay(end);

        [saved_field, saved_z_this_fiber] = func.extract_saved_field(prop_output.fields, max_save_per_fiber, current_z, prop_output.z);
        field{rt_num}(:,:,zn:zn+size(saved_field,3)-1) = saved_field;
        saved_z(zn:zn+size(saved_field,3)-1) = saved_z_this_fiber;
        current_z = saved_z_this_fiber(end);  zn = zn + size(saved_field,3)-1;
    end

     
    % Through HR                                    % 峰值反射率（示例）
    Ein    = prop_output.fields(:,1,end);
    [Eref, Etrn] = fbg_split(Ein, lambda, 1030, 2.3, R_HR);

    prop_output.fields(:,1,end)          = Eref;       % 留腔o   

    saved_z = saved_z(1:zn-1);

    % -----------------------------------------------------------------
    % Energy of the output field
    output_energy(rt_num) = trapz(abs(output_field(:,1,rt_num)).^2) * prop_output.dt / 1e3; % nJ
    if rt_num ~= 1
        close(fig); 
    end
    warning('off'); output_field(:,:,rt_num) = pulse_tracker(output_field(:,:,rt_num)); warning('on');
    [converged_yes,force_stop_yes,fig] = check_convergence(output_energy, output_field(:,:,rt_num), f, t, tol_convergence, true, force_stop);

    % 更新 t_rep（包含正向+返向的时移）
    gain_param{1}.t_rep = gain_rate_eqn.t_rep + time_delay*1e-12;

    if (converged_yes || force_stop_yes.convergence)
        cprintf('blue','The field has converged!\n'); break;
    end
    if output_energy(rt_num) < 0.01
        disp('The pulse dies.'); pulse_survives=false; break;
    end
end

%% Add output fiber to fill in missing part of spectrum

prop_amp = prop_output;                       % 复用容器，保证 dt/t 轴一致
prop_amp.fields = amp_seed_lastRT;            % 单个通道：Nt x 1

prop_amp = GMMNLSE_propagate(fiber_8c, prop_amp, sim8);
prop_amp = GMMNLSE_propagate(fiber_Gain_b, prop_amp, sim_Gain, gain_param);

E_amp_nJ = trapz(abs(prop_amp.fields(:,1,end)).^2) * prop_amp.dt / 1e3;
fprintf('Amplifier output energy ≈ %.2f nJ\n', E_amp_nJ);


%% Finish the simulation and save the data
% Clear reducdant parts of the data
%field = field(1:rt_num);
%output_field = output_field(:,:,1:rt_num);
%energy = output_energy(arrayfun(@any,output_energy)); % clear zero

% -------------------------------------------------------------------------
% Save the final output field
%if pulse_survives
    %save('mamyshev10um4W.mat', 't','f','lambda','output_field','energy',...
                     %'saved_z','splice_z','field',...
                      %'fiber_cavity','sim_cavity','gain_param',... % cavity parameters
                      %'-v7.3'); % saved mat file version
%end
% -------------------------------------------------------------------------

%close(fig,fig_filter,fig_evolution);

% Compress the pulse
[~,~,~,~] = analyze_field( ...
    t, f, prop_amp.fields(:,:,end), 'Treacy-t', pi/6, 1e-6, true);

%% Go to sleep if doing long loops
%pause(10);
%system('rundll32.exe powrprof.dll,SetSuspendState 0,1,0');
function [E_reflect, E_transmit] = fbg_split(E_t, lambda_nm, cw_nm, bw_nm, R0)
    % E_t: 时域输入场（FBG 前）
    % lambda_nm: 波长轴（与你主程序的 lambda 一致, 单位 nm）
    % cw_nm, bw_nm: FBG 中心/带宽(FWHM, nm)
    % R0: 峰值反射率 (0..1)

    % -> 频域
    Ef = fftshift(fft(E_t));

    % 高斯反射谱 R(λ)
    sigma = bw_nm/(2*sqrt(2*log(2)));                 % FWHM -> sigma
    Rlam  = R0 .* exp(-0.5*((lambda_nm - cw_nm)/sigma).^2);
    rLam  = sqrt(Rlam);                                % 幅度反射
    tLam  = sqrt(max(0, 1 - Rlam));                    % 幅度透射（数值安全）

    % 频域分光
    Ef_ref = rLam .* Ef;                               % 反射
    Ef_trn = tLam .* Ef;                               % 透射

    % 回到时域
    E_reflect  = ifft(ifftshift(Ef_ref));              % 留腔
    E_transmit = ifft(ifftshift(Ef_trn));              % 出腔/种子
end
