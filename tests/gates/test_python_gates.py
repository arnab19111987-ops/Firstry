"""
Unit tests for Python-related gates.

Goal:
- Exercise python_lint/python_mypy/python_pytest gate call paths
  without running real tools.
"""

from unittest import mock

import pytest

from firsttry.gates import python_lint
from firsttry.gates import python_mypy
from firsttry.gates import python_pytest


class FakeProc:
    def __init__(self, returncode=0, stdout="ok", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


@pytest.mark.parametrize("gate_mod,gate_cls", [
    (python_lint, python_lint.PythonRuffGate),
    (python_mypy, python_mypy.PythonMypyGate),
    (python_pytest, python_pytest.PythonPytestGate),
])
def test_python_gates_success(gate_mod, gate_cls):
    """
    When the underlying subprocess returns returncode 0, the gate should succeed.
    """
    gate = gate_cls()
    with mock.patch.object(gate_mod, "subprocess") as mock_subproc:
        mock_subproc.run.return_value = FakeProc(returncode=0, stdout="ok")
        res = gate.run(project_root=None)
    assert getattr(res, "ok", True) is True


@pytest.mark.parametrize("gate_mod,gate_cls", [
    (python_lint, python_lint.PythonRuffGate),
    (python_mypy, python_mypy.PythonMypyGate),
    (python_pytest, python_pytest.PythonPytestGate),
])
def test_python_gates_failure(gate_mod, gate_cls):
    """
    When the underlying subprocess fails, gate should mark result as failed.
    """
    gate = gate_cls()
    with mock.patch.object(gate_mod, "subprocess") as mock_subproc:
        mock_subproc.run.return_value = FakeProc(returncode=1, stdout="err", stderr="err")
        res = gate.run(project_root=None)
    assert getattr(res, "ok", True) is False
