from types import SimpleNamespace


def run_ruff(*a, **k):
    return SimpleNamespace(
        ok=True, name="real-ruff", duration_s=0.1, stdout="", stderr="", cmd=()
    )


def run_black_check(*a, **k):
    return SimpleNamespace(
        ok=True, name="real-black", duration_s=0.1, stdout="", stderr="", cmd=()
    )


def run_mypy(*a, **k):
    return SimpleNamespace(
        ok=True, name="real-mypy", duration_s=0.1, stdout="", stderr="", cmd=()
    )
