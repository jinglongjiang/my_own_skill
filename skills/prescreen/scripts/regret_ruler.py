#!/usr/bin/env python3
"""反事实查表尺：用"每个状态下每个候选动作的真实回报"表，量基线余量并离线筛候选规则。

输入：JSONL 或 JSONL.GZ，每行一个决策状态，至少包含
  - 候选打分数组（部署策略实际用来排序的分数，--score，默认 final_scores）
  - 候选真实回报数组（--ret，默认 G_A；全部候选都要有，包括被过滤的）
可选字段：实际选中的下标（--chosen，默认取打分最大者）、分组字段（--group）、聚类字段（--cluster）、主键（--key）。

子命令：
  target   量靶子：基线 regret、相对随机的消除率及区间、尾部集中度、top-k 重排序上限
  rule     查一条"只改排序规则"的候选：--rule 文件.py:函数名
           函数签名 f(record: dict, feasible: list[int]) -> int（返回选中的候选下标）
  compare  查一个"改了打分"的候选（换了输入或换了权重）：--alt 文件提供同一批状态上的新打分
  channel  实测作用通道：新旧打分之差在存活候选之间的离散程度，相对原第一二名间距有多大

回报表是在基线策略续行下得到的，所以这里量的是"这一步换个选择、之后仍按基线走"的单步 regret。
输入有问题（字段缺失、主键重复、非有限数值、选中了被过滤的动作）时直接报错退出，不带着坏数据出结论。
"""
import argparse
import gzip
import hashlib
import importlib.util
import json
import sys

import numpy as np


def read_records(paths):
    out = []
    for p in paths:
        op = gzip.open if p.endswith(".gz") else open
        with op(p, "rt", encoding="utf-8") as f:
            for ln, line in enumerate(f, 1):
                line = line.strip()
                if line:
                    try:
                        out.append(json.loads(line))
                    except ValueError:
                        sys.exit("%s 第 %d 行不是合法 JSON" % (p, ln))
    return out


def parse_group_map(spec):
    m, order = {}, []
    if not spec:
        return m, order
    for part in spec.split(";"):
        if "=" not in part:
            sys.exit("--group-map 写法应为 '0,1=名称;2,3=名称'")
        ks, name = part.split("=", 1)
        if name not in order:
            order.append(name)
        for k in ks.split(","):
            m[k.strip()] = name
    return m, order


def make_key(r, fields, where):
    vals = []
    for k in fields:
        if k not in r or r[k] is None:
            sys.exit("%s 缺少主键字段 '%s'" % (where, k))
        vals.append(str(r[k]))
    return tuple(vals)


class State(object):
    __slots__ = ("rec", "score", "ret", "feas", "base", "best", "group", "cluster", "key")


def build(records, a):
    gmap, order = parse_group_map(a.group_map)
    keyf = [k for k in a.key.split(",") if k] if a.key else []
    states, skipped, seen, dup = [], 0, set(), {}
    for i, r in enumerate(records):
        where = "第 %d 条记录" % (i + 1)
        for fld in (a.score, a.ret):
            if fld not in r:
                sys.exit("%s 缺少字段 '%s'" % (where, fld))
        s = State()
        s.rec = r
        s.score = np.asarray(r[a.score], dtype=float)
        s.ret = np.asarray(r[a.ret], dtype=float)
        if s.score.ndim != 1 or s.score.shape != s.ret.shape:
            sys.exit("%s：打分与回报必须是等长的一维数组" % where)
        if not np.isfinite(s.score).all():
            sys.exit("%s：打分里有 NaN 或无穷（被过滤的候选请用一个很小的有限值表示）" % where)
        if not np.isfinite(s.ret).all():
            sys.exit("%s：回报里有 NaN 或无穷。回报表必须对全部候选给出有限值" % where)
        s.feas = np.where(s.score > a.mask_below)[0]
        if a.group:
            if a.group not in r or r[a.group] is None:
                sys.exit("%s 缺少分组字段 '%s'" % (where, a.group))
            g = str(r[a.group])
            s.group = gmap.get(g, g)
        else:
            s.group = "all"
        if a.cluster:
            if a.cluster not in r or r[a.cluster] is None:
                sys.exit("%s 缺少聚类字段 '%s'（不会退回按状态统计）" % (where, a.cluster))
            s.cluster = str(r[a.cluster])
        else:
            # 没有聚类字段时每个状态自成一类。用内容哈希而不是行号做标识，结果才不依赖输入行的顺序
            h = hashlib.md5(json.dumps(r, sort_keys=True).encode("utf-8")).hexdigest()
            dup[h] = dup.get(h, 0) + 1
            s.cluster = "%s#%d" % (h, dup[h])
        if keyf:
            s.key = make_key(r, keyf, where)
            if s.key in seen:
                sys.exit("主键重复：%s（%s）" % (s.key, where))
            seen.add(s.key)
        else:
            s.key = ("#%d" % i,)
        if s.feas.size == 0:
            if a.mode in ("compare", "channel"):
                sys.exit("%s：原打分下没有任何可行候选，无法确定基线动作。部署时全部候选都被过滤的状态，请按部署的实际回退行为"
                         "把候选标为可行后再造表" % where)
            skipped += 1
            continue
        if s.feas.size < 2 and a.mode in ("target", "rule"):
            # 只有一个可行候选：这一步没有选择余地，量余量和查排序规则时不计入。
            # compare/channel 不能跳过——新打分可能让别的候选变得可行，从而真的改变动作。
            skipped += 1
            continue
        if a.chosen and a.chosen in r and r[a.chosen] is not None:
            s.base = int(r[a.chosen])
            if s.base not in set(s.feas.tolist()):
                sys.exit("%s：记录的选中动作 %d 是被过滤的候选或越界。检查 --chosen 字段与 --mask-below" % (where, s.base))
        else:
            s.base = int(s.feas[np.argmax(s.score[s.feas])])
        s.best = float(s.ret[s.feas].max())
        states.append(s)
    groups = [g for g in order if any(s.group == g for s in states)] or sorted({s.group for s in states})
    for s in states:
        if s.group not in groups:
            groups.append(s.group)
    return states, groups, skipped


def load_alt(a):
    keyf = [k for k in a.key.split(",") if k]
    fld = a.alt_score or a.score
    alt = {}
    for i, r in enumerate(read_records(a.alt)):
        where = "新打分文件第 %d 条" % (i + 1)
        k = make_key(r, keyf, where)
        if k in alt:
            sys.exit("新打分文件主键重复：%s" % (k,))
        if fld not in r:
            sys.exit("%s 缺少字段 '%s'" % (where, fld))
        v = np.asarray(r[fld], dtype=float)
        if not np.isfinite(v).all():
            sys.exit("%s：新打分里有 NaN 或无穷" % where)
        alt[k] = v
    return alt


def cluster_boot(values_by_cluster, stat, n_boot, seed_seq):
    rng = np.random.default_rng(seed_seq)
    k = len(values_by_cluster)
    out = np.empty(n_boot)
    for b in range(n_boot):
        idx = rng.integers(0, k, k)
        out[b] = stat(np.concatenate([values_by_cluster[j] for j in idx], axis=0))
    return out


def by_cluster(states, cols):
    d = {}
    for s, row in zip(states, cols):
        d.setdefault(s.cluster, []).append(row)
    return [np.asarray(d[k], dtype=float) for k in sorted(d)]  # 排序：结果不依赖输入行的顺序


def ci(x, lo=2.5, hi=97.5):
    x = x[np.isfinite(x)]
    return (float(np.percentile(x, lo)), float(np.percentile(x, hi))) if x.size else (float("nan"),) * 2


def elim(m):  # m[:,0]=策略 regret, m[:,1]=随机 regret
    den = m[:, 1].mean()
    return 1.0 - m[:, 0].mean() / den if den > 0 else float("nan")


def cmd_target(a, states, groups):
    res = {}
    print("靶子测量：基线策略的单步 regret（越小越好）与相对随机的消除率（越大越好）\n")
    hdr = "%-8s%5s%6s %9s %9s %9s | %8s %-18s | %7s %7s %7s | %7s %7s"
    print(hdr % ("组", "n", "聚类", "基线均值", "中位", "随机均值", "消除率", "95%区间", "去最大1", "去最大3", "中位口径", "已最优%", "最大1例占比"))
    boots = {}
    for gi, g in enumerate(groups):
        S = [s for s in states if s.group == g]
        net = np.array([s.best - s.ret[s.base] for s in S])
        rnd = np.array([s.best - s.ret[s.feas].mean() for s in S])
        m = np.stack([net, rnd], axis=1)
        bc = by_cluster(S, m)
        # 每个组用各自独立的随机流；否则组间差的区间会因为共用同一串重采样下标而被错误地耦合
        bs = cluster_boot(bc, elim, a.boot, [a.seed, 11, gi])
        boots[g] = bs
        order = np.argsort(net)[::-1]
        d1 = elim(m[order[1:]]) if len(S) > 1 else float("nan")
        d3 = elim(m[order[3:]]) if len(S) > 3 else float("nan")
        med = 1.0 - np.median(net) / np.median(rnd) if np.median(rnd) > 0 else float("nan")
        tot = net.sum()
        top1 = net[order[0]] / tot if tot > 0 else 0.0
        lo, hi = ci(bs)
        print("%-8s%5d%6d %9.5f %9.5f %9.5f | %7.1f%% [%5.1f%%, %5.1f%%]   | %6.1f%% %6.1f%% %6.1f%% | %6.1f%% %6.1f%%" % (
            g, len(S), len(bc), net.mean(), np.median(net), rnd.mean(), 100 * elim(m), 100 * lo, 100 * hi,
            100 * d1, 100 * d3, 100 * med, 100 * np.mean(net <= 1e-12), 100 * top1))
        res[g] = {"n": len(S), "n_clusters": len(bc), "regret_mean": float(net.mean()), "regret_median": float(np.median(net)),
                  "random_regret_mean": float(rnd.mean()), "elimination": float(elim(m)), "elimination_ci95": [lo, hi],
                  "elimination_drop_top1": float(d1), "elimination_drop_top3": float(d3),
                  "elimination_median_based": float(med), "share_optimal": float(np.mean(net <= 1e-12)),
                  "top1_share_of_total_regret": float(top1),
                  "top3_share_of_total_regret": float(net[order[:3]].sum() / tot) if tot > 0 else 0.0}
    print("\n头部重排序上限：只在基线打分的前 k 名里换成真实最优，能回收多少 regret（事后上限，不是可达增益）")
    print("%-8s %8s %-18s %8s" % ("组", "top-5", "95%区间", "top-10"))
    rec = lambda mm: 1.0 - mm[:, 1].mean() / mm[:, 0].mean() if mm[:, 0].mean() > 0 else float("nan")
    for gi, g in enumerate(groups):
        S = [s for s in states if s.group == g]
        net = np.array([s.best - s.ret[s.base] for s in S])
        tk = {}
        for k in (5, 10):
            tk[k] = np.array([s.best - s.ret[s.feas[np.argsort(-s.score[s.feas])][:k]].max() for s in S])
        bs = cluster_boot(by_cluster(S, np.stack([net, tk[5]], axis=1)), rec, a.boot, [a.seed, 13, gi])
        lo, hi = ci(bs)
        r5 = rec(np.stack([net, tk[5]], axis=1)); r10 = rec(np.stack([net, tk[10]], axis=1))
        print("%-8s %7.1f%% [%5.1f%%, %5.1f%%]   %7.1f%%" % (g, 100 * r5, 100 * lo, 100 * hi, 100 * r10))
        res[g].update({"top5_recoverable": float(r5), "top5_recoverable_ci95": [lo, hi], "top10_recoverable": float(r10)})
    if len(groups) >= 2:
        g0, g1 = groups[0], groups[-1]
        d = boots[g0] - boots[g1]
        lo, hi = ci(d)
        print("\n组间差（%s − %s）的消除率：%.1f 个百分点，95%%区间 [%.1f, %.1f]，P(差>0)=%.1f%%（两组独立重采样）" % (
            g0, g1, 100 * np.nanmean(d), 100 * lo, 100 * hi, 100 * np.mean(d > 0)))
        res["_group_diff"] = {"groups": [g0, g1], "diff": float(np.nanmean(d)), "ci95": [lo, hi]}
    if not a.cluster:
        print("\n注意：未指定 --cluster，每个状态当作一个独立样本。同一 episode 取了多个状态时必须指定聚类字段，否则区间偏窄。")
    print("\n读数提示：区间很宽或最大 1 例占比很高时，点估计不能单独引用；消除率在不同口径间差别大时全部报出。")
    return res


def eval_choice(states, groups, pick, a, label):
    """pick(s) -> (候选下标, 该状态参与比较的可行集合)。输出相对基线的配对差，以及分数带内随机对照。"""
    res = {}
    print("%-8s%5s %8s | %9s %9s %9s | %-34s | %-34s" % (
        "组", "n", "改变率", "基线", label, "带内随机", "基线−候选 [95%区间]（正=候选更好）", "随机−候选 [95%区间]（正=胜过随机）"))
    for gi, g in enumerate(groups):
        S = [s for s in states if s.group == g]
        base, cand, rnd, chg, kept = [], [], [], [], []
        for s in S:
            got = pick(s)
            if got is None:  # 按 --empty-policy skip 排除
                continue
            kept.append(s)
            c, pool = got
            c = int(c)
            if c < 0 or c >= s.ret.size:
                sys.exit("候选返回了越界的下标 %d（组 %s）" % (c, g))
            best = float(s.ret[pool].max())  # 新旧可行集合的并集上的最优，两臂用同一个参照
            base.append(best - s.ret[s.base])
            cand.append(best - s.ret[c])
            changed = c != s.base
            chg.append(changed)
            if changed:
                band = s.feas[s.score[s.feas] >= s.score[c] - 1e-15] if c in set(s.feas.tolist()) else s.feas
                rnd.append(best - s.ret[band].mean())
            else:
                rnd.append(best - s.ret[s.base])
        if not kept:
            print("%-8s    0  （该组没有可比较的状态）" % g)
            continue
        S = kept
        base, cand, rnd = map(np.asarray, (base, cand, rnd))
        d1 = np.stack([base - cand], axis=1); d2 = np.stack([rnd - cand], axis=1)
        mean0 = lambda mm: mm[:, 0].mean()
        b1 = cluster_boot(by_cluster(S, d1), mean0, a.boot, [a.seed, 17, gi])
        b2 = cluster_boot(by_cluster(S, d2), mean0, a.boot, [a.seed, 19, gi])
        (l1, h1), (l2, h2) = ci(b1), ci(b2)
        print("%-8s%5d %7.1f%% | %9.5f %9.5f %9.5f | %+9.5f [%+.5f, %+.5f]      | %+9.5f [%+.5f, %+.5f]" % (
            g, len(S), 100 * np.mean(chg), base.mean(), cand.mean(), rnd.mean(),
            (base - cand).mean(), l1, h1, (rnd - cand).mean(), l2, h2))
        v = "检出改善" if l1 > 0 else ("检出变差" if h1 < 0 else "未检出差异")
        v2 = "胜过带内随机" if l2 > 0 else ("不如带内随机" if h2 < 0 else "与带内随机不可区分")
        print("         → %s；%s" % (v, v2))
        res[g] = {"n": len(S), "change_rate": float(np.mean(chg)), "regret_base": float(base.mean()),
                  "regret_candidate": float(cand.mean()), "regret_band_random": float(rnd.mean()),
                  "base_minus_candidate": float((base - cand).mean()), "ci95": [l1, h1],
                  "random_minus_candidate": float((rnd - cand).mean()), "ci95_vs_random": [l2, h2],
                  "reading": v, "reading_vs_random": v2}
    print("\n'带内随机'：在原打分不低于候选所选动作的可行候选里均匀取。它控制的是'改到了哪个分数带'，不是严格匹配改动幅度。")
    print("读数提示：'未检出差异'不等于'无效'——看区间宽度。改变率高而差异为零，说明规则改了决策但没有选到更好的动作。")
    return res


def cmd_rule(a, states, groups):
    path, _, fn = a.rule.partition(":")
    spec = importlib.util.spec_from_file_location("candidate_rule", path)
    if spec is None:
        sys.exit("无法加载规则文件 " + path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    f = getattr(mod, fn or "rule", None)
    if f is None:
        sys.exit("规则文件里没有函数 " + (fn or "rule"))

    def pick(s):
        c = int(f(s.rec, s.feas.tolist()))
        if c not in set(s.feas.tolist()):
            sys.exit("候选规则返回了不可行的下标 %d（状态 %s）。规则只能在传入的可行集合里选" % (c, s.key))
        return c, s.feas
    return eval_choice(states, groups, pick, a, "候选规则")


def align_alt(states, alt):
    missing = [s.key for s in states if s.key not in alt]
    if missing:
        sys.exit("新打分文件缺少 %d 个状态（例如 %s）；两边必须是同一批状态" % (len(missing), missing[0]))
    for s in states:
        if alt[s.key].shape != s.score.shape:
            sys.exit("状态 %s 的新旧打分长度不一致" % (s.key,))


def cmd_compare(a, states, groups):
    alt = load_alt(a)
    align_alt(states, alt)
    stat = {"set_changed": 0, "outside": 0, "empty": 0}

    n_empty = sum(1 for s in states if not (alt[s.key] > a.mask_below).any())
    if n_empty and a.empty_policy == "error":
        sys.exit("有 %d 个状态在新打分下没有任何可行候选。这时策略实际会选什么取决于部署代码的回退行为，工具不替你假设。\n"
                 "  部署确实会退回原动作 → 加 --empty-policy keep\n"
                 "  想把这些状态排除在比较之外 → 加 --empty-policy skip（会单独报告个数）\n"
                 "  部署有别的回退规则 → 按那个规则把回退动作标为可行后重新生成新打分" % n_empty)

    def pick(s):
        sc = alt[s.key]
        nf = np.where(sc > a.mask_below)[0]
        if nf.size == 0:
            stat["empty"] += 1
            return None if a.empty_policy == "skip" else (s.base, s.feas)
        if not np.array_equal(nf, s.feas):
            stat["set_changed"] += 1
        c = int(nf[np.argmax(sc[nf])])
        if c not in set(s.feas.tolist()):
            stat["outside"] += 1
        return c, np.union1d(s.feas, nf)
    res = eval_choice(states, groups, pick, a, "新打分")
    n = len(states)
    print("\n可行集合：%d/%d 个状态的新旧可行集合不同；其中 %d 个状态新选中的动作原先被过滤；%d 个状态新打分下无可行候选（%s）。" % (
        stat["set_changed"], n, stat["outside"], stat["empty"],
        {"keep": "按 --empty-policy keep 视为退回原动作", "skip": "按 --empty-policy skip 已排除", "error": "无"}[a.empty_policy]))
    if stat["set_changed"]:
        print("集合不同的状态以新旧集合的并集为参照计算两臂的 regret，新选中的动作按它真实的回报计入，不会被悄悄换回原动作。")
    res["_feasible_set"] = dict(stat, n=n)
    return res


def cmd_channel(a, states, groups):
    alt = load_alt(a)
    align_alt(states, alt)
    tot_empty = sum(1 for s in states if not (alt[s.key] > a.mask_below).any())
    if tot_empty and a.empty_policy == "error":
        sys.exit("有 %d 个状态在新打分下没有任何可行候选。用 --empty-policy keep（部署会退回原动作）或 skip（排除）明确处理方式" % tot_empty)
    res = {}
    print("作用通道实测：Δ(a) = 新打分 − 原打分。离散度在新旧都可行的候选上计算；第一名更换按各自完整的可行集合判断。\n")
    print("%-8s%5s | %12s %12s %10s %10s | %12s | %8s %10s %12s" % (
        "组", "n", "Δ离散度中位", "原1-2名间距", "比值中位", "比值>1占比", "Δ均值(共模)", "第一名更换", "集合变化", "原第一名被滤"))
    for g in groups:
        S = [s for s in states if s.group == g]
        spread, gap, ratio, common, flip = [], [], [], [], []
        set_chg = top_masked = zero_gap = no_common = n_empty = 0
        for s in S:
            new = alt[s.key]
            nf = np.where(new > a.mask_below)[0]
            if nf.size == 0:
                n_empty += 1
                if a.empty_policy == "skip":
                    continue
            old_top = int(s.feas[np.argmax(s.score[s.feas])])
            if not np.array_equal(nf, s.feas):
                set_chg += 1
            if old_top not in set(nf.tolist()):
                top_masked += 1
            new_top = int(nf[np.argmax(new[nf])]) if nf.size else old_top
            flip.append(new_top != old_top)
            f = np.intersect1d(s.feas, nf)
            if f.size < 2:
                no_common += 1
                continue
            d = new[f] - s.score[f]
            top = np.sort(s.score[s.feas])[::-1]
            sp, gp = float(d.std()), float(top[0] - top[1])
            spread.append(sp); gap.append(gp); common.append(float(d.mean()))
            if gp > 0:
                ratio.append(sp / gp)
            else:
                zero_gap += 1  # 原本并列：间距为零，比值没有意义，单独计数
        if not flip:
            continue
        ratio = np.asarray(ratio)
        med = float(np.median(ratio)) if ratio.size else float("nan")
        print("%-8s%5d | %12.3e %12.3e %10.3f %9.1f%% | %12.3e | %7.1f%% %9.1f%% %11.1f%%" % (
            g, len(S), np.median(spread) if spread else float("nan"), np.median(gap) if gap else float("nan"), med,
            100 * np.mean(ratio > 1) if ratio.size else float("nan"), np.mean(common) if common else float("nan"),
            100 * np.mean(flip), 100.0 * set_chg / len(S), 100.0 * top_masked / len(S)))
        if zero_gap or no_common or n_empty:
            print("         原第一二名并列（间距为零，不计入比值）%d 个；新旧共同可行候选不足 2 个 %d 个；新打分下无可行候选 %d 个（%s）" % (
                zero_gap, no_common, n_empty, "已排除" if a.empty_policy == "skip" else "视为退回原动作"))
        res[g] = {"n": len(S), "delta_spread_median": float(np.median(spread)) if spread else None,
                  "top_gap_median": float(np.median(gap)) if gap else None, "ratio_median": med if ratio.size else None,
                  "share_ratio_gt_1": float(np.mean(ratio > 1)) if ratio.size else None,
                  "common_shift_mean": float(np.mean(common)) if common else None,
                  "argmax_flip_rate": float(np.mean(flip)), "feasible_set_changed": set_chg,
                  "old_top_masked": top_masked, "zero_gap_states": zero_gap, "too_few_common": no_common}
    print("\n读数：比值远小于 1、第一名几乎不换、集合不变 → 在这批状态上基本是共模改动（实测结论，只对这批状态和这份权重成立）。"
          "\n      比值接近或大于 1，或集合发生变化 → 通道存在，接着用 compare 看换到的动作是否更好。"
          "\n      共模部分（Δ均值）再大也不影响排序。")
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=["target", "rule", "compare", "channel"])
    ap.add_argument("files", nargs="+")
    ap.add_argument("--score", default="final_scores")
    ap.add_argument("--ret", default="G_A")
    ap.add_argument("--chosen", default="chosen")
    ap.add_argument("--mask-below", type=float, default=-1e8, help="打分低于此值视为被过滤的不可行候选")
    ap.add_argument("--group", help="分组字段名")
    ap.add_argument("--group-map", help="合并分组，如 '0,1=5人;2,3=10人;4,5=20人'")
    ap.add_argument("--cluster", help="bootstrap 聚类字段（同一 episode 多个状态时填 case 之类）")
    ap.add_argument("--key", default="", help="状态主键字段，逗号分隔（compare/channel 必填）")
    ap.add_argument("--rule", help="rule 模式：文件.py:函数名")
    ap.add_argument("--alt", nargs="*", help="compare/channel 模式：新打分文件")
    ap.add_argument("--alt-score", help="新打分字段名，默认同 --score")
    ap.add_argument("--empty-policy", choices=["error", "keep", "skip"], default="error",
                    help="compare/channel：新打分下没有可行候选的状态怎么处理。默认报错；keep=部署会退回原动作；skip=排除")
    ap.add_argument("--boot", type=int, default=10000)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--json-out")
    a = ap.parse_args()
    if a.mode == "rule" and not a.rule:
        sys.exit("rule 模式需要 --rule 文件.py:函数名")
    if a.mode in ("compare", "channel") and (not a.alt or not a.key):
        sys.exit("%s 模式需要 --alt 和 --key" % a.mode)
    states, groups, skipped = build(read_records(a.files), a)
    if not states:
        sys.exit("没有可用状态")
    print("读入 %d 个状态（%s %d 个）\n" % (len(states), "跳过没有选择余地的" if a.mode in ("target", "rule") else "跳过", skipped))
    res = {"target": cmd_target, "rule": cmd_rule, "compare": cmd_compare, "channel": cmd_channel}[a.mode](a, states, groups)
    if a.json_out:
        with open(a.json_out, "w", encoding="utf-8") as f:
            json.dump({"mode": a.mode, "files": a.files, "n_states": len(states), "skipped": skipped, "result": res},
                      f, ensure_ascii=False, indent=1)
        print("\n已写出", a.json_out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
