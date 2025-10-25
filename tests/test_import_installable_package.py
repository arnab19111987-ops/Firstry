import shutil
import sys
import types
from pathlib import Path


def test_import_firsttry_as_if_installed(tmp_path, monkeypatch):
    """
    Simulate a real install by copying the canonical firsttry/ package
    into a fake site-packages dir, then importing it with ONLY that dir
    on sys.path. This makes sure the package is self-contained.
    """

    repo_root = Path.cwd()
    src_pkg = repo_root / "firsttry"
    assert src_pkg.is_dir(), "expected ./firsttry to be the canonical package"

    fake_site = tmp_path / "site-packages"
    shutil.copytree(src_pkg, fake_site / "firsttry")

    # prepend fake_site to sys.path so import firsttry resolves to copied code
    monkeypatch.syspath_prepend(str(fake_site))
    # ensure we import a fresh module, not a cached one from earlier tests
    sys.modules.pop("firsttry", None)
    # also clear common submodules if any
    for sub in list(sys.modules.keys()):
        if sub.startswith("firsttry."):
            sys.modules.pop(sub, None)

    mod = __import__("firsttry")
    assert isinstance(mod, types.ModuleType)
    assert hasattr(mod, "__file__")

    # sanity check: importing known public modules works
    __import__("firsttry.cli")
    __import__("firsttry.doctor")
    __import__("firsttry.license")

    # confirm we are not accidentally depending on tools/ alias tricks
    assert str(fake_site) in mod.__file__
