#!/usr/bin/env bash
set -euo pipefail
LOG="${1:-/tmp/pytest_full_rich.log}"

# 1) Normalize: strip ANSI and collapse CRs
CLEAN="$(mktemp)"
sed -E 's/\x1b\[[0-9;]*m//g' "$LOG" | tr -d '\r' > "$CLEAN"

echo "== file = $LOG"
echo

# 2) Collected line (first occurrence)
echo "== collected =="
grep -n -m1 '^collected [0-9]\+ items' "$CLEAN" || echo "n/a"
echo

# 3) Final overall summary line (pytest emits: === 123 passed, 2 skipped in 12.34s ===)
echo "== final summary line =="
FINAL_SUMMARY="$(grep -n '^[=]\{3,\} .* in [0-9.]\+s [=]\{3,\}$' "$CLEAN" | tail -n1 || true)"
if [ -n "$FINAL_SUMMARY" ]; then
  echo "$FINAL_SUMMARY"
else
  echo "n/a"
fi
echo

# 4) JSON badge (parse counts from final summary if present)
echo "== badge (json) =="
if [ -n "$FINAL_SUMMARY" ]; then
  LINE="${FINAL_SUMMARY#*:}"                    # drop line number prefix
  COUNTS="$(echo "$LINE" | sed -E 's/^=+ (.+) in ([0-9.]+)s =+$/\1|\2/')" || true
  PARTS="${COUNTS%|*}"
  SECS="${COUNTS#*|}"
  # normalize commas into newline, strip spaces
  echo "$PARTS" | tr ',' '\n' | sed -E 's/^ +| +$//g' | awk -v secs="$SECS" '
    BEGIN{passed=failed=skipped=xfailed=xpassed=errors=rerun=0}
    /([0-9]+) passed/{passed=$1}
    /([0-9]+) failed/{failed=$1}
    /([0-9]+) errors?/{errors=$1}
    /([0-9]+) skipped/{skipped=$1}
    /([0-9]+) xfailed/{xfailed=$1}
    /([0-9]+) xpassed/{xpassed=$1}
    /([0-9]+) rerun/{rerun=$1}
    END{
      printf("{\"passed\":%d,\"failed\":%d,\"errors\":%d,\"skipped\":%d,\"xfailed\":%d,\"xpassed\":%d,\"rerun\":%d,\"time_sec\":%s}\n",
        passed,failed,errors,skipped,xfailed,xpassed,rerun,secs)
    }'
else
  echo "n/a"
fi
echo

# 5) First failures/errors block (if any)
echo "== first failures/errors block =="
awk '
  BEGIN{p=0}
  /^= FAILURES =|^= ERRORS =/{p=1}
  p{print}
  /^=+ .* in [0-9.]+s =+$/{if(p){exit}}
' "$CLEAN" | sed -n '1,200p' | sed -E 's/[[:space:]]+$//' | sed '/^$/q' || true
echo

# 6) Short test summary (last one, up to 15 lines)
echo "== short test summary =="
START=$(grep -n 'short test summary info' "$CLEAN" | tail -n1 | cut -d: -f1 || true)
if [ -n "$START" ]; then
  sed -n "$((START)),$((START+15))p" "$CLEAN"
else
  echo "n/a"
fi
echo

# 7) Slowest durations block (if --durations used)
echo "== slowest durations (if present) =="
SLOW=$(grep -n '^=+ slowest ' "$CLEAN" | tail -n1 | cut -d: -f1 || true)
if [ -n "$SLOW" ]; then
  sed -n "$SLOW,$((SLOW+80))p" "$CLEAN"
else
  echo "n/a"
fi
echo

# 8) Final tail (last 120 lines)
echo "== tail (last 120 lines) =="
tail -n 120 "$CLEAN"
rm -f "$CLEAN"
