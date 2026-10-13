# 数据说明

全部是离线表，不需要仿真器和 GPU。总计约 43 MB。

## data/kda_s443_cf/ —— 主表

来源：CF-Rank 实验 Stage 1 的冻结训练标签。母体 KDA T24 seed 443，
权重 SHA256 `c6cf228f…c23fd`。场景 case 93000–93174 × 六格，每回合均匀随机抽 2 步，
不按结局筛选。由 `tools/build_cf_table.py` 从冻结索引合并，合并时逐项校验
（数组哈希、回报一致、选中即最高分、无干预重放逐位一致），结果在 `MANIFEST.json`。

### table.jsonl.gz（2100 行，每行一个根状态）

| 字段 | 含义 |
|---|---|
| `key` | 主键 `c{格}-k{case}-s{步}` |
| `episode` | 回合标识 `c{格}-k{case}`。**统计时按它聚类，划分训练/验证时按它整体划分** |
| `cell`, `cell_name` | 场景格 0–5 = 5C/5S/10C/10S/20C/20S |
| `chosen` | 母体实际选的候选下标 |
| `final_scores[80]` | 部署打分；被安全过滤的候选是 −1e9 |
| `eligible[80]` | 是否通过安全过滤（与 `final_scores > −1e8` 完全一致） |
| `G_A[80]` | 每个候选的反事实回报：这一步执行它，之后按母体走到结束 |
| `rewards[80]`, `values[80]`, `clearance[80]` | 打分的三个组成量：即时奖励、价值网络输出、一步后的净距 |
| `commands[80]` | 候选的速度指令 (vx, vy) |
| `pred_terminal[80]`, `pred_terminal_type[80]` | 前瞻模型是否预测该候选一步后终止 |
| `true_terminal_step1[80]` | 真实仿真里该候选是否一步后终止 |
| `branch_outcome[80]` | 该分支的最终结局：success / collision / timeout |
| `branch_steps[80]`, `branch_min_clearance[80]` | 该分支的步数和全程最小净距 |
| `episode_outcome`, `episode_length`, `root_step`, `root_return` | 原始回合信息 |

### features_cell{0..5}.npz（网络输入，行顺序由 `key` 数组给出）

| 数组 | 形状 | 含义 |
|---|---|---|
| `key` | (350,) | 与 table 的 `key` 对应 |
| `current_window` | (350, 24, 8, 13) | 当前的历史窗口：24 步 × 8 个槽位 × 13 维 |
| `prefix` | (350, 23, 8, 13) | 候选窗口的前 23 步（所有候选共用） |
| `candidate_last` | (350, 80, 8, 13) | 每个候选一步后的最后一帧；与 `prefix` 拼起来就是价值网络对该候选的输入 |

槽位和 13 维的具体含义以代码为准：公开仓库 `jinglongjiang/KDARL` 的
`CrowdNav/crowd_nav/policy/mamba_rl.py`（编码器）和 `crowd_nav/contracts.py`（特征定义）。
使用前先读代码确认，不要猜。

## 这些表能回答什么，不能回答什么

能：某条"只看根状态信息"的打分或排序规则，在这 2100 个状态上会选哪个候选、
单步 regret 是多少、后续结局如何。

不能：
- 改动之后的闭环表现。回报是在**母体续行**下得到的；策略一变，后面的状态分布就变了。
  查表通过只是进入闭环测试的必要条件。
- 多步改动的累积效果。
- 换了母体权重之后的情况。

## 工具

- `../skills/prescreen/scripts/regret_ruler.py`：量 regret、查规则、比较新旧打分。
  `--cluster episode --key key --group cell --group-map '0,1=5人;2,3=10人;4,5=20人'`
- `tools/rescue_stats.py`：按结局统计"换一步可成功"的比例。
- `tools/build_cf_table.py`：造表脚本，留作记录；原始标签文件不在本仓库。
