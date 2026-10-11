# Phase 2 第四批：单次真实整腔集成尝试

2026-09-27，`single_validation_001/validation_001`。

**本次正常整腔集成验收未完成：唯一尝试因外部预算停止，父进程 final 为 `timeout`。**
真实生产入口、实际参数捕获、已完成段的计数，以及超时清理→父进程安全 final 路径已有
实测证据。尾纤、压缩分析和正常返回后的完整候选/记录 gate 链路没有完成，不能标为通过。
没有第二次尝试、修复重跑或额外 MATLAB 任务。Phase 2 仍为 **in_progress**，等待审核。

## 授权、起点与实际命令

本批新指令只授权最多一次真实启动、supervisor 总墙钟900秒。第三批“未授权真实运行”
的历史报告保持原样；本批没有回写其结论或更改其源身份。

- 本机 Darwin/arm64；仓库根目录和分支 `feature/mamyshev-ml-mvp` 已核对。
- 基础 commit：`489bf4242f9b5266d47f8892840a24af66931ff0`，保留所有原有未提交修改。
- 230份生产源码、配置、测试/启动器及物理数据的清单与第三批最终
  `launchprep_001/candidate_002/launch_request.json` 完全一致；第三批最终文件哈希无差异。
- 源清单摘要：`e820c77de90f77ec6911d91cb40866b2fcdb41a02b560f3e216da59060f8d1cd`。
  这是当前最终版本，不是较早 preflight 的代码身份。
- 启动前真实批次目录不存在，未有预留/结果。旧 capture_001 的独立失败核查依据保留；
  只读进程表确认旧测试PID/进程组均未出现，没有凭旧PID发送信号。
- 静态检查确认真实入口没有组件 backend 注入，不定义任何 test_hook 字段；Capture
  仍拒绝字段存在（包括 []/false），独立只读观察器保持原实现。
- 只执行一次无传播 `--dry-run` 核对路径/预算，没有额外 MATLAB preflight、fixture或回归。

从仓库根目录执行的唯一真实命令：

```sh
/opt/homebrew/Caskroom/miniforge/base/bin/conda run \
  -n mamyshev-ml --no-capture-output python \
  scripts/run_mamyshev_once.py --execute-real --run-id validation_001 \
  --matlab /Applications/MATLAB_R2025a.app/bin/matlab
```

实际输出目录与第三批一致：
`reports/local/phase2/single_validation_001/validation_001/`。
没有修改源码、物理/数值配置、supervisor、观察器或协议。没有安装依赖、修改环境或全局
配置，没有切分支、reset/clean/stash、commit/push/PR/合并。

## A. 调用链、尝试和最终状态

实际链路：`run_mamyshev_once.py → supervisor.execute_once → MATLAB -batch
launch_mamyshev_once → run_mamyshev_recorded → run_mamyshev → GMMNLSE_propagate`，
进入仓库的增益及无源自适应生产路径。不是诊断副本、reproduction入口或简化模型。
本次配置记录的实际函数解析路径与仓库相符。

| 项目 | 实际结果 |
|---|---|
| 尝试是否预留 | 是，attempt=1 / max_attempts=1，唯一 validation_001 |
| MATLAB是否启动 | 是，父监控器创建独立进程组并记录PID；没有额外传播进程 |
| 是否进入真实传播 | 是；21次实际段调用，含20段正常完成与第6圈活动增益段 |
| backend是否正常返回 | 否，`runtime_calls.backend_returned=false` |
| MATLAB进程退出 | `-15`，对应本次监控器的超时TERM；`cleanup_verified=true` |
| 顶层Conda/launcher退出 | 1；与本次非成功最终结果一致 |
| runner | `status=failed`、`stop_reason=timeout` |
| candidate | **缺失**，没有正常/异常候选写出；未人工补造 |
| 父进程final | **存在**，`job_status=timeout`、`Supervisor:timeout` |
| 最终圈数/旧标志 | final圈数为null，`No trustworthy final count`；legacy_flags为空对象 |
| 尾纤/压缩 | 未执行，超时发生在第6圈增益段；没有其C记录 |

独立进度证据：`runtime_observer.json` 中前5圈各4段正常完成，stdout也有第1–5圈结束
及第6圈开始行。因此报告可说“**5圈完成、第6圈开始**”；这不覆盖 final 中缺失的最终
圈数，也不宣称整个程序完成了6圈。未达到 max_rt=50；没有返回旧能量收敛/force-stop结论。

父进程首次确认的停止事件为 timeout，没有STOP取消事件。原final优先保留该超时原因；
candidate缺失只是附加诊断，不替代超时原因。`required_records_error=null` **不表示完整
记录 gate 通过**：没有候选，正常完成 gate 根本未执行。不得修改gate或重新合并成成功。

运行后只读进程表确认本次所属进程组已消失；没有额外清理动作或操作用户其他 MATLAB。
不存在 supervisor_error.json，存在的是final中的超时及缺候选原因、runner终态和原stdout。

## B. 本次真实参数、C层与计数

B由**本次**生产局部变量在首次传播前保存到 configuration.mat/json，不是复制第三批
快照。与直接捕获的 `phase1/baseline_001/configuration.mat` 比较256个叶项：类型、尺寸、
数值精确核对通过，意外差异0。baseline_002的引用配置没有被当作独立捕获。

保留4 W / 1030 nm / plot=false、seed=0/twister、Nt=32768、50 ps、max_rt=50；
实际增益4 m、无源0.4/1.5/3.2 m，原随机开关、保存设置、滤波和1-H端口均未改变。
N_total计算值为89814125.93190747，最终覆盖为90000000。无源声明MFD=10.5 μm而实际
SR=`3.596467889937611e10 m^-2`、面积=`2.7805058479678165e-11 m²`，仍保留其旧5.95 μm
派生来源。**H02没有解决，新的物理参数约定没有确认或验证。**

A、B、C、observer、请求和final的源身份一致。21个已进入段均实际观测到引擎解析的
max_deltaZ=0.01 m、初始deltaZ=0.001 m、threshold=1e-6、save_period=0.1 m。
这不表示整个传播中步长固定为0.001 m；后续自适应步长照原算法变化。
21次调用的 gain_param 数组均通过与B引用一致性检查。

| 增益段调用圈号 | 实际 t_rep (s) |
|---|---:|
| 1 | 4.442711000000001e-8 |
| 2 | 4.442471742187501e-8 |
| 3 | 4.4424827285156266e-8 |
| 4 | 4.44248364404297e-8 |
| 5 | 4.442483491455079e-8 |
| 6（未完成） | 4.44248364404297e-8 |

t_rep确实动态演化，未强行固定。第6圈后续无源段、尾纤及压缩实参未被观察到。
原C文件中压缩状态仍写 `deferred_to_authorized_run`；这是既有未到达状态文字。
**本批已经授权，实际原因是超时前未到达该位置**，不是本批没有授权；原文件未改写。
`analyze_field` 的路径解析记录不能当作压缩器已执行的证据。

| 路径与范围 | 正常完成段数 | trials | rejections | accepted_advanced_steps | 完整性 |
|---|---:|---:|---:|---:|---|
| 增益 cavity_1，第1–5圈 | 5 | 23310 | 15 | 23295 | 仅此已完成子集完整 |
| 无源 cavity_2，第1–5圈 | 5 | 7483 | 10 | 7473 | 仅此已完成子集完整 |
| 无源 cavity_3，第1–5圈 | 5 | 1879 | 0 | 1879 | 仅此已完成子集完整 |
| 无源 cavity_4，第1–5圈 | 5 | 1615 | 0 | 1615 | 仅此已完成子集完整 |
| 无源三段小计，第1–5圈 | 15 | 10977 | 10 | 10967 | 不含未到达后续段 |
| 第6圈活动增益段 | 未正常结束 | null | null | null | active_segment_counters_not_flushed |
| 尾纤 | 未执行 | null | null | null | 未到达，不能补0 |
| 全次运行总数 | 未完整取得 | null | null | null | 活动段未知，不能把子集小计当总数 |

20个正常完成段逐段满足 `trials=rejections+accepted_advanced_steps`，pending=0。
第6圈活动段的trial、拒绝、推进、pending及z均为null，全局counts_complete和
runtime_resolved_complete均为false。没有为使计数关系成立而填补值。

前5个增益段每段有3次真实拒绝，说明本次生产同向泵路径确实经过H01对应的拒绝/重试
及回滚分支。无源的10次拒绝不计作H01触发证据。未知第6圈计数不能据此判0；这些记录
也不能反推Phase 1拒绝次数或误差，更不能独立验证随机拒绝协议。

## C. 与Phase 1的同口径对照

下表旧值直接读取 `phase1/baseline_001/result.json`（baseline_002/result.json相同），
保存场派生峰值/尾纤量读取 `phase1/diagnostic_002/waveform_checks.json` 的相应run_id。
没有拿公开报告的四舍五入数字计算高精度差值。**本次无最终科学结果，不计算指标差值。**

| 输出平面 / 处理 / 指标 | Phase 1 baseline_001（002相同） | 本次权威final |
|---|---:|---|
| SF1拒绝端、尾纤前、未压缩能量(nJ) | 128.72209125504324 | null：timeout，无最终指标 |
| 同平面保存场峰值(W) | 22799.273014143564 | null：同上 |
| 同平面全局半高跨度(ps) | 6.4056396484375 | null：同上 |
| 尾纤后、未压缩能量(nJ) | 128.71677171714188 | null：尾纤未执行 |
| 尾纤后、未压缩峰值(W) | 20828.852970782682 | null：尾纤未执行 |
| 尾纤后全局半高跨度(ps) | 6.13555908203125 | null：未执行；现适配器也未提取该标量 |
| 原压缩分析FWHM(fs) | 29.868593383716302 | null：压缩分析未执行 |
| 原压缩分析峰值(W) | 2778735.439884705 | null：压缩分析未执行 |
| 去谱相位理想参考宽度(fs) | 22.742140402294446 | null：分析未执行；本来也不是实得压缩宽度 |
| 压缩能量 / 压缩复场 | null：旧入口未返回 | null：未执行，原接口亦不返回 |
| 最终返回圈数 | 6 | null：无可信最终返回圈数 |
| 停止原因 | 旧能量收敛 | 外部timeout；诊断显示5圈完成、第6圈开始 |
| converged / force_stop / pulse_survives / ML_state | true / false / true / 1 | 未返回，不能填false或stable_single |

SF1能量使用原标量定义（tracker居中前积分），没有换成旧保存场复算的
128.72209140947456 nJ。旧半高跨度与压缩器局部峰宽定义不同，没有混用；没有用
上游能量补压缩能量，也没有用energy/FWHM冒充峰值。

新最终复场没有落盘，configuration.mat仅含初场；因此**未做新旧复场比较**。没有额外
启动MATLAB、重算传播/压缩或安装离线读取依赖。

这是不同终点的对照：旧运行6圈后完成尾纤/压缩，本次第6圈内超时。不能把输出或成本
变化全部归因于H01；当前修复集合还包括H04、无进展防护、包装修复和诊断接线。
同seed不构成独立数值收敛或稳定单脉冲验证；物理状态继续undetermined，数值验证
not_verified，训练真值资格false。

## D. 实际成本、记录缺失与限制

| 量 | 实际记录 |
|---|---|
| MATLAB外部墙钟（含启动/退出/组清理） | **870.1859403339913 s**，约14分30秒 |
| 首次确认timeout的单调时间 | 870.0443839170039 s |
| 父进程提交final前的总墙钟 | **870.3312462080503 s** |
| 父进程直到final提交完成的精确总墙钟 | null：既有实现只记录precommit，提交自身耗时未单独计量 |
| 清理独立耗时 | null：未单独采样；包含在外部墙钟中，cleanup_verified=true |
| 总限 / 清理与最终化预留 | 900 s / 30 s，预留包含在900内，不是已消耗30秒或额外预算 |
| 本次进程组峰值RSS | null：现监控器未采样，也无资源记录文件；没有追加测量 |
| 原始运行产物 | **10个文件，1,331,265 bytes（约1.27 MiB）**；不含事后报告/核查文件 |
| MATLAB开始/父runner结束UTC | 22:01:34.654243 / 22:16:04.842926（2026-09-27） |

30秒是预算预留。约870秒开始关停与随后快速退出符合该策略，不能改说“未用满900秒
所以应继续”。final已存在，但没有精确final提交完成计时；不以文件时间戳冒充单调计时。

| run_id | MATLAB外部墙钟(s) | 测量终点 |
|---|---:|---|
| baseline_001 | 714.3236418330343 | 6圈＋尾纤＋压缩，正常返回；原诊断副本 |
| baseline_002 | 800.0699579999782 | 6圈＋尾纤＋压缩，正常返回；原入口 |
| validation_001 | 870.1859403339913 | 第6圈增益段预算停止；无尾纤/压缩 |

旧RSS峰值分别2722464和2324800 KiB，来源为旧runner约每秒对所属进程组各进程RSS求和，
共享页可能重复；本次没有同口径测量，不能比较。不同终点、负载与诊断开销下的单次
墙钟只作描述，不宣称加速比、优化收益或某项修复的独立成本。

stdout保留两条 `WARNING: package sun.awt.X11 not in java.desktop`。没有持久化数值
异常证据，但旧传播代码屏蔽warning的限制仍存在，不能由日志少就证明没有数值警告。
本次停止分类为**预算停止**，不是已证实的数值错误、配置gate拒绝、监控清理失败或物理
不稳定。正常候选缺失，完整记录gate未执行，压缩/尾纤及正常返回链仍未验证。

## 文件、保留性与下一步

权威原始文件：

- `reports/local/phase2/single_validation_001/validation_001/final_result.json`
- `reports/local/phase2/single_validation_001/validation_001/runner_record.json`
- 同目录 requested、configuration、configuration_comparison、runtime_calls、runtime_observer、
  launch_request及stdout；**没有matlab_candidate.json或supervisor_error.json**。

本批独立只读核查存在批次根目录的 review_start.json、postrun_review.json 和命令记录，
不替换原始runner/final，不另造结果协议。运行期间没有编辑参与身份校验的文件；结束后
才新增本报告并更新EXECUTION_STATUS。启动前记录的1831份文件在报告落笔前哈希一致，
随后只有本批两份文档允许变化；最终保留性核查和 `git diff --check` 结果另存本地。

下一步建议：先审核本次预算终点、完整段计数和既有耗时证据，决定是否另行授权足够
完成正常返回链路的预算/诊断方案。不能从本次超时判断模型物理不稳定，也没有依据宣布
通过正常整腔验证。本批不修复、不调参、不增加精度研究、不再运行、不生成训练数据。
**一次授权已经消耗；现在停止，等待审核。Phase 2B/3及之后未开始。**
