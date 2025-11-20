"""
Smoke test for FirstTry pre-commit CLI wiring.
Ensures the pre-commit wrapper exists and is callable.
"""


def test_pre_commit_fast_gate_exists():
    from firsttry.cli import pre_commit_fast_gate

    assert callable(pre_commit_fast_gate)
    # Optionally, check it returns an int exit code
    rc = pre_commit_fast_gate()
    assert isinstance(rc, int)
    # Should not crash; rc==0 means all checks pass, rc==1 means some failed
    assert rc in (0, 1)
