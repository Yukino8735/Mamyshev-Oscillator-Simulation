# Phase 2 第一批：最小修复与安全结果契约

日期：2026-09-27；批次：`repair_001`。本批完成后等待审核，整个 Phase 2 仍为
`in_progress`。Phase 2B、Phase 3 及以后没有开始。

本批没有完整腔体运行，也没有新的物理设计或训练样本。修复后短测通过，只证明以下
限定的软件行为；当前后端仍不得作为已经验证的训练真值。Phase 1 的29.869 fs /
2.779 MW仍是未经独立验证的legacy输出，不是本批验收目标或修复后的性能。

## 起点、证据和实际修改范围

实际在本地Mac、预期项目目录执行，分支保持 `feature/mamyshev-ml-mvp`，起始commit为
`489bf4242f9b5266d47f8892840a24af66931ff0`。依据当前未提交工作区，没有取远程旧版本
覆盖本地内容。已读取AGENTS、项目规范、Phase 2提示词、AUDIT、BASELINE_REPORT、
EXECUTION_STATUS、相关测试和Phase 1监控器；本次明确指令限定了第一批，优先于
AGENTS中旧的“仅Phase 0授权”及规划中的完整Phase 2范围。

本地 `reports/local/phase2/repair_001/` 保存：起始commit/分支/status、staged及
unstaged差异、1047个原有文件哈希、相关源码修复前副本、61个Phase 1证据文件哈希。
现有两项Python配置测试在修复前通过。没有覆盖 `reports/local/phase1/`。

本批允许改变的原有文件如下；行号对应修复后源码：

| 文件 | 修改位置与用途 |
|---|---|
| `code/simulation_engine/GMMNLSE/Gain_rate_eqn/GMMNLSE_adaptive_rategain.m` | 343–352：两泵snapshot/restore；355–361、387–396、417–419：默认关闭的fixture观察点；402–410：无进展重试显式失败 |
| `code/simulation_engine/GMMNLSE/check_convergence.m` | 1–99：兼容输入、完成圈数、有限性与空/零保护；105–151：保留原判据并检查派生量；新增诊断输出 |
| `code/ring_cavity/scans/run_mamyshev.m` | 222–236：tracker前保护；两处分支传实际rt_num |
| `code/ring_cavity/main/Mamyshev_ring_cavity.m` | 196–206：相同保护与完成圈数 |
| `code/linear_cavity/main/Mamyshev_linear_cavity.m` | 254–272：相同共享helper调用的保护与完成圈数；未运行线性腔 |
| `docs/EXECUTION_STATUS.md` | 记录第一批完成待审，保留Phase 1历史证据 |

新增生产代码在 `code/ml_bridge/`：`mamyshev_result_record.m`、
`mamyshev_failure_status.m`、`write_mamyshev_record.m`、`run_mamyshev_recorded.m`。
新增冻结身份为 `configs/legacy_physics_identity.json`。回归源码与人工fixture生成方法
位于 `tests/matlab/` 及 `tests/test_physics_identity.py`、`tests/test_short_runner.py`；
短测监控器为 `tests/run_matlab_short.py`，不是只保存在ignored目录里的测试。

原有 `.gitignore` 修改、Phase 0文件、规划和reproduction文件保留。原RK4IP步函数、
rate solver、loader、滤波器、截面数据及历史数据未改。完整文件清单、修复前后差异和
允许变化之外的哈希核验见本地 `preservation.json`、`repair.patch`、`final_manifest.json`。

## H01：拒绝试探不能污染重试起点

实际调用链为 `GMMNLSE_adaptive_rategain` → `GMMNLSE_RK4IP_rategain_adaptive` →
`solve_gain_rate_eqn_RK4IP`。已重新检查当前源码，不只依赖旧报告行号。

| 状态 | 试探行为与处理 |
|---|---|
| 信号复场、a5导数缓存 | 步函数改写；原外层已有snapshot/restore，保留并验证 |
| 前向/后向泵功率 | 步函数改写；补上两个snapshot和两个restore赋值 |
| z、last_deltaZ | 试探失败前未推进，精确检查retry起点不变 |
| N2_next | 当前trial的输出，不作为下一个trial的输入；每次重算，接受后才用于保存，无需盲目回滚 |
| 保存历史、脉冲居中及时间延迟 | 在接受之后处理，拒绝trial尚未改变这些量 |
| sim.deltaZ、success/ever_fail、错误信息 | 重试控制状态；保留缩小步长，不恢复为失败的大步长 |
| 随机发生器状态 | 本批不改变；确定性fixture隔离回滚问题，随机拒绝协议仍未验证 |

`tests/matlab/helpers/gain_rollback_fixture.m:1` 生成32点人工输入，非零4 W同向泵，
保留非零色散和Kerr，关闭Raman仅用于该fixture。生产Nt、max_rt、容差及随机开关未改。

默认不存在的 `sim.adaptive_deltaZ.test_hook` 观察真实试探前后状态，可在真实kernel
已更新泵后强制一次拒绝并指定更小重试步；没有替换数值更新函数。测试在首个接受trial
后、z推进与保存前用专用异常结束，所以这是**接受trial状态检查，不是完整增益段运行**。
无拒绝控制还与未经修改的生产RK4IP函数直接调用作比较。

比较规则在执行前写入 `tests/matlab/test_gain_rollback.m:6–9` 及本地设计记录：
需要恢复的signal/a5/两泵/z/last_deltaZ采用 `isequaln` 或精确相等；确定性接受结果
的全部复场、a5、两泵和N2使用 `max_abs_error <= 1e-12 + 1e-12*max(abs(reference))`。
该容差容纳double舍入，远小于原泵泄漏；未按测试结果放宽。

| H01检查 | 修复前实测 | 修复后实测 |
|---|---:|---:|
| 第一次真实试探的前向泵变化 | −0.00091541891565105615 W | 同一变化，证明fixture并非恒定泵mock |
| 重试起点的前向泵泄漏 | −0.00091541891565105615 W | 0 |
| 需恢复状态精确一致 | 失败：前向泵不同 | 通过 |
| 拒绝一次再接受小步 vs 直接接受小步 | 失败；场max差1.430317764e−7，泵max差9.153980889e−4 W | 场、a5、两泵、N2全部差0 |
| 无拒绝路径 vs 原生产RK4IP | 全部比较差0 | 全部比较差0 |
| 缩小后的重试步长保留 | 通过 | 通过 |

在失败分支新增 `NonProgressingRetry`：新步长必须为有限、实、正标量，严格缩小且能使
z产生浮点进展；否则显式报错。没有改变误差公式或接受条件。NaN步长、零步长、不缩小
步长三种注入均发生在真实kernel试探之后，均在下一次trial之前正确失败。

本测试只覆盖首步、同向泵、初始空a5缓存的确定性输入。非空缓存起点、非零反向泵、
连续多次拒绝、居中/保存后路径和随机拒绝协议未验证；guard的负数/复数/Inf/非标量及
z+dz舍入分支仅静态核对，未逐项动态覆盖。无源及其他方向更广泛重试防护仍未完成。
**H01对Phase 1两次基准的实际影响仍未量化。**

## H04：非有限数据不能变成收敛证据

旧4个可选参数顺序与返回前3项保持兼容，新增第5可选参数 `completed_rounds` 和第4
输出diagnostic。默认将传入的全部历史视为有效观察；预分配调用必须显式传圈数或切片，
不再通过“最后非零值”猜长度。当前code下5个实际调用点全部传 `1, rt_num`。

先对有效历史和实际被检查场做完整有限性检查，不删除NaN/Inf、不把reset前的坏数据
隐藏掉。非有限值分别抛出 `check_convergence:NonFiniteEnergy`、`NonFiniteField`；
有限输入计算相对差发生溢出时抛 `NonFiniteDifference`。真实调用在tracker之前也检查
本圈能量和场，避免先被findpeaks等报为不明错误。空、不足、全零场、零分母保留未收敛
及可追踪原因。原least_rt、容差和相对差公式未改变，没有新造稳定性阈值。

原实现实测：有限正常控制通过；NaN能量、Inf能量、有限能量配NaN场三项安全断言
**预期失败**。修复后 `test_convergence_safety.m:23–60` 共20项通过，包含上述案例、
早期有效NaN、复场Inf、空/不足/全零、零分母、显式排除预分配尾部、不能过滤真实末圈0、
不猜尾部、无效圈数、派生差溢出、行列历史一致，以及等能量单/双Gaussian对照。

布尔结果、原因、错误ID和圈数精确比较；仅单双Gaussian的人工等能量构造允许1e−14
相对差。两者都可以满足旧能量判据，但diagnostic及结果契约均为 `undetermined`，
不产生 `stable_single` 真值。没有新增循环或无进展路径。

archive与third_party历史调用保持不动；未来若旧入口解析到新helper，需要明确有效
历史长度，不能假定旧的“零尾部自动推测”仍生效。带图分支、整腔和线性腔集成未执行。

## H02：冻结旧物理身份，未修正MFD

`configs/legacy_physics_identity.json` 的 `legacy_ring_phase1_v1` 与数值修复版本
`repair_001_h01_h04`、结果协议 `safe_result_v1` 分开。Pump/cw2及随机初态另记，
固定物理身份不要求数值修复前后逐元素一致。

- 无源声明MFD=10.5 μm；loader先按5.95 μm派生，再被入口覆盖MFD字段。
- 实际SR=`3.5964678899376106e10 m^-2`，有效面积及gain_Aeff均为
  `2.7805058479678165e-11 m²`，三段无源及尾纤沿用这些值。
- 10.5 μm没有被认定为真实器件参数，没有重算生产SR，也没有用3.114比例修正输出。
- 1-H端口、原滤波公式、N_total覆盖、固定无源长度、随机开关、尾纤和压缩器假设均保留。
- 冻结值与Phase 1实际解析快照核对；loader和截面源哈希也通过Python检查。

H02状态明确为：**派生不一致已确认；旧实际参数已冻结；新的物理参数约定尚未完成
确认/运行验证。** 该JSON是身份记录，不是已经实现的四维配置驱动接口。

## 实际使用的安全记录与序列化路径

`mamyshev_result_record.m:1–120` 分开记录job_status、stop_reason/failure_reason、
physical_state、numerical_validation、legacy_flags；未知物理状态保持undetermined，
`eligible_as_validated_training_truth=false`。成功返回、max_rt、观察不足、失败、超时和
取消不能互相替代。已存在timeout/cancelled/具体失败原因时，partial NaN只增加诊断，
不会覆盖原停止原因。非有限完整返回则降为failed/numerical_error。

`mamyshev_failure_status.m:1` 处理生产NonFinite、NonProgressingRetry与取消异常；
`write_mamyshev_record.m:1` 是实际JSON写盘路径，NaN序列化为null并保留missing_reason，
拒绝覆盖已有证据。`run_mamyshev_recorded.m:1` 将原函数接入这些生产函数；**本批没有
调用该整腔包装入口**。进程被外部超时终止后的record接入仍未做整腔集成验证。

| 输出位置 | 记录与来源 |
|---|---|
| SF1拒绝端、尾纤前、未压缩 | 原能量nJ；保存复场提取峰值W；原全局半高跨度ps。注明原能量在tracker居中前积分 |
| 尾纤后、未压缩 | 由实际返回复场提取峰值W，按t(ps)积分得nJ；未返回的独立尾纤宽度留null+reason |
| 压缩分析后 | 原压缩器局部峰宽fs及复场分析峰值W；宽度定义与全局跨度分开；压缩能量和复场仍null+reason |

不以energy/FWHM代替真实峰值，不用上游能量填压缩能量；理想去相位宽度单列参考。
`test_result_contract.m:18–37` 的20项测试实际执行上述记录器/错误映射/JSON写入及读取，
包括缺失值、输出面、ML_state=1但未知物理状态、超时/取消、max_rt、partial NaN保留
原错误、圈数合法性、功率溢出、真实check_convergence异常和单双Gaussian。
另只读Phase 1 result.mat通过同一记录器，明确标为legacy历史读取，不是新仿真。
整腔wrapper的try/catch接线仅静态审查，未以mock整腔代替验证。

## 实际运行、成本与测试统计

Python全程使用指定现有mamyshev-ml；MATLAB使用指定R2025a。没有安装依赖、修改环境
或全局配置。准确绝对路径命令、UTC时间、退出状态在本地 `COMMANDS.md` 和各次
`runner_record.json`；公开报告不复制本机绝对路径。

| run_id / 执行入口 | 外部墙钟秒 | 退出码 | 结果含义 |
|---|---:|---:|---|
| h04_before / `run_convergence_before.m` | 10.929546 | 0 | 1控制通过、3原缺陷安全断言预期失败；复现脚本确认了这些失败 |
| h01_before / `run_gain_before.m` | 9.312480 | 0 | 5组回归断言中3控制通过、2原缺陷预期失败；复现成功，不是修复通过 |
| regression_001 / `run_repair_regressions.m` | 10.107789 | 0 | H01 6组断言（含3种retry保护）通过；H04 20项、结果契约20项通过 |

MATLAB **3个串行短测进程，外部墙钟总计30.349815秒/600秒**，每次小于180秒；
无MATLAB超时、取消或重试。**完整腔体真实运行0次。** fixture的单步kernel调用不
计为腔体设计、独立物理结果或训练样本。

监控器沿用Phase 1独立进程组策略，串行锁、已用墙钟累加、不可覆盖run_id和关停预留
限制本批成本。只有本次启动的组可被终止；Python测试使用自己的sleep进程验证取消、
超时、对照进程不受影响，以及记录写盘异常仍清理子进程。没有终止其他MATLAB会话。

Python修复前现有2项通过；中间5项通过；最终 **9项通过、0失败、0跳过**，包含原配置、
冻结身份/源哈希、隔离、预算、退出码、超时和写盘失败清理。最终unittest内部耗时
0.480秒，外部启动耗时另存 `python_tests_after.json`。`git diff --check`通过。
原缺陷预期失败、修复后通过、未运行项目在本地 `test_summary.json` 分栏，不混称全部通过。

## 未执行、残余风险及下一批建议

本批要求的短回归没有阻塞或未通过项。以下明确未验证，不计入通过统计：

- H01在Phase 1基准中的实际触发次数、误差，以及随机拒绝/非零反向泵/多拒绝等扩展情况。
- 修复后完整腔体运行、真实wrapper集成和超时后结果契约衔接。
- H02新器件/物理约定、MFD对照，四维接口，网格/时间窗/步长/容差独立收敛。
- 足够观察窗口、单/多脉冲与呼吸分类、不同seed、自启动和实验有效性。
- M07内存探测、更广泛重试防护、warning管理、性能及保存策略；没有为关闭全部审计项扩展本批。

建议下一批先审核本批补丁与物理参数约定，再决定扩展局部回归；任何修复后真实整腔
比较或独立收敛计算需要单独确认预算与方案。本批不执行这些计算，不扫参、训练、优化、
建立替代后端、修改简历/README性能、commit、push、PR或合并。现在停止等待审核。
