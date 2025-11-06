#!/usr/bin/env python3
"""
Demo: Simplified FirstTry CLI - One Command, One Intent
Shows the new clean CLI interface with hidden complexity
"""

import subprocess
from pathlib import Path


def run_command(cmd, description):
    """Run a command and display results"""
    print(f"\n🧪 {description}")
    print("=" * 60)
    print(f"$ {cmd}")
    print("-" * 60)

    try:
        result = subprocess.run(
            cmd.split(), capture_output=True, text=True, cwd=Path(__file__).parent
        )

        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)

        return result.returncode == 0
    except Exception as e:
        print(f"Error: {e}")
        return False


def main():
    """Demo the simplified CLI interface"""
    print("🚀 FirstTry Simplified CLI Demo")
    print("=" * 60)
    print("New mental model: One command, one intent")
    print()
    print("Available modes:")
    print("  firsttry run        → auto, fast-enough (default)")
    print("  firsttry run fast   → only fast/local checks (sub-30s)")
    print("  firsttry run full   → everything for this repo")
    print("  firsttry run ci     → do what CI does")
    print("  firsttry run config → use your firsttry.toml")
    print("  firsttry run teams  → team/heavy version")
    print()
    print("Shortcuts:")
    print("  firsttry run q      → fast (quick)")
    print("  firsttry run c      → ci")
    print("  firsttry run t      → teams")
    print()

    # Demo 1: Help shows clean interface
    run_command("python -m firsttry run --help", "Clean help interface")

    # Demo 2: Default mode (auto)
    run_command("python -m firsttry run", "Default mode: auto (clean output)")

    # Demo 3: Fast mode
    run_command("python -m firsttry run fast", "Fast mode: sub-30s target")

    # Demo 4: Shortcut alias
    run_command("python -m firsttry run q", "Shortcut: q = fast")

    # Demo 5: Debug phases (shows internal buckets)
    run_command("python -m firsttry run fast --debug-phases", "Debug mode: shows phase buckets")

    print("\n🎯 CLI Simplification Summary")
    print("=" * 60)
    print("✅ BEFORE: Complex flags")
    print("   firsttry run --source detect --tier developer --profile fast")
    print()
    print("✅ AFTER: Simple mode")
    print("   firsttry run fast")
    print()
    print("Key improvements:")
    print("  • Single positional argument instead of 3 flags")
    print("  • Intuitive mode names aligned with user intent")
    print("  • Hidden phase output (FAST/MUTATING/SLOW buckets)")
    print("  • Backward compatibility preserved (old flags still work)")
    print("  • Shell aliases for power users (q, c, t)")
    print("  • Debug flag for troubleshooting (--debug-phases)")
    print()
    print("Users now only need to learn 3 commands:")
    print("  1. firsttry run       (for daily development)")
    print("  2. firsttry run fast  (when in a hurry)")
    print("  3. firsttry run ci    (to match CI exactly)")


if __name__ == "__main__":
    main()
