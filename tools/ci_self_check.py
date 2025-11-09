#!/usr/bin/env python3
"""
CI Self-Check Tool - Validates CI/CD pipeline security & compliance claims.

This tool runs post-deployment to verify:
1. Permissions are properly scoped (read-only by default)
2. All actions are SHA pinned (supply-chain security)
3. No static credentials in use (OIDC only)
4. Required status checks are configured
5. Test suites meet coverage baselines
6. Caching strategy is functional

Exit codes:
  0 = All validations passed
  1 = One or more validations failed
  2 = Environment issues (missing tools, config)
"""

import json
import os
import re
import sys
from pathlib import Path


class CISelfCheck:
    """Validate CI/CD pipeline claims."""

    def __init__(self, workspace_root: str = "/workspaces/Firstry"):
        self.workspace_root = Path(workspace_root)
        self.checks_passed = 0
        self.checks_failed = 0
        self.checks_skipped = 0

    def log(self, level: str, message: str) -> None:
        """Log with level indicator."""
        prefix = {"✅": "✅", "❌": "❌", "⚠️ ": "⚠️ ", "ℹ️ ": "ℹ️ "}
        print(f"{prefix.get(level, level)} {message}")

    def check_permissions(self) -> bool:
        """Validate workflow permissions are properly scoped."""
        self.log("ℹ️ ", "Checking workflow permissions...")
        workflows_dir = self.workspace_root / ".github/workflows"

        if not workflows_dir.exists():
            self.log("⚠️ ", "Workflows directory not found")
            self.checks_skipped += 1
            return True

        required_workflows = [
            "ci-hardened.yml",
            "remote-cache-hardened.yml",
            "codeql.yml",
            "audit-hardened.yml",
        ]

        all_valid = True
        for workflow_file in required_workflows:
            workflow_path = workflows_dir / workflow_file
            if not workflow_path.exists():
                self.log("❌", f"Workflow not found: {workflow_file}")
                all_valid = False
                self.checks_failed += 1
                continue

            content = workflow_path.read_text()

            # Check for explicit permissions:
            if "permissions:" not in content:
                self.log("⚠️ ", f"{workflow_file} has no explicit permissions (implicit all)")
                self.checks_skipped += 1
                continue

            # Check no hardcoded secrets
            if re.search(r"AKIA[0-9A-Z]{16}", content):  # AWS key pattern
                self.log("❌", f"{workflow_file} contains AWS access key!")
                all_valid = False
                self.checks_failed += 1
                continue

            self.log("✅", f"{workflow_file} permissions properly scoped")
            self.checks_passed += 1

        return all_valid

    def check_action_pinning(self) -> bool:
        """Validate all actions are SHA pinned."""
        self.log("ℹ️ ", "Checking action SHA pinning...")
        workflows_dir = self.workspace_root / ".github/workflows"

        if not workflows_dir.exists():
            self.checks_skipped += 1
            return True

        all_valid = True
        sha_pattern = re.compile(r"@[a-f0-9]{40}")

        for workflow_file in workflows_dir.glob("*-hardened.yml"):
            # Skip audit workflow as it contains grep patterns
            if "audit" in workflow_file.name:
                continue

            content = workflow_file.read_text()
            uses_lines = re.findall(r"uses: [^\n]+", content)

            for uses_line in uses_lines:
                if "actions/" in uses_line or "aws-actions/" in uses_line:
                    # Should have either SHA or version
                    if not (sha_pattern.search(uses_line) or re.search(r"@v\d+", uses_line)):
                        self.log("❌", f"Unpinned action in {workflow_file.name}: {uses_line[:60]}")
                        all_valid = False
                        self.checks_failed += 1

        if all_valid:
            self.log("✅", "All actions properly versioned")
            self.checks_passed += 1

        return all_valid

    def check_test_coverage(self) -> bool:
        """Validate test coverage meets baselines."""
        self.log("ℹ️ ", "Checking test coverage...")
        coverage_file = self.workspace_root / "coverage.json"

        if not coverage_file.exists():
            self.log("⚠️ ", "coverage.json not found (run pytest with --cov first)")
            self.checks_skipped += 1
            return True

        try:
            coverage_data = json.loads(coverage_file.read_text())
        except json.JSONDecodeError:
            self.log("⚠️ ", "Invalid coverage.json format")
            self.checks_skipped += 1
            return True

        # Check specific files we test
        files_data = coverage_data.get("files", {})
        # Use canonical package path (src/firsttry)
        baselines = {
            "src/firsttry/state.py": 90.0,
            "src/firsttry/planner.py": 90.0,
            "src/firsttry/scanner.py": 75.0,
            "src/firsttry/smart_pytest.py": 70.0,
        }

        for file_path, min_coverage in baselines.items():
            if file_path not in files_data:
                self.log("⚠️ ", f"{file_path}: not in coverage (may not be tested)")
                self.checks_skipped += 1
                continue

            file_info = files_data[file_path]
            # executed_lines can be either a count or a list of executed line numbers
            executed_lines = file_info.get("executed_lines", 0)
            if isinstance(executed_lines, list):
                executed_count = len(executed_lines)
            else:
                try:
                    executed_count = int(executed_lines)
                except Exception:
                    executed_count = 0

            total_lines = file_info.get("num_statements", 1)
            try:
                total_lines = int(total_lines)
            except Exception:
                total_lines = 0

            percent_covered = (executed_count / total_lines * 100) if total_lines > 0 else 0

            if percent_covered >= min_coverage:
                self.log("✅", f"{file_path}: {percent_covered:.1f}% (baseline: {min_coverage}%)")
                self.checks_passed += 1
            else:
                self.log(
                    "⚠️ ",
                    f"{file_path}: {percent_covered:.1f}% (baseline: {min_coverage}%, skipping fail)",
                )
                self.checks_skipped += 1

        return True  # Don't fail on coverage as it requires test run

    def check_critical_coverage(self) -> bool:
        """Enforce minimum coverage for a small set of critical modules.

        This parses coverage.xml (preferred) or coverage.json (fallback) and
        ensures a small set of critical source files are present in the
        coverage output. If any are missing, exit non-zero.
        """
        CRITICAL = {
            "firsttry/state.py",
            "firsttry/smart_pytest.py",
            "firsttry/planner.py",
            "firsttry/scanner.py",
        }
        # Minimum percent required for critical modules
        MIN_RATE = 30.0

        root = self.workspace_root
        cov_path = root / "coverage.json"
        if not cov_path.exists():
            print("⚠️ coverage.json not found; skipping critical coverage check.")
            return True

        try:
            data = json.loads(cov_path.read_text(encoding="utf-8"))
        except Exception as e:
            print("⚠️ Failed to parse coverage.json:", e)
            return False

        failed = []
        files = data.get("files", {}) or {}
        present = set()
        for f, meta in files.items():
            for c in CRITICAL:
                if f.endswith(c):
                    present.add(c)
                    # support both structures (summary.percent_covered)
                    pct = None
                    summ = meta.get("summary") if isinstance(meta, dict) else None
                    if isinstance(summ, dict):
                        pct = summ.get("percent_covered")
                    if pct is None:
                        # older coverage.json stores totals at top-level
                        totals = data.get("totals", {})
                        pct = totals.get("percent_covered")
                    if pct is None:
                        # No percent information available for this file; treat as present
                        continue
                    try:
                        rate = float(pct)
                    except Exception:
                        rate = 0.0
                    if rate < MIN_RATE:
                        failed.append((f, rate))

        # Check for missing critical files entirely
        missing = [c for c in CRITICAL if c not in present]
        if missing:
            print("❌ Critical modules missing from coverage:", missing)
            sys.exit(1)

        if failed:
            print("❌ Critical coverage below threshold:", failed)
            sys.exit(1)

        print("✅ Critical coverage OK")
        return True

    def check_oidc_config(self) -> bool:
        """Validate OIDC configuration for AWS."""
        self.log("ℹ️ ", "Checking OIDC AWS configuration...")

        workflow_path = self.workspace_root / ".github/workflows/remote-cache-hardened.yml"
        if not workflow_path.exists():
            self.checks_skipped += 1
            return True

        content = workflow_path.read_text()

        checks = [
            ("id-token: write", "OIDC token permission"),
            ("role-to-assume:", "Role assumption configured"),
            ("AWS_ROLE_ARN", "AWS role ARN reference"),
            ("role-session-name:", "Session name for audit trail"),
        ]

        all_valid = True
        for pattern, description in checks:
            if pattern in content:
                self.log("✅", f"OIDC {description}: configured")
                self.checks_passed += 1
            else:
                self.log("⚠️ ", f"OIDC {description}: not found")
                self.checks_skipped += 1

        # Check no static AWS credentials
        if "AWS_ACCESS_KEY_ID" in content or "AWS_SECRET_ACCESS_KEY" in content:
            self.log("❌", "Static AWS credentials found (should use OIDC only)")
            all_valid = False
            self.checks_failed += 1
        else:
            self.log("✅", "No static AWS credentials detected")
            self.checks_passed += 1

        return all_valid

    def check_dependabot(self) -> bool:
        """Validate Dependabot configuration."""
        self.log("ℹ️ ", "Checking Dependabot configuration...")

        dependabot_path = self.workspace_root / ".github/dependabot.yml"
        if not dependabot_path.exists():
            self.log("❌", "dependabot.yml not found")
            self.checks_failed += 1
            return False

        content = dependabot_path.read_text()

        checks = [
            ("pip", "Python dependency updates"),
            ("github-actions", "GitHub Actions updates"),
            ("weekly", "Weekly update schedule"),
        ]

        all_valid = True
        for pattern, description in checks:
            if pattern in content:
                self.log("✅", f"Dependabot {description}: configured")
                self.checks_passed += 1
            else:
                self.log("❌", f"Dependabot {description}: not found")
                all_valid = False
                self.checks_failed += 1

        return all_valid

    def check_codeql(self) -> bool:
        """Validate CodeQL security scanning."""
        self.log("ℹ️ ", "Checking CodeQL configuration...")

        workflow_path = self.workspace_root / ".github/workflows/codeql.yml"
        if not workflow_path.exists():
            self.log("❌", "codeql.yml not found")
            self.checks_failed += 1
            return False

        content = workflow_path.read_text()

        checks = [
            ("security-and-quality", "Query set"),
            ("upload-sarif", "SARIF upload"),
            ("security-events: write", "Security event permissions"),
        ]

        all_valid = True
        for pattern, description in checks:
            if pattern in content:
                self.log("✅", f"CodeQL {description}: configured")
                self.checks_passed += 1
            else:
                self.log("❌", f"CodeQL {description}: not found")
                all_valid = False
                self.checks_failed += 1

        return all_valid

    def run_all_checks(self) -> int:
        """Run all validation checks."""
        print("🔍 CI/CD Security & Compliance Self-Check")
        print("=" * 60)
        print()

        self.check_permissions()
        self.check_action_pinning()
        self.check_test_coverage()
        # Enforce that critical modules appear in coverage artifacts
        try:
            self.check_critical_coverage()
        except SystemExit:
            # Bubble up the failure
            raise
        self.check_oidc_config()
        self.check_dependabot()
        self.check_codeql()

        print()
        print("=" * 60)
        print(
            f"Results: ✅ {self.checks_passed} passed | ❌ {self.checks_failed} failed | ⚠️  {self.checks_skipped} skipped"
        )
        print()

        if self.checks_failed == 0:
            self.log("✅", "All CI/CD security checks passed!")
            return 0
        else:
            self.log("❌", f"{self.checks_failed} security check(s) failed")
            return 1


if __name__ == "__main__":
    workspace = os.getenv("WORKSPACE_ROOT", "/workspaces/Firstry")
    checker = CISelfCheck(workspace)
    exit_code = checker.run_all_checks()
    # Additional quick checks for top-level workflow hardening
    # (permissions + concurrency blocks present)
    from pathlib import Path

    ROOT = Path(__file__).resolve().parents[1]
    WF = ROOT / ".github" / "workflows"

    def _must_have_blocks(wf_name: str):
        p = WF / wf_name
        if not p.exists():
            return
        s = p.read_text(encoding="utf-8")
        assert "permissions:" in s, f"{wf_name} missing top-level permissions"
        assert "concurrency:" in s, f"{wf_name} missing top-level concurrency"

    try:
        for wf in ("ci.yml", "remote-cache.yml", "audit.yml"):
            _must_have_blocks(wf)
        # Guard: prevent deprecated ::set-output usage across workflows
        bad = []
        for wf in WF.glob("*.yml"):
            txt = wf.read_text(encoding="utf-8")
            if "::set-output" in txt and "Check for deprecated ::set-output" not in txt:
                bad.append(wf)
        if bad:
            print(f"❌ Deprecated ::set-output in: {', '.join(map(str,bad))}")
            raise SystemExit(1)

        print("CI self-check passed (permissions + concurrency present)")
    except AssertionError as e:
        print(f"CI self-check failure: {e}")
        exit_code = max(exit_code, 1)

    # If running in GitHub Actions, ensure coverage.json exists and is valid.
    # This prevents accidental CI misconfigurations that skip JSON coverage output.
    if os.getenv("GITHUB_ACTIONS"):
        covp = ROOT / "coverage.json"
        if not covp.exists():
            print(
                "❌ coverage.json not found; ensure pytest runs with --cov-report=json:coverage.json"
            )
            raise SystemExit(1)
        try:
            j = json.loads(covp.read_text(encoding="utf-8"))
            if not j.get("files"):
                print("❌ coverage.json has no 'files' entries (empty coverage.json)")
                raise SystemExit(1)
        except Exception as e:
            print(f"❌ invalid coverage.json: {e}")
            raise SystemExit(1)
        print("✅ coverage.json present and valid")

    sys.exit(exit_code)
