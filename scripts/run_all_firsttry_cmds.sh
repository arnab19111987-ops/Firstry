#!/usr/bin/env bash
set -euo pipefail

LOGDIR=benchmarks/ft_cmd_logs
mkdir -p "$LOGDIR" .firsttry
export PATH=$(pwd)/.venv/bin:$PATH
export PYTHONPATH=./src

# List of commands to run (as arrays)
CMDS=(
  "ft --help"
  "ft version"
  "ft lite --report-json .firsttry/free-lite.ent.json --show-report"
  "ft strict --report-json .firsttry/free-strict.ent.json --show-report"
  "ft pro --report-json .firsttry/pro.ent.json --show-report"
  "ft promax --report-json .firsttry/promax.ent.json --show-report"
  "ft doctor --tools"
  "ft doctor --check report-json --check telemetry"
  "ft setup --install-hooks"
  "ft dash --json .firsttry/cli_test.json"
  "ft lock --filter locked=true --json .firsttry/lock.json"
  "ft ruff --help"
  "ft mypy --help"
  "ft pytest --help"
)

SUMMARY=$LOGDIR/summary.tsv
echo -e "cmd\texit\tlog" > "$SUMMARY"

for c in "${CMDS[@]}"; do
  ts=$(date +%Y%m%d-%H%M%S)
  # Make a filesystem-safe name for the log file
  safe_name=$(echo "$c" | sed 's/[^A-Za-z0-9._-]/_/g' | tr -s '_')
  logfile="$LOGDIR/${ts}_${safe_name}.log"
  echo "=== Running: $c" | tee -a "$logfile"
  # Run and capture exit code
  bash -lc "$c" >>"$logfile" 2>&1 || rc=$?; rc=${rc:-0}
  echo -e "$c\t$rc\t$logfile" >> "$SUMMARY"
  echo "Wrote $logfile (rc=$rc)"
  # reset rc var
  rc=0
  sleep 1
done

echo "Done. Summary at $SUMMARY" 
