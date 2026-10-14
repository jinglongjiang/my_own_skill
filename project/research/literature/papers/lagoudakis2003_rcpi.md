# Reinforcement Learning as Classification: Leveraging Modern Classifiers

- ID：lagoudakis2003；Lagoudakis & Parr，ICML 2003，pp.424–431。
- 角色：near-miss / mechanism-source。
- 阅读：full；公开全文主文 §§1–8 已读，含算法和实验；本轮 2026-10-14。
- 主来源：[AAAI 官方全文](https://cdn.aaai.org/ICML/2003/ICML03-057.pdf)。旧 aaai.org PDF 与 Duke 镜像读取失败，官方 CDN 成功。
- 状态：已验证通过（原文机制核查）；本仓库复现：未验证。

## 文献证据
§2.3 / Fig.1：在状态执行候选动作，再用给定策略续行，累计折扣奖励估计 Q；可作函数逼近目标。§3 / Fig.2：所有动作 rollout 后，将较优动作转为分类监督，交替采样与策略更新。§6：用 t-test 避免噪声导致的错误正负标签；不强行把近似并列动作标成唯一赢家。§4 明说当前策略与更新策略的状态分布可能不同。§7.1 的倒立摆为 3 动作，约 200 rollout states；§7.2 自行车为 5 动作，成功示例用 4000 rollout states 和两轮 SVM 更新。论文未给现代多 seed 配对置信区间；不是导航指标。§8 将采样复杂度、restart distribution 留作后续问题。

## 与本任务的关系（本轮推论）
同：一次动作干预+母体续行的 G_A，以及用事后赢家监督决策，都落在该骨架内。异：本轮是冻结 KDA、既有九个动作标量、单轮离线回归/失败重排；RCPI 为通用迭代分类策略。差别不足以证明方法创新。标签噪声处理不宜照搬：当前确定性分支回报并非同一动作重复随机 rollout 的均值。

## 可用与不可用
可用：Fig.1/2 作为最低必比机制定义。未核实作者完整可运行代码。不拿倒立摆/自行车表现与 CrowdNav 数字并排，不宣称 RCPI 保证本轮回归后的闭环改进。
