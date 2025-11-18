from __future__ import annotations

import pathlib
import re
from typing import Optional

_MISSING_MOD_RE = re.compile(r"No module named ['\"](?P<mod>[^'\"]+)['\"]")


def _read_pyproject(root: pathlib.Path) -> Optional[str]:
    path = root / "pyproject.toml"
    if not path.is_file():
        return None
    return path.read_text(encoding="utf8")


def suggest_dependency_fix(
    *,
    root: pathlib.Path,
    stderr: str,
    cmd: str,
) -> None:
    """
    Inspect stderr for common missing dependency patterns and print an advisory.

    This is *read-only* and cannot break anything; it only prints suggestions.
    """
    m = _MISSING_MOD_RE.search(stderr)
    if not m:
        return

    missing = m.group("mod")
    # Common noise modules we don't want to nag about.
    if missing in {"__main__", "tests"}:
        return

    pyproj = _read_pyproject(root)
    already_present = False
    if pyproj is not None:
        # Very simple check: see if the module name shows up in dependencies.
        # This is intentionally dumb-but-safe; it's just a hint.
        if f'"{missing}"' in pyproj or f"{missing}>=" in pyproj:
            already_present = True

    print("\n[FirstTry] Dependency advisory")
    print("------------------------------")
    print(f"Command that failed: {cmd!r}")
    print(f"Detected missing module: {missing!r}")
    print()
    print("Reason:")
    print(f"  - Python reported 'No module named {missing}'.")
    print("  - This likely means a runtime dependency is not installed or not")
    print("    declared in your project dependencies.")
    print()

    if pyproj is None:
        print("Suggested fix:")
        print("  - Add the missing dependency to your environment or project config.")
        print("  - For Python projects using pyproject.toml, declare it under")
        print("    [project.dependencies].")
    elif already_present:
        print("Suggested fix:")
        print("  - The dependency seems referenced in pyproject.toml already.")
        print("  - Ensure your CI and local env run the same install command, e.g.:")
        print("      python -m pip install -e .[ci]")
    else:
        print("Suggested fix:")
        print("  - Add this to your pyproject.toml (adjust version as needed):")
        print()
        print("      [project]")
        print("      dependencies = [")
        print(f'          "{missing}>=0.0.0",')
        print("          # ... existing deps ...")
        print("      ]")
        print()
        print("  - Then re-run: firsttry gate dev")

    print()
