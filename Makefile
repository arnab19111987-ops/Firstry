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
	ruff check src tests --fix
	black src tests


.PHONY: check
check:
	@echo "[firsttry] running full quality gate..."
	ruff check src tests
	mypy src tests
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
