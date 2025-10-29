# FirstTry

**FirstTry makes sure your pull request is green on the first push.**  
It runs the same checks as your GitHub Actions CI, locally, in seconds — and tells you exactly which step would fail and how to fix it.

**Pass CI on the first try.**

FirstTry is a pre-commit quality gate that runs the same checks your CI does, locally, before you push. No more "fix lint" commits.

Security Gate: Blocks unsafe shell execution patterns and secret leaks before you ever push to GitHub. This is what your CI wishes it did locally.

<!-- ci-trigger: touch to run CI workflows -->

---

# FirstTry — Ship Green On The First Try ✅

Quick Start
- Install: `pip install -e .` or `pip install firsttry`
- Run the pre-commit gate locally: `firsttry run --gate pre-commit`
- Install hooks: `firsttry install-hooks`

Pro vs Free
- Free: local gating (`firsttry gates`) that prevents obviously broken commits and surfaces failing steps.
- Pro: `firsttry mirror-ci --run` executes your CI steps locally (safe sandbox, denies destructive commands) and requires a license key.

VS Code flow (one-click onboarding)
- Click the extension `Protect this repo` action.
- Extension runs: `firsttry init`, `firsttry install-hooks`, `firsttry run --gate pre-commit`.
- Extension writes `.firsttry.json` with install metadata and coverage threshold and surfaces PASS/FAIL inline in the editor.

---

## Quick Start

```bash
# Install
pip install firsttry

# Run checks before commit
firsttry run --gate pre-commit

# Install git hooks for automatic checking
firsttry install-hooks

# See what your CI will run
firsttry mirror-ci --root .
```

### Trying FirstTry locally (no install)
You can run FirstTry directly from the repo using Python:

```bash
# Check version
python -m firsttry.cli --version

# See if your repo is clean to push (lint, typecheck, etc.)
python -m firsttry.cli gates --json --root .

# Simulate CI locally (requires a license key for --run)
python -m firsttry.cli mirror-ci --root . --run --json --license-key TEST-KEY-OK


python -m firsttry.cli uses the same engine and returns the same JSON you'd get from the packaged firsttry command.

This absolutely matters for onboarding. It means you don’t have to ship wheels or publish to PyPI before giving someone value. You can just DM them the repo and a license key.

And critically: that block makes it crystal clear that `mirror-ci` is gated behind a key. That’s how you start charging.
```

## Fast start — one-command activation

If you want a single command to install hooks, run an initial autofix pass, and finish onboarding, use the
`activate` command we added to the CLI. This is the smoothest way to get FirstTry protecting a repo.

```bash
# Install
pip install firsttry

# One-command activation (installs hooks + runs autofix scan)
python -m firsttry.cli activate
```

What this does:
- Installs `pre-commit` and `pre-push` git hooks for FirstTry.
- Runs the `pre-commit` gate once in non-interactive autofix mode (applies safe fixes).
- Prints onboarding instructions and next steps.

If the initial scan finds issues that require manual attention, `activate` will still install hooks and
print guidance on how to review and finish onboarding.


## FirstTry — ship green on the first push

FirstTry runs all your quality gates (lint, typecheck, formatting, etc.) and even simulates your GitHub Actions pipeline locally — safely — so you don't spam PRs with "fix lint lol" commits.

### 1. Repo Health (Free)
Check if your repo is clean before you push.

```bash
firsttry gates --json


or

python -m firsttry.cli gates --json


What this does:

Runs your "pre-commit" / "pre-push" style gates (ruff, mypy, tests, etc.).

Captures returncode, stdout, and stderr from each check.

Never crashes — even if a tool explodes, the result comes back as a structured failure entry.

Returns a single JSON report:

{
  "ok": false,
  "results": [
    {
      "gate": "pre-commit",
      "ok": false,
      > **Public Beta (v0.1.0-beta)**  
      > You can start using FirstTry right now:
      >
      > 1. **CLI setup & workflow** → [GET_STARTED.md](./GET_STARTED.md)  
      > 2. **VS Code extension install** → [INSTALL_VSCODE_EXTENSION.md](./INSTALL_VSCODE_EXTENSION.md)  
      > 3. **Download the extension (.vsix)** → Check the latest Release tagged `v0.1.0-beta`
      >
      > FirstTry = ship code that passes CI on the first try. No more "fix lint lol" commits.

      ````markdown
      # FirstTry

      **FirstTry makes sure your pull request is green on the first push.**  
      It runs the same checks as your GitHub Actions CI, locally, in seconds — and tells you exactly which step would fail and how to fix it.

      **Pass CI on the first try.**

      FirstTry is a pre-commit quality gate that runs the same checks your CI does, locally, before you push. No more "fix lint" commits.

      <!-- ci-trigger: touch to run CI workflows -->

      ## Quick Start

      ```bash
      # Install
      pip install firsttry

      # Run checks before commit
      firsttry run --gate pre-commit

      # Install git hooks for automatic checking
      firsttry install-hooks

      # See what your CI will run
      firsttry mirror-ci --root .
      ```
    "failed_at": {
      "workflow": "ci.yml",
      "job": "build",
      "step": "Run tests",
      "cmd": "pytest -q",
      "stderr": "E    AssertionError: 1 != 0\n",
      "duration_s": 3.24
    }
  }
}
```

Want early access to Pro? Reach out to our team to request an early access key — we'll enable `--run` for your account.

# Option B: via flag
firsttry mirror-ci --root . --run --json --license-key YOUR-LICENSE-KEY


What this does:

Reads .github/workflows/*.yml

Builds your CI plan (jobs, steps, run commands)

Executes allowed steps locally in order

Blocks obviously dangerous commands with a safety denylist

e.g. rm -rf /, fork bombs, shutdown

Captures stdout / stderr / return codes per step

Returns a structured JSON summary so you know exactly what will fail in PR

If no valid license key is provided:

You still get the dry-run plan (visibility)

But Pro execution (--run) is restricted

This is perfect for:

Senior engineers who are sick of red PRs

Juniors who don't want to look bad on review

Teams that want “CI green on first try”

3. Safety

We will not run destructive commands.
Known-dangerous patterns (like rm -rf /) are denied up front.
Blocked steps are reported as:

{
  "job": "build",
  "step": "cleanup",
  "cmd": "rm -rf /",
  "status": "blocked",
  "reason": "blocked_for_safety",
  "returncode": null,
  "stdout": "",
  "stderr": "Command blocked by safety policy"
}


So you get transparency without wrecking your machine.

4. Quality Gates on FirstTry itself

Before we ship anything, we run one command:

AUTOFIX=1 bash local_ci.sh


That enforces:

Ruff + Black formatting

Mypy (0 errors, repo-wide)

Pytest (currently 70+ tests)

Coverage (75%+ across core modules like gates, mirror-ci, licensing, safety)

Node-side checks for supporting extensions / dashboard code

JSON contract tests for both gates and mirror-ci CLI commands

If any of that fails, we don't ship.

This isn’t a toy script. This is production posture.


That block:
- Teaches what you do in under 2 minutes.
- Shows off that you're serious (mypy, coverage, safety).
- Draws a clean pricing line between Free and Pro without using the ugly word "paywall".
- Gives you screenshots you can post.

Add that to README.md and commit it. That is step one toward onboarding pilot teams.

---

## 2. Tiny UX/sales tweaks you should do next

These are easy wins that make demos way more convincing:

### (a) Human output mode for `firsttry gates`
Right now `--json` prints JSON, which is perfect for your VS Code / Codespaces panel and tests.  
For humans (no `--json` flag), you're already printing a readable summary like:

```text
FirstTry Gates Report
---------------------
[pre-commit] ok=False status=fail returncode=1
[pre-push] ok=True status=pass returncode=0

OVERALL OK: False
```

Keep that. That’s a screenshot candidate. That goes in README too, as a second example.

 (b) Add “Suggested next step”

At the end of that human-readable print in cmd_gates, append something like:

if not all_ok:
    print("\nTip: Run `firsttry gates --json` to see exact stdout/stderr for each failed gate.")
else:
    print("\n✓ Repo is clean. You’re safe to push.")


That one line does two things:

It teaches people how to self-diagnose without DMing you.

It markets your JSON format (which is your dashboard API) right inside the CLI.

(c) Screenshot those two commands for marketing:

firsttry gates (failing repo)

firsttry mirror-ci --run --json (with one failing step and one blocked dangerous step)

The second one especially is money because you can say:

“We blocked a destructive command from your CI and still told you what else passed. Your laptop is safe.”

That’s how you close teams.

## Roadmap

- [ ] Security baseline noise reducer (group known test/tool files instead of flooding output)

Screenshots / GIFs
-------------------

Saved example placeholders (replace with real images):

- `docs/screenshots/gates_failure.png` — screenshot of `firsttry gates` with one gate failing
- `docs/screenshots/mirror_ci_failed_at.gif` — GIF showing `firsttry mirror-ci --run --json` highlighting `failed_at`

### Visual demos

We're capturing real CI runs and hook failures and will publish anonymized screenshots and GIFs here after a short private beta. For now, the forensic `failed_at` JSON block above is the canonical proof of value.

### Workflow timing (why devs actually use it)

FirstTry runs in three layers so you don't get slowed down:

1. `pre-commit` gate (auto-installed git hook)
  - ~1-3 seconds
  - Lint, imports, basic safety checks
  - Blocks dumb mistakes from even entering your history

2. `pre-push` gate
  - ~5-10 seconds (depends on repo)
  - Type-check, smoke tests, DB drift sanity
  - Blocks "oops broke tests" from hitting origin

3. `firsttry mirror-ci --run` (Pro)
  - Runs the actual steps from your GitHub Actions locally
  - Stops at the first failing step
  - Gives you a forensic `failed_at` block with job, step, stderr, and a suggested quick-fix when available
  - Use this before opening a PR so your PR goes green on first try

This three-tier story sells both speed and workflow: quick developer feedback at commit time, broader checks on push, and a full confidence check before your PR.

### Local dev requirements

To run `pytest -q` and to run the Pro CI mirror locally:

- Python 3.11+
- `pip install -e .` from repo root
- `ruff`, `mypy`, `pytest` installed in your venv (our tests assume they're available)
- For Pro mode (`firsttry mirror-ci --run`):
  - set `FIRSTTRY_LICENSE_KEY=TEST-KEY-OK` for local testing
  - some steps in your GitHub Actions may assume tools you haven't installed locally yet (example: `ruff check .`). FirstTry will report that failure and stop instantly on that step.

Why this matters: we're honest about local assumptions. If a CI step requires a tool you don't have, FirstTry will tell you quickly so you can install it and re-run.

### 30-second smoke test

1. Create and activate a venv and install:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

2. Quick health report:

```bash
firsttry doctor --json
```

3. Preview your CI plan:

```bash
firsttry mirror-ci --root .
```

4. (Pro preview) simulate running those steps locally:

```bash
FIRSTTRY_LICENSE_KEY=TEST-KEY-OK firsttry mirror-ci --root . --run
```

If step 4 stops with a JSON block that includes `"failed_at"`, that's exactly what would have broken your PR.


## Features

### 🚀 Pre-Commit/Pre-Push Gates

Run quality checks before commits hit CI:

```bash
**Output:**
```
Lint.......... PASS ruff
## FirstTry security gate & baseline

FirstTry includes a local CI gate you can run with `python -m firsttry.cli run --gate pre-push`.
It executes linting, type checks, security scans (bandit), and tests with coverage. Findings are grouped into
two buckets: (1) unreviewed high-risk security files which will block a push, and (2) baselined files
that are known noisy/test/tool paths and are shown for information only. Use `python -m firsttry.cli baseline add <glob>`
to add a path or glob to the baseline and immediately re-run the full gate to see its effect.
Format........ PASS black-check
Types......... PASS mypy
Tests......... PASS pytest
Coverage XML.. PASS coverage_xml
Coverage Gate. PASS coverage_gate

Verdict: SAFE TO COMMIT ✅

Everything looks good. You'll almost certainly pass CI on the first try.
```

### 🔍 Mirror CI Locally

See exactly what your GitHub Actions workflows will run:

```bash
firsttry mirror-ci --root .
```

**Example Output:**
```
Workflow: ci.yml
  Job: qa
    Step: Lint
      Run:
        ruff check .
    Step: Test
      Run:
        pytest -q
    Step: Type Check
      Run:
        mypy .
```

This is your CI plan as a dry-run checklist.

### ⚙️ Environment Variables

#### `FIRSTTRY_USE_REAL_RUNNERS`

Toggle between stub runners (fast, no dependencies) and real analysis tools:

```bash
# Use lightweight stubs (default)
firsttry run --gate pre-commit

# Use real ruff, black, mypy, pytest
FIRSTTRY_USE_REAL_RUNNERS=1 firsttry run --gate pre-commit
```

**Why this matters:**
- Stubs: Fast feedback loop during development
- Real runners: Serious analysis before pushing
- **One env var to flip** between "quick sanity" and "CI-grade checks"

Perfect for CI pipelines, pre-push hooks, or when you want confidence.

## Installation

```bash
pip install firsttry
```

Or from source:

```bash
git clone https://github.com/arnab19111987-ops/Firstry.git
cd Firstry
pip install -e .
```

## Commands

### `firsttry run`

Run a quality gate (pre-commit or pre-push).

```bash
firsttry run --gate pre-commit
firsttry run --gate pre-push
firsttry run --gate pre-commit --require-license
```

When something fails, FirstTry explains exactly what broke and how to fix it.

Example:

```text
--- Format (black) FAILED ---
Fix:
  Run: black .

--- Lint (ruff) FAILED ---
Fix:
  Run: ruff --fix .
```

**Options:**
- `--gate`: Which gate to run (`pre-commit` | `pre-push`)
- `--require-license`: Fail if license check fails

### `firsttry install-hooks`

Install git hooks that automatically run FirstTry before commits/pushes.

```bash
firsttry install-hooks
```

Creates:
- `.git/hooks/pre-commit` - Runs `pre-commit` gate
- `.git/hooks/pre-push` - Runs `pre-push` gate

### `firsttry mirror-ci`

Show what CI workflows will run, locally.

```bash
firsttry mirror-ci --root .
```

**Options:**
- `--root`: Project root containing `.github/workflows` (default: `.`)

## Runners API (Semi-Stable)

FirstTry's runner interface is **semi-stable**. You can build alternate runner packs by implementing:

```python
from types import SimpleNamespace

def run_ruff(args) -> SimpleNamespace:
    """Run ruff linter."""
    return SimpleNamespace(
        ok=True,           # bool: did the check pass?
        name="ruff",       # str: runner name
        duration_s=0.5,    # float: how long it took
        stdout="",         # str: command stdout
        stderr="",         # str: command stderr
        cmd=("ruff", ...") # tuple: command that ran
    )

def run_black_check(args) -> SimpleNamespace:
    """Run black formatter check."""
    # Same signature as above

def run_mypy(args) -> SimpleNamespace:
    """Run mypy type checker."""
    # Same signature as above
```

**Why you'd want this:**
- Ship alternate tool sets (ruff → pylint, black → yapf)
- Add company-specific checks
- Integrate proprietary analysis tools

Place your runners in `tools/firsttry/firsttry/runners.py` and set `FIRSTTRY_USE_REAL_RUNNERS=1`.

## Development

```bash
# Run tests
pytest -q

# Run with real runners
FIRSTTRY_USE_REAL_RUNNERS=1 pytest -q

# Install in editable mode
pip install -e .
```

## License

MIT

## Tags & Branches

- `firsttry-core-v0.1`: First stable release, 42/42 tests passing, hardened runner loader
- `feat/firsttry-stable-core`: Development branch for stable core features
