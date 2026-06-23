#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/iyubin/Documents/Codex/2026-06-05/pdf"
RUN_DIR="$ROOT/outputs/figure3/runs"
PID_FILE="$ROOT/outputs/figure3/figure3_queue.pid"
STATUS="$ROOT/outputs/figure3/figure3_queue_status.tsv"
SCREEN_SESSION="figure3_queue"

total="$(find "$RUN_DIR" -maxdepth 1 -type f -name '*.xml' | wc -l | tr -d ' ')"
completed="$(find "$RUN_DIR" -maxdepth 1 -type f -name '*_rates.txt' | wc -l | tr -d ' ')"
failed=0
if [[ -f "$ROOT/outputs/figure3/figure3_queue_failures.tsv" ]]; then
  failed="$(wc -l < "$ROOT/outputs/figure3/figure3_queue_failures.tsv" | tr -d ' ')"
fi

echo "Figure 3 queue status"
echo "completed rates: $completed / $total"
echo "failures: $failed"

if /usr/bin/screen -ls | grep -q "[.]$SCREEN_SESSION"; then
  echo "screen session: $SCREEN_SESSION running"
else
  echo "screen session: $SCREEN_SESSION not running (normal if started in Terminal)"
fi

active="$(pgrep -af 'work/transcpp/transcpp .*outputs/figure3/runs' 2>/dev/null || true)"
if [[ -n "$active" ]]; then
  echo "active transcpp:"
  echo "$active"
else
  echo "active transcpp: none detected"
fi

if [[ -f "$STATUS" ]]; then
  echo "last status lines:"
  tail -n 8 "$STATUS"
fi
