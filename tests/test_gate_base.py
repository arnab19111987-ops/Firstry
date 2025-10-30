from firsttry.gates.base import Gate


class PyGate(Gate):
    gate_id = "py"
    patterns = ("*.py",)


def test_gate_runs_for_matching_file():
    g = PyGate()
    assert g.should_run_for(["foo.py"]) is True


def test_gate_skips_for_non_matching_file():
    g = PyGate()
    assert g.should_run_for(["README.md"]) is False
