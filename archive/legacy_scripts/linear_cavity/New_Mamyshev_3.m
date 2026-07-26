% This code finds the mode-locked state of a Mamyshev Oscillator

% A Mamyshev laser typically contains a sequence of small core passive fibers with spectral filters, 
% an isolator, short gain fiber (GMN regime), following by an output
% coupler, and an initial spectral filter.
%
% This file uses the rate-equation gain model for the gain fiber.

close all; clearvars;

addpath('../../');
    
%% Quick Change variables
PumpPower = 15; %(W)

%wa = 5.55; % (um) the radius of the MFD of 10um fiber
%wb = 5.25; % (um) the radius of the MFD of the 8.5um fiber
%eta = 4*(wa^2*wb^2)/(wa^2+wb^2)^2; %Estimated loss factor for large to small fiber core


%% Gain info
gain_rate_eqn.cross_section_filename = 'Liekki Yb_AV_20160530.txt'; % specify the folder with the eigenmode profiles
gain_rate_eqn.reuse_data = true; % For a ring or linear cavity, the pulse will enter a steady state eventually.
                                  % If reusing the pump and ASE data from the previous roundtrip, the convergence can be much faster, especially for counterpumping.
gain_rate_eqn.linear_oscillator_model = 1; % For a linear oscillator, there are pulses from both directions simultaneously, which will deplete the gain;
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
sim.lambda0 = 1040e-9; % m; center wavelength
sim.f0 = 2.99792458e-4/sim.lambda0; % THz; center frequency
sim.gpu_yes = false; % 
sim.step_method = 'MPA'; 
sim.adaptive_deltaZ.model = 0;
sim.deltaZ = 5e-5;               % 步长 (m)，单模可取 10–100 µm 量级；多模可适当更小

% MPA 相关控制（你的代码里从 sim.n_tot_max 读取，所以扁平放在 sim 根上）
sim.n_tot_max = 8;               % MPA 最大迭代
sim.n_tot_min = 3;               % MPA 最小迭代
sim.tol       = 1e-3;            % MPA 收敛阈值（NRMSE）
sim.M         = 8;   


sim8 = sim; % for the passive fibers
sim8.progress_bar_name = 'SMF (8.5um)';
sim8.save_period = 0.1; % m
[fiber8,sim8] = load_default_GMMNLSE_propagate([],sim8,'single_mode'); % for the passive fibers
fiber8.MFD = 10.5; % (um)

% Gain fiber
sim_Gain = sim;
sim_Gain.gain_model = 4; % use the rate-eqn-gain model
sim_Gain.progress_bar_name = 'Gain (10um)';
sim_Gain.save_period = 0.1; % m
fiber_Gain.L0 = 4;
fiber_Gain.MFD = 11.1; % (um)
[fiber_Gain,sim_Gain] = load_default_GMMNLSE_propagate(fiber_Gain,sim_Gain,'single_mode'); % for the gain fibers

fiber_8a = fiber8;       fiber_8a.L0 = 1.0;   % m  long passive near HR side
fiber_Gain_a = fiber_Gain; fiber_Gain_a.L0 = 0.9; % m  oscillator gain
fiber_8b = fiber8;       fiber_8b.L0 = 0.1;   % m  short passive near LR side

fiber_cavity = [fiber_8a, fiber_Gain_a, fiber_8b, fiber_8b, fiber_Gain_a, fiber_8a];
sim_cavity   = [sim8,     sim_Gain,     sim8    , sim8,     sim_Gain,     sim8];

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

%% Spectral filter parameters
spectral_filter1 = struct('bw',2.3, ... % bandwidth (nm)
                         'cw',1030); % center wavelength (nm)
spectral_filter2 = struct('bw',2.3, ... % bandwidth (nm)
                         'cw',1036); % center wavelength (nm)

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

gain_rate_eqn.t_rep = L0 / v; % s; the time required to finish a roundtrip (the inverse repetition rate of the pulse)
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
HR = 0.55; LR = 0.15;
[prop_output,fig_filter1] = gaussian_spectral_filter(prop_output, sim.f0, spectral_filter1.cw, spectral_filter1.bw,4,true); % Filter
prop_output.fields = prop_output.fields(:,:,end) * sqrt(1 - HR) + prop_output.rejected_fields(:,:,end);
rate_gain_saved_data = [];
while rt_num < max_rt
    time_delay = 0;
    current_z = 0;
    zn = 1;
    rt_num = rt_num + 1;
    
    t_iteration_start = tic;
    cprintf('*[1 0.5 0.31]','Iteration %d', rt_num);
    % -----------------------------------------------------------------
    for j = 1:6

        % Spectral filters
        if (j == 2 || j == 5)
            warning('off')
            prop_output = GMMNLSE_propagate(fiber_cavity(j), prop_output, sim_cavity(j),gain_param, rate_gain_saved_data);
            rate_gain_saved_data = prop_output.saved_data;
            warning('on')
            % Save the information
            [saved_field,saved_z_this_fiber] = func.extract_saved_field(prop_output.fields,max_save_per_fiber,current_z,prop_output.z);
            field{rt_num}(:,:,zn:zn+size(saved_field,3)-1) = saved_field;
            saved_z(zn:zn+size(saved_field,3)-1) = saved_z_this_fiber;
        
            current_z = saved_z_this_fiber(end);
            zn = zn + size(saved_field,3)-1;
        end
        if (j==3)
            if rt_num ~= 1
                close(fig_filter2); % close the previous figure and plot a new one
            end
            warning('off')
            prop_output = GMMNLSE_propagate(fiber_cavity(j), prop_output, sim_cavity(j),gain_param);
            warning('on')
            % Save the information
            [saved_field,saved_z_this_fiber] = func.extract_saved_field(prop_output.fields,max_save_per_fiber,current_z,prop_output.z);
            field{rt_num}(:,:,zn:zn+size(saved_field,3)-1) = saved_field;
            saved_z(zn:zn+size(saved_field,3)-1) = saved_z_this_fiber;
        
            current_z = saved_z_this_fiber(end);
            zn = zn + size(saved_field,3)-1;

            [prop_output,fig_filter2] = gaussian_spectral_filter(prop_output, sim.f0, spectral_filter2.cw, spectral_filter2.bw,4,true); % Filter
            prop_output.rejected_fields = prop_output.fields(:,:,end) * sqrt(1 - LR) + prop_output.rejected_fields(:,:,end);
            prop_output.fields = prop_output.fields(:,:,end) * sqrt(LR);
            output_field(:,:,rt_num) = prop_output.rejected_fields(:,:,end);
        end
        if (j == 6)
            if rt_num ~= 1
                close(fig_filter1); % close the previous figure and plot a new one
            end
            warning('off')
            prop_output = GMMNLSE_propagate(fiber_cavity(j), prop_output, sim_cavity(j),gain_param);
            warning('on')
            % Save the information
            [saved_field,saved_z_this_fiber] = func.extract_saved_field(prop_output.fields,max_save_per_fiber,current_z,prop_output.z);
            field{rt_num}(:,:,zn:zn+size(saved_field,3)-1) = saved_field;
            saved_z(zn:zn+size(saved_field,3)-1) = saved_z_this_fiber;
        
            current_z = saved_z_this_fiber(end);
            zn = zn + size(saved_field,3)-1;
           [prop_output,fig_filter1] = gaussian_spectral_filter(prop_output, sim.f0, spectral_filter1.cw, spectral_filter1.bw,4,true); % Filter
           prop_output.fields = prop_output.fields(:,:,end) * sqrt(HR);
        else
            warning('off')
            prop_output = GMMNLSE_propagate(fiber_cavity(j), prop_output, sim_cavity(j),gain_param);
            warning('on')
            % Save the information
            [saved_field,saved_z_this_fiber] = func.extract_saved_field(prop_output.fields,max_save_per_fiber,current_z,prop_output.z);
            field{rt_num}(:,:,zn:zn+size(saved_field,3)-1) = saved_field;
            saved_z(zn:zn+size(saved_field,3)-1) = saved_z_this_fiber;
        
            current_z = saved_z_this_fiber(end);
            zn = zn + size(saved_field,3)-1;
        end

        
    end

    saved_z = saved_z(1:zn);

    % -----------------------------------------------------------------
    % Energy of the output field
    output_energy(rt_num) = trapz(abs(output_field(:,:,rt_num)).^2)*prop_output.dt/1e3; % energy in nJ

    % If the energies stop changing, then we're done!
    if rt_num ~= 1
        close(fig); % close the previous figure and plot a new one
    end
    warning('off')
    output_field(:,:,rt_num) = pulse_tracker(output_field(:,:,rt_num));
    warning('on');
    [converged_yes,force_stop_yes,fig] = check_convergence( output_energy,output_field(:,:,rt_num),f,t,tol_convergence,true,force_stop );
    
    % ---------------------------------------------------------------------
    % Display running time of each roundtrip
    t_iteration_end = toc(t_iteration_start);
    t_iteration_spent = datevec(t_iteration_end/3600/24);
    fprintf(': %1u:%2u:%3.1f\n',t_iteration_spent(4),t_iteration_spent(5),t_iteration_spent(6));
    
    % ---------------------------------------------------------------------
    % Update the repetition rate based on "time_delay"
    % The pulse will shift in time with respect to the moving frame.
    % Since I implement the pulse centering function in the code,
    % I can use the information of "time_delay" in each roundtrip to calibrate to get the actual repetition rate.
    gain_param{1}.t_rep = gain_rate_eqn.t_rep + time_delay*1e-12;
    
    % ---------------------------------------------------------------------
    % Characteristic lengths
    [ dispersion_length,nonlinear_length ] = characteristic_lengths( abs(output_field(:,1,rt_num)).^2,t,sim.f0,fiber_cavity(end).betas(3,:),1/fiber_cavity(end).SR );
    fprintf('  L_DL=%4f(m)\n',dispersion_length);
    fprintf('  L_NL=%4f(m)\n',nonlinear_length);
     
    if(rt_num ~= 1)
        close(fig_evolution)
    end 
    fig_evolution = func.analyze_fields_within_cavity(t,f,field{rt_num},saved_z,splice_z);


    % ---------------------------------------------------------------------
    % Break if converged
    if converged_yes || force_stop_yes.convergence
        cprintf('blue','The field has converged!\n');
        break;
    end
    % Break if pulse dies
    if output_energy(rt_num) < 0.01 % smaller than 0.01 nJ
        disp('The pulse dies.');
        pulse_survives = false;
        break;
    end
end

%% Add output fiber to fill in missing part of spectrum

% Short SMF
fiber_8c = fiber8; fiber_8c.L0 = 0.1;
fiber_Gain_b = fiber_Gain; fiber_Gain_b.L0 = 1.9; % m  oscillator gain

prop_output1 = prop_output; %to reset the appropraite variables in this to keep the raw output and passively broadened output 
prop_output1.fields = output_field(:,:,rt_num);
prop_output1 = GMMNLSE_propagate(fiber_8c, prop_output1, sim8, gain_param);
prop_output1 = GMMNLSE_propagate(fiber_Gain_b, prop_output1, sim_Gain, gain_param);




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
[~,~,~,~] = analyze_field( t,f,prop_output1.fields(:,:,end),'Treacy-t',pi/6,1e-6,true );

%% Go to sleep if doing long loops
%pause(10);
%system('rundll32.exe powrprof.dll,SetSuspendState 0,1,0');

