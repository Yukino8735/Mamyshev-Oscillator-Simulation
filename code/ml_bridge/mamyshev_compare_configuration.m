function report=mamyshev_compare_configuration(current,reference_path,design_config)
% Exact recursive values/classes/shapes against directly captured baseline_001.
% Only cuda installation path and newly attached observer metadata are excluded.
report=struct('reference_path',reference_path, ...
    'reference_provenance','baseline_001 direct production-local capture; never baseline_002 copied reference', ...
    'comparison_rule','Exact class, shape and numeric values; NaNs equal only in matching legacy metadata', ...
    'checked_leaves',0,'unexpected_differences',{{}},'expected_metadata_differences',{{}}, ...
    'new_metadata_outside_reference',{{'A: run/source/worktree/wrapper/observer identities', ...
    'B: capture timestamps and resolved function paths', ...
    'C: runtime-only observations are deferred until production calls'}}, ...
    'additional_observations_not_in_baseline_001_mat',{{ ...
    'gain_info computed N_total was discarded in baseline_001; newly captured before unchanged override', ...
    'pulse death threshold was not in old config MAT; captured from same named production stopping condition'}}, ...
    'known_legacy_issues',{{'Passive MFD=10.5 um retains SR/area derived from 5.95 um', ...
    'Final N_total=9e7 overrides gain_info computation', ...
    'gain_info legacy memory_limit probe may report 0.5 bytes; unchanged physics'}}, ...
    'passed',false);
if ~isfile(reference_path)
    report.unexpected_differences={'critical baseline_001 configuration.mat missing'}; return;
end
reference=load(reference_path,'phase1_config','gain_param','prop_output','t','f','lambda');
if nargin>=3
    [design_config,resolved]=mamyshev_resolve_config(design_config);
    report.design_config=design_config;
    report.historical_reference_instance_unchanged=resolved.matches_historical_reference;
    report.comparison_rule=['Exact class, shape and values against historical reference with only explicitly requested ' ...
        'four-dimensional inputs and initial total-length/t_rep dependencies replaced; all other fields invariant.'];
    report.allowed_design_dependencies={'PumpPower_W/gain copump','cw2_nm/SF2 cw','SF2 bw', ...
        'gain fiber L0','initial t_rep from actual fixed-passive cavity length'};
    reference.phase1_config.PumpPower_W=design_config.pump_power_W;
    reference.phase1_config.cw2_nm=resolved.sf2_center_nm;
    reference.phase1_config.spectral_filter2.cw=resolved.sf2_center_nm;
    reference.phase1_config.spectral_filter2.bw=design_config.filter2_bw_nm;
    reference.phase1_config.fiber_cavity(1).L0=design_config.gain_length_m;
    v=1/reference.phase1_config.fiber_cavity(1).betas(2)*1e12;
    initial_t_rep=sum([reference.phase1_config.fiber_cavity.L0])/v;
    reference.phase1_config.gain_rate_eqn.copump_power=design_config.pump_power_W;
    reference.phase1_config.gain_rate_eqn.t_rep=initial_t_rep;
    reference.gain_param{1}.copump_power=design_config.pump_power_W;
    reference.gain_param{1}.t_rep=initial_t_rep;
end
required={'phase1_config','gain_param','prop_output','t','f','lambda'};
for k=1:numel(required)
    name=required{k};
    if ~isfield(reference,name) || ~isfield(current,name)
        report.unexpected_differences{end+1}=['critical field missing: ' name];
    else
        compare(current.(name),reference.(name),name);
    end
end
report.passed=isempty(report.unexpected_differences);

    function compare(a,b,path)
        if endsWith(path,'.cuda_dir_path') || endsWith(path,'.readonly_observer')
            if ~isequaln(a,b), report.expected_metadata_differences{end+1}=path; end
            return;
        end
        if ~strcmp(class(a),class(b)) || ~isequal(size(a),size(b))
            report.unexpected_differences{end+1}=[path ': class/shape mismatch']; return;
        end
        if isstruct(b)
            names=fieldnames(b); actual_names=fieldnames(a);
            for index=1:numel(b)
                for field_index=1:numel(names)
                    field=names{field_index}; next=sprintf('%s(%d).%s',path,index,field);
                    if ~isfield(a,field)
                        report.unexpected_differences{end+1}=[next ': missing'];
                    else, compare(a(index).(field),b(index).(field),next);
                    end
                end
            end
            extra=setdiff(actual_names,names);
            for field_index=1:numel(extra)
                field=extra{field_index};
                if strcmp(field,'readonly_observer')
                    report.expected_metadata_differences{end+1}=[path '.' field];
                else, report.unexpected_differences{end+1}=[path '.' field ': unexpected field'];
                end
            end
        elseif iscell(b)
            for index=1:numel(b), compare(a{index},b{index},sprintf('%s{%d}',path,index)); end
        else
            report.checked_leaves=report.checked_leaves+1;
            if ~isequaln(a,b)
                if isnumeric(a) && isnumeric(b) && all(isfinite(a(:))) && all(isfinite(b(:)))
                    detail=sprintf(': max abs difference %.17g',max(abs(double(a(:))-double(b(:)))));
                else, detail=': value mismatch'; end
                report.unexpected_differences{end+1}=[path detail];
            end
        end
    end
end
