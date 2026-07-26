function [output] = gaussian_spectral_notch_filter(input, f0, center_lambda, bandwidth_lambda)
%GAUSSIAN_SPECTRAL_FILTER  Apply a gaussian spectral filter to a field
%
% Input:
%   input.fields - a (N, num_modes, m) matrix with each mode's field, in the time domain
%   input.dt - the time grid spacing, in ps
%   f0 - the center frequency of simulations, in THz
%   center_lambda - the center wavelength of the filter, in nm
%   bandwidth_lambda - the FWHM of the filtetr, in nm
%
%   Optional inputs (varargin):
%       gaussexpo - supergaussian exponent (~exp(-t^(2*gaussexpo))) (default: 1)
%       verbose - true(1) or false(0); whether to plot the input and the output spectra (default: false)
%
% Output:
%   output.fields
%   output.rejected_fields
%   output.dt
%   fig - the figure handle of the figure if "verbose" is true

c = 299792.458; % in nm/ps

if ~isstruct(input)
    error('Unlike most auxiliary functions, gaussian_spectral_filter requires that the input be a struct with at least fields and dt');
end

optargs = 1;
[gaussexpo] = optargs;

if floor(gaussexpo) ~= gaussexpo
    error('Gaussian exponent needs to be an integer.');
end

input_field = input.fields;
Nt = size(input_field, 1);
dt = input.dt;

f = f0 + ifftshift(linspace(-Nt/2, Nt/2-1, Nt))'/(Nt*dt); % in THz, in the order that the fft gives

% Calculate the filter profile in frequency space
f_small = 299792.458/(center_lambda + bandwidth_lambda/2); % THz
f_large = 299792.458/(center_lambda - bandwidth_lambda/2); % THz
f_fwhm = f_large - f_small;
%f_fwhm = c/center_lambda^2*bandwidth_lambda; % in THz
f_0 = f_fwhm/(2*sqrt(log(2)));    % ps; 2*sqrt(log(2))=1.665
center_f = c/center_lambda;
gexpo = 2*gaussexpo;
mult_factor = exp(-(f-center_f).^gexpo/(2*f_0^gexpo));

% Apply the filter in frequency space
output = struct('dt',input.dt,...
                'fields',fft((1-mult_factor).*ifft(input_field)),...
                'rejected_fields',fft(mult_factor.*ifft(input_field)));

