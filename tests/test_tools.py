#!/usr/bin/env python3
"""工具回归测试。只用合成数据，不依赖任何外部文件或网络。运行: python3 tests/test_tools.py
每个测试对应一个曾经出过的问题；全部通过才允许说"工具已验证"。"""
import json
import os
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SK = os.path.join(ROOT, "skills")
PS = os.path.join(SK, "result-verdict/scripts/paired_stats.py")
RR = os.path.join(SK, "prescreen/scripts/regret_ruler.py")
JW = os.path.join(SK, "method-build/scripts/jobwatch.py")
LIT = os.path.join(SK, "paper-scout/scripts/lit.py")
LED = os.path.join(SK, "research-ledger/scripts/ledger.py")
FRZ = os.path.join(SK, "protocol-freeze/scripts/freeze.py")
T = tempfile.mkdtemp(prefix="mos_test_")
results = []


def run(*args):
    p = subprocess.run([sys.executable] + list(args), stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    return p.returncode, p.stdout, p.stderr


def wjson(name, episodes):
    p = os.path.join(T, name)
    with open(p, "w") as f:
        json.dump({"episodes": episodes}, f)
    return p


def wjsonl(name, rows):
    p = os.path.join(T, name)
    with open(p, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    return p


def check(name, cond, detail=""):
    results.append((name, bool(cond)))
    print("%s  %s%s" % ("通过" if cond else "失败", name, ("  ← " + detail) if (detail and not cond) else ""))


def line(out, prefix, must=""):
    for l in out.splitlines():
        if l.startswith(prefix) and must in l:
            return l
    return ""


def evline(out, event):
    """检验表里某个事件的那一行（比率表里也有同名行，用方括号区分）。"""
    return line(out, event + " ", "[")


# ---------------- paired_stats ----------------
ok = [{"case": i, "outcome": "success", "ret": 0.5} for i in range(30)]
one = [dict(r) for r in ok]; one[0] = dict(one[0], outcome="timeout")
a, b = wjson("ok.json", ok), wjson("one.json", one)
rc, out, _ = run(PS, "--a", *([a] * 10), "--b", *([b] * 10))
check("配对统计：同一 case 重复 10 次不被当成 10 个独立样本", "30 个 case 聚类" in out and " 1.0000 " in evline(out, "success"), out[:300])

z = wjson("z.json", [{"case": i, "outcome": "success", "ret": 0.5} for i in range(20)])
rc, out, _ = run(PS, "--a", *([z] * 10), "--b", *([z] * 10), "--ni", "collision:2.0")
check("配对统计：20 个零事件 case 重复后非劣效不通过", "不满足" in line(out, "非劣效"), line(out, "非劣效"))
rc, out, _ = run(PS, "--a", z, "--b", z, "--ni", "collision:2.0")
check("配对统计：单文件 20 例零事件非劣效不通过", "不满足" in line(out, "非劣效"))

rc, out, err = run(PS, "--a", wjson("m2.json", ok[:2]), "--b", wjson("m1.json", ok[:1]))
check("配对统计：两臂 case 不一致时报错退出", rc != 0 and "不完全相同" in err, err[:200])
rc, out, err = run(PS, "--a", os.path.join(T, "m2.json"), "--b", os.path.join(T, "m1.json"), "--allow-missing")
check("配对统计：--allow-missing 时只比交集并注明", rc == 0 and "只比交集" in out)

big_a = [{"case": i, "outcome": "success" if i < 1200 else "timeout", "ret": 0.1} for i in range(2400)]
big_b = [{"case": i, "outcome": "timeout" if i < 1200 else "success", "ret": 0.1} for i in range(2400)]
rc, out, err = run(PS, "--a", wjson("ba.json", big_a), "--b", wjson("bb.json", big_b), "--boot", "500")
check("配对统计：1200 个不一致配对不溢出", rc == 0 and "1200" in evline(out, "success"), err[-200:])

mix_a = [{"case": i, "outcome": "success" if i % 5 else "collision", "ret": 0.3} for i in range(200)]
mix_b = [{"case": i, "outcome": "success" if i % 4 else "timeout", "ret": 0.3} for i in range(200)]
fa, fb = wjson("xa.json", mix_a), wjson("xb.json", mix_b)
_, o1, _ = run(PS, "--a", fa, "--b", fb, "--alpha", "0.05", "--ni", "timeout:50")
_, o2, _ = run(PS, "--a", fa, "--b", fb, "--alpha", "0.2", "--ni", "timeout:50")
check("配对统计：--alpha 同时改变事件区间与非劣效界", evline(o1, "success") != evline(o2, "success") and evline(o1, "success") != "" and line(o1, "非劣效") != line(o2, "非劣效"))
check("配对统计：不再把区间半宽叫作最小可检出效应", "最小可检出的差" not in o1 and "不是功效意义上" in o1)

sys.path.insert(0, os.path.dirname(PS))
import paired_stats as ps  # noqa: E402
lo, hi = ps.score_diff_bounds(0, 0, 20)
zz = 1.959964
check("配对统计：零事件 score 区间等于闭式解", abs(hi - zz * zz / (20 + zz * zz)) < 1e-6 and abs(lo + hi) < 1e-9)
check("配对统计：精确 p 与已知值一致（23/18 → 0.5327）", abs(ps.mcnemar_exact(23, 18) - 0.532709) < 1e-5)

# 第三轮审查的反例
fa, fb = [[], []], [[], []]
for c in range(99):  # 66 个 case 各救回 1 例，33 个 case 各破坏 2 例：平均成功率差恰为 0
    for f in range(2):
        if c < 66:
            x, y = ("timeout", "success") if f == 0 else ("success", "success")
        else:
            x, y = "success", "timeout"
        fa[f].append({"case": c, "outcome": x, "ret": 0.1}); fb[f].append({"case": c, "outcome": y, "ret": 0.1})
rc, out, _ = run(PS, "--a", wjson("sa0.json", fa[0]), wjson("sa1.json", fa[1]), "--b", wjson("sb0.json", fb[0]), wjson("sb1.json", fb[1]), "--boot", "1000")
l = evline(out, "success")
check("配对统计：多数 case 变好但平均差为 0 时不判显著", "+0.00" in l and " 1.0000 " in l and "否" in l and "33 减 / 66 增" in l, l)

nf = 40  # 不等大小簇：1 个 case 出现 40 次且全部变成碰撞，另 119 个 case 各出现 1 次且不变
UA, UB = [[] for _ in range(nf)], [[] for _ in range(nf)]
for f in range(nf):
    UA[f].append({"case": 0, "outcome": "success", "ret": 0.1}); UB[f].append({"case": 0, "outcome": "collision", "ret": 0.1})
for c in range(1, 120):
    UA[0].append({"case": c, "outcome": "success", "ret": 0.1}); UB[0].append({"case": c, "outcome": "success", "ret": 0.1})
ua = [wjson("ua%d.json" % f, UA[f]) for f in range(nf)]; ub = [wjson("ub%d.json" % f, UB[f]) for f in range(nf)]
rc, out, _ = run(PS, "--a", *ua, "--b", *ub, "--ni", "collision:2.0", "--boot", "1000", "--json-out", os.path.join(T, "u.json"))
uj = json.load(open(os.path.join(T, "u.json")))
bd = uj["bounds"][0]; est = uj["events"]["collision"]["diff_pp"]
check("配对统计：不等大小簇下非劣效上界不低于点估计且不通过", est > 20 and bd["bound_pp"] >= est and not bd["satisfied"], "est=%.2f bound=%.2f" % (est, bd["bound_pp"]))
for e_, v in uj["events"].items():
    if not (v["ci_guard_pp"][0] <= v["diff_pp"] + 1e-9 <= v["ci_guard_pp"][1] + 2e-9 and v["ci_bootstrap_pp"][0] <= v["diff_pp"] + 1e-9 <= v["ci_bootstrap_pp"][1] + 2e-9):
        check("配对统计：区间包含点估计（%s）" % e_, False, str(v))
        break
else:
    check("配对统计：所有区间都包含点估计", True)

nan_f = wjson("nan.json", [{"case": i, "outcome": "success", "ret": float("nan")} for i in range(5)])
rc, out, err = run(PS, "--a", nan_f, "--b", nan_f)
check("配对统计：回报列全为 NaN 时报错而不是说'未提供'", rc != 0 and "NaN" in err, err[:120])
noret = wjson("noret.json", [{"case": i, "outcome": "success"} for i in range(5)])
rc, out, err = run(PS, "--a", noret, "--b", noret)
check("配对统计：确实没有回报列时正常跳过", rc == 0 and "没有回报列" in out)
rc, out, err = run(PS, "--a", noret, "--b", wjson("hasret.json", [{"case": i, "outcome": "success", "ret": 0.1} for i in range(5)]))
check("配对统计：回报列只在一臂出现时报错", rc != 0 and "部分记录" in err)

import itertools  # noqa: E402
okk = True
for nets in ([2, 2, 2, -1], [3, -1, -1, 2, -4, 1, 1], [1, 1, 1, -2, 5, -3], [1] * 6 + [-1] * 2):
    mags = [abs(v) for v in nets if v]; obs = abs(sum(nets))
    brute = sum(abs(sum(sg * m for sg, m in zip(sgn, mags))) >= obs for sgn in itertools.product((1, -1), repeat=len(mags))) / float(2 ** len(mags))
    okk = okk and abs(ps.signflip_exact(nets) - brute) < 1e-12
check("配对统计：符号翻转检验与穷举一致", okk)
check("配对统计：单位幅度时符号翻转检验等于 McNemar", abs(ps.signflip_exact([1] * 18 + [-1] * 23) - ps.mcnemar_exact(23, 18)) < 1e-12)

# ---------------- regret_ruler ----------------
import random  # noqa: E402
random.seed(3)
rows = [{"k": i, "case": i // 2, "final_scores": [random.random() for _ in range(6)], "G_A": [random.random() for _ in range(6)]} for i in range(40)]
A = [dict(r, g="a") for r in rows] + [dict(r, g="b", k=r["k"] + 100) for r in rows]
B = A[::-1]
_, o1, _ = run(RR, "target", wjsonl("gA.jsonl", A), "--group", "g", "--key", "k", "--boot", "1500")
_, o2, _ = run(RR, "target", wjsonl("gB.jsonl", B), "--group", "g", "--key", "k", "--boot", "1500")
check("反事实尺：调换输入行顺序结果不变", line(o1, "组间差") == line(o2, "组间差") and line(o1, "组间差") != "", line(o1, "组间差") + " | " + line(o2, "组间差"))
check("反事实尺：两个相同的组独立重采样，组间差区间不是零宽", "[0.0, 0.0]" not in line(o1, "组间差"))

base = [{"k": i, "case": i // 2, "final_scores": [1.0, 0.9, 0.5], "G_A": [0.2, 0.6, 0.1]} for i in range(20)]
bad = {
    "回报含 NaN": (wjsonl("nan.jsonl", [dict(base[0], G_A=[0.2, float("nan"), 0.1])] + base[1:]), []),
    "选中了被过滤的动作": (wjsonl("ch.jsonl", [dict(base[0], final_scores=[1.0, 0.9, -1e9], chosen=2)] + base[1:]), []),
    "主键重复": (wjsonl("dup.jsonl", base + [base[0]]), ["--key", "k"]),
    "主键字段缺失": (wjsonl("nok.jsonl", [{x: v for x, v in base[0].items() if x != "k"}] + base[1:]), ["--key", "k"]),
    "聚类字段不存在": (wjsonl("b.jsonl", base), ["--cluster", "nope"]),
    "分组字段不存在": (os.path.join(T, "b.jsonl"), ["--group", "nope"]),
}
for name, (f, extra) in bad.items():
    rc, out, err = run(RR, "target", f, "--boot", "200", *extra)
    check("反事实尺：%s时报错退出" % name, rc != 0 and err.strip() != "", "rc=%d" % rc)
rc, out, _ = run(RR, "target", os.path.join(T, "b.jsonl"), "--cluster", "case", "--boot", "200")
check("反事实尺：聚类字段生效（20 个状态 → 10 个聚类）", "   20    10 " in line(out, "all"), line(out, "all"))

mb = wjsonl("mb.jsonl", [{"k": i, "final_scores": [1.0, 0.9, -1e9], "G_A": [0.2, 0.6, 0.9]} for i in range(10)])
ma = wjsonl("ma.jsonl", [{"k": i, "final_scores": [-1e9, 0.5, 0.8]} for i in range(10)])
rc, out, _ = run(RR, "compare", mb, "--alt", ma, "--key", "k", "--boot", "200")
check("反事实尺：新选中的动作原先被过滤时不退回原动作", "100.0%" in line(out, "all") and "10 个状态新选中的动作原先被过滤" in out, out[-300:])
rc, out, _ = run(RR, "channel", mb, "--alt", ma, "--key", "k")
check("反事实尺：原第一名被过滤时 channel 报告更换", line(out, "all").count("100.0%") >= 3, line(out, "all"))
rc, out, err = run(RR, "compare", mb, "--alt", wjsonl("ad.jsonl", [{"k": i, "final_scores": [1, 0.9, -1e9]} for i in range(10)] + [{"k": 0, "final_scores": [0, 1, -1e9]}]), "--key", "k")
check("反事实尺：新打分文件主键重复时报错退出", rc != 0 and "重复" in err)
zb = wjsonl("zb.jsonl", [{"k": i, "final_scores": [1.0, 1.0, 0.3], "G_A": [0.2, 0.6, 0.1]} for i in range(5)])
za = wjsonl("za.jsonl", [{"k": i, "final_scores": [1.5, 1.5, 0.8]} for i in range(5)])
rc, out, _ = run(RR, "channel", zb, "--alt", za, "--key", "k")
check("反事实尺：并列候选统一加常数不报无穷大比值", "inf" not in out and "并列（间距为零，不计入比值）5 个" in out, out[-300:])
cm = wjsonl("cm.jsonl", [dict(r, final_scores=[x + 0.37 for x in r["final_scores"]]) for r in rows])
rc, out, _ = run(RR, "channel", wjsonl("rows.jsonl", rows), "--alt", cm, "--key", "k")
check("反事实尺：纯共模偏移 → 第一名更换 0%", "0.0%" in line(out, "all") and rc == 0)
orc = wjsonl("orc.jsonl", [{"k": r["k"], "final_scores": r["G_A"]} for r in rows])
rc, out, _ = run(RR, "compare", os.path.join(T, "rows.jsonl"), "--alt", orc, "--key", "k", "--boot", "500")
check("反事实尺：把真实回报当新打分 → 检出改善", "检出改善" in out)
rule = os.path.join(T, "rule.py")
open(rule, "w").write("def rule(rec, feas):\n    return max(feas, key=lambda i: rec['final_scores'][i])\n")
rc, out, _ = run(RR, "rule", os.path.join(T, "rows.jsonl"), "--rule", rule + ":rule", "--boot", "200")
check("反事实尺：与基线相同的规则 → 改变率 0%", "0.0%" in line(out, "all") and "未检出差异" in out)

s1b = wjsonl("s1b.jsonl", [{"k": i, "final_scores": [1.0, -1e9, -1e9], "G_A": [0.2, 0.1, 0.9]} for i in range(8)])
s1a = wjsonl("s1a.jsonl", [{"k": i, "final_scores": [0.5, -1e9, 0.8]} for i in range(8)])
rc, out, _ = run(RR, "compare", s1b, "--alt", s1a, "--key", "k", "--boot", "200")
check("反事实尺：原集合只有 1 个动作、新打分换了动作的状态不被跳过", "读入 8 个状态" in out and "100.0%" in line(out, "all") and "检出改善" in out, out[:200])
eb = wjsonl("eb.jsonl", [{"k": i, "final_scores": [1.0, 0.9, 0.1], "G_A": [0.2, 0.6, 0.1]} for i in range(6)])
ea = wjsonl("ea.jsonl", [{"k": i, "final_scores": [-1e9, -1e9, -1e9] if i < 2 else [0.1, 0.9, 0.2]} for i in range(6)])
rc, out, err = run(RR, "compare", eb, "--alt", ea, "--key", "k")
check("反事实尺：新打分下无可行候选时默认报错", rc != 0 and "回退" in err)
rc, out, err = run(RR, "channel", eb, "--alt", ea, "--key", "k")
check("反事实尺：channel 遇到空集合默认报错", rc != 0)
rc, out, _ = run(RR, "compare", eb, "--alt", ea, "--key", "k", "--boot", "200", "--empty-policy", "skip")
check("反事实尺：--empty-policy skip 排除并报告", rc == 0 and line(out, "all").split()[1] == "4" and "已排除" in out)
rc, out, _ = run(RR, "compare", eb, "--alt", ea, "--key", "k", "--boot", "200", "--empty-policy", "keep")
check("反事实尺：--empty-policy keep 保留并注明", rc == 0 and line(out, "all").split()[1] == "6" and "视为退回原动作" in out)
e0 = wjsonl("e0.jsonl", [{"k": 0, "final_scores": [-1e9, -1e9], "G_A": [0.1, 0.2]}])
rc, out, err = run(RR, "compare", e0, "--alt", e0, "--key", "k")
check("反事实尺：原打分下无可行候选时 compare 报错", rc != 0 and "基线动作" in err)

# ---------------- jobwatch ----------------
d = os.path.join(T, "j1")
rc, _, _ = run(JW, "start", "--dir", d, "--", sys.executable, "-c", 'import sys; print("a b", len(sys.argv)); sys.exit(5)')
rc2, out, _ = run(JW, "wait", "--dir", d, "--timeout", "20", "--poll", "0.2")
check("任务监控：带引号和空格的命令原样执行并记下退出码", rc == 0 and rc2 == 1 and open(os.path.join(d, "log.txt")).read().strip() == "a b 1")
d = os.path.join(T, "j2")
ps_ = [subprocess.Popen([sys.executable, JW, "start", "--dir", d, "--", "sleep", "1"], stdout=subprocess.PIPE, stderr=subprocess.PIPE) for _ in range(4)]
codes = sorted(p.wait() for p in ps_)
check("任务监控：并发抢同一目录只有一个成功", codes.count(0) == 1, str(codes))
d = os.path.join(T, "j3"); os.makedirs(d); open(os.path.join(d, "exit_code"), "w").write("0\n")
rc, _, err = run(JW, "start", "--dir", d, "--", "false")
check("任务监控：目录里有旧退出码时拒绝启动", rc != 0 and not os.path.exists(os.path.join(d, "pid.json")))
sys.path.insert(0, os.path.dirname(JW))
import jobwatch as jw  # noqa: E402
pid = os.fork()
if pid == 0:
    os._exit(0)
time.sleep(0.3)
st, start = jw.proc_stat(pid)
check("任务监控：僵尸进程不算存活", st == "Z" and not jw.alive({"pid": pid, "starttime": start}))
os.waitpid(pid, 0)
d = os.path.join(T, "j4"); run(JW, "start", "--dir", d, "--", "echo hi; sleep 20")
time.sleep(2.5)
rc, out, _ = run(JW, "status", "--dir", d, "--stall", "1")
check("任务监控：日志长时间不更新判为疑似卡住", rc == 2)
import signal  # noqa: E402
os.killpg(json.load(open(os.path.join(d, "pid.json")))["pid"], signal.SIGKILL); time.sleep(0.5)
rc, out, _ = run(JW, "status", "--dir", d)
check("任务监控：被杀后无退出码不当作完成", rc == 3)
d = os.path.join(T, "j5"); run(JW, "start", "--dir", d, "--", "echo ok"); time.sleep(0.8)
rc, out, _ = run(JW, "status", "--dir", d)
check("任务监控：正常结束退出码 0", rc == 0 and "已结束，退出码 0" in out)

# ---------------- lit ----------------
ld = os.path.join(T, "lit")
run(LIT, "init", "--dir", ld); run(LIT, "add", "--dir", ld, "--id", "oa:W1", "--title", "Old title")
run(LIT, "screen", "oa:W1", "include", "--reason", "r", "--role", "near-miss", "--dir", ld)
rc, _, err = run(LIT, "read", "oa:W1", "--level", "full", "--dir", ld)
check("文献台账：没有笔记不能登记阅读", rc != 0)
note = os.path.join(ld, "papers", "oa_W1.md"); open(note, "w").write("只看了摘要\n")
rc, _, _ = run(LIT, "read", "oa:W1", "--level", "full", "--dir", ld)
check("文献台账：锚点不足不能登记 full", rc != 0)
open(note, "w").write("Sec. 3 的机制；Table 2 的结果\n")
rc, _, _ = run(LIT, "read", "oa:W1", "--level", "full", "--dir", ld)
check("文献台账：有锚点的笔记可以登记 full", rc == 0)
sys.path.insert(0, os.path.dirname(LIT))
import argparse  # noqa: E402
import lit  # noqa: E402
lit.BACKENDS["fake"] = lambda q, n, since: [{"id": "oa:W1", "title": "Brand new title", "year": 2025, "date": None, "authors": [],
                                             "venue": "", "abstract": "", "url": "", "cited_by": 3}]
_o = sys.stdout; sys.stdout = open(os.devnull, "w")
lit.cmd_search(argparse.Namespace(dir=ld, query="x", regime="same", probe=None, source="fake", n=5, since=None))
sys.stdout = _o
p = json.load(open(os.path.join(ld, "ledger.json")))["papers"]["oa:W1"]
check("文献台账：同一 ID 标题变化后筛选与阅读记录保留", p["title"] == "Brand new title" and p["screen"] == "include" and p["read"]["level"] == "full")
cite = os.path.join(T, "c.md"); open(cite, "w").write("见 [@oa:W1] 与 [@arxiv:0000.00000]\n")
rc, out, _ = run(LIT, "check", "--dir", ld, "--cite", cite)
check("文献台账：引用了台账里没有的论文时报错", rc == 1 and "arxiv:0000.00000" in out)
os.remove(note)
rc, out, _ = run(LIT, "check", "--dir", ld)
check("文献台账：笔记被删后核查报错", rc == 1 and "笔记文件不存在" in out)

# ---------------- ledger ----------------
lf = os.path.join(T, "dir.jsonl")
run(LED, "add", "--file", lf, "--title", "并列集合内用净距仲裁", "--keywords", "tied set,clearance,并列,净距", "--axis", "部署期规则")
run(LED, "set", "C01", "已杀", "--file", lf, "--reason", "净零", "--evidence", "path/A")
run(LED, "set", "C01", "进行中", "--file", lf, "--reason", "重开", "--evidence", "path/B")
h = json.loads(open(lf).read())["history"]
check("方向台账：历史保留每次的证据位置", [x["evidence"] for x in h] == ["", "path/A", "path/B"])
rc, _, _ = run(LED, "set", "C01", "搁置", "--file", lf, "--reason", "等结果")
check("方向台账：搁置必须写解除条件", rc != 0)
run(LED, "set", "C01", "已杀", "--file", lf, "--reason", "净零")
rc, out, _ = run(LED, "dup", "--file", lf, "在打分并列的候选里按净距重新仲裁")
check("方向台账：换了说法的已杀方向能被查到", rc == 3 and "C01" in out)

# ---------------- freeze ----------------
fd_ = os.path.join(T, "prot"); os.makedirs(fd_)
open(os.path.join(fd_, "PROTOCOL.md"), "w").write("主张 不可声称 数据划分 对照臂 裁决条件 自动停止 阶段 Bonferroni 非劣效 同数据\n")
rc, out, _ = run(FRZ, "freeze", fd_)
check("协议冻结：冻结成功", rc == 0)
rc, _, _ = run(FRZ, "freeze", fd_)
check("协议冻结：不能重复冻结", rc != 0)
ext = os.path.join(T, "AMENDMENT-1.md"); open(ext, "w").write("改排程\n")
rc, _, err = run(FRZ, "amend", fd_, ext, "--seen", "仅停止报告，无任何结果数据", "--reason", "x")
check("协议冻结：协议目录外的修订被拒绝", rc != 0 and "协议目录" in err)
open(os.path.join(fd_, "AMENDMENT-1.md"), "w").write("改排程\n")
rc, _, _ = run(FRZ, "amend", fd_, "AMENDMENT-1.md", "--seen", "无", "--reason", "x")
check("协议冻结：修订必须写明已看到的数据", rc != 0)
rc, _, _ = run(FRZ, "amend", fd_, "AMENDMENT-1.md", "--seen", "仅停止报告，无任何结果数据", "--reason", "x")
rc2, out, _ = run(FRZ, "verify", fd_)
check("协议冻结：目录内修订登记后可校验", rc == 0 and rc2 == 0)
open(os.path.join(fd_, "PROTOCOL.md"), "a").write("x")
rc, _, _ = run(FRZ, "verify", fd_)
check("协议冻结：协议被改动后校验失败", rc == 1)

# ---------------- init_workspace ----------------
ws = os.path.join(T, "ws")
rc, out, _ = run(os.path.join(SK, "research-pipeline/scripts/init_workspace.py"), ws)
open(os.path.join(ws, "STATE.md"), "a").write("自定义内容\n")
rc2, out2, _ = run(os.path.join(SK, "research-pipeline/scripts/init_workspace.py"), ws)
check("工作区：重复初始化不覆盖已有文件", rc == 0 and rc2 == 0 and "自定义内容" in open(os.path.join(ws, "STATE.md")).read())

bad_n = sum(1 for _, okk in results if not okk)
print("\n共 %d 项，失败 %d 项" % (len(results), bad_n))
sys.exit(1 if bad_n else 0)
