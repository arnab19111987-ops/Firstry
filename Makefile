.PHONY: pro pro-warm pro-verify bandit-json
pro:
	@rm -rf .firsttry && ft pro --report-json .firsttry/pro.cold.json --show-report || true

pro-warm:
	@ft pro --report-json .firsttry/pro.warm.json --show-report || true

pro-verify:
	@python -c "import json,sys; p='.firsttry/pro.warm.json'; d=json.load(open(p)); b=[c for c in d.get('checks',[]) if c.get('name')=='bandit' or c.get('id')=='bandit']; assert b, 'Bandit missing in report'; b=b[0]; assert b.get('status') in ('pass','advisory','ok'), 'Unexpected status: %s'%b.get('status'); print('OK: bandit', b.get('status'))"

bandit-json:
	@jq . ".firsttry/bandit.json" 2>/dev/null || echo "bandit.json not present yet"
# Top-level Makefile helpers
.PHONY: node-validate
node-validate:
	@bash scripts/validate-node.sh

# Python helpers
.PHONY: py-validate licensing-test
py-validate:  ## run firsttry tests locally
	@. .venv/bin/activate && pip install -e tools/firsttry && pytest -q tools/firsttry/tests

licensing-test:  ## run licensing FastAPI tests
	@. .venv/bin/activate || true
	@PYTHONPATH=licensing pytest -q licensing

.PHONY: run-licensing
run-licensing:
	@export PYTHONPATH=licensing && \
	 FIRSTTRY_KEYS="ABC123:featX|featY" \
	 uvicorn app.main:app --host 127.0.0.1 --port 8081 --reload

.PHONY: ruff-fix
ruff-fix:  ## auto-fix ruff lint issues and format with black
	ruff check . --fix
	black .

.PHONY: check
check:
	@echo "[firsttry] running full quality gate..."
	ruff check .
	mypy .
	coverage run -m pytest -q
	coverage report --fail-under=80

.PHONY: coverage-check
coverage-check:  ## run tests with coverage and check floor
	pytest tests \
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


# Developer convenience targets
.PHONY: dev
dev:
	@bash scripts/bootstrap_dev.sh

.PHONY: ft-help
ft-help:
	@which ft || true
	@ft --help || python -m firsttry --help

.PHONY: test
test:
	PYTHONPATH=./src pytest tests

.PHONY: test-all
test-all:
	PYTHONPATH=./src pytest


.PHONY: perf
perf:
	bash scripts/perf_snapshot.sh


.PHONY: ci-bandit
ci-bandit:
	@set -euo pipefail; \
	python -m pip install -e . >/dev/null; \
	python -m pip install "bandit==1.7.9" >/dev/null; \
	ft pro --report-json .firsttry/pro.json --show-report || true; \
	python - <<'PY' || exit $$?
import json, sys
d=json.load(open('.firsttry/pro.json'))
b=[c for c in d.get('checks',[]) if c.get('id')=='bandit' or c.get('name')=='bandit']
assert b, 'bandit check missing'
b=b[0]; s=b.get('summary',{}); blocking=b.get('blocking',True); high=s.get('high',0) or s.get('HIGH',0) or 0
print('bandit blocking:', blocking, 'high:', high)
sys.exit(1 if (blocking and high>0) else 0)
PY

