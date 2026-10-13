#!/usr/bin/env python3
"""协议冻结与修订登记。仅依赖标准库。

  freeze  DIR                 对 DIR/PROTOCOL.md 取 SHA256，写 FREEZE.json；已冻结则拒绝
  verify  DIR                 核对 PROTOCOL.md 与全部修订文件的哈希是否与登记一致
  amend   DIR FILE --seen "修订时已看到的数据" --reason "原因"
                              登记一份修订；必须声明当时已看到哪些数据
  lint    DIR                 检查协议是否写了必需的章节

范围：只锁定协议文本和修订文件的哈希。它不检查模板是否真的填完，也不校验协议里列出的权重、数据等资产——
那些哈希要在执行的第一阶段另行核对。
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import sys

REQUIRED = [
    ("主张", r"(主张|研究问题|Claim)"),
    ("不可声称", r"(不可声称|不声称)"),
    ("数据划分", r"(数据划分|划分)"),
    ("对照臂", r"(对照臂|四臂|各臂|臂[（(])"),
    ("裁决条件", r"(裁决|判据|判死)"),
    ("停止条件", r"(自动停止|停止条件)"),
    ("阶段", r"(阶段|Stage)"),
]


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def fpath(d):
    return os.path.join(d, "FREEZE.json")


def load(d):
    if not os.path.exists(fpath(d)):
        sys.exit("尚未冻结: " + d)
    with open(fpath(d), encoding="utf-8") as f:
        return json.load(f)


def lint(d):
    p = os.path.join(d, "PROTOCOL.md")
    if not os.path.exists(p):
        sys.exit("缺少 " + p)
    text = open(p, encoding="utf-8").read()
    missing = [name for name, pat in REQUIRED if not re.search(pat, text)]
    warns = []
    if not re.search(r"(Bonferroni|校正|多重)", text):
        warns.append("没有提到多重比较校正")
    if not re.search(r"(非劣|保持性|不得.*恶化|上界|下界)", text):
        warns.append("没有安全/保持性类的保护条件")
    if not re.search(r"(同数据|同预算|同状态|同梯度)", text):
        warns.append("没有看到'同数据同预算'的对照说明")
    if re.search(r"(待定|TBD|TODO|稍后确定)", text):
        warns.append("协议里还有未定项（待定/TBD/TODO）")
    return missing, warns


def cmd_lint(a):
    missing, warns = lint(a.dir)
    for w in warns:
        print("警告:", w)
    for m in missing:
        print("缺少章节:", m)
    print("lint: 缺 %d 项, %d 警告" % (len(missing), len(warns)))
    return 1 if missing else 0


def cmd_freeze(a):
    if os.path.exists(fpath(a.dir)):
        sys.exit("已冻结，不能重复冻结；需要改动请用 amend")
    missing, warns = lint(a.dir)
    if missing and not a.force:
        sys.exit("协议缺少章节: %s（确认无需时加 --force）" % ", ".join(missing))
    p = os.path.join(a.dir, "PROTOCOL.md")
    rec = {"protocol_sha256": sha(p), "frozen_at": datetime.datetime.now().isoformat(timespec="seconds"),
           "lint_missing": missing, "lint_warnings": warns, "amendments": []}
    with open(fpath(a.dir), "w", encoding="utf-8") as f:
        json.dump(rec, f, ensure_ascii=False, indent=1)
    print("已冻结 PROTOCOL.md")
    print("SHA256", rec["protocol_sha256"])
    return 0


def cmd_amend(a):
    rec = load(a.dir)
    src = a.file if os.path.isabs(a.file) else os.path.join(a.dir, a.file)
    if not os.path.exists(src) and os.path.exists(a.file):
        src = a.file
    if not os.path.exists(src):
        sys.exit("找不到修订文件 " + src)
    root = os.path.realpath(a.dir)
    if os.path.dirname(os.path.realpath(src)) != root:
        sys.exit("修订文件必须直接放在协议目录 %s 里（当前在 %s）。先把它复制进去再登记，否则之后无法校验"
                 % (root, os.path.dirname(os.path.realpath(src))))
    if any(am["file"] == os.path.basename(src) for am in rec["amendments"]):
        sys.exit("同名修订已登记过：%s。修订不可覆盖，另起一个编号" % os.path.basename(src))
    if sha(os.path.join(a.dir, "PROTOCOL.md")) != rec["protocol_sha256"]:
        sys.exit("PROTOCOL.md 已被改动，与冻结哈希不符。修订应写成单独文件，不改协议本体。")
    if len(a.seen.strip()) < 8:
        sys.exit("--seen 必须具体写明修订时已经看到了哪些数据（没看到任何结果也要明说）")
    rec["amendments"].append({"file": os.path.basename(src), "sha256": sha(src), "seen": a.seen, "reason": a.reason,
                              "at": datetime.datetime.now().isoformat(timespec="seconds")})
    with open(fpath(a.dir), "w", encoding="utf-8") as f:
        json.dump(rec, f, ensure_ascii=False, indent=1)
    print("已登记修订 %d: %s" % (len(rec["amendments"]), os.path.basename(src)))
    print("SHA256", rec["amendments"][-1]["sha256"])
    return 0


def cmd_verify(a):
    rec = load(a.dir)
    bad = 0
    cur = sha(os.path.join(a.dir, "PROTOCOL.md"))
    ok = cur == rec["protocol_sha256"]
    bad += not ok
    print("PROTOCOL.md %s  %s" % ("一致" if ok else "不一致!", cur))
    for am in rec["amendments"]:
        p = os.path.join(a.dir, am["file"])
        ok = os.path.exists(p) and sha(p) == am["sha256"]
        bad += not ok
        print("%s %s  （修订时已见: %s）" % (am["file"], "一致" if ok else "不一致或缺失!", am["seen"][:60]))
    print("verify: %s" % ("通过" if not bad else "%d 项不一致" % bad))
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    sub.required = True
    s = sub.add_parser("freeze"); s.add_argument("dir"); s.add_argument("--force", action="store_true"); s.set_defaults(fn=cmd_freeze)
    s = sub.add_parser("verify"); s.add_argument("dir"); s.set_defaults(fn=cmd_verify)
    s = sub.add_parser("lint"); s.add_argument("dir"); s.set_defaults(fn=cmd_lint)
    s = sub.add_parser("amend"); s.add_argument("dir"); s.add_argument("file")
    s.add_argument("--seen", required=True); s.add_argument("--reason", required=True); s.set_defaults(fn=cmd_amend)
    a = ap.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
