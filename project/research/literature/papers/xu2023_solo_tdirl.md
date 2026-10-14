# SoLo T-DIRL: Socially-Aware Dynamic Local Planner based on Trajectory-Ranked Deep Inverse Reinforcement Learning

- ID：xu2023solo；Xu, Chakhachiro, Kathuria, Ghaffari，ICRA2023（作者仓库确认）；阅读：full，主文 §§I–V。
- 角色：near-miss；主来源：[公开全文](https://arxiv.org/pdf/2209.07996)。
- 状态：已验证通过（全文、官方仓库存在）；复现未验证。

## 文献证据
§III-B / Eq.(5)：以两条示范轨迹的排序损失辅助 MEDIRL 奖励学习；Alg.1 用附近行人突然速度变化率（SVCR）排序。§III-A/C：局部栅格、五个离散移动动作、静障碍/目标/预测轨迹/社交距离特征。§IV-A：Gazebo/PedSim social force，100多条示范，3m×3m特征图。TableII 圆穿越报告 SoLo success=100%、time=10.41s、invasion=0.0112/m；没有明确该表独立训练seed数、测试样本数或CI。TableIII 的排序准确率不是导航成功率。§IV-D 明确人工特征、粗网格、惯性忽略与实机感知缺陷。

## 与本任务的关系（本轮推论）
同为人群导航、事后轨迹质量排序。不同：它学习任务奖励并优化栅格策略；不是冻结价值母体上对同一根状态80个单步干预的终局回报回归。本轮不能宣称首次在crowd navigation中引入排序监督，但也不能把两者写成同一方法。

## 代码与边界
原文[Fetch_IRL链接](https://github.com/UMich-CURLY/Fetch_IRL)实际重定向[SoLo_TDIRL官方仓库](https://github.com/UMich-CURLY/SoLo_TDIRL)，可见训练/ROS/Gazebo入口。未运行。公开存在不等于顺利复现。本文没有本任务明确的“隐藏行人策略类型”协议，不能替它补设定。
