#!/usr/bin/env python3
"""基线失败的根状态里，有多少"只换这一步动作、之后仍按基线走"就能成功。

这是事后量：分支结局来自同一个确定性世界的真实续行，机器人决策时看不到。
区间按 episode 整体重采样。用法：rescue_stats.py table.jsonl.gz
"""
import collections, gzip, json, sys
import numpy as np

GROUP = {0: "5人", 1: "5人", 2: "10人", 3: "10人", 4: "20人", 5: "20人"}


def per_row(r):
    """(是否失败, 失败且安全动作内可救, 失败且前5名内可救, 随机安全动作失败率)"""
    ok = np.array([o == "success" for o in r["branch_outcome"]])
    e = np.array(r["eligible"]); s = np.array(r["final_scores"])
    pool = np.where(e)[0]
    top5 = pool[np.argsort(-s[pool])[:5]]
    fail = not ok[r["chosen"]]
    return (float(fail), float(fail and ok[pool].any()), float(fail and ok[top5].any()), 1 - ok[pool].mean())


def stats(M):
    """M: 每行 per_row 的结果，形状 (n, 4)"""
    n = len(M); fail, resc, resc5, rand = M.sum(axis=0)
    return fail / n, resc / max(fail, 1), resc5 / max(fail, 1), rand / n, int(fail)


def main():
    rows = [json.loads(l) for l in gzip.open(sys.argv[1], "rt")]
    rng = np.random.default_rng(0)
    out = {}
    for g in ("5人", "10人", "20人"):
        R = [r for r in rows if GROUP[r["cell"]] == g]
        by = collections.defaultdict(list)
        for r in R:
            by[r["episode"]].append(per_row(r))
        eps = sorted(by)
        point = stats(np.array([x for e in eps for x in by[e]]))
        bs = np.array([stats(np.array([x for e in rng.choice(eps, len(eps)) for x in by[e]]))[:4] for _ in range(2000)])
        lo, hi = np.percentile(bs, [2.5, 97.5], axis=0)
        names = ("基线后续失败率", "失败中换一步安全动作可成功的比例", "失败中基线前5名内可成功的比例", "随机安全动作的失败率")
        out[g] = dict(roots=len(R), episodes=len(eps), failures=point[4],
                      **{k: dict(point=round(point[i], 4), ci95=[round(lo[i], 4), round(hi[i], 4)]) for i, k in enumerate(names)})
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
