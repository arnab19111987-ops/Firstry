#!/usr/bin/env bash
set -euo pipefail

# ===== CONFIGURATION =====
REPO_ROOT="/workspaces/Firstry"
MAX_SECONDS_PER_CASE="${MAX_SECONDS_PER_CASE:-900}"  # 15 minutes default per case

cd "$REPO_ROOT"

mkdir -p .firsttry

ts="$(date -u +%Y%m%dT%H%M%SZ)"
BENCH_DIR=".firsttry/bench/manual/$ts"
LOG_DIR="$BENCH_DIR/logs"
META_DIR="$BENCH_DIR/meta"

mkdir -p "$LOG_DIR" "$META_DIR"

echo "created $BENCH_DIR"
echo "$ts" > "$BENCH_DIR/TIMESTAMP"

MATRIX_FILE="$BENCH_DIR/bench_matrix.tsv"
echo -e "case_name\trc\telapsed_seconds" > "$MATRIX_FILE"

run_case() {
    local case_name="$1"
    local cmd="$2"

    echo "==> Running case: $case_name"
    echo "$cmd" > "$META_DIR/$case_name.cmd"

    local start end elapsed rc

    start="$(date +%s)"

    # run with timeout so nothing can hang forever
    set +e
    /usr/bin/env timeout --preserve-status "$MAX_SECONDS_PER_CASE" \
        bash -lc "$cmd" >"$LOG_DIR/${case_name}.stdout" 2>"$LOG_DIR/${case_name}.stderr"
    rc=$?
    set -e

    end="$(date +%s)"
    elapsed=$(( end - start ))

    echo -e "${case_name}\t${rc}\t${elapsed}" >> "$MATRIX_FILE"

    if [ "$rc" -eq 124 ]; then
        echo "   -> rc=$rc (TIMEOUT after ${elapsed}s)"
    else
        echo "   -> rc=$rc, elapsed=${elapsed}s"
    fi
}

########################################
# RAW BASELINE (LIGHT SET FIRST)
########################################

# Start with a minimal, cheap set so the terminal doesn't die:
# - free-lite_raw: ruff only
# - free-strict_raw: ruff + mypy + pytest

run_case "free-lite_raw"   "ruff check ."

run_case "free-strict_raw" "
ruff check . && \
mypy . --pretty && \
pytest -q
"

########################################
# FIRSTTRY TIERS (COLD RUN, NO CACHE)
########################################

run_case "free-lite_ft_fast_nocache" "
python -m firsttry.cli run fast --json --no-cache
"

run_case "free-strict_ft_strict_cold" "
rm -rf .firsttry/cache && \
python -m firsttry.cli run strict --json
"

# If you want to include pro / promax, UNCOMMENT these one by one
# once the above runs cleanly and you know the box can handle it.

# run_case "pro_raw" "
# ruff check . && \
# mypy . --pretty && \
# pytest -q && \
# bandit -q -r .
# "

# run_case "promax_raw" "
# ruff check . && \
# mypy . --pretty && \
# pytest -q && \
# bandit -q -r . && \
# pip-audit
# "

# run_case "pro_ft_nocache" "
# python -m firsttry.cli run pro --json --no-cache
# "

# run_case "promax_ft_nocache" "
# python -m firsttry.cli run promax --json --no-cache
# "

########################################
# OPTIONAL: WARM-CACHE PASS (SAFE)
########################################

run_case "free-lite_ft_fast_warm" "
python -m firsttry.cli run fast --json
"

run_case "free-strict_ft_strict_warm" "
python -m firsttry.cli run strict --json
"

# And same idea here – only enable if you're comfortable with load:
# run_case "pro_ft_warm" "
# python -m firsttry.cli run pro --json
# "
#
# run_case "promax_ft_warm" "
# python -m firsttry.cli run promax --json
# "

echo
echo "Benchmark complete. Matrix: $MATRIX_FILE"
echo "Logs: $LOG_DIR"
