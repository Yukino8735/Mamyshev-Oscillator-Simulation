# V4.1 固定硬件切片诊断与有界补样对照

2026-09-28 UTC。本批已按开发失败停止：**没有候选通过全部门槛，不生成新 calibration/test，不扩大样本或继续调参。** `pipeline_completed=true` 指诊断与限定对照流程完成；`accuracy_target_met=false`。最佳诊断候选为 B2，未获部署或全域精度认证，也未替换 V4。

本批只执行用户附件末尾的 V4.1 增量指令。MATLAB 启动 **0**，真实 GMMNLSE **0**，BO/随机优化 **0**。未重做 V4、历史波形或环境。所有标签仍是 `repository_guided_synthetic`。`physical_state=undetermined`、`numerical_validation=not_verified`、`eligible_as_validated_training_truth=false`。旧 Phase 2 仍为 `in_progress`，深度物理验证未完成。

本地证据根目录：[accuracy_v4_1_001](../reports/local/accuracy_v4_1_001/)。旧 V4 模型、选择、校准、逐点分数、搜索轨迹及历史失败保留。

## 1. 旧失败的检查结果

[完整诊断](../reports/local/accuracy_v4_1_001/diagnostics/diagnostic_summary.json)与[逐点残差](../reports/local/accuracy_v4_1_001/diagnostics/old_holdout_diagnostic_residuals.csv)读取旧 test 1536 行、challenge 512 行。这些已观察数据只用于诊断，不是本批新盲测，也不参与 B1/B2 拟合、选择或校准。

- 按 design_id 核对 CSV 与只读数据库：四列 X、三目标 Y、角色、行关联及 source/backend 一致。特征顺序为 `pump_power_W, filter_offset_nm, filter2_bw_nm, gain_length_m`；单位 W/nm/nm/m，目标 nJ/fs/MW。offset 是 SF1−SF2，固定 SF1=1040 nm，故 cw2=1040−offset；输入不是把 offset 与 cw2 同时当作自由参数。
- 原模型 SHA-256 为 `4e0097e404281b3b8eaee075fb1d7f6d7db3e4a817daa823ac04bc5cfd263935`。冻结训练源码、数据库/协议哈希、oracle/recipe 身份及原 CLI helper 均核对。发布 SQLite 单行没有完整 recipe/seed 元数据；版本由冻结数据库哈希和原 evaluator 身份关联，而非补造逐行信息。
- 保存预测、批量调用、单行调用、直接拟合 Pipeline 的 log 输出再 exp、实际 CLI loader/evaluator 路径一致。批量与直接 Pipeline 差为 0；单行/CLI 对旧 test 最大绝对差 `3.97904e-13`，对 challenge `3.41061e-13`。事前容差 `atol=1e-10, rtol=1e-10`，零违反。这里检查的是 CLI 复用的实际 Python 适配器，不是启动 2048 个 shell CLI。
- 声明域缩放与模型 `_x` 一致；三个目标的 scaler 都来自原 512 行 X、137 个变换特征，均值和方差复算最大差均为 0。预测未 fit、未按当前批次重新缩放、未查 oracle/缓存标签。只追加了使用范围元数据，数值及 Prediction 身份不变。
- `confirmed_wiring_issue=false` 表示这些实际检查中没有接线错误证据，**不等于证明所有潜在实现问题均不存在**。没有添加默认点特例、乘系数或偏差平移。

旧固定 P=4 W、L=4 m 的 128 点能量全部高估：

| 量（prediction−truth） | P50 | P90 | P95 | 最大 |
|---|---:|---:|---:|---:|
| 能量带符号/绝对残差 nJ | 5.128356 | 6.113557 | 6.512589 | 7.132823 |
| 能量带符号/绝对相对残差 | 3.885956% | 4.692617% | 4.807254% | 5.337969% |
| 容差归一化绝对残差 r | 1.295319 | 1.564206 | 1.602418 | 1.779323 |

平均能量偏差与 MAE 均为 +4.966128 nJ，平均相对偏差 +3.855552%，最小残差 +1.743462 nJ。能量通过 11/128=8.59375%，表示 117 点超过规定容差，**不是 91.41% 的数值相对误差**。切片脉宽平均偏差 +0.566167 fs、峰值 +0.053571 MW，二者容差通过率均 100%。[原始散点误差图](../reports/local/accuracy_v4_1_001/diagnostics/fixed_P4_L4_challenge_signed_error.png)直接用 offset×bandwidth 散点，没有插值成网格。

旧主 test 中 pump∈[4,6) 的 557 点能量 bias +0.245127 nJ、MAE 2.951987 nJ；正/负残差 293/264 点，通过率 89.7666%。绝对相对误差 P50/P90/P95/max 为 1.276590%/3.013728%/3.472241%/4.896249%；r 为 0.425530/1.004576/1.157414/1.632083。它并非整个分箱持续同向偏差，不能把该泵功率区间整体判不可用。脉宽/峰值通过率 100%/99.8205%。[分箱散点图](../reports/local/accuracy_v4_1_001/diagnostics/test_pump_4_to_6_signed_error.png)保留其他输入变化。

| 旧集合 | 能量 bias / MAE nJ | 脉宽 bias / MAE fs | 峰值 bias / MAE MW | E / τ / peak 容差率 |
|---|---|---|---|---|
| test 1536 | +0.139562 / 2.095031 | +0.008297 / 0.288012 | +0.004476 / 0.045576 | 95.3125% / 98.6979% / 99.9349% |
| challenge 512 | +2.741217 / 2.953154 | −0.023439 / 0.721014 | +0.041006 / 0.044855 | 71.0938% / 96.0938% / 96.4844% |

训练支持只看原 512 点 X：精确 P4/L4 **0** 点，P 恰为 4 **0** 点，L 恰为 4 **12** 点；P∈[3.5,4.5]、L∈[3.7,4.3] 邻域 **17** 点。pump∈[4,6) **190** 点。四维声明域归一化的最近邻距离，固定切片 P50/P95/max=0.117126/0.183919/0.258828；距离本身不能认证精度。

全部 2048 个诊断点中，242 点至少一个坐标超出样条训练 X 支持边界；P/offset/BW/L 分别 75/77/94/0 点（不可相加）。533 点超出至少一个变换特征的训练观测范围。样条分支采用 constant 外推，但模型另有多项式交互，不能把整个模型称为常数。这是所有诊断点的统计，不能直接当作固定切片失败原因。固定切片均在声明输入域内。

**原因证据分级：**已确认的是原切片系统性正偏及容差失败；检查过的接线未发现错误。覆盖/表示能力不足与现象相符，但未拆分二者因果。直接根因尚不能唯一确定，也没有证据支持通用偏差补偿。

## 2. 先冻结的对照与采样

[正常源码协议](../configs/accuracy_v4_1_protocol.json)与[本地冻结副本](../reports/local/accuracy_v4_1_001/protocol.json)在新标签/新拟合前独占写入，含源码哈希、旧模型身份、规则和种子。冻结合格后没有改学习源码或协议。使用原 spline_interactions：16 个 uniform knots、样条 degree=3、交互多项式 degree=4、Ridge alpha=0.1、log 正目标；只固定 order11，不挑种子、不换家族、不搜索超参数。

| 候选 | 实际训练设计 | 新拟合 | 本批角色 |
|---|---:|---:|---|
| B0 | 原 order11 前512 | 0 | 原冻结基准，不改权重 |
| B1 | 原 order11 前1024，包含前512 | 1 | 普通增量 |
| B2 | 原前512＋新训练512 | 1 | 定向覆盖增量 |

每次拟合包含原实现的三个目标回归器；没有另计成六个独立候选。三个实际训练 ID 清单位于 `development/B0,B1,B2/training_ids.json`；保存模型后对旧 validation 和新 dev 重载预测逐元素相同。

新训练 512：slice128、near_slice128、outer_faces64、corners64、reference_core64、reference_expanded64。新开发 512：四个特殊组各128。只按 X 采样；三个连续量保留六位小数，长度先采合法 0.1 m 整数格点；邻域排除精确切片；边界按8个面循环，角落按16个角的各轴外侧5%邻域，长度端各4个合法层级。expanded 排除 core。每个角色/组使用 SHA-256 派生的独立流，种子 train41011、dev41022、calibration41033、test41044；不读取生成器内部结点或系数。

排除表按四个规范化 float 输入生成 canonical ID，避免旧 ID 命名不同导致重复。旧标注、原锚点、旧搜索、20k 未标注候选、旧数据库和历史 ID 共 **28,589** 个唯一排除身份，来源映射 **51,435** 行；其中 **368** 个旧 canonical ID 没有 X，按已知 ID 方案排除，没有重建坐标。排除工作没有打开旧未用目标作选择。[排除清单](../reports/local/accuracy_v4_1_001/exclusions_before/)和[采样后清单](../reports/local/accuracy_v4_1_001/exclusions_after_development/)保留输入投影哈希、别名关联及拒绝日志。新两角色共1024个设计互不重复，也不与旧排除表重合。

容差不变：能量 max(2 nJ,3%|y|)，脉宽 max(1 fs,3%|y|)，峰值 max(0.05 MW,5%|y|)。旧参考 validation1024：每目标≥95%、联合≥90%，core/expanded 各目标≥90%；新四组：每组每目标≥95%、联合≥90%。只从全部通过者选择，先最少样本，再比较六组等权（core、expanded、slice、near、faces、corners）的各目标容差归一化 RMSE 均值；不让整体组再占一个权重。没有通过者就停止。

后置 calibration1024/test2048 的规则和种子同样预冻结，分布是 core25%、expanded25%、四特殊组各12.5%；**本次未生成/打开这些新标签**。其选择门控和空结果处理有组件测试，实际新校准/唯一最终评分分支未执行，不能宣称该分支本批集成通过。

## 3. 同预算开发结果与停止

下表各格为 **E / τ / peak / 联合**容差通过率（%）。旧参考每组512、总体1024；每个新开发组128。本表没有混入旧 test/challenge。

| 分组 | B0，512点 | B1，1024点 | B2，1024点 |
|---|---|---|---|
| reference 全体 | 96.680 / 98.535 / 99.902 / 95.313 | 97.070 / 98.633 / 100 / 95.801 | **94.824** / 99.023 / 100 / 93.848 |
| historical_core | 96.484 / 98.047 / 100 / 94.727 | 95.703 / 98.242 / 100 / 94.141 | 91.992 / 98.828 / 100 / 90.820 |
| expanded_proposal | 96.875 / 99.023 / 99.805 / 95.898 | 98.438 / 99.023 / 100 / 97.461 | 97.656 / 99.219 / 100 / 96.875 |
| 精确 P4/L4 切片 | 10.938 / 100 / 100 / 10.938 | 3.125 / 100 / 100 / 3.125 | 100 / 100 / 100 / 100 |
| 切片邻域 | 82.813 / 96.875 / 97.656 / 79.688 | 82.813 / 96.875 / 100 / 79.688 | **82.031** / 97.656 / 99.219 / **79.688** |
| 外边界面 | 85.938 / 98.438 / 96.094 / 83.594 | 96.875 / 99.219 / 100 / 96.094 | 95.313 / 99.219 / 100 / 94.531 |
| 角落邻域 | 88.281 / 86.719 / 94.531 / 75.000 | 99.219 / 100 / 100 / 99.219 | 100 / 100 / 100 / 100 |

六组等权归一化 RMSE：B0 **0.4969877911**、B1 **0.4277757129**、B2 **0.3258508860**。B2 平均误差最低，只能保留为最佳诊断候选；它在参考总体能量仅 **971/1024** 通过，在邻域能量 **105/128**、联合 **102/128**，不允许把94.824%四舍五入为95%以过门槛。

B1 普通加倍训练量改善了边界/角落，精确切片仍失败；B2 把精确切片开发集提升到128/128，却没有改善整个邻域并降低了参考总体能量通过率。说明本次固定表示、参数和单一顺序下，精确切片补样的收益没有自动推广到附近。它不能证明“所有1024点方案均无效”，也不能证明某个模型结构一定是唯一原因。未做多顺序鲁棒性或表示变更实验。

[完整对照与所有目标统计](../reports/local/accuracy_v4_1_001/development/comparison.json)保留 MAE/RMSE/R²、带符号统计、P50/P90/P95/max、容差比及 Wilson 区间；[扁平指标 CSV](../reports/local/accuracy_v4_1_001/summary/development_metrics.csv)、[对照图](../reports/local/accuracy_v4_1_001/summary/development_pass_rates.png)由实际记录生成。经验样本通过率门槛不是 Wilson 下界保证。

正式选择为 `selected=null`，[selection.json](../reports/local/accuracy_v4_1_001/development/selection.json)记录 `development_gates_not_met_no_holdout`。B1/B2 权重均另存并已重载核对；[B2 model.joblib](../reports/local/accuracy_v4_1_001/development/B2/model.joblib)只供诊断审阅。原模型继续保留。新 calibration、test、校准 q、测试区间覆盖、τ≤40/E≥100 新测试误判统计均为 **null / not_run：开发未达标**，没有把旧 q 套新模型，也没有写假 final_metrics。

## 4. 代码、测试与使用范围

实际新增：

- `src/mamyshev_ml/v41_diagnostics.py`、`v41_sampling.py`、`v41_experiment.py`、`model_usage.py`：已有结果诊断、X-only 排除采样、冻结开发/条件评估、按模型哈希匹配的使用说明。
- `scripts/start_v41.py`、`diagnose_v41.py`、`run_v41.py`、`summarize_v41.py`、`audit_v41_preservation.py`：独占快照、分阶段入口、已存结果制图和保全检查。
- `configs/accuracy_v4_1_protocol.json`、`v4_model_usage.json`；`tests/test_v41_diagnostics.py`、`test_v41_sampling.py`、`test_v41_experiment.py`、`test_v41_model_usage.py`。
- 本报告及 SCOPE/EXECUTION_STATUS 的 V4.1 状态增补。

既有源码仅改两处：

```python
# scripts/run_v4_budget.py：旧 batch 默认不变，复用原串行预算与进程监控器
parser.add_argument('--batch', choices=['accuracy_v4_001', 'accuracy_v4_1_001'],
                    default='accuracy_v4_001')
# 所有预算/锁/缓存路径指向选中且已独占创建的 evidence；未新增监控器。

# v4_evaluators.py / SurrogateEvaluator：数值和身份生成沿用原实现
record = {...}  # 原 Prediction、targets、model_identity、prediction_id
return annotate_prediction(record)  # 只追加模型版本/范围/限制
```

V4 精确权重哈希注册其参考分布通过、P4/L4 能量失败、challenge 联合与区间限制。pump[4,6)仅标为观测分箱短板，不是区域禁用。未知模型为 `not_evaluated`，仍可输出 Prediction；无失败标记不等于可靠认证。原冻结 `v4_ml.py`、`v4_roles.py`、`scripts/run_v4_ml.py` 及包内模型/指标源码没有改：旧 raw CLI 的历史输出保留，新常用 `scripts/v4_scan.py` 复用的 SurrogateEvaluator 已带范围字段。

新增 **31** 项组件方法通过（诊断8、采样8、选择/门控6、元数据及预算9）；复用 **10** 项既有回归通过（模型加载/source 与 Prediction/扫描4，角色/冻结/指标6）。没有把重复执行算新测试。首次 discovery 命令使用相对 tests 路径，因监控器工作目录不同失败，**0 个测试执行**；0.113265秒已入账。改用绝对路径后通过，没有隐藏该次失败。人工预测扫描只是两点 fixture，不是新 oracle 数据或物理设计。

本批没运行 MATLAB 短测、传播、旧波形分析、完整扫描演示或 BO。现有 MATLAB 数据生成、扫描、续扫、数据库、CSV/MAT 导出和真实调用代码原样保留；相关 Prediction 入库/源隔离/扫描路径执行了有限 Python 回归。未重新声明本批验证了全部 MATLAB 功能。真实执行许可仍默认关闭。

## 5. 成本、命令与保全

新增 oracle：train512＋dev512＝**1024 个唯一设计**，全部成功、无缓存命中、无未完成预留；剩余3072额度未消费。B1读取既有 train1024，B0/B2复用其中前512，旧训练标签并集1024；旧 validation1024用于选择，旧 test/challenge2048用于诊断。这些成本分开记录，不藏在“只训练1024点”中。只拟合B1/B2，各约0.0156秒；不是真实仿真成本。

ML 监控外部墙钟：旧诊断31.860000秒、开发全链5.136848秒、已有结果汇总/图2.375490秒，合计 **39.372338 / 900秒**。工程累计 **9.622469 / 300秒**，包含起点快照、失败 discovery、短测、协议冻结和末项保全；所有明细见[budget_ledger.json](../reports/local/accuracy_v4_1_001/budget_ledger.json)。计费口径为已有隔离监控器所包围的子进程墙钟，含对应初始化/退出；不把交互编辑等待、工具等待等未测时间补成运行成本。全部串行，CPU线程上限2；不使用GPU/云计算。保全核查时新证据 **70,327,457 bytes，约67.1 MiB**，随后只有报告/命令清单等小文件完善；主要体积是去重审计映射，无传播大场。

实际命令均由指定绝对 Conda 路径 `conda run -n mamyshev-ml --no-capture-output python` 执行；完整命令数组、stdout、runner 和时间保存在 `budget/{engineering,ml}/<label>/` 以及预算台账。主要步骤：

```text
scripts/start_v41.py
scripts/run_v4_budget.py --batch accuracy_v4_1_001 --timeout-s 90 engineering targeted_tests_002 -- -m unittest discover -s <repo>/tests -p test_v41_*.py -v
scripts/run_v4_budget.py --batch accuracy_v4_1_001 --timeout-s 150 ml diagnosis_001 -- scripts/diagnose_v41.py --out <evidence>/diagnostics --snapshot <evidence>/start_snapshot.json
scripts/run_v4_budget.py --batch accuracy_v4_1_001 --timeout-s 30 engineering protocol_freeze -- scripts/run_v41.py freeze --diagnosis <evidence>/diagnostics/diagnostic_summary.json
scripts/run_v4_budget.py --batch accuracy_v4_1_001 --timeout-s 500 ml development_001 -- scripts/run_v41.py develop
scripts/run_v4_budget.py --batch accuracy_v4_1_001 --timeout-s 60 ml summarize_001 -- scripts/summarize_v41.py
```

其中 `<repo>` 和 `<evidence>` 在实际命令中是已记录的本机绝对路径，不是执行时占位符。既有10项回归和末项保全命令也在台账。没有执行 `run_v41.py evaluate`。

起点分支 `feature/mamyshev-ml-mvp`，基础提交 `489bf4242f9b5266d47f8892840a24af66931ff0`；不切换、不提交。开始记录2522个既有文件哈希，[末项保全结果](../reports/local/accuracy_v4_1_001/preservation_check.json)核对旧 V4包/oracle/模型/评分/搜索、全部历史数据报告及 code 下源码。仅允许本批两份既有 Python 接线文件和 SCOPE/STATUS 增补变化；所有原有未提交物理修改也按开始字节保留。历史 observation_001 的 failed runner 与缺失 final 不补写。

实际保全结果 **passed=true**：2522个既有文件中2518个字节不变，4个变化恰为上述两份Python接线和SCOPE/STATUS；缺失0、非预期变化0。1306个历史证据/数据包文件全部不变，`code/` 全部不变，分支/commit一致。新旧设计交叉0、train/dev交叉0；两库各512条 Evaluation、0条 Prediction，source均为合成评价；新holdout四项产物仍不存在。`git diff --check` 返回0。原始未提交内容和历史失败没有被覆盖。

## 6. 审核后下一步建议（未执行）

优先研究为何相同表示下“精确切片修好、邻域仍失败、参考能量略回退”：使用已保存的新开发逐点残差，提出一个有明确假设的后续表示或局部覆盖实验，再申请新协议/预算。不能用本批未通过者直接给优化候选可靠性标签，也不应自动扩大到4096/100k或反复挑更好测试集。现有证据不足以在覆盖数量、训练分布与固定表示偏差之间作唯一归因。

**本批结束，等待审核。** 不额外重训、不启动真实候选评价、不进入下一 Phase，不作 GitHub 发布。
