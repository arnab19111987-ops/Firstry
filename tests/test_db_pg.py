import pytest

from firsttry.db_pg import parse_destructive_ops, run_pg_probe


def test_parse_destructive_ops_classification():
    script = """
def upgrade():
    op.create_table('foo')
    op.drop_column('foo', 'old_col')
    op.add_column('foo', sa.Column('new_col', sa.String()))
    op.drop_table('bar')
    # raw SQL
    op.execute("DROP TABLE baz")
def downgrade():
    pass
"""
    ops = parse_destructive_ops(script)
    # destructive should include drops
    assert any("drop_column" in line for line in ops["destructive"])
    assert any("drop_table" in line for line in ops["destructive"])
    # create_table should land in non_destructive
    assert any("create_table" in line for line in ops["non_destructive"])


def test_run_pg_probe_skips_if_not_pg(monkeypatch):
    # make sure env not set
    monkeypatch.delenv("DATABASE_URL", raising=False)
    # no DB URL set
    res = run_pg_probe(import_target="backend")
    assert res["skipped"] is True
    assert "not Postgres" in res["reason"]

    # sqlite url shouldn't trigger Postgres logic
    monkeypatch.setenv("DATABASE_URL", "sqlite:///foo.db")
    res2 = run_pg_probe(import_target="backend")
    assert res2["skipped"] is True
    assert "not Postgres" in res2["reason"]


def test_run_pg_probe_destructive_raises(monkeypatch):
    """We can't run the full Alembic autogen without Postgres here.
    Instead we'll simulate the final destructive check by faking env:
    We'll set a real-looking PG URL, then monkeypatch _alembic_autogen_pg
    to return destructive ops.
    """
    from firsttry import db_pg

    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/db")

    def fake_autogen(import_target: str, db_url: str):
        return {
            "has_drift": True,
            "script_text": "irrelevant",
            "skipped": False,
            "ops": {
                "destructive": ["op.drop_table('foo')"],
                "non_destructive": ["op.create_table('bar')"],
            },
        }

    monkeypatch.setattr(db_pg, "_alembic_autogen_pg", fake_autogen)

    # not allowed → should raise
    with pytest.raises(RuntimeError):
        run_pg_probe(import_target="backend", allow_destructive=False)

    # allowed → should return dict and not raise
    ok = run_pg_probe(import_target="backend", allow_destructive=True)
    assert ok["skipped"] is False
    assert ok["has_drift"] is True
    assert ok["ops"]["destructive"]
