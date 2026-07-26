# 主要参考文献

原文件对应关系：

- `22342051-外文原文附件2.pdf` → 环形腔参考文献。
- `22342051-外文原文附件1.pdf` → 线性腔参考文献。
- 原项目内的 `New Mamyshev.pdf` 与附件 1 的 SHA-256 完全相同，因此文献目录
  只保留一份规范命名副本；历史重复件仍可在 `archive/` 中追溯。

## 环形腔

文件：`references/01_环形腔参考_Haig_2022.pdf`

Henry Haig, Pavel Sidorenko, Robert Thorne, Frank Wise,
“Megawatt Pulses from an All-Fiber and Self-Starting Femtosecond Oscillator,”
Optics Letters, 2022.

文献给出全 PM 光纤环形 Mamyshev 振荡器：4 m 有源光纤、一个关键的 1.5 m
无源臂、1040 nm/5 nm 与 1036 nm/3 nm 两个超高斯滤波器。仿真包含 Kerr、
Raman、自陡峭和四阶色散，并采用稳态速率方程增益。实验获得 110 nJ、4 ps
腔内输出，压缩后约 80 nJ、40 fs、1.5 MW。

本项目环形腔保留了其“单有源臂 + 无源臂 + 拒绝端输出”的结构，但论文基准把
第二滤波器改到 1030 nm，形成更大的 10 nm 偏移。

## 线性腔

文件：`references/02_线性腔参考_Boulanger_2023.pdf`

Vincent Boulanger, Michel Olivier, François Trépanier,
Pascal Deladurantaye, Michel Piché,
“Multi-megawatt pulses at 50 MHz from a single-pump Mamyshev oscillator
gain-managed amplifier laser,” Optics Letters 48(10), 2700-2703, 2023.

文献系统由 HR/LR FBG 终止的线性 Mamyshev 振荡器和后接 GMN 放大器组成，
共享一只 976 nm 泵浦二极管。FBG 位于 1030 nm 和 1036 nm，系统在 52 MHz
下输出 129 nJ、2 ps 脉冲，压缩后为 102 nJ、36.7 fs、2.13 MW。

本项目线性主程序只复现振荡器及短输出尾纤，未包含文献的完整 GMN 放大器。
因此应把它视为“线性 FBG Mamyshev 振荡器参数研究”，而不是完整 MOGMA 性能
复现。
