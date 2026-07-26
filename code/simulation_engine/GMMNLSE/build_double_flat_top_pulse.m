function output = build_double_flat_top_pulse(time_window, num_modes, N, pulse_duration, high_power, low_power, transition_time, varargin)
%BUILD_DOUBLE_FLAT_TOP_PULSE Builds a multimode flat-top temporal pulse with two distinct power levels.
%
% time_window - width of the entire time window, in ps
% num_modes - number of modes
% N - number of time grid points
% pulse_duration - total duration of the pulse in ps
% high_power - power level of the second half of the pulse (W)
% low_power - power level of the first half of the pulse (W)
% transition_time - transition duration between levels (ps)
%
% Optional inputs (varargin):
%   frequency_shift - a cell with two elements:
%                     the amount of shifted frequency (THz) (default is 0)
%                     and
%                     Fourier Transform type: 'fft' or 'ifft' (default is 'ifft')
%   coeffs - the normalized complex amplitude coefficients of different modes (default: equal across all modes)
%   center - temporal position of the pulse in the time window (default is 0)
%
% Notes:
%   Only smooths the **low to high power** transition inside the pulse.
%   The start and end of the pulse (0 to low_power, high_power to 0) are **not smoothed**.

%% Default optional input arguments
numvarargs = length(varargin);
if numvarargs > 3
    error('build_flat_top_pulse:TooManyInputs', ...
        'It takes at most 3 optional inputs');
end

% Set default values
frequency_shift = {'ifft', 0};
coeffs = ones(1, num_modes); % Equal energy distribution across modes
optargs = {frequency_shift, coeffs, 0};

% Overwrite defaults with varargin inputs
optargs(1:numvarargs) = varargin;
[frequency_shift, coeffs, center] = optargs{:};

% Ensure "coeffs" is a row vector and normalize
if size(coeffs, 2) == 1
    coeffs = coeffs.';
end
coeffs = coeffs ./ sqrt(sum(abs(coeffs).^2)); % Normalization

%% Define time array
dt = time_window / N;  % ps
t = (-N/2:N/2-1)' * dt; % Time array in ps

% Initialize pulse shape as zero
pulse_shape = zeros(size(t));

% Define the initial **step-like** pulse structure
pulse_shape((t >= center - pulse_duration/2) & (t < center)) = low_power;  % First half at low power
pulse_shape((t >= center) & (t <= center + pulse_duration/2)) = high_power;  % Second half at high power

% Apply smoothing **only** at the low to high transition
transition_mask = 0.5 * (1 + tanh((t - center) / transition_time));

% Apply the smooth transition while keeping the rest of the pulse unchanged
pulse_shape((t >= center - transition_time) & (t <= center + transition_time)) = ...
    low_power + (high_power - low_power) * transition_mask((t >= center - transition_time) & (t <= center + transition_time));

% Enforce **hard cutoff** beyond the pulse duration
pulse_shape(t < center - pulse_duration/2) = 0;
pulse_shape(t > center + pulse_duration/2) = 0;

% Convert intensity profile into field amplitude (sqrt of power)
field_amplitude = sqrt(pulse_shape);

% Apply frequency shift
switch frequency_shift{1}
    case 'ifft'
        field_amplitude = field_amplitude .* exp(-1i * (2 * pi * frequency_shift{2}) .* t);
    case 'fft'
        field_amplitude = field_amplitude .* exp(1i * (2 * pi * frequency_shift{2}) .* t);
    otherwise
        error('build_flat_top_pulse:frequency_shiftError',...
              'Fourier Transform type must be ''ifft'' or ''fft''.');
end

% Apply modal coefficients
field = coeffs .* field_amplitude;

% Output as a struct
output = struct('fields', field, 'dt', dt, 'time', t, 'pulse_shape', pulse_shape);

end
