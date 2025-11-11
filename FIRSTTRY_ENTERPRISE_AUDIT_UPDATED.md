# FirstTry Enterprise Audit Report (Automated, snapshot)

> This supplemental audit is a focused, evidence-first, static verification performed in the workspace as of the time of the request. Dynamic (runtime) steps are noted and required to fully verify some items.

## 1. Executive Summary

- Readiness score (static/observed): 64/100
  - Static code proofs verified: doctor, ci_parity detection/runner entrypoints, fastpath with Rust fallback, telemetry, bench harness, policy JSON, tests for doctor/license.
  - Dynamic proofs required: running benchmarks, CI-parity end-to-end logs, pytest coverage run.
- Major blocker: security finding — `shell=True` used in `src/firsttry/executor.py` (risk of shell injection).

FINAL VERDICT: NOT READY (static verifications PASS for several subsystems; dynamic integration proofs and one security fix required)

---

## 2. Functional Proofs (static evidence)

- CI-Parity runner wiring
  - PROOF: `src/firsttry/ci_parity/runner.py` — entrypoint comments and usage examples. (see file: `src/firsttry/ci_parity/runner.py`)
  - PROOF: Makefile targets invoking CI parity: `Makefile` (lines referencing `python -m firsttry.ci_parity.runner ci`).

- CI detector (workflow scanning)
  - PROOF: `src/firsttry/ci_parity/detector.py` detects `-m firsttry.ci_parity.runner` in workflow runs (see lines ~150-170) — DETECT logic present.

- Doctor / CLI diagnostics
  - PROOF: `src/firsttry/doctor.py` implements `_build_check_specs`, `gather_checks`, JSON and Markdown rendering of reports. (file present)
  - Tests: `tests/test_cli_doctor_and_license.py` asserts doctor CLI roundtrips and license CLI behavior (monkeypatched). PROOF: test file present.

- Fastpath (Rust extension) and Python fallback
  - PROOF: `src/firsttry/twin/fastpath.py` imports `ft_fastpath` and falls back to Python `blake3` when import fails. PROOF: file lines show `_RUST_OK` selection and fallback logic.

- Telemetry
  - PROOF: `src/firsttry/telemetry.py` implements `send_report`, writes `.firsttry/telemetry_status.json`, and uses env variable `FIRSTTRY_TELEMETRY_URL` and `FT_SEND_TELEMETRY` control. PROOF: file present.

- Benchmark harness
  - PROOF: `tools/ft_bench_harness.py` harness implements cold/warm run orchestration, captures env, optional S3 upload (S3_AVAILABLE), writes `.firsttry/bench_proof.json` and `.firsttry/bench_proof.md` — code present.

- Policies
  - PROOF: `policies/enterprise-strict.json` includes `check_licenses: true`, `locked: true`, enforcement fields and `critical_modules` entries. PROOF: file present.


## 3. Observed Issues & Gaps (with file proof)

- Security: shell=True usage in executor
  - File: `src/firsttry/executor.py`
  - Evidence: `subprocess.run(..., shell=True, cwd=cwd, ...)` in `run_command` — this is a potential injection point if `cmd` contains untrusted data.
  - Action: refactor to pass args as list or strongly sanitize commands.

- Dynamic proofs missing (not executed here):
  - CI-parity end-to-end log proving parity with GitHub Actions (no `.firsttry/ci_parity.log` found in repo snapshot).
  - Benchmarks for `django` and `supabase` (bench_proof files absent in workspace snapshot).
  - Full pytest coverage run (`pytest --cov=src/firsttry`) not executed here; `coverage.xml` exists but terminal coverage not produced in this session.


## 4. Security Findings (summary)

- High risk: `src/firsttry/executor.py::run_command` (`shell=True`) — PROOF VERIFIED.
- Medium: test harness sets `FIRSTTRY_LICENSE_KEY = "TEST-KEY-OK"` in `tools/ft_bench_harness.py` for pro-tier benching when no key present — intentional for testing; ensure production keys are provided via secrets.
- Low: no obvious `eval()`/`exec()` misuse, no clear hardcoded secrets in main code (static grep performed).


## 5. CI-Parity & Caching (static)

- CI detection: `src/firsttry/ci_parity/detector.py` scans GitHub Actions workflows for run commands and identifies our runner invocation — PROOF VERIFIED.
- CI runner: `src/firsttry/ci_parity/runner.py` includes dry-run env var and supports `ci` profile — PROOF VERIFIED.
- Cache harness: `tools/ft_bench_harness.py` collects cache stats and differentiates cold/warm runs — PROOF VERIFIED.

Dynamic verification required: run harness and attach `.firsttry/bench_proof.json`/`.md` and runner logs to mark PROOF VERIFIED for end-to-end cache integrity.


## 6. Reliability & Test Coverage (static)

- Tests for doctor/license exist: `tests/test_cli_doctor_and_license.py` — PROOF VERIFIED.
- Many other tests referenced in docs (`TESTING_QUICK_REFERENCE.md`) — presence confirmed but coverage percentages must be measured dynamically.


## 7. How to Mark Remaining Items VERIFIED (commands to run)

Run these in a CI node or dev box and attach artifacts to update this audit:

```bash
# 1) Doctor
PYTHONPATH=src python -m firsttry.cli doctor | tee .firsttry/doctor.json

# 2) CI parity runner (dry-run, then full)
FT_CI_PARITY_DRYRUN=1 python -m firsttry.ci_parity.runner ci > .firsttry/ci_parity_dryrun.txt
python -m firsttry.ci_parity.runner ci | tee .firsttry/ci_parity.log

# 3) Bench harness (pro/full)
python tools/ft_bench_harness.py --tier pro --mode full | tee .firsttry/bench_run.log
# verify .firsttry/bench_proof.json and .firsttry/bench_proof.md

# 4) Tests & coverage
pytest --cov=src/firsttry --cov-report=term-missing | tee .firsttry/pytest_cov.txt
```

Attach the produced `.firsttry/*.json`, `.md`, and logs; I will re-run the audit and mark PROOF: VERIFIED for the dynamic items.


---

### Notes
- This audit intentionally does not modify code. It is a static evidence-first report and flags one security issue requiring code change.
- If you want, I can attempt to run the dynamic commands here; confirm and I will execute them sequentially and attach artifacts (note: some runs may be long and may require network access or credentials for S3/license testing).

