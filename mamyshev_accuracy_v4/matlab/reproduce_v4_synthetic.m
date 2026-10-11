function summary = reproduce_v4_synthetic(package_root, output_csv, include_evaluation)
% Recompute frozen V3 formulas for V4 inputs. No GMMNLSE or propagation.
% Held-out labels are opt-in for integrity/parity verification only, not tuning.
if nargin<1 || isempty(package_root), package_root=fileparts(fileparts(mfilename('fullpath'))); end
if nargin<3, include_evaluation=false; end
if nargin<2 || isempty(output_csv), error('V4:OutputRequired','Provide new output CSV path.'); end
if isfile(output_csv), error('V4:NoOverwrite','Output already exists.'); end
recipe=jsondecode(fileread(fullfile(package_root,'configs','generator_recipe.json')));
files={'data/train_pool_4096.csv','data/validation_1024.csv'};
if include_evaluation
    files=[files,{'evaluation_only/calibration_1024.csv','evaluation_only/test_1536.csv','evaluation_only/challenge_512.csv'}];
end
features={'pump_power_W','filter_offset_nm','filter2_bw_nm','gain_length_m'};
targets={'compressed_energy_nJ','compressed_duration_fs','compressed_peak_power_MW'};
allTables=cell(numel(files),1);maxError=zeros(1,3);count=0;
for k=1:numel(files)
    T=readtable(fullfile(package_root,files{k}),'VariableNamingRule','preserve','TextType','string');
    calculated=zeros(height(T),3);
    for i=1:height(T)
        d=struct();for j=1:4,d.(features{j})=T.(features{j})(i);end
        y=v3_evaluate_synthetic(d,recipe);
        for j=1:3
            calculated(i,j)=y.(targets{j});reference=T.(targets{j})(i);
            err=abs(calculated(i,j)-reference);
            if ~isfinite(err) || err>1e-10+2e-10*abs(reference)
                error('V4:ParityFailure','%s row%d target%s differs by%.17g',files{k},i,targets{j},err);
            end
            maxError(j)=max(maxError(j),err);
        end
    end
    for j=1:3,T.(targets{j})=calculated(:,j);end
    allTables{k}=T;count=count+height(T);
end
writetable(vertcat(allTables{:}),output_csv);
summary=struct('rows',count,'max_abs_error',maxError,'source_kind','repository_guided_synthetic', ...
    'label_function','mamyshev_repository_guided_synthetic_v3','release_id','mamyshev_accuracy_v4', ...
    'gmmnlse_calls',0,'contains_evaluation_roles',logical(include_evaluation));
end
