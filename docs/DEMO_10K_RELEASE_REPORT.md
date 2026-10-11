# Demo、10k 合成模型与 Git 发布预审报告

2026-09-28 UTC。本批依据 `CODEX_DEMO_10K_AND_GIT_REVIEW_PROMPT.md`，在现有
`feature/mamyshev-ml-mvp` 工作区执行；起点 commit 为
`489bf4242f9b5266d47f8892840a24af66931ff0`。原有未提交工作是本批起点，不能把
相对该 commit 的全部差异归为本批修改。新原始证据统一存于
`reports/local/demo_10k_release_001/`，本文此类路径均标作 **local-only**，不是
公开下载入口。历史 V4/V4.1/V4.2/V4.3、closeout 和失败/timeout 证据保留。

本批完成一次确实使用 **10,000 个不同合成设计**的三目标拟合；开发通过后，
才对新 calibration/test 取标和评分。14,096 个新标签全部属于
`repository_guided_synthetic`，**原 GMMNLSE/完整腔体传播与真实扫描为0次**。
新增独立推理资产和10,000行待执行计划，旧1024模型及默认选择未替换。
整个历史 Phase2 深度物理验证仍为 `in_progress/deferred`，不因本批合成指标完成。

实现、固定训练、限定点评分、独立副本AppTest、MATLAB计划及无传播检查已完成。
浏览器视觉检查未完成；浏览器控制工具异常等待超出工程墙钟预算，详见第7节。
发布仍受已跟踪数据、许可与敏感路径审查阻塞，不将本批标作无条件全部验收。

## 1. 实际改动、环境与历史资产保留

| 文件或必要文件组 | 本批用途 |
|---|---|
| `configs/demo10k_protocol.json` | 固定四角色配额、种子、模型、门槛、一次拟合和预算 |
| `src/mamyshev_ml/demo10k_experiment.py`、`scripts/run_demo10k.py` | 复用原采样几何、Evaluation、模型和指标的一次训练/校准/评价 |
| `src/mamyshev_ml/demo_inference.py`、`scripts/build_demo_assets.py` | 数据无关的受信清单加载、先验hash检查、纯预测和最小资产构建 |
| `demo/` | 四视图界面、业务逻辑、纯预测入口、依赖及经过清单约束的资产 |
| `src/mamyshev_ml/demo10k_plan.py`、本批计划/recorded/MATLAB短测 scripts 与 tests | 通用N输入校验、10000行待执行计划、分块/续扫读回及无传播检查 |
| 本批 start/budget/check/build/review scripts | 复用现有监控；保存身份、预算、独立副本和Git只读审查 |
| README、指南、`docs/assets/`、本报告及 MATLAB 功能矩阵 | 可提交入口、聚合指标/图与来源说明 |
| `.gitignore` | 增量排除数据/完整计划/日志/输出，不全局忽略引擎所需MAT/TXT |

原 `models_v4.py`、生产传播算法、四维物理规则和旧release未改成新模型。
旧权重SHA为 `c236c2d2dd6cb5b59e32bd5ab4f8c3823f7fefc10d7571108a3d6339ee46b2e0`；
旧 calibration SHA为 `5163e9f635cddd2432cb5e737439c0c9b9118d604c127907f65d5229eed5116a`，
旧q为0.003266551289750619。原类SHA为
`46f9779b878d195b601930446cce3ec5335f694ef219f28c2ae728a353590b11`。
独立资产构建先复用旧release严格核查，未通过关闭旧缺文件检查来打包。

依本批明确授权，只在既有 `mamyshev-ml` 增加 Streamlit 1.64.0 及必要传递依赖。
安装前后 NumPy2.4.6、SciPy1.17.1、scikit-learn1.9.1、Matplotlib3.11.2、
joblib1.6.0、threadpoolctl3.7.0 均保持不变，Python3.11.16/arm64。
证据：`ui_dependency/result.json`；完整解析/安装记录仅本地。
未创建环境、改base、全局shell/PATH或权限。

`preservation_check.json` 对起点2967个已有文件核对：2961个字节未变；仅6个
已授权说明/忽略文件改变：README、.gitignore、SCOPE、EXECUTION_STATUS、
USER_GUIDE_ZH、CLAIM_EVIDENCE。异常修改0；生产物理源码、原合成配方/类、旧
模型/q、旧compact包和历史证据均保留。起点文件已有的未提交差异没有被归零。
分支、HEAD、staged diff均保持；staged路径0。`git diff --check` 退出0，无输出。
另记录61个新非local文件的大小和hash，完整路径见该记录。
Git清单及保留核查是收尾时点快照；本文随后仅补写检查结果，最终文档hash另存
`final_document_hashes.txt`，不把快照里的旧文档hash冒充最终字节。

## 2. 真正进入拟合的10k设计与固定协议

四输入保持 P[2,10]W、offset[2,16]nm、BW[0.5,8]nm、L[1,8]m，L严格0.1m格点。
冻结的V3配方、三目标定义和V4.1采样几何未变；不读取配方系数作为特征。

| 角色 | 新标签/唯一设计 | core / expanded | slice / near / faces / corners | 固定种子 |
|---|---:|---:|---:|---:|
| train | 10000 | 各2500 | 各1250 | 61001 |
| development | 1024 | 各256 | 各128 | 61002 |
| calibration | 1024 | 各256 | 各128 | 61003 |
| final_test | 2048 | 各512 | 各256 | 61004 |

`sampling.json` 记录：四角色共14,096个不同输入，在首个新标签前全部冻结；
角色间互斥，对已捕获的32,685个旧canonical排除ID交叉为0。排除读取旧X/ID，
包括本地可见旧Evaluation/查询记录、角色输入和20k候选池，不使用旧Y选新点。
本地以外或未持久化的查询无法确认，未假称全世界输入隔离。

`oracle_queries.jsonl` 与各角色accounting记录14,096次预留、14,096次完成；
没有删失败/难点凑数。source为 `repository_guided_synthetic`，backend为
`mamyshev_repository_guided_synthetic_v3`；采样分组不是物理标签或额外输入。

仅一次正式 `LogSurrogate.fit`，内部三个目标回归器合计仍为一次三目标训练。
64 uniform knots、degree3样条、degree4多项式、原域缩放、StandardScaler、
Ridge alpha0.001、log正目标保持固定。`fit_record.json` 的 `n_unique_fit=10000`，
`fit_inspection.json` 中三个scaler均 `n_samples_seen=10000`，各329个实际特征；
结点/scaler只拟合新train X。model random_state=11、确定性配方seed=0，
不据此宣称多seed鲁棒性。

开发门槛使用原整数判定：参考core+expanded总体各目标≥95%、联合≥90%；
core/expanded分别各目标≥90%；四特殊组各目标≥95%、联合≥90%。全部通过后
冻结权重，才取1024个新calibration标签并生成本模型q，随后唯一一次新test评分。
没有再次拟合、补样、调参或重评分旧V4.2 test。

## 3. 新模型自己的实际精度与区间限制

来源：本地 `final_metrics.json`；可审阅聚合副本为
`demo/assets/models/demo_10k_v1/metrics.json`。以下绝对指标均用原单位。

| 目标 | MAE | RMSE | R² | 绝对误差P95 | 最大绝对误差 |
|---|---:|---:|---:|---:|---:|
| 能量 nJ | 0.1191669481 | 0.1913725151 | 0.9999961384 | 0.4382451048 | 1.2927230298 |
| 脉宽 fs | 0.0233741876 | 0.0412812602 | 0.9999968772 | 0.0851586793 | 0.4375467668 |
| 峰值 MW | 0.0024745678 | 0.0045286562 | 0.9999964786 | 0.0098284067 | 0.0551481567 |

固定容差是 `abs(pred-truth) <= max(abs_tol, rel_tol*abs(truth))`：
能量2nJ/3%，脉宽1fs/3%，峰值0.05MW/5%。新test各目标和联合均2048/2048
在容差内，联合Wilson区间 `[0.9981277993949387,1]`；这不是“100%准确”、
GMMNLSE精度或未来保证。原相对P95为0.0025004701、0.0021210802、
0.0024010253，均为比例而不是百分数字。

train/development各目标及联合分别10000/10000、1024/1024。其三目标MAE：
train为0.1135091596nJ /0.0233080702fs /0.0023660641MW；
development为0.1192472376nJ /0.0242072061fs /0.0023712314MW。
原单位P50/P90/P95/R²和逐组记录保留于 `train_metrics.json`、
`development_metrics.json`，完整逐点评分仅本地。

| 新test采样组 | n | 能量MAE nJ | 脉宽MAE fs | 峰值MAE MW | 联合容差通过 | 联合区间覆盖 |
|---|---:|---:|---:|---:|---:|---:|
| core | 512 | 0.1954694551 | 0.0269808541 | 0.0045904473 | 512/512 | 468/512 |
| expanded | 512 | 0.1113096457 | 0.0194853366 | 0.0026584320 | 512/512 | 494/512 |
| slice | 256 | 0.0759509933 | 0.0143150962 | 0.0009074118 | 256/256 | 256/256 |
| near_slice | 256 | 0.1876430268 | 0.0509433673 | 0.0028084194 | 256/256 | 218/256 |
| outer_faces | 256 | 0.0712129529 | 0.0229471972 | 0.0015164095 | 256/256 | 250/256 |
| corners | 256 | 0.0049704105 | 0.0058554589 | 0.0000665426 | 256/256 | 256/256 |

新q=`0.0030957846673075884`，calibration n1024、alpha0.05、rank974，
joint max absolute log residual。总体联合覆盖1942/2048=94.82421875%，
Wilson区间 `[0.937780624715102,0.9570253516955948]`；core91.40625%、
near_slice85.15625%。区间因此保持 **limited**，不提供逐点/条件组/优化候选
或真实激光安全保证。旧q没有用于新权重。

全区间宽度的median/P95分别为：能量0.9020283434/2.1613889369nJ，
脉宽0.2347315854/0.5665012515fs，峰值0.0159018663/0.0495864714MW。
固定test的tau≤40fs有1158个实际可行，点预测选1157且误可行0；区间筛选选1152，
误可行0、uncertain14。E≥100nJ有1549个实际可行，点预测选1549且误可行0；
区间筛选选1546，误可行0、uncertain5。全部分组约束计数保存在原JSON。

新10k与旧1024成绩来自不同新旧测试集，不能作为同一独立测试上的样本量消融，
也不证明增加数据必然改善。旧V4.3候选改善和旧冷启动搜索属于原版本，本批没有
新BO/随机对照或候选确认标签。`physical_state=undetermined`、
`numerical_validation=not_verified`、`eligible_as_validated_training_truth=false`。

## 4. 纯推理资产、依赖和可复现范围

新本地权重 `reports/local/demo_10k_release_001/release/model.joblib` 的SHA为
`9885e8f258fa10de0a69844b70fa72242fcc64267d9db1e6c07dd4bd4609b6d0`。
冻结身份在同目录 `frozen_model.json`，新q在 `calibration.json`。
独立推理副本为 `demo/assets/models/demo_10k_v1/`，manifest为
`demo/assets/models/demo_10k_v1/manifest.json`；旧版另存于 `demo/assets/models/v42/`。
`catalog.json` 的默认仍为 `v42_T2_K64_A0001`，用户可以明确选择已通过限定
点预测验收的 `demo_10k_v1`。

两个版本的运行资产合计675,413字节：权重、原类、域、各自q、聚合metrics/card、
依赖、独立manifest与catalog，不包含训练/测试行、完整ID列表、DB、CSV或旧ZIP。
构建时检查已核对的可信对象状态及其可达NumPy数组，没有保存原始训练X/Y。
加载先核对catalog固定目录、manifest与实际权重/自定义类字节，再反序列化；
不接受上传任意模型或源码。Hash检查不是对未知pickle的沙箱/安全认证。

同模型三个已存新development输入经过direct/joblib single/batch/CSV/JSON读回，
最大绝对差均0，使用预先固定atol=rtol=1e-10；没有新增标签或拟合。
`demo_inference.py` 运行态不导入训练、Evaluation或扫描模块，不调用oracle/MATLAB
回退。独立副本的实际UI/CLI检查单列下一节，不与该模型读回混为同一项测试。

公开小型 `configs/demo10k_protocol.json` 包含配额、几何版本、种子和规则；
本地protocol另冻结源码、依赖、配方、旧ID排除身份。支持“按同配方再生成”，
不声称仅凭公开资产就逐点重建此次发布：完整历史排除ID表保留本地，公开仅hash。
当前验证使用既有环境，未验证全新环境或其他平台。模型/配方/类/图的可分发权
仍需审查；内部功能副本不等同获准公开发布。

## 5. 交互Demo与独立展示副本

入口 `demo/app.py`，业务层 `demo/ui_logic.py`，纯CLI `demo/predict.py`。
四个视图分别处理单点Prediction、最多21点/21×21点的批量预测扫描、最多4096个
X-only候选的预测排名与原版本历史成果、MATLAB管道及零额度待审批计划。
三目标均标明单位/model_id/n_train/source/interval状态；Prediction不是Evaluation，
模型标量也不是传播复场。历史真实波形只能展示源MAT已有结果，不跟滑块合成波形。
界面没有启动真实传播的按钮/API，受控真实CLI链仍保留。

从仓库根目录启动，默认仅本机访问、应用使用统计关闭：

```sh
/opt/homebrew/Caskroom/miniforge/base/bin/conda run -n mamyshev-ml --no-capture-output python -m streamlit run demo/app.py --server.address 127.0.0.1 --server.port 8501 --server.headless true --browser.gatherUsageStats false
```

使用前需要准备上述经过核对的本地模型资产，不通过重训启动Demo。停止自己启动的
服务使用前台终端Ctrl-C；本批测试服务的实际关闭情况必须以末项检查为准。

实际结果：首次 `ui_check/` 在图表断言失败，外部耗时6.088214s；原因是检查器
使用旧 `arrow_vega_lite_chart`，Streamlit1.64实际enqueue为 `vega_lite_chart`。
仅修检查器并断言真实protobuf spec/Arrow数据，不改应用或放宽数值容差。
原失败stdout/stderr/process保留。`ui_check_002/` 成功，外部8.741436s，内部7.980305s。

11个AppTest交互情形：两模型各完成真实单点提交、变更/非法输入、1D/2D图及导出、
四场景X-only候选/历史/待审批导出、无live按钮管道页；另测缺模型无回退。
同一进程另执行3个业务测试方法。两模型UI与同模型CLI最大绝对差均0，固定
atol=rtol=1e-10。运行期拦截计数fit/oracle/Evaluation/MATLAB均0；18次预测方法
调用不等于18个独立研究设计。证据为 `ui_check_002/app_test_result.json`。

独立allowlist功能副本实际位于
`/private/var/folders/v4/k3141v0s2zx7j_jfk_py92qh0000gn/T/mamyshev_demo_review_m6borm21/preview`。
精确文件清单与hash在 `ui_check_002/independent_copy.json` 和副本 `preview_manifest.json`；
仅含必要源码/模型/聚合配置/精选图，无data、reports/local、CSV或实验DB。
清除PYTHONPATH，以 `-I -B` 从副本启动，两模型原类均来自副本；退出0。
副本含许可待审资产，`public_release_blocked=true`，不是公开发布包。
临时副本可能被系统清理；仓库内Demo及受信资产为持久入口。

短服务器从该副本以127.0.0.1随机端口启动，health实测正常；预算120s含5s清理。
`cua_repl getApp(Safari)` 调用报告等待2717.7581s，返回时服务器已按窗口自动关闭，
未导航到Demo页面。故 `browser_visual_check=not_run`，首页/扫描/方案截图均缺失，
没有用AppTest或历史图冒充真实截图。服务外部115.579722s，子进程退出0、
自身清理0.344890s、child_stopped=true；最终端口核对在preservation记录。
原 `browser_preview/server_record.json` 未改，后续独立说明在 `visual_check.json`。
没有重启第二个预览服务，未操作用户其他浏览器页面或MATLAB进程。

## 6. MATLAB完整管道与10k待执行计划

详见 [DEMO_10K_MATLAB_MATRIX.md](DEMO_10K_MATLAB_MATRIX.md)：逐项列实现位置、
当前测试、历史证据、未验证范围及阻塞；这里保留本批关键实测。

调用链已直接查源码：计划/四输入/ID → `GMMNLSEEvaluator` →
`execute_authorized_design`/授权账本 → supervisor/launch_request → MATLAB行请求
读取/校验 → `run_mamyshev_recorded`/`run_mamyshev_config` → 原生产循环 →
终点尾纤与同次压缩 → 分平面输出/waveform writer → 父final → DB/CSV/MAT导出。
原单点、1D/任意2D/4D grid/random/LHS/CSV、精确recorded查询、逐点保存、进度、
STOP/续扫、失败需明确重试授权、来源/单位/导出代码保留，没有替代求解器。

用这次train纯X生成独立 `matlab_plan/gmmnlse_pending_plan.json`，恰好10000个唯一
设计，所有solver targets=null/not_run，真实额度0。canonical计划hash：
`82de9d55aabbb0fcdd5a3657c856f5f5b0f8a411093bdd156063f2d8c7884d9d`。
真正plan/validation代码验证首/中/末第1/5001/10000行、40块（39×256+16）、
筛选、范围/格点、ID和hash，不把合成Y抄进原solver计划。完整计划仅本地。

实际以其中3条已有同源标签做RecordedEvaluator重放：第一行提交后STOP、关闭DB、
重开续扫另2行、再次进入跳过全部；DB/CSV/MAT读回通过，错误身份无回退，原训练DB
hash不变。3次调度/缓存读取新增研究标签0、配方调用0、真实尝试0。

只启动**1个MATLAB短进程**，7个断言组通过：校验10000行结构/单位/格点/ID/空目标，
只对首中末3点及legacy默认共4次实际无传播初始化；原Nt32768、50ps、max_rt50、
步长/容差、固定无源长度0.4/1.5/3.2m及尾纤0.2m均保留。
32个已有合成标签跨语言复算，最大差分别
3.4106051316484809e-13nJ /6.3948846218409017e-14fs /6.2172489379008766e-15MW，
满足固定 `abs(error)<=1e-10+2e-10*abs(ref)`；RNG不变，不新增研究标签。

MATLAB短进程exit0、cleanup_verified=true，无stop事件。当前结果支持
“10k计划与调度路径经过检查”，**不支持“10k真实数据生成通过”**。实际全量
GMMNLSE、长时磁盘/内存压力、所有系统故障恢复均not_run。现有调度一次只执行
一行并持久化，不预分配10000组传播复场；状态/resume不加载全部历史MAT。

0许可在真实目录/进程预留前拒绝；完整执行仍需独立批准完整plan hash、ID集合、
次数和单次/累计预算，resume不能重置余额。原单次物理保存规则没有为扩展性改动。
H02未解决，MFD/SR、1-H、滤波、N_total覆盖、增益材料、H01/H04及RNG/精度未改。

公开clone还有明确依赖边界：现有capture B严格初始化比较依赖本地历史
`reports/local/phase1/baseline_001/configuration.mat`。该原始证据不进入公开Demo，
缺失时gate拒绝。本批验证的是现有本机数据链和独立纯推理，不声称公开clone已包含
全部真实执行证据；最小可分发参考资产需另行审核，不能关闭gate绕过。

## 7. 实际命令、测试、成本与未执行项

所有项目Python均通过指定Conda环境，详细绝对命令、退出状态及日志在本地
`budget_ledger.json` 及其各label监控目录；未直接绕过现有串行监控。
以下仅为可读后缀，计划的输入/输出在实际argv中使用仓库绝对路径，因为监控器
子进程cwd是日志目录；不能直接复制相对数据路径版本重跑已消耗的批次：

```text
scripts/run_demo10k_budget.py --timeout-s 850 ml formal_training -- scripts/run_demo10k.py
scripts/run_demo10k_budget.py --timeout-s 60 engineering model_assets -- scripts/build_demo_assets.py
scripts/run_demo10k_budget.py --timeout-s 60 engineering pending_10k_plan -- scripts/prepare_demo10k_matlab_plan.py --inputs reports/local/demo_10k_release_001/samples/train/inputs.csv --labels reports/local/demo_10k_release_001/samples/train/labels.csv --count 10000 --out reports/local/demo_10k_release_001/matlab_plan
scripts/run_demo10k_budget.py --timeout-s 60 engineering recorded_resume -- scripts/demo10k_recorded_resume.py
scripts/run_demo10k_budget.py --timeout-s 180 matlab plan_and_parity -- scripts/run_demo10k_matlab_components.py
```

| 验证 | 本批实际结果 | 解释 |
|---|---|---|
| `test_demo10k_experiment.py` | 6项通过 | 配额/一次fit协议、X-only几何、跨角色互斥、确定性/碰撞、独占预留、整数gate；fixture不产生标签 |
| `test_demo10k_plan.py` | 6项通过 | 通用N/null目标、分块/筛选/hash、CSV身份、非法/重复/单位/格点拒绝及0许可 |
| `test_demo_inference.py` | 5项通过 | 严格输入、两版本身份/各自q、保存预测回归、缺失/篡改前置拒绝、任意模型名拒绝 |
| 原live授权回归 | 复用5项通过 | 0额度、变更计划/ID、禁止目录/批次重置、未完成预留阻断、累计预算/STOP；真实执行mock |
| Recorded重放 | 1个三行流程通过 | 非新增拟合/标签；不能把3次读取算3个新物理样本 |
| MATLAB | 1进程、7断言组通过 | 4次初始化和32已取标点parity；传播0 |

上述Python为17项新增组件方法和5项复用方法；界面测试另列第5节，不把重复运行
或三个输出扩增成独立测试/设计数。历史完整单点成功/失败不计为本批执行。

| 预算类别 | 实测计账外部墙钟 | 上限 |
|---|---:|---:|
| 生成/训练/校准/新评价/重载 | 35.91768304200377秒 | 900秒 |
| MATLAB短进程（含父侧记账） | 40.07521795807406秒 | 180秒、最多2进程 |
| 工程受监控子进程，含失败、重测、短服务及收尾取证 | 187.7524386671139秒 | 600秒；工具等待另计，见下方超限说明 |

**预算异常：** 浏览器控制 `cua_repl getApp(Safari)` 单次工具返回元数据为
2717.7581s，未纳入原子进程ledger。按包含控制工具等待的保守工程墙钟口径，
600s预算已超出，不能以187.75s声称整个工程任务未超限。它与短服务器时间重叠，
不能简单相加声称精确总耗时；精确去重总工程墙钟未测得。服务仍在自身120s上限内
停止，未延长计算窗口。返回后没有新增组件/浏览器/科学尝试，只做停止后的
Git/保留核查和报告落盘（受监控2.495496s，已计入上表）。独立异常记录在
`budget_exception.json`；视觉验收留为未完成，不用伪截图补齐。

Streamlit安装的首次自动审批因尚未核对prompt的安装授权而拒绝，未执行安装；
补充原指令第30行及固定数值版本约束后，同一具体安装获得批准并执行一次。
解析和安装退出状态保留在 `ui_dependency/`；未绕过审批、未用sudo或改权限。

唯一模型fit内部计时0.32434795796871185秒，pipeline内部33.51601879193913秒，
不能把fit内部时间当成全实验成本。MATLAB被监控进程墙钟40.07441891601775秒。
工程中的失败尝试和重测均保留、计费；安装数值库版本未变。全部串行，数值线程
最多2；MATLAB显式singleCompThread，无parpool/GPU/云计算。

未执行：第二次拟合或调参、新BO/随机对照、10k真实扫描、额外整腔、物理/网格/
窗口/步长/随机鲁棒性验证、旧test重评分、新全新环境验收、Git写操作或公开部署。
真实solver泛化误差和节省均为not_measured。本批结束等待审核，不自动后续计算。

## 8. 交付路径、发布范围与下一步

| 工件 | 实际路径与边界 |
|---|---|
| 新权重/新q/冻结身份 | `reports/local/demo_10k_release_001/release/`（local-only原始证据） |
| 两版最小推理资产 | `demo/assets/models/`；功能可用不等于许可已确认 |
| 新推理manifest | `demo/assets/models/demo_10k_v1/manifest.json` |
| Demo入口 | `demo/app.py`、`demo/predict.py` |
| 聚合指标 | 两版各自 `metrics.json` / `model_card.json`，不混用旧新成绩 |
| 10000行原solver待执行计划 | `reports/local/demo_10k_release_001/matlab_plan/gmmnlse_pending_plan.json`（local-only） |
| 原始X/Y、角色/查询账本、逐点评分 | 本批 `samples/`、`oracle_queries.jsonl`、`*_predictions.csv`（local-only） |
| 独立展示副本/截图 | 见第5节最终核查；内部副本需清楚标记许可待审 |
| MATLAB接口矩阵 | [DEMO_10K_MATLAB_MATRIX.md](DEMO_10K_MATLAB_MATRIX.md) |

允许的事实表述是“在10,000个repository-guided synthetic设计上训练四输入代理，
并保留可续扫的MATLAB/GMMNLSE数据生成管道及参数化10000设计计划”。不能写成
“10,000次GMMNLSE仿真训练通过”。小样本1024版本保留为历史效率参考，新版不是
对原方法的否定或真实激光性能升级。

源码、模型、配方和图片许可按来源分别审查；MMTools的GPLv3不自动为整个定制
GMMNLSE引擎或混合仓库授予同一许可。本批未给全仓库添加MIT结论，未上传数据，
未发布模型/截图/源码。当前 `public_release_blocked`：功能验收和法律上可公开
allowlist不同。下一步只应审查具体文件/许可及拟发布范围，不自动训练或运行真扫描。

## 9. Git建议上传／不上传／待审批文件清单

完整逐文件路径、字节数、SHA-256、tracked/staged/untracked/ignored状态、匹配
ignore规则、用途/来源/必要依赖和后续动作，以本地
`reports/local/demo_10k_release_001/git_release_manifest.json` 与
[GIT_RELEASE_PLAN.md](GIT_RELEASE_PLAN.md) 的实际末项审查为准。
该机器清单不含原始数据行。以下是文件组决策，**不是git add或发布授权**。

实际工作树快照3176个文件，当前tracked1017、staged0，可用本地历史相关对象340。
逐文件建议：include243、keep_local1884、review_sensitive40、
needs_untrack_approval149、blocked_license860。149是保守的历史数据/归档路径数，
包含归档脚本，不等于149份独立数据集；是否保留脚本公开版本仍需逐项审查，
不能据此自动取消源代码跟踪。860同样包含引擎源码、材料、示例与参考文献，
不是声称每个文件都是当前MATLAB运行必需依赖。
清单SHA-256为
`e5dcdf11afb0e8b5b75f392570cc9a6d200965249a638b30fd53907280c8aa71`。
完整清单保存实际状态和ignore行号；README/指南中的机器命令等标记review_sensitive，
公开quick entry不依赖这些私人路径。结构扫描能发现常见全量JSON设计/ID/XY数组，
不是对任意编码数据/秘密的完备证明；新增审计分类代码仅静态复核，没有在预算异常
后再增加组件测试。上述快照不包含随后生成的自身/保留核查及最终文档hash文件。

| 类别 | 实际路径/必要文件组 | 建议及所需动作 |
|---|---|---|
| A 拟提交工程 | `demo/app.py`、`demo/ui_logic.py`、`demo/predict.py`；新推理/训练/计划源码与测试；小型 `configs/demo10k_protocol.json`、Demo依赖、README/指南/聚合指标与自有图 | 按实际逐文件allowlist审查；只包含生成方法/小配置，不能夹入完整数据快照 |
| B 仅本地数据与运行证据 | `reports/local/`；`mamyshev_accuracy_v4/data/`、`evaluation_only/`、`evidence/`、`plans/`、完整provenance数据；新10000行plan、X/Y/逐点评分、SQLite/JSONL/CSV、原逐圈MAT/日志/缓存 | keep_local；改成JSON/ZIP/LFS仍是上传数据，不接受绕行 |
| C 推理工件 | `demo/assets/models/{v42,demo_10k_v1}/` 及catalog | 明确权重/原类/域/q/manifest/card和聚合metrics；blocked_license，先审核来源和分发权，不上传旧整包ZIP |
| D 已跟踪/历史/第三方 | 现有 `data/`、`archive/original_experiment_folder/` 输出；历史完整JSON身份表；`code/simulation_engine/`、`third_party/` 材料/源码及论文 | 数据跟踪问题须另批untrack/history动作；第三方MAT/CSV截面输入是依赖，应保留署名逐项审查，不能全局删除 |

`.gitignore` 对已跟踪文件和旧历史无效。即使新数据均ignored，也不能声称索引或
历史已清除；本批没有 `git rm --cached`、取消用户stage、删除数据或改写历史。
完整 `configs/accuracy_v4_2_protocol.json` 是含旧训练ID和私人路径的历史身份快照，
不能当作普通“小型配置”上传；保留其字节并在实际清单中单列待审/本地范围。
只审查可用本地历史，未联网核对远程，不能声称远程从未含数据。

下一次需用户批准的动作：具体源码/模型/配方/图的许可范围与精确提交allowlist；
哪些已跟踪数据如需取消跟踪；是否另行处理历史及其影响。当前不执行任何
add/commit/push/tag/PR/Release、远程修改或公网部署。
