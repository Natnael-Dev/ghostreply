"""Verify SQLite migrations parity, idempotency, and backup creation."""
from pathlib import Path
import sqlite3
import pytest

from app import db
from app.migrations import run_migrations, create_backup, get_applied_migrations


def get_schema_fingerprint(conn: sqlite3.Connection) -> dict:
    """Extract normalized schema information: tables, columns, indexes, triggers."""
    # Exclude schema_migrations tracking table from parity comparison
    tables = [
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name != 'schema_migrations' ORDER BY name"
        ).fetchall()
    ]

    schema = {}
    for table in tables:
        cols = conn.execute(f"PRAGMA table_info({table})").fetchall()
        # col: (cid, name, type, notnull, dflt_value, pk)
        normalized_cols = [
            (c[1], (c[2] or "").upper(), c[3], str(c[4]), c[5])
            for c in cols
        ]
        indexes = conn.execute(f"PRAGMA index_list({table})").fetchall()
        normalized_indexes = sorted([idx[1] for idx in indexes])
        schema[table] = {
            "columns": normalized_cols,
            "indexes": normalized_indexes,
        }

    triggers = [
        (r[0], r[1], " ".join((r[2] or "").split()))
        for r in conn.execute(
            "SELECT name, tbl_name, sql FROM sqlite_master WHERE type='trigger' ORDER BY name"
        ).fetchall()
    ]
    return {"schema": schema, "triggers": triggers}


def test_migrations_create_backup(tmp_path: Path):
    db_file = tmp_path / "test.db"
    conn = sqlite3.connect(db_file)
    conn.execute("CREATE TABLE foo (id INT)")
    conn.commit()
    conn.close()

    backup = create_backup(db_file)
    assert backup is not None
    assert backup.exists()
    assert backup.name.startswith("test.db.")
    assert backup.name.endswith(".bak")


def test_migrations_parity_fresh_vs_upgraded(tmp_path: Path):
    # 1. Fresh database initialized via migrations
    fresh_db_path = tmp_path / "fresh.db"
    run_migrations(fresh_db_path)
    fresh_conn = sqlite3.connect(fresh_db_path)
    fresh_fingerprint = get_schema_fingerprint(fresh_conn)
    fresh_conn.close()

    # 2. Legacy database pre-created with initial legacy schema and upgraded
    legacy_db_path = tmp_path / "legacy.db"
    legacy_conn = sqlite3.connect(legacy_db_path)
    # Simulate early legacy schema without reason and number columns
    legacy_conn.execute("""
        CREATE TABLE held (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts REAL,
            chat_id TEXT,
            incoming TEXT,
            reply TEXT,
            status TEXT DEFAULT 'pending'
        )
    """)
    legacy_conn.commit()
    legacy_conn.close()

    # Run migrations on legacy database
    run_migrations(legacy_db_path)
    upgraded_conn = sqlite3.connect(legacy_db_path)
    upgraded_fingerprint = get_schema_fingerprint(upgraded_conn)
    upgraded_conn.close()

    # Assert exact schema parity
    assert fresh_fingerprint["schema"] == upgraded_fingerprint["schema"]
    assert fresh_fingerprint["triggers"] == upgraded_fingerprint["triggers"]


def test_migrations_idempotency_and_double_run(tmp_path: Path):
    db_path = tmp_path / "idempotent.db"
    applied_first = run_migrations(db_path)
    assert len(applied_first) >= 4
    assert "000_baseline_schema.sql" in applied_first
    assert "001_inbound_ledger.sql" in applied_first
    assert "002_audit_log_triggers.sql" in applied_first
    assert "003_add_held_reason_and_number.sql" in applied_first

    # Second run should apply 0 migrations and make no backups
    backups_before = list(tmp_path.glob("*.bak"))
    applied_second = run_migrations(db_path)
    assert applied_second == []
    backups_after = list(tmp_path.glob("*.bak"))
    assert len(backups_after) == len(backups_before)


def test_schema_migrations_table_tracking(tmp_path: Path):
    db_path = tmp_path / "tracking.db"
    run_migrations(db_path)

    conn = sqlite3.connect(db_path)
    applied = get_applied_migrations(conn)
    conn.close()

    assert "000_baseline_schema.sql" in applied
    assert "001_inbound_ledger.sql" in applied
    assert "002_audit_log_triggers.sql" in applied
    assert "003_add_held_reason_and_number.sql" in applied


def test_failclosed_clamp_runs_once(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Legacy DB with auto_reply=1 is clamped once; owner re-enables it; a second init keeps it."""
    db_file = tmp_path / "legacy_clamp.db"
    monkeypatch.setattr(db, "DB_PATH", db_file)

    # 1. Simulate legacy DB before failclosed clamp, with auto_reply='1'
    conn = sqlite3.connect(db_file)
    conn.execute("CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    conn.execute("INSERT INTO settings (key, value) VALUES ('auto_reply', '1')")
    conn.execute("INSERT INTO settings (key, value) VALUES ('direct_send', '1')")
    conn.commit()
    conn.close()

    # First init(): migrations run, then fail-closed clamp runs
    db.init()

    # auto_reply and direct_send clamped to '0'
    assert db.get_setting("auto_reply") == "0"
    assert db.get_setting("direct_send") == "0"
    assert db.get_setting(db.FAILCLOSED_MARKER) == "1"

    # Owner re-enables auto_reply
    db.set_setting("auto_reply", "1")
    assert db.get_setting("auto_reply") == "1"

    # Second init(): marker is present, clamp must NOT overwrite owner choice
    db.init()
    assert db.get_setting("auto_reply") == "1"
