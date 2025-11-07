#!/usr/bin/env bash
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1

clean() { rm -rf .firsttry/cache .firsttry/logs .firsttry/report.json || true; }

run() {
  label="$1"; shift
  { time "$@"; } 2>&1 | tee -a .firsttry/audit/STEP_11_speedfix.log
  echo "$label completed" | tee -a .firsttry/audit/STEP_11_speedfix.log
}

mkdir -p .firsttry/audit

echo "== Cold =="
clean
run "Cold" env PYTHONPATH=src python -m firsttry.cli_dag run --report-json .firsttry/report.json

echo ""
echo "== Warm =="
run "Warm" env PYTHONPATH=src python -m firsttry.cli_dag run --report-json .firsttry/report.json

echo ""
echo "== Warm+Prune (touch 1 test) =="
touch tests/test_ok.py
run "Warm+Prune" env PYTHONPATH=src python -m firsttry.cli_dag run --report-json .firsttry/report.json --prune-tests

echo ""
echo "---- Proof (report.json excerpts) ----"
python - <<'PY'
import json, pathlib
p = pathlib.Path(".firsttry/report.json")
r = json.loads(p.read_text())
print("levels:", r.get("levels"))
print("level_stats:", r.get("level_stats"))
print("prune_metadata:", r.get("prune_metadata"))
tasks = r.get("tasks", [])
for t in tasks:
    dur = t.get("duration_s", 0)
    print(f"- {t['id']}: level={t.get('level')} code={t['code']} dur={dur:.3f}s")
    if t["id"] == "pytest":
        cmd_str = " ".join(t.get("cmd", []))
        print(f"  pytest cmd: {cmd_str[:180]}", "..." if len(cmd_str) > 180 else "")
PY
