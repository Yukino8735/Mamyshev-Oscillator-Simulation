# Demo 10k MATLAB 数据管道审查

本批检查的是 **10,000 个不同输入的计划、实际解析与串行调度能力**。
本批完整腔体/GMMNLSE 传播和真实扫描均为 **0 次 / not_run**。
合成训练数据与待执行 GMMNLSE 计划严格分开；全量计划只在 ignored
`reports/local/demo_10k_release_001/matlab_plan/`，不能随公开 Demo 发布。

## 本批实际结果

2026-09-28 UTC 的以下步骤均正常结束。数值直接取自新批次机器记录；
MATLAB 只运行了 **1 个短进程**，没有启动第二次短测或任何真实传播。

| 执行项 | 实际覆盖及结果 | 计账外部墙钟 |
|---|---|---:|
| `plan_components` | 6 项新 Python 测试通过：通用 N、null solver targets、分块/筛选/hash、CSV ID/数量、重复/非法字段/单位/非有限/格点拒绝、真实0许可预留前拒绝 | 0.22418929100967944 s |
| `pending_10k_plan` | 精确10000个唯一训练 X，首/中/末为第1/5001/10000行；40块（39×256+16）保序、过滤一致、完整计划 hash 通过；solver targets 全null，真实额度0 | 3.4795172089943662 s |
| `recorded_resume` | 3次既有同源合成记录缓存读取；第一行提交后取消，关闭重开DB续扫其余2行，第三次进入跳过全部；DB/CSV/MAT读回及错误身份不回退均通过，原训练DB hash未变 | 0.5533612089930102 s |
| `plan_and_parity` | 1个 MATLAB 进程、7个断言组通过；10000行格式/单位/格点/ID唯一性/目标空值；实际首中末3次初始化和1次legacy默认初始化；32个已取标点跨语言复算 | 40.07521795807406 s |
| `reused_authorization` | 选中的5项既有 `LiveAuthorization` 组件通过（下列精确名称）；没有运行整套历史回归，也没有真实启动 | 0.21582458296325058 s |

本批重复执行的授权回归只有以下5项；不计作新测试：

- `test_default_denial_and_zero_allowance_do_not_reserve`
- `test_changed_plan_unauthorized_id_and_unknown_fields_fail`
- `test_serial_ledger_refuses_run_or_directory_reset`
- `test_incomplete_attempt_remains_reserved_and_blocks_resume`
- `test_exhausted_cumulative_wall_and_stop_refuse_launch`

MATLAB 的已有 monitor 记录 `exit_code=0`、`status=completed`、
`cleanup_verified=true`、`stop_events=[]`，所监控进程外部墙钟为
40.07441891601775秒；预算 ledger 包含父侧记账开销，计40.07521795807406/180秒。
4次初始化均保持 Nt32768、50ps、max_rt50、原步长/容差、固定无源段和尾纤；
实际传播调用数0。7个断言组属于同一个短进程，不计成7次独立物理实验。

32行 parity 的逐目标最大绝对差为：能量
`3.4106051316484809e-13 nJ`，脉宽 `6.3948846218409017e-14 fs`，峰值
`6.2172489379008766e-15 MW`。全部满足启动前固定的
`abs(MATLAB-ref) <= 1e-10 + 2e-10*abs(ref)`；RNG 不变。这里重算的是
已取标的相同32个点，**新增研究标签0**，不是新增训练设计或GMMNLSE结果。
recorded重放的3次调度请求也全部来自已有标签；不能将其 `new_attempts=3`
解释成3次新oracle计算或3次真实仿真。

完整计划 canonical hash：
`82de9d55aabbb0fcdd5a3657c856f5f5b0f8a411093bdd156063f2d8c7884d9d`。
MATLAB还核对实际读取计划文件的SHA256：
`bb6c191b700d6a8a78316420cd73eac50394e1e3dc22f8b593d3f474029246a2`。
原始 `plan_validation.json` 中 `matlab_status=not_run` 是创建计划时的快照，
未回写覆盖；随后短测的实测状态在独立 `demo10k_matlab_components.json` 中。
上述全部支持“10k计划与调度路径经过检查”，**不支持“10k真实数据生成通过”**。

机器证据（均 local-only）：

- `reports/local/demo_10k_release_001/matlab_plan/plan_validation.json`
- `reports/local/demo_10k_release_001/matlab_plan/recorded_resume/resume_report.json`
- `reports/local/demo_10k_release_001/matlab_short/process_001/demo10k_matlab_components.json`
- `reports/local/demo_10k_release_001/budget/matlab/plan_and_parity/runner_record.json`
- `reports/local/demo_10k_release_001/budget_ledger.json`

## 实际调用链

1. `scripts/prepare_demo10k_matlab_plan.py` 从新 train 的纯 X CSV 读取四字段；
   `src/mamyshev_ml/demo10k_plan.py:18` 检查精确 N、有限值、单位字段、
   canonical ID 和重复。复用 `v4_scan.make_plan:16`、`verify_plan:74`、
   `v4_evaluators.validate_design:27`。所有 solver targets 均为 null。
2. 原 `scripts/v4_scan.py` 的 `run --evaluator gmmnlse` 选择
   `v4_evaluators.GMMNLSEEvaluator:248`；它调用
   `supervisor.execute_authorized_design:149`。纯计划或 `--execute` 本身不授予
   真实运行权；仍需 `--execute-real` 及匹配完整 plan hash/ID 集合的显式授权。
3. `supervisor.validate_live_authorization:105` 核对授权；0 额度在创建真实
   目录、授权账本或 MATLAB 进程前拒绝。跨批次持久账本按 authorization_id
   计费，未终结尝试仍扣全额，换 run_id/batch 不能恢复额度。
4. `execute_authorized_design` 从计划选取**一行**，将其四参数、身份、seed、
   预算和许可写入 `launch_request.json`。MATLAB
   `code/ml_bridge/launch_mamyshev_once.m:5` 读取该行对应的请求，不在 MATLAB
   中重复载入 10,000 份传播状态。`mamyshev_validate_launch_context.m` 再核对
   许可/实际设计/单位由字段名规定/禁止注入，然后调用
   `run_mamyshev_recorded.m` → `run_mamyshev_config.m` → 同一 `run_mamyshev.m`。
5. `run_mamyshev.m:85` 的 pump、`:113` 的增益长度、`:152` 的 SF2、`:167` 的
   总长及 `:179` 的初始 t_rep 来自实际解析值。真正传播仍在 `:247`；SF1 的
   1-H 输出在 `:276`，逐圈 pre/post 场保存调用在 `:350`。终点尾纤在 `:400`，
   原同次压缩分析在 `:408`，`MamyshevWaveforms.finish:75` 留存其实际场。
6. MATLAB wrapper 只写 candidate；`supervisor.execute_once:761` 完成 owned
   group 清理、身份/实际配置/计数/波形 gate、失败优先合并，父进程独占 final。
   `v4_evaluators.import_safe_result:141` 只导入 parent final，并保留来源/平面/
   单位与错误。candidate 不会冒充 final；失败 targets 为 null。
7. `v4_scan.execute_scan:94` 每设计提交 SQLite，再进入下一设计；
   `v4_store.V4Store` 保持 Prediction 与 Evaluation 分表，按精确来源查缓存。
   `export_scan` 导出同一记录的 CSV/MAT/来源及缺失原因。历史复场读取是
   `v4_scan.read_saved_waveform:230`，不调用传播或再次优化压缩器。

## 功能矩阵

“当前测试”只针对本批实际执行证据；历史通过不计作本批新测试。

| 功能 | 实现位置 | 当前测试 | 历史证据 | 未验证范围 | blocked 原因 |
|---|---|---|---|---|---|
| 单点 / 1D / 任意两轴 / 4D grid | `v4_scan.make_plan`，`run_mamyshev_config` | 新计划通用 N 组件；本批选中首/中/末初始化见机器记录 | V4 `data_chain` 的 1D/2D、4D plan；Phase2 正常单点 | 非默认完整物理运行未执行 | 本批无真实额度 |
| random / LHS / CSV | `v4_scan.make_plan` | 新 X-only CSV 精确 ID/计数/重复/非法输入组件 | V4 random/LHS/CSV plan 和组件 | 全域 GMMNLSE 可靠性未验证 | 输入域是探索域 |
| 10k 计划、分块与筛选 | `demo10k_plan.{read_input_rows,pending_plan,chunk_rows,select_rows}` | `plan_validation.json`；固定 N=10000、chunk=256、首/中/末、过滤与 canonical hash | 原 V4 任意 N 计划接口 | 全量真实执行 not_run | 需独立批准完整 hash、ID、次数和预算 |
| 实际四参数/长度依赖 | `mamyshev_resolve_config`，`run_mamyshev` 初始化与 capture B | `demo10k_matlab_components.json`；原 Nt32768/50ps，不传播 | Phase2 4D 接口及 V4 5 个初始化 | 各参数对完整动态轨迹/稳定性影响 | 本批仅初始化 |
| 精确 recorded 查询 | `RecordedEvaluator`, `V4Store.lookup` | 3 个本批已取标的同源记录；错误 seed 不回退 | V4 真实历史 final 只读导入 | 缺失的真实设计不生成替代数据 | 缺记录时 not_available |
| 逐点持久化 / 状态 / 取消与续扫 | `v4_scan.execute_scan`，SQLite scans/scan_items/attempts | 3 行 recorded：第一行提交→STOP→关闭DB→重开→完成→再次进入跳过 | V4 小合成扫描 | 10k 长时运行/磁盘耗尽/所有 OS 故障 | 本批不开展长时压力测试 |
| 授权与跨 resume 预算 | `supervisor:105,149`，`v4_scan:94` | 0 授权默认拒绝；复用 live supervisor 组件测试 | V4 测过禁止换批重置、reserved 阻断、总墙钟/STOP | 真10k长扫描故障恢复 | 需独立授权 |
| 失败显式重试 | `execute_scan` 跳过非 pending；授权账本拒绝相同设计再次尝试 | 既有授权组件；无自动重试 | 原失败/timeout 原样保留 | UI 不提供重试；须另行审批新 attempt/plan/scan 身份，旧证据不改 | 本批不批准重试 |
| 版本 / 来源 / 单位 / DB-CSV-MAT | `v4_evaluators`, `v4_store.export_scan` | 3 行真实持久化的已存合成记录读回；原 DB hash 保持 | V4 分源 schema、历史 real import | 大量输出长期迁移 | 未执行 |
| 尾纤 / 同次压缩 / 波形 writer / parent final | `run_mamyshev:393–465`, `MamyshevWaveforms`, `supervisor` | 静态查过；本批不执行传播或压缩 | `config_waveform_001` 正常真实链路；`observation_001` 失败 final 历史仍保留 | 新10k设计输出和 full-scan end-to-end | 明确 not_run |
| 已有真实 MAT 读回 / 绘图 | `v4_scan.read_saved_waveform` | 本批精选历史图片来源检查，未重新传播 | V4 `data_chain/historical_mat_read` 实际读 MAT/画图 | 原始文件不存在时不可重建 | 缺失则 not_available |
| Python/MATLAB 合成配方 parity | 原 `v3_evaluate_synthetic.m` | 最多32条本批已取标 train；固定 atol1e-10 + rtol2e-10×abs(ref)，不新增标签 | V4 24行 parity 和已有完整配方检查 | 不是真实光学 solver parity | 合成 scalar 配方不是传播模型 |

## 内存、恢复及物理边界

计划、ID 和标量导出可在内存中持有 N 行；没有 N 组传播复场预分配。
`execute_scan` 的一个 evaluator 调用终结后将标量/路径记录提交并进入下一行。
调度、状态和 resume 只查询 SQLite/JSON，不打开全部历史 MAT；只有用户显式
选定 waveform replay 才读该次复场。原单次仿真的场历史/逐圈保存规则未更改，
因此本批不声称已解决单次原引擎的内存或存储成本。

新严格导入拒绝重复和单位别名；旧通用 CSV/grid 接口的去重行为仍原样保留，
其 duplicates_removed 必须公开记录。本批 10k 路径要求该值严格为0，不能靠
旧接口静默丢行凑数。分块是审查/选择，不是新增额度；授权始终绑定完整计划。

MFD/SR 的 H02 仍 unresolved，固定无源长度0.4/1.5/3.2m、尾纤0.2m、1-H、
滤波、N_total 覆盖、增益材料、H01/H04、RNG 与原数值精度均未修改。
当前短 MATLAB 脚本已检查10000个配置结构，只对首/中/末三个实例及 legacy
默认做真实初始化，且在既有 preflight return 退出；未调用任何传播内核。
合成32点重算是既定标签的跨语言一致性复核，不增加研究标签或训练设计。
`physical_state=undetermined`、`numerical_validation=not_verified`、
`eligible_as_validated_training_truth=false` 保持不变。

公开副本另有明确边界：现有 `MamyshevCapture.configuration` 仍要求本地
`reports/local/phase1/baseline_001/configuration.mat` 作为严格历史初始化参考。
该原始本机证据不进入公开 Demo 包；缺失时 gate 会拒绝，绝不关闭校验来让
clone 看似能执行。当前本机接口完整并有历史单点证据，不代表新的公开 clone
已经具备全部真实执行依赖。最小参考资产的可分发范围和替代发布方式需后续
单独审核，本批仅公开 Demo 推理独立性，不改此安全规则。

## 本批命令与证据

所有 Python 使用指定 Miniforge 的 `conda run -n mamyshev-ml --no-capture-output python`。
以下为可复用的相对路径命令；实际执行的绝对路径、label 和预算以 ledger 为准，
均由 `scripts/run_demo10k_budget.py` 的同一串行监控执行：

```text
--timeout-s 60 engineering plan_components -- -m unittest discover -s tests -p test_demo10k_plan.py
--timeout-s 60 engineering pending_10k_plan -- scripts/prepare_demo10k_matlab_plan.py --inputs reports/local/demo_10k_release_001/samples/train/inputs.csv --labels reports/local/demo_10k_release_001/samples/train/labels.csv --count 10000 --out reports/local/demo_10k_release_001/matlab_plan
--timeout-s 60 engineering recorded_resume -- scripts/demo10k_recorded_resume.py
--timeout-s 180 matlab plan_and_parity -- scripts/run_demo10k_matlab_components.py
```

实际 label/退出状态/耗时以本地 `budget_ledger.json` 为准。MATLAB exec driver
复用旧监控的所属进程组与累计预算，不新增监控器；`matlab_short/process_*/reservation.json`
统计短进程预留，最多2个，总预算180秒。完整 GMMNLSE 次数始终0。
MATLAB 命令显式使用 `-singleCompThread`；不创建 parpool、不使用 GPU。
详细测试结果和本批成本见最终 `DEMO_10K_RELEASE_REPORT.md` 与上述机器记录。
