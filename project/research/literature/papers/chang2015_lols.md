# Learning to Search Better than Your Teacher

- ID：chang2015；Chang, Krishnamurthy, Agarwal, Daumé III, Langford，ICML 2015，PMLR37:2058–2066。
- 角色：near-miss / mechanism-source。
- 阅读：full；主文 §§1–5、Fig.2/3、Alg.1/2、Tables1–4 已读；另行附录未核查。
- 主来源：[PMLR 官方全文](https://proceedings.mlr.press/v37/changb15.pdf)。
- 状态：已验证通过（全文机制核查）；本仓库复现：未验证。

## 文献证据
§2 / Fig.2 / Alg.1：learner roll-in 后枚举单步偏离，再以 reference/learner mixture 续行，形成 cost-sensitive 样本。Eq.(2) 按该状态最小 rollout loss 减去共同偏置。§3.1 / Fig.3 / Table1 给出仅 reference roll-in 或 rollout 的失败例；§3.2 的保证针对 reference regret 与自身单步偏离 regret 的组合。§3.3 / Theorem4 说明任意问题中达到局部最优也可能很慢。§5 评测分类、POS、dependency parsing，非导航；Table4 的 suboptimal-reference LOLS UAS=90.2，reference/reference=83.3，未给本表多 seed CI。实现基于 Vowpal Wabbit，五遍数据；本轮未核实具体可复现实验提交版本。

## 与本任务的关系（本轮推论）
同：替换单步、完成分支、按终局损失构造动作监督。异：本轮续行始终冻结 KDA，根状态也只来自母体；LOLS 用在线 learner roll-in、混合续行更新。其反例说明离线一步读数不能直接推出部署策略闭环效果，但并不证明本轮一定失败。

## 可用与不可用
可用：roll-in/roll-out 两轴与分布变化的公平实验说明。不能将 UAS 与本任务 regret/失败率比较，不能把“胜过自己的母体”当独创目标。
