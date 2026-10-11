# 完整管道限定检查与双仓库代码发布

2026-10-11。执行依据为本次 full-pipeline publish 指令及用户随后明确确认：
**发布自有管道代码，MATLAB live 路径标注 blocked；Cornell 文件不作新增或更新发布。**
此范围不等于“公开 clone 后全部 MATLAB 无条件可运行”。原历史审批文字保持原样；
当前授权只适用于本次审核过的代码/最小模型资产，不包括数据或 Cloud 部署。

## 实际发布结果（不是准备清单）

| 仓库 | 实际分支/结果 | 已重新读取的源码发布commit |
|---|---|---|
| [主项目](https://github.com/Yukino8735/Mamyshev-Oscillator-Simulation) | 功能分支已推送；main普通快进成功；PR无 | `e2926392f8a772f138b02a97cf5ce3b525fb7bf6` |
| [Demo](https://github.com/Yukino8735/mamyshev-design-explorer) | 新公开仓库main已创建并推送；PR无 | `c9ac9bfafaaf6f1481b22749a82bd6f918d7be6b` |

GitHub API实际main/功能分支SHA均与本地一致。主仓库全部1274个blob、Demo全部29个blob
与本地提交树一致；又下载核对了主README/训练CLI/训练桥/导出器及Demo README/app/
预测入口/manifest的内容。主仓库从旧远程基线到发布commit没有修改data/results/archive/
simulation_engine/third_party；Demo没有任何额外文件或主.git历史。不是仅以push退出0判断。

这次附记与README双向链接作为一次独立**仅文档补记**提交，保持上述源码发布commit
不变。补记自身最终commit、两分支最终SHA以及再次远程核查记入本地
`reports/local/full_pipeline_publish_001/publication_receipt.json`，避免自身hash循环。
部署副本不因报告自身变化重新导出，原manifest的导出时身份与dirty说明保持真实。

截至首次完整远程读回，受控Python计算计费 **15.523827秒**，
Git/网络步骤计费 **20.603880秒**；每个进程均远低于120秒。
这些为现有监控器子进程外部墙钟，不含人工/工具等待和Conda外层启动；最终文档、
保存检查及远程复核的额外计费并入最终publication_receipt/budget_ledger，全部失败亦计入。
唯一失败状态是开始时查询尚不存在Demo仓库的预期“repository not found”；没有测试、
拟合、提交或推送失败。没有自动重试计算或重新fit。

公开代码已完成，浏览器视觉仍pending，Cloud未开始，网站没有已确认Live URL。
本批在文档补记与最终保存检查完成后停止。

## 实际功能与证据

| 环节 | 实际入口/源码 | 本批证据与边界 |
|---|---|---|
| 四维真实生产 | `run_mamyshev_config.m` → `run_mamyshev.m`；泵、offset、带宽、增益长度接入同一循环；尾纤和同次压缩 | 静态核对；复用 `config_waveform_001` 的6圈成功历史；本批 MATLAB0 |
| 计划/调度 | `scripts/v4_scan.py`、`src/mamyshev_ml/v4_scan.py`；1D/2D/4D grid、LHS/random、CSV；`demo10k_plan.py` | 已有10k计划只读确认10000行、零真实额度；相关组件复用/执行，无新标签 |
| 保存/续扫/DB | `V4Store` 分开 Evaluation、Prediction、attempt；STOP、累积预算、已完成点跳过；CSV/MAT及波形引用 | 15项相关组件通过；未改的取消→续扫→再调用0新尝试链复用上一批3条已存记录检查 |
| 真实标签进口 | `v4_evaluators.import_safe_result` → DB → 新 `v4_training.training_records/read_records` | 原 parent final、request、runner、artifact/单位复核；实际1条成功记录导出并重读 |
| 特征/训练 | `scripts/train_surrogate.py` 的 identities/export/split/fit/predict；新薄适配 `v4_training.py` | 干净代码副本，显式小数据，单次真实临时fit/save/load/predict通过 |
| 特征细节 | 原 `reference/models_v4.py::LogSurrogate` | 四输入域缩放→样条/交互特征→训练集scaler→正目标log Ridge→exp；329维；没有目标/source/split泄漏到X |
| 冻结Demo | `demo/app.py`、`demo/predict.py`、`demo_inference.py` | 仅demo_10k_v1，额外1点隔离推理差0；上批9/81点、图表及会话证据按相同源码复用 |
| 轻量导出 | `scripts/export_demo.py` + `demo/deploy/profile.json` | 只读白名单读取；新29文件副本，无完整训练/扫描/物理后端复制 |

源位置：四维入口 `code/ring_cavity/scans/run_mamyshev_config.m:1`；生产参数
`run_mamyshev.m:85,113,152,167–184`，传播241–247，尾纤390–402，压缩404–410，
波形463–467；计划/调度 `v4_scan.py:16–71,94–186`；实际final导入
`v4_evaluators.py:141–233`；DB与导出 `v4_store.py:45–95,109–131`。
这些是实际源检查位置，不代表本批执行过传播。

## 最小修复与资格语义

新增 `src/mamyshev_ml/v4_training.py`、`scripts/train_surrogate.py`、
`tests/test_v4_training.py` 和两个小型X-only示例。没有改写冻结的
`v4_store.py`、`v4_evaluators.py` 或原模型类；旧底层 training_records
只是筛选器，不能单独作为已核验训练资格。正常新CLI统一走限定适配器。

- 必须选择完全一致的source/backend/numerical_version/seed/observation_protocol/
  metric_definition；不默认混合synthetic和solver。
- completed真实记录通过原final重新验证；Prediction、失败/超时、缺失final、
  非有限/null目标、单位或来源冲突被拒绝/排除并记录原因。
- E/τ/peak均为压缩分析平面，不拿上游能量补缺。solver-emulation资格仅代表
  可以拟合此求解器输出，不改变原undetermined/not_verified/false科学标记。
- CSV保留完整record_json和证据引用，并核对便捷标量列；与旧scan平铺results.csv
  不同。真实CSV读取仍要求显式原始final及其证据存在，不虚构便携认证。
- 分组split拒绝同设计跨角色；一条真实数据不足以训练/评分。新模型记录本次
  来源、split、样本数、特征/类/权重身份；不借用10k的q或性能。

实际真实记录：`config_waveform_001`，X=[4,10,3,4]；按现有导入器得到
Y=[128.66941786965054 nJ, 29.84941905629446 fs, 2.8509406179669123 MW]。
原final SHA-256=`4cb2cd8499a1a5057dc85b52e162436853867cf40f779967ad6e54dfa06263cd`。
这是一条历史真实记录的重读，不是新增物理运行或新独立设计。

## 唯一临时拟合与测试

从已有10k批次的训练角色只选128条，开发角色只选16条；144个不同设计。
未读取原held-out标签，未生成新synthetic/GMMNLSE标签。实际fit仍保持原train/dev
分离；通用split命令另作接口检查，不用其重新分配的角色覆盖本次原角色。

干净白名单源码副本不含reports/local、完整数据或原工作区源码回退，数据路径
显式提供；运行时审计拒绝原源码、oracle/实验模块与子进程启动。一次
`release-smoke`三目标fit：329特征、scaler.n_samples_seen_=128，训练均值检查通过；
权重保存/重载后预测最大差0，三目标有限且为正。开发误差仅留本地检查记录，
没有新科学精度结论、正式模型选择或校准。独立test角色为空，明确不评分。

| 本批实际检查 | 结果 | 外部计费秒 |
|---|---|---:|
| 训练桥10个人工组件方法 | 通过；没有成功fit | 0.317422 |
| 导出器7个组件方法 | 通过 | 0.421089 |
| 计划/来源/零授权/失败保存等15个已有方法 | 通过；运行守卫计数全0 | 1.983077 |
| 旧数据准备+真实1条进口/导出 | 通过 | 0.627670 |
| 干净源码唯一临时fit与完整CLI | 通过 | 3.039222 |
| 主项目白名单导出 | 通过 | 0.212902 |
| 新Demo隔离1点及资产比较 | 通过；atol=rtol=1e-10，实际差0 | 3.577437 |

所有受控过程串行、单进程≤120秒、数值线程≤2；包含准备、检查、失败的完整
成本见本地budget_ledger。MATLAB/传播/新oracle标签/正式10k fit/校准/BO均0；
临时三目标fit恰好1。浏览器、AppTest整套复跑、Cloud/Linux部署验收未执行。
上批原UI/图表/会话及续扫证据是复用证据，不重复计作本批新测试。

## 公开运行范围与具体阻塞

`main_code_ready` 按原“完整公开live链路”门槛仍为false；用户明确缩小范围后的
**自有数据/特征/训练代码发布门槛通过**。`demo_code_ready=true`。

MATLAB的 `code/ml_bridge/MamyshevCapture.m:74` 和
`src/mamyshev_ml/supervisor.py:669` 仍依赖两个私人精确基准：

- `reports/local/phase1/baseline_001/configuration.mat`（876001字节；
  SHA-256 `4bda69acf3c6bfa3d63e1113f0c4fc7997615a0b9bdad21d8cce8606ad813bba`）。
- 同目录 `configuration.json`（18305字节；
  SHA-256 `ade8bca16564dbe7f593088e2a01dfb0ec167b27f1794c6068721db791387319`）。

MAT参与6组精确初态/参数数组比较；JSON单独不足，且含私人路径/RNG信息。
没有已实现、已验收的公开资源准备替代路径。本批不分发这些证据、不关闭gate、
不以新摘要替代数组检查。保留其历史身份及本地可运行条件。

实际生产路径使用定制 `code/simulation_engine/GMMNLSE`；`third_party/MMTools`
才是未加入setup路径的参考包。两个来源不能混用许可证。按用户决定，下列四个
已有本地修改不stage、不新增推送；原件与历史证据仍在本机：

```text
code/simulation_engine/GMMNLSE/GMMNLSE algorithm/GMMNLSE_propagate_with_adaptive_deltaZ_RK4IP.m
code/simulation_engine/GMMNLSE/Gain_rate_eqn/GMMNLSE_adaptive_rategain.m
code/simulation_engine/GMMNLSE/analyze_field.m
code/simulation_engine/GMMNLSE/check_convergence.m
```

原remote历史已含引擎及176个data/results/archive跟踪路径，本次不新增/更新这些
内容，也没有删除、untrack、清洗或宣称已清除。未给全项目新增MIT等许可证；
旧署名/权利待决记录保留。旧V4.2权重与严格实验文件仅本地保留，不进入当前Demo。

## 导出身份与发布状态

新副本29文件、678489字节，manifest SHA-256：
`d3f3a9249a87d0d8c6eb0c46ab3a08a8e772ee642cf5d00156298d8070b271ac`。
与原29文件快照相比，只改README、DEPLOYMENT、THIRD_PARTY_NOTICES与外层manifest。
所有运行代码、6个纯函数适配、UI/charts、scaler/结点/权重/内层manifest/q相同。
旧manifest `519bf7b14f22f0e6e00efda775c47c9c8cca24663ac54d778ec9d36d2b5c6547`
及旧快照未变。新manifest忠实记录导出时HEAD及dirty源码哈希，不假称全工作区已提交。

冻结10k权重SHA-256=`9885e8f258fa10de0a69844b70fa72242fcc64267d9db1e6c07dd4bd4609b6d0`；
类SHA-256=`46f9779b878d195b601930446cce3ec5335f694ef219f28c2ae728a353590b11`；
q=`0.0030957846673075884`。本批全程未改。

主仓库确认地址：<https://github.com/Yukino8735/Mamyshev-Oscillator-Simulation>。
发布目标功能分支为 `feature/mamyshev-ml-mvp`，默认main仅允许受检查的普通快进。
Demo目标为 `Yukino8735/mamyshev-design-explorer`，新main，不复制主仓库.git。
写入此初始报告时尚未执行Git写入；实际结果随后附记，最终SHA/远程核查保存在
独立本地publication_receipt，避免报告自引用commit循环。GitHub代码上传不等于网站上线。

## 保留与交付边界

本批改动：新训练桥/CLI/测试和小示例；README/中文指南/SCOPE/EXECUTION_STATUS/
本报告；导出器的一处发布授权描述字段及3个公开说明模板。其他主项目工程文件
为之前积累、本次逐文件审核的项目成果，不是本批重写。保留完整本地MATLAB、
扫描、保存、续扫、DB、研究源码；从未以轻量Demo模块覆盖完整版src。

本地详细证据：`reports/local/full_pipeline_publish_001/`，含起点status/index/文件
哈希、备份、exact命令、32个组件方法日志、真实单条导出、clean副本、release-smoke、
新导出receipt、逐文件清单和实际暂存/远程核查。该目录、完整数据、逐点结果、
真实波形、旧模型、旧图、prompt/review包、临时模型均不进入新增发布。
历史工具仍可要求各自显式实验档案；不把这些档案当新通用训练命令的隐式依赖。

物理Phase2仍in_progress；H02、独立数值收敛、随机鲁棒性和物理状态分类未解决。
physical_state=undetermined；numerical_validation=not_verified；
eligible_as_validated_training_truth=false。发布后停止，不自动开始下一实验或Cloud部署。

## 本次精确文件范围（暂存审查与远程receipt另存）

主仓库审核清单262项（包含已有相同文件时，不产生多余Git差异）：

```text
.gitignore
.streamlit/config.toml
README.md
checks/presentation_smoke.py
code/linear_cavity/main/Mamyshev_linear_cavity.m
code/ml_bridge/MamyshevCapture.m
code/ml_bridge/MamyshevObserver.m
code/ml_bridge/MamyshevWaveforms.m
code/ml_bridge/launch_mamyshev_once.m
code/ml_bridge/mamyshev_artifact_integrity.m
code/ml_bridge/mamyshev_compare_configuration.m
code/ml_bridge/mamyshev_failure_status.m
code/ml_bridge/mamyshev_result_record.m
code/ml_bridge/mamyshev_source_identity.m
code/ml_bridge/mamyshev_validate_launch_context.m
code/ml_bridge/mamyshev_write_diagnostic.m
code/ml_bridge/run_mamyshev_recorded.m
code/ml_bridge/write_mamyshev_record.m
code/ring_cavity/main/Mamyshev_ring_cavity.m
code/ring_cavity/main/README_reproduction.md
code/ring_cavity/main/export_ring_spectrum_display.m
code/ring_cavity/main/plot_ring_reproduction.m
code/ring_cavity/main/reproduce_ring_spectrum.m
code/ring_cavity/main/run_ring_spectrum_figure.m
code/ring_cavity/scans/mamyshev_observation_decision.m
code/ring_cavity/scans/mamyshev_observation_options.m
code/ring_cavity/scans/mamyshev_resolve_config.m
code/ring_cavity/scans/run_mamyshev.m
code/ring_cavity/scans/run_mamyshev_config.m
configs/accuracy_v4_1_protocol.json
configs/demo10k_matlab_plan.json
configs/demo10k_protocol.json
configs/legacy_physics_identity.json
configs/phase2_config_waveform_default.json
configs/phase2_config_waveform_regression.json
configs/phase2_stationarity_protocol.json
configs/v4_model_usage.json
demo/app.py
demo/assets/matlab_plan_summary.json
demo/assets/models/catalog.json
demo/assets/models/demo_10k_v1/calibration.json
demo/assets/models/demo_10k_v1/dependencies.json
demo/assets/models/demo_10k_v1/domain.json
demo/assets/models/demo_10k_v1/manifest.json
demo/assets/models/demo_10k_v1/metrics.json
demo/assets/models/demo_10k_v1/model.joblib
demo/assets/models/demo_10k_v1/model_card.json
demo/assets/models/demo_10k_v1/models_v4.py
demo/assets/scenarios.json
demo/deploy/profile.json
demo/deploy/templates/DEPLOYMENT.md
demo/deploy/templates/README.md
demo/deploy/templates/THIRD_PARTY_NOTICES.md
demo/deploy/templates/gitignore.txt
demo/deploy/templates/package_init.py
demo/predict.py
demo/requirements.txt
demo/source_version.json
demo/ui_charts.py
demo/ui_logic.py
demo/ui_presentation.py
docs/ACCURACY_FIRST_V4_REPORT.md
docs/ACCURACY_V4_1_TARGETED_REPORT.md
docs/ACCURACY_V4_2_REPRESENTATION_REPORT.md
docs/ATTRIBUTION_REVIEW.md
docs/AUDIT.md
docs/BASELINE_REPORT.md
docs/CLAIM_EVIDENCE.md
docs/DEMO_10K_MATLAB_MATRIX.md
docs/DEMO_10K_RELEASE_REPORT.md
docs/DEMO_CHART_RENDER_FIX_REPORT.md
docs/DEMO_DEVELOPMENT.md
docs/DEMO_MAIN_SYNC_REPORT.md
docs/DEMO_SHOWCASE.md
docs/DEMO_UX_REVIEW_REPORT.md
docs/EXECUTION_STATUS.md
docs/FROZEN_MODEL_APPLICATION_V4_3_REPORT.md
docs/FULL_PIPELINE_GITHUB_RELEASE_REPORT.md
docs/GIT_RELEASE_PLAN.md
docs/MVP_CLOSEOUT_REPORT.md
docs/PHASE2_CONFIG_AND_WAVEFORM_REPORT.md
docs/PHASE2_EXTENDED_SINGLE_RUN_REPORT.md
docs/PHASE2_INTEGRATION_READINESS.md
docs/PHASE2_LAUNCHER_REPORT.md
docs/PHASE2_REPAIR_REPORT.md
docs/PHASE2_SINGLE_RUN_REPORT.md
docs/PHASE2_STATIONARITY_REPORT.md
docs/PROJECT_DEMO_SYNC_REPORT.md
docs/REAL_SIMULATION_VALIDATION_PLAN.md
docs/SCOPE.md
docs/USER_GUIDE_ZH.md
docs/assets/demo10k/aggregate_metrics.json
docs/assets/demo10k/model_comparison.md
environment.yml
examples/design_default.json
examples/plan_small.json
mamyshev_accuracy_v4/configs/accuracy_protocol.json
mamyshev_accuracy_v4/configs/domain.json
mamyshev_accuracy_v4/configs/generator_recipe.json
mamyshev_accuracy_v4/configs/scenarios.json
mamyshev_accuracy_v4/matlab/reproduce_v4_synthetic.m
mamyshev_accuracy_v4/matlab/test_v4_oracle_parity.m
mamyshev_accuracy_v4/matlab/v3_evaluate_synthetic.m
mamyshev_accuracy_v4/provenance/METHODOLOGY_SOURCES.md
mamyshev_accuracy_v4/provenance/SOURCES.md
mamyshev_accuracy_v4/provenance/V3_ORACLE_IDENTITY.json
mamyshev_accuracy_v4/reference/build_release.py
mamyshev_accuracy_v4/reference/evaluate_frozen.py
mamyshev_accuracy_v4/reference/metrics_v4.py
mamyshev_accuracy_v4/reference/models_v4.py
mamyshev_accuracy_v4/reference/oracle.py
mamyshev_accuracy_v4/reference/run_validation_pilot.py
mamyshev_accuracy_v4/tests/test_v4_release.py
pyproject.toml
scripts/analyze_mamyshev_stationarity.m
scripts/analyze_mamyshev_waveforms.m
scripts/audit_v41_preservation.py
scripts/audit_v42.py
scripts/audit_v43.py
scripts/audit_v4_delivery.py
scripts/build_demo10k_public_evidence.py
scripts/build_demo_assets.py
scripts/build_demo_summary_assets.py
scripts/build_mvp_inference_bundle.py
scripts/check_demo10k_authorization.py
scripts/check_demo_chart_render.py
scripts/check_demo_ui.py
scripts/check_demo_ux.py
scripts/check_demo_ux_components.py
scripts/check_mvp_closeout_demo.py
scripts/check_mvp_closeout_help.py
scripts/check_mvp_closeout_preservation.py
scripts/check_v4_release_local.py
scripts/demo10k_recorded_resume.py
scripts/demo_ux_preservation.py
scripts/demo_v43.py
scripts/demo_v4_data_chain.py
scripts/diagnose_v41.py
scripts/export_demo.py
scripts/export_mvp_evidence.py
scripts/finalize_demo10k_review.py
scripts/inspect_v43.py
scripts/install_demo10k_ui_dependency.py
scripts/mamyshev_intensity_alignment.m
scripts/prepare_demo10k_matlab_plan.py
scripts/preview_demo10k.py
scripts/review_demo10k_git.py
scripts/run_demo10k.py
scripts/run_demo10k_budget.py
scripts/run_demo10k_matlab_components.py
scripts/run_demo_chart_budget.py
scripts/run_demo_ux_budget.py
scripts/run_mamyshev_once.py
scripts/run_mvp_closeout_budget.py
scripts/run_v41.py
scripts/run_v42.py
scripts/run_v43_budget.py
scripts/run_v43_candidates.py
scripts/run_v4_budget.py
scripts/run_v4_ml.py
scripts/run_v4_search.py
scripts/start_demo10k_batch.py
scripts/start_mvp_closeout.py
scripts/start_v41.py
scripts/start_v42.py
scripts/start_v43.py
scripts/summarize_v41.py
scripts/summarize_v42.py
scripts/summarize_v43.py
scripts/test_v43_components.py
scripts/train_surrogate.py
scripts/v43_scan.py
scripts/v4_scan.py
scripts/verify_v4_prediction_store.py
src/mamyshev_ml/__init__.py
src/mamyshev_ml/closeout_inference.py
src/mamyshev_ml/config.py
src/mamyshev_ml/demo10k_experiment.py
src/mamyshev_ml/demo10k_plan.py
src/mamyshev_ml/demo_inference.py
src/mamyshev_ml/model_usage.py
src/mamyshev_ml/supervisor.py
src/mamyshev_ml/v41_diagnostics.py
src/mamyshev_ml/v41_experiment.py
src/mamyshev_ml/v41_sampling.py
src/mamyshev_ml/v42_data.py
src/mamyshev_ml/v42_experiment.py
src/mamyshev_ml/v42_models.py
src/mamyshev_ml/v42_release.py
src/mamyshev_ml/v43_adapter.py
src/mamyshev_ml/v43_candidates.py
src/mamyshev_ml/v4_evaluators.py
src/mamyshev_ml/v4_ml.py
src/mamyshev_ml/v4_roles.py
src/mamyshev_ml/v4_scan.py
src/mamyshev_ml/v4_search.py
src/mamyshev_ml/v4_store.py
src/mamyshev_ml/v4_training.py
tests/matlab/helpers/gain_rollback_fixture.m
tests/matlab/run_config_waveform_analysis_component.m
tests/matlab/run_config_waveform_components.m
tests/matlab/run_config_waveform_offline_analysis.m
tests/matlab/run_convergence_before.m
tests/matlab/run_demo10k_plan_components.m
tests/matlab/run_gain_before.m
tests/matlab/run_launchprep_candidate.m
tests/matlab/run_launchprep_capture.m
tests/matlab/run_launchprep_observer.m
tests/matlab/run_launchprep_preflight.m
tests/matlab/run_readiness_regressions.m
tests/matlab/run_repair_regressions.m
tests/matlab/run_stationarity_controls.m
tests/matlab/run_stationarity_existing.m
tests/matlab/run_stationarity_observation.m
tests/matlab/run_v4_live_components.m
tests/matlab/run_v4_synthetic_parity.m
tests/matlab/run_wrapper_expected_failure.m
tests/matlab/test_config_entry.m
tests/matlab/test_convergence_safety.m
tests/matlab/test_gain_readiness.m
tests/matlab/test_gain_rollback.m
tests/matlab/test_launchprep_capture.m
tests/matlab/test_observation_control.m
tests/matlab/test_result_contract.m
tests/matlab/test_runtime_observer.m
tests/matlab/test_stationarity_analysis.m
tests/matlab/test_waveform_analysis.m
tests/matlab/test_waveform_io.m
tests/matlab/test_wrapper_readiness.m
tests/run_matlab_short.py
tests/test_closeout_inference.py
tests/test_config.py
tests/test_config_waveform_supervisor.py
tests/test_demo10k_experiment.py
tests/test_demo10k_plan.py
tests/test_demo_chart_padding.py
tests/test_demo_export.py
tests/test_demo_inference.py
tests/test_demo_single_model.py
tests/test_demo_ui_logic.py
tests/test_demo_ux.py
tests/test_observation_supervisor.py
tests/test_once_launcher.py
tests/test_physics_identity.py
tests/test_short_runner.py
tests/test_supervisor.py
tests/test_v41_diagnostics.py
tests/test_v41_experiment.py
tests/test_v41_model_usage.py
tests/test_v41_sampling.py
tests/test_v42_data.py
tests/test_v42_flow.py
tests/test_v42_models.py
tests/test_v42_release.py
tests/test_v43_adapter.py
tests/test_v43_budget.py
tests/test_v43_candidates.py
tests/test_v4_data_chain.py
tests/test_v4_live_supervisor.py
tests/test_v4_ml.py
tests/test_v4_search.py
tests/test_v4_training.py
```

Demo审核清单29项：

```text
.gitignore
.streamlit/config.toml
DEPLOYMENT.md
README.md
THIRD_PARTY_NOTICES.md
checks/presentation_smoke.py
demo/app.py
demo/assets/matlab_plan_summary.json
demo/assets/models/catalog.json
demo/assets/models/demo_10k_v1/calibration.json
demo/assets/models/demo_10k_v1/dependencies.json
demo/assets/models/demo_10k_v1/domain.json
demo/assets/models/demo_10k_v1/manifest.json
demo/assets/models/demo_10k_v1/metrics.json
demo/assets/models/demo_10k_v1/model.joblib
demo/assets/models/demo_10k_v1/model_card.json
demo/assets/models/demo_10k_v1/models_v4.py
demo/assets/scenarios.json
demo/predict.py
demo/ui_charts.py
demo/ui_logic.py
demo/ui_presentation.py
deploy_manifest.json
mamyshev_accuracy_v4/configs/domain.json
requirements.txt
src/mamyshev_ml/__init__.py
src/mamyshev_ml/demo_inference.py
src/mamyshev_ml/v4_evaluators.py
src/mamyshev_ml/v4_scan.py
```

明确排除新增/更新发布、仍留本地的当前候选路径：

```text
AGENTS.md
_codex_plan/PROJECT_SPEC.md
_codex_plan/README.md
_codex_plan/SOURCES.md
_codex_plan/prompts/phase_0_environment.md
_codex_plan/prompts/phase_1_audit.md
_codex_plan/prompts/phase_2_backend.md
_codex_plan/prompts/phase_2b_reduced_model.md
_codex_plan/prompts/phase_3_dataset.md
_codex_plan/prompts/phase_4_ml.md
_codex_plan/prompts/phase_5_optimization.md
_codex_plan/prompts/phase_6_portfolio.md
_codex_plan/prompts/phase_7_publish.md
_codex_plan/templates/AGENTS.template.md
_codex_plan/templates/environment.bootstrap.yml
code/simulation_engine/GMMNLSE/GMMNLSE algorithm/GMMNLSE_propagate_with_adaptive_deltaZ_RK4IP.m
code/simulation_engine/GMMNLSE/Gain_rate_eqn/GMMNLSE_adaptive_rategain.m
code/simulation_engine/GMMNLSE/analyze_field.m
code/simulation_engine/GMMNLSE/check_convergence.m
demo/assets/historical_candidates.json
demo/assets/historical_waveform.json
demo/assets/historical_waveforms.png
demo/assets/models/v42/calibration.json
demo/assets/models/v42/dependencies.json
demo/assets/models/v42/domain.json
demo/assets/models/v42/manifest.json
demo/assets/models/v42/metrics.json
demo/assets/models/v42/model.joblib
demo/assets/models/v42/model_card.json
demo/assets/models/v42/models_v4.py
docs/DEMO_10K_PRESENTATION_REPORT.md
docs/STREAMLIT_DEPLOY_REPORT.md
docs/assets/demo10k/figure_provenance.json
docs/assets/demo10k/v42_accuracy.png
docs/assets/demo10k/v42_representation.png
docs/assets/demo10k/v43_candidate_confirmation.png
docs/assets/demo10k/v43_prediction_heatmap.png
docs/environment.osx-arm64.explicit.txt
mamyshev_accuracy_v4/CODEX_DEMO_10K_AND_GIT_REVIEW_PROMPT.md
mamyshev_accuracy_v4/CODEX_DEMO_CHART_RENDER_FIX.md
mamyshev_accuracy_v4/CODEX_DEMO_TASK_ORIENTED_UX_PROMPT.md
mamyshev_accuracy_v4/CODEX_FULL_PIPELINE_AND_GITHUB_PUBLISH.md
mamyshev_accuracy_v4/CODEX_MVP_CLOSEOUT_PROMPT.md
mamyshev_accuracy_v4/CODEX_PROJECT_DEMO_SYNC_PROMPT.md
mamyshev_accuracy_v4/CODEX_STREAMLIT_DEPLOY_PROMPT.md
mamyshev_accuracy_v4/CODEX_V4_2_REPRESENTATION_PROMPT.md
mamyshev_accuracy_v4/CODEX_V4_3_FROZEN_APPLICATION_PROMPT.md
mamyshev_accuracy_v4/CODEX_V4_PROMPT.md
mamyshev_accuracy_v4/DATA_BUILD_SUMMARY.json
mamyshev_accuracy_v4/DATA_CHECKS.json
mamyshev_accuracy_v4/DOCUMENT_REVIEW.json
mamyshev_accuracy_v4/EXECUTION_LOGIC.md
mamyshev_accuracy_v4/MANIFEST.json
mamyshev_accuracy_v4/PREDICTION_REVIEW_SCOPE.json
mamyshev_accuracy_v4/README_zh.md
mamyshev_accuracy_v4/UPLOAD_REVIEW_CHECKS.json
mamyshev_accuracy_v4/V4_2_UPLOAD_REVIEW.json
mamyshev_accuracy_v4/V4_3_UPLOAD_REVIEW.json
mamyshev_accuracy_v4/provenance/CHART_REVIEW_SCOPE.json
```

另有整个 `reports/local/`、完整科学数据/旧模型/真实MAT/逐点清单和原有未跟踪工作保持本地。原remote已跟踪历史树原样继承，不是本批新增清单；其精确路径保存在本地 `tracked_historical_paths.txt`。具体许可待决范围为上列4个定制引擎修改及既有ATTRIBUTION_REVIEW所述第三方材料；不新增分发、不删除远程历史。
