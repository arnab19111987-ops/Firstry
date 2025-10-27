# Protect this repo — VS Code extension flow

This document describes the lightweight onboarding flow the VS Code extension performs when the user clicks "Protect this repo".

Goal: get a developer from a fresh clone to a repository protected by FirstTry hooks and an in-editor PASS/FAIL indicator in under 5 minutes.

Steps the extension performs

1. Validate workspace contains a FirstTry-compatible repo root (contains `firsttry` package or `pyproject.toml`).
2. Run `firsttry init` (this will attempt to ensure dev support files and write hooks). This is safe and idempotent.
3. Run `firsttry install-hooks` to place `.git/hooks/pre-commit` and `.git/hooks/pre-push` that call FirstTry.
4. Run `firsttry run --gate pre-commit` to get immediate feedback.
5. Write `.firsttry.json` in the repo root containing:
   - `hook_installed`: true
   - `installed_at`: ISO timestamp
   - `coverage_threshold`: (number)
   - `last_verdict`: `pass` or `fail`
6. Surface the verdict inline in the VS Code UI (status bar + gutter/icon) and attach a link to the full gate summary.

Notes for implementers

- The extension MUST not run destructive commands. Mirror CI run is optional and gated by the user supplying a license.
- When calling CLI commands, prefer spawning the same Python interpreter the workspace uses (if known) or `python` on PATH.
- If `firsttry init` fails due to missing permissions, surface a clear action: "Run: sudo chown -R $(whoami) .git/hooks" or run in a terminal.

Telemetry (optional)

- Capture success/failure of the Protect flow (boolean) and duration.
- Don't capture any source code or command output. Only high-level success/failure and duration.
