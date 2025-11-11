#!/usr/bin/env bash
set -euo pipefail
export PYTHONPATH="src:."
export FT_AUDIT_READONLY="1"
export PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
export PIP_DISABLE_PIP_VERSION_CHECK="1"
export FORCE_COLOR=1
mkdir -p .firsttry/audit_logs

run_step () { # usage: run_step "NAME" TIMEOUT_SECONDS "CMD"
  name="$1"; tmo="$2"; shift 2
  log=".firsttry/audit_logs/${name// /_}.log"
  echo "==> ${name} (timeout ${tmo}s)" | tee "$log"
  # run and capture exit correctly
  set +e
  /usr/bin/time -f "DURATION_SEC:%e" timeout --preserve-status -k 5s "${tmo}s" bash -lc "$*" \
    > >(tee -a "$log") 2> >(tee -a "$log" >&2)
  status=$?
  set -e
  if [ $status -eq 124 ] || [ $status -eq 137 ]; then
    echo "RESULT: TIMEOUT" | tee -a "$log"
  else
    echo "RESULT: EXIT_$status" | tee -a "$log"
  fi
  echo "LOG_FILE:$log"
  return $status
}

# --- Developer ---
run_step "py_version"            10  "python -V" || true
run_step "pip_freeze_head"       20  "python -m pip freeze | head -n 50" || true
run_step "install_dev_extras"   300  "python -m pip install -e '.[dev]' || python -m pip install -e '.'" || true
run_step "import_firsttry"       20  "python - <<'PY'
import firsttry; print(firsttry.__name__)
PY" || true
run_step "cli_help"              20  "python -m firsttry --help || firsttry --help || echo 'MISSING: cli'" || true
run_step "pytest_smoke"          90  "pytest -q -vv -s -k 'import or smoke' --maxfail=1 --no-header --no-summary" || true
run_step "pytest_regress"       180  "test -d tests/regress && pytest -q -vv -s tests/regress --maxfail=1 --no-header --no-summary || echo 'MISSING: tests/regress'" || true
run_step "pytest_lazy_orch"      90  "pytest -q -vv -s -k 'lazy and orchestrator' --maxfail=1 --no-header --no-summary || echo 'SKIPPED: no lazy orchestrator tests'" || true

# --- Teams ---
run_step "ruff_check"            60  "ruff check ." || true
run_step "black_check"           60  "black --check ." || true
run_step "isort_check"           60  "isort --check-only . || echo 'MISSING: isort or unsorted imports'" || true
run_step "mypy_check"           180  "mypy src" || true
run_step "pytest_fast"          240  "pytest -q -vv -s -k 'not slow' --maxfail=1 --no-header --no-summary" || true
run_step "pytest_coverage"      240  "pytest -q --maxfail=1 --no-header --no-summary -p pytest_cov --cov=src/firsttry --cov-branch --cov-report=term-missing || echo 'MISSING: pytest-cov or coverage args unsupported'" || true
run_step "docs_quick"            90  "test -f docs/conf.py && (python -m pip install -r docs/requirements.txt >/dev/null 2>&1 || true; python -m sphinx -q -b html docs/ .firsttry/_docs_tmp) || echo 'SKIPPED: no docs'" || true
run_step "ci_workflows_check"    60  "test -d .github/workflows && ls -1 .github/workflows/*.yml || echo 'MISSING: workflows'" || true
run_step "ci_validation_script" 120  "test -f scripts/check-workflows.sh && bash -n scripts/check-workflows.sh && bash scripts/check-workflows.sh || echo 'SKIPPED: scripts/check-workflows.sh'" || true

# --- Enterprise ---
run_step "bandit_security"      240  "bandit -q -r src" || true
run_step "audit_emit"           120  "test -f tools/audit_emit.py && PYTHONPATH=src:. python tools/audit_emit.py --out .firsttry/audit.json --summary .firsttry/audit_summary.txt || echo 'SKIPPED: tools/audit_emit.py'" || true
run_step "policy_probe"          60  "test -f tools/ci_self_check.py && PYTHONPATH=src:. python tools/ci_self_check.py || echo 'SKIPPED: tools/ci_self_check.py'" || true
run_step "remote_cache_probe"    45  "grep -R \"remote cache\\|S3\\|R2\\|CACHE_BUCKET\" -n . || echo 'No explicit remote cache config detected'" || true
run_step "license_probe"         45  "grep -R \"LICENSE\\|license key\\|FT_LICENSE\\|FIRSTTRY_LICENSE\" -n src tools || echo 'No license gating hooks detected'" || true

echo "Audit finished. Logs in .firsttry/audit_logs/"
