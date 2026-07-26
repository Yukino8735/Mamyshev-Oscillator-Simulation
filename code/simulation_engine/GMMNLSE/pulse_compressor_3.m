function [compressed_field] = pulse_compressor_3( compressor_type,optimal_separation,theta_in,wavelength0,time,field,grating_spacing,percentage_to_FTL,varargin )
%PULSE_COMPRESSOR_3 Compresses the pulse to a desired separation of the gratings, 
% with the optimal_separation being the FTL and the percentage_to_FTL is the ratio the separation is adjusted by 
% after differernt grating separations of the compressor from zero to input
%
%   compressor_type: 'Treacy-r': reflective grating pair,
%                    'Treacy-t': transmissive grating pair,
%                    'Treacy-beta2': consider only "beta2" term of a Treacy reflective grating compressor
%                                    (Please refer to Ch.6.2 in Applications of Nonlinear Fiber Optics (2ed), Agrawal)
%                    'Offner1': single-grating Offner compressor
%                               Offner1 is the Offner stretcher with one off-centered grating
%                    'Offner2': double-grating Offner compressor
%                               (Assume the off-center distance of the first grating is known and fixed.
%                                The grating separation is varied for pulse compression here.)
%                               Offner2 is the Offner stretcher with two gratings, one off-center and the other some distance away.
%   theta_in: a scalar; For a grating pair, the incident angle on the grating (rad);
%                       For a prism pair, it's also the Brewster angle (rad)
%   wavelength0: a scalar; central wavelength (nm)
%   time: (N,1); the time grid points (ps)
%   field: (N,1); the electric field in time domain
%   grating_spacing: a scalar; the spacing between each grating line (m)
%   percentage_to_FTL - a scaler that shows the ratio of the separation to
%                       the FTL value
%   Extra required arguments for the Offner compressor:
%
%       R: radius of curvature of the convex mirror (R and 2R for two mirrors; 2R for the concave mirror) (m)
%       offcenter: the off-center distance of the first grating (m)
%
%   Optional arguments:
%
%       m: a scalar; the diffraction order (default: -1)
% =========================================================================
% Use:
%   Treacy:
%      pulse_compressor( compressor_type,theta_in,wavelength0,time,field,grating_spacing,m )
%
%       * compressor_type is either 'Treacy-t', 'Treacy-r', or 'Treacy-beta2'
%       * m is an optional input
%
%   Offner1:
%       pulse_compressor( 'Offner1',theta_in,wavelength0,time,field,grating_spacing,R,m )
%
%       * m is an optional input
%
%   Offner2:
%       pulse_compressor( 'Offner2',theta_in,wavelength0,time,field,grating_spacing,R,offcenter,m )
%
%       * Compared to "Offner1", "offcenter" is required for an input here
%       * m is an optional input

switch compressor_type
    case 'Offner1'
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
optargs = {-1};
% Load paramters
optargs(1:length(varargin)) = varargin;
m = optargs{:};

separation = optimal_separation*percentage_to_FTL;
switch compressor_type
    case {'Treacy-beta2','Treacy-r','Treacy-t'}
        compressed_field = Treacy(compressor_type,separation,theta_in,wavelength0,time,field,grating_spacing,m);
    case 'Offner1'
        compressed_field = Offner(compressor_type,separation,theta_in,wavelength0,time,field,grating_spacing,R,0,m);
    case 'Offner2'
        compressed_field = Offner(compressor_type,separation,theta_in,wavelength0,time,field,grating_spacing,R,offcenter,m);
    otherwise
        error('The value of compressor_type is wrong.');
end

end

%%
function dechirped_field = Treacy(compressor_type,separation,theta_in,wavelength0,time,field,grating_spacing,m)
%GRATING_PAIR

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

% The dechirped pulse
    dechirped_field = Treacy_dechirping(compressor_type,separation,theta_in,theta_out,wavelength,wavelength_c,time,field_w,grating_spacing,m);
 

end

%%
function [field,y] = Treacy_dechirping(compressor_type,separation,theta_in,theta_out,wavelength,wavelength0,time,field_w,grating_spacing,m)
%DECHIRPING It finds the field after propagating through the compressor

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
            grating_phase = pi - m*2*pi*separation*tan(theta_out)/grating_spacing;
        case 'Treacy-t' % transmissive grating pair
            propagation_distance = (separation*1e9)*sec(theta_out).*(1-cos(theta_in-theta_out)); % nm
            grating_phase = -m*2*pi*separation*tan(theta_out)/grating_spacing;
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

y = -separation*tan(theta_out);

end

%%
function dechirped_field = Offner(compressor_type,separation,theta_in,wavelength0,time,field,grating_spacing,R,offcenter,m)
%GRATING_PAIR

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


    if compressor_type(end) == '1' % single-grating
        dechirped_field = Offner_dechirping(0,separation,theta_in,theta_out,wavelength,time,field_w,grating_spacing,R,m);
    else % '2', double-grating
        dechirped_field = Offner_dechirping(separation,offcenter,theta_in,theta_out,wavelength,time,field_w,grating_spacing,R,m);
    end

end

%%
function [field,y,concave_leftmost,concave_rightmost,convex_size] = Offner_dechirping(separation,offcenter,theta_in,theta_out,wavelength,time,field_w,grating_spacing,R,m)
%STRETCHING It finds the field after propagating through the compressor

% The light can go out of the grating pairs under certain angles or
% wavelengths, so this part of light is rejected from the compressor.
rejected_part_f = arrayfun(@(x)any(imag(x)),theta_out) | wavelength<0;
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

function f_c = calc_f_c(f,A2_f)

idx = f>0;
f = f(idx);
A2_f = A2_f(idx);

A2_f(A2_f<max(A2_f)/10) = 0; % it's necessary to kill the background

area = trapz(f,A2_f);
f_c = trapz(f,f.*A2_f)./area;

end