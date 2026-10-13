#!/usr/bin/env python3
"""Read bytes only; verify every file named in the frozen manifest."""
from hashlib import sha256
import json
from pathlib import Path


base = Path("project/data/kda_s443_cf")
manifest_path = base / "MANIFEST.json"
manifest = json.loads(manifest_path.read_text())
checks = []
for name, expected in manifest["files"].items():
    path = base / name
    data = path.read_bytes()
    actual = {"sha256": sha256(data).hexdigest(), "bytes": len(data)}
    checks.append({"file": str(path), "expected": expected, "actual": actual,
                   "status": "已验证通过" if actual == expected else "已确认失败"})
    if actual != expected:
        print(json.dumps({"status": "已确认失败", "checks": checks}, ensure_ascii=False, indent=2))
        raise SystemExit(1)
print(json.dumps({
    "status": "已验证通过", "manifest": str(manifest_path),
    "manifest_sha256": sha256(manifest_path.read_bytes()).hexdigest(),
    "verified_file_count": len(checks), "checks": checks,
    "scope": "Local file SHA256 and byte counts only. Source index and mother weights are absent and not reverified. NPZ files hashed without decoding.",
}, ensure_ascii=False, indent=2))
