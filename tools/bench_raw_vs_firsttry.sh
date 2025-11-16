#!/usr/bin/env bash
set -euo pipefail

# Drop-in harness: run raw tools vs FirstTry runs and record immutable artifacts

# --------- 0. Setup ---------
TS="$(date -u +%Y%m%dT%H%M%SZ)"
BENCH_DIR=".firsttry/bench/manual/${TS}"
LOGS="${BENCH_DIR}/logs"
META="${BENCH_DIR}/meta"
MATRIX="${BENCH_DIR}/bench_matrix.tsv"

mkdir -p "${LOGS}" "${META}"

echo "Benchmark timestamp (UTC): ${TS}"
echo "Benchmark dir: ${BENCH_DIR}"

# Record context for proof
{
  echo "timestamp_utc=${TS}"
  echo "pwd=$(pwd)"
  echo "git_head=$(git rev-parse HEAD 2>/dev/null || echo 'NO_GIT')"
  # Indicate whether working tree is clean
  (git diff --quiet 2>/dev/null && echo "git_status_clean=yes") || echo "git_status_clean=no"
  echo "python_version=$(python -V 2>&1 || echo 'unknown')"
  echo "firsttry_version=$(python -m firsttry.cli --version 2>&1 || echo 'unknown')"
  echo "pyproject_sha256=$(sha256sum pyproject.toml 2>/dev/null || echo 'missing')"
} > "${META}/context.env"

# Copy context for quick manual inspection
cat "${META}/context.env"

# --------- 1. Define cases ---------
# label | kind | command
CASES=(
  "free-lite_raw|raw|ruff check ."
  "free-lite_ft|firsttry|python -m firsttry.cli run fast --json"
  "free-strict_raw|raw|ruff check . && mypy . --pretty && pytest -q"
  "free-strict_ft|firsttry|python -m firsttry.cli run strict --json"
)

echo -e "label\tkind\tseconds\texit_code" > "${MATRIX}"

run_case() {
  local label="$1"
  local kind="$2"
  shift 2
  local cmd="$*"

  echo
  echo "=== CASE: ${label} (${kind}) ==="
  echo "CMD: ${cmd}"

  local base="${label}_${kind}"
  local out="${LOGS}/${base}.stdout"
  local err="${LOGS}/${base}.stderr"
  local timef="${LOGS}/${base}.time"
  local meta="${META}/${base}.env"

  # Record per-case meta (command + env)
  {
    echo "label=${label}"
    echo "kind=${kind}"
    echo "cmd=${cmd}"
  } > "${meta}"

  # 900s timeout to avoid hangs (15 minutes per bundle)
  rc=0
  /usr/bin/time -f "%e" -o "${timef}" timeout 900 bash -lc "${cmd}" >"${out}" 2>"${err}" || rc=$?

  seconds="$(cat "${timef}" 2>/dev/null || echo "")"

  echo "     rc=${rc}, seconds=${seconds}"
  echo -e "${label}\t${kind}\t${seconds}\t${rc}" >> "${MATRIX}"

  # If this is a firsttry run, copy the JSON report into the bench dir for proof
  if [[ "${kind}" == "firsttry" ]]; then
    if [[ -f ".firsttry/report.json" ]]; then
      cp ".firsttry/report.json" "${BENCH_DIR}/${base}_report.json"
    fi
  fi
}

for entry in "${CASES[@]}"; do
  IFS="|" read -r label kind cmd <<< "${entry}"
  run_case "${label}" "${kind}" ${cmd}
done

echo
echo "=== DONE ==="
echo "Benchmark directory: ${BENCH_DIR}"
echo "Matrix:"
cat "${MATRIX}"
