# Phase 2：四维入口、波形留存与一次默认配置验证

2026-09-27（本地；运行日志使用 UTC 2026-09-28）。

**本批已完成四维入口、针对性测试、唯一一次真实默认运行及保存场复核。**
`config_waveform_validation_001 / config_waveform_001` 从原初场冷启动，完成6圈、
尾纤和原压缩分析，MATLAB退出0；candidate、runner及父进程final一致为completed。
外部墙钟586.4352557079983秒。旧定义标量与validation_002精确一致；本次另外保存了
6圈SF1居中前后复场、最终输出/尾纤场和同次原压缩分析的实际压缩场。

这通过的是**默认单点的配置传递、真实调用、波形留存及最终记录链路**，不是整个四维域、
独立数值收敛或稳定单脉冲验证。Phase 2仍为in_progress，等待审核；
physical_state=undetermined，numerical_validation=not_verified，
eligible_as_validated_training_truth=false。本批真实尝试额度已消耗，不再计算。

## 起点、身份和保全

读取适用AGENTS、当前EXECUTION_STATUS、追加预算运行报告、AUDIT相关H02/H03/H05及
M01–M05条目，以及实际入口、包装、观察器、记录器、supervisor和相关测试。
AGENTS中的旧Phase 0授权文字由本批明确指令覆盖，未重做环境或H01审计。

- 分支保持`feature/mamyshev-ml-mvp`；基础commit为
  `489bf4242f9b5266d47f8892840a24af66931ff0`，已有未提交工作保留。
- 起点保存1880份已有文件哈希；详细证据新建于`reports/local/phase2/config_waveform_001/`，
  真实运行独占目录为`reports/local/phase2/config_waveform_validation_001/config_waveform_001/`。
  两个旧validation目录、锁、final、参数和历史报告均未覆盖。
- 启动冻结源码清单244项，SHA-256摘要
  `54c9be5a5084b0f83735ad60f5c99233934b1d780e745ce0b5745f0b3b9d05bd`。
  这是本批新身份，不声称与validation_002的231项旧清单相同。运行期间及结束后身份一致。
- 单次启动器预留前确认新真实批次不存在；只读识别到其他MATLAB进程属于VS Code服务，
  未发送信号。仅本批所属组由既有监控器清理，runner均确认cleanup_verified=true。
- 全部Python经指定Miniforge的mamyshev-ml执行；没有安装依赖、改环境或全局配置。
  一次沙箱内Conda命令在Python执行前报NoWritableEnvsDirError，随后获具体执行权限完成
  只读dry-run；该错误未预留真实尝试、未启动MATLAB，也未改变环境。

## 四维入口与实际传递

```matlab
result = run_mamyshev_config(config, plot_on, diagnostic_options)
config = struct('pump_power_W',4, 'filter_offset_nm',10, ...
                'filter2_bw_nm',3, 'gain_length_m',4);
```

省略整个config参数才使用上述默认值；传入不完整struct报错。`plot_on`默认false，
`diagnostic_options`沿用原独立capture通道。新入口只委托同一个`run_mamyshev`初始化及循环，
没有复制传播引擎。旧`run_mamyshev(PumpPower,cw2,plot_on,diagnostic_options)`继续可用，
在边界转换为offset后进入同一解析器。内部第五参数与非空旧PumpPower/cw2同时提供会报错。

| 输入（单位） | 默认值 | 实际生产接线 |
|---|---:|---|
| pump_power_W（W） | 4 | `run_mamyshev.m:75` → gain_rate_eqn.copump_power → gain_info → gain_param{1}，传入实际增益传播 |
| filter_offset_nm（nm） | 10 | `run_mamyshev.m:34`、`:42`；offset=1040−cw2，SF1固定1040，默认SF2为1030 |
| filter2_bw_nm（nm） | 3 | `run_mamyshev.m:138` → spectral_filter2.bw → `:263`实际SF2滤波调用 |
| gain_length_m（m） | 4 | `run_mamyshev.m:101` → fiber_Gain.L0 → `:229`实际传播；`:154`总长/保存容量/拼接坐标、`:167`初始t_rep随之计算 |

`mamyshev_resolve_config.m:7`起要求恰好四个已知字段、有限实数标量，拒绝布尔、向量、复数、
NaN/Inf、缺字段和包括cw2在内的未知/冲突字段。泵≥0，带宽和增益长度>0，SF2中心>0。
JSON还拒绝重复键。长度必须至少覆盖一个继承的0.1 m保存间隔，并满足引擎原有的
length/save_period整数或相邻一个eps兼容规则（`:22`）；例如4.1 m可解析，4.15 m被拒绝。
**不取整物理长度，不修改保存间距或步长来通过。** 这些仅为输入合法性约束，历史范围不是
已验证可用域；非默认配置在本批只做初始化检查，没有完成非默认设计传播。

关键接线摘要：

```matlab
% run_mamyshev_config.m:9，共用原生产循环
result=run_mamyshev([],[],plot_on,diagnostic_options,config);
% run_mamyshev.m中的实际参数及原有依赖计算
fiber_Gain.L0 = design_config.gain_length_m;
spectral_filter2 = struct('bw',design_config.filter2_bw_nm,'cw',cw2);
L0 = sum([fiber_cavity.L0]);
gain_rate_eqn.t_rep = L0/(1/fiber_cavity(1).betas(2)*1e12);
```

最后一行展示等价依赖关系；生产源码保留原来的先计算v、再L0/v的运算顺序。
无源三段始终0.4/1.5/3.2 m，尾纤0.2 m；默认腔长9.1 m，增益4.1 m初始化时腔长9.2 m。
后者实际初始t_rep=4.4915320000000005e-08 s，与Python核对值精确一致。
运行后的动态t_rep继续由原时间延迟更新，自适应步长继续按原算法演化。

## 保留的物理身份与安全记录

H02仍未解决：无源MFD声明10.5 μm，而实际SR仍来自默认5.95 μm的派生过程。
本次B记录实际SR=35964678899.37611 m⁻²，面积=2.7805058479678165e-11 m²；未重算SR，
也未把10.5 μm宣布为已确认器件参数。增益MFD11.1 μm及材料/增益规则均保留。

`ring_legacy_rules_config_v1`明确区分继承规则、本次四维输入和历史参考
`legacy_ring_phase1_v1`；默认值matches_historical_reference=true，非默认初始化为false。
没有覆盖`configs/legacy_physics_identity.json`或历史结果。1-H端口、原滤波公式/四阶参数、
N_total=9e7覆盖、初态、随机开关、尾纤及Treacy-t压缩器假设不变。

Nt=32768、50 ps、max_rt=50、原步长/误差容差/保存设置/停止条件全部保留。
`analyze_field.m:1`只添加第七返回量`dechirped_field`，复用原函数已计算的变量；
该文件其余数值正文未改，也没有第二次调用压缩器、改变目标或用去谱相位理想场替代。
GMMNLSE传播和增益更新、H01/H04修复、观察器及check_convergence未在本批修改。

旧无design_config路径继续完整严格比较原baseline；新路径只替换请求的四维量及其
初始总长/t_rep依赖，其他值、类和形状仍严格核对（`mamyshev_compare_configuration.m:22`）。
B来自真实局部变量，C在实际传播/滤波调用前记录参数，不只复述身份JSON。
supervisor核对A→B→C、每圈SF1后SF2的12次滤波实参、固定规则、段序列及计数完整性。
默认配置本次通过256个叶项精确比较；本批新增参数接线没有关闭旧基准校验。

启动器、STOP、所属进程组、每批一次预留、拒绝覆盖和父进程独占final机制均复用。
新CLI批次只允许本次默认四维请求和显式1800秒；旧默认900秒行为保持。
真实模式没有component backend或任何test_hook字段。候选/最终记录继续safe_result_v1；
超时、取消、非零退出、配置/完整性不符仍优先于候选成功。波形引用也纳入完整性gate，
失败不能凭已保存MAT升级为成功。

## 波形留存契约

生产循环先保留旧居中前能量，再复制该平面的场；完成该圈的原更新后，正常停止判断前
保存pre/post两份场（`run_mamyshev.m:284`、`:331`）。保存不修改生产场或物理RNG。
最终正常返回位置调用writer.finish，再完成原capture.finish（`:430`）。

| 文件（真实run目录内） | 内容/位置 |
|---|---|
| waveforms_round_0001.mat 至 waveforms_round_0006.mat | 各圈同一SF1的1-H拒绝端；pre_tracker_field与post_tracker_field，圈号、原raw_energy_nJ |
| waveforms_final.mat | 实际返回output_field（SF1居中后、尾纤前）、pigtail_output_field（尾纤后）、compressed_field（同次原压缩分析）；全部原能量历史和rt_num=6 |
| waveform_manifest.json | 文件引用、大小/SHA-256、run_id、源码身份、四维请求、网格/单位/处理平面及有限/完整性摘要；不内嵌复数组 |
| configuration.mat | 原初始化快照，**不是最终场或恢复checkpoint** |

每份波形MAT均带t_ps、f_THz、f0_THz和metadata；场单位sqrt(W)，时间ps，频率THz，
能量nJ，功率W。最终场与第6圈post场精确相等。文件独占写入，拒绝覆盖；只保存上述
有限输出，不新增trial历史或checkpoint。原生产内部完整传播历史的内存成本未顺带重构。
父进程对6份原记录及8份波形产物（manifest+7个MAT）共14项做完整性核对。
本次压缩复场实际取得，因此压缩能量由该场独立积分；JSON的field.value仍为null，
同时available=true并引用MAT变量，原因是复数组不内嵌JSON，而不是声称没有保存。

## 测试、一次失败及预算

固定比较规则在启动前存入`configs/phase2_config_waveform_regression.json`：
`abs(new-old) <= atol + 1e-10*abs(old)`；能量atol=1e-10 nJ，峰值1e-7 W，
全局宽度1e-12 ps，原压缩/TL宽度1e-9 fs，旧能量相对波动1e-12。
圈数、停止原因、旧标志和最终场对最后一圈场要求精确相等。未根据结果放宽。

| 检查 | 实际范围和结果 |
|---|---|
| test_config_entry | 8组通过；6次真实生产初始化、0传播：legacy/默认完全一致；4.1 W、offset9.5 nm、带宽3.2 nm、增益4.1 m逐项改变，实际解析值/依赖及不变初场/RNG/SR正确；非法/冲突/保存网格失败，额外SR改动被拒绝 |
| test_waveform_io | 5组人工复数数组检查通过：开/关保存计算与RNG精确一致；复数MAT读写、维度/单位/身份/哈希、拒绝覆盖、非有限拒绝、压缩场缺失原因 |
| test_waveform_analysis | 10组人工128点FFT-bin平面波检查通过：闭式量、FFT/Parseval、trapz差别、边界、未归一化L2、宽度定义、PNG/RNG及损坏场/坐标/单位拒绝；不是设计样本 |
| 受影响的已有MATLAB回归 | capture 14组、result_contract 20组、wrapper 11组通过；未重跑H01和第三方全套。contract的assert已通过后才进入后续失败分析步骤；该首进程无总summary，未伪造原summary |
| Python | 48个不同方法通过：新gate11、launcher11（其中新3/旧8）、supervisor17、short_runner9；14新增、34复用，开发重复执行不增独立数量；最终完整套件计时约2.073秒，不含Conda启动 |
| 跨语言只读核查 | 6份真实初始化B与Python预期精确一致；5份设计A/B规则一致；人工MAT/manifest通过Python波形gate。内存schema fixture不是新candidate或仿真 |
| 本次MAT离线检查 | 55项复算检查通过；15项对validation_002的固定回归通过。独立列为真实保存数据分析，非fixture或新传播 |

第一次短进程在前述配置、IO、capture和contract完成后，遇到新离线脚本结构体数组初始化
错误，exit1；原stdout和失败runner保留。修正`rounds`为空但字段明确的结构数组，随后
只执行受影响分析组件与包装回归，未重复六次初始化。该局部修正未改物理或容差。

| 串行MATLAB短进程 | 实际墙钟(s) | 状态 |
|---|---:|---|
| components_001 | 13.74371104198508 | failed/exit1；分析组件结构体赋值错误 |
| analysis_component_001 | 20.823312999971677 | completed/exit0；修正后的人工分析及wrapper回归 |
| offline_analysis_001 | 14.819950875011273 | completed/exit0；仅读取本次真实MAT及绘图 |
| 合计 | 49.38697491696803 / 300 | 含失败，单进程均小于180秒 |

沿用短测监控器的通用kind字段为synthetic_short_test；第三项的实际脚本与analysis.json
明确为offline_recomputation_from_saved_complex_fields，0传播、0压缩优化，不能据通用标签
把真实保存场分析说成人工物理结果。所有任务串行；无parpool/GPU或后台传播任务。

## 实际命令与唯一真实运行

以下真实命令只执行一次；此前将`--execute-real`替换为`--dry-run`核对过新目录、真实后端、
默认请求、seed=0/twister、保存开启、1800秒总限及其中30秒预留，dry-run未预留尝试。

```sh
/opt/homebrew/Caskroom/miniforge/base/bin/conda run -n mamyshev-ml --no-capture-output python scripts/run_mamyshev_once.py --execute-real --run-id config_waveform_001 --batch-id config_waveform_validation_001 --timeout-s 1800 --design-config configs/phase2_config_waveform_default.json --save-waveforms --matlab /Applications/MATLAB_R2025a.app/bin/matlab
```

取消入口原样保留：
`touch reports/local/phase2/config_waveform_validation_001/config_waveform_001/STOP`。
本次无取消/超时/重试。短测及离线实际命令：

```sh
/opt/homebrew/Caskroom/miniforge/base/bin/conda run -n mamyshev-ml --no-capture-output python tests/run_matlab_short.py components_001 tests/matlab/run_config_waveform_components.m --batch config_waveform_001 --matlab /Applications/MATLAB_R2025a.app/bin/matlab
/opt/homebrew/Caskroom/miniforge/base/bin/conda run -n mamyshev-ml --no-capture-output python tests/run_matlab_short.py analysis_component_001 tests/matlab/run_config_waveform_analysis_component.m --batch config_waveform_001 --matlab /Applications/MATLAB_R2025a.app/bin/matlab
/opt/homebrew/Caskroom/miniforge/base/bin/conda run -n mamyshev-ml --no-capture-output python tests/run_matlab_short.py offline_analysis_001 tests/matlab/run_config_waveform_offline_analysis.m --batch config_waveform_001 --matlab /Applications/MATLAB_R2025a.app/bin/matlab
```

完整请求、真实命令、预先固定规则和源码身份在本地launch_freeze.json及原launch_request.json。

调用链：launcher → 原supervisor → launch_mamyshev_once → run_mamyshev_recorded →
**run_mamyshev_config → 同一run_mamyshev** → 原GMMNLSE；随后原尾纤、一次analyze_field、
MAT留存、candidate，最后父进程验证并提交final。冷启动rng(0,'twister')，未读取旧末场恢复。

预留、MATLAB启动、传播和正常后端返回均实际发生；6圈按legacy_energy_convergence停止，
不是max_rt、数值错误或预算停止。旧标志converged=true、force_stop=false、pulse_survives=true、
ML_state=1；保持旧标志身份，不映射stable_single。参数/计数记录完整，无活动段；
candidate_valid=true，candidate_error=null，required_records_error=null，exit0，stop_events=[]。

| 实际路径 | 完整段数 | trials | rejections | accepted_advanced_steps |
|---|---:|---:|---:|---:|
| 增益cavity_1 | 6 | 27374 | 18 | 27356 |
| 无源cavity_2 | 6 | 9116 | 12 | 9104 |
| 无源cavity_3 | 6 | 2258 | 0 | 2258 |
| 无源cavity_4 | 6 | 1938 | 0 | 1938 |
| 尾纤 | 1 | 719 | 2 | 717 |
| 总计 | 25 | 41405 | 32 | 41373 |

各段均pending=0、trial=reject+advance且正常完成；计数逐段与validation_002一致。
18次真实增益拒绝说明本次走到该回滚分支，但未独立验证随机拒绝协议；无源拒绝不算H01证据。
本批没有改H01，也不能用计数反推Phase 1旧运行误差或拒绝次数。

## 与validation_002的同定义软件回归

旧值直接读取`reports/local/phase2/single_validation_002/validation_002/final_result.json`，
本次值来自父进程final。下列所有旧已有数值**精确相同，差值0**，而非仅在容差内接近。
本次前后完整RNG状态也分别与旧记录相同；没有额外真实保存关闭对照运行。

| 位置/定义 | validation_002与本次共同值 |
|---|---:|
| SF1拒绝端居中前原积分能量，nJ | 128.7196822190777 |
| 同端居中后实际场峰值，W | 22779.272914985067 |
| 同端居中后全局半高跨度，ps | 6.4117431640625 |
| 尾纤后未压缩场能量，nJ | 128.7146060101117 |
| 尾纤后未压缩场峰值，W | 20872.27893766115 |
| 原压缩分析局部峰宽，fs | 29.84941905629446 |
| 原压缩实际场峰值，W | 2850940.6179669127 |
| 去谱相位理想参考宽度，fs（不是实际压缩场） | 22.753081194425736 |
| 旧末五圈能量相对波动 | 0.0004224468255450582 |
| 停止圈数/原因 | 6 / legacy_energy_convergence |

四个旧标志和停止原因也精确相等，共15项固定检查通过。两次终点相同，但仍只是同seed、
同设计的软件回归，不是独立物理设计或随机/网格收敛证据。validation_002未保存最终复场，
所以新旧复场差值=null（缺旧场），未补造或补跑。其压缩能量/压缩场历史null保持不变。

## 本次MAT独立读取与实际图

重新读取7个波形MAT，复场及坐标均有限，32768×1，时间间隔0.00152587890625 ps
（1.52587890625 fs），f0=289.65454879227053 THz，df=0.02 THz。
频域使用`fftshift(ifft(A,[],1),1)`，完整保留1902个负绝对频率样本；不截谱后冒称全域检查。
PSD=`abs(spectrum).^2*(N*dt_ps)^2/1000`，单位nJ/THz。

| 本次保存平面 | 复算trapz能量(nJ) | 峰值(W) | 全局样本半高跨度(ps) |
|---|---:|---:|---:|
| SF1居中前 | 128.7196822190776 | 22779.272914985067 | 6.4117431640625 |
| SF1居中后/实际output_field | 128.71968200801632 | 22779.272914985067 | 6.4117431640625 |
| 尾纤后 | 128.7146060101117 | 20872.27893766115 | 6.12945556640625 |
| 同次压缩场 | 128.66941786965054 | 2850940.6179669127 | 0.02899169921875 |

SF1居中前的复算与旧式标量积分只有浮点累加顺序差异，满足预定容差；居中后的trapz能量
与居中前约差−2.1106e-7 nJ，未拿它替换原output_energy。两者周期离散求和都为
128.71968547804119 nJ：tracker循环移动使端点半权重不同，trapz不等于周期求和。
时域/频域周期求和的Parseval检查全部通过；这不代表网格或窗口已经收敛。

尾纤全局宽度是本次新离线派生量；原final的该标量仍按旧适配器保留null+reason。
压缩场能量由实际场计算，未借尾纤能量。压缩全局样本跨度28.99169921875 fs与原
局部峰宽29.84941905629446 fs定义不同：前者不插值、可跨多个峰，后者是原局部峰算法。
未重新优化压缩器或离线重算局部峰宽，也未把理想参考场当作压缩场。

每侧取`ceil(0.01*N)=328`个原样本（实际每侧1.0009765625%），下表为**离散能量比例**，
不是百分数；时间和频率左、右分别计算，未平滑/删峰/归一化或裁谱后积分。

| 平面 | 时间左 | 时间右 | 频率左 | 频率右 |
|---|---:|---:|---:|---:|
| SF1居中前 | 7.0876713e-6 | 9.5741488e-6 | 1.7630166e-13 | 1.3233605e-10 |
| SF1居中后 | 7.5912562e-6 | 1.0105276e-5 | 1.7630166e-13 | 1.3233605e-10 |
| 尾纤后 | 3.1065986e-5 | 3.5168950e-5 | 2.1117969e-13 | 1.3956117e-9 |
| 压缩后 | 4.4262380e-9 | 9.9174600e-9 | 7.3848608e-14 | 7.4141752e-14 |

逐圈强度变化=`norm(I_rt-I_previous)/norm(I_previous)`，在pre/post位置分别计算。
分析不额外时移；post本身已由生产pulse_tracker居中。没有逐圈独立归一化。

| 圈 | 原始生产能量(nJ) | pre相对L2 | post相对L2 |
|---|---:|---:|---:|
| 1 | 132.8064818374161 | null：无前圈 | null：无前圈 |
| 2 | 128.60432753052683 | 0.2337369901 | 0.2337369901 |
| 3 | 128.72879635511288 | 0.0451461694 | 0.0322655397 |
| 4 | 128.72760947627913 | 0.0391877650 | 0.0252130133 |
| 5 | 128.7264871825689 | 0.0455488927 | 0.0455488927 |
| 6 | 128.7196822190777 | 0.0454466966 | 0.0454466966 |

能量判据停止时，相邻强度仍约4.54%变化；压缩峰附近原始样本图可见旁峰/旁瓣。
这些事实限制“稳定单脉冲”的推断，并未在本批新增分类规则。6圈观察、低边缘能量、
Parseval恒等式或一次同seed回归都不能替代独立数值/物理验证。

下列三图已从本次MAT生成并检查，保留原样本、完整域与局部峰附近视图，没有引用历史图。
图与详细JSON保持本地，发布仓库时不会自动包含这些忽略目录。

- [本次时域四平面及峰附近样本](../reports/local/phase2/config_waveform_001/offline_analysis_001/figures_and_checks/time_domains.png)
- [本次全频域光谱](../reports/local/phase2/config_waveform_001/offline_analysis_001/figures_and_checks/frequency_domains.png)
- [本次逐圈能量、波形及强度变化](../reports/local/phase2/config_waveform_001/offline_analysis_001/figures_and_checks/round_comparison.png)
- [全部55项复算与15项回归的数值/误差/容差](../reports/local/phase2/config_waveform_001/offline_analysis_001/figures_and_checks/analysis.json)

## 运行成本、缺失项与实际文件修改

| 项目 | 实测/原因 |
|---|---|
| 真实尝试 | 1/1；不是新增独立物理设计或训练样本 |
| MATLAB外部墙钟（含退出/所属组清理） | 586.4352557079983 s |
| wrapper内部范围 | 576.3701195416667 s |
| 父进程到final提交前 | 586.5082124159671 s |
| final提交完成精确总墙钟 | null：既有监控器只记precommit，未测提交自身耗时 |
| 独立清理耗时 | null：未单独计量，已包含外部墙钟 |
| 预算/内含预留 | 1800 / 30 s；不是1800+30 |
| 进程组峰值RSS | null：既有监控器未采样，本批没有新增采样平台 |
| 原始run产物 | 19文件，9,986,403 bytes；其中7个波形MAT共8,474,331 bytes |
| runner UTC起止 | 2026-09-28 00:27:59.088748 → 00:37:45.536627 |

validation_002同终点外部墙钟1040.4727931660018 s，本次586.4352557079983 s；仅作描述，
没有受控性能实验，不宣称加速比、优化收益或波形I/O的独立开销。stdout只有两条既有Java
package warning，未记录数值异常；旧warning屏蔽限制仍在，不能据此断言没有数值警告。
无supervisor_error.json，因为本次没有该错误；无资源记录，原因见上表。

本批已有文件修改（相对起点，而非把所有未提交内容算作本批）：

- `code/ring_cavity/scans/run_mamyshev.m`：统一配置入口、实际四维赋值和有限波形接线。
- `code/simulation_engine/GMMNLSE/analyze_field.m`：仅第七兼容附加输出；其余正文不变。
- `code/ml_bridge/MamyshevCapture.m`、`mamyshev_compare_configuration.m`：实际设计/继承规则、
  C滤波参数、限定参考调整及波形完整性。
- `code/ml_bridge/run_mamyshev_recorded.m`、`launch_mamyshev_once.m`、`mamyshev_result_record.m`：
  新入口选择、身份/冲突校验、真实压缩场能量及MAT引用；失败传播保留。
- `scripts/run_mamyshev_once.py`、`src/mamyshev_ml/supervisor.py`：受限新批次请求和原安全gate扩展。
- `tests/run_matlab_short.py`：同一监控器增加本批300秒预算；`tests/test_once_launcher.py`增加3方法。
- `docs/EXECUTION_STATUS.md`更新本批事实；本报告新增，旧报告保留。

新增可复用源码/配置/测试：

- `code/ring_cavity/scans/mamyshev_resolve_config.m`、`run_mamyshev_config.m`；
  `code/ml_bridge/MamyshevWaveforms.m`；`scripts/analyze_mamyshev_waveforms.m`。
- `configs/phase2_config_waveform_default.json`、`phase2_config_waveform_regression.json`。
- `tests/matlab/test_config_entry.m`、`test_waveform_io.m`、`test_waveform_analysis.m`；
  `run_config_waveform_components.m`、`run_config_waveform_analysis_component.m`、
  `run_config_waveform_offline_analysis.m`；`tests/test_config_waveform_supervisor.py`。

交付执行git diff --check；起点与原始run产物哈希保全检查、最终状态及命令证据保存在
本批本地目录。没有重建环境、修改数值引擎/核心物理规则、降低分辨率、扫描、训练、优化、
独立收敛研究、checkpoint恢复、简历/README性能数字更新或GitHub操作。

本次集成无未完成阻塞；后续科学用途仍受H02未决、独立分辨率/窗口/步长验证缺失、
随机拒绝协议未独立验证、短观察及波形变化限制。建议先审核这些证据，再另行确定数值和
物理验证范围。本批不执行该建议；Phase 2B/3及之后未开始。
