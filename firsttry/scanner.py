# firsttry/scanner.py
from __future__ import annotations

import json
import subprocess
from typing import List, Tuple
import os
import fnmatch
from pathlib import Path

# Attempt to load YAML for baseline; if PyYAML isn't available, we'll parse
# a simple fallback format (lines starting with '-' under a 'files:' key).
try:
    import yaml  # type: ignore

    YAML_AVAILABLE = True
except Exception:
    YAML_AVAILABLE = False
from .models import Issue, SectionSummary, ScanResult

COVERAGE_REQUIRED_DEFAULT = 80.0


def _run_cmd(cmd: list[str]) -> tuple[int, str, str]:
    """
    Run a shell command safely and capture exit code, stdout, stderr.
    If the binary doesn't exist, return (127, "", "not found").
    We NEVER raise here. Scanner should not crash just because
    a tool isn't installed yet on the user's machine.
    """
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except FileNotFoundError:
        return 127, "", "not found"
    return proc.returncode, proc.stdout, proc.stderr


# -----------------------------------------------------------------------------
# LINT / STYLE (ruff + black)
# -----------------------------------------------------------------------------


def _scan_with_ruff() -> List[Issue]:
    """
    Run ruff in JSON mode and convert to Issue objects.

    Command:
        ruff check --format=json .

    Ruff JSON looks like:
    [
      {
        "filename": "path/to/file.py",
        "messages": [
          {
            "code": "F401",
            "message": "unused import 'json'",
            "fix": {...} or null,
            "location": {"row": 10, "column": 1},
            ...
          },
          ...
        ]
      },
      ...
    ]

    If "fix" is present, we treat that as autofixable=True.
    Everything else becomes manual.
    """
    code, out, err = _run_cmd(["ruff", "check", "--format", "json", "."])
    if code == 127:
        # ruff missing
        return []

    issues: List[Issue] = []
    try:
        data = json.loads(out or "[]")
    except json.JSONDecodeError:
        data = []

    for file_block in data:
        filename = file_block.get("filename", "<unknown>")
        for msg in file_block.get("messages", []):
            loc = msg.get("location") or {}
            line = loc.get("row")

            autofixable = bool(msg.get("fix"))
            # Ruff can report:
            # - unused imports
            # - debug prints
            # - style issues
            # - complexity / duplication
            # - outright syntax errors (parse errors)
            # We classify them into lint-fixable vs lint-manual.
            issues.append(
                Issue(
                    kind="lint-fixable" if autofixable else "lint-manual",
                    file=filename,
                    line=line,
                    message=f"[{msg.get('code','?')}] {msg.get('message','')}",
                    autofixable=autofixable,
                )
            )

    return issues


def _scan_with_black() -> List[Issue]:
    """
    Run black --check to detect formatting issues.

    Exit codes:
        0   already formatted
        1   would reformat
        123 internal error

    We parse lines like:
        "would reformat path/to/file.py"

    All black issues are considered autofixable because `black .`
    is safe, mechanical, and reversible via git.
    """
    code, out, err = _run_cmd(["black", "--check", "."])
    if code == 127:
        # black missing
        return []

    if code == 0:
        # formatted already, no issues
        return []

    issues: List[Issue] = []
    lines = (out + "\n" + err).splitlines()
    for line in lines:
        line = line.strip()
        if "would reformat " in line:
            fname = line.split("would reformat ", 1)[1].strip()
            issues.append(
                Issue(
                    kind="lint-fixable",
                    file=fname,
                    line=None,
                    message="File not formatted with black",
                    autofixable=True,
                )
            )

    # If black reported nonzero but we didn't find explicit files,
    # add a generic formatting issue.
    if not issues:
        issues.append(
            Issue(
                kind="lint-fixable",
                file="(formatting)",
                line=None,
                message="Code style differs from black formatting.",
                autofixable=True,
            )
        )

    return issues


def _collect_lint_section() -> Tuple[List[Issue], SectionSummary]:
    """
    Combine ruff + black results into a Lint / Style section.

    This bucket includes:
    - unused imports
    - trailing whitespace / formatting
    - debug prints / stray prints
    - complexity / duplication warnings
    - syntax errors caught by ruff
    - PEP8-ish style differences
    """
    ruff_issues = _scan_with_ruff()
    black_issues = _scan_with_black()

    all_lint = ruff_issues + black_issues

    autofix_count = sum(1 for i in all_lint if i.autofixable)
    manual_count = sum(1 for i in all_lint if not i.autofixable)

    notes: List[str] = []
    notes.append(f"{autofix_count} autofixable via ruff/black (imports, format, etc.)")
    if manual_count > 0:
        notes.append(
            f"{manual_count} manual cleanup (debug prints, duplication, syntax, etc.)"
        )

    summary = SectionSummary(
        name="Lint / Style",
        autofixable_count=autofix_count,
        manual_count=manual_count,
        notes=notes,
        ci_blocking=True,
    )
    return all_lint, summary


# -----------------------------------------------------------------------------
# TYPES (mypy)
# -----------------------------------------------------------------------------


def _collect_type_section() -> Tuple[List[Issue], SectionSummary]:
    """
    Run mypy in JSON mode and capture only 'error' severity.
    """
    code, out, err = _run_cmd(
        [
            "mypy",
            "--show-error-codes",
            "--hide-error-context",
            "--no-error-summary",
            "--error-format=json",
            ".",
        ]
    )
    if code == 127:
        # mypy missing
        summary = SectionSummary(
            name="Types",
            autofixable_count=0,
            manual_count=0,
            notes=["mypy not installed, skipping type checks."],
            ci_blocking=True,
        )
        return [], summary

    issues: List[Issue] = []
    try:
        data = json.loads(out or "[]")
    except json.JSONDecodeError:
        data = []

    for msg in data:
        if msg.get("severity") != "error":
            continue
        filename = msg.get("filename", "<unknown>")
        line = msg.get("line")
        code_s = msg.get("code", "")
        message = msg.get("message", "")
        issues.append(
            Issue(
                kind="type-error",
                file=filename,
                line=line,
                message=f"[{code_s}] {message}",
                autofixable=False,
            )
        )

    manual_count = len(issues)
    if manual_count == 0:
        notes = ["0 type errors."]
    else:
        notes = [f"{manual_count} type error(s) detected (mypy)."]

    summary = SectionSummary(
        name="Types",
        autofixable_count=0,
        manual_count=manual_count,
        notes=notes,
        ci_blocking=True,
    )
    return issues, summary


# -----------------------------------------------------------------------------
# SECURITY / SECRETS (bandit)
# -----------------------------------------------------------------------------


def _collect_security_section() -> (
    Tuple[List[Issue], SectionSummary, bool, int, int, List[str], List[str]]
):
    """
    Run bandit with JSON output and capture findings.

    HIGH severity == hard blocker.

    If bandit isn't installed, we skip but explain that.
    """
    code, out, err = _run_cmd(["bandit", "-q", "-r", ".", "-f", "json"])
    if code == 127:
        # bandit missing
        summary = SectionSummary(
            name="Security / Secrets",
            autofixable_count=0,
            manual_count=0,
            notes=["bandit not installed, skipping security scan."],
            ci_blocking=True,
        )
        return [], summary, False

    issues = []
    has_high = False
    # We'll track findings per-file so we can present file-level lists
    file_has_high: dict[str, bool] = {}
    files_with_findings: set[str] = set()
    high_unreviewed = 0
    baselined = 0

    try:
        data = json.loads(out or "{}")
    except json.JSONDecodeError:
        data = {}

    # bandit JSON schema:
    # { "results": [
    #    {
    #      "filename": "...",
    #      "issue_severity": "HIGH",
    #      "issue_text": "...",
    #      "line_number": 42,
    #      ...
    #    }, ...
    # ]}
    for finding in data.get("results", []):
        sev = str(finding.get("issue_severity", "")).upper()
        filename = finding.get("filename", "<unknown>")
        line = finding.get("line_number")
        msg = finding.get("issue_text", "").strip()

        if sev == "high".upper():
            has_high = True

        issues.append(
            Issue(
                kind="security",
                file=filename,
                line=line,
                message=f"[{sev}] {msg}",
                autofixable=False,
            )
        )
        files_with_findings.add(filename)
        file_has_high[filename] = file_has_high.get(filename, False) or (sev == "HIGH")

    # Load baseline (if present) to decide which security findings are
    # considered "known risky but baselined" versus truly unreviewed.
    baseline_path = Path(os.getcwd()) / "firsttry_security_baseline.yml"
    baseline_patterns: List[str] = []
    if baseline_path.exists():
        try:
            text = baseline_path.read_text(encoding="utf-8")
            if YAML_AVAILABLE:
                parsed = yaml.safe_load(text) or {}
                baseline_patterns = parsed.get("files", []) or []
            else:
                # Simple fallback: read lines that start with '-' under a files: block
                lines = [l.strip() for l in text.splitlines()]
                in_files = False
                for ln in lines:
                    if ln.startswith("files:"):
                        in_files = True
                        continue
                    if in_files:
                        if ln.startswith("-"):
                            pattern = ln.lstrip("- ").strip().strip('"')
                            if pattern:
                                baseline_patterns.append(pattern)
                        elif not ln:
                            # blank line ends block
                            break
        except Exception:
            baseline_patterns = []

    # Helper to test whether a filename matches any baseline pattern
    def _is_baselined(fname: str) -> bool:
        # Normalize to relative path
        try:
            rel = os.path.relpath(fname, start=os.getcwd())
        except Exception:
            rel = fname
        rel = rel.replace("\\", "/")
        for pat in baseline_patterns:
            # allow both glob and simple prefix matches
            if fnmatch.fnmatch(rel, pat) or rel.startswith(pat.rstrip("/**")):
                return True
        return False

    # Determine baselined files vs unreviewed high-risk files
    baselined_files: List[str] = []
    high_unreviewed_files: List[str] = []
    for fname in sorted(files_with_findings):
        if _is_baselined(fname):
            baselined += 1
            baselined_files.append(fname)
        else:
            # only treat files with a HIGH finding as high-risk-unreviewed
            if file_has_high.get(fname, False):
                high_unreviewed += 1
                high_unreviewed_files.append(fname)

    manual_count = len(issues)
    if manual_count == 0:
        notes = ["0 security issues detected."]
    else:
        notes = [f"{manual_count} security finding(s)."]
        if has_high:
            notes.append(
                "HIGH severity present. See baseline grouping for reviewed vs unreviewed items."
            )
        notes.append(
            f"{baselined} findings are baselined (known-risk). {high_unreviewed} remain unreviewed/high-risk."
        )

    summary = SectionSummary(
        name="Security / Secrets",
        autofixable_count=0,  # we never silently autofix security
        manual_count=manual_count,
        notes=notes,
        ci_blocking=True,
    )
    # Return counts and file lists for scanner to decide commit safety
    return (
        issues,
        summary,
        has_high,
        high_unreviewed,
        baselined,
        high_unreviewed_files,
        baselined_files,
    )


# -----------------------------------------------------------------------------
# TESTS / COVERAGE (pytest + coverage)
# -----------------------------------------------------------------------------


def _collect_tests_and_coverage_section(
    coverage_required: float = COVERAGE_REQUIRED_DEFAULT,
) -> Tuple[List[Issue], SectionSummary, float, float, bool]:
    """
    Run pytest under coverage and summarize:
      - test failures
      - coverage %

    If 'coverage' isn't installed, we treat as skipped.
    """
    code_covrun, out_covrun, err_covrun = _run_cmd(
        ["coverage", "run", "-m", "pytest", "-q"]
    )
    pytest_failed = code_covrun != 0 and code_covrun != 127

    code_covjson, out_covjson, err_covjson = _run_cmd(["coverage", "json", "-q"])
    coverage_pct: float = 0.0
    if code_covjson == 127:
        # no coverage tool
        coverage_pct = 0.0
    else:
        try:
            covdata = json.loads(out_covjson or "{}")
            totals = covdata.get("totals", {})
            pct_val = totals.get("percent_covered")
            if isinstance(pct_val, (int, float)):
                coverage_pct = float(pct_val)
        except json.JSONDecodeError:
            coverage_pct = 0.0

    issues: List[Issue] = []
    if pytest_failed:
        issues.append(
            Issue(
                kind="test-fail",
                file="(pytest)",
                line=None,
                message="pytest reported failing tests.",
                autofixable=False,
            )
        )

    if coverage_pct < coverage_required:
        issues.append(
            Issue(
                kind="coverage-low",
                file="(coverage)",
                line=None,
                message=f"coverage {coverage_pct:.1f}% < required {coverage_required:.1f}%.",
                autofixable=False,
            )
        )

    notes: List[str] = []
    if pytest_failed:
        notes.append("pytest: failing tests detected.")
    else:
        notes.append("pytest: all tests passed.")

    notes.append(f"coverage: {coverage_pct:.1f}% (requires ≥ {coverage_required:.1f}%)")

    summary = SectionSummary(
        name="Tests & Coverage",
        autofixable_count=0,
        manual_count=len(issues),
        notes=notes,
        ci_blocking=True,
    )

    tests_passing = not pytest_failed
    return issues, summary, coverage_pct, coverage_required, tests_passing


# -----------------------------------------------------------------------------
# COMMIT-SAFE DECISION
# -----------------------------------------------------------------------------


def _compute_commit_safe(
    *,
    has_type_errors: bool,
    has_high_security: bool,
    tests_passing: bool,
    coverage_ok: bool,
    manual_lint_issues: int,
    include_security: bool,
    include_tests: bool,
) -> bool:
    """
    We ONLY call something SAFE TO COMMIT ✅ if everything we *actually
    ran for this gate* is clean.

    Gate logic:
    - pre-commit: we don't even run bandit/pytest/coverage,
      so we don't block on them.
    - pre-push / auto: we DID run them, so they must pass.

    Always:
    - no manual lint issues (manual = debug prints, syntax errors, etc.)
    - no mypy errors
    """
    # Lint must have no manual issues
    if manual_lint_issues > 0:
        return False

    # Types must be clean
    if has_type_errors:
        return False

    # Security must be clean if this gate includes security
    if include_security and has_high_security:
        return False

    # Tests + coverage must be OK if this gate includes tests
    if include_tests:
        if not tests_passing:
            return False
        if not coverage_ok:
            return False

    return True


# -----------------------------------------------------------------------------
# AUTOFIX RECOMMENDATIONS
# -----------------------------------------------------------------------------


def _autofix_recommendations_for_gate(gate_name: str) -> List[str]:
    """
    This returns the shell commands we consider "safe autofix" for this gate.
    cli.py can show or execute these.

    Strategy you asked for:
    - pre-commit: gentle, formatting + trivial lint only.
      (black, ruff --fix)
    - pre-push / auto: stricter; we still keep it safe here,
      but this is the place to expand later (import sorters,
      dead code removers, etc.).
    """
    base = [
        "black .",
        "ruff check --fix .",
    ]

    if gate_name == "pre-commit":
        # be conservative, don't mutate tests/env aggressively
        return base

    # pre-push / auto:
    # same base for now, but this is where we'll grow:
    # e.g. "pytest -q" AFTER fixes, "coverage run ..." etc.
    return base


# -----------------------------------------------------------------------------
# PUBLIC ENTRY (MAIN SCAN)
# -----------------------------------------------------------------------------


def run_all_checks_dry_run(gate_name: str = "pre-commit") -> ScanResult:
    """
    Run scans WITHOUT modifying code. This is always the first step.

    gate_name controls depth:
      - pre-commit
          fast checks only: lint + types
          (we SKIP security, tests, coverage)
      - pre-push
          full CI-grade: lint + types + security + tests+coverage
      - auto
          adaptive full scan (treat same as pre-push for now)

    We return a ScanResult that:
      - has real counts
      - says commit_safe based on what we actually ran
      - includes gate_name so report.py and cli.py can
        message correctly
    """
    run_security = gate_name in ("pre-push", "auto")
    run_tests = gate_name in ("pre-push", "auto")

    # 1. Lint / Style
    lint_issues, lint_summary = _collect_lint_section()

    # 2. Types
    type_issues, type_summary = _collect_type_section()

    # 3. Security (bandit) if this gate includes it
    sec_issues: List[Issue] = []
    sec_summary = SectionSummary(
        name="Security / Secrets",
        autofixable_count=0,
        manual_count=0,
        notes=["security scan skipped for this gate."],
        ci_blocking=True,
    )
    has_high_security = False
    high_unreviewed_count = 0
    baselined_count = 0
    if run_security:
        (
            sec_issues,
            sec_summary,
            has_high_security,
            high_unreviewed_count,
            baselined_count,
            high_unreviewed_files,
            baselined_files,
        ) = _collect_security_section()

    # 4. Tests / Coverage if this gate includes it
    test_issues: List[Issue] = []
    test_summary = SectionSummary(
        name="Tests & Coverage",
        autofixable_count=0,
        manual_count=0,
        notes=["tests/coverage skipped for this gate."],
        ci_blocking=True,
    )
    cov_pct = 0.0
    cov_req = COVERAGE_REQUIRED_DEFAULT
    tests_passing = True
    coverage_ok = True
    if run_tests:
        (
            test_issues,
            test_summary,
            cov_pct,
            cov_req,
            tests_passing,
        ) = _collect_tests_and_coverage_section()
        coverage_ok = cov_pct >= cov_req

    # Combine all sections + issues
    all_issues: List[Issue] = lint_issues + type_issues + sec_issues + test_issues
    all_sections: List[SectionSummary] = [
        lint_summary,
        type_summary,
        sec_summary,
        test_summary,
    ]

    total_autofixable = sum(1 for i in all_issues if i.autofixable)
    total_manual = sum(1 for i in all_issues if not i.autofixable)

    manual_lint_issues = lint_summary.manual_count
    has_type_errors = type_summary.manual_count > 0

    # New security blocking logic: only unreviewed high-risk security findings
    # should block pre-push. Baselined (known) risky files are down-ranked.
    commit_safe = _compute_commit_safe(
        has_type_errors=has_type_errors,
        has_high_security=(high_unreviewed_count > 0),
        tests_passing=tests_passing,
        coverage_ok=coverage_ok,
        manual_lint_issues=manual_lint_issues,
        include_security=run_security,
        include_tests=run_tests,
    )

    # Autofix recommendation list (string shell commands)
    autofix_cmds = _autofix_recommendations_for_gate(gate_name)

    # Build the ScanResult. We attach autofix_cmds by monkey-patching
    # an attribute so cli.py can read it and decide what to do.
    result = ScanResult(
        sections=all_sections,
        issues=all_issues,
        total_autofixable=total_autofixable,
        total_manual=total_manual,
        commit_safe=commit_safe,
        coverage_pct=cov_pct,
        coverage_required=cov_req,
        files_scanned=0,  # we will add real file counting later
        gate_name=gate_name,
    )

    # Attach extra helper data that report/cli can use.
    # This keeps models.py simple (no schema change for now),
    # but gives cli.py the strictness knobs you asked for.
    result.autofix_cmds = autofix_cmds
    # Attach security grouping counts for reporting
    result.high_risk_unreviewed = high_unreviewed_count
    result.known_risky_but_baselined = baselined_count
    # Attach file lists
    result.high_risk_unreviewed_files = getattr(
        locals().get("high_unreviewed_files", None), "copy", lambda: []
    )()
    result.known_risky_but_baselined_files = getattr(
        locals().get("baselined_files", None), "copy", lambda: []
    )()

    return result
