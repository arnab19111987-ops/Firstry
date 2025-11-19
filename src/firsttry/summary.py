from __future__ import annotations

import os
import sys
from typing import Any, Dict, List

LEVEL_NAME_MAP = {
    1: "Developers — Fast",
    2: "Developers — Strict",
    3: "Teams — CI parity",
    4: "Teams — Enforced",
}


class SummaryPrinter:
    def __init__(
        self, *, tier: str, results: List[Dict[str, Any]], meta: Dict[str, Any]
    ):
        # tier: "free" | "pro"
        self.tier = (tier or "free").lower()
        self.results = results or []
        self.meta = meta or {}

    def print(self) -> int:
        if self.tier == "pro":
            return self._print_pro()
        return self._print_free()

    def _print_header(self):
        """Prints the main tool header."""
        if self.tier == "pro":
            print("🔹 FirstTry (Pro) — Team Enforcement & CI Parity")
        else:
            print("🔹 FirstTry (Free) — Fastest Local CI Mirror")

    def _print_metadata(self):
        """Prints the formatted 'Context' block."""
        machine = self.meta.get("machine", {})
        repo = self.meta.get("repo", {})
        planned = self.meta.get("planned_checks", [])

        cpus = machine.get("cpus", "unknown")
        files = repo.get("files", "?")
        tests = repo.get("tests", "?")

        print("\n--- Context ---")
        print(f"  Machine: {cpus} CPUs")
        print(f"  Repo:    {files} files, {tests} tests")
        print(f"  Checks:  {', '.join(planned) if planned else 'None'}")

        if self.tier == "pro":
            cfg = self.meta.get("config", {})
            level = cfg.get("level")
            level_name = LEVEL_NAME_MAP.get(
                level, f"Level {level}" if level else "Default"
            )
            drift = "Yes" if cfg.get("fail_on_drift") else "No"
            print(f"  Config:  {level_name} (Enforcing drift: {drift})")

    def _print_summary_line(self, failed: int):
        """Prints the final Pass/Fail result line."""
        if failed:
            s = "s" if failed != 1 else ""
            print(f"  Result: ❌ FAILED ({failed} check{s} failed)")
        else:
            print("  Result: ✅ PASSED (all checks passed)")

    # ---------------- FREE ----------------

    def _print_free(self) -> int:
        self._print_header()
        self._print_metadata()

        print("\n--- Results ---")
        failed = 0
        if not self.results:
            print("  No checks were run.")

        for item in self.results:
            status = item.get("status")
            name = item.get("name") or ""
            detail = item.get("detail", "")
            if status == "ok":
                print(f"  ✅ {name}: {detail}")
            elif status == "warn":
                print(f"  🟡 {name}: {detail}")
            else:
                failed += 1
                print(f"  ❌ {name}: {detail}")
                # Teaser for free tier
                if "mypy" in name:
                    print(
                        "      🔒 Upgrade to FirstTry Pro to get a plain-English fix for this."
                    )
                elif "ci-parity" in name or "ci_parity" in name:
                    print(
                        "      🔒 Upgrade to Pro to see the full drift report (tools, env, deps)."
                    )

        print("\n--- Summary ---")
        self._print_summary_line(failed)
        self._print_footer_free()

        return 1 if failed else 0

    def _print_footer_free(self):
        """Prints the upsell block for the free tier."""
        print("\n💡 Upgrade to FirstTry Pro to:")
        print("   • See full CI Parity (tools, env, deps, score)")
        print("   • Get plain-English fix suggestions for mypy/pytest/eslint")
        print("   • Enforce team-wide consistency via firsttry.toml")

    # ---------------- PRO ----------------

    def _print_pro(self) -> int:
        self._print_header()
        self._print_metadata()

        print("\n--- Results ---")
        failed = 0
        if not self.results:
            print("  No checks were run.")

        for item in self.results:
            status = item.get("status")
            name = item.get("name")
            detail = item.get("detail", "")
            override = item.get("config_override", False)
            suggestion = item.get("suggestion")

            if status == "ok":
                extra = " (config override)" if override else ""
                print(f"  ✅ {name}: {detail}{extra}")
            elif status == "warn":
                print(f"  🟡 {name}: {detail}")
            else:
                failed += 1
                print(f"  ❌ {name}: {detail}")
                if suggestion:
                    print(f"      💡 {suggestion}")

        print("\n--- Summary ---")
        self._print_summary_line(failed)
        self._print_footer_pro()

        return 1 if failed else 0

    def _print_footer_pro(self):
        """Prints the confirmation block for the pro tier."""
        print("  Status: ✅ Pro features enabled.")
        cfg = self.meta.get("config", {})
        if cfg.get("fail_on_drift"):
            print("  Config: ✅ Enforcement active (fail_on_drift=true).")


def print_run_summary(
    results: List[Dict[str, Any]], meta: Dict[str, Any], tier: str | None = None
) -> int:
    if not tier:
        tier = os.getenv("FIRSTTRY_TIER", "free")
    sp = SummaryPrinter(tier=tier, results=results, meta=meta)
    return sp.print()

    def _print_summary_line(self, failed: int):
        """Prints the final Pass/Fail result line."""
        if failed:
            s = "s" if failed != 1 else ""
            print(f"  Result: ❌ FAILED ({failed} check{s} failed)")
        else:
            print("  Result: ✅ PASSED (all checks passed)")

    def _print_footer_status(self):
        """Prints the status lines, which are essentially the upsell for 'developer'."""
        if self.tier == "teams":
            print("  Status: ✅ Teams features enabled.")
            cfg = self.meta.get("config", {})
            if cfg.get("fail_on_drift"):
                print("  Config: ✅ Enforcement active (fail_on_drift=true).")
        else:
            # We use the same structure but keep the upsell as per your sample
            print("  Status: ❓ Limited features. Upgrade for full report.")
            cfg = self.meta.get("config", {})
            if cfg.get("fail_on_drift"):
                print("  Config: 🔒 Enforcement active (details locked).")

    # ---------------- INTERACTIVE FLOW METHODS ----------------

    def _prompt_for_details(self) -> None:
        """Handles the interactive prompt and non-interactive detection."""
        if not sys.stdin.isatty():
            print("⚠️ Non-interactive environment detected. Printing full error report.")
            if self.tier == "teams":
                self._print_detailed_report_teams()
            else:
                self._print_detailed_report_developer()
            return

        # Interactive Mode
        try:
            while True:
                user_input = input("💡 Detailed error report? (Y/N): ").strip().upper()
                if user_input == "Y":
                    if self.tier == "teams":
                        self._print_detailed_report_teams()
                    else:
                        self._print_detailed_report_developer()
                    break
                elif user_input == "N":
                    print("\nDetailed report skipped.")
                    break
                else:
                    print("Invalid input. Please enter 'Y' or 'N'.")
        except EOFError:
            print("\nDetailed report skipped (EOF detected).")
        except KeyboardInterrupt:
            print("\nDetailed report skipped (interrupted).")

    # ---------------- TEAMS (Full Detail) ----------------

    def _print_teams_interactive(self) -> int:
        failed_count = len(self.failed_results)

        self._print_header()
        self._print_metadata()
        print("\n--- Results ---")
        self._print_results_summary_only(is_teams=True)
        print("\n--- Summary ---")
        self._print_summary_line(failed_count)
        self._print_footer_status()

        if failed_count > 0:
            print()
            self._prompt_for_details()

        return 1 if failed_count else 0

    def _print_detailed_report_teams(self):
        """Prints the full, helpful details for the Teams tier."""
        print("\n================ DETAILED ERROR REPORT (TEAMS) ================")

        for item in self.failed_results:
            name = item.get("name")
            detail = item.get("detail", "")
            suggestion = item.get("suggestion")

            print(f"\n--- ❌ {name.upper()} ---")
            print(f"  Summary: {detail}")

            if suggestion:
                print("  Fix Suggestion:")
                print(f"    💡 {suggestion}")
            else:
                print("  Details: Review tool logs for complete output.")

        print("\n================ END REPORT ================")

    def _print_results_summary_only(self, is_teams=False):
        """Prints the results list without error details/suggestions."""
        if not self.results:
            print("  No checks were run.")
            return

        for item in self.results:
            status = item.get("status")
            name = item.get("name")
            detail = item.get("detail", "")
            override = item.get("config_override", False)

            if status == "ok":
                extra = " (config override)" if override else ""
                print(f"  ✅ {name}[0]: {detail}{extra}")
            elif status == "warn":
                print(f"  🟡 {name}[0]: {detail}")
            else:
                # For failures, we only print the high-level summary line
                print(f"  ❌ {name}[0]: {detail}")

    # ---------------- DEVELOPER (Locked Detail) ----------------

    def _print_developer_interactive(self) -> int:
        failed_count = len(self.failed_results)

        self._print_header()
        self._print_metadata()
        print("\n--- Results ---")

        # Developer Tier must print the high-level summary line AND the lock messages directly
        for item in self.results:
            status = item.get("status")
            name = item.get("name")
            detail = item.get("detail", "")
            if status == "ok":
                print(f"  ✅ {name}[0]: {detail}")
            elif status == "warn":
                print(f"  🟡 {name}[0]: {detail}")
            else:
                print(f"  ❌ {name}[0]: {detail}")
                # The lock messages remain in the main report block
                if name == "mypy":
                    print(
                        "      🔒 Upgrade to FirstTry Teams to get a plain-English fix for this."
                    )
                elif name in ("ci-parity", "ci_parity"):
                    print(
                        "      🔒 Upgrade to Teams to see the full drift report (tools, env, deps)."
                    )

        print("\n--- Summary ---")
        self._print_summary_line(failed_count)
        self._print_footer_status()  # Now prints the "Limited features" status

        if failed_count > 0:
            print()
            self._prompt_for_details()

        return 1 if failed_count else 0

    def _print_detailed_report_developer(self):
        """Prints the *limited* details and includes a final, large upsell block."""
        print("\n================ DETAILED ERROR REPORT (DEVELOPER) ================")

        for item in self.failed_results:
            name = item.get("name")
            detail = item.get("detail", "")

            print(f"\n--- ❌ {name.upper()} ---")
            print(f"  Summary: {detail}")

            # This is the "detail" when a user asks for it, which is still an upsell
            if name == "mypy":
                print("  Details: Full fix suggestion is locked. Upgrade to Teams.")
            elif name in ("ci-parity", "ci_parity"):
                print("  Details: Full drift report is locked. Upgrade to Teams.")
            else:
                print(
                    "  Details: No further details available. Upgrade to Teams for assistance."
                )

        print("\n--- Upgrade Information ---")
        print("💡 Upgrade to FirstTry Teams to:")
        print(
            "   • Get detailed, actionable fix suggestions instead of this placeholder."
        )
        print("   • See full CI Parity (tools, env, deps, score).")
        print("   • Enforce team-wide consistency via firsttry.toml.")

        print("\n================ END REPORT ================")

    # ---------------- FREE ----------------

    def _print_free(self) -> int:
        failed = len(self.failed_results)

        self._print_header()
        self._print_metadata()

        print("\n--- Results ---")
        if not self.results:
            print("  No checks were run.")

        for item in self.results:
            status = item.get("status")
            name = item.get("name")
            detail = item.get("detail", "")
            if status == "ok":
                print(f"  ✅ {name}[0]: {detail}")
            elif status == "warn":
                print(f"  🟡 {name}[0]: {detail}")
            else:
                print(f"  ❌ {name}[0]: {detail}")
                # Teaser for free tier
                if name == "mypy":
                    print(
                        "      🔒 Upgrade to FirstTry Pro to get a plain-English fix for this."
                    )
                elif name in ("ci-parity", "ci_parity"):
                    print(
                        "      � Upgrade to Pro to see the full drift report (tools, env, deps)."
                    )

        print("\n--- Summary ---")
        self._print_summary_line(failed)
        self._print_footer_free()

        return 1 if failed else 0

    def _print_footer_free(self):
        """Prints the upsell block for the free tier."""
        print("\n💡 Upgrade to FirstTry Pro to:")
        print("   • See full CI Parity (tools, env, deps, score)")
        print("   • Get plain-English fix suggestions for mypy/pytest/eslint")
        print("   • Enforce team-wide consistency via firsttry.toml")
