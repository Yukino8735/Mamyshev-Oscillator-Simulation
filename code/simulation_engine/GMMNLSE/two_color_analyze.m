function [field_1,field_2] = two_color_analyze2(t,field)
%TWO_COLOR_ANALYZE is used to find and separate a single two color field
%into their own respective field outputs
% By: Dean Eaton, 2025
%
% Input:
%   t: (N,1); time (ps)
%   field(N,?); the pulse electric field (W)
%               If ? isn't 1, it'll choose the most energetic field
%
% This function takes a two color field in which the colors are separated 
% in time and finds peaks in the time vs intensity plot and then compares 
% these to Gaussian fits to determine the best center of the two peaks to
% rule out noisy peaks and takes the minimum field value between them to
% separate them. Then it will output these as their own field.

%% Frequency domain analyze to find peaks in the plot
[~,mi] = max(sum(abs(field).^2,1));% Selects the most energetic mode
field = field(:,mi);
intensity = abs(field).^2; % Put the plot in terms of time vs intensity 

%% Check against Gaussian fits to ensure proper peak separation
% Define the sum of two Gaussians

gaussian_sum = @(x, t) ...
    x(1) * exp(-((t - x(2)).^2) / (2 * x(3)^2)) + ... % First Gaussian
    x(4) * exp(-((t - x(5)).^2) / (2 * x(6)^2));      % Second Gaussian

% Consider only points above a noise threshold
noise_threshold = 0.0025*max(intensity); % Set a threshold
valid_indices = intensity > noise_threshold; % Valid points above threshold
t_valid = t(valid_indices); % Time points above threshold
intensity_valid = intensity(valid_indices); % Corresponding intensity

% Initial guesses for fitting
[~, max_idx1] = max(intensity_valid(1:floor(end/2)));
[~, max_idx2] = max(intensity_valid(ceil(end/2):end));
center1 = t_valid(max_idx1);
center2 = t_valid(max_idx2 + floor(end/2));
amp1 = max(intensity_valid(1:floor(end/2)));
amp2 = max(intensity_valid(ceil(end/2):end));
initial_guess = [amp1, center1, 5, amp2, center2, 5];

% Define optimization
lb = [0, t_valid(1), 0.1, 0, t_valid(1), 0.1];
ub = [2 * max(intensity_valid), t_valid(end), 10, 2 * max(intensity_valid), t_valid(end), 10];
options = optimoptions('fmincon', 'Display', 'off', 'Algorithm', 'interior-point');
objective = @(x) sum((intensity_valid - gaussian_sum(x, t_valid)).^2);
best_fit_params = fmincon(objective, initial_guess, [], [], [], [], lb, ub, [], options);

% Extract parameters for both Gaussians
fit_params_1 = best_fit_params(1:3);
fit_params_2 = best_fit_params(4:6);

fitted_gaussian_1 = fit_params_1(1) * exp(-((t - fit_params_1(2)).^2) / (2 * fit_params_1(3)^2));
fitted_gaussian_2 = fit_params_2(1) * exp(-((t - fit_params_2(2)).^2) / (2 * fit_params_2(3)^2));
fitted_gaussian_sum = fitted_gaussian_1 + fitted_gaussian_2;

% Identify the Gaussian centers
[~, refined_peak_1_idx] = min(abs(t - fit_params_1(2)));
[~, refined_peak_2_idx] = min(abs(t - fit_params_2(2)));

%% Determine the separation point
largest_peaks = sort([refined_peak_1_idx, refined_peak_2_idx]);
[~,mid_point_index] = min(intensity(largest_peaks(1):largest_peaks(2)));
mid_point_index = mid_point_index+largest_peaks(1)-1;

%% Allow user input for correction
prompt = 'Enter an approximate midpoint time (or press enter to keep auto selection): ';
user_midpoint = input(prompt,'s');
if ~isempty(user_midpoint)
    user_midpoint = str2double(user_midpoint);
    if ~isnan(user_midpoint) && user_midpoint >= t(1) && user_midpoint <= t(end)
        [~, mid_point_index] = min(abs(t - user_midpoint));
    else
        warning('Invalid input, keeping automatic midpoint selection.');
    end
end

%% Plotting for verification
figure;
plot(t, intensity, 'b', 'LineWidth', 1.5, 'DisplayName', 'Intensity');
hold on;
plot(t, fitted_gaussian_sum, 'r-', 'LineWidth', 2, 'DisplayName', 'Fitted Gaussian Sum');
plot(t, fitted_gaussian_1, 'g--', 'LineWidth', 1.5, 'DisplayName', 'Gaussian 1');
plot(t, fitted_gaussian_2, 'm--', 'LineWidth', 1.5, 'DisplayName', 'Gaussian 2');
scatter(t(mid_point_index), intensity(mid_point_index), 50, 'k', 'filled', 'DisplayName', 'Separation Point');
xlabel('Time (ps)');
ylabel('Intensity');
title('Intensity, Gaussian Fits, and Separation Point');
legend('Location', 'best');
grid on;
hold off;

%% Applies masks to separate the fields
mask_1 = zeros(size(t));
mask_2 = zeros(size(t));
mask_1(1:mid_point_index) = 1;
mask_2(mid_point_index+1:end) = 1;

field_1 = field.*mask_1; 
field_2 = field.*mask_2;

original_energy = sum(intensity);
separated_energy = sum(abs(field_1).^2) + sum(abs(field_2).^2);
if abs(original_energy - separated_energy) > 1e-2 * original_energy
    warning('Energy conservation failed. Difference: %e', original_energy - separated_energy);
    fprintf('Original Energy: %f, Separated Energy: %f\n', original_energy, separated_energy);
end

end
