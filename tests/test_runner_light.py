from pathlib import Path

from firsttry.runner_light import run_profile


def test_runner_light_runs_fast_profile(tmp_path):
    # run in empty dir — most gates will skip
    code = run_profile(tmp_path, "fast", since_ref=None)
    assert code in (0, 1)
