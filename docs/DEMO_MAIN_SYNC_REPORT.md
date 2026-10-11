# 主仓库与 Demo 同步报告

2026-10-11。本次按用户要求将本地主仓库 Demo 入口同步到已完成部署副本的
`single_10k_001`，唯一活动模型为 `demo_10k_v1`。这是本地工作树版本，
不是新 Git 标签、GitHub release 或云端发布。

## 版本与范围

- 本地分支：`feature/mamyshev-ml-mvp`；基础 HEAD：`489bf4242f9b5266d47f8892840a24af66931ff0`。
- 查询时 GitHub `main` 也是同一 HEAD；大量后续研究工作尚未提交。
- 部署快照 manifest SHA-256：`cbf2cb69f1e0aa9d7bbf03e9dacc3fa8f0c57d42c2c4f127e583118963597f93`。
- 10k 权重 SHA-256：`9885e8f258fa10de0a69844b70fa72242fcc64267d9db1e6c07dd4bd4609b6d0`。
- `demo/source_version.json` 记录来源、活动模型与同步源文件 hash。
- UI、推理、活动 catalog 及 Streamlit 配置来自部署副本；主项目保留完整
  `v4_evaluators.py` / `v4_scan.py`，没有用部署精简文件覆盖。
- V4.2历史权重、历史摘要、原研究CLI、MATLAB/GMMNLSE、DB、扫描/续扫/
  CSV/MAT导出均保留。原图表和10k八项冻结资产字节未变，六个纯函数AST一致。
- 依赖声明同步UI栈并保留Matplotlib；实测既有环境版本全部匹配，未安装/升级。
- 旧资产构建入口现在只核验活动冻结快照，防止历史模板恢复双模型清单；
  旧实现保留为内部历史函数。旧双模型UI检查脚本仍是历史证据；当前入口为
  `scripts/check_demo_ux_components.py` 和 `checks/presentation_smoke.py`。

## 验证

- 22个Demo单元方法通过：输入域、资产校验、预测回读、图表padding、
  UI规划/导出及活动模型/旧会话拒绝。人工UI夹具仅在对应导出边界mock身份检查；
  新身份回归与真实模型AppTest未mock该检查。
- 9个原V4.3适配器方法通过，使用标明的人工夹具检查研究扫描、DB和CSV/MAT导出。
- 对部署副本实际捕获参照，再检验主仓库同步副本的单点、1D9点、2D81点及
  两个CLI：三目标/上下界/导出一致，最大绝对差0，固定atol=rtol=1e-10。
- 六组1D/2D×三目标实际Streamlit图表规格、坐标、rect、标记、tooltip与
  CSV/JSON严格相同；图表异常保留表/下载，无效新请求清除旧结果。
- 工作台512候选、同模型比较、最多3个零额度请求、旧输入失效、零可行、
  数据来源正文和独立会话缓存检查通过；旧会话拒绝并须显式重置。
- 所有AppTest阶段fit/oracle/Evaluation/MATLAB计数为0。无新科学标签、
  再训练、校准、真实传播或数据采集；研究夹具不报告为科学结果。
- 短检查均串行/两数值线程/每进程60秒上限，受控用时合计35.765903秒。
- 浏览器视觉、云端构建、匿名端到端访问、完整物理测试与全仓历史测试未运行。
  AppTest是组件验证；真实GMMNLSE泛化仍未测量，Phase2物理状态未改变。

准备阶段失败保留记录：两次依赖一致性断言发现主/部署依赖不同，随后
合并声明并核验环境；一次监控日志目录缺失、一次相对脚本路径随cwd变化，
修正适配器后真实测试通过。失败不计为通过，未修改模型或放宽数值断言。

## 文件、备份与实际命令

本次仅同步以下20个文件，逐项before/after hash与新增路径见私人
`reports/local/demo_main_sync_001/change_manifest.json`：

- `.streamlit/config.toml`
- `README.md`
- `demo/app.py`
- `demo/predict.py`
- `demo/ui_logic.py`
- `demo/ui_presentation.py`
- `demo/requirements.txt`
- `demo/assets/models/catalog.json`
- `demo/source_version.json`
- `src/mamyshev_ml/demo_inference.py`
- `checks/presentation_smoke.py`
- `scripts/build_demo_assets.py`
- `scripts/check_demo_ux_components.py`
- `tests/test_demo_inference.py`
- `tests/test_demo_ui_logic.py`
- `tests/test_demo_ux.py`
- `tests/test_demo_single_model.py`
- `docs/USER_GUIDE_ZH.md`
- `docs/EXECUTION_STATUS.md`
- `docs/DEMO_MAIN_SYNC_REPORT.md`

被覆盖文件逐项备份在 `reports/local/demo_main_sync_001/before/`；
完整本批证据在同目录 `evidence/`。Git分支、HEAD与索引保持不变，
未执行add/commit/push/tag/PR/合并或发布；部署副本保持不变。

全部Python使用已确认Miniforge前缀：

```sh
/opt/homebrew/Caskroom/miniforge/base/bin/conda run -n mamyshev-ml --no-capture-output python -B ...
```

准备副本中，复用原 `tests/run_matlab_short.py:run_isolated` 监控短Python检查，
完整argv、日志、退出码和时间见 `evidence/ledger.json`及每个runner记录。
实际子命令分别为 `scripts/check_demo_ux_components.py`，部署副本
`checks/presentation_smoke.py capture`，同步副本
`checks/presentation_smoke.py {inference,charts,ui,session}`（明确reference/out），
以及 `-m unittest discover -s <同步副本/tests> -p test_v43_adapter.py -v`。
捕获输出在私人目录，不进入Demo资产。写回后以逐文件hash和Git差异检查
确认落地内容与验证副本一致，不重复科学计算。

继续工作可从本仓库 `demo/app.py` 启动新版UI；数据生成等研究入口仍按
`docs/USER_GUIDE_ZH.md` 的完整后端说明使用。活动模型训练来源是
repository-guided synthetic；后续真实物理验证须作为单独任务确定范围。
