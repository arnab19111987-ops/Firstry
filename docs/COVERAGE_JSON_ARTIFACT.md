### Critical coverage JSON artifact

CI writes a machine-readable summary at `.firsttry/critical_coverage_summary.json` (path configurable via `FT_COVERAGE_JSON_OUT`). Schema:

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
