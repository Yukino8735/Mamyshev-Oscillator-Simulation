# MVP 本地收尾报告

2026-09-28。按 `mamyshev_accuracy_v4/CODEX_MVP_CLOSEOUT_PROMPT.md` 完成本地文档、冻结推理包和有限演示。V4.3 审核 JSON 的四项输入文件身份均吻合。本批不新增实验，停止等待审核；公开发布仍为 `not_authorized`。

## 交付及实际依赖

- [英文 README](../README.md)、[中文使用指南](USER_GUIDE_ZH.md)、[主张—证据表](CLAIM_EVIDENCE.md)、[署名与许可待审](ATTRIBUTION_REVIEW.md)。
- 本地精简包：[inference_bundle.zip](../reports/local/mvp_closeout_001/inference_bundle.zip)，124,646 字节；[展开目录](../reports/local/mvp_closeout_001/inference_bundle/)，共 301,015 字节，含清单在内 16 个文件。
- [构建收据](../reports/local/mvp_closeout_001/bundle_build.json)、[推理工件清单](../reports/local/mvp_closeout_001/inference_bundle/manifest.json)、[依赖版本](../reports/local/mvp_closeout_001/inference_bundle/dependencies.json)、[来源](../reports/local/mvp_closeout_001/inference_bundle/provenance.json)。
- [机器结果摘要](../reports/local/mvp_closeout_001/evidence/evidence_summary.json)、[自动生成 README 表格](../reports/local/mvp_closeout_001/evidence/readme_tables.md)、[四张历史图副本](../reports/local/mvp_closeout_001/evidence/figures/)。只读取已有机器记录，未重新打开测试集评分；表格由序列化摘要生成并插入 README 标记区。

ZIP SHA-256：`488a5b348e76e3043f971db86719fcf24e3af7c7e58dc570ed0da12043b4bb89`。
原模型 SHA-256 保持 `c236c2d2dd6cb5b59e32bd5ab4f8c3823f7fefc10d7571108a3d6339ee46b2e0`，42,530 字节。
原 `models_v4.py` 自定义类逐字节复制，未重新实现 329 维变换、重建权重或修改输出反变换。训练来源为 T2 的 1024 个仓库趋势引导合成设计（既有 512 + V4.1 定向 512），训练 ID 与原协议/选择/评分身份在包中保留。

实际环境为本机 Darwin arm64，Python 3.11.16，`/opt/homebrew/var/conda_envs/mamyshev-ml/bin/python`；全部 Python 工作由指定 Conda 环境启动。包记录并核对 numpy 2.4.6、scipy 1.17.1、scikit-learn 1.9.1、joblib 1.6.0、threadpoolctl 3.7.0。没有安装、修改环境或全局配置。

包可在原仓库之外运行，不依赖历史绝对路径；其中 `origin_*` 的历史相对路径仅作来源引用。实际 builder 也在包中，但重新构建仍需原仓库和完整实验资产。未装入全部历史数据、67 MB 审计映射、论文或第三方传播引擎。

## 加载规则与区间边界

构建先执行原 `verify_release` 和已有 `calibration_reference`。原完整实验 release、selection 和默认部署不变。新增的独立推理清单只绑定本包所需 15 个资产文件，不替代完整实验归档。

新薄入口先检查文件集合/哈希、固定模型及实际自定义源码身份、domain/schema、原协议/训练 ID/评分来源、q 语义关系和依赖版本，随后才导入固定文件名的自定义类并 joblib 加载。自定义类执行已验证源码字节，避免采用未绑定的缓存 pyc；不接受任意自定义代码路径。模型内部 family/parameters/domain/三输出也核对。哈希是可信本地资产的身份/完整性检查，不是对不可信 pickle 或任意修改包的安全认证。

原 release 未直接绑定 calibration 文件字节；原适配器通过 model/selected、协议 n/alpha/rank/method，以及与已绑定 final 中区间宽度的关系核查 q。本次新增清单直接绑定原 calibration 字节，保留 q=`0.003266551289750619`，未重校准。仓库原适配器可在可选校准不可用时保留点预测并将区间置 null+reason；本独立包把 calibration 列为必需资产，缺失则拒绝。

四字段顺序、单位、域和严格 0.1 m 长度格点均在 schema 中；未知/缺失/非有限/域外/非格点输入拒绝，不裁剪。预测是合成代理标量，不生成复场。区间 `limited`：整体 1936/2048、near_slice 216/256、core 467/512，不是逐点、逐组或物理安全保证。

## 实际执行及预算

工作目录为本地仓库；分支保持 `feature/mamyshev-ml-mvp`，基础 commit 保持 `489bf4242f9b5266d47f8892840a24af66931ff0`。原工作树已有大量未提交工作，保全依据是本批开始时的逐文件快照，而非只与 HEAD 比较。

所有下列命令前缀为：

```sh
/opt/homebrew/Caskroom/miniforge/base/bin/conda run -n mamyshev-ml --no-capture-output python
```

实际串行命令如下（每一行独立执行；不能重跑到已有目录）：

```text
scripts/start_mvp_closeout.py
scripts/run_mvp_closeout_budget.py --timeout-s 60 engineering bundle_build -- scripts/build_mvp_inference_bundle.py
scripts/run_mvp_closeout_budget.py --timeout-s 60 engineering saved_evidence -- scripts/export_mvp_evidence.py --update-readme
scripts/run_mvp_closeout_budget.py --timeout-s 60 engineering finite_demo -- scripts/check_mvp_closeout_demo.py
scripts/run_mvp_closeout_budget.py --timeout-s 60 engineering cli_help -- scripts/check_mvp_closeout_help.py
scripts/run_mvp_closeout_budget.py --timeout-s 60 engineering final_preservation -- scripts/check_mvp_closeout_preservation.py
```

沿用现有 `run_v4_budget.py` 和进程隔离监控器，新薄封装只限定本批目录、单一累计 300 秒类别和每进程 60 秒；没有新建监控平台或修改旧 monitor。BLAS/数值线程上限 2，全部串行，无 GPU。预算记录见 [budget_ledger.json](../reports/local/mvp_closeout_001/budget_ledger.json)，每项有 command、开始/结束、状态及 charged 外部墙钟。该口径是受控 Python 子任务墙钟（含内部子命令），不是开发人员耗时、物理求解速度或加速比；不把内部子命令再次累加收费。

| 实际工作 | 退出/结果 | 本批记账秒 |
|---|---|---:|
| 独占起点快照及四项审核输入核对 | 0 / 全部吻合 | 1.194149083 |
| 构建、原 release/q 核查及新 manifest 验证 | 0 / 通过 | 0.524975375 |
| 只读历史摘要、四图副本、README 表格 | 0 / 通过 | 0.211023542 |
| 仓库外有限演示及 8 项测试 | 0 / 通过 | 27.000512083 |
| 六条 CLI 帮助 | 0 / 全部通过 | 2.195533209 |
| 最终保全核查 | 以同批原始账本与核查记录为准 | 见下方完成记录 |

帮助实际检查：`v43_scan.py predict --help`、`v43_scan.py run --help`、`v4_scan.py run --help`、`v4_scan.py waveform --help`、`run_v4_ml.py select --help`、`run_v4_search.py --help`。逐条完整命令、退出码和输出保存在 [help/](../reports/local/mvp_closeout_001/help/)。未调用训练、生成或搜索执行分支。

## 一次有限复用演示

[固定协议](../reports/local/mvp_closeout_001/demo/protocol.json)在预测前写出：只使用旧默认输入 `(4,10,3,4)` 和旧 curve CSV 的前两点 `(4,10,0.5,4)`、`(4,10,1.4,4)`。总计 3 个不同旧输入；3 次单点 + 两次三行批量 = 9 行重复预测，不是 9 个新设计或标签。没有重跑 20k 池预测、81 点热图或 64 次候选确认。

ZIP 解压至仓库外系统临时目录，子 Python 使用 `-I`、清除 `PYTHONPATH`，cwd 在外部目录，包只通过自身目录寻找资产；没有借仓库目录导入自定义类。测试后移除本批临时副本，实际命令和结果留存于 [demo/result.json](../reports/local/mvp_closeout_001/demo/result.json)。组件测试另行显式导入仓库测试源码，不与包自足性验证混称。沿用同一现有环境，未建立全新环境，未声明跨平台可复现。

包命令是 `infer.py verify` 与 `infer.py predict --input ... --output ...`。有限演示通过 runtime guard 的 `runpy` 执行同一 CLI 主入口，完整子命令可在各 `*.command.json` 核对。

| 对照（固定 atol=rtol=1e-10） | 最大绝对差 | 结果 |
|---|---:|---|
| 三个单点 vs 旧保存预测 | 0 | 通过 |
| 三行批量 vs 旧保存预测 | 4.440892098500626e-16 | 通过 |
| 单点 vs 批量 | 4.440892098500626e-16 | 通过 |
| CSV 读回 vs JSON 读回 | 0 | 通过 |

每次成功预测实际执行原类一次、joblib 加载一次；5 次预测命令均退出 0。verify 退出 0，未反序列化模型或执行自定义类。malformed、缺 model、缺类、篡改类四个独立 CLI 场景全部退出 2；模型加载、类执行和预测计数均 0，无失败回退。这四个演示场景不虚报为额外独立单元测试。

新增测试 `test_closeout_inference` 的 7 个方法检查有效 schema、未知/缺字段、非有限/布尔/域外/长度格点、JSON/CSV 同输入、重复字段/空输入、缺清单、伪造清单不得放行未知权重；复用 1 个原 `LiveAuthorization.test_default_denial_and_zero_allowance_do_not_reserve`，验证未显式执行及额度 0 均在预留前拒绝，未启动 MATLAB。共 8 方法通过，见 [组件输出](../reports/local/mvp_closeout_001/demo/components.stderr.log)；没有重跑完整旧回归。

运行期 guard 记录并阻止 fit/partial_fit/fit_transform、校准、oracle 以及外部进程/网络回退调用，计数均 0。它是本次可信演示的诊断防护，不作为对任意敌意 Python 代码的隔离保证。只读摘要与帮助不产生标签，历史数据库和 query ledger 的最终字节保全另行核对。

## 证据摘要、保留功能与未执行项

README 的三张数值表来自原机器记录：A 是 V4.2 的 1024 训练/2048 固定混合测试；B 是历史 V4 的四场景×三种子×两方法×64 冷启动；C 是 V4.3 已有 1024 训练先验、每方法每场景 8 次、64 事件/63 新设计/1 缓存的有限确认。不能混写成同一个实验。MAE/P95 保留原单位，容差通过不写“100%准确”。

V4.3 四场景改善按共享 T2 incumbent 和原目标方向重算，约 6.087842%、14.477877%、0.732486%、0.598363%；随机法包含 incumbent 后均为 0%，未丢掉原最好。S4 的机器浮点显示 `-0.000000%` 与 0 相同，不代表变差。所有值为已存在合成评价，真实 solver 精度与真实仿真节省率仍 `null/not_measured`。历史标签与 fit 成本按阶段分别列在机器摘要，不把重用记录相加为独立样本。

MATLAB 数据生成、真实四维入口、1D/2D/4D 扫描、random/LHS 合法长度、逐点持久化、取消/续扫、数据库、CSV/MAT 导出及真实波形读取代码全部保留。中文指南给出实际命令及 schema；旧单点、组件、MAT 回放证据仍是历史，不新增“物理通过”结论。本批只检查帮助和零授权拒绝，没有重新绘制真实波形、传播或离线压缩。新完整 live 扫描 `not_run`，pending 请求真实额度仍为 0，supervisor/STOP/失败优先机制未改。

未执行：MATLAB 启动/GMMNLSE/真实扫描 0；新 train/dev/cal/test/candidate 标签 0；fit/调参/重校准/test 重评分/BO/随机或冻结模型新搜索 0；环境改动、Git 提交/推送/PR、网络发布 0。没有修复旧 timeout、missing final 或历史失败。

## 本批文件和保全范围

仅修改既有 `README.md`、`docs/SCOPE.md`、`docs/EXECUTION_STATUS.md` 的当前说明；保留状态文件内全部旧阶段条目。新增：

- `src/mamyshev_ml/closeout_inference.py`、`tests/test_closeout_inference.py`。
- `scripts/build_mvp_inference_bundle.py`、`scripts/export_mvp_evidence.py`、`scripts/check_mvp_closeout_demo.py`、`scripts/check_mvp_closeout_help.py`、`scripts/check_mvp_closeout_preservation.py`。
- `scripts/start_mvp_closeout.py`、`scripts/run_mvp_closeout_budget.py`：现有预算工具的本批起点/设置薄封装。
- 本报告及 `docs/USER_GUIDE_ZH.md`、`docs/CLAIM_EVIDENCE.md`、`docs/ATTRIBUTION_REVIEW.md`。
- ignored `reports/local/mvp_closeout_001/` 的请求、原始日志、摘要、推理包及检查证据；未修改 `.gitignore`。

[起点快照](../reports/local/mvp_closeout_001/start_snapshot.json)记录 2846 个原文件与开始时完整 git status。
[最终保全检查](../reports/local/mvp_closeout_001/preservation_check.json)逐项核对原模型/q/历史结果、原生产/数值/授权/扫描源码以及 Evaluation/query 账本，列出真实变化，核对分支和 commit、文档链接、图副本与包 hash，并执行 `git diff --check`。检查结果见下方完成记录。

许可方面未给第三方套用 MIT 或删除署名。MMTools GPLv3 与嵌套声明保留，实际 GMMNLSE 副本来源独立记录。根许可证、实际定制引擎分发范围、自有代码/模型资产署名及论文图再分发范围仍需用户发布前审阅，详见署名文档；不阻塞当前内部本地交付，不自动发布。

修订合成 ML 的限定点预测验收及 V4.3 应用已完成，本次交付完成后等待审核。整个旧 Phase 2 仍为 `in_progress`，深度物理验证 `deferred`；`physical_state=undetermined`、`numerical_validation=not_verified`、`eligible_as_validated_training_truth=false`。本批结束不启动下一实验或阶段。

## 最终完成记录

最终保全进程退出 0，记账 1.366990166 秒；本批六项合计 **32.493183458 秒 / 300 秒**，最长受控子任务 27.000512083 秒，全部小于 60 秒上限。无失败重试或预算追加。监控器将输出合并到每项 `stdout.log`，独立包演示的各子命令另有 stdout/stderr 文件。

保全检查通过：2846 个原文件中 2843 个逐字节不变，只有允许的 README/SCOPE/EXECUTION_STATUS 三项更新；无丢失、无意外变更。416 个原源码/测试/配置文件及 1508 个历史本地证据文件全部不变，原 Evaluation/query ledger 和数据库字节不变，无历史目录新增文件。分支与 commit 不变，原模型/q/旧 release、已生成 ZIP、四图副本与摘要来源 hash 均通过。

`git diff --check` 退出 0、无输出；新增文件无行尾空白，文档本地链接全部有效。随后仅追加本节实测结论，没有再执行推理、修改资产或改动生产源码。本地收尾验收通过，公开许可/署名范围仍待审，停止等待用户审核。
