#!/usr/bin/env bash
set -euo pipefail

# -------- Config --------
# Adjust targets as needed:
PY_SRC_DIRS=${PY_SRC_DIRS:-"src"}
PY_TEST_DIRS=${PY_TEST_DIRS:-"tests"}
BANDIT_PATHS=${BANDIT_PATHS:-"src"}
TIER=${TIER:-"lite"}            # free-lite | lite | pro | strict
OUTROOT=${OUTROOT:-".firsttry/bench"}
LOGDIR="$OUTROOT/logs"
RPTDIR="$OUTROOT/reports"

mkdir -p "$LOGDIR" "$RPTDIR"

# Ensure FT wrapper exists; otherwise run via python -m
FT_BIN=${FT_BIN:-".venv/bin/ft"}
if [ ! -x "$FT_BIN" ]; then
  mkdir -p .venv/bin
  cat > .venv/bin/ft <<'SH'
#!/usr/bin/env bash
export PYTHONPATH=src
exec python -m firsttry.cli "$@"
SH
  chmod +x .venv/bin/ft
fi

export PYTHONPATH=src
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1

ts() { date -u +"%Y%m%dT%H%M%SZ"; }
# POSIX-safe timer
time_s() { python - "$@" <<'PY'
import subprocess, sys, time, json
cmd = sys.argv[1:]
t0=time.perf_counter()
p = subprocess.run(cmd, capture_output=True, text=True)
t1=time.perf_counter()
out = {
  "rc": p.returncode,
  "elapsed_s": round(t1-t0, 6),
  "stdout": p.stdout,
  "stderr": p.stderr,
  "cmd": cmd,
}
print(json.dumps(out))
PY
}

# -------- Manual runs --------
run_manual_ruff() {
  local name="manual_ruff"; local tgt="$PY_SRC_DIRS $PY_TEST_DIRS"
  # JSON output to count diagnostics reliably
  time_s ruff check $PY_SRC_DIRS $PY_TEST_DIRS --output-format json | tee "$LOGDIR/${name}.json" >/dev/null
}

run_manual_mypy() {
  local name="manual_mypy"
  time_s mypy $PY_SRC_DIRS --no-color-output --hide-error-context | tee "$LOGDIR/${name}.json" >/dev/null
}

run_manual_pytest() {
  local name="manual_pytest"
  time_s pytest -q $PY_TEST_DIRS | tee "$LOGDIR/${name}.json" >/dev/null
}

run_manual_bandit() {
  local name="manual_bandit"
  time_s bandit -q -r $BANDIT_PATHS -f json | tee "$LOGDIR/${name}.json" >/dev/null
}

echo "== [$(ts)] Running manual checks =="
run_manual_ruff
run_manual_mypy
run_manual_pytest
run_manual_bandit || true   # bandit often returns nonzero

# -------- FT runs (cold → warm) --------
echo "== [$(ts)] Running FT (cold) =="
$FT_BIN run --tier "$TIER" --show-report || true
cp .firsttry/report.json "$RPTDIR/ft_${TIER}_cold.json" || true

echo "== [$(ts)] Running FT (warm) =="
$FT_BIN run --tier "$TIER" --show-report || true
cp .firsttry/report.json "$RPTDIR/ft_${TIER}_warm.json" || true

echo "Artifacts:"
echo " - Logs:    $LOGDIR"
echo " - Reports: $RPTDIR"
