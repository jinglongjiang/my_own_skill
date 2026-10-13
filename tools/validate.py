#!/usr/bin/env python3
"""项目自检：每个技能的 frontmatter、正文长度、正文里提到的相对文件是否存在、脚本能否编译、shared 副本是否最新。"""
import filecmp
import os
import py_compile
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SK = os.path.join(ROOT, "skills")
errs, warns = [], []
names = sorted(os.listdir(SK))
for n in names:
    d = os.path.join(SK, n)
    p = os.path.join(d, "SKILL.md")
    if not os.path.exists(p):
        errs.append("%s: 缺 SKILL.md" % n); continue
    text = open(p, encoding="utf-8").read()
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    if not m:
        errs.append("%s: 没有 frontmatter" % n); continue
    fm = dict(l.split(":", 1) for l in m.group(1).splitlines() if ":" in l)
    if fm.get("name", "").strip() != n:
        errs.append("%s: name 与目录名不一致 (%s)" % (n, fm.get("name")))
    desc = fm.get("description", "").strip()
    if len(desc) < 60:
        errs.append("%s: description 太短" % n)
    if len(desc) > 1024:
        errs.append("%s: description 超过 1024 字符 (%d)" % (n, len(desc)))
    lines = text.count("\n")
    if lines > 500:
        warns.append("%s: SKILL.md %d 行，超过 500" % (n, lines))
    for rel in set(re.findall(r"`((?:references|assets|scripts)/[A-Za-z0-9_./\-]+)`", text)):
        if not os.path.exists(os.path.join(d, rel)):
            errs.append("%s: 正文提到的 %s 不存在" % (n, rel))
    for rel in set(re.findall(r"`([a-z\-]+/(?:references|assets|scripts)/[A-Za-z0-9_./\-]+)`", text)):
        if not os.path.exists(os.path.join(SK, rel)):
            errs.append("%s: 正文提到的跨技能文件 %s 不存在" % (n, rel))
    for other in set(re.findall(r"`([a-z]+(?:-[a-z]+)+)`", text)):
        if other not in names and other in ("paper-scout", "paper-synthesis", "idea-forge", "prior-art-duel", "prescreen",
                                             "protocol-freeze", "exec-handoff", "result-verdict", "research-ledger",
                                             "paper-claims", "research-pipeline", "method-build"):
            errs.append("%s: 提到了不存在的技能 %s" % (n, other))
    for root, _, files in os.walk(d):
        for f in files:
            fp = os.path.join(root, f)
            if f.endswith(".py"):
                try:
                    py_compile.compile(fp, doraise=True)
                except py_compile.PyCompileError as e:
                    errs.append("%s: %s 编译失败 %s" % (n, f, e))
    for f in os.listdir(os.path.join(ROOT, "shared")):
        cp = os.path.join(d, "references", "shared", f)
        if not os.path.exists(cp) or not filecmp.cmp(os.path.join(ROOT, "shared", f), cp, shallow=False):
            errs.append("%s: references/shared/%s 缺失或过期，运行 tools/sync_shared.sh" % (n, f))
    print("%-18s %4d 行  description %4d 字符" % (n, lines, len(desc)))
for w in warns:
    print("警告:", w)
for e in errs:
    print("错误:", e)
print("自检: %d 个技能, %d 错误, %d 警告" % (len(names), len(errs), len(warns)))
sys.exit(1 if errs else 0)
