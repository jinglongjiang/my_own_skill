# Reinforcement and Imitation Learning via Interactive No-Regret Learning

- ID：ross2014；Ross & Bagnell，2014，arXiv:1406.5979v1。
- 角色：near-miss / mechanism-source。
- 阅读：full；主文 §§1–4、Alg.1/2、Theorem 2.1/2.2/3.1 已读；附录未逐项验算。
- 主来源：[作者公开全文](https://arxiv.org/pdf/1406.5979)。同行评审发表记录本轮未核实，不能写成某届会议论文。
- 状态：已验证通过（全文机制核查）；本仓库复现：未验证。

## 文献证据
§2.2 / Alg.1：AGGREVATE 在访问状态探索动作，之后交给专家续行，用 cost-to-go 训练成本敏感策略并聚合数据。§2.3 明确包括所有动作成本向量、ranking reduction，以及拟合平方损失回归器后 argmin。§3 / Alg.2：NRPI 从探索分布采样，执行探索动作后按当前策略续行，再更新策略。§3.1 / Theorem 3.1 的界含探索分布与比较策略访问分布的距离项。§2.5 警告专家续行过于乐观；§4 警告每个标签需整条轨迹、采集昂贵。该文主要为理论，无可比人群导航成功率或多 seed 表。

## 与本任务的关系（本轮推论）
最危险的对应不是只说“像 AGGREVATE”：九标量→G_A 的 Ridge/HGB 是 §2.3 的回归后选动作；“换一步然后母体续行”更接近 NRPI 单轮数据生成。当前没有在线数据聚合、更新策略续行或分布覆盖证明，不能借其 no-regret 或闭环保证。折扣、受限安全候选和 top-5 范围是实现/接口约束，不自动成为新核心机制。

## 可用与不可用
可用：把 rollout-derived action-cost supervision 写成既有机制，报告标签预算。代码完整性未核实。不能把当前离线查表结果解释为其定理条件已经满足。
