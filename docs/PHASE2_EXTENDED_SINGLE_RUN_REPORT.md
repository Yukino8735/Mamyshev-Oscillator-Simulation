# Phase 2：一次追加预算的真实验证

2026-09-27，`single_validation_002 / validation_002`。

**本次单点真实入口的正常返回及父进程最终记录链路通过。** 新授权只启动一次，
6圈后按旧能量收敛判据停止，完成尾纤和原压缩分析，MATLAB退出0；candidate、runner、
父进程final一致，final为`completed`。外部墙钟1040.4727931660018秒，未触及1800秒总限。
这不是物理验证或独立数值收敛验证，也不是新增独立设计/训练样本。

Phase 2仍为**in_progress**，本批结束等待审核。physical_state=undetermined，
numerical_validation=not_verified，eligible_as_validated_training_truth=false。

## 范围、授权和最小接线

读取适用AGENTS、EXECUTION_STATUS、第四批报告及validation_001原始final/runner/进度，
直接检查启动器、supervisor、进程监控器和MATLAB入口。AGENTS中的旧Phase 0授权描述
由本次明确指令覆盖；未重做环境、Phase 1、MATLAB preflight或整套短测。

- 当前分支`feature/mamyshev-ml-mvp`，commit
  `489bf4242f9b5266d47f8892840a24af66931ff0`；保留原有未提交工作。
- 新批次起初不存在。先保存1852份已有文件哈希，之后只在新批次根目录保存审核文件，
  没有提前建立真实run子目录。旧目录、锁、timeout结果和历史报告保持不变。
- 旧进程组已消失。发现的其他MATLAB进程来自VS Code MATLAB服务，归属与本次不同；
  未发送信号或关闭它们。首次只读核查因过严的“无其他MATLAB”断言停止，纠正识别后继续；
  该核查未预留尝试或启动MATLAB。
- `scripts/run_mamyshev_once.py`新增受限`--batch-id`及`--timeout-s`接线。
  旧默认仍为single_validation_001/900秒；1800秒只接受显式的新批次＋validation_002组合，
  组件模式拒绝这些真实运行参数。dry-run显示真实预算、内含预留、原请求和STOP路径。
- 新请求明确记录batch_id、total_wall_limit_s和30秒预留。原批次flock、任意已有预留目录
  拒绝第二次、独占创建run目录、STOP及父进程final规则原样保留。
- **没有修改supervisor、所属进程组监控器、MATLAB数值/传播源码、物理配置或停止判据。**
  新增的`tests/test_once_launcher.py`只测试Python接线，不是替代后端。

关键接线（完整diff位于本地`launcher_change.patch`）：

```python
batch_id = args.batch_id or "single_validation_001"
timeout = args.timeout_s if args.timeout_s is not None else 900
if batch_id == "single_validation_002":
    if args.run_id != "validation_002" or args.timeout_s != 1800:
        p.error("single_validation_002 requires validation_002 and explicit --timeout-s 1800")
elif timeout != 900:
    p.error("The original batch retains its 900 second limit")
```

没有另写监控器或结果协议；仍使用safe_result_v1。没有删除锁、关闭gate或覆盖旧记录。

## 测试、dry-run与唯一实际命令

| Python验证 | 结果 | 测试框架耗时 | 范围 |
|---|---|---:|---|
| 新增test_once_launcher.py | 8项通过 | 0.029 s | 默认900、新显式1800、请求身份/预算传递、无效组合、组件参数隔离、预留拒绝、失败后禁止重试、30秒预留 |
| 复用test_supervisor.py | 17项通过 | 1.237 s | candidate/gate、失败优先、STOP/timeout、final拒绝覆盖、写盘失败和所属组清理 |

新测试使用临时目录/mock；既有Python测试使用短小shell子进程。**没有MATLAB fixture。**
这25项是Python测试方法，不是25次物理仿真或新增独立数值验证。日志在本批根目录的
`python_launcher_tests.log`和`python_supervisor_tests.log`。

已执行的无传播核对命令：

```sh
/opt/homebrew/Caskroom/miniforge/base/bin/conda run -n mamyshev-ml --no-capture-output python -B scripts/run_mamyshev_once.py --dry-run --run-id validation_002 --batch-id single_validation_002 --timeout-s 1800 --matlab /Applications/MATLAB_R2025a.app/bin/matlab
```

dry-run退出0：新目录正确、real后端、1800秒总限、30秒预留包含在总限内、max_attempts=1，
4 W/1030 nm/plot=false、seed=0/twister；未创建真实尝试或传播。

随后执行且仅执行一次：

```sh
/opt/homebrew/Caskroom/miniforge/base/bin/conda run -n mamyshev-ml --no-capture-output python scripts/run_mamyshev_once.py --execute-real --run-id validation_002 --batch-id single_validation_002 --timeout-s 1800 --matlab /Applications/MATLAB_R2025a.app/bin/matlab
```

输出目录：`reports/local/phase2/single_validation_002/validation_002/`。
取消入口仍是该目录的STOP文件；本次未触发取消，也无自动重试或加时。

## 真实身份、参数和冷启动

本次源码清单231项，摘要：
`3f036eae64f5740177bb4595a7328f5e7fface5c66e7004929250f6f52001337`。
旧validation_001摘要为
`e820c77de90f77ec6911d91cb40866b2fcdb41a02b560f3e216da59060f8d1cd`。
清单唯一已有文件变化是启动器，唯一新增是其Python测试。**没有声称全仓库哈希不变**；
旧清单未修改，新请求和本次A/B/C/candidate/final使用新身份，运行期间身份未变化。

本次B来自真实生产局部变量，与Phase 1 baseline_001直接保存的configuration.mat精确比较
256个叶项通过，unexpected_differences和expected_metadata_differences均为空。
与validation_001的B相比，仅时间/run_id/源码身份元数据不同；实际配置、初场和网格摘要、
完整RNG状态一致。入口重新rng(0,'twister')并调用原build_MMgaussian初态，
未读取旧末场或将旧configuration.mat当成第五圈checkpoint。

- 4 W同向泵、cw2=1030 nm、plot=false；Nt=32768、50 ps、max_rt=50。
- 增益4 m；无源0.4/1.5/3.2 m；尾纤0.2 m。原MFD/SR、N_total计算后覆盖、1-H端口、
  滤波、长度规则、随机开关和压缩器假设不变；H02物理约定仍未解决。
- 25次实际调用均观察到max_deltaZ=0.01 m、初始deltaZ=0.001 m、threshold=1e-6、
  save_period=0.1 m；没有固定后续自适应步长。
- 增益t_rep按原算法演化：第1圈4.442711000000001e-8 s，第6圈
  4.44248364404297e-8 s；完整六次值保留于runtime_calls。24次腔段的增益数组引用核对通过。
- 使用CPU，无parpool/GPU、test_hook字段或synthetic backend。全部Python均经指定环境。

## 返回链路、停止和完整性

真实链路仍为Python launcher → supervisor → launch_mamyshev_once →
run_mamyshev_recorded → run_mamyshev → GMMNLSE生产增益/无源引擎。

| 事实 | 原始记录 |
|---|---|
| 预留/启动/传播 | 均发生；attempt=1/max_attempts=1，独立进程组 |
| 正常后端返回 | runtime_calls.backend_returned=true |
| 完成圈数 | 6；非max_rt停止 |
| 物理计算入口的停止原因 | legacy_energy_convergence |
| 旧标志 | converged=true、force_stop=false、pulse_survives=true、ML_state=1 |
| 旧相对能量波动 | 0.0004224468255450582 |
| MATLAB / runner | exit_code=0；completed/process_exit；stop_events=[] |
| candidate / final | 均completed；父进程candidate_valid=true、required_records_error=null |
| 参数/计数完整性 | counts_complete=true、runtime_resolved_complete=true，无活动段 |
| 清理 | cleanup_verified=true；运行后只读确认所属进程组消失 |
| 写盘 | candidate、runner、父进程final均存在；无supervisor_error.json |

本次正常candidate通过了既有完整性gate；六份要求产物的bytes/SHA-256与记录逐一一致，
相关run_id与源清单一致。没有修改gate、重新合并或人工修写runner/final。

25段包括6圈×4段及尾纤。压缩C记录是在analyze_field调用前捕获，因此其中
`analyzer_has_returned_at_capture=false`不单独证明分析完成；结合后续backend_returned=true、
实际返回压缩指标、MATLAB退出0及父进程完整gate，确认这次原分析正常结束。
Treacy-t、入射角0.5235987755982988 rad、光栅间距1e-6 m、plot=false均按实际调用记录。
分析函数内部默认值仅由未变源码身份覆盖，不夸大为逐项运行时观测。

| 路径 | 完成段数 | trials | rejections | accepted_advanced_steps |
|---|---:|---:|---:|---:|
| 增益cavity_1 | 6 | 27374 | 18 | 27356 |
| 无源cavity_2 | 6 | 9116 | 12 | 9104 |
| 无源cavity_3 | 6 | 2258 | 0 | 2258 |
| 无源cavity_4 | 6 | 1938 | 0 | 1938 |
| 无源腔段小计 | 18 | 13312 | 12 | 13300 |
| 尾纤 | 1 | 719 | 2 | 717 |
| 整次传播合计（不重复小计） | 25 | 41405 | 32 | 41373 |

每段均pending=0，trials=rejections+accepted_advanced_steps，normal_completion=true。
18次**增益**拒绝说明本次确实走到H01对应拒绝/回滚分支；无源及尾纤拒绝不是H01证据。
这不是随机拒绝协议独立验证，也不能反推Phase 1旧运行的拒绝次数或误差。

## 分平面结果及Phase 1比较

旧值直接来自`reports/local/phase1/baseline_001/result.json`和baseline_002对应记录；
两个旧运行这些指标相同。保存场派生峰值及尾纤量来自
`reports/local/phase1/diagnostic_002/waveform_checks.json`对应run_id。
新值只取已由父进程接受的final；未从报告四舍五入数值反推高精度差异。

| 平面/处理/指标 | Phase 1旧数值版本 | validation_002 final |
|---|---:|---:|
| SF1拒绝端、尾纤前、未压缩；原标量能量(nJ) | 128.72209125504324 | 128.7196822190777 |
| 同平面；复场最大强度(W) | 22799.273014143564 | 22779.272914985067 |
| 同平面；全局半高跨度(ps) | 6.4056396484375 | 6.4117431640625 |
| 尾纤后、未压缩；能量(nJ) | 128.71677171714188 | 128.7146060101117 |
| 同平面；复场最大强度(W) | 20828.852970782682 | 20872.27893766115 |
| 同平面；全局半高跨度(ps) | 6.13555908203125 | null：现适配器未提取独立标量 |
| 原压缩分析；局部峰半高宽(fs) | 29.868593383716302 | 29.84941905629446 |
| 同分析；场峰值(W) | 2778735.439884705 | 2850940.6179669127 |
| 去谱相位理想参考宽度(fs) | 22.742140402294446 | 22.753081194425736 |
| 压缩能量/压缩复场 | null：原入口未返回 | null：原入口未返回，保留reason |

SF1能量使用tracker居中前的原标量定义，未改用旧保存场复算128.72209140947456 nJ。
峰值来自真实复场强度，未用energy/FWHM替代。未压缩全局跨度、压缩局部峰宽和理想参考宽度
是不同定义，不混用。没有借上游能量填补压缩能量。

两次Phase 1和本次均在6圈按旧能量逻辑停止，且完成尾纤/压缩，故上述同平面、同定义
标量可以作描述性对照。但数值修复集合含H01、H04、无进展防护、包装修复与诊断接线，
不能把差异全部归因H01，也不宣称性能改进。ML_state=1仍不转换为stable_single。
同seed不构成独立数值收敛或物理稳定性验证。

本次没有保存最终输出复场文件，configuration.mat只含初场/配置。因此未做新旧复场比较，
也未新增MATLAB重算、离线压缩或依赖安装。最终标量存在不代表相应复场已落盘。

## 与上次超时的进度和成本

validation_001在5圈完成后、第6圈增益段超时，尾纤/压缩未执行；本次冷启动完成6圈及
全部后处理。两次共享的前20个完整段trial/rejection/advance计数逐段一致；这只是同seed
同配置的共享前缀一致性，不是新的独立设计或数值收敛试验。旧timeout和其null指标原样保留。

现有观察器保存了真实UTC开始/结束时间。以下为段边界时间戳差之和，含该边界内的
诊断/调用成本，不是单调计时或纯数值内核计时；逐段明细在postrun_review.json。

| 路径 | 本次完整范围 | 本次UTC边界耗时合计(s) |
|---|---|---:|
| 增益 | 6段 | 651.335 |
| 无源cavity_2 | 6段 | 221.047 |
| 无源cavity_3 | 6段 | 68.667 |
| 无源cavity_4 | 6段 | 60.858 |
| 尾纤 | 1段 | 18.304 |

主要已观测计算位置是增益段，其次为cavity_2；这仅定位耗时，不自动优化或改精度。
不能给上次被打断的活动段补计数/终点耗时，或把两个不同终点的总墙钟解释成加速比。

| 成本项 | 本次实际记录 |
|---|---|
| MATLAB外部墙钟（启动/退出/所属组清理） | 1040.4727931660018 s，约17分20秒 |
| wrapper执行范围 | 1024.90720875 s；与Phase 1内部计时起止范围不完全相同 |
| 父进程final提交前总墙钟 | 1040.5507749579847 s |
| 父进程到final提交完成精确总墙钟 | null：既有实现只记precommit，未测提交自身耗时 |
| 独立清理耗时 | null：未单独计量，已包含在外部墙钟中 |
| 总限/内含清理最终化预留 | 1800 / 30 s；不是1800秒计算加额外30秒 |
| 进程组峰值RSS | null：既有监控器未采样，无资源记录文件 |
| 原始产物 | 11文件、1,443,726 bytes（约1.38 MiB），不含批次根目录审核材料 |
| runner UTC起止 | 2026-09-27 22:37:50.826558 → 22:55:11.253655 |

旧runner外部墙钟：baseline_001为714.3236418330343 s（诊断副本），baseline_002为
800.0699579999782 s（原入口）；两者均6圈加尾纤/压缩。validation_001为
870.1859403339913 s（第6圈增益段超时）。本次没有测RSS；不拿旧2,722,464/2,324,800 KiB
代填或声称内存优化。前后单次成本只作描述，不拆出某项修复的独立开销或收益。

stdout有两条`WARNING: package sun.awt.X11 not in java.desktop`，没有记录数值异常；
旧代码屏蔽warning的限制仍存在，不能由正常退出/空异常认定不存在数值问题。

## 交付、限制和停止

本批改动：启动器、其新增Python测试、本报告及EXECUTION_STATUS；独立详细证据位于
`reports/local/phase2/single_validation_002/`，由已有ignore规则保持本地。
未改生产MATLAB、supervisor、monitor、物理配置、数值公式、原停止设置或历史记录。
交付时执行git diff --check，并以启动前哈希及本次原始产物哈希核对保全；结果见
`preservation.json`、`git_diff_check.log`和`git_status_final.txt`。

原始目录中的requested、launch_request、configuration.mat/json、configuration_comparison、
runtime_calls、runtime_observer、stdout、candidate、runner、final共11份均存在。
无supervisor_error.json（本次未触发该错误路径），无资源文件或最终复场；缺失原因不补造。
独立postrun_review和命令记录不替代safe_result_v1原始证据。

下一步仅建议审核本次单点集成结果、H02未决物理约定和独立数值/物理验证范围，再决定
后续授权。当前没有建立训练真值，也没有新增独立物理设计。没有第三次修复后尝试、
扫描、训练、优化、收敛实验、checkpoint、监控平台、环境修改或GitHub发布。
**本次追加额度已消耗，已停止；Phase 2B/3及之后未开始。**
