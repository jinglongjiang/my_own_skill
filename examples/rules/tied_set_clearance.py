"""示例候选规则：在与最高分相差不超过 eps 的并列集合里，改选净距最大的候选。
用于演示 regret_ruler.py 的 rule 模式；它是一个已知在闭环里净零的规则，适合当阴性回测。"""
EPS = 1e-3


def rule(record, feasible):
    score = record["final_scores"]
    clearance = record["clearance"]
    top = max(score[i] for i in feasible)
    tied = [i for i in feasible if score[i] >= top - EPS]
    if len(tied) < 2:
        return max(feasible, key=lambda i: score[i])
    return max(tied, key=lambda i: clearance[i])
