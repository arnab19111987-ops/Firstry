**Quality & Coverage Guidelines**

- **Global CI coverage target:** 45% (temporary).
- **Local critical modules:** aim for >= 80% coverage when modifying core modules (CLI, parity runner, reporting, license guard).
- **New files / features:** coverage < 70% for a new file is a smell — add focused tests before landing.
- **Why:** we reduced the CI gate to allow incremental test additions while keeping a safety floor. Teams should still strive to increase coverage and remove excluded modules from `.coveragerc` only when they are truly out-of-scope.

If you want this policy enforced more granularly (per-module checks, or a separate pre-commit hook), tell me and I can add a CI job or script to validate module-level thresholds.
