#!/usr/bin/env python3
"""方向台账：登记、改状态、列表、查重。仅依赖标准库。

  add   --title T --keywords "k1,k2" [--axis 轴] [--status 进行中]      新增方向，返回编号
  set   ID 状态 --reason "依据" [--evidence 路径]                         改状态（进行中/通过/已杀/搁置）
  list  [--status 已杀]                                                 列表
  dup   "一段描述新想法的文字"                                            与已有方向比对，提示相似者及其状态
  axes                                                                  按"轴"汇总各状态的数量（看零结果是否集中在同一条轴）
都接受 --file（默认 research/directions.jsonl）。同一时间只应有一个进程写这个文件（没有加锁）。
"""
import argparse
import datetime
import json
import os
import re
import sys

STATUSES = ["进行中", "通过", "已杀", "搁置"]


def load(p):
    if not os.path.exists(p):
        return []
    with open(p, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def save(p, rows):
    os.makedirs(os.path.dirname(p) or ".", exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    os.replace(tmp, p)


def tokens(text):
    text = text.lower()
    toks = set(re.findall(r"[a-z0-9][a-z0-9\-]{1,}", text))
    for run in re.findall(r"[一-鿿]+", text):  # 中文按二元组
        toks.update(run[i:i + 2] for i in range(len(run) - 1))
    return toks


def cmd_add(a):
    rows = load(a.file)
    nid = "C%02d" % (max([int(r["id"][1:]) for r in rows] or [0]) + 1)
    rows.append({"id": nid, "title": a.title, "keywords": [k.strip() for k in a.keywords.split(",") if k.strip()],
                 "axis": a.axis or "", "status": a.status, "reason": "", "evidence": "",
                 "history": [{"status": a.status, "at": datetime.date.today().isoformat(), "reason": "新增", "evidence": ""}]})
    save(a.file, rows)
    print(nid)


def cmd_set(a):
    rows = load(a.file)
    for r in rows:
        if r["id"] == a.id:
            if a.status == "搁置" and "解除" not in a.reason:
                sys.exit("搁置必须在 --reason 里写明解除条件（包含'解除'二字）")
            ev = a.evidence or r.get("evidence", "")
            r.update({"status": a.status, "reason": a.reason, "evidence": ev})
            # 历史里每一条都带当时的证据位置；之后证据路径变了，旧的定位仍然查得到
            r["history"].append({"status": a.status, "at": datetime.date.today().isoformat(), "reason": a.reason,
                                 "evidence": ev})
            save(a.file, rows)
            print(a.id, "->", a.status)
            return 0
    sys.exit("没有 " + a.id)


def cmd_list(a):
    for r in load(a.file):
        if a.status and r["status"] != a.status:
            continue
        print("%s  %-4s  %-10s  %s  | %s" % (r["id"], r["status"], r.get("axis", ""), r["title"], r["reason"]))


def cmd_dup(a):
    q = tokens(a.text)
    if not q:
        sys.exit("描述为空")
    hits = []
    for r in load(a.file):
        t = tokens(r["title"] + " " + " ".join(r["keywords"]))
        if not t:
            continue
        common = q & t
        s = len(common) / float(min(len(q), len(t)))
        # 宁可多报：查重漏掉一个已杀方向的代价远大于多看一眼
        if len(common) >= 2 and s >= a.threshold:
            hits.append((s, r))
    hits.sort(key=lambda x: -x[0])
    if not hits:
        print("未发现相似方向（阈值 %.2f）。这只是关键词比对，仍需人工对照 RECORD.md。" % a.threshold)
        return 0
    for s, r in hits:
        flag = "  ← 已杀，重提前须说明与上次死因无关" if r["status"] == "已杀" else ""
        print("%.2f  %s  %s  %s | %s%s" % (s, r["id"], r["status"], r["title"], r["reason"], flag))
    return 3 if any(r["status"] == "已杀" for _, r in hits) else 0


def cmd_axes(a):
    agg = {}
    for r in load(a.file):
        d = agg.setdefault(r.get("axis") or "(未标轴)", {s: 0 for s in STATUSES})
        d[r["status"]] += 1
    print("%-14s" % "轴" + "".join("%8s" % s for s in STATUSES))
    for ax, d in sorted(agg.items()):
        print("%-14s" % ax + "".join("%8d" % d[s] for s in STATUSES))
        if d["已杀"] >= 3 and d["通过"] == 0:
            print("    ↑ 这条轴上已杀 %d 个且无一通过：换候选之前先问余量是否在这条轴上" % d["已杀"])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    sub.required = True

    def mk(name, fn):
        s = sub.add_parser(name)
        s.add_argument("--file", default="research/directions.jsonl")
        s.set_defaults(fn=fn)
        return s
    s = mk("add", cmd_add); s.add_argument("--title", required=True); s.add_argument("--keywords", default="")
    s.add_argument("--axis"); s.add_argument("--status", choices=STATUSES, default="进行中")
    s = mk("set", cmd_set); s.add_argument("id"); s.add_argument("status", choices=STATUSES)
    s.add_argument("--reason", required=True); s.add_argument("--evidence")
    s = mk("list", cmd_list); s.add_argument("--status", choices=STATUSES)
    s = mk("dup", cmd_dup); s.add_argument("text"); s.add_argument("--threshold", type=float, default=0.15)
    mk("axes", cmd_axes)
    a = ap.parse_args()
    return a.fn(a) or 0


if __name__ == "__main__":
    sys.exit(main())
