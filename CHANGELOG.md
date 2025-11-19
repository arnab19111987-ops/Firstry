# Changelog

## 1.0.1 - 2025-11-18

- Added: `firsttry gate {dev,merge,release}` — minimal gate policy using CI intents.
- Added: `firsttry ci-intent-lint` and `firsttry ci-intent-autofill` for discovering and mapping GitHub Actions jobs.
- Added: `firsttry.ci_parity` package (intent discovery, mirror autofill, and runner).
- Added: local simulation harness and reporting under `.firsttry/` to improve reliability of release checks.

Notes:
- `ci-intent-autofill` will create `.firsttry/ci_mirror.toml` when run without `--dry-run`.
- The `ci_parity` implementation intentionally performs non-destructive checks; autofill can append mirror entries.
