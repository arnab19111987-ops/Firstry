#!/usr/bin/env bash
set -euo pipefail

export FIRSTTRY_SHARED_SECRET="${FIRSTTRY_SHARED_SECRET:-dev-fallback-secret-0123456789012345}"

tmp_dir=$(mktemp -d)
trap 'rm -rf "$tmp_dir"' EXIT

# You can copy a small representative project into $tmp_dir if you want to run
# the command against a sandbox. For now this runs in-place by default.
# Example to run in sandbox (uncomment):
# cp -r . "$tmp_dir"
# cd "$tmp_dir"

rc=""
for i in $(seq 1 30); do
  echo "Run #$i"
  set +e
  output=$(python -m firsttry.cli run 2>&1)
  code=$?
  set -e

  if [ -z "$rc" ]; then
    rc="$code"
  fi

  if [ "$code" -ne "$rc" ]; then
    echo "❌ Non-deterministic exit code: expected $rc but got $code on run #$i"
    echo "--- output ---"
    echo "$output"
    exit 1
  fi

  if echo "$output" | grep -i "Traceback" >/dev/null; then
    echo "❌ Traceback detected on run #$i"
    echo "--- output ---"
    echo "$output"
    exit 1
  fi
done

echo "✅ ft run is stable across 30 runs (exit code = $rc)"
