# Mamyshev 振荡器数值仿真项目

本目录是对原 `Maymashev 1` 项目的整理版，包含环形腔、线性腔、实际使用的
GMMNLSE 仿真引擎、历史数据与成图、毕业论文、两篇主要参考文献，以及仅供参考
的 MMTools 包。原始文件未被覆盖；所有旧版本仍保存在 `archive/`。

## 目录

| 路径 | 内容 |
|---|---|
| `code/ring_cavity/` | 环形腔主程序、扫描与绘图脚本 |
| `code/linear_cavity/` | 线性 FBG 腔主程序、扫描与绘图脚本 |
| `code/simulation_engine/GMMNLSE/` | 本项目实际依赖的定制 GMMNLSE 代码 |
| `data/` | 原始扫描、插值后处理、趋势数据和演化 MAT 文件 |
| `results/` | 已导出的论文图、PDF 和 PNG |
| `docs/thesis/` | 毕业论文 |
| `docs/references/` | 环形腔与线性腔参考文献 |
| `third_party/MMTools/` | 独立保留的 MMTools 参考包，不是本项目的直接运行依赖 |
| `archive/` | 原始实验目录和所有历史脚本版本 |

更详细的对应关系见：

- [论文、文献与参数映射](docs/PARAMETER_MAPPING.md)
- [数据来源说明](data/README.md)
- [文献说明](docs/LITERATURE_NOTES.md)

## MATLAB 快速开始

建议使用 MATLAB R2021a 或更新版本。项目使用了脚本内局部函数、`tiledlayout`、
`exportgraphics`、`table` 等较新的 MATLAB 功能。当前代码默认使用 CPU。

在 MATLAB 中执行：

```matlab
cd('/path/to/Mamyshev_Oscillator_Project/code')
[project_root, engine_root] = setup_mamyshev_project();
```

运行环形腔单点仿真：

```matlab
run(fullfile(project_root, 'code', 'ring_cavity', ...
    'main', 'Mamyshev_ring_cavity.m'));
```

运行线性腔单点仿真：

```matlab
run(fullfile(project_root, 'code', 'linear_cavity', ...
    'main', 'Mamyshev_linear_cavity.m'));
```

运行环形腔泵浦功率/第二滤波器中心波长二维扫描：

```matlab
run(fullfile(project_root, 'code', 'ring_cavity', ...
    'scans', 'scan_mamyshev.m'));
```

运行线性腔四组单参数扫描：

```matlab
run(fullfile(project_root, 'code', 'linear_cavity', ...
    'scans', 'scan_linear_FBG_mamyshev.m'));
```

## 两套模型

环形腔模型以 Haig 等人的全光纤环形 Mamyshev 振荡器为结构参考，代码采用
4 m 增益光纤、三段无源光纤以及两个偏移滤波器。论文基准计算把第二滤波器
从参考文献中的 1036 nm 改为 1030 nm，因此基准滤波间隔为 10 nm。

线性腔模型以 Boulanger 等人的单泵浦 MOGMA 系统中的线性 FBG 振荡器为结构
参考。整理后的主程序仍是“振荡器 + 0.2 m 输出尾纤”模型，并未完整复现参考
文献中的外接 GMN 放大器。该差异已在参数映射和代码审查中明确记录。

## 复现边界

本次整理环境没有 MATLAB 或 Octave，因此完成的是代码级静态审查、文件校验、
数据来源核对和 PDF 视觉核验，未重新运行耗时仿真。历史结果原样保留；修正版
代码需要在有 MATLAB 的机器上做一次单点运行和小范围扫描后，再用于新的定量
结论。
