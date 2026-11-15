#!/usr/bin/env bash
# WenMind AI 回滚脚本（在目标 ECS 上执行）
# 用法: rollback.sh [目标tag]
# 不带参数时自动回滚到 current 之外的最新一个 release; 数据目录 /opt/wenmind/data 全程不动
set -euo pipefail

BASE=/opt/wenmind
CURRENT_NAME="$(basename "$(readlink -f "$BASE/current")")"

if [ -n "${1:-}" ]; then
  TARGET="$1"
else
  TARGET="$(ls -1t "$BASE/releases" | grep -v -x "$CURRENT_NAME" | head -1 || true)"
fi

if [ -z "${TARGET:-}" ] || [ ! -d "$BASE/releases/$TARGET" ]; then
  echo "ROLLBACK_FAIL no_previous_release current=$CURRENT_NAME"
  exit 1
fi

ln -sfn "$BASE/releases/$TARGET" "$BASE/current"
systemctl restart wenmind

for i in $(seq 1 10); do
  if curl -fsS http://127.0.0.1:8000/api/v1/health | grep -q '"code":0'; then
    echo "ROLLBACK_OK from=$CURRENT_NAME to=$TARGET"
    exit 0
  fi
  sleep 3
done

echo "ROLLBACK_HEALTH_FAIL target=$TARGET"
journalctl -u wenmind -n 30 --no-pager || true
exit 1