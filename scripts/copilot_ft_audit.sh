#!/usr/bin/env bash
set -euo pipefail

# READ-ONLY: do not export demo or license keys here; we only audit behavior.
# Ensure directories
mkdir -p .firsttry .firsttry/copilot logs

PROBE="scripts/_ft_probe.py"
REPORT_MD=".firsttry/copilot_ft_audit_report.md"
REPORT_JSONL=".firsttry/copilot_ft_audit_report.jsonl"

chmod +x "$PROBE" || true

entrypoints=(
  "ft"
  "firsttry"
  "python -m firsttry.cli"
)

# Matrix of safe invocations (non-destructive)
declare -a COMMANDS=(
  "--help"
  "--version"
  "run --gate pre-commit --dry-run"
  "mirror-ci --dry-run"
  "doctor --dry-run"
  "gates list"
  "install-hooks --check"
)

# Clean previous report
: > "$REPORT_JSONL"

# Utility: run and append jsonl
run_probe () {
  local line="$1"
  # Split line into array safely
  # shellcheck disable=SC2206
  args=($line)
  python "$PROBE" "${args[@]}" | tee -a "$REPORT_JSONL" >/dev/null
}

# Expand command matrix for each entrypoint
for ep in "${entrypoints[@]}"; do
  # help/version are standalone
  run_probe "$ep --help"
  run_probe "$ep --version"

  # subcommands
  for sub in "${COMMANDS[@]}"; do
    run_probe "$ep $sub"
  done
done

# Build Markdown summary
{
  echo "# FirstTry CLI Audit (Read-only, Report-only, No-fix)"
  echo
  echo "- Timestamp: $(date -u +'%Y-%m-%d %H:%M:%S UTC')"
  echo "- Host: $(uname -a)"
  echo "- Python: $(python -V 2>&1 || true)"
  echo
  echo "## Results"
  echo
  echo "| Command | Exit | Status | Duration (ms) | Error Summary | Traceback |"
  echo "|--------|------|--------|---------------:|---------------|-----------|"

  python - <<'PY'
import json, sys
from pathlib import Path

p = Path(".firsttry/copilot_ft_audit_report.jsonl")
for line in p.read_text().splitlines():
    try:
        rec = json.loads(line)
    except Exception:
        continue
    cmd = " ".join(rec.get("cmd", []))
    exit_code = rec.get("exit_code")
    dur = rec.get("duration_ms")
    tb = "YES" if rec.get("has_traceback") else ""
    status = "PASS" if exit_code == 0 else "FAIL"
    # Summarize error (stderr tail first, else stdout tail); clip to one line
    err = rec.get("stderr_tail") or rec.get("stdout_tail") or ""
    err = err.strip().splitlines()[-1] if err.strip().splitlines() else ""
    # Escape pipes in Markdown
    err = err.replace("|","\\|")
    print(f"| `{cmd}` | {exit_code} | {status} | {dur:.2f} | {err} | {tb} |")
PY

  echo
  echo "### Notes"
  echo "- This audit is **read-only** and uses safe flags only."
  echo "- Any non-zero exit is marked **FAIL**; timeouts appear as exit 124."
  echo "- See ".firsttry/copilot_ft_audit_report.jsonl" for full JSON records (stdout/stderr tails)."
} > "$REPORT_MD"

echo "Wrote: $REPORT_MD"
echo "Raw JSONL: $REPORT_JSONL"
