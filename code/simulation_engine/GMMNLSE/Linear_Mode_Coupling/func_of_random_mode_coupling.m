function func = func_of_random_mode_coupling
%FUNC_OF_LINEAR_MODE_COUPLING It includes several functions related to
%random mode coupling used in "GMMNLSE_propagate.m"

func.rmc_check = @rmc_check; % check the random mode coupling input

func.rmc_Manakov_kappa = @rmc_Manakov_kappa; % calculate Manakov nonlinear coefficients

func.Manakov_dispersion_operator = @Manakov_dispersion_operator; % calculate the dispersion operator for linear mode coupling

end

%%
function rmc_check(sim)
%rmc_CHECK Check the random mode coupling inputs

% Check the random mode coupling inputs
if sim.rmc.model == 1
    if ~sim.gpu_yes
        error('GMMNLSE_propagate:gpuError',...
              'GPU is required for the iQA model of random mode coupling.');
    end
    
    if length(sim.midx) > 1 % more than one spatial mode
        if ~isfield(sim.rmc,'Lcoup_spatialmode') || isempty(sim.rmc.Lcoup_spatialmode)
            error('GMMNLSE_propagate:rmc_lengthError',...
                '"Lcoup_spatialmode" matrix for rmc_model=2 (iQA model) is required.');
        else
            num_mode_groups = length(sim.rmc.mode_groups);
            if ~isequal(size(sim.rmc.Lcoup_spatialmode),[num_mode_groups,num_mode_groups])
                error('GMMNLSE_propagate:rmc_lengthError',...
                    'The size of "sim.rmc.Lcoup_spatialmode" should be [num_mode_groups,num_mode_groups].');
            end
            if ~issymmetric(sim.rmc.Lcoup_spatialmode)
                error('GMMNLSE_propagate:rmc_lengthError',...
                    '"sim.rmc.Lcoup_spatialmode" needs to be symmetric.');
            end
        end
    end
end

end

%%
function [kappaK,kappaR1,kappaR2] = rmc_Manakov_kappa( sim,num_modes,mode_info,SK_info )
%rmc_MANAKOV_KAPPA Calculate Manakov nonlinear coefficients

% Manakov equation always considers polarizations, which affects SRSK
% and the following nonlinear coefficients, kappaK, kappaR1, kappaR2.
%
% mode_groups_all and num_modes_all both considers polarization modes if necessary.
mode_groups_all = 2*sim.rmc.mode_groups;
if sim.scalar
    num_modes_all = num_modes*2;
else
    num_modes_all = num_modes;
end
mode_group_idx_all = mat2cell(1:num_modes_all,1,mode_groups_all); % the index of modes in each mode group including polarization modes if running under polarized fields

% Recover SR,SK back to 4D array for "Manakov_SRSK"
if sim.gpu_yes
    if sim.single_yes
        SR = zeros(num_modes_all,num_modes_all,num_modes_all,num_modes_all,'single','gpuArray');
        SK = zeros(num_modes_all,num_modes_all,num_modes_all,num_modes_all,'single','gpuArray');
    else
        SR = zeros(num_modes_all,num_modes_all,num_modes_all,num_modes_all,'gpuArray');
        SK = zeros(num_modes_all,num_modes_all,num_modes_all,num_modes_all,'gpuArray');
    end
else
    if sim.single_yes
        SR = zeros(num_modes_all,num_modes_all,num_modes_all,num_modes_all,'single');
        SK = zeros(num_modes_all,num_modes_all,num_modes_all,num_modes_all,'single');
    else
        SR = zeros(num_modes_all,num_modes_all,num_modes_all,num_modes_all);
        SK = zeros(num_modes_all,num_modes_all,num_modes_all,num_modes_all);
    end
end
% SR
SRidx = sub2ind(num_modes_all*ones(1,4),mode_info.nonzero_midx1234s(1,:),mode_info.nonzero_midx1234s(2,:),mode_info.nonzero_midx1234s(3,:),mode_info.nonzero_midx1234s(4,:));
SR(SRidx') = mode_info.SRa;
% SK
SKidx = sub2ind(num_modes_all*ones(1,4),SK_info.nonzero_midx1234s(1,:),SK_info.nonzero_midx1234s(2,:),SK_info.nonzero_midx1234s(3,:),SK_info.nonzero_midx1234s(4,:));
SK(SKidx') = SK_info.SK;

% Compute the Manakov nonlinear coefficients, kappaK, kappaR1, kappaR2.
[kappaK,kappaR1,kappaR2] = Manakov_SRSK(SR,SK,mode_group_idx_all,sim);

end

%%
function D0_op = Manakov_dispersion_operator( sim,D0_op,num_modes,N,mode_groups )
%rmc_DISPERSION_OPERATOR Calculate the dispersion operator for Manakov
%equations
%
% For Manakov equations, dispersion term is averaged in each mode group.

if sim.gpu_yes % "mg" stands for "mode group"
    if sim.single_yes
        D0_op_mg = zeros(N,num_modes,'single','gpuArray');
    else
        D0_op_mg = zeros(N,num_modes,'gpuArray');
    end
else
    if sim.single_yes
        D0_op_mg = zeros(N,num_modes,'single');
    else
        D0_op_mg = zeros(N,num_modes);
    end
end
for mg = 1:length(mode_groups)
    if sim.scalar
        D0_op_mg(:,mode_groups{mg}) = mean(D0_op(:,mode_groups{mg}),2).*ones(1,sim.rmc.mode_groups(mg));
    else
        D0_op_mg(:,mode_groups{mg}) = mean(D0_op(:,mode_groups{mg}),2).*ones(1,sim.rmc.mode_groups(mg)*2);
    end
end
D0_op = D0_op_mg;

end