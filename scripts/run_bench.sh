#!/usr/bin/env bash
set -euo pipefail
mkdir -p benchmarks/ft_logs .firsttry

echo "== FREE-LITE =="
PYTHONPATH=./src ft lite --report-json .firsttry/free-lite.json --show-report | tee benchmarks/ft_logs/free-lite.now.log || true

echo "== FREE-STRICT =="
PYTHONPATH=./src ft strict --report-json .firsttry/free-strict.json --show-report | tee benchmarks/ft_logs/free-strict.now.log || true

if [[ -n "${FIRSTTRY_LICENSE_KEY:-}" ]]; then
  echo "== PRO =="
  PYTHONPATH=./src ft pro --report-json .firsttry/pro.json --show-report | tee benchmarks/ft_logs/pro.now.log || true
  echo "== PROMAX =="
  PYTHONPATH=./src ft promax --report-json .firsttry/promax.json --show-report | tee benchmarks/ft_logs/promax.now.log || true
else
  echo "ℹ️  FIRSTTRY_LICENSE_KEY not set; skipping paid tiers."
fi
