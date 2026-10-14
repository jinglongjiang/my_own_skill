# Relational Graph Learning for Crowd Navigation

- ID：chen2020rgl；Chen et al.，IROS 2020；角色：baseline / near-miss。
- 阅读：full，主文 §§I–VI、Eq.(1)(2)、Alg.1、TableI 已读。
- 主来源：[作者机构全文](https://www2.cs.sfu.ca/~mori/research/papers/chen-iros20.pdf)。
- 状态：已验证通过（原文与公开仓库核查）；本仓库复现未验证。

## 文献证据
§III-C / Eq.(2)：学人群转移模型和价值函数，以 d-step 预测、top-w clipping 搜索动作。§III-D / Alg.1：ORCA 初始化后联合训练，价值标签为 bootstrap target，非逐动作真实终局 G_A。§IV：80动作（5速度×16方向），五人、半径4m圆形、ORCA参数随机；机器人对人不可见；500测试cases。TableI：MP-RGL-Multistep success=0.96±0.02、collision=0.02±0.01，±为五次独立训练的标准差，不是CI；d=2,w=2。§VI 承认未建模过去轨迹时序。

## 与本任务的关系（本轮推论）
最贴现有80动作 Deep-V 系统的导航基线，但模型预测搜索与真实未来监督不同。它已在 top-w 候选上多步评估，不能把“只在价值最高的少数动作中进一步筛选”宽泛声称为首次。原文五人协议、γ=0.9、网络与母体都不同于本轮 KDA seed443；不能引用其0.96与本仓库成功率排名。

## 代码与比较
原文作者链接及[公开仓库](https://github.com/ChanganVR/RelationalGraphLearning)均已打开，README确认IROS2020、训练/500case测试入口。没有安装运行；可运行性未验证。若将来比较，须固定同一 CrowdNav 设置、权重训练预算、历史观测与候选计算预算。
