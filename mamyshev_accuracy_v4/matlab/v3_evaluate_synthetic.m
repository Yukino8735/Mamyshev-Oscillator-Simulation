function [targets, metadata] = v3_evaluate_synthetic(design, recipe)
% V3_EVALUATE_SYNTHETIC Explicit repository-guided scalar benchmark.
% This is NOT run_mamyshev_config / GMMNLSE. No propagation or RNG is used.
% Python/MATLAB parity must be tested on the user's installed MATLAB.
if nargin < 2
    root = fileparts(fileparts(mfilename('fullpath')));
    recipe = jsondecode(fileread(fullfile(root,'configs','generator_recipe.json')));
elseif ischar(recipe) || isstring(recipe)
    recipe = jsondecode(fileread(recipe));
end
names = {'pump_power_W','filter_offset_nm','filter2_bw_nm','gain_length_m'};
if ~isstruct(design) || ~isscalar(design) || ~isequal(sort(fieldnames(design)),sort(names'))
    error('V3:InvalidDesign','Exactly four design fields are required.');
end
for j=1:4
    k=names{j}; v=design.(k); lim=recipe.domain.(k);
    if ~isnumeric(v) || islogical(v) || ~isscalar(v) || ~isreal(v) || ~isfinite(v)
        error('V3:InvalidValue','%s must be finite, real, numeric and scalar.',k);
    end
    if v<lim(1) || v>lim(2)
        error('V3:OutsideDomain','%s outside the V3 benchmark domain.',k);
    end
end
ticks=design.gain_length_m/recipe.gain_length_step_m;
if abs(ticks-round(ticks))>1e-9
    error('V3:LengthGrid','Length must be on 0.1 m grid; it is not rounded.');
end
q=recipe.assumed_coefficients; r=recipe.reference_design; a=recipe.scale_anchor;
le=0; lt=0; low=zeros(1,4); high=zeros(1,4); u=zeros(1,4);
for j=1:4
    k=names{j}; cr=recipe.curves.(k); x=design.(k);
    le=le+logcurve(x,cr.x,cr.energy,cr.extension_scale)-logcurve(r.(k),cr.x,cr.energy,cr.extension_scale);
    lt=lt+logcurve(x,cr.x,cr.duration,cr.extension_scale)-logcurve(r.(k),cr.x,cr.duration,cr.extension_scale);
    core=recipe.historical_core_domain.(k); whole=recipe.domain.(k);
    low(j)=max(0,core(1)-x)/(core(1)-whole(1));
    high(j)=max(0,x-core(2))/(whole(2)-core(2));
    u(j)=(x-r.(k))/q.normalized_input_scales(j);
end
pl=u(1)*u(4); db=u(2)*u(3); pd=u(1)*u(2);
le=le+q.energy_cross_PL*pl+q.energy_cross_DB*db+q.energy_cross_PD*pd;
lt=lt+q.duration_cross_PL*pl+q.duration_cross_DB*db;
for j=1:4
    le=le-q.energy_outside_lower(j)*low(j)^2-q.energy_outside_upper(j)*high(j)^2;
    lt=lt+q.duration_outside_lower(j)*low(j)^2+q.duration_outside_upper(j)*high(j)^2;
end
energy=a.compressed_energy_nJ*exp(le); duration=a.compressed_duration_fs*exp(lt);
k0=a.compressed_peak_power_MW*a.compressed_duration_fs/a.compressed_energy_nJ;
shape=k0*exp(-q.shape_cross_PL_squared*pl^2-q.shape_cross_DB_squared*db^2);
peak=shape*energy/duration;
if ~all(isfinite([energy,duration,peak])) || any([energy,duration,peak]<=0)
    error('V3:InvalidOutput','Nonfinite or nonpositive synthetic result.');
end
targets=struct('compressed_energy_nJ',energy,'compressed_duration_fs',duration,'compressed_peak_power_MW',peak);
metadata=struct('backend_id',recipe.benchmark_id,'source_kind',recipe.source_kind,...
    'physical_state','undetermined','numerical_validation','not_verified',...
    'eligible_for_benchmark_ml',true,'eligible_as_validated_training_truth',false,...
    'waveform_available',false);
end

function y=logcurve(x,xs,ys,h)
xs=double(xs(:)); logs=log(double(ys(:)));
if x<xs(1)
    slope=(logs(2)-logs(1))/(xs(2)-xs(1));
    y=logs(1)+slope*h*tanh((x-xs(1))/h);
elseif x>xs(end)
    slope=(logs(end)-logs(end-1))/(xs(end)-xs(end-1));
    y=logs(end)+slope*h*tanh((x-xs(end))/h);
else
    y=interp1(xs,logs,x,'linear');
end
end
