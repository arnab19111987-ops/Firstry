"""Shim module to expose `licensing.app.main` as `app.main` for tests.
"""
from licensing.app.main import app as app  # re-export the FastAPI app

__all__ = ["app"]
