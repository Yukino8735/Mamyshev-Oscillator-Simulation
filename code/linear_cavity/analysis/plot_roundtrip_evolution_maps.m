clear; clc; close all;

script_dir = fileparts(mfilename('fullpath'));
code_dir = fileparts(fileparts(script_dir));
addpath(code_dir);
[project_root, ~] = setup_mamyshev_project();

generated_data_dir = fullfile(project_root, 'data', ...
    'linear_cavity', 'evolution_generated');
archived_data_dir = fullfile(project_root, 'data', ...
    'linear_cavity', 'evolution');
out_dir = fullfile(project_root, 'results', ...
    'linear_cavity', 'evolution_generated');
if ~isfolder(out_dir)
    mkdir(out_dir);
end

% 你已经跑过并保存的功率文件
file_list = { ...
    'evolution_P3p00W.mat', ...
    'evolution_P4p00W.mat', ...
    'evolution_P5p00W.mat', ...
    'evolution_P6p00W.mat', ...
    'evolution_P7p00W.mat'};

ncase = numel(file_list);

stable_rt_all = nan(ncase,1);
pump_all = nan(ncase,1);
status_all = strings(ncase,1);

figure('Color','w','Position',[80 80 1200 700]);
tiledlayout(2, ceil(ncase/2), 'TileSpacing', 'compact', 'Padding', 'compact');

for k = 1:ncase
    data_file = fullfile(generated_data_dir, file_list{k});
    if ~isfile(data_file)
        data_file = fullfile(archived_data_dir, file_list{k});
    end
    S = load(data_file);

    pump_all(k) = S.PumpPower;

    % 提取每一圈的时域强度
    % output_field size usually: Nt x 1 x Nrt
    E = S.output_field;
    nrt = min(S.rt_num, size(E,3));
    E = E(:,:,1:nrt);
    energy_rt = S.output_energy(1:nrt);
    if ndims(E) == 3
        I = squeeze(abs(E(:,1,:)).^2);   % Nt x Nrt
    else
        I = abs(E).^2;
    end

    % 如果是多模，改成 sum over mode，这里你当前单模所以直接这样即可
    % I = squeeze(sum(abs(E).^2, 2));  % Nt x Nrt

    % 每张图归一化，便于看演化
    I = I ./ max(I(:) + eps);

    % 估计第几圈稳定
    [stable_rt, status_str] = estimate_stable_rt(I, energy_rt);
    stable_rt_all(k) = stable_rt;
    status_all(k) = status_str;

    nexttile;
    imagesc(S.t, 1:size(I,2), I.');
    axis xy;
    xlabel('Time / ps');
    ylabel('Round trip');
    title(sprintf('Pump = %.2f W, %s', S.PumpPower, status_str));
    colormap(turbo);
    colorbar;
    caxis([0 1]);
end

exportgraphics(gcf, fullfile(out_dir, 'roundtrip_evolution_maps.png'), 'Resolution', 300);

%% Summary figure: stable round trip vs pump power
figure('Color','w','Position',[200 200 700 450]);
hold on; box on; grid on;

for k = 1:ncase
    if status_all(k) == "stable"
        plot(pump_all(k), stable_rt_all(k), 'o', 'MarkerSize', 8, 'LineWidth', 1.5);
    elseif status_all(k) == "unstable"
        plot(pump_all(k), stable_rt_all(k), 's', 'MarkerSize', 8, 'LineWidth', 1.5);
    elseif status_all(k) == "dies"
        plot(pump_all(k), stable_rt_all(k), 'x', 'MarkerSize', 10, 'LineWidth', 1.8);
    end
end

xlabel('Pump power / W');
ylabel('Round trip to stability');
title('Round-trip number required for pulse stabilization');
legend('stable','unstable','dies','Location','best');

exportgraphics(gcf, fullfile(out_dir, 'stability_roundtrip_vs_pump.png'), 'Resolution', 300);

%% ===== local function =====
function [stable_rt, status_str] = estimate_stable_rt(I, energy_rt)
% I: Nt x Nrt normalized intensity map
% energy_rt: Nrt x 1 output pulse energy per round trip

    nrt = size(I,2);

    % 如果最后能量太低，认为脉冲死掉
    if isempty(energy_rt) || max(energy_rt) < 1e-3 || energy_rt(end) < 1e-2
        stable_rt = nrt;
        status_str = "dies";
        return;
    end

    % 判断稳定：连续若干圈变化都很小
    tol_energy = 2e-3;      % relative energy fluctuation
    tol_shape  = 5e-3;      % normalized pulse-shape difference
    need_consecutive = 3;   % 连续3圈满足才算稳定

    flag = false(nrt,1);

    for m = 2:nrt
        prev = I(:,m-1);
        curr = I(:,m);

        % 归一化，比较形状
        prev = prev / max(sum(prev), eps);
        curr = curr / max(sum(curr), eps);

        dshape = norm(curr - prev) / max(norm(curr), eps);
        dE = abs(energy_rt(m) - energy_rt(m-1)) / max(abs(energy_rt(m)), eps);

        if dshape < tol_shape && dE < tol_energy
            flag(m) = true;
        end
    end

    stable_rt = NaN;
    for m = need_consecutive+1:nrt
        if all(flag(m-need_consecutive+1:m))
            stable_rt = m - need_consecutive + 1;
            break;
        end
    end

    if isnan(stable_rt)
        stable_rt = nrt;
        status_str = "unstable";
    else
        status_str = "stable";
    end
end
