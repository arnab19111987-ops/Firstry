#!/usr/bin/env bash
set -euo pipefail
# Read-only audit script for FirstTry
# Writes logs to .firsttry/copilot/logs and prints a final JSON summary to stdout

LOGDIR=".firsttry/copilot/logs"
SCANFILE_FULL=".firsttry/copilot/scan_full.txt"
SCANFILE_EVIDENCE=".firsttry/copilot/scan_evidence.txt"
SUMMARYJSON=".firsttry/copilot/summary.json"
mkdir -p "$LOGDIR"

# Helper: run a command and capture stdout/stderr to a log file, but don't exit on failure
run_log() {
  local out="$1"; shift
  echo "Running: $*" > "$out"
  if "$@" >> "$out" 2>&1; then
    echo "[OK] $*" >> "$out"
    return 0
  else
    echo "[FAILED] $*" >> "$out"
    return 1
  fi
}

# 1) Environment
python -V > "$LOGDIR/python_version.log" 2>&1 || true
pip -V > "$LOGDIR/pip_version.log" 2>&1 || true
( command -v rg >/dev/null 2>&1 && rg --version > "$LOGDIR/rg_version.log" 2>&1 ) || ( grep --version > "$LOGDIR/grep_version.log" 2>&1 ) || true
pytest -V > "$LOGDIR/pytest_version.log" 2>&1 || true
( python -c "import importlib; importlib.import_module('mypy')" > "$LOGDIR/mypy_import.log" 2>&1 ) || true
( python -c "import importlib; importlib.import_module('ruff')" > "$LOGDIR/ruff_import.log" 2>&1 ) || true
( python -c "import importlib; importlib.import_module('bandit')" > "$LOGDIR/bandit_import.log" 2>&1 ) || true
node -v > "$LOGDIR/node_version.log" 2>&1 || true
npm -v > "$LOGDIR/npm_version.log" 2>&1 || true

# 2) Source scans (rg preferred)
if command -v rg >/dev/null 2>&1; then
  # Full deep scan (internal only)
  rg -n --hidden --no-ignore-vcs . > "$SCANFILE_FULL" 2>&1 || true

  # Trimmed, shareable evidence scan
  rg -n --hidden --no-ignore-vcs \
    "firsttry|telemetry|license_guard|cli.py|actions/checkout|upload-artifact|download-artifact" \
    | head -n 5000 > "$SCANFILE_EVIDENCE" 2>&1 || true
else
  # Fallback using grep
  grep -RIn --exclude-dir=.git --exclude-dir=.venv -E \
    "firsttry|telemetry|license_guard|cli.py|actions/checkout|upload-artifact|download-artifact" . > "$SCANFILE_EVIDENCE" 2>&1 || true
  # Also produce a full scan via grep (may be large)
  grep -RIn --exclude-dir=.git --exclude-dir=.venv . > "$SCANFILE_FULL" 2>&1 || true
fi

# Also capture list of key files
( ls -la .github || true ) > "$LOGDIR/github_workflows_list.log" 2>&1 || true
( ls -la src/firsttry || true ) > "$LOGDIR/src_firsttry_list.log" 2>&1 || true

# 3) Safe CLI probes (help and dry-run forms). Use python -m firsttry.cli where possible
run_log "$LOGDIR/cli_help.log" python -m firsttry.cli --help || true
run_log "$LOGDIR/cli_run_help.log" python -m firsttry.cli run --help || true
# Dry-run gate/probe using --dry-run or --dag-only if available
run_log "$LOGDIR/cli_run_dry_run.log" python -m firsttry.cli run --gate pre-commit --dry-run || true
# --require-license/--gate mapping smoke (should be non-mutating)
run_log "$LOGDIR/cli_require_license.log" python -m firsttry.cli run --gate pre-commit --require-license || true
# DAG-only listing
run_log "$LOGDIR/cli_dag_only.log" python -m firsttry.cli run --dag-only || true
# version
run_log "$LOGDIR/cli_version.log" python -m firsttry.cli version || true

# 4) Import reflection checks (non-destructive)
python - <<'PY' > "$LOGDIR/import_reflection.log" 2>&1 || true
import importlib, sys, json
modules = [
 'firsttry.cli', 'firsttry.license_guard', 'firsttry.config', 'firsttry.planner',
 'firsttry.planner.dag', 'firsttry.checks_orchestrator', 'firsttry.run_swarm'
]
out = {}
for m in modules:
    try:
        mod = importlib.import_module(m)
        out[m] = sorted([x for x in dir(mod) if not x.startswith('_')])[:200]
    except Exception as e:
        out[m] = f"IMPORT_ERROR: {e}"
print(json.dumps(out, indent=2))
PY

# 5) Search for GitHub Actions upload/action versions
if [ -d .github/workflows ]; then
  rg -n "actions/upload-artifact|uses: .*@v" .github/workflows > "$LOGDIR/github_actions_versions.log" 2>&1 || true
else
  echo "no workflows dir" > "$LOGDIR/github_actions_versions.log" 2>&1 || true
fi

# 6) List .firsttry artifacts (read-only listing)
mkdir -p .firsttry
ls -la .firsttry > "$LOGDIR/firsttry_root_list.log" 2>&1 || true
ls -la .firsttry/* > "$LOGDIR/firsttry_contents_list.log" 2>&1 || true || true

# 7) Collate simple PASS/FAIL/UNKNOWN checks by heuristics (non-authoritative)
cli_help_status=1
cli_run_help_status=1
python -m firsttry.cli --help > "$LOGDIR/cli_help.log" 2>&1 && cli_help_status=0 || true
python -m firsttry.cli run --help > "$LOGDIR/cli_run_help.log" 2>&1 && cli_run_help_status=0 || true

if [ "$cli_help_status" -eq 0 ] && [ "$cli_run_help_status" -eq 0 ]; then
  cli_status="PASS"
else
  cli_status="FAIL"
fi

if command -v jq >/dev/null 2>&1; then
  jq -n --arg cli "$cli_status" '{cli:$cli}' > "$SUMMARYJSON" || true
else
  printf '{"cli":"%s"}\n' "$cli_status" > "$SUMMARYJSON" || true
fi

# Print summary JSON to stdout (also leave it on disk)
cat "$SUMMARYJSON"

# Keep script exit code 0 per requirements
exit 0
