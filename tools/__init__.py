"""Package marker for tools namespace so tests can import `tools.firsttry`.

This is intentionally minimal: real code lives in subpackages and is re-exported
by `tools.firsttry` wrapper.
"""

from __future__ import annotations

__all__: list[str] = []
