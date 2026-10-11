# Demo 开发与单向部署导出

完整 Mamyshev 主项目是唯一维护来源。当前网页使用 `demo_10k_v1`，旧1024模型
仍用于历史研究复现；两者的权重、q、实验身份不会由界面或导出重写。
部署目录是按白名单生成的普通文件快照，不是另一个需要手工同步的源码仓库。

## 修改主项目

| 位置 | 维护内容 |
|---|---|
| `demo/app.py`、`demo/ui_logic.py`、`demo/ui_presentation.py` | 页面、会话、任务与展示格式 |
| `demo/ui_charts.py` | 1D及真实rect热图、标记与逐边对象padding |
| `demo/predict.py`、`src/mamyshev_ml/demo_inference.py` | 当前单10k推理、身份核验与CLI |
| `demo/assets/models/catalog.json` | 当前Demo活动清单；不修改历史release身份 |
| `scripts/export_demo.py`、`demo/deploy/` | 公开白名单、模板、依赖与导出转换 |
| `tests/test_demo_export.py`、当前Demo组件检查 | 导出边界及当前交互回归 |

不要从部署版复制整棵 `src/` 回主项目。主项目 `v4_evaluators.py`、`v4_scan.py`
以及数据库、真实授权、扫描/续扫和MATLAB路由保留完整能力；公开版只生成
推理和计划所需的纯函数，函数来源绑定主项目的实际源码。

所有新界面仍只接受当前模型：同模型基准/候选、全精度排名和导出、最多三条
零真实额度请求、旧结果失效、旧/未知会话拒绝、session级缓存均须保留。
图表失败时当前表格与下载仍可用。加载资产失败不得回退到旧模型、oracle或训练。

训练来源在 **Method & data / Data & validation** 集中说明：10,000个
repository-guided synthetic设计，不是GMMNLSE训练数据。模型卡/校准/原聚合
指标是冻结事实；新应用hash与原训练身份分别记录。不重评分held-out逐点数据。

## 先检查，再导出

从主项目根目录，使用已有环境。当前Demo逻辑组件检查入口为：

```sh
/opt/homebrew/Caskroom/miniforge/base/bin/conda run -n mamyshev-ml --no-capture-output python -B scripts/check_demo_ux_components.py
```

本批受控检查复用已有隔离监控，累计墙钟上限300秒、单进程60秒、串行、最多
两数值线程；AppTest是组件验证，不能代替用户浏览器视觉验收。详细的三方
预测/图表/导出对照、历史loader与完整后端组件检查以
[PROJECT_DEMO_SYNC_REPORT.md](PROJECT_DEMO_SYNC_REPORT.md)和本批私人日志为准。
不因这份维护说明而重复执行已完成实验或批准新的计算预算。

本批产物对应的导出命令（从主项目根目录先解析父目录的绝对路径）：

```sh
/opt/homebrew/Caskroom/miniforge/base/bin/conda run -n mamyshev-ml --no-capture-output python -B scripts/export_demo.py --output "$(cd .. && pwd)/Mamyshev_Demo_Deploy_synced_001"
```

传入的路径不能含字面 `..`，且目标必须不存在；命令成功后保留该快照，
不能清空、覆盖或换编号绕过失败。
未来新版本应明确选择新目的目录。导出拒绝路径逃逸、软链接和未声明文件，
模型缺项明确报错；不自动下载、训练、读取标签或访问旧部署目录。

导出输入来自本项目正常源码中的profile/模板和受信资产，不依赖 `reports/local/`、
训练CSV、历史DB或Phase 1 MAT。公开依赖来自 `demo/deploy/` 的独立profile，
不将完整科研环境打包进副本，也不覆盖主项目的依赖声明。

`deploy_manifest.json` 绑定实际公开文件、源码内容和模型身份。`source_commit`
配合dirty事实与源文件hash说明当前工作树，不把HEAD当作所有未提交代码的身份。
时间与本机路径留在私人receipt；公开清单不含原始设计行或完整工作区差异。
新manifest独立审核，原29文件快照和原批准范围不被改写或自动沿用。

## 运行入口与发布边界

主项目根目录可启动完整项目中的纯预测Demo：

```sh
/opt/homebrew/Caskroom/miniforge/base/bin/conda run -n mamyshev-ml --no-capture-output python -m streamlit run demo/app.py --server.address 127.0.0.1 --server.headless true --browser.gatherUsageStats false
```

新导出副本先进入其目录，再用同一已有环境：

```sh
cd ../Mamyshev_Demo_Deploy_synced_001
/opt/homebrew/Caskroom/miniforge/base/bin/conda run -n mamyshev-ml --no-capture-output python -m streamlit run demo/app.py --server.address 127.0.0.1 --server.headless true --browser.gatherUsageStats false
```

这两个命令均只启动网页，停止用所属终端的Ctrl-C；本批没有启动服务或浏览器。
主项目保留完整后端，轻量副本不具备真实传播依赖。二者的网页都不提供传播按钮。
真实四参数/扫描/取消/续扫/存储/CSV与MAT导出的原操作说明继续见
[USER_GUIDE_ZH.md](USER_GUIDE_ZH.md)，执行仍需要独立的具体授权和预算。

固定流程为 **修改主项目 → 受影响测试 → 白名单导出 → 审核新manifest → 单独批准后发布**。
公开仓库和Live Demo地址保持pending，未创建的地址不作为链接提供。
许可、真实浏览器、Cloud构建及匿名访问未由组件测试批准；不自动init、add、commit、
push或部署。H02、独立数值验证和真实训练资格等科学问题仍按原报告保持未完成。
