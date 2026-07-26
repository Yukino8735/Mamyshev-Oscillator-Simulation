function foutput = GMMNLSE_propagate_no_adaptive_deltaZ(fiber, initial_condition, sim, rate_gain_parameters, rate_gain_saved_data)
%GMMNLSE_PROPAGATE_NO_ADAPTIVE_DELTAZ Propagate an initial multimode pulse
%through an arbitrary distance of an optical fiber without the use of
%adaptive-step method.
%
% -------------------------------------------------------------------------
%
%   "fiber" is a structure with the fields:
%
%       Basic properties -->
%
%           betas - a (?,nm) matrix; "nm" = num_spatial_modes if under scalar fields;
%                                    otherwise, "nm" can be both num_spatial_modes or 2*num_spatial_modes depending on whether there's birefringence.
%                   betas(i, :) = (i-1)th order dispersion coefficient for each mode, in ps^n/m
%
%           n2 - the nonlinear coefficient (default to 2.3e-20 if not set)
%
%           SR - SR tensor, in m^-2
%           L0 - length of fiber, in m
%
%       Gain properties (for gain model 1,2,3; for rate-eqn gain model, see "gain_info.m") -->
%
%           dB_gain - the small-signal gain amplification of the pulse energy in dB;
%                     This is used to calculate the gain_coeff  (default to 30)
%           gain_coeff - small signal gain coefficient in m^-1, defined by "g" in A(z)=exp(gz/2)A(0)
%           gain_fwhm - FWHM of the gain spectrum, in m
%
%           saturation ==>
%                   The following three parameters are used to calculate the saturation intensity,
%                   or you can set the saturation intensity directly.
%
%                   gain_tau - the lifetime of the upper energy level
%                   t_rep - the repetition rate of the pulse
%                   gain_cross_section - the absorption+emission cross sections
%
%               saturation_intensity - for Taylor or new gain model, the scale intensity in J/m^2
%                                      This is defined by h*f/(sigma*tau), where f is the center frequency,
%                                                                                sigma is the sum of the emission and absorption cross sections,
%                                                                                tau is the lifetime of the higher energy level for population inversion,
%                   OR
%               saturation_energy - for SM gain model, the scale energy in nJ
%                                   This is defined by "saturation_intensity*Aeff"
%
% -------------------------------------------------------------------------
%
%   "initial_condition" is a structure with the fields:
%
%       dt - time step
%       fields - initial field, in W^1/2, (N-by-num_modes).
%                If the size is (N-by-num_modes-by-S), then it will take the last S.
%
%                num_modes = num_spatial_modes if "sim.scalar = true"
%                num_modes = num_spatial_modes*2 (spatial modes + polarization modes-x,y) otherwise
%
% -------------------------------------------------------------------------
%
%   "sim" is a structure with the fields:
%
%       Basic settings -->
%
%           betas - the betas for the slowly varying approximation and the moving frame, 
%                   that is to say, fiber.betas([1 2],:) = fiber.betas([1 2],:) - sim.betas;
%                   (2,1) column vector;
%                   if not set, no "sim.betas", the simulation will be run relative to the first mode
%           f0 - center frequency, in THz
%           sw - 1 includes self-steepening, 0 does not
%           deltaZ - small step size, in m
%                    This may need to be 1-50 um to account for intermodal beating,
%                    even if the nonlinear length is much larger than 50 um.
%           save_period - spatial period between saves, in m
%                         0 = only save input and output (save_period = fiber.L0)
%
%       MPA -->
%
%           MPA.M - parallel extent for MPA;
%                   1 is no parallelization,
%                   5-20 is recommended; there are strongly diminishing returns after 5-10.
%           MPA.n_tot_max - maximum number of iterations for MPA
%                           This doesn't really matter because if the step size is too large, the algorithm will diverge after a few iterations.
%           MPA.n_tot_min - minimum number of iterations for MPA
%           MPA.tol - tolerance for convergence for MPA
%                     Value of the average NRMSE between consecutive itertaions in MPA at which the step is considered converged.
%
%       Linear mode coupling -->
%
%           rmc.model - 0 = no linear mode coupling
%                       1 = unitary-matrix-R model
%                       2 = iQA-addition model
%                       3 = Manakov eqaution
%
%           Manakov equation ==>
%
%               When rmc.model = 3
%               Use "mode_groups" below.
%                   If this term is empty or doesn't exist in "sim", it's assumed that they're all in the same mode group.
%
%           rmc.Lcorr - any number; the correlation length of random mode coupling
%                       inf = use the same random matrix along the fiber
%
%           rmc.Lcoup - (rmc.model: 2) a matrix of the size (num_mode_groups,num_mode_groups);
%                       the coupling length of linear mode coupling between or inside mode groups, in m
%                       "inf" for its elements = no random mode coupling for that linear inter-or-intra-mode-group coupling
%
%           ---------------------------------------------------------------
%
%           rmc.mode_groups - an array; each number representing the number of modes in that mode groups.
%                             The summation of this array should be equal to the total number of modes.
%
%                                 E.g. [2 4] means there are 6 modes in total and 2 mode groups
%
%                             For rmc_model 1,2, this determines the block-diagonal structure of the random matrices.
%
%                             If not specified (no field "mode_group" in "sim" or sim.mode_groups=[];), 
%                                 R model:   the structure of R is determined by the difference in group velocities.
%                                 iQA model: Q is a full random matrix
%
%       Polarization included -->
%
%           scalar - 0(false) = consider polarization mode coupling
%                    1(true) = don't consider polarization mode coupling
%
%           *If under scalar field, the input field takes only the scalar fields, e.g., [mode1, mode2, mode3......].
%           *Otherwise, the input field of each polarization needs to be specified in the order of [mode1_+ mode1_- mode2_+ mode2_-......], where (+,-) can be (x,y) or any orthogonal modes.
%           *SRSK is always loaded in a dimension of num_spatial_modes^4. It's automatically calculated to its polarized version in the code.
%
%           ellipticity - the ellipticity of the polarization modes; Please refer to "Nonlinear Fiber Optics, eq (6.1.18) Agrawal" for the equations.
%                         0: linear polarization   -> (+,-)=(x,y)
%                         1: circular polarization -> (+,-)=(right,left)
%
%       Adaptive method -->
%
%           adaptive_deltaZ.model - 0 = don't use adaptive step method,
%                                   1 = use adaptive step based on RK4IP
%           adaptive_deltaZ.threshold - a scalar;
%                                       the accuracy used to determined whether to increase or decrease the step size.
%           adaptive_deltaZ.max_deltaZ - a scalar; the maximum adaptive step size
%
%           Currently, adaptive method supports only RK4IP.
%
%       Algorithms to use -->
%
%           singe_yes - 1(true) = single
%                       0(false) = double
%
%                       Many GPUs are optimized for single precision, to the point where one can get a 10-30x speedup just by switching to single precision.
%
%           gpu_yes - 1(true) = GPU
%                     0(false) = CPU
%
%                     Whether or not to use the GPU. Using the GPU is HIGHLY recommended, as a speedup of 50-100x should be possible.
%
%           Raman_model - 0 = ignore Raman effect
%                         1 = Raman model approximated analytically by a single vibrational frequency of silica molecules
%                                 (Ch. 2.3, p.42, Nonlinear Fiber Optics (5th), Agrawal)
%                         2 = Raman model including the anisotropic contribution
%                                 ("Ch. 2.3, p.43" and "Ch. 8.5, p.340", Nonlinear Fiber Optics (5th), Agrawal)
%                                 For more details, please read "Raman response function for silica fibers", by Q. Lin and Govind P. Agrawal (2006)
%
%               Raman_sponRS - true or false; whether to include spontaneous Raman term or not
%
%           step_method - a string that specifies which pulse-propagation algorithm to use;
%                         'split-step' - split-step algorithm
%                         'RK4IP'      - Runge-kutta under the interaction picture
%                         'MPA'        - massively parallel algorithm
%
%           gain_model - 0 = no gain
%                        1 = SM gain (total energy saturation)
%                        2 = new gain (spatial saturation)
%                        3 = Taylor expansion gain (approximate spatial saturation)
%                        4 = Gain-rate-equation model: see "gain_info.m" for details
%
%       Others -->
%
%           pulse_centering - 1(true) = center the pulse according to the time window, 0(false) = do not
%                             The time delay will be stored in time_delay after running GMMNLSE_propagate().
%           num_photon_noise_per_band - a scalar; include photon noise (typically one photon per frequency band)
%           gpuDevice.Index - a scalar; the GPU to use
%           gpuDevice.Device - the output of MATLAB "gpuDevice(gpu_index)"
%           cuda_dir_path - path to the cuda directory into which ptx files will be compiled and stored
%           progress_bar - 1(true) = show progress bar, 0(false) = do not
%                          It'll slow down the code slightly. Turn it off for performance.
%           progress_bar_name - the name of the GMMNLSE propagation shown on the progress bar.
%                               If not set (no "sim.progress_bar_name"), it uses a default empty string, ''.
%
% -------------------------------------------------------------------------
%
%   gain_parameters - Only used for gain_model=4, "gain rate-equation model".
%                     Please refer to "gain_info.m" for details.
%
% =========================================================================
%
% All the cases of num_modes for input fields and betas:
%
%                 | field   betas   SRSK
%   --------------------------------------------
%   (s,nl)        |   m       m      m
%   (s,M)         |   m       m      m
%   (s,r)         |   m       m      m
%   (p,nl)        |   2m     m,2m    m
%   (p,M)         |   2m     m,2m    m
%   (p,r)         |   2m     m,2m    m
%
%   m: num_spatial_modes
%   s: scalar fields, p: polarized fields
%   nl: no linear mode coupling, M: Manakov equation, r: random linear coupling
%
%   If num_modes(betas) = m, it's assumed that polarization modes are
%   degenerate in betas and is expanded into 2m modes automatically in 
%   the code, that is, (m,2m)->2m.
%
%   SRSK is always in a dimension of num_spatial_modes^4.
%
% =========================================================================
% Output:
% foutput.fields - (N, num_modes, num_save_points) matrix with the multimode field at each save point
% foutput.dt - time grid point spacing, to fully identify the field
% foutput.z - the propagation length of the saved points
% foutput.deltaZ - the (small) step size for each saved points
% foutput.betas - the [betas0,betas1] used for the moving frame
% foutput.t_delay - the time delay of each pulse which is centered in the time window during propagation
% foutput.seconds - time spent in the main loop
%
% For MPA:
%   foutput.full_iterations_hist - histogram of the number of iterations, accumulated and saved between each save point
%
% For gain-rate-equation model:
%   foutput.Power.pump_forward - (1,1,num_save_points); the forward pump power along the fiber
%   foutput.Power.pump_backward - (1,1,num_save_points); the backward pump power along the fiber
%   *If ASE is considered,
%       foutput.Power.ASE_forward - (1,1,num_save_points); the forward ASE power along the fiber
%       foutput.Power.ASE_backward - (1,1,num_save_points); the backward ASE power along the fiber
%   *If N2 is exported,
%       foutput.N2 - (Nx,Nx,num_save_points); the doped ion density of the upper state
%   *If reuse_data,
%       If save_all_in_RAM,
%           foutput.saved_data - saved_data_info used for an oscillator to converge faster
%       else
%           foutput.clean_rate_gain_mat - the function handle to clear the saved mat files used for an oscillator to converge faster

% Consider only the last fields of the initial condition
initial_condition.fields = initial_condition.fields(:,:,end);

%% Add the folder of functions of random mode coupling and its functions
% Besides loading mode coupling folder, this "sep_char" is also used in GPU setup below.

if sim.rmc.model ~= 0
    if ispc
        sep_char = '\';
    else % unix
        sep_char = '/';
    end
    
    current_path = mfilename('fullpath');
    sep_pos = strfind(current_path,sep_char);
    current_folder = current_path(1:sep_pos(end));
    addpath([current_folder '../Linear_Mode_Coupling/']);
    clear sep_char sep_pos current_folder;
    
    % Load the main functions of random mode coupling.
    rmc_func = func_of_random_mode_coupling();
end

%% Check the validity of input parameters
if sim.gain_model == 3 && isequal(sim.step_method,'MPA')
    error('GMMNLSE_propagate:GainModelError',...
          'The taylor series gain model has only been implemented with the split-step and RK4IP algorithm, as the MM gain model should be more accurate');
end

if sim.save_period == 0
    sim.save_period = fiber.L0;
end

% MPA performs M large steps in parallel
if isequal(sim.step_method,'MPA')
    large_step = sim.deltaZ*sim.MPA.M;
else % split-step, RK4IP
    large_step = sim.deltaZ; % for those not MPA, the large step and small step are the same
end
num_large_steps_total = fiber.L0/large_step;
num_large_steps_persave = sim.save_period/large_step;
num_saves_total = fiber.L0/sim.save_period;

% Because of machine error, "rem" alone to determine divisibility isn't
% enough. eps() is included here.
if rem(num_large_steps_total,1) && rem(num_large_steps_total+eps(num_large_steps_total),1) && rem(num_large_steps_total-eps(num_large_steps_total),1)
    error('GMMNLSE_propagate:SizeIncommemsurateError',...
        'The large step size is %f m and the fiber length is %f m, which are not commensurate', large_step, fiber.L0)
else
    num_large_steps_total = round(num_large_steps_total);
end

if rem(num_large_steps_persave,1) && rem(num_large_steps_persave+eps(num_large_steps_persave),1) && rem(num_large_steps_persave-eps(num_large_steps_persave),1)
    error('GMMNLSE_propagate:SizeIncommemsurateError',...
        'The large step size is %f m and the save period is %f m, which are not commensurate', large_step, sim.save_period)
else
    num_large_steps_persave = round(num_large_steps_persave);
end

if rem(num_saves_total,1) && rem(num_saves_total+eps(num_saves_total),1) && rem(num_saves_total-eps(num_saves_total),1)
    error('GMMNLSE_propagate:SizeIncommemsurateError',...
        'The save period is %f m and the fiber length is %f m, which are not commensurate', sim.save_period, fiber.L0)
else
    num_saves_total = round(num_saves_total);
end

% Error check on the dimensions (num_modes) of matrices
check_nummodes(sim, fiber, initial_condition.fields);

% Check the random mode coupling input
if sim.rmc.model == 1
    rmc_func.rmc_check(sim);
end

%% Check the precision of the input fields and match it with "sim.single_yes"
if isequal(class(initial_condition.fields),'gpuArray')
    initial_condition.fields = gather(initial_condition.fields);
    input_field_precision = classUnderlying(initial_condition.fields);
else
    input_field_precision = class(initial_condition.fields);
end
if sim.single_yes
    running_precision = 'single';
else
    running_precision = 'double';
end
if ~isequal(input_field_precision,running_precision)
    initial_condition.fields = feval(str2func(['@' running_precision]), initial_condition.fields);
end

fiber.SR = double(fiber.SR); % input fiber.SR is always double-precision

%% Some Parameters

% Get the numerical parameters from the initial condition.
[Nt, num_modes,~] = size(initial_condition.fields);
num_spatial_modes = size(fiber.SR,1);

% For polarized fields, the dimension of the input betas is allowed to be
% "num_spatial_modes", so it needs to be expanded into
% "2*num_spatial_modes" in the rest of the computation.
fiber = betas_expansion_including_polarization_modes(sim,fiber,num_modes);

% Compute the index of modes in each mode group from "sim.mode_groups".
if sim.rmc.model ~= 0
    % Error check "sim.mode_groups".
    if sim.scalar
        sum_mode_groups = sum(sim.rmc.mode_groups);
    else
        sum_mode_groups = sum(sim.rmc.mode_groups)*2;
    end
    if sum_mode_groups ~= num_modes
        error('GMMNLSE_propagate:ModeGroupError',...
              'The total number of elements in mode groups should be equal to the number of modes.');
    end
    clear sum_mode_groups;
    
    if sim.rmc.model == 2 % Manakov equation
        if sim.scalar
            mode_group_idx = mat2cell(1:num_modes,1,sim.rmc.mode_groups); % the index of modes in each mode group
        else
            mode_group_idx = mat2cell(1:num_modes,1,sim.rmc.mode_groups*2); % the index of modes in each mode group
        end
    end
end

%% Pulse centering based on the moment of its intensity
if sim.pulse_centering
    % Center the pulse
    TCenter = floor(sum(sum((-floor(Nt/2):floor((Nt-1)/2))'.*abs(initial_condition.fields).^2),2)/sum(sum(abs(initial_condition.fields).^2),2));
    % Because circshift is slow on GPU, I discard it.
    %last_result = ifft(circshift(initial_condition.fields,-tCenter));
    if TCenter ~= 0
        if TCenter > 0
            initial_condition.fields = [initial_condition.fields(1+TCenter:end,:);initial_condition.fields(1:TCenter,:)];
        elseif TCenter < 0
            initial_condition.fields = [initial_condition.fields(end+1+TCenter:end,:);initial_condition.fields(1:end+TCenter,:)];
        end

        if sim.gpu_yes
            TCenter = gather(TCenter);
        end
        T_delay = TCenter*initial_condition.dt;
    else
        T_delay = 0;
    end
else
    T_delay = 0;
end

%% Set up the GPU details
% Use the specified GPU
% This needs to run at the beginning; otherwise, the already-stored values
% in GPU will be unavailable in a new GPU if the GPU device is switched.
if sim.gpu_yes
    try
        sim.gpuDevice.Device = gpuDevice(sim.gpuDevice.Index); % use the specified GPU device
    catch
        error('Please set the GPU you''re going to use by setting "sim.gpuDevice.Index".');
    end
end

% Additional info:
%   For Manakov equations, there's no cuda file for computing overlap
%   integrals. Because the complexity is O(N^2), it's done with MATLAB
%   itself.
if sim.gpu_yes && sim.rmc.model ~= 2
    if sim.single_yes
        single_str = 'single';
    else
        single_str = 'double';
    end
    
    % For no gain, SM gain, or rate-eqn gain use the normal cuda file
    % For the new gain model, use the slightly modified cuda file
    if ismember(sim.gain_model, [0 1 4])
        fname_part = 'sumterm';
    else % sim.gain_model == [2 3]; new_gain/taylor_gain models
        fname_part = 'sumterms';
    end
    
    % Polarization modes
    if sim.scalar && sim.rmc.model ~= 2
        polar_str = '';
    else % polarized fields or scalar Manakov
        polar_str = 'polarization_';
    end
    
    % Whether to include "anisotropic Raman term" or not
    if sim.Raman_model==0
        Raman_str = 'noRaman_';
    elseif ~sim.scalar && sim.Raman_model==2
        Raman_str = 'anisoRaman_';
    else
        Raman_str = '';
    end
    
    % Nonlinear term
    SRSK_filename = ['calculate_' fname_part '_part_' polar_str Raman_str single_str];
    clear fname_part polar_str Raman_str;
    
    % The number of blocks is set based on the total number of threads
    if isequal(sim.step_method,'MPA')
        tot_num_threads = Nt*(sim.MPA.M+1);
    else % split-step, RK4IP
        tot_num_threads = Nt;
    end
    
    % Finally save the kernel
    sim.cuda_SRSK = setup_kernel(SRSK_filename,sim,tot_num_threads);
    if sim.rmc.model == 1
        sim.rmc.cuda_add_iQdz = setup_kernel(['add_iQdz_' single_str],sim,Nt*(sim.MPA.M+1)*num_modes);
        sim.rmc.cuda_add_iQdz_final = setup_kernel(['add_iQdz_final_' single_str],sim,Nt*num_modes);
        sim.rmc.cuda_energy_calibration = setup_kernel(['energy_calibration_' single_str],sim,Nt*(sim.MPA.M+1));
        sim.rmc.cuda_energy_calibration_final = setup_kernel(['energy_calibration_' single_str],sim,Nt);
    end
    clear single_str;
end

%% Work out the overlap tensor details
% Because of the symmetry, there are possibly zeros in SR. To improve the
% performance, store only the indices of each nonzero elements and their
% corresponding values.
nonzero_midx1234s = find(permute(fiber.SR,[4 3 2 1])); % The indices of nonzero elements in SR will be stored in nonzero_midx1234s.
nonzero_midx1234s = reverse_linear_indexing(nonzero_midx1234s,num_spatial_modes);
[midx1,midx2,midx3,midx4] = ind2sub(num_spatial_modes*ones(1,4),nonzero_midx1234s'); % restore linear indexing back to subscripts
SRa_info.nonzero_midx1234s = uint8([midx1;midx2;midx3;midx4]);
SRa_info.SRa = fiber.SR(nonzero_midx1234s); % the corresponding values of each nonzero elements
clear nonzero_midx1234s midx1 midx2

if sim.single_yes
   SRa_info.SRa = single(SRa_info.SRa);
end
if sim.gpu_yes
   SRa_info.SRa = gpuArray(SRa_info.SRa);
else % If not using the GPU, we also need to calculate the indices that don't have all zero coefficients for any given last two indices
    tmp = cellfun(@(SR12) any(SR12(:)), mat2cell(fiber.SR,num_spatial_modes,num_spatial_modes,ones(num_spatial_modes,1),ones(num_spatial_modes,1)));
    nonzero_midx34s = find(squeeze(tmp));
    [midx3,midx4] = ind2sub(num_spatial_modes*ones(1,2),nonzero_midx34s');
    SRa_info.nonzero_midx34s = uint8([midx3;midx4]);
end
clear midx3 midx4

% Update SRa, SRb, and SK regarding polarization modes.
if ~( sim.scalar && sim.rmc.model ~= 2 )
    if sim.Raman_model ~= 2
        [SRa_info, SK_info] = calc_polarized_SRSK(SRa_info,sim.ellipticity);
        SRb_info = [];
    else
        [SRa_info, SRb_info, SK_info] = calc_polarized_SRSK(SRa_info,sim.ellipticity,true);
    end
else % scalar fields: SK is proportional to SR by a factor, sim.SK_factor
    switch sim.ellipticity
        case 0 % linear polarization
            sim.SK_factor = 1;
        case 1 % circular polarization
            sim.SK_factor = 2/3;
        otherwise
            error('GMMNLSE_propagate:ellipticityError',...
                'The scalar mode supports only linear and circular polarizations.');
    end
    if sim.single_yes
        sim.SK_factor = single(sim.SK_factor);
    end
    
    SK_info = [];
    SRb_info = [];
end

% Manakov equation:
% Calculate its overlap integral or nonlinear coefficients.
if sim.rmc.model == 2
    [kappaK,kappaR1,kappaR2] = rmc_func.rmc_Manakov_kappa( sim,num_modes,SRa_info,SK_info );
end

%% Pre-calculate the dispersion term
% The "omegas" here is actually (omega - omega0), omega: true angular frequency
%                                                 omega0: central angular frequency (=2*pi*f0)
if sim.gpu_yes
    dt = gpuArray(initial_condition.dt);
else
    dt = initial_condition.dt;
end
omegas = 2*pi*ifftshift(linspace(-floor(Nt/2), floor((Nt-1)/2), Nt))'/(Nt*dt); % in 1/ps, in the order that the fft gives
if sim.single_yes
    omegas = single(omegas);
end
if sim.gpu_yes
    omegas = gpuArray(omegas);
end

% The dispersion term in the GMMNLSE, in frequency space
if any(size(fiber.betas) == Nt) % the betas is given over different frequencies,
                               % instead of the coefficients of the Taylor series expansion over the center frequency
    if size(fiber.betas,2) == Nt % betas should be a column vector
        fiber.betas = fiber.betas.';
    end
    if ~isfield(sim,'betas')
        sim.betas = zeros(2,1,'gpuArray');

        % Obtain the betas of the input pulse
        fftshift_omegas = fftshift(omegas,1);
        spectrum = sum(abs(fftshift(ifft(initial_condition.fields),1)).^2,2);
        omega0 = sum(fftshift_omegas.*spectrum)/sum(spectrum); % 2*pi*THz; the pulse center frequency (under shifted omega)
        omega_range = 1/dt; % 2*pi*THz
        omegas_idx_near_pulse = fftshift_omegas>omega0-omega_range/5 & fftshift_omegas<omega0+omega_range/5;% pick only the data near the pulse center frequency to find its beta0 and beta1
        clear spectrum omega0 omega_range;

        fit_order = 7;
        [betas_Taylor_coeff,~,mu] = polyfit(fftshift_omegas(omegas_idx_near_pulse),real(fiber.betas(omegas_idx_near_pulse,1)),fit_order);
        sim.betas = [betas_Taylor_coeff(end);betas_Taylor_coeff(end-1)];
        sim.betas = [sim.betas(1)-sim.betas(2)*mu(1)/mu(2);...
                     sim.betas(2)/mu(2)];
        clear fftshift_omegas fit_order betas_Taylor_coeff mu;
        %{
        % The following code finds sim.betas that minimizes the range and
        % values of betas.
        % However, it can pick a sim.betas that is far away from the input
        % pulse if the center frequency of the frequency window is too far away
        % from the pulse frequency. The result can deviate from the physics if
        % the step size isn't small enough.
        sim.betas = zeros(2,1,'gpuArray');

        % Obtain the betas of the input pulse
        fftshift_omegas = fftshift(omegas,1);
        fit_order = 7;
        [betas_Taylor_coeff,~,mu] = polyfit(fftshift_omegas,real(fiber.betas(:,1)),fit_order);
        sim.betas = [betas_Taylor_coeff(end);betas_Taylor_coeff(end-1)];
        new_betas = real(fiber.betas(:,1))-(sim.betas(1)+sim.betas(2)*(fftshift_omegas-mu(1))/mu(2));
        sim.betas = [sim.betas(1)-sim.betas(2)*mu(1)/mu(2) + (max(new_betas) + min(new_betas))/2;...
                     sim.betas(2)/mu(2)];
        clear fftshift_omegas fit_order betas_Taylor_coeff mu new_betas;
        %}
    end
    
    D0_op = 1i*(ifftshift(fiber.betas,1)-(sim.betas(1)+sim.betas(2)*omegas));
else
    % D0_op = sum( i*beta_n/n!*omega^n ,n)
    if ~isfield(sim,'betas')
        sim.betas = real(fiber.betas([1 2],1));
    end
    fiber.betas([1 2],:) = fiber.betas([1 2],:) - sim.betas; % beta0 and beta1 are set relative to sim.betas, or the fundamental mode if sim.betas doesn't exist
    % D_op = sum( 1i*beta_n/n!*omegas^n ,n,0,size(fiber.betas,1)-1 )
    taylor_n = permute(0:size(fiber.betas,1)-1,[1 3 2]); % calculation starting here is under the dimension (N,num_modes,order_betas)
    taylor_power = omegas.^taylor_n;
    D0_op = sum( 1i./factorial(taylor_n).*permute(fiber.betas,[3 2 1]).*taylor_power,3); % sum(...,3) sums over different "n" adding all Taylor series expansion terms
    clear taylor_n taylor_power
end

% If using rmc.model 2, Manakov equations, dispersion term is averaged in each mode group.
if sim.rmc.model == 2
    D0_op = rmc_func.Manakov_dispersion_operator( sim,D0_op,num_modes,Nt,mode_group_idx );
end

%% Pre-calculate the factor used in GMMNLSE (the nonlinear constant)
c = 2.99792458e-4; % speed of ligth m/ps
if ~isfield(fiber,'n2') || isempty(fiber.n2)
    fiber.n2 = 2.3e-20; % m^2/W
end
prefactor = 1i*fiber.n2*(omegas+2*pi*sim.f0)/c; % m/W

%% Pre-calculate the gain term if necessary
if sim.gpu_yes
    switch sim.gain_model
        case 1
            fiber.saturation_energy = gpuArray(fiber.saturation_energy);
        case {2,3}
            fiber.saturation_intensity = gpuArray(fiber.saturation_intensity);
    end
end
if ismember(sim.gain_model,[1 2 3])
    % Gaussian gain
    if fiber.gain_coeff ~= 0
        w_fwhm = 2*pi*sim.f0^2/c*fiber.gain_fwhm;
        w_0 = w_fwhm/(2*sqrt(log(2))); % 2*sqrt(log(2))=1.665
        gain_term = fiber.gain_coeff/2*exp(-omegas.^2/w_0^2);
        clear w_fwhm w_0;
    else
        gain_term = 0;
    end
    
    switch sim.gain_model
        case 1
            if isequal(sim.step_method,'MPA')
                G = gain_term*sim.deltaZ; % SM gain
            else
                G = gain_term*sim.deltaZ/2; % half because of symmetrized SS; SM gain
            end
        case {2,3}
            G = gain_term; % new-gain, Taylor-gain
    end
    clear gain_term;
end

%% Pre-compute the dispersion operator
if sim.gain_model == 4 % gain_rate_equation model
    is_fundamental_mode = isequal(rate_gain_parameters{1}.midx,1);
    D = calc_D(sim,D0_op,is_fundamental_mode);
else
    D = calc_D(sim,D0_op);
end

%% Pre-compute the Raman response in frequency space
if ~isfield(fiber,'material')
    fiber.material = 'silica';
end
[fiber,haw,hbw] = Raman_model( fiber,sim,Nt,dt);

%% Incoporate (1-fiber.fr) and fiber.fr into SRa,SRb,SK, or kappaK,kappaR1,kappaR2 to save the computational time
if sim.rmc.model ~= 2
    if isempty(SK_info) % scalar fields
        if sim.Raman_model ~= 0
            sim.SK_factor = (1-fiber.fr)/fiber.fr*sim.SK_factor; % For scalar fields, (1-fr)*SK = (1-fr)*( SK_factor*SRa )
                                                                 % SK' = (1-fr)*SK
                                                                 % SRa' = fr*SRa
                                                                 % SK' = (1-fr)*( SK_factor/fr*SRa' )
                                                                 % such that
                                                                 % SK_factor' = (1-fr)/fr*SK_factor
        end
    else % polarized fields
        SK_info.SK = (1-fiber.fr)*SK_info.SK;
    end
    
    if sim.Raman_model ~= 0
        SRa_info.SRa = fiber.fr*SRa_info.SRa;
    end
    
    if ~isempty(SRb_info)
        SRb_info.SRb = fiber.fr*SRb_info.SRb;
    end
else % Manakov
    kappaK = (1-fiber.fr)*kappaK;
    if sim.gain_model ~= 2
        kappaR1 = fiber.fr*kappaR1;
        kappaR2 = fiber.fr*kappaR2;
    else % new-gain model
        kappaR1.NL = fiber.fr*kappaR1.NL;
        kappaR2.NL = fiber.fr*kappaR2.NL;
    end
end

%% Random Mode coupling

z_points = num_large_steps_total + 1;
if sim.rmc.model == 1
    func_blkdiag_rand = blkdiag_rand(sim);
    
    % Find the random mode coupling strength
    std_Q = rmc_std_Q( sim,fiber,num_modes );
    
    if ~isequal(sim.step_method,'MPA')
        error('GMMNLSE_propagate:AlgorithmError',...
              '"Random mode coupling" (rmc.model=1,2) is currently implemented only with "MPA".');
    end
    % Because I use exp(iQdz)=1+iQdz+..., iQdz needs to be small compared to 1.
    MdeltaZ_threshold = 0.1;
    if max(std_Q(:))*sim.MPA.M*sim.deltaZ > MdeltaZ_threshold
        error('GMMNLSE_propagate:deltaZError',...
              ['M*deltaZ of MPA is too large for the current coupling strength.\n',...
               'Current iQdz is on the order of %6.4f, while the threshold is set to %3.2f.'],max(std_Q(:))*sim.MPA.M*sim.deltaZ,MdeltaZ_threshold);
    end
else % dummy variables
    iQdz = [];
    iQdz_2 = [];
    iQdz_3 = [];
end

%% Include the shot noise: one photon per mode
if sim.num_photon_noise_per_band ~= 0
    hbar = 6.62607015e-34/2/pi*1e24; % pJ*ps
    photon_noise_intensity = hbar*(omegas+2*pi*sim.f0)/(Nt*dt)*sim.num_photon_noise_per_band;
    % I use analytical-signal representation for solving GMMNLSE, so the field covers only the positive frequencies.
    photon_noise_intensity(photon_noise_intensity<0) = 0; % no noise at negative frequencies
    photon_noise_amplitude = sqrt(photon_noise_intensity);
    if sim.gpu_yes
        rand_phase = exp(1i*2*pi*rand(Nt,size(initial_condition.fields,2),'gpuArray'));
    else
        rand_phase = exp(1i*2*pi*rand(Nt,size(initial_condition.fields,2)));
    end
    initial_condition.fields = ifft(initial_condition.fields) + photon_noise_amplitude.*rand_phase;

    clear hbar photon_noise_intensity photon_noise_amplitude rand_phase;
else
    initial_condition.fields = ifft(initial_condition.fields);
    if sim.gpu_yes
        initial_condition.fields = gpuArray(initial_condition.fields);
    end
end

%% Include spontaneous Raman scattering
if sim.Raman_model ~= 0 && sim.Raman_sponRS
    sponRS_prefactor = spontaneous_Raman(Nt,dt,sim,fiber,num_modes);
else
    sponRS_prefactor = 0; % dummy variable
end

%% Setup the exact save points

% We will always save the initial condition as well
save_points = int64(num_saves_total + 1);

field_out = zeros(Nt, num_modes, save_points);
if sim.single_yes
    field_out = single(field_out);
end

% Start by saving the initial condition
if sim.gpu_yes
    field_out(:, :, 1) = gather(fft(initial_condition.fields));
else
    field_out(:, :, 1) = fft(initial_condition.fields);
end

T_delay_out = zeros(save_points,1);
T_delay_out(1) = T_delay;

%% Run the step function over each step
run_start = tic;
% -------------------------------------------------------------------------
if sim.gain_model == 4 % Gain rate-equation model
    if isequal(rate_gain_parameters{1}.midx,1) % fundamental mode
        if length(rate_gain_parameters) == 7 % single-mode computation ignores FmFnN and GammaN
            rate_gain_parameters = rate_gain_parameters(1:5);
        end
        [gain_rate_eqn,cross_sections_pump,cross_sections,overlap_factor,N_total] = deal(rate_gain_parameters{:});
        FmFnN = []; % set these dummy variables to pass into the function below
        GammaN = [];
    else % multimode or higher-order modes
        [gain_rate_eqn,cross_sections_pump,cross_sections,overlap_factor,N_total,FmFnN,GammaN] = deal(rate_gain_parameters{:});
    end
    % For fundamental mode, the computation of the gain amplification
    % factor is faster with CPU if the number of point < ~2^20.
    if sim.gpu_yes && ~isequal(rate_gain_parameters{1}.midx,1) % not fundamental mode
        %cross_sections_pump = structfun(@(c) gpuArray(c),cross_sections_pump,'UniformOutput',false);
        %overlap_factor = structfun(@(c) gpuArray(c),overlap_factor,'UniformOutput',false);
        cross_sections = structfun(@(c) gpuArray(c),cross_sections,'UniformOutput',false);
        overlap_factor.signal = gpuArray(overlap_factor.signal);
        N_total = gpuArray(N_total);
        FmFnN = gpuArray(FmFnN);
        GammaN = gpuArray(GammaN);
    end
    
    if ~gain_rate_eqn.ignore_ASE
        initial_condition.ASE_forward  = ifftshift(initial_condition.ASE_forward (:,:,end),1); % in the order of fft
        initial_condition.ASE_backward = ifftshift(initial_condition.ASE_backward(:,:,end),1); % in the order of fft
        if ~isequal(input_field_precision,running_precision)
            initial_condition.ASE_forward  = feval(str2func(['@' running_precision]), initial_condition.ASE_forward);
            initial_condition.ASE_backward = feval(str2func(['@' running_precision]), initial_condition.ASE_backward);
        end
        if sim.gpu_yes
            initial_condition.ASE_forward  = gpuArray(initial_condition.ASE_forward);
            initial_condition.ASE_backward = gpuArray(initial_condition.ASE_backward);
        end
    end
    if ~exist('rate_gain_saved_data','var')
        rate_gain_saved_data = []; % create a dummy variable to run the function
    end
    
    current_caller_path = cd;
    not_first_run  = exist(fullfile(current_caller_path, sprintf('%s%u.mat',gain_rate_eqn.saved_mat_filename,1)), 'file') == 2 ||...
                     ( exist('rate_gain_saved_data','var') && ~isempty(rate_gain_saved_data) );
    % Since for a linear oscillator, it's in general a self-consistent
    % system, it's not necessary to get the result of the first propagation
    % really accurately.
    if gain_rate_eqn.linear_oscillator_model == 2 && ~not_first_run
        gain_rate_eqn.tol = gain_rate_eqn.tol*10; % the tolerance of the iterations of the gain rate-eqn model is increased
    end
    % =====================================================================
    % Run the correct step function depending on the options chosen.
    % =====================================================================
    % For a linear oscillator, two propagations are coupled by their pump
    % power, ASE power, and pulses; therefore, the first propagation is run
    % normally in "GMMNLSE_rategain" and then use
    % "GMMNLSE_rategain_linear_oscillator" for the latter propagations
    % to consider this coupling effect.
    if gain_rate_eqn.linear_oscillator_model == 2 && not_first_run
        if isequal(sim.step_method,'MPA')
            if gain_rate_eqn.export_N2
                [field_out,T_delay_out,Power,N2,full_iterations_hist,saved_data_info] = GMMNLSE_rategain_linear_oscillator( sim,gain_rate_eqn,cross_sections_pump,cross_sections,overlap_factor,N_total,FmFnN,GammaN,z_points,save_points,num_large_steps_persave,T_delay,T_delay_out,initial_condition,prefactor, SRa_info, SRb_info, SK_info, omegas, D, haw, hbw, sponRS_prefactor, rate_gain_saved_data);
            else
                [field_out,T_delay_out,Power,   full_iterations_hist,saved_data_info] = GMMNLSE_rategain_linear_oscillator( sim,gain_rate_eqn,cross_sections_pump,cross_sections,overlap_factor,N_total,FmFnN,GammaN,z_points,save_points,num_large_steps_persave,T_delay,T_delay_out,initial_condition,prefactor, SRa_info, SRb_info, SK_info, omegas, D, haw, hbw, sponRS_prefactor, rate_gain_saved_data);
            end
        else % split-step, RK4IP
            if gain_rate_eqn.export_N2
                [field_out,T_delay_out,Power,N2,saved_data_info] = GMMNLSE_rategain_linear_oscillator( sim,gain_rate_eqn,cross_sections_pump,cross_sections,overlap_factor,N_total,FmFnN,GammaN,z_points,save_points,num_large_steps_persave,T_delay,T_delay_out,initial_condition,prefactor, SRa_info, SRb_info, SK_info, omegas, D, haw, hbw, sponRS_prefactor, rate_gain_saved_data);
            else
                [field_out,T_delay_out,Power,saved_data_info]    = GMMNLSE_rategain_linear_oscillator( simr,gain_rate_eqn,cross_sections_pump,cross_sections,overlap_factor,N_total,FmFnN,GammaN,z_points,save_points,num_large_steps_persave,T_delay,T_delay_out,initial_condition,prefactor, SRa_info, SRb_info, SK_info, omegas, D, haw, hbw, sponRS_prefactor, rate_gain_saved_data);
            end
        end
    else
        if gain_rate_eqn.reuse_data
            if isequal(sim.step_method,'MPA')
                if gain_rate_eqn.export_N2
                    [field_out,T_delay_out,Power,N2,full_iterations_hist,saved_data_info] = GMMNLSE_rategain( sim,gain_rate_eqn,cross_sections_pump,cross_sections,overlap_factor,N_total,FmFnN,GammaN,z_points,save_points,num_large_steps_persave,T_delay,T_delay_out,initial_condition,prefactor, SRa_info, SRb_info, SK_info, omegas, D, haw, hbw, sponRS_prefactor, rate_gain_saved_data);
                else
                    [field_out,T_delay_out,Power,   full_iterations_hist,saved_data_info] = GMMNLSE_rategain( sim,gain_rate_eqn,cross_sections_pump,cross_sections,overlap_factor,N_total,FmFnN,GammaN,z_points,save_points,num_large_steps_persave,T_delay,T_delay_out,initial_condition,prefactor, SRa_info, SRb_info, SK_info, omegas, D, haw, hbw, sponRS_prefactor, rate_gain_saved_data);
                end
            else % split-step, RK4IP
                if gain_rate_eqn.export_N2
                    [field_out,T_delay_out,Power,N2,saved_data_info] = GMMNLSE_rategain( sim,gain_rate_eqn,cross_sections_pump,cross_sections,overlap_factor,N_total,FmFnN,GammaN,z_points,save_points,num_large_steps_persave,T_delay,T_delay_out,initial_condition,prefactor, SRa_info, SRb_info, SK_info, omegas, D, haw, hbw, sponRS_prefactor, rate_gain_saved_data);
                else
                    [field_out,T_delay_out,Power,saved_data_info]    = GMMNLSE_rategain( sim,gain_rate_eqn,cross_sections_pump,cross_sections,overlap_factor,N_total,FmFnN,GammaN,z_points,save_points,num_large_steps_persave,T_delay,T_delay_out,initial_condition,prefactor, SRa_info, SRb_info, SK_info, omegas, D, haw, hbw, sponRS_prefactor, rate_gain_saved_data);
                end
            end
        else
            if isequal(sim.step_method,'MPA')
                if gain_rate_eqn.export_N2
                    [field_out,T_delay_out,Power,N2,full_iterations_hist] = GMMNLSE_rategain( sim,gain_rate_eqn,cross_sections_pump,cross_sections,overlap_factor,N_total,FmFnN,GammaN,z_points,save_points,num_large_steps_persave,T_delay,T_delay_out,initial_condition,prefactor, SRa_info, SRb_info, SK_info, omegas, D, haw, hbw, sponRS_prefactor);
                else
                    [field_out,T_delay_out,Power,   full_iterations_hist] = GMMNLSE_rategain( sim,gain_rate_eqn,cross_sections_pump,cross_sections,overlap_factor,N_total,FmFnN,GammaN,z_points,save_points,num_large_steps_persave,T_delay,T_delay_out,initial_condition,prefactor, SRa_info, SRb_info, SK_info, omegas, D, haw, hbw, sponRS_prefactor);
                end
            else % split-step, RK4IP
                if gain_rate_eqn.export_N2
                    [field_out,T_delay_out,Power,N2] = GMMNLSE_rategain( sim,gain_rate_eqn,cross_sections_pump,cross_sections,overlap_factor,N_total,FmFnN,GammaN,z_points,save_points,num_large_steps_persave,T_delay,T_delay_out,initial_condition,prefactor, SRa_info, SRb_info, SK_info, omegas, D, haw, hbw, sponRS_prefactor);
                else
                    [field_out,T_delay_out,Power]    = GMMNLSE_rategain( sim,gain_rate_eqn,cross_sections_pump,cross_sections,overlap_factor,N_total,FmFnN,GammaN,z_points,save_points,num_large_steps_persave,T_delay,T_delay_out,initial_condition,prefactor, SRa_info, SRb_info, SK_info, omegas, D, haw, hbw, sponRS_prefactor);
                end
            end
        end
    end
% -------------------------------------------------------------------------
else % No gain, SM-gain, or new-gain, Taylor-gain model
    last_A = initial_condition.fields;
    
    % Setup a small matrix to track the number of iterations per step
    if isequal(sim.step_method,'MPA')
        iterations_hist = zeros(sim.MPA.n_tot_max, 1);
        full_iterations_hist = zeros(sim.MPA.n_tot_max, save_points-1);
    end
    
    % Create a progress bar first
    if sim.progress_bar
        if ~isfield(sim,'progress_bar_name')
            sim.progress_bar_name = '';
        elseif ~ischar(sim.progress_bar_name)
            error('GMMNLSE_propagate:ProgressBarNameError',...
                '"sim.progress_bar_name" should be a string.');
        end
        h_progress_bar = waitbar(0,sprintf('%s   0.0%%',sim.progress_bar_name),...
            'Name',sprintf('Running GMMNLSE: %s...',sim.progress_bar_name),...
            'CreateCancelBtn',...
            'setappdata(gcbf,''canceling'',1)');
        setappdata(h_progress_bar,'canceling',0);

        % Create the cleanup object
        cleanupObj = onCleanup(@()cleanMeUp(h_progress_bar));

        % Use this to control the number of updated time for the progress bar below 1000 times.
        count_progress_bar = 1;
        num_progress_updates = 1000;
    end
    
    % Then start the propagation
    for ii = 2:z_points
        % Check for Cancel button press
        if sim.progress_bar && getappdata(h_progress_bar,'canceling')
            error('GMMNLSE_propagate:ProgressBarBreak',...
                  'The "cancel" button of the progress bar has been clicked.');
        end

        % =====================================================================
        % Linear Mode Coupling
        % =====================================================================
        if sim.rmc.model == 1
            % Update Q
            iQdz = 1i*func_blkdiag_rand.hermitian(num_modes,1).*std_Q*sim.deltaZ;
            iQdz_2 = iQdz^2/2; % more terms in Taylor series expansion of exp(iQdz)
            iQdz_3 = iQdz_2*iQdz/6;
        end
        
        % =====================================================================
        % Run the correct step function depending on the options chosen.
        % =====================================================================
        if sim.rmc.model ~= 2
            % -----------------------------------------------------------------
            % GMMNLLSE
            % -----------------------------------------------------------------
            switch sim.step_method
                case 'MPA'
                    switch sim.gain_model
                        case 0
                            [num_it, last_A] = GMMNLSE_MPA_nogain( last_A,     sim, prefactor, SRa_info, SRb_info, SK_info, D, haw, hbw, sponRS_prefactor, iQdz, iQdz_2, iQdz_3);
                        case 1
                            [num_it, last_A] = GMMNLSE_MPA_SMgain( last_A, dt, sim, prefactor, SRa_info, SRb_info, SK_info, D, haw, hbw, sponRS_prefactor, iQdz, iQdz_2, iQdz_3, G, fiber.saturation_energy);
                        case 2
                            [num_it, last_A] = GMMNLSE_MPA_newgain(last_A, dt, sim, prefactor, SRa_info, SRb_info, SK_info, D, haw, hbw, sponRS_prefactor, iQdz, iQdz_2, iQdz_3, G, fiber.saturation_intensity, fiber.fr);
                    end

                    iterations_hist(num_it) = iterations_hist(num_it)+1;
                case 'split-step'
                    if sim.rmc.model == 0
                        switch sim.gain_model
                            case 0
                                last_A = GMMNLSE_ss_nogain(    last_A,     sim, prefactor, SRa_info, SRb_info, SK_info, D, haw, hbw, sponRS_prefactor);
                            case 1
                                last_A = GMMNLSE_ss_SMgain(    last_A, dt, sim, prefactor, SRa_info, SRb_info, SK_info, D, haw, hbw, sponRS_prefactor, G, fiber.saturation_energy);
                            case 2
                                last_A = GMMNLSE_ss_newgain(   last_A, dt, sim, prefactor, SRa_info, SRb_info, SK_info, D, haw, hbw, sponRS_prefactor, G, fiber.saturation_intensity, fiber.fr);
                            case 3
                                last_A = GMMNLSE_ss_taylorgain(last_A, dt, sim, prefactor, SRa_info, SRb_info, SK_info, D, haw, hbw, sponRS_prefactor, G, fiber.saturation_intensity, fiber.fr);
                        end
                    else
                        error('GMMNLSE_propagate:AlgorithmError',...
                            '"Random mode coupling" (rmc.model=1,2) is currently implemented only with "MPA".');
                    end
                case 'RK4IP'
                    if sim.rmc.model == 0
                        switch sim.gain_model
                            case 0
                                last_A = GMMNLSE_RK4IP_nogain(    last_A,     sim, prefactor, SRa_info, SRb_info, SK_info, D, haw, hbw, sponRS_prefactor);
                            case 1
                                last_A = GMMNLSE_RK4IP_SMgain(    last_A, dt, sim, prefactor, SRa_info, SRb_info, SK_info, D, haw, hbw, sponRS_prefactor, G, fiber.saturation_energy);
                            case 2
                                last_A = GMMNLSE_RK4IP_newgain(   last_A, dt, sim, prefactor, SRa_info, SRb_info, SK_info, D, haw, hbw, sponRS_prefactor, G, fiber.saturation_intensity, fiber.fr);
                            case 3
                                last_A = GMMNLSE_RK4IP_taylorgain(last_A, dt, sim, prefactor, SRa_info, SRb_info, SK_info, D, haw, hbw, sponRS_prefactor, G, fiber.saturation_intensity, fiber.fr);
                        end
                    else
                        error('GMMNLSE_propagate:AlgorithmError',...
                            '"Random mode coupling" (rmc.model=1,2) is currently implemented only with "MPA".');
                    end
            end
        else
            % -----------------------------------------------------------------
            % Manakov equation
            % -----------------------------------------------------------------
            if isequal(sim.step_method,'MPA')
                switch sim.gain_model
                    case 0
                        [num_it, last_A] = GMMNLSE_MPA_nogain_Manakov( last_A,     sim, prefactor, kappaK, kappaR1, kappaR2, D, haw,                                mode_group_idx);
                    case 1
                        [num_it, last_A] = GMMNLSE_MPA_SMgain_Manakov( last_A, dt, sim, prefactor, kappaK, kappaR1, kappaR2, D, haw, G, fiber.saturation_energy,    mode_group_idx);
                    case 2
                        [num_it, last_A] = GMMNLSE_MPA_newgain_Manakov(last_A, dt, sim, prefactor, kappaK, kappaR1, kappaR2, D, haw, G, fiber.saturation_intensity, mode_group_idx);
                end

                iterations_hist(num_it) = iterations_hist(num_it)+1;
            else % split-step, RK4IP
                error('GMMNLSE_propagate:AlgorithmError',...
                    'Manakov equation is currently implemented only with "MPA".');
            end
        end
        % =====================================================================
        % Others
        % =====================================================================
        % Check for any NaN elements, if desired
        if any(any(isnan(last_A))) %any(isnan(last_A),'all')
            error('GMMNLSE_propagate:NaNError',...
                'NaN field encountered, aborting.\nPossible reason is that the nonlinear length is too close to the large step size, deltaZ*M for MPA or deltaZ for split-step.');
        end
        
        % Center the pulse
        if sim.pulse_centering
            last_A_in_time = fft(last_A);
            TCenter = floor(sum(sum((-floor(Nt/2):floor((Nt-1)/2))'.*abs(last_A_in_time).^2),2)/sum(sum(abs(last_A_in_time).^2),2));
            % Because circshift is slow on GPU, I discard it.
            %last_result = ifft(circshift(last_A_in_time,-tCenter));
            if TCenter ~= 0
                if TCenter > 0
                    last_A = ifft([last_A_in_time(1+TCenter:end,:);last_A_in_time(1:TCenter,:)]);
                elseif TCenter < 0
                    last_A = ifft([last_A_in_time(end+1+TCenter:end,:);last_A_in_time(1:end+TCenter,:)]);
                end
                if sim.gpu_yes
                    TCenter = gather(TCenter);
                end
                T_delay = T_delay + TCenter*initial_condition.dt;
            end
        end
        
        % If it's time to save, get the result from the GPU if necessary,
        % transform to the time domain, and save it
        if rem(ii-1, num_large_steps_persave) == 0
            A_out_ii = fft(last_A);

            if sim.gpu_yes
                field_out(:, :, int64((ii-1)/num_large_steps_persave)+1) = gather(A_out_ii);
            else
                field_out(:, :, int64((ii-1)/num_large_steps_persave)+1) = A_out_ii;
            end
            
            T_delay_out(int64((ii-1)/num_large_steps_persave)+1) = T_delay;

            % If using MPA, also save and reset the iteration number histogram
            if isequal(sim.step_method,'MPA')
                full_iterations_hist(:, int64((ii-1)/num_large_steps_persave)) = iterations_hist;
                iterations_hist = zeros(size(iterations_hist));
            end
        end

        % Report current status in the progress bar's message field
        if sim.progress_bar
            if z_points < num_progress_updates || floor((ii-1)/((z_points-1)/num_progress_updates)) == count_progress_bar
                waitbar((ii-1)/(z_points-1),h_progress_bar,sprintf('%s%6.1f%%',sim.progress_bar_name,(ii-1)/(z_points-1)*100));
                count_progress_bar = count_progress_bar+1;
            end
        end
    end
end
% -------------------------------------------------------------------------

% Just to get an accurate timing, wait before recording the time
if sim.gpu_yes
    sim.betas = gather(sim.betas);
end
if sim.gpu_yes
    wait(sim.gpuDevice.Device);
end
fulltime = toc(run_start);

%% Save the results in a struct

foutput = struct('z', sim.save_period*(0:num_saves_total),...
                 'fields', field_out,...
                 'dt', initial_condition.dt,...
                 'betas', sim.betas,...
                 'seconds', fulltime,...
                 't_delay', T_delay_out);
if sim.gain_model == 4
    foutput.Power = Power;
    if gain_rate_eqn.export_N2
        foutput.N2 = N2;
    end
    if gain_rate_eqn.reuse_data
        if gain_rate_eqn.save_all_in_RAM
            foutput.saved_data = saved_data_info;
        else
            foutput.clean_rate_gain_mat=  saved_data_info;
        end
    end
end

if isequal(sim.step_method,'MPA')
    foutput.full_iterations_hist = full_iterations_hist;
end

end

%% Helper functions
% -------------------------------------------------------------------------
    % ---------------------------------------------------------------------
    function recompile_ptx(sim,cudaFilename,ptxFilename)
        if ispc
            system(['nvcc -ptx "', fullfile(sim.cuda_dir_path,cudaFilename), '" --output-file "', fullfile(sim.cuda_dir_path,ptxFilename) '"']);
        else % unix
            % tested: Debian 10 (Buster)
            system(['nvcc -ccbin clang -ptx "', fullfile(sim.cuda_dir_path,cudaFilename), '" --output-file "', fullfile(sim.cuda_dir_path,ptxFilename) '"']);
            
            % For Yi-Hao's Debian PC only.
            % Matlab 2020b generates ptx of ".target sm_52" by default.
            % However, my own GPU, GeForce 660 Ti" is too old. I need to set it to sm_30 to make it work.
            % Starting from Matlab 2021a, my own GPU isn't supported.
            system(['sed -i ''s/.target sm_52/.target sm_30/g'' "' fullfile(sim.cuda_dir_path,ptxFilename) '"']); % run the shell script to change it to sm_30
        end
    end
    % ---------------------------------------------------------------------
function kernel = setup_kernel(filename,sim,total_num)

total_num = gather(total_num);

cudaFilename = [filename, '.cu'];
ptxFilename = [filename, '.ptx'];

if ~exist(fullfile(sim.cuda_dir_path,ptxFilename), 'file')
    recompile_ptx(sim,cudaFilename,ptxFilename);
end

% Setup the kernel from the cu and ptx files
try
    kernel = parallel.gpu.CUDAKernel(fullfile(sim.cuda_dir_path,ptxFilename), fullfile(sim.cuda_dir_path,cudaFilename));
catch
    % Compile the CUDA code again.
    % Currently found error:
    %    version mismatch due to different versions of cuda I use in Windows and Debian.
    recompile_ptx(sim,cudaFilename,ptxFilename);
    kernel = parallel.gpu.CUDAKernel(fullfile(sim.cuda_dir_path,ptxFilename), fullfile(sim.cuda_dir_path,cudaFilename));
end

if total_num > kernel.MaxThreadsPerBlock
    ThreadsPerBlock = kernel.MaxThreadsPerBlock;
else
    ThreadsPerBlock = total_num;
end
kernel.ThreadBlockSize = [ThreadsPerBlock,1,1];
kernel.GridSize =[ceil(total_num/ThreadsPerBlock), 1];

end
% =========================================================================
function check_nummodes(sim, fiber, fields)
%CHECK_NUMMODES It checks the consistency of the number of modes of betas, SR tensors, and fields.

% Get the number of spatial modes from "SR".
num_spatial_modes = size(fiber.SR,1);

% -------------------------------------------------------------------------
% Check the number of spatial modes from betas and SR.
if sim.scalar
    num_spatial_modes_betas = size(fiber.betas,2);
else % polarized fields
    num_modes_betas = size(fiber.betas,2);
    if num_modes_betas == num_spatial_modes
        num_spatial_modes_betas = num_modes_betas;
    else % betas has already included polarization modes
        num_spatial_modes_betas = num_modes_betas/2;
    end
end

if num_spatial_modes_betas ~= num_spatial_modes
    if size(fiber.betas,1)==1 % if the user give betas in row vector for single mode. It should be in column vector.
        error('GMMNLSE_propagate:NumModesError',...
            '"betas" of each mode should be be in the form of "column vector".\nThe number of spatial modes of betas and SR tensors should be the same.');
    else
        error('GMMNLSE_propagate:NumModesError',...
            'The number of spatial modes of betas and SR tensors should be the same.');
    end
end

% -------------------------------------------------------------------------
% Check the number of modes of fields
num_modes_fields = size(fields,2); % spatial modes (+ polarization modes)

field_modes_mismatched = false;
if sim.scalar
    if num_modes_fields ~= num_spatial_modes
        field_modes_mismatched = true;
    end
else
    if num_modes_fields ~= 2*num_spatial_modes
        field_modes_mismatched = true;
    end
end
if field_modes_mismatched
    error('GMMNLSE_propagate:NumModesError',...
        'The number of modes of fields doesn''t match those of betas and SR tensors.\nIf not scalar fields, num_modes(field)=2*num_spatial_modes(SR,betas).');
end

end
% -------------------------------------------------------------------------
function fiber = betas_expansion_including_polarization_modes(sim,fiber,num_modes)
%BETAS_EXPANSION_INCLUDING_POLARIZATION_MODES It extends betas into 2*num_spatial_modes if necessary.

num_modes_betas = size(fiber.betas,2);

if ~sim.scalar
    if num_modes_betas == num_modes/2 % num_modes = 2*num_spatial_modes
        betas(:,2:2:num_modes) = fiber.betas;
        betas(:,1:2:num_modes-1) = fiber.betas;
        fiber.betas = betas;
    end
end

end
% -------------------------------------------------------------------------
function rev_idx = reverse_linear_indexing(idx,n)
%REVERSE_LINEAR_INDEXING
%
%   MATLAB linear indexing starts from the first dimension and so on, e.g.,
%   A = [7 5; is expanded into [7 8 1 9 5 2 4 1] while its indices correspond to [1 5;
%        8 2;                                                                     2 6;
%        1 4;                                                                     3 7;
%        9 1]                                                                     4 8]
%
%   Please refer to MATLAB linear indexing for details.
%
%   However, in SR and SK summation calculation, "Ra" and "nonlinear" loop  
%   over the first two indices. If "nonzero_midx" can be sorted in a way 
%   that doesn't move back and forth the memory all the time, it should be
%   faster...probably. So I add this function to correct the linear 
%   indexing direction given from "find" function.
%
%   Take the above as an example, the result indexing should now be [1 2;  while the first two rows correspond to midx1 and midx2.
%                                                                    3 4;
%                                                                    5 6;
%                                                                    7 8]
% -------------------------------------------------------------------------
% Original linear indexing direction:
%   nonzero_midx1234s = find(fiber.SR);
%
% Corrected linear indexing direction:
%   nonzero_midx1234s = find(permute(fiber.SR,[4 3 2 1]));
%   nonzero_midx1234s = reverse_linear_indexing(nonzero_midx1234s,num_spatial_modes);

rev_matrix = permute(reshape(1:n^4,n,n,n,n),[4 3 2 1]);
rev_idx = rev_matrix(idx);

end
% -------------------------------------------------------------------------
function D = calc_D(sim,D_op,varargin)
%CALC_D It calculates the dispersion term in exp(Dz) or D*deltaZ, depending on the algorithm used.

if sim.gain_model == 4
    is_fundamental_mode = varargin{1};
    if is_fundamental_mode
        gain_model = 1;
    else
        gain_model = 2;
    end
else
    gain_model = sim.gain_model;
end

if isequal(sim.step_method,'MPA')
    switch gain_model
        case {0,2} % no gain, new gain
            % We can pre-compute exp(D_op*z) and exp(-D_op*z) for all z.
            z = permute((0:sim.MPA.M)',circshift(1:3,-1));% to make "Dz" into (N,num_modes,M+1)
            Dz = D_op*sim.deltaZ.*z;
            D = struct('pos', exp(Dz), 'neg', exp(-Dz));
        case {1,4} % SM gain
            % Since gain G is calculated/updated with D, we can't 
            % pre-compute exp(D*z) here, but we can still take into account 
            % the z step.
            D = D_op*sim.deltaZ;
    end
else % split-step, RK4IP
    % If we're not using MPA then we don't bother with pre-calculating exp(D*z)
    D = D_op*sim.deltaZ/2; % half here because of the symmetrized SS
end

end
% -------------------------------------------------------------------------
function cleanMeUp(h_progress_bar)
%CLEANMEUP It deletes the progress bar.

% DELETE the progress bar; don't try to CLOSE it.
delete(h_progress_bar);
    
end
% -------------------------------------------------------------------------