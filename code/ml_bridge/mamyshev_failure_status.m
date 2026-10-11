function execution = mamyshev_failure_status(exception)
%MAMYSHEV_FAILURE_STATUS Separate numerical/operational failure from physics.
identifier = exception.identifier;
if strcmp(identifier,'GMMNLSE_propagate:ProgressBarBreak')
    execution = struct('job_status','cancelled','stop_reason','user_cancelled', ...
        'failure_reason',struct('identifier',identifier,'message',exception.message));
    return;
end
is_numerical = startsWith(identifier,'check_convergence:NonFinite') || ...
    contains(identifier,'NonFinite') || contains(identifier,'NoProgress') || ...
    contains(identifier,'RetryLimit') || contains(identifier,'InvalidRetryStep') || ...
    contains(identifier,'NonProgressingRetry');
if is_numerical
    reason = 'numerical_error';
else
    reason = 'execution_error';
end
execution = struct('job_status','failed','stop_reason',reason, ...
    'failure_reason',struct('identifier',identifier,'message',exception.message));
end
