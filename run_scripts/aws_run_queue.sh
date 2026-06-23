#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

JOBS="${CLOUD_JOBS:-$(nproc)}"
echo "Starting AWS Figure 3D queue with $JOBS parallel jobs"
echo "Target XMLs: $(find runs -maxdepth 1 -type f -name 'self_on*_seed00.xml' | wc -l | tr -d ' ')"

find "$ROOT/runs" -maxdepth 1 -type f -name 'self_on*_seed00.xml' \
  | sort \
  | xargs -n 1 -P "$JOBS" bash "$ROOT/aws_fit_one_xml.sh"

bash "$ROOT/aws_pack_results.sh"
echo "AWS queue complete."
