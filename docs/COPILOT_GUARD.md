COPILOT Guard — Conftest and CI
================================

This file contains strict constraints for any automated assistant (Copilot or
similar) when proposing edits to `tests/conftest.py`, CI parity workflows, or
the tests added as part of the stability hardening.

You are ONLY allowed to propose changes that:

- Do NOT weaken the existing fixtures.
- Do NOT remove the autouse behavior for `FIRSTTRY_SHARED_SECRET`.
- Do NOT broaden `stub_external_calls` so much that it starts stubbing generic
  commands (e.g. `echo`, `python -m module`, or simple system utilities).
- Do NOT change the parity lock contract encoded in
  `tests/ci/test_parity_lock_matches_pyproject.py`.
- Do NOT change the pre-commit hook contract encoded in
  `tests/precommit/test_ft_pre_commit_hook.py` (GIT_HOOK=pre-push, FT_NO_NETWORK=1).

When proposing changes, prioritize:

- Small, surgical fixes that are narrowly scoped and well-tested.
- Adding tests when making behavioral changes.
- Avoiding global state mutations that persist beyond the current process.

If a requested change would violate any of the rules above, refuse and explain
what safer alternatives could achieve the goal without weakening the invariants.
