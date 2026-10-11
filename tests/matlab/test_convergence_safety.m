function report = test_convergence_safety(mode)
%TEST_CONVERGENCE_SAFETY Non-propagating fixtures against the real helper.
%   report = test_convergence_safety('before') uses only legacy signatures.
%   Its three unsafe-input expectations must FAIL against the original code.
%   report = test_convergence_safety('after') also checks the repaired API.
%   No cavity is run, no physical label is inferred, and no fixture is data.
%   Decisions/IDs/counts are compared exactly; Gaussian equality uses 1e-14
%   relative tolerance solely to construct equal-energy artificial fields.

if nargin < 1
    mode = 'after';
end
assert(any(strcmp(mode, {'before','after'})), 'Unknown test mode.');
t = linspace(-8,8,256)';
freq = zeros(size(t)); % Unused because plotting is disabled.
single_field = exp(-t.^2);
double_field = exp(-(t-3).^2) + exp(-(t+3).^2);
double_field = double_field * sqrt(sum(abs(single_field).^2) / sum(abs(double_field).^2));
energy = ones(6,1);
force = struct('tol_convergence',1e-4,'tol_fluctuation',5e-4,'min_rt',30);
cases = struct('name',{},'passed',{},'error_identifier',{},'detail',{});

add_case('finite_legacy_energy_criterion', @finite_legacy);
add_case('reject_nan_effective_energy', @() expect_error( ...
    @() check_convergence(nan(6,1),single_field,freq,t,1e-3,false,force), ...
    'check_convergence:NonFiniteEnergy'));
add_case('reject_inf_effective_energy', @() expect_error( ...
    @() check_convergence(inf(6,1),single_field,freq,t,1e-3,false,force), ...
    'check_convergence:NonFiniteEnergy'));
bad_field = single_field; bad_field(10) = NaN;
add_case('reject_nonfinite_field_with_finite_energy', @() expect_error( ...
    @() check_convergence(energy,bad_field,freq,t,1e-3,false,force), ...
    'check_convergence:NonFiniteField'));

if strcmp(mode,'after')
    add_case('nan_early_valid_history_not_discarded', @() expect_error( ...
        @() check_convergence([NaN;ones(8,1)],single_field,freq,t,1e-3,false,force), ...
        'check_convergence:NonFiniteEnergy'));
    inf_field = single_field; inf_field(10) = complex(0,Inf);
    add_case('reject_inf_complex_field', @() expect_error( ...
        @() check_convergence(energy,inf_field,freq,t,1e-3,false,force), ...
        'check_convergence:NonFiniteField'));
    add_case('empty_history', @() expect_unresolved([],single_field,'empty_history'));
    add_case('insufficient_history_one_through_five', @insufficient);
    add_case('empty_field', @() expect_unresolved(energy,[],'empty_field'));
    add_case('all_zero_field', @() expect_unresolved(energy,zeros(size(single_field)),'zero_field'));
    add_case('all_zero_energy', @() expect_unresolved(zeros(6,1),single_field,'zero_energy_denominator'));
    add_case('zero_denominator_inside_valid_history', @() expect_unresolved([1;1;0;1;1;1],single_field,'zero_energy_denominator'));
    add_case('preallocated_tail_excluded_by_completed_rounds', @explicit_tail);
    add_case('nonfinite_unused_tail_excluded_only_by_completed_rounds', @nonfinite_tail);
    add_case('zero_completed_observation_not_trimmed', @observed_zero);
    add_case('omitted_count_does_not_guess_zero_tail', @() expect_unresolved([energy;zeros(44,1)],single_field,'zero_energy_denominator'));
    add_case('invalid_completed_round_count', @() expect_error( ...
        @() check_convergence(energy,single_field,freq,t,1e-3,false,force,1,7), ...
        'check_convergence:InvalidCompletedRounds'));
    add_case('nonfinite_derived_relative_difference', @() expect_error( ...
        @() check_convergence([1;realmin;realmax;1;1;1],single_field,freq,t,1e-3,false,force), ...
        'check_convergence:NonFiniteDifference'));
    add_case('row_column_history_equivalent', @orientation);
    add_case('equal_energy_single_double_are_not_physical_labels', @single_double);
end

report = struct('suite','convergence_safety','mode',mode, ...
    'fixture_only',true,'physical_cavity_runs',0, ...
    'production_function',which('check_convergence'), ...
    'cases',cases,'passed',sum([cases.passed]),'failed',sum(~[cases.passed]), ...
    'all_passed',all([cases.passed]));

    function add_case(name, fn)
        item = struct('name',name,'passed',false,'error_identifier','','detail','');
        try
            fn();
            item.passed = true;
        catch err
            item.error_identifier = err.identifier;
            item.detail = err.message;
        end
        cases(end+1) = item;
    end

    function finite_legacy()
        [yes, stopped] = check_convergence(energy,single_field,freq,t,1e-3,false,force);
        assert(isequal(yes,true) && ~stopped.convergence && ~stopped.fluctuation);
    end

    function expect_unresolved(e, field, reason)
        [yes, stopped, fig, diagnostic] = check_convergence(e,field,freq,t,1e-3,false,force);
        assert(isequal(yes,false) && ~stopped.convergence && ~stopped.fluctuation);
        assert(isempty(fig));
        assert(strcmp(diagnostic.reason,reason));
        assert(strcmp(diagnostic.criterion,'legacy_energy_change'));
        assert(strcmp(diagnostic.physical_state,'undetermined'));
    end

    function insufficient()
        for n = 1:5
            expect_unresolved(ones(n,1),single_field,'insufficient_history');
        end
    end

    function explicit_tail()
        [yes, ~, ~, d] = check_convergence([energy;zeros(44,1)],single_field,freq,t,1e-3,false,force,1,6);
        assert(yes && d.completed_rounds == 6 && d.observations_used == 6);
        assert(strcmp(d.reason,'energy_converged'));
    end

    function nonfinite_tail()
        values = [energy;NaN;Inf;zeros(42,1)];
        [yes, ~, ~, d] = check_convergence(values,single_field,freq,t,1e-3,false,force,1,6);
        assert(yes && d.observations_used == 6);
        expect_error(@() check_convergence(values,single_field,freq,t,1e-3,false,force,1,7), ...
            'check_convergence:NonFiniteEnergy');
    end

    function observed_zero()
        [yes, stopped, ~, d] = check_convergence([energy;0;zeros(43,1)],single_field,freq,t,1e-3,false,force,1,7);
        assert(~yes && ~stopped.convergence && d.observations_used == 7);
        assert(strcmp(d.physical_state,'undetermined'));
    end

    function orientation()
        [column_yes,column_stop] = check_convergence(energy,single_field,freq,t,1e-3,false,force);
        [row_yes,row_stop] = check_convergence(energy',single_field,freq,t,1e-3,false,force);
        assert(isequal(column_yes,row_yes) && isequal(column_stop,row_stop));
    end

    function single_double()
        relative_fixture_energy_difference = abs(sum(abs(single_field).^2)-sum(abs(double_field).^2))/sum(abs(single_field).^2);
        assert(relative_fixture_energy_difference <= 1e-14);
        [single_yes,~,~,single_d] = check_convergence(energy,single_field,freq,t,1e-3,false,force);
        [double_yes,~,~,double_d] = check_convergence(energy,double_field,freq,t,1e-3,false,force);
        assert(single_yes && double_yes);
        assert(strcmp(single_d.physical_state,'undetermined') && strcmp(double_d.physical_state,'undetermined'));
        assert(~isfield(single_d,'stable_single') && ~isfield(double_d,'stable_single'));
    end
end

function expect_error(fn, expected_id)
try
    fn();
catch err
    assert(strcmp(err.identifier,expected_id), ...
        'test_convergence_safety:WrongError', ...
        'Expected %s; observed %s: %s',expected_id,err.identifier,err.message);
    return;
end
error('test_convergence_safety:MissingError','Expected %s; function returned without error.',expected_id);
end
