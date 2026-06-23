#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 /path/to/figure3d_cloud_results_*.tar.gz" >&2
  exit 1
fi

ROOT="/Users/iyubin/Documents/Codex/2026-06-05/pdf"
archive="$1"
stamp="$(date '+%Y%m%d_%H%M%S')"
dest="$ROOT/outputs/figure3/aws_results_${stamp}"

mkdir -p "$dest"
tar -xzf "$archive" -C "$dest"

if [[ ! -d "$dest/runs" ]]; then
  echo "Could not find runs/ in extracted AWS result archive." >&2
  exit 1
fi

rsync -av "$dest/runs/" "$ROOT/outputs/figure3/runs/"

for f in "$dest"/runs/self_on*_seed00.xml; do
  [[ -e "$f" ]] || continue
  stem="$(basename "$f" .xml)"
  if [[ -s "$ROOT/outputs/figure3/runs/${stem}_rates.txt" && -s "$ROOT/outputs/figure3/runs/${stem}_score.txt" ]]; then
    rmdir "$ROOT/outputs/figure3/locks/${stem}.lock" 2>/dev/null || true
  fi
done

"$ROOT/../pdf"/work/collect_figure3_results.py >/dev/null 2>&1 || true

echo "Merged AWS results into $ROOT/outputs/figure3/runs"
echo "Extracted copy kept at $dest"
echo "Current self_on completed:"
find "$ROOT/outputs/figure3/runs" -maxdepth 1 -type f -name 'self_on*_rates.txt' | wc -l
