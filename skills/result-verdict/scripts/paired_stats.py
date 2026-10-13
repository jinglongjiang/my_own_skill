#!/usr/bin/env python3
"""逐例配对裁决：两臂在同一批 case 上的结局与回报对比。

用法:
  paired_stats.py --a 基线文件... --b 候选文件... [选项]
文件可以是 JSON（--json-path 指向 episode 列表）或 CSV（表头含 case/outcome/ret 对应列）。
多个文件按位置配对（A 的第 i 个对 B 的第 i 个，例如同一场景）。同一个 case 出现在多个文件里时，
它们共享同一个世界，不是独立样本：所有检验与区间都以 case 为单位（聚类）计算。

统计目标只有一个：事件比率之差（候选 − 基线），按配对加权，即表里的"差(B−A)"。检验、区间、非劣效判定都针对它：
  - 检验：以 case 为单位的精确符号翻转检验（零假设：两臂在每个 case 内可交换）。每个 case 只出现一次时它就是精确 McNemar。
  - 区间：按 case 聚类的 bootstrap。
  - 小样本保护界：事件太少时 bootstrap 会退化成零宽，这时改用不退化的界（见 guard_bounds）。
"多少个 case 变好、多少个变坏"只作为描述给出，不用来判断平均比率是否改善——多数 case 小幅变好、少数 case 大幅变坏时，两者会相反。
两臂的 case 集合不一致时默认报错退出（缺失的 case 可能正是失败的那些），--allow-missing 才只比交集。
"""
import argparse
import csv
import json
import math
import statistics
import sys

import numpy as np

SMALL = 20  # 某事件上"净变化不为零的聚类"少于这个数时，bootstrap 区间不可信


def load(path, a):
    if path.endswith(".csv"):
        with open(path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
    else:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        for k in [p for p in a.json_path.split(".") if p]:
            d = d[k]
        rows = d
    out = {}
    for i, r in enumerate(rows):
        if a.case not in r or r[a.case] in ("", None):
            sys.exit("%s 第 %d 条缺少 case 字段 '%s'" % (path, i, a.case))
        if a.outcome not in r or r[a.outcome] in ("", None):
            sys.exit("%s 第 %d 条缺少结局字段 '%s'" % (path, i, a.outcome))
        c = str(r[a.case])
        if c in out:
            sys.exit("%s 里 case %s 重复" % (path, c))
        if a.ret in r and r[a.ret] not in ("", None):
            try:
                ret = float(r[a.ret])
            except (TypeError, ValueError):
                sys.exit("%s 第 %d 条的回报 '%s' 不是数值" % (path, i, r[a.ret]))
            if not math.isfinite(ret):
                sys.exit("%s 第 %d 条（case %s）的回报是 NaN 或无穷。回报列给了就必须是有限值；确实没有回报时请去掉这一列"
                         % (path, i, c))
        else:
            ret = None  # 这条记录没有回报字段
        out[c] = (str(r[a.outcome]), ret)
    return out


def _log_binom_pmf(n, k, logp, log1mp):
    return math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1) + k * logp + (n - k) * log1mp


def binom_cdf(k, n, p):
    """P(X <= k)，X ~ Bin(n, p)。对数域求和，n 很大时不溢出。"""
    if k < 0:
        return 0.0
    if k >= n:
        return 1.0
    if p <= 0.0:
        return 1.0
    if p >= 1.0:
        return 0.0
    lp, l1 = math.log(p), math.log1p(-p)
    return min(1.0, sum(math.exp(_log_binom_pmf(n, i, lp, l1)) for i in range(k + 1)))


def mcnemar_exact(b, c):
    """双侧精确符号检验。b、c 为两个方向上的不一致单位数。"""
    n = b + c
    if n == 0:
        return 1.0
    return min(1.0, 2.0 * binom_cdf(min(b, c), n, 0.5))


def cp_upper(x, n, alpha):
    """Clopper-Pearson 单侧上界。"""
    if x >= n:
        return 1.0
    lo, hi = x / float(n), 1.0
    for _ in range(60):
        mid = (lo + hi) / 2.0
        if binom_cdf(x, n, mid) > alpha:
            lo = mid
        else:
            hi = mid
    return hi


def cp_lower(x, n, alpha):
    if x <= 0:
        return 0.0
    lo, hi = 0.0, x / float(n)
    for _ in range(60):
        mid = (lo + hi) / 2.0
        if 1.0 - binom_cdf(x - 1, n, mid) > alpha:
            hi = mid
        else:
            lo = mid
    return lo


def _tango_T(n12, n21, n, delta):
    """Tango (1998) 配对比例差的 score 统计量。delta = p12 - p21。"""
    A = 2.0 * n
    B = -n12 - n21 + (2.0 * n - n12 + n21) * delta
    C = -n21 * delta * (1.0 - delta)
    disc = max(B * B - 4.0 * A * C, 0.0)
    p21 = (math.sqrt(disc) - B) / (2.0 * A)
    var = n * (2.0 * p21 + delta * (1.0 - delta))
    num = n12 - n21 - n * delta
    if var <= 0.0:
        return 0.0 if abs(num) < 1e-12 else math.copysign(float("inf"), num)
    return num / math.sqrt(var)


def score_diff_bounds(b, c, n, z=1.959964):
    """(c-b)/n 的 Tango score 区间。只适用于各配对相互独立（每个 case 只出现一次）的情形。"""
    n12, n21 = c, b
    est = (n12 - n21) / float(n)
    lo, hi = -1.0 + 1e-12, est
    for _ in range(80):
        mid = (lo + hi) / 2.0
        if _tango_T(n12, n21, n, mid) > z:
            lo = mid
        else:
            hi = mid
    lower = hi
    lo, hi = est, 1.0 - 1e-12
    for _ in range(80):
        mid = (lo + hi) / 2.0
        if _tango_T(n12, n21, n, mid) < -z:
            hi = mid
        else:
            lo = mid
    return lower, lo


def signflip_exact(nets):
    """以 case 为单位的精确符号翻转检验，检验"按配对加权的平均差为零"。
    nets: 每个 case 的净变化（整数，候选事件数 − 基线事件数）。零假设下每个 case 的净变化正负等概率。
    用动态规划得到 Σ±|d_k| 的精确分布；所有非零 |d_k| 都是 1 时等于精确 McNemar。"""
    mags = [abs(int(v)) for v in nets if int(v) != 0]
    if not mags:
        return 1.0
    obs = abs(int(sum(int(v) for v in nets)))
    S = sum(mags)
    dist = np.zeros(2 * S + 1)
    dist[S] = 1.0
    for m in mags:
        new = np.zeros_like(dist)
        new[m:] += 0.5 * dist[:-m]
        new[:-m] += 0.5 * dist[m:]
        dist = new
    sums = np.arange(-S, S + 1)
    return float(min(1.0, dist[np.abs(sums) >= obs].sum()))


def guard_bounds(net, sizes, one_sided, z, clustered):
    """事件很少时用的保护界，目标量与点估计相同（按配对加权的比率差）。返回 (下界, 上界, 名称)，单位为比例。
    每个 case 只出现一次：Tango score 区间。
    同一 case 出现多次：一个 case 的净变化不超过它的配对数，所以
        平均差 ≤ (最大簇大小 / 平均簇大小) × P(该 case 净增加)，
    后者用 Clopper-Pearson 上界。簇大小不等时这个系数会自动变大，界不会落到点估计的错误一侧。"""
    K = len(net)
    b, c = int((net < 0).sum()), int((net > 0).sum())
    if not clustered:
        lo, hi = score_diff_bounds(b, c, K, z)
        return lo, hi, "score"
    ratio = float(sizes.max()) / float(sizes.mean())
    hi = min(1.0, ratio * cp_upper(c, K, one_sided))
    lo = max(-1.0, -ratio * cp_upper(b, K, one_sided))
    return lo, hi, "保守"


def boot_mean(mat_by_cluster, n_boot, seed):
    rng = np.random.default_rng(seed)
    sums = np.array([m.sum(axis=0) for m in mat_by_cluster])
    cnts = np.array([len(m) for m in mat_by_cluster], dtype=float)
    k = len(sums)
    idx = rng.integers(0, k, size=(n_boot, k))
    return sums[idx].sum(axis=1) / cnts[idx].sum(axis=1)[:, None]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--a", nargs="+", required=True, help="基线臂文件")
    ap.add_argument("--b", nargs="+", required=True, help="候选臂文件")
    ap.add_argument("--json-path", default="episodes")
    ap.add_argument("--case", default="case")
    ap.add_argument("--outcome", default="outcome")
    ap.add_argument("--ret", default="ret")
    ap.add_argument("--events", default="success,collision,timeout", help="结局取值，第一个视为成功")
    ap.add_argument("--family", type=int, help="Bonferroni 的检验个数，默认 = 事件数")
    ap.add_argument("--alpha", type=float, default=0.05, help="双侧显著性水平；区间为 1-alpha，非劣效/保持性用单侧 alpha/2")
    ap.add_argument("--ni", action="append", default=[], help="非劣效：事件:界值pp，例如 collision:2.0（候选−基线的单侧上界须小于界值）")
    ap.add_argument("--hold", action="append", default=[], help="保持性：事件:界值pp，例如 success:-1.0（单侧下界须大于界值）")
    ap.add_argument("--allow-missing", action="store_true", help="两臂 case 集合不一致时只比交集（默认报错）")
    ap.add_argument("--boot", type=int, default=10000)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--json-out")
    a = ap.parse_args()
    if len(a.a) != len(a.b):
        sys.exit("--a 与 --b 的文件数必须相同（按位置配对）")
    if not 0.0 < a.alpha < 1.0:
        sys.exit("--alpha 必须在 0 与 1 之间")
    events = a.events.split(",")
    fam = a.family or len(events)
    one_sided = a.alpha / 2.0
    z = statistics.NormalDist().inv_cdf(1.0 - one_sided)
    qlo, qhi = 100.0 * one_sided, 100.0 * (1.0 - one_sided)
    lvl = "%g%%" % (100.0 * (1.0 - a.alpha))

    pairs, missing = [], []
    for fa, fb in zip(a.a, a.b):
        A, B = load(fa, a), load(fb, a)
        only_a, only_b = sorted(set(A) - set(B)), sorted(set(B) - set(A))
        if only_a or only_b:
            missing.append((fa, fb, len(only_a), len(only_b), (only_a + only_b)[:5]))
        for c in sorted(set(A) & set(B)):
            pairs.append((c, A[c][0], B[c][0], A[c][1], B[c][1]))
    if missing:
        for fa, fb, na, nb, ex in missing:
            print("case 集合不一致：%s 独有 %d 个，%s 独有 %d 个（例如 %s）" % (fa, na, fb, nb, ", ".join(ex)), file=sys.stderr)
        if not a.allow_missing:
            sys.exit("两臂的 case 不完全相同。缺失的 case 可能正是失败或未跑完的那些，不能默认忽略；"
                     "确认可以只比交集时加 --allow-missing")
    n = len(pairs)
    if n == 0:
        sys.exit("没有配对的 case")
    unknown = {o for p in pairs for o in (p[1], p[2])} - set(events)
    if unknown:
        sys.exit("出现未声明的结局取值: %s（用 --events 声明）" % sorted(unknown))

    clusters = {}
    for i, p in enumerate(pairs):
        clusters.setdefault(p[0], []).append(i)
    K = len(clusters)
    clustered = K < n
    res = {"n_pairs": n, "n_clusters": K, "clustered": clustered, "alpha": a.alpha, "events": {},
           "missing_cases": [{"a": m[0], "b": m[1], "only_a": m[2], "only_b": m[3]} for m in missing]}
    print("配对 %d 例，%d 个 case 聚类%s%s\n" % (
        n, K, "（同一 case 出现在多个文件，全部推断以 case 为单位）" if clustered else "",
        "；已按 --allow-missing 只比交集" if missing else ""))
    print("%-10s %9s %9s" % ("", "基线A", "候选B"))
    for e in events:
        ra = np.mean([p[1] == e for p in pairs]); rb = np.mean([p[2] == e for p in pairs])
        print("%-10s %8.2f%% %8.2f%%" % (e, 100 * ra, 100 * rb))
    n_none = sum(1 for p in pairs for v in (p[3], p[4]) if v is None)
    if n_none == 0:
        has_ret = True
        ra_ = np.array([p[3] for p in pairs], dtype=float); rb_ = np.array([p[4] for p in pairs], dtype=float)
        print("%-10s %9.4f %9.4f" % ("回报均值", ra_.mean(), rb_.mean()))
    elif n_none == 2 * n:
        has_ret = False
        print("（两臂都没有回报列 '%s'，跳过回报比较）" % a.ret)
    else:
        sys.exit("回报列 '%s' 只在部分记录里出现（缺 %d / 共 %d）：无法做配对比较，请补齐或整列去掉" % (a.ret, n_none, 2 * n))

    cols = [np.array([(p[2] == e) - (p[1] == e) for p in pairs], dtype=float) for e in events]
    if has_ret:
        cols.append(rb_ - ra_)
    M = np.stack(cols, axis=1)
    by_cluster = [M[idx] for idx in clusters.values()]
    bs = boot_mean(by_cluster, a.boot, a.seed)

    sizes = np.array([len(m) for m in by_cluster], dtype=float)
    print("\n统计目标：差(B−A) = 事件比率之差，按配对加权。p 值检验的是这个差是否为零（以 case 为单位的精确符号翻转检验）。")
    print("事件          差(B−A) pp   bootstrap %s        保护界 %s            精确p    校正p(×%d)  过校正   变差/变好的case数" % (lvl, lvl, fam))
    guard = {}
    for j, e in enumerate(events):
        net = np.array([m[:, j].sum() for m in by_cluster])
        b, c = int((net < 0).sum()), int((net > 0).sum())
        pval = signflip_exact(net)
        padj = min(1.0, pval * fam)
        est = float(M[:, j].mean())
        lo, hi = np.percentile(bs[:, j], [qlo, qhi])
        glo, ghi, gname = guard_bounds(net, sizes, one_sided, z, clustered)
        # 任何界都不允许落在点估计的错误一侧
        lo, hi = min(lo, est), max(hi, est)
        glo, ghi = min(glo, est), max(ghi, est)
        small = (b + c) < SMALL
        guard[e] = (100 * glo, 100 * ghi, small, gname)
        print("%-10s   %+9.2f   [%+6.2f, %+6.2f]   [%+6.2f, %+6.2f] %-5s  %8.4f  %8.4f    %s      %d 减 / %d 增" % (
            e, 100 * est, 100 * lo, 100 * hi, 100 * glo, 100 * ghi, gname, pval, padj, "是" if padj < a.alpha else "否", b, c))
        if small:
            print("           ↑ 该事件有净变化的 case 只有 %d 个（<%d）：bootstrap 区间不可信（零事件时宽度为零），以保护界为准" % (b + c, SMALL))
        res["events"][e] = {"diff_pp": 100 * est, "ci_bootstrap_pp": [float(100 * lo), float(100 * hi)],
                            "ci_guard_pp": [float(100 * glo), float(100 * ghi)], "guard_kind": gname, "small_sample": bool(small),
                            "p_exact_signflip": pval, "p_bonferroni": padj, "significant": bool(padj < a.alpha),
                            "cases_event_decreased": b, "cases_event_increased": c}
    print("'减/增'是该事件净减少、净增加的 case 个数，只作描述：多数 case 小幅变好、少数 case 大幅变坏时，case 个数的方向与平均差可以相反。")
    print("区间半宽（bootstrap）：" + "，".join(
        "%s ±%.1f pp" % (e, (res["events"][e]["ci_bootstrap_pp"][1] - res["events"][e]["ci_bootstrap_pp"][0]) / 2.0) for e in events)
        + "。这是区间的宽度，不是功效意义上的最小可检出效应；后者需要另做功效分析。")
    if clustered:
        print("聚类数据（簇大小 %d–%d）：保护界 = (最大簇/平均簇) × '净增 case 比例'的精确上界，很保守，只在小样本时用于判定。" % (sizes.min(), sizes.max()))

    if has_ret:
        j = len(events)
        lo, hi = np.percentile(bs[:, j], [qlo, qhi])
        alo, ahi = np.percentile(bs[:, j], [100 * a.alpha / fam / 2, 100 * (1 - a.alpha / fam / 2)])
        print("\n回报配对差(B−A)：均值 %+.5f，中位 %+.5f，%s区间 [%+.5f, %+.5f]，校正后 %.4g%%区间 [%+.5f, %+.5f]" % (
            M[:, j].mean(), np.median(M[:, j]), lvl, lo, hi, 100 * (1 - a.alpha / fam), alo, ahi))
        res["return"] = {"mean_diff": float(M[:, j].mean()), "median_diff": float(np.median(M[:, j])),
                         "ci": [float(lo), float(hi)], "ci_adjusted": [float(alo), float(ahi)],
                         "adjusted_lower_gt_0": bool(alo > 0)}

    def bound(spec, upper):
        e, _, m = spec.partition(":")
        if e not in events:
            sys.exit("未知事件 " + e)
        try:
            margin = float(m)
        except ValueError:
            sys.exit("界值写法应为 事件:数值，例如 collision:2.0")
        j = events.index(e)
        est = 100.0 * float(M[:, j].mean())
        qb = np.percentile(bs[:, j], qhi if upper else qlo) * 100
        qb = max(qb, est) if upper else min(qb, est)
        glo, ghi, small, gname = guard[e]
        qg = ghi if upper else glo
        if clustered:
            q, used = (qg, gname + "界") if small else (qb, "聚类 bootstrap")
        else:
            q = max(qb, qg) if upper else min(qb, qg)
            used = "bootstrap 与 score 中更保守者"
        assert (q >= est - 1e-9) if upper else (q <= est + 1e-9), "界落在了点估计的错误一侧"
        ok = q < margin if upper else q > margin
        print("%s %s：差(B−A)的单侧 %.4g%% %s界 = %+.2f pp（%s；bootstrap %+.2f / %s %+.2f），界值 %+.2f pp → %s" % (
            "非劣效" if upper else "保持性", e, 100 * (1 - one_sided), "上" if upper else "下", q, used, qb, gname, qg, margin,
            "满足" if ok else "不满足"))
        if not ok and (qb < margin if upper else qb > margin):
            print("    ↑ 单看 bootstrap 会判满足；事件太少，bootstrap 低估了不确定性，需要更多 case")
        res.setdefault("bounds", []).append({"event": e, "kind": "ni" if upper else "hold", "bound_pp": float(q),
                                             "method": used, "bootstrap_bound_pp": float(qb), "guard_bound_pp": float(qg),
                                             "margin_pp": margin, "satisfied": bool(ok)})
    if a.ni or a.hold:
        print()
    for s in a.ni:
        bound(s, True)
    for s in a.hold:
        bound(s, False)

    print("\n结局转移（行=基线A，列=候选B；按配对计数）")
    print("%-10s" % "" + "".join("%10s" % e for e in events))
    trans = {}
    for ea in events:
        row = [sum(1 for p in pairs if p[1] == ea and p[2] == eb) for eb in events]
        trans[ea] = dict(zip(events, row))
        print("%-10s" % ea + "".join("%10d" % v for v in row))
    res["transitions"] = trans
    disc = sum(1 for p in pairs if p[1] != p[2])
    print("\n结局不一致的配对：%d/%d（%.1f%%）。不一致率高而净差接近零 = 改动很多、净效果为零。" % (disc, n, 100.0 * disc / n))
    res["discordant_rate"] = disc / float(n)
    if a.json_out:
        with open(a.json_out, "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=1)
        print("已写出", a.json_out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
