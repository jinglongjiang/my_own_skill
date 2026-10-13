# my_own_skill

面向方法论文的研究技能套件：从筛论文到实现、下裁决的一条完整流水线，12 个技能、7 个可执行工具，各阶段只通过文件交接。


## 研究项目上下文（`project/`）

这个仓库同时带着一个具体研究项目的现状和离线数据，供远程代理接手：

- `project/SITUATION.md`：研究现状，每条结论标了证据等级。
- `project/DATA.md`：数据字段说明，以及这些表能回答什么、不能回答什么。
- `project/DOTS_BRIEF.md`：给云端代理的任务书。
- `project/data/`：反事实表（2100 个状态 × 80 个候选）。
- `project/results/`、`project/tools/`：已有读数和复现脚本。

## 设计出发点
研究浪费时间有两种相反的方式：没筛就上大规模实验；以及一轮轮核查和交接、没有新数字。这套技能围绕一个问题组织：**拿到下一个真实数字最快的办法是什么？**

所以有两条通道：
- **原型通道**：最小原型几小时内能出数字时直接动手——候选卡 → `method-build` → `result-verdict`。
- **完整通道**：要占用夜班算力、要作为论文证据时走全程——
  量靶子 → 筛文献 → 整合 → 找创新点 → 先例对照 → 前筛 → 冻结协议 → 执行 → 裁决 → 记录 → 写作骨架。

只有一条硬闸：协议没冻结不读最终测试块。"先有靶子""先前筛"是默认做法，各有时间预算，超了就改走原型通道。同一候选连续两次停在核查或交接上而没有新数字时，下一步改为自己动手。

## 技能一览
| 阶段 | 技能 | 做什么 | 工具 |
|---|---|---|---|
| 调度 | `research-pipeline` | 判断当前阶段、指出下一步、拦住跳步，维护 STATE.md | `init_workspace.py` |
| 论文筛选 | `paper-scout` | 冻结检索问题；同问题找近邻、跨领域找机制；带理由筛选；读过才能引用 | `lit.py` |
| 整合 | `paper-synthesis` | 按机制分组、评测口径对照表、方法级缺口、对标入口 | — |
| 找创新点 | `idea-forge` | 对标改进与跨领域迁移两条路；候选卡必须写作用通道、必要条件、最便宜的否定方式 | — |
| 对比 | `prior-art-duel` | 找最危险的先例；四轴判定；性能对照是否公平；不可声称清单 | — |
| 前筛 | `prescreen` | 靶子模式量余量；候选模式做通道检查（代数或实测）、反事实查表、最小判别测试 | `regret_ruler.py` |
| 实现 | `method-build` | 调查调用链、最小原型、退化一致/重建一致/梯度单测、smoke、启动并盯住长任务 | `jobwatch.py` |
| 协议 | `protocol-freeze` | 主张、划分、对照臂、裁决条件、停止条件；哈希冻结与修订登记 | `freeze.py` |
| 执行 | `exec-handoff` | 给执行代理的指令；评估它交回的完成/停止报告 | — |
| 裁决 | `result-verdict` | 配对统计、稳健性检查、按预注册条件下结论；逐条核对第三方意见 | `paired_stats.py` |
| 记录 | `research-ledger` | 实验台账、方向状态、已杀方向查重、资产、噪声底、教训 | `ledger.py` |
| 写作骨架 | `paper-claims` | 主张—证据表、贡献定位、对比表口径、审稿攻击点、limitation | — |

## 目录
```
my_own_skill/
├── README.md
├── install.sh              安装到 ~/.claude/skills（--codex 同时装到 ~/.codex/skills）
├── shared/                 全部技能共用：证据规则、使用者档案、工作区约定
├── skills/<技能>/
│   ├── SKILL.md
│   ├── references/         按需读取的细则（含 shared/ 的同步副本）
│   ├── assets/             模板
│   └── scripts/            工具
├── tools/
│   ├── sync_shared.sh      改了 shared/ 之后运行
│   └── validate.py         项目自检
├── examples/               示例规则与用法
├── tests/test_tools.py     工具回归测试（合成数据，63 项）
└── evals/evals.json        技能的提示词级用例（尚未跑过对照评测）
```

## 安装与使用
```bash
bash install.sh --dry-run        # 先看会装什么
bash install.sh                  # 装到 ~/.claude/skills；已有同名技能会跳过
bash install.sh --codex          # 同时装到 ~/.codex/skills
```
装好后对 Claude 说"下一步做什么""帮我筛一下这个方向的论文""这个想法值不值得跑"之类的话即可触发；也可以直接点名技能。新课题从 `research-pipeline` 开始，它会创建 `research/` 工作区。

换项目或换人时改 `shared/profile.md`（语言、目标产出、算力、分工），然后运行 `tools/sync_shared.sh`。

工具依赖：Python 3.8+；`regret_ruler.py` 和 `paired_stats.py` 需要 numpy，其余只用标准库。`lit.py` 的检索需要能访问 arXiv 和 OpenAlex。

## 工具速查
```bash
# 文献台账
python3 skills/paper-scout/scripts/lit.py init --question "…"
python3 skills/paper-scout/scripts/lit.py search "…" --regime same --since 2019
python3 skills/paper-scout/scripts/lit.py search "…" --regime cross --probe "information retrieval"
python3 skills/paper-scout/scripts/lit.py screen <id> include --role near-miss --reason "…"
python3 skills/paper-scout/scripts/lit.py read <id> --level full
python3 skills/paper-scout/scripts/lit.py check --cite research/lit/synthesis.md

# 反事实查表尺
python3 skills/prescreen/scripts/regret_ruler.py target  表.jsonl.gz --group cell
python3 skills/prescreen/scripts/regret_ruler.py rule    表.jsonl.gz --rule examples/rules/tied_set_clearance.py:rule
python3 skills/prescreen/scripts/regret_ruler.py compare 表.jsonl.gz --alt 新打分.jsonl --key cell,case,root_step
python3 skills/prescreen/scripts/regret_ruler.py channel 表.jsonl.gz --alt 新打分.jsonl --key cell,case,root_step

# 长任务
python3 skills/method-build/scripts/jobwatch.py start  --dir runs/x -- <命令>
python3 skills/method-build/scripts/jobwatch.py status --dir runs/x --stall 600

# 协议冻结
python3 skills/protocol-freeze/scripts/freeze.py lint|freeze|verify <协议目录>
python3 skills/protocol-freeze/scripts/freeze.py amend <协议目录> AMENDMENT-1.md --seen "…" --reason "…"

# 配对裁决
python3 skills/result-verdict/scripts/paired_stats.py --a 基线.json --b 候选.json --ni collision:2.0 --hold success:-1.0

# 方向台账
python3 skills/research-ledger/scripts/ledger.py add|set|list|dup|axes
```

## 各部分借鉴了什么
| 来源 | 取用的做法 | 没有取用的 |
|---|---|---|
| Grounded Research Ideation | 同问题 / 跨领域两种检索；去领域名词的结构描述；读过才能引用并用程序把关；各阶段只通过文件交接；迁移四项自测 | 固定的检索与阅读配额 |
| IdeaSpark | 候选必须有具体机制和否定方案；"用了什么额外信息就要有对应对照"；提案不等于有效性证据 | 请求/回执式的重流程、一次只出一个方案 |
| ARIS idea-discovery-robot | 先确定接口、仿真器、已有资产和预算再构思；降低"换个模型套上去"的优先级 | 自动推进到实验 |
| research-proof | 实施前先写主张、验证边界、敌对项、淘汰门；结论只分已支持/被否定/未定 | 固定十栏输出格式 |
| Anthropic risk-assessment | 把决定成败的假设移到最前面检验 | 风险打分与成功概率 |
| idea-evaluator | 四轴判定是否重复；数据已否定核心机制时直接终止 | 五维打分 |
| Research Opportunity Graph | 每个方案带与最近工作的差异、最小实验、停止条件 | —— |
| 本项目自己的经历 | 反事实查表尺与分数带内随机对照；配对裁决与稳健性清单；冻结与修订规则；执行回执的分类处理；已杀方向查重与按轴汇总 | —— |

## 已验证与未验证
**已验证通过**
- 工具回归测试 `python3 tests/test_tools.py`：63 项全部通过。只用合成数据，不依赖外部文件和网络；每一项对应一个曾经出过的问题（正常路径、拒绝路径、边界情况）。
- 在真实数据上的复现：`regret_ruler.py` 在 200 状态 × 80 候选的反事实表上复现了此前手算的数字，对一个闭环确认净零的规则读数一致；`paired_stats.py` 复现了一组 n=200 配对评测的计数、精确 p 值与回报差，精确 p 与 scipy 在 5 组计数上一致。
- `lit.py` 的 arXiv 与 OpenAlex 检索实际跑通过（依赖网络，不在回归测试里；后端超时会如实记进台账）。
- `install.sh`、`tools/validate.py`：安装到临时目录、重复安装跳过、12 个技能自检 0 错误。

**未验证**
- 12 个技能的正文没有做"用技能 / 不用技能"的对照评测，触发描述没有优化。`evals/evals.json` 是提示词级用例，没有配套的固定数据和可执行判分器。
- 技能是否真的提高研究效率，没有证据。
- 反事实尺没有做过真实候选的阳性回测（一个闭环确认有效的改动）；在此之前它的"未检出"只能提示，不能单独用来淘汰。

## 使用限制
- `freeze.py` 只锁定协议文本和修订文件的哈希。它不判断模板是否填完，也不校验协议里列出的权重和数据。
- `regret_ruler.py` 的"带内随机"对照是在候选所选动作的分数带内均匀取，控制的是"改到了哪个分数带"，不是严格匹配改动幅度。它量的是单步、事后的 regret。
- `paired_stats.py`：统计目标是按配对加权的比率差；同一 case 出现在多个文件时以 case 为单位。聚类数据在事件很少时用的保护界很保守（簇大小不等时更保守），可能把本来合格的结果判成不满足，但不会落到点估计的错误一侧。区间半宽不是功效意义上的最小可检出效应。
- `regret_ruler.py compare/channel`：新打分下没有可行候选的状态默认报错，需要用 `--empty-policy` 说明部署的回退行为。
- `ledger.py` 没有写锁，同一时间只能一个会话写；`dup` 是关键词比对，中英文混述时会漏。
- `jobwatch.py` 只支持 Linux（依赖 /proc）。
- 代数通道检查只能否定"价值网络固定时的即时排序改变"，不能否定重新训练后的影响。

## 修订记录
- 第 4 版（第三次外部复核后，只动两个脚本）：
  - `paired_stats.py`：检验、区间、非劣效判定统一到同一个统计目标（按配对加权的比率差）。检验改为以 case 为单位的精确符号翻转检验，"多少个 case 变好"只作描述；聚类保护界按簇大小修正，并强制任何界不得落在点估计的错误一侧；回报列出现 NaN 时报错，与"没有回报列"区分。
  - `regret_ruler.py`：原可行集合只有一个动作的状态在 compare/channel 中不再跳过；新打分下无可行候选时默认报错，由 `--empty-policy` 明确处理。
  - 上一版"聚类保护界只会保守误拒"的说法不成立，已撤回。
- 第 3 版（第二次外部全量审查后，16 个功能问题 + 5 条规则冲突）：
  - `paired_stats.py`：检验与区间全部以 case 为单位，同一 case 重复出现不再被当成独立样本；两臂 case 不一致时默认报错；`--alpha` 现在同时作用于事件区间和非劣效界；去掉"最小可检出效应"的叫法。
  - `regret_ruler.py`：各组独立重采样且结果不依赖输入行顺序；字段缺失、主键重复、非有限数值、选中被过滤的动作一律报错退出；新打分改变可行集合时不再悄悄退回原动作，并单独报告；并列间距为零时不再报无穷大。
  - `jobwatch.py`：多参数命令逐个转义；独占创建 PID 文件防并发；拒绝带旧退出码的目录；僵尸进程不算存活。
  - `lit.py`：同一 ID 再次出现时保留筛选与阅读记录；核查时确认笔记文件仍在。
  - `ledger.py`：历史保留每次的证据位置。`freeze.py`：修订文件必须在协议目录内。
  - 规则统一：无靶子原型通道与候选淘汰条款不再冲突；共模奖励淘汰限定在固定价值网络；smoke 出现 0%/100% 改为查明原因；脚本路径统一用 `$SKILL_DIR`，与研究工作区分开；趋势用针对趋势的检验；两个骨干通过只写"在所测试的骨干上成立"。
  - 新增 `tests/test_tools.py`。
- 第 2 版（第一次外部审查后）：
  1. 作用通道检查不再把"输入扰动相同"当作"分数变化相同"；经过网络的改动改为实测（新增 `regret_ruler.py channel`）。
  2. `paired_stats.py`：McNemar 改为对数域计算；非劣效判定加入不退化的区间。
  3. 新增 `method-build`（实现与运行）和原型通道；"先有靶子""先前筛"从硬闸改为带时间预算的默认。
