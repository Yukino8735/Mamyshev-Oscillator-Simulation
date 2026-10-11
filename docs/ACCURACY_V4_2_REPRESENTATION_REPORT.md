# V4.2 固定数据的样条表示与正则化对照

2026-09-28 UTC。**12格全部完成，8格通过开发门槛；唯一选中 `T2_K64_A0001`，一次新校准和测试完成，预声明点预测精度门槛通过。** 没有替换默认模型。区间联合经验覆盖总体94.53125%、切片邻域仅84.375%，不能把点预测通过解释成每组都有95%区间保证。

本批只执行 `CODEX_V4_2_REPRESENTATION_PROMPT.md` 的增量任务。MATLAB/GMMNLSE/真实扫描/BO均0次；新训练、新开发标签均0。物理深度验证继续deferred，旧Phase2仍为in_progress；`physical_state=undetermined`、`numerical_validation=not_verified`、`eligible_as_validated_training_truth=false`。

本地证据：[accuracy_v4_2_001](../reports/local/accuracy_v4_2_001/)。原V4/V4.1模型、失败、校准和报告不改；本批完成后停止等待审核。

## 1. 起点、身份和固定数据

分支仍为 `feature/mamyshev-ml-mvp`，HEAD `489bf4242f9b5266d47f8892840a24af66931ff0`。适用AGENTS、本批完整指令、SCOPE/EXECUTION_STATUS、V4.1报告、protocol/selection/summary、B1/B2训练IDs、模型及数据引用均已读取或通过实际载入核验。

`UPLOAD_REVIEW_CHECKS.json` 的三份输入哈希均与本机一致：旧报告 `2ebf02fa…`、selection `640ca71c…`、summary `8c79ef0c…`。这确认审核文件引用的是当前证据，不冒充独立重训复现。完整哈希在 [start_snapshot.json](../reports/local/accuracy_v4_2_001/start_snapshot.json) 和新protocol中。新目录原先不存在，独占创建，没有换ID或复用旧预算。

| 数据 | 本批实际读取范围 | 角色 |
|---|---:|---|
| T1 | 原B1的1024个ID，原order11顺序 | 原训练池前1024 |
| T2 | 原B2的1024个ID，原顺序 | 原前512＋V4.1定向512 |
| T1∪T2 | **1536**个canonical设计，两集交集512 | 不是2048个独立标签 |
| reference validation | 1024，core/expanded各512 | 已使用过的开发数据 |
| V4.1特殊组dev | 512，slice/near/faces/corners各128 | 已使用过的开发数据 |
| 旧V4 test/challenge | 本批不重新评分，不取来训练或选模型 | 保留历史结果 |

保存的V4.1 train/dev CSV逐点与SQLite及查询台账交叉核对：X、Y、source/backend/recipe/seed/units均一致；没有调用oracle重算。训练/开发间无canonical ID交集；T1/T2保持原行序，未合并训练。规范ID来自四个数值输入，避免别名误去重。旧B1/B2模型哈希与旧selection一致，两者不能缺失后偷偷重训。

旧V4.1 protocol仍按原字节保留。唯一必要既有源码变化是预算脚本增加V4.2批次选项，因此旧V4.1 protocol中的该脚本哈希与当前版本不同；新协议明确记录旧/新身份，没有声称全仓库哈希未变，也没有改旧清单解除锁。

## 2. 拟合前冻结的协议与实际表示

冻结时间 `2026-09-28T06:06:09.387400+00:00`，[protocol.json](../reports/local/accuracy_v4_2_001/protocol.json) SHA-256：
`fb624723207ee5f864976e70d971c3400fc2309313bf0467623237a59644f1cb`。
正常目录副本为 [accuracy_v4_2_protocol.json](../configs/accuracy_v4_2_protocol.json)。它在任何实际候选新拟合和新标签查询之前保存数据ID/哈希、12格矩阵、排序、门槛、并列规则、后置种子和预算。实验由V4.1结果引出，不声称从项目开始预注册。

每个T用6格：16/32/64个结点，各取Ridge alpha=0.1/0.001。标签 `A01` 表示0.1，`A0001` 表示0.001，实际参数已检查。两格16/0.1复用旧B1/B2；其余10格新拟合，三个目标共用每格的配置。

直接调用原 `LogSurrogate(parameters=...)`，没有修改 `reference/models_v4.py` 或 `v4_ml.py`：四输入声明域缩放、正目标log拟合、degree3样条、uniform结点、constant样条外推、include_bias=False、degree4 Polynomial并集、StandardScaler及原Ridge设置不变。实际拟合solver为cholesky（原solver='auto'的解析结果），没有强制改求解器。结点来自各自训练X，不读oracle内部曲线或人工添加P4/L4特殊结点。

实际每目标特征数确为 **137/201/329**。每格的三目标实际extended knots、训练范围、scaler均值/方差/scale、矩阵哈希、求解器设置保存在 `development/<slot>/inspection.json`；[六组alpha配对核查](../reports/local/accuracy_v4_2_001/development/feature_pairs.json)全部通过。同T、同结点下，alpha变化不改变特征及缩放矩阵。

训练X端点不同：T1的P=[2.003336,9.990153]、offset=[2.014525,15.991760]、BW=[0.514662,7.972302]；T2到达声明域P=[2,10]、offset=[2,16]、BW=[0.5,8]端点。两者长度均[1,8]。跨T比较同时包含人群和拟合结点端点差异，不能全部归因于单一因素。

容差沿用 E=max(2nJ,3%|y|)、τ=max(1fs,3%|y|)、peak=max(0.05MW,5%|y|)。先检查有限，再按r≤1计整数。reference总体每目标≥95%、联合≥90%；core/expanded各目标≥90%；四特殊组各目标≥95%、联合≥90%。使用整数交叉乘判门槛，Wilson只报告、不替换判据。

所有格终止后才正式选择。对通过者，按core、expanded、slice、near、faces、corners六组等权的各目标容差归一化RMSE均值最小选择；reference总体不重复加权。距最小分数≤1e−12时按结点少、alpha大、T1优先。实际没有并列。没通过则不得打开holdout；该拒绝分支做了组件测试。

## 3. 完整12格训练与开发结果

下表“E/τ/P/联合”都是**通过整数/同列n=1024**，训练分数仅为拟合诊断。两格“复用”fit_count=0。实际12格数值有效，警告0、数值失败0、未执行格0。

| 训练集/配置 | 特征数 | 训练 E/τ/P/联合 | reference E/τ/P/联合 | 六组分数 | 全部门槛 |
|---|---:|---|---|---:|---|
| T1 K16 A01（复用B1） |137|1005/1015/1024/996|994/1010/1024/981|0.427775713|失败|
| T1 K16 A0001 |137|1004/1015/1024/995|994/1011/1024/983|0.423725288|失败|
| T1 K32 A01 |201|1024/1024/1024/1024|1024/1024/1024/1024|0.185868416|通过|
| T1 K32 A0001 |201|1024/1024/1024/1024|1024/1024/1024/1024|0.161257809|通过|
| T1 K64 A01 |329|1024/1024/1024/1024|1024/1024/1024/1024|0.137121852|通过|
| T1 K64 A0001 |329|1024/1024/1024/1024|1024/1024/1024/1024|0.085116663|通过|
| T2 K16 A01（复用B2） |137|985/1015/1024/976|971/1014/1024/961|0.325850886|失败|
| T2 K16 A0001 |137|983/1015/1024/974|971/1014/1024/961|0.324086461|失败|
| T2 K32 A01 |201|1024/1024/1024/1024|1024/1024/1024/1024|0.106079541|通过|
| T2 K32 A0001 |201|1024/1024/1024/1024|1024/1024/1024/1024|0.090861303|通过|
| T2 K64 A01 |329|1024/1024/1024/1024|1024/1024/1024/1024|0.059833867|通过|
| **T2 K64 A0001** |329|1024/1024/1024/1024|1024/1024/1024/1024|**0.031183740**|**选中**|

关键能量误差，每个特殊组n=128；bias定义prediction−truth，单位nJ；尾差为绝对相对误差P95。

| 配置 | slice/near/faces/corners 能量通过数 | 训练E RMSE | reference E RMSE | slice bias / P95 | near bias / P95 |
|---|---|---:|---:|---|---|
| T1 K16 A01 |4/106/124/127|2.240091|2.445512|+4.929266 / 4.686190%|−0.494037 / 3.572902%|
| T1 K16 A0001 |6/106/125/127|2.238172|2.454660|+4.910243 / 4.595178%|−0.508407 / 3.525582%|
| T1 K32 A01 |128/128/127/128|0.663484|0.757592|+1.312258 / 1.359189%|+0.014346 / 0.946074%|
| T1 K32 A0001 |128/128/128/128|0.647691|0.745636|+1.266135 / 1.338312%|−0.017941 / 0.889323%|
| T1 K64 A01 |128/128/128/128|0.225748|0.348554|+0.695502 / 0.695587%|−0.040846 / 0.360254%|
| T1 K64 A0001 |128/128/128/128|0.172279|0.224890|+0.683506 / 0.608062%|−0.060483 / 0.326184%|
| T2 K16 A01 |128/105/122/128|2.637393|3.089760|+1.875794 / 2.314029%|−2.122903 / 3.752453%|
| T2 K16 A0001 |128/105/122/128|2.637081|3.092249|+1.876467 / 2.350306%|−2.127069 / 3.753498%|
| T2 K32 A01 |128/128/128/128|0.629905|0.783073|+0.336330 / 0.544032%|−0.355706 / 0.984366%|
| T2 K32 A0001 |128/128/128/128|0.618696|0.767859|+0.328721 / 0.536699%|−0.365503 / 1.014369%|
| T2 K64 A01 |128/128/128/128|0.203237|0.341471|+0.062646 / 0.215838%|−0.122924 / 0.501557%|
| T2 K64 A0001 |128/128/128/128|0.167962|0.264009|+0.066847 / 0.166351%|−0.123763 / 0.457192%|

每格各目标、各开发组以及有样本的训练分组完整bias/MAE/RMSE/R²/P50/P90/P95/max、整数率和Wilson在[comparison.json](../reports/local/accuracy_v4_2_001/development/comparison.json)、[all_metrics.csv](../reports/local/accuracy_v4_2_001/analysis/all_metrics.csv)及slot结果中。缺训练组n=0明确null/empty_group，没有生成额外样本补表。[对照图](../reports/local/accuracy_v4_2_001/analysis/energy_pass_comparison.png)与[受控差异记录](../reports/local/accuracy_v4_2_001/analysis/controlled_effects.json)只使用已存数据。

原B1/B2加载后，对原保存的reference1024与dev512逐行核对，最大预测差均为 **0**，固定atol=rtol=1e−10。全部格保存/重载后reference/dev也逐元素相同。没有重复旧2048点test/challenge链路诊断。

## 4. 对假设的回答

1. **在固定T、固定alpha下，16→32→64明显降低训练和六组开发误差。** 四个16结点格仍失败，八个32/64格通过。例：T1、alpha=.1训练能量RMSE 2.240091→0.663484→0.225748nJ，邻域开发RMSE 3.131575→0.716854→0.296244nJ。
2. **仅减小16结点的alpha没有解决问题。** T1切片4→6/128，邻域仍106/128；T2邻域仍105/128、reference能量仍971/1024。32/64结点下减小alpha进一步降低六组综合分数，属于在相同特征/缩放下的正则化对照。
3. **局部改善并非单调。** T1、16结点减小alpha时训练RMSE略降，但reference 2.445512→2.454660nJ、邻域3.131575→3.132352nJ略差。T1、alpha=.1的32→64，faces能量RMSE 1.737104→1.891597nJ、corners 0.519269→0.520921nJ。存在局部不利泛化迹象，不能因综合变好而隐去；也不足以给整个64结点模型贴过拟合标签。
4. **覆盖仍有取舍。** 同64/.001时，T2比T1切片RMSE更低（0.112026对0.693640nJ）、faces更低（0.186741对1.219877nJ）；但reference较高（0.264009对0.224890nJ）、near较高（0.317670对0.237693nJ）。不同T的训练人群与结点端点一起变化，不能拿不同人群训练误差作唯一归因。

本轮支持“旧16结点表示限制是重要影响因素，单纯alpha .1→.001不足以修好失败”。这不是证明唯一根因、整个连续域可靠，或其他种子/数据量下也必然同样。未追加degree/quantile结点/神经网络/默认点补偿等试验。

## 5. 唯一选择、隔离及一次条件评价

[selection.json](../reports/local/accuracy_v4_2_001/selection.json)在新cal/test取标前冻结唯一 `T2_K64_A0001`，权重SHA-256：
`c236c2d2dd6cb5b59e32bd5ab4f8c3823f7fefc10d7571108a3d6339ee46b2e0`。
未把dev/cal加入重训，也未挑第二名重看test。

确认V4.1对应holdout目录、final评价锁均缺失，查询台账只有train/dev。复用原采样算法和固定种子cal41033、test41044，继承29,613个canonical排除身份；368条缺X的历史项仍按已知canonical ID排除。只引用原清单哈希，不复制旧67MB映射。每次取标前还核对本仓库其他已记录query ledger/SQLite的X/ID，没有发现计划样本已被评价。该隔离保证限于本仓库可用记录；外部/未记录查询无法确认，不声称全世界从未见过这些点。

新calibration1024：core/expanded各256、四特殊组各128；新test2048：core/expanded各512、四特殊组各256。两集合互不重复、与继承排除表不重复。X重抽25/58次是几何/重复排除，不算标签；没有先看Y选样。3072个唯一新设计全部经冻结SyntheticEvaluator成功评价，cache hit=0，训练/dev新查询=0，数据入独立Evaluation表而非Prediction表。[继承引用](../reports/local/accuracy_v4_2_001/inherited_exclusions.json)、[采样摘要](../reports/local/accuracy_v4_2_001/holdout_sampling_summary.json)、各角色isolation_check/inputs/rejections/accounting及数据库均保留。

实际校准m=1024、alpha=.05、秩974，joint max absolute log-residual得到 **q=0.003266551289750619**；只设置新区间，不用旧V4 q，不改变点预测。

### 点预测门槛

test总体2048点的E、τ、peak和联合均 **2048/2048**；独立核对reference子集1024点、core/expanded各512和四特殊组各256，三目标与联合也分别全数通过。完整[final_metrics.json](../reports/local/accuracy_v4_2_001/evaluation/final_metrics.json)、[原单位逐点CSV](../reports/local/accuracy_v4_2_001/evaluation/test_predictions.csv)、[分组CSV](../reports/local/accuracy_v4_2_001/analysis/test_groups.csv)和[同次散点图](../reports/local/accuracy_v4_2_001/analysis/selected_test_scatter.png)不合并旧test。

| 全体test目标 | bias | MAE | RMSE | R² | 绝对相对误差P50/P90/P95 | 最大绝对误差 |
|---|---:|---:|---:|---:|---|---:|
| E nJ |−0.0132003|0.1594724|0.2396563|0.999994069|0.066903% / 0.209180% / 0.282357%|1.2569982|
| τ fs |+0.0001691|0.0335371|0.0493923|0.999995606|0.056928% / 0.174635% / 0.227693%|0.6157347|
| peak MW |−0.0004142|0.0032583|0.0053170|0.999995188|0.070136% / 0.210132% / 0.265623%|0.0365796|

2048/2048通过率的Wilson95区间为[99.8128%,100%]；各n=512、256组对应[99.2553%,100%]、[98.5216%,100%]。验收依据整数样本率，不用R²或Wilson下界替代。

### 区间与筛选限制

评价分布固定为core25%、expanded25%、四特殊组各12.5%。联合区间经验覆盖不是点预测容差率：

| 组 | n | 联合覆盖率 | Wilson95区间 | E / τ / peak覆盖率 |
|---|---:|---:|---|---|
| 全体 |2048|94.53125%|[93.46055%,95.43521%]|96.82617% / 98.63281% / 97.31445%|
| core |512|91.21094%|[88.44150%,93.36658%]|95.89844% / 97.65625% / 95.50781%|
| expanded |512|96.09375%|[94.04369%,97.45729%]|97.65625% / 99.21875% / 97.07031%|
| slice |256|99.60938%|[97.82090%,99.93101%]|100% / 100% / 99.60938%|
| **near_slice** |256|**84.37500%**|**[79.42285%,88.31076%]**|87.89063% / 95.70313% / 95.31250%|
| faces |256|97.65625%|[94.98190%,98.92151%]|99.60938% / 99.60938% / 98.43750%|
| corners |256|100%|[98.52161%,100%]|100% / 100% / 100%|

原单位区间宽度（median / P95）：

| 组 | E nJ | τ fs | peak MW |
|---|---|---|---|
| 全体 |0.946589 / 2.336694|0.248246 / 0.619209|0.017020 / 0.053072|
| core |1.322470 / 2.251262|0.217896 / 0.327474|0.025576 / 0.053165|
| expanded |1.413271 / 2.599542|0.233101 / 0.424491|0.025304 / 0.063258|
| slice |0.868334 / 0.993699|0.227141 / 0.308175|0.015927 / 0.023114|
| near |0.886211 / 1.235464|0.239153 / 0.342665|0.015852 / 0.026440|
| faces |0.855708 / 2.467922|0.301467 / 0.609179|0.012916 / 0.042253|
| corners |0.270159 / 2.020171|0.525204 / 1.019851|0.001998 / 0.018159|

各目标覆盖的Wilson也完整保存。分层定额数据不自动满足任意条件交换性，**near区间明显不足95%，没有扩大区间掩盖问题**。理论conformal保证只有相应统计前提成立时适用；本次只报告固定分布的经验覆盖。

| 约束/筛选 | 实际可行 | 选中 | 真可行 / 假可行 | precision / recall | 区间跨阈值点 / 其中未选中 |
|---|---:|---:|---|---|---|
| τ≤40，点估计 |1167|1167|1166 / **1**|99.91431% / 99.91431%|18 / 10|
| τ≤40，区间上界≤40 |1167|1159|1159 / 0|100% / 99.31448%|18 / 18|
| E≥100，点估计 |1564|1564|1564 / 0|100% / 100%|6 / 0|
| E≥100，区间下界≥100 |1564|1558|1558 / 0|100% / 99.61637%|6 / 6|

末列保留机器字段 `uncertain_abstentions` 的原计算口径：区间跨阈值且未被该规则选中的交集。点预测规则本身不使用区间、不主动弃权，因此其中10/0不能解读为因区间不确定而拒绝。保守规则则确实要求整个区间满足约束。

唯一τ点估计假可行出现在expanded。各组的可行数、误判、上述交集计数、precision/recall及Wilson详见final_metrics的group_constraints；没有为阈值附近补样或重抽。这里的“保守”是区间筛选规则名称，不代表每个未来点一定可行。代理推荐后仍需对应Evaluator确认，不能写成物理真值。

## 6. 可加载候选与工程验证

独立候选：[release/model.joblib](../reports/local/accuracy_v4_2_001/release/model.joblib)及[release/selection.json](../reports/local/accuracy_v4_2_001/release/selection.json)。后者绑定模型、1024训练IDs、数据、协议、源码、summary和final_metrics哈希。加载先核验再反序列化，检查class来源、四输入顺序/单位和表示参数。实际加载后对同次已评分的首个保存测试点做一致性核对，固定atol/rtol=1e−10通过；没有新oracle或重新选模。

显式审核预测入口：`scripts/run_v42.py predict --model <release/model.joblib> --selection <release/selection.json> --design-json <四输入JSON>`，同样用既有Conda Python。该命令不是额外真实仿真许可。本批实际执行的是同一loader/evaluator的重载核查；未另外运行一批预测扫描。新Prediction只附本模型的合成实测范围与限制，不继承旧V4 P4/L4失败标签，也不保证所有域内点。`deployment_replaced=false`，旧默认CLI/模型原样保留。

新增正常源码：`v42_data.py`、`v42_models.py`、`v42_experiment.py`、`v42_release.py`；新增脚本 `start_v42.py`、`run_v42.py`、`summarize_v42.py`、`audit_v42.py`；4份 `test_v42_*.py`，以及新协议。唯一既有Python源码改动：

```diff
- choices=['accuracy_v4_001', 'accuracy_v4_1_001']
+ choices=['accuracy_v4_001', 'accuracy_v4_1_001', 'accuracy_v4_2_001']
```

预算默认、累计扣费、串行锁、STOP、拒绝覆盖和所属进程监控全部复用。数据角色/指标/采样/数据库沿用原模块，新代码没有复制物理引擎或建立另一套监控器。

**30项新组件方法＋10项相关旧Python回归通过，失败0。** 新测试包含6个8行人工拟合fixture以核对137/201/329维数和alpha变换一致性；它们不使用T1/T2、不是新设计标签，单独于10个实际新候选计数。测试覆盖数据/哈希篡改拒绝、参数生效且无oracle查询、整数门槛/并列/partial和无通过停止、holdout门控、可信重载、单位及Prediction不能进入Evaluation。未重跑整套历史测试、MATLAB初始化、传播或旧波形分析。

## 7. 成本、命令、保全和停止

本批实际新增训练标签0、开发标签0、校准1024、测试2048，**合成评价总计3072个唯一设计**。当前候选只训练1024点；两个训练集并集1536、已用开发1536、新评价3072分开计费，本批这些角色合计6144个唯一有标签设计，且项目之前还有V4测试/搜索等历史成本。不能声称整个研究只花1024次评价，更没有真实求解器节省率。

ML外部墙钟：完整比较 **2.794393s**、条件评价 **5.160192s**、已存结果分析/绘图 **11.760995s**，累计 **19.715580/900s**。10个实际新候选纯fit计时合计0.150966s，12格首次train/reference/dev预测合计0.222710s；这些内部子计时不包含全部加载/检查/重载/写盘，不能替代外部预算。工程外部墙钟累计 **9.073630/300s**，其中末项保全检查2.040109s，详见[budget_ledger.json](../reports/local/accuracy_v4_2_001/budget_ledger.json)；全程串行、最多2CPU线程，无GPU/云资源。没有失败重试或隐藏加时。没有实测峰值RSS；启动前数百MB是估计，不当作测量值。保全检查时本批文件合计22,905,677字节（不含随后写出的保全摘要与命令清单），没有复制旧67MB映射。

所有Python都用 `/opt/homebrew/Caskroom/miniforge/base/bin/conda run -n mamyshev-ml --no-capture-output python ...`。实际主步骤及对应本地runner/stdout：

```text
scripts/start_v42.py
scripts/run_v4_budget.py --batch accuracy_v4_2_001 --timeout-s 120 engineering targeted_tests_001 -- -m unittest discover -s <repo>/tests -p test_v42_*.py -v
scripts/run_v4_budget.py --batch accuracy_v4_2_001 --timeout-s 60 engineering protocol_freeze -- scripts/run_v42.py freeze
scripts/run_v4_budget.py --batch accuracy_v4_2_001 --timeout-s 450 ml comparison_001 -- scripts/run_v42.py compare
scripts/run_v4_budget.py --batch accuracy_v4_2_001 --timeout-s 350 ml final_evaluation_001 -- scripts/run_v42.py evaluate
scripts/run_v4_budget.py --batch accuracy_v4_2_001 --timeout-s 90 ml saved_result_analysis_001 -- scripts/summarize_v42.py
```

`<repo>`在实际执行时是已记录的绝对项目路径。既有4项Prediction回归、6项角色/指标回归和末项保全命令也在台账及commands.json。模型比较STOP为 `reports/local/accuracy_v4_2_001/budget/ml/comparison_001/STOP`，条件评价对应 `final_evaluation_001/STOP`；没有使用取消/超时。全部结果已结束，不需要恢复进程。

开始保存2612个既有文件哈希，末项[保全检查](../reports/local/accuracy_v4_2_001/preservation_check.json)**通过**：2609个未变，仅预算脚本及SCOPE/EXECUTION_STATUS三份按授权变化，缺失0、意外变化0；1381份历史证据全部未变，`code/`生产源码全部未变，分支与HEAD未变。SCOPE/EXECUTION_STATUS只追加本批结果。数据库确认cal/test分别1024/2048条Evaluation、Prediction均0，release身份再次核验通过。`git diff --check`通过。没有改环境、全局shell/权限、分支、commit/push/PR；MATLAB生成/扫描/逐点保存/取消续扫、CSV/MAT导出、DB/recorded/真实GMMNLSE路由保持原样，真实执行许可仍需后续明确授权。

本批已完成限定交付，独立候选等待审核。下一步最值得审查的是邻域区间覆盖不足及用途边界；这里只提出，不校准第二套区间、不增样、不重训、不再看第二模型的同一test、不执行真实候选或进入下一Phase。

技术定义参照官方 [SplineTransformer](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.SplineTransformer.html) 与 [Ridge](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.Ridge.html) 文档；本报告的维数、求解器、误差和成本均来自实际本地源码/记录，文档不是本项目运行证据。
