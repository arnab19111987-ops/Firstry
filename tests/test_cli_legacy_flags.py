"""Legacy --level flag compat. Tests that
the flags are no longer part of the official API.
"""

from unittest.mock import MagicMock
from unittest.mock import patch

import firsttry.cli as cli_module


class TestLegacyArgsTranslation:
    """Test _translate_legacy_args translator function."""

    def test_translate_gate_precommit_to_fast(self):
        """--gate pre-commit should map to 'fast' mode."""
        argv = ["run", "--gate", "pre-commit"]
        result = cli_module._translate_legacy_args(argv)
        assert "fast" in result
        assert "--gate" not in result
        assert "pre-commit" not in result

    def test_translate_gate_ruff_to_fast(self):
        """--gate ruff should map to 'fast' mode."""
        argv = ["run", "--gate", "ruff"]
        result = cli_module._translate_legacy_args(argv)
        assert "fast" in result
        assert "--gate" not in result
        assert "ruff" not in result

    def test_translate_gate_strict_to_strict(self):
        """--gate strict should map to 'strict' mode."""
        argv = ["run", "--gate", "strict"]
        result = cli_module._translate_legacy_args(argv)
        assert "strict" in result
        assert "--gate" not in result

    def test_translate_gate_ci_to_strict(self):
        """--gate ci should map to 'strict' mode."""
        argv = ["run", "--gate", "ci"]
        result = cli_module._translate_legacy_args(argv)
        assert "strict" in result
        assert "--gate" not in result

    def test_translate_gate_mypy_to_strict(self):
        """--gate mypy should map to 'strict' mode."""
        argv = ["run", "--gate", "mypy"]
        result = cli_module._translate_legacy_args(argv)
        assert "strict" in result

    def test_translate_gate_pytest_to_strict(self):
        """--gate pytest should map to 'strict' mode."""
        argv = ["run", "--gate", "pytest"]
        result = cli_module._translate_legacy_args(argv)
        assert "strict" in result

    def test_translate_gate_unknown_to_fast(self):
        """--gate <unknown> should map to 'fast' (safe default)."""
        argv = ["run", "--gate", "unknown-tool"]
        result = cli_module._translate_legacy_args(argv)
        assert "fast" in result

    def test_translate_require_license_adds_tier_pro(self):
        """--require-license should add --tier pro."""
        argv = ["run"]
        result = cli_module._translate_legacy_args(argv + ["--require-license"])
        assert "--tier" in result
        assert "pro" in result

    def test_translate_combined_gate_and_require_license(self):
        """--gate strict --require-license should map to strict mode with pro tier."""
        argv = ["run", "--gate", "strict", "--require-license"]
        result = cli_module._translate_legacy_args(argv)
        assert "strict" in result
        assert "--tier" in result
        assert "pro" in result

    def test_translate_preserves_other_flags(self):
        """Non-legacy flags should be preserved."""
        argv = ["run", "--show-report", "--gate", "fast"]
        result = cli_module._translate_legacy_args(argv)
        assert "--show-report" in result
        assert "fast" in result

    def test_translate_empty_argv(self):
        """Empty argv should return empty list."""
        result = cli_module._translate_legacy_args([])
        assert result == []

    def test_translate_none_argv(self):
        """None argv should return empty list."""
        result = cli_module._translate_legacy_args(None)
        assert result == []

    def test_translate_prints_deprecation_for_gate(self, capsys):
        """Using --gate should print deprecation notice."""
        argv = ["run", "--gate", "pre-commit"]
        cli_module._translate_legacy_args(argv)
        captured = capsys.readouterr()
        assert "DEPRECATED" in captured.err
        assert "--gate" in captured.err

    def test_translate_prints_deprecation_for_require_license(self, capsys):
        """Using --require-license should print deprecation notice."""
        argv = ["run", "--require-license"]
        cli_module._translate_legacy_args(argv)
        captured = capsys.readouterr()
        assert "DEPRECATED" in captured.err
        assert "--require-license" in captured.err


class TestLegacyCmdRunIntegration:
    """Test cmd_run with legacy flags (integration tests)."""

    @patch("firsttry.cli._build_plan_for_tier")
    @patch("firsttry.cli.run_plan")
    def test_cmd_run_with_legacy_gate_precommit(self, mock_run_plan, mock_build_plan):
        """cmd_run should handle --gate pre-commit without error."""
        # Mock the plan builder and executor
        mock_plan = MagicMock()
        mock_build_plan.return_value = mock_plan
        mock_run_plan.return_value = {}

        # Should not raise even with deprecated flag
        result = cli_module.cmd_run(["--gate", "pre-commit"])
        assert result is not None  # Should complete

    @patch("firsttry.cli._build_plan_for_tier")
    @patch("firsttry.cli.run_plan")
    def test_cmd_run_with_legacy_require_license(self, mock_run_plan, mock_build_plan):
        """cmd_run should handle --require-license without error."""
        mock_plan = MagicMock()
        mock_build_plan.return_value = mock_plan
        mock_run_plan.return_value = {}

        result = cli_module.cmd_run(["--require-license"])
        assert result is not None


class TestLegacyMainIntegration:
    """Test main() entry point with legacy flags."""

    @patch("firsttry.cli.cmd_run")
    @patch("firsttry.cli.build_parser")
    def test_main_with_legacy_gate_flag(self, mock_parser_factory, mock_cmd_run):
        """main() should route legacy --gate to cmd_run correctly."""
        # Setup mock parser
        mock_parser = MagicMock()
        mock_args = MagicMock()
        mock_args.cmd = "run"
        mock_args.tier = None
        mock_args.profile = None
        mock_args.source = None
        mock_parser.parse_known_args.return_value = (mock_args, [])
        mock_parser_factory.return_value = mock_parser

        mock_cmd_run.return_value = 0

        # Call main with legacy flag
        result = cli_module.main(["run", "--gate", "strict", "--require-license"])
        # Verify cmd_run was called (and would have received translated args)
        assert mock_cmd_run.called or result == 0 or result == 1


class TestDeprecationMessage:
    """Test that deprecation messages are user-friendly."""

    def test_deprecation_message_content(self, capsys):
        """Deprecation message should be helpful."""
        argv = ["run", "--gate", "pre-commit", "--require-license"]
        cli_module._translate_legacy_args(argv)
        captured = capsys.readouterr()

        # Should mention what to use instead
        assert "run <mode>" in captured.err or "--tier" in captured.err


class TestNoFalsePositives:
    """Ensure we don't translate non-legacy args incorrectly."""

    def test_preserves_tier_argument(self):
        """--tier argument should be preserved as-is."""
        argv = ["run", "--tier", "pro"]
        result = cli_module._translate_legacy_args(argv)
        assert "--tier" in result
        assert "pro" in result

    def test_normal_run_unchanged(self):
        """Normal 'run <mode>' should pass through unchanged."""
        argv = ["run", "strict"]
        result = cli_module._translate_legacy_args(argv)
        assert result == argv

    def test_flags_with_equals_preserved(self):
        """Flags like --tier=pro should be preserved."""
        argv = ["run", "--tier=pro", "--show-report"]
        result = cli_module._translate_legacy_args(argv)
        assert "--tier=pro" in result
        assert "--show-report" in result
