# 数据来源与可信度分层

## 环形腔

- `ring_cavity/mamyshev_phase_scan.mat`：由 `scan_mamyshev.m` 保存的泵浦功率
  与第二滤波器中心波长二维扫描，包含稳定状态、输出能量、未压缩 FWHM 和能量
  波动。该文件来自原项目，是历史数据。
- 论文中的泵浦、偏移、带宽和增益光纤长度单参数曲线没有完整逐点 MAT/CSV。
  对应数值写在 `code/ring_cavity/analysis/plot_*_dependence.m` 的数组中，属于
  历史记录/后处理值。

## 线性腔趋势数据

`linear_cavity/trend_guided/` 来自原脚本明确标注的
“trend-guided processed data”。这些数组依据原始量级与预期物理趋势构造，
并非逐点数值仿真的直接输出。论文中约 80 fs、数百 kW 的线性腔曲线与这组数据
相符。
