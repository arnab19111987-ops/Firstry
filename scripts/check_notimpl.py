#!/usr/bin/env python3
"""Check for NotImplementedError outside abstract base classes."""

import ast
import sys
from pathlib import Path


def check_file(filepath):
    """Check a single file for stray NotImplementedError."""
    try:
        with open(filepath, encoding="utf-8", errors="ignore") as f:
            code = f.read()
        tree = ast.parse(code, filepath)
    except (SyntaxError, ValueError):
        return []

    # Check if file uses ABC
    uses_abc = any(
        isinstance(n, ast.ImportFrom) and (n.module in ("abc", "collections.abc"))
        for n in ast.walk(tree)
    )

    if uses_abc:
        return []  # File properly uses ABC, so NotImplementedError is OK

    # Look for NotImplementedError raises
    issues = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Raise):
            if isinstance(node.exc, ast.Call):
                if (
                    isinstance(node.exc.func, ast.Name)
                    and node.exc.func.id == "NotImplementedError"
                ):
                    issues.append(f"{filepath}:{node.lineno}: NotImplementedError outside ABC")
            elif isinstance(node.exc, ast.Name) and node.exc.id == "NotImplementedError":
                issues.append(f"{filepath}:{node.lineno}: NotImplementedError outside ABC")

    return issues


def main():
    """Main entry point."""
    issues = []

    # Get all Python files
    for pyfile in Path("src").rglob("*.py"):
        issues.extend(check_file(str(pyfile)))

    if issues:
        print("❌ Stray NotImplementedError (use ABC for abstract classes):")
        for issue in issues:
            print(f"  {issue}")
        sys.exit(1)
    else:
        print("✅ No stray NotImplementedError")
        sys.exit(0)


if __name__ == "__main__":
    main()
