#!/usr/bin/env bash
set -u

ROOT="/Users/iyubin/Documents/Codex/2026-06-05/pdf"
RUN_DIR="$ROOT/outputs/figure3/runs"
LOG_DIR="$ROOT/outputs/figure3/logs"
STATUS="$ROOT/outputs/figure3/figure3_queue_status.tsv"
FAILURES="$ROOT/outputs/figure3/figure3_queue_failures.tsv"
PYTHON="/Users/iyubin/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3"

cd "$ROOT" || exit 1
mkdir -p "$RUN_DIR" "$LOG_DIR"

total="$(find "$RUN_DIR" -maxdepth 1 -type f -name '*.xml' | wc -l | tr -d ' ')"
echo -e "timestamp\tevent\tindex\ttotal\tfile\tmessage" >> "$STATUS"

idx=0
find "$RUN_DIR" -maxdepth 1 -type f -name '*.xml' | sort | while IFS= read -r f; do
  idx=$((idx + 1))
  stem="$(basename "$f" .xml)"
  rates="${f%.xml}_rates.txt"
  score="${f%.xml}_score.txt"
  log="$LOG_DIR/${stem}.log"

  if [[ -f "$rates" && -f "$score" && -s "$rates" && -s "$score" && $(grep -c '<Output' "$f") -gt 0 ]]; then
    echo -e "$(date '+%Y-%m-%d %H:%M:%S')\tSKIP\t$idx\t$total\t$f\tcompleted" >> "$STATUS"
    continue
  fi

  echo -e "$(date '+%Y-%m-%d %H:%M:%S')\tSTART\t$idx\t$total\t$f\t-" >> "$STATUS"
  work/transcpp/transcpp "$f" > "$log" 2>&1
  rc=$?
  if [[ "$rc" -ne 0 ]]; then
    echo -e "$(date '+%Y-%m-%d %H:%M:%S')\tFAIL\t$idx\t$total\t$f\ttranscpp rc=$rc" >> "$STATUS"
    echo -e "$(date '+%Y-%m-%d %H:%M:%S')\t$f\ttranscpp rc=$rc\t$log" >> "$FAILURES"
    continue
  fi

  if ! grep -q '<Output' "$f"; then
    echo -e "$(date '+%Y-%m-%d %H:%M:%S')\tFAIL\t$idx\t$total\t$f\tmissing Output block" >> "$STATUS"
    echo -e "$(date '+%Y-%m-%d %H:%M:%S')\t$f\tmissing Output block\t$log" >> "$FAILURES"
    continue
  fi

  work/transcpp/unfold -i "$f" -s Output --rate --invert > "$rates"
  rate_rc=$?
  work/transcpp/unfold -i "$f" -s Output --score > "$score"
  score_rc=$?
  if [[ "$rate_rc" -ne 0 || "$score_rc" -ne 0 ]]; then
    echo -e "$(date '+%Y-%m-%d %H:%M:%S')\tFAIL\t$idx\t$total\t$f\tunfold rate=$rate_rc score=$score_rc" >> "$STATUS"
    echo -e "$(date '+%Y-%m-%d %H:%M:%S')\t$f\tunfold rate=$rate_rc score=$score_rc\t$log" >> "$FAILURES"
    continue
  fi

  echo -e "$(date '+%Y-%m-%d %H:%M:%S')\tDONE\t$idx\t$total\t$f\t-" >> "$STATUS"

  completed="$(find "$RUN_DIR" -maxdepth 1 -type f -name '*_rates.txt' | wc -l | tr -d ' ')"
  if [[ $((completed % 10)) -eq 0 ]]; then
    "$PYTHON" work/collect_figure3_results.py > "$LOG_DIR/collect_latest.log" 2>&1 || true
    "$PYTHON" work/make_figure3BD_from_completed.py > "$LOG_DIR/plot_figure3BD_latest.log" 2>&1 || true
  fi
done

"$PYTHON" work/collect_figure3_results.py > "$LOG_DIR/collect_final.log" 2>&1 || true
"$PYTHON" work/make_figure3D_groups_from_completed.py > "$LOG_DIR/plot_figure3D_latest.log" 2>&1 || true
"$PYTHON" work/make_figure3BD_from_completed.py > "$LOG_DIR/plot_figure3BD_latest.log" 2>&1 || true
echo -e "$(date '+%Y-%m-%d %H:%M:%S')\tQUEUE_DONE\t$total\t$total\t-\t-" >> "$STATUS"
