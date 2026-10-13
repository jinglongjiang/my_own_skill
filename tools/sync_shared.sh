#!/usr/bin/env bash
# 把 shared/ 下的共用文件复制到每个技能的 references/shared/。
# 改了 shared/ 里的任何文件之后运行一次；技能被单独安装时靠这份副本工作。
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
for d in "$ROOT"/skills/*/; do
  mkdir -p "$d/references/shared"
  cp "$ROOT"/shared/*.md "$d/references/shared/"
done
echo "已同步 shared/ 到 $(ls -d "$ROOT"/skills/*/ | wc -l) 个技能"
