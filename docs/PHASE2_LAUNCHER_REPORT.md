# Phase 2 第三批：实际诊断接线与单次最终记录

2026-09-27，`launchprep_001`。基于 `feature/mamyshev-ml-mvp` /
`489bf4242f9b5266d47f8892840a24af66931ff0` 的现有未提交工作；没有切换分支或提交。
Phase 2 仍为 **in_progress**。本批只做组件验证，完整腔体运行 **0 次**。

本批落实第二批的两项接线缺口。下面的整腔命令已有实现，仍须用户另行批准，未执行。
三项就绪状态均为 true（仅指可以申请下一次运行）；completed 仅指执行完成，
不表示物理验证通过。

## 本批实际改动

- `code/ring_cavity/scans/run_mamyshev.m`：可选独立诊断参数；真实初始化后、首次传播前
  保存 B；显式 preflight 正常返回；在实际腔段、尾纤、压缩调用处记录 C。
  原有尾纤/压缩器/死亡阈值常数仅提为同值局部变量供计算和记录共用。
- `code/ml_bridge/MamyshevCapture.m`、`MamyshevObserver.m`：A/B/C 记录、独立只读标量
  计数、正常段边界、未决段及最终所需记录完整性。没有使用主动 test_hook 作为观察器。
- `mamyshev_compare_configuration.m`、`mamyshev_source_identity.m`、
  `mamyshev_write_diagnostic.m`、`mamyshev_artifact_integrity.m`：内容核对、真实源码核验、
  不消耗物理 RNG 的临时写盘、已写记录的摘要核验。
- `run_mamyshev_recorded.m`、`write_mamyshev_record.m`：独立 run_context、真实模式拒绝
  backend 注入、候选身份/RNG/完整性记录、检查写入和关闭错误。
- `GMMNLSE_adaptive_rategain.m` 与
  `GMMNLSE algorithm/GMMNLSE_propagate_with_adaptive_deltaZ_RK4IP.m`：仅加入真实事件计数
  和已解析步长观察点。**这两个引擎源码及哈希确已改变**，没有修改数值更新公式。
- `src/mamyshev_ml/supervisor.py`、`scripts/run_mamyshev_once.py`、
  `code/ml_bridge/launch_mamyshev_once.m`：可复用单次执行、最终合并和明确的真实启动入口。
- `tests/run_matlab_short.py`：新增独立预算目录、一次 preflight 约束，复用原进程组清理；
  补齐清理异常记录和已消失进程组的只读核查。
- 新增/扩展 Python 与 MATLAB 测试，更新 `docs/EXECUTION_STATUS.md` 和本报告。

完整本批文件清单、起点副本与 **相对本批起点** 的 `launchprep.patch` 位于
`reports/local/phase2/launchprep_001/`。没有把 Phase 1、repair_001、readiness_001
或原用户修改记作本批新修复。

## 实际参数，而非身份 JSON 的复述

| 层次 | 采集位置与内容 | 本批证据 |
|---|---|---|
| A | launcher/wrapper 实参 PumpPower、cw2、seed；物理、数值、wrapper/result/observer 版本；源码清单、commit/工作树、RNG | 实际 preflight 请求；synthetic 跨语言请求使用单独身份 |
| B | `run_mamyshev` 的 loader/gain_info 后，首次传播前；fiber_cavity、sim_cavity、gain_param、初场/网格、停止条件及随机开关 | 原 Nt=32768、50 ps、max_rt=50 的唯一初始化检查；正常提前返回 |
| C | 每次实际传播调用前的 fiber/sim/gain_param/t_rep；引擎初始化后的 max/initial dz、threshold；尾纤及压缩器调用实参 | 短 fixture 验证观察点；**原基准所有 C 位置仍 deferred_to_authorized_run** |

每份 JSON 包含采集位置、时点、来源、单位和 observed/deferred 状态。数组存 MAT，JSON
保存维度、类型、有限性和引用。按段核对 gain_param 数组与 B 引用相同，动态 t_rep 单独
保存；不会将 B 的计划值说成已解析 C。记录/hash 操作不调用 MATLAB rand/randi。

唯一初始化检查 `preflight_001`：`propagation_started=false`、`full_cavity_attempts=0`，
没有 `matlab_candidate.json`，RNG 前后相同。与直接捕获的
`reports/local/phase1/baseline_001/configuration.mat` 做 **256 项叶节点**检查，逐项
比较类型、尺寸及值（复数组也比较），结果全部相同、意外差异 0。没有使用 baseline_002
引用副本，也没有改变参考文件。Python 最终 gate 另核对可读配置与 baseline_001 JSON。

本次实际观测：gain_info 的 N_total=`89814125.93190747`，最终仍覆盖为 `90000000`；
增益声明 MFD=11.1 μm、SR=`1.0333897774005056e10 m^-2`；无源声明 MFD=10.5 μm、
SR=`3.596467889937611e10 m^-2`、面积=`2.7805058479678165e-11 m²`。
H02 保持原状：无源 SR 源于 5.95 μm，没有重算，也没有确认 10.5 μm 为真实器件参数。

差异分类：版本/工作树/采集时间等是新增元数据，不要求整份结构字节一致；CUDA 安装路径
及观察器元数据有明确排除规则，本次旧可比字段没有实际排除差异。MFD/SR、不变的 N_total
覆盖和旧内存探测属于已知 legacy 问题。计算所得 N_total 与死亡阈值原来不在 baseline_001
MAT，现新增实际捕获，不冒称这两个字段已有独立旧快照数值对照。

## 只读计数与默认路径

关键插入形式（两个生产引擎，原计算语句保留）：

```matlab
if ~isempty(readonly_observer), readonly_observer.trial(); end
% 原始 RK4IP 数值 trial，不由观察器返回 success/dz
if ~success
    if ~isempty(readonly_observer), readonly_observer.reject(); end
end
% 原始接受后状态更新
z = z + sim.deltaZ;
if ~isempty(readonly_observer), readonly_observer.advanced(z); end
```

每步只增减标量；在开始、默认值解析和正常返回边界刷摘要，不写逐步场历史。
实际位置：增益引擎 340/377/414/461 行；无源引擎 619/641/658/691 行分别为
已解析值/trial/reject/z 推进观察点。Capture 100 行记录实参，155 行汇总；
supervisor 97/164/238/340 行分别执行协议校验、合并、真实记录 gate 和单次监控。
只有实际 GMMNLSE 返回后调用 complete_segment；正常段断言
`trials = rejections + accepted_advanced_steps` 且 pending=0。
活动段磁盘计数为 null/incomplete；捕获异常时的部分计数保留来源及未决 trial，不补 0。
同一无源路径的腔段与 pigtail 有不同 segment_id、圈号。

0.004 m 人工短段实测计数如下；不是完整腔体或物理设计样本：

| 路径 | trial / 拒绝 / 实际推进 / 未决 | 正常完成 |
|---|---|---|
| 增益控制 | 3 / 0 / 3 / 0 | 是 |
| 增益受控两拒绝 | 6 / 2 / 4 / 0 | 是 |
| 无源腔段 | 23 / 0 / 23 / 0 | 是 |
| pigtail身份控制 | 23 / 0 / 23 / 0 | 是 |
| trial后人工异常 | 1 / 0 / 0 / 1（异常处理器所见部分计数） | 否，incomplete |

人工异常发生时，未刷出的磁盘活动段计数是 null，而不是上表异常处理器后来取得的值。

默认无 readonly_observer 时不调用观察器。test_hook 的“关闭”仍须删除字段；真实 capture
拒绝任何 test_hook 字段，包括 []/false。真实 wrapper 先拒绝组件 backend 注入。
同一生产 fixture 的观察关闭/开启输出及相关保存状态精确相等，比较前均检查有限；
RNG 状态精确相同。确定性比较容差为 0，严于之前的 1e-12 绝对+相对规则，未放宽容差。
两次受控拒绝使用真实增益更新，泵实际变化；这是显式 synthetic 协议。

## 最终记录的所有权和失败规则

MATLAB 仅写 `matlab_candidate.json`；父进程写 `runner_record.json`，且是
`final_result.json` 唯一 writer。不同文件、独占 run 目录、同名 run 拒绝覆盖。继续使用
`safe_result_v1`，只增加 provenance/observability/supervisor 元数据，原指标协议不变。

| 场景 | 最终处理 |
|---|---|
| 父进程已确认 timeout/STOP，后来退出 0 或有成功候选 | 首个已确认停止事件优先，保留事件列表；同轮观察时先记录 STOP |
| 非零退出＋可信 failed/numerical_error | failed，并保留具体数值错误及退出码 |
| 非零退出＋completed | failed，记录退出/候选不一致 |
| 退出 0＋候选缺失、损坏、协议/身份不符 | failed，不采信该候选指标 |
| 退出 0＋候选明确失败 | 仍失败，记录包装/退出不一致 |
| 正常结束＋合法完成候选＋必要记录完整 | 才可 completed；仍 undetermined / not_verified / false |

父进程校验 run_id、真实/fixture 来源、版本、源码、seed/输入、单位、有限性及合法圈数。
真实模式还检查实际 B/C 字段、与旧基准一致的初始化、实际段序列/实参、计数关系和记录
摘要；文件哈希只验证写盘完整性，不能代替前述参数内容检查。
所有失败最终记录的各输出面及参考科学指标为 null+reason；部分候选只保留为诊断文件。
圈数/进度带来源和完整性标记，不生成物理不稳定标签。

父进程采用临时文件、fsync、同文件系统 hard-link 最终提交，已有 final（即使损坏）也
拒绝覆盖。写盘失败向上抛错、尽力写 supervisor_error，并清理本次进程组。
父进程强杀/阻塞 I/O 仍可能留下无 final 或 running，必须人工核查，绝不自动补成功。

## 测试口径、实际成本及异常

| run_id | 外部 MATLAB 墙钟或保守计费(s) | 退出码 | 结果 |
|---|---:|---:|---|
| observer_001 | 15.042172 | 0 | 首版观察器4组＋既有62组回归通过 |
| capture_001 | **180（保守计费；实测时长未保存）** | null | 12项组件断言通过；父清理失败，见下文，进程不计成功 |
| preflight_001 | 16.515068 | 0 | 唯一完整配置初始化，256项内容比较通过，零传播 |
| observer_002 | 14.616009 | 0 | 最终5组观察器＋12组捕获检查＋既有62组通过 |
| capture_002 | 13.466417 | 0 | 捕获最终14组通过（包含新增2组文件摘要检查） |
| candidate_001 | 13.227925 | 0 | synthetic MATLAB→父进程 final 通过 |
| candidate_002 | 12.898978 | 0 | 完整补齐缺失压缩场契约后的同一跨语言案例重复，通过 |

共7个串行 MATLAB 进程；正常终态可测总计 **85.766570秒**，另对未完成账目保守计费
180秒，预算合计 **265.766570/600秒**。每进程限制180秒；无自动重试、GPU或parpool。
不能把保守计费说成该失败进程的实测耗时。跨语言最终父提交前总墙钟为12.926786秒。

新增覆盖：MATLAB观察器5组、配置/身份/写盘14组、跨语言synthetic链路1种；一次真实
初始化（256个叶节点不是256次仿真）。重复回归：H01 rollback 6组、第二批H01 5组、
wrapper 11项、H04 20项、结果契约20项，共62组；重复执行不增加独立测试数量。
Python最终 **30个 unittest 方法通过**，内部2.034秒：11个既有＋19个新增；子场景
不重复计为独立方法。包括完整合并矩阵、真实短子进程、fork后代清理、写盘失败、
非法数据及缺失/损坏观测文件。新source/记录哈希和实际函数路径均保存。

预期错误仅为组件内断言的 timeout/STOP/拒绝覆盖/写盘失败/异常等场景，没有额外运行
旧缺陷 before 套件；上述 capture_001 和一次Python测试失败是非预期操作/fixture问题，
单列而非混入“全部通过”。`git diff --check`通过。384份此前阶段证据文件哈希保持相同，
没有丢失起点文件。整腔集成仍明确**未执行**。

已发生的非预期操作失败：capture_001 的 12 项 MATLAB 组件断言通过，但父进程在终态
写盘前收到 killpg PermissionError。只读进程表确认本批组已消失；未终止其他 MATLAB。
原未完成 runner_record 原样保留，外部核查单列 runner_reconciliation.json，标 failed，
精确墙钟/退出码为未知，**保守计满 180 秒预算**，不把它包装为成功进程。
修复后仅当 leader 已退出且成功核实其进程组不存在才接受 EPERM；活组或核查失败仍报错。
独立失败核查仅用于全额扣减预算，不改写原父进程记录，更不能将其转成 completed。
另有一轮 Python 新测试因 macOS 无 `/bin/true` 失败，已改为 `/bin/sh -c 'exit 0'`；
这是 fixture 可移植性问题，没有启动 MATLAB，相关失败日志保留。

本地命令、原始 stdout、运行记录、fixture 波形、参数/计数摘要及保护检查全部存放在
`reports/local/phase2/launchprep_001/`。该目录仍由 Git 忽略，不复制到公开报告。

## 已实现但未执行的单次整腔命令

无传播检查（只打印，不创建真实尝试）：

```sh
/opt/homebrew/Caskroom/miniforge/base/bin/conda run -n mamyshev-ml --no-capture-output python \
  scripts/run_mamyshev_once.py --dry-run --run-id validation_001 \
  --matlab /Applications/MATLAB_R2025a.app/bin/matlab
```

**下面的独立动作仅供下一批审核，本批未执行：**

```sh
/opt/homebrew/Caskroom/miniforge/base/bin/conda run -n mamyshev-ml --no-capture-output python \
  scripts/run_mamyshev_once.py --execute-real --run-id validation_001 \
  --matlab /Applications/MATLAB_R2025a.app/bin/matlab
```

启动后取消：`touch reports/local/phase2/single_validation_001/validation_001/STOP`。
父进程只终止自己启动的进程组；真实批次目录只允许一个已保留尝试，无自动重试。
单调时钟总限 900 秒，包含 MATLAB 启动/退出，保留 30 秒用于组清理、源核验和 final
提交；记录 MATLAB 进程墙钟及父进程提交前总耗时。该预留不保证强杀或阻塞 I/O 下必有 final。

固定 `run_mamyshev_recorded(4,1030,false,...)`、seed=0/twister；保留原 Nt、时间窗、
max_rt、容差、随机开关、MFD/SR、1-H、滤波公式、长度规则及压缩假设。启动后再次从
真实局部变量核对 B，C 从实际调用/引擎处采集，不把本批 preflight 文件直接当新运行配置。
记录当前修复集合、源码、RNG、有效圈数、停止原因、分平面输出、计数及成本。

可与 Phase 1 比较同配置、同输出面/处理定义的旧数值、停止圈数和成本；不能将变化全部
归因于 H01，也不能把同 seed 当作独立收敛或稳定单脉冲验证。停止逻辑已包含 H04 安全修复，
源中加入了诊断开销；随机拒绝语义尚未验证。

## 阶段边界与最终状态

| 状态 | 结果 | 依据与限制 |
|---|---|---|
| runtime_observability_ready | **true** | A/B实际初始化、精确内容对照、增益/无源/尾纤计数和C调用组件证据齐备；真实整腔C仍待获批运行 |
| supervisor_finalization_ready | **true** | 合并矩阵、真实短子进程、实际MATLAB synthetic候选→父final及写盘/清理组件通过 |
| ready_to_request_single_run | **true** | 两项接线阻塞已落实；可以申请最多1次900秒运行，但本批未获授权启动 |

本批限定组件范围无剩余阻塞。静态检查、组件执行和真实无传播初始化已有证据，
**完整腔体集成仍未执行**；完整传播的成本、C实测值、实际接受/拒绝次数及结果仍未知。
文件摘要最终化为初始化之后补入的纯记录检查，已单独短测；没有重做初始化或把原
preflight重新标成新源码运行。各次保留各自源哈希及版本身份。

未执行：完整腔体集成、完整线性腔、历史扫描、非零反向泵/随机拒绝扩展、独立网格/
时间窗/步长收敛、四维接口、采样/训练/优化、替代模型。未改物理约定、README/简历性能，
未安装依赖、改其他环境/全局配置，未 reset/clean/stash/commit/push/PR/合并。
H02 新物理参数未确认；physical_state=undetermined、训练真值资格=false。
本批结束即停止，Phase 2B/3 未开始，等待审核。
