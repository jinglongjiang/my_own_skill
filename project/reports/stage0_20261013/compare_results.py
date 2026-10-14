#!/usr/bin/env python3
"""Compare frozen and reproduced JSON without numeric tolerance.

Only target.files[0]'s documented repository-relative path prefix may differ.
Decimal parsing preserves the complete serialized numerical values.
"""
import argparse
from decimal import Decimal
import json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("frozen")
    parser.add_argument("reproduced")
    parser.add_argument("--target-path-prefix", action="store_true")
    args = parser.parse_args()
    with open(args.frozen, encoding="utf-8") as stream:
        old = json.load(stream, parse_float=Decimal, parse_int=Decimal)
    with open(args.reproduced, encoding="utf-8") as stream:
        new = json.load(stream, parse_float=Decimal, parse_int=Decimal)
    counts = {"numeric_leaves": 0, "other_leaves": 0}
    mismatches, metadata_changes = [], []

    def walk(a, b, path="$"):
        if isinstance(a, Decimal) and isinstance(b, Decimal):
            counts["numeric_leaves"] += 1
            if a != b:
                mismatches.append({"path": path, "frozen": str(a), "reproduced": str(b)})
        elif isinstance(a, dict) and isinstance(b, dict):
            if a.keys() != b.keys():
                mismatches.append({"path": path, "key_difference": sorted(a.keys() ^ b.keys())})
            for key in sorted(a.keys() & b.keys()):
                walk(a[key], b[key], path + "." + key)
        elif isinstance(a, list) and isinstance(b, list):
            if len(a) != len(b):
                mismatches.append({"path": path, "lengths": [len(a), len(b)]})
            for i, (x, y) in enumerate(zip(a, b)):
                walk(x, y, "%s[%d]" % (path, i))
        else:
            counts["other_leaves"] += 1
            if a == b and type(a) is type(b):
                return
            difference = {"path": path, "frozen": str(a), "reproduced": str(b)}
            if (args.target_path_prefix and path == "$.files[0]"
                    and a == "data/kda_s443_cf/table.jsonl.gz"
                    and b == "project/data/kda_s443_cf/table.jsonl.gz"):
                metadata_changes.append(difference)
            else:
                mismatches.append(difference)

    walk(old, new)
    print(json.dumps({
        "status": "已确认失败" if mismatches else "已验证通过",
        "frozen": args.frozen, "reproduced": args.reproduced,
        "comparison": "exact Decimal equality; no tolerance; all keys checked",
        **counts, "allowed_path_metadata_changes": metadata_changes,
        "mismatches": mismatches,
    }, ensure_ascii=False, indent=2))
    return bool(mismatches)


if __name__ == "__main__":
    raise SystemExit(main())
