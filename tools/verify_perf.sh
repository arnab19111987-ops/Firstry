#!/usr/bin/env bash
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1

clean() { rm -rf .firsttry/cache .firsttry/logs .firsttry/report.json || true; }

run() {
  label="$1"; shift
  echo "Running $label..."
  time "$@"
  echo "$label completed"
  echo ""
}

mkdir -p .firsttry/audit

echo "== Cold (no cache) =="
clean
run "Cold" env PYTHONPATH=src python -m firsttry.cli_dag run --report-json .firsttry/report.json

echo "== Warm (plan cached) =="
run "Warm" env PYTHONPATH=src python -m firsttry.cli_dag run --report-json .firsttry/report.json

echo "== Zero-run (full cache hit) =="
run "Zero-run" env PYTHONPATH=src python -m firsttry.cli_dag run --report-json .firsttry/report.json

echo "== Partial cache (touch 1 file to invalidate some tasks) =="
touch src/firsttry/__init__.py
run "Partial" env PYTHONPATH=src python -m firsttry.cli_dag run --report-json .firsttry/report.json

echo "== Warm+Prune (touch 1 test) =="
touch tests/test_ok.py
run "Warm+Prune" env PYTHONPATH=src python -m firsttry.cli_dag run --report-json .firsttry/report.json --prune-tests

echo "---- Proof (report.json excerpts) ----"
python - <<'PY'
import json, pathlib
p = pathlib.Path(".firsttry/report.json")
r = json.loads(p.read_text())
print("verified_from_cache:", r.get("verified_from_cache"))
print("levels:", r.get("levels"))
print("level_stats:", r.get("level_stats"))
print("prune_metadata:", r.get("prune_metadata"))
tasks = r.get("tasks", [])
for t in tasks:
    dur = t.get("duration_s", 0)
    cache = t.get("cache", "unknown")
    print(f"- {t['id']}: level={t.get('level')} code={t['code']} dur={dur:.3f}s cache={cache}")
    if t["id"] == "pytest":
        cmd_str = " ".join(t.get("cmd", []))
        print(f"  pytest cmd: {cmd_str[:180]}", "..." if len(cmd_str) > 180 else "")
PY

