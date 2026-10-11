# 方法与来源

项目特定数据来源沿用SOURCES.md与原V3 generator_recipe.json；本轮未重新读取远程repo或用户Mac新代码，不将历史快照称为当前工作区验证。

本轮查阅的外部方法说明：
- scikit-learn学习曲线：https://scikit-learn.org/stable/modules/learning_curve.html
- 误差与任务决策的关系：https://scikit-learn.org/stable/modules/model_evaluation.html
- MAPE近零值限制：https://scikit-learn.org/stable/modules/generated/sklearn.metrics.mean_absolute_percentage_error.html
- 防止数据泄漏：https://scikit-learn.org/stable/common_pitfalls.html
- Angelopoulos & Bates，A Gentle Introduction to Conformal Prediction and Distribution-Free Uncertainty Quantification：https://arxiv.org/abs/2107.07511

方法资料不支持“本项目必须8192样本”“512即可预测GMMNLSE”或某个3%/5%物理精度承诺。样本上限和容差都是本次项目设计；选择模型来自开发实测。共形区间的边际覆盖依赖交换性，不等于每个最优候选的保证。

为保持配方身份，本包沿用原V3文档里的GitHub blob引用；它们说明原历史曲线出处，不证明曲线物理准确或是四维仿真记录。引用和内容不构成对整个第三方仓库重新赋予许可证。
