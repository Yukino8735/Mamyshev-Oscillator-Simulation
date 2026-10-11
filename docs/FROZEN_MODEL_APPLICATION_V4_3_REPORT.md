# V4.3 冻结模型应用与有限候选确认

2026-09-28 UTC。本批完成冻结 V4.2 模型的显式预测入口、实际扫描/Prediction 数据库、CSV/MAT 导出读回，以及四场景一次有限合成确认。**64 次逻辑查询、63 个新设计、1 次缓存命中、0 次失败；模型法四场景均超过各自 T2 既有最好可行值，本次随机法均未超过。** 这是单种子、每方法8点且已有1024点训练先验的应用结果，不是冷启动优化、统计显著优势或物理最优。

权重、q、旧默认与历史证据保持不变；新增训练/开发/校准/测试标签、拟合、BO、MATLAB/GMMNLSE 启动均0。只新增 `candidate_verification` 角色的合成评价。[本批summary](../reports/local/application_v4_3_001/summary.json)分别记录 `pipeline_completed=true` 与 `candidate_goal_improved=true`，不能用后者替代工程完成判据。旧 Phase2 深度物理验证仍 `deferred/in_progress`；`physical_state=undetermined`、`numerical_validation=not_verified`、`eligible_as_validated_training_truth=false`。本批结束等待审核。

## 冻结身份与用途

实际本地分支 `feature/mamyshev-ml-mvp`，HEAD `489bf4242f9b5266d47f8892840a24af66931ff0`。已完整读取正式 V4.3 指令、适用 AGENTS、SCOPE/状态、V4.2 报告和相关源码。`V4_2_UPLOAD_REVIEW.json` 的报告、summary、release selection 三项哈希与字节数全部匹配本机；这只是核对审核对象身份，不冒充远端独立重算。

使用原 [model.joblib](../reports/local/accuracy_v4_2_001/release/model.joblib) 与 [release/selection.json](../reports/local/accuracy_v4_2_001/release/selection.json)，候选 `T2_K64_A0001`：训练1024点、64结点三次样条、degree4交互、alpha=.001、log目标。实际通过 `v42_release.load_release_evaluator` 核验完整绑定并加载；没有修改训练/加载器源码或改旧清单让校验通过。

| 资产 | SHA-256 |
|---|---|
| 权重 | `c236c2d2dd6cb5b59e32bd5ab4f8c3823f7fefc10d7571108a3d6339ee46b2e0` |
| 原 release selection | `603bf1e1ec670c2f151aaa879f0ec15b450b3b1ae1cd01abac301c27f82eb095` |
| 原 protocol | `fb624723207ee5f864976e70d971c3400fc2309313bf0467623237a59644f1cb` |
| 原 summary | `2595dcbdfe61094cb699ab0ac5735225e48262338096da512868888b1af9b06c` |
| 原 final_metrics | `2478d70d898d3898a5ed0cb3034d4f491baf8484b3d2a7ad61555686dbbf6d37` |
| 本批预测适配器 | `8b73b9d778d0247a22e94782ae79bb708a0dfa058881e70e44b84921033c0e32` |

完整依据见 [frozen_asset_check.json](../reports/local/application_v4_3_001/frozen_asset_check.json)。应用代码身份与原训练身份分开记录；新预测带 `application_adapter`、原 model/hash、来源/后端、单位、定义与限制。四输入仍严格为 W/nm/nm/m，域外、非有限、未知字段与非0.1m长度格点明确拒绝，不裁剪或取整；任意新点没有被擅自归为“已保证”的历史评估组。

V4.2 原2048点合成测试满足固定点误差容差，这是历史限定评估，不是零误差、未来输入或原 GMMNLSE 保证。本批不重开该测试。旧校准 q=`0.003266551289750619` 从原 `evaluation/calibration.json` 读取，没有硬编码产生区间或重校准。

**旧 release 没有直接绑定 calibration.json 的文件哈希。** 本批核对该文件的模型/选中候选及协议 n=1024、alpha=.05、rank=974、method，再检验 `2*sinh(q)` 与已哈希绑定的 final_metrics 三目标相对区间宽度一致，固定 atol=1e−14、rtol=0。该语义核对通过，另记录实际校准文件 SHA `5163e9f635cddd2432cb5e737439c0c9b9118d604c127907f65d5229eed5116a`；没有倒写旧manifest。缺失/不一致时保留点预测、区间 `null+reason` 的分支已测。

区间明确为 `limited`：历史联合经验覆盖总体1936/2048，near_slice仅216/256（84.375%）。它是诊断信息；跨阈值为 `uncertain`，完全位于一侧也仍需 Evaluator 确认，不是95%安全区间。

## 实际预测扫描与导出

新增薄 CLI `scripts/v43_scan.py` 显式接收 `--model` 与 `--selection`，复用原 `make_plan → execute_scan → V4Store → export_scan/plot_scan`。没有替换旧 `scripts/v4_scan.py` 默认模型。演示中的9个实际 CLI 子命令均退出0，工作目录在新证据目录，主动删除继承的 `PYTHONPATH`，由 CLI 自行建立可信模块路径；并非依靠交互会话才能反序列化。

单点输入 `{pump_power_W:4, filter_offset_nm:10, filter2_bw_nm:3, gain_length_m:4}` 的纯预测：

| 目标 | 点预测 | 诊断区间 |
|---|---:|---|
| compressed_energy_nJ |128.730669248|[128.310849968,129.151862131]|
| compressed_duration_fs |29.930087880|[29.832479222,30.028015904]|
| compressed_peak_power_MW |2.844749460|[2.835472101,2.854057174]|

这不是新真实基线或实测压缩场。合成代理没有复场，`waveforms=null`，没有生成时域/频域假波形。

- 三点向量化批量与逐行路径最大绝对差 `1.1368683772161603e−13`；单点CLI也一致。
- 对原测试CSV仅取前三条**已保存预测**核对适配器，最大差 `2.2737367544323206e−13`。两项固定 atol=rtol=1e−10，未放宽；不是重开一次测试评分。
- 一维曲线：固定 pump4、offset10、gain4，bandwidth取 `.5,1.4,2.3,3.2,4.1,5,5.9,6.8,8`，9点。
- 二维热图：固定 pump4、gain4，offset取 `2,3.75,5.5,7.25,9,10.75,12.5,14.25,16`，bandwidth同上，共81点。
- 两扫描实际分别写入9/81条 Prediction，Evaluation 表均0。三个目标均导出CSV/MAT，并重读逐元素核对 X、Y、设计ID、来源/模型身份、目标名称与单位；输入单位随摘要保存。没有缺失值画成0或为绘图调用oracle。

证据：[演示摘要](../reports/local/application_v4_3_001/demonstration/summary.json)、[9点CSV/MAT](../reports/local/application_v4_3_001/demonstration/curve/export/)、[81点CSV/MAT](../reports/local/application_v4_3_001/demonstration/heatmap/export/)。每目录有三个目标图，均注明 repository-guided synthetic surrogate prediction 和区间限制；线段仅连接已有9个预测点，热图显示原81点格子，不算新数据。

![本批9点预测曲线](../reports/local/application_v4_3_001/demonstration/curve/plots/compressed_energy_nJ.png)

![本批固定硬件预测热图](../reports/local/application_v4_3_001/demonstration/heatmap/plots/compressed_peak_power_MW.png)

## 一次冻结候选计划

实际场景为 `mamyshev_accuracy_v4/configs/scenarios.json`（不是不存在的仓库根 `configs/scenarios.json`），四定义与指令一致：S1 τ≤40最大peak；S2再加pump≤5；S3固定pump4/gain4；S4 pump≤7且E≥100最小τ。没有更改历史场景。

发布的20,000行X-only池包含global16000、fixed_P4_L4 4000，按包manifest核对身份和每行canonical ID/格点。**没有给整池取标。** 旧V4.2 holdout排除清单包含全20k未标注池，不能直接解释为它们均已评价。本批复用既有X/ID投影，从实际Evaluation JOIN、明确标注角色、历史搜索/查询记录重建13,915个排除身份；不读取排除Y排名、不复制67MB历史映射。该数包含历史保留身份，不等于13,915个新训练标签。隔离只能覆盖本仓库已有记录，外部或未记录查询无法确认。

其中1,230个候选池点因历史已评价而排除，剩18,770点仅做预测（global15072、fixed3698）。四场景相同输入可行池人数分别15072/5495/3698/9240；预测满足输出约束人数9357/2029/2722/6250。

模型法按原点预测目标排序、完全同分按canonical ID，取8；随机法从同一输入可行及同一排除池无放回取8，不按预测输出筛选。随机流固定 `SeedSequence([43043, zero_based_scenario_index])`。四场景两方法全部ID和原预测/有限区间/阈值关系一次存入 [frozen_candidate_plan.json](../reports/local/application_v4_3_001/candidates/frozen_candidate_plan.json)，冻结时间 `2026-09-28T06:58:51.471478+00:00`，plan hash：

`64932231e664c5a983130a72bce4a5bb5c64c11061c007192957c215e44a9daf`。

该计划在第一次新查询前冻结模型、场景、池、oracle/recipe、校准、应用代码与排除来源。确认前重新核对来源字节及完整 `SyntheticEvaluator.identity`，每个返回继续核对设计、来源、单位和有限值。oracle/recipe只做字节哈希和既有Evaluator调用，没有读取配方内容设计排名规则。

四场景的共同既有最好值只读取当前T2的1024条训练观察；不从旧test或全库挑最好点。双方均继承这个已知值，不把有训练先验的模型描述成从零8次搜索。

## 实际候选确认

完成64次逻辑事件、63个新独立设计、1次同源缓存命中、0失败；S1/S4模型名单共享一个点，仍按各方法查询计费。64次三目标容差均通过；这是定向确认的误差描述，不能新增“随机测试100%”声明。所有32个模型推荐均实际合成可行，模型/随机各场景均无预测假可行。随机法实际可行数为6/1/3/7。

S1随机点 `d_779968713a71b42879c8f3cd` 的τ预测39.895872220fs、实际39.944023963fs，区间跨40，如实标 `uncertain`，仍通过Evaluator确认；其余63个逻辑事件区间在阈值一侧。没有把区间当成确认许可或因不确定而换点。

以下结果名称均为 `best_evaluated_on_synthetic`；S1–S3单位MW（越大越好），S4单位fs（越小越好）。

| 场景 | 方法 | 查询 / 实际可行 | 共享T2既有最好 | 本批新评价最好 | 含既有的最终最好 | 相对既有改善 |
|---|---|---|---:|---:|---:|---|
| S1 |模型|8 / 8|13.520637947|14.343753053|14.343753053|是|
| S1 |随机|8 / 6|13.520637947|9.163755917|13.520637947|否|
| S2 |模型|8 / 8|7.882290246|9.023478515|9.023478515|是|
| S2 |随机|8 / 1|7.882290246|2.311168124|7.882290246|否|
| S3 |模型|8 / 8|3.925271991|3.954024075|3.954024075|是|
| S3 |随机|8 / 3|3.925271991|2.720107452|3.925271991|否|
| S4 |模型|8 / 8|20.303332577|20.181844851|20.181844851|是|
| S4 |随机|8 / 7|20.303332577|23.284711272|20.303332577|否|

没有惩罚分数冒充可行目标，没有改变种子或补跑。新值仅为本次实际已评价候选的最好值，不是整个20k池、连续域或物理最优；没有运行原64-query GP搜索，也没有改其旧轨迹。

![同批实际合成候选对照](../reports/local/application_v4_3_001/analysis/candidate_comparison.png)

逐点原预测/实际/容差/可行性见 [candidate_results.csv](../reports/local/application_v4_3_001/candidates/candidate_results.csv)，完整Prediction、区间和Evaluation来源见 `events.jsonl`、`candidate_verification.sqlite`；`oracle_queries.jsonl`按事件先预留后完成，锁保留，禁止重跑。最终机器记录为 [candidate_summary.json](../reports/local/application_v4_3_001/candidates/candidate_summary.json)。新查询没有进入原训练、开发、校准或test。

## MATLAB请求与当前真实链路状态

从本次实际合成可行候选每场景导出3条，共12条请求、11个唯一设计。复用原 `export_recommendations → make_plan → verify_plan → validate_live_authorization`，纯Python实际核对四字段传递与长度合法性。请求见 [matlab_requests.json](../reports/local/application_v4_3_001/candidates/requests/matlab_requests.json)、同目录CSV/MAT、`candidate_scan_plan.json` 和 `request_mapping_check.json`。

全部 `status=pending_manual_approval`、`max_new_real_attempts=0`、`real_targets=null`。合成Y只保留在明确命名的 `synthetic_targets`/`synthetic_Y`，没有写入real_targets；去重后的扫描计划11点仍不是执行授权。`zero_attempt_authorization.json` 中900秒等值只是原请求schema草案，0次额度禁止启动任何真实进程。

当前MATLAB启动0（含短测），真实整腔/扫描0。四维真实入口、1D/2D/4D扫描、逐点保存、取消续扫、CSV/MAT导出、数据库、recorded/真实路由及波形引用保留。历史 `validation_002` 等完整调用证据仍是历史证据，本批只完成Python组件和应用接线；没有把当前未运行的完整传播或深度物理验证写成通过，也没有补写旧missing-final。

## 修改与验证

新增正常源码 `v43_adapter.py`、`v43_candidates.py`；新增CLI/批次脚本 `v43_scan.py`、`start_v43.py`、`run_v43_budget.py`、`inspect_v43.py`、`test_v43_components.py`、`demo_v43.py`、`run_v43_candidates.py`、`summarize_v43.py`、`audit_v43.py`；新增 `test_v43_adapter.py`、`test_v43_candidates.py`、`test_v43_budget.py`。没有第二套训练、扫描或进程监控引擎。

唯一既有执行源码变化在 `v4_scan.plot_scan`：

```python
# 原先只画 completed Evaluation，Prediction 会被当成缺失。
r["status"] in ("completed", "predicted")
# 可选 source_title / limitation_note 用于本批图注明来源和限制。
```

可信release绑定了原预算脚本，因此**原 `run_v4_budget.py` 未改**。新薄入口导入其原main，仅用局部ArgumentParser代理限定新批次，并将本批工程/应用两个cap均设300秒。旧默认、串行锁、预留计费、拒绝覆盖、线程设置、STOP和所属进程清理逻辑原样复用；没有修改全局argparse或旧manifest。

**23项新组件＋18项相关旧回归，共41项通过，失败/错误0。** 新测试覆盖真实参数/单位拒绝、校准身份与null分支、单行批量、Prediction入库及导出、非空预测绘图、场景/tie/随机选择、未标注池与已评价排除区别、不解码排除Y、同源缓存计费、失败null、锁/超时不重试、Evaluator身份和返回身份、零真实请求映射。全部是人工组件/只读历史角色检查，无新训练或oracle标签。旧回归为可信加载8、输入/Prediction/计划/CLI6、零真实授权2、角色2；未重跑其他旧测试或MATLAB。

实际应用检查与组件测试分开：9个CLI命令、90条扫描Prediction、3条已存预测接线回归、一次64逻辑候选确认、一次离线已有结果绘图。模型应用预测行合计18,933（18,770个未评价池点＋63次入选单行一致性＋演示100），这些行数包含重复数值检查，**不等于18,933个标签或物理仿真**。

## 成本、命令与停止

应用外部墙钟：演示5.448052s、候选预测/冻结2.353999s、确认0.862886s、已存结果分析0.533637s，累计 **9.198574/300s**。候选循环内部计时0.133694s不含完整启动/加载，不能代替外部预算。工程累计 **16.198041/300s**（其中组件11.998024s、末项保全0.967589s）；完整计费见本批 [budget_ledger.json](../reports/local/application_v4_3_001/budget_ledger.json)。这些是沿用监控器记录的外部子进程墙钟，不是整段人工开发会话时长。全程串行、最多2CPU线程，无GPU/云资源；峰值RSS未测，启动前内存为估计值。没有失败执行或自动重试。保全核查时本批产物共9,676,032字节，不含随后写出的保全/summary/命令摘要。

先验/历史成本单列，不能把本轮8点称为全部研究成本：

| 范围 | 已记录成本（存在重用，禁止逐行简单相加） |
|---|---|
| 当前冻结模型 |T2共1024训练设计：旧512＋V4.1新增512；旧权重复用，本批fit0|
| V4模型开发历史 |早期pilot已接触train4096/validation1024；V4本地选择使用unique train1349＋validation1024，fit8|
| V4一次评价 |calibration1024、test1536、challenge512；保留原成功与失败|
| V4独立冷启动搜索 |24个历史实验，1536逻辑事件、1230唯一计算、306缓存；本批不重做|
| V4.1 |新增train512＋dev512=1024；fit2，旧test/challenge2048仅历史诊断|
| V4.2 |T1/T2训练并集1536，开发1536均旧数据；新增cal1024＋test2048=3072，fit10|
| 本V4.3 |新训练/dev/cal/test0；candidate_verification逻辑64、新唯一计算63、缓存1；无重校准/BO|

上述来自原各批selection/summary和预算台账，未重算旧预测。历史预算工程/ML秒分别为V4 39.765384/22.009273、V4.1 9.622469/39.372338、V4.2 9.073630/19.715580；它们不代表用户更早全部人工/实验成本，也不换算真实GMMNLSE节省率。

所有项目Python由固定命令启动：

```text
/opt/homebrew/Caskroom/miniforge/base/bin/conda run -n mamyshev-ml --no-capture-output python ...
```

实际执行的主步骤（路径实参详见本批台账及 `commands.json`）：

```text
scripts/start_v43.py
scripts/run_v43_budget.py --timeout-s 30 engineering frozen_asset_check -- scripts/inspect_v43.py
scripts/run_v43_budget.py --timeout-s 120 engineering application_components -- scripts/test_v43_components.py
scripts/run_v43_budget.py --timeout-s 180 ml prediction_demo -- scripts/demo_v43.py
scripts/run_v43_budget.py --timeout-s 90 ml candidate_plan -- scripts/run_v43_candidates.py freeze --model <原V4.2权重> --selection <原V4.2清单> --out <新批次/candidates>
scripts/run_v43_budget.py --timeout-s 120 ml candidate_confirmation -- scripts/run_v43_candidates.py confirm --plan <新批次/candidates/frozen_candidate_plan.json>
scripts/run_v43_budget.py --timeout-s 45 ml saved_result_analysis -- scripts/summarize_v43.py
scripts/run_v43_budget.py --timeout-s 45 engineering preservation_final -- scripts/audit_v43.py
```

实际扫描命令包括 `predict --input ... --out ... --model ... --selection ...`，以及各曲线的 `plan`、`run --execute --max-new-attempts 9/81 --total-wall-s 30 --stop ... --model ... --selection ...`、`export`、`plot`；完整绝对argv、无PYTHONPATH环境和退出码在 [demonstration/commands.jsonl](../reports/local/application_v4_3_001/demonstration/commands.jsonl)。取消入口沿用 `budget/<category>/<label>/STOP`，没有取消、超时或后台续跑。

末项[保全检查](../reports/local/application_v4_3_001/preservation_check.json)通过：起点2757份既有文件中2754份未变，仅绘图函数和两份状态文档变化；缺失0、意外变化0。1512份历史证据均未变，原模型/配方/旧test/cal和全部生产物理源码保留，原预算脚本未变，release再次完整核验通过。候选数据库实有63条Evaluation与63条独立Prediction，64次事件计费一致；零真实额度请求检查和 `git diff --check` 均通过。新应用源码的完整哈希另存于该检查，不改训练身份。SCOPE/EXECUTION_STATUS新增当前应用状态，旧阶段记录保留。无环境/权限更改、分支切换或Git发布。

本批到此结束。冻结点预测已完成限定评估，区间仍limited，应用接线与有限合成确认已执行；真实候选仍待后续明确审批。没有自动替换默认模型、执行MATLAB候选、开展下一轮搜索、数值验证或下一Phase。
