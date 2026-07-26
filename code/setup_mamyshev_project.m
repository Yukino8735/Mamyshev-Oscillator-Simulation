function [project_root, engine_root] = setup_mamyshev_project()
%SETUP_MAMYSHEV_PROJECT Add the organized project code to the MATLAB path.
%
% Run this once after opening MATLAB, or let the canonical scripts call it
% automatically. The function uses its own location, so it is independent
% of MATLAB's current working directory.

code_root = fileparts(mfilename('fullpath'));
project_root = fileparts(code_root);
engine_root = fullfile(code_root, 'simulation_engine', 'GMMNLSE');

if ~isfolder(engine_root)
    error('Mamyshev:MissingEngine', ...
        'Simulation engine not found: %s', engine_root);
end

experiment_dirs = {
    fullfile(code_root, 'ring_cavity', 'main')
    fullfile(code_root, 'ring_cavity', 'scans')
    fullfile(code_root, 'ring_cavity', 'analysis')
    fullfile(code_root, 'linear_cavity', 'main')
    fullfile(code_root, 'linear_cavity', 'scans')
    fullfile(code_root, 'linear_cavity', 'analysis')
};

addpath(code_root);
addpath(engine_root);
addpath(experiment_dirs{:});
end
