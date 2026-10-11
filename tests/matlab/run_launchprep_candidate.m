% Cross-language candidate -> parent final chain; explicit synthetic fixture.
% This script NEVER calls the full cavity backend or propagation engine.
root=getenv('PHASE2_ROOT'); output_dir=getenv('PHASE2_OUTPUT_DIR');
addpath(fullfile(root,'code','ml_bridge'));
context=jsondecode(fileread(fullfile(output_dir,'launch_request.json')));
assert(strcmp(context.mode,'synthetic'),'Mamyshev:FixtureIdentity','Synthetic context required.');
rng(context.seed,'twister');
options=struct('kind','wrapper_component_fixture','backend',@synthetic_backend);
run_mamyshev_recorded(4,1030,false,fullfile(output_dir,'matlab_candidate.json'),options,context);

function legacy=synthetic_backend(pump,cw,plot_on)
assert(pump==4 && cw==1030 && isequal(plot_on,false));
t=(-2:2)'; field=exp(-t.^2).*exp(0.2i*t);
legacy=struct('t',t,'output_field',field,'pigtail_output_field',field, ...
    'output_energy',trapz(t,abs(field).^2)/1000,'fwhm_ps',1, ...
    'dechirped_fwhm_fs',NaN,'dechirped_peak_power_W',NaN, ...
    'rt_num',6,'converged',true,'force_stop',false,'pulse_survives',true, ...
    'ML_state',1,'energy_rel_fluct',0);
end
