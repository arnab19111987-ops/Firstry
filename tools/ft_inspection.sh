#!/usr/bin/env bash
set -euo pipefail
echo "== FirstTry structural inspection =="

req=(
  "src/firsttry/planner/dag.py"
  "src/firsttry/executor/dag.py"
  "src/firsttry/reporting/renderer.py"
  "src/firsttry/reporting/html.py"
  "src/firsttry/runners/ruff.py"
  "src/firsttry/runners/mypy.py"
  "src/firsttry/runners/pytest.py"
  "src/firsttry/runners/bandit.py"
  "src/firsttry/runners/npm_lint.py"
  "src/firsttry/runners/npm_test.py"
  "src/firsttry/runners/registry.py"
)
miss=0
for f in "${req[@]}"; do
  if [[ -f "$f" ]]; then echo "✅ $f"; else echo "❌ $f"; miss=$((miss+1)); fi
done
[[ $miss -eq 0 ]] && echo "PASS" || { echo "FAIL ($miss missing)"; exit 2; }
