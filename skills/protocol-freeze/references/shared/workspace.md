# 研究工作区约定

## 两个目录，不要混
- **技能目录** `$SKILL_DIR`：当前这份 SKILL.md 所在的目录。脚本、模板、参考文件都在它下面。运行脚本一律写成 `python3 "$SKILL_DIR/scripts/<脚本>"`，调用别的技能的脚本写成 `"$SKILL_DIR/../<技能名>/scripts/<脚本>"`。执行前把 `$SKILL_DIR` 换成实际的绝对路径。
- **研究工作区**：用户项目里的 `research/` 目录（或用户指定的位置），存放所有产物。脚本的 `--dir`、`--file` 等参数指向这里，用绝对路径或相对项目根目录的路径。

不要 `cd` 到技能目录里再运行脚本——那样相对路径 `research/` 会落在技能目录下，凭空多出一个错位的工作区。开始前先确认工作区的绝对路径；如果当前目录下没有 `research/`，先问清或用 `init_workspace.py` 在用户的项目目录里建，不在技能目录或临时目录里建。

## 工作区结构

所有技能读写同一个目录（默认 `research/`，由 `research-pipeline` 的 `init_workspace.py` 创建）。各阶段只通过文件交接，这样每一步都能单独检查、单独重做，换一个会话也接得上。

```
research/
├── STATE.md            当前阶段、当前候选、下一步动作、阻塞项（research-pipeline 维护）
├── RECORD.md           全部做过的实验、方向及其状态、资产、噪声底、教训（research-ledger 维护）
├── directions.jsonl    方向台账，机器可查重（research-ledger 维护）
├── TARGET.md           实测靶子：余量在哪、多大、怎么量的（prescreen 产出，idea-forge 的入口条件）
├── lit/
│   ├── ledger.json     文献台账：检索式、候选论文、筛选决定、阅读记录（paper-scout）
│   ├── papers/         每篇精读笔记，一篇一个文件
│   ├── screened.md     筛选结果表
│   └── synthesis.md    机制分组、评测口径对照、方法级缺口（paper-synthesis）
├── ideas/
│   ├── candidates.md   候选卡（idea-forge）
│   └── duel-<id>.md    先例对照（prior-art-duel）
├── prescreen/<id>.md   前筛结论（prescreen）
├── protocols/<id>/     PROTOCOL.md、FREEZE.json、AMENDMENT-n.md（protocol-freeze）
├── handoffs/<id>.md    给执行方的指令与回执评估（exec-handoff）
├── verdicts/<id>.md    裁决与稳健性检查（result-verdict）
└── claims.md           主张—证据表（paper-claims）
```

候选编号用 `C01`、`C02`…，全流程不变。一个候选从 `candidates.md` 的一张卡开始，依次得到 duel、prescreen、protocol、handoff、verdict 各一份文件，最后在 RECORD.md 和 directions.jsonl 里落一个终态。
