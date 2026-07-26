function [P1, p5,...
          opt_deltaZ,success] = backward_RK4IP_rategain_adaptive(sim, gain_rate_eqn,...
                                                                 P0, p5_1,...
                                                                 omegas, dt,...
                                                                 cross_sections_pump,cross_sections,overlap_factor,N_total,FmFnN,GammaN,...
                                                                 dummy_var)
%BACKWARD_RK4IP_RATEGAIN_ADAPTIVE Take one step according to the GMMNLSE, 
%with a gain model solved from rate equations. The gain term is treated as 
%a dispersion term like the normal SM gain we use, instead of a nonlinear 
%term.
%
% A0 - initial field, (N, num_modes) matrix, in the frequency domain in W^1/2
%
% Power_pump_forward - scalar; the power of the co-propagating pump
% Power_pump_backward - scalar; the power of the counter-propagating pump
% Power_ASE_forward - (N,num_modes); the power of the co-propagating ASE
% Power_ASE_backward - (N,num_modes); the power of the counter-propagating ASE
%
% dt - time grid point spacing, in ps
%
% sim.f0 - center frequency, in THz
% sim.sw - 1 includes self-steepening, 0 does not
% sim.deltaZ - small step size, in m
% sim.singe_yes - 1 = single, 0 = double
% sim.gpu_yes - 1 = GPU, 0 = CPU
% sim.SK_factor - SK = SK_factor * fiber.SR
% sim.scalar - scalar or polarized fields
% sim.Raman_model - which Raman model is used
%
% nonlin_const - n2*w0/c, in W^-1 m
% SRa_info.SRa - SRa tensor, in m^-2
% SRa_info.nonzero_midx1234s - required SRa indices in total
% SRa_info.nonzero_midx34s - required (SRa) indices for partial Raman term (only for CPU computation)
% SRb_info.SRb - SRb tensor, in m^-2
% SRb_info.nonzero_midx1234s - required SRb indices in total
% SRb_info.nonzero_midx34s - required (SRb) indices for partial Raman term (only for CPU computation)
% SK_info.SK - SK tensor, in m^2 (unempty if considering polarizaton modes)
% SK_info.nonzero_midx1234s - required SK indices in total (unempty if considering polarizaton modes)
%
% omegas - angular frequencies in 1/ps, in the fft ordering
%
% D_op - dispersion operator for all modes and all small steps, with size (N, num_modes)
%
% haw - isotropic Raman response in the frequency domain
% hbw - anisotropic Raman response in the frequency domain
%
% *Please refer to "gain_info.m" for details.
% gain_rate_eqn
% cross_sections_pump
% cross_sections
% overlap_factor - no unit for fundamental mode and 1/um^2 for multimode
% N_total - (Nx,Nx); the doped ion density; in "1/um^3"
% FmFnN - the integral2(overlap_factor*N_total) for the signal and ASE
% GammaN - the integral2(overlap_factor*N_total) for the pump
% first_backward_before_iterations - 1(true) or 0(false);
%                                    For bi/counter-pumping cases, the first backward propagation doesn't consider the signal fields.
%
% Output:
%
%   A1 - (N, num_modes) matrix with the field at the end of the step, for each mode, in the frequency domain
%   Power_pump_forward - scalar; the power of the co-propagating pump
%   Power_ASE_forward - (N,num_modes); the power of the co-propagating ASE
%   N2 - (Nx,Nx); the ion density of the upper state

% 1) Propagate through the nonlinearity
if isempty(p5_1)
    p5_1 = N_op(sim, gain_rate_eqn,...
                P0,...
                omegas, dt,...
                cross_sections_pump,cross_sections,overlap_factor,N_total,FmFnN,GammaN,...
                dummy_var);
end
p1 = p5_1;
p2 = N_op(sim, gain_rate_eqn,...
          P0+p1*(sim.deltaZ/2),...
          omegas, dt,...
          cross_sections_pump,cross_sections,overlap_factor,N_total,FmFnN,GammaN,...
          dummy_var);
p3 = N_op(sim, gain_rate_eqn,...
          P0+p2*(sim.deltaZ/2),...
          omegas, dt,...
          cross_sections_pump,cross_sections,overlap_factor,N_total,FmFnN,GammaN,...
          dummy_var);
p4 = N_op(sim, gain_rate_eqn,...
          P0+p3*(sim.deltaZ),...
          omegas, dt,...
          cross_sections_pump,cross_sections,overlap_factor,N_total,FmFnN,GammaN,...
          dummy_var);

P1 = P0 + (p1+2*p2+2*p3)*(sim.deltaZ/6) + p4*(sim.deltaZ/6);

% 2) Local error estimate
p5 = N_op(sim, gain_rate_eqn,...
          P1,...
          omegas, dt,...
          cross_sections_pump,cross_sections,overlap_factor,N_total,FmFnN,GammaN,...
          dummy_var);
err = sum(abs((p4-p5)*(sim.deltaZ/10)).^2,1);

% 3) Stepsize control
if isnan(err)
    opt_deltaZ = 0.5*sim.deltaZ;
    success = false;
else
    opt_deltaZ = max(0.5,min(2,0.8*(sim.adaptive_deltaZ.threshold/10/err)^(1/4)))*sim.deltaZ;

    success = err < sim.adaptive_deltaZ.threshold;
end

end

function dPdz = N_op(sim, gain_rate_eqn,...
                          Power_pump_backward,...
                          omegas, dt,...
                          cross_sections_pump,cross_sections,overlap_factor,N_total,FmFnN,GammaN,...
                          dummy_var)
%N_op Calculate dPdz for the backward pump power

new_Power_pump_backward = solve_gain_rate_eqn_RK4IP('backward',sim,gain_rate_eqn,dummy_var,dummy_var,0,Power_pump_backward,dummy_var,dummy_var,omegas,dt,sim.deltaZ,cross_sections_pump,cross_sections,overlap_factor,N_total,FmFnN,GammaN,true );
dPdz = (new_Power_pump_backward - Power_pump_backward)/sim.deltaZ;

end