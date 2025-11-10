#!/usr/bin/env python3
"""
Generate gate documentation automatically from code inspection.

This script scans the firsttry.gates package to find all gate classes
and automatically generates comprehensive documentation in Markdown format.
"""

import importlib
import inspect
import pkgutil
import sys
from pathlib import Path


def find_gate_classes():
    """
    Discover all gate classes by introspecting the firsttry.gates package.

    Returns:
        List of tuples: (gate_id, module_path, description, class_name, full_module)
    """
    rows = []

    try:
        # Add src to path so we can import firsttry
        src_path = Path(__file__).parent.parent / "src"
        if str(src_path) not in sys.path:
            sys.path.insert(0, str(src_path))

        pkg_name = "firsttry.gates"
        pkg = importlib.import_module(pkg_name)

        # Iterate through all modules in the gates package
        for _, module_name, _ in pkgutil.iter_modules(pkg.__path__):
            try:
                full_module_name = f"{pkg_name}.{module_name}"
                module = importlib.import_module(full_module_name)

                # Look for classes that have a gate_id attribute
                for name, cls in inspect.getmembers(module, inspect.isclass):
                    if (
                        hasattr(cls, "gate_id")
                        and cls.gate_id
                        and cls.__module__
                        == full_module_name  # Only classes defined in this module
                        and name != "Gate"
                    ):  # Skip base Gate class
                        # Extract description from docstring
                        doc = cls.__doc__ or ""
                        description = (
                            doc.strip().split("\n")[0] if doc.strip() else "No description"
                        )

                        # Clean up description
                        if description.endswith("."):
                            description = description[:-1]

                        module_file = f"src/firsttry/gates/{module_name}.py"

                        rows.append((cls.gate_id, module_file, description, name, full_module_name))

            except ImportError as e:
                print(f"Warning: Could not import {full_module_name}: {e}", file=sys.stderr)
                continue

    except ImportError as e:
        print(f"Error: Could not import firsttry.gates package: {e}", file=sys.stderr)
        return []

    # Sort by gate_id for consistent output
    rows.sort(key=lambda x: x[0])
    return rows


def generate_gate_documentation(output_path: Path):
    """
    Generate comprehensive gate documentation.

    Args:
        output_path: Path where to write the documentation
    """
    gate_classes = find_gate_classes()

    if not gate_classes:
        print("Warning: No gate classes found. Documentation may be incomplete.", file=sys.stderr)

    # Generate markdown content
    content = [
        "# Gate Registry & Configuration Guide",
        "",
        "This document is automatically generated from the FirstTry codebase.",
        "It provides a complete reference of all available gates and their configurations.",
        "",
        "## Available Gates",
        "",
        "| Gate ID | Module | Description | Class |",
        "|---------|--------|-------------|-------|",
    ]

    for gate_id, module_path, description, class_name, full_module in gate_classes:
        # Escape pipe characters in description for Markdown table
        safe_description = description.replace("|", "\\|")
        content.append(f"| `{gate_id}` | `{module_path}` | {safe_description} | `{class_name}` |")

    content.extend(
        [
            "",
            "## Gate Descriptions",
            "",
        ]
    )

    # Add detailed descriptions for each gate
    for gate_id, module_path, description, class_name, full_module in gate_classes:
        content.extend(
            [
                f"### `{gate_id}` - {class_name}",
                "",
                f"**Module:** `{module_path}`",
                f"**Description:** {description}",
                "",
            ]
        )

        # Try to get more detailed information from the class
        try:
            module = importlib.import_module(full_module)
            cls = getattr(module, class_name)

            # Get full docstring if available
            if cls.__doc__:
                full_doc = cls.__doc__.strip()
                if len(full_doc) > len(description):
                    content.extend(
                        [
                            "**Details:**",
                            "",
                            full_doc,
                            "",
                        ]
                    )

            # Check for configuration attributes
            config_attrs = []
            for attr_name in dir(cls):
                if not attr_name.startswith("_") and attr_name.isupper():
                    try:
                        attr_value = getattr(cls, attr_name)
                        if isinstance(attr_value, (str, int, bool, list, dict)):
                            config_attrs.append(f"- `{attr_name}`: `{attr_value}`")
                    except Exception:
                        # Ignore attribute access errors (e.g., descriptors that raise)
                        pass

            if config_attrs:
                content.extend(
                    [
                        "**Configuration:**",
                        "",
                    ]
                    + config_attrs
                    + [""]
                )

        except Exception as e:
            print(f"Warning: Could not introspect {class_name}: {e}", file=sys.stderr)

    content.extend(
        [
            "## Usage Examples",
            "",
            "### Basic Configuration",
            "",
            "```yaml",
            "# .firsttry.yml",
            "gates:",
            "  pre-commit:",
        ]
    )

    # Add example configuration using first few gates
    for gate_id, _, _, _, _ in gate_classes[:5]:
        content.append(f"    - {gate_id}")

    content.extend(
        [
            "  pre-push:",
            "    - lint",
            "    - types",
            "    - tests",
            "```",
            "",
            "### Command Line Usage",
            "",
            "```bash",
            "# Run specific gate",
            f"firsttry run --gate {gate_classes[0][0] if gate_classes else 'lint'}",
            "",
            "# Run multiple gates",
            "firsttry run --gate pre-commit",
            "",
            "# List available gates",
            "firsttry gates",
            "```",
            "",
            "---",
            "",
            f"*Documentation generated automatically from {len(gate_classes)} gate classes*",
            f"*Last updated: {__file__} inspection*",
        ]
    )

    # Write the documentation
    output_path.write_text("\n".join(content) + "\n")
    print(f"Generated gate documentation: {output_path}")
    print(f"Found {len(gate_classes)} gate classes")


def main():
    """Main entry point."""
    # Default output location
    docs_dir = Path(__file__).parent.parent / "docs"
    docs_dir.mkdir(exist_ok=True)

    output_path = docs_dir / "Gates.md"

    try:
        generate_gate_documentation(output_path)
        print(f"✅ Gate documentation written to: {output_path}")
    except Exception as e:
        print(f"❌ Error generating documentation: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
