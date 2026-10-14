# Stage 2 搜索台账（机制侧）

日期：2026-10-14，UTC。实际工具：助手端公开网页 search/open；没有使用用户浏览器，没有运行 lit.py/API抓取脚本。公开PDF通过网页阅读器读取，没有注册、登录、上传、外发项目数据或下载需登录内容。

原始问题与纳排标准见 [QUESTION_FREEZE.md](QUESTION_FREEZE.md)。02:14 接到整体预算更正，交付期限收紧为02:34；后收紧至02:30左右交付。不能把本轮当系统综述或穷尽检索。搜索引擎合并每批结果，无法可靠追溯每条检索式的精确命中数；下面仅记录人工确认的批次新增候选，不伪造命中计数。设定侧独立查询见 [settings/SEARCH_LEDGER.md](settings/SEARCH_LEDGER.md)。

| 批次/时间 | 检索式（每行一条） | 类型/跨域probe | 人工发现、行动 |
|---|---|---|---|
| M01–04 / 02:12 | crowd navigation action ranking counterfactual rollout value learning<br>crowd navigation policy improvement rollout action value supervision<br>crowd navigation action relabeling hindsight reinforcement learning<br>AGGREVATE rollout classification policy iteration action cost-to-go | 同问题3；跨域：模仿/成本敏感1 | 泛counterfactual rank结果多，发现COLTR、Generalized Hindsight、HFR/HTR；暂不作机制结论 |
| M05–08 / 02:13 | "crowd navigation" "ranking"<br>"crowd navigation" "counterfactual"<br>"crowd navigation" "rollout" "value"<br>"AGGREVATE" Ross Bagnell 2014 | 同问题3；跨域：模仿1 | 发现CrowdVLA、game-theoretic forecasting、Deeply AggreVaTeD与Ross2014线索；不采用生成式二手摘要 |
| M09–12 / 02:13 | "Reinforcement and Imitation Learning via Interactive No-Regret Learning" Ross Bagnell<br>"Reinforcement learning as classification" Lagoudakis Parr 2003<br>"Learning to Search Better than Your Teacher" LOLS<br>"crowd navigation" "value" "Monte Carlo" "Chen" | 跨域：近似策略迭代2/结构化预测1；同问题1 | 找到Ross2014、RCPI2003、LOLS2015官方/作者全文；前三作为核心精读 |
| M13–16 / 02:13 | "Reinforcement Learning as Classification" "pdf" Lagoudakis Parr Duke<br>"crowd navigation" "value" "lookahead" "reinforcement" Chen<br>"crowd navigation" "action" "re-ranking"<br>"crowd navigation" "relabeling" | 文献定位1；同问题3 | 找到RGL2020；RCPI旧链接失败后官方CDN成功；后两式未增加本轮直接近邻 |
| M17–20 / 02:14 | crowd navigation reward learning ranked trajectories demonstrations preference learning<br>"crowd navigation" "action ranking" value learning<br>"crowd navigation" "action relabeling"<br>"counterfactual risk minimization" "Swaminathan" "Joachims" | 同问题3；跨域：信息检索/日志bandit1 | CRM官方页与PDF；SPLC2026、D-REX、PioneeR线索。CRM只完成摘要筛选，PDF打开不等于全文已读 |
| M21–24 / 02:15 | "crowd navigation" "rollout" "supervised"<br>"crowd navigation" "value learning" "ranking"<br>"CrowdVLA" counterfactual arxiv<br>"crowd navigation" "trajectory ranking" | 同问题4 | 找到SoLo T-DIRL、CrowdVLA原文；两篇全文精读。有限时间内没有证明搜索饱和 |
| M25–28 / 02:15 | "Smart Predict, then Optimize" Elmachtoub Grigas paper<br>"learning to rank" "privileged information" paper<br>"crowd navigation" "hindsight" value<br>"social navigation" "cost-to-go" "rollout" | 跨域：决策导向优化1/特权信息视觉排序1；同问题2 | SPO只读摘要；LUPI只读标题/检索片段，不进入机制论证；后两式没有新直接近邻 |
| M29–31 / 02:16 | "Relational Graph Learning for Crowd Navigation" github<br>"SoLo T-DIRL" ICRA 2023<br>"CrowdVLA" github | 代码/发表核验3 | RGL、SoLo官方仓库打开确认；CrowdVLA官方代码未验证 |
| M32–35 / 02:16 | "Value-Guided Policy Steering" paper<br>"crowd navigation" "counterfactual" -"Lacuna" -"newx" -"scribd"<br>"crowd navigation" "cost-sensitive"<br>"Risk-Sensitive Mobile Robot Navigation" offline paper | 跨域：离线RL机器人操纵1；同问题3 | 找到V-GPS，完整阅读主文及B–D，官方作者代码验证；Risk-sensitive crowd离线RL只摘要筛选 |

## 本轮补查的引用链
RCPI/AGGREVATE原文交叉提及SEARN、PSDP、conservative policy iteration；LOLS是关于roll-in/roll-out的直接展开。RGL的引用把 SARL、LeTS-Drive定位为导航环境/搜索基线。V-GPS §2引用IDQL与生成式behavior modeling。未精读这些被引论文，不据此复述细节；没有完成系统的被引网络回溯。

## 检索/读取失败
- aaai.org旧PDF、旧ICML索引403/读取失败；官方cdn.aaai.org对应全文读取成功。
- Duke两个RCPI镜像读取失败；不需要任何登录。
- 一次本地工具调用JavaScript引号语法错误，未发出网络请求；修正后仅执行预定四条普通检索。
- 无整个搜索后端失败；没有绕过身份验证或安全警告。

## 明确未完成
不是系统综述；未穷尽所有近期crowd/action-label论文；未完成所有候选全文、代码运行、复现实验；“本轮没有找到完全相同实现”不等于它不存在。
