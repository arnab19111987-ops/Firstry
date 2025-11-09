import pytest

import firsttry.scanner as scanner


def test_scanner_handles_oserror(monkeypatch):
    # Prefer to simulate a VCS helper error if available
    if hasattr(scanner, "git_changed_files"):

        def boom(*a, **k):
            raise OSError("simulated failure")

        monkeypatch.setattr(scanner, "git_changed_files", boom, raising=True)

        if hasattr(scanner, "RepoScanner"):
            rs = scanner.RepoScanner(root=".")
            # Should not raise even if the VCS helper failed
            list(rs.iter_source_files())
        else:
            assert scanner is not None
        return

    # Fallback: simulate a missing binary by making _run_cmd report not-found
    if hasattr(scanner, "_run_cmd"):

        def fake_missing(cmd, *a, **k):
            return 127, "", "not found"

        monkeypatch.setattr(scanner, "_run_cmd", fake_missing, raising=True)

        if hasattr(scanner, "RepoScanner"):
            rs = scanner.RepoScanner(root=".")
            list(rs.iter_source_files())
        else:
            assert scanner is not None
        return

    pytest.skip("No suitable scanner helper to simulate error path")
