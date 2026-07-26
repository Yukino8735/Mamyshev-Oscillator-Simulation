function compressed = pulse_compressor2

compressed.pulsecompressor2                     =   @pulsecompressor2;
compressed.Treacy                               =   @Treacy;
compressed.Treacy_dechirping                    =   @Treacy_dechirping;
compressed.Offner                               =   @Offner;
compressed.Offner_dechirping_with_aberration    =   @Offner_dechirping_with_aberration;
compressed.Treacy_calc_max_intensity            =   @Treacy_calc_max_intensity;
compressed.Offner_calc_max_intensity            =   @Offner_calc_max_intensity;
compressed.Treacy_calc_FWHM                     =   @Treacy_calc_FWHM;
compressed.Offner_calc_FWHM                     =   @Offner_calc_FWHM;
compressed.show_result                          =   @show_result;
compressed.calc_f_c                             =   @calc_f_c;


function [optimal_value,dechirped_FWHM,dechirped_field,varargout] = pulse_compressor2( compressor_type,theta_in,wavelength0,time,field,grating_spacing,varargin )
%PULSE_COMPRESSOR Find the optimum grating separation and the corresponding 
%dechirped field after different types of compressors
%
%   compressor_type: 'Treacy-r': reflective grating pair,
%                    'Treacy-t': transmissive grating pair,
%                    'Treacy-beta2': consider only "beta2" term of a Treacy reflective grating compressor
%                                    (Please refer to Ch.6.2 in Applications of Nonlinear Fiber Optics (2ed), Agrawal)
%                    'Offner1': single-grating Offner compressor
%                               Offner1 is the Offner compressor with one off-centered grating
%                    'Offner2': double-grating Offner compressor
%                               (Assume the off-center distance of the first grating is known and fixed.
%                                The grating separation is varied for pulse compression here.)
%                               Offner2 is the Offner compressor with two gratings, one off-center and the other some distance away.
%                    'Offner3': true aberration-free double-grating Offner compressor
%                               Offner3 is the Offner compressor with two gratings, one on-center and the other some distance away.
%   theta_in: a scalar; For a grating pair, the incident angle on the grating (rad);
%                       For a prism pair, it's also the Brewster angle (rad)
%   wavelength0: a scalar; central wavelength (nm)
%   time: (N,1); the time grid points (ps)
%   field: (N,1); the electric field in time domain
%   grating_spacing: a scalar; the spacing between each grating line (m)
%
%   Extra required arguments for the Offner compressor:
%
%       R: radius of curvature of the convex mirror (R and 2R for two mirrors; 2R for the concave mirror) (m)
%       offcenter: the off-center distance of the first grating (m);
%                  required only for 'Offner2'
%
%   Optional arguments:
%
%       verbose: display the result in the command window;
%                true(1) or false(0) (default: false)
%       global_opt: turn on global optimization to find the optimal compression;
%                   This is necessary sometimes if the pulse is messy.
%                   true(1) or false(0) (default: false)
%       m: a scalar; the diffraction order (default: -1)
% =========================================================================
% Use:
%   Treacy:
%      [optimal_separation,dechirped_FWHM,dechirped_field,grating_size,roof_mirror_size] = pulse_compressor( compressor_type,theta_in,wavelength0,time,field,grating_spacing,verbose,global_opt,m )
%
%       * compressor_type is either 'Treacy-t', 'Treacy-r', or 'Treacy-beta2'
%       * grating_size and roof_mirror_size are optional outputs
%       * verbose, global_opt, and m are optional inputs
%
%   Offner1:
%       [optimal_offcenter,dechirped_FWHM,dechirped_field,grating_size,roof_mirror_size,concave_size,convex_size] = pulse_compressor( 'Offner1',theta_in,wavelength0,time,field,grating_spacing,R,verbose,global_opt,m )
%
%       * grating_size, roof_mirror_size, concave_size, convex_size are optional outputs
%       * verbose, global_opt, and m are optional inputs
%
%   Offner2:
%       [optimal_separation,dechirped_FWHM,dechirped_field,grating_size,roof_mirror_size,concave_size,convex_size] = pulse_compressor( 'Offner2',theta_in,wavelength0,time,field,grating_spacing,R,offcenter,verbose,global_opt,m )
%
%       * Compared to "Offner1", "offcenter" is required for an input here
%       * grating_size, roof_mirror_size, concave_size, convex_size are optional outputs
%       * verbose, global_opt, and m are optional inputs
%
%   Offner3:
%       [optimal_separation,dechirped_FWHM,dechirped_field,grating_size,roof_mirror_size,concave_size,convex_size] = pulse_compressor( 'Offner3',theta_in,wavelength0,time,field,grating_spacing,R,verbose,global_opt,m )
%
%       * grating_size, roof_mirror_size, concave_size, convex_size are optional outputs
%       * verbose, global_opt, and m are optional inputs

switch compressor_type
    case {'Offner1','Offner3'}
        R = varargin{1};
        
        if length(varargin) > 1
            varargin = varargin(2:end);
        end
    case 'Offner2'
        R = varargin{1};
        offcenter = varargin{2};
        
        if length(varargin) > 2
            varargin = varargin(3:end);
        end
end

% Default parameters
optargs = {false false -1};
% Load paramters
optargs(1:length(varargin)) = varargin;
[verbose,global_opt,m] = optargs{:};
switch compressor_type
    case {'Treacy-beta2','Treacy-r','Treacy-t'}
        [optimal_separation,dechirped_FWHM,dechirped_field,grating_size,roof_mirror_size] = Treacy(compressor_type,theta_in,wavelength0,time,field,grating_spacing,verbose,m,global_opt);
        optimal_value = optimal_separation;
        varargout = {grating_size,roof_mirror_size};
    case 'Offner1'
        [optimal_offcenter,dechirped_FWHM,dechirped_field,grating_size,roof_mirror_size,concave_size,convex_size] = Offner(compressor_type,theta_in,wavelength0,time,field,grating_spacing,R,0,         verbose,m,global_opt);
        optimal_value = optimal_offcenter;
        varargout = {grating_size,roof_mirror_size,concave_size,convex_size};
    case 'Offner2'
        [optimal_separation,dechirped_FWHM,dechirped_field,grating_size,roof_mirror_size,concave_size,convex_size] = Offner(compressor_type,theta_in,wavelength0,time,field,grating_spacing,R,offcenter,verbose,m,global_opt);
        optimal_value = optimal_separation;
        varargout = {grating_size,roof_mirror_size,concave_size,convex_size};
    case 'Offner3'
        [optimal_separation,dechirped_FWHM,dechirped_field,grating_size,roof_mirror_size,concave_size,convex_size] = Offner(compressor_type,theta_in,wavelength0,time,field,grating_spacing,R,0,        verbose,m,global_opt);
        optimal_value = optimal_separation;
        varargout = {grating_size,roof_mirror_size,concave_size,convex_size};
    otherwise
        error('The value of compressor_type is wrong.');
end

end

%%
function [optimal_separation,dechirped_FWHM,dechirped_field,grating_size,roof_mirror_size] = Treacy(compressor_type,theta_in,wavelength0,time,field,grating_spacing,verbose,m,global_opt)
%TREACY

N = length(time); % the number of time points
dt = abs(time(2)-time(1)); % ps
c = 299792.458; % nm/ps
wavelength = c./((-N/2:N/2-1)'/N/dt + c/wavelength0); % nm
if size(time,1) == 1
    time = time';
end

field_w = fftshift(ifft(field),1); % frequency domain

% Find the center wavelength of the pulse spectrum with its second moment
f = c./wavelength; % THz
f_c = calc_f_c(f,abs(field_w).^2);
wavelength_c = c/f_c;
wavelength = c./(f+f_c-c/wavelength0);
field = field.*exp(1i*2*pi*(f_c-c/wavelength0)*time);
field_w = fftshift(ifft(field),1);

if isequal(compressor_type,'Treacy-beta2')
    theta_out = asin( m*wavelength_c/(grating_spacing*1e9) + sin(theta_in) ); % the transmitted/reflected angle of the -1st order diffraction
else % 'r' and 't'
    theta_out = asin( m*wavelength/(grating_spacing*1e9) + sin(theta_in) ); % the transmitted/reflected angle of the m-th order diffraction
end

find_optimum_compressor_separation = @(d) -Treacy_calc_max_intensity(compressor_type,d,theta_in,theta_out,wavelength,wavelength_c,time,field_w,grating_spacing,m);
find_FWHM = @(d) Treacy_calc_FWHM(compressor_type,d,theta_in,theta_out,wavelength,wavelength_c,time,field_w,grating_spacing,m);

% Run the global optimization process to find the optimal grating separation
% -------------------------------------------------------------------------
min_separation = 0;
max_separation = 1;
GVD_before_dechirping = characterize_spectral_phase(c./wavelength,fftshift(ifft(ifftshift(field(:,1),1)),1),3,false); % consider only the 1st mode
% Obtain the initial guess from the beta2 of a grating compressor.
% This number should be close to the answer already.
initial_guess = GVD_before_dechirping/2/(m^2*wavelength_c^3/(2*pi*c^2*grating_spacing^2)*(1-(-m*(wavelength_c*1e-9)/grating_spacing-sin(theta_in))^2)^(-1.5)*1e-3);
if initial_guess < min_separation
    initial_guess = 0;
elseif ~isreal(initial_guess) % in case that the phase is a mess
    initial_guess = (min_separation+max_separation)/2;
end

% This is the local optimization I used before which might be stuck at
% local minimum if the pulse isn't smooth enough.
option = optimset('TolX',1e-20);
%option = optimset('PlotFcns',@optimplotfval,'TolX',1e-20); % plot the process of optimization
[optimal_separation1,feval1] = fminsearch(find_optimum_compressor_separation,initial_guess,option);
% Because fminsearch is unconstrained method, I set the constrain below.
if optimal_separation1 < min_separation
    optimal_separation1 = min_separation;
end
% Global optimization
if global_opt
    problem = createOptimProblem('fmincon',...
        'objective',find_optimum_compressor_separation,...
        'x0',initial_guess,...
        'lb',min_separation,...
        'options',optimoptions(@fmincon,'Display','off','TolX',1e-20));
    gs = GlobalSearch('MaxTime',60,'NumTrialPoints',130,'NumStageOnePoints',20,'MaxWaitCycle',5,'Display','off');
    %gs = MultiStart('MaxTime',120,'Display','off','UseParallel',true,'StartPointsToRun','bounds-ineqs');
    %[optimal_separation2,feval2] = run(gs,problem,20);
    [optimal_separation2,feval2] = run(gs,problem);
else
    optimal_separation2 = 0;
    feval2 = 0;
end

if feval1 < feval2
    optimal_separation = optimal_separation1;
else
    optimal_separation = optimal_separation2;
end

% The final dechirped pulse
[dechirped_field,y] = Treacy_dechirping(compressor_type,optimal_separation,theta_in,theta_out,wavelength,wavelength_c,time,field_w,grating_spacing,m);
dechirped_FWHM = find_FWHM(optimal_separation); % ps
dechirped_FWHM = dechirped_FWHM*1e3; % fs

tol_range = 1e-3; % 1 mm
if optimal_separation < (min_separation+tol_range)
    warning('The distance of the grating compressor is too small.');
    
    if ~global_opt
        fprintf('Try running with global optimization.\n');
    end
end

dechirped_field_w = fftshift(ifft(dechirped_field),1);

% Minimum size required for the grating and the mirror
I = sum(abs(dechirped_field_w).^2,2);
considered_regime = I > max(I)/1e4 & ~arrayfun(@(x)any(imag(x)),theta_out) & wavelength>0;
if ~isequal(compressor_type,'Treacy-beta2')
    grating_size = max(y(considered_regime)) - min(y(considered_regime));
    roof_mirror_size = grating_size*cos(theta_in);
else
    grating_size = 0;
    roof_mirror_size = 0;
end

% Plot the result, if "verbose" is true.
if verbose
    show_result(compressor_type,time,dechirped_field,optimal_separation,0,dechirped_FWHM,grating_size,roof_mirror_size);
end

% Recover back to the input frequency range
dechirped_field = dechirped_field.*exp(-1i*2*pi*(f_c-c/wavelength0)*time);

end

%%
function [field,y] = Treacy_dechirping(compressor_type,separation,theta_in,theta_out,wavelength,wavelength0,time,field_w,grating_spacing,m)
%TREACY_DECHIRPING It finds the field after propagating through the 
%compressor

% The light can go out of the grating pairs under certain angles or
% wavelengths, so this part of light is rejected from the compressor.
rejected_part_f = imag(theta_out)~=0 | wavelength<0;
rejected_part = rejected_part_f | abs(field_w)<max(abs(field_w(:)))/1e3;
if all(rejected_part)
    error('All the spectral components are rejected with the selected diffractive order.');
end
field_w(rejected_part) = 0;
theta_out(rejected_part_f) = 0;

if ~isequal(compressor_type,'Treacy-beta2')
    switch compressor_type
        case 'Treacy-r' % reflective grating pair
            propagation_distance = (separation*1e9)*sec(theta_out).*(1+cos(theta_in+theta_out)); % nm
            grating_phase = pi + m*2*pi*separation*tan(-theta_out)/grating_spacing;
        case 'Treacy-t' % transmissive grating pair
            propagation_distance = (separation*1e9)*sec(theta_out).*(1-cos(theta_in-theta_out)); % nm
            grating_phase = m*2*pi*separation*tan(-theta_out)/grating_spacing;
    end

    propagation_phase = 2*pi./wavelength.*propagation_distance;
    
    total_phase = zeros(size(propagation_phase));
    total_phase(~rejected_part_f) = mod(2*(propagation_phase(~rejected_part_f)+grating_phase(~rejected_part_f)),2*pi); % "2" accounts for back-and-forth propagation
                                                                                                                 % (~rejected_part) accounts for the light going into the compressor; if this is ignored, "mod" will give error when the input argument isn't real
else % 'beta2'
    c = 299792.458; % nm/ps
    omega = 2*pi*c./wavelength; % 2*pi*THz
    omega0 = feval(@(x) x(1), ifftshift(omega,1));
    phi2 = -m^2*wavelength0^3*(separation*1e9)/(2*pi*c^2*(grating_spacing*1e9)^2)*(1-(-m*wavelength0/(grating_spacing*1e9)-sin(theta_in))^2)^(-1.5);
    total_phase = (phi2/2*(omega-omega0).^2)*2; % "2", at the end, accounts for back-and-forth propagation
end

% Propagate the light through the grating and transform it back to time domain
field = fft( ifftshift(field_w.*exp(1i*total_phase),1) );

% Shift the pulse to the center of the time window
[~,pulse_center] = max(sum(abs(field).^2,2));
index_shift = pulse_center-floor(length(time)/2);
field = double(circshift(field,-index_shift,1));

y = separation*tan(-theta_out);

end

%%
function [optimal_value,dechirped_FWHM,dechirped_field,grating_size,roof_mirror_size,concave_size,convex_size] = Offner(compressor_type,theta_in,wavelength0,time,field,grating_spacing,R,offcenter,verbose,m,global_opt)
%OFFNER

N = length(time); % the number of time points
dt = abs(time(2)-time(1)); % ps
c = 299792.458; % nm/ps
wavelength = c./((-N/2:N/2-1)'/N/dt + c/wavelength0); % nm
if size(time,1) == 1
    time = time';
end

field_w = fftshift(ifft(field),1); % frequency domain

% Find the center wavelength of the pulse spectrum with its second moment
f = c./wavelength; % THz
f_c = calc_f_c(f,abs(field_w).^2);
wavelength = c./(f+f_c-c/wavelength0);
field = field.*exp(1i*2*pi*(f_c-c/wavelength0)*time);
field_w = fftshift(ifft(field),1);

theta_out = asin( m*wavelength/(grating_spacing*1e9) + sin(theta_in) ); % the transmitted/reflected angle of the m-th order diffraction

switch compressor_type(end)
    case '1' % single-grating Offner compressor
        find_optimum_compressor_value = @(o) -Offner_calc_max_intensity(compressor_type,0,o,theta_in,theta_out,wavelength,time,field_w,grating_spacing,R,m);
        find_FWHM = @(o) Offner_calc_FWHM(compressor_type,0,o,theta_in,theta_out,wavelength,time,field_w,grating_spacing,R,m);
    case '2' % double-grating version for the single-grating case
        find_optimum_compressor_value = @(s) -Offner_calc_max_intensity(compressor_type,s,offcenter,theta_in,theta_out,wavelength,time,field_w,grating_spacing,R,m);
        find_FWHM = @(s) Offner_calc_FWHM(compressor_type,s,offcenter,theta_in,theta_out,wavelength,time,field_w,grating_spacing,R,m);
    case '3' % true aberration-free double-grating Offner compressor
        find_optimum_compressor_value = @(s) -Offner_calc_max_intensity(compressor_type,s,0,theta_in,theta_out,wavelength,time,field_w,grating_spacing,R,m);
        find_FWHM = @(s) Offner_calc_FWHM(compressor_type,s,0,theta_in,theta_out,wavelength,time,field_w,grating_spacing,R,m);
end

% Run the global optimization process to find the optimal grating separation
% -------------------------------------------------------------------------
switch compressor_type(end)
    case {'1','2'} % Offner compressor with aberration
        min_value = -R*0.9;
        max_value =  R*0.9;
    case '3' % Offner compressor without aberration
        min_value = -2*R*0.9;
        max_value =  2*R*0.9;
end
initial_guess = 0;

% This is the local optimization I used before which might be stuck at
% local minimum if the pulse isn't smooth enough.
option = optimset('TolX',1e-20);
%option = optimset('PlotFcns',@optimplotfval,'TolX',1e-20); % plot the process of optimization
try
    [optimal_value1,feval1] = fminsearch(find_optimum_compressor_value,0,option);
catch
    optimal_value1 = 0;
    feval1 = 0;
end
% Because fminsearch is unconstrained method, I set the constrain below.
if optimal_value1 < min_value
    optimal_value1 = min_value;
elseif optimal_value1 > max_value
    optimal_value1 = max_value;
end
% Global optimization
if global_opt
    problem = createOptimProblem('fmincon',...
        'objective',find_optimum_compressor_value,...
        'x0',initial_guess,...
        'lb',min_value,'ub',max_value,...
        'options',optimoptions(@fmincon,'Display','off','TolX',1e-20));
    gs = GlobalSearch('MaxTime',60,'NumTrialPoints',130,'NumStageOnePoints',20,'MaxWaitCycle',5,'Display','off');
    %gs = MultiStart('MaxTime',120,'Display','off','UseParallel',true,'StartPointsToRun','bounds-ineqs');
    %[optimal_separation2,feval2] = run(gs,problem,20);
    [optimal_value2,feval2] = run(gs,problem);
else
    optimal_value2 = 0;
    feval2 = 0;
end

if feval1 < feval2
    optimal_value = optimal_value1;
else
    optimal_value = optimal_value2;
end

% The final dechirped pulse
switch compressor_type(end) 
    case '1' % single-grating Offner compressor
        [dechirped_field,y,concave_leftmost,concave_rightmost,convex_size] = Offner_dechirping_with_aberration(0,optimal_value,theta_in,theta_out,wavelength,time,field_w,grating_spacing,R,m);
    case '2' % double-grating version for the single-grating case
        [dechirped_field,y,concave_leftmost,concave_rightmost,convex_size] = Offner_dechirping_with_aberration(optimal_value,offcenter,theta_in,theta_out,wavelength,time,field_w,grating_spacing,R,m);
    case '3' % true aberration-free double-grating Offner compressor
        dechirped_field = Offner_dechirping_no_aberration(optimal_value,theta_in,theta_out,wavelength,field_w,grating_spacing,R,m);
end
dechirped_FWHM = find_FWHM(optimal_value); % ps
dechirped_FWHM = dechirped_FWHM*1e3; % fs

tol_range = 1e-3; % 1 mm
if optimal_value < (min_value+tol_range) || optimal_value > (max_value-tol_range)
    warning('The distance of the grating compressor is too close to the edge of the distance range used in the optimization.');
    
    if ~global_opt
        fprintf('Try running with global optimization.\n');
    end
end

dechirped_field_w = fftshift(ifft(dechirped_field),1);

% Minimum size required for the grating and the mirror
I = sum(abs(dechirped_field_w).^2,2);
considered_regime = I > max(I)/1e4 & ~arrayfun(@(x)any(imag(x)),theta_out) & wavelength>0;
switch compressor_type(end)
    case {'1','2'} % Offner compressor with aberration
        concave1_leftmost = min(concave_leftmost(considered_regime));
        concave1_rightmost = max(concave_leftmost(considered_regime));
        concave2_leftmost = min(concave_rightmost(considered_regime));
        concave2_rightmost = max(concave_rightmost(considered_regime));
        concave_size = {[concave1_leftmost,concave1_rightmost],...
                        [concave2_leftmost,concave2_rightmost]};
        % Minimum size required for the concave mirror
        convex_size = max(convex_size(considered_regime)) - min(convex_size(considered_regime));
        % Minimum size required for the grating
        grating_leftmost = min(y(considered_regime));
        grating_rightmost = max(y(considered_regime));
        grating_size = [grating_leftmost,grating_rightmost];
        roof_mirror_size = grating_size*cos(theta_in);
    case '3' % Offner compressor without aberration
        grating_size = max(optimal_value*tan(theta_out(considered_regime))) - min(optimal_value*tan(theta_out(considered_regime)));
        concave_size = max(2*R*theta_out(considered_regime)) - min(2*R*theta_out(considered_regime));
        convex_size = concave_size/2;
        roof_mirror_size = grating_size*cos(theta_in);
end

% Plot the result, if "verbose" is true.
if verbose
    switch compressor_type(end)
        case '1' % single-grating Offner compressor
            show_result(compressor_type,time,dechirped_field,0,optimal_value,        dechirped_FWHM,grating_size,roof_mirror_size,concave_size,convex_size);
        case '2' % double-grating version for the single-grating case
            show_result(compressor_type,time,dechirped_field,optimal_value,offcenter,dechirped_FWHM,grating_size,roof_mirror_size,concave_size,convex_size);
        case '3' % true aberration-free double-grating Offner compressor
            show_result(compressor_type,time,dechirped_field,optimal_value,0,        dechirped_FWHM,grating_size,roof_mirror_size,concave_size,convex_size);
    end
end

% Recover back to the input frequency range
dechirped_field = dechirped_field.*exp(-1i*2*pi*(f_c-c/wavelength0)*time);

end

%%
function [field,y,concave_leftmost,concave_rightmost,convex_size] = Offner_dechirping_with_aberration(separation,offcenter,theta_in,theta_out,wavelength,time,field_w,grating_spacing,R,m)
%OFFNER_DECHIRPING_WITH_ABERRATION It finds the field after propagating 
%through the Offner compressor

% The light can go out of the grating pairs under certain angles or
% wavelengths, so this part of light is rejected from the compressor.
rejected_part_f = imag(theta_out)~=0 | wavelength<0;
rejected_part = rejected_part_f | abs(field_w)<max(abs(field_w(:)))/1e3;
if all(rejected_part)
    error('All the spectral components are rejected with the selected diffractive order.');
end
field_w(rejected_part) = 0;
theta_out(rejected_part_f) = 0;

theta_diff = theta_in - theta_out;
theta = asin(-offcenter/2/R*cos(theta_diff));
psi = asin(-offcenter/R*cos(theta_diff));
delta = psi - 2*theta;

l1 = 2*R*(cos(theta)+tan(theta_diff).*sin(theta));
l2 = R*(2*cos(theta)-cos(psi));
tmp = 2*(l2.*sin(psi)-l1.*sin(delta));
x = tmp./(cos(delta).*cot(delta-theta_out)-sin(delta));
y = tmp./(cos(delta-theta_out)-tan(delta).*sin(delta-theta_out));

tmp2 = 2*(delta+theta_diff-pi/2);
theta1 = 2*theta_in-theta_out-pi/2-tmp2;
theta2 = theta_diff-tmp2;
delta_l = separation*csc(theta1).*cos(theta2);

propagation_distance = 2*(l1+l2)-x-y.*sin(theta_in)+delta_l; % m
% The difference between the transmissive and reflective grating pairs,
% the only difference is an extra "pi" phase which doesn't affect the analysis here.
grating_phase = -m*2*pi*y/grating_spacing;

propagation_phase = 2*pi./wavelength.*propagation_distance*1e9;

total_phase = zeros(size(propagation_phase));
total_phase(~rejected_part_f) = mod(2*(propagation_phase(~rejected_part_f)+grating_phase(~rejected_part_f)),2*pi); % "2" accounts for back-and-forth propagation
    
% Propagate the light through the grating and transform it back to time domain
field = fft( ifftshift(field_w.*exp(1i*total_phase),1) );

% Shift the pulse to the center of the time window
[~,pulse_center] = max(sum(abs(field).^2,2));
index_shift = pulse_center-floor(length(time)/2);
field = double(circshift(field,-index_shift,1));

% The leftmost and rightmost positions on the concave mirror
% Below are to compute the minimum size required for a concave mirror
phi = theta_diff-pi/2-theta;
phi2 = psi-theta+phi;
phi3 = (psi-theta)*2+phi;
concave_leftmost = 2*R*phi;
concave_rightmost = 2*R*phi3;
% Below is to compute the minimum size required for a convex mirror
convex_size = R*phi2;

end

%%
function field = Offner_dechirping_no_aberration(separation,theta_in,theta_out,wavelength,field_w,grating_spacing,R,m)
%OFFNER_DECHIRPING_NO_ABERRATION It finds the field after propagating 
%through the aberration-free double-grating Offner compressor

if separation < 2*R
    % The light can go out of the grating pairs under certain angles or
    % wavelengths, so this part of light is rejected from the compressor.
    rejected_part = imag(theta_out)~=0 | wavelength<0;
    if all(rejected_part)
        error('All the spectral components are rejected with the selected diffractive order.');
    end
    
    original_energy = sum(abs(field_w).^2,1);
    field_w(rejected_part) = 0;
    updated_energy = sum(abs(field_w).^2,1);
    theta_out(rejected_part) = 0;
    
    if abs(updated_energy/original_energy - 1) < 0.05
        x = separation*sec(-theta_out);
        phi = -theta_out - (pi/2 - theta_in);

        propagation_distance = -x.*(1+sin(phi)); % m
        % The difference between the transmissive and reflective grating pairs,
        % the only difference is an extra "pi" phase which doesn't affect the analysis here.
        grating_phase = -m*2*pi*(separation*tan(-theta_out))/grating_spacing;

        propagation_phase = 2*pi./wavelength.*propagation_distance*1e9;

        total_phase = zeros(size(propagation_phase));
        total_phase(~rejected_part) = mod(2*(propagation_phase(~rejected_part)+grating_phase(~rejected_part)),2*pi); % "2" accounts for back-and-forth propagation

        % Propagate the light through the grating and transform it back to time domain
        field = fft( ifftshift(field_w.*exp(1i*total_phase),1) );

       % Shift the pulse to where it was before
        field0 = fft( ifftshift(field_w,1) );
        [~,pulse_center0] = max(abs(field0));
        [~,pulse_center] = max(abs(field));
        index_shift = pulse_center - pulse_center0;
        field = double(circshift(field,-index_shift,1));
    else
        field = fft( ifftshift(field_w,1) );
    end
else
    field = fft( ifftshift(field_w,1) );
end

end

%%
function max_intensity = Treacy_calc_max_intensity(compressor_type,separation,theta_in,theta_out,wavelength,wavelength0,time,field_w,grating_spacing,m)
%TREACY_CALC_MAX_INTENSITY

field = Treacy_dechirping(compressor_type,separation,theta_in,theta_out,wavelength,wavelength0,time,field_w,grating_spacing,m);

max_intensity = max(sum(abs(field).^2,2));

end

function max_intensity = Offner_calc_max_intensity(compressor_type,separation,offcenter,theta_in,theta_out,wavelength,time,field_w,grating_spacing,R,m)
%OFFNER_CALC_MAX_INTENSITY

switch compressor_type(end)
    case {'1','2'} % Offner compressor with aberration
        field = Offner_dechirping_with_aberration(separation,offcenter,theta_in,theta_out,wavelength,time,field_w,grating_spacing,R,m);
    case '3'  % Offner compressor without aberration
        field = Offner_dechirping_no_aberration(separation,theta_in,theta_out,wavelength,field_w,grating_spacing,R,m);
end
max_intensity = max(sum(abs(field).^2,2));

end

%%
function FWHM = Treacy_calc_FWHM(compressor_type,separation,theta_in,theta_out,wavelength,wavelength0,time,field_w,grating_spacing,m)
%TREACY_CALC_FWHM It finds the FWHM

field = Treacy_dechirping(compressor_type,separation,theta_in,theta_out,wavelength,wavelength0,time,field_w,grating_spacing,m);

I = sum(abs(field).^2,2);
threshold = max(I)/1.0001;
[~,~,FWHM,~] = findpeaks(I,time,'MinPeakHeight',threshold,'WidthReference','halfheight','MinPeakProminence',threshold/2);
FWHM = FWHM(1); % just in case the pulse is dechirped so badly that it has many peaks and is thus outputed many FWHMs

end

function FWHM = Offner_calc_FWHM(compressor_type,separation,offcenter,theta_in,theta_out,wavelength,time,field_w,grating_spacing,R,m)
%OFFNER_CALC_FWHM It finds the FWHM

switch compressor_type(end)
    case {'1','2'} % Offner compressor with aberration
        field = Offner_dechirping_with_aberration(separation,offcenter,theta_in,theta_out,wavelength,time,field_w,grating_spacing,R,m);
    case '3' % Offner compressor without aberration
        field = Offner_dechirping_no_aberration(separation,theta_in,theta_out,wavelength,field_w,grating_spacing,R,m);
end

I = sum(abs(field).^2,2);
threshold = max(I)/1.0001;
[~,~,FWHM,~] = findpeaks(I,time,'MinPeakHeight',threshold,'WidthReference','halfheight','MinPeakProminence',threshold/2);
FWHM = FWHM(1); % just in case the pulse is dechirped so badly that it has many peaks and is thus outputed many FWHMs

end

%%
function show_result(compressor_type,time,dechirped_field,separation,offcenter,dechirped_FWHM,grating_size,roof_mirror_size,varargin)
%SHOW_RESULT

if contains(compressor_type,'Offner')
    concave_size = varargin{1};
    convex_size = varargin{2};
end

time = time*1e3; % fs
intensity = sum(abs(dechirped_field).^2,2);

% Plot only the central part of the time window
intensity_plot = intensity;
threshold_factor = 100;
intensity_plot(intensity<max(intensity)/threshold_factor) = 0;
left = find(intensity_plot~=0,1);
right = find(intensity_plot~=0,1,'last');
center = floor((left+right)/2);
span_factor = 2;
span = floor((right-left)/2)*span_factor;
left = max(1,floor(center-span));
right = min(length(time),ceil(center+span));

figure('Name','Dechirped pulse');
h = plot(time(left:right),intensity(left:right));
xlim([min(time(left:right)) max(time(left:right))]);
xlabel('Time (fs)');
ylabel('Power (W)');
title('Dechirped pulse');

set(h,'linewidth',2);
set(gca,'fontsize',14);

fprintf('the shortest FWHM = %6.4f(fs)\n',dechirped_FWHM);
switch compressor_type
    case {'Treacy-t','Treacy-r'} % Treacy compressor
        fprintf('Grating separation = %6.4f(cm)\n',separation*100);
        fprintf('Minimum size of the grating = %6.4f(cm)\n',grating_size*100);
        fprintf('Minimum size of the mirror = %6.4f(cm)\n',roof_mirror_size*100);
    case {'Offner1','Offner2'} % Offner compressor with aberration
        if compressor_type(end) == '1' % single-grating Offner compressor
            fprintf('Grating offcenter = %6.4f(cm)\n',offcenter*100);
        else % '2', double-grating version for the single-grating case
            fprintf('Grating separation = %6.4f(cm)\n',separation*100);
        end
        fprintf('(1) Light position on the grating = %6.4f ~ %6.4f(cm)\n',grating_size(1)*100,grating_size(2)*100);
        fprintf('--> Minimum size = %6.4f(cm)\n',(grating_size(2)-grating_size(1))*100);
        fprintf('(2) Light position on the concave mirror 1 = %6.4f ~ %6.4f(cm)\n',concave_size{1}(1)*100,concave_size{1}(2)*100);
        fprintf('--> Minimum size = %6.4f(cm)\n',(concave_size{1}(2)-concave_size{1}(1))*100);
        fprintf('(3) Light position on the concave mirror 2 = %6.4f ~ %6.4f(cm)\n',concave_size{2}(1)*100,concave_size{2}(2)*100);
        fprintf('--> Minimum size = %6.4f(cm)\n',(concave_size{2}(2)-concave_size{2}(1))*100);
        fprintf('(4) Size of the convex mirror = %6.4f(cm)\n',convex_size*100);
    case 'Offner3' % true aberration-free double-grating Offner compressor
        fprintf('Grating separation = %6.4f(cm)\n',separation*100);
        fprintf('Minimum size of the grating = %6.4f(cm)\n',grating_size*100);
        fprintf('Minimum size of the mirror = %6.4f(cm)\n',roof_mirror_size*100);
        fprintf('Minimum size of the concave mirror = %6.4f(cm)\n',concave_size*100);
        fprintf('Minimum size of the convex mirror = %6.4f(cm)\n',convex_size*100);
end

end

function f_c = calc_f_c(f,A2_f)

idx = f>0;
f = f(idx);
A2_f = A2_f(idx);

A2_f(A2_f<max(A2_f)/10) = 0; % it's necessary to kill the background

area = trapz(f,A2_f);
f_c = trapz(f,f.*A2_f)./area;

end

end