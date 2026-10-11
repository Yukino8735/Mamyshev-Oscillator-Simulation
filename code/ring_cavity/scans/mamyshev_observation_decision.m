function [stop,reason]=mamyshev_observation_decision(options,rt,converged,force,energy,death_threshold,max_rt)
% Called after original convergence evaluation and completed-round updates.
% Does not evaluate or replace the convergence algorithm or propagate a field.
options=mamyshev_observation_options(options,max_rt);
assert(isscalar(rt) && isfinite(rt) && rt==fix(rt) && rt>=1 && rt<=max_rt, ...
    'MamyshevObservation:RoundCount','Invalid actual completed round.');
assert(islogical(converged) && isscalar(converged) && isstruct(force) && ...
    all(isfield(force,{'convergence','fluctuation'})) && ...
    islogical(force.convergence) && isscalar(force.convergence) && ...
    islogical(force.fluctuation) && isscalar(force.fluctuation), ...
    'MamyshevObservation:Flags','Expected actual logical convergence and force flags.');
assert(isscalar(energy) && isreal(energy) && isfinite(energy), ...
    'check_convergence:NonFiniteEnergy','Nonfinite energy cannot be bypassed by observation mode.');
stop=false; reason='';
if strcmp(options.observation_mode,'legacy')
    % Preserve the original ring caller order, including its unused fluctuation flag.
    if converged, stop=true; reason='legacy_energy_convergence';
    elseif force.convergence, stop=true; reason='legacy_average_energy_convergence';
    elseif energy<death_threshold, stop=true; reason='legacy_energy_below_threshold';
    end
else
    % Only convergence-type stops are bypassed. Other stop evidence wins even at N.
    if energy<death_threshold, stop=true; reason='legacy_energy_below_threshold';
    elseif force.fluctuation, stop=true; reason='legacy_energy_fluctuation_stop';
    elseif rt>=options.observation_roundtrips, stop=true; reason='observation_budget_reached';
    end
end
end
