from __future__ import annotations

"""
LEGACY SHIM — preserved for historical imports only.

All configuration logic now lives in firsttry.config._core.

New code MUST use:

    from firsttry.config import Config, get_config, get_workflow_requires, get_s3_settings

This module only re-exports those functions and the Config dataclass
so that older imports keep working.
"""

from firsttry.config import Config
from firsttry.config import get_config
from firsttry.config import get_s3_settings
from firsttry.config import get_workflow_requires

__all__ = [
    "Config",
    "get_config",
    "get_workflow_requires",
    "get_s3_settings",
]

# Optional alias if any legacy path used this name
load_config = get_config
