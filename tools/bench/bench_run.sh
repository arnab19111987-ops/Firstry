#!/usr/bin/env bash
set -euo pipefail
# bench_run.sh
# Run one cell (scenario x mode x toolchain) for N trials and append JSONL rows.

SCENARIO=${SCENARIO:-lite}
MODE=${MODE:-cold}   # cold|warm
TOOLCHAIN=${TOOLCHAIN:-ft} # ft|manual
TRIALS=${TRIALS:-3}
OUTDIR=${OUTDIR:-.firsttry/bench/raw}

mkdir -p "$OUTDIR"

RAWFILE="$OUTDIR/${SCENARIO}.${MODE}.${TOOLCHAIN}.jsonl"

git_sha=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
cpu_count=$(nproc 2>/dev/null || getconf _NPROCESSORS_ONLN 2>/dev/null || echo 1)

timestamp_iso() { date -u --iso-8601=seconds 2>/dev/null || python - <<'PY'
import datetime
print(datetime.datetime.utcnow().isoformat()+'Z')
PY
}

mono_time() { # seconds with nanoseconds
  date +%s.%N 2>/dev/null || python - <<'PY'
import time
print(repr(time.time()))
PY
}

capture_versions() {
  ft_ver=""
  if command -v ft >/dev/null 2>&1; then
    ft_ver=$(ft --version 2>&1 | head -n1 || true)
  elif python -m firsttry --version >/dev/null 2>&1; then
    ft_ver=$(python -m firsttry --version 2>&1 | head -n1 || true)
  fi
  ruff_ver=$(ruff --version 2>&1 | head -n1 || true || echo "missing")
  mypy_ver=$(mypy --version 2>&1 | head -n1 || true || echo "missing")
  pytest_ver=$(pytest --version 2>&1 | head -n1 || true || echo "missing")
  bandit_ver=$(bandit --version 2>&1 | head -n1 || true || echo "missing")
  echo "$ft_ver|$ruff_ver|$mypy_ver|$pytest_ver|$bandit_ver"
}

# Mapping of scenarios -> manual commands
manual_cmd_for() {
  case "$1" in
    lite)
      echo "ruff check ."
      ;;
    strict)
      echo "ruff check . && mypy ."
      ;;
    pro)
      echo "ruff check . && mypy . && pytest -q && bandit -r ."
      ;;
    promax)
      # best-effort: run pro plus pip-audit if available
      echo "ruff check . && mypy . && pytest -q && bandit -r . && python -m pip_audit || true"
      ;;
    *)
      echo "";
      ;;
  esac
}

resolve_ft_cmd() {
  # Prefer ft wrapper if present else use python -m firsttry run --tier <scenario>
  if command -v ft >/dev/null 2>&1; then
    echo "ft $1 --show-report"
  else
    echo "python -m firsttry run --tier $1 --show-report"
  fi
}

check_toolchain_available() {
  if [ "$TOOLCHAIN" = "ft" ]; then
    if command -v ft >/dev/null 2>&1 || python -m firsttry --version >/dev/null 2>&1; then
      return 0
    else
      return 1
    fi
  else
    # manual: check required tools roughly by scenario
    cmd=$(manual_cmd_for "$SCENARIO")
    # extract words that look like tool names and check first token
    for tool in ruff mypy pytest bandit python; do
      if echo "$cmd" | grep -qw "$tool"; then
        if ! command -v $tool >/dev/null 2>&1 && ! ( [ "$tool" = "python" ] && command -v python >/dev/null 2>&1); then
          return 2
        fi
      fi
    done
    return 0
  fi
}

run_one_trial() {
  local trial=$1
  # For cold: remove caches before each trial
  if [ "$MODE" = "cold" ]; then
    rm -rf .firsttry .ruff_cache .mypy_cache .pytest_cache .coverage .cache node_modules/.cache || true
  fi

  local cmd=""
  if [ "$TOOLCHAIN" = "ft" ]; then
    cmd=$(resolve_ft_cmd "$SCENARIO")
  else
    cmd=$(manual_cmd_for "$SCENARIO")
  fi

  if [ -z "$cmd" ]; then
    echo "{\"scenario\":\"$SCENARIO\",\"toolchain\":\"$TOOLCHAIN\",\"skipped\":true,\"reason\":\"unknown scenario\"}" >> "$RAWFILE"
    return
  fi

  # capture versions
  ver_line=$(capture_versions)
  IFS='|' read -r ft_ver ruff_ver mypy_ver pytest_ver bandit_ver <<< "$ver_line"

  # For warm: on first trial do a warm-up run (unmeasured)
  if [ "$MODE" = "warm" ] && [ "$trial" -eq 1 ]; then
    echo "[warmup] $TOOLCHAIN $SCENARIO"
    sh -c "$cmd" >/dev/null 2>&1 || true
  fi

  # measure
  tmp_out=$(mktemp)
  tmp_time=$(mktemp)
  start_iso=$(timestamp_iso)
  start_mono=$(mono_time)

  # Use /usr/bin/time to measure user/sys/real; redirect command output to tmp_out
  if command -v /usr/bin/time >/dev/null 2>&1; then
    /usr/bin/time -p -o "$tmp_time" sh -c "$cmd" >"$tmp_out" 2>&1 || RC=$? || true
    RC=${RC:-0}
  else
    # fallback: use bash time and hope
    (time sh -c "$cmd") >"$tmp_out" 2>&1 || RC=$? || true
    RC=${RC:-0}
    # fake time file
    echo "real 0.0" >"$tmp_time"
    echo "user 0.0" >>"$tmp_time"
    echo "sys 0.0" >>"$tmp_time"
  fi

  end_iso=$(timestamp_iso)
  end_mono=$(mono_time)

  # parse time file
  real_s=$(grep -E '^real ' "$tmp_time" 2>/dev/null | awk '{print $2}' || echo 0)
  user_s=$(grep -E '^user ' "$tmp_time" 2>/dev/null | awk '{print $2}' || echo 0)
  sys_s=$(grep -E '^sys ' "$tmp_time" 2>/dev/null | awk '{print $2}' || echo 0)

  out=$(sed -n '1,200p' "$tmp_out" | sed 's/"/\\"/g' | awk '{printf "%s\\n", $0}' | sed ':a;N;$!ba;s/\n/\\n/g')
  # capture stderr snippet (last 200 chars)
  stderr_snippet=$(tail -c 200 "$tmp_out" | sed 's/"/\\"/g' | tr -d '\r' | sed ':a;N;$!ba;s/\n/\\n/g')

  ok_bool=true
  if [ "$RC" -ne 0 ]; then
    ok_bool=false
  fi

  cat >>"$RAWFILE" <<EOF
{"scenario":"$SCENARIO","toolchain":"$TOOLCHAIN","command":"$cmd","run_mode":"$MODE","trial":$trial,"wall_seconds":$real_s,"user_seconds":$user_s,"sys_seconds":$sys_s,"rc":$RC,"ok":$ok_bool,"start_iso":"$start_iso","end_iso":"$end_iso","start_mono":"$start_mono","end_mono":"$end_mono","git_sha":"$git_sha","cpu_count":$cpu_count,"ft_version":"$ft_ver","ruff_version":"$ruff_ver","mypy_version":"$mypy_ver","pytest_version":"$pytest_ver","bandit_version":"$bandit_ver","stderr_snippet":"$stderr_snippet"}
EOF

  rm -f "$tmp_out" "$tmp_time"
}

main() {
  check_toolchain_available || {
    echo "Toolchain $TOOLCHAIN not available for scenario $SCENARIO; writing skip entry"
    echo "{\"scenario\":\"$SCENARIO\",\"toolchain\":\"$TOOLCHAIN\",\"skipped\":true}" >> "$RAWFILE"
    return 0
  }

  for i in $(seq 1 "$TRIALS"); do
    echo "[run] $SCENARIO $MODE $TOOLCHAIN trial $i"
    run_one_trial $i
  done
}

main
