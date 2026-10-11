# Demo 图表渲染最小修复

2026-10-10。结论：已确认并修复本应用与 Streamlit 前端的顶层数字 padding 不兼容；**代码与组件完成，等待用户现有浏览器刷新验证**。未将 AppTest 通过当作 Safari 页面已恢复。

## 证据与改动

- 本机 Darwin arm64；Streamlit **1.64.0**、Altair **6.3.0**、PyArrow **25.0.1**。安装的 Safari **26.6.2**、Chrome **154.0.8037.99**，均仅读取版本，未启动；不推断用户报错时使用的版本。
- 修复前两个模型 × 1D/2D × 三个目标的 **12 份实际 Streamlit protobuf `spec` 均有顶层 `padding: 16`**。1D 的实际页面范围为 BW **0.5–8 nm，9 点**，固定 P=4 W、offset=10 nm、L=4 m，目标包含 `compressed_peak_power_MW`；2D 增加 offset **2–16 nm，9 点**，共 81 条 Prediction。范围来自页面的 BOUNDS 与提交请求，没有根据截图猜测。
- 本地 `ArrowVegaLiteChart.CnqICc92.js` 含 `c.padding||={},f(c.padding.bottom)&&(c.padding.bottom=L)`；与 [Streamlit 1.64.0 源码第 213、290–295 行](https://raw.githubusercontent.com/streamlit/streamlit/1.64.0/frontend/lib/src/components/elements/ArrowVegaLiteChart/useVegaElementPreprocessor.ts)一致：JSON.parse 后保留正数 padding，再向数字写 bottom。这已确认本地实际传输值进入不兼容路径；[MDN](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Errors/Cant_assign_to_property)列出的 Safari primitive 属性赋值错误与用户文字吻合。未现场复现用户浏览器堆栈。
- [Vega-Lite 允许数字 padding](https://vega.github.io/vega-lite/docs/spec.html)，修复前 schema 验证也通过，故 schema 合法并不等于可经过此 Streamlit 前端预处理。

生产改动仅两处：

1. `demo/ui_charts.py:18` 新增顶层适配，`response_chart` 返回时调用；数字 16 转为同值四边对象。0 也显式转换；缺失字段保持缺失；合法完整/部分/空逐边对象保持内容；布尔、负值、非有限值、None、字符串等明确拒绝。不递归改 layer，不改数据、图例、tooltip、单位、曲线/rect、标记或排名。
2. `demo/app.py:439` 将当前请求的预测表及导出来源移出图表 try；构造失败仍显示错误并清除旧图表状态。完整请求身份与旧结果失效逻辑保留。此措施经 Python 构造异常注入验证，不能等同真实浏览器 JS 崩溃时的显示验收。

关键传输差异只有：

```diff
- "padding": 16
+ "padding": {"left": 16, "right": 16, "top": 16, "bottom": 16}
```

新增测试/运行文件：`tests/test_demo_chart_padding.py`、`scripts/check_demo_chart_render.py`、`scripts/run_demo_chart_budget.py`。最后一个仅给已有 `run_v4_budget.py` / `run_matlab_short.py` 绑定本批 180 秒总预算、30 秒单进程限制，没有另写监控器。说明文件为本报告；按工作约定追加 `EXECUTION_STATUS.md`，旧记录保留。

## 实际调用链与数值保留

1. 页面 `demo/app.py:391` → BOUNDS/控件 → `ui_logic.scan_plan` 构造 X-only 9/81 点请求；未读取训练标签。
2. `execute` → `frozen_prediction` → `demo_inference.predict` → catalog/manifest/资产哈希验证 → `load_model` → 已存 `LogSurrogate._x/predict`。使用已存 spline/scaler 与三路 log-target 回归系数，exp 返回 nJ/fs/MW；本批不 fit、不重新校准。
3. 已有 Prediction → `response_chart` → 顶层 padding 适配 → `st.vega_lite_chart` → protobuf spec/Arrow datasets → 浏览器预处理。图表构造不调用预测器、oracle 或 Evaluation。

实际加载权重（相对仓库根目录；完整身份见本地 `before/after/<model>/identity.json`）：

| 模型 ID | 文件 | SHA-256 |
|---|---|---|
| `v42_T2_K64_A0001`（默认，未变） | `demo/assets/models/v42/model.joblib` | `c236c2d2dd6cb5b59e32bd5ab4f8c3823f7fefc10d7571108a3d6339ee46b2e0` |
| `demo_10k_v1`（显式切换） | `demo/assets/models/demo_10k_v1/model.joblib` | `9885e8f258fa10de0a69844b70fa72242fcc64267d9db1e6c07dd4bd4609b6d0` |

比较规则在修复前固定：**整个 request、Prediction、CSV/JSON 字符串、Arrow 数据、summary 和最终 spec 精确相等，仅允许顶层 padding 表示不同**，未用舍入或放宽容差。修复后全部 12 组满足；数据与导出差异为零。实际独立基准坐标、最佳可行点、无可行点、固定值改变与旧请求清除均已核对。Prediction 仍不属于 Evaluation。

## 验证与成本

| 项目 | 结果 | 监控器计费墙钟（秒） |
|---|---|---:|
| 保护快照 | 已保存 | 1.456054 |
| 修复前 AppTest：默认/10k，各 6 个图表组合 | 12 份最终 spec 捕获成功，均数字 padding | 10.339502 / 10.084339 |
| 首次组件测试 discovery | **失败，未执行测试**：隔离工作目录下相对 tests 不可导入 | 0.107997 |
| 改为明确测试文件后，新增 5 个测试方法 | 全通过；含 6 个 1D/2D×目标 fixture 子案例 | 1.053534 |
| 修复后 AppTest：默认/10k | 各 6 个图表组合＋3 个故障/失效/无可行交互通过 | 11.101263 / 11.395457 |
| 直接相关既有回归 3 个方法 | rect 数值几何、约束/导出、原始数值比较通过 | 0.213401 |
| 保护核查及 diff 检查 | 全部受保护组一致；git diff --check 为 0 | 1.473127 |

累计 **47.224673 秒 / 180 秒**，包含失败尝试；最长进程 11.395457 秒，小于 30 秒。全部串行，数值线程上限 2。时间口径为既有监控器的 charged_s，非人工审查或 Conda 外层启动耗时。修复前/后矩阵是同一批预测的回归对照，不算独立设计、训练样本或新增物理验证。未跑全项目测试。

- 动态调用保护记录：fit/校准、oracle、Evaluation、MATLAB 均为 **0**；真实传播、BO、新标签为 0。权重、模型类、q、数据/配方、科学 Python、MATLAB/材料、扫描/数据库代码及全部旧本地证据的保护组哈希一致；分支、HEAD、暂存区未变。环境/site-packages/全局配置未修改。
- **JS 最小机制测试：not_run**，PATH 与常见本地目录未找到已有 Node；未安装。机制依据为实际 spec、本机 bundle 及官方源码，不声称运行过 JS 复现。
- **真实浏览器 1D/2D 绘制与控制台：not_run**。没有可靠有界的现成浏览器手段，未调用此前阻塞的 Safari/cua，未启动服务器或浏览器，未干预用户已有会话。[AppTest 是模拟应用组件工具](https://docs.streamlit.io/develop/api-reference/app-testing/st.testing.v1.apptest)，不能替代此项。
- AppTest 日志保留了原有 missing ScriptRunContext / widget 默认值与 session state 提示；不能把组件无异常理解为浏览器控制台无错误。

## 命令与本地证据

所有受控 Python 通过同一前缀执行：

```sh
/opt/homebrew/Caskroom/miniforge/base/bin/conda run -n mamyshev-ml --no-capture-output python scripts/run_demo_chart_budget.py --timeout-s 30 engineering LABEL -- COMMAND
```

实际 LABEL/COMMAND、开始结束时间、退出状态逐项保存在 `reports/local/demo_chart_fix_001/budget_ledger.json`，每项完整 stdout/runner 在 `budget/engineering/<LABEL>/`。命令分别为 `preservation.py start/check`、`scripts/check_demo_chart_render.py before/after <model_id> --output reports/local/demo_chart_fix_001`、失败的 `-m unittest discover -s tests -p test_demo_chart_padding.py -v`、`tests/test_demo_chart_padding.py -v`，以及 `tests/test_demo_ux.py` 指定的上述三个既有方法。没有删除失败日志。

新的 ignored 目录 `reports/local/demo_chart_fix_001/` 还保存：

- `before/`、`after/` 下的完整最终 spec、Arrow 数据读回、实际请求/预测/CSV/JSON、身份及断言结果；最初默认模型捕获因隔离 cwd 落在其进程子目录，原件保留，另复制到统一 before 位置，没有重跑或覆盖。
- `start_snapshot.json`、`preservation_check.json`、`runtime_metadata.json`、`installed_frontend_excerpt.txt`、`code_change.diff` 和仅本批使用的 `preservation.py`。

## 用户现有浏览器验证与停止

刷新现有页面，在 Parameter response 选择固定硬件任务，P=4、offset=10、L=4、BW 0.5–8、9 点、peak power，点击 Run prediction response，确认真实折线与红色基准/最佳可行标记出现；再选 2D，BW×offset=9×9，确认 rect 热图与控制台不再出现 readonly-property 错误。分别切换两个已有模型和三个目标，核对表格与 CSV/JSON 可下载；改变固定值后须重新提交才能显示结果。

若服务未运行，在仓库根目录使用原正常启动命令（本批没有执行）：

```sh
/opt/homebrew/Caskroom/miniforge/base/bin/conda run -n mamyshev-ml --no-capture-output python -m streamlit run demo/app.py
```

本批到此停止，等待实际浏览器审核；不提交/推送/上传，不扩展研究或下一 Phase。旧物理 Phase 2 保持 in_progress/deferred；physical_state=undetermined、numerical_validation=not_verified、eligible_as_validated_training_truth=false。
