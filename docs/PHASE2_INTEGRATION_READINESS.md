# Phase 2 第二批：局部回归与整腔接线准备

2026-09-27，`readiness_001`。分支保持 `feature/mamyshev-ml-mvp`，起始commit
`489bf4242f9b5266d47f8892840a24af66931ff0`。依据当前本地未提交源码，已读AGENTS、
第一批报告和状态文件。本批完成限定测试和审查后停止；Phase 2仍为in_progress。

**局部回归通过，但尚不具备无条件启动单次整腔验证的接线条件。** 下述900秒方案可供
审核；实际解析参数/步数诊断观察点，以及外部最终安全记录合并仍需准备和组件测试。
本批完整腔体运行 **0次**，没有运行默认整腔backend，未进入Phase 3或Phase 2B。

## 本批改动

| 文件 | 修改与行号 |
|---|---|
| `code/ml_bridge/run_mamyshev_recorded.m` | 12–38：显式组件fixture注入及独立wrapper版本；42–67：失败候选写盘后重新抛错，禁止失败被进程退出0掩盖 |
| `code/ml_bridge/write_mamyshev_record.m` | 7–9：缺失父目录明确报WriteError |
| `tests/run_matlab_short.py` | 23–27、98–117：新增独立readiness_001目录/预算选择，保留180/600秒限制 |
| `tests/test_short_runner.py` | 17–24、59–71：独立批次及超时优先于退出0/成功候选的测试 |
| `tests/matlab/test_result_contract.m` | 217–221：加强既有历史JSON读回身份断言，不新增独立案例数 |
| `docs/EXECUTION_STATUS.md` | 第二批完成待审核；整个Phase 2未完成 |

新增 `tests/matlab/test_gain_readiness.m`、`test_wrapper_readiness.m`、
`run_readiness_regressions.m`、`run_wrapper_expected_failure.m` 及本报告。
**生产增益引擎、RK4IP、原fixture、ring入口、收敛函数、物理身份JSON本批均未改。**
未重建环境、安装依赖、改全局配置或Git分支，没有reset/clean/stash/commit/push/PR/合并。
修复前相关文件副本、差异及命令只存新的本地目录，没有重做Phase 0/1或整套审核包。

## 新增H01覆盖：真实后续起点与正常返回

`test_gain_readiness.m:89–132,157–244` 沿用32点确定性fixture，仅将诊断短段终点设为
0.004 m。保留实际色散、Kerr及增益/泵更新；Raman关闭仅为既有人工fixture设置。
没有新增替代求解器或修改生产默认值。

| 断言/量 | 实测结果 |
|---|---|
| 真实生产循环接受、推进后的起点 | z=0.001 m，last_deltaZ=0.001 m；a5非空，共32元素，范数0.107204082162 |
| 同一起点连续两次受控拒绝 | trial步长0.002 → 0.001 → 0.0005 m；前两次真kernel泵变化−0.00183075843543 / −0.000915379217713 W |
| 重试状态回滚 | signal、a5、两泵、z、last_deltaZ精确恢复，两次泵泄漏均0；缩小后的步长保留 |
| A最终接受 vs B直接最终小步 | 全复场、a5、两泵、N2、last_deltaZ比较差均0 |
| 短段正常返回与保存 | A完成4个接受步；纯观察控制3步；保存z=[0,0.004]，save_i=3；初末场、泵、N2归一化及时间延迟检查通过 |
| 无hook vs 纯观察hook | 返回场、两泵、N2、时间延迟、保存位置和步长全部差0 |

所有比较先断言相关数组有限。回滚用精确相等；数值比较保持第一批预声明规则
`max_abs_error <= 1e-12 + 1e-12*max(abs(reference))`，未放宽容差。
三次短段均让生产函数正常返回，没有用测试专用结束异常。B从A实际捕获起点直接调用
原生产RK4IP，**不是第二次完整外层循环或独立求解器**。N2是trial输出，不是重试输入。

覆盖共5组断言，内部为3次短增益段和1次kernel对照，不是5个物理设计。
未覆盖pulse_centering=true缓存平移、多保存点N2插值、非零反向泵、随机拒绝协议；
这些不阻碍本批限定同向泵结论，也不构成整腔或物理有效性验证。

## 接线审查：分清静态、组件与整腔

| 项目 | 静态检查 | 本批动态证据 |
|---|---|---|
| 增益test_hook | 引擎357/387/417仅在字段存在时调用；loader/ring默认不定义。关闭方式是删除字段，[]/false不算关闭 | 无hook与纯观察hook短段正常返回对照通过 |
| 包装器异常 | 原catch吞异常，可让MATLAB退出0；现先写失败候选，再rethrow；写盘失败保留原cause | 11项wrapper组件通过；另真实MATLAB进程预期退出1，父记录failed，候选failed/execution_error |
| 默认backend与结果路径 | 默认仍调用真实run_mamyshev；record、failure mapper、JSON writer连接现有生产函数，动态which也核对本仓库路径 | 测试显式注入synthetic backend，仅验证组件接线；未执行默认完整腔体路径 |
| 有效历史 | 当前5个调用均传1,rt_num：ring scan233/236、ring main206、linear main268/272；本圈能量/场已写入 | 原H04的20项重复回归通过；未运行ring/linear整腔或archive入口 |
| Phase 1历史身份 | 通用记录器不重写调用者给出的旧版本 | 既有历史案例加强JSON读回断言，保留legacy_pre_repair_phase1/read_only_phase1_artifact |
| 外部超时/取消 | 父Python独占runner_record；先清理所属进程组再写终态。MATLAB应只写不同路径candidate | Python测试：已观察timeout后，即使子进程退出0且有成功candidate，父记录仍failed/timeout |

关键生产修复（wrapper:49–66）：

```matlab
% write_mamyshev_record errors propagate; original exception is retained as cause
if ~isempty(record_path), write_mamyshev_record(record_path,record); end
% after successful candidate write:
if ~isempty(backend_exception)
    rethrow(backend_exception);
elseif ~strcmp(record.job_status,'completed')
    error('MamyshevRecord:ReturnedFailure', ...);
end
```

组件注入需要显式 `kind=wrapper_component_fixture`，强制写synthetic物理/数值身份，
不能伪装修复后真实运行。测试结束异常仅允许被所属测试捕获，不会被生产包装器包装成成功。
串行ExistingRecord检查防止已有失败文件被成功记录覆盖，但不构成多writer并发锁。

**尚未接通的外部终态职责：** 当前短测监控器只写进程记录，不生成safe_result_v1最终
结果。未来单次监控器必须是final_result.json唯一writer，MATLAB只能写matlab_candidate.json；
timeout/cancel/非零退出优先于候选completed。强杀监控器留下running只能待核查，不能补成成功。
这部分没有通过整腔集成；本批不新建完整结果管道。

## 成本与测试口径

| run_id | 外部墙钟 | MATLAB退出码 | 含义 |
|---|---:|---:|---|
| regression_001 | 14.069126 s | 0 | 新增H01 5组、wrapper 11项通过；重复H01 6组、H04 20项、结果契约20项通过 |
| wrapper_exit_001 | 9.396600 s | 1 | **预期失败进程**：不捕获fixture结束异常，验证候选失败、非零退出及父进程失败，不是意外测试失败 |

MATLAB共2个串行短测进程，**23.465726/600秒**，均小于180秒；失败进程也计入预算，
没有重试、MATLAB超时、GPU或parpool。完整腔体仍为0次。
Python最终11项通过：9项既有回归+2项新增；早先10项运行不额外算独立案例。
Python最终内部0.760秒、含Conda启动的外部2.359382秒。`git diff --check`通过。
本批要求的局部测试无blocked项；整腔、随机/反向泵及下述待接线项不计入通过统计。

详细命令、完整状态/MAT、stdout、预算和保留性检查在
`reports/local/phase2/readiness_001/`，见COMMANDS.md、readiness_summary.json、preservation.json。
修复前后差异以本批起点为准，不把第一批或用户原有修改计为本批新增。

## 下一次单次整腔验证方案——仅供审核，未执行

预算拟为**最多1次、外部墙钟900秒（含启动/退出及关停预留）**，新目录
`reports/local/phase2/single_validation_001/`；无自动重试，不降低精度获取成功退出。
父监控器复用已测owned-process-group函数，但须另加单次预算及最终记录接线，不能
直接把当前180秒短测CLI当900秒整腔启动器。

拟定入口命令如下，其中两个single_validation脚本**尚未新增，不是可立即执行的命令**；
本机绝对路径展开版位于本地PROPOSED_SINGLE_RUN.md。补齐接线并经审核后才可执行：

```sh
<既有Conda> run -n mamyshev-ml --no-capture-output python \
  reports/local/phase2/single_validation_001/launch_once.py \
  --matlab <既有MATLAB> --script reports/local/phase2/single_validation_001/run_once.m \
  --max-attempts 1 --timeout 900
```

MATLAB拟调用 `rng(0,'twister'); run_mamyshev_recorded(4,1030,false,candidate_path)`，
**不传test_options**。记录完整RNG前后状态、当时commit及工作树/数值源码哈希，物理身份
legacy_ring_phase1_v1、数值修复版本和wrapper/result版本分别记录。保留Phase 1实际
MFD/SR、1-H端口、滤波公式、N_total、4/.4/1.5/3.2 m长度、尾纤及压缩假设；Nt32768、
50 ps、max_rt50、原能量/步长容差、Raman_model=1及Raman_sponRS=true均不变。

启动前的具体准备/阻塞项：

1. **实际参数和轻量诊断观察点尚未接线。** 在真实入口loader/gain_info后、首次传播前
   捕获fiber_cavity、sim_cavity、gain_param/N_total、初场、网格、滤波参数；与Phase 1
   已保存配置逐项核对。传播初始化后再确认实际SR/面积、max_deltaZ/初始步长/threshold，
   同时核对尾纤与压缩实参，不能只复读身份JSON或跑旧诊断副本冒充新入口。
   在实际trial决策处计总trial/拒绝数，在z推进后计接受步；仅按段/圈刷写标量汇总，
   观察器不得改success、步长或RNG。不保存庞大逐步状态；超时活动段未刷出计数标不完整。
2. **单次supervisor及最终安全记录合并尚未实现/组件验证。** 独立run_id和目录拒绝覆盖，
   外部900秒内预留关停时间，只结束所启动组；保存stdout、起止UTC/耗时、进程组RSS
   （注明共享页可能重复）、磁盘量、圈数与停止原因。final只由父进程写；失败/超时指标
   null+reason，候选仅作诊断。外部STOP为取消、不重试；失败退出不能被候选成功覆盖。

这两项不是要求先证明物理正确，但必须在真正启动前补齐并检查。当前可审核方案和局部
证据，**不能把整腔集成写为已执行，也不能视为已获运行批准**。

比较时只对同平面、同处理状态、同定义的能量/峰值/宽度和保存复场作差；停止圈数不同
须单列。保存实际圈数、legacy_flags、分平面指标、缺失原因与成本。压缩能量/场未获得
继续null。修复集合包括H01、H04、无进展保护和包装错误传播；不能把输出变化全归于H01，
更不能把同seed一致或变化当作独立数值收敛或稳定单脉冲证据。

H02仍是旧实际参数已冻结、新物理约定未确认/验证；physical_state=undetermined，
eligible_as_validated_training_truth=false。本批未做四维接口、扫参、训练、优化、独立
收敛研究或README/简历性能修改。第二批结束，停止等待审核。
