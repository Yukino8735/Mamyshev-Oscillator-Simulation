# 仿真引擎来源

本目录中的 `GMMNLSE/` 是原项目实际使用的工作副本，不是 `third_party/MMTools`
中的新版参考包。

原工作副本的嵌套 Git 元数据记录为：

- 远端：`git@github.coecis.cornell.edu:yc2368/GMMNLSE`
- 分支：`master`
- 基线提交：`66a1bff`（2020-10-12，`Extend pulse_compressor to multimode`）

原工作区在该提交之上有大量未提交的修改、删除和新增文件。本整理版复制了当时
磁盘上的实际工作文件，但没有复制约 250 MB 的 `.git/objects`。项目专用脚本已
移到 `code/ring_cavity`、`code/linear_cavity` 和 `archive/`。

