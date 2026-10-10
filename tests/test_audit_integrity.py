"""Adversarial audit log immutability and trigger tests (T2)."""
from pathlib import Path
import sqlite3
import pytest

from app import db


@pytest.fixture
def audit_db(tmp_path: Path, monkeypatch):
    test_db_path = tmp_path / "audit_test.db"
    monkeypatch.setattr(db, "DB_PATH", test_db_path)
    db.init()
    return test_db_path


def test_migration_002_applies_cleanly(tmp_path: Path):
    migration_file = Path("migrations/002_audit_log_triggers.sql")
    assert migration_file.exists(), "Migration 002 file must exist"

    db_path = tmp_path / "migration_test.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "CREATE TABLE audit (id INTEGER PRIMARY KEY, ts REAL, kind TEXT, target TEXT)"
        )
        conn.executescript(migration_file.read_text(encoding="utf-8"))

        # Verify triggers are registered
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'trigger'"
        )
        triggers = {row[0] for row in cur.fetchall()}
        assert "trg_audit_no_update" in triggers
        assert "trg_audit_no_delete" in triggers


def test_audit_insert_succeeds(audit_db):
    db.log("test_event", "target_user")
    records = db.recent_audit(limit=10)
    assert len(records) >= 1
    assert records[0]["kind"] == "test_event"
    assert records[0]["target"] == "target_user"


def test_audit_update_aborts_with_integrity_error(audit_db):
    db.log("login_success", "user_1")
    with sqlite3.connect(audit_db) as conn:
        cur = conn.execute("SELECT id, kind FROM audit LIMIT 1")
        record_id, original_kind = cur.fetchone()

        with pytest.raises((sqlite3.IntegrityError, sqlite3.OperationalError)) as exc:
            conn.execute(
                "UPDATE audit SET kind = 'tampered' WHERE id = ?",
                (record_id,),
            )
        assert "Audit log is append-only" in str(exc.value)

        # Assert unchanged
        cur = conn.execute("SELECT kind FROM audit WHERE id = ?", (record_id,))
        assert cur.fetchone()[0] == original_kind


def test_audit_delete_aborts_with_integrity_error(audit_db):
    db.log("login_failure", "user_2")
    with sqlite3.connect(audit_db) as conn:
        cur = conn.execute("SELECT id FROM audit LIMIT 1")
        record_id = cur.fetchone()[0]

        with pytest.raises((sqlite3.IntegrityError, sqlite3.OperationalError)) as exc:
            conn.execute("DELETE FROM audit WHERE id = ?", (record_id,))
        assert "Audit log is append-only" in str(exc.value)

        # Assert record still exists
        cur = conn.execute("SELECT COUNT(*) FROM audit WHERE id = ?", (record_id,))
        assert cur.fetchone()[0] == 1
