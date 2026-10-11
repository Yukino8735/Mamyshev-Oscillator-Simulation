# 本地署名与发布前待审清单

本文件只记录本机文件中可直接核对的来源、署名与许可证线索，不重新授权任何文件，也不作跨文件许可兼容性的法律结论。本次交付供本地审阅，GitHub 或其他公开发布仍为 `not_authorized`。

| 文件范围 | 本地证据 | 本次处理及仍待审内容 |
|---|---|---|
| 项目新增的 `src/mamyshev_ml/`、`scripts/`、测试、运行协议与文档 | 阶段报告和实际差异记录能区分新接线、数据来源检查、记录器、ML 应用与旧传播算法 | 可描述为本项目增量工程工作；不能据此推定全部代码、配方或资产都可按某个新许可证发布。根目录未发现统一 `LICENSE`，作者、贡献归属及拟采用的许可仍由项目所有者确认。 |
| `code/simulation_engine/GMMNLSE/` 的实际工作副本 | [来源记录](../code/simulation_engine/README.md)记载原远端 `git@github.coecis.cornell.edu:yc2368/GMMNLSE`、分支 `master`、基线 `66a1bff`（2020-10-12），并明确有大量未提交改动 | 保留原文件及原注释。该目录未发现独立的顶层许可文本；不把另一个 MMTools 包的许可自动套在此副本，也不把此引擎说成新写。公开分发权利及具体修改归属待审。 |
| `third_party/MMTools/` 参考包 | [README](../third_party/MMTools/README.md)署名 Yi-Hao Chen，说明来自 Cornell Applied Physics 的 Frank Wise 团队，是旧 GMMNLSE-Solver 的后续实现；[LICENSE](../third_party/MMTools/LICENSE)是 GNU GPL v3（2007-06-29）全文 | 作为单独的第三方参考包保留。本项目实际 MATLAB 路径使用上面的定制工作副本，`setup_mamyshev_project` 不加入 MMTools。不能将 MMTools 整体重新标成 MIT。 |
| 实际引擎的 `cprintf.m` | [注释](../code/simulation_engine/GMMNLSE/cprintf.m)第 113–116 行保留 Yair M. Altman 署名，以及使用/修改须保留原作者归属的文字 | 保留逐文件声明，发布前核对原来源及适用条款；不能因在同一目录就抹去署名。 |
| 实际引擎的 `distinguishable_colors.m` | [文件](../code/simulation_engine/GMMNLSE/distinguishable_colors.m)第 57 行为 Timothy E. Holy，2010–2011 | 该署名保留；文件内看到的作者信息不等于已经核清全部再分发条件。 |
| 实际引擎 `Linear_Mode_Coupling/myexpm_.m` 等辅助代码 | [文件](../code/simulation_engine/GMMNLSE/Linear_Mode_Coupling/myexpm_.m)第 125 行署 Ken Johnson，第 148 行署 Yi-Hao Chen，第 153 行说明由前者的 `expm_` 修改；还保留资助与免责声明 | 修改来源链保留，不把数值工具的全部贡献归于当前仓库作者。完整逐文件权利清单仍待发布审核。 |
| MMTools 的 `Judd-Ofelt theory/JO_matlab` 子目录 | [本地 license.txt](<../third_party/MMTools/GMMNLSE/Steady_state_Gain_rate_eqn/Judd-Ofelt theory/JO_matlab/license.txt>)署 siamak Dawazdah emami（2015），包含源/二进制再分发时保留声明的条件与免责声明 | 子目录自带声明单独保留；不从顶层许可名称猜测所有嵌套文件都只有同一声明。 |
| `docs/references/`、`docs/thesis/`、历史图、归档与外来数据包 | 原 README、[文献说明](LITERATURE_NOTES.md)、[数据来源说明](../data/README.md)保留来源分类 | 本次不打入精简推理包、不重新发布。这些材料的作者许可、学校/机构要求及图表再分发范围待单独审核。 |
| 冻结权重、校准及小型推理包 | V4.2 训练来源和版本在原 release 与本批包清单中分开记录；精简包只复制必要资产 | 本地可复现交付不等于已批准公开权重、配方、数据或代码。包的 SHA-256 用于完整性与身份，不能认证任意不可信 pickle 的安全性。 |

本次精简包不包含整个第三方传播引擎、MMTools、论文 PDF、全部历史训练/测试记录或大型审计映射。已有严格实验 release 保持原样，推理包清单也不替代原实验归档。本次没有新增统一许可证、删除原署名、重新分发或上传这些文件。

发布前需要用户最终审阅：项目新增工程代码与模型资产的作者/许可选择；实际定制 GMMNLSE 副本与其逐文件辅助代码的分发范围；第三方参考包及文献/论文/历史图是否应包含在公开仓库。以上待审不阻塞本地只读审阅与已授权的有限推理演示。
