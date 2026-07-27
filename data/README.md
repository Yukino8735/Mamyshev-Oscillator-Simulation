# 数据来源与可信度分层

## 环形腔

- `ring_cavity/mamyshev_phase_scan.mat`：由 `scan_mamyshev.m` 保存的泵浦功率
  与第二滤波器中心波长二维扫描，包含稳定状态、输出能量、未压缩 FWHM 和能量
  波动。该文件来自原项目，是历史数据。
- 论文中的泵浦、偏移、带宽和增益光纤长度单参数曲线没有完整逐点 MAT/CSV。
  对应数值写在 `code/ring_cavity/analysis/plot_*_dependence.m` 的数组中，属于
  历史记录/后处理值。

## 线性腔原始扫描

`linear_cavity/raw_scans/` 是原扫描脚本直接写出的 CSV/MAT：

- 泵浦与 FBG 偏移扫描均有完整成功记录。
- LR-FBG 带宽扫描只有 0.75-2.0 nm 成功；0.5 nm 和 2.25-4.0 nm 记录为用户取消
  的进度条错误。
- 增益光纤长度扫描中，0.05 m 的奇数半步与 0.1 m 保存周期不整除，因此多点
  失败；0.7、0.8、…、1.4 m 等整 0.1 m 点成功。
- 历史 CSV 中的 `pulse_duration_ps` 是未压缩时域宽度，约 1.3-1.7 ps；
  `peak_power_W` 也是未压缩峰值。

## 线性腔趋势数据

`linear_cavity/trend_guided/` 来自原脚本明确标注的
“trend-guided processed data”。这些数组依据原始量级与预期物理趋势构造，
并非逐点数值仿真的直接输出。论文中约 80 fs、数百 kW 的线性腔曲线与这组数据
相符。
