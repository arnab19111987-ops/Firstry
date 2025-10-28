from __future__ import annotations

from .models import ScanResult


def _status_line(commit_safe: bool) -> str:
    return "SAFE TO COMMIT ✅" if commit_safe else "NOT SAFE ❌"


def print_human_report(scan: ScanResult) -> None:
    """
    High-level summary shown BEFORE asking user to allow autofix.

    This now includes explicit per-section counts so the user immediately sees:
    - how many lint issues
    - how many type errors
    - how many security problems
    - how many test/coverage problems
    """
    bar = "─" * 60
    print(f"{bar}")
    print(f"FirstTry: {scan.gate_name} Gate (read-only scan)")
    print(f"{bar}\n")

    # transparent about scope
    print(f"Project check: {scan.files_scanned} files scanned")
    print(f"Gate mode: {scan.gate_name}")
    print(
        "Meaning of this gate:\n"
        "  pre-commit = fast (lint + types only)\n"
        "  pre-push   = full (lint + types + security + tests + coverage)\n"
        "  auto       = adaptive full scan\n"
    )

    # Per-section breakdown
    print("──────── Sections ────────")
    for section in scan.sections:
        total_section_issues = section.autofixable_count + section.manual_count
        print(f"{section.name}")
        print(f"   • Total issues in this section: {total_section_issues}")
        print(f"     - Autofixable: {section.autofixable_count}")
        print(f"     - Manual:      {section.manual_count}")
        for note in section.notes:
            print(f"     - {note}")
        if section.ci_blocking:
            print("     - enforcement: required by CI ✅")
        print()

    # Global rollup
    total_issues_overall = scan.total_autofixable + scan.total_manual
    print("──────── Summary ────────")
    print(f"• Total issues found: {total_issues_overall}")
    print(f"  - Autofixable safely: {scan.total_autofixable}")
    print(f"  - Manual attention:   {scan.total_manual}")
    print(
        f"• Coverage: {scan.coverage_pct:.1f}% "
        f"(requires ≥ {scan.coverage_required:.1f}%)"
    )
    print(f"• Commit status: {_status_line(scan.commit_safe)}")
    if not scan.commit_safe:
        print("  (CI would fail for this gate level)")
    else:
        print("  (CI should pass for this gate level)")
    print()

    # Autofix guidance for this gate
    autofix_cmds = getattr(scan, "autofix_cmds", [])
    if autofix_cmds:
        print("Suggested autofix commands for this gate:")
        for cmd in autofix_cmds:
            print(f"   $ {cmd}")
        print(
            "\nThese are considered safe for this gate.\n"
            "For pre-commit they're gentle (format/import cleanup).\n"
            "For pre-push/auto they can be stricter over time.\n"
        )


def print_detailed_issue_table(scan: ScanResult) -> None:
    """
    Deep dive if user asks "show details".
    Shows every individual issue with file:line and message.
    """
    print("──────── Detailed Issues ────────")
    if not scan.issues:
        print("No issues found 🎉\n")
        return

    for issue in scan.issues:
        loc = f"{issue.file}:{issue.line}" if issue.line is not None else issue.file
        fix_tag = "AUTO" if issue.autofixable else "MANUAL"
        print(f"[{fix_tag}] {issue.kind} @ {loc}")
        print(f"    {issue.message}")
    print()


def print_after_autofix_report(
    before: ScanResult,
    after: ScanResult,
) -> None:
    """
    Show improvement after autofix attempt.
    """
    print("──────────────── AFTER AUTOFIX ────────────────")

    before_total = before.total_autofixable + before.total_manual
    after_total = after.total_autofixable + after.total_manual

    print(
        "Before:\n"
        f"  Total issues: {before_total}\n"
        f"    - Autofixable: {before.total_autofixable}\n"
        f"    - Manual:      {before.total_manual}\n"
        f"  Commit status:  {_status_line(before.commit_safe)}\n"
    )

    print(
        "After:\n"
        f"  Total issues: {after_total}\n"
        f"    - Autofixable: {after.total_autofixable}\n"
        f"    - Manual:      {after.total_manual}\n"
        f"  Commit status:  {_status_line(after.commit_safe)}\n"
    )

    if not after.commit_safe:
        print(
            "CI would still fail at this gate level. Please fix remaining manual issues."
        )
    else:
        print("CI should pass at this gate level now.")
    print()
