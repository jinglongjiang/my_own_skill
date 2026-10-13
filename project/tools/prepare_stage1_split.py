#!/usr/bin/env python3
"""Prepare label-blind grouped splits; never JSON-decode outcome-bearing rows.

Only key/episode/cell/eligible are extracted with anchored field expressions.
Assignments depend solely on case IDs and the fixed hash salt, across all cells.
Existing output files are not overwritten, even by an identical rerun.
"""
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path
import re


TABLE = Path("project/data/kda_s443_cf/table.jsonl.gz")
OUT = Path("project/stage1")
TABLE_SHA = "3e4f137d86455e1db9e496420f365a0713e6f8b9f0bb3f6c99649aec07d5a5a2"
SALT = "dots-stage1-split-v1|20261013|"


def field(line, name, pattern):
    matches = re.findall(r'(?:^|[,\{])\s*"' + name + r'"\s*:\s*(' + pattern + r')', line)
    if len(matches) != 1:
        raise ValueError("Expected exactly one scalar metadata field: " + name)
    return matches[0]


def metadata(line):
    key = json.loads(field(line, "key", r'"[^"\\]*"'))
    episode = json.loads(field(line, "episode", r'"[^"\\]*"'))
    cell = int(field(line, "cell", r'[0-9]+'))
    eligible = json.loads(field(line, "eligible", r'\[(?:\s*(?:true|false)\s*,?)*\]'))
    match = re.fullmatch(r"c([0-5])-k(93[0-9]{3})-s([0-9]+)", key)
    if not match or len(eligible) != 80 or not all(type(v) is bool for v in eligible):
        raise ValueError("Malformed allowed metadata")
    keycell, case, step = map(int, match.groups())
    if keycell != cell or episode != "c%d-k%d" % (cell, case) or not 93000 <= case <= 93174:
        raise ValueError("Unexpected case/cell identity")
    return {"key": key, "episode": episode, "cell": cell, "case": case,
            "step": step, "eligible_count": sum(eligible)}


def main():
    raw = TABLE.read_bytes()
    if hashlib.sha256(raw).hexdigest() != TABLE_SHA:
        raise ValueError("STOP: table SHA mismatch")
    rows = [metadata(line) for line in gzip.decompress(raw).decode().splitlines() if line.strip()]
    assert len(rows) == 2100 and len({r["key"] for r in rows}) == 2100
    episodes = {}
    for row in rows:
        episodes.setdefault(row["episode"], []).append(row)
    assert len(episodes) == 1050 and all(len(v) == 2 for v in episodes.values())
    cases = list(range(93000, 93175))
    assert sorted({r["case"] for r in rows}) == cases
    for cell in range(6):
        assert sorted({r["case"] for r in rows if r["cell"] == cell}) == cases
    order = sorted(cases, key=lambda case: hashlib.sha256((SALT + str(case)).encode()).hexdigest())
    locked = set(order[:35])
    folds = {case: i % 5 for i, case in enumerate(order[35:])}
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(["episode", "cell", "case", "partition", "fold", "key_1", "key_2", "eligible_1", "eligible_2"])
    counts = {}
    for episode in sorted(episodes):
        pair = sorted(episodes[episode], key=lambda r: r["step"])
        r = pair[0]
        partition = "locked" if r["case"] in locked else "development"
        fold = "" if partition == "locked" else folds[r["case"]]
        writer.writerow([episode, r["cell"], r["case"], partition, fold,
                         pair[0]["key"], pair[1]["key"], pair[0]["eligible_count"], pair[1]["eligible_count"]])
        counts.setdefault(str(r["cell"]), {"locked_episodes": 0, "development_episodes": 0, "fold_episodes": [0] * 5})
        counts[str(r["cell"])][partition + "_episodes"] += 1
        if partition == "development":
            counts[str(r["cell"])]["fold_episodes"][fold] += 1
    for c in counts.values():
        assert c == {"locked_episodes": 35, "development_episodes": 140, "fold_episodes": [28] * 5}
    assert not any(r["eligible_count"] == 0 for r in rows)
    singleton = [{k: r[k] for k in ["key", "episode", "cell", "case", "eligible_count"]} for r in rows if r["eligible_count"] == 1]
    assert len(singleton) == 3 and all(r["cell"] in [4, 5] for r in singleton)
    csv_bytes = buffer.getvalue().encode()
    manifest = {
        "status": "prepared; effective freeze requires remote commit confirmation before modeling",
        "table_path": str(TABLE), "table_sha256": TABLE_SHA,
        "assignment_method": "Sort case IDs by SHA256(salt + decimal case); first 35 locked; remaining 140 assigned fold by index modulo 5. Same assignment in all six cells.",
        "salt": SALT, "metadata_fields_read": ["key", "episode", "cell", "eligible"],
        "future_outcomes_decoded": False, "rows": len(rows), "episodes": len(episodes),
        "unique_cases": len(cases), "per_cell": counts,
        "total_locked_episodes": 210, "total_locked_states": 420,
        "total_development_episodes": 840, "total_development_states": 1680,
        "zero_eligible_roots": 0, "single_eligible_roots": singleton,
        "metric_denominators": {"regret": "eligible_count >= 2; same rule as frozen target", "failure": "all roots; same rule as frozen rescue", "failure_comparable": "also report eligible_count >= 2 as descriptive sensitivity"},
        "episodes_csv_sha256": hashlib.sha256(csv_bytes).hexdigest(),
        "case_overlap_between_partitions_or_folds": 0,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    for name in ["episodes.csv", "split_manifest.json"]:
        if (OUT / name).exists():
            raise FileExistsError("Refusing overwrite: " + str(OUT / name))
    (OUT / "episodes.csv").write_bytes(csv_bytes)
    (OUT / "split_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
