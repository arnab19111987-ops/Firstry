# firsttry/setup.py
from pathlib import Path
from .detect import detect_language, deps_for_stacks
from .hooks import install_all_hooks, hooks_installed

DEFAULT_CONFIG_TEMPLATE = """# FirstTry config
version: 1
gates:
  pre-commit:
    - python-lint
    - python-format
    - python-imports
    - js-lint
  pre-push:
    - python-type
    - pytest
    - security
"""


def write_default_config(path: str = ".firsttry.yml"):
    cfg = Path(path)
    if not cfg.exists():
        cfg.write_text(DEFAULT_CONFIG_TEMPLATE)


def run_setup_interactive():
    stacks = detect_language()
    print(f"🔍 Detected project stacks: {', '.join(stacks)}")

    deps = deps_for_stacks(stacks)
    if deps:
        print("📦 Recommended tools for this repo:")
        for stack, tools in deps.items():
            if stack == "python":
                print(f"  - pip install {' '.join(tools)}")
            elif stack == "node":
                print(f"  - npm install -D {' '.join(tools)}")
            else:
                print(f"  - {stack}: {' '.join(tools)}")

    # write config
    write_default_config()
    print("✅ Created .firsttry.yml (or kept existing).")

    # install hooks
    if hooks_installed():
        print("✅ Git hooks already installed.")
    else:
        ans = (
            input("Install Git hooks (pre-commit, pre-push) now? [Y/n]: ")
            .strip()
            .lower()
        )
        if ans in ("", "y", "yes"):
            if install_all_hooks():
                print("✅ Git hooks installed.")
            else:
                print("⚠️ Could not install hooks (no .git/ ?).")
    print("🎉 Setup complete.")
