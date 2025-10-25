"""Day 4 probe:
- Force DATABASE_URL to local sqlite file ./.firsttry.db
- Try importing the target module (default: "backend")
- Run a safe Alembic autogenerate in a temp dir, NOT touching your repo

Public API:
    run_sqlite_probe(import_target: str = "backend") -> dict
"""

from __future__ import annotations

import importlib
import os
import tempfile
import time
from pathlib import Path
from typing import Optional, Tuple


def _set_sqlite_env(db_path: str = "./.firsttry.db") -> str:
    url = f"sqlite:///{db_path}"
    os.environ["DATABASE_URL"] = url
    return url


def _try_import(import_target: str) -> Tuple[bool, Optional[BaseException]]:
    try:
        importlib.import_module(import_target)
        return True, None
    except BaseException as exc:  # broad on purpose; we want to capture anything
        return False, exc


def _guess_metadata_module(import_target: str):
    """
    We try a couple of common places to get SQLAlchemy Base.metadata.
    Rules:
    - backend.Base.metadata
    - backend.db.Base.metadata
    - backend.models.Base.metadata
    Return (metadata_obj | None, note:str)
    """
    tried = []

    def probe(mod_name: str):
        try:
            mod = importlib.import_module(mod_name)
        except ImportError as e:
            tried.append((mod_name, f"ImportError: {e}"))
            return None
        # Common patterns
        for attr_candidate in ("Base", "base", "DBBase"):
            base_obj = getattr(mod, attr_candidate, None)
            if base_obj is not None and hasattr(base_obj, "metadata"):
                return base_obj.metadata
        # direct metadata attr
        if hasattr(mod, "metadata"):
            return getattr(mod, "metadata")
        tried.append((mod_name, "No Base/metadata found"))
        return None

    # probes, in priority order
    for candidate in (
        import_target,
        f"{import_target}.db",
        f"{import_target}.models",
    ):
        md = probe(candidate)
        if md is not None:
            return md, f"metadata from {candidate}"

    return None, f"No metadata found; tried {tried!r}"


def _write_temp_alembic_env(temp_dir: Path, import_target: str) -> None:
    """
    Create a minimal Alembic environment in temp_dir:
    temp_dir/
      env.py
      script.py.mako (alembic needs this template)
      versions/        (empty dir where revision goes)
    """
    versions_dir = temp_dir / "versions"
    versions_dir.mkdir(parents=True, exist_ok=True)

    # Alembic needs a template for new revisions.
    # We'll drop a very small script.py.mako that produces upgrade()/downgrade().
    (temp_dir / "script.py.mako").write_text(
        """# ${message}
#
# Revision ID: ${up_revision}
# Revises: ${down_revision | comma,n}
# Create Date: ${create_date}
#
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


def upgrade():
${upgrades if upgrades else "    pass"}


def downgrade():
${downgrades if downgrades else "    pass"}
""",
        encoding="utf-8",
    )

    # env.py: we import the user's code dynamically to discover metadata at runtime.
    # We do NOT bake metadata into this file so we don't have to serialize it.
    env_py = f"""\
import os
import importlib
from alembic import context
from sqlalchemy import engine_from_config, pool

config = context.config

# Make sure sqlalchemy.url is set from env var or fallback
db_url = os.environ.get("DATABASE_URL")
if db_url:
    config.set_main_option("sqlalchemy.url", db_url)

def _resolve_metadata():
    target_mod = "{import_target}"
    tried = []

    def probe(mod_name: str):
        try:
            mod = importlib.import_module(mod_name)
        except ImportError as e:
            tried.append((mod_name, f"ImportError: {{e}}"))
            return None
        for attr_candidate in ("Base", "base", "DBBase"):
            base_obj = getattr(mod, attr_candidate, None)
            if base_obj is not None and hasattr(base_obj, "metadata"):
                return base_obj.metadata
        if hasattr(mod, "metadata"):
            return getattr(mod, "metadata")
        tried.append((mod_name, "No Base/metadata found"))
        return None

    for candidate in (
        target_mod,
        f"{import_target}.db",
        f"{import_target}.models",
    ):
        md = probe(candidate)
        if md is not None:
            return md
    raise RuntimeError(f"No SQLAlchemy metadata found in {{tried!r}}")

target_metadata = _resolve_metadata()

def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section) or {{ }},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()

run_migrations_online()
"""
    (temp_dir / "env.py").write_text(env_py, encoding="utf-8")


def _run_alembic_autogen(import_target: str, db_url: str) -> dict:
    """
    We programmatically drive Alembic's `revision --autogenerate` into a temp dir.
    Returns:
        {
          "has_drift": bool,
          "revision_file": Path,
          "preview": str,
        }
    If we can't complete (no metadata, no alembic installed, etc.) we mark skipped.
    """
    try:
        from alembic.config import Config
        from alembic import command
    except ImportError as e:  # Alembic not installed
        return {
            "skipped": True,
            "reason": f"Alembic not available: {e}",
        }

    with tempfile.TemporaryDirectory(prefix="firsttry_alembic_") as tmp:
        tmp_path = Path(tmp)
        _write_temp_alembic_env(tmp_path, import_target)

        cfg = Config()  # in-memory config
        cfg.set_main_option("script_location", str(tmp_path))
        cfg.set_main_option("sqlalchemy.url", db_url)

        message = f"firsttry_autogen_probe_{int(time.time())}"
        command.revision(
            cfg,
            message=message,
            autogenerate=True,
        )

        # Alembic will have created exactly one file in versions/
        versions_dir = tmp_path / "versions"
        rev_files = list(versions_dir.glob("*.py"))
        if not rev_files:
            # nothing created = no drift
            return {
                "has_drift": False,
                "revision_file": None,
                "preview": "",
                "skipped": False,
            }

        rev_file = rev_files[0]
        script_text = rev_file.read_text(encoding="utf-8")

        # Heuristic: if upgrade() body is only "pass", no drift.
        has_drift = (
            "def upgrade()" in script_text
            and "pass" not in _extract_upgrade_body(script_text)
        )

        return {
            "has_drift": has_drift,
            "revision_file": rev_file,
            "preview": script_text,
            "skipped": False,
        }


def _extract_upgrade_body(script_text: str) -> str:
    """
    Extract the body of upgrade() for heuristic drift detection.
    We'll do a simple textual slice, not full AST.
    """
    up_start = script_text.find("def upgrade()")
    if up_start == -1:
        return ""
    up_block = script_text[up_start:]
    # cut off at next def
    next_def = up_block.find("def downgrade()")
    if next_def != -1:
        up_block = up_block[:next_def]
    # remove header line
    lines = up_block.splitlines()[1:]
    # strip leading indentation consistently
    stripped = "\n".join(line.lstrip() for line in lines)
    return stripped.strip()


def run_sqlite_probe(import_target: str = "backend") -> dict:
    """
    High-level probe.
    Returns:
    {
        "import_ok": bool,
        "import_error": str | None,
        "drift": "none" | "pending_migrations" | "skipped",
        "details": str,
    }
    """
    db_url = _set_sqlite_env("./.firsttry.db")

    ok, err = _try_import(import_target)

    if not ok:
        return {
            "import_ok": False,
            "import_error": repr(err),
            "drift": "skipped",
            "details": "Import failed, skipped autogen",
        }

    autogen_res = _run_alembic_autogen(import_target, db_url)

    if autogen_res.get("skipped"):
        return {
            "import_ok": True,
            "import_error": None,
            "drift": "skipped",
            "details": autogen_res.get("reason", "autogen skipped"),
        }

    drift_status = "pending_migrations" if autogen_res["has_drift"] else "none"
    return {
        "import_ok": True,
        "import_error": None,
        "drift": drift_status,
        "details": ("Import ok" if drift_status == "none" else "Schema drift detected"),
    }
