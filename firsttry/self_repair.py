import importlib
import subprocess
import sys
from pathlib import Path


# These are the tools FirstTry depends on to judge repo health.
# Pin versions you trust in CI so that local == CI.
REQUIRED_PACKAGES = [
    "ruff==0.6.9",
    "mypy==1.13.0",
    "pytest==8.3.3",
    "coverage==7.6.4",
    "black==23.1.0",
    "click",
    "pyyaml",
]


def _have_module(mod_name: str) -> bool:
    """
    Return True if we can import this module.
    This DOESN'T guarantee exact version, just existence.
    """
    try:
        importlib.import_module(mod_name)
        return True
    except Exception:
        return False


def _pip_install(pkg: str) -> None:
    """
    Try to install/upgrade a package in the current interpreter environment.
    We do not hard fail here -- we try and continue.
    """
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", pkg],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except Exception:
        # We intentionally swallow, we'll report later.
        pass


def self_repair() -> None:
    """
    Ensure this environment has what FirstTry needs to run honest checks.

    Behavior:
    - For each REQUIRED_PACKAGES entry, if we can't import it, we attempt to pip install it.
    - We print minimal status so the user understands what's happening.
    - We don't raise if something can't be installed; the actual gate will still fail
      later and explain why (which is acceptable).
    """
    print("[firsttry] Verifying environment and tooling...")

    missing = []
    for pkg in REQUIRED_PACKAGES:
        mod_name = pkg.split("==")[0]
        if not _have_module(mod_name):
            missing.append(pkg)

    if not missing:
        print("[firsttry] ✅ Tooling ready.")
        return

    print("[firsttry] Installing missing tooling:")
    for pkg in missing:
        print(f"[firsttry]   - {pkg}")
        _pip_install(pkg)

    # After attempt, recheck
    still_missing = []
    for pkg in missing:
        mod_name = pkg.split("==")[0]
        if not _have_module(mod_name):
            still_missing.append(pkg)

    if still_missing:
        print("[firsttry] ⚠ Some tools could not be installed automatically:")
        for pkg in still_missing:
            print(f"[firsttry]   - {pkg}")
        print(
            "[firsttry] You may need to activate a virtualenv and re-run `firsttry init`."
        )
    else:
        print("[firsttry] ✅ All required tooling installed.")


def ensure_dev_support_files():
    """
    Make sure the repo has the basic support files FirstTry expects:
    - requirements-dev.txt
    - Makefile with `check` and `ruff-fix`
    This is used by `firsttry init`.
    """
    # 1. requirements-dev.txt
    req_path = Path("requirements-dev.txt")
    if not req_path.exists():
        req_path.write_text(
            "\n".join(
                [
                    "ruff==0.6.9",
                    "mypy==1.13.0",
                    "pytest==8.3.3",
                    "coverage==7.6.4",
                    "black==23.1.0",
                    "click",
                    "pyyaml",
                ]
            )
            + "\n"
        )
        print("[firsttry] wrote requirements-dev.txt")

    # 2. Makefile
    mk_path = Path("Makefile")
    if not mk_path.exists():
        mk_path.write_text(
            """\
.PHONY: check ruff-fix

check:
\t@echo "[firsttry] running full quality gate..."
\truff check .
\tmypy .
\tcoverage run -m pytest -q
\tcoverage report --fail-under=80

ruff-fix:
\truff check . --fix
\tblack .
"""
        )
        print("[firsttry] wrote Makefile with `check` and `ruff-fix` targets")
