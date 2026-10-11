# Demo 任务导向 UX 检查报告

本批依据 `CODEX_DEMO_TASK_ORIENTED_UX_PROMPT.md`，以现有未提交工作为起点，
仅调整 Demo 的设计比较旅程。分支 `feature/mamyshev-ml-mvp`，起点 commit
`489bf4242f9b5266d47f8892840a24af66931ff0`。完整记录在本机
`reports/local/demo_ux_001/`；本文这些路径均为 local-only，不是公开数据下载。

本批没有训练、partial_fit、调参、校准、新标签、oracle、BO、MATLAB 启动或
真实传播，没有改变环境或模型资产。已有模型的有限批量预测不是新增仿真。
`DOCUMENT_REVIEW.json` 描述的是较早上传文档的审核范围，不能把其中旧1024点
身份当作本批实际新资产；本批直接核对受信模型文件。指令提到两张滚动视口截图，
本批未取得可读取的对应图片文件；改动依据其描述及实际旧源码，不声称独立审图，
也不据截图描述断言原页面顶部没有标题。

## 1. 从调试表单到设计决策

| 旧问题与源码依据 | 当前实现 | 实际检查范围 |
|---|---|---|
| 旧单点页主体直接输出四字段JSON、密集小数与重复状态 | 工作台以任务、基准和结果卡片开场；E/τ显示2位、peak显示3位；全部身份与原请求移入Technical details | 新AppTest旅程；视觉状态单列 |
| 原探索页仅技术场景编号、top表和批量导出，缺少明确基准比较 | 四个可读场景，目标/每条约束/固定项明确；同模型基准、候选差值、选择及最多3条零额度导出 | 默认案例及场景/状态检查 |
| 原2D使用着色散点，轴参数也有“固定值”输入框 | Parameter response只编辑非轴固定输入；真正rect热图，数值中点边界，实际节点值与baseline/best标记 | chart spec、实际Arrow单元格和原Prediction对照 |
| 访客不清楚pred来自何处，旧确认结果与新模型容易混淆 | Method & evidence解释原329维模型及本版本聚合误差；旧SyntheticEvaluation单独保留1024身份 | 受信聚合资产读取与页面组件检查 |
| MATLAB能力和当前授权易混淆 | 保留数据链、10k摘要与历史图；下载明确null真实目标/0额度，无启动按钮 | 界面组件检查；本批MATLAB为0 |

核心文件为 `demo/app.py`、`demo/ui_logic.py`，新增 `demo/ui_charts.py`。
实际定位：app第270行工作台、第391行响应页、第466行方法页、第501行数据链，
第528行Technical details；logic第85行scan_plan、第134行candidate_plan、
第213行逐项约束、第260行原精度比较、第189行最多3条导出；charts第120行
response_chart、第65行baseline位置校验、第82行可核查摘要。
CSS仅在app内设置紧凑字阶、1440px容器和留白，无新框架、渐变或动画。
用户点击 **Load 10k fixed-hardware example** 才切换会话模型；catalog旧默认不改。
请求键绑定model_id/hash及全部有效输入、场景/约束、范围、固定项、种子、轴/点数、
目标和基准。输入变化立即清除失效结果；换版后两侧基准/候选均按同一模型计算。

热图每个rect只表示一个预测节点；半间距端点和中点边界是显示几何，不是插值
或额外有效设计。非均匀坐标仍用真实数字位置。baseline另行实际预测；超出范围
或不属于当前固定切片时明确省略，不代换最近网格点。最佳标记依据场景目标，
切换着色目标不会偷偷改变优化目标。缺失单元格保留空缺，非有限值报错；1D缺点
不跨缺口连接。候选图是实际随机候选的散点投影，明确与rect响应网格区分。

## 2. 实际交互案例与解释

明确选择 `demo_10k_v1`，基准(4 W,10 nm,3 nm,4 m)。固定P=4 W、L=4 m，
offset范围[2,16]nm、BW范围[0.5,8]nm，预声明seed=72001、512个X-only候选。
全部512个实际预测后按τ≤40 fs过滤，392个满足点预测约束，再按未舍入peak降序。
这是有限集合的预测筛选，不是新BO、后端评价或全局最优。

| 同一模型Prediction | P W | offset nm | BW nm | L m | E nJ | τ fs | peak MW |
|---|---:|---:|---:|---:|---:|---:|---:|
| 基准 | 4 | 10 | 3 | 4 | 128.7709920859408 | 29.91580676994026 | 2.846866677231053 |
| 本集合排名1 | 4 | 12.748250674704583 | 2.5909894419446977 | 4 | 157.70846025712183 | 26.631904950854267 | 3.9159414878563075 |
| 交互选择的排名2 | 4 | 12.542048893119789 | 3.261074843050721 | 4 | 157.88135476760615 | 26.89363358722789 | 3.882471992273093 |

实际选择排名2进行比较，再选排名1–3导出3条请求。排名2相对同模型基准：
E差29.11036268166535nJ、τ差−3.022173182712372fs、peak差1.03560531504204MW；
peak相对差36.377021914117186%，分母是基准原精度2.846866677231053MW。
这只是Prediction之间的比较，不能作为新确认改善或真实性能收益。
基准与这两候选的τ点预测及诊断上界均小于40fs，区间仍是limited，不能叫物理安全。

原请求、全部预测与未舍入对照保留在 `app_test_002/actual_example.json`；
首轮与最终轮基准、top3原精度对象完全相等。请求构造及下载控件接线经过AppTest，
没有实际浏览器点击下载；不把组件导出检查说成浏览器下载已完成。
导出中prediction与 `real_targets=null` 分离，`evaluation_id=null`、
`max_new_real_attempts=0`、状态not_run。没有创建Evaluation或执行任务。
另外通过无可行点、用户固定项、非法长度、重复轴、模型/输入/约束/范围/种子变动
检查，确认不放宽约束、不会保留已失效推荐。

## 3. pred的真实计算路径

实际调用为 `demo/app.py:frozen_prediction/execute` →
`src/mamyshev_ml/demo_inference.py:predict`（第145行）→
`load_model`（第124行：verify后加载joblib）→
受信 `demo/assets/models/<版本>/models_v4.py:LogSurrogate.predict`（第35行）。
该类 `_x`（第16–22行）校验四字段数值和0.1m长度格点，并按原声明域缩放。

64结点三次B-spline与最高4阶Polynomial并集共329维；保存的StandardScaler
随后进入三个分别针对log目标的Ridge(alpha=.001)，预测后exp返回nJ/fs/MW。
训练构造见原类第23–34行，**本批未执行这些fit行**。三个输出独立回归，
推理时没有用E/τ拼装峰值。所需只是已保存的结点、缩放统计和系数，不查训练CSV。
旧/new q分别绑定旧/new权重，从受信calibration只读取得；区间由预测×exp(±q)
构成，不代表传播噪声，不承诺每组或每候选95%覆盖。

实际加载与warm predict计时分别记录，不包含渲染，也不除以旧MATLAB任务成本
宣称加速比。81/441预测节点不等于81/441次传播。真实GMMNLSE泛化及计算节省
仍not_measured；physical_state=undetermined、numerical_validation=not_verified，
eligible_as_validated_training_truth=false。

## 4. 运行依赖、测试与预算

无需训练数据集或MATLAB即可启动这份纯推理Demo；保留 `demo/`、
`src/mamyshev_ml/{__init__,demo_inference,v4_evaluators,v4_scan}.py` 和域/场景小配置。
受信两版模型/类/q/manifest/catalog与精选摘要/历史PNG保持原字节。
沿用已有Python3.11环境、Streamlit1.64、pandas/pyarrow/Vega-Lite与原数值依赖；
本批没有安装或更新任何包。独立副本清除PYTHONPATH，从副本加载原类；
没有借原仓库data/reports补依赖，也没有声称全新环境或跨平台验收。

```sh
/opt/homebrew/Caskroom/miniforge/base/bin/conda run -n mamyshev-ml --no-capture-output python -m streamlit run demo/app.py --server.address 127.0.0.1 --server.headless true --browser.gatherUsageStats false
```

用户可打开 `http://127.0.0.1:8501`，用Ctrl-C停止自己启动的服务。本批未启动服务器，
未结束用户已有服务，也未占用或清理未知端口。没有调用任何浏览器控制工具，尤其
没有再次调用上次阻塞的Safari路径；**browser_visual_check=not_run**，真实桌面
1366/1440布局与截图仍待用户网页审核。AppTest、chart spec和Arrow数据检查是组件
证据，不冒充视觉验收，没有伪造截图。

| 实际执行 | 覆盖与结果 | 受控墙钟 |
|---|---|---:|
| 起点保全 | 独占目录、模型hash、紧凑组摘要 | 1.314026375s（初始化内部记账） |
| `components_001` | 5项新增fixture + 旧UI3项 + 旧推理5项；13项通过 | 3.451331584s |
| `app_test_001` | 10个真实AppTest交互情形通过 | 22.442734084s |
| `app_test_002` | 10个重复回归 + 2个新增情形通过 | 23.945659042s |
| 最终保全/差异检查 | 分组/分支/索引均保持，diff检查退出0 | 1.524436833s |

合计52.678187918s，上限300s；最大单进程23.945659042s，均小于60s。
5个fixture方法与12个独立交互情形分开统计，重复10项不算新增测试或研究设计。
AppTest最终runtime计数fit/oracle/Evaluation/MATLAB均0；23次原类predict方法调用
不等于23个独立设计。两模型UI/direct/CLI最大绝对差均0，atol=rtol=1e-10未变。
441cell测试读取Streamlit实际Vega-Lite spec及Arrow数据，逐格核对4输入、3输出、
颜色字段、x/x2/y/y2边界、单位和baseline/best标记；不是只断言图元素存在。

首轮通过后静态复核补了3处小修，原记录保留：用户额外fixed需合并到有效场景
供baseline约束/排名/导出；current提交失败清空局部旧值；baseline须在预测成功后
同时更新输入和结果。第二轮新增S1固定P5而baselineP4的逐项失败/导出快照检查，
以及只抛错、不生成输出的UI异常fixture，验证旧current不再显示、baseline不被
半更新。该人工异常不是模型失败数据或模拟标签。

实际命令均使用指定Conda前缀；测试后缀分别为
`scripts/run_demo_ux_budget.py --timeout-s 60 engineering components_001 -- scripts/check_demo_ux_components.py`、
`scripts/run_demo_ux_budget.py --timeout-s 60 engineering app_test_001 -- scripts/check_demo_ux.py --out <本批绝对路径>/app_test_001`、
以及相同命令的新 `app_test_002` 目录。全部完整argv及退出0记录在 `budget_ledger.json`。
最终功能副本为 `/private/var/folders/v4/k3141v0s2zx7j_jfk_py92qh0000gn/T/mamyshev_demo_ux_ascs7cim/preview`，
35个allowlist文件；清单/hash在 `app_test_002/independent_copy.json`，不含数据集，
仍 `public_release_blocked=true`。副本可能被系统清理，仓库内Demo为持久入口。

第二轮实测单行verified loading分别3.190523750s（旧模型，含首次依赖导入）与
0.017341250s（新模型，依赖已导入）；warm原类predict分别0.005044500s与0.004994917s。
这是该进程次序下的诊断计时，不是两模型加载性能对比，也不是物理仿真加速比。

预算沿用 `run_v4_budget.py` 和 `tests/run_matlab_short.py` 的原进程组监控，
仅用 `scripts/run_demo_ux_budget.py` 将本批总额固定300s、单子进程≤60s、串行、
数值线程≤2；AppTest另有50s内部watchdog。失败和复测均计账。此预算是受控
子进程计算墙钟，不包括人工编辑/工具交互等待；本批无不可中止的浏览器等待。

## 5. 保全与边界

起点保全是紧凑分组hash，未复制几千个历史文件；只备份6个拟改文件用于差异核对。
保护两模型全部22个资产、原code/third_party、已有1767个local证据文件以及数据/
配方/科学Python代码。新10k权重SHA：
`9885e8f258fa10de0a69844b70fa72242fcc64267d9db1e6c07dd4bd4609b6d0`。
旧默认、q、模型类、真实MATLAB单点/扫描/10k计划/保存/续扫/DB/导出与门禁不变。
最终 `preservation_check.json` 全部为true：模型/精选资产22文件、生产/材料859文件、
旧local证据1767文件、数据/配方/科学Python298文件分组hash均与起点一致。
原loader与CLI单独hash也一致；分支、commit、索引diff未变（staged仍为空）。
上批三份最终报告另按原final_document_hashes核对，全部OK。
`git diff --check`退出0、输出为空。最终报告随后只补写这些实测结论；
新改文件最终hash记录在本批 `final_file_hashes.txt`。
只改变界面与相关测试/说明；旧报告不覆盖，历史Phase2深度物理验证仍in_progress。
本批交付后停止，不继续训练、搜索、扫描或发布。

## 6. Git建议上传/仅本地/许可待审

| 实际增量路径 | 建议 | 本批行为 |
|---|---|---|
| `demo/app.py`、`demo/ui_logic.py`、新增 `demo/ui_charts.py` | 拟审阅源码；CSS在app内 | 仅工作树改动，模型计算器不变 |
| `tests/test_demo_ux.py`、`scripts/check_demo_ux.py`、`scripts/check_demo_ux_components.py` | 拟审阅组件/交互测试 | 人工fixture不是数据集；实际预测证据不嵌入公共源码 |
| `scripts/run_demo_ux_budget.py`、`scripts/demo_ux_preservation.py` | 拟审阅薄预算/保全适配 | 复用已有监控，不新建运行平台 |
| README、`docs/USER_GUIDE_ZH.md`、本报告、SCOPE/EXECUTION_STATUS | 拟审阅文档；本机命令/路径另作敏感范围审查 | 历史报告保持原字节 |
| `reports/local/demo_ux_001/`及仓库外临时副本 | 仅本地 | 全部预测候选/完整plan、日志、请求与测试账本不上传；数据不改装JSON/ZIP/LFS发布 |
| 截图 | 未生成 | 视觉not_run，不将旧图或AI图当运行截图 |
| 原两版权重/类/manifest/q、第三方材料/引擎及历史资产 | 许可仍待审，非本批增量 | 无取消跟踪、删文件、Git写操作或公开发布 |

本批不解除上批已跟踪数据/许可/私人路径的发布阻塞，不重写全仓库Git清单，
也不把未提交旧生产修改误归为此次UX改动。
