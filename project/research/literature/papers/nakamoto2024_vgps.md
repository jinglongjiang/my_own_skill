# Steering Your Generalists: Improving Robotic Foundation Models via Value Guidance

- ID：nakamoto2024；Nakamoto, Mees, Kumar, Levine。CoRL 2024；[正式 PMLR 卷](https://proceedings.mlr.press/v270/nakamoto25a.html) 为 270:4996–5013，2025。
- 角色：near-miss / baseline；阅读：full，主文 §§1–7 和 Appendix B–D 已读；其余附录未逐表审计。
- 主来源：[作者全文 v2](https://arxiv.org/html/2410.13816v2)。
- 状态：已验证通过（全文与公开代码可见）；复现未验证。

## 文献证据
§5.1 / Eq.(1)：由既有机器人数据训练 Cal-QL Q 函数。§5.2 / Eq.(2) / Alg.1：冻结黑箱母体抽 K 个动作，用 Q 重排后执行，可贪心或 softmax。Appendix B.2：实机 K=50；仿真对 K、温度扫参后报告每策略最好结果。Table1 实机任务“green pepper in pot”成功率母体 0.15、V-GPS 0.35；Appendix D 指每任务20次，表未附 CI。仿真常用三随机种子、每种100次；OpenVLA 每任务50次。§7 指出需要随机候选、增加部署计算、陌生物体/语言仍受限。

## 与本任务的关系（本轮推论）
同：不改母体权重，加独立动作评分器并在母体候选中挑选。异：本文 critic 来自离线 RL 数据与保守 TD 学习，不是本轮所有80动作、一次干预后冻结 KDA 续行的精确 G_A；输入是视觉/语言，非九标量。故 wrapper 结构已有先例，标签结构须另外对照 RCPI/NRPI。不能说我们首次用离线价值评分改善冻结机器人策略。

## 可用与不可用
[作者主页](https://nakamotoo.github.io/V-GPS/) 的 Code 链接实际打开到 [官方仓库](https://github.com/nakamotoo/V-GPS)，可见 Cal-QL 训练和 SIMPLER 评测说明；未下载、安装、运行权重或代码。其操纵成功率不能与本仓库导航 regret 对比；额外 critic 训练及候选采样预算须计入。
