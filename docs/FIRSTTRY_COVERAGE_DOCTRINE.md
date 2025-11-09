# FirstTry Coverage Doctrine
# FirstTry Coverage Doctrine

## Purpose
Coverage is evidence that FirstTry executes the same decision paths locally as CI (CI-parity). We don’t chase 100% globally; we enforce high coverage on code that decides *what runs* and *what’s reported*.

## Tiers & Targets
| Tier | Modules | Target (line-rate) | Gate |
|---|---|---|---|
| **Critical** | `firsttry/planner.py`, `firsttry/scanner.py`, `firsttry/smart_pytest.py`, `firsttry/state.py` | **≥ 90%** (stretch), **≥ 30%** (minimum gate) | **Yes** (per-file) |
| **Supporting** | cache, reporting, runners, telemetry | ≥ 60% (advised) | Optional |
| **Shell/UI/Legacy** | CLI wrappers, legacy paths | ≥ 30% smoke | No |

> CI fails if any **Critical** file is missing from `coverage.json` or falls below the minimum per-file threshold (default 30%). Raise thresholds as the suite hardens.

## Measurement Rules
- Coverage source is pinned to `src/firsttry` via `.coveragerc`.
- CI runs tests with explicit `--cov` flags; local narrow runs can use `--no-cov` or `--cov-fail-under=0`.
- A tiny import shim at the top of workflow tests ensures “single-test with coverage” doesn’t trip “no data collected.”

## Evidence Artifacts
- `coverage.xml`, `coverage.json`
- (Optional) embed the **Critical** file rates inside FirstTry’s audit JSON for enterprise proof.

## Process
1. Run full suite with coverage flags (fail-under disabled).
2. Run the **Critical Coverage Gate** script.
3. (Optional) publish `coverage.xml` to codecov/gh-pages, and include the per-file table in release notes.

## Exceptions
- Temporary exceptions require a JIRA/Ticket reference and a dated TODO to restore the threshold within 2 releases.

### Critical coverage JSON artifact

CI writes a machine-readable summary at `.firsttry/critical_coverage_summary.json` (override via `FT_COVERAGE_JSON_OUT`). Schema:

```json
{
	"threshold": 60.0,
	"files": [
		{"path": "src/firsttry/state.py", "percent_covered": 61.0}
	],
	"missing": ["src/firsttry/planner.py"],
	"status": "pass"
}
```

Use this for PR comments, dashboards, or embedding into audit artifacts.
