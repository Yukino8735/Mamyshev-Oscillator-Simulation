# 主项目与单 10k Demo 单向导出报告

2026-10-11。本批执行 `CODEX_PROJECT_DEMO_SYNC_PROMPT.md`。完整主项目继续作为唯一维护来源；已实际生成新的独立普通文件快照 `Mamyshev_Demo_Deploy_synced_001`，旧 `Mamyshev_Demo_Deploy` 只读保留。没有训练、取标、校准、oracle、MATLAB、传播、BO、浏览器/服务、Git写操作或部署。

## 起点与本批实际变更

本地分支 `feature/mamyshev-ml-mvp`，HEAD `489bf4242f9b5266d47f8892840a24af66931ff0`。开始时已经存在大量未提交工作；完整起点清单和实际拟改四份文档的原件保存于 `reports/local/project_demo_sync_001/`。不把相对HEAD的全部差异归成本批。

读取实际文件发现：此前 `demo_main_sync_001` 已把单10k通用界面合回主项目。当前app、UI逻辑/格式器、推理CLI/loader、活动catalog、图表与参考相同。本批复用这些已有改动，没有再次覆盖。历史 `demo/source_version.json` 和 `DEMO_MAIN_SYNC_REPORT.md` 仍记录原迁移身份，新导出身份由新manifest记录。

| 参考位置 | 主项目与新导出的处理 |
|---|---|
| `demo/app.py`、`ui_logic.py`、`ui_charts.py`、`ui_presentation.py`、`predict.py` | 主项目已有同字节通用版本；新副本按白名单复制 |
| `src/mamyshev_ml/demo_inference.py`、活动catalog、八个10k资产、scenarios、domain、plan summary | 主项目已有受信版本；保持字节和当前单模型限制 |
| `checks/presentation_smoke.py` | 保留主项目已有检查器：允许完整研究库保留旧资产目录，同时拒绝旧活动ID；新副本复制此版本 |
| 精简 `v4_evaluators.py`、`v4_scan.py` | 不复制回主项目；导出器从完整源码提取六个纯函数、所需常量与导入 |
| 轻量 `__init__.py`、README、DEPLOYMENT、THIRD_PARTY_NOTICES、.gitignore | 新增主项目公开模板，仅用于生成副本；不替换完整科研包和依赖 |
| requirements、Streamlit配置 | 从主项目公开profile生成；保留已验证的九项固定版本，无安装升级 |
| 旧V4.2模型、研究loader、MATLAB/扫描/DB/续扫/历史报告 | 原位置保留，不进入部署白名单 |

逐文件起点映射：`file_mapping_before.json`；导出源到载荷映射及实际源hash：新manifest的 `source_files`、`files[].source/transform`。当前catalog此前已单模型化；原双模型catalog仍保存在 `reports/local/demo_main_sync_001/before/demo/assets/models/catalog.json`，本批没有改写。历史可信release加载不依赖当前Demo catalog，未关闭其哈希核验。

新增 `scripts/export_demo.py`、`demo/deploy/profile.json`、五份模板及 `tests/test_demo_export.py`。仅修改README、USER_GUIDE_ZH、SCOPE、EXECUTION_STATUS的当前说明，新增本报告和DEMO_DEVELOPMENT；旧科学章节及失败记录保留。没有改动主项目的生产数值、完整Python后端、环境或冻结模型。

## 导出机制与独立性

profile版本为 `single_10k_from_main_001`。显式名单包含19个复制载荷、5个模板载荷、2个profile生成载荷、2个AST生成薄模块，加manifest共29文件。导出不反序列化模型，不执行被解析的完整后端。

六个权威函数是 `canonical/digest/validate_design/design_id/make_plan/verify_plan`。导出核对选中节点AST、全局依赖和导入白名单；新增未声明依赖会拒绝。旧参考薄 `v4_scan.py` 的CSV分支使用 `Path` 却没有导入，本次生成器从完整源码自动带上该依赖；CSV人工输入语义回归已覆盖。旧参考没有被修补或改写。

校验全部必要源文件、冻结内层manifest、权重、类、catalog、域及绑定依赖后才创建目录；缺项一起列出，拒绝覆盖、路径逃逸、软链接、未声明输出和模型篡改。不维护第二套手写算法、不复制完整src、.git、引擎、研究数据或日志。

实际导出通过读取审计执行原CLI：仅28个声明源文件被读取，旧参考及主项目其他数据路径均被拒绝访问，实际拒绝事件为0。七个导出测试还使用只有这些声明文件的临时来源目录，两个临时导出的所有字节（含manifest）一致；没有旧副本、私人模板、训练CSV、历史DB或Phase1 MAT。临时无Git来源的commit/dirty为null；本次实际来源则记录真实HEAD、dirty=true及逐项源码hash，不伪称整个工作树等于HEAD。

运行新副本时使用 `-I -B`、独立cwd、清除PYTHONPATH和旧有读取/调用审计。加载路径来自新副本；主项目读取尝试和fit/oracle/Evaluation/MATLAB计数均为0。正常环境包来自既有mamyshev-ml；没有新环境或跨平台验证。

## 数值、图表与交互结果

比较规则在运行前沿用固定 `atol=rtol=1e-10`，先断言有限及形状一致；没有调整容差。参考实际捕获后，主项目和新副本分别与其对照。

| 项目 | 参考→主项目 | 参考→新导出 |
|---|---:|---:|
| 默认(4,10,3,4)输入/三目标/区间最大绝对差 | 0 | 0 |
| 1D带宽9点输入/三目标/区间最大绝对差 | 0 | 0 |
| 2D offset×带宽81点输入/三目标/区间最大绝对差 | 0 | 0 |
| 两个当前CLI默认输出最大绝对差 | 0 | 0 |
| 六组实际Streamlit spec/Arrow数据、rect几何、坐标、单位、标记、tooltip、CSV/JSON | 完全一致 | 完全一致 |
| q及全部八个模型资产 | 相同 | 相同 |

预测记录中的输入順序、单位、约束旗标、来源及权限一起比较；ranked基准/最佳预测可行标记与图表严格一致。实际工作台另检验512个X-only预测候选、同模型基准/候选、未舍入差值和排名、最多3请求、零真实额度和null真实目标；这是预测组件测试，不是新增Evaluation或训练样本。导出的新外层manifest、源hash、模板文本及生成薄模块身份允许变化；原内层模型和数值事实不变。

主项目与新副本均通过：没有旧版本下拉框，默认/示例为10k；旧ID/旧会话明确拒绝并需显式重置；参数/约束变化后旧结果失效；零可行点不造候选；图表错误仍保留当前表格和下载；无效轴请求清除旧图；padding始终为四边均16的对象。两会话状态及session缓存隔离通过，仅测试框架为AppTest分配不同session ID；没有替换真实模型或缓存实现。

来源仍集中显示于 **Method & data → Data & validation**：10,000 repository-guided synthetic designs，不冒充GMMNLSE训练。下载保留真实model_id、来源、区间、零执行权限和null真实目标；原聚合metrics/model_card未经重评分或改写。

冻结证据：

| 对象 | SHA-256或实值 |
|---|---|
| 旧29文件参考manifest | `cbf2cb69f1e0aa9d7bbf03e9dacc3fa8f0c57d42c2c4f127e583118963597f93` |
| 10k权重 | `9885e8f258fa10de0a69844b70fa72242fcc64267d9db1e6c07dd4bd4609b6d0` |
| 自定义类 | `46f9779b878d195b601930446cce3ec5335f694ef219f28c2ae728a353590b11` |
| 图表源码 | `9e905a560b5218408078f8b9a48a89a1104102509930bbc2280d0161bfd86415` |
| 从受信校准文件读取的q | `0.0030957846673075884` |

## 完整后端、历史重载与受控成本

15个既有方法通过：`test_demo10k_plan.py`的6项、`test_v4_data_chain.py`选定8项、`test_v43_adapter.py`的Prediction DB/CSV/MAT回读1项。覆盖小型X-only与1D计划、4D random/LHS计划、输入与单位拒绝、Prediction/Evaluation隔离、零真实授权、candidate/final/runner身份拒绝、失败记录和更紧预算拒绝；另由Demo组件检验2D预测请求。4D grid分支静态保留，本批未单独执行该分支。没有执行整套会调用合成标签器的旧测试，没有生成完整10k计划。

原 `v43_adapter → v42_release` 可信链单独进程重载一个已存默认输入，三目标及区间最大绝对差均为0，身份/Prediction ID不变。旧模型仍为 `v42_T2_K64_A0001`，权重 `c236c2d2dd6cb5b59e32bd5ab4f8c3823f7fefc10d7571108a3d6339ee46b2e0`，旧q=`0.003266551289750619`。该loader依原规则读取训练/dev制品及排除ID等文件以核验冻结hash，并读取已有聚合指标；没有重评分独立test Y，也没有修改manifest或把该路径包装成无需历史资产。部署导出不依赖这些文件，与历史重载是不同契约。

用已有 `three_saved_records.sqlite` 三条同来源记录的只读副本检验：取消后1条完成→关闭并重开DB→累计3条完成→第三次调用新增0条；更改累计预算被拒绝，逐个来源身份字段不符返回not_available/null。CSV/MAT回读最大差0，原DB hash不变。这是Recorded缓存重放，不是3个新标签、3次物理运行或场checkpoint恢复。人工fixture也不计为科学设计。

7个新导出单元方法、15个既有后端方法和上述有限历史/Recorded检查均通过；主项目与新副本重复执行的AppTest属于两种运行上下文，不能相加宣称更多独立科研验证。完整MATLAB、真实10k扫描、训练、独立数值/随机收敛及全仓库历史测试未运行。

开始时已保存7组内容清单：模型/资产22文件、生产/材料859文件、旧本地证据2186文件、数据/recipe/科研Python298文件，另有全部模型与完整后端重叠分组。结束保全确认7组内容、分支、HEAD和暂存差异全部不变，原有文件仅本批四份授权文档改变；详见 `preservation_check.json`、`actual_document_changes.diff`。重叠组不累加为独立文件数。新导出测试后全部载荷及28个源身份仍匹配；旧29文件manifest和载荷保持原样，`git diff --check`通过。

受控墙钟合计 **64.973627 / 300秒**，最大单次9.465165秒，所有任务串行。计入两次失败、参考捕获、重复运行上下文、导出和首尾保全；不是MATLAB耗时或科学加速比。

| 监控label | 检查范围 | 结果 | 外部墙钟秒 |
|---|---|---|---:|
| `preserve_start` | 起点保全 | completed | 1.882087 |
| `reference_capture` | 参考预测/六图捕获 | completed | 9.465165 |
| `main_inference` | 主项目推理/CLI | completed | 2.824115 |
| `main_charts` | 主项目图表/故障路径 | completed | 8.771274 |
| `main_ui` | 主项目工作台 | completed | 7.255503 |
| `export_components` | 启动语法失败（未进入测试体） | failed | 0.104790 |
| `export_components_corrected_command` | 发现路径失败（未进入测试体） | failed | 0.102339 |
| `export_components_script` | 7个新导出单元方法 | completed | 0.317104 |
| `actual_export` | 实际白名单导出/读取审计 | completed | 0.106762 |
| `main_session` | 主项目会话隔离 | completed | 4.786453 |
| `export_inference` | 新副本推理/CLI | completed | 2.726749 |
| `export_charts` | 新副本图表/故障路径 | completed | 8.376772 |
| `export_ui` | 新副本工作台 | completed | 7.180994 |
| `export_session` | 新副本会话隔离 | completed | 4.373117 |
| `backend_units` | 15个既有后端方法 | completed | 1.678892 |
| `backend_history` | 1个旧模型已存输入 | completed | 2.720155 |
| `backend_replay` | 3条已有记录重放 | completed | 0.522801 |
| `preserve_end` | 结束保全/manifest/git diff检查 | completed | 1.778556 |

失败保留：第一次给监控器传 `-B -m`，旧监控器把 `-B` 解析成脚本路径；第二次用相对 `tests`，而旧监控器cwd为隔离日志目录，unittest发现阶段失败。分别耗时0.104790/0.102339秒，均未进入测试体。修正为绝对解析的 `tests/test_demo_export.py -v` 后7项通过；没有修改测试断言、生产代码或放宽容差来消除失败。每次原始stdout/runner均保留。

## 实际命令与证据

所有Python均通过指定Miniforge绝对路径和mamyshev-ml。预算复用 `scripts/run_v4_budget.py` 与已有 `tests/run_matlab_short.py:run_isolated`，本批私人适配仅设置300秒总量/60秒单次，串行并限制最多两数值线程。完整argv、stdout、退出码、清理确认及耗时见 `reports/local/project_demo_sync_001/budget_ledger.json` 和 `budget/engineering/*/`。

实际导出在该监控器下由私人 `guard_export.py` 加装只读审计，以runpy执行以下真实CLI及参数（不是第二个导出器）：

```sh
/opt/homebrew/Caskroom/miniforge/base/bin/conda run -n mamyshev-ml --no-capture-output python scripts/export_demo.py --output "$(cd .. && pwd)/Mamyshev_Demo_Deploy_synced_001"
```

该目录现已存在，不能再次运行此命令覆盖。本批主要证据是 `export_receipt.json`、`reference_capture/evidence/references/reference.json`、`main_{inference,charts,ui,session}/`、`export_{inference,charts,ui,session}/`，以及本批后端回归与保全记录。所有详细路径/原件/命令留私人目录，不装进公开副本。

主项目根目录启动Demo的命令（本批未启动）：

```sh
/opt/homebrew/Caskroom/miniforge/base/bin/conda run -n mamyshev-ml --no-capture-output python -m streamlit run demo/app.py --server.address 127.0.0.1 --server.headless true --browser.gatherUsageStats false
```

新副本根目录使用同一启动命令；两者都只提供预测及请求准备，没有在线传播按钮。完整MATLAB受控执行仍走主项目原CLI。后续维护见 [DEMO_DEVELOPMENT.md](DEMO_DEVELOPMENT.md)：修改主项目→测试→白名单导出→审核新manifest→单独批准后发布。

浏览器视觉、JavaScript控制台、Cloud/Linux构建、匿名访问未执行；AppTest仅证明组件行为。用户可按新DEPLOYMENT逐项检查示例/基准、1D/2D、Method & data及下载。没有公开App URL；旧29文件批准不自动覆盖新manifest。Phase2深度物理验证仍为in_progress/deferred，physical_state=undetermined、numerical_validation=not_verified、eligible_as_validated_training_truth=false；H02、随机鲁棒性和已记录的真实training_records资格缺口不在本批修复。

## Git范围：仅清单，未暂存或发布

主项目本批拟提交的具体路径（不是当前整个dirty工作树）：

| 路径 | 原因 |
|---|---|
| `scripts/export_demo.py` | 唯一可复用白名单导出入口 |
| `demo/deploy/profile.json` | 源/载荷、冻结身份、依赖和转换规则 |
| `demo/deploy/templates/README.md` | 轻量副本用途与数据边界 |
| `demo/deploy/templates/DEPLOYMENT.md` | 独立副本运行/人工检查说明 |
| `demo/deploy/templates/THIRD_PARTY_NOTICES.md` | 保留来源、权利未决项 |
| `demo/deploy/templates/gitignore.txt` | 公开快照排除规则 |
| `demo/deploy/templates/package_init.py` | 轻量包初始化，不覆盖主项目 |
| `tests/test_demo_export.py` | 七个导出回归方法 |
| `README.md`、`docs/USER_GUIDE_ZH.md` | 完整主项目定位及单向导出命令 |
| `docs/SCOPE.md`、`docs/EXECUTION_STATUS.md` | 本批范围/状态；保留旧阶段 |
| `docs/DEMO_DEVELOPMENT.md`、`docs/PROJECT_DEMO_SYNC_REPORT.md` | 维护流程与实际交付证据 |

上述14个路径为本批范围。运行所依赖但此前已存在的未提交app、推理、资产和科研模块，不自动并入本批提交；将来主仓库发布必须另审完整依赖范围，不能仅提交导出器后宣称是完整科研发布。

新副本拟提交精确白名单、大小及hash如下。外层manifest另有自身SHA，未伪造递归自hash。没有创建该副本的Git仓库。

快照：`Mamyshev_Demo_Deploy_synced_001`。**29文件，677,721字节**。

外部manifest SHA-256：`519bf7b14f22f0e6e00efda775c47c9c8cca24663ac54d778ec9d36d2b5c6547`。

| 相对路径 | 字节 | SHA-256 |
|---|---:|---|
| `.gitignore` | 121 | `23d1d4223d9c1db0ff48ba90610e8de3d1585f50488ae1e1a2b380817ce1fee1` |
| `.streamlit/config.toml` | 68 | `963c54d6732f16c775f41197f2119e653ff88383a2a2d84673d7e876621af758` |
| `DEPLOYMENT.md` | 3934 | `be545e434989bb2f2b40543bb4906564145f059034dcd3cdc0a7e502b6017a41` |
| `README.md` | 3345 | `c6f849e02e7d2de272a03c809b27a3eee852174d31b716ddd9d857c7e1217f14` |
| `THIRD_PARTY_NOTICES.md` | 2594 | `432d1b2d3d961247ecf05a2d7f615826ca48f3d09fd61acda48d03a1cf43706a` |
| `checks/presentation_smoke.py` | 25524 | `af6a7e7a0150b3e34a9aba2b93b39a84579ea6e456e5c52b49a3f70545cf88cd` |
| `demo/app.py` | 29549 | `7f096ce1efa6e36a879a1cf654d3a8be7a9ba147552aad1e62dc3f7c038e6c5d` |
| `demo/assets/matlab_plan_summary.json` | 852 | `4e836ff2291c16806aa1c08d8b753015fe7cddfabc503bd7c43da192b4cc05ba` |
| `demo/assets/models/catalog.json` | 515 | `d49e4171b29d0fa6c39a15968994b9753da42a9d17414ca43ec1e783c00aa78e` |
| `demo/assets/models/demo_10k_v1/calibration.json` | 262 | `48799a2dde0cf0c03b7c216b03f4f1418011fdb79a3f7aa308cbbf28ca4873f8` |
| `demo/assets/models/demo_10k_v1/dependencies.json` | 256 | `9777a503430f8b5c37587b17ffec3b9c8aeadf7ad43591fa32489e645234c08b` |
| `demo/assets/models/demo_10k_v1/domain.json` | 700 | `66802d60ab841a6ca5f7530147c80cbd465936ccef8b82b411f38d7a126ba668` |
| `demo/assets/models/demo_10k_v1/manifest.json` | 861 | `9908e22c30358d51f0f8993a39da5c2e8fbc76710fbf08213ab7199e1ae9ce7c` |
| `demo/assets/models/demo_10k_v1/metrics.json` | 77644 | `68549e3151386270a7965e92e659ea139b6fa1dd3038580e9e1c213935863501` |
| `demo/assets/models/demo_10k_v1/model.joblib` | 461433 | `9885e8f258fa10de0a69844b70fa72242fcc64267d9db1e6c07dd4bd4609b6d0` |
| `demo/assets/models/demo_10k_v1/model_card.json` | 2838 | `21c17bff0125f0b2128325f2e452fc5f47e4d937f2ad5cebcdc48b873268d6e0` |
| `demo/assets/models/demo_10k_v1/models_v4.py` | 2991 | `46f9779b878d195b601930446cce3ec5335f694ef219f28c2ae728a353590b11` |
| `demo/assets/scenarios.json` | 1741 | `b14b48526a186871cd9826ebf4f5dc09c89a5fda259373766b5ac186c97388eb` |
| `demo/predict.py` | 1023 | `b2379d3f046972021f99c9bf6793d8d6979d60b3cdf8db9e09871946b1c83946` |
| `demo/ui_charts.py` | 11321 | `9e905a560b5218408078f8b9a48a89a1104102509930bbc2280d0161bfd86415` |
| `demo/ui_logic.py` | 16281 | `b6a9745aef5b414253436a4bdd8e8fe734dd5d4968e701709c16b58e4a87b82a` |
| `demo/ui_presentation.py` | 3119 | `bac8b6e63974e1b1b0586a33c12be4650b32202da3759ac1a2029917d96d05a2` |
| `deploy_manifest.json` | 13516 | `519bf7b14f22f0e6e00efda775c47c9c8cca24663ac54d778ec9d36d2b5c6547` |
| `mamyshev_accuracy_v4/configs/domain.json` | 700 | `66802d60ab841a6ca5f7530147c80cbd465936ccef8b82b411f38d7a126ba668` |
| `requirements.txt` | 144 | `a86790d4d6f4eb2af967ea412a20ad51a6274184d79609d8f173b557fd4b2b38` |
| `src/mamyshev_ml/__init__.py` | 75 | `743f8ec5587975790330d1d33e4502f25f992c043b92e5dc5233249772656c69` |
| `src/mamyshev_ml/demo_inference.py` | 10143 | `86e68c07c87d6fede870b596f2a4ddd983209d0040b51b3e917232421f7ccffb` |
| `src/mamyshev_ml/v4_evaluators.py` | 1658 | `144b73498d7ee90e20ffaf229ca50cd36ecd96364bad2ec727286f7b127902e7` |
| `src/mamyshev_ml/v4_scan.py` | 4513 | `7c9ac779365499b1ccb578dff6160e925e8bc82f5202e56bdc25c556497c97ad` |

仅本地保留：`reports/local/project_demo_sync_001/`及所有旧 `reports/local/`、`data/`、`results/`、`archive/`、研究CSV/SQLite/MAT/JSONL、逐点预测、波形、原训练/测试和完整10k计划、旧V4.2研究权重/校准/冻结包。主项目这些文件没有被删除；“排除部署”不等于取消Git跟踪。

待审批：新manifest列出的项目代码、10k权重/自定义类及必要资产的公开权利，第三方依赖许可和已有pending-review元数据；原仓库已跟踪历史数据及其历史处理方案仍沿用既有 `GIT_RELEASE_PLAN.md`/归属审核未决项。本批没有取消跟踪、重写历史、授予统一许可或重新展开引擎许可调查。旧模型及旧候选成绩未移植为10k新成绩。完成后停止，等待审核。
