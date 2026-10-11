
# Phase 1：原始后端、数值约定与数据来源审计

日期：2026-09-27。审计基于当前工作区源码与 MATLAB `diagnostic_001/002` 依赖/合约探针；
基线运行结果、实测成本与停止原因统一见 [BASELINE_REPORT.md](BASELINE_REPORT.md)。
初始化通过不等于完整基线通过，也不等于数值或实验有效性通过。

本阶段保留既有物理模型、采样点数、最大圈数及未提交工作。以下“已确认问题”表示
源码或独立探针足以确认的缺陷/定义不一致；“需要运行验证”表示触发条件、影响量或
物理解释仍缺证据；“仅为改进建议”不表示已实施。旧简历数字和历史成图不作为验收条件。

## 范围、版本与依赖

审计基准 commit 为 `489bf42`，分支 `feature/mamyshev-ml-mvp`；原有未提交文件与差异
在本地 Phase 1 快照中保留。实际引擎是 `code/simulation_engine/GMMNLSE/`，不是
`third_party/MMTools/`。八类检查均已覆盖：依赖与路径、参数接口、单位与数值、指标、
收敛与状态、模型一致性、数据来源、计算成本；尚未完成的运行验证在对应条目列明。

`code/setup_mamyshev_project.m:8–28` 添加项目引擎和实验目录；
`GMMNLSE_propagate.m:239–242`、`gain_info.m:140–143` 再添加算法和增益子目录。
`diagnostic_001/preflight.json` 中 `which -all` 已确认 setup、run_mamyshev、propagate、
loader、gain_info、filter、convergence、tracker、compressor、analyze_field 的首选路径
均是上述本地项目代码。未发现首选函数误指向 MMTools。MathWorks 方法重载的同名条目
不等于错误版本抢占路径。

| 组件 | 实际用途与源码证据 | 本次状态 |
|---|---|---|
| MATLAB R2025a Update 1，maca64 | CPU、double、单模、adaptive RK4IP；`code/ring_cavity/scans/run_mamyshev.m:63–80`；loader `:567–601` | 启动、初始化成功；基础许可测试=1 |
| Curve Fitting Toolbox | `smooth`；`code/simulation_engine/GMMNLSE/Gain_rate_eqn/smooth_cross_sections.m:22–23`，由 `read_cross_sections.m:73` 调用 | 正确首选函数、安装、许可=1；初始化已调用 |
| Signal Processing Toolbox | `findpeaks`；`pulse_tracker.m:118,126`、`characteristic_lengths.m:55`、`pulse_compressor.m:565` | 正确首选函数、安装、许可=1；完整真实运行另见基线报告 |
| Liekki Yb 截面文本 | `code/simulation_engine/GMMNLSE/Gain_rate_eqn/Liekki Yb_AV_20160530.txt`；`gain_info.m:192` | 文件存在，初始化读取成功 |
| MATLAB 优化函数 | 默认压缩器 `fminsearch`；`pulse_compressor.m:157–159` | 首选解析为 MATLAB 自带实现 |
| Parallel Computing Toolbox | GPU/distributed条件分支；CPU进度更新也调用 `gather`（adaptive gain `:461–465`） | 已安装，许可=1；实际CPU标量gather解析到MATLAB基础bigdata/gather并执行成功，不能仅据此断言PCT是默认CPU必需；GPU未验证 |
| Optimization Toolbox | 压缩器条件分支；`pulse_compressor.m:165–176` | 已安装，许可=1；默认 `global_opt=false` 不走该全局优化分支 |
| Image Processing / Global Optimization Toolbox | 静态依赖分析列出 | 已安装；本探针未单独测试许可，也未证明默认路径实际调用 |
| CUDA、GPU、nvcc/PTX | `GMMNLSE_propagate_with_adaptive_deltaZ_RK4IP.m:250–294,757–791` | 默认 `gpu_yes=false`，未验证且本基准不需要启用 |
| 多模场、betas/S tensor MAT | loader `:450–497`、`gain_info.m:202–250` | 单模默认不依赖这些模式文件；多模分支未验证 |
| 外部 CPU 编译组件 | 当前 scalar adaptive CPU 路径 | 未见强制外部 MEX/编译步骤；其他分支未验证 |
| `fminsearchbnd` | 探针查询结果为空 | 缺失，但未发现是默认压缩器必要依赖，不能据此判基线阻断 |

上述表中未写完整目录的函数均位于 `code/simulation_engine/GMMNLSE/`，adaptive gain
位于其 `Gain_rate_eqn/`，adaptive propagator 位于其 `GMMNLSE algorithm/`。
静态 `requiredFilesAndProducts` 的列表不能代替分支执行验证：它可能只列出已安装工具箱，
路径外依赖也可能遗漏；本次结合实际路径、许可与初始化检查，而不把该列表当作完整性
证明。参见 [MathWorks 依赖分析说明](https://www.mathworks.com/help/matlab/ref/matlab.codetools.requiredfilesandproducts.html)。

## 高严重性：影响定量解释或标签正确性

### H01 增益自适应步被拒绝后没有完整回滚泵状态

**已确认代码问题；实际触发次数与误差大小需要运行验证。**
`code/simulation_engine/GMMNLSE/Gain_rate_eqn/GMMNLSE_adaptive_rategain.m:340–378`
在尝试前保存、失败后恢复信号场和 `a5`，但步函数同时覆盖的前/后向泵功率没有回滚。
`GMMNLSE_RK4IP_rategain_adaptive.m:112–124,151–161` 先推进泵，再决定该步成功与否；
`solve_gain_rate_eqn_RK4IP.m:105,317` 返回更新后的泵。在外层 z 尚未推进时
（`GMMNLSE_adaptive_rategain.m:404–405`）重试，可能重复演化泵。

这不能由“程序完成”排除。应先记录拒绝步数，构造强制一次拒绝的最小测试，对比完整
状态恢复后的信号/泵；涉及数值算法，本阶段只记录，不擅自修复。自适应局部误差也
未直接覆盖泵/反转粒子误差：`GMMNLSE_RK4IP_rategain_adaptive.m:147–161` 使用非线性
导数差，`solve_gain_rate_eqn_RK4IP.m:263–267,317` 的增益/泵采用另一离散更新。
因此不能把全耦合求解仅凭“RK4IP”名称称为已验证四阶算法。

### H02 无源 MFD 字段与实际非线性参数不一致

**已确认问题，初始化实测确认。**
`code/ring_cavity/main/Mamyshev_ring_cavity.m:56–57` 和
`code/ring_cavity/scans/run_mamyshev.m:70–71` 先加载缺省光纤，再把 MFD 改为 10.5 μm。
`code/simulation_engine/GMMNLSE/load_default_GMMNLSE_propagate.m:425–449` 此前已经
按 5.95 μm 计算有效面积、`SR` 和 `gain_Aeff`。传播使用 `SR`，不随字段赋值重算。

探针实测 `SR=3.5964678899376106e10 m^-2`；按声明的 10.5 μm 得
`1.1548658002132996e10 m^-2`，比值 **3.114186851211**。这也影响以同一无源光纤
构造的尾纤。增益段在 loader 前传入 MFD=11.1 μm（run `:78–80`），没有同样的
赋值顺序问题。应冻结 legacy 配置并记录实际派生值；直接纠正会改变物理计算，不能
把纠正后的输出悄悄叫作同一历史模型。

### H03 能量收敛及末五圈标签不足以判稳定单脉冲

**已确认问题。** `code/ring_cavity/scans/run_mamyshev.m:269–278,328–335` 以最后至多
五圈输出能量的相对标准差分类；低于 2% 的存活场标作 `ML_state=1`，注释还将 breathing
包含在内。没有验证足够观察窗口、对齐波形变化、主脉冲数或呼吸周期。`ML_state=-1`
混合多种状态；到 `max_rt` 的循环结束没有独立的“未充分观察”状态（`:157`）。

`code/simulation_engine/GMMNLSE/check_convergence.m:45–83` 的实际判据也是能量变化；
field 仅用于可选绘图（`:87–122`）。`pulse_tracker.m:103–135` 虽提供多脉冲启发式
判断，主脚本 `:196–198` 与 run `:221–223` 只接收第一返回值，同时屏蔽警告。
脉冲居中不等于单脉冲验证。

`diagnostic_002/contracts.json` 的独立人工样例已实测：相同常量能量历史下，单Gaussian
和等能量双Gaussian都返回converged=true。这是判据局限的复现，不是两次激光仿真。
真实基线最后几圈能量几乎不变，但第4→5圈和5→6圈已居中强度的相对L2变化分别为
4.733%和0.627%；没有预先验证的波形阈值/充分观察窗口，故保留undetermined。

**需要运行验证：** 保存代表性末圈场/能量序列后，区分 stable_single、stable_multipulse、
breathing、dead、nonstationary、undetermined；原 tracker 启发式自身也须验证。
超时/异常是作业状态；达到 max_rt 是观察停止原因，均不能直接作为物理不稳定标签。

### H04 非有限输入可能被收敛函数误判为收敛

**已确认缺陷，独立NaN样例已复现；本次保存的真实末圈场未发现非有限值。**
`code/simulation_engine/GMMNLSE/check_convergence.m:45–83` 没有有限性检查，使用
`any(abs(difference)>tol)`；NaN 比较不会产生 true，因此存在错误进入 converged 的路径。
`diagnostic_002` 向原函数传入6个NaN能量和44个预分配零，实际返回converged=true。
这不表示真实基线出现NaN；两个真实运行保存的拒绝端和尾纤场都通过有限性检查。
非有限真实运行应保留为numerical_error/undetermined，不能让这一错误分支产出稳定标签。

另有无进展风险：`Gain_rate_eqn/GMMNLSE_adaptive_rategain.m:344–379` 和
`GMMNLSE algorithm/GMMNLSE_propagate_with_adaptive_deltaZ_RK4IP.m:622–649` 重试循环
没有明确最小步长或重试上限；步函数在 NaN 时减半步长。**已确认防护缺口，是否造成
本次慢运行需要运行证据**，不能直接宣布这就是实测瓶颈。

### H05 能量、峰值功率和脉宽字段混合不同输出平面

**已确认问题。** `code/ring_cavity/scans/run_mamyshev.m:280–326` 返回的字段应这样解读：

| 字段/位置 | 处理状态 | 单位与边界 |
|---|---|---|
| `output_field/output_energy/fwhm_ps` | SF1 拒绝端，未经过尾纤或压缩器 | sqrt(W)、nJ、ps |
| `pigtail_output_field` | 拒绝端再传播 0.2 m 无源尾纤 | 原始复场；不是腔内反馈 |
| `dechirped_fwhm_fs/dechirped_peak_power_W` | 尾纤后经理想化 Treacy 压缩分析 | fs、W；不能与前尾纤能量直接作同面联合性能声明 |
| `transform_limited_fwhm_fs` | 去除谱相位的理想参考 | 不是实际已实现压缩输出 |
| 腔内 `field`/演化图 | 多个传播位置 | `analyze_sim.m:141–149` 为阈值处理后的 RMS，不是 FWHM |

函数没有同时返回尾纤能量、压缩能量和压缩场。压缩器参数为 Treacy-t、入射角 π/6、
刻线间距 1e-6 m、衍射级 -1，默认 `global_opt=false`（run `:290–292`；
`code/simulation_engine/GMMNLSE/analyze_field.m:60–63,159`）。
`pulse_compressor.m:138–189` 最大化峰值强度，不直接最小化 FWHM；`:230–235,262`
会屏蔽不可传播/极弱谱分量再乘相位，未建模实际光栅效率曲线。

`run_mamyshev.m:343–356` 的原始 FWHM 是所有高于半峰点最左到最右的跨度；
`pulse_compressor.m:558–566` 使用局部峰宽。多脉冲/周期边界可能给出不同含义的宽度。
**需要运行验证：** 真实峰结构、边界与压缩最优化质量；不能把后处理成功当数值收敛。

### H06 历史绘图、处理表与新物理训练数据不能混用

**已确认来源问题。** `data/README.md:5–15` 已说明历史性质；实际文件进一步表明：

| 来源 | 实际内容 | 可用边界 |
|---|---|---|
| `data/ring_cavity/mamyshev_phase_scan.mat` | 与 archive 副本 SHA-256 相同的历史二维汇总 | 可作历史比对；不当成本阶段新运行或完整逐次日志 |
| 环形四个 `plot_*_dependence.m` | 手工历史/后处理数组，17+17+11+9=54条绘图记录 | 不能认定为54个独立物理设计或四维联合训练样本 |
| archive 线性原扫描 CSV/MAT | 66行记录、48个逐点MAT；含失败、死亡、重复基准 | 历史执行证据候选；不属于当前ring模型，标签和输出定义待重新核验 |
| archive `processed_scan_figures/` | 原始失败位置也出现填充值 | 生成算法未找到；不是独立模拟 |
| `data/linear_cavity/trend_guided/` | 62行明确按预期趋势处理的曲线数据 | 仅历史参考，不作物理标签 |
| 既存 ignored reproduction 结果 | 六组有端口复场/配置的旧候选模型结果 | 必须区分模型与版本，不能充作本阶段新基线 |

具体证据：`code/ring_cavity/analysis/plot_pump_dependence.m:3–4,15–22`、
`plot_offset_dependence.m:3–4,15–35`、`plot_bandwidth_dependence.m:4–5,17–35`、
`plot_gain_length_dependence.m:3–4,15–27`。
其中 pump/bandwidth/gain 的峰值功率直接用 `Energy_nJ/FWHM_fs` 当 MW；量纲正确，
但缺少形状因子、旁瓣信息，不是同平面复场的实测峰值。offset 则是另一手工数组。

线性 `code/linear_cavity/analysis/plot_trend_guided_scan.m:2–7,36–64,78–105,121–148,162–201`
从常量数组输出 CSV/MAT，未调用传播引擎。4 W 历史原始表是 **33.742786 nJ、
23.052788 kW、1.489258 ps**（archive `scan_results_linear_FBG/scan_pump_power.csv:6`）；
trend-guided 是 **33.7 nJ、377.1 kW、84 fs**（data 中同类 CSV `:6`）。不能把后者
视作前者已压缩的独立物理测量。

### H07 archive 的成功/错误标签不能直接作为可行性标签

**已确认问题。** `archive/original_experiment_folder/scan_results_linear_FBG/` 四 CSV
共66行，48 success、18 error。18 error 分为9次进度条取消
（`scan_LR_FBG_bandwidth.csv:2,9–16`）和9次保存步长/长度不整除
（`scan_gain_fiber_length.csv:3,5,7,9,11,13,15,17,19`），不能标为激光不稳定。
`scan_gain_fiber_length.csv:2,4` 两条 success 的 `pulse_survives=0`。

按表内 pump、HR/LR波长、HR/LR带宽、gain length 去重为63个设计元组；45个唯一
success设计、43个唯一存活success设计。缺少无源长度、种子、源码SHA，故这里只是
“记录字段去重”，不是完整物理配置证明。四组的共同基准重复，不能跨训练/测试拆分。

`archive/original_experiment_folder/processed_scan_figures/processed_gain_fiber_length.csv:3`
在0.75 m给出26.169 nJ等数值，对应原扫描CSV `:7` 为error/NaN；其他多个失败中间点
也被填值。**已确认不等价；插值或拟合的具体算法尚未验证。** 不得替它指定未经查证的算法。

archive扫描的指标提取取原始 `output_field` 峰值/FWHM
（`archive/original_experiment_folder/scan_linear_FBG_mamyshev.m:255–269`），当前整理版
则取尾纤后的压缩指标（`code/linear_cavity/scans/scan_linear_FBG_mamyshev.m:285–296`）。
相同列名不保证相同输出面/处理状态，旧新CSV不能直接拼接。

## 中严重性：参数表达、模型一致性与诊断成本

### M01 名义滤波带宽和拒绝端接法须按实际公式解释

**已确认定义不一致；是否符合器件意图需要核对。**
`code/simulation_engine/GMMNLSE/gaussian_spectral_filter.m:43–55` 使用场传递
`H=exp[-(f-fc)^(2g)/(2*f0^(2g))]`，其中 `f0=Bf/(2*sqrt(log(2)))`。
主脚本 `:171,179`、run `:187–205` 使用 g=4，所以强度 FWHM 为
`Bf*(ln2)^(1/(2g)-1/2)`，约为名义频带宽的1.147倍；传入的5/3 nm并非严格
实际波长强度FWHM。

同函数 `:54–55` 透射为 H、拒绝为 1-H；两端功率和为
`H²+(1-H)²`，过渡区小于1。它不是理想无损互补 `sqrt(1-H²)`，也不是固定90%输出。
应记录这是原实现；不能为增大输出自动换接法或带宽公式。

人工平谱fixture实测g=4的强度FWHM/名义频带宽=1.1472549，与公式1.1473356在
网格误差内一致；g=1为1.0000758。在H约0.5的频点，两端功率和约0.500004。
这些测试确认实际实现，并不证明它符合某个真实器件；平谱fixture不是物理运行数据。

### M02 可调用设计接口目前只有两个维度

**已确认接口缺口。** `code/ring_cavity/scans/run_mamyshev.m:1,21–29` 接受 pump、cw2
和 plot_on；后者不是物理设计变量。pump确实进入同向泵（`:50`），cw2进入第二滤波器
（`:115`）；第二带宽与增益长度固定（`:78,114–115`）。主脚本仍须编辑源码改变参数。

| 比较项 | 单点主脚本行号 | 扫描函数行号 | 静态结论 |
|---|---|---|---|
| 1035 nm、32768点、50 ps、50圈 | `Mamyshev_ring_cavity.m:50–52,85–90` | `run_mamyshev.m:63–65,99–106` | 一致 |
| 1 nJ、1 ps、单模零啁啾Gaussian | `:104–107` | `:117–120` | 一致；不代表随机传播确定 |
| 4/.4/1.5/3.2 m四段 | `:64,68–82` | `:78,82–96` | 总9.1 m，一致 |
| 增益→.4→SF1→1.5→SF2→3.2 | `:149–180` | `:166–207` | 一致；SF1拒绝端取出，透射端留腔 |
| SF1=1040/5；SF2=1030/3 nm | `:98–101` | `:114–115` | 默认一致；offset=1040-cw2 |
| gain model 4、ASE忽略、Ntotal覆盖 | `:24–46,61,128–130` | `:40–60,75,137–140` | 一致 |
| L0/v与逐圈time_delay修正 | `:123–128,212` | `:133–140,238` | 一致 |
| 输出后0.2 m尾纤、最终压缩配置 | `:240–271` | `:280–292` | 最终配置一致；主脚本另做一次尾纤前分析/图 |

该表路径前缀分别为 `code/ring_cavity/main/` 和 `code/ring_cavity/scans/`。
运行入口等价性仍需相同seed、同配置的实际比较，不能由静态相似直接宣布通过。

ring原实现修改增益长度不会自动修改无源三段。线性扫描则显式使用
`passiveL=base.passiveL*gainL/base.gainL`
（`code/linear_cavity/scans/scan_linear_FBG_mamyshev.m:120–123`）。二者不同，不能
擅自把线性比例规则移植到ring。

**仅为改进建议：** 四维接口需加入 `filter2_bw_nm/gain_length_m`，冻结长度族规则，
更新总长/t_rep与派生参数，增加单位校验和配置快照。当前没有这样的已实现接口。

### M03 增益浓度有意覆盖，依据尚待补全

**已确认覆盖，数值是否正确需要来源核对。**
`code/ring_cavity/scans/run_mamyshev.m:137–140` 和主脚本 `:128–130` 丢弃 gain_info
计算的浓度，强制 `N_total=9e7 ions/μm³`；主脚本称来自datasheet，但未注明文件/页码。
`code/simulation_engine/GMMNLSE/gain_info.m:189–194,273–277` 使用920 nm、1.7 dB/m、
截面与几何计算另一值。因此吸收输入不是最终实际浓度的决定因素；必须同时保存计算
结果和最终值，不能默默改回计算值。tau、重叠等单位见后文，未因这一覆盖而断言常量错误。

本次重新计算的吸收推算值为 `8.981412593e7 ions/μm³`，与实际使用的9e7接近。
因此不能把此覆盖本身说成巨大增益错误；仍需补全datasheet来源和模型约定。

### M04 warning屏蔽与随机状态使复现/诊断不足

**已确认问题。** 主脚本 `code/ring_cavity/main/Mamyshev_ring_cavity.m:150–152,196–198`
和 `code/ring_cavity/scans/run_mamyshev.m:167–169,221–223` 全局关/开warnings，没有
恢复调用者原状态，异常时恢复语句也不会运行。没有日志警告不能证明没有数值警告。
入口 `close all` 会影响同会话图窗（主脚本`:9`、run`:31`），本阶段采用独立batch隔离。

`code/simulation_engine/GMMNLSE/load_default_GMMNLSE_propagate.m:598–599` 的
`Raman_sponRS=true` 与 photon noise=0 是不同开关；步函数调用rand/randn
（`GMMNLSE algorithm/GMMNLSE_RK4IP_nogain_adaptive.m:38–41`；
`Gain_rate_eqn/GMMNLSE_RK4IP_rategain_adaptive.m:66–69`）。原入口没有rng快照。
相同Gaussian不代表完全确定，固定seed重复也不证明自启动或随机鲁棒性。
拒绝步重抽随机项的影响**需要运行验证**，本阶段不改噪声算法。

### M05 全传播历史、隐藏UI与重复初始化增加成本

**已确认成本来源；峰值内存与时间占比以实测为准。**
`code/ring_cavity/scans/run_mamyshev.m:124–130,173–179` 即使plot_on=false也保存每圈
全部0.1 m传播场。四段约92个合并截面，32768点单模complex double约46 MiB/圈；
50圈仅field约2.25 GiB，另有output_field约25 MiB、增益/RK临时内存和MATLAB运行时。
这是数组结构估算，不是实测RSS。`max_save_per_fiber=1000` 大于当前每段点数，未减存。

run `:149–155` 只隐藏图；loader `:601` 默认progress_bar=true，实际仍创建/更新waitbar
（adaptive gain `:286–305,461–465`）；gain verbose（run`:60`）与逐圈特征长度日志
（`:240–244`）也仍存在。每段重新构造频率、色散、SR索引和Raman核
（`GMMNLSE algorithm/GMMNLSE_propagate_with_adaptive_deltaZ_RK4IP.m:297–425,448–500`）。
默认无项目层parfor；MATLAB内部线程行为不能由此推断。

**仅为改进建议：** 可评估代表圈/端口保存、关闭进度UI和可缓存初始化；需profile后
量化。不能直接增加save_period：默认max_deltaZ与初始dz由它派生（同propagator
`:606–609`、adaptive gain`:309–323`），这样会改变数值算法。不能降低Nt/max_rt伪装成功。

### M06 扫描脚本缺逐次恢复记录，整个扫描超出预算

**已确认问题。** `code/ring_cavity/scans/scan_mamyshev.m:15–16` 是9×5=45点，
超过本阶段最多6尝试；`:38,55–60` 逐点调用但只在全部结束后保存汇总，无逐次checkpoint。
任一点错误可中断并丢失之前未写盘结果；`:21–28` 的零初始化也不能区分未运行/失败。
W→MW（`:45–46`）和ps→fs（`:84`）转换正确。
**仅为改进建议：** 独立attempt记录、失败null+原因和安全恢复，在后续阶段实现。

### M07 内存探测得到0.5 bytes，初始化未失败不表示探测正确

**已确认静默解析错误；本次adaptive基线未因此被阻断。**
`code/simulation_engine/GMMNLSE/gain_info.m:360–378` 的isunix分支调用
`free -b | grep Mem`，不检查状态/空输出就索引 `stats(end)`；原入口未设置memory_limit。
MathWorks明确isunix在macOS也为true，不能把它当Linux专用判断。
参见 [isunix官方说明](https://www.mathworks.com/help/matlab/ref/isunix.html)。

本次原始初始化已返回，但 `baseline_001/configuration.json` 实际记录
`gain_rate_eqn.memory_limit=0.5` bytes。`diagnostic_002/additional_checks.json` 已复现：
命令退出码1，原始输出为 `zsh:1: command not found: free`；原正则提取行号1并除2。
`command -v free` 也返回1/空字符串。因此不是实际可用RAM，初始化的“成功”掩盖错误。
memory_limit也不是进程RAM上限：它在
fixed-step rate-gain路径参与分段（`Gain_rate_eqn/GMMNLSE_rategain.m:82–85`），当前
adaptive路径并不据此限制整个进程，因此该异常不能直接解释本次adaptive传播性能或
判定仿真无法运行。本阶段记录最小修复建议：检查命令退出码/数据有效性，正确区分
macOS并测试含数字stderr；没有修改引擎、安装命令包或改全局PATH绕过。

## 数值与单位核对：已确认和仍需验证的边界

| 项目 | 源码/探针证据 | 结论 |
|---|---|---|
| 场、功率、能量 | `build_MMgaussian.m:4–8,50–58`；run`:215` | sqrt(W)、W；W·ps/1000=nJ；初始能量实测0.99999999999999978 nJ |
| FFT方向 | adaptive propagator`:354,492,519–522`；filter`:54–55` | 时间→频率用ifft，返回用fft，全链一致；不是单凭名称可判的符号错误 |
| Parseval | `solve_gain_rate_eqn_RK4IP.m:15,32–36,213–214`；diagnostic_001 | Aw=ifft(A)时sum|A|²=N·sum|Aw|²；初始频域能量实测1 nJ |
| 频率/波长 | run`:63–64,99–106` | THz=1/ps；lambda_nm=299792.458/f_THz；1035 nm载频约289.65455 THz |
| 时间采样 | run`:99–106`；diagnostic_001 | 50 ps/32768=1.52587890625 fs；40 fs约26.2间隔，df=.02 THz |
| 色散/非线性 | `GMMNLSE_propagate.m:15,38,54`；adaptive propagator`:421–425` | betas为ps^n/m，n2为m²/W，SR为m^-2，非线性系数为W^-1m^-1 |
| 增益单位 | `gain_info.m:189–198,277`；`solve_gain_rate_eqn_RK4IP.m:105,110` | 截面转换为μm²、密度ions/μm³、dz(m)转μm；t_rep使用s |
| Raman卷积归一化 | `Raman_model.m:132–134` | ifft(ha)×Nt×dt与离散卷积约定对应；不是传播收敛证明 |
| 理想TL后处理 | `analyze_field.m:183–184`；`calc_transform_limited.m:45–53` | 去谱相位并零填充，不增加独立物理样本，也不是求解网格收敛 |

本表短文件名在 `code/simulation_engine/GMMNLSE/` 下；run为
`code/ring_cavity/scans/run_mamyshev.m`，adaptive propagator在`GMMNLSE algorithm/`，
增益求解在`Gain_rate_eqn/`。

**本次已检查：** 保存的末圈场均为有限值；拒绝端场时域两端各1%内能量占比合计
约6.386e-5，频域对应占比约1.059e-8，负绝对频率能量占比约9.334e-12。
也已比较trapz与周期sum积分，并验证该保存场的离散Parseval关系；详见基线报告及
`diagnostic_002/waveform_checks.json`。这些检查不覆盖未保存的完整传播过程。

**需要运行验证：** 网格/时间窗/空间步长独立收敛，以及完整传播过程中边界与
非有限值监测。当前频带包含负绝对频率；`spontaneous_Raman.m:12–14` 对负频噪声
置零，但不能据此假定所有传播位置的信号都远离该区域。
`Gain_rate_eqn/read_cross_sections.m:75–108` 在数据外做外推，实际光谱是否进入外推区
也需检验。采样间隔能容纳40 fs不等于已经证明40 fs输出可靠。

## 历史资料与新增候选模型的边界

**已确认，不等价于原基准。** 工作区原有未跟踪
`code/ring_cavity/main/reproduce_ring_spectrum.m:16–20` 默认16384点/100圈；
`run_ring_spectrum_figure.m:6–8` 选table_broadband90、8192点/40圈。
reproduction `:41–75` 分legacy/table的MFD、吸收、浓度、重叠处理，`:102–110` 分
90/10宽带或拒绝端耦合，`:173–180` 分带宽公式，`:119–164` 用另一停止/尾纤协议。
即便legacy分支也不是原入口的严格等价封装。六组此前ignored MAT/CSV仅为旧计算证据，
本阶段不重算、不覆盖、不记入新尝试。`README_reproduction.md:15–33` 已说明假设。

**已确认，仅显示处理。** `code/ring_cavity/analysis/plot_phase_surfaces.m:23–35` 的
101×101插值网格默认关闭，`:46,57,68` 的shading也仅显示；
`export_ring_spectrum_display.m:14–35` 由单个复场线性插值波长网格再高斯平滑，保存
source_result与处理宽度。多条平滑曲线、端口、尾纤或谱点都不是新独立仿真。

**已确认来源版本差异。** archive `scan_mamyshev.m:6–7` 是cw2=1026:2:1036，
当前 `code/ring_cavity/scans/scan_mamyshev.m:15–16` 从1028开始；当前保存列表
`:55–60` 也增加压缩指标。相同MAT文件名不能证明同一源码版本。
`diagnostic_002` 实际读取历史MAT，确认maps为9×6、cw2=1026:2:1036，仅有能量、
原始FWHM、fluctuation、convergence和state等旧字段，没有当前新增压缩指标。
`plot_phase_surfaces.m:10–16` 优先generated再回退历史文件，实际加载来源必须记录。

**已确认缺少演化图输入。** `code/linear_cavity/analysis/plot_roundtrip_evolution_maps.m:18–24`
要求五个evolution_P*.mat，`:36–40` 回退后直接load；本次包含ignored的data/results/archive
清单未找到它们，不能把旧图或注释当作现存逐圈原始数据。

**需要来源验证。** `docs/PARAMETER_MAPPING.md:7–14`、`docs/LITERATURE_NOTES.md:18–24`
说明ring参考文献SF2=1036 nm、本项目基准1030 nm；后者`:35–41` 说明线性模型不含文献
外部GMN放大器。本次核对了项目说明，未重新审读论文PDF；不宣称独立核验文献全部数值。
文献性能不能作为当前不同模型必须达到的目标。

## 本阶段结论与下一步边界

依赖/初始化检查已提供正面证据，但H01–H05使原后端不能未经检验就作为定量训练真值。
当前已有B类（实现/指标/状态）确认问题与D类成本来源；C类“数值可靠但激光性能差”
需要先通过数值和状态检查。真实运行是否完成、成本与观测属于哪些类别，以
[基线报告](BASELINE_REPORT.md) 为准，不从静态审计猜测结果。

推荐后续优先 **① 修复并保留原后端**：先对NaN收敛和拒绝步状态回滚建立独立测试，
明确legacy与修复后的参数派生、输出面及标签协议，再进行有预算的收敛检查。
尚无依据冻结已可靠的四维参数域，也未申请或实现reduced-order替代后端。
此建议不授权自动进入Phase 2。

详细路径、机器信息、完整探针和源码审计工作记录保存在ignored的
`reports/local/phase1/`；公开文档只记录仓库相对路径和必要测量。
