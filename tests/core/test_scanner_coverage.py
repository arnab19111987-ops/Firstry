"""Comprehensive coverage tests for src/firsttry/scanner.py

This suite targets:
- Command execution and safety (_run_cmd)
- Issue and ScanResult model creation and aggregation
- Coverage threshold constants
"""

from firsttry.models import Issue, ScanResult, SectionSummary
from firsttry.scanner import COVERAGE_REQUIRED_DEFAULT, _run_cmd


class TestRunCmd:
    """Test safe command execution."""

    def test_run_cmd_success(self):
        """Test _run_cmd with successful command."""
        code, out, err = _run_cmd(["echo", "hello"])
        assert code == 0
        assert "hello" in out

    def test_run_cmd_failure(self):
        """Test _run_cmd with failing command."""
        code, out, err = _run_cmd(["sh", "-c", "exit 42"])
        assert code == 42

    def test_run_cmd_not_found(self):
        """Test _run_cmd with non-existent command."""
        code, out, err = _run_cmd(["nonexistent_binary_xyz", "--help"])
        assert code == 127
        assert out == ""
        assert err == "not found"

    def test_run_cmd_captures_stderr(self):
        """Test _run_cmd captures stderr."""
        code, out, err = _run_cmd(["sh", "-c", "echo error >&2; exit 0"])
        assert code == 0
        assert "error" in err

    def test_run_cmd_captures_stdout(self):
        """Test _run_cmd captures stdout."""
        code, out, err = _run_cmd(["sh", "-c", "echo output; exit 0"])
        assert code == 0
        assert "output" in out

    def test_run_cmd_never_raises(self):
        """Test _run_cmd never raises exceptions."""
        code, out, err = _run_cmd(["bash", "-c", "kill -9 $$"])
        assert isinstance(code, int)
        assert isinstance(out, str)
        assert isinstance(err, str)

    def test_run_cmd_multiline_output(self):
        """Test _run_cmd handles multiline output."""
        code, out, err = _run_cmd(["sh", "-c", "echo line1; echo line2; echo line3"])
        assert code == 0
        assert "line1" in out
        assert "line2" in out
        assert "line3" in out

    def test_run_cmd_empty_output(self):
        """Test _run_cmd handles empty output."""
        code, out, err = _run_cmd(["true"])
        assert code == 0
        assert out == ""
        assert err == ""

    def test_run_cmd_large_output(self):
        """Test _run_cmd handles large output."""
        code, out, err = _run_cmd(["python", "-c", "print('x' * 10000)"])
        assert code == 0
        assert len(out) > 9900

    def test_run_cmd_stderr_and_stdout(self):
        """Test _run_cmd handles both stdout and stderr."""
        code, out, err = _run_cmd(["sh", "-c", "echo stdout; echo stderr >&2; exit 0"])
        assert code == 0
        assert "stdout" in out
        assert "stderr" in err


class TestIssueModel:
    """Test Issue model creation and attributes."""

    def test_issue_basic_creation(self):
        """Test Issue can be created with required fields."""
        issue = Issue(
            kind="lint-fixable",
            file="test.py",
            line=10,
            message="unused import",
            autofixable=True,
        )
        assert issue.kind == "lint-fixable"
        assert issue.file == "test.py"
        assert issue.line == 10
        assert issue.message == "unused import"
        assert issue.autofixable is True

    def test_issue_with_none_line(self):
        """Test Issue with None line number."""
        issue = Issue(
            kind="security",
            file="(pytest)",
            line=None,
            message="coverage low",
            autofixable=False,
        )
        assert issue.line is None
        assert issue.kind == "security"

    def test_issue_all_kinds(self):
        """Test Issue supports all valid kinds."""
        kinds = [
            "lint-fixable",
            "lint-manual",
            "type-error",
            "security",
            "test-fail",
            "coverage-low",
        ]
        for kind in kinds:
            issue = Issue(kind=kind, file="f.py", line=1, message="msg", autofixable=False)
            assert issue.kind == kind

    def test_issue_unicode_filename(self):
        """Test Issue handles unicode filenames."""
        issue = Issue(
            kind="lint-fixable",
            file="тест.py",
            line=1,
            message="error",
            autofixable=True,
        )
        assert issue.file == "тест.py"

    def test_issue_long_message(self):
        """Test Issue handles long messages."""
        long_msg = "x" * 10000
        issue = Issue(
            kind="type-error",
            file="f.py",
            line=1,
            message=long_msg,
            autofixable=False,
        )
        assert issue.message == long_msg

    def test_issue_zero_line(self):
        """Test Issue handles line=0."""
        issue = Issue(kind="security", file="f.py", line=0, message="error", autofixable=False)
        assert issue.line == 0


class TestSectionSummary:
    """Test SectionSummary model."""

    def test_section_summary_creation(self):
        """Test SectionSummary creation."""
        summary = SectionSummary(
            name="Lint / Style",
            autofixable_count=5,
            manual_count=2,
            notes=["All issues detected"],
            ci_blocking=True,
        )
        assert summary.name == "Lint / Style"
        assert summary.autofixable_count == 5
        assert summary.manual_count == 2
        assert summary.ci_blocking is True

    def test_section_summary_empty(self):
        """Test SectionSummary with no issues."""
        summary = SectionSummary(
            name="Types",
            autofixable_count=0,
            manual_count=0,
            notes=[],
            ci_blocking=False,
        )
        assert summary.autofixable_count == 0
        assert summary.manual_count == 0

    def test_section_summary_multiple_notes(self):
        """Test SectionSummary with multiple notes."""
        notes = ["Note 1", "Note 2", "Note 3"]
        summary = SectionSummary(
            name="Security",
            autofixable_count=0,
            manual_count=3,
            notes=notes,
            ci_blocking=True,
        )
        assert len(summary.notes) == 3
        assert "Note 1" in summary.notes


class TestScanResult:
    """Test ScanResult model and aggregation."""

    def test_scan_result_creation(self):
        """Test ScanResult creation."""
        result = ScanResult()
        assert result.sections == []
        assert result.issues == []
        assert result.total_autofixable == 0
        assert result.total_manual == 0
        assert result.commit_safe is False

    def test_scan_result_with_sections(self):
        """Test ScanResult with multiple sections."""
        sections = [
            SectionSummary(
                name="Lint", autofixable_count=1, manual_count=0, notes=[], ci_blocking=False
            ),
            SectionSummary(
                name="Types", autofixable_count=0, manual_count=2, notes=[], ci_blocking=True
            ),
        ]
        result = ScanResult(
            sections=sections,
            total_autofixable=1,
            total_manual=2,
            commit_safe=False,
        )
        assert len(result.sections) == 2

    def test_scan_result_with_issues(self):
        """Test ScanResult with issues."""
        issues = [
            Issue(
                kind="lint-fixable",
                file="a.py",
                line=1,
                message="error",
                autofixable=True,
            ),
            Issue(
                kind="type-error",
                file="b.py",
                line=10,
                message="type error",
                autofixable=False,
            ),
        ]
        result = ScanResult(issues=issues)
        assert len(result.issues) == 2

    def test_scan_result_coverage_fields(self):
        """Test ScanResult coverage fields."""
        result = ScanResult(
            coverage_pct=85.5,
            coverage_required=80.0,
        )
        assert result.coverage_pct == 85.5
        assert result.coverage_required == 80.0

    def test_scan_result_as_dict(self):
        """Test ScanResult.as_dict() conversion."""
        result = ScanResult(
            gate_name="pre-commit",
            files_scanned=42,
            commit_safe=True,
            coverage_pct=90.0,
            coverage_required=80.0,
            total_autofixable=2,
            total_manual=1,
        )
        result_dict = result.as_dict()

        assert isinstance(result_dict, dict)
        assert result_dict["gate_name"] == "pre-commit"
        assert result_dict["files_scanned"] == 42
        assert result_dict["commit_safe"] is True
        assert result_dict["coverage_pct"] == 90.0

    def test_scan_result_as_dict_with_autofix_cmds(self):
        """Test ScanResult.as_dict() includes autofix commands."""
        result = ScanResult()
        result.autofix_cmds = ["black .", "ruff check --fix ."]
        result_dict = result.as_dict()

        assert "autofix_cmds" in result_dict
        assert len(result_dict["autofix_cmds"]) == 2

    def test_scan_result_as_dict_with_security_fields(self):
        """Test ScanResult.as_dict() includes security fields."""
        result = ScanResult()
        result.high_risk_unreviewed = 5
        result.known_risky_but_baselined = 3
        result.high_risk_unreviewed_files = ["sec1.py", "sec2.py"]
        result.known_risky_but_baselined_files = ["base1.py"]

        result_dict = result.as_dict()

        assert result_dict["high_risk_unreviewed"] == 5
        assert result_dict["known_risky_but_baselined"] == 3


class TestCoverageThreshold:
    """Test coverage threshold constant."""

    def test_coverage_required_default_value(self):
        """Test default coverage threshold value."""
        assert COVERAGE_REQUIRED_DEFAULT == 80.0

    def test_coverage_required_is_float(self):
        """Test coverage threshold is float type."""
        assert isinstance(COVERAGE_REQUIRED_DEFAULT, float)


class TestScannerIntegration:
    """Integration tests combining scanner components."""

    def test_full_scan_result_workflow(self):
        """Test complete scan result workflow."""
        # Create issues
        issues = [
            Issue(
                kind="lint-fixable",
                file="src/main.py",
                line=10,
                message="unused import",
                autofixable=True,
            ),
            Issue(
                kind="type-error",
                file="src/types.py",
                line=5,
                message="incompatible types",
                autofixable=False,
            ),
        ]

        # Create sections
        sections = [
            SectionSummary(
                name="Lint / Style",
                autofixable_count=1,
                manual_count=0,
                notes=["1 autofixable issue"],
                ci_blocking=False,
            ),
            SectionSummary(
                name="Types",
                autofixable_count=0,
                manual_count=1,
                notes=["1 type error"],
                ci_blocking=True,
            ),
        ]

        # Create result
        result = ScanResult(
            sections=sections,
            issues=issues,
            total_autofixable=1,
            total_manual=1,
            commit_safe=False,
            coverage_pct=75.0,
            coverage_required=80.0,
            files_scanned=150,
            gate_name="pre-push",
        )

        # Verify structure
        assert len(result.sections) == 2
        assert len(result.issues) == 2
        assert result.total_autofixable == 1
        assert result.total_manual == 1
        assert result.commit_safe is False

        # Convert to dict
        result_dict = result.as_dict()
        assert result_dict["gate_name"] == "pre-push"
        assert result_dict["files_scanned"] == 150


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_scan_result_missing_optional_fields(self):
        """Test ScanResult when optional fields are missing."""
        result = ScanResult()
        # getattr should handle missing fields gracefully
        result_dict = result.as_dict()
        assert "autofix_cmds" in result_dict

    def test_issue_with_special_characters(self):
        """Test Issue with special characters in message."""
        issue = Issue(
            kind="security",
            file="<stdin>",
            line=None,
            message="SQL injection: `'; DROP TABLE users; --`",
            autofixable=False,
        )
        assert "DROP TABLE" in issue.message

    def test_section_summary_high_counts(self):
        """Test SectionSummary with high issue counts."""
        summary = SectionSummary(
            name="Huge Section",
            autofixable_count=1000,
            manual_count=5000,
            notes=[f"Issue {i}" for i in range(100)],
            ci_blocking=True,
        )
        assert summary.autofixable_count == 1000
        assert summary.manual_count == 5000
        assert len(summary.notes) == 100
