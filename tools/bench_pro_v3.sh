#!/usr/bin/env bash
set -euo pipefail

###############################################################################
# Strict + PRO benchmark harness (v3)
#
# What it measures:
# RAW:
#   pro_raw_ruff
#   pro_raw_mypy_src
#   pro_raw_pytest
#   pro_raw_bandit
#   pro_raw_pip_audit   (DISABLED BY DEFAULT)
#
# FIRSTTRY:
#   pro_ft_cold
#   pro_ft_warm
#
# Timing in milliseconds. Safe timeouts.
#
###############################################################################

REPO_ROOT="${REPO_ROOT:-/workspaces/Firstry}"
MAX_SECONDS_PER_CASE="${MAX_SECONDS_PER_CASE:-1800}"  # 30 minutes each if needed

cd "$REPO_ROOT"
mkdir -p .firsttry

ts="$(date -u +%Y%m%dT%H%M%SZ)"
BENCH_DIR=".firsttry/bench/manual/${ts}"
LOG_DIR="$BENCH_DIR/logs"
META_DIR="$BENCH_DIR/meta"

mkdir -p "$LOG_DIR" "$META_DIR"

echo "created $BENCH_DIR"
echo "$ts" > "$BENCH_DIR/TIMESTAMP"

MATRIX_FILE="$BENCH_DIR/bench_matrix.tsv"
echo -e "case_name\trc\telapsed_ms" > "$MATRIX_FILE"

now_ms() { date +%s%3N; }

run_case() {
    local case_name="$1"
    local cmd="$2"

    echo "==> Running case: $case_name"
    echo "$cmd" > "$META_DIR/$case_name.cmd"

    local start_ms end_ms elapsed_ms rc
    start_ms="$(now_ms)"

    set +e
    /usr/bin/env timeout --preserve-status "${MAX_SECONDS_PER_CASE}" \
        bash -lc "$cmd" >"$LOG_DIR/${case_name}.stdout" 2>"$LOG_DIR/${case_name}.stderr"
    rc=$?
    set -e

    end_ms="$(now_ms)"
    elapsed_ms=$((end_ms - start_ms))

    echo -e "${case_name}\t${rc}\t${elapsed_ms}" >> "$MATRIX_FILE"

    if [ "$rc" -eq 124 ]; then
        echo "   -> rc=$rc (TIMEOUT ~${elapsed_ms} ms)"
    else
        echo "   -> rc=$rc, elapsed=${elapsed_ms} ms"
    fi
}

###############################################################################
# RAW PRO TOOL RUNS
###############################################################################

run_case "pro_raw_ruff"       "ruff check ."
run_case "pro_raw_mypy_src"   "mypy src --pretty"
run_case "pro_raw_pytest"     "pytest -q"
run_case "pro_raw_bandit"     "bandit -q -r ."

# DISABLED BY DEFAULT – pip-audit is extremely heavy in Codespaces.
# Enable only if needed:
# run_case "pro_raw_pip_audit" "pip-audit"

###############################################################################
# FIRSTTRY PRO (COLD + WARM)
###############################################################################

run_case "pro_ft_cold" "
rm -rf .firsttry/cache && \
python -m firsttry.cli run pro --json
"

run_case "pro_ft_warm" "
python -m firsttry.cli run pro --json
"

echo
echo "PRO benchmark v3 complete."
echo "Matrix: $MATRIX_FILE"
echo "Logs:   $LOG_DIR"
