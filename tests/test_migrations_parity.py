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


def test_legacy_database_upgrade_faithful(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Build a legacy database faithfully using old db.py logic (7fbfb78),
    insert rows into held, settings (auto_reply=1), audit, and verify:
    (a) upgrades without error and preserves all rows
    (b) failclosed clamp runs once (auto_reply clamped to 0)
    (c) legacy database that lacks reason and number gets them added
    (d) running init twice is a no-op
    (e) backup file is created
    """
    db_file = tmp_path / "faithful_legacy.db"
    monkeypatch.setattr(db, "DB_PATH", db_file)

    # 1. Create faithful legacy database as it existed in 7fbfb78 (or before reason/number)
    conn = sqlite3.connect(db_file)
    conn.execute("""CREATE TABLE held (
        id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, chat_id TEXT,
        incoming TEXT, reply TEXT, status TEXT DEFAULT 'pending'
    )""")
    # Note: omit reason and number columns to test (c)
    conn.execute("""CREATE TABLE audit (
        id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, kind TEXT, target TEXT
    )""")
    conn.execute("""CREATE TABLE messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, chat_id TEXT, role TEXT, content TEXT
    )""")
    conn.execute("CREATE TABLE contact_modes (name TEXT PRIMARY KEY, mode TEXT NOT NULL)")
    conn.execute("CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    conn.execute("""CREATE TABLE message_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, chat_id TEXT, name TEXT,
        direction TEXT, body TEXT, outcome TEXT
    )""")

    # Insert test data across held, settings, and audit
    conn.execute(
        "INSERT INTO held (ts, chat_id, incoming, reply, status) VALUES (?, ?, ?, ?, ?)",
        (1000.0, "chat123", "hello from contact", "draft reply", "pending"),
    )
    conn.execute(
        "INSERT INTO audit (ts, kind, target) VALUES (?, ?, ?)",
        (1001.0, "hold", "chat123"),
    )
    conn.execute("INSERT INTO settings (key, value) VALUES ('auto_reply', '1')")
    conn.execute("INSERT INTO settings (key, value) VALUES ('direct_send', '1')")
    conn.commit()
    conn.close()

    # Pre-check: columns reason and number do NOT exist yet
    conn_pre = sqlite3.connect(db_file)
    cols_pre = {r[1] for r in conn_pre.execute("PRAGMA table_info(held)").fetchall()}
    conn_pre.close()
    assert "reason" not in cols_pre
    assert "number" not in cols_pre

    # (a) Run new db.init(): upgrades without error
    db.init()

    # (e) Verify backup file was created
    backups = list(tmp_path.glob("faithful_legacy.db.*.bak"))
    assert len(backups) == 1
    assert backups[0].exists()

    conn_post = sqlite3.connect(db_file)
    # (a) Verify all original rows are preserved
    held_rows = conn_post.execute("SELECT id, chat_id, incoming, reply, status, reason, number FROM held").fetchall()
    assert len(held_rows) == 1
    assert held_rows[0][0] == 1
    assert held_rows[0][1] == "chat123"
    assert held_rows[0][2] == "hello from contact"
    assert held_rows[0][3] == "draft reply"
    assert held_rows[0][4] == "pending"

    audit_rows = conn_post.execute("SELECT id, kind, target FROM audit").fetchall()
    assert len(audit_rows) == 1
    assert audit_rows[0][1] == "hold"
    assert audit_rows[0][2] == "chat123"

    # (c) Verify reason and number columns are added
    cols_post = {r[1] for r in conn_post.execute("PRAGMA table_info(held)").fetchall()}
    assert "reason" in cols_post
    assert "number" in cols_post
    conn_post.close()

    # (b) Verify failclosed clamp ran once
    assert db.get_setting("auto_reply") == "0"
    assert db.get_setting("direct_send") == "0"
    assert db.get_setting(db.FAILCLOSED_MARKER) == "1"

    # Owner re-enables auto_reply
    db.set_setting("auto_reply", "1")

    # (d) Running init twice is a no-op
    db.init()
    assert db.get_setting("auto_reply") == "1"
    # No additional backups created
    assert len(list(tmp_path.glob("faithful_legacy.db.*.bak"))) == 1
