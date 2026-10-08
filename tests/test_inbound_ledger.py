import sqlite3
import pytest
from pathlib import Path
from app.channels.ledger import SqliteInboundLedger


@pytest.fixture
def temp_db(tmp_path: Path) -> Path:
    db_file = tmp_path / "test_ledger.db"
    return db_file


@pytest.mark.anyio
async def test_claim_first_time_returns_true(temp_db: Path):
    ledger = SqliteInboundLedger(db_path=temp_db)
    result = await ledger.claim("wa", "msg_12345")
    assert result is True


@pytest.mark.anyio
async def test_claim_duplicate_returns_false(temp_db: Path):
    ledger = SqliteInboundLedger(db_path=temp_db)
    first = await ledger.claim("wa", "msg_12345")
    second = await ledger.claim("wa", "msg_12345")
    assert first is True
    assert second is False


@pytest.mark.anyio
async def test_claim_distinct_channels_same_msg_id(temp_db: Path):
    ledger = SqliteInboundLedger(db_path=temp_db)
    wa_claim = await ledger.claim("wa", "msg_shared")
    tg_claim = await ledger.claim("tg", "msg_shared")
    assert wa_claim is True
    assert tg_claim is True


@pytest.mark.anyio
async def test_migration_script_applies_cleanly(temp_db: Path):
    migration_file = Path("migrations/001_inbound_ledger.sql")
    assert migration_file.exists(), "Migration file must exist"
    sql = migration_file.read_text(encoding="utf-8")
    with sqlite3.connect(temp_db) as conn:
        conn.executescript(sql)
    ledger = SqliteInboundLedger(db_path=temp_db)
    assert await ledger.claim("wa", "msg_migrated") is True
