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

.PHONY: inspection
inspection:
	@./tools/ft_inspection.sh || (echo "Inspection failed"; exit 2)

.PHONY: report
report:
	@echo "Generating HTML report & dashboard (requires a recent run)"
	@python - <<'PY'
	from pathlib import Path
	from src.firsttry.reporting.html import write_html_report, write_html_dashboard
	repo = Path('.').resolve()
	try:
		import json
		data = json.loads((repo/'.firsttry/report.json').read_text())
		class R: pass
		results = {}
		for k,v in (data.get('checks',{}) or {}).items():
			r = R(); r.status=v.get('status',''); r.duration_ms=int(v.get('duration_ms',0))
			results[k]=r
		write_html_report(repo, results)
	except Exception:
		pass
	write_html_dashboard(repo)
	print('HTML written under .firsttry/')
	PY

# Fast demo helpers: cold -> warm -> proof
.PHONY: ft-cold ft-warm ft-proof
ft-cold:
	@PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=src python -m firsttry.cli run --tier free-fast --show-report || true
ft-warm:
	@PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=src python -m firsttry.cli run --tier free-fast --show-report
ft-proof: ft-cold ft-warm
	@python - <<'PY'
import json, pathlib
p=pathlib.Path('.firsttry/report.json'); d=json.loads(p.read_text())
print("== checks ==")
for k,v in d["checks"].items(): print(k, v["status"], v.get("cache_status"))
h=pathlib.Path('.firsttry/history.jsonl')
if h.exists():
  lines=h.read_text().splitlines()[-5:]
  for ln in lines:
    rec=json.loads(ln); hits=sum(1 for c in rec["checks"].values() if c.get("cache_status") in ("hit-local","hit-remote"))
    print(rec['ts'], rec.get('tier'), f"{hits}/{len(rec['checks'])} hits")
PY

.PHONY: ft-perf
ft-perf:
	@PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=src python -m firsttry.cli run --tier free-fast --show-report || true
	@PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=src python -m firsttry.cli run --tier free-fast --show-report
	@python - <<'PY'
import json, pathlib
p=pathlib.Path('.firsttry/report.json'); d=json.loads(p.read_text())
hits=sum(1 for r in d["checks"].values() if r.get("cache_status") in ("hit-local","hit-remote"))
total=len(d["checks"])
slow=sorted(((k, r.get("duration_ms",0)) for k,r in d["checks"].items()), key=lambda x: x[1], reverse=True)
print(f"cache hits: {hits}/{total}")
print("slowest:", ", ".join(f"{k}:{ms}ms" for k,ms in slow))
PY
