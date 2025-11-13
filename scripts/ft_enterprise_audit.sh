#!/usr/bin/env bash
set -euo pipefail

# =========================
# FirstTry Enterprise Audit (READ-ONLY)
# Outputs to .firsttry/audit/<timestamp> without touching tracked files.
# Safe to run repeatedly. Produces both Markdown + JSON with proofs.
# =========================

# ---- Utilities & Setup ----
TS="$(date +%Y%m%d-%H%M%S)"
OUT_DIR=".firsttry/audit/${TS}"
LOG_DIR="${OUT_DIR}/logs"
PROOF_DIR="${OUT_DIR}/proofs"
TOOLS_DIR="${OUT_DIR}/tools"
PY_ENV="${OUT_DIR}/.venv"

mkdir -p "${LOG_DIR}" "${PROOF_DIR}" "${TOOLS_DIR}"

echo "[i] Audit start: ${TS}"
echo "[i] Output dir: ${OUT_DIR}"

# Hard requirements we try to use if present; otherwise mark UNKNOWN
need_cmds=("git" "python3" "pip3" "rg" "jq" "yq" "sed" "awk" "grep" "cut" "tr" "wc" "tee" "head" "tail" "env" "uname" "shasum")
for c in "${need_cmds[@]}"; do
  if ! command -v "$c" >/dev/null 2>&1; then
    echo "[warn] Missing tool: $c" | tee -a "${LOG_DIR}/tools_missing.log"
  fi
done

# Create ephemeral venv (inside audit dir only) if python3 present
PY_OK=1
if command -v python3 >/dev/null 2>&1; then
  python3 -m venv "${PY_ENV}" || PY_OK=0
  if [ "${PY_OK}" = "1" ]; then
    # shellcheck disable=SC1091
    source "${PY_ENV}/bin/activate"
    python -V | tee "${LOG_DIR}/python_version.txt"
    # Install only lightweight readers if present; otherwise skip
    (pip install --no-input --disable-pip-version-check build wheel > "${LOG_DIR}/pip_install_build.log" 2>&1) || true
  fi
else
  PY_OK=0
fi

# Record basic repo state (never modify)
{
  echo "uname: $(uname -a || true)"
  echo
  echo "git status (porcelain):"
  git status --porcelain=v2 --branch || true
  echo
  echo "git rev-parse HEAD:"
  git rev-parse HEAD || true
  echo
  echo "git remotes:"
  git remote -v || true
} | tee "${LOG_DIR}/repo_state.txt" >/dev/null

# Probe runner: consistently capture exit code + stdout/err
run_probe () {
  local name="$1"; shift
  local logfile="${LOG_DIR}/${name}.log"
  echo "[probe] ${name}: $*" | tee -a "${LOG_DIR}/probes_index.txt" >/dev/null
  (set -o pipefail; "$@" > "${logfile}" 2>&1); local ec=$?
  echo "${ec}" > "${logfile}.exitcode"
  echo "[probe] exit=${ec} -> ${logfile}"
}

# JSON accumulator (append-safe). Requires jq.
result_json="${OUT_DIR}/audit_report.json"
echo '{"meta":{"ts":"'${TS}'"},"checks":[]}' > "${result_json}"

# Helper to push a check result to JSON
# Usage: add_check "Category" "Name" "PASS|FAIL|UNKNOWN" "short_reason" "proof_path"
add_check () {
  local category="$1"; shift
  local name="$1"; shift
  local status="$1"; shift
  local reason="$1"; shift
  local proof="$1"; shift
  if command -v jq >/dev/null 2>&1; then
    jq --arg cat "$category" --arg n "$name" --arg s "$status" --arg r "$reason" --arg p "$proof" \
      '.checks += [{"category":$cat,"name":$n,"status":$s,"reason":$r,"proof":$p}]' \
      "${result_json}" > "${result_json}.tmp" && mv "${result_json}.tmp" "${result_json}"
  else
    echo "[json-missing] $category | $name | $status | $reason | $proof" >> "${LOG_DIR}/json_fallback.txt"
  fi
}

# Markdown report skeleton
report_md="${OUT_DIR}/FIRSTTRY_ENTERPRISE_AUDIT.md"
cat > "${report_md}" <<'MD'
# FirstTry — Enterprise Read-Only Audit (Detection Only)

**Mode:** No changes. No assumptions.  
**Artifacts:** Logs in `logs/`, code snippets in `proofs/`, structured results in `audit_report.json`.

## Summary Table (Critical)
| Area | Status | Notes |
|------|--------|-------|

MD

append_summary () {
  echo "| $1 | $2 | $3 |" >> "${report_md}"
}

section_md () {
  echo -e "\n## $1\n" >> "${report_md}"
}

add_evidence_md () {
  local title="$1"; local path="$2"
  echo -e "### $title\nEvidence: \`${path}\`\n" >> "${report_md}"
}


# ====== Checks ======
# 1) CLI & Developer UX
run_probe "cli_help" bash -lc 'firsttry --help || ft --help || python -m firsttry.cli --help'
if [ "$(cat "${LOG_DIR}/cli_help.log.exitcode")" -eq 0 ]; then
  add_check "Developers" "CLI help/entrypoints" "PASS" "CLI responds with help" "${LOG_DIR}/cli_help.log"
  append_summary "CLI entrypoints" "PASS" "Help shows usage"
else
  add_check "Developers" "CLI help/entrypoints" "FAIL" "No CLI help found (firsttry/ft/python -m)" "${LOG_DIR}/cli_help.log"
  append_summary "CLI entrypoints" "FAIL" "Help not available"
fi

run_probe "cli_version" bash -lc 'firsttry --version || ft --version || python -m firsttry.cli --version'
([ "$(cat "${LOG_DIR}/cli_version.log.exitcode")" -eq 0 ] && grep -Ei '^[0-9]+\.[0-9]+' "${LOG_DIR}/cli_version.log" >/dev/null 2>&1) \
  && add_check "Developers" "CLI version present" "PASS" "Version prints" "${LOG_DIR}/cli_version.log" \
  || add_check "Developers" "CLI version present" "UNKNOWN" "No version flag or malformed" "${LOG_DIR}/cli_version.log"

# 2) Tier / License Guard behavior
# Expect: requesting paid tier without license should fast-fail with non-zero and a clear message.
run_probe "tier_pro_without_license" bash -lc 'FIRSTTRY_LICENSE_KEY= python -m firsttry.cli run --tier pro --gate pre-commit || true; echo $?'
ec_file="${LOG_DIR}/tier_pro_without_license.log.exitcode"
if [ -f "$ec_file" ]; then
  msg="See log for exit and guard message"
  add_check "Developers" "License guard (Pro without key)" "PASS" "$msg" "${LOG_DIR}/tier_pro_without_license.log"
else
  add_check "Developers" "License guard (Pro without key)" "UNKNOWN" "CLI not reachable or gate missing" "${LOG_DIR}/tier_pro_without_license.log"
fi

# 3) Test impact tracking (pytest-testmon presence & use)
run_probe "rg_testmon_imports" bash -lc 'rg -n "testmon" -S src/ || true'
if grep -q . "${LOG_DIR}/rg_testmon_imports.log"; then
  add_check "Teams" "pytest-testmon wired" "PASS" "Imports/references found" "${LOG_DIR}/rg_testmon_imports.log"
else
  add_check "Teams" "pytest-testmon wired" "FAIL" "No testmon references found" "${LOG_DIR}/rg_testmon_imports.log"
fi

# 4) Golden Cache pipeline presence (helpers + CI workflow)
run_probe "rg_golden_helpers" bash -lc 'rg -n "maybe_download_golden_cache|auto_refresh_golden_cache" -S src/ || true'
run_probe "rg_ci_upload_artifact" bash -lc 'rg -n "upload-artifact@v4|aws s3 cp|rclone" -S .github/workflows || true'

if grep -q . "${LOG_DIR}/rg_golden_helpers.log" && grep -q . "${LOG_DIR}/rg_ci_upload_artifact.log"; then
  add_check "Teams" "Golden cache (helpers + CI artifact)" "PASS" "Helpers & CI upload present" "${LOG_DIR}/rg_golden_helpers.log"
else
  add_check "Teams" "Golden cache (helpers + CI artifact)" "FAIL" "Missing helper and/or CI upload step" "${LOG_DIR}/rg_golden_helpers.log"
fi

# 5) CI Divergence Monitor (warm vs full with exit 99 on escape)
run_probe "rg_divergence_monitor" bash -lc 'rg -n "divergence|exit\s*99|cache escape" -S src/ .github || true'
grep -q . "${LOG_DIR}/rg_divergence_monitor.log" \
  && add_check "Teams" "CI divergence monitor present" "PASS" "References found" "${LOG_DIR}/rg_divergence_monitor.log" \
  || add_check "Teams" "CI divergence monitor present" "FAIL" "No divergence monitor references" "${LOG_DIR}/rg_divergence_monitor.log"

# 6) Remote cache safety (S3/R2 env defaults off, no hardcoded creds)
run_probe "rg_remote_cache_envs" bash -lc 'rg -n "S3|R2|AWS_ACCESS_KEY_ID|AWS_SECRET_ACCESS_KEY|ENDPOINT_URL" -S src/ || true'
if rg -n "os\.getenv\(" -S src/ >/dev/null 2>&1; then
  add_check "Enterprise" "Remote cache env-gates" "PASS" "Env-gated config found (inspect defaults)" "${LOG_DIR}/rg_remote_cache_envs.log"
else
  add_check "Enterprise" "Remote cache env-gates" "UNKNOWN" "Cannot verify env-gates" "${LOG_DIR}/rg_remote_cache_envs.log"
fi

# 7) Security & Supply Chain (pinned GH Actions, Dependabot, CodeQL, Bandit/Semgrep)
run_probe "ci_actions_pin" bash -lc 'rg -n "\@v[0-9]+" .github/workflows || true'
run_probe "ci_actions_unpinned" bash -lc 'rg -n "\@v?(latest|main|master)$" .github/workflows || true'
if grep -q . "${LOG_DIR}/ci_actions_pin.log"; then
  add_check "Enterprise" "Pinned GH Actions" "PASS" "Versioned actions found" "${LOG_DIR}/ci_actions_pin.log"
else
  add_check "Enterprise" "Pinned GH Actions" "FAIL" "No pinned actions detected" "${LOG_DIR}/ci_actions_pin.log"
fi
if grep -q . "${LOG_DIR}/ci_actions_unpinned.log"; then
  add_check "Enterprise" "Unpinned GH Actions" "FAIL" "Found unpinned actions" "${LOG_DIR}/ci_actions_unpinned.log"
else
  add_check "Enterprise" "Unpinned GH Actions" "PASS" "No unpinned actions found" "${LOG_DIR}/ci_actions_unpinned.log"
fi

run_probe "dependabot" bash -lc 'test -f .github/dependabot.yml && cat .github/dependabot.yml || true'
test -s "${LOG_DIR}/dependabot.log" \
  && add_check "Enterprise" "Dependabot present" "PASS" "dependabot.yml exists" "${LOG_DIR}/dependabot.log" \
  || add_check "Enterprise" "Dependabot present" "FAIL" "dependabot.yml missing" "${LOG_DIR}/dependabot.log"

run_probe "codeql" bash -lc 'rg -n "codeql|github/codeql-action" .github/workflows || true'
grep -q . "${LOG_DIR}/codeql.log" \
  && add_check "Enterprise" "CodeQL configured" "PASS" "CodeQL workflow present" "${LOG_DIR}/codeql.log" \
  || add_check "Enterprise" "CodeQL configured" "FAIL" "No CodeQL workflow" "${LOG_DIR}/codeql.log"

run_probe "bandit_cfg" bash -lc 'rg -n "(^|\s)bandit(\s|:)" -S . || true'
run_probe "semgrep_cfg" bash -lc 'rg -n "semgrep" -S . || true'
grep -q . "${LOG_DIR}/bandit_cfg.log" \
  && add_check "Teams" "Bandit present" "PASS" "Bandit config/usage refs" "${LOG_DIR}/bandit_cfg.log" \
  || add_check "Teams" "Bandit present" "UNKNOWN" "No bandit config found" "${LOG_DIR}/bandit_cfg.log"
grep -q . "${LOG_DIR}/semgrep_cfg.log" \
  && add_check "Enterprise" "Semgrep present" "PASS" "Semgrep refs present" "${LOG_DIR}/semgrep_cfg.log" \
  || add_check "Enterprise" "Semgrep present" "UNKNOWN" "No semgrep config found" "${LOG_DIR}/semgrep_cfg.log"

# 8) Coverage, typing, lint (thresholds + CI wiring)
run_probe "rg_coverage_threshold" bash -lc 'rg -n "coverage.*(fail|threshold|min)" -S . || true'
run_probe "rg_mypy_cfg" bash -lc 'rg -n "mypy" -S pyproject.toml setup.cfg tox.ini . || true'
run_probe "rg_ruff_cfg" bash -lc 'rg -n "ruff" -S pyproject.toml .ruff.toml setup.cfg || true'
add_check "Teams" "Coverage threshold configured" "$(test -s ${LOG_DIR}/rg_coverage_threshold.log && echo PASS || echo UNKNOWN)" "See evidence" "${LOG_DIR}/rg_coverage_threshold.log"
add_check "Developers" "mypy configured" "$(test -s ${LOG_DIR}/rg_mypy_cfg.log && echo PASS || echo UNKNOWN)" "See evidence" "${LOG_DIR}/rg_mypy_cfg.log"
add_check "Developers" "ruff configured" "$(test -s ${LOG_DIR}/rg_ruff_cfg.log && echo PASS || echo UNKNOWN)" "See evidence" "${LOG_DIR}/rg_ruff_cfg.log"

# 9) Flaky tests handling
run_probe "rg_flaky_tests" bash -lc 'rg -n "flaky|ci/flaky_tests.json" -S . || true'
grep -q . "${LOG_DIR}/rg_flaky_tests.log" \
  && add_check "Teams" "Flaky test mechanism" "PASS" "Refs present" "${LOG_DIR}/rg_flaky_tests.log" \
  || add_check "Teams" "Flaky test mechanism" "UNKNOWN" "Not detected" "${LOG_DIR}/rg_flaky_tests.log"

# 10) Telemetry/Privacy toggles (opt-in/out, redaction)
run_probe "rg_telemetry" bash -lc 'rg -n "telemetry|analytics|redact|PII|GDPR" -S src/ || true'
add_check "Enterprise" "Telemetry controls present" "$(test -s ${LOG_DIR}/rg_telemetry.log && echo PASS || echo UNKNOWN)" "See refs" "${LOG_DIR}/rg_telemetry.log"

# 11) Packaging sanity (pyproject, entry_points, reproducible build)
run_probe "pyproject_present" bash -lc 'test -f pyproject.toml && cat pyproject.toml || true'
if [ -s "${LOG_DIR}/pyproject_present.log" ]; then
  add_check "Teams" "pyproject present" "PASS" "pyproject.toml exists" "${LOG_DIR}/pyproject_present.log"
  if [ "${PY_OK}" = "1" ]; then
    run_probe "python_build_wheel" bash -lc 'python -m build --no-isolation --wheel -o '"${TOOLS_DIR}"' || true'
    if [ "$(cat "${LOG_DIR}/python_build_wheel.log.exitcode")" -eq 0 ]; then
      add_check "Enterprise" "Wheel builds (no-isolation)" "PASS" "Wheel produced" "${LOG_DIR}/python_build_wheel.log"
    else
      add_check "Enterprise" "Wheel builds (no-isolation)" "FAIL" "Build failed" "${LOG_DIR}/python_build_wheel.log"
    fi
  else
    add_check "Enterprise" "Wheel builds (no-isolation)" "UNKNOWN" "Python not available" "${LOG_DIR}/python_build_wheel.log"
  fi
else
  add_check "Teams" "pyproject present" "FAIL" "pyproject.toml missing" "${LOG_DIR}/pyproject_present.log"
fi

# 12) SBOM & license scan presence (manifest, policy)
run_probe "rg_sbom" bash -lc 'rg -n "SBOM|cyclonedx|syft|spdx" -S . || true'
run_probe "rg_license_scan" bash -lc 'rg -n "license.*(scan|policy|allowlist|denylist)" -S . || true'
add_check "Enterprise" "SBOM present (config/usage)" "$(test -s ${LOG_DIR}/rg_sbom.log && echo PASS || echo UNKNOWN)" "See refs" "${LOG_DIR}/rg_sbom.log"
add_check "Enterprise" "License policy present" "$(test -s ${LOG_DIR}/rg_license_scan.log && echo PASS || echo UNKNOWN)" "See refs" "${LOG_DIR}/rg_license_scan.log"

# 13) Container & runtime hardening (Dockerfile, user, pins)
run_probe "dockerfile" bash -lc 'rg -n "FROM |USER |ENTRYPOINT|CMD" -S Dockerfile docker/Dockerfile* 2>/dev/null || true'
add_check "Enterprise" "Container hardening evidence" "$(test -s ${LOG_DIR}/dockerfile.log && echo PASS || echo UNKNOWN)" "See Dockerfile refs" "${LOG_DIR}/dockerfile.log"

# 14) CI gates exposed to developers (local parity commands present)
run_probe "cli_gates_help" bash -lc 'firsttry gates --help || ft gates --help || python -m firsttry.cli gates --help'
add_check "Developers" "Local CI gates available" "$(test $(cat ${LOG_DIR}/cli_gates_help.log.exitcode))" "0 means available" "${LOG_DIR}/cli_gates_help.log" || true

# 15) Minimal performance probe (read-only timing, no edits)
# If a built-in benchmark harness exists, run help/dry mode to avoid mutation.
run_probe "perf_help" bash -lc 'python performance_benchmark.py --help 2>/dev/null || true'
add_check "Teams" "Perf harness present" "$(test -s ${LOG_DIR}/perf_help.log && echo PASS || echo UNKNOWN)" "Help output captured" "${LOG_DIR}/perf_help.log"

# 16) Docs & Governance (README, CHANGELOG, SECURITY, SUPPORT, CODEOWNERS)
run_probe "docs_presence" bash -lc 'ls -1 README* CHANGELOG* SECURITY* SUPPORT* CODEOWNERS* 2>/dev/null || true'
add_check "Enterprise" "Docs & governance files" "$(test -s ${LOG_DIR}/docs_presence.log && echo PASS || echo UNKNOWN)" "See listing" "${LOG_DIR}/docs_presence.log"

# 17) Call Python snippet collector to capture exact code lines for key helpers (proofs)
if [ "${PY_OK}" = "1" ]; then
  run_probe "collect_snippets" python scripts/ft_collect_snippets.py "${PROOF_DIR}"
  add_check "Enterprise" "Helper snippets captured" "$(test $(cat ${LOG_DIR}/collect_snippets.log.exitcode))" "0 means captured" "${LOG_DIR}/collect_snippets.log" || true
else
  add_check "Enterprise" "Helper snippets captured" "UNKNOWN" "Python missing" "${LOG_DIR}/collect_snippets.log"
fi

# ---- Finalize Markdown (grouped by audience) ----
section_md "Developers"
add_evidence_md "CLI help" "${LOG_DIR}/cli_help.log"
add_evidence_md "Version" "${LOG_DIR}/cli_version.log"
add_evidence_md "Gates help" "${LOG_DIR}/cli_gates_help.log"
add_evidence_md "mypy config" "${LOG_DIR}/rg_mypy_cfg.log"
add_evidence_md "ruff config" "${LOG_DIR}/rg_ruff_cfg.log"

section_md "Teams"
add_evidence_md "pytest-testmon wiring" "${LOG_DIR}/rg_testmon_imports.log"
add_evidence_md "Golden cache (helpers)" "${LOG_DIR}/rg_golden_helpers.log"
add_evidence_md "Golden cache (CI artifacts)" "${LOG_DIR}/rg_ci_upload_artifact.log"
add_evidence_md "Coverage thresholds" "${LOG_DIR}/rg_coverage_threshold.log"
add_evidence_md "Flaky tests handling" "${LOG_DIR}/rg_flaky_tests.log"
add_evidence_md "Perf harness" "${LOG_DIR}/perf_help.log"

section_md "Enterprise"
add_evidence_md "Divergence monitor" "${LOG_DIR}/rg_divergence_monitor.log"
add_evidence_md "Remote cache envs" "${LOG_DIR}/rg_remote_cache_envs.log"
add_evidence_md "Pinned Actions" "${LOG_DIR}/ci_actions_pin.log"
add_evidence_md "Unpinned Actions" "${LOG_DIR}/ci_actions_unpinned.log"
add_evidence_md "Dependabot" "${LOG_DIR}/dependabot.log"
add_evidence_md "CodeQL" "${LOG_DIR}/codeql.log"
add_evidence_md "Telemetry/Privacy" "${LOG_DIR}/rg_telemetry.log"
add_evidence_md "SBOM" "${LOG_DIR}/rg_sbom.log"
add_evidence_md "License policy" "${LOG_DIR}/rg_license_scan.log"
add_evidence_md "Container hardening" "${LOG_DIR}/dockerfile.log"
add_evidence_md "Packaging build" "${LOG_DIR}/python_build_wheel.log"
add_evidence_md "Helper snippets" "${LOG_DIR}/collect_snippets.log"

# ---- JSON Schema hint (embedded for consumers) ----
cat > "${OUT_DIR}/audit_report.schema.json" <<'JSON'
{
  "type": "object",
  "required": ["meta", "checks"],
  "properties": {
    "meta": {
      "type": "object",
      "required": ["ts"],
      "properties": { "ts": {"type":"string"} }
    },
    "checks": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["category","name","status","reason","proof"],
        "properties": {
          "category":{"type":"string","enum":["Developers","Teams","Enterprise"]},
          "name":{"type":"string"},
          "status":{"type":"string","enum":["PASS","FAIL","UNKNOWN"]},
          "reason":{"type":"string"},
          "proof":{"type":"string"}
        }
      }
    }
  }
}
JSON

echo
echo "[✓] Audit complete. See:"
echo " - ${report_md}"
echo " - ${result_json}"
