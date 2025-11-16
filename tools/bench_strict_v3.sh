#!/usr/bin/env bash
set -euo pipefail

###############################################################################
# Strict-only benchmark harness (v3)
#
# What it measures:
#   1) strict_raw_ruff       -> ruff check .
#   2) strict_raw_mypy_src   -> mypy src --pretty
#   3) strict_raw_pytest     -> pytest -q
#   4) strict_ft_strict_cold -> rm -rf .firsttry/cache && ft strict (full tier)
#   5) strict_ft_strict_warm -> ft strict again (warm FT cache)
#
# All timings are recorded in milliseconds in bench_matrix.tsv.
#
# Usage:
#   chmod +x tools/bench_strict_v3.sh
#   ./tools/bench_strict_v3.sh
#
# Optional env tweaks:
#   MAX_SECONDS_PER_CASE=1800 ./tools/bench_strict_v3.sh
#   REPO_ROOT=/some/other/path ./tools/bench_strict_v3.sh
###############################################################################

REPO_ROOT="${REPO_ROOT:-/workspaces/Firstry}"
MAX_SECONDS_PER_CASE="${MAX_SECONDS_PER_CASE:-1800}"  # 30 minutes per case by default

cd "$REPO_ROOT"

mkdir -p .firsttry

ts="$(date -u +%Y%m%dT%H%M%SZ)"
BENCH_DIR=".firsttry/bench/manual/${ts}"
#!/usr/bin/env bash
set -euo pipefail

# Canonical public strict-only benchmark harness.
# Lightweight and safe for contributors to run locally.
# Heavy experimental harnesses live under tools/internal/ and won't run
# unless explicitly invoked by maintainers.

REPO_ROOT="/workspaces/Firstry"
MAX_SECONDS_PER_CASE="${MAX_SECONDS_PER_CASE:-900}"

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

now_ms() { date +%s%3N; }

run_case_ms() {
    local case_name="$1"
    local cmd="$2"

    echo "==> Running case: $case_name"
    echo "$cmd" > "$META_DIR/$case_name.cmd"

    local start end elapsed rc
    start="$(now_ms)"

    set +e
    /usr/bin/env timeout --preserve-status "$MAX_SECONDS_PER_CASE" \
        bash -lc "$cmd" >"$LOG_DIR/${case_name}.stdout" 2>"$LOG_DIR/${case_name}.stderr"
    rc=$?
    set -e

    end="$(now_ms)"
    elapsed=$(( (end - start) / 1000 ))

    echo -e "${case_name}\t${rc}\t${elapsed}" >> "$MATRIX_FILE"

    if [ "$rc" -eq 124 ]; then
        echo "   -> rc=$rc (TIMEOUT after ${elapsed}s)"
    else
        echo "   -> rc=$rc, elapsed=${elapsed}s"
    fi
}

# RAW BASELINE
run_case_ms "strict_raw_ruff" "ruff check ."
run_case_ms "strict_raw_mypy_src" "mypy src --pretty"
run_case_ms "strict_raw_pytest" "pytest -q"

# FIRSTTRY (cold)
run_case_ms "strict_ft_strict_cold" "rm -rf .firsttry/cache && python -m firsttry.cli run strict --json"

# FIRSTTRY (warm)
run_case_ms "strict_ft_strict_warm" "python -m firsttry.cli run strict --json"

echo
echo "Benchmark complete. Matrix: $MATRIX_FILE"
echo "Logs: $LOG_DIR"
run_case "strict_ft_strict_cold" "
rm -rf .firsttry/cache && \
python -m firsttry.cli run strict --json
"

# 5) FT strict "warm" (immediately after, so FT cache is hot)
run_case "strict_ft_strict_warm" "
python -m firsttry.cli run strict --json
"

echo
echo "Strict benchmark (v3) complete."
echo "Matrix: $MATRIX_FILE"
echo "Logs:   $LOG_DIR"
