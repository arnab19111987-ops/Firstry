#!/usr/bin/env python3
"""
Demo script for the new FirstTry pipeline system.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from firsttry.planner import build_plan
from firsttry.executor import execute_plan


def demo_pipeline():
    print("🚀 FirstTry Pipeline System Demo")
    print("=" * 40)

    # 1. Build plan
    plan = build_plan(".")
    print(f"📋 Detected languages: {', '.join(plan['languages'])}")
    print(f"📋 Pipeline steps: {len(plan['steps'])}")

    # Show the plan structure
    print("\n📝 Pipeline steps:")
    for step in plan["steps"]:
        autofix_info = f" (autofix: {len(step['autofix'])} commands)" if step["autofix"] else ""
        optional_info = " [optional]" if step["optional"] else ""
        print(f"  • {step['id']} ({step['lang']}){autofix_info}{optional_info}")

    # 2. Test with a minimal subset
    print("\n🔧 Testing first Python step...")
    py_steps = [s for s in plan["steps"] if s["lang"] == "python"][:1]
    if py_steps:
        test_plan = {"root": plan["root"], "languages": ["python"], "steps": py_steps}

        # Run without autofix first
        print("   Running without autofix...")
        report = execute_plan(test_plan, autofix=False, interactive_autofix=False)

        # Show summary
        step_result = report["summary"][0] if report["summary"] else None
        if step_result:
            status = "✅ PASSED" if step_result["ok"] else "❌ FAILED"
            print(f"   Result: {status}")
            if not step_result["ok"] and step_result.get("results"):
                failed_cmd = step_result["results"][-1]["cmd"]
                print(f"   Failed command: {failed_cmd}")

    print("\n✨ Pipeline system is working!")
    print("   Use: python -m firsttry.cli_pipelines run --autofix")


if __name__ == "__main__":
    demo_pipeline()
