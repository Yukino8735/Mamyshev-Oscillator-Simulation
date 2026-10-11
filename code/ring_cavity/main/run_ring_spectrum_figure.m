function result = run_ring_spectrum_figure()
%RUN_RING_SPECTRUM_FIGURE Re-run the near-target candidate and both displays.
% Table fiber parameters; super-Gaussian intensity-FWHM filters; 90% broadband
% coupling BEFORE SF1. This is a candidate interpretation, not a uniquely
% proven reproduction of the historical thesis figure.
result = reproduce_ring_spectrum('table_broadband90',struct( ...
    'Nt',8192,'max_rt',40,'min_rt',20,'filter_order',4, ...
    'tail_lengths_m',[0 .2],'tag','_figure_candidate'));
project_root = fileparts(fileparts(fileparts(fileparts(mfilename('fullpath')))));
result_file = fullfile(project_root,'results','ring_cavity','generated', ...
    'table_broadband90_figure_candidate','result.mat');
export_ring_spectrum_display(result_file,2,0);
export_ring_spectrum_display(result_file,8,0);
if ~strcmp(result.status,'converged')
    warning('Mamyshev:NotConverged', ...
        'This result is not a verified steady state. Do not label the smoothed display as a steady-state raw spectrum.');
end
end
