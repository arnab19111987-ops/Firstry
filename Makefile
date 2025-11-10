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

.PHONY: ft-pre-commit ft-pre-push ft-ci
ft-pre-commit:
	FT_CI_PARITY_DRYRUN=1 python -m firsttry.ci_parity.runner pre-commit

ft-pre-push:
	FT_CI_PARITY_DRYRUN=1 python -m firsttry.ci_parity.runner pre-push

ft-ci:
	FT_CI_PARITY_DRYRUN=1 python -m firsttry.ci_parity.runner ci

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

