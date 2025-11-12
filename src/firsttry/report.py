from __future__ import annotations

from collections.abc import Iterable

from .models import ScanResult, SectionSummary as SectionResult


def _plural(n: int, word: str) -> str:
    # 1 issue / 2 issues
    return f"{n} {word}" + ("" if n == 1 else "s")


def _status_emoji(section: SectionResult) -> str:
    # SectionSummary in models.py doesn't have a `status` field.
    # Derive a display status from the summary attributes:
    # - ✅  when there are no issues
    # - ❌  when the section is CI-blocking and has issues
    # - ⚠️  for manual / review-needed items
    try:
        if section.autofixable_count == 0 and section.manual_count == 0:
            return "✅"
        if getattr(section, "ci_blocking", False) and (
            section.autofixable_count > 0 or section.manual_count > 0
        ):
            return "❌"
    except Exception:
        # Fallback
        pass
    return "⚠️"


def _fmt_section_line(section: SectionResult) -> str:
    # Example:
    # Lint / Style ......... ❌  3 autofixable / 0 manual
    # Security / Secrets ... ⚠️  0 autofixable / 42 manual
    dots = "." * max(1, 20 - len(section.name))
    return (
        f"{section.name} {dots} {_status_emoji(section)}  "
        f"{section.autofixable_count} autofixable / "
        f"{section.manual_count} manual"
    )


def _explain_security_groups(result: ScanResult) -> list[str]:
    """Builds the new Security summary block:
    - high_risk_unreviewed (blocks push)
    - known_risky_but_baselined (FYI only)
    This function is careful: if those attrs don't exist we degrade gracefully.
    """
    lines: list[str] = []

    high_unrev = getattr(result, "high_risk_unreviewed", None)
    known_base = getattr(result, "known_risky_but_baselined", None)

    if high_unrev is None and known_base is None:
        # Old behavior / fallback
        return lines

    lines.append("")
    lines.append("Security review status:")

    if high_unrev is not None:
        lines.append(
            f"  • {_plural(high_unrev, 'unreviewed high-risk file')} " "(blocking)",
        )
    if known_base is not None:
        lines.append(
            f"  • {_plural(known_base, 'baselined risky file')} "
            "(known test/tool context, not blocking)",
        )

    # If file-level lists are available, print a short list for triage.
    high_files = getattr(result, "high_risk_unreviewed_files", None)
    base_files = getattr(result, "known_risky_but_baselined_files", None)

    if high_files:
        lines.append("")
        lines.append("  Unreviewed high-risk files:")
        # show a compact list, developers can copy/paste these paths
        for p in high_files:
            lines.append(f"    - {p}")

    if base_files:
        lines.append("")
        lines.append("  Baselined (known) risky files:")
        for p in base_files:
            lines.append(f"    - {p}")

    # Guidance text for developer
    # - tells them what to actually do next
    if high_unrev and high_unrev > 0:
        lines.append(
            "  → You must review and fix/annotate those high-risk files before you push.",
        )
    else:
        lines.append("  → No unreviewed high-risk files. Security gate is satisfied.")

    if known_base and known_base > 0:
        lines.append(
            "  → Baseline files are allowed this push, but you still own them. "
            "Keep them from leaking secrets / unsafe exec over time.",
        )

    return lines


def _overall_gate_message(result: ScanResult, gate_name: str) -> str:
    """Final verdict banner.
    We decide the message based on:
      - Are there autofixable failures we haven't fixed yet?
      - Are there unreviewed high-risk security findings? (blocks on pre-push)
      - Did tests/coverage fail? (your scanner should already fold that into sections)
    Logic:
      - pre-commit: block only on autofixable hygiene (lint, format, types)
      - pre-push: also block on unreviewed high-risk security & tests
    """
    high_unrev = getattr(result, "high_risk_unreviewed", 0) or 0

    # A section is considered 'failed' when it has any issues that are
    # CI-blocking (ci_blocking == True) or simply any remaining issues.
    has_failed_section = any(
        (getattr(s, "ci_blocking", False) and (s.autofixable_count > 0 or s.manual_count > 0))
        for s in result.sections
    )

    # Anything autofixable present counts as an autofix block on the pre-commit
    # gate (we assume presence of autofixable issues equals 'needs fix').
    autofix_block = any((s.autofixable_count > 0) for s in result.sections)

    # For test/coverage: consider them blocking when they have any issues.
    tests_block = any(
        (
            ("test" in s.name.lower() or "coverage" in s.name.lower())
            and (s.autofixable_count > 0 or s.manual_count > 0)
        )
        for s in result.sections
    )

    if gate_name == "pre-commit":
        # In pre-commit we only care about autofixable hygiene.
        if autofix_block:
            return "❌  Not ready. Fix autofixable issues (see commands below) before committing."
        # If only MANUAL or baselined security remains, we still allow commit.
        return "✅  Safe to commit. (Full security/test gate will run at pre-push.)"

    # gate_name == "pre-push" or "auto"
    if autofix_block:
        return (
            "❌  Not ready. Autofixable issues still failing. Run the suggested "
            "commands below, then re-run this gate."
        )
    if tests_block:
        return (
            "❌  Tests / coverage not satisfied. Fix failing tests or adjust "
            "coverage budget before pushing."
        )
    if high_unrev and high_unrev > 0:
        return (
            "❌  Not ready. There are unreviewed high-risk security findings. "
            "Either fix them or baseline them with justification."
        )

    if has_failed_section:
        # safety fallback if something else is still FAILED for some reason
        return "❌  Not ready. One or more sections are still failing. Scroll up for details."

    return "✅  Safe to push. CI should pass."


def _autofix_hints(sections: Iterable[SectionResult]) -> list[str]:
    """Build per-tool autofix guidance. This is what feels 'magical':
    - if Format FAILED -> tell them "Run: black ."
    - if Lint FAILED -> tell them "Run: ruff check --fix ."
    - etc.
    We never invent fake commands: we give deterministic, copy-pasteable fixes.
    """
    hints: list[str] = []
    for s in sections:
        # `SectionSummary` doesn't have a `status` attribute. Consider a
        # section 'failed' when it has any issues (autofixable or manual).
        if not (getattr(s, "autofixable_count", 0) > 0 or getattr(s, "manual_count", 0) > 0):
            continue
        # You can customize pattern matching here so we don't guess.
        name_lower = s.name.lower()
        if "format" in name_lower:
            hints.append("Run: black .")
        elif "lint" in name_lower or "style" in name_lower:
            hints.append("Run: ruff check --fix .")
        elif "import" in name_lower or "isort" in name_lower:
            hints.append("Run: isort . --profile black")
        elif "type" in name_lower or "mypy" in name_lower:
            hints.append("Run: mypy --strict .")
        elif "security" in name_lower or "bandit" in name_lower:
            hints.append(
                "Review security findings. High-risk items must be fixed or "
                "explicitly baselined in firsttry_security_baseline.yml.",
            )
        elif "test" in name_lower or "coverage" in name_lower:
            hints.append("Run: pytest -q && coverage run -m pytest && coverage report")
        # else: leave it alone
    return hints


def print_human_report(result: ScanResult, gate_name: str) -> None:
    """Pretty-print the full gate summary in a way that's honest:
    - per section status
    - security breakdown (high-risk vs baselined)
    - final verdict banner
    - autofix hints
    """
    print("\n=== FirstTry Gate Summary ===")

    # 1. Section breakdown
    for section in result.sections:
        print(_fmt_section_line(section))

    # 2. Security explanation block
    sec_lines = _explain_security_groups(result)
    if sec_lines:
        for line in sec_lines:
            print(line)

    # 3. Overall verdict banner
    print()
    print(_overall_gate_message(result, gate_name))
    print()

    # 4. Autofix hints / next steps
    hints = _autofix_hints(result.sections)
    if hints:
        print("Next steps:")
        for h in hints:
            print(f"   ➜ {h}")
        print()

    # 5. Safety note (helps with demos and sales)
    print("FirstTry runs your CI-grade checks locally.")
    print("If this says ✅ Safe to push, your GitHub CI should pass.")
    print()


def print_detailed_issue_table(result: ScanResult) -> None:
    """Show every issue with file:line and message."""
    print("──────── Detailed Issues ────────")
    if not result.issues:
        print("No issues found 🎉\n")
        return

    for issue in result.issues:
        loc = f"{issue.file}:{issue.line}" if issue.line is not None else issue.file
        fix_tag = "AUTO" if issue.autofixable else "MANUAL"
        print(f"[{fix_tag}] {issue.kind} @ {loc}")
        print(f"    {issue.message}")
    print()


def print_after_autofix_report(before: ScanResult, after: ScanResult) -> None:
    """Show a compact before/after summary after autofix attempts."""
    print("──────────────── AFTER AUTOFIX ────────────────")

    before_total = before.total_autofixable + before.total_manual
    after_total = after.total_autofixable + after.total_manual

    print(
        "Before:\n"
        f"  Total issues: {before_total}\n"
        f"    - Autofixable: {before.total_autofixable}\n"
        f"    - Manual:      {before.total_manual}\n"
        f"  Commit status:  {_overall_gate_message(before, before.gate_name)}\n",
    )

    print(
        "After:\n"
        f"  Total issues: {after_total}\n"
        f"    - Autofixable: {after.total_autofixable}\n"
        f"    - Manual:      {after.total_manual}\n"
        f"  Commit status:  {_overall_gate_message(after, after.gate_name)}\n",
    )

    if "Not ready" in _overall_gate_message(after, after.gate_name):
        print(
            "CI would still fail at this gate level. Please fix remaining manual issues.",
        )
    else:
        print("CI should pass at this gate level now.")
    print()
