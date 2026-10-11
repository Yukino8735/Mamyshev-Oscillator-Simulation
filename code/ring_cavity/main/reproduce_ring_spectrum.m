function result = reproduce_ring_spectrum(case_name, overrides)
%REPRODUCE_RING_SPECTRUM Headless, auditable ring-cavity spectrum experiment.
%   r = reproduce_ring_spectrum('legacy_rejected');
%   r = reproduce_ring_spectrum('table_rejected');
%   r = reproduce_ring_spectrum('table_broadband90');
% Table profiles use the stated MFD, absorption and intensity filter FWHM.
% broadband90 = a 90/10 broadband coupler BEFORE SF1, not a display scaling.
% rejected = SF1 rejected port (historical field difference for legacy;
% lossless complementary amplitude for table). No output-curve smoothing.
% An optional output pigtail is OUTSIDE the cavity and absent from the table.
% All generated results are saved under the existing Git-ignored directory.
if nargin < 1, case_name = 'legacy_rejected'; end
if nargin < 2, overrides = struct; end
addpath(fileparts(fileparts(fileparts(mfilename('fullpath')))));
project_root = setup_mamyshev_project();
cfg = struct('Nt',2^14,'time_window_ps',50,'max_rt',100,'min_rt',20, ...
    'stable_roundtrips',5,'tolerance',1e-3,'seed',1,'initial_energy_nJ',1, ...
    'initial_fwhm_ps',1,'tail_lengths_m',[0 .05 .1 .2 .4 .6], ...
    'step_tolerance',1e-6,'max_step_m',.02,'tag','','initial_file','', ...
    'filter_order',4,'spontaneous_raman',true);
names = fieldnames(overrides);
for k = 1:numel(names)
    assert(isfield(cfg,names{k}),'Unknown setting: %s',names{k});
    cfg.(names{k}) = overrides.(names{k});
end
assert(any(strcmp(case_name,{'legacy_rejected','legacy_broadband90', ...
    'table_rejected','table_broadband90'})),'Unknown physical model');
legacy = startsWith(case_name,'legacy');
broadband = endsWith(case_name,'broadband90');
rng(cfg.seed,'twister');
set(groot,'defaultFigureVisible','off');
run_name = [case_name cfg.tag];
output_dir = fullfile(project_root,'results','ring_cavity','generated',run_name);
if ~isfolder(output_dir), mkdir(output_dir); end

sim = struct('lambda0',1035e-9,'f0',2.99792458e-4/1035e-9, ...
    'gpu_yes',false,'progress_bar',false,'save_period',0, ...
    'Raman_sponRS',cfg.spontaneous_raman, ...
    'adaptive_deltaZ',struct('model',1,'threshold',cfg.step_tolerance, ...
    'max_deltaZ',cfg.max_step_m));
if legacy
    [passive,sim_passive] = load_default_GMMNLSE_propagate([],sim,'single_mode');
    passive.MFD = 10.5; % Deliberately preserve historical SR inconsistency.
else
    [passive,sim_passive] = load_default_GMMNLSE_propagate(struct('MFD',10.5),sim,'single_mode');
end
sim.gain_model = 4;
[gain_fiber,sim_gain] = load_default_GMMNLSE_propagate(struct('MFD',11.1,'L0',4),sim,'single_mode');
fibers = {gain_fiber,passive,passive,passive};
lengths = [4 .4 1.5 3.2];
for j = 1:4, fibers{j}.L0 = lengths(j); end
sims = {sim_gain,sim_passive,sim_passive,sim_passive};
dt = cfg.time_window_ps/cfg.Nt;
t = (-cfg.Nt/2:cfg.Nt/2-1)'*dt;
f = sim.f0+(-cfg.Nt/2:cfg.Nt/2-1)'/cfg.time_window_ps;
lambda = 299792.458./f;
gain = struct('cross_section_filename','Liekki Yb_AV_20160530.txt', ...
    'reuse_data',false,'linear_oscillator_model',0,'core_diameter',10, ...
    'cladding_diameter',125,'core_NA',.08, ...
    'absorption_wavelength_to_get_N_total',975,'absorption_to_get_N_total',6.4, ...
    'pump_wavelength',976,'copump_power',4,'counterpump_power',0, ...
    'midx',1,'mode_volume',1,'tau',840e-6,'export_N2',false,'ignore_ASE',true, ...
    'max_iterations',50,'tol',1e-5,'allow_coupling_to_zero_fields',false, ...
    'verbose',false,'memory_limit',2^30,'save_all_in_RAM',false, ...
    't_rep',sum(lengths)*gain_fiber.betas(2)*1e-12);
if legacy
    gain.absorption_wavelength_to_get_N_total = 920;
    gain.absorption_to_get_N_total = 1.7;
end
[gain,xsp,xss,overlap,N_total] = gain_info(sim_gain,gain,ifftshift(lambda));
if legacy
    N_total = 9e7;
else
    overlap.signal = (1-exp(-2*(gain.core_diameter/11.1)^2))/(pi*(gain.core_diameter/2)^2);
end
gain_param = {gain,xsp,xss,overlap,N_total};
T1 = filter_amplitude(sim.f0,dt,cfg.Nt,1040,5,legacy,cfg.filter_order);
T2 = filter_amplitude(sim.f0,dt,cfg.Nt,1030,3,legacy,cfg.filter_order);
state = build_MMgaussian(cfg.initial_fwhm_ps,cfg.time_window_ps,cfg.initial_energy_nJ,1,cfg.Nt);
if ~isempty(cfg.initial_file)
    initial = load(cfg.initial_file,'result');
    assert(initial.result.cfg.Nt == cfg.Nt && initial.result.cfg.time_window_ps == cfg.time_window_ps, ...
        'Checkpoint grid must match');
    state = struct('fields',initial.result.cavity_return,'dt',dt);
end
history = zeros(cfg.max_rt,5); % rt, output nJ, return nJ, dE, dSpectrum
stable = 0; previous_spectrum = []; status = 'maximum_roundtrips';
fprintf('START %s: N=%d; passive gamma=%.7g /W/m; Ntotal=%.8g /um^3; frep=%.5g Hz\n', ...
    run_name,cfg.Nt,2*pi*passive.n2/1035e-9*passive.SR,N_total,1/gain.t_rep);
timer = tic;
for rt = 1:cfg.max_rt
    time_delay = 0;
    for j = 1:4
        propagated = GMMNLSE_propagate(fibers{j},state,sims{j},gain_param);
        time_delay = time_delay+propagated.t_delay(end);
        field = propagated.fields(:,:,end);
        if j == 1
            after_gain = field;
        elseif j == 2
            before_SF1 = field;
            spectral_field = ifft(field);
            if broadband
                output_field = sqrt(.9)*field;
                transmitted = fft(sqrt(.1)*T1.*spectral_field);
                rejected = fft(sqrt(.1)*sqrt(max(0,1-T1.^2)).*spectral_field);
            else
                transmitted = fft(T1.*spectral_field);
                if legacy, R = 1-T1; else, R = sqrt(max(0,1-T1.^2)); end
                rejected = fft(R.*spectral_field);
                output_field = rejected;
            end
            field = transmitted;
        elseif j == 3
            field = fft(T2.*ifft(field));
            after_SF2 = field;
        end
        state = struct('fields',field,'dt',dt);
    end
    spectrum_f = abs(fftshift(ifft(output_field))).^2*(cfg.Nt*dt)^2/1e3;
    energy = sum(abs(output_field).^2)*dt/1e3;
    return_energy = sum(abs(state.fields).^2)*dt/1e3;
    if rt == 1
        dE = Inf; dS = Inf;
    else
        dE = abs(energy-history(rt-1,2))/max(energy,eps);
        dS = norm(spectrum_f-previous_spectrum)/max(norm(spectrum_f),eps);
    end
    previous_spectrum = spectrum_f;
    history(rt,:) = [rt energy return_energy dE dS];
    fprintf('%s RT %3d Eout=%9.4f nJ Ereturn=%9.4g dE=%.3g dS=%.3g elapsed=%.1fs\n', ...
        run_name,rt,energy,return_energy,dE,dS,toc(timer));
    gain_param{1}.t_rep = gain.t_rep+time_delay*1e-12;
    if rt >= cfg.min_rt && dE < cfg.tolerance && dS < cfg.tolerance
        stable = stable+1;
    else
        stable = 0;
    end
    if stable >= cfg.stable_roundtrips, status = 'converged'; end
    if return_energy < 1e-7, status = 'pulse_died'; end
    if ~isfinite(energy) || ~isfinite(return_energy) || any(~isfinite(state.fields(:)))
        status = 'nonfinite_field';
    end
    if mod(rt,5)==0 || ~strcmp(status,'maximum_roundtrips') || rt==cfg.max_rt
        result = struct('case_name',case_name,'cfg',cfg,'status',status, ...
            'rt',rt,'t_ps',t,'f_THz',f,'dt_ps',dt,'history',history(1:rt,:), ...
            'after_gain',after_gain,'before_SF1',before_SF1,'transmitted_SF1',transmitted, ...
            'rejected_SF1',rejected,'output_field',output_field, ...
            'after_SF2',after_SF2,'cavity_return',state.fields, ...
            'fibers',{fibers},'simulations',{sims},'gain_settings',gain,'overlap',overlap, ...
            'N_total',N_total,'T1',T1,'T2',T2,'elapsed_s',toc(timer), ...
            'matlab_version',version,'rng_final',rng);
        save(fullfile(output_dir,'checkpoint.mat'),'result','-v7');
    end
    if ~strcmp(status,'maximum_roundtrips'), break; end
end
tail_fields = zeros(cfg.Nt,numel(cfg.tail_lengths_m));
for k = 1:numel(cfg.tail_lengths_m)
    tail = passive; tail.L0 = cfg.tail_lengths_m(k);
    if tail.L0 == 0
        tail_fields(:,k) = output_field;
    else
        propagated = GMMNLSE_propagate(tail,struct('fields',output_field,'dt',dt),sim_passive);
        tail_fields(:,k) = propagated.fields(:,:,end);
    end
end
result.tail_fields = tail_fields;
result.elapsed_s = toc(timer);
save(fullfile(output_dir,'result.mat'),'result','-v7');
plot_ring_reproduction(result,output_dir);
fprintf('DONE %s: %s, %d roundtrips, %.1fs. %s\n',run_name,status,rt,toc(timer),output_dir);
end

function T = filter_amplitude(f0,dt,N,cw,bw,legacy,order)
f = f0+ifftshift((-N/2:N/2-1)')/(N*dt);
df = 299792.458/(cw-bw/2)-299792.458/(cw+bw/2);
x = 2*(f-299792.458/cw)/df;
if legacy
    T = exp(-.5*(x*sqrt(log(2))).^(2*order));
else
    T = exp(-.5*log(2)*x.^(2*order));
end
end
