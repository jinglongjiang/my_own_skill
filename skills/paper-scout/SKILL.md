---
name: paper-scout
description: 论文检索与筛选。把一个研究问题变成冻结的检索问题、两种检索方式（同问题找近邻、跨领域找可借用的机制）、带理由的纳入/排除决定，以及"读过才能引用"的阅读台账。用户说"帮我找相关论文""筛一下文献""有没有人做过""查一下这个方向的工作""找对标论文""找可以借鉴的方法"，或者任何后续步骤需要引用文献而台账还没建时，都用这个技能。它不写综述、不生成创新点，只负责把该读的论文找全、筛准、读实。
---

# paper-scout：论文检索与筛选

## 为什么要有台账
语言模型做文献工作最常见的失败是凭印象引用：论文存在，但它说的不是你以为的那句话。另一个失败是检索做了一半就开始下结论，然后被一篇没找到的近邻推翻。台账把"搜了什么、找到什么、为什么留、读到哪一层"全部落在文件里，后面的整合、对照、写作都只从台账取材。

先读 `references/shared/evidence-rules.md`。工具是 `scripts/lit.py`（只用标准库），所有命令加 `--dir research/lit`。
命令里的 `$SKILL_DIR` 指本文件所在目录，运行时换成它的绝对路径；`research/` 指用户项目里的研究工作区，不在技能目录下（见 `references/shared/workspace.md`）。

## 流程

### 1. 冻结检索问题
在动手搜之前写下 1–3 个问题，每个问题包含：输入、期望输出、现有方法在什么条件下不行。问题里不放候选解法的名字——放进去会让检索只找支持它的论文。
```
python3 "$SKILL_DIR/scripts/lit.py" init --dir research/lit --question "……" --question "……"
```
同时在 `ledger.json` 的 `criteria` 里写纳入和排除标准（见 `references/screening-criteria.md`），筛选时按标准办，不临场改。

### 2. 同问题检索：找近邻
用这个问题自己的术语，目标是把"同一个问题、同一个困难"的已有工作尽量找全。每个问题 4–8 条检索式，换说法直到新结果变少。
```
python3 "$SKILL_DIR/scripts/lit.py" search "crowd navigation value-based reinforcement learning" --regime same --since 2019
```
对标优先时（见 `references/shared/profile.md`），额外找：有开源代码的、和你同一评测环境的、被后续工作当基线的。这三类是最值得临摹的对象。

### 3. 跨领域检索：找机制
把困难改写成去掉本领域名词的结构描述（例如"候选集合是对的，集合内部的次序学不出来"），然后到至少三个把这种结构当核心问题的子领域去搜。每条检索式用 `--probe` 声明目标子领域。
```
python3 "$SKILL_DIR/scripts/lit.py" search "learning to rank with privileged information" --regime cross --probe "information retrieval"
```
结构描述怎么写、怎么选子领域，见 `references/query-craft.md`。

### 4. 筛选
对每篇候选做决定并写理由，同时标角色：
- `near-miss`：同问题、差一点就解决了你的困难的工作
- `mechanism-source`：打算借用其机制的工作
- `baseline`：要比较的对象
- `background`：只提供背景
```
python3 "$SKILL_DIR/scripts/lit.py" screen arxiv:2401.00001 include --role near-miss --reason "同环境同设定，用图注意力选人，未处理并列候选"
```
排除也要写理由。"不相关"不算理由，写清楚是问题不同、设定不同，还是只是标题相似。

### 5. 精读并登记
对每篇 `near-miss` 和 `mechanism-source` 取全文，按 `assets/paper-note-template.md` 写笔记到 `research/lit/papers/<id>.md`，然后登记。`full` 级要求笔记里有至少两个位置锚点（Sec./Eq./Table/Fig.），这是防止只看摘要就当读过。
```
python3 "$SKILL_DIR/scripts/lit.py" read arxiv:2401.00001 --level full
```
精读时带着问题读：它用什么机制对付这个困难？依赖什么假设？评测口径是什么（环境、人数、seed 数、报的是均值还是配对）？它自己承认什么没解决？最后这一项是对标时的入口。

取不到全文的论文不引用。网页检索找到的论文用 `add` 手工登记后再走同样流程。

### 6. 核查与导出
```
python3 "$SKILL_DIR/scripts/lit.py" check --cite research/lit/synthesis.md research/ideas/candidates.md
python3 "$SKILL_DIR/scripts/lit.py" export
```
`check` 的错误必须修（引用了没读的论文、近邻只读了摘要）。警告逐条看：要么补，要么在交付时说明。

## 交付
简短汇报：冻结的问题；检索了多少条、覆盖哪些子领域、有无后端失败；纳入多少篇、其中近邻和机制来源各几篇；最接近的 3–5 篇各一句话说它做了什么、差在哪；台账路径。写明"没检索到直接重合的工作"只代表在这些检索式下没找到，不代表不存在。

下一步通常是 `paper-synthesis`。

## 检索不了的时候
没有网络或后端全部失败时，不产出筛选结论。如实说明，并把已有的检索式和失败信息留在台账里。
