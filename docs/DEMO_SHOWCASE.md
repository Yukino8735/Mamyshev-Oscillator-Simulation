# Demo 展示入口与上线方案

2026-10-11。用户确认还没有公开网址；当前状态：**本地Demo完成，网站待上线**。
本页是主仓库README的展示入口说明，不是已经运行的公开网站。

## 建议方案

将已有 `Mamyshev_Demo_Deploy` 的单模型快照部署到Streamlit Community Cloud，
然后在主仓库README顶部放一个 **Open live demo** 链接，指向平台实际返回的URL。
完整研究项目留在主仓库；展示仓库仅使用已准备的29文件范围和冻结10k模型。
这延续现有Python界面，可以直接使用交互预测、候选筛选及图表/下载。
[官方部署说明](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy)
说明了仓库/分支/入口设置和公开URL生成方式。

GitHub Pages可以另做静态介绍或截图页；当前Streamlit交互程序需要Python运行环境。
这个静态站点不是本轮必需的新项目。
[GitHub Pages说明](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages)

## 当前可审阅的部署配置

| 项目 | 已准备值或状态 |
|---|---|
| 快照 | single_10k_001 / demo_10k_v1 |
| 部署文件范围 | 29文件；当前deploy_manifest.json描述28个载荷，自身另计 |
| 单独展示仓库 | 既有拟定名称Yukino8735/mamyshev-design-explorer；尚未创建 |
| 分支/入口 | 拟用main / demo/app.py；尚未推送 |
| Python | 请求3.11，实际部署选项及云端运行尚未验收 |
| 依赖 | 部署副本根requirements.txt的精确版本；不自动改依赖以加载权重 |
| Secrets | 本Demo不需要研究环境凭据 |
| 公开访问URL | 未分配，不猜测子域名或编造链接 |
| 云端/匿名访问 | 未验收 |

部署副本含模型完整性/来源检查，只有冻结推理和零额度验证请求，不启动
MATLAB或训练。原第三方/模型权利审查项仍保留；公开前按当前manifest核对。
本次仅准备README入口和方案，没有创建仓库、上传文件或部署网站。

## 上线后的README形式

收到平台真实URL并通过匿名访问、预测/图表/下载验收后，将README的
“Interactive demo & website status”链接改成“Open live demo”，目标填实际URL。
旁边保留Quick start及此页链接。不要把本机127.0.0.1地址当作外部可访问的网站。

还应把展示仓库的主页设置成同一个实际URL，便于从GitHub About找到网站。
网站文案和README应保留当前模型的合成训练来源，未来真实验证版本发布时再
更新模型卡和展示信息；不能因为网站上线就宣称完成真实物理验证。

## 本地查看

从主仓库根目录，使用既有环境：

```sh
/opt/homebrew/Caskroom/miniforge/base/bin/conda run -n mamyshev-ml --no-capture-output python -m streamlit run demo/app.py --server.address 127.0.0.1 --server.headless true --browser.gatherUsageStats false
```

打开本机 http://127.0.0.1:8501，Ctrl-C停止自己启动的服务。
这只是本地查看方法；本批没有启动服务器。

## 部署验收

按平台实际选项设置Python3.11，核验所有精确依赖在Linux构建和模型加载通过；
若不通过先保存构建错误，不放宽冻结权重/依赖校验。
[依赖规则](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies)
说明入口目录和仓库根目录的依赖文件位置；独立部署快照仅使用根requirements。

匿名浏览器验证：示例/单点、基准比较、候选/零可行、1D/2D三个目标、输入修改
清除旧结果、最多3请求和CSV/JSON下载。公开页面及下载必须保留真实模型ID和
合成来源；AppTest通过不能替代浏览器绘制与匿名访问验收。

当前入口只能打开本说明。网站地址取得并验收后，README才会直接链接公开Demo。
