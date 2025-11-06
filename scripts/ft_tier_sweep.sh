#!/usr/bin/env bash
set -euo pipefail

# Config
TIERS=(${TIERS:-free-lite lite pro strict})
OUTDIR=${OUTDIR:-.firsttry/reports}
LOGDIR=${LOGDIR:-.firsttry/logs}

mkdir -p "$OUTDIR" "$LOGDIR"

export PYTHONPATH=src
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1

ts() { date -u +"%Y%m%dT%H%M%SZ"; }

run_one() {
  local tier="$1" phase="$2" tstamp; tstamp="$(ts)"
  echo "== [$tstamp] tier=$tier phase=$phase =="
  # run via your CLI (DAG path)
  .venv/bin/ft run --tier "$tier" --show-report 2>&1 | tee "$LOGDIR/${tstamp}_${tier}_${phase}.log" || true

  # stash the report.json with a deterministic name
  local src=".firsttry/report.json"
  local dst="$OUTDIR/${tstamp}_${tier}_${phase}.json"
  if [ -f "$src" ]; then
    cp "$src" "$dst"
    echo "saved report: $dst"
  else
    echo "WARN: no report.json for tier=$tier phase=$phase" >&2
  fi
}

for tier in "${TIERS[@]}"; do
  run_one "$tier" "cold"
  run_one "$tier" "warm"
done

echo "All done. Reports in $OUTDIR, logs in $LOGDIR"
