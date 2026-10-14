# CrowdVLA: Embodied Vision-Language-Action Agents for Context-Aware Crowd Simulation

- ID：hwang2026；Hwang et al.，arXiv:2604.05525v1，2026-04-07；同行评审发表状态未验证。
- 阅读：full，公开HTML主文 §§1–5；补充材料未核查。角色：near-miss（宽泛机制防过度声称）。
- 主来源：[作者公开全文](https://arxiv.org/html/2604.05525v1)。
- 状态：已验证通过（全文存在与机制）；发表/完整代码未验证。

## 文献证据
§3.1：Unity重建ETH/UCY场景，64个20帧motion skills。§3.2：替代动作在环境中rollout，生成动作选择/结果预测QA；§3.3 / Eq.(1)–(3)：示范动作交叉熵和QA token loss联合训练，部署仅选下一skill。§4.3/Table1–4：评测含PDM-ADE/FDE、GSR、SRVR；PDM采用teacher-forcing单段评测，不能替代闭环安全。§5列motion discretization、场景语义定义、长意图局限。本轮不引用表格数值作为导航基准，统计细节/补充材料未完整核实。

## 与本任务的关系（本轮推论）
它足以约束“首次在人群动作学习中使用反事实分支结果监督”的宽泛声称。区别是行人模拟VLA/语言QA、有限motion-skill段，对比本轮robot导航、单步干预后冻结母体终局G_A、标量评分器；不能宣称已被同一个具体算法覆盖，也不能将这篇预印本写成已发表机器人导航基准。

## 代码
检索了标题+github、打开作者原文；本轮未核实可用官方代码，记“未验证”，不记“没有代码”。
