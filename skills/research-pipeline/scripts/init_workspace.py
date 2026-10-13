#!/usr/bin/env python3
"""创建研究工作区骨架。已存在的文件不覆盖。

用法: python3 init_workspace.py [目录=research] [--line 研究线名称]
"""
import argparse
import datetime
import os
import sys

STATE = """# 研究状态

更新日期：{today}

## 研究线：{line}
- 当前阶段：0 定靶子
- 当前候选：无
- 下一步动作：用 prescreen 的靶子模式量出余量，写入 TARGET.md
- 阻塞项：无
- 跳过的默认：无
- 最近一个实验数字的日期：无

## 一句话问题
（待填：输入是什么、期望输出是什么、现有方法在哪种条件下不行）
"""

RECORD = """# 研究记录

## 1. 实验台账
| # | 实验 | 目录 | 证据类 | 结果 | 限制 |
|---|---|---|---|---|---|

## 2. 方向状态
| 编号 | 方向 | 状态 | 依据 | 日期 |
|---|---|---|---|---|
状态只用：进行中 / 通过 / 已杀 / 搁置（写明解除条件）

## 3. 资产
（权重及哈希、数据集、可复用脚本、保留的测试块）

## 4. 噪声底
（同配置跨 seed 的各指标波动：均值与最大值。裁决时用来判断差异是否超出噪声）

## 5. 工程缺陷与已知陷阱

## 6. 教训
（每条写成"下次在什么情况下应该怎么做"）
"""

TARGET = """# 靶子

状态：未测

## 余量在哪
## 多大（点估计、区间、尾部集中度）
## 怎么量的（数据来源、口径、脚本）
## 尺子的资格（阳性对照是否看得见、样本量、适用范围）
## 不能由此得出的结论
"""

FILES = {
    "STATE.md": STATE,
    "RECORD.md": RECORD,
    "TARGET.md": TARGET,
    "directions.jsonl": "",
    "claims.md": "# 主张—证据表\n",
    "ideas/candidates.md": "# 候选卡\n",
    "lit/screened.md": "# 文献筛选结果\n",
    "lit/synthesis.md": "# 文献整合\n",
}
DIRS = ["lit/papers", "ideas", "prescreen", "protocols", "handoffs", "verdicts"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", nargs="?", default="research")
    ap.add_argument("--line", default="主线")
    a = ap.parse_args()
    today = datetime.date.today().isoformat()
    made, kept = [], []
    for d in DIRS:
        os.makedirs(os.path.join(a.root, d), exist_ok=True)
    for rel, body in FILES.items():
        p = os.path.join(a.root, rel)
        os.makedirs(os.path.dirname(p) or ".", exist_ok=True)
        if os.path.exists(p):
            kept.append(rel)
            continue
        with open(p, "w", encoding="utf-8") as f:
            f.write(body.format(today=today, line=a.line) if "{today}" in body else body)
        made.append(rel)
    print("工作区:", os.path.abspath(a.root))
    print("新建:", ", ".join(made) if made else "无")
    print("保留未动:", ", ".join(kept) if kept else "无")
    return 0


if __name__ == "__main__":
    sys.exit(main())
