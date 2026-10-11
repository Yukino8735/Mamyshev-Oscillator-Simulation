% Expected NONZERO process exit; a synthetic component, never a cavity run.
root=getenv('PHASE2_ROOT'); output_dir=getenv('PHASE2_OUTPUT_DIR');
addpath(fullfile(root,'code','ml_bridge'));
options=struct('kind','wrapper_component_fixture','backend',@fixture_stop);
% The real wrapper must write a failed candidate and propagate this exception.
% The supervisor owns runner_record.json; MATLAB owns only the candidate path.
run_mamyshev_recorded(4,1030,false,fullfile(output_dir,'matlab_candidate.json'),options);
error('WrapperTest:UnexpectedSuccess','Expected the synthetic stop exception to escape.');

function value=fixture_stop(~,~,~)
error('H01:FixtureAcceptedStepCaptured','Uncaught synthetic wrapper fixture stop: expected failure, no propagation.');
value=struct(); %#ok<UNRCH>
end
