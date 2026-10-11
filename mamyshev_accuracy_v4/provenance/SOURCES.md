# 来源与用途

## 用户项目历史数据（本轮通过GitHub connector实际读取）

仓库：Yukino8735/Mamyshev-Oscillator-Simulation。默认分支为main；读取的是已提交历史文件，不是Mac的feature分支未提交源码。

- `code/ring_cavity/analysis/plot_pump_dependence.m`，blob d04171eba5ba21d0ac5fed75e8f729871f9e95bf：17个历史/后处理能量和脉宽值。
- `code/ring_cavity/analysis/plot_offset_dependence.m`，blob ba8d6e26b1ee0643340dc0c5f9c3b63103b0c039：17个历史/后处理值。
- `code/ring_cavity/analysis/plot_bandwidth_dependence.m`，blob d853dba285635869b315ddee134c9bafe97a04a2：11个历史/后处理值。
- `code/ring_cavity/analysis/plot_gain_length_dependence.m`，blob 02c7aa081126a6b473650d5a972564ea7deb4d4c：9个历史/后处理值。
- `code/ring_cavity/scans/scan_mamyshev.m`，blob 330fab771af7ac2f4849c9dc27718c21f96596a0：历史二维扫描3:0.5:7 W、1028:2:1036nm。并未在本轮执行。

四个曲线文件均有明确历史/后处理注释。仅使用归一化趋势，不转称54个独立4D求解器样本。原峰值近似列没有当作实测峰值。

## 用户上传报告

`PHASE2_CONFIG_AND_WAVEFORM_REPORT.md`：四输入真实接线、无源长度、0.1m限制，以及成功config_waveform_001压缩能量/脉宽/峰值。只作接口约定与尺度参考，不证明多设计泛化。

`AUDIT.md`：数据来源/输出平面局限，不能混合历史曲线、线性腔、填值表与当前ring真值。

`PHASE2_STATIONARITY_REPORT.md`、`EXECUTION_STATUS.md`：20圈诊断、监督清理错误和缺失final必须保留；不以它们产生稳定分类真值。

## 方法资料（本轮访问的官方文档/论文页面）

https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.qmc.LatinHypercube.html
用途：分层抽样方法；不支持本次具体新参数范围或1024样本一定足够。

https://scikit-learn.org/stable/modules/gaussian_process.html
用途：GPR均值/标准差、核及超参数的官方方法接口。实际软件版本以用户本机为准，不要求升级。

https://scikit-learn.org/stable/common_pitfalls.html
用途：训练/测试隔离和预处理泄漏。

https://proceedings.mlr.press/v32/gardner14.html
Gardner et al. (2014), Bayesian Optimization with Inequality Constraints.
用途：少量昂贵目标/约束评价的优化框架；不支持本项目胜率、具体节省率或最优解已经验证。

## 本轮自行提出的设计

新边界2–10W、2–16nm、0.5–8nm、1–8m；1,024标签、20,000无标签候选；四场景阈值、64查询预算、三随机种子；历史曲线的有界延伸、乘性组合、交互/惩罚和形状因子都是本次明确构造的基准设计，不是引用论文中的器件结论。
