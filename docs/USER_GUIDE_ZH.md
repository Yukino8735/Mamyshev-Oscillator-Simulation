# 使用指南：数据、特征、训练与保留的 MATLAB 后端

## 本次发布检查：可复用训练入口与明确的真实运行前置条件

主项目仍是唯一维护来源。当前授权是在限定检查后发布本人项目代码和轻量 Demo，
不是重新训练10k模型、上传完整数据或部署云端 App。下文旧批次的“未授权发布”
属于历史记录；本次实际 Git 分支、commit、main/PR 和未发布内容以
[发布报告](FULL_PIPELINE_GITHUB_RELEASE_REPORT.md)为准。主项目已有仓库为
[Mamyshev-Oscillator-Simulation](https://github.com/Yukino8735/Mamyshev-Oscillator-Simulation)；
Demo 仓库及在线 App 的实际状态须分别核验，不能将拟用地址当作已经上线。

普通新数据训练使用 `scripts/train_surrogate.py`，不再要求旧私人实验目录、
固定 run_id 或冻结研究 manifest。它读显式给定的 V4Store 数据库或无损训练 CSV，
按完整来源身份选择记录，调用原 `LogSurrogate`，保存并重载同一特征变换。
原10k权重、模型类、q、评分和历史加载器保持独立。

以下命令是未来自行执行的小例子；本次没有执行16点标签生成。
从仓库根目录运行，目录已存在时先检查，不清空旧产物：

```sh
mkdir -p reports/local
mkdir reports/local/user_pipeline_001
/opt/homebrew/Caskroom/miniforge/base/bin/conda run -n mamyshev-ml --no-capture-output python scripts/v4_scan.py plan \
  --spec examples/plan_small.json --out reports/local/user_pipeline_001/plan.json
/opt/homebrew/Caskroom/miniforge/base/bin/conda run -n mamyshev-ml --no-capture-output python scripts/v4_scan.py run \
  --plan reports/local/user_pipeline_001/plan.json --db reports/local/user_pipeline_001/evaluations.sqlite \
  --scan-id small_synthetic --evaluator synthetic --execute --max-new-attempts 16 --total-wall-s 60 \
  --stop reports/local/user_pipeline_001/STOP
/opt/homebrew/Caskroom/miniforge/base/bin/conda run -n mamyshev-ml --no-capture-output python scripts/train_surrogate.py identities \
  --db reports/local/user_pipeline_001/evaluations.sqlite --out reports/local/user_pipeline_001/identities.json
```

`examples/plan_small.json` 是16个四维 LHS 输入；plan 本身不取标签。
显式 `--evaluator synthetic --execute` 才生成已标明来源的解析合成标签，
不是GMMNLSE结果；去掉 `--execute` 只显示计划。检查 `identities.json` 后，
从 `identities` 数组中**选择一个完整对象**，单独保存为同目录 `identity.json`。
不要保存外层数组，不要删改 source/backend/numerical_version/seed/
observation_protocol/metric_definition 六个字段；没有默认混训或来源回退。

```sh
/opt/homebrew/Caskroom/miniforge/base/bin/conda run -n mamyshev-ml --no-capture-output python scripts/train_surrogate.py export \
  --db reports/local/user_pipeline_001/evaluations.sqlite --identity reports/local/user_pipeline_001/identity.json \
  --out reports/local/user_pipeline_001/training.csv
/opt/homebrew/Caskroom/miniforge/base/bin/conda run -n mamyshev-ml --no-capture-output python scripts/train_surrogate.py split \
  --csv reports/local/user_pipeline_001/training.csv --identity reports/local/user_pipeline_001/identity.json \
  --seed 11 --out reports/local/user_pipeline_001/split.json
/opt/homebrew/Caskroom/miniforge/base/bin/conda run -n mamyshev-ml --no-capture-output python scripts/train_surrogate.py fit \
  --csv reports/local/user_pipeline_001/training.csv --identity reports/local/user_pipeline_001/identity.json \
  --split reports/local/user_pipeline_001/split.json --model-id user-source-emulation-001 \
  --out reports/local/user_pipeline_001/model
/opt/homebrew/Caskroom/miniforge/base/bin/conda run -n mamyshev-ml --no-capture-output python scripts/train_surrogate.py predict \
  --model-dir reports/local/user_pipeline_001/model --trusted-local --design examples/design_default.json \
  --out reports/local/user_pipeline_001/prediction.json
```

`training.csv` 保留 `record_json`、原单位、来源和证据引用，是上述 export 专用格式；
它不是 `v4_scan.py export` 输出的扁平 `results.csv`。也可在 fit/split 中直接用
`--db` 代替 `--csv`。记录选择会报告失败、缺失、不合格或其他身份的排除原因。
同设计重复记录按 `design_id` 分组，不能跨训练/开发/测试集合；至少8个不同训练
设计、2个开发设计才能执行接口，这个最低数量不保证模型质量。需要测试集时，
显式 split 可包含独立 test ID 列表，不能借用旧冻结实验 held-out。

特征只取四维设计输入：声明域缩放 → 样条和交互多项式 → 仅训练集拟合的
StandardScaler → log正目标 Ridge → exp还原。固定K64表示共329个特征；
一次 fit 调用拟合三个目标，不做调参或重校准。新模型元数据保存自身来源/协议、
split、行数与独立设计数、模型/类哈希和变换信息，不能沿用10k模型的性能或q。
`--trusted-local` 只用于自己信任的本机权重，joblib 反序列化可执行代码。

真实结果也走同一个训练导出和fit入口。先只读导入其原始父进程 final：

```sh
/opt/homebrew/Caskroom/miniforge/base/bin/conda run -n mamyshev-ml --no-capture-output python scripts/v4_scan.py import-final \
  --db reports/local/user_pipeline_001/solver.sqlite --final /path/to/original/run/final_result.json
```

之后对 `solver.sqlite` 执行相同 identities/选择/export 流程。资格边界是新增的
`v4_training.training_records/read_records`，不是仍保持冻结字节的低层
`V4Store.training_records`。会复查真实模式、原final/request/runner、来源身份、
停止/退出一致性和引用波形完整性；三个正有限目标均来自相同压缩分析平面。
`undetermined` 可以取得**拟合该求解器输出**的资格，但不会变成物理验证真值。
Prediction、timeout/failed、缺final、null、非有限值、错误单位或混入上游能量均不合格。
真实CSV仍须保留原证据路径可访问，不能用CSV自行补造final。只有一条真实设计时
可以验证X/y导出，不能靠复制记录凑训练或R²。

本次限定验证已通过：复用128条既有训练记录和16条开发记录，共144个不同设计，
未访问旧held-out。在干净源码副本中仅执行一次临时 `release-smoke` 三目标 fit，
329个特征，scaler仅用128条训练行拟合，保存/重载预测最大差为0。
另有一条真实历史final通过数据库 → 有资格的训练CSV → X/y核对，物理标志未改。
这些证明接口接通，不是新的模型精度研究。没有新增标签、重训10k或启动MATLAB；
组件测试结果和实际耗时见发布报告。

**公开 MATLAB live 路径仍 blocked。** 原严格 gate 要求本机历史
`reports/local/phase1/baseline_001/configuration.mat` 及 `configuration.json`，
尚无公开的可替代参考或参数化资源准备入口；本轮没有关闭 gate 或制造参考。
本机修改的 Cornell 传播代码也不进入本次新增发布范围。完整本机MATLAB代码、
材料及历史证据保留，单独下载上游不能被说成等价于当前定制引擎。
因此公开代码具备计划、调度和保存等接口，不代表新用户 clone 后可无条件真实运行。
未来 live 须解决这些精确资源和分发范围、MATLAB及工具箱，再取得具体预算授权。

计划可复用上述 `examples/plan_small.json`；未来真实路由仍为
`GMMNLSEEvaluator → supervisor → run_mamyshev_recorded → run_mamyshev_config`。
`scripts/v4_scan.py run` 的真实选项是 `--evaluator gmmnlse --authorization ...
--batch-dir ... --execute --execute-real`，必须绑定明确plan hash/设计/seed/次数/
墙钟授权，不能因这些标志存在就视为得到授权。STOP、所属进程组清理、父进程final
和取消/续扫累计预算保持原实现，本次不启动MATLAB。

## 前次同步记录：完整主项目 → 检查 → 白名单导出

原 Mamyshev 主项目是唯一维护来源，包含数据生成、训练/评估、条件搜索、
MATLAB/GMMNLSE、扫描/保存/续扫、数据库及导出；网页只是其中的纯预测入口。
当前 Demo 只展示 `demo_10k_v1`，旧1024模型、q、研究CLI和历史证据继续保留。
本批复用此前已同步的界面，收回导出规则与模板，不重新训练或重做物理阶段。

以后修改主项目的 `demo/` 及相关推理/校验代码，执行受影响检查，再从主项目根目录导出：

```sh
/opt/homebrew/Caskroom/miniforge/base/bin/conda run -n mamyshev-ml --no-capture-output python -B scripts/export_demo.py --output "$(cd .. && pwd)/Mamyshev_Demo_Deploy_synced_001"
```

命令先将本批目标解析为绝对路径；导出器拒绝含字面 `..` 的路径。
产物存在后不要再次使用此路径，导出器会拒绝覆盖。
旧 `Mamyshev_Demo_Deploy` 是只读比对依据，新副本是交付产物，都不是并行开发仓库。
导出仅需主项目源码、`demo/deploy/` profile/模板及受信10k资产，不依赖私人报告、
训练CSV、数据库或旧部署副本；不下载模型、不拟合、不取标、不启动MATLAB。

新副本内可用下方同一 Streamlit 命令启动 `demo/app.py`，依赖声明使用副本根目录
`requirements.txt`。主项目仍使用自己的完整环境声明。不要将副本的精简 `src/`、
README或依赖文件拷回覆盖主项目。发布前须对新 manifest 单独审批；本批不启动
浏览器/服务、不做Git写操作或部署。详细流程见 [DEMO_DEVELOPMENT.md](DEMO_DEVELOPMENT.md)，
结果见 [PROJECT_DEMO_SYNC_REPORT.md](PROJECT_DEMO_SYNC_REPORT.md)。

训练来源集中在当前 Demo 的 **Method & data / Data & validation**：10,000个
repository-guided synthetic设计，不是10,000次GMMNLSE输出。已有预测、聚合指标
和区间保持原身份；下面的历史结果、失败记录及完整MATLAB操作说明不改写。

## 任务工作流：比较方案并导出待验证请求

本次UX改动仅使用已有权重预测，没有训练、生成标签、校准或启动MATLAB。
当前 Demo 已同步为 single_10k_001，只使用 demo_10k_v1；启动方式为下方同一命令。

1. 打开 **Design workbench**，点击 **Load fixed-hardware example**。
   该按钮重置当前会话基准和结果，使用唯一的10k模型。基准为(4,10,3,4)，
   页面从选中模型实际计算它的三个输出。
2. 查看任务：泵功率4 W、增益长度4 m固定，改变滤波偏移与带宽，在预测
   脉宽≤40 fs的约束下寻找本次有限候选集合内更高预测峰值。
   可以编辑适用范围、约束、候选数及种子，再显式提交预测。
3. 查看每条约束的预测可行性，诊断区间在展开区查看，选择候选与基准
   并排比较；也可把当前设计设为会话基准。两侧均使用同一10k模型，
   旧模型会话被拒绝，须点击示例按钮重置。输入变化后旧结果失效，需重新提交。
4. 在 **Parameter response** 选择1D或2D、变化轴及范围/点数；只有非变化轴
   出现固定值编辑框。二维图每个色块来自该坐标的实际模型预测，不插值。
   基准标记使用真实坐标，不会把最近网格点当作基准。图示可行性是预测判据，
   不是物理稳定性相图。
5. 回工作台，选中最多3个候选下载待审批请求。预测值与 `real_targets=null`
   分开，`max_new_real_attempts=0`；下载不是启动任务，候选尚未被后端确认。

主卡片能量/脉宽显示2位、峰值显示3位小数；排名、约束、差值和下载使用未舍入
的原始值。没有可行候选时页面如实显示，不放宽约束。JSON、q、hash和model card
放在 **Technical details**，底层来源未删除。**Method & data** 解释预测计算，
旧SyntheticEvaluation始终保留旧1024模型身份，不能当成新10k预测的确认结果。

本批视觉验收留待用户检查真实网页；不使用AI图或静态假页面充当截图。
可按上述旅程查看桌面工作台与热图；技术测试及实际案例见
[DEMO_UX_REVIEW_REPORT.md](DEMO_UX_REVIEW_REPORT.md)。

## 当前入口：交互 Demo 与独立推理资产

新增 `demo_10k_v1`，实际以 10,000 个唯一合成设计进行一次三目标拟合。
Demo 默认且仅接受 `demo_10k_v1`，没有版本选择器；技术详情与下载保留真实身份。
旧 `v42_T2_K64_A0001` 的1024点权重、q、历史证据及独立研究CLI保留，
不进入当前Demo的活动清单。
这两版均为 repository-guided synthetic 代理，不是 10k 次 GMMNLSE 的模型。

从仓库根目录运行这一行；停止使用终端 Ctrl-C：

```sh
/opt/homebrew/Caskroom/miniforge/base/bin/conda run -n mamyshev-ml --no-capture-output python -m streamlit run demo/app.py --server.address 127.0.0.1 --server.headless true --browser.gatherUsageStats false
```

浏览器打开 `http://127.0.0.1:8501`。页面包括单点预测、1D/2D 预测、
四场景预测候选及MATLAB零额度待审批请求。输入/约束变化后须重新提交，
避免把旧结果当成新输入预测。下载只产生预测或零真实额度请求，不产生确认标签。
扫描上限 21/441 点，候选上限 4096；没有启动传播的界面按钮。

模型准备：保留 `demo/assets/models/` 的受信清单、原类、权重、q、域和聚合卡片。
该入口不依赖训练 CSV、历史数据库或 `reports/local`，也不会缺模型后自动训练。
仅使用这份已审阅来源的模型；哈希只能证明完整性，不能保证未知 joblib 安全。
依赖实测版本在 `demo/requirements.txt`；本批只在原环境新增 Streamlit 及必要传递依赖，
原数值库版本未变。没有验证新建环境或其他平台。

结果和实测检查见 [DEMO_10K_RELEASE_REPORT.md](DEMO_10K_RELEASE_REPORT.md)。
公开审查用[聚合指标](assets/demo10k/aggregate_metrics.json)、
[分版本表](assets/demo10k/model_comparison.md)不含训练/测试行。
两版测试集不同，不能当成严格规模消融；新 q 不借用旧 q，区间仍 limited。
真实参数 gate 仍依赖本机历史基准 MAT，公开 Demo 副本不携带它。
全量 10k GMMNLSE 扫描未运行；公开发布还须审批许可及已跟踪数据的处理。

## 以下为旧 closeout 与 V4.3 的 local-only 操作说明

下文“本批/当前收尾”指旧 closeout，保留原历史身份。
`reports/local` 路径仅供已有原始资产的本机用户使用，不是公开下载链接；
新用户应使用上面的 Demo 入口。旧 q 的说明只适用于 V4.2。

本项目目前可用于四输入 Mamyshev 设计的**仓库趋势引导合成基准代理预测**，并保留独立的 GMMNLSE 数据生成链路。V4.2 模型学到的是标明来源的合成标量响应，不能说已经学会完整真实 GMMNLSE 响应。当前收尾只演示已有输入、读取历史结果；新 MATLAB、标签、训练、校准、搜索额度都是 0。

所有相对路径从仓库根目录解释；本机 Python 固定使用下列命令前缀，不安装环境，也不使用裸 `python`/`pip`：

```sh
/opt/homebrew/Caskroom/miniforge/base/bin/conda run -n mamyshev-ml --no-capture-output python
```

本批实际命令、退出码、时间和允许的最多 9 个旧输入见 [MVP_CLOSEOUT_REPORT.md](MVP_CLOSEOUT_REPORT.md)。以下是各功能的具体用法说明，不构成新的计算授权；已有输出不得覆盖。V4.3 历史已执行的 9 点/81 点演示见 [应用报告](FROZEN_MODEL_APPLICATION_V4_3_REPORT.md)，不能算成本批再次执行。

## 输入、输出和来源

| 输入（顺序固定） | 单位 | 接口域 |
|---|---|---|
| `pump_power_W` | W | 2–10 |
| `filter_offset_nm` | nm | 2–16 |
| `filter2_bw_nm` | nm | 0.5–8 |
| `gain_length_m` | m | 1–8，严格 0.1 m 格点 |

四个字段必须完整，不能增加 `cw2`；`filter_offset_nm = 1040 - SF2中心波长[nm]`。未知字段、非有限数、域外值、不合法长度会拒绝，不裁剪或取整。上述是合成模型的探索域，**不是已验证激光运行域**。三段无源长度仍为 0.4/1.5/3.2 m，尾纤 0.2 m；H02 的 MFD/SR 约定仍未解决。

输出顺序是 `compressed_energy_nJ`、`compressed_duration_fs`、`compressed_peak_power_MW`，分别用 nJ、fs、MW。预测没有真实复场；原仓库记录为 `waveforms=null`，精简包仅输出标量和区间，不提供场文件。区间采用原 q，不重校准：历史联合覆盖总体 1936/2048，near_slice 216/256=84.375%，core 也没有逐组达到 95%；均标 `limited`，不能作为物理安全保证。

| 类型 | 意义 | 是否产生新真实传播 |
|---|---|---|
| synthetic `Evaluation` | 解析合成生成器已经评价过的设计，带配方/源身份 | 否；也不冒称 GMMNLSE 标签 |
| recorded `Evaluation` | 只读重放完全匹配源/数值/seed/观察协议/指标定义的历史结果 | 否 |
| surrogate `Prediction` | 显式冻结权重的预测，与 Evaluation 分表 | 否 |
| GMMNLSE `Evaluation` | 授权后经 supervisor 调真实四维生产入口的记录 | 是；本批 0 次 |

## Quick Start：纯预测和旧结果

仓库内显式选择 V4.2 的两个资产，旧默认模型不变：

```sh
mkdir reports/local/user_demo_001
/opt/homebrew/Caskroom/miniforge/base/bin/conda run -n mamyshev-ml --no-capture-output python scripts/v43_scan.py predict \
  --input reports/local/application_v4_3_001/demonstration/single_input.json \
  --model reports/local/accuracy_v4_2_001/release/model.joblib \
  --selection reports/local/accuracy_v4_2_001/release/selection.json \
  --out reports/local/user_demo_001/single_prediction.json
```

`mkdir` 若提示目录已存在，先审查已有文件，不能清空或覆盖。该旧输入是 `{"pump_power_W":4,"filter_offset_nm":10,"filter2_bw_nm":3,"gain_length_m":4}`。`predict --input` 也接受这些完整对象组成的 JSON 数组。加载器核对完整 release 依赖；只拷贝 `model.joblib` 到空目录不足以复现仓库内加载。必要权重、清单、源码或绑定证据缺失时拒绝加载。原仓库适配器的可选校准不可用时仍可保留点预测，区间为 `null` 并记录原因；本批独立包则把校准列为必需绑定资产。两者都不回退到 oracle、训练或 MATLAB。

历史候选结果直接读 [candidate_results.csv](../reports/local/application_v4_3_001/candidates/candidate_results.csv) 与 [candidate_summary.json](../reports/local/application_v4_3_001/candidates/candidate_summary.json)。其中 14.34 MW 等值是相应合成生成器评价，不是 MATLAB 或实验测量。64 逻辑事件对应 63 新设计和 1 缓存；模型方法事先已有 T2 的 1024 点，不能当作从零 8 次搜索。四场景的共享既有最好、加入新点后的最好都保留；不要将随机法较差的新点说成丢失原来的最优。

## CSV 批量预测、入库、导出

CSV 只含四列输入，不为新设计填三列输出。示例可复用 V4.3 曲线前三点：

```csv
pump_power_W,filter_offset_nm,filter2_bw_nm,gain_length_m
4,10,0.5,4
4,10,1.4,4
4,10,2.3,4
```

将其存到新的 `reports/local/user_demo_001/inputs.csv`。对应 `csv_spec.json` 的实际 schema：

```json
{"method":"csv","csv_path":"reports/local/user_demo_001/inputs.csv"}
```

```sh
/opt/homebrew/Caskroom/miniforge/base/bin/conda run -n mamyshev-ml --no-capture-output python scripts/v43_scan.py plan \
  --spec reports/local/user_demo_001/csv_spec.json --out reports/local/user_demo_001/csv_plan.json
/opt/homebrew/Caskroom/miniforge/base/bin/conda run -n mamyshev-ml --no-capture-output python scripts/v43_scan.py run \
  --plan reports/local/user_demo_001/csv_plan.json --db reports/local/user_demo_001/predictions.sqlite \
  --scan-id csv_demo --execute --max-new-attempts 3 --total-wall-s 30 \
  --stop reports/local/user_demo_001/STOP \
  --model reports/local/accuracy_v4_2_001/release/model.joblib \
  --selection reports/local/accuracy_v4_2_001/release/selection.json
/opt/homebrew/Caskroom/miniforge/base/bin/conda run -n mamyshev-ml --no-capture-output python scripts/v43_scan.py export \
  --db reports/local/user_demo_001/predictions.sqlite --scan-id csv_demo \
  --out reports/local/user_demo_001/export
```

输出 `results.csv` 和 `results.mat`；MAT 包含 X、Y、字段/单位与来源记录。这里 `--max-new-attempts` 是预测扫描预算，不是授权任何真实运行。`v43_scan.py` 固定使用显式冻结预测适配器，Evaluation 数不得增长。省略 `--execute` 时仅显示计划。CSV 计划先记录非法输入，执行时拒绝含非法项的计划；规范化 ID 去重，但行数不是独立新物理设计数。

## 1D/2D 预测图与只读回放

计划复用同一 `plan → run → export → plot` 链。已存在的精确 spec：

- `reports/local/application_v4_3_001/demonstration/curve/spec.json`：仅改变带宽的 9 点曲线。
- `reports/local/application_v4_3_001/demonstration/heatmap/spec.json`：offset×带宽的 9×9 热图，pump=4、gain=4 固定。

例如 1D spec 的键为 `{"axes":{"filter2_bw_nm":[0.5,1.4,2.3]},"fixed":{"pump_power_W":4,"filter_offset_nm":10,"gain_length_m":4}}`；2D 将 `filter_offset_nm` 移到 `axes`。同一参数不能既 fixed 又 varying。4D 格点计划用四轴且 `fixed={}`，不通过二维插值伪造新数据。

本批不重新预测历史 81 点。需要重新导出/绘图时先拷贝数据库，避免 CLI 的数据库初始化写入旧证据；以下仅消费已有结果：

```sh
cp -n reports/local/application_v4_3_001/demonstration/heatmap/predictions.sqlite reports/local/user_demo_001/heatmap_replay.sqlite
/opt/homebrew/Caskroom/miniforge/base/bin/conda run -n mamyshev-ml --no-capture-output python scripts/v43_scan.py export \
  --db reports/local/user_demo_001/heatmap_replay.sqlite --scan-id heatmap \
  --out reports/local/user_demo_001/heatmap_export
/opt/homebrew/Caskroom/miniforge/base/bin/conda run -n mamyshev-ml --no-capture-output python scripts/v43_scan.py plot \
  --db reports/local/user_demo_001/heatmap_replay.sqlite --scan-id heatmap \
  --plan reports/local/application_v4_3_001/demonstration/heatmap/plan.json \
  --out reports/local/user_demo_001/heatmap_plots
```

1D 回放相同，将来源 `heatmap` 改为 `curve`、`--scan-id curve`，使用新的目标目录。绘图只显示已有值，缺失不补 0，不插值算新标签；这些是预测图，不是传播波形。

## 读取真实历史 MAT 波形

下面只读取已完成 `config_waveform_001` 的原 final 与引用 MAT，不启动 MATLAB、传播或压缩优化：

```sh
/opt/homebrew/Caskroom/miniforge/base/bin/conda run -n mamyshev-ml --no-capture-output python scripts/v4_scan.py waveform \
  --final reports/local/phase2/config_waveform_validation_001/config_waveform_001/final_result.json \
  --out reports/local/user_demo_001/historical_waveform
```

输出 `waveform_read.json` 与 `saved_waveforms.png`。现有读取函数使用原复场样本、`fftshift(ifft)`、时间 ps、功率 W、能量 `trapz(power,t_ps)/1000` nJ；分开显示 output、尾纤后和压缩场。保存场积分不能无说明替换生产函数居中前的原能量标量。没有真实场的 Prediction/合成记录返回 `not_available`，不会生成假的时间/频域波形。

历史 `recorded` 路由需要 `--identity` 精确身份，并从指定数据库读已存在 Evaluation；它不允许用新版本名字覆盖旧数值版本。CLI 为 `scripts/v4_scan.py import-final --db ... --final ...` 与 `run --evaluator recorded --identity ...`，仅在新数据库中导入，不改原 final。回放不是 live，超时/失败的历史记录不能借导入变成物理成功。

## MATLAB 计划与真实运行的保留边界

真实四维入口为 `run_mamyshev_config(config,plot_on,diagnostic_options)`，复用原初始化及生产循环。上层通过 `GMMNLSEEvaluator → execute_authorized_design → supervisor → run_mamyshev_recorded → run_mamyshev_config`；父进程拥有 final，MATLAB 仅写 candidate。四输入数据生成、1D/2D/4D 格点、random/LHS 合法长度采样、逐点持久化、取消/续扫、数据库、CSV/MAT 导出功能均保留。

先生成计划不运行：

```sh
/opt/homebrew/Caskroom/miniforge/base/bin/conda run -n mamyshev-ml --no-capture-output python scripts/v4_scan.py plan \
  --spec reports/local/application_v4_3_001/demonstration/curve/spec.json \
  --out reports/local/user_demo_001/matlab_plan_only.json
```

计划默认 `max_new_real_attempts=0`。已有 `candidates/requests/matlab_requests.json` 是 12 条待审请求、11 个唯一设计；同目录 `zero_attempt_authorization.json` 的实际授权字段是 `max_new_attempts:0`，900 秒是 schema 草案值，不能据此启动 MATLAB。

未来真实运行必须单独批准具体 plan hash、允许设计 ID、次数、每次/累计墙钟和 batch 目录。真实 CLI `scripts/v4_scan.py run` 有 `--evaluator gmmnlse --authorization ... --batch-dir ... --execute --execute-real`；本指南不提供启用执行的一键命令。本批与当前新完整扫描的状态是 `not_run`，不是功能缺失。

STOP 分层保留：扫描 `--stop` 路径在点之间停止；真实 batch/授权目录的 `STOP` 阻止新点启动；活动的本次 run 目录 `STOP` 由 supervisor 轮询并清理所属进程组。不能杀用户其他 MATLAB。续扫只允许相同计划、来源身份、授权与累计预算；已完成点跳过，失败点不自动重试，未知 running 状态须独立确认归属。不能删锁或换 ID 绕过预算。

## 数据生成、训练和旧搜索：本批只看帮助/配置

下列帮助命令不会执行这些实验：

```sh
/opt/homebrew/Caskroom/miniforge/base/bin/conda run -n mamyshev-ml --no-capture-output python scripts/v4_scan.py run --help
/opt/homebrew/Caskroom/miniforge/base/bin/conda run -n mamyshev-ml --no-capture-output python scripts/run_v4_ml.py select --help
/opt/homebrew/Caskroom/miniforge/base/bin/conda run -n mamyshev-ml --no-capture-output python scripts/run_v4_search.py --help
```

合成数据生成是 `v4_scan.py` 的 `--evaluator synthetic` 路由；真实数据生成是上节的 GMMNLSE 路由。两者都需要另批明确的新评价预算。配置入口为 `mamyshev_accuracy_v4/configs/domain.json`、`accuracy_protocol.json`、`scenarios.json`；不要为复现演示修改配方、域或阈值。

旧训练入口 `run_v4_ml.py select --out ... --deadline-s ...` 会拟合；`evaluate` 还需要 `--authorize-final-evaluation`，本批禁止。V4.2 `run_v42.py` 的 freeze/compare/evaluate 是已经消费过的一次实验，不要对旧目录再执行。旧 `run_v4_search.py --package ... --output ... --wall-seconds ...` 会运行固定合成 GP/随机搜索，不能把它放在普通演示中；只有 `--help` 在本批允许。V4 历史 4 场景×3 种子×2 策略、每次 64 逻辑评价与 V4.3 单种子每方法每场景 8 次确认是不同实验。

## 验证范围和交付

本批有限演示结果以 [收尾报告](MVP_CLOSEOUT_REPORT.md)为准。V4.3 历史已实测单点/批量、9/81 点扫描、入库与 CSV/MAT 读回；V4 历史实测合成取消/续扫和真实 MAT 只读入口。完整新 GMMNLSE 扫描仍未运行，功能存在和历史单点返回不能代替物理/数值验证。

独立推理包为 `reports/local/mvp_closeout_001/inference_bundle.zip`，展开副本在同批 `inference_bundle/`。包内 `infer.py` 从自身目录定位所需资产，不使用原仓库绝对路径或继承的 `PYTHONPATH`。在另一个临时目录解压后，可用同一既有环境：

```sh
# 在解压后含 infer.py 的目录内；先核对包来源及本批清单。
env -u PYTHONPATH /opt/homebrew/Caskroom/miniforge/base/bin/conda run -n mamyshev-ml --no-capture-output python infer.py verify
env -u PYTHONPATH /opt/homebrew/Caskroom/miniforge/base/bin/conda run -n mamyshev-ml --no-capture-output python infer.py predict \
  --input inputs.json --output predictions.json
env -u PYTHONPATH /opt/homebrew/Caskroom/miniforge/base/bin/conda run -n mamyshev-ml --no-capture-output python infer.py predict \
  --input inputs.csv --output predictions.csv
```

`verify` 只核查，不加载模型或预测；`predict` 的 JSON 支持单对象或列表，CSV 标题必须恰好四字段；输出拒绝覆盖。输入采用上文已有默认/演示值。包内还包括原 `models_v4.py` 自定义类、模型、domain、calibration、schema、依赖版本、provenance 和 manifest，以及原选择/协议/评分/训练 ID/summary 的必要来源副本。builder 记录实际打包脚本，但重建包仍需要原仓库。

原模型字节和 q 保留，独立工件清单绑定实际执行代码；它不替代历史 release 的完整实验校验。精确版本核查和本机仓库外测试不是新建干净环境验证，也不意味着任意 sklearn 版本或跨平台可运行。原模型 SHA-256 必须是 `c236c2d2dd6cb5b59e32bd5ab4f8c3823f7fefc10d7571108a3d6339ee46b2e0`；哈希只是身份/完整性检查，不使陌生 pickle 成为可信资产。

证据对应关系见 [CLAIM_EVIDENCE.md](CLAIM_EVIDENCE.md)，归属待审见 [ATTRIBUTION_REVIEW.md](ATTRIBUTION_REVIEW.md)。`physical_state=undetermined`、`numerical_validation=not_verified`、`eligible_as_validated_training_truth=false` 保持；旧 Phase 2 深度物理验证仍 `deferred/in_progress`。本地收尾不等于 GitHub 已发布，发布与下一次实验都等待另行审核。
