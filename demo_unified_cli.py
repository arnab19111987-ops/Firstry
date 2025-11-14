#!/usr/bin/env python3
"""
Demonstration of the new unified FirstTry CLI interface.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from firsttry.cli import main


def demo_unified_cli():
    print("🚀 FirstTry Unified CLI Demo")
    print("=" * 40)

    print("\n1️⃣ Help command:")
    print("   > firsttry --help")
    try:
        main(["--help"])
    except SystemExit:
        pass

    print("\n2️⃣ Status command:")
    print("   > firsttry status")
    try:
        main(["status"])
    except SystemExit:
        pass

    print("\n3️⃣ Setup command:")
    print("   > firsttry setup")
    try:
        main(["setup"])
    except SystemExit:
        pass

    print("\n4️⃣ Available commands:")
    print("   • firsttry run            # detect → plan → run → report")
    print("   • firsttry fix            # run only autofix-capable steps")
    print("   • firsttry setup          # create .firsttry.yml, detect langs")
    print("   • firsttry status         # show last run + detected langs")
    print("   • ft run                  # short form (same as firsttry)")

    print("\n✨ Single binary, clean interface!")
    print("   No more 'pipeline vs enhanced vs stable' confusion.")
    print("   All engines work together internally.")


if __name__ == "__main__":
    demo_unified_cli()
