#!/usr/bin/env bash
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
f="$1"
cd "$ROOT" || exit 1

stem="$(basename "$f" .xml)"
rates="${f%.xml}_rates.txt"
score="${f%.xml}_score.txt"
log="$ROOT/logs/${stem}.log"
lock="$ROOT/locks/${stem}.lock"
status="$ROOT/cloud_status.tsv"
failures="$ROOT/cloud_failures.tsv"

mkdir -p "$ROOT/logs" "$ROOT/locks"

if [[ -f "$rates" && -f "$score" && -s "$rates" && -s "$score" && $(grep -c '<Output' "$f") -gt 0 ]]; then
  echo -e "$(date '+%Y-%m-%d %H:%M:%S')\tSKIP\t$f\tcompleted" >> "$status"
  exit 0
fi

if ! mkdir "$lock" 2>/dev/null; then
  echo -e "$(date '+%Y-%m-%d %H:%M:%S')\tSKIP\t$f\tlocked" >> "$status"
  exit 0
fi
trap 'rmdir "$lock" 2>/dev/null || true' EXIT

echo -e "$(date '+%Y-%m-%d %H:%M:%S')\tSTART\t$f\t-" >> "$status"
work/transcpp/transcpp "$f" > "$log" 2>&1 &
transcpp_pid=$!
while kill -0 "$transcpp_pid" 2>/dev/null; do
  if grep -qi 'initial score is nan\|score is nan after initial moves' "$log" 2>/dev/null; then
    kill "$transcpp_pid" 2>/dev/null || true
    wait "$transcpp_pid" 2>/dev/null || true
    echo -e "$(date '+%Y-%m-%d %H:%M:%S')\tFAIL\t$f\tnan_initial_score" >> "$status"
    echo -e "$(date '+%Y-%m-%d %H:%M:%S')\t$f\tnan_initial_score\t$log" >> "$failures"
    exit 0
  fi
  sleep 15
done

wait "$transcpp_pid"
rc=$?
if [[ "$rc" -ne 0 ]]; then
  echo -e "$(date '+%Y-%m-%d %H:%M:%S')\tFAIL\t$f\ttranscpp rc=$rc" >> "$status"
  echo -e "$(date '+%Y-%m-%d %H:%M:%S')\t$f\ttranscpp rc=$rc\t$log" >> "$failures"
  exit 0
fi

if ! grep -q '<Output' "$f"; then
  echo -e "$(date '+%Y-%m-%d %H:%M:%S')\tFAIL\t$f\tmissing Output block" >> "$status"
  echo -e "$(date '+%Y-%m-%d %H:%M:%S')\t$f\tmissing Output block\t$log" >> "$failures"
  exit 0
fi

work/transcpp/unfold -i "$f" -s Output --rate --invert > "$rates"
rate_rc=$?
work/transcpp/unfold -i "$f" -s Output --score > "$score"
score_rc=$?
if [[ "$rate_rc" -ne 0 || "$score_rc" -ne 0 ]]; then
  echo -e "$(date '+%Y-%m-%d %H:%M:%S')\tFAIL\t$f\tunfold rate=$rate_rc score=$score_rc" >> "$status"
  echo -e "$(date '+%Y-%m-%d %H:%M:%S')\t$f\tunfold rate=$rate_rc score=$score_rc\t$log" >> "$failures"
  exit 0
fi

echo -e "$(date '+%Y-%m-%d %H:%M:%S')\tDONE\t$f\t-" >> "$status"
