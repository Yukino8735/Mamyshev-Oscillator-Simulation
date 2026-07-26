# 代码入口

- `setup_mamyshev_project.m`：统一添加仿真引擎和实验脚本路径。
- `ring_cavity/main/Mamyshev_ring_cavity.m`：环形腔单点主程序。
- `ring_cavity/scans/run_mamyshev.m`：可调用的环形腔单点函数。
- `ring_cavity/scans/scan_mamyshev.m`：泵浦/滤波器中心二维扫描。
- `linear_cavity/main/Mamyshev_linear_cavity.m`：线性 FBG 腔单点主程序。
- `linear_cavity/scans/scan_linear_FBG_mamyshev.m`：四组单参数扫描。
- `simulation_engine/GMMNLSE/`：项目实际使用的定制传播与增益代码。

MMTools 位于项目根目录的 `third_party/`，不加入 MATLAB 路径。

