# Phase 2：波形平稳性诊断与固定20圈观察

2026-09-27本地／2026-09-28 UTC。本批诊断、控制测试及唯一真实尝试已结束，等待审核。

**第6圈的能量停止，不足以作为本次波形平稳性观察的结束依据。**
旧6圈第6对第5圈整体平移后仍有2.28386%的强度相对L2差、2.66038%的光谱强度差。
本次延长观察的前1–6圈复场和原能量与旧记录精确一致；后续变化没有持续消失。
第20对第19圈对齐残差2.70599%、光谱差4.30622%；第20对第6圈对齐残差2.37241%、
光谱差3.37163%。这些描述没有给出稳定／不稳定阈值，不构成stable_single、breathing或多脉冲真值。

**真实后端返回了20圈、尾纤与同次压缩结果，但本次最终记录链路未通过。** MATLAB退出0，
candidate为completed／observation_budget_reached；既有监控器在所属进程组清理时发生
PermissionError，runner为failed、cleanup_verified=false，CLI退出1，父进程final缺失。
下文新波形和candidate一律是**事后诊断证据，不是成功final结果**。未修复重跑、重合并或补写final。

Phase 2仍为in_progress；physical_state=undetermined，numerical_validation=not_verified，
eligible_as_validated_training_truth=false。20圈不替代网格、窗口、步长独立收敛，H02及随机鲁棒性仍未验证。

## 范围、身份与最小改动

读取适用AGENTS、EXECUTION_STATUS、上一批配置/波形报告和实际生产入口、捕获、记录器、
监控器、判据及测试源码。AGENTS旧阶段授权由本条明确指令覆盖。没有重做环境、H01审计或运行平台。
本机Darwin/arm64；保持feature/mamyshev-ml-mvp，基础commit
489bf4242f9b5266d47f8892840a24af66931ff0和原有未提交修改。起点2038份文件哈希见
`reports/local/phase2/stationarity_001/review_start.json`。

启动冻结255个源码/配置/测试文件，摘要
`c5f9d4bd61fa26a25d0b6f3bab4dc211252f2afcb51206b3693155f8fefe3505`。
这是本批新身份，未把旧244项清单改写成新版本；实际运行期间没有修改参与身份核验的文件。
完整请求、命令、冻结规则及起点差异见本机`launch_freeze.json`与真实目录`launch_request.json`。

| 本批修改的已有文件 | 作用 |
|---|---|
| code/ring_cavity/scans/run_mamyshev.m | 独立观察选项；保留原更新和判据，记录逐圈布尔值，调用停止决策 |
| code/ml_bridge/MamyshevCapture.m | B实际观察选项及C逐圈history/首次旧收敛圈 |
| code/ml_bridge/run_mamyshev_recorded.m、mamyshev_result_record.m | 选项传递、保留真实观察停止原因和旧布尔值 |
| code/ml_bridge/launch_mamyshev_once.m | 核对唯一授权批次、预算与独立观察选项 |
| scripts/run_mamyshev_once.py | 本批显式3600秒/fixed20参数；原900/1800默认与批次限制不变 |
| src/mamyshev_ml/supervisor.py | A→B→C→candidate观察history/停止原因gate；失败优先不变 |
| scripts/analyze_mamyshev_waveforms.m | opt-in部分/失败记录只读分析，不恢复失败final指标 |
| tests/test_once_launcher.py、tests/run_matlab_short.py | 针对性参数测试；已有短测监控器增加本批300秒总额 |

新增正常源码：`code/ring_cavity/scans/mamyshev_observation_options.m`、
`mamyshev_observation_decision.m`；`scripts/mamyshev_intensity_alignment.m`、
`analyze_mamyshev_stationarity.m`；`configs/phase2_stationarity_protocol.json`；
`tests/test_observation_supervisor.py`；`tests/matlab/test_observation_control.m`、
`test_stationarity_analysis.m`、`run_stationarity_controls.m`、`run_stationarity_existing.m`、
`run_stationarity_observation.m`。另新增本报告并更新EXECUTION_STATUS；详细产物仅位于新的本机目录。

四维design_config仍恰好为4 W、offset10 nm、SF2带宽3 nm、增益4 m四个字段。
Nt32768、50 ps、max_rt50、原步长/容差/保存设置、seed0/twister、原初场和随机开关不变。
三段无源0.4/1.5/3.2 m、尾纤0.2 m、1-H端口、滤波公式、增益材料和N_total覆盖、
MFD/SR及压缩器假设均未改。H02仍是声明MFD10.5与实际SR派生来源5.95的不一致，未重算SR。
GMMNLSE传播/增益数值正文、check_convergence本体、pulse_tracker、波形writer及压缩器未在本批修改。

## 观察协议及控制分支

```matlab
% 独立于四维design_config；省略时仍为legacy
observation_options = struct('observation_mode','fixed_roundtrips', ...
                            'observation_roundtrips',20);
% 每圈继续调用原check_convergence，包括H04和真实有效圈数
[converged,force_stop_yes,~,criterion_diagnostic] = check_convergence(...);
% 完成该圈原状态更新及pre/post保存后，才作观察停止决策
decision = mamyshev_observation_decision(observation_options, ...);
```

options拒绝未知/缺失字段、模式冲突、布尔、非有限、非整数或超过实际max_rt的圈数。
`run_mamyshev.m:321`/`:324`继续执行原判据，`:353`以后只改变停止接线。
默认legacy顺序保持converged→force.convergence→死亡；fixed模式只跳过前两种收敛停止，
死亡优先于非收敛force.fluctuation，再检查20圈预算。数值错误、H04非有限、无进展保护、
外部STOP/timeout保留。原caller没有使用force.fluctuation；fixed将其作为非收敛安全停止，
没有修改判据计算或把该分支当作收敛绕过。其实际触发与否单独记录。

原动态t_rep、循环入场、泵和自适应步长继续更新；第6圈没有尾纤/压缩后再继续腔体。
实际第1–5圈criterion_reason=insufficient_history；第6–20圈均energy_converged，
两种force标志均false。首次旧能量判据满足=6；第1–19圈实际stop_reason为空，
第20圈=observation_budget_reached。末圈converged=true、ML_state=1如实保留，未改成false，
也未翻译为稳定性收敛或stable_single。

`MamyshevCapture.m:122`核对请求与实际B，`:142`记录实际逐圈C；
`supervisor.py:424`起检查A/B/C/candidate选项、连续history、首次旧收敛、死亡原能量、
布尔标志与停止优先级。旧无观察选项路径保留旧gate。STOP、一次锁、拒绝覆盖、所属组清理和父进程final独占均复用。

## 测试与预算

| 类型 | 实际执行范围 |
|---|---|
| 新分析人工fixture | 9组通过：相同场、纯整体移位、等能量形变、周期/多峰/近并列/平坦歧义、固定参考与末5圈、主半高区、失败及零圈诊断、RNG不变；0传播 |
| 新观察控制 | 8组通过：legacy兼容、只跳过收敛、安全优先、20圈预算、原H04、请求到实际选项和结果契约；其中1次真实初始化、0传播 |
| 复用MATLAB回归 | convergence_safety20组、result_contract20组、wrapper_readiness11组通过；人工20次能量判据和10次synthetic包装调用不是物理仿真 |
| Python | 55个不同方法通过：18新增、37已有；先前14方法开发重复不增加独立数；4套件合计约2.049秒，不含Conda启动 |
| 旧真实6圈离线复核 | 55项保存场/单位/标量检查通过；不是fixture、不是新传播 |
| 新真实保存数据离线复核 | 146项保存场/能量/Parseval/历史一致性通过；7项与父final标量比较not_verified（final缺失）；前缀6组全部通过 |

人工fixture、无传播初始化、真实唯一尝试与离线分析分别计数，没有新增物理设计或训练样本。
原有H01/第三方全套没有重复执行，未额外启动MATLAB preflight。
真实尝试之外共3个串行MATLAB短进程：

| 短进程 | 外部墙钟(s) | 结果 |
|---|---|---|
| existing_analysis_001 | 26.171164291 | completed / exit0；cleanup_verified=true |
| controls_001 | 9.739364500 | completed / exit0；cleanup_verified=true |
| observation_analysis_001 | 21.793061583 | completed / exit0；cleanup_verified=true |

短测、初始化及新旧MAT分析合计**57.70359037397429 / 300秒**；每个进程均小于180秒。
没有短测重试或额外压缩优化。短测监控器通用kind为synthetic_short_test；两个分析脚本实际读取真实保存MAT，
并不因此变成人工仿真。新离线分析明确run_job_status=missing_final、diagnostic_only=true。

所有Python命令经指定Conda。三个MATLAB短任务均通过同一现有监控器，形式为：

```sh
/opt/homebrew/Caskroom/miniforge/base/bin/conda run -n mamyshev-ml --no-capture-output python   tests/run_matlab_short.py existing_analysis_001 tests/matlab/run_stationarity_existing.m   --batch stationarity_001 --matlab /Applications/MATLAB_R2025a.app/bin/matlab
# 同一前缀/参数的另两个已执行任务：
# controls_001 tests/matlab/run_stationarity_controls.m
# observation_analysis_001 tests/matlab/run_stationarity_observation.m
```

## 唯一真实命令、返回与监控失败

先只读dry-run确认新目录、默认四维、fixed20、3600秒内含30秒预留、最多一次和真实后端；不预留传播。
启动前已冻结前缀及分析规则，没有结果后放宽。唯一真实命令为：

```sh
/opt/homebrew/Caskroom/miniforge/base/bin/conda run -n mamyshev-ml --no-capture-output python scripts/run_mamyshev_once.py --execute-real --run-id observation_001 --batch-id observation_validation_001 --timeout-s 3600 --design-config configs/phase2_config_waveform_default.json --save-waveforms --observation-mode fixed_roundtrips --observation-roundtrips 20 --matlab /Applications/MATLAB_R2025a.app/bin/matlab
```

原始目录：`reports/local/phase2/observation_validation_001/observation_001/`。
真实入口为launch_mamyshev_once→run_mamyshev_recorded→run_mamyshev_config→原run_mamyshev生产循环，
无test_hook、component backend、简化/reproduction入口或恢复checkpoint。

| 事项 | 实际证据 |
|---|---|
| 尝试 | 已预留；1/1已消耗；MATLAB确实启动、进入传播、正常返回 |
| 原始初始化B | 256个物理/数值叶项精确核对通过；观察选项A/B/C一致 |
| 实际路径 | 20圈×4腔段、40次SF1/SF2滤波、终点尾纤一次、原压缩分析一次；81段计数完整 |
| MATLAB/candidate | MATLAB退出0；candidate completed、20圈、observation_budget_reached |
| runner | failed；stop_reason=process_exit；无STOP/timeout事件；cleanup_verified=false |
| supervisor/CLI | SIGKILL清理PermissionError，CLI退出1；supervisor_error.json存在 |
| 父进程final | **不存在**；正常完成及final提交集成验收未通过 |

错误在既有`tests/run_matlab_short.py:86`的`os.killpg(process.pid,SIGKILL)`，
`:143`起捕获并在`:153`写出failed runner，`:155`重新抛出；`supervisor.py:633`的run_isolated未返回，
因此其后候选读取/gate/合并/final提交未执行。supervisor_error的runner=null是赋值未完成，
不是磁盘runner_record缺失。原监控算法未为本批重写，不能因MATLAB退出0就忽略清理错误。

所属组23043在之后成功的只读ps检查中已无成员；未向其他MATLAB会话发送信号。
这个事后现状**不能证明抛错瞬间组已不存在，也不能修正原cleanup_verified=false**。
EPERM究竟来自退出竞态、权限或某成员状态尚未查明，当时进程表未留存；本批不修复重跑。
后续独立纯校验A/B/C、计数、waveform哈希和candidate均无校验错误，但它不是原父进程gate通过，
未调用merge/finalize，未补写final。事后candidate-only的7项标量对照沿用原容差全部通过：
SF1 pre能量差2.84e−14 nJ，其余6项差为0；这不填补原分析的7项final未验证检查。
详细事实见本机`postrun_record_review.json/.md`和`real_cli_exit_error.txt`。

以下计数仅为已完整保存的失败作业诊断，不证明独立数值收敛或随机协议正确：

| 位置 | trial | rejection | accepted_advanced_steps | 完整性 |
|---|---|---|---|---|
| 20个增益段 | 90146 | 48 | 90098 | 全部完整/平衡 |
| 60个无源腔段 | 44867 | 40 | 44827 | 全部完整/平衡 |
| 终点尾纤 | 684 | 2 | 682 | 完整/平衡 |

所有段pending=0，trial=rejection+accepted_advanced_steps，无活动段。48次真实增益拒绝说明本次经过H01相关分支；
无源拒绝不是H01证据，计数不能反推Phase 1误差，也不能把所有输出变化归因于H01。
历史数值修复集合、观察终点及未独立验证的随机协议仍需区分。

## 对齐与能量约定

对每个平面分别取I=sum(abs(A)^2, modes)，计算D=norm(I_current−I_reference)/norm(I_reference)。
参考范数只是相对误差的分母，不是逐圈场/强度归一化。原始D与整体对齐D同时保留。
FFT周期互相关`real(ifft(fft(reference).*conj(fft(current))))`在全窗整数lag上寻找最大值，
对当前强度副本作circshift；正lag表示向正索引移动。区间[-N/2,N/2−1]，时间周期50 ps，
精度dt=0.00152587890625 ps=1.52587890625 fs；没有亚采样插值、平滑、删峰或局部时间变形。
数值tie阈值1e−12×两向量范数积，歧义阈值1e−8×范数积，均启动前固定；tie选最小绝对lag，再选负lag。
若多峰相关近并列则标歧义，实际本次所有适用比较都未标歧义。此整数分辨率不能排除未解析的亚采样时移。

频谱沿原约定fftshift(ifft(A))，PSD=sum(abs(spectrum)^2)×(Ndt)^2/1000，单位nJ/THz；
同一绝对频率网格、df=0.02 THz、f0=289.65454879227053 THz，保留负频率bin，未按各圈峰值或能量重标。
频谱强度相对L2用同样参考范数定义。纯周期整体复场平移应保持频谱强度，实际非零谱差排除了“全是纯平移”的解释，
但不区分物理形变、随机项与尚未独立验证的数值因素；两个L2不能相减当作严格时移/形变分解。

原raw_energy仍为生产pre-tracker trapz积分／1000，单位nJ；post场为生产tracker后的循环移位副本。
周期sum积分与trapz端点规则分别报告，不用post积分替换原能量。边缘各ceil(1%×32768)=328点，
实际各占1.0009765625%的采样区间，能量占比以全窗周期sum为分母。小边缘占比不是窗口或采样收敛证据。

## 旧六圈及共同前缀

旧分析来自原config_waveform_001的真实MAT，先于本次传播完成；没有重算旧传播或压缩。
下表前6行同时就是旧数据的原能量/峰值；新旧每圈pre/post复场最大绝对差=0、原能量差=0，
时间/频率坐标及维度精确一致。先断言有限，再按预声明规则比较：
场maxabs差≤1e−10+1e−10×maxabs(reference)，单位sqrt(W)；
原能量差≤1e−10+1e−10×abs(reference)，单位nJ；不做任何时间/相位/幅值对齐。
6组全部通过；这只是观察选项未提前改变轨迹的软件回归，不是独立收敛或随机鲁棒性证据。
未比较旧六圈终点尾纤/压缩后的RNG与新第6圈腔体结束RNG。

旧第6对第5圈：pre/post原始L2均4.54467%，整体平移+4样本（+6.103516 fs）后2.28386%，
谱差2.66038%；旧末5圈固定2–6，没有单调消失。旧固定第6圈参考只有自比较零值，不能说明后续保持。

## 全部可用圈的诊断值

**以下新20圈数值均为missing_final作业的离线诊断。** 未放入成功final结果表。
所有40条pre/post逐圈记录、完整精度、原积分/周期积分、左右时间/频率边缘、邻圈及固定6参考均在
[per_round.csv](../reports/local/phase2/stationarity_001/observation_analysis_001/observation_rounds/per_round.csv)与
[stationarity.json](../reports/local/phase2/stationarity_001/observation_analysis_001/observation_rounds/stationarity.json)。
旧6圈对应表见
[旧per_round.csv](../reports/local/phase2/stationarity_001/existing_analysis_001/old_six_rounds/per_round.csv)。

原能量未经替换；pre/post峰值相等，因为tracker保持采样值只改变位置。表格做显示舍入，计算使用原double。

| 圈 | 原能量(nJ) | 峰值(W)，pre=post |
|---|---|---|
| 1 | 132.806481837 | 21687.658785 |
| 2 | 128.604327531 | 22796.220770 |
| 3 | 128.728796355 | 22762.512307 |
| 4 | 128.727609476 | 22794.202674 |
| 5 | 128.726487183 | 22786.889713 |
| 6 | 128.719682219 | 22779.272915 |
| 7 | 128.726348296 | 22796.326824 |
| 8 | 128.726861662 | 22787.656802 |
| 9 | 128.726191929 | 22798.246511 |
| 10 | 128.726349237 | 22806.932901 |
| 11 | 128.726814026 | 22791.599736 |
| 12 | 128.726907673 | 22768.116133 |
| 13 | 128.726977656 | 22777.744778 |
| 14 | 128.726964655 | 22755.669199 |
| 15 | 128.726682283 | 22796.317808 |
| 16 | 128.725530568 | 22796.772814 |
| 17 | 128.727329971 | 22750.863204 |
| 18 | 128.728849918 | 22754.227712 |
| 19 | 128.718535132 | 22776.721683 |
| 20 | 128.727029831 | 22786.939841 |

相邻圈：D列单位%，Δt列单位fs；对当前圈施加的整体移位。第一圈没有前圈，null有此原因。
pre/post对齐残差与谱差在下列精度相同，完整的两个值分别保存在CSV/JSON，未混用原始误差或位移。

| 圈 | D原pre % | D原post % | D对齐 % | Δt pre fs | Δt post fs | D谱 % |
|---|---|---|---|---|---|---|
| 1 | null | null | null | null | null | null |
| 2 | 23.37370 | 23.37370 | 12.63328 | +320.434570 | +320.434570 | 9.12909 |
| 3 | 4.51462 | 3.22655 | 0.99204 | -12.207031 | -10.681152 | 3.02135 |
| 4 | 3.91878 | 2.52130 | 0.87149 | -3.051758 | -1.525879 | 0.69240 |
| 5 | 4.55489 | 4.55489 | 0.84432 | +4.577637 | +4.577637 | 1.11875 |
| 6 | 4.54467 | 4.54467 | 2.28386 | +6.103516 | +6.103516 | 2.66038 |
| 7 | 2.71894 | 2.71894 | 2.08343 | -9.155273 | -9.155273 | 2.95640 |
| 8 | 2.50516 | 3.99384 | 0.82467 | -1.525879 | -3.051758 | 0.78080 |
| 9 | 1.90943 | 3.61933 | 1.09631 | +1.525879 | +3.051758 | 0.88363 |
| 10 | 3.43722 | 3.43722 | 0.96060 | -6.103516 | -6.103516 | 0.61877 |
| 11 | 3.64913 | 2.14982 | 0.80569 | -6.103516 | -7.629395 | 0.32882 |
| 12 | 3.78391 | 4.21760 | 0.75411 | -6.103516 | -4.577637 | 0.09880 |
| 13 | 3.62689 | 4.22140 | 0.67785 | -3.051758 | -4.577637 | 0.01300 |
| 14 | 3.78358 | 3.78358 | 0.70562 | +3.051758 | +3.051758 | 0.15601 |
| 15 | 2.40824 | 2.40824 | 0.68630 | +7.629395 | +7.629395 | 0.43242 |
| 16 | 2.90296 | 4.17426 | 0.92840 | +1.525879 | +3.051758 | 0.50535 |
| 17 | 3.68123 | 3.68123 | 1.39583 | -12.207031 | -12.207031 | 1.07142 |
| 18 | 4.17225 | 3.56510 | 0.80352 | -4.577637 | -6.103516 | 0.53218 |
| 19 | 5.76361 | 5.48638 | 2.84030 | +24.414062 | +25.939941 | 4.39690 |
| 20 | 4.94710 | 5.08843 | 2.70599 | -13.732910 | -15.258789 | 4.30622 |

相对固定第6圈：第1–5圈不适用；第6圈零差仅为自比较。两平面对齐残差和谱差在显示精度相同。

| 圈 | D原pre % | D原post % | D对齐 % | Δt pre fs | Δt post fs | D谱 % |
|---|---|---|---|---|---|---|
| 6 | 0.00000 | 0.00000 | 0.00000 | +0.000000 | +0.000000 | 0.00000 |
| 7 | 2.71894 | 2.71894 | 2.08343 | -9.155273 | -9.155273 | 2.95640 |
| 8 | 4.00349 | 4.97466 | 2.36405 | -10.681152 | -12.207031 | 3.61424 |
| 9 | 2.79048 | 2.79048 | 2.22277 | -9.155273 | -9.155273 | 2.86213 |
| 10 | 3.99396 | 3.99396 | 2.27776 | -16.784668 | -16.784668 | 3.39113 |
| 11 | 5.11421 | 5.08664 | 2.31170 | -13.732910 | -15.258789 | 3.61152 |
| 12 | 3.96521 | 3.96521 | 2.42553 | -19.836426 | -19.836426 | 3.62852 |
| 13 | 5.18651 | 5.27190 | 2.47562 | -13.732910 | -15.258789 | 3.63747 |
| 14 | 3.92300 | 4.77100 | 2.52509 | -18.310547 | -19.836426 | 3.54270 |
| 15 | 4.10305 | 4.96682 | 2.30809 | -12.207031 | -13.732910 | 3.38901 |
| 16 | 2.66787 | 2.66787 | 2.09409 | -9.155273 | -9.155273 | 2.95935 |
| 17 | 5.12212 | 5.12212 | 2.42369 | -21.362305 | -21.362305 | 3.77245 |
| 18 | 4.95677 | 4.67093 | 2.61233 | -25.939941 | -27.465820 | 3.51738 |
| 19 | 2.94592 | 2.94592 | 0.98317 | -1.525879 | -1.525879 | 1.00174 |
| 20 | 4.79528 | 4.15265 | 2.37241 | -15.258789 | -16.784668 | 3.37163 |

各边缘能量占比（无量纲fraction，不是百分数），每格为pre / post；完整精度在CSV。

| 圈 | 时间左 | 时间右 | 频率左 | 频率右 |
|---|---|---|---|---|
| 1 | 3.5951e-11 / 3.5557e-11 | 3.3325e-11 / 3.2488e-11 | 2.9541e-16 / 2.9541e-16 | 3.4555e-13 / 3.4555e-13 |
| 2 | 3.1734e-05 / 3.0847e-05 | 2.8352e-05 / 2.7950e-05 | 8.6835e-12 / 8.6835e-12 | 3.1821e-09 / 3.1821e-09 |
| 3 | 3.3674e-05 / 3.2901e-05 | 3.0518e-05 / 3.0031e-05 | 2.9135e-11 / 2.9135e-11 | 1.0907e-10 / 1.0907e-10 |
| 4 | 3.4139e-05 / 3.3576e-05 | 3.1769e-05 / 3.1442e-05 | 1.0536e-11 / 1.0536e-11 | 5.3709e-09 / 5.3709e-09 |
| 5 | 3.2613e-05 / 3.2240e-05 | 3.0927e-05 / 3.0622e-05 | 1.3236e-11 / 1.3236e-11 | 4.4991e-09 / 4.4991e-09 |
| 6 | 7.0877e-06 / 7.5913e-06 | 9.5741e-06 / 1.0105e-05 | 1.7630e-13 / 1.7630e-13 | 1.3234e-10 / 1.3234e-10 |
| 7 | 3.1949e-05 / 3.1620e-05 | 3.0406e-05 / 3.0121e-05 | 6.2718e-12 / 6.2718e-12 | 1.3168e-08 / 1.3168e-08 |
| 8 | 3.4355e-05 / 3.3802e-05 | 3.1985e-05 / 3.1627e-05 | 9.0663e-12 / 9.0663e-12 | 6.4548e-09 / 6.4548e-09 |
| 9 | 3.2214e-05 / 3.1855e-05 | 3.0588e-05 / 3.0297e-05 | 8.4587e-12 / 8.4587e-12 | 1.0096e-08 / 1.0096e-08 |
| 10 | 3.3305e-05 / 3.2892e-05 | 3.1453e-05 / 3.1127e-05 | 6.0091e-12 / 6.0091e-12 | 1.1873e-08 / 1.1873e-08 |
| 11 | 3.4408e-05 / 3.3812e-05 | 3.1916e-05 / 3.1556e-05 | 1.1015e-11 / 1.1015e-11 | 5.1488e-09 / 5.1488e-09 |
| 12 | 3.4213e-05 / 3.3561e-05 | 3.1538e-05 / 3.1163e-05 | 1.4220e-11 / 1.4220e-11 | 2.0730e-09 / 2.0730e-09 |
| 13 | 3.4205e-05 / 3.3541e-05 | 3.1523e-05 / 3.1141e-05 | 1.3865e-11 / 1.3865e-11 | 2.0657e-09 / 2.0657e-09 |
| 14 | 3.3857e-05 / 3.3151e-05 | 3.1056e-05 / 3.0655e-05 | 1.8748e-11 / 1.8748e-11 | 1.9436e-10 / 1.9436e-10 |
| 15 | 3.3221e-05 / 3.2804e-05 | 3.1384e-05 / 3.1060e-05 | 6.0494e-12 / 6.0494e-12 | 1.1565e-08 / 1.1565e-08 |
| 16 | 3.1784e-05 / 3.1457e-05 | 3.0247e-05 / 2.9963e-05 | 5.7222e-12 / 5.7222e-12 | 1.3610e-08 / 1.3610e-08 |
| 17 | 3.1796e-05 / 3.0958e-05 | 2.8226e-05 / 2.7674e-05 | 1.7125e-11 / 1.7125e-11 | 1.3720e-10 / 1.3720e-10 |
| 18 | 2.5637e-05 / 2.4656e-05 | 2.2131e-05 / 2.2242e-05 | 2.1444e-11 / 2.1444e-11 | 1.2755e-11 / 1.2755e-11 |
| 19 | 3.7464e-06 / 4.0561e-06 | 5.3706e-06 / 5.7551e-06 | 2.9178e-14 / 2.9178e-14 | 4.1821e-11 / 4.1821e-11 |
| 20 | 3.3162e-05 / 3.2761e-05 | 3.1380e-05 / 3.1056e-05 | 5.2375e-12 / 5.2375e-12 | 1.4700e-08 / 1.4700e-08 |

预定末5圈是**16–20**：原能量128.718535132–128.728849918 nJ，峰值22750.863204–22796.772814 W；
pre邻圈原始差2.90296%–5.76361%，post原始差3.56510%–5.48638%，
整体对齐后0.80352%–2.84030%，邻圈谱差0.50535%–4.39690%。相对第6圈对齐残差0.98317%–2.61233%。
第12–15圈某些邻圈差较小，但第19–20圈再次变大；未事后挑选那段代替末5圈。
整体时移有明显贡献，对齐后仍有幅值/形状及未解析亚采样位置变化；谱差证据表明并非仅同一复场整体移动。
在当前观察范围内应描述为**变化持续、未单调减小至零**，不能进一步定为呼吸态、物理不稳定或数值错误。
相对第6圈变化也不是单调累积漂移，20圈仍不足以确定长期行为。

## 终点实际峰结构、积分及原始曲线

主半高区定义：原坐标最早全局最大样本所在的I≥0.5×Imax周期连通区；首尾相邻。
区能量为sum(I_region)×dt/1000，占比以同一定义全窗sum为分母；跨度=(样本数−1)dt。
它不等于全局半高跨度、插值局部FWHM、主脉冲全部能量或压缩效率。局部极值/连通区数量不等于独立脉冲数。

| 诊断平面 | trapz能量(nJ) | 峰值(W) | 全局半高跨度(ps) | 主半高区能量占比 | 区外最大/主峰 |
|---|---|---|---|---|---|
| 第20圈SF1 pre | 128.727029831475 | 22786.939841 | 6.40716552734375 | 0.824352477 | 0.584992885 |
| 第20圈SF1 post | 128.727029982430 | 22786.939841 | 6.40716552734375 | 0.824352477 | 0.584992885 |
| 第20圈终点同次压缩场 | 128.692474877810 | 2778112.692975 | 0.02899169921875 | 0.530175010 | 0.453056126 |

SF1主半高区3638点、跨度5.54962158203125 ps，能量106.11645631921184 nJ，不跨边界；
区外仍有0.58499×峰值的结构。压缩主半高区20点、跨度28.99169921875 fs，
区能量68.22953429921694 nJ（占53.01750%），区外最大约0.45306×峰值；均不跨边界。
图中压缩场的旁瓣是实际保存样本，不能仅凭图形称为独立脉冲。压缩场能量从同次实际场积分，
没有借用上游能量、用energy/FWHM估峰或再次运行优化器。原压缩器的局部峰宽定义不被离散全局跨度替换。
尾纤场同样实际保存，trapz能量128.72169429932478 nJ，峰值20828.870923574585 W。

第6与第20圈是不同观察终点，压缩输出差别不是性能优化收益；第6圈后的随机演化未被另行验证。
SF1 pre/post trapz的约1.51e−7 nJ差别来自周期移位与trapz端点权重，周期sum能量相同到舍入量级，
原raw_energy=128.72702983147477 nJ未替换。没有对波形做独立能量归一化。

下图全部来自本次MAT；图线只是连接原样本，不产生新的物理数据。原始全窗与整体对齐局部图分开标记。
profiles右侧实际画第15–20圈（末6圈）；这是绘图窗口，不是末5圈统计窗口，统计仍严格16–20。

![逐圈未对齐/整体对齐差异、位移及同网格谱差](../reports/local/phase2/stationarity_001/observation_analysis_001/observation_rounds/stationarity_differences.png)

![SF1完整时间窗与仅整体移位的峰附近原样本](../reports/local/phase2/stationarity_001/observation_analysis_001/observation_rounds/stationarity_profiles.png)

![终点全时间窗及同次压缩场峰附近原样本](../reports/local/phase2/stationarity_001/observation_analysis_001/observation_rounds/waveform_checks/time_domains.png)

更多实际图：[同网格光谱](../reports/local/phase2/stationarity_001/observation_analysis_001/observation_rounds/waveform_checks/frequency_domains.png)、
[全部逐圈原曲线](../reports/local/phase2/stationarity_001/observation_analysis_001/observation_rounds/waveform_checks/round_comparison.png)、
[半高区/能量/峰值](../reports/local/phase2/stationarity_001/observation_analysis_001/observation_rounds/stationarity_regions.png)、
[旧六圈差异](../reports/local/phase2/stationarity_001/existing_analysis_001/old_six_rounds/stationarity_differences.png)。

## 成本、文件与证据限制

| 项目 | 实测或缺失原因 |
|---|---|
| MATLAB监控外部墙钟 | 2115.063928082993秒（约35.25分钟）；runner单调时钟，包含其关停/失败清理段，不是纯传播时间 |
| backend内部elapsed | 2104.935732秒；口径更窄，不替代外部墙钟 |
| supervisor总限 | 3600秒，包含30秒关停/最终化预留；内部runner收到3599.9985932499985秒，是父启动已耗时扣除后的余额 |
| 父进程至final提交总墙钟 | null：final从未提交；不得用candidate或事后检查时间补造 |
| 分离清理耗时/精确父退出墙钟 | null：未单独持久化；两种计时之差不全部等于清理开销 |
| 进程组峰值RSS | null：已有监控未采样；未追加任务补测 |
| 真实原始产物 | 33个文件，26,175,918 bytes；其中21个波形MAT共24,508,168 bytes，不含批次目录锁 |
| 短进程合计 | 57.70359037397429秒；3次，0失败，0额外传播 |

开始UTC 2026-09-28T01:16:44.719287+00:00；runner结束UTC 01:51:59.811165+00:00。
总预算未耗尽，失败不是timeout或新的数值错误证据，而是监控清理与finalization失败。
原stdout含Java模块WARNING；生产旧warning屏蔽仍是限制，不能用空数值warning栏证明无警告。

原始目录保存requested、launch_request、B configuration.json/.mat、configuration_comparison、
C runtime_calls、runtime_observer、matlab_candidate、runner_record、supervisor_error、stdout、
waveform_manifest、waveforms_round_0001.mat…0020.mat、waveforms_final.mat。
最终MAT包括真实output/pigtail/compressed场、网格、原能量历史；configuration.mat仍不是checkpoint。
**final_result.json缺失**。原结果、锁、日志及旧批次证据没有覆盖；本机产物由既有ignore排除公开仓库。

离线分析器本身不重新验证MAT字节哈希；本批另以原始manifest/candidate完整性清单和保存后哈希核对输入，
分析后再次确认原文件未变。7项final标量对照继续null/not_verified；任何candidate单独对照均只能是事后诊断，
不能填补这7项或弥补父进程未执行gate。独立审查记录保存在本机，不作为替代final。

## 结论与下一步（仅建议）

这次已完成：旧6圈时移/形状区分、观察控制及必要测试、唯一一次真实冷启动到20圈、
保存场共同前缀验证与全部可用圈诊断、原始曲线及报告。正常返回的物理后端和完整波形存在，
但监控清理错误使本次final记录链路未通过；这个边界没有被离线分析抹去。

第6圈能量停止对本次波形观察**不够**：能量判据满足后仍有未被单一整体时间平移消除的强度和谱变化，
且末5圈没有持续趋零；它只能描述原能量判据，不足以确定波形平稳性或任何物理类别。
没有预设波形稳定阈值，也没有足够独立数值/随机验证，不能反向宣称物理不稳定或呼吸态。

下一步首先应在另行授权范围内定位**现有**stop_owned清理EPERM及父final中断原因，
保留失败优先规则，不以删除锁/忽略清理换成功。科学上优先区分整数精度下的残余时移、
形状/相位演化及随机/数值因素，再单独申请有边界的独立数值检查；H02仍需另行确认。
本批没有执行这些建议。未启动第二次观察、收敛实验、扫描、训练、优化、Phase 2B/3或GitHub发布，
没有改环境、全局配置、分支或提交。最终git diff --check与历史/源码保全结果见本机delivery_review.json。
整个Phase 2仍为in_progress；本批结束并停止，等待审核。
