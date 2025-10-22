#!/usr/bin/env bash
set -euo pipefail

run_one() {
  local dir="$1"
  if [[ ! -d "$dir" || ! -f "$dir/package.json" ]]; then
    echo "→ skip $dir (no package.json)"; return 0
  fi
  echo "=== $dir ==="
  pushd "$dir" >/dev/null

  if [[ -f package-lock.json ]]; then
    if ! npm ci --no-audit --no-fund; then
      echo "npm ci failed → falling back to npm install"
      npm install --no-audit --no-fund
    fi
  else
    npm install --no-audit --no-fund
  fi

  npm run --if-present lint
  npm run --if-present typecheck
  CI=1 npm test --if-present --silent
  npm run --if-present build
  popd >/dev/null
}

run_one "dashboard"
run_one "vscode-extension"

echo "✓ Node validation complete"
