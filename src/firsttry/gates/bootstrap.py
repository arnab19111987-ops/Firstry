from __future__ import annotations

import os
import pathlib
from typing import Optional

from .ci_discovery import discover_and_write_ci_mirror

DEFAULT_POLICY_TOML = """\
[gates.dev]
tags = ["dev_gate"]

[gates.merge]
tags = ["dev_gate", "merge_gate"]

[gates.release]
tags = ["merge_gate", "release_gate"]
require_cloud_only_success_in_ci = true
"""


def ensure_policy_exists(
    root: Optional[pathlib.Path] = None,
    filename: str = ".firsttry/policy.toml",
) -> pathlib.Path:
    root = root or pathlib.Path(os.getcwd())
    path = root / filename
    if path.is_file():
        return path

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(DEFAULT_POLICY_TOML, encoding="utf8")
    return path


def ensure_ci_mirror_exists(
    root: Optional[pathlib.Path] = None,
    filename: str = ".firsttry/ci_mirror.toml",
) -> pathlib.Path:
    """
    Ensure CI mirror file exists.

    If missing, try to discover from GitHub Actions workflows.
    If discovery finds nothing, create an empty but valid skeleton.
    """
    root = root or pathlib.Path(os.getcwd())
    path = root / filename
    if path.is_file():
        return path

    # Try discovery
    try:
        created = discover_and_write_ci_mirror(root=root, filename=filename, overwrite=False)
        # If discovery produced an empty/placeholder file, fall back to skeleton
        try:
            txt = created.read_text(encoding="utf8")
        except Exception:
            txt = ""
        if "[jobs." not in txt and "[plans." not in txt:
            # Write minimal skeleton instead
            pass
        else:
            return created
    except FileExistsError:
        # raced with something else; just return
        return path
    except RuntimeError:
        # YAML not available; fall back to minimal skeleton
        pass
    except Exception:
        # Discovery failed for some reason; fall back to skeleton
        pass

    # minimal skeleton
    skeleton = """\
# Auto-generated minimal CI mirror by FirstTry.
# You can edit this file to tune which jobs map to which gates.

[jobs.example]
workflow = "ci.yml"
job_name = "tests"
tags = ["dev_gate", "merge_gate"]
plan = "example_plan"

[plans.example_plan]
[[plans.example_plan.steps]]
id = "example"
run = "echo 'Configure .firsttry/ci_mirror.toml to mirror your CI'"
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(skeleton, encoding="utf8")
    return path
