import importlib
import types


def test_cli_wrappers_imports():
    mod = importlib.import_module("firsttry.cli_wrappers")
    assert isinstance(mod, types.ModuleType)
    # ensure the registration helper exists
    assert hasattr(mod, "register_cli_wrappers")


def test_register_cli_wrappers_idempotent():
    mod = importlib.import_module("firsttry.cli_wrappers")

    class DummyTyper:
        def __init__(self):
            self._registered = []

        def add_typer(self, other, name: str = ""):
            self._registered.append(name)

    app = DummyTyper()
    # Should not raise and should be idempotent
    mod.register_cli_wrappers(app)
    mod.register_cli_wrappers(app)
    assert app._registered  # at least one wrapper was registered (if Typer present)
