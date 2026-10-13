#!/usr/bin/env python3
"""把 CF-Rank Stage 1 的逐 case 标签文件合并成一张紧凑的反事实表。

输入是冻结的训练数据索引（FROZEN-*-TRAINING-DATA.json，roots 列表即权威清单）和
标签运行目录（索引里的 array_file 是执行机上的绝对路径，按 --remote-root 映射到本地）。
输出：
  table.jsonl.gz          每行一个根状态，regret_ruler.py 可直接读
  features_cell{c}.npz    该格全部根状态的网络输入，行顺序与 table 中该格的行一致
  MANIFEST.json           计数、校验结果、各文件 SHA256
任何一项校验不过就报错退出，不写 MANIFEST。
"""
import argparse, gzip, hashlib, json, os, sys
import numpy as np

CELL_NAMES = {0: "5C", 1: "5S", 2: "10C", 3: "10S", 4: "20C", 5: "20S"}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("index")
    ap.add_argument("local_root")
    ap.add_argument("out")
    ap.add_argument("--remote-root", default="/root/cfrank-20261013/run")
    a = ap.parse_args()
    index = json.load(open(a.index))
    roots = sorted(index["roots"], key=lambda r: (r["cell"], r["case"], r["root_step"]))
    if not roots:
        sys.exit("empty index")
    rows, feats = [], {}
    checks = dict(array_sha_mismatch=0, G_mismatch=0, chosen_not_argmax=0,
                  chosen_G_ne_root_return=0, chosen_ineligible=0, replay_not_exact=0)
    for r in roots:
        if True:
            if not r["array_file"].startswith(a.remote_root + "/"):
                sys.exit("unexpected array path: " + r["array_file"])
            npz_path = os.path.join(a.local_root, r["array_file"][len(a.remote_root) + 1:])
            if sha256(npz_path) != r["array_sha256"]:
                checks["array_sha_mismatch"] += 1
            z = np.load(npz_path, allow_pickle=False)
            G = np.array([b["G"] for b in r["branches"]], dtype=np.float64)
            if not np.array_equal(G, z["G"]):
                checks["G_mismatch"] += 1
            elig = np.array(r["eligible"], dtype=bool)
            sc = np.array(r["final_scores"], dtype=np.float64)
            pool = np.where(elig)[0] if elig.any() else np.arange(len(sc))
            if int(pool[np.argmax(sc[pool])]) != r["chosen"]:
                checks["chosen_not_argmax"] += 1
            if elig.any() and not elig[r["chosen"]]:
                checks["chosen_ineligible"] += 1
            if abs(G[r["chosen"]] - r["root_return"]) > 1e-12:
                checks["chosen_G_ne_root_return"] += 1
            if not (r["human_forward_bitwise"] and r["root_replay_values_scores_exact"]
                    and r["branches"][r["chosen"]]["A0_replay_exact"] is True
                    and sum(b["A0_replay_exact"] is True for b in r["branches"]) == 1):
                checks["replay_not_exact"] += 1
            c = r["cell"]
            rows.append(dict(
                key="c%d-k%d-s%d" % (c, r["case"], r["root_step"]),
                episode="c%d-k%d" % (c, r["case"]),
                cell=c, cell_name=CELL_NAMES[c], case=r["case"], root_step=r["root_step"],
                episode_outcome=r["episode_outcome"], episode_length=r["episode_length"],
                root_return=r["root_return"], chosen=r["chosen"],
                all_unsafe=bool(not elig.any()),
                final_scores=r["final_scores"], G_A=G.tolist(),
                rewards=r["rewards"], values=r["values"], clearance=r["clearance"],
                eligible=r["eligible"], commands=r["commands"],
                pred_terminal=r["pred_terminal"], pred_terminal_type=r["pred_terminal_type"],
                branch_outcome=[b["outcome"] for b in r["branches"]],
                branch_steps=[b["steps"] for b in r["branches"]],
                branch_min_clearance=[b["minimum_clearance"] for b in r["branches"]],
                true_terminal_step1=[b["true_terminal_step1"] for b in r["branches"]],
            ))
            d = feats.setdefault(c, dict(prefix=[], candidate_last=[], current_window=[], key=[]))
            for k in ("prefix", "candidate_last", "current_window"):
                d[k].append(z[k])
            d["key"].append(rows[-1]["key"])
    keys = [r["key"] for r in rows]
    if len(set(keys)) != len(keys):
        sys.exit("duplicate keys")
    bad = {k: v for k, v in checks.items() if v}
    if bad:
        sys.exit("verification failed: %s" % bad)
    os.makedirs(a.out, exist_ok=True)
    tpath = os.path.join(a.out, "table.jsonl.gz")
    with gzip.open(tpath, "wt", compresslevel=9) as g:
        for r in rows:
            g.write(json.dumps(r, separators=(",", ":")) + "\n")
    outs = {"table.jsonl.gz": tpath}
    for c, d in sorted(feats.items()):
        p = os.path.join(a.out, "features_cell%d.npz" % c)
        np.savez_compressed(p, key=np.array(d["key"]),
                            prefix=np.stack(d["prefix"]),
                            candidate_last=np.stack(d["candidate_last"]),
                            current_window=np.stack(d["current_window"]))
        outs[os.path.basename(p)] = p
    per_cell = {}
    for r in rows:
        pc = per_cell.setdefault(r["cell_name"], dict(roots=0, episodes=set(), all_unsafe=0))
        pc["roots"] += 1; pc["episodes"].add(r["episode"]); pc["all_unsafe"] += r["all_unsafe"]
    manifest = dict(
        roots=len(rows), candidates_per_root=80,
        source_index_sha256=sha256(a.index), mother_sha256=index["mother_sha256"], backbone=index["backbone"],
        per_cell={k: dict(roots=v["roots"], episodes=len(v["episodes"]), all_unsafe_roots=v["all_unsafe"])
                  for k, v in per_cell.items()},
        checks_all_zero=checks,
        files={k: dict(sha256=sha256(p), bytes=os.path.getsize(p)) for k, p in outs.items()},
    )
    with open(os.path.join(a.out, "MANIFEST.json"), "w") as g:
        json.dump(manifest, g, indent=2, ensure_ascii=False)
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
