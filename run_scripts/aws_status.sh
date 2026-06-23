#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

done_count="$(find runs -maxdepth 1 -type f -name 'self_on*_rates.txt' | wc -l | tr -d ' ')"
total_count="$(find runs -maxdepth 1 -type f -name 'self_on*_seed00.xml' | wc -l | tr -d ' ')"
echo "AWS Figure 3D cloud status"
echo "completed rates: $done_count / $total_count"
echo "active transcpp:"
ps -Ao pid,etime,pcpu,pmem,command | awk '/[t]ranscpp .*runs\\/self_on/ {print}' || true
echo "last status lines:"
tail -20 cloud_status.tsv 2>/dev/null || true
