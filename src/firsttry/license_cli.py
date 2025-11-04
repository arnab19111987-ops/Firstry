from __future__ import annotations

import argparse


def cmd_activate(args: argparse.Namespace) -> int:
    """Activate and persist a license key.

    Usage: firsttry license activate <KEY> [--scope repo|user]
    """
    try:
        from .license_loader import save_license_key
    except Exception as e:
        print(f"license: failed to load license saver: {e}")
        return 2

    key = getattr(args, "key", None)
    if not key:
        key = input("Enter license key: ")

    scope = getattr(args, "scope", "user")
    try:
        save_license_key(key.strip(), scope=scope)
        print(f"✅ License activated ({scope})")
        print("Tip: you can also set FIRSTTRY_LICENSE_KEY in the environment for a one-off run.")
        return 0
    except Exception as e:
        print(f"Failed to save license key: {e}")
        return 2


def cmd_show(args: argparse.Namespace) -> int:
    """Show the current license key (env → repo → user)."""
    try:
        from .license_loader import repo_license_path, user_license_path
    except Exception as e:
        print(f"license: failed to load license loader: {e}")
        return 2

    scope = getattr(args, "scope", "all")

    if scope in ("env", "all"):
        import os

        v = os.getenv("FIRSTTRY_LICENSE_KEY")
        if v:
            print("env:", v)
            if scope == "env":
                return 0

    if scope in ("repo", "all"):
        rp = repo_license_path()
        if rp.exists():
            print("repo:", rp.read_text(encoding="utf-8").strip())
            if scope == "repo":
                return 0

    if scope in ("user", "all"):
        up = user_license_path()
        if up.exists():
            print("user:", up.read_text(encoding="utf-8").strip())
            return 0

    print("No license key found (env, repo, or user scope).")
    return 2


def cmd_deactivate(args: argparse.Namespace) -> int:
    """Remove persisted license key(s)."""
    try:
        from .license_loader import remove_license_key, repo_license_path, user_license_path
    except Exception as e:
        print(f"license: failed to load license loader: {e}")
        return 2

    scope = getattr(args, "scope", "all")

    removed = False
    if scope in ("repo", "all"):
        rp = repo_license_path()
        if rp.exists():
            remove_license_key(scope="repo")
            print(f"Removed repo license at {rp}")
            removed = True

    if scope in ("user", "all"):
        up = user_license_path()
        if up.exists():
            remove_license_key(scope="user")
            print(f"Removed user license at {up}")
            removed = True

    if not removed:
        print("No persisted license keys found for the requested scope.")
        return 2

    return 0


__all__ = ["cmd_activate", "cmd_show", "cmd_deactivate"]
