# Accuracy-first V4 执行报告

2026-09-28 UTC。本次正式指令为 `mamyshev_accuracy_v4/CODEX_V4_PROMPT.md`，替代旧 V1/V2/V3 和扫描补充条款。本修订阶段已完成并停止，等待审核。

**功能状态：本阶段规定的离线 ML、合成扫描、历史导入及无传播 live 接线验收已完成；新的完整真实扫描为 not_run。精度状态：512 点样条模型通过开发选择和唯一主测试门槛，但挑战分布存在明显失败，不能称整个四维域可靠。新增真实 GMMNLSE / 整腔尝试为 0。**

主测试三目标容差通过率为 **95.31% / 98.70% / 99.93%**，同点联合通过率 **94.08%**。挑战集联合通过率只有 **65.04%**，固定 P=4 W、L=4 m 切片的能量通过率只有 **8.59%**。模型、阈值及训练规模没有因挑战结果而调整。

所有新结果都是明确标注的合成标量学习/查询，或只读历史结果。真实 solver 泛化误差和墙钟节省仍为 null/not_measured；H02、长期物理稳态、独立网格/窗口/步长收敛 deferred。继续保留 `physical_state=undetermined`、`numerical_validation=not_verified`、`eligible_as_validated_training_truth=false`。

## 起点、身份及数据完整性

已完整读取 V4 提示、README、EXECUTION_LOGIC、accuracy_protocol、MANIFEST、DATA_CHECKS、DATA_BUILD_SUMMARY，以及适用 AGENTS、SCOPE、EXECUTION_STATUS、配置波形和 stationarity 报告；实际检查原生产入口、记录器、启动器、监控器、参考模型和相关测试。AGENTS 中旧 Phase 0 授权范围由本条 V4 明确指令取代。

本机 macOS/arm64，分支保持 `feature/mamyshev-ml-mvp`，基础 commit 为 `489bf4242f9b5266d47f8892840a24af66931ff0`。起点记录 2281 个已有文件哈希及完整 dirty 状态，见本地 [start_snapshot.json](../reports/local/accuracy_v4_001/start_snapshot.json)。没有切分支、reset/clean/stash、提交或发布。旧报告、timeout、原始 MAT、旧 final 和源码身份保留。

| 数据 | 本地核查结果 |
|---|---|
| 发布标签 | train4096 / validation1024 / calibration1024 / test1536 / challenge512，共8192个合成设计；不是8192次传播 |
| 历史继承 | V3 train512/validation128共640行保留；旧test256/boundary128共384个ID排除；没有混用V1/V2模型或标签 |
| 候选 | 20000行只有X；本次另外保存预测，不回填原候选CSV目标 |
| 原solver计划 | 8192行目标仍全部为空、状态not_run；没有以synthetic标签填充 |
| 文件身份 | MANIFEST的70项文件大小/哈希匹配；冻结V3 Python oracle、配方和MATLAB oracle未改 |
| 原发布测试 | 15个方法中13通过、2失败；失败是跨平台浮点逐位/CSV字节相等，不写成15/15通过 |
| 补充本地复算 | 8192行最大差异 E=2.27374e−13 nJ、τ=9.94760e−14 fs、P=7.99361e−15 MW；非逐位相等值数162/100/223；输入、角色、非标签元数据及训练顺序一致 |
| MATLAB实际复算 | 24点parity通过；8192行最大差异 E=1.02318e−12 nJ、τ=1.27898e−13 fs、P=2.30926e−14 MW；RNG不变、0传播 |

本地补充核查沿用包中既定的 `1e-10 + 2e-10*abs(reference)` 单位容差，没有改原精度门槛、发布文件或失败测试。补充检查脚本首次错误地要求原 builder 重建另行继承的候选CSV而失败；修正检查范围后通过，失败日志和费用保留。原 builder 实际重建标签/solver计划；候选单独核对哈希、schema和不重叠性，不声称其经过该 builder 字节重建。

证据：[发布核查](../reports/local/accuracy_v4_001/release_local_checks.json)、[原失败日志](../reports/local/accuracy_v4_001/budget/engineering/release_checks/stdout.log)、[MATLAB parity](../reports/local/phase2/accuracy_v4_001/synthetic_parity_001/parity_summary.json)。包内 DATA_CHECKS 是发布时历史状态，未覆盖为本机状态。

一致性复算可以接触 evaluation 标签，但只做完整性核对，没有模型打分或调参。模型选择器默认只打开只读 development.sqlite，并强制角色/source/训练前缀ID；calibration/test/challenge 只在模型哈希冻结后开启。未发现本批在开发前使用 V4 holdout 模型分数的行为；公开配方本身不等于真实未知物理后端。

## 固定模型、规模选择与冻结

四输入按原声明域缩放，正目标独立 log 拟合，回原单位验收。复用包内未改的 `models_v4.py`：二阶多项式+Scaler+Ridge(alpha1)；16均匀结点三次Spline主效应+degree4 Polynomial交互+Scaler+Ridge(alpha0.1)；每目标 HistGB(300iter,31叶,lr0.08,min_leaf10,l2=0.1,early_stopping=false)。样条结点只由当前训练X决定。无oracle中间量、系数、历史曲线结点或 E/τ 特征。

门槛固定为每目标总体≥95%、三目标联合≥90%、核心/扩展各目标≥90%；容差为 `max(atol,rtol*abs(y))`：E 2 nJ/3%，τ 1 fs/3%，P 0.05 MW/5%。这不是光学标准，也不把 Wilson 下界要求擅自加入或删掉。

下表均在同一1024点validation计算；百分数只是容差通过率，R²不是准确率百分比。

| 家族 | n | 顺序 | E通过% | τ通过% | P通过% | 联合% | 均值归一化RMSE | 全部门槛 |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| ridge2 |256|11|22.85|47.66|31.35|10.25|2.92544|失败|
| spline_interactions |256|11|93.46|97.27|99.61|91.21|0.41349|失败：能量总体不足95%|
| hist_gb |256|11|35.94|50.29|36.62|12.50|2.68267|失败|
| ridge2 |512|11|26.27|46.58|35.25|11.04|2.80746|失败|
| spline_interactions |512|11|96.68|98.54|99.90|95.31|0.33588|通过|
| hist_gb |512|11|43.46|63.28|47.75|23.05|2.10453|失败|
| spline_interactions |512|22|96.19|98.44|99.51|94.43|0.34478|通过|
| spline_interactions |512|33|95.90|98.63|99.32|94.34|0.35208|通过|

512点样条三个顺序核心/扩展最低单目标通过率分别为96.48%/96.88%、94.53%/97.85%、94.73%/97.07%，均通过90%组内要求。因此按规则停止升档，1024/2048/4096未拟合，未挑选最好seed。8次候选拟合，每次含三个目标模型；生产权重固定使用order11的512点，未再拟合一次“最终模型”。样条家族来自包发布前的开发比较，不宣称家族选择是盲预注册。

生产权重保存/实际joblib重载，对1024点validation预测逐位一致（最大绝对差0）。四输入默认值(4,10,3,4)实际预测为 E=133.650999530 nJ、τ=30.723091349 fs、P=2.882495433 MW；它是 Prediction，不是原solver实测。另经实际 `SurrogateEvaluator` 写入 prediction表，oracle evaluation表数量未增加。最终CLI又对既有5点计划实际生成5条Prediction并独立入库，没有新的oracle标签。

冻结时间 `2026-09-28T04:25:18.064247+00:00`；model SHA-256 `4e0097e404281b3b8eaee075fb1d7f6d7db3e4a817daa823ac04bc5cfd263935`；protocol SHA-256 `89869bf5f9702a2f27f8b4d60199c1759bfcfb0a2beaa457a48566ae146562ff`。source/split/参数/训练ID见 [selection.json](../reports/local/accuracy_v4_001/models/selection.json)。冻结后任何来源/权重/协议变化会拒绝评估；本批模型哈希的一次评估锁位于固定目录，复制权重到另一目录不能重开同一holdout评估。

![本地实际学习曲线](../reports/local/accuracy_v4_001/models/learning_curve.png)

本地选择实际读取1349个唯一train标签和1024个validation标签，共2373个，不是整个研究只看512标签。包制作阶段此前已看4096+1024个开发标签；独立校准/最终评估随后另用3072个。完整性复算8192行是另一个用途，不能将它混算为模型训练量。

## 唯一冻结评估：主测试与挑战必须分开

下表误差单位跟随目标；P50/P90/P95为相对误差百分数。非有限输入/输出直接失败、不静默删点；近零相对误差分母下限固定1e−12，本次触发0次。常值真值R²为null并给原因，包含小数常值的回归测试。

| 数据/目标 | MAE | RMSE | R² | 相对误差P50/P90/P95 % | 最大绝对差 | 容差率% [Wilson95%] |
|---|---:|---:|---:|---|---:|---|
| test E nJ |2.095031|2.839396|0.999153|0.826/2.325/2.974|11.778467|95.313 [94.138,96.261]|
| test τ fs |0.288012|0.443239|0.998549|0.544/1.633/2.124|3.508097|98.698 [97.997,99.156]|
| test P MW |0.045576|0.065159|0.999370|0.874/2.354/2.751|0.321946|99.935 [99.632,99.989]|
| challenge E nJ |2.953154|4.001376|0.998185|2.191/4.315/4.707|15.872243|71.094 [67.021,74.852]|
| challenge τ fs |0.721014|1.042218|0.998796|1.128/2.278/2.804|4.261242|96.094 [94.044,97.457]|
| challenge P MW |0.044855|0.065625|0.998585|2.321/5.613/6.809|0.307350|96.484 [94.512,97.765]|

主test1536联合通过率94.0755%，Wilson [92.7813%,95.1498%]；challenge512为65.0391%，Wilson [60.8106%,69.0436%]。主test能量的Wilson下界低于95%，不等于违反预定的样本通过率门槛，也不能被省略成总体95%保证。

| 分组 | n | E/τ/P容差率% | 联合% | 联合区间覆盖% |
|---|---:|---|---:|---:|
| test historical_core |773|93.53 / 98.19 / 100.00|91.72|93.79|
| test expanded_proposal |763|97.12 / 99.21 / 99.87|96.46|95.28|
| challenge outer_boundary |256|92.19 / 98.05 / 94.92|87.11|67.19|
| challenge fixed_P4_L4 |128|8.59 / 100.00 / 100.00|8.59|16.41|
| challenge corner_neighborhood |128|91.41 / 88.28 / 96.09|77.34|40.63|

尤其固定硬件切片的能量误差不能被其余目标高R²或总体均值掩盖。challenge不是同参考混合分布的独立重复，不能套用同分布覆盖承诺。本批只报告，不增加数据/换模型重测。

主test四等宽输入分箱结果（区间左闭右开，最后箱右闭；E/τ/P通过率依次排列）：

| 变量/区间 | n | E/τ/P % | 联合% |
|---|---:|---|---:|
| pump [2,4) W |380|96.32/94.74/100|91.32|
| pump [4,6) W |557|89.77/100/99.82|89.77|
| pump [6,8) W |396|100/100/100|100|
| pump [8,10] W |203|99.51/100/100|99.51|
| offset [2,5.5) nm |341|95.60/97.95/100|93.84|
| offset [5.5,9) nm |530|95.85/99.06/100|94.91|
| offset [9,12.5) nm |461|93.93/98.48/100|92.41|
| offset [12.5,16] nm |204|96.57/99.51/99.51|96.08|
| BW [0.5,2.375) nm |399|96.24/98.50/100|94.74|
| BW [2.375,4.25) nm |471|94.48/98.73/100|93.21|
| BW [4.25,6.125) nm |458|94.98/98.91/100|93.89|
| BW [6.125,8] nm |208|96.15/98.56/99.52|95.19|
| gain [1,2.75) m |243|95.88/99.59/100|95.88|
| gain [2.75,4.5) m |576|96.01/98.78/100|94.79|
| gain [4.5,6.25) m |495|94.75/98.18/100|92.93|
| gain [6.25,8] m |222|94.14/98.65/99.55|92.79|

主test真值τ38–42 fs组n=160，E/τ/P率94.375/96.875/100%，联合91.25%；E95–105 nJ组n=42，三项各97.619%、联合95.238%，**低样本支持**。challenge对应n=55与16、联合61.818%与43.75%，后者也低样本支持。所有组/分箱的完整MAE、RMSE、R²、分位误差、Wilson和挑战分箱已保存 [final_metrics.json](../reports/local/accuracy_v4_001/evaluation/final_metrics.json)，不因分箱低分反向调参。

![唯一主测试预测及误差](../reports/local/accuracy_v4_001/evaluation/test_errors.png)

[挑战集实际误差图](../reports/local/accuracy_v4_001/evaluation/challenge_errors.png)。逐点CSV保存真实标签、冻结预测和区间；不重新计算第二轮评分。

## 独立校准与约束筛选

冻结后读取1024点calibration，joint max absolute log residual，alpha=.05，秩974，q=0.03236704829091064。三目标共同使用 `prediction*exp(±q)`，相对总宽约6.47454%。没有用校准标签改权重、选规模或重新训练。

| 数据/目标 | 实际覆盖% [Wilson95%] | 区间宽中位 / P95（原单位） |
|---|---|---|
| test E |96.875 [95.881,97.635]|13.633945 / 25.058665 nJ|
| test τ |98.958 [98.315,99.358]|2.202947 / 3.853727 fs|
| test P |97.591 [96.697,98.247]|0.266244 / 0.565714 MW|
| challenge E |69.531 [65.411,73.360]|8.238302 / 21.245365 nJ|
| challenge τ |96.484 [94.512,97.765]|2.941874 / 7.662666 fs|
| challenge P |70.117 [66.014,73.920]|0.123031 / 0.347177 MW|

实际联合覆盖：test **94.5313% [93.2791%,95.5612%]**；challenge **47.8516% [43.5567%,52.1784%]**。理论名义95%仅在交换性、相同参考分布下作联合边际声明；不是每个点、切片、边界、主动优化候选或MATLAB的95%保证。挑战覆盖失败照实保留。

τ≤40 fs任务，precision/recall按合成真值计算，非物理类别：

| 数据/筛选 | 选中 / 总数 | false-feasible | precision | recall | 未选中 | uncertain |
|---|---:|---:|---:|---:|---:|---:|
| test point |1096/1536|6|99.453%|99.453%|440|全体94|
| test upper≤40 |1044/1536|0|100%|95.255%|492|94全部弃权|
| challenge point |181/512|4|97.790%|96.721%|331|全体39|
| challenge upper≤40 |160/512|0|100%|87.432%|352|39全部弃权|

主test保守筛选覆盖67.969%输入；precision Wilson下界99.633%、recall Wilson [93.831%,96.364%]。challenge筛选覆盖31.25%，precision下界97.655%、recall [81.847%,91.477%]。区间跨40标uncertain；未选中也包含明确不满足约束者，不把所有未选中混称不确定。零次误判是这次经验值，不是未来候选零风险保证。

## 独立条件查询对照

与监督学习完全隔离：每场景/seed各方法从共同16点开始，后12批×4；选定整批并fsync批锁后才调用synthetic evaluator。未读取监督标签/权重、校准/test/challenge或oracle系数指导选点。固定log多目标GP使用Matérn2.5、length_scale=.35、alpha=1e−6、optimizer=None，最多用60个已观察点拟合最后一次采集模型。候选池每实验≤4096，S3为4000；不是给20000点预计算Y后查表取优。

全部24序列完成，**1536逻辑事件 = 1230唯一计算 + 306缓存命中**。16/32/64预算点均24/24有实际可行点；早期无可行处保留null。以下64次终点为3个种子的中位[最小,最大]；全部24序列的16/32/64值与误判/候选详表见 [搜索摘录](../reports/local/accuracy_v4_001/search_report_notes.md) 和原 [experiment_summaries.json](../reports/local/accuracy_v4_001/search/experiment_summaries.json)。

| 场景 | 条件/目标 | GP | random |
|---|---|---|---|
| S1 | τ≤40，最大P MW |14.495433 [14.346262,14.922996]|10.827394 [10.595879,10.985664]|
| S2 | 另pump≤5，最大P MW |9.843885 [9.415626,9.843885]|7.459385 [6.682697,8.671796]|
| S3 | pump4/L4固定，τ≤40，最大P MW |3.996139 [3.996139,3.996139]|3.711079 [3.677688,3.849530]|
| S4 | pump≤7/E≥100，最小τ fs |20.061453 [20.013675,20.092473]|22.077907 [21.188020,22.948093]|

本次12个配对GP终点更优，只有3个固定seed、固定构造配方，不宣称普遍或统计显著更优。GP的576个带预测推荐点中567个被预测可行，**88个实际不满足约束**；推荐点整体MAE为37.705574 nJ / 5.041124 fs / 1.280876 MW。每序列48个推荐的完整误差均保留。random没有预测器，其预测误差/false-feasible为null+reason，不是0。GP约束概率乘积未经校准，不能解释为物理稳定概率。

同场景已查询并集事后最佳分别14.922996 MW、9.843885 MW、3.996139 MW、20.013675 fs；只是在实际查询并集中的有限参考，不是连续全域最优或严格全域regret。跨场景有设计重叠，不能把各场景唯一数相加冒充独立样本。

![全部种子轨迹与中位范围](../reports/local/accuracy_v4_001/search/all_seed_trajectories.png)

图中早期中位数仅在已有可行点的种子上统计，配套 `trajectory_aggregates.json` 明确可行/无可行种子数量；没有将缺失补0。16/32/64各检查点均无缺可行种子。

每场景3个、合计12个实际synthetic评价过的候选已导出 [JSON](../reports/local/accuracy_v4_001/search/matlab_requests.json)、[CSV](../reports/local/accuracy_v4_001/search/matlab_requests.csv)、[MAT](../reports/local/accuracy_v4_001/search/matlab_requests.mat)。全部 `pending_manual_approval`、`max_new_real_attempts=0`、`real_targets=null`；不产生真实波形，不作为已执行MATLAB结果。本批没有运行这些请求。

## MATLAB生成、扫描、保存与数据库功能矩阵

| 功能 | implemented | tested_current | historical_evidence / blocked / not_run |
|---|---|---|---|
| synthetic Python/MATLAB evaluator | 同冻结V3配方、有限标量与来源身份 | Python8192复算；MATLAB24 parity+8192复算 | 非原GMMNLSE替代标签；没有虚构复场 |
| recorded精确查询 | design+source/backend/numerical_version+seed+observation+metric匹配；缺失not_available | 来源/身份不匹配、无fallback、candidate拒绝、失败null测试；成功历史导入实际执行 | observation_001仍缺final，不导入为成功 |
| gmmnlse live | 新计划行→MATLAB读取launch_request及授权/选中设计校验→原recorded→config→同一生产循环→尾纤/同次压缩→writer→父final | 5次真实无传播初始化；默认/单独改变4.1W、9.5nm、3.2nm、4.1m，gain/filter/L/总长/t_rep实值；7组校验 | 原config_waveform_001六圈为历史证据；新配置驱动完整传播和真实扫描not_run；本批无当前传播阻塞结论 |
| surrogate | 冻结已训练模型只生成Prediction，独立表 | 实际重载、四输入预测、Prediction入库；oracle表未增加 | 无波形、不是已评价设计 |
| 1D/任意2D/4Dgrid/LHS/random/CSV/候选计划 | 合法性、明确固定项、去重、哈希、默认只plan；长度不偷偷取整 | 1D5点/2D9点真实合成执行；4D16点、LHS5、random5、CSV去重只plan | 8192原solver计划未执行且Y为空 |
| 串行执行/设计间续扫 | 原supervisor；计划/允许ID/次数/单点总时间/显式real双门；全局授权持久账本 | 合成先执行2点取消，续扫至5点，再续扫新增0；身份缓存跳过，failed不重试、unknown running阻断；小于live预算的scan请求拒绝 | 无腔内checkpoint；真实逐点续扫not_run |
| 逐点保存/DB/导出 | designs/evaluations/predictions/attempts分表；单位、来源版本、seed、协议、平面、产物可追溯 | 演示13新synthetic设计+1历史evaluation（同一默认design），13attempt；CSV/MAT导出；新增1预测独立保存 | synthetic与真实历史共库但训练显式source筛选，预测不能进标签表 |
| 曲线/热图/真实波形读取 | 1D响应、固定其余参数2D三指标热图；原MAT复场/频谱读取 | 实际6张扫描图及旧真实MAT读取图；无插值、缺点NaN留空 | 无场的synthetic/Prediction返回not_available，不造波形 |
| 清理EPERM/失败final | 沿用原monitor，present/absent/unknown分开；仅本次失败runner可由父进程写failed final | 自身短shell进程+受控EPERM、未知组拒绝、timeout/STOP优先、写盘失败保留错误 | 未复现历史OS根因；旧missing-final不补写，不把leader退出当组为空 |

运行许可默认关闭不是空接口：`GMMNLSEEvaluator.evaluate` 实际调用 `execute_authorized_design`，后者仍调用原 `execute_once`。Python核验完整plan hash并把选中计划行、design_id、授权和余量写入launch_request，MATLAB读取并检查该行后走原真实入口；没有另建传播引擎。C传播参数/计数/完整波形gate保留，本批只执行A/B与组件，**不声称实际C传播已重新验证**。

默认配置(4 W,offset10 nm,BW3 nm,gain4 m)及legacy兼容不变；SF1固定1040 nm、SF2=1040−offset。声明探索域为P[2,10]W、offset[2,16]nm、BW[0.5,8]nm、L[1,8]m且0.1m格点；这是探索输入域，不是经过验证的器件工作域。三段无源仍0.4/1.5/3.2m、尾纤0.2m；实际Nt32768/50ps/max_rt50、步长/容差/随机/停止规则未改。新live请求默认seed0/twister和legacy观察协议，实际初始化会核对请求到B，不只信身份JSON。

H02继续保留：无源声明MFD10.5μm，而SR仍来自原默认5.95μm派生，SR=35964678899.37611m⁻²、面积2.7805058479678165e−11m²；未重算SR。1-H、滤波公式、N_total覆盖、材料、初态、尾纤和压缩假设未改。

只读导入的 `config_waveform_001` 保持旧源码摘要 `54c9be5a5084b0f83735ad60f5c99233934b1d780e745ce0b5745f0b3b9d05bd`、repair_001_h01_h04、seed0、legacy停止身份，不标成本批新运行。真实压缩后E=128.66941786965054nJ、原局部宽度29.84941905629446fs、P由2850940.6179669127W显式换算约2.850940617966912MW；场为32768×1实际复数组。

MAT仅读取，使用原 `fftshift(ifft)`、sqrt(W)/ps/THz和trapz/1000约定。SF1 post能量128.71968200801635nJ、尾纤128.7146060101117nJ、压缩128.66941786965054nJ；没有用post场积分替换历史pre能量，不重跑压缩器。manifest/MAT哈希、字节数、单位和身份校验后读取，绝对路径/逃逸引用拒绝。证据：[实际演示及历史导入](../reports/local/accuracy_v4_001/data_chain/demo_001/demo_report.json)、[真实保存场图](../reports/local/accuracy_v4_001/data_chain/demo_001/historical_mat_read/saved_waveforms.png)、[Prediction独立入库](../reports/local/accuracy_v4_001/data_chain/frozen_prediction_store.json)。

## 入口、安全约束与实际修改

新增正常源码：`v4_roles.py`（角色/冻结）、`v4_ml.py`（选择/一次评估）、`v4_evaluators.py`、`v4_store.py`、`v4_scan.py`、`v4_search.py`，均在 `src/mamyshev_ml/`；CLI/分析验证脚本在 `scripts/`。新增 `mamyshev_validate_launch_context.m`、两份MATLAB短测和四个V4 Python测试模块。完整新文件清单与起点差异见 [delivery_review.json](../reports/local/accuracy_v4_001/delivery_review.json)。

已有文件仅按需修改：`supervisor.py`（授权账本/失败final）、`run_mamyshev_once.py`（配置计划入口）、`launch_mamyshev_once.m`（复用校验器）、`tests/run_matlab_short.py`（EPERM安全核查/V4短测预算）、environment.yml和pyproject.toml的依赖记录，以及SCOPE/EXECUTION_STATUS。**环形腔生产初始化/循环、传播/增益/收敛/压缩数值代码没有本批改动**，原未提交物理修改仍保留。

关键规则：`execute_real is not True or max_new_attempts == 0` 在预留之前拒绝；同授权ID全局ledger不随run_id/DB/目录重置；未完成预留保守扣完整cap并阻断续扫。已失败设计不自动重试，新尝试需新明确授权且计费。scan总预算比live授权小则拒绝；剩余时间放不下完整单点cap便停止，不偷偷改数值参数。

STOP有明确作用范围：scan `--stop` 在设计之间生效；授权目录/batch的STOP阻止下一点；活动 `<run_dir>/STOP` 由原monitor停止当前所属进程组。只操作本次启动的新会话，不凭旧PID杀进程。EPERM只有成功只读进程表确认该组不存在才可解除，否则cleanup_error保留、父final失败、CLI非零。timeout/取消仍优先。最终写盘失败不冒充成功，不复制candidate。

用户入口为 `scripts/v4_scan.py plan --spec ... --out ...`；spec支持grid/1D、任意2D、4D、lhs、random、csv、candidates。`run` 不带 `--execute` 只显示计划；gmmnlse还需独立授权JSON和 `--execute-real`，默认新尝试0。完整必需授权字段、单点dry-run、三个STOP位置和源码行号见 [live接线说明](../reports/local/accuracy_v4_001/live_matrix_notes.md)。这是可用入口说明，不是本批追加真实运行许可。原scan_mamyshev/线性腔/历史图入口保留，新的串行入口薄接已有单点生产链。

## 测试、命令与实际预算

Python实际环境为 `/opt/homebrew/var/conda_envs/mamyshev-ml/bin/python`，Python3.11.16、arm64；Conda为 `/opt/homebrew/Caskroom/miniforge/base/bin/conda`，版本26.3.2。V4所需栈原先缺失，仅在mamyshev-ml安装 numpy2.4.6/scipy1.17.1/scikit-learn1.9.1/matplotlib3.11.2/joblib1.6.0/threadpoolctl3.7.0及必要传递依赖；未升级其他环境或改全局设置。pip check通过，安装清单见本地dependency_install.json；分享environment无绝对prefix。

| 检查 | 实际结果与统计口径 |
|---|---|
| V4新组件 | 最终43个不同Python方法通过：data_chain17、live12、ML6、search8；40方法整轮后新增人工MAT读取回归，再跑受影响15方法；最终加2个CLI加载门禁测试，受影响17方法通过。34/40/15/17轮次有重复，不累计冒充独立测试 |
| 直接影响的旧回归 | supervisor17、launcher14、short_runner9，共40个方法通过；实际自身短进程与纯/注入组件分开，不是MATLAB传播 |
| 发布原测试 | 13/15通过，两项浮点逐位/CSV字节失败保留；另外完整性/既定容差检查通过 |
| MATLAB短1 | 24点parity+8192复算，8.449393959秒，exit0/cleanup_verified=true |
| MATLAB短2 | 5次真实无传播初始化、7组断言，8.232997500秒，exit0/cleanup_verified=true |
| 扫描实际演示 | 1D取消/续扫/再次跳过、2D执行、4D/LHS/random/CSV只plan、入库/CSV/MAT/6图、旧MAT读取全部完成 |
| 软件保存/重载 | order11模型重载1024点预测精确一致；实际Prediction来源隔离写入通过 |

工程中修正过补充release checker的候选重建范围；NumPy2.4不再提供np.trapz，原 `getattr(np,'trapezoid',np.trapz)` 会立即求值失败fallback，已改为显式分支并加入人工复数MAT读取测试。后者在实际demo前发现，未改原波形数据或数值定义。最后补齐独立CLI的models_v4反序列化路径：surrogate执行必须传`--trusted-model`和`--selection`，先核验冻结/hash，再导入可信参考类，不能依赖预算脚本的PYTHONPATH偶然可用；两项门禁测试及5点实际CLI预测通过，未更改冻结学习或搜索源码。一次只读conda版本命令路径笔误退出127，未启动Python或改变环境，随后以正确路径核对。

所有项目Python命令均冠以：

```sh
/opt/homebrew/Caskroom/miniforge/base/bin/conda run -n mamyshev-ml --no-capture-output python
```

预算脚本只是给**已有** `run_isolated` 加本批分类账本和2线程环境，不另写监控器。完整实际子进程argv、UTC、墙钟、退出和日志在 [budget_ledger.json](../reports/local/accuracy_v4_001/budget_ledger.json) 及各任务runner/stdout；下列是前缀后的主要实际参数（输出根统一为本机绝对仓库路径）：

```text
scripts/run_v4_budget.py --timeout-s 330 ml selection_001 -- scripts/run_v4_ml.py select --out <repo>/reports/local/accuracy_v4_001/models --deadline-s 300
scripts/run_v4_budget.py --timeout-s 90 ml evaluation_001 -- scripts/run_v4_ml.py evaluate --model <repo>/reports/local/accuracy_v4_001/models/model.joblib --selection <repo>/reports/local/accuracy_v4_001/models/selection.json --out <repo>/reports/local/accuracy_v4_001/evaluation --authorize-final-evaluation
scripts/run_v4_budget.py --timeout-s 380 ml search_001 -- scripts/run_v4_search.py --wall-seconds 350
scripts/run_v4_budget.py --timeout-s 20 ml prediction_store_001 -- scripts/verify_v4_prediction_store.py
scripts/run_v4_budget.py --timeout-s 45 engineering data_chain_demo -- scripts/demo_v4_data_chain.py --out <repo>/reports/local/accuracy_v4_001/data_chain/demo_001
tests/run_matlab_short.py synthetic_parity_001 tests/matlab/run_v4_synthetic_parity.m --batch accuracy_v4_001 --matlab /Applications/MATLAB_R2025a.app/bin/matlab
tests/run_matlab_short.py live_components_001 tests/matlab/run_v4_live_components.m --batch accuracy_v4_001 --matlab /Applications/MATLAB_R2025a.app/bin/matlab
```

上述命令已经执行，不是要求审核人重新执行。发布/组件/回归/依赖/交付核查命令均在同一账本中，失败也计费。所有工作串行，ML/BLAS最多2线程；没有parpool/GPU、后台长任务或云端运行。

| 预算类别 | 实测外部子进程墙钟 | 限额 |
|---|---:|---:|
| MATLAB |16.682391459秒，2进程|180秒、最多2进程|
| ML训练/校准/预测/搜索 |22.009272834秒|900秒|
| 工程Python |39.765384377秒，含失败、重复回归和最终交付核查|300秒|
| 完整GMMNLSE |0次|0次|

ML外部成本细分：选择15.256709秒、校准/test/challenge/20000候选预测及绘图1.943221秒、独立搜索3.005807秒、Prediction入库0.963594秒、最终CLI五点预测0.839942秒。选择内部计时1.057268秒截止模型冻结，随后首次绘图库初始化及绘图包含在外部墙钟；不能用内部值代替整个任务成本。独立校准内部0.036734秒、test指标内部0.019248秒、challenge指标内部0.013215秒、最终评估函数内部0.961871秒；这些内部子范围不能与外部墙钟重复相加。搜索内部1.932803秒、GP拟合/预测0.434572秒。精确范围见各记录，Conda调用/工具审批等待未并入被监控子进程计时，未据它们宣称性能优化。

单次评价有3输出仍算1设计。监督研究实际预测9217行（8×1024验证+1024重载+1默认）；冻结评估23072行（cal1024+test1536+challenge512+候选20000），Prediction入库再1行、最终CLI再5行，总32295个三目标预测行。搜索另有144次GP候选池预测、580896个输入预测行及576个被推荐点的先验预测记录，均不增加oracle设计数。小扫描另14次合成逻辑调用、13唯一计算；与1536次独立搜索账目分开，组件fixture调用不冒充实验设计。发布8192标签和包内已有开发成本没有从账上消失，不能宣称“只花512标签”或“节省70%”。

峰值RSS为null：已有监控器未采样，未新增平台补测。所有图由本次保存标量/预测或真实历史MAT生成并检查；没有复制历史图当新结果、插值生成独立样本或构造复场。

## 交付与停止

新详细证据仅位于 `reports/local/accuracy_v4_001/`，两次MATLAB短测位于 `reports/local/phase2/accuracy_v4_001/`；继承ignore排除本机路径、原始数据和模型，不自动公开。原报告与所有历史证据保持；尤其 `observation_001/final_result.json` 仍缺失，当前清理修复不回溯改变它。

执行 `git diff --check`，并相对起点核对2281份旧文件哈希：无缺失、无意外改动，8份有意修改的已有文件与上文一致。生产数值源码、冻结权重/学习/搜索源码及分支/commit不变；新文件空白检查通过，delivery_review.passed=true。审计时本机V4主证据目录178文件、15,920,888 bytes（不含审计记录自身及随后runner最终写盘，也不含另列MATLAB短测目录），不包装成RSS或真实传播存储成本。本次交付完成的是V4修订MVP的指定层级，**不是旧深度物理Phase 2全部完成**。EXECUTION_STATUS/SCOPE记录物理验证deferred及本次功能/精度两个状态。

下一步仅建议审核挑战固定硬件切片的能量偏差及其适用范围，并在另行明确预算后决定是否用真实后端评价候选。本批没有据失败调参、另跑holdout、启动真实候选、独立物理收敛、继续下一Phase或GitHub发布。现在停止，等待审核。
