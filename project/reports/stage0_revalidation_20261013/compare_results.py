#!/usr/bin/env python3
"""Revalidation only: integer exactness and Decimal absolute float error <= 1e-9.

Historical strict comparator and frozen results are deliberately unchanged.
JSON numeric types are retained; int/float type changes are rejected.
"""
import argparse
from decimal import Decimal
import json


TOLERANCE = Decimal("1e-9")


def compare(old, new, allow_target_prefix=False):
    counts = {"integer_leaves": 0, "floating_leaves": 0, "other_leaves": 0}
    mismatches, within_tolerance_differences, metadata_changes = [], [], []

    def walk(a, b, path="$"):
        if type(a) is not type(b):
            mismatches.append({"path": path, "reason": "type mismatch",
                               "frozen_type": type(a).__name__, "reproduced_type": type(b).__name__,
                               "frozen": str(a), "reproduced": str(b)})
        elif isinstance(a, dict):
            if a.keys() != b.keys():
                mismatches.append({"path": path, "key_difference": sorted(a.keys() ^ b.keys())})
            for key in sorted(a.keys() & b.keys()):
                walk(a[key], b[key], path + "." + key)
        elif isinstance(a, list):
            if len(a) != len(b):
                mismatches.append({"path": path, "lengths": [len(a), len(b)]})
            for i, (x, y) in enumerate(zip(a, b)):
                walk(x, y, "%s[%d]" % (path, i))
        elif type(a) is int:
            counts["integer_leaves"] += 1
            if a != b:
                mismatches.append({"path": path, "reason": "integer must match exactly", "frozen": a, "reproduced": b})
        elif isinstance(a, Decimal):
            counts["floating_leaves"] += 1
            if not a.is_finite() or not b.is_finite():
                mismatches.append({"path": path, "reason": "nonfinite number"})
                return
            delta = b - a
            if delta:
                detail = {"path": path, "frozen": str(a), "reproduced": str(b), "signed_difference": str(delta), "absolute_difference": str(abs(delta))}
                if abs(delta) > TOLERANCE:
                    mismatches.append(detail)
                else:
                    within_tolerance_differences.append(detail)
        else:
            counts["other_leaves"] += 1
            if a == b:
                return
            difference = {"path": path, "frozen": str(a), "reproduced": str(b)}
            if (allow_target_prefix and path == "$.files[0]"
                    and a == "data/kda_s443_cf/table.jsonl.gz"
                    and b == "project/data/kda_s443_cf/table.jsonl.gz"):
                metadata_changes.append(difference)
            else:
                mismatches.append(difference)

    walk(old, new)
    return {
        "status": "已确认失败" if mismatches else "已验证通过",
        "comparison": "JSON ints exact; floats absolute difference <= 1e-9; same numeric type; all keys checked",
        **counts, "allowed_path_metadata_changes": metadata_changes,
        "within_tolerance_differences": within_tolerance_differences,
        "mismatches": mismatches,
    }


def self_test():
    checks = [
        (1, 1, True), (1, 2, False),
        (1, Decimal("1.0"), False), (True, 1, False),
        (Decimal("0.1"), Decimal("0.100000001"), True),
        (Decimal("0.1"), Decimal("0.10000000100001"), False),
        (Decimal("1e20"), Decimal("100000000000000000001"), False),
        (Decimal("NaN"), Decimal("NaN"), False),
        ({"a": [1, Decimal("0.1")]}, {"a": [1, Decimal("0.1")]}, True),
        ({"a": 1}, {"b": 1}, False), ([1], [1, 1], False),
    ]
    for a, b, expected in checks:
        assert (not compare(a, b)["mismatches"]) is expected, (a, b)
    print("11 comparator self-tests passed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("frozen", nargs="?")
    parser.add_argument("reproduced", nargs="?")
    parser.add_argument("--target-path-prefix", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    if not args.frozen or not args.reproduced:
        parser.error("frozen and reproduced are required unless --self-test")
    with open(args.frozen, encoding="utf-8") as stream:
        old = json.load(stream, parse_float=Decimal)
    with open(args.reproduced, encoding="utf-8") as stream:
        new = json.load(stream, parse_float=Decimal)
    result = compare(old, new, args.target_path_prefix)
    result.update(frozen=args.frozen, reproduced=args.reproduced)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return bool(result["mismatches"])


if __name__ == "__main__":
    raise SystemExit(main())
