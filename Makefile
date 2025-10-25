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
