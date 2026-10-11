function test_v4_oracle_parity(package_root)
% Development/parity-only test. No propagation and no predictive scoring.
if nargin<1,package_root=fileparts(fileparts(mfilename('fullpath')));end
T=readtable(fullfile(package_root,'provenance','oracle_parity_cases_24.csv'),'VariableNamingRule','preserve');
F={'pump_power_W','filter_offset_nm','filter2_bw_nm','gain_length_m'};
Y={'compressed_energy_nJ','compressed_duration_fs','compressed_peak_power_MW'};
r=jsondecode(fileread(fullfile(package_root,'configs','generator_recipe.json')));
for i=1:height(T)
    d=struct();for j=1:4,d.(F{j})=T.(F{j})(i);end
    y=v3_evaluate_synthetic(d,r);
    for j=1:3,assert(abs(y.(Y{j})-T.(Y{j})(i))<=1e-10+2e-10*abs(T.(Y{j})(i)));end
end
fprintf('Passed %d formula parity rows. GMMNLSE calls: 0.\n',height(T));
end
