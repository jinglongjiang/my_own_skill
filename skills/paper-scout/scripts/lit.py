#!/usr/bin/env python3
"""文献台账：检索、登记、筛选、阅读登记、核查。仅依赖标准库。

子命令:
  init    --dir DIR --question "..."            建立台账
  search  "关键词" --regime same|cross [--probe 子领域] [--source arxiv,openalex] [--n 15] [--since 年份]
  add     --id ID --title T [--year Y] [--url U] [--abstract A]   手工登记（网页检索到的论文）
  screen  ID include|exclude|maybe --reason "..." [--role near-miss|mechanism-source|baseline|background]
  read    ID --level full|abstract [--force]     登记已读（full 需要笔记文件含 >=2 个位置锚点）
  status                                         统计
  export                                         生成 screened.md
  check   [--cite FILE ...]                      核查：引用是否都读过、检索是否够、跨领域是否够宽
所有子命令都接受 --dir（默认 research/lit）。
"""
import argparse
import datetime
import json
import os
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

UA = {"User-Agent": "my-own-skill-lit/1.0 (research use)"}
ANCHOR = re.compile(r"(Sec\.|Section|Eq\.|Table|Fig\.|Figure|Appendix|Alg\.|§|第\s*\d+\s*节|表\s*\d|图\s*\d|式\s*[\(（]?\d)")


def lpath(d):
    return os.path.join(d, "ledger.json")


def load(d):
    p = lpath(d)
    if not os.path.exists(p):
        sys.exit("找不到台账 %s，先运行 init" % p)
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def save(d, L):
    tmp = lpath(d) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(L, f, ensure_ascii=False, indent=1)
    os.replace(tmp, lpath(d))


def safe_id(pid):
    return re.sub(r"[:/]", "_", pid)


def norm_title(t):
    return re.sub(r"[^a-z0-9]+", " ", (t or "").lower()).strip()


def http(url, timeout=30):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def search_arxiv(q, n, since):
    # arXiv 对多词查询默认按 OR 匹配，相关性很差；这里把每个词用 AND 连接
    terms = [t for t in re.findall(r"[A-Za-z0-9\-]+", q) if len(t) > 2]
    sq = " AND ".join("all:" + t for t in terms) if terms else "all:" + q
    url = "http://export.arxiv.org/api/query?" + urllib.parse.urlencode(
        {"search_query": sq, "max_results": n, "sortBy": "relevance"})
    root = ET.fromstring(http(url))
    ns = {"a": "http://www.w3.org/2005/Atom"}
    out = []
    for e in root.findall("a:entry", ns):
        raw = (e.findtext("a:id", "", ns) or "").rsplit("/abs/", 1)[-1]
        aid = re.sub(r"v\d+$", "", raw)
        pub = e.findtext("a:published", "", ns)[:10]
        year = int(pub[:4]) if pub[:4].isdigit() else None
        if since and year and year < since:
            continue
        out.append({
            "id": "arxiv:" + aid,
            "title": " ".join((e.findtext("a:title", "", ns) or "").split()),
            "year": year, "date": pub,
            "authors": [x.findtext("a:name", "", ns) for x in e.findall("a:author", ns)][:6],
            "venue": "arXiv",
            "abstract": " ".join((e.findtext("a:summary", "", ns) or "").split()),
            "url": "https://arxiv.org/abs/" + aid, "cited_by": None,
        })
    return out


def search_openalex(q, n, since):
    params = {"search": q, "per-page": n}
    if since:
        params["filter"] = "from_publication_date:%d-01-01" % since
    data = json.loads(http("https://api.openalex.org/works?" + urllib.parse.urlencode(params)))
    out = []
    for w in data.get("results", []):
        inv = w.get("abstract_inverted_index") or {}
        words = sorted(((pos, tok) for tok, ps in inv.items() for pos in ps))
        loc = (w.get("primary_location") or {}).get("source") or {}
        out.append({
            "id": "oa:" + w["id"].rsplit("/", 1)[-1],
            "title": w.get("title") or "",
            "year": w.get("publication_year"), "date": w.get("publication_date"),
            "authors": [a["author"]["display_name"] for a in w.get("authorships", [])][:6],
            "venue": loc.get("display_name") or "",
            "abstract": " ".join(t for _, t in words),
            "url": w.get("doi") or w["id"], "cited_by": w.get("cited_by_count"),
        })
    return out


BACKENDS = {"arxiv": search_arxiv, "openalex": search_openalex}


def cmd_init(a):
    os.makedirs(os.path.join(a.dir, "papers"), exist_ok=True)
    if os.path.exists(lpath(a.dir)):
        sys.exit("台账已存在，不覆盖: " + lpath(a.dir))
    save(a.dir, {"created": datetime.date.today().isoformat(), "questions": a.question or [],
                 "criteria": {"include": [], "exclude": []}, "queries": [], "papers": {}})
    print("已建立", lpath(a.dir))


def cmd_search(a):
    L = load(a.dir)
    if a.regime == "cross" and not a.probe:
        sys.exit("cross 检索必须用 --probe 声明目标子领域（用来统计跨了几个领域）")
    seen = {norm_title(p["title"]): pid for pid, p in L["papers"].items()}
    new, dup, errs = [], 0, []
    for src in a.source.split(","):
        fn = BACKENDS.get(src.strip())
        if not fn:
            errs.append("未知来源 " + src)
            continue
        try:
            res = fn(a.query, a.n, a.since)
        except Exception as e:  # 网络失败如实记录，不伪造结果
            errs.append("%s 失败: %s" % (src, e))
            continue
        for p in res:
            k = norm_title(p["title"])
            if not k:
                continue
            if p["id"] in L["papers"]:
                # 同一个 ID 再次出现（标题可能被作者改过）：只更新元数据，筛选决定和阅读记录原样保留
                old = L["papers"][p["id"]]
                for fld in ("title", "year", "date", "authors", "venue", "abstract", "url", "cited_by"):
                    if p.get(fld) not in (None, "", []):
                        old[fld] = p[fld]
                old.setdefault("found_by", []).append(len(L["queries"]))
                seen[k] = p["id"]
                dup += 1
                continue
            if k in seen:
                dup += 1
                L["papers"][seen[k]].setdefault("found_by", []).append(len(L["queries"]))
                continue
            p.update({"screen": None, "reason": "", "role": "", "read": None, "found_by": [len(L["queries"])]})
            L["papers"][p["id"]] = p
            seen[k] = p["id"]
            new.append(p)
    L["queries"].append({"q": a.query, "regime": a.regime, "probe": a.probe or "", "source": a.source,
                         "since": a.since, "new": len(new), "dup": dup, "errors": errs,
                         "at": datetime.datetime.now().isoformat(timespec="seconds")})
    save(a.dir, L)
    for p in new:
        print("%-22s %s  %s" % (p["id"], p["year"] or "----", p["title"][:90]))
    print("新增 %d，重复 %d%s" % (len(new), dup, ("；错误: " + "; ".join(errs)) if errs else ""))
    if errs and not new:
        return 2
    return 0


def cmd_add(a):
    L = load(a.dir)
    if a.id in L["papers"]:
        sys.exit("已存在 %s；不覆盖已有的筛选与阅读记录" % a.id)
    L["papers"][a.id] = {"id": a.id, "title": a.title, "year": a.year, "date": None, "authors": [],
                         "venue": a.venue or "", "abstract": a.abstract or "", "url": a.url or "",
                         "cited_by": None, "screen": None, "reason": "", "role": "", "read": None,
                         "found_by": ["manual"]}
    save(a.dir, L)
    print("已登记", a.id)


def need(L, pid):
    if pid not in L["papers"]:
        sys.exit("台账里没有 %s（先 search 或 add）" % pid)
    return L["papers"][pid]


def cmd_screen(a):
    L = load(a.dir)
    p = need(L, a.id)
    if not a.reason.strip():
        sys.exit("筛选决定必须写理由")
    p.update({"screen": a.decision, "reason": a.reason, "role": a.role or p.get("role", "")})
    save(a.dir, L)
    print(a.id, "->", a.decision)


def cmd_read(a):
    L = load(a.dir)
    p = need(L, a.id)
    note = os.path.join(a.dir, "papers", safe_id(a.id) + ".md")
    if not os.path.exists(note):
        sys.exit("缺少笔记文件 %s —— 先写笔记再登记" % note)
    text = open(note, encoding="utf-8").read()
    anchors = len(ANCHOR.findall(text))
    forced = False
    if a.level == "full" and anchors < 2:
        if not a.force:
            sys.exit("full 级阅读要求笔记里至少 2 个位置锚点（Sec./Eq./Table/Fig./节/表/图），当前 %d 个。"
                     "只看了摘要就登记 abstract。" % anchors)
        forced = True
    p["read"] = {"level": a.level, "anchors": anchors, "forced": forced,
                 "at": datetime.date.today().isoformat(), "note": note}
    save(a.dir, L)
    print("%s 已登记为 %s 级阅读（锚点 %d%s）" % (a.id, a.level, anchors, "，强制" if forced else ""))


def cmd_status(a):
    L = load(a.dir)
    P = list(L["papers"].values())
    c = lambda f: sum(1 for p in P if f(p))
    probes = sorted({q["probe"] for q in L["queries"] if q["regime"] == "cross" and q["probe"]})
    print("检索式 %d 条（same %d / cross %d，跨领域 %d 个: %s）" % (
        len(L["queries"]), sum(q["regime"] == "same" for q in L["queries"]),
        sum(q["regime"] == "cross" for q in L["queries"]), len(probes), ", ".join(probes) or "无"))
    print("论文 %d 篇：纳入 %d / 待定 %d / 排除 %d / 未筛 %d" % (
        len(P), c(lambda p: p["screen"] == "include"), c(lambda p: p["screen"] == "maybe"),
        c(lambda p: p["screen"] == "exclude"), c(lambda p: p["screen"] is None)))
    print("阅读：full %d / abstract %d；纳入但未读 %d" % (
        c(lambda p: p["read"] and p["read"]["level"] == "full"),
        c(lambda p: p["read"] and p["read"]["level"] == "abstract"),
        c(lambda p: p["screen"] == "include" and not p["read"])))


def cmd_export(a):
    L = load(a.dir)
    rows = sorted(L["papers"].values(), key=lambda p: ({"include": 0, "maybe": 1, "exclude": 2, None: 3}[p["screen"]],
                                                       -(p["year"] or 0)))
    out = ["# 文献筛选结果", "", "生成日期：%s" % datetime.date.today().isoformat(), "",
           "| 决定 | 角色 | ID | 年 | 标题 | 阅读 | 理由 |", "|---|---|---|---|---|---|---|"]
    for p in rows:
        if p["screen"] is None and not a.all:
            continue
        rd = (p["read"]["level"] + ("(强制)" if p["read"].get("forced") else "")) if p["read"] else "未读"
        out.append("| %s | %s | %s | %s | %s | %s | %s |" % (
            p["screen"] or "未筛", p["role"], p["id"], p["year"] or "", p["title"].replace("|", "/")[:100], rd,
            p["reason"].replace("|", "/")))
    dst = os.path.join(a.dir, "screened.md")
    with open(dst, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    print("已写出", dst, "（%d 行）" % (len(out) - 6))


def cmd_check(a):
    L = load(a.dir)
    P = L["papers"]
    errors, warns = [], []
    for pid, p in P.items():
        if p["screen"] == "include" and not p["read"]:
            errors.append("纳入但未读: " + pid)
        if p["screen"] == "include" and p["role"] in ("near-miss", "mechanism-source") and p["read"] \
                and p["read"]["level"] != "full":
            errors.append("近邻/机制来源必须 full 级阅读: " + pid)
        if p["read"] and p["read"].get("forced"):
            warns.append("强制登记的 full 阅读（交付时须说明）: " + pid)
        if p["read"]:
            # 阅读登记依赖笔记文件；笔记被删或被改空后，登记不再有效
            note = os.path.join(a.dir, "papers", safe_id(pid) + ".md")
            if not os.path.exists(note):
                errors.append("已登记阅读但笔记文件不存在: %s（%s）" % (pid, note))
            elif p["read"]["level"] == "full" and not p["read"].get("forced") \
                    and len(ANCHOR.findall(open(note, encoding="utf-8").read())) < 2:
                errors.append("full 级阅读的笔记现在不足 2 个位置锚点: " + pid)
    for fpath in a.cite or []:
        if not os.path.exists(fpath):
            errors.append("引用检查的文件不存在: " + fpath)
            continue
        for cid in sorted(set(re.findall(r"\[@([^\]\s]+)\]", open(fpath, encoding="utf-8").read()))):
            if cid not in P:
                errors.append("%s 引用了台账里没有的 %s" % (fpath, cid))
            elif not P[cid]["read"]:
                errors.append("%s 引用了未读的 %s" % (fpath, cid))
    same = [q for q in L["queries"] if q["regime"] == "same"]
    cross = [q for q in L["queries"] if q["regime"] == "cross"]
    if len(same) < 4:
        warns.append("同问题检索只有 %d 条，近邻可能没找全（建议 >=4）" % len(same))
    probes = {q["probe"] for q in cross if q["probe"]}
    if cross and len(probes) < 3:
        warns.append("跨领域检索只覆盖 %d 个子领域（建议 >=3）" % len(probes))
    if any(q["errors"] for q in L["queries"]):
        warns.append("有检索后端失败过，覆盖可能不全: 见 ledger.json 的 queries[].errors")
    unscreened = sum(1 for p in P.values() if p["screen"] is None)
    if unscreened:
        warns.append("%d 篇尚未筛选" % unscreened)
    for w in warns:
        print("警告:", w)
    for e in errors:
        print("错误:", e)
    print("核查结果: %d 错误, %d 警告" % (len(errors), len(warns)))
    return 1 if errors else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    sub.required = True

    def mk(name, fn):
        s = sub.add_parser(name)
        s.add_argument("--dir", default="research/lit")
        s.set_defaults(fn=fn)
        return s
    s = mk("init", cmd_init); s.add_argument("--question", action="append")
    s = mk("search", cmd_search); s.add_argument("query"); s.add_argument("--regime", choices=["same", "cross"], required=True)
    s.add_argument("--probe"); s.add_argument("--source", default="arxiv,openalex"); s.add_argument("--n", type=int, default=15)
    s.add_argument("--since", type=int)
    s = mk("add", cmd_add); s.add_argument("--id", required=True); s.add_argument("--title", required=True)
    s.add_argument("--year", type=int); s.add_argument("--url"); s.add_argument("--venue"); s.add_argument("--abstract")
    s = mk("screen", cmd_screen); s.add_argument("id"); s.add_argument("decision", choices=["include", "exclude", "maybe"])
    s.add_argument("--reason", required=True); s.add_argument("--role", choices=["near-miss", "mechanism-source", "baseline", "background"])
    s = mk("read", cmd_read); s.add_argument("id"); s.add_argument("--level", choices=["full", "abstract"], required=True)
    s.add_argument("--force", action="store_true")
    mk("status", cmd_status)
    s = mk("export", cmd_export); s.add_argument("--all", action="store_true")
    s = mk("check", cmd_check); s.add_argument("--cite", nargs="*")
    a = ap.parse_args()
    return a.fn(a) or 0


if __name__ == "__main__":
    sys.exit(main())
