# mypy: ignore-errors
from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

# Import sqlalchemy early, before other imports that might skip
try:
    import sqlalchemy as sa
    from sqlalchemy.orm import declarative_base
except ImportError:
    pytest.importorskip("sqlalchemy", reason="SQLAlchemy required for DB tests")

from firsttry.db_sqlite import _extract_upgrade_body
from firsttry.db_sqlite import run_sqlite_probe


def _install_fake_backend_module(mod_name: str = "backend"):
    Base = declarative_base()

    class Foo(Base):
        __tablename__ = "foo"
        id = sa.Column(sa.Integer, primary_key=True)
        name = sa.Column(sa.String(50), nullable=False)

    fake_backend = types.ModuleType(mod_name)
    fake_backend.Base = Base
    fake_backend.Foo = Foo

    sys.modules[mod_name] = fake_backend
    return fake_backend


def test_extract_upgrade_body_simple():
    script = """
def upgrade():
    op.create_table('foo')
    op.add_column('bar', sa.Column('x', sa.Integer()))
def downgrade():
    pass
"""
    body = _extract_upgrade_body(script)
    assert "create_table" in body
    assert "add_column" in body
    assert "downgrade" not in body


def test_run_sqlite_probe_import_and_drift(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    _install_fake_backend_module("backend")

    result = run_sqlite_probe(import_target="backend")

    assert "import_ok" in result
    assert result["import_ok"] is True
    assert result["import_error"] is None

    assert result["drift"] in ("pending_migrations", "skipped")

    assert Path(".firsttry.db").exists()
