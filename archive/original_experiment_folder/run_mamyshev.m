function result = run_mamyshev(PumpPower, cw2, plot_on)
% run_mamyshev  模拟 Mamyshev 振荡器在给定 Pump 和 cw2 下的稳态
%
% result 结构中包含：
%   t, f, lambda
%   output_field          最后一圈输出场（滤波器1 rejected 部分）
%   output_energy         最后一圈能量 (nJ)
%   pulse_survives        是否死亡
%   rt_num                实际运行的 roundtrip 数
%   converged             check_convergence 的数值收敛标志
%   force_stop            是否由 force_stop 提前终止
%   energy_mean/std/rel_fluct  最后几圈能量统计
%   fwhm_ps               时域 FWHM（ps）
%   ML_state              物理上的锁模状态：
%                         0 = 无锁模（脉冲死亡）
%                         1 = 稳定单脉冲或轻微呼吸（锁模成功）
%                        -1 = 不稳定 / 多脉冲 / 噪声态（锁模失败）

    if nargin < 1
        PumpPower = 4*0.8;   % 默认 Pump
    end
    if nargin < 2
        cw2 = 1030;          % 默认滤波器2中心波长
    end
    if nargin < 3
        plot_on = false;     % 扫描时建议 false，单点调试可以 true
    end

    close all;
    addpath('../../');

    %% Quick Change variables
    % PumpPower 由输入参数决定

    %% Gain info
    gain_rate_eqn.cross_section_filename = 'Liekki Yb_AV_20160530.txt';
    gain_rate_eqn.reuse_data = false;
    gain_rate_eqn.linear_oscillator_model = 0;
    gain_rate_eqn.core_diameter = 10; % um
    gain_rate_eqn.cladding_diameter = 125; % um
    gain_rate_eqn.core_NA = 0.08;
    gain_rate_eqn.absorption_wavelength_to_get_N_total = 920; % nm
    gain_rate_eqn.absorption_to_get_N_total = 1.7; % dB/m
    gain_rate_eqn.pump_wavelength = 976; % nm
    gain_rate_eqn.copump_power = PumpPower; % W
    gain_rate_eqn.counterpump_power = 0; % W
    gain_rate_eqn.midx = 1;
    gain_rate_eqn.mode_volume = 1;
    gain_rate_eqn.tau = 840e-6; % s
    gain_rate_eqn.export_N2 = true;
    gain_rate_eqn.ignore_ASE = true;
    gain_rate_eqn.max_iterations = 50;
    gain_rate_eqn.tol = 1e-5;
    gain_rate_eqn.allow_coupling_to_zero_fields = false;
    gain_rate_eqn.verbose = true;

    %% Setup fiber parameters
    sim.lambda0 = 1040e-9; % m
    sim.f0 = 2.99792458e-4/sim.lambda0; % THz
    sim.gpu_yes = false;

    sim8 = sim;
    sim8.progress_bar_name = 'SMF (8.5um)';
    sim8.save_period = 0.1; % m
    [fiber8,sim8] = load_default_GMMNLSE_propagate([],sim8,'single_mode');
    fiber8.MFD = 10.5; % um

    % Gain fiber
    sim_Gain = sim;
    sim_Gain.gain_model = 4;
    sim_Gain.progress_bar_name = 'Gain (10um)';
    sim_Gain.save_period = 0.5;
    fiber_Gain.L0 = 4;
    fiber_Gain.MFD = 11.1; % um
    [fiber_Gain,sim_Gain] = load_default_GMMNLSE_propagate(fiber_Gain,sim_Gain,'single_mode');

    % Short SMF (Gain to BPF1)
    fiber_8a = fiber8;
    fiber_8a.L0 = 0.4;

    % Long SMF (BPF1 to BPF2)
    fiber_8b = fiber8;
    fiber_8b.L0 = 1.5;

    % Short SMF (BPF2 to Gain)
    fiber_8c = fiber8;
    fiber_8c.L0 = 3.2;

    % Putting fibers together
    fiber_cavity = [fiber_Gain fiber_8a fiber_8b fiber_8c];
    sim_cavity   = [sim_Gain  sim8      sim8      sim8];

    %% Setup general cavity parameters
    max_rt = 50;          % 建议扫描时稍大一点
    Nt = 2^15;
    time_window = 40; % ps
    dt = time_window/Nt;
    f = sim.f0+(-Nt/2:Nt/2-1)'/(Nt*dt); % THz
    t = (-Nt/2:Nt/2-1)*dt; % ps
    c0 = 299792458; % m/s
    lambda = c0./(f*1e12)*1e9; % nm

    tol_convergence = 1e-3;
    force_stop = struct('tol_convergence',5e-3,...
                        'tol_fluctuation',1e-2,...
                        'min_rt',10);  % 10 圈后开始判断

    %% Spectral filter parameters
    spectral_filter1 = struct('bw',5,'cw',1040); % 你这里用 1040
    spectral_filter2 = struct('bw',3,'cw',cw2);

    %% Setup initial conditions
    tfwhm = 1; % ps
    total_energy = 1; % nJ
    prop_output = build_MMgaussian(tfwhm, time_window, total_energy,1,Nt);
    OC = 0.9; %#ok<NASGU> % 目前没直接用到

    %% Saved field information
    L0 = sum([fiber_cavity.L0]);
    save_num = sum(int64([fiber_cavity.L0]./[sim_cavity.save_period] - length(fiber_cavity)));
    save_num = double(save_num);
    saved_z = zeros(1,save_num);
    field = cell(1,max_rt);
    pump = cell(1,max_rt); %#ok<NASGU>
    splice_z = cumsum([fiber_cavity.L0]);
    output_field = zeros(Nt,1,max_rt);
    max_save_per_fiber = 1000;

    %% Load gain parameters
    c = 299792458;
    v = 1/fiber_cavity(1).betas(2)*1e12;
    gain_rate_eqn.t_rep = L0/v;
    disp(1/gain_rate_eqn.t_rep);
    [gain_rate_eqn,cross_sections_pump,cross_sections,overlap_factor,~] = ...
        gain_info( sim_Gain,gain_rate_eqn,ifftshift(lambda,1) );
    N_total = 9e7;
    gain_param = {gain_rate_eqn,cross_sections_pump,cross_sections,overlap_factor,N_total};

    %% Run the cavity simulation
    func = analyze_sim;

    output_energy = zeros(max_rt,1);
    rt_num = 0;
    pulse_survives = true;

    if ~plot_on
        % 关闭所有 figure 显示（扫描时建议）
        set(0,'DefaultFigureVisible','off');
    end

    while rt_num < max_rt
        time_delay = 0;
        current_z = 0;
        zn = 1;
        rt_num = rt_num + 1;

        t_iteration_start = tic;
        cprintf('*[1 0.5 0.31]','Iteration %d', rt_num);

        for j = 1:4
            warning('off');
            prop_output = GMMNLSE_propagate(fiber_cavity(j), prop_output, sim_cavity(j),gain_param);
            warning('on');

            time_delay = time_delay + prop_output.t_delay(end);

            [saved_field,saved_z_this_fiber] = func.extract_saved_field( ...
                prop_output.fields,max_save_per_fiber,current_z,prop_output.z);
            field{rt_num}(:,:,zn:zn+size(saved_field,3)-1) = saved_field;
            saved_z(zn:zn+size(saved_field,3)-1) = saved_z_this_fiber;

            current_z = saved_z_this_fiber(end);
            zn = zn + size(saved_field,3)-1;

            % Spectral filters
            if (j==2)
                if plot_on && rt_num ~= 1
                    close(fig_filter1);
                end
                if plot_on
                    [prop_output,fig_filter1] = gaussian_spectral_filter( ...
                        prop_output, sim.f0, spectral_filter1.cw, spectral_filter1.bw,4,true);
                else
                    prop_output = gaussian_spectral_filter( ...
                        prop_output, sim.f0, spectral_filter1.cw, spectral_filter1.bw,4,false);
                end
                output_field(:,:,rt_num) = prop_output.rejected_fields(:,:,end);
            end

            if (j==3)
                if plot_on && rt_num ~= 1
                    close(fig_filter2);
                end
                if plot_on
                    [prop_output,fig_filter2] = gaussian_spectral_filter( ...
                        prop_output, sim.f0, spectral_filter2.cw, spectral_filter2.bw,4,true);
                else
                    prop_output = gaussian_spectral_filter( ...
                        prop_output, sim.f0, spectral_filter2.cw, spectral_filter2.bw,4,false);
                end
            end
        end

        saved_z = saved_z(1:zn);

        % Energy of the output field
        output_energy(rt_num) = trapz(abs(output_field(:,:,rt_num)).^2)*prop_output.dt/1e3; % nJ

        % Convergence check
        if rt_num ~= 1 && plot_on
            close(fig); % 只有画图时关
        end
        warning('off');
        output_field(:,:,rt_num) = pulse_tracker(output_field(:,:,rt_num));
        warning('on');
        if plot_on
            [converged_yes,force_stop_yes,fig] = check_convergence( ...
                output_energy,output_field(:,:,rt_num),f,t,tol_convergence,plot_on,force_stop);
        else
            [converged_yes,force_stop_yes] = check_convergence( ...
                output_energy,output_field(:,:,rt_num),f,t,tol_convergence,plot_on,force_stop);
        end

        % 显示时间
        t_iteration_end = toc(t_iteration_start);
        t_iteration_spent = datevec(t_iteration_end/3600/24);
        fprintf(': %1u:%2u:%3.1f\n',t_iteration_spent(4),t_iteration_spent(5),t_iteration_spent(6));

        % 更新重复频率
        gain_param{1}.t_rep = gain_rate_eqn.t_rep + time_delay*1e-12;

        % Characteristic lengths
        [ dispersion_length,nonlinear_length ] = characteristic_lengths( ...
            abs(output_field(:,1,rt_num)).^2,t,sim.f0,fiber_cavity(end).betas(3,:),1/fiber_cavity(end).SR );
        fprintf('  L_DL=%4f(m)\n',dispersion_length);
        fprintf('  L_NL=%4f(m)\n',nonlinear_length);

        if plot_on
            if(rt_num ~= 1)
                close(fig_evolution);
            end
            fig_evolution = func.analyze_fields_within_cavity(t,f,field{rt_num},saved_z,splice_z);
        end

        % Break if converged
        if (exist('converged_yes','var') && converged_yes) || ...
           (exist('force_stop_yes','var') && isstruct(force_stop_yes) && ...
            isfield(force_stop_yes,'convergence') && force_stop_yes.convergence)
            cprintf('blue','The field has converged!\n');
            break;
        end

        % Break if pulse dies
        if output_energy(rt_num) < 0.01
            disp('The pulse dies.');
            pulse_survives = false;
            break;
        end
    end

    if ~plot_on
        set(0,'DefaultFigureVisible','on');
    end

    %% 计算最后几圈的能量波动
    if rt_num >= 5
        window = 5;
    else
        window = rt_num;
    end
    E_tail = output_energy(rt_num-window+1:rt_num);
    E_mean = mean(E_tail);
    E_std  = std(E_tail);
    rel_fluct = E_std / max(E_mean, 1e-12);

    %% Add output fiber
    fiber_8c = fiber8;
    fiber_8c.L0 = 0.2;

    prop_output1 = prop_output;
    prop_output1.fields = output_field(:,:,rt_num);

    if plot_on
        [~,~,~,~] = analyze_field( t,f,output_field(:,:,rt_num),'Treacy-t',pi/6,1e-6,true );
    else
        [~,~,~,~] = analyze_field( t,f,output_field(:,:,rt_num),'Treacy-t',pi/6,1e-6,false );
    end

    prop_output1 = GMMNLSE_propagate(fiber_8c, prop_output1, sim8);


    %% Pack results
    result = struct();
    result.t = t;
    result.f = f;
    result.lambda = lambda;
    result.output_field = output_field(:,:,rt_num);
    result.output_energy = output_energy(rt_num);
    result.pulse_survives = pulse_survives;
    result.rt_num = rt_num;

    if exist('converged_yes','var') && ~isempty(converged_yes)
        result.converged = converged_yes;
    else
        result.converged = false;
    end

    if exist('force_stop_yes','var') && isstruct(force_stop_yes) ...
            && isfield(force_stop_yes,'convergence')
        result.force_stop = force_stop_yes.convergence;
    else
        result.force_stop = false;
    end

    result.energy_mean       = E_mean;
    result.energy_std        = E_std;
    result.energy_rel_fluct  = rel_fluct;

    result.fwhm_ps = compute_fwhm(t, abs(result.output_field).^2);

    % 物理锁模状态：0 无锁模；1 单脉冲/轻微呼吸；-1 不稳定/多脉冲
    if ~pulse_survives || result.output_energy < 0.01
        result.ML_state = 0;
    elseif rel_fluct < 0.02   % <2% 波动视为锁模成功（包括 breathing）
        result.ML_state = 1;
    else
        result.ML_state = -1;
    end

end


function fwhm = compute_fwhm(t, I)
    I = I(:);
    t = t(:);
    if max(I) <= 0
        fwhm = NaN;
        return;
    end
    I = I / max(I);
    idx = find(I >= 0.5);
    if isempty(idx)
        fwhm = NaN;
        return;
    end
    fwhm = t(idx(end)) - t(idx(1)); % ps
end
