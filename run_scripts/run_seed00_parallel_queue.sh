#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/iyubin/Documents/Codex/2026-06-05/pdf"
JOBS="${FIG3_JOBS:-4}"
PYTHON="/Users/iyubin/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3"

cd "$ROOT"
mkdir -p outputs/figure3/logs outputs/figure3/locks
echo "Starting seed00 Figure 3 queue with $JOBS parallel jobs"
echo "Target runs: $(find outputs/figure3/runs -maxdepth 1 -type f -name '*_seed00.xml' | wc -l | tr -d ' ')"

find "$ROOT/outputs/figure3/runs" -maxdepth 1 -type f -name '*_seed00.xml' \
  | sort \
  | xargs -n 1 -P "$JOBS" bash outputs/figure3/fit_one_figure3_xml.sh

"$PYTHON" work/collect_figure3_results.py > outputs/figure3/logs/collect_final_seed00.log 2>&1 || true
"$PYTHON" work/make_figure3BD_from_completed.py > outputs/figure3/logs/plot_figure3BD_seed00.log 2>&1 || true
"$PYTHON" work/make_figure3D_groups_from_completed.py > outputs/figure3/logs/plot_figure3D_seed00.log 2>&1 || true
echo "seed00 Figure 3 queue complete"
