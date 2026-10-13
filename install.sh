#!/usr/bin/env bash
# 安装全部技能。默认装到 ~/.claude/skills；--codex 同时装到 ~/.codex/skills。
# 已存在同名技能时默认跳过，--force 才覆盖。--dry-run 只打印不动文件。
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
TARGETS=("$HOME/.claude/skills"); FORCE=0; DRY=0
while [ $# -gt 0 ]; do
  case "$1" in
    --codex) TARGETS+=("$HOME/.codex/skills");;
    --target) shift; TARGETS=("$1");;
    --force) FORCE=1;;
    --dry-run) DRY=1;;
    -h|--help) sed -n '2,4p' "$0"; exit 0;;
    *) echo "未知参数 $1" >&2; exit 2;;
  esac; shift
done
[ "$DRY" = 1 ] || bash "$ROOT/tools/sync_shared.sh"
for T in "${TARGETS[@]}"; do
  echo "目标: $T"
  for d in "$ROOT"/skills/*/; do
    n="$(basename "$d")"
    if [ -e "$T/$n" ] && [ "$FORCE" = 0 ]; then echo "  跳过（已存在）: $n"; continue; fi
    if [ "$DRY" = 1 ]; then echo "  将安装: $n"; continue; fi
    mkdir -p "$T"; rm -rf "$T/$n"; cp -r "$d" "$T/$n"
    find "$T/$n" -name "__pycache__" -type d -prune -exec rm -rf {} +
    echo "  已安装: $n"
  done
done
