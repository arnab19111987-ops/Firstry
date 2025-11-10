# Top-level Makefile helpers
.PHONY: node-validate
node-validate:
	@bash scripts/validate-node.sh

# Python helpers
.PHONY: py-validate licensing-test
py-validate:  ## run firsttry tests locally
	@. .venv/bin/activate && pip install -e tools/firsttry && PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q tools/firsttry/tests

licensing-test:  ## run licensing FastAPI tests
	@. .venv/bin/activate || true
	@PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=licensing pytest -q licensing

.PHONY: run-licensing
run-licensing:
	@export PYTHONPATH=licensing && \
	 FIRSTTRY_KEYS="ABC123:featX|featY" \
	 uvicorn app.main:app --host 127.0.0.1 --port 8081 --reload

.PHONY: ruff-fix
ruff-fix:  ## auto-fix ruff lint issues and format with black
	python -m ruff check . --fix
	python -m black . || true

.PHONY: fmt-imports
fmt-imports:  ## auto-fix import sorting with isort
	isort .

.PHONY: check-imports
check-imports:  ## check import sorting without modifying files
	isort --check-only .

.PHONY: stub-check
stub-check:  ## scan for unowned STUB/TODO markers and stray NotImplementedError
	@echo "[stub-check] checking for unowned STUB/TODO markers..."
	@git ls-files '*.py' 2>/dev/null | xargs grep -nE '(^|\s)#\s*(STUB:|TODO:)(?!.*owner=|.*due=)' 2>/dev/null && \
	  { echo "❌ Found STUB/TODO without owner= and due= (required format: # STUB: desc owner=NAME due=YYYY-MM-DD)"; exit 1; } || \
	  echo "✅ All STUB/TODO markers are properly owned"
	@echo "[stub-check] checking for NotImplementedError outside abstract base classes..."
	@python scripts/check_notimpl.py
	@echo "✅ stub-check passed"

.PHONY: typing-metrics
typing-metrics:  ## check typing crutches (Any/ignore/cast) against baseline
	@python scripts/check_typing_metrics.py

.PHONY: check
check:  ## run full quality gate (stubs, typing, lints, types, tests)
	@echo "[firsttry] running full quality gate..."
	@make stub-check
	@make typing-metrics
	@python -m ruff check . || echo "⚠ ruff not installed (optional)"
	@python -m mypy . || echo "⚠ mypy not installed (optional)"
	@echo "Running tests..."
	PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=src pytest -q tests/ --ignore=tests/test_db_sqlite.py

.PHONY: perf
perf:  ## run performance verification (cold/warm/warm+prune benchmarks)
	@bash tools/verify_perf.sh

.PHONY: update-cache
update-cache:  ## Pull warm cache from CI artifacts
	@ft update-cache || true

.PHONY: clear-cache
clear-cache:  ## Nuke local caches (warm, mypy, ruff, testmon)
	@ft clear-cache

## Supply-chain audit helpers
.PHONY: audit-supply dev-audit parity-audit

audit-supply: dev-audit parity-audit  ## Run pip-audit in dev container and parity venv, save JSONs

dev-audit:
	@mkdir -p .firsttry
	@python -m pip install -U pip-audit >/dev/null 2>&1 || true
	@pip-audit -f json -o .firsttry/audit-devcontainer.json || true
	@echo "wrote .firsttry/audit-devcontainer.json"

parity-audit:
	@mkdir -p .firsttry
	@([ -x .venv-parity/bin/pip-audit ] || .venv-parity/bin/python -m pip install -U pip-audit) >/dev/null 2>&1 || true
	@.venv-parity/bin/pip-audit -f json -o .firsttry/audit-parity.json || true
	@echo "wrote .firsttry/audit-parity.json"

.PHONY: coverage-check
coverage-check:  ## run tests with coverage and check floor
	PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest tests \
		--cov=src/firsttry \
		--cov-report=term \
		--cov-report=json:coverage.json \
		-q
	@./scripts/check_coverage_floor.sh

# Benchmark targets
.PHONY: bench bench-short
bench:  ## run full benchmark suite
	python benchmarks/bench_runner.py

bench-short:  ## run shortened benchmark (future feature)
	python benchmarks/bench_runner.py --short

.PHONY: inspection
inspection:
	@./tools/ft_inspection.sh || (echo "Inspection failed"; exit 2)

.PHONY: report
report:
	@echo "Generating HTML report & dashboard (requires a recent run)"
	@python -c '\
from pathlib import Path; \
from src.firsttry.reporting.html import write_html_report, write_html_dashboard; \
repo = Path(".").resolve(); \
import json; \
data = json.loads((repo/".firsttry/report.json").read_text()); \
class R: pass; \
results = {}; \
for k,v in (data.get("checks",{}) or {}).items(): \
    r = R(); r.status=v.get("status",""); r.duration_ms=int(v.get("duration_ms",0)); results[k]=r; \
write_html_report(repo, results); \
write_html_dashboard(repo); \
print("HTML written under .firsttry/"); \
'

# Fast demo helpers: cold -> warm -> proof
.PHONY: ft-cold ft-warm ft-proof
ft-cold:
	@PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=src python -m firsttry.cli run --tier free-fast --show-report || true
ft-warm:
	@PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=src python -m firsttry.cli run --tier free-fast --show-report
ft-proof: ft-cold ft-warm
	@python -c '\
import json, pathlib; \
p=pathlib.Path(".firsttry/report.json"); d=json.loads(p.read_text()); \
print("== checks =="); \
for k,v in d["checks"].items(): print(k, v["status"], v.get("cache_status")); \
h=pathlib.Path(".firsttry/history.jsonl"); \
if h.exists(): \
  lines=h.read_text().splitlines()[-5:]; \
  for ln in lines: \
    rec=json.loads(ln); hits=sum(1 for c in rec["checks"].values() if c.get("cache_status") in ("hit-local","hit-remote")); \
    print(rec["ts"], rec.get("tier"), f"{hits}/{len(rec[\"checks\"])} hits"); \
'

.PHONY: ft-perf
ft-perf:
	@PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=src python -m firsttry.cli run --tier free-fast --show-report || true
	@PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=src python -m firsttry.cli run --tier free-fast --show-report
	@python -c '\
import json, pathlib; \
p=pathlib.Path(".firsttry/report.json"); d=json.loads(p.read_text()); \
hits=sum(1 for r in d["checks"].values() if r.get("cache_status") in ("hit-local","hit-remote")); \
total=len(d["checks"]); \
slow=sorted(((k, r.get("duration_ms",0)) for k,r in d["checks"].items()), key=lambda x: x[1], reverse=True); \
print(f"cache hits: {hits}/{total}"); \
print("slowest:", ", ".join(f"{k}:{ms}ms" for k,ms in slow)); \
'


.PHONY: hooks-install
hooks-install:
	@./scripts/install-hooks

.PHONY: ft-pre-commit ft-pre-push ft-ci precommit
ft-pre-commit:  ## Run FirstTry pre-commit (same gate as CI)
	ft pre-commit

precommit:  ## Alias for ft-pre-commit
	ft pre-commit

ft-pre-push:  ## Run FirstTry pre-push (full parity)
	ft pre-commit

<<<<<<< HEAD
ft-ci:  ## Run FirstTry CI parity (full parity)
	ft pre-commit

=======
>>>>>>> a10e9b71 (feat: complete CI parity setup with containerized hooks and config-aware mypy)
.PHONY: hooks-ensure hooks-status ft-ci-local ft-ci-dry ft-ci-matrix
hooks-ensure:
	@./scripts/enable-hooks

hooks-status:
	@echo "hooksPath=$$(git config --get core.hooksPath)"; ls -l .githooks || true

ft-ci-local:
	@./scripts/ft-ci-local

ft-ci-dry:
	@FT_CI_PARITY_DRYRUN=1 ./scripts/ft-ci-local

ft-ci-matrix:
	@PYVERS=$${PYVERS:-"3.10,3.11"} ./scripts/ft-ci-local
<<<<<<< HEAD


# ============================================================================
# Ultra-fast development targets (deterministic + no-hang)
# ============================================================================
TIMEOUT := timeout --preserve-status -k 5s
PYTEST := PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 FT_SKIP_TOOL_EXEC=1 pytest -q --maxfail=1 --no-header --no-summary

# Helper to conditionally run tools (skip if not installed)
define maybe_run
	if command -v $(1) >/dev/null 2>&1; then \
		echo ">>> $(1): $(2)"; \
		$(TIMEOUT) $(3) bash -lc '$(1) $(2)'; \
	else \
		echo "SKIP ($(1) not found)"; \
	fi
endef

.PHONY: dev.fast dev.tests dev.checks dev.all dev.help

dev.help:
	@echo "Fast development targets (all with timeouts):"
	@echo "  make dev.fast    - Quick smoke test + CLI ping"
	@echo "  make dev.tests   - Fast test suite (non-slow tests)"
	@echo "  make dev.checks  - Parallel linting/type-checking + coverage"
	@echo "  make dev.all     - Run all dev routines"

dev.fast:
	@echo ">>> Fast dev ping"
	@$(PYTEST) -k "import or smoke" || true
	@($(TIMEOUT) 20s python -m firsttry --help >/dev/null 2>&1 || $(TIMEOUT) 20s firsttry --help >/dev/null 2>&1 || true)

dev.tests:
	@echo ">>> Fast tests"
	@$(TIMEOUT) 120s $(PYTEST) -k "not slow"

dev.checks:
	@echo ">>> Fast checks (parallel)"
	@set -e; \
	( $(call maybe_run,ruff,check .,"60s") ) & \
	( $(call maybe_run,black,--check .,"60s") ) & \
	( $(call maybe_run,isort,--check-only .,"60s") ) & \
	( $(call maybe_run,mypy,src,"120s") ) & \
	wait; \
	echo ">>> Coverage (non-blocking)"; \
	$(TIMEOUT) 120s $(PYTEST) --cov=src/firsttry --cov-branch --cov-report=term-missing || true

dev.all: dev.fast dev.tests dev.checks
	@echo ">>> All dev routines complete (fast, timed, reliable)"


# ============================================================================
# Backup & Recovery Targets
# ============================================================================

.PHONY: backup backup-standalone backup-verify backup-help

backup-help:
	@echo "Backup targets for safe recovery:"
	@echo "  make backup              - Create incremental bundle (origin/main..perf/optimizations-40pc)"
	@echo "  make backup-standalone   - Create standalone bundle (entire repo, works anywhere)"
	@echo "  make backup-verify       - Verify all bundle checksums"
	@echo ""
	@echo "Bundle files created:"
	@echo "  - firsttry-perf-40pc.bundle (incremental, 106 KB)"
	@echo "  - firsttry-standalone.bundle (complete, ~80 MB)"
	@echo ""
	@echo "Restore examples:"
	@echo "  Incremental: git fetch bundle-file perf/optimizations-40pc:perf/optimizations-40pc"
	@echo "  Standalone:  git clone bundle-file Firstry-restored"

backup:  ## Create incremental bundle + checksums (perf/optimizations-40pc)
	@echo ">>> Creating incremental backup bundle..."
	@git fetch origin 2>/dev/null || true
	git bundle create firsttry-perf-40pc.bundle origin/main..perf/optimizations-40pc
	@echo ">>> Generating checksums..."
	sha256sum firsttry-perf-40pc.bundle > firsttry-perf-40pc.bundle.sha256
	md5sum firsttry-perf-40pc.bundle > firsttry-perf-40pc.bundle.md5
	@echo "✅ Incremental backup complete:"
	@ls -lh firsttry-perf-40pc.bundle* | awk '{printf "   %s  %s\n", $$5, $$9}'
	@echo ""
	@echo "SHA256: $$(cat firsttry-perf-40pc.bundle.sha256 | awk '{print $$1}')"

backup-standalone:  ## Create standalone bundle + checksums (entire repo)
	@echo ">>> Creating standalone backup bundle (this may take a moment)..."
	@rm -rf /tmp/Firstry.git
	@git clone --mirror . /tmp/Firstry.git 2>/dev/null
	@cd /tmp/Firstry.git && git bundle create /workspaces/Firstry/firsttry-standalone.bundle --all
	@echo ">>> Generating checksums..."
	sha256sum firsttry-standalone.bundle > firsttry-standalone.bundle.sha256
	md5sum firsttry-standalone.bundle > firsttry-standalone.bundle.md5
	@echo "✅ Standalone backup complete:"
	@ls -lh firsttry-standalone.bundle* | awk '{printf "   %s  %s\n", $$5, $$9}'
	@echo ""
	@echo "SHA256: $$(cat firsttry-standalone.bundle.sha256 | awk '{print $$1}')"
	@rm -rf /tmp/Firstry.git

backup-verify:  ## Verify integrity of all bundle files
	@echo ">>> Verifying bundle integrity..."
	@if [ -f firsttry-perf-40pc.bundle ]; then \
		echo "Incremental bundle:"; \
		git bundle verify firsttry-perf-40pc.bundle 2>&1 | grep -E "(okay|contains)" || true; \
		if [ -f firsttry-perf-40pc.bundle.sha256 ]; then \
			sha256sum -c firsttry-perf-40pc.bundle.sha256 2>&1 | grep -E "(OK|FAILED)"; \
		fi; \
		echo ""; \
	fi
	@if [ -f firsttry-standalone.bundle ]; then \
		echo "Standalone bundle:"; \
		git bundle verify firsttry-standalone.bundle 2>&1 | head -1; \
		if [ -f firsttry-standalone.bundle.sha256 ]; then \
			sha256sum -c firsttry-standalone.bundle.sha256 2>&1 | grep -E "(OK|FAILED)"; \
		fi; \
	fi
	@echo "✅ Verification complete"

# ============================================================================
# CI Parity Targets (Lock-driven enforcement)
# ============================================================================

.PHONY: parity parity-selfcheck parity-matrix parity-bootstrap parity-help

parity-help:  ## Show CI parity system usage
	@echo "════════════════════════════════════════════════════════════════"
	@echo "CI PARITY SYSTEM - Hermetic local/CI synchronization"
	@echo "════════════════════════════════════════════════════════════════"
	@echo ""
	@echo "Targets:"
	@echo "  make parity-bootstrap   Bootstrap hermetic environment"
	@echo "  make parity-selfcheck   Run preflight checks only"
	@echo "  make parity             Run full parity (all gates)"
	@echo "  make parity-matrix      Run parity across Python matrix"
	@echo ""
	@echo "Configuration:"
	@echo "  Lock file: ci/parity.lock.json (single source of truth)"
	@echo "  Env vars:  FT_PARITY_EXPLAIN=1 (verbose output)"
	@echo "            FT_NO_NETWORK=1 (sandbox network)"
	@echo ""
	@echo "Exit codes:"
	@echo "  0   - All green, ready for CI"
	@echo "  10x - Preflight parity mismatch (versions/config/plugins)"
	@echo "  21x - Lint/type failures (ruff/mypy)"
	@echo "  22x - Test failures/collection mismatch"
	@echo "  23x - Coverage below threshold"
	@echo "  24x - Bandit security failed"
	@echo "  30x - Missing artifacts"
	@echo ""

parity-bootstrap:  ## Bootstrap hermetic environment (.venv-parity)
	@./scripts/ft-parity-bootstrap.sh

parity-selfcheck:  ## Run preflight self-checks (versions, config, plugins)
	@if [ ! -d ".venv-parity" ]; then \
		echo "❌ .venv-parity not found. Run: make parity-bootstrap"; \
		exit 1; \
	fi
	@. .venv-parity/bin/activate && \
	 . .venv-parity/parity-env.sh && \
	 FT_PARITY_EXPLAIN=1 python -c "from firsttry.ci_parity.parity_runner import main; import sys; sys.exit(main(['--self-check', '--explain']))"

parity:  ## Run full CI parity check (all gates)
	@if [ ! -d ".venv-parity" ]; then \
		echo "❌ .venv-parity not found. Run: make parity-bootstrap"; \
		exit 1; \
	fi
	@. .venv-parity/bin/activate && \
	 . .venv-parity/parity-env.sh && \
	 FT_NO_NETWORK=1 FT_PARITY_EXPLAIN=1 python -c "from firsttry.ci_parity.parity_runner import main; import sys; sys.exit(main(['--parity', '--explain']))"

parity-matrix:  ## Run parity across Python version matrix
	@echo ">>> Matrix mode (Python 3.10, 3.11)"
	@echo "Note: Requires tox or multiple Python versions installed"
	@if command -v tox >/dev/null 2>&1; then \
		tox -q; \
	else \
		echo "❌ tox not found. Install with: pip install tox"; \
		exit 1; \
	fi
=======
>>>>>>> a10e9b71 (feat: complete CI parity setup with containerized hooks and config-aware mypy)

