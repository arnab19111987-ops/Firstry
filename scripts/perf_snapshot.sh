#!/usr/bin/env bash
set -euo pipefail
export PYTHONPATH=./src
mkdir -p benchmarks/ft_logs .firsttry

ts="$(date +%Y%m%d-%H%M%S)"
for tier in lite strict; do
  echo "== FREE-$tier =="
  ft "$tier" --report-json ".firsttry/free-$tier.$ts.json" --show-report \
    2>&1 | tee "benchmarks/ft_logs/free-$tier.$ts.log" || true
done

if [[ -n "${FIRSTTRY_LICENSE_KEY:-}" ]]; then
  for tier in pro promax; do
    echo "== $tier =="
    ft "$tier" --report-json ".firsttry/$tier.$ts.json" --show-report \
      2>&1 | tee "benchmarks/ft_logs/$tier.$ts.log" || true
  done
fi

echo "✅ Perf snapshot complete -> benchmarks/ft_logs/*.$ts.log"
