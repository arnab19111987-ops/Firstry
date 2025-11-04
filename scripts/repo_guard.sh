#!/usr/bin/env bash
set -euo pipefail

echo "▶ Repo guard: scanning for forbidden patterns…"
for p in src/firsttry; do
  if grep -REn "(pass|NotImplementedError|TODO|FIXME)" "$p" >/dev/null 2>&1; then
    echo "❌ Stubs/TODO found in $p"
    grep -REn "(pass|NotImplementedError|TODO|FIXME)" "$p" | sed 's/^/  /'
    exit 1
  fi
done
echo "✅ Guard clean"
