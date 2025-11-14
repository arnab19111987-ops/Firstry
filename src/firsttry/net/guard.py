from __future__ import annotations


class NetworkDisabled(RuntimeError): ...


class NetworkGuard:
    def __init__(self, enabled: bool):
        self.disabled = enabled

    def assert_allowed(self, reason: str = ""):
        if self.disabled:
            raise NetworkDisabled(f"Network disabled by policy. {reason}".strip())
