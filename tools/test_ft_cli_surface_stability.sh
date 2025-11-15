#!/usr/bin/env bash
set -euo pipefail

# Run stability checks for the Dev CLI surface commands.
# Usage: FT_STABILITY_ITER=10 tools/test_ft_cli_surface_stability.sh

export FIRSTTRY_SHARED_SECRET="${FIRSTTRY_SHARED_SECRET:-dev-fallback-secret-0123456789012345}"
ITER=${FT_STABILITY_ITER:-10}

tmp_dir=$(mktemp -d)
trap 'rm -rf "$tmp_dir"' EXIT

echo "Running CLI surface stability checks (iterations=$ITER)"

run_cmd() {
  local desc="$1"; shift
  local cmd=("$@")

  echo "\n=== Command: $desc -> ${cmd[*]} ==="

  rc=""
  for i in $(seq 1 "$ITER"); do
    echo "Run #$i"
    set +e
    output=$("${cmd[@]}" 2>&1 || true)
    code=$?
    set -e

    if [ -z "$rc" ]; then
      rc="$code"
    fi

    if [ "$code" -ne "$rc" ]; then
      echo "❌ Non-deterministic exit code for ${cmd[*]}: expected $rc but got $code on run #$i"
      echo "--- output ---"
      echo "$output"
      return 1
    fi

    if echo "$output" | grep -i "Traceback" >/dev/null; then
      echo "❌ Traceback detected for ${cmd[*]} on run #$i"
      echo "--- output ---"
      echo "$output"
      return 1
    fi
  done

  echo "✅ ${desc} stable across $ITER runs (exit code=$rc)"
  return 0
}

# 1) ft run
run_cmd "ft run" python -m firsttry.cli run || exit 1

# 2) ft init -- run in a sandbox copy to avoid mutating working tree
echo "Preparing sandbox for ft init"
cp -a . "$tmp_dir/replica" || true
pushd "$tmp_dir/replica" >/dev/null
run_cmd "ft init (sandbox)" python -m firsttry.cli init || { popd >/dev/null; exit 1; }
popd >/dev/null

# 3) ft pre-commit (hook contract)
export GIT_HOOK=pre-push
export FT_NO_NETWORK=1
run_cmd "ft pre-commit" python -m firsttry.cli pre-commit || exit 1

# 4) ft cache clear
run_cmd "ft cache clear" python -m firsttry.cli cache clear || exit 1

# 5) ft parity (warn-only)
run_cmd "ft parity (warn-only)" python -m firsttry.cli parity || exit 1

echo "\nAll CLI surface commands stable across $ITER runs"
