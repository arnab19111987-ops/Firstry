Artifact & ignore policy

- Canonical run report: FirstTry writes the default run summary to `.firsttry/last_run.json` unless an alternative `--report-json` path is explicitly provided. This keeps the repository root clean by centralizing run artifacts under the `.firsttry/` folder.

- Central ignore: `src/firsttry/ignore.py` is the single source of truth for paths/globs excluded from checks. Avoid adding ad-hoc ignore lists elsewhere; `scripts/ci_checks.py` will enforce this in CI.

Notes:
- If you need to persist alternate reports for automation or archives, pass `--report-json` explicitly.
- The CI guard script will fail if new code adds `IGNORE_DIRS` or `IGNORE_GLOBS` outside the allowed files; update `ignore.py` instead.
